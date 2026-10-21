"""Modal wrapper of the stage A estimands (scripts/estimands_v1.py), on the image of
scripts/modal_recode_v1.py. No model is called. Reads the accepted codes and the packets on the
volume, Paper 1's assemblies (amended primary, and the originally registered corpus passed from
the local repository), and writes counts, classes, bounds and seeds; no quotation.

    PYTHONPATH=../03_release_resolution/scripts modal run scripts/modal_estimands_v1.py::tests
    ... modal run --detach scripts/modal_estimands_v1.py::estimate --estimates <json> --indices <json>
"""

import collections
import csv
import hashlib
import json

import modal

from modal_coding_v2 import CHECKS, E2, E3, MOUNT, REG, ROOT, vol
from modal_judges_stage_a_v1 import FOLDER
from modal_recode_v1 import LOCAL, PACKETS, image, write_once
from modal_retrieve_v2 import E4, PAPER1

app = modal.App("release-resolution-v2-estimands", image=image)
ORIGINAL = "outputs/registry/2026-10-03_registered_with_27_coded_a"
META = "../03_release_resolution/reference/meta_analysis_expansions_omitted_v2.csv"

with image.imports():
    import subprocess

    import build_registry as br
    import coding_queue as q
    import estimands_v1 as es
    import recode_v1 as rc
    from build_registry import RegistryClaim
    from dataset_relations import load_rows


@app.function(timeout=1800, memory=8192)
def tests_job() -> dict:
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                          "test_estimands_v1.py"], capture_output=True, text=True,
                         cwd=f"{E4}/tests")
    return {"returncode": run.returncode, "output": run.stdout + run.stderr}


def read_claims(lines):
    return [RegistryClaim.model_validate_json(l) for l in lines if l.strip()]


def plain_of(lines):
    out = {}
    for l in lines:
        if l.strip():
            r = json.loads(l)
            out[r["claim_record_id"]] = r
    return out


def written_of() -> dict:
    out = {}
    for c in CHECKS:
        for l in open(f"{E2}/{c}").read().splitlines():
            if l.strip():
                r = json.loads(l)
                if "claim_record_id" in r:
                    out.setdefault(r["claim_record_id"], r["outcome_as_written"])
    return out


def strip(t: dict) -> dict:
    return {k: v for k, v in t.items() if not k.startswith("_")}


@app.function(volumes={str(MOUNT): vol}, timeout=12 * 3600, memory=32768, cpu=4.0)
def estimate_job(meta_rows: list[str], original_coded: list[str], original_plain: list[str],
                 metadata: dict, dates: dict, platforms: dict) -> dict:
    vol.reload()
    rows = load_rows()
    components = {r.name: r.components for r in rows}
    meta = set(meta_rows)
    coded = read_claims(open(f"{E2}/{REG}/registry_claims.jsonl").read().splitlines())
    plain = plain_of(open(f"{E2}/{REG}/registry_claims_without_manual_coding.jsonl").read()
                     .splitlines())
    written = written_of()
    accepted_full = json.loads((FOLDER / "accepted" / "stage_a.json").read_text())
    accepted = {rid: {"accepted": a["accepted"], "code": a["code"]}
                for rid, a in accepted_full.items()}
    manifest = json.loads((PACKETS / "manifest.json").read_text())
    packets = {m["name"]: json.loads((PACKETS / f"{m['name']}.json").read_text())
               for m in manifest}
    scope_packets = {m["record_id"]: packets[m["name"]] for m in manifest
                     if m["population"] == "scope"}
    routes, kinds_of_file = {}, {}
    for rec, p in scope_packets.items():
        sources = json.loads((ROOT / "retrieval" / rec / "result.json").read_text())["sources"]
        fr = rc.frozen_files(p, sources)
        routes[rec] = {fid: f.get("route") for fid, f in fr.items()}
        kinds_of_file[rec] = {f["file_id"]: f["kind"] for f in p["files"]}
    queue = json.loads((ROOT / "coding" / "inputs" / "queue.json").read_text())["queue"]
    study = {r["row_id"]: r for r in queue}

    def keep_for(rid):
        rec = study[rid]["record_id"]
        ev = accepted[rid]["code"]["decisive_evidence"]

        def ok(release):
            return any(e["release"] == release and (
                kinds_of_file[rec].get(e["file_id"]) == "abstract"
                or routes[rec].get(e["file_id"]) == "R1") for e in ev)
        return ok

    keep = {rid: keep_for(rid) for rid in study if accepted.get(rid, {}).get("accepted")}

    variants, stats = {}, {}
    for name, kwargs in (("primary", {}),
                         ("without_attribution_resolution", {"attribution_resolution": False}),
                         ("europe_pmc_sources_only", {"keep": keep})):
        claims, st = es.claims_with_codes(coded, plain, written, accepted, **kwargs)
        registry = br.build(claims, rows)
        variants[name] = es.tables_rep(registry, meta, components)
        stats[name] = st
        if name == "primary":
            primary_registry = registry
    paper1_registry = br.build(coded, rows)
    before = {pair: (br.pair_h2(f), br.pair_overlap(f))
              for pair, f in paper1_registry.items() if len(f) >= 2}
    after = es.pair_classes(primary_registry, meta, components)
    paper1_est = strip(br.estimates(paper1_registry))

    o_coded = read_claims(original_coded)
    o_plain = plain_of(original_plain)
    o_claims, o_st = es.claims_with_codes(o_coded, o_plain, written, accepted)
    original = es.tables_rep(br.build(o_claims, rows), meta, components)

    # Mention-level indices over the scope's study rows.
    has_full = {rec: any(f["kind"] == "full_text" for f in p["files"])
                for rec, p in scope_packets.items()}
    mentions = []
    for rid, r in study.items():
        a = accepted.get(rid)
        rec = r["record_id"]
        name = r["name_as_written"]
        state = "not_stated" if name == q.SHOWN_NOT_STATED else es.mention_state(name, r["side"],
                                                                                 rows)
        ev = (a["code"]["decisive_evidence"] if a and a["accepted"] else [])
        locs = {("abstract" if kinds_of_file[rec].get(e["file_id"]) == "abstract"
                 else "full_text") for e in ev}
        fts = [routes[rec][f] for f, k in kinds_of_file[rec].items() if k == "full_text"]
        mentions.append({"row_id": rid, "record_id": rec, "side": r["side"],
                         "abstract_state": state, "resolved": es.resolved(a),
                         "locations": locs,
                         "transition": (a["code"].get("abstract_transition", "settled_row")
                                        if a and a["accepted"] else "not_accepted"),
                         "route": "R1" if "R1" in fts else "R3" if "R3" in fts else "none",
                         "has_full_text": has_full[rec]})
    indices = es.mention_indices(mentions)

    # Rows with no eligible source and no decisive abstract evidence: the pipeline's no_source.
    indices["no_source_rows"] = sum(1 for m in mentions if not m["has_full_text"]
                                    and not m["resolved"])

    # Attribution transitions (added rule 1).
    scope_records = set(scope_packets)
    unclear = [c for c in coded if c.claim_record_id.rsplit(":", 1)[0] in scope_records
               and c.dataset_attribution == "unclear"]
    settled_ids = set()
    prim_claims, _ = es.claims_with_codes(coded, plain, written, accepted)
    by_id = {c.claim_record_id: c for c in prim_claims}
    for c in unclear:
        if by_id[c.claim_record_id].dataset_attribution != "unclear":
            settled_ids.add(c.claim_record_id)
    multi_pairs = {pair for pair, f in primary_registry.items() if len(f) >= 2}
    pairs_of = collections.defaultdict(set)
    for c in coded:
        if (c.protein_id, c.outcome_id) in multi_pairs:
            pairs_of[c.claim_record_id].add((c.protein_id, c.outcome_id))
    indices["attribution_transitions"] = {
        "claim_records_unclear_in_paper1": len(unclear),
        "unclear_to_resolved": len(settled_ids),
        "still_unclear": len(unclear) - len(settled_ids),
        "repeated_pairs_held_by_unclear_records": len({p for c in unclear
                                                       for p in pairs_of[c.claim_record_id]}),
        "repeated_pairs_held_by_records_still_unclear": len(
            {p for c in unclear if c.claim_record_id not in settled_ids
             for p in pairs_of[c.claim_record_id]})}

    # Agreement with Paper 1's accepted manual codes (comparison only).
    seen, agree = set(), collections.Counter()
    for c in coded:
        rec = c.claim_record_id.rsplit(":", 1)[0]
        if rec not in scope_records:
            continue
        for item in c.manual_dataset_codes:
            side, name, row = item.split("|", 2)
            rid = es.row_key(c.claim_record_id, side, name, written[c.claim_record_id])
            if rid in seen:
                continue
            seen.add(rid)
            a = accepted.get(rid)
            rels = set(es.entering(a["code"])) if a and a["accepted"] else set()
            agree["same_row" if rels == {row} else "another_row" if rels
                  else "unresolved_here"] += 1
    indices["agreement_with_paper1_codes"] = {"mentions": len(seen), **dict(agree)}

    # Pair movement, fully accessible pairs, pairs unresolved for want of a source.
    indices["pair_movement"] = es.movement(before, after)
    fam_records = collections.defaultdict(set)
    for c in prim_claims:
        fam_records[(c.protein_id, c.outcome_id)].add(c.claim_record_id.rsplit(":", 1)[0])
    accessible = [p for p in multi_pairs if all(has_full.get(r, False)
                                                for r in fam_records[p])]
    cls = {p: after[p] for p in accessible}
    n = len(accessible)
    h2c = collections.Counter(v[0] for v in cls.values())
    h2bc = collections.Counter(v[1] for v in cls.values())
    indices["fully_accessible_pairs"] = {
        "pairs": n, "h2": dict(h2c), "h2b": dict(h2bc),
        "h2_lower": h2c["known_identical"] / n if n else None,
        "h2_upper": (h2c["known_identical"] + h2c["unresolved"]) / n if n else None,
        "h2b_lower": h2bc["known_overlapping"] / n if n else None,
        "h2b_upper": (h2bc["known_overlapping"] + h2bc["unresolved"]) / n if n else None,
        "note": "descriptive; no verdict"}
    rows_of_pair = collections.defaultdict(list)
    for c in coded:
        pair = (c.protein_id, c.outcome_id)
        if pair not in multi_pairs:
            continue
        for side, field in (("pqtl", "pqtl_datasets"), ("outcome", "outcome_datasets")):
            for name in plain[c.claim_record_id][field]:
                rows_of_pair[pair].append(es.row_key(c.claim_record_id, side, name,
                                                     written[c.claim_record_id]))
    by_row = {m["row_id"]: m for m in mentions}
    want = 0
    for p in multi_pairs:
        if after[p][0] != "unresolved":
            continue
        blocking = [by_row[r] for r in rows_of_pair[p] if r in by_row and not by_row[r]["resolved"]]
        if blocking and all(not m["has_full_text"] for m in blocking):
            want += 1
    indices["pairs_unresolved_for_want_of_a_source"] = {
        "pairs": want, "unresolved_pairs": sum(after[p][0] == "unresolved" for p in multi_pairs),
        "definition": "H2-unresolved pairs whose every unresolved mention comes from a record "
                      "with no eligible source other than the abstract"}

    # Source availability of the scope's papers.
    avail = collections.defaultdict(lambda: collections.Counter())
    pq_rows = collections.defaultdict(set)
    for m in mentions:
        a = accepted.get(m["row_id"])
        if m["side"] == "pqtl" and a and a["accepted"]:
            for rel in es.entering(a["code"]):
                pq_rows[m["record_id"]].add(platforms.get(rel, "other"))
    for rec in scope_records:
        plat = pq_rows[rec]
        platform = ("not_stated" if not plat else plat.pop() if len(plat) == 1 else "mixed")
        for dim, value in (("year", (dates.get(rec) or {}).get("value", "")[:4] or "unknown"),
                           ("journal", (metadata.get(rec) or {}).get("journal") or "unknown"),
                           ("document_class", (metadata.get(rec) or {}).get("kind") or "unknown"),
                           ("proteomic_assay_platform", platform)):
            avail[dim][f"{value}|{'eligible_source' if has_full[rec] else 'abstract_only'}"] += 1
    indices["source_availability"] = {
        "papers": len(scope_records), "with_an_eligible_source": sum(has_full.values()),
        **{k: dict(sorted(v.items())) for k, v in avail.items()}}
    indices["canonicalization"] = {
        "comparisons_canonicalized": 0,
        "comparisons_representation_unresolved":
            variants["primary"]["estimates"]["representation_unresolved_comparisons"],
        "repeated_pairs_with_one": variants["primary"]["estimates"]
        ["representation_unresolved_pairs"],
        "note": "no meta-analysis row has an expansion (reference/meta_analysis_expansions_v2.csv)"}
    return {"variants": {k: strip(v) for k, v in variants.items()},
            "claims_stats": stats, "originally_registered_corpus": strip(original),
            "originally_registered_corpus_stats": o_st,
            "paper1_registered_amended_primary": paper1_est,
            "indices": indices,
            "inputs_sha256": {
                "volume:04_release_resolution_v2/coding/accepted/stage_a.json":
                    hashlib.sha256((FOLDER / "accepted" / "stage_a.json").read_bytes()).hexdigest(),
                "volume:04_release_resolution_v2/packets/stage_a/manifest.json":
                    hashlib.sha256((PACKETS / "manifest.json").read_bytes()).hexdigest()},
            "seeds": {"pair_bootstrap": br.SEED, "protein_cluster_bootstrap": [br.SEED, 1],
                      "replicates": br.N_BOOT}}


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-3000:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def estimate(estimates: str, indices: str) -> None:
    meta_rows = sorted({r["meta_analysis_row"] for r in csv.DictReader(
        (LOCAL / META).read_text().splitlines())})
    reg = PAPER1 / ORIGINAL
    metadata = {}
    for line in (PAPER1 / f"{REG}/record_metadata.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            metadata[r["record_id"]] = {"journal": r.get("journal"), "kind": r.get("kind")}
    dates = json.loads((PAPER1 / f"{REG}/record_dates.json").read_text())
    platforms = {r["dictionary_row"]: r["platform_family"] for r in csv.DictReader(
        (PAPER1 / "verification/pqtl_row_attributes.csv").read_text().splitlines())}
    result = estimate_job.remote(
        meta_rows, (reg / "registry_claims.jsonl").read_text().splitlines(),
        (reg / "registry_claims_without_manual_coding.jsonl").read_text().splitlines(),
        metadata, dates, platforms)
    files = {f"../02_claims_meta/{p}": hashlib.sha256((PAPER1 / p).read_bytes()).hexdigest()
             for p in (f"{REG}/registry_claims.jsonl",
                       f"{REG}/registry_claims_without_manual_coding.jsonl",
                       f"{REG}/record_metadata.jsonl", f"{REG}/record_dates.json",
                       f"{ORIGINAL}/registry_claims.jsonl",
                       f"{ORIGINAL}/registry_claims_without_manual_coding.jsonl",
                       "verification/pqtl_row_attributes.csv", "dataset_dictionary.csv",
                       "verification/dataset_components.csv")}
    files[META] = hashlib.sha256((LOCAL / META).read_bytes()).hexdigest()
    inputs = result.pop("inputs_sha256") | files
    idx = result.pop("indices")
    write_once(estimates, {"script": "scripts/estimands_v1.py", "inputs_sha256": inputs,
                           **result})
    write_once(indices, {"script": "scripts/estimands_v1.py", "inputs_sha256": inputs, **idx})
    print("written", estimates, indices)
