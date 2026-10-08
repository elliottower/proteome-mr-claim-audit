# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "openpyxl==3.1.5", "pydantic==2.13.5"]
# ///
"""The author's second look at coded rows that rest on a reference entry (PREREG.md log,
2026-10-08). The page of the second look holds rows the author had already marked and rows he
had not; some of its rows are flagged by mechanical rules as harder. This script reads his
marks on that page: a JSON file `{"marks": [{"table_line", "author_mark", "author_note"}, ...]}`
whose lines must be exactly the `table_lines` of the page's manifest.

For a row the author had not marked, the rule fixed for voluntary marks holds: `yes` makes the
row `author_confirmed`; `no` makes it unresolved (`author_did_not_confirm`) with the note kept;
`unsure` or an empty mark leaves it `machine_gate_only`. Its context is
`second_look_page_flagged_row` or `second_look_page_unflagged_row`, with the ending
`_discussed_with_coordinating_session` for the lines given with `--discussed`.

For a row the author had already marked as confirmed, a `yes` changes no value of the table:
the first mark and its context stay, and the second mark is written to the record beside the
table. An empty mark does nothing. A `no` or an `unsure` for such a row blocks the step: no
rule has been fixed for a second mark that departs from the first.

The record (`<out>.second_look.json`) holds, for each line marked yes on the page: the table
line, whether it is flagged, whether it was discussed, whether the mark is a first or a second
mark, and the context the row had before; and the counts of the flagged rows by what marks
they now have.

Usage:
    uv run scripts/manual_coding_check3_second_look.py --table <check3_author_table.csv> \\
        --codes <extended csv> --marked <marks.json> --page <manifest with table_lines> \\
        --flagged <json with table_lines> [--discussed <json with table_lines>] --out <new csv>
"""

import argparse
import collections
import hashlib
import json
import pathlib

from manual_coding_check3_followup_v2 import MARKS, NOT_CONFIRMED, FollowupError, row_ids, row_lines
from manual_coding_check3_sample import read_table
from manual_coding_table_v6 import EXTENDED_FIELDS, read_extended
from manual_dataset_coding import write_csv

FLAGGED = "second_look_page_flagged_row"
UNFLAGGED = "second_look_page_unflagged_row"
TALKED = "_discussed_with_coordinating_session"


def read_marks(path: pathlib.Path, page: list[int]) -> dict[int, tuple[str, str]]:
    """table line -> (mark, note); the lines are exactly the lines of the page."""
    out = {}
    for item in json.loads(path.read_text())["marks"]:
        line = int(item["table_line"])
        mark = str(item.get("author_mark") or "").strip().casefold()
        if line in out or mark not in MARKS:
            raise FollowupError(f"{path.name}: line {line} is repeated, or its mark is none "
                                "of yes, no, unsure, empty")
        out[line] = (mark, " ".join(str(item.get("author_note") or "").split()))
    if sorted(out) != sorted(page) or len(set(page)) != len(page):
        raise FollowupError(f"{path.name}: its lines are not the lines of the page")
    return out


def apply_second_look(table: list[dict], lines: list[dict], marks: dict[int, tuple[str, str]],
                      flagged: frozenset[int], discussed: frozenset[int] = frozenset()
                      ) -> tuple[list[dict], dict]:
    """The table with the first marks of the page written in, and the record of the page."""
    said_yes = {k for k, (m, _) in marks.items() if m == "yes"}
    if not flagged <= set(marks) or not discussed <= said_yes:
        raise FollowupError("a flagged line is not on the page, or a discussed line is not "
                            "marked yes")
    line_of, out, seen, yes = row_lines(lines), [], set(), []
    for row_id, r in row_ids(table):
        line = line_of.get(row_id, -1)
        mark, note = marks.get(line, ("", ""))
        new = dict(r)
        if line in marks:
            seen.add(line)
        if mark and r["third_check"] not in ("machine_gate_only", "author_confirmed"):
            raise FollowupError(f"{row_id}: a mark for a row that is not a coded row")
        if mark in ("no", "unsure") and r["third_check"] == "author_confirmed":
            raise FollowupError(f"{row_id}: a second mark that departs from the first; no "
                                "rule has been fixed for it")
        context = (FLAGGED if line in flagged else UNFLAGGED) + (
            TALKED if line in discussed else "")
        if mark == "yes":
            first = r["third_check"] == "machine_gate_only"
            yes.append({"table_line": line, "flagged": line in flagged,
                        "discussed_with_coordinating_session": line in discussed,
                        "mark": "first" if first else "second",
                        "context_before": r["third_check_context"]})
            if first:
                new |= {"third_check": "author_confirmed", "author_confirms": "yes",
                        "third_check_context": context}
                if note:
                    new["resolution_note"] = f"{r['resolution_note']} [author: {note}]".strip()
        elif mark == "no":
            new |= {"third_check": NOT_CONFIRMED, "author_confirms": "no",
                    "status": "unresolved", "unresolved_reason": NOT_CONFIRMED,
                    "third_check_context": context,
                    "resolution_note": (f"{r['resolution_note']} [author did not confirm"
                                        f"{': ' + note if note else ''}]").strip()}
        out.append(new)
    if seen != set(marks):
        raise FollowupError("a line of the page has no row in the table")
    state = {line_of[i]: r["third_check"] for i, r in row_ids(out) if i in line_of}
    twice = {y["table_line"] for y in yes if y["mark"] == "second"}
    record = {
        "marks": dict(collections.Counter(m or "empty" for m, _ in marks.values())),
        "yes_first_mark": sum(y["mark"] == "first" for y in yes),
        "yes_second_mark": len(twice),
        "yes_discussed": sum(y["discussed_with_coordinating_session"] for y in yes),
        "flagged_rows": len(flagged),
        "flagged_marked_yes_on_this_page": len(flagged & said_yes),
        "flagged_marked_once_only_elsewhere": sum(
            state[k] == "author_confirmed" for k in flagged - said_yes),
        "flagged_unmarked": sum(state[k] == "machine_gate_only" for k in flagged),
        "lines_marked_yes": sorted(yes, key=lambda y: y["table_line"])}
    return out, record


def main() -> None:
    ap = argparse.ArgumentParser()
    for name in ("table", "codes", "marked", "page", "flagged", "out"):
        ap.add_argument(f"--{name}", type=pathlib.Path, required=True)
    ap.add_argument("--discussed", type=pathlib.Path)
    a = ap.parse_args()

    def table_lines(path: pathlib.Path) -> list[int]:
        return [int(x) for x in json.loads(path.read_text())["table_lines"]]

    lines = read_table(a.table)
    marks = read_marks(a.marked, table_lines(a.page))
    made, record = apply_second_look(
        read_extended(a.codes), lines, marks, frozenset(table_lines(a.flagged)),
        frozenset(table_lines(a.discussed)) if a.discussed else frozenset())
    target = a.out.with_suffix(".second_look.json")
    if a.out.exists() or target.exists():
        raise FileExistsError(f"{a.out} or its record exists; archive it before rerunning")
    write_csv(a.out, EXTENDED_FIELDS, made)
    record = {
        "marked_file_sha256": hashlib.sha256(a.marked.read_bytes()).hexdigest(),
        "third_check": dict(collections.Counter(r["third_check"] or "not_applicable"
                                                for r in made)),
        "third_check_context": dict(collections.Counter(
            r["third_check_context"] or "none" for r in made)),
        "status": dict(collections.Counter(r["status"] for r in made)), **record}
    target.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({k: v for k, v in record.items() if k != "lines_marked_yes"}, indent=1))


if __name__ == "__main__":
    main()
