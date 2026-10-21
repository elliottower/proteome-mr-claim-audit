# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""One file holding every registered result of the second release-resolution registration's
stage A with its registered criterion (PREREG.md §Inference criteria, and the first
registration's as carried over), read only from the committed outputs named in INPUTS; nothing
is computed anew but the verdicts' restatement. No model is called.

Usage, from experiments/04_release_resolution_v2:
    uv run --no-project python scripts/results_summary_v1.py
"""

import hashlib
import json
import pathlib

OUT = pathlib.Path("outputs/stage_a_results_summary_2026-10-21.json")
INPUTS = {"control_set": "outputs/control_set_2026-10-20.json",
          "validity": "outputs/control_validity_2026-10-20.json",
          "h5": "outputs/manifest_mapping_check_v2_2026-10-20.json",
          "calibration": "outputs/stage_a_calibration_2026-10-21.json",
          "accepted": "outputs/stage_a_accepted_codes_2026-10-21.json",
          "c1": "outputs/stage_a_c1_2026-10-21.json",
          "stage_b": "outputs/stage_b_decision_2026-10-21.json",
          "estimates": "outputs/stage_a_estimates_2026-10-21.json",
          "indices": "outputs/stage_a_indices_2026-10-21.json",
          "sensitivity": "outputs/stage_a_sensitivity_counts_sizes_2026-10-21.json",
          "secondary": "outputs/stage_a_secondary_2026-10-21.json"}


def bounds(e: dict) -> dict:
    keys = ("h2_multi_family_pairs", "h2_known_identical", "h2_known_not_identical",
            "h2_unresolved", "h2_lower", "h2_upper", "h2b_known_overlapping",
            "h2b_known_not_overlapping", "h2b_unresolved", "h2b_lower", "h2b_upper")
    return {k: e[k] for k in keys if k in e}


def main() -> None:
    if OUT.exists():
        raise FileExistsError(f"{OUT} exists; it is written once")
    d = {k: json.loads(pathlib.Path(p).read_text()) for k, p in INPUTS.items()}
    prim = d["estimates"]["variants"]["primary"]
    e = prim["estimates"]
    c1 = d["c1"]
    summary = {
        "registration": "experiments/04_release_resolution_v2/PREREG.md (sha256 555ec9a9ddb628e55fd3642a0282a9b5b75702646968092f98dfd8b74c4ba62c)",
        "primary_analysis": d["stage_b"]["decision"]["primary_analysis"],
        "hypotheses": {
            "H1 [H2-R] more than half of the 245 repeated pairs known_identical": {
                "criterion": "supported when LB > 0.5; contradicted when UB <= 0.5; else unresolved",
                "LB": e["h2_lower"], "UB": e["h2_upper"],
                "counts": {k: e[k] for k in ("h2_known_identical", "h2_known_not_identical",
                                             "h2_unresolved")},
                "verdict": prim["h2_verdict"]},
            "H2 [H2b-R] more than half known_overlapping": {
                "criterion": "supported when LB_b > 0.5; contradicted when UB_b <= 0.5; else unresolved",
                "LB_b": e["h2b_lower"], "UB_b": e["h2b_upper"],
                "counts": {k: e[k] for k in ("h2b_known_overlapping", "h2b_known_not_overlapping",
                                             "h2b_unresolved")},
                "verdict": prim["h2b_verdict"]},
            "H3 [H1-R] concordance of independent edges": {
                "criterion": "no verdict; estimate with Wilson interval; not estimable with no "
                             "independent edge",
                "pairs_with_an_independent_edge": e["h1_pairs"],
                "estimate": e["h1_pair_concordance"],
                "verdict": "not estimable" if not e["h1_pairs"] else "estimate only"},
            "H4 [C1] positive control": {
                "criterion": "recovery >= 0.90 and contradiction <= 0.02 on >= 50 drawn controls, "
                             "accepted codes",
                "controls": c1["overall"]["controls"], "recovered": c1["overall"]["recovered"],
                "recovery": c1["overall"]["recovery"],
                "contradiction": c1["overall"]["contradiction"],
                "by_identifier_type": {k: {"recovered": v["recovered"], "controls": v["controls"]}
                                       for k, v in c1["by_identifier_type"].items()},
                "verdict": c1["verdict"]},
            "H5 [manifest check]": {
                "criterion": "31 of 31 manifest accessions return the expected row",
                "pass": d["h5"]["pass"], "accessions": d["h5"]["accessions"],
                "verdict": "holds" if d["h5"]["h5_holds"] else "fails"}},
        "gates": {"eligible_controls": d["control_set"]["eligible"],
                  "minimum_50_met": d["control_set"]["eligible_at_least_50"],
                  "drawn_controls": d["control_set"]["drawn"],
                  "calibration": {t: v["verdict"] for t, v in d["calibration"]["tasks"].items()},
                  "escalation_triggered": d["calibration"]["escalation"]["triggered"],
                  "accepted_rows": d["accepted"]["counts"]["accepted_by_source"],
                  "stage_b": d["stage_b"]["decision"]},
        "sensitivity": {**{k: bounds(v["estimates"]) | {"h2_verdict": v["h2_verdict"],
                                                         "h2b_verdict": v["h2b_verdict"]}
                           for k, v in d["estimates"]["variants"].items() if k != "primary"},
                        "originally_registered_corpus": bounds(
                            d["estimates"]["originally_registered_corpus"]["estimates"])
                        | {"h2_verdict": d["estimates"]["originally_registered_corpus"]["h2_verdict"],
                           "h2b_verdict": d["estimates"]["originally_registered_corpus"]["h2b_verdict"]},
                        **{k: bounds(v["estimates"]) | {"h2_verdict": v["h2_verdict"],
                                                         "h2b_verdict": v["h2b_verdict"]}
                           for k, v in d["sensitivity"]["variants"].items()},
                        "equal_to_primary_by_construction": d["sensitivity"]["unchanged_by_construction"]},
        "indices": {k: d["indices"][k] for k in (
            "full_text_resolution_yield", "incremental_yield_by_source",
            "abstract_to_full_text_transitions", "attribution_transitions",
            "accessibility_stratified_resolution", "pairs_unresolved_for_want_of_a_source",
            "agreement_with_paper1_codes", "pair_movement", "fully_accessible_pairs",
            "canonicalization")},
        "count_and_size": {k: d["sensitivity"][k] for k in (
            "count_only_candidate_mappings", "size_inferred_candidates",
            "size_candidates_by_verification", "amendment5_labels")},
        "secondary": {"SA1": d["secondary"]["sa1"], "SA2": d["secondary"]["sa2"],
                      "SA3": d["secondary"]["sa3"], "SA4": d["secondary"]["sa4"],
                      "SA5": d["secondary"]["sa5"], "SA6": d["secondary"]["sa6"],
                      "SA7": {k: v for k, v in d["secondary"]["sa7"].items() if k != "by_year"},
                      "SA8": d["secondary"]["sa8"], "SA9": d["secondary"]["sa9"]},
        "inputs_sha256": {p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
                          for p in INPUTS.values()}}
    OUT.write_text(json.dumps(summary, indent=1) + "\n")
    print(f"{OUT} sha256 {hashlib.sha256(OUT.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
