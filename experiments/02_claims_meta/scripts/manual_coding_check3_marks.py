# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""Read the author's marks of the third check of the manual dataset coding back into the
extended table, and write the reading view of the table the author marks (PREREG.md, §Manual
coding of dataset names, item 5: the author confirms each row against the pinned sentence; a
row is coded only when all three agree).

`view` writes a markdown file with the lines of the author's table (scripts/
manual_coding_check3_table.py) in the same order and with the same content: per line a block
with the coded dictionary row on top, then the pinned sentence, then the reference entry when
there is one, then the basis and the rows. The CSV stays the file that is marked.

`apply` reads the marked CSV. Every line must be marked `yes` or `no` in `author_confirms`
(case and surrounding white space ignored); a line left blank, or marked otherwise, blocks the
step, and nothing is written. The marked file must hold the lines of the unmarked table,
unchanged but for the two author columns. For every row of a line: `author_confirms` of the
extended table is set to the mark; `status` is `coded` for yes. A row marked no is unresolved:
the registered reader takes a row as coded only when the author confirms, so the value does
not stand, and the author's note is kept in `resolution_note` (appended, in brackets) with the
reason `author_did_not_confirm` in `unresolved_reason`. A row not in the table (standing
unresolved after two checks and the reread) gets `author_confirms` `yes` only in the sense the
registered reader needs, that the recorded unresolved value is the one that stands, and the
status `unresolved`. The sha256 of the marked file and the counts are written beside the new
table.

Usage:
    uv run scripts/manual_coding_check3_marks.py view --table <check3_author_table.csv> \\
        --out <check3_author_table.md>
    uv run scripts/manual_coding_check3_marks.py apply --marked <marked csv> \\
        --unmarked <check3_author_table.csv> --codes <extended csv after the reread> \\
        --out <new extended csv>
"""

import argparse
import collections
import csv
import hashlib
import json
import pathlib
import textwrap

from manual_coding_check3_table import FIELDS, UNRESOLVED, standing
from manual_coding_table_v2 import EXTENDED_FIELDS, read_extended
from manual_dataset_coding import NOT_STATED, write_csv

AUTHOR = ("author_confirms", "author_note")
NOT_CONFIRMED = "author_did_not_confirm"


class MarksError(Exception):
    """A line is unmarked, the marked file is not the table, or an output exists."""


def read_table(path: pathlib.Path) -> list[dict]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != FIELDS:
            raise MarksError(f"{path.name}: columns must be {FIELDS}")
        return list(reader)


def view(lines: list[dict]) -> str:
    """The reading view: one block per line, in the table's order."""
    def wrapped(text: str) -> str:
        return "\n".join(textwrap.wrap(text, 96, break_long_words=False,
                                       break_on_hyphens=False)) or "(none)"
    out = ["# Third check of the manual dataset coding: reading view", "",
           "Same lines and order as `check3_author_table.csv`, which is the file to mark "
           "(`author_confirms`: yes or no; `author_note`). The question for each line: does "
           "the pinned sentence, or the table it names, state the coded dataset name, release "
           "or count?", ""]
    for line in lines:
        out += [f"## Line {line['line']}: {line['dictionary_row']}", "",
                f"Side: {line['side']}. Rows: {line['rows']}", "",
                "Pinned sentence:", "", "> " + wrapped(line["pinned_sentence"]).replace(
                    "\n", "\n> "), ""]
        if line["reference_entry"]:
            out += ["Reference entry:", "", "> " + wrapped(line["reference_entry"]).replace(
                "\n", "\n> "), ""]
        out += [f"Basis: {line['identification_basis']}. Identifier the gate found: "
                f"{line['gate_identifier']}. Source read: {line['source_read']}.", ""]
    return "\n".join(out)


def marks(marked: list[dict], unmarked: list[dict]) -> dict[str, tuple[str, str]]:
    """row id -> (yes or no, note). Raises unless every line is marked and nothing else in the
    table changed."""
    def rest(line: dict) -> dict:
        return {k: v for k, v in line.items() if k not in AUTHOR}

    if [rest(x) for x in marked] != [rest(x) for x in unmarked]:
        raise MarksError("the marked file differs from the table outside the author's columns")
    out, blank = {}, []
    for line in marked:
        mark = line["author_confirms"].strip().casefold()
        if mark not in ("yes", "no"):
            blank.append(line["line"])
            continue
        for item in line["rows"].split(" ; "):
            out[item.split(" [", 1)[0]] = (mark, " ".join(line["author_note"].split()))
    if blank:
        raise MarksError(f"{len(blank)} line(s) are not marked yes or no: {blank[:20]}")
    return out


def apply(table: list[dict], row_marks: dict[str, tuple[str, str]]) -> list[dict]:
    """The extended table with the author's check written in."""
    out, used = [], set()
    nth: collections.Counter = collections.Counter()
    for r in table:
        nth[(r["record_id"], r["side"])] += 1
        row_id = f"{r['record_id']}#{r['side']}_{nth[(r['record_id'], r['side'])]}"
        new = dict(r)
        if standing(r) in UNRESOLVED:
            if row_id in row_marks:
                raise MarksError(f"{row_id} is marked and does not stand coded")
            new |= {"author_confirms": "yes", "status": "unresolved"}
        else:
            if row_id not in row_marks:
                raise MarksError(f"{row_id} stands coded and has no mark")
            used.add(row_id)
            mark, note = row_marks[row_id]
            if mark == "yes":
                new |= {"author_confirms": "yes", "status": "coded"}
                if note:
                    new["resolution_note"] = (f"{r['resolution_note']} [author: {note}]"
                                              ).strip()
            else:
                new |= {"author_confirms": "no", "status": "unresolved",
                        "unresolved_reason": NOT_CONFIRMED,
                        "resolution_note": (f"{r['resolution_note']} [author did not confirm"
                                            f"{': ' + note if note else ''}]").strip()}
        out.append(new)
    if used != set(row_marks):
        raise MarksError(f"marks for rows not in the table: {sorted(set(row_marks) - used)[:5]}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    v = sub.add_parser("view")
    v.add_argument("--table", type=pathlib.Path, required=True)
    v.add_argument("--out", type=pathlib.Path, required=True)
    a = sub.add_parser("apply")
    for name in ("marked", "unmarked", "codes", "out"):
        a.add_argument(f"--{name}", type=pathlib.Path, required=True)
    args = ap.parse_args()
    if args.command == "view":
        if args.out.exists():
            raise MarksError(f"{args.out} exists")
        args.out.write_text(view(read_table(args.table)) + "\n")
        print(args.out)
        return
    row_marks = marks(read_table(args.marked), read_table(args.unmarked))
    made = apply(read_extended(args.codes), row_marks)
    write_csv(args.out, EXTENDED_FIELDS, made)
    counts = collections.Counter(m for m, _ in row_marks.values())
    record = {"marked_file": str(args.marked),
              "marked_file_sha256": hashlib.sha256(args.marked.read_bytes()).hexdigest(),
              "rows_marked": len(row_marks), "confirmed": counts["yes"],
              "not_confirmed": counts["no"],
              "status": dict(collections.Counter(r["status"] for r in made))}
    args.out.with_suffix(".marks.json").write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(record, indent=1))


if __name__ == "__main__":
    main()
