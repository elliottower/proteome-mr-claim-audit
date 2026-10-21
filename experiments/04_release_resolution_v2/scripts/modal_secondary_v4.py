"""Fourth version of the secondary wrapper: a copy of scripts/modal_secondary_v1.py (sealed, left
unchanged) whose image also holds Paper 1's families.json (amended primary assembly), which SA6
reads; the first run stopped without it, and versions 2 and 3, which tried to reuse the first
version's job, stopped before any job ran. Nothing else differs from the first version.

Modal wrapper of the remaining registered analyses of the second registration's stage A
(scripts/secondary_v1.py; scripts/estimands_v1.py for the classes and bounds), on the image of
scripts/modal_recode_v1.py. No model is called. Writes counts, classes, bounds and seeds; no
quotation.

    PYTHONPATH=../03_release_resolution/scripts modal run scripts/modal_secondary_v4.py::tests
    ... modal run --detach scripts/modal_secondary_v4.py::run --sensitivity <json> --secondary <json>
"""

import collections
import csv
import hashlib
import json

import modal

from modal_coding_v2 import CHECKS, DEFINITIONS, E2, E3, MOUNT, REG, ROOT, vol
from modal_judges_stage_a_v1 import FOLDER
from modal_recode_v1 import LOCAL, PACKETS, image as base, write_once
from modal_retrieve_v2 import E4, PAPER1
from modal_calibration_stage_a_v1 import MARKS, MARKS_SHA256

image = base.add_local_file(PAPER1 / REG / "families.json", f"{E2}/{REG}/families.json",
                            copy=True)
app = modal.App("release-resolution-v2-secondary-4", image=image)
META = "../03_release_resolution/reference/meta_analysis_expansions_omitted_v2.csv"

with image.imports():
    import pathlib
    import subprocess

    import author_page_helper_v1 as helper
    import build_registry as br
    import c1_controls as c1
    import coding_queue as q
    import estimands_v1 as es
    import secondary_v1 as sv
    import source_scanner_v2 as scanner
    from dataset_relations import load_rows
    from modal_estimands_v1 import plain_of, read_claims, strip, written_of


@app.function(timeout=1800, memory=8192)
def tests_job() -> dict:
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                          "test_secondary_v1.py", "test_estimands_v1.py"],
                         capture_output=True, text=True, cwd=f"{E4}/tests")
    return {"returncode": run.returncode, "output": run.stdout + run.stderr}


def answers_of(model: str) -> dict:
    out = {}
    for path in sorted((FOLDER / "answers" / "stage_a" / model).glob("*.json")):
        if ".attempt" in path.name:
            continue
        f = json.loads(path.read_text())
        if f["state"] == "accepted":
            for row in f["answer"]["rows"]:
                out[row["row_id"]] = row
    return out


def wilson(k, n):
    w = br.wilson(k, n)
    return [round(x, 4) for x in w] if w else None


@app.function(volumes={str(MOUNT): vol}, timeout=24 * 3600, memory=65536, cpu=4.0)
def run_job(meta_rows: list[str], marks: dict, dates: dict) -> dict:
    vol.reload()
    rows = load_rows()
    components = {r.name: r.components for r in rows}
    meta = set(meta_rows)
    definitions = helper.load_dictionary(pathlib.Path(f"{E2}/{DEFINITIONS}"))
    counts_by_pair = collections.defaultdict(list)
    with open(f"{E3}/reference/release_counts.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            counts_by_pair[(sv.digits(r["cases"]), sv.digits(r["controls"]))].append(r)
    coded = read_claims(open(f"{E2}/{REG}/registry_claims.jsonl").read().splitlines())
    plain = plain_of(open(f"{E2}/{REG}/registry_claims_without_manual_coding.jsonl").read()
                     .splitlines())
    written = written_of()
    acc_full = json.loads((FOLDER / "accepted" / "stage_a.json").read_text())
    accepted = {rid: {"accepted": a["accepted"], "code": a["code"]} for rid, a in acc_full.items()}
    answers = {m: answers_of(m) for m in ("claude-sonnet-5-5", "gpt-6.1-sol")}
    manifest = json.loads((PACKETS / "manifest.json").read_text())
    scope_packets = {m["record_id"]: json.loads((PACKETS / f"{m['name']}.json").read_text())
                     for m in manifest if m["population"] == "scope"}
    kinds_of_file, has_full, status = {}, {}, {}
    for rec, p in scope_packets.items():
        kinds_of_file[rec] = {f["file_id"]: f["kind"] for f in p["files"]}
        has_full[rec] = any(f["kind"] == "full_text" for f in p["files"])
        status[rec] = json.loads((ROOT / "retrieval" / rec / "result.json").read_text())["status"]
    queue = json.loads((ROOT / "coding" / "inputs" / "queue.json").read_text())["queue"]
    study = {r["row_id"]: r for r in queue}

    def entries_of(rid):
        a = accepted.get(rid)
        if a and a["accepted"] and "count_evidence" in a["code"]:
            return a["code"]["count_evidence"]
        out = []
        for m in answers:
            for e in (answers[m].get(rid) or {}).get("count_evidence", []):
                if e not in out:
                    out.append(e)
        return out

    def no_decisive(rid):
        a = accepted.get(rid)
        return not (a and a["accepted"] and a["code"]["identified_releases"])

    # Count-inferred.
    matches = {rid: sv.count_matches(entries_of(rid), study[rid]["side"], rows, counts_by_pair)
               for rid in study if no_decisive(rid)}
    count_only = {"mentions_with_no_decisive_rule": len(matches)}
    for mode in ("strict", "compatible"):
        picked = {rid: {m["dictionary_row"] + "|" + m["endpoint_code"] for m in ms if m[mode]}
                  for rid, ms in matches.items()}
        count_only[mode] = {"equal_to_exactly_one_release": sum(len(v) == 1
                                                               for v in picked.values()),
                            "equal_to_several": sum(len(v) > 1 for v in picked.values())}
    count_only["mentions_with_any_count_match"] = sum(bool(v) for v in matches.values())

    def augmented(extra: dict) -> dict:
        out = dict(accepted)
        for rid, release in extra.items():
            old = accepted.get(rid)
            state = (old["code"]["attribution_state"] if old and old["accepted"] else "unresolved")
            out[rid] = {"accepted": True, "code": {
                "identified_releases": [release], "roles": [{"release": release,
                                                             "role": "primary"}],
                "attribution_state": state, "unresolved_reasons": []}}
        return out

    resolved_by = {mode: {rid: r for rid, ms in matches.items()
                          if (r := sv.count_inferred(ms, mode))} for mode in ("strict",
                                                                               "compatible")}
    # Size flags (Amendment 5).
    flags = {}
    for rid in study:
        if not no_decisive(rid):
            continue
        a = accepted.get(rid)
        ent = entries_of(rid)
        passages = [e.get("quote", "") for e in ent]
        if a and a["accepted"] and a["code"].get("attribution_passage"):
            passages.append(a["code"]["attribution_passage"]["quote"])
        names = [study[rid]["name_as_written"]] + [e.get("resource") or "" for e in ent]
        flags[rid] = sv.size_flag("\n".join(passages), names, study[rid]["side"], definitions)
    size_extra = {rid: f["row"] for rid, f in flags.items() if f["flag"] == "size_match"
                  and rid not in resolved_by["compatible"]
                  and "conflicting_identifiers" not in ((accepted.get(rid) or {}).get("code") or {})
                  .get("unresolved_reasons", [])}
    rejected = {rid for rid in size_extra if marks.get(rid, {}).get("size_belongs") == "no"}
    confirmed = {rid for rid in size_extra if marks.get(rid, {}).get("size_belongs") == "yes"}
    unseen = {rid for rid in size_extra if rid not in marks}

    variants = {
        "count_inferred_strict": augmented(resolved_by["strict"]),
        "count_inferred_compatible": augmented(resolved_by["compatible"]),
        "count_inferred_exact_total_permitted": augmented(resolved_by["compatible"]),
        "size_inferred_script_based": augmented(resolved_by["compatible"] | size_extra),
        "size_inferred_with_author_attribution_corrections": augmented(
            resolved_by["compatible"] | {r: v for r, v in size_extra.items()
                                         if r not in rejected})}
    sens = {}
    for name, acc in variants.items():
        claims, st = es.claims_with_codes(coded, plain, written, acc)
        t = es.tables_rep(br.build(claims, rows), meta, components)
        sens[name] = {"h2_verdict": t["h2_verdict"], "h2b_verdict": t["h2b_verdict"],
                      "estimates": {k: v for k, v in t["estimates"].items()
                                    if k.startswith(("h2", "h1"))}, "claims_stats": st}
    labels = collections.Counter()
    for rid in study:
        a = accepted.get(rid)
        if a and a["accepted"] and "conflicting_identifiers" in a["code"]["unresolved_reasons"]:
            labels["conflicting identifiers"] += 1
        elif not no_decisive(rid):
            labels["explicitly identified"] += 1
        elif rid in size_extra:
            labels["size-inferred candidate"] += 1
        else:
            labels["not explicitly identified under the registered rules"] += 1
            f = flags.get(rid, {}).get("flag")
            if f in ("size_ambiguous", "size_conflict"):
                labels[f"  of which {f}"] += 1
    sensitivity = {
        "count_only_candidate_mappings": count_only,
        "rows_resolved_by_counts": {m: len(v) for m, v in resolved_by.items()},
        "exact_total_sample_size_note": "the coders record no total sample size (coding prompt "
                                        "v3: 'decides nothing; not recorded as evidence'), so "
                                        "this analysis equals the compatible one",
        "size_flags": dict(collections.Counter(f["flag"] or "none" for f in flags.values())),
        "size_inferred_candidates": len(size_extra),
        "size_candidates_by_verification": {"attribution_confirmed_by_the_author": len(confirmed),
                                            "attribution_rejected": len(rejected),
                                            "script_only_unseen_by_the_author": len(unseen),
                                            "seen_without_the_question_answered": len(size_extra)
                                            - len(confirmed) - len(rejected) - len(unseen)},
        "amendment5_labels": dict(labels),
        "author_inferred_releases_recorded": sum(1 for m in marks.values() if m.get("inferred")),
        "variants": sens,
        "unchanged_by_construction": {"all_count_only_mappings_unresolved": "primary",
                                      "without_meta_analysis_canonicalization": "primary"}}

    # Primary registry and classes for the secondary analyses.
    claims, _ = es.claims_with_codes(coded, plain, written, accepted)
    registry = br.build(claims, rows)
    multi = {p: f for p, f in registry.items() if len(f) >= 2}
    classes = es.pair_classes(registry, meta, components)
    paper1 = br.build(coded, rows)
    out = {}
    # SA1, as registered after item 4: A and C and the A-to-C contrast (B void).
    a_cls = {p: (br.pair_h2(f), br.pair_overlap(f)) for p, f in paper1.items() if len(f) >= 2}
    row_change = collections.Counter()
    for rid, r in study.items():
        a_state = es.mention_state(r["name_as_written"] if r["name_as_written"] != q.SHOWN_NOT_STATED
                                   else q.NOT_STATED, r["side"], rows)
        row_change[f"{'resolved' if a_state == 'unique' else 'unresolved'} -> "
                   f"{'resolved' if es.resolved(accepted.get(rid)) else 'unresolved'}"] += 1
    out["sa1"] = {"B": "void (made under the first registration; second registration item 4)",
                  "A_to_C_pair_classes": es.movement(a_cls, classes),
                  "A_to_C_rows": dict(sorted(row_change.items())),
                  "note": "A: Paper 1's registered result; C: this registration's stage A"}
    out["sa2"] = sv.sa2(registry)
    # SA3.
    cats = {}
    for rid, r in study.items():
        a = accepted.get(rid)
        rec = r["record_id"]
        if es.resolved(a):
            continue
        s = set(a["code"]["unresolved_reasons"]) if a and a["accepted"] else {"not_accepted"}
        if not has_full[rec] and no_decisive(rid):
            s.add("source_unreadable" if status.get(rec) == "source_unreadable" else "no_source")
        cats[rid] = s
    row_level = collections.Counter(c for s in cats.values() for c in s)
    fam_records = collections.defaultdict(lambda: collections.defaultdict(set))
    for c in claims:
        fam_records[(c.protein_id, c.outcome_id)][c.family_id].add(c.claim_record_id)
    pair_rows = collections.defaultdict(set)
    for c in coded:
        pair = (c.protein_id, c.outcome_id)
        if pair in multi:
            for side, field in (("pqtl", "pqtl_datasets"), ("outcome", "outcome_datasets")):
                for name in plain[c.claim_record_id][field]:
                    pair_rows[pair].add(es.row_key(c.claim_record_id, side, name,
                                                   written[c.claim_record_id]))
    sa3 = {"rows": dict(sorted(row_level.items())), "unresolved_rows": len(cats)}
    for hyp, idx, fallback in (("h2", 0, "attribution_unresolved"),
                               ("h2b", 1, "composition_incomplete_or_icelandic")):
        blocking = {}
        for p in multi:
            if classes[p][idx] != "unresolved":
                continue
            rs = [r for r in pair_rows[p] if r in cats]
            if any(not fp.attribution_clear for fp in multi[p].values()):
                rs = rs + ["attribution_unresolved"]
            blocking[p] = rs or [fallback]
        sa3[hyp] = sv.sa3_pairs(blocking, cats)
    out["sa3"] = sa3
    # SA4.
    patterns = json.loads(open(f"{E3}/reference/c1_scanner_patterns_v2.json").read())
    with open(f"{E3}/reference/accession_releases.csv", newline="") as fh:
        table = list(csv.DictReader(fh))
    mapper = scanner.Mapper(patterns, table, list(csv.DictReader(open(f"{E2}/dataset_dictionary.csv"))))
    inv, several = collections.Counter(), 0
    for rid, r in study.items():
        a = accepted.get(rid)
        if not es.resolved(a):
            continue
        types = set()
        for e in a["code"]["decisive_evidence"]:
            if e["rule"] == "D2_reference_entry":
                continue
            loc = "abstract" if kinds_of_file[r["record_id"]].get(e["file_id"]) == "abstract" \
                else "main_text"
            for t in sv.sa4_types(e["quote"], patterns, mapper, e["rule"]):
                inv[f"{t}|{loc}"] += 1
                types.add(t)
        several += len(types) > 1
    out["sa4"] = {"resolved_rows": sum(es.resolved(accepted.get(r)) for r in study),
                  "passages_by_type_and_location": dict(sorted(inv.items())),
                  "rows_with_several_agreeing_types": several, "supplement": 0}
    # SA5.
    rec_cls, fam_cls = {}, collections.defaultdict(list)
    for c in claims:
        pair = (c.protein_id, c.outcome_id)
        if pair not in multi:
            continue
        from_pq = [sv.map_name(n, "pqtl", rows) for n in c.pqtl_datasets]
        from_oc = [sv.map_name(n, "outcome", rows) for n in c.outcome_datasets]
        cls = sv.record_overlap(from_pq, from_oc, c.dataset_attribution != "unclear")
        rec_cls[c.claim_record_id] = cls
        fam_cls[(c.family_id, pair)].append(cls)
    fam = {k: sv.family_class(v) for k, v in fam_cls.items()}
    out["sa5"] = {"claim_records": dict(collections.Counter(rec_cls.values())),
                  "families_on_pairs": dict(collections.Counter(fam.values())),
                  "repeated_pairs_with_a_family_in_class": {
                      k: len({p for (f, p), v in fam.items() if v == k})
                      for k in set(fam.values())}}
    # SA6, by the family's first-public year (B void).
    families = json.loads(open(f"{E2}/{REG}/families.json").read())["families"]
    year_of = {}
    for fid, recs in families.items():
        ys = sorted((dates.get(r) or {}).get("value", "")[:4] for r in recs if dates.get(r))
        for r in recs:
            year_of[r] = ys[0] if ys else "unknown"
    by_year = collections.defaultdict(lambda: [0, 0])
    papers = collections.defaultdict(list)
    for rid, r in study.items():
        y = year_of.get(r["record_id"], "unknown")
        by_year[y][0] += es.resolved(accepted.get(rid))
        by_year[y][1] += 1
        papers[r["record_id"]].append(es.resolved(accepted.get(rid)))
    pap_year = collections.defaultdict(lambda: [0, 0])
    for rec, v in papers.items():
        y = year_of.get(rec, "unknown")
        pap_year[y][0] += all(v)
        pap_year[y][1] += 1
    out["sa6"] = {y: {"rows": n, "rows_identified": k, "share": round(k / n, 4),
                      "wilson95": wilson(k, n), "papers": pap_year[y][1],
                      "papers_all_rows_identified": pap_year[y][0],
                      "papers_share": round(pap_year[y][0] / pap_year[y][1], 4),
                      "papers_wilson95": wilson(*pap_year[y])}
                  for y, (k, n) in sorted(by_year.items()) if y in
                  ("2019", "2020", "2021", "2022", "2023", "2024", "2025")}
    out["sa6"]["abstract_alone_B"] = "void"
    out["sa6"]["outside_window"] = {y: v for y, v in by_year.items()
                                    if y not in out["sa6"]}
    # SA7, every eligible retrieved source (full texts and supplements).
    hosts = json.loads(open(f"{E3}/reference/repository_link_hosts.json").read())
    links, no_src = {}, 0
    for rec in sorted(scope_packets):
        result = json.loads((ROOT / "retrieval" / rec / "result.json").read_text())
        if not any(s.get("text") for s in result["sources"]):
            no_src += 1
            continue
        units = c1.units(rec, result["sources"])
        links[rec] = scanner.links(units, hosts).get(rec, {"any_link": False,
                                                           "availability_section_link": False,
                                                           "hosts": []})
    sa7 = collections.defaultdict(collections.Counter)
    for rec, l in links.items():
        y = year_of.get(rec, "unknown")
        sa7[y]["papers"] += 1
        sa7[y]["any_link"] += l["any_link"]
        sa7[y]["availability_section_link"] += l["availability_section_link"]
        for h in l["hosts"]:
            sa7[y][f"host:{h}"] += 1
    out["sa7"] = {"papers_with_an_eligible_source": len(links),
                  "papers_with_no_eligible_source": no_src,
                  "by_year": {y: dict(v) for y, v in sorted(sa7.items())},
                  "any_link": sum(l["any_link"] for l in links.values()),
                  "availability_section_link": sum(l["availability_section_link"]
                                                   for l in links.values())}
    # SA8, levels (Amendment 6 item 1).
    lev, lev_attr = {}, collections.Counter()
    for rid, r in study.items():
        a = accepted.get(rid)
        res_names = [e.get("resource") or "" for e in entries_of(rid)]
        lev[rid] = sv.level(a["code"] if a else None, bool(a and a["accepted"]),
                            r["name_as_written"], r["side"], res_names, rows,
                            lambda: es.resolved(a))
        if a and a["accepted"] and "attribution_unresolved" in a["code"]["unresolved_reasons"]:
            lev_attr[lev[rid]] += 1
    pairs_by_level = collections.Counter()
    for p in multi:
        for L in {lev[r] for r in pair_rows[p] if r in lev}:
            pairs_by_level[L] += 1
    out["sa8"] = {"rows_by_level": dict(collections.Counter(lev.values())),
                  "attribution_unresolved_by_level": dict(lev_attr),
                  "repeated_pairs_holding_a_row_at_level": dict(pairs_by_level)}
    out["sa9"] = "not run: the recovery pass needs agent or model requests; none were made"
    return {"sensitivity": sensitivity, "secondary": out,
            "inputs_sha256": {
                "volume:04_release_resolution_v2/coding/accepted/stage_a.json":
                    hashlib.sha256((FOLDER / "accepted" / "stage_a.json").read_bytes()).hexdigest()}}


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-3000:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def run(sensitivity: str, secondary: str) -> None:
    raw = MARKS.read_bytes()
    if hashlib.sha256(raw).hexdigest() != MARKS_SHA256:
        raise SystemExit("the marks file is not the logged one")
    marks = {m["row_id"]: {"size_belongs": m.get("size_belongs"), "inferred": m.get("inferred")}
             for m in json.loads(raw)["marks"]}
    meta_rows = sorted({r["meta_analysis_row"] for r in csv.DictReader(
        (LOCAL / META).read_text().splitlines())})
    dates = json.loads((PAPER1 / f"{REG}/record_dates.json").read_text())
    result = run_job.remote(meta_rows, marks, dates)
    inputs = result.pop("inputs_sha256") | {
        "marks_sha256": MARKS_SHA256,
        "../03_release_resolution/reference/release_counts.csv": hashlib.sha256(
            (LOCAL.parent / "03_release_resolution/reference/release_counts.csv").read_bytes())
        .hexdigest()}
    write_once(sensitivity, {"script": "scripts/secondary_v1.py", "inputs_sha256": inputs,
                             **result["sensitivity"]})
    write_once(secondary, {"script": "scripts/secondary_v1.py", "inputs_sha256": inputs,
                           **result["secondary"]})
    print("written", sensitivity, secondary)
