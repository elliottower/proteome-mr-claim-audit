# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5", "modal==1.4.3"]
# ///
"""Unregistered: H1 [H2-R], H2 [H2b-R] and SA8 recomputed with the supplement triage decisions
after the author's review (outputs/supplement_triage_decisions_v2_2026-10-23.json), which code
some rows per claim record (rule R2). No model is called. v1 of this script
(supplement_triage_estimates_v1.py) overlays only row-level codes; this version adds the claim
level, and otherwise reuses v1's functions and the registered ones unchanged
(estimands_v1.claims_with_codes, build_registry.build, estimands_v1.estimates_rep,
secondary_v1.level).

Row-level codes (`resolved` rows) are overlaid as in v1. A `split` row is overlaid with no
release, so estimands_v1.claims_with_codes leaves its name as written in every claim, and then,
per claim record of the row (`claim_level`): the name is replaced by the claim's releases with
an entering role (primary, meta-analysis component) and, for each source with no dictionary row,
by a name that maps to no dictionary row (`absent_name`), which Paper 1's comparison treats as
unresolved; a claim left unresolved, or with only non-entering releases, keeps the name, and so
does every claim of a row whose releases are all replication or sensitivity (added rule 4). The
claim's attribution is left as Paper 1's.

SA8 is row-level: a split row counts as L1 when every one of its claim records is resolved with
no absent source; otherwise its stage A code stands. Split rows are counted apart.

Layers as in v1: `stage_a`; `rules` (rows whose decision rests on the stage A rules); `practical`
(adds the practical rows).

    PYTHONPATH=scripts:../03_release_resolution/scripts:../02_claims_meta/scripts \\
        uv run python scripts/supplement_triage_estimates_v2.py \\
        --out outputs/supplement_triage_estimates_v2_2026-10-23.json
"""

import argparse
import collections
import csv
import hashlib
import json
import pathlib

import build_registry as br
import estimands_v1 as es
import supplement_triage_estimates_v1 as v1
from build_registry import RegistryClaim
from dataset_relations import load_rows, map_name
from modal_coding_v2 import CHECKS, REG

HERE = pathlib.Path(__file__).resolve().parent
E4 = HERE.parent
E2 = E4.parent / "02_claims_meta"
ROOT = E4.parent.parent
DECISIONS = E4 / "outputs" / "supplement_triage_decisions_v2_2026-10-23.json"
V1_ESTIMATES = E4 / "outputs" / "supplement_triage_estimates_2026-10-22.json"
ENTERING = ("primary", "meta_analysis_component")


class TriageEstimateV2Error(Exception):
    """An absent-source name maps to a dictionary row, or the output exists."""


def absent_name(label: str) -> str:
    return f"zz source with no dictionary row {label}"


def row_overlay(accepted: dict, rows: list[dict], layers: tuple[str, ...]) -> tuple[dict, dict]:
    """Accepted codes with resolved rows overlaid (v1.overlay) and split rows emptied; and the
    split rows to apply per claim."""
    resolved = [r | {"decision": "resolved"} for r in rows
                if r["decision"] == "resolved" and r["layer"] in layers]
    out, _ = v1.overlay(accepted, resolved, layers)
    split = {r["row_id"]: r for r in rows if r["decision"] == "split" and r["layer"] in layers}
    for rid in split:
        out[rid] = {"accepted": True, "code": {
            "identified_releases": [], "roles": [], "attribution_state": "explicit",
            "unresolved_reasons": [], "decisive_evidence": []}}
    return out, split


def replication_only(row: dict) -> bool:
    """A split row whose every release is replication or sensitivity: none of it enters, absent
    sources included (added rule 4)."""
    roles = [x["role"] for c in row["claims"].values() for x in c["releases"]]
    return bool(roles) and not any(r in ENTERING for r in roles)


def claim_level(claims: list, plain: dict, written: dict, split: dict) -> tuple[list, dict]:
    split = {rid: r for rid, r in split.items() if not replication_only(r)}
    stats = collections.Counter()
    out = []
    for c in claims:
        cid = c.claim_record_id
        update = {}
        for side, field in (("pqtl", "pqtl_datasets"), ("outcome", "outcome_datasets")):
            names = list(getattr(c, field))
            for name in plain[cid][field]:
                rid = es.row_key(cid, side, name, written[cid])
                code = split.get(rid, {}).get("claims", {}).get(cid)
                if not code or code["state"] == "unresolved" or name not in names:
                    continue
                new = [x["release"] for x in code["releases"] if x["role"] in ENTERING]
                new += [absent_name(label) for label in code["absent"]]
                if not new:
                    continue
                i = names.index(name)
                names[i:i + 1] = new
                stats[f"claim_names_replaced|{code['state']}"] += 1
            update[field] = tuple(dict.fromkeys(names))
        out.append(c.model_copy(update=update))
    return out, dict(stats)


def sa8_overlay(accepted: dict, rows: list[dict], layers: tuple[str, ...]) -> dict:
    full = []
    for r in rows:
        if r["layer"] not in layers:
            continue
        if r["decision"] == "resolved":
            full.append(r)
        elif r["decision"] == "split" and r["claims"] and all(
                c["state"] == "resolved" for c in r["claims"].values()):
            rels = {x["release"]: x["role"] for c in r["claims"].values() for x in c["releases"]}
            full.append({"row_id": r["row_id"], "decision": "resolved", "layer": r["layer"],
                         "releases": [{"release": k, "role": v} for k, v in rels.items()]})
    out, _ = v1.overlay(accepted, full, layers)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise TriageEstimateV2Error(f"{a.out} exists; it is written once")
    for path, want in v1.EXPECTED_SHA256.items():
        if v1.sha256(path) != want:
            raise TriageEstimateV2Error(f"{path} is not the file stage A used")
    rows_dict = load_rows()
    for side in ("pqtl", "outcome"):
        if map_name(absent_name("x"), side, rows_dict).candidates:
            raise TriageEstimateV2Error("the absent-source name maps to a dictionary row")
    components = {r.name: r.components for r in rows_dict}
    meta = {r["meta_analysis_row"] for r in csv.DictReader(v1.META.read_text().splitlines())}
    coded = [RegistryClaim.model_validate(r) for r in v1.jsonl(E2 / REG / "registry_claims.jsonl")]
    plain = {r["claim_record_id"]: r
             for r in v1.jsonl(E2 / REG / "registry_claims_without_manual_coding.jsonl")}
    written = v1.written_of()
    accepted = {rid: {"accepted": x["accepted"], "code": x["code"]}
                for rid, x in json.loads(v1.ACCEPTED.read_text()).items()}
    study = {r["row_id"]: r for r in json.loads(v1.QUEUE.read_text())["queue"]}
    answers = {m: v1.answers_of(m) for m in ("claude-sonnet-5-5", "gpt-6.1-sol")}
    rows = json.loads(DECISIONS.read_text())["rows"]

    results, before = {}, None
    for name, layers in (("stage_a", ()), ("rules", ("rules",)),
                         ("practical", ("rules", "practical"))):
        acc, split = row_overlay(accepted, rows, layers)
        claims, stats = es.claims_with_codes(coded, plain, written, acc)
        claims, cstats = claim_level(claims, plain, written, split)
        registry = br.build(claims, rows_dict)
        est = es.estimates_rep(registry, meta, components)
        multi = {p for p, f in registry.items() if len(f) >= 2}
        pair_rows = collections.defaultdict(set)
        for c in coded:
            pair = (c.protein_id, c.outcome_id)
            if pair in multi:
                for side, field in (("pqtl", "pqtl_datasets"), ("outcome", "outcome_datasets")):
                    for nm in plain[c.claim_record_id][field]:
                        pair_rows[pair].add(es.row_key(c.claim_record_id, side, nm,
                                                       written[c.claim_record_id]))
        classes = es.pair_classes(registry, meta, components)
        results[name] = {
            "rows_overlaid": sum(1 for r in rows if r["decision"] == "resolved"
                                 and r["layer"] in layers),
            "split_rows_overlaid_per_claim": len(split),
            "estimates": {k: est[k] for k in v1.KEYS},
            "h2_verdict": br.h2_verdict(est), "h2b_verdict": br.h2_verdict(est, "h2b"),
            "claims_stats": stats | cstats,
            "sa8": v1.levels(sa8_overlay(accepted, rows, layers), study, rows_dict, answers,
                             pair_rows, multi),
            "pair_movement_from_stage_a": es.movement(before, classes) if before else None}
        if name == "stage_a":
            before = classes
    reg = json.loads(v1.STAGE_A["estimates"].read_text())["variants"]["primary"]["estimates"]
    sa8 = json.loads(v1.STAGE_A["secondary"].read_text())["sa8"]
    prior = json.loads(V1_ESTIMATES.read_text())["layers"]
    files = [v1.ACCEPTED, v1.QUEUE, DECISIONS, V1_ESTIMATES, v1.META, v1.STAGE_A["estimates"],
             v1.STAGE_A["secondary"], E2 / REG / "registry_claims.jsonl",
             E2 / REG / "registry_claims_without_manual_coding.jsonl",
             E2 / "dataset_dictionary.csv", E2 / "verification" / "dataset_components.csv",
             HERE / "supplement_triage_estimates_v2.py", HERE / "supplement_triage_estimates_v1.py",
             HERE / "estimands_v1.py", HERE / "secondary_v1.py"] + [E2 / c for c in CHECKS]
    out = {"script": "scripts/supplement_triage_estimates_v2.py",
           "what": "unregistered; the registered estimands recomputed with the supplement "
                   "triage decisions after the author's review, at claim level for split rows; "
                   "changes no registered result",
           "inputs_sha256": {str(f.relative_to(ROOT)): v1.sha256(f) for f in files},
           "answers_files_sha256": hashlib.sha256("".join(
               v1.sha256(p) for p in sorted(v1.ANSWERS.rglob("*.json"))).encode()).hexdigest(),
           "stage_a_reproduced": {
               "estimates_equal_to_registered": all(
                   results["stage_a"]["estimates"][k] == reg[k] for k in v1.KEYS if k in reg),
               "sa8_equal_to_registered": results["stage_a"]["sa8"]["rows_by_level"]
               == dict(sorted(sa8["rows_by_level"].items()))},
           "side_by_side": {k: {
               "h1_identical_not_identical_unresolved": [
                   v["estimates"]["h2_known_identical"], v["estimates"]["h2_known_not_identical"],
                   v["estimates"]["h2_unresolved"]],
               "h2_overlapping_not_overlapping_unresolved": [
                   v["estimates"]["h2b_known_overlapping"],
                   v["estimates"]["h2b_known_not_overlapping"], v["estimates"]["h2b_unresolved"]],
               "before_the_author_review": None if k == "stage_a" else [
                   [prior[k]["estimates"][x] for x in ("h2_known_identical",
                                                       "h2_known_not_identical", "h2_unresolved")],
                   [prior[k]["estimates"][x] for x in ("h2b_known_overlapping",
                                                       "h2b_known_not_overlapping",
                                                       "h2b_unresolved")]]}
               for k, v in results.items()},
           "layers": results}
    a.out.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(json.dumps(out["stage_a_reproduced"]), json.dumps(out["side_by_side"], indent=1))
    print(json.dumps({k: v["sa8"]["rows_by_level"] for k, v in results.items()}, indent=1))


if __name__ == "__main__":
    main()
