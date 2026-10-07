# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Assign the papers of the manual dataset-coding queue to coders and write each coder's input
files (PREREG.md log, 2026-10-07). One coder per paper: every row of a paper goes to the coder
the paper goes to.

The papers, sorted by record id, are shuffled with `random.Random(seed)` and dealt in turn to
`coder_1` ... `coder_<n>`. Each coder's folder gets `input/<file name>.json`, the paper's
passage file of scripts/coding_passages.py with the coder's id added, and an empty `codes/`
folder. `assignment.json` records the seed, the number of coders and the coder of every paper;
`dictionary_definitions.csv` holds the dictionary fields a coder may read.

Usage: uv run scripts/coding_assignment.py --passages <passages dir> --out <coders dir> \\
           [--seed 20261007] [--coders 4]
"""

import argparse
import csv
import json
import pathlib
import random

DICTIONARY = pathlib.Path(__file__).resolve().parent.parent / "dataset_dictionary.csv"
DEFINITION_FIELDS = ("side", "name", "aliases", "release", "cohort_components", "ancestry",
                     "sample_size", "platform", "source_citation", "source_identifier")
PAPER_FIELDS = {"record_id", "source", "rows", "coder_id"}
ROW_FIELDS = {"side", "name_as_written", "mapping_state", "candidates", "status", "passages"}
SUMMARY = "passages_summary.json"


class AssignmentError(Exception):
    """The output exists, or a passage file holds a field a coder may not receive."""


def assign(papers: list[str], seed: int, n_coders: int) -> dict[str, str]:
    order = sorted(papers)
    random.Random(seed).shuffle(order)
    return {rid: f"coder_{i % n_coders + 1}" for i, rid in enumerate(order)}


def coder_input(paper: dict, coder: str) -> dict:
    made = {**paper, "coder_id": coder}
    if set(made) != PAPER_FIELDS or any(set(r) != ROW_FIELDS for r in made["rows"]):
        raise AssignmentError(f"{paper.get('record_id')}: fields other than the permitted ones")
    return made


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--passages", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--seed", type=int, default=20261007)
    ap.add_argument("--coders", type=int, default=4)
    a = ap.parse_args()
    if a.out.exists():
        raise AssignmentError(f"{a.out} exists; the assignment is made once")
    files = {p: json.loads(p.read_text()) for p in sorted(a.passages.glob("*.json"))
             if p.name != SUMMARY}
    coder_of = assign([paper["record_id"] for paper in files.values()], a.seed, a.coders)
    for k in range(1, a.coders + 1):
        (a.out / f"coder_{k}" / "input").mkdir(parents=True)
        (a.out / f"coder_{k}" / "codes").mkdir()
    for path, paper in files.items():
        coder = coder_of[paper["record_id"]]
        (a.out / coder / "input" / path.name).write_text(
            json.dumps(coder_input(paper, coder), indent=1, ensure_ascii=False) + "\n")
    with DICTIONARY.open(newline="") as f, \
            (a.out / "dictionary_definitions.csv").open("w", newline="") as g:
        w = csv.DictWriter(g, fieldnames=DEFINITION_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(csv.DictReader(f))
    per_coder = {f"coder_{k}": sum(c == f"coder_{k}" for c in coder_of.values())
                 for k in range(1, a.coders + 1)}
    (a.out / "assignment.json").write_text(json.dumps(
        {"seed": a.seed, "n_coders": a.coders, "papers": len(coder_of),
         "papers_per_coder": per_coder, "coder_of": dict(sorted(coder_of.items()))},
        indent=1) + "\n")
    print(json.dumps({"seed": a.seed, "papers": len(coder_of), "papers_per_coder": per_coder}))


if __name__ == "__main__":
    main()
