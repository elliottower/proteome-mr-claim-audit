# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""Two additions to the record of the third check of the manual dataset coding (PREREG.md log,
2026-10-08, after the review of the check as carried out). Neither changes a rule or a code
already given.

`context` adds to the extended table the column `third_check_context`: for the rows of the
author's seeded spot-check, whether the author's mark followed a discussion of that row with
the coordinating session (`spot_check_discussed_with_coordinating_session`) or not
(`spot_check_not_discussed`). The discussed rows are given as table lines of the author's
table in a file; they must all be lines of the sample.

`voluntary` reads marks the author gave, after the spot-check had closed, on rows he had not
read: a JSON file `{"marks": [{"table_line", "author_mark", "author_note"}, ...]}`. Fixed
before any such mark existed: `yes` makes the row `author_confirmed`; `no` makes it unresolved
(`author_did_not_confirm`) with the note kept; `unsure` or an empty mark leaves it
`machine_gate_only`. A no is counted and reported and has no consequence beyond its own row.
A line that is not in the author's table, that was in the spot-check, that stands twice, or a
mark that is none of the four, blocks the step. Where the voluntary read is itself a seeded
sample (`--seed`, `--n`: a sample of the lines outside the spot-check, in file order, and with
`--basis` only of those whose identification basis is the one named), the marked lines must be
exactly that sample. Rows marked yes or no take the context
`voluntary_read_after_spot_check`, or `voluntary_read_discussed_with_coordinating_session` for
the lines given with `--discussed`.

Usage:
    uv run scripts/manual_coding_check3_followup.py context --table <check3_author_table.csv> \\
        --codes <extended csv after the third check> --discussed <json with table_lines> \\
        --out <new extended csv>
    uv run scripts/manual_coding_check3_followup.py voluntary --table <check3_author_table.csv> \\
        --codes <extended csv with the context column> --marked <marks.json> \\
        [--seed <seed> --n <n> [--basis <basis>]] [--discussed <json with table_lines>] \\
        --out <new csv>
"""

import argparse
import collections
import csv
import hashlib
import json
import pathlib

from manual_coding_check3_sample import N, SEED, draw, read_table
from manual_coding_table_v3 import EXTENDED_FIELDS as BEFORE
from manual_coding_table_v4 import EXTENDED_FIELDS, read_extended
from manual_dataset_coding import write_csv

DISCUSSED = "spot_check_discussed_with_coordinating_session"
NOT_DISCUSSED = "spot_check_not_discussed"
VOLUNTARY = "voluntary_read_after_spot_check"
VOLUNTARY_DISCUSSED = "voluntary_read_discussed_with_coordinating_session"
NOT_CONFIRMED = "author_did_not_confirm"
MARKS = ("yes", "no", "unsure", "")


class FollowupError(Exception):
    """A line is not where it should be, a mark is unknown, or an output exists."""


def row_lines(lines: list[dict]) -> dict[str, int]:
    return {item.split(" [", 1)[0]: int(x["line"]) for x in lines
            for item in x["rows"].split(" ; ")}


def row_ids(table: list[dict]):
    nth: collections.Counter = collections.Counter()
    for r in table:
        nth[(r["record_id"], r["side"])] += 1
        yield f"{r['record_id']}#{r['side']}_{nth[(r['record_id'], r['side'])]}", r


def add_context(table: list[dict], lines: list[dict], discussed: list[int]) -> list[dict]:
    """The table with `third_check_context` set for the rows of the spot-check."""
    sample = set(draw([int(x["line"]) for x in lines], SEED, N))
    if not set(discussed) <= sample or len(set(discussed)) != len(discussed):
        raise FollowupError("a discussed line is not a line of the sample, or stands twice")
    line_of, out = row_lines(lines), []
    for row_id, r in row_ids(table):
        line = line_of.get(row_id)
        marked = r["author_confirms"] in ("yes", "no")
        if marked != (line in sample):
            raise FollowupError(f"{row_id}: the author's mark and the sample do not agree")
        out.append({**r, "third_check_context": "" if not marked
                    else DISCUSSED if line in discussed else NOT_DISCUSSED})
    return out


def read_voluntary(path: pathlib.Path, lines: list[dict], seed: int | None = None,
                   n: int | None = None, basis: str | None = None
                   ) -> dict[int, tuple[str, str]]:
    """table line -> (mark, note), for lines outside the spot-check; with a seed, exactly the
    seeded sample of those lines."""
    all_lines = [int(x["line"]) for x in lines]
    sample = set(draw(all_lines, SEED, N))
    out = {}
    for item in json.loads(path.read_text())["marks"]:
        line = int(item["table_line"])
        mark = str(item.get("author_mark") or "").strip().casefold()
        if line in out or line not in all_lines or line in sample or mark not in MARKS:
            raise FollowupError(f"{path.name}: line {line} is repeated, unknown, in the "
                                "spot-check, or its mark is none of yes, no, unsure, empty")
        out[line] = (mark, " ".join(str(item.get("author_note") or "").split()))
    if seed is not None:
        rest = [int(x["line"]) for x in lines if int(x["line"]) not in sample
                and (basis is None or x["identification_basis"] == basis)]
        if sorted(out) != draw(rest, seed, n):
            raise FollowupError(f"{path.name}: its lines are not the seeded sample")
    return out


def apply_voluntary(table: list[dict], lines: list[dict], marks: dict[int, tuple[str, str]],
                    discussed: frozenset[int] = frozenset()) -> list[dict]:
    """The table with the voluntary marks written in."""
    if not discussed <= set(marks):
        raise FollowupError("a discussed line is not among the marked lines")
    line_of, out = row_lines(lines), []
    for row_id, r in row_ids(table):
        line = line_of.get(row_id, -1)
        mark, note = marks.get(line, ("", ""))
        context = VOLUNTARY_DISCUSSED if line in discussed else VOLUNTARY
        new = dict(r)
        if mark in ("yes", "no") and r["third_check"] != "machine_gate_only":
            raise FollowupError(f"{row_id}: a voluntary mark for a row that is not "
                                "machine_gate_only")
        if mark == "yes":
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
    return out


def read_before(path: pathlib.Path) -> list[dict]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != BEFORE:
            raise FollowupError(f"{path.name}: not the extended table of the third check")
        return list(reader)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    c = sub.add_parser("context")
    for name in ("table", "codes", "discussed", "out"):
        c.add_argument(f"--{name}", type=pathlib.Path, required=True)
    v = sub.add_parser("voluntary")
    for name in ("table", "codes", "marked", "out"):
        v.add_argument(f"--{name}", type=pathlib.Path, required=True)
    v.add_argument("--seed", type=int)
    v.add_argument("--n", type=int)
    v.add_argument("--basis")
    v.add_argument("--discussed", type=pathlib.Path)
    a = ap.parse_args()
    lines = read_table(a.table)
    if a.command == "context":
        discussed = [int(n) for n in json.loads(a.discussed.read_text())["table_lines"]]
        made = add_context(read_before(a.codes), lines, discussed)
    else:
        marks = read_voluntary(a.marked, lines, a.seed, a.n, a.basis)
        talked = (frozenset(int(x) for x in json.loads(a.discussed.read_text())["table_lines"])
                  if a.discussed else frozenset())
        made = apply_voluntary(read_extended(a.codes), lines, marks, talked)
    write_csv(a.out, EXTENDED_FIELDS, made)
    record = {"command": a.command,
              "third_check": dict(collections.Counter(r["third_check"] or "not_applicable"
                                                      for r in made)),
              "third_check_context": dict(collections.Counter(
                  r["third_check_context"] or "none" for r in made)),
              "status": dict(collections.Counter(r["status"] for r in made))}
    if a.command == "voluntary":
        record |= {"marked_file_sha256": hashlib.sha256(a.marked.read_bytes()).hexdigest(),
                   "marks": dict(collections.Counter(m or "empty" for m, _ in marks.values()))}
    a.out.with_suffix(f".{a.command}.json").write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(record, indent=1))


if __name__ == "__main__":
    main()
