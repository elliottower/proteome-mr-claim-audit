# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""Read the second check's answers on the manual dataset coding, check each batch, and compare
them with the first check (PREREG.md, §Manual coding of dataset names, item 5; log of
2026-10-08). No answer is repaired by hand: a batch that fails a check is listed for rerun.

Answers. One file per batch and run, `batch_<NN>_<anything>.md`, as the checker returned it.
An answer line is

    <row id> | <answer> | <sentence quoted, or none> | <reference label, or none> | <reasoning>

where the row id is `<record>#<side>_<k>` (a backslash before `#` is dropped) and footnote
marks at the end of a line are dropped. The quoted sentence may itself hold " | " (a table row
line); the fields are split so that the quotation is a supplied sentence where that is
possible.

Checks, per file: every row of the batch (the `### Row` headings of `batch_<NN>.md`) answered
once and in the batch's order, and no other row; each answer the exact name of a dictionary
row of the row's side, `not_stated_in_source` or `source_names_dataset_absent_from_dictionary`;
each quotation that is not `none` a whole sentence of that row's supplied passages or of
another row of the same paper (which is recorded), white space normalised, and a quotation
given for every answer that names a dictionary row or an absent dataset; the closing line
`external sources used: none`; every footnote naming an attached file (the batch, the prompt,
the dictionary definitions) and no address. For a `not_stated_in_source` answer the category
the reasoning begins with (`release_not_identified` or `conflicting_identifiers`) is recorded;
its absence is a warning, not a failure.

Outputs in `--out`, never overwritten: `<answers file stem>.json` (the parsed answers and every
check), `summary.json` (per batch: files, which pass, which batches need a rerun, which are
still unanswered), and, for the batches with exactly one passing file,
`comparison_with_first_check.json`: per row the first check's final value (the paper's highest
attempt) and the second check's, classed as agree on the same dictionary row, agree unresolved
with the same category, agree unresolved with another category, both unresolved with different
values, or disagree; counts by class. Agreement is a count; a disagreement is resolved by
rereading the source, and both original answers stay in the table.

`merge` writes a copy of the extended table of scripts/manual_coding_table.py with
`perplexity_value` filled from the passing files; it refuses unless every row has an answer.

Usage:
    uv run scripts/manual_coding_check2_ingest.py ingest --answers <dir> --batches <dir> \\
        --coders <coders dir> --out <dir>
    uv run scripts/manual_coding_check2_ingest.py merge --ingested <dir> \\
        --codes <manual_dataset_codes_extended.csv> --out <new extended csv>
"""

import argparse
import collections
import csv
import json
import pathlib
import re

from dataset_relations import DICTIONARY
from manual_coding_table import ABSENT, ATTEMPT, EXTENDED_FIELDS, read_extended
from manual_dataset_coding import NOT_STATED, write_csv

ANSWERS_FILE = re.compile(r"^batch_(\d{2})_.+\.md$")
ROW_ID = re.compile(r"^([^\s|#]+)#((?:pqtl|outcome)_\d+)$")
HEADING = re.compile(r"^### Row (\S+)#((?:pqtl|outcome)_\d+)\s*$", re.M)
FOOTNOTE_MARKS = re.compile(r"(?:\s*\[\^[^\]]+\])+\s*$")
FOOTNOTE = re.compile(r"^\[\^([^\]]+)\]:\s*(.*)$", re.M)
ATTACHED = re.compile(r"^(?:batch_\d{2}|01_PROMPT_check2\w*|02_dictionary_definitions)"
                      r"(?:-\d+)?\.(?:md|csv)$")
CLOSING = re.compile(r"^\W*external sources used:\s*none\W*$", re.I | re.M)
MODEL = re.compile(r"^\W*model:\s*(.+?)\s*$", re.I | re.M)
CATEGORY = re.compile(r"^\W*(release_not_identified|conflicting_identifiers)\b")
UNRESOLVED = (NOT_STATED, ABSENT)


class IngestError(Exception):
    """An output exists, or a batch or input file an answers file needs is missing."""


def collapsed(text: str) -> str:
    return " ".join(text.split())


def paper_rows(coders: pathlib.Path) -> dict[str, dict]:
    """row id -> {side, sentences, record} for every row of every coder input file."""
    out = {}
    for path in sorted(coders.glob("coder_*/input/*.json")):
        given = json.loads(path.read_text())
        nth: collections.Counter = collections.Counter()
        for row in given["rows"]:
            nth[row["side"]] += 1
            out[f"{given['record_id']}#{row['side']}_{nth[row['side']]}"] = {
                "record": given["record_id"], "side": row["side"],
                "name_as_written": row["name_as_written"],
                "sentences": {collapsed(s) for p in row["passages"] for s in p["sentences"]}}
    return out


def split_line(line: str, sentences: set[str]) -> dict | None:
    """The fields of one answer line, or None when it is not one."""
    parts = [p.strip() for p in FOOTNOTE_MARKS.sub("", line).split(" | ")]
    row = ROW_ID.match(parts[0].replace("\\#", "#").replace("\\_", "_")) if parts else None
    if not row or len(parts) < 5:
        return None
    cut = len(parts) - 3
    for j in range(2, len(parts) - 2):
        quote = collapsed(" | ".join(parts[2:j + 1]))
        if quote == "none" or quote in sentences:
            cut = j
            break
    return {"row": f"{row[1]}#{row[2]}", "answer": parts[1].strip("`"),
            "quote": collapsed(" | ".join(parts[2:cut + 1])), "reference": parts[cut + 1],
            "reasoning": " | ".join(parts[cut + 2:])}


def check_file(text: str, expected: list[str], rows: dict[str, dict],
               names: set[tuple[str, str]]) -> dict:
    """The parsed answers of one answers file and every check on it."""
    answers, failures = [], []
    for line in text.splitlines():
        head = line.split(" | ")[0].strip().replace("\\#", "#").replace("\\_", "_")
        known = rows.get(head, {"sentences": set()})
        parsed = split_line(line, known["sentences"])
        if parsed:
            answers.append(parsed)
    got = [a["row"] for a in answers]
    if got != expected:
        failures.append({"check": "rows_present_once_and_in_order",
                         "missing": [r for r in expected if r not in got],
                         "not_in_the_batch": [r for r in got if r not in expected],
                         "repeated": sorted({r for r in got if got.count(r) > 1}),
                         "out_of_order": sorted(set(got)) == sorted(set(expected))})
    for a in answers:
        row = rows.get(a["row"])
        a["checks"] = {}
        if row is None:
            continue
        coded = (row["side"], a["answer"]) in names
        a["checks"]["answer_allowed"] = coded or a["answer"] in UNRESOLVED
        a["quote_from_another_row"] = None
        if a["quote"] == "none":
            a["checks"]["quote_supplied"] = not (coded or a["answer"] == ABSENT)
        elif a["quote"] in row["sentences"]:
            a["checks"]["quote_supplied"] = True
        else:
            other = sorted(k for k, v in rows.items() if v["record"] == row["record"]
                           and k != a["row"] and a["quote"] in v["sentences"])
            a["checks"]["quote_supplied"] = bool(other)
            a["quote_from_another_row"] = other[0] if other else None
        category = CATEGORY.match(a["reasoning"])
        a["unresolved_category"] = (category[1] if category and a["answer"] == NOT_STATED
                                    else "dataset_absent_from_dictionary"
                                    if a["answer"] == ABSENT else None)
        for check, passed in a["checks"].items():
            if not passed:
                failures.append({"check": check, "row": a["row"]})
    notes = dict(FOOTNOTE.findall(text))
    foreign = sorted(k for k, v in notes.items() if not ATTACHED.match(v.strip()))
    if foreign:
        failures.append({"check": "footnotes_name_attached_files_only", "footnotes": foreign})
    if not CLOSING.search(text):
        failures.append({"check": "closing_line_external_sources_none"})
    model = MODEL.search(text)
    warnings = [{"warning": "unresolved_category_not_stated", "row": a["row"]} for a in answers
                if a["answer"] == NOT_STATED and a.get("unresolved_category") is None]
    return {"answers": answers, "rows_expected": len(expected), "rows_answered": len(got),
            "model_line": model[1] if model else None, "footnotes": notes,
            "passes": not failures, "failures": failures, "warnings": warnings}


def first_check(coders: pathlib.Path, names: set[tuple[str, str]]) -> dict[str, dict]:
    """row id -> the first check's final value, from the highest attempt of each paper."""
    out = {}
    for coder in sorted(p for p in coders.glob("coder_*") if p.is_dir()):
        best: dict[str, tuple[int, pathlib.Path]] = {}
        for path in sorted((coder / "codes").glob("*.json")):
            m = ATTEMPT.match(path.name)
            if m and (m["name"] not in best or int(m["n"]) > best[m["name"]][0]):
                best[m["name"]] = (int(m["n"]), path)
        for _, path in best.values():
            made = json.loads(path.read_text())
            nth: collections.Counter = collections.Counter()
            for r in made["rows"]:
                nth[r["side"]] += 1
                coded = (r["side"], r["value"]) in names
                out[f"{made['record_id']}#{r['side']}_{nth[r['side']]}"] = {
                    "value": r["value"], "coded": coded,
                    "category": None if coded else r.get("unresolved_reason")}
    return out


def compare(first: dict, second: dict) -> str:
    """The class of one row: `first` from the first check, `second` an ingested answer."""
    a, b = first["value"], second["answer"]
    if first["coded"] or b not in UNRESOLVED:
        return "agree_same_dictionary_row" if a == b else "disagree"
    if a != b:
        return "both_unresolved_different_value"
    same = first["category"] == second["unresolved_category"]
    return "agree_unresolved_same_category" if same else "agree_unresolved_other_category"


def ingest(answers: pathlib.Path, batches: pathlib.Path, coders: pathlib.Path,
           out: pathlib.Path) -> dict:
    if out.exists():
        raise IngestError(f"{out} exists; an ingest is written once")
    with DICTIONARY.open(newline="") as f:
        names = {(r["side"], r["name"]) for r in csv.DictReader(f)}
    rows = paper_rows(coders)
    expected = {p.stem[-2:]: [f"{a}#{b}" for a, b in HEADING.findall(p.read_text())]
                for p in sorted(batches.glob("batch_[0-9][0-9].md"))}
    out.mkdir(parents=True)
    by_batch: dict[str, list] = collections.defaultdict(list)
    for path in sorted(answers.glob("batch_*.md")):
        m = ANSWERS_FILE.match(path.name)
        if not m:
            continue
        if m[1] not in expected:
            raise IngestError(f"{path.name}: no batch_{m[1]}.md among the batches")
        result = check_file(path.read_text(), expected[m[1]], rows, names)
        result = {"answers_file": path.name, "batch": m[1], **result}
        (out / f"{path.stem}.json").write_text(
            json.dumps(result, indent=1, ensure_ascii=False) + "\n")
        by_batch[m[1]].append(result)
    summary: dict = {"batches": {}, "rerun": [], "unanswered": [], "several_passing_files": []}
    counted: dict[str, dict] = {}
    for batch in sorted(expected):
        files = by_batch.get(batch, [])
        passing = [f["answers_file"] for f in files if f["passes"]]
        summary["batches"][batch] = {"rows": len(expected[batch]),
                                     "files": [f["answers_file"] for f in files],
                                     "passing": passing}
        if not files:
            summary["unanswered"].append(batch)
        elif not passing:
            summary["rerun"].append(batch)
        elif len(passing) > 1:
            summary["several_passing_files"].append(batch)
        else:
            chosen = next(f for f in files if f["passes"])
            counted.update({a["row"]: {**a, "answers_file": chosen["answers_file"]}
                            for a in chosen["answers"]})
    before = first_check(coders, names)
    compared = [{"row": row, "first_check": before[row]["value"],
                 "first_check_category": before[row]["category"],
                 "second_check": a["answer"], "second_check_category": a["unresolved_category"],
                 "class": compare(before[row], a), "answers_file": a["answers_file"]}
                for row, a in sorted(counted.items())]
    counts = collections.Counter(c["class"] for c in compared)
    summary["rows_with_a_counted_answer"] = len(compared)
    summary["rows_in_all_batches"] = sum(len(v) for v in expected.values())
    summary["comparison_counts"] = dict(sorted(counts.items()))
    (out / "comparison_with_first_check.json").write_text(json.dumps(
        {"counts": summary["comparison_counts"], "rows": compared}, indent=1,
        ensure_ascii=False) + "\n")
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    return summary


def merge(ingested: pathlib.Path, table: list[dict]) -> list[dict]:
    """The extended table with `perplexity_value` filled from the counted answers."""
    rows = json.loads((ingested / "comparison_with_first_check.json").read_text())["rows"]
    second = {r["row"]: r["second_check"] for r in rows}
    out, nth = [], collections.Counter()
    for r in table:
        nth[(r["record_id"], r["side"])] += 1
        key = f"{r['record_id']}#{r['side']}_{nth[(r['record_id'], r['side'])]}"
        if key not in second:
            raise IngestError(f"{key} has no counted second-check answer")
        out.append({**r, "perplexity_value": second[key]})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    i = sub.add_parser("ingest")
    for name in ("answers", "batches", "coders", "out"):
        i.add_argument(f"--{name}", type=pathlib.Path, required=True)
    m = sub.add_parser("merge")
    for name in ("ingested", "codes", "out"):
        m.add_argument(f"--{name}", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.command == "ingest":
        summary = ingest(a.answers, a.batches, a.coders, a.out)
        print(json.dumps({k: v for k, v in summary.items() if k != "batches"}, indent=1))
        return
    write_csv(a.out, EXTENDED_FIELDS, merge(a.ingested, read_extended(a.codes)))
    print(a.out)


if __name__ == "__main__":
    main()
