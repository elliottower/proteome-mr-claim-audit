# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "openpyxl==3.1.5", "pydantic==2.13.5"]
# ///
"""The third check of the manual dataset coding as carried out in this run (PREREG.md log,
2026-10-08, deviation from item 5): the literal match is made for every coded row by the
machine gates, and the author reads a random sample of the coded rows and marks each yes or no.
No row is recorded as confirmed by the author unless he marked it.

`draw` reproduces the sample: `random.Random(seed).sample(range(N), n)` over the lines of the
author's table (scripts/manual_coding_check3_table.py) in file order, sorted, optionally over
the lines left after an earlier sample (`--exclude`). With `--manifest` it checks that the
lines equal those of a manifest already written and exits non-zero if they do not.

`apply` reads the marked spreadsheet of the sample: one row per sampled line under a header
row, with the table line in column K, the mark in column F (yes or no; case and surrounding
white space ignored) and the note in column G. A blank or other mark, a line that is not in the
sample, or a missing line blocks the step. Rules, fixed before any mark existed:

    0 of the sample marked no   every sampled row is `author_confirmed`; every other coded row
                                is `machine_gate_only`
    1 marked no                 that row is unresolved (`author_did_not_confirm`, the note
                                kept); a second sample of the same size is drawn from the
                                remaining lines with the next seed and read (`--second`); no
                                further no closes the check
    2 or more marked no,        the sample has failed as an audit: the step stops, and every
    or a no in the second       remaining row is read by a person
    sample                      (scripts/manual_coding_check3_marks.py); only if the author
                                declines (`--author-declines-full-read`) every coded row not
                                confirmed by the author whose identification basis is that of
                                a row marked no is set unresolved (`audit_failed_basis_class`)

It writes a new extended table in the form of scripts/manual_coding_table_v3.py (the column
`third_check`; `author_confirms` yes or no only for a marked row, `not_read` otherwise) and a
record with the sha256 of each marked file, the counts, and the one-sided 95% upper bound on
the share of coded rows that would not be confirmed: the largest p with
P(X <= x | n, p) >= 0.05 for x rows marked no among n read, which for x = 0 is
1 - 0.05 ** (1 / n).

Usage:
    uv run scripts/manual_coding_check3_sample.py draw --table <check3_author_table.csv> \\
        --seed 20261008 --n 20 [--exclude <manifest.json>] [--manifest <manifest.json>]
    uv run scripts/manual_coding_check3_sample.py apply --table <check3_author_table.csv> \\
        --codes <extended csv after the reread> --marked <xlsx> [--second <xlsx>] \\
        [--author-declines-full-read] --out <new extended csv>
"""

import argparse
import collections
import csv
import hashlib
import json
import math
import pathlib
import random

import openpyxl

from manual_coding_check3_table import FIELDS, UNRESOLVED, standing
from manual_coding_table_v2 import read_extended
from manual_coding_table_v3 import EXTENDED_FIELDS
from manual_dataset_coding import NOT_STATED, write_csv

SEED, N = 20261008, 20
MARK_COLUMN, NOTE_COLUMN, LINE_COLUMN = 6, 7, 11
NOT_CONFIRMED, AUDIT_FAILED = "author_did_not_confirm", "audit_failed_basis_class"


class SampleError(Exception):
    """A mark is missing, the sample is not the drawn one, or the audit has failed."""


def draw(lines: list[int], seed: int, n: int) -> list[int]:
    """The sampled table lines, sorted: a seeded sample of positions in the list given."""
    return sorted(lines[i] for i in random.Random(seed).sample(range(len(lines)), n))


def upper_bound(failures: int, n: int, alpha: float = 0.05) -> float:
    """One-sided upper confidence bound on a proportion (exact binomial)."""
    if failures >= n:
        return 1.0
    if failures == 0:
        return 1 - alpha ** (1 / n)
    lo, hi = 0.0, 1.0
    for _ in range(200):
        p = (lo + hi) / 2
        tail = sum(math.comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(failures + 1))
        lo, hi = (p, hi) if tail > alpha else (lo, p)
    return hi


def read_marks(path: pathlib.Path, sampled: list[int]) -> dict[int, tuple[str, str]]:
    """table line -> (yes or no, note) from a marked spreadsheet. Raises unless it holds
    exactly the sampled lines, each marked."""
    sheet = openpyxl.load_workbook(path, data_only=True).active
    out, bad = {}, []
    for row in range(2, sheet.max_row + 1):
        line = sheet.cell(row, LINE_COLUMN).value
        if line in (None, ""):
            continue
        mark = str(sheet.cell(row, MARK_COLUMN).value or "").strip().casefold()
        note = " ".join(str(sheet.cell(row, NOTE_COLUMN).value or "").split())
        if int(line) in out:
            raise SampleError(f"{path.name}: table line {line} stands twice")
        if mark not in ("yes", "no"):
            bad.append(int(line))
        out[int(line)] = (mark, note)
    if sorted(out) != sorted(sampled):
        raise SampleError(f"{path.name}: its lines are not the sampled lines")
    if bad:
        raise SampleError(f"{path.name}: {len(bad)} line(s) not marked yes or no: {bad}")
    return out


def decide(first: dict[int, tuple[str, str]], second: dict[int, tuple[str, str]] | None,
           declines: bool) -> dict:
    """What the marks mean under the rules fixed before any mark existed."""
    no_first = sorted(k for k, (m, _) in first.items() if m == "no")
    no_second = sorted(k for k, (m, _) in (second or {}).items() if m == "no")
    read = len(first) + len(second or {})
    base = {"lines_read": read, "marked_no": len(no_first) + len(no_second),
            "upper_bound_95_one_sided": upper_bound(len(no_first) + len(no_second), read)}
    if len(no_first) == 1 and second is None:
        raise SampleError("one sampled line is marked no: the second sample must be read")
    if len(no_first) == 0 and second is not None:
        raise SampleError("a second sample is given though no line of the first is marked no")
    failed = len(no_first) >= 2 or bool(no_second)
    if failed and not declines:
        raise SampleError("the sample has failed as an audit: every remaining row is read by a "
                          "person (scripts/manual_coding_check3_marks.py)")
    return base | {"audit": "failed" if failed else "passed", "lines_marked_no": no_first
                   + no_second}


def apply(table: list[dict], lines: list[dict], marks: dict[int, tuple[str, str]],
          decision: dict) -> list[dict]:
    """The extended table with the third check written in."""
    line_of = {item.split(" [", 1)[0]: int(x["line"]) for x in lines
               for item in x["rows"].split(" ; ")}
    failed_bases = set()
    if decision["audit"] == "failed":
        by_line = {int(x["line"]): x["identification_basis"] for x in lines}
        failed_bases = {by_line[k] for k in decision["lines_marked_no"]}
    out, seen = [], set()
    nth: collections.Counter = collections.Counter()
    for r in table:
        nth[(r["record_id"], r["side"])] += 1
        row_id = f"{r['record_id']}#{r['side']}_{nth[(r['record_id'], r['side'])]}"
        new = {**r, "third_check": "", "author_confirms": "not_read"}
        if standing(r) in UNRESOLVED:
            if row_id in line_of:
                raise SampleError(f"{row_id} is in the author's table and does not stand coded")
            new["status"] = "unresolved"
        else:
            if row_id not in line_of:
                raise SampleError(f"{row_id} stands coded and is not in the author's table")
            seen.add(row_id)
            mark, note = marks.get(line_of[row_id], (None, ""))
            if mark == "yes":
                new |= {"third_check": "author_confirmed", "author_confirms": "yes",
                        "status": "coded"}
                if note:
                    new["resolution_note"] = f"{r['resolution_note']} [author: {note}]".strip()
            elif mark == "no":
                new |= {"third_check": NOT_CONFIRMED, "author_confirms": "no",
                        "status": "unresolved", "unresolved_reason": NOT_CONFIRMED,
                        "resolution_note": (f"{r['resolution_note']} [author did not confirm"
                                            f"{': ' + note if note else ''}]").strip()}
            elif r["identification_basis"] in failed_bases:
                new |= {"third_check": NOT_CONFIRMED, "status": "unresolved",
                        "unresolved_reason": AUDIT_FAILED,
                        "resolution_note": (f"{r['resolution_note']} [the author's audit "
                                            "failed for this basis; not read]").strip()}
            else:
                new |= {"third_check": "machine_gate_only", "status": "coded"}
        out.append(new)
    if seen != set(line_of):
        raise SampleError("the author's table holds rows that are not in the extended table")
    return out


def read_table(path: pathlib.Path) -> list[dict]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != FIELDS:
            raise SampleError(f"{path.name}: columns must be {FIELDS}")
        return list(reader)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    d = sub.add_parser("draw")
    d.add_argument("--table", type=pathlib.Path, required=True)
    d.add_argument("--seed", type=int, default=SEED)
    d.add_argument("--n", type=int, default=N)
    d.add_argument("--exclude", type=pathlib.Path)
    d.add_argument("--manifest", type=pathlib.Path)
    a = sub.add_parser("apply")
    for name in ("table", "codes", "marked", "out"):
        a.add_argument(f"--{name}", type=pathlib.Path, required=True)
    a.add_argument("--second", type=pathlib.Path)
    a.add_argument("--author-declines-full-read", action="store_true")
    args = ap.parse_args()
    lines = read_table(args.table)
    all_lines = [int(x["line"]) for x in lines]
    if args.command == "draw":
        excluded = ({int(n) for n in json.loads(args.exclude.read_text())["table_lines"]}
                    if args.exclude else set())
        sampled = draw([n for n in all_lines if n not in excluded], args.seed, args.n)
        print(json.dumps({"seed": args.seed, "n": args.n, "of": len(all_lines) - len(excluded),
                          "table_sha256": hashlib.sha256(args.table.read_bytes()).hexdigest(),
                          "table_lines": sampled}))
        if args.manifest and [int(n) for n in json.loads(
                args.manifest.read_text())["table_lines"]] != sampled:
            raise SystemExit("the draw does not give the lines of the manifest")
        return
    first_lines = draw(all_lines, SEED, N)
    first = read_marks(args.marked, first_lines)
    second = None
    if args.second:
        rest = [n for n in all_lines if n not in set(first_lines)]
        second = read_marks(args.second, draw(rest, SEED + 1, N))
    decision = decide(first, second, args.author_declines_full_read)
    made = apply(read_extended(args.codes), lines, {**first, **(second or {})}, decision)
    write_csv(args.out, EXTENDED_FIELDS, made)
    record = {**decision, "seed": SEED, "sample_size": N,
              "marked_file": {"path": str(args.marked),
                              "sha256": hashlib.sha256(args.marked.read_bytes()).hexdigest()},
              "second_marked_file": None if not args.second else {
                  "path": str(args.second),
                  "sha256": hashlib.sha256(args.second.read_bytes()).hexdigest()},
              "third_check": dict(collections.Counter(
                  r["third_check"] or "not_applicable" for r in made)),
              "status": dict(collections.Counter(r["status"] for r in made))}
    args.out.with_suffix(".third_check.json").write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(record, indent=1))


if __name__ == "__main__":
    main()
