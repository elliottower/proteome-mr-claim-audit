# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Apply the registered eligibility rule to Sol's eligibility answers.

Criteria (1) genetic instruments for circulating protein levels, (2) at least one stated result of
the protein analysis on an outcome and (3) a proteome-wide or panel-wide screen are each `yes`,
`no` or `uncertain`. Ineligible when any criterion is `no`, an exclusion category applies, or the
applicable protein count is below 100. Otherwise `uncertain` when any criterion is `uncertain` (goes
to extraction, flagged, removed in a sensitivity analysis); otherwise eligible, with
`eligible_count_not_stated` when no tested count is stated. The 100 floor applies to
`n_proteins_tested` (proteins stated as tested in the MR analysis) when it is stated; when it is
not, the floor applies to `count_other` (proteins measured, with pQTLs or instrumented, not stated
as tested): below 100 is ineligible, 100 or more is `eligible_count_not_stated`. With neither
stated, `eligible_count_not_stated`. Papers with `also_tissue_or_csf` are flagged
for a sensitivity analysis, never excluded. A record whose eligibility call failed is
`extraction_failed`, never ineligible.

Usage: uv run scripts/apply_eligibility.py --eligibility outputs/parsed/sol_eligibility_<label>_<rev>.jsonl
"""

import argparse
import json
import pathlib

MIN_PROTEINS = 100


CRITERIA = {
    "genetic_instruments_for_circulating_proteins": "no_circulating_protein_instruments",
    "states_protein_outcome_result": "no_protein_outcome_result",
    "proteome_or_panel_wide_screen": "not_proteome_or_panel_wide",
}


def decide(o: dict) -> tuple[str, list[str], list[str]]:
    reasons = [code for field, code in CRITERIA.items() if o[field] == "no"]
    floor_count = o["n_proteins_tested"] if o["n_proteins_tested"] is not None else o.get("count_other")
    if floor_count is not None and floor_count < MIN_PROTEINS:
        reasons.append("fewer_than_100_proteins")
    reasons += [f"excluded_{e}" for e in o["exclusion"]]
    flags = [f"uncertain_{field}" for field in CRITERIA if o[field] == "uncertain"]
    if o["also_tissue_or_csf"]:
        flags.append("also_tissue_or_csf")
    if reasons:
        return "ineligible", reasons, flags
    if any(f.startswith("uncertain_") for f in flags):
        return "uncertain", [], flags
    return ("eligible_count_not_stated" if o["n_proteins_tested"] is None else "eligible"), [], flags


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eligibility", type=pathlib.Path, required=True)
    a = ap.parse_args()
    out = a.eligibility.with_name(a.eligibility.stem + ".decisions.jsonl")
    if out.exists():
        raise FileExistsError(f"{out} exists; archive it before rerunning")
    counts: dict[str, int] = {}
    with out.open("w") as f:
        for row in map(json.loads, a.eligibility.read_text().splitlines()):
            if row["status"] != "ok":
                decision, reasons, flags = "extraction_failed", [], []
            else:
                decision, reasons, flags = decide(row["output"])
            counts[decision] = counts.get(decision, 0) + 1
            o = row["output"] or {}
            f.write(json.dumps({"pmid": row["pmid"], "decision": decision,
                                "reasons": reasons, "flags": flags,
                                "n_proteins_tested": o.get("n_proteins_tested"),
                                "count_other": o.get("count_other")}) + "\n")
    print(out, counts)


if __name__ == "__main__":
    main()
