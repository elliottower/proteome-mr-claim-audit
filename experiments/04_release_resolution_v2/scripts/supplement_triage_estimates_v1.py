# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5", "modal==1.4.3"]
# ///
"""Unregistered: the H1 [H2-R] and H2 [H2b-R] pair classes and the SA8 levels of the second
registration's stage A, recomputed with the supplement triage's resolutions
(outputs/supplement_triage_decisions_2026-10-22.json) laid over stage A's accepted codes. No
model is called. Every class, bound and level is computed by the registered functions, unchanged:
estimands_v1.claims_with_codes, build_registry.build, estimands_v1.estimates_rep and
secondary_v1.level. This module only reads the inputs locally and overlays the decisions, as
modal_secondary_v4's `augmented` overlays count-inferred releases: a resolved row's code becomes
its decided releases with their roles, its attribution state `explicit`, and no unresolved
reason.

Layers. `stage_a`: the accepted codes as they are (reproduces the registered 0 / 23 / 222 and
8 / 11 / 226, which checks the local inputs). `rules`: rows whose decision rests on evidence the
stage A rules count as decisive (D1 through the frozen tables or a release number; D2 through the
dictionary). `practical`: adds rows resolved by evidence outside those tables (OpenGWAS metadata,
file-naming conventions, exact counts or sizes), each with a pinned quotation.

Inputs read locally: the accepted codes, queue, coder answers and packet manifest copied from the
volume into outputs/raw/volume_copy_2026-10-22/ (sha256 checked against the values the stage A
outputs record), Paper 1's registry and claim checks, the dictionary.

    PYTHONPATH=scripts:../03_release_resolution/scripts:../02_claims_meta/scripts \\
        uv run python scripts/supplement_triage_estimates_v1.py \\
        --out outputs/supplement_triage_estimates_2026-10-22.json
"""

import argparse
import collections
import csv
import hashlib
import json
import pathlib

import build_registry as br
import estimands_v1 as es
import secondary_v1 as sv
from build_registry import RegistryClaim
from dataset_relations import load_rows
from modal_coding_v2 import CHECKS, REG

HERE = pathlib.Path(__file__).resolve().parent
E4 = HERE.parent
E3 = E4.parent / "03_release_resolution"
E2 = E4.parent / "02_claims_meta"
VOL = E4 / "outputs" / "raw" / "volume_copy_2026-10-22"
ACCEPTED = VOL / "accepted_stage_a.json"
QUEUE = VOL / "queue.json"
ANSWERS = VOL / "answers" / "stage_a"
DECISIONS = E4 / "outputs" / "supplement_triage_decisions_2026-10-22.json"
META = E3 / "reference" / "meta_analysis_expansions_omitted_v2.csv"
STAGE_A = {"estimates": E4 / "outputs" / "stage_a_estimates_2026-10-21.json",
           "secondary": E4 / "outputs" / "stage_a_secondary_2026-10-21.json"}
EXPECTED_SHA256 = {ACCEPTED: "b64373bf8fdb0627db69ab02822aa431dc68e17b753a08ea4c2509685e89ab62"}
LAYERS = ("rules", "practical")
KEYS = ("h2_multi_family_pairs", "h2_known_identical", "h2_known_not_identical", "h2_unresolved",
        "h2_lower", "h2_upper", "h2b_known_overlapping", "h2b_known_not_overlapping",
        "h2b_unresolved", "h2b_lower", "h2b_upper", "representation_unresolved_pairs",
        "h1_pairs")


class TriageEstimateError(Exception):
    """An input differs from the one stage A used, or the output exists."""


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def written_of() -> dict[str, str]:
    out = {}
    for c in CHECKS:
        for r in jsonl(E2 / c):
            if "claim_record_id" in r:
                out.setdefault(r["claim_record_id"], r["outcome_as_written"])
    return out


def answers_of(model: str) -> dict:
    out = {}
    for path in sorted((ANSWERS / model).glob("*.json")):
        if ".attempt" in path.name:
            continue
        f = json.loads(path.read_text())
        if f["state"] == "accepted":
            for row in f["answer"]["rows"]:
                out[row["row_id"]] = row
    return out


def overlay(accepted: dict, decisions: list[dict], layers: tuple[str, ...]) -> tuple[dict, list]:
    out, used = dict(accepted), []
    for d in decisions:
        if d["decision"] != "resolved" or d["layer"] not in layers:
            continue
        out[d["row_id"]] = {"accepted": True, "code": {
            "identified_releases": [r["release"] for r in d["releases"]],
            "roles": [{"release": r["release"], "role": r["role"]} for r in d["releases"]],
            "attribution_state": "explicit", "unresolved_reasons": [],
            "decisive_evidence": [{"release": r["release"]} for r in d["releases"]]}}
        used.append(d["row_id"])
    return out, used


def levels(accepted: dict, study: dict, rows, answers: dict, pair_rows: dict, multi) -> dict:
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

    lev, attr = {}, collections.Counter()
    for rid, r in study.items():
        a = accepted.get(rid)
        names = [e.get("resource") or "" for e in entries_of(rid)]
        lev[rid] = sv.level(a["code"] if a else None, bool(a and a["accepted"]),
                            r["name_as_written"], r["side"], names, rows, lambda: es.resolved(a))
        if a and a["accepted"] and "attribution_unresolved" in a["code"]["unresolved_reasons"]:
            attr[lev[rid]] += 1
    pairs = collections.Counter()
    for p in multi:
        for level in {lev[r] for r in pair_rows[p] if r in lev}:
            pairs[level] += 1
    return {"rows_by_level": dict(sorted(collections.Counter(lev.values()).items())),
            "attribution_unresolved_by_level": dict(sorted(attr.items())),
            "repeated_pairs_holding_a_row_at_level": dict(sorted(pairs.items()))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise TriageEstimateError(f"{a.out} exists; it is written once")
    for path, want in EXPECTED_SHA256.items():
        if sha256(path) != want:
            raise TriageEstimateError(f"{path} is not the file stage A used")
    rows = load_rows()
    components = {r.name: r.components for r in rows}
    meta = {r["meta_analysis_row"] for r in csv.DictReader(META.read_text().splitlines())}
    coded = [RegistryClaim.model_validate(r) for r in jsonl(E2 / REG / "registry_claims.jsonl")]
    plain = {r["claim_record_id"]: r
             for r in jsonl(E2 / REG / "registry_claims_without_manual_coding.jsonl")}
    written = written_of()
    accepted = {rid: {"accepted": x["accepted"], "code": x["code"]}
                for rid, x in json.loads(ACCEPTED.read_text()).items()}
    study = {r["row_id"]: r for r in json.loads(QUEUE.read_text())["queue"]}
    answers = {m: answers_of(m) for m in ("claude-sonnet-5-5", "gpt-6.1-sol")}
    decisions = json.loads(DECISIONS.read_text())["rows"]

    results, before = {}, None
    for name, layers in (("stage_a", ()), ("rules", ("rules",)),
                         ("practical", ("rules", "practical"))):
        acc, used = overlay(accepted, decisions, layers)
        claims, stats = es.claims_with_codes(coded, plain, written, acc)
        registry = br.build(claims, rows)
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
            "rows_overlaid": len(used),
            "estimates": {k: est[k] for k in KEYS},
            "h2_verdict": br.h2_verdict(est), "h2b_verdict": br.h2_verdict(est, "h2b"),
            "claims_stats": stats,
            "sa8": levels(acc, study, rows, answers, pair_rows, multi),
            "pair_movement_from_stage_a": (es.movement(before, classes) if before else None)}
        if name == "stage_a":
            before = classes
    reg = json.loads(STAGE_A["estimates"].read_text())["variants"]["primary"]["estimates"]
    sa8 = json.loads(STAGE_A["secondary"].read_text())["sa8"]
    check = {"estimates_equal_to_registered": all(results["stage_a"]["estimates"][k] == reg[k]
                                                  for k in KEYS if k in reg),
             "sa8_equal_to_registered": results["stage_a"]["sa8"]["rows_by_level"]
             == dict(sorted(sa8["rows_by_level"].items()))}
    files = [ACCEPTED, QUEUE, DECISIONS, META, STAGE_A["estimates"], STAGE_A["secondary"],
             E2 / REG / "registry_claims.jsonl",
             E2 / REG / "registry_claims_without_manual_coding.jsonl",
             E2 / "dataset_dictionary.csv", E2 / "verification" / "dataset_components.csv",
             HERE / "supplement_triage_estimates_v1.py", HERE / "estimands_v1.py",
             HERE / "secondary_v1.py"] + [E2 / c for c in CHECKS]
    root = E4.parent.parent
    out = {"script": "scripts/supplement_triage_estimates_v1.py",
           "what": "unregistered; the registered estimands recomputed with the supplement "
                   "triage's resolutions laid over stage A's accepted codes; changes no "
                   "registered result",
           "inputs_sha256": {str(f.relative_to(root)): sha256(f) for f in files},
           "answers_files_sha256": hashlib.sha256("".join(
               sha256(p) for p in sorted(ANSWERS.rglob("*.json"))).encode()).hexdigest(),
           "stage_a_reproduced": check,
           "registered_stage_a": {"estimates": {k: reg.get(k) for k in KEYS},
                                  "sa8_rows_by_level": sa8["rows_by_level"],
                                  "sa8_repeated_pairs_holding_a_row_at_level":
                                      sa8["repeated_pairs_holding_a_row_at_level"]},
           "layers": results}
    a.out.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(json.dumps({k: (v["estimates"], v["sa8"]["rows_by_level"])
                      for k, v in results.items()}, indent=1))


if __name__ == "__main__":
    main()
