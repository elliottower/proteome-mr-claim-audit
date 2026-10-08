# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Compare the manual-coding queue rebuilt for the amended primary analysis with the queue that
was coded (PREREG.md, Amendment 2). Every row of the coded queue must be in the rebuilt queue
unchanged; rows only in the rebuilt queue are new rows to code. It prints counts only and exits
non-zero when an assertion fails.

A row is one record, side and name as written. Its hash covers the record, the side, the name
as written, the family, the mapping state and the candidate rows of the queue file, and, where
the passage folders are given, the status and the passages the generator wrote for the row
(every sentence, its place in the document, the terms it matched and its reference entries).
`claim_records`, the number of claim records that carry the name, is not in the hash: a record
that enters the analysis can raise it for a row that is otherwise the same. Rows whose count
changed are counted.

Assertions:
    every_coded_row_present     no row of the coded queue is missing from the rebuilt queue
    every_coded_row_unchanged   each has the same hash in both
    no_duplicate_rows           neither queue holds a row twice

Written to --out: the assertions, the hashes of the input files, counts, and the new rows (record,
side, name as written, mapping state, whether the paper already had a row).

Usage: uv run scripts/queue_rebuild_comparison.py --coded <manual_coding_queue.csv> \\
           --rebuilt <manual_coding_queue.csv> [--coded-passages <dir> --rebuilt-passages <dir>] \\
           --out <json>
"""

import argparse
import collections
import csv
import hashlib
import json
import pathlib

FIELDS = ("record_id", "side", "name_as_written", "family_id", "mapping_state", "candidates")
Key = tuple[str, str, str]


def sha(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
                          ).hexdigest()


def read_queue(path: pathlib.Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def read_passages(folder: pathlib.Path) -> dict[Key, list]:
    """row -> [status, passages], from every paper file of a passage folder."""
    out: dict[Key, list] = {}
    for path in sorted(folder.glob("*.json")):
        made = json.loads(path.read_text())
        if "rows" not in made:
            continue
        for row in made["rows"]:
            out[(made["record_id"], row["side"], row["name_as_written"])] = [
                row["status"], row["passages"]]
    return out


def row_hashes(rows: list[dict], passages: dict[Key, list] | None) -> dict[Key, str]:
    out = {}
    for r in rows:
        key = (r["record_id"], r["side"], r["name_as_written"])
        if key in out:
            raise ValueError("a queue holds a row twice")
        held = [r[f] for f in FIELDS]
        if passages is not None:
            held.append(passages[key])
        out[key] = sha(held)
    return out


def compare(coded: list[dict], rebuilt: list[dict], coded_passages: dict[Key, list] | None,
            rebuilt_passages: dict[Key, list] | None) -> dict:
    old, new = row_hashes(coded, coded_passages), row_hashes(rebuilt, rebuilt_passages)
    counts = {(r["record_id"], r["side"], r["name_as_written"]): r["claim_records"]
              for r in coded}
    missing = sorted(k for k in old if k not in new)
    changed = sorted(k for k in old if k in new and old[k] != new[k])
    papers = {k[0] for k in old}
    added = [r for r in rebuilt
             if (r["record_id"], r["side"], r["name_as_written"]) not in old]
    return {
        "coded_rows": len(old), "rebuilt_rows": len(new),
        "passages_in_the_hash": coded_passages is not None,
        "every_coded_row_present": not missing, "every_coded_row_unchanged": not changed,
        "no_duplicate_rows": True,
        "coded_rows_missing": [list(k) for k in missing],
        "coded_rows_changed": [list(k) for k in changed],
        "coded_rows_whose_claim_record_count_changed": sum(
            counts[(r["record_id"], r["side"], r["name_as_written"])] != r["claim_records"]
            for r in rebuilt if (r["record_id"], r["side"], r["name_as_written"]) in old),
        "new_rows": len(added),
        "new_rows_by_side": dict(collections.Counter(r["side"] for r in added)),
        "new_rows_by_state": dict(collections.Counter(r["mapping_state"] for r in added)),
        "new_rows_papers": len({r["record_id"] for r in added}),
        "new_rows_papers_already_in_the_coded_queue": len(
            {r["record_id"] for r in added} & papers),
        "new_rows_list": [{"record_id": r["record_id"], "side": r["side"],
                           "name_as_written": r["name_as_written"],
                           "mapping_state": r["mapping_state"],
                           "paper_already_in_the_coded_queue": r["record_id"] in papers}
                          for r in added],
        "holds": not missing and not changed}


def main() -> None:
    ap = argparse.ArgumentParser()
    for name in ("coded", "rebuilt", "out"):
        ap.add_argument(f"--{name}", type=pathlib.Path, required=True)
    ap.add_argument("--coded-passages", type=pathlib.Path)
    ap.add_argument("--rebuilt-passages", type=pathlib.Path)
    a = ap.parse_args()
    if a.out.exists():
        raise FileExistsError(f"{a.out} exists; a comparison is written once")
    if (a.coded_passages is None) != (a.rebuilt_passages is None):
        raise ValueError("give both passage folders or neither")
    made = compare(read_queue(a.coded), read_queue(a.rebuilt),
                   read_passages(a.coded_passages) if a.coded_passages else None,
                   read_passages(a.rebuilt_passages) if a.rebuilt_passages else None)
    made = {"coded": {"path": str(a.coded),
                      "sha256": hashlib.sha256(a.coded.read_bytes()).hexdigest()},
            "rebuilt": {"path": str(a.rebuilt),
                        "sha256": hashlib.sha256(a.rebuilt.read_bytes()).hexdigest()},
            "coded_passages": str(a.coded_passages), "rebuilt_passages": str(a.rebuilt_passages),
            **made}
    a.out.write_text(json.dumps(made, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in made.items()
                      if k not in ("new_rows_list", "coded_rows_missing", "coded_rows_changed")},
                     indent=1))
    if not made["holds"]:
        raise SystemExit("a coded queue row is missing or changed: stop")


if __name__ == "__main__":
    main()
