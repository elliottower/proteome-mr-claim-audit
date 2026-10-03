# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""Negative-control specificity per stratum. No model is called.

The 50 negative-control records (search/negative_controls.jsonl: 10 from each of five PubMed
queries that make a record ineligible by construction) are judged once, after the freeze, by the
frozen eligibility prompt and rule (run_extraction.py --task eligibility, apply_eligibility.py).
Per stratum and overall:

    no_abstract     control records classed `no_abstract` (scripts/abstract_floor.py): not
                    judged, counted apart, outside the denominator
    judged          records with an eligibility decision (`extraction_failed` records are
                    counted apart and leave the denominator)
    not_eligible    decision `ineligible`
    specificity     not_eligible / judged
    judged eligible decisions `eligible`, `eligible_count_not_stated` and `uncertain`, listed by
                    record with their flags

Wilson 95% intervals are naive descriptive intervals. The figures describe these five record
types only; the set is never used to revise a prompt.

Usage: uv run scripts/negative_control_specificity.py --controls search/negative_controls.jsonl
           --decisions <...decisions.jsonl>
           --no-abstract outputs/negative_controls/negative_control_no_abstract.jsonl --out <dir>
"""

import argparse
import collections
import datetime
import hashlib
import json
import pathlib

from build_registry import wilson

NOT_ELIGIBLE = "ineligible"
FAILED = "extraction_failed"


class ControlError(Exception):
    """The decisions do not cover the control set exactly."""


def specificity(controls: list[dict], decisions: list[dict],
                no_abstract: frozenset[str] = frozenset()) -> dict:
    """`no_abstract`: the control records classed `no_abstract`, which have no decision."""
    stratum = {c["pmid"]: c["stratum"] for c in controls}
    if len(stratum) != len(controls):
        raise ControlError("a control record is listed twice")
    if no_abstract - set(stratum):
        raise ControlError(f"no_abstract records that are not controls: "
                           f"{sorted(no_abstract - set(stratum))[:5]}")
    decided = {d["pmid"]: d for d in decisions}
    expected = set(stratum) - no_abstract
    if len(decided) != len(decisions) or set(decided) != expected:
        raise ControlError("the decisions must hold each control record that has an abstract "
                           f"once and nothing else: missing {sorted(expected - set(decided))[:5]}, "
                           f"extra {sorted(set(decided) - expected)[:5]}")

    def row(all_ids: list[str]) -> dict:
        ids = [i for i in all_ids if i not in no_abstract]
        by = collections.Counter(decided[i]["decision"] for i in ids)
        judged = len(ids) - by[FAILED]
        return {"records": len(all_ids), "no_abstract": len(all_ids) - len(ids),
                "extraction_failed": by[FAILED], "judged": judged,
                "not_eligible": by[NOT_ELIGIBLE],
                "specificity": by[NOT_ELIGIBLE] / judged if judged else None,
                "wilson_descriptive": wilson(by[NOT_ELIGIBLE], judged),
                "decisions": dict(sorted(by.items())),
                "ineligibility_reasons": dict(sorted(collections.Counter(
                    r for i in ids for r in decided[i]["reasons"]).items())),
                "judged_eligible": [{"pmid": i, "decision": decided[i]["decision"],
                                     "flags": decided[i]["flags"]} for i in sorted(ids)
                                    if decided[i]["decision"] not in (NOT_ELIGIBLE, FAILED)]}

    strata: dict[str, list[str]] = collections.defaultdict(list)
    for pmid, s in stratum.items():
        strata[s].append(pmid)
    return {"per_stratum": {s: row(ids) for s, ids in sorted(strata.items())},
            "overall": row(sorted(stratum))}


def read_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--controls", type=pathlib.Path, required=True)
    ap.add_argument("--decisions", type=pathlib.Path, required=True)
    ap.add_argument("--no-abstract", type=pathlib.Path, required=True,
                    help="negative_control_no_abstract.jsonl (fetch_known_item_abstracts.py)")
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    result = {
        "controls": str(a.controls),
        "controls_sha256": hashlib.sha256(a.controls.read_bytes()).hexdigest(),
        "decisions": str(a.decisions),
        "decisions_sha256": hashlib.sha256(a.decisions.read_bytes()).hexdigest(),
        "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "no_abstract": str(a.no_abstract),
        **specificity(read_jsonl(a.controls), read_jsonl(a.decisions),
                      frozenset(r["pmid"] for r in read_jsonl(a.no_abstract)))}
    a.out.mkdir(parents=True, exist_ok=True)
    target = a.out / "negative_control_specificity.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; archive it before rerunning")
    target.write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
