# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""The manual dataset codes for a rebuilt queue (PREREG.md, Amendment 2): the rows coded in the
first run, carried unchanged, and the rows the rebuilt queue adds, coded by the same checks.

`new-rows` writes the third check into the table of the new rows. Input: their extended table
after the second check (scripts/manual_coding_table_v6.py), the author's table of their coded
rows (scripts/manual_coding_check3_table_v2.py) and the author's marks on the page made from
it, `{"marks": [{"table_line", "author_mark", "author_note"}, ...]}`. The marks file must hold
exactly the lines of the table. The rule is the one fixed for the author's marks: `yes` makes
the row `author_confirmed` (context `new_queue_row_marked_on_its_own_page`); `no` makes it
unresolved (`author_did_not_confirm`), the note kept; `unsure` or an empty mark leaves it
`machine_gate_only`. A row on which the two checks differ and that has no resolution stops the
step: such a row goes to a reread first. A row that stands unresolved gets the status
`unresolved`.

`merge` writes the extended table of a rebuilt queue: for each row of the queue, in the
queue's order, the row of the first run's record or of the new rows' table. A queue row found
in neither, or in both, stops the step; a row of the first run's record that the queue does
not hold stops it too; rows of the new rows' table outside the queue are left out and counted.
Beside the table it writes a record with the sha256 of the inputs, the counts by status and
unresolved reason, and `first_run_rows_carried_unchanged`: that every row of the first run's
record stands in the new table with every field as it was.

Usage:
    uv run scripts/manual_coding_final_tables.py new-rows --codes <extended csv, second check> \\
        --table <author table csv> --marked <marks.json> --out <extended csv, third check>
    uv run scripts/manual_coding_final_tables.py merge --first <extended csv of the first run> \\
        --new <extended csv of the new rows, third check> --queue <manual_coding_queue.csv> \\
        --out <extended csv>
"""

import argparse
import collections
import csv
import hashlib
import json
import pathlib

from manual_coding_check3_sample import apply as third_check
from manual_coding_check3_table_v2 import FIELDS as TABLE_FIELDS
from manual_coding_table_v7 import EXTENDED_FIELDS, read_extended
from manual_dataset_coding import write_csv

CONTEXT = "new_queue_row_marked_on_its_own_page"
MARKS = ("yes", "no", "unsure", "")
Key = tuple[str, str, str]


class FinalTableError(Exception):
    """A mark or a row is not where it should be, or an output exists."""


def key(row: dict) -> Key:
    return row["record_id"], row["side"], row["name_as_written"]


def read_marks(path: pathlib.Path, lines: list[dict]) -> dict[int, tuple[str, str]]:
    """table line -> (mark, note); the lines are exactly those of the author's table."""
    out = {}
    for item in json.loads(path.read_text())["marks"]:
        line = int(item["table_line"])
        mark = str(item.get("author_mark") or "").strip().casefold()
        if line in out or mark not in MARKS:
            raise FinalTableError(f"{path.name}: line {line} is repeated, or its mark is none "
                                  "of yes, no, unsure, empty")
        out[line] = (mark, " ".join(str(item.get("author_note") or "").split()))
    if sorted(out) != sorted(int(x["line"]) for x in lines):
        raise FinalTableError(f"{path.name}: its lines are not the lines of the author's table")
    return out


def new_rows(table: list[dict], lines: list[dict], marks: dict[int, tuple[str, str]]
             ) -> list[dict]:
    """The new rows' table with the third check written in."""
    for r in table:
        if r["claude_code_value"] != r["perplexity_value"] and not r["resolved_value"]:
            raise FinalTableError(f"{key(r)}: the two checks differ and no reread has resolved it")
    decided = {k: v for k, v in marks.items() if v[0] in ("yes", "no")}
    made = third_check(table, lines, decided, {"audit": "passed", "lines_marked_no": []})
    return [{**r, "third_check_context": CONTEXT if r["author_confirms"] in ("yes", "no")
             else ""} for r in made]


def merge(first: list[dict], new: list[dict], queue: list[dict]) -> tuple[list[dict], dict]:
    """(the rows of the queue in its order, counts)."""
    old, added = {key(r): r for r in first}, {key(r): r for r in new}
    if len(old) != len(first) or len(added) != len(new) or set(old) & set(added):
        raise FinalTableError("a row stands twice, or in both tables")
    wanted = [key(q) for q in queue]
    if len(set(wanted)) != len(wanted):
        raise FinalTableError("the queue holds a row twice")
    missing = [k for k in wanted if k not in old and k not in added]
    dropped = [k for k in old if k not in set(wanted)]
    if missing or dropped:
        raise FinalTableError(f"{len(missing)} queue rows without a coded row; {len(dropped)} "
                              "rows of the first run not in the queue")
    out = [old.get(k) or added[k] for k in wanted]
    counts = {"rows": len(out), "rows_of_the_first_run": len(old),
              "new_rows_in_the_queue": sum(k in added for k in wanted),
              "new_rows_outside_the_queue": sum(k not in set(wanted) for k in added),
              "first_run_rows_carried_unchanged": all(r == old[key(r)] for r in out
                                                      if key(r) in old),
              "by_status": dict(collections.Counter(r["status"] for r in out)),
              "unresolved_by_reason": dict(collections.Counter(
                  r["unresolved_reason"] or "none_recorded"
                  for r in out if r["status"] != "coded")),
              "by_third_check": dict(collections.Counter(
                  r["third_check"] or "not_applicable" for r in out))}
    return out, counts


def read_csv(path: pathlib.Path, fields: list[str] | None = None) -> list[dict]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if fields is not None and reader.fieldnames != fields:
            raise FinalTableError(f"{path.name}: columns must be {fields}")
        return list(reader)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    n = sub.add_parser("new-rows")
    for name in ("codes", "table", "marked", "out"):
        n.add_argument(f"--{name}", type=pathlib.Path, required=True)
    m = sub.add_parser("merge")
    for name in ("first", "new", "queue", "out"):
        m.add_argument(f"--{name}", type=pathlib.Path, required=True)
    a = ap.parse_args()
    record_file = a.out.with_suffix(f".{a.command.replace('-', '_')}.json")
    if a.out.exists() or record_file.exists():
        raise FinalTableError(f"{a.out} or its record exists; it is written once")
    if a.command == "new-rows":
        lines = read_csv(a.table, TABLE_FIELDS)
        marks = read_marks(a.marked, lines)
        made = new_rows(read_extended(a.codes), lines, marks)
        record = {"inputs_sha256": {str(p): sha256(p) for p in (a.codes, a.table, a.marked)},
                  "marks": dict(collections.Counter(v[0] or "empty" for v in marks.values())),
                  "by_status": dict(collections.Counter(r["status"] for r in made)),
                  "by_third_check": dict(collections.Counter(
                      r["third_check"] or "not_applicable" for r in made))}
    else:
        made, record = merge(read_extended(a.first), read_extended(a.new), read_csv(a.queue))
        record = {"inputs_sha256": {str(p): sha256(p) for p in (a.first, a.new, a.queue)},
                  **record}
        if not record["first_run_rows_carried_unchanged"]:
            raise FinalTableError("a row of the first run would change")
    write_csv(a.out, EXTENDED_FIELDS, made)
    record["table_sha256"] = sha256(a.out)
    record_file.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(record, indent=1))


if __name__ == "__main__":
    main()
