# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""The row queue of the release-resolution follow-up (PREREG.md, §Study design, Scope and Unit;
frozen, https://osf.io/2s479). No model is called and no source is read.

Scope. Every claim record of Paper 1's amended primary analysis
(`outputs/registry/2026-10-03_amended_primary_coded_a/registry_claims.jsonl`) whose canonical
pair is a repeated pair (a pair two or more families report, `build_registry.build`), and every
dataset side of each such claim. Paper 1's accepted manual codes are not inherited: the names
are read from the same assembly made without them (`registry_claims_without_manual_coding.jsonl`,
the same claim records), as the abstract wrote them.

Unit. One row per record, side and name as written. On a side where the abstract names no
dataset (`not_stated`), one row per record and side (pQTL), or per record, side and outcome as
written (outcome); the outcome as written is the claim's `outcome_as_written` in Paper 1's
verification records. Every outcome-side row carries the outcomes as written of the claims it
covers.

Candidates. For a named row, the dictionary rows `dataset_relations.map_name` gives for the name
on its side, without the `unlisted release of` and `unlisted combination` entries, which are not
dictionary rows; for a `not_stated` row, every dictionary row of the side.

Row identifiers are the first 12 hex digits of the sha256 of `record|side|name|outcome`, so a
control row added later is not told from a study row by its identifier.

Usage: uv run scripts/coding_queue.py --coded <registry_claims.jsonl> \\
           --plain <registry_claims_without_manual_coding.jsonl> --checks <claim_checks.jsonl> [...] \\
           --out <json>
"""

import argparse
import collections
import csv
import datetime
import hashlib
import json
import pathlib

from build_registry import RegistryClaim, build
from dataset_relations import DICTIONARY, load_rows, map_name

NOT_STATED = "not_stated"
SHOWN_NOT_STATED = "not stated"


class QueueError(Exception):
    """A claim record lacks its plain names or its outcome as written, or the output exists."""


def row_id(record: str, side: str, name: str, outcome: str) -> str:
    return hashlib.sha256(f"{record}|{side}|{name}|{outcome}".encode()).hexdigest()[:12]


def side_rows(dictionary: pathlib.Path = DICTIONARY) -> dict[str, list[str]]:
    with dictionary.open(newline="") as f:
        out: dict[str, list[str]] = collections.defaultdict(list)
        for r in csv.DictReader(f):
            out[r["side"]].append(r["name"])
    return {k: sorted(v) for k, v in out.items()}


def queue(coded: list[RegistryClaim], plain: dict[str, dict], outcome_written: dict[str, str],
          dictionary: pathlib.Path = DICTIONARY) -> list[dict]:
    rows = load_rows()
    names_of_side = side_rows(dictionary)
    real = {r.name for r in rows}
    registry = build(coded, rows)
    repeated = {p for p, fams in registry.items() if len(fams) > 1}
    found: dict[tuple, dict] = {}
    for c in coded:
        if (c.protein_id, c.outcome_id) not in repeated:
            continue
        cid = c.claim_record_id
        if cid not in plain or cid not in outcome_written:
            raise QueueError(f"{cid}: no plain names or no outcome as written")
        record = cid.rsplit(":", 1)[0]
        written = outcome_written[cid]
        for side, field in (("pqtl", "pqtl_datasets"), ("outcome", "outcome_datasets")):
            for name in plain[cid][field]:
                stated = name.strip() != NOT_STATED
                outcome = "" if stated or side == "pqtl" else written
                key = (record, side, name if stated else NOT_STATED, outcome)
                if key not in found:
                    if stated:
                        cands = [x for x in map_name(name, side, rows).candidates if x in real]
                    else:
                        cands = names_of_side[side]
                    found[key] = {"row_id": row_id(*key), "record_id": record, "side": side,
                                  "name_as_written": name if stated else SHOWN_NOT_STATED,
                                  "outcomes_as_written": [], "candidates": cands,
                                  "claim_record_ids": [], "family_id": c.family_id,
                                  "kind": "study"}
                row = found[key]
                if side == "outcome" and written not in row["outcomes_as_written"]:
                    row["outcomes_as_written"].append(written)
                if cid not in row["claim_record_ids"]:
                    row["claim_record_ids"].append(cid)
    return [found[k] for k in sorted(found)]


def read_jsonl(paths: list[pathlib.Path]) -> list[dict]:
    return [json.loads(l) for p in paths for l in p.read_text().splitlines() if l.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coded", type=pathlib.Path, required=True)
    ap.add_argument("--plain", type=pathlib.Path, required=True)
    ap.add_argument("--checks", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise QueueError(f"{a.out} exists; it is written once")
    coded = [RegistryClaim.model_validate_json(l) for l in a.coded.read_text().splitlines()
             if l.strip()]
    plain = {r["claim_record_id"]: r for r in read_jsonl([a.plain])}
    written: dict[str, str] = {}
    for r in read_jsonl(a.checks):
        if "claim_record_id" in r:
            written.setdefault(r["claim_record_id"], r["outcome_as_written"])
    rows = queue(coded, plain, written)
    files = [a.coded, a.plain, *a.checks, DICTIONARY]
    out = {"written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
           "inputs_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
           "rows": len(rows),
           "rows_by_side": dict(sorted(collections.Counter(r["side"] for r in rows).items())),
           "rows_not_stated_by_side": dict(sorted(collections.Counter(
               r["side"] for r in rows if r["name_as_written"] == SHOWN_NOT_STATED).items())),
           "records": len({r["record_id"] for r in rows}),
           "claim_records": len({c for r in rows for c in r["claim_record_ids"]}),
           "queue": rows}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "queue"}, indent=1))


if __name__ == "__main__":
    main()
