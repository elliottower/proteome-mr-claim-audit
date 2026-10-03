# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Select the records that go to extraction: those whose eligibility decision
(apply_eligibility.py) is `eligible`, `eligible_count_not_stated` or `uncertain`. No model is
called.

Written next to the decisions file:

    <decisions stem>.eligible_abstracts.jsonl   pmid (the record id), title, abstract: the input
                                                of run_extraction.py --task extraction
    <decisions stem>.eligible_records.jsonl     the screening records of the same ids: the seeds
                                                of citation_chase.py

A record with decision `ineligible` or `extraction_failed` is in neither file. An eligible record
missing from the screening set or the screening records raises.

A citation-chasing round passes several decisions files: those of its screening queue and those
of its gate-audit batches (scripts/gate_audit.py), so a sampled record judged eligible goes to
extraction and seeds the next round like any other. The outputs are written next to the first
file. A record with two decisions raises. A record classed `no_abstract`
(scripts/abstract_floor.py) is never judged, so a decision on one raises.

Usage: uv run scripts/select_eligible.py --decisions <...decisions.jsonl> [<...> ...]
           --screening-set <screening_set.jsonl> --screening-records <screening_records.jsonl>
"""

import argparse
import json
import pathlib

ELIGIBLE = ("eligible", "eligible_count_not_stated", "uncertain")


class SelectError(Exception):
    """An eligible record has no screening record, or an output exists."""


def select(decisions: list[dict], abstracts: list[dict], records: list[dict]
           ) -> tuple[list[dict], list[dict]]:
    """(abstract records, screening records) of the eligible ids, in record-id order."""
    decided = [d["pmid"] for d in decisions]
    if len(set(decided)) != len(decided):
        raise SelectError("a record has two eligibility decisions")
    ids = sorted({d["pmid"] for d in decisions if d["decision"] in ELIGIBLE})
    by_abstract = {r["pmid"]: r for r in abstracts}
    by_record = {r["record_id"]: r for r in records}
    judged_without = sorted(i for i in decided if by_record.get(i, {}).get("no_abstract"))
    if judged_without:
        raise SelectError(f"records classed no_abstract have an eligibility decision: "
                          f"{judged_without[:5]}")
    missing = [i for i in ids if i not in by_abstract or i not in by_record]
    if missing:
        raise SelectError(f"eligible records without a screening record: {missing[:5]}")
    return [by_abstract[i] for i in ids], [by_record[i] for i in ids]


def read_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--decisions", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--screening-set", type=pathlib.Path, required=True)
    ap.add_argument("--screening-records", type=pathlib.Path, required=True)
    a = ap.parse_args()
    stem = a.decisions[0].name.removesuffix(".jsonl")
    out_abstracts = a.decisions[0].with_name(stem + ".eligible_abstracts.jsonl")
    out_records = a.decisions[0].with_name(stem + ".eligible_records.jsonl")
    if out_abstracts.exists() or out_records.exists():
        raise SelectError(f"{out_abstracts} or {out_records} exists; archive it before rerunning")
    abstracts, records = select([d for p in a.decisions for d in read_jsonl(p)],
                                read_jsonl(a.screening_set), read_jsonl(a.screening_records))
    out_abstracts.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in abstracts))
    out_records.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
    print(json.dumps({"eligible_records": len(abstracts), "abstracts": str(out_abstracts),
                      "records": str(out_records)}))


if __name__ == "__main__":
    main()
