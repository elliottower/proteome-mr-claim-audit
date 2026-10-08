# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "openpyxl==3.1.5", "pydantic==2.13.5"]
# ///
"""The reader of scripts/manual_coding_check3_sample.py for marks saved as JSON (PREREG.md log,
2026-10-08). The author marked the sample on a web page that saves the marks as one JSON file,
`{"marks": [{"table_line": ..., "author_confirms": "yes" | "no", "author_note": ...}, ...]}`,
and not in the spreadsheet. Only how the marks are read differs: the draw, the refusals (a
blank or other mark, a line outside the sample, a missing or repeated line), the rules and the
table written are those of the sealed script, whose functions are used.

Usage: uv run scripts/manual_coding_check3_sample_json.py --table <check3_author_table.csv> \\
           --codes <extended csv after the reread> --marked <marks.json> [--second <json>] \\
           [--author-declines-full-read] --out <new extended csv>
"""

import argparse
import collections
import hashlib
import json
import pathlib

from manual_coding_check3_sample import N, SEED, SampleError, apply, decide, draw, read_table
from manual_coding_table_v2 import read_extended
from manual_coding_table_v3 import EXTENDED_FIELDS
from manual_dataset_coding import write_csv


def read_marks_json(path: pathlib.Path, sampled: list[int]) -> dict[int, tuple[str, str]]:
    """table line -> (yes or no, note) from a marks file. Raises unless it holds exactly the
    sampled lines, each once and each marked."""
    out, bad = {}, []
    for item in json.loads(path.read_text())["marks"]:
        line = int(item["table_line"])
        if line in out:
            raise SampleError(f"{path.name}: table line {line} stands twice")
        mark = str(item.get("author_confirms") or "").strip().casefold()
        if mark not in ("yes", "no"):
            bad.append(line)
        out[line] = (mark, " ".join(str(item.get("author_note") or "").split()))
    if sorted(out) != sorted(sampled):
        raise SampleError(f"{path.name}: its lines are not the sampled lines")
    if bad:
        raise SampleError(f"{path.name}: {len(bad)} line(s) not marked yes or no: {bad}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    for name in ("table", "codes", "marked", "out"):
        ap.add_argument(f"--{name}", type=pathlib.Path, required=True)
    ap.add_argument("--second", type=pathlib.Path)
    ap.add_argument("--author-declines-full-read", action="store_true")
    args = ap.parse_args()
    lines = read_table(args.table)
    all_lines = [int(x["line"]) for x in lines]
    first_lines = draw(all_lines, SEED, N)
    first = read_marks_json(args.marked, first_lines)
    second = None
    if args.second:
        rest = [n for n in all_lines if n not in set(first_lines)]
        second = read_marks_json(args.second, draw(rest, SEED + 1, N))
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
