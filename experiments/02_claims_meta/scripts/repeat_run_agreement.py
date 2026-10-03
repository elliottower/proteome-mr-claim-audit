# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.13.5"]
# ///
"""Repeat-run stability: field-level agreement between the registered extraction (run 1) and the
second run of the same prompt on the 10% stability sample (scripts/sample_repeat_run.py). No
model is called. The first run stays the registered extraction; nothing here changes a record.

Abstracts. An abstract is compared when both runs returned schema-valid output for it; an
abstract with `extraction_failed` in either run is counted and not compared.

Pairing, within one abstract, in two passes:

    pass 1   records pair on the folded `protein_as_written`, the folded `outcome_as_written`
             and the context key (`analysis_context_as_written | subgroup_as_written`, lower
             case, whitespace collapsed: the registry's context key)
    pass 2   records left unpaired pair on the folded protein and outcome alone

Folding is the verifier's (`verify_claims.compact`: Greek letters spelled out, accents removed,
lower case, non-alphanumeric characters removed). Within a pass, the records of each run that
share a key are taken in their order in the output and the k-th of run 1 pairs with the k-th of
run 2; the surplus stays unpaired. No record pairs twice.

Reported: abstracts compared and not compared; abstracts whose two runs return the same number
of records; the share of each run's records with a partner, by pass; and, among paired records,
exact agreement per field. List fields (`pqtl_datasets`, `outcome_datasets`, `platform`) agree
when the two sets are equal; `evidence_span` agrees when equal after whitespace is collapsed;
every other field agrees when the two values are equal. Pass-1 pairs share a context key, so
their `analysis_context_as_written` and `subgroup_as_written` can differ only in case and
spacing.

Usage: uv run scripts/repeat_run_agreement.py --run1 <sol_extraction_<label>_<rev>.jsonl>
           --run2 <sol_extraction_<repeat label>_<rev>.jsonl>
           --sample <...repeat_sample.json> --out <dir>
"""

import argparse
import collections
import datetime
import hashlib
import json
import pathlib

from pydantic import BaseModel

from verify_claims import compact

SET_FIELDS = ("pqtl_datasets", "outcome_datasets", "platform")
FIELDS = ("protein_as_written", "outcome_as_written", "direction", "evidence_type",
          "claim_scope", "analysis_context_as_written", "subgroup_as_written", "pqtl_datasets",
          "outcome_datasets", "dataset_attribution", "platform", "ancestry",
          "relation_ambiguous", "evidence_span")


class AgreementError(Exception):
    """The two runs do not cover the sample, or used different prompts."""


class Pairing(BaseModel):
    pairs: list[tuple[int, int, int]]
    unpaired_run1: list[int]
    unpaired_run2: list[int]


def context_key(c: dict) -> str:
    return " ".join(f"{c['analysis_context_as_written']} | {c['subgroup_as_written']}"
                    .lower().split())


def full_key(c: dict) -> tuple[str, str, str]:
    return compact(c["protein_as_written"]), compact(c["outcome_as_written"]), context_key(c)


def pair_key(c: dict) -> tuple[str, str]:
    return compact(c["protein_as_written"]), compact(c["outcome_as_written"])


def pair_records(run1: list[dict], run2: list[dict]) -> Pairing:
    """(index in run 1, index in run 2, pass) for every pair, and the unpaired indices."""
    pairs: list[tuple[int, int, int]] = []
    left1, left2 = list(range(len(run1))), list(range(len(run2)))
    for number, key in ((1, full_key), (2, pair_key)):
        by_key: dict[tuple, list[int]] = collections.defaultdict(list)
        for j in left2:
            by_key[key(run2[j])].append(j)
        still1 = []
        for i in left1:
            partners = by_key[key(run1[i])]
            if partners:
                pairs.append((i, partners.pop(0), number))
            else:
                still1.append(i)
        used = {j for _, j, _ in pairs}
        left1, left2 = still1, [j for j in left2 if j not in used]
    return Pairing(pairs=sorted(pairs), unpaired_run1=left1, unpaired_run2=left2)


def agrees(field: str, a: dict, b: dict) -> bool:
    if field in SET_FIELDS:
        return set(a[field]) == set(b[field])
    if field == "evidence_span":
        return " ".join(a[field].split()) == " ".join(b[field].split())
    return a[field] == b[field]


def agreement(run1: dict[str, dict], run2: dict[str, dict], sampled: list[str]) -> dict:
    """`run1` and `run2` map record id to its extraction row (run_extraction.py)."""
    missing = [i for i in sampled if i not in run1 or i not in run2]
    if missing:
        raise AgreementError(f"sampled records missing from a run: {missing[:5]}")
    revisions = {run1[i]["revision"] for i in sampled} | {run2[i]["revision"] for i in sampled}
    if len(revisions) != 1:
        raise AgreementError(f"the two runs used different prompt revisions: {sorted(revisions)}")
    compared = [i for i in sampled if run1[i]["status"] == "ok" and run2[i]["status"] == "ok"]
    n1 = n2 = same_count = 0
    by_pass: collections.Counter = collections.Counter()
    agree: collections.Counter = collections.Counter()
    per_abstract = []
    for rid in compared:
        a, b = run1[rid]["output"]["claims"], run2[rid]["output"]["claims"]
        pairing = pair_records(a, b)
        n1, n2 = n1 + len(a), n2 + len(b)
        same_count += len(a) == len(b)
        for i, j, number in pairing.pairs:
            by_pass[number] += 1
            for f in FIELDS:
                agree[f] += agrees(f, a[i], b[j])
        per_abstract.append({"record_id": rid, "run1_records": len(a), "run2_records": len(b),
                             "pairs": len(pairing.pairs),
                             "unpaired_run1": len(pairing.unpaired_run1),
                             "unpaired_run2": len(pairing.unpaired_run2)})
    paired = sum(by_pass.values())
    return {
        "revision": next(iter(revisions)),
        "sampled_abstracts": len(sampled),
        "abstracts_compared": len(compared),
        "abstracts_extraction_failed_in_run1": sum(run1[i]["status"] != "ok" for i in sampled),
        "abstracts_extraction_failed_in_run2": sum(run2[i]["status"] != "ok" for i in sampled),
        "abstracts_with_equal_record_count": same_count,
        "run1_records": n1, "run2_records": n2,
        "paired_records": paired,
        "paired_by_pass": {"full_key": by_pass[1], "protein_and_outcome_only": by_pass[2]},
        "run1_share_paired": paired / n1 if n1 else None,
        "run2_share_paired": paired / n2 if n2 else None,
        "field_agreement_among_paired": {
            f: {"agree": agree[f], "share": agree[f] / paired if paired else None}
            for f in FIELDS},
        "per_abstract": per_abstract,
    }


def read_rows(path: pathlib.Path) -> dict[str, dict]:
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    out = {r["pmid"]: r for r in rows}
    if len(out) != len(rows):
        raise AgreementError(f"{path}: a record id occurs twice")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run1", type=pathlib.Path, required=True)
    ap.add_argument("--run2", type=pathlib.Path, required=True)
    ap.add_argument("--sample", type=pathlib.Path, required=True,
                    help="the .repeat_sample.json written by sample_repeat_run.py")
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    sample = json.loads(a.sample.read_text())
    result = {
        "run1": str(a.run1), "run1_sha256": hashlib.sha256(a.run1.read_bytes()).hexdigest(),
        "run2": str(a.run2), "run2_sha256": hashlib.sha256(a.run2.read_bytes()).hexdigest(),
        "sample": str(a.sample), "seed": sample["seed"], "fraction": sample["fraction"],
        "n_eligible": sample["n_eligible"],
        "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        **agreement(read_rows(a.run1), read_rows(a.run2), sample["sampled_ids"])}
    a.out.mkdir(parents=True, exist_ok=True)
    target = a.out / "repeat_run_agreement.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; archive it before rerunning")
    target.write_text(json.dumps(result, indent=1))
    print(json.dumps({k: v for k, v in result.items() if k != "per_abstract"}, indent=1))


if __name__ == "__main__":
    main()
