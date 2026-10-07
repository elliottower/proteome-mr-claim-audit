# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "numpy==2.5.3", "pydantic==2.13.5", "pyyaml==6.0.3"]
# ///
"""Screen of the rows a coder left unresolved for want of an identified release, for an
identifier the coder's reading may have missed (PREREG.md log, 2026-10-07). An added
quality-control gate: it replaces none of the three registered checks, and a hit codes
nothing. It marks a paper for rereading by its own coder with every passage shown in full.

Rows screened: in the last attempt of each paper, every row whose value is
`not_stated_in_source` with the reason `release_not_identified`.

A hit: the full text of one of the row's passages holds what would let a code pass the machine
gates (scripts/manual_coding_gates.py, whose functions are used here), for a dictionary row of
the row's side:

    sentence          `identifier_basis` is not empty for the dictionary row on one sentence
                      (or table row line) of a passage: an identifier of that row no other
                      candidate has, or its exact sample size with its platform or a year
    reference entry   a reference entry attached to a passage is verified against the
                      dictionary row by `reference_check` (its DOI, else PMID, else PMC
                      identifier), or `identifier_basis` is not empty on the entry's text with
                      its identifiers

The candidates a dictionary row is compared with are the gate's: the row's candidates that are
dictionary rows when it is one of them, else every dictionary row of the side.

Rows named with `--refused-pin` (`<coder>/<input file name>#<side>_<k>`, the k-th row of that
side in the paper's file: a row left unresolved because `citations pin` refused its sentence)
are marked as well.

Outputs, never overwritten: `coders/<coder>/screen/<file name>.attempt<n>.screen.json` for each
marked paper, listing the marked rows by side and name with the reason (`missed_identifier_screen`
or `refused_pin`) and nothing else, for the coder; `<out>/<coder>.json` with every hit
(passage, sentence or entry, dictionary row, basis), which no coder is given; `<out>/summary.json`.

Usage: uv run scripts/manual_coding_missed_identifier_screen.py --coders <coders dir> \\
           --out <audit dir> [--refused-pin <coder>/<file name>#<side>_<k> ...]
"""

import argparse
import collections
import csv
import json
import pathlib

from dataset_relations import DICTIONARY
from manual_coding_gates import identifier_basis, reference_check
from manual_coding_passages import dictionary_terms, matches
from manual_coding_table import ATTEMPT, NOT_STATED

REASON = "release_not_identified"
SCREEN, REFUSED = "missed_identifier_screen", "refused_pin"


class ScreenError(Exception):
    """An output exists, or a row named as a refused pin is not in the paper's file."""


def entry_material(entry: dict) -> str:
    return " ".join(str(entry.get(f) or "") for f in ("entry", "doi", "pmid", "pmcid"))


def touches(row: dict, text: str) -> bool:
    """Whether any term of the dictionary row occurs in the text (a cheap necessary condition
    for `identifier_basis`, which is then what decides)."""
    return any(matches(t, text) for t in dictionary_terms(row))


def row_hits(given: dict, dictionary: dict[tuple[str, str], dict]) -> list[dict]:
    """Every hit of one row the coder was given, over its passages in full."""
    side = given["side"]
    rows = [r for (s, _), r in dictionary.items() if s == side]
    named = [dictionary[(side, c)] for c in given["candidates"] if (side, c) in dictionary]
    hits = []
    for passage in given["passages"]:
        for row in rows:
            pool = named if row in named else rows
            for i, sentence in enumerate(passage["sentences"]):
                basis = identifier_basis(row, pool, sentence) if touches(row, sentence) else []
                if basis:
                    hits.append({"passage_id": passage["passage_id"], "via": "sentence",
                                 "sentence": i, "dictionary_row": row["name"], "basis": basis})
            for entry in passage["references"]:
                material = entry_material(entry)
                verified, failure = reference_check(entry, row["source_identifier"])
                basis = identifier_basis(row, pool, material) if touches(row, material) else []
                if failure is None or basis:
                    hits.append({"passage_id": passage["passage_id"], "via": "reference_entry",
                                 "reference_label": entry["label"],
                                 "dictionary_row": row["name"], "basis": basis,
                                 "verified_by": verified if failure is None else None})
    return hits


def screen_attempt(attempt: dict, given: dict, dictionary: dict[tuple[str, str], dict],
                   refused: set[str]) -> tuple[list[dict], list[dict]]:
    """(the rows marked, for the coder; every hit, for the audit) of one attempt file."""
    marked, audit = [], []
    nth: collections.Counter = collections.Counter()
    for coded, g in zip(attempt["rows"], given["rows"], strict=True):
        nth[g["side"]] += 1
        row_id = f"{g['side']}_{nth[g['side']]}"
        reasons = []
        if coded["value"] == NOT_STATED and coded.get("unresolved_reason") == REASON:
            hits = row_hits(g, dictionary)
            if hits:
                reasons.append(SCREEN)
                audit.append({"row": row_id, "side": g["side"],
                              "name_as_written": g["name_as_written"], "hits": hits})
        if row_id in refused:
            reasons.append(REFUSED)
        if reasons:
            marked.append({"row": row_id, "side": g["side"],
                           "name_as_written": g["name_as_written"], "reasons": reasons})
    missing = refused - {f"{s}_{k}" for s, n in nth.items() for k in range(1, n + 1)}
    if missing:
        raise ScreenError(f"{given['record_id']}: no row {sorted(missing)}")
    return marked, audit


def last_attempts(coder: pathlib.Path) -> dict[str, tuple[int, pathlib.Path]]:
    best: dict[str, tuple[int, pathlib.Path]] = {}
    for path in sorted((coder / "codes").glob("*.json")):
        m = ATTEMPT.match(path.name)
        if not m:
            raise ScreenError(f"{path}: not an attempt file")
        if m["name"] not in best or int(m["n"]) > best[m["name"]][0]:
            best[m["name"]] = (int(m["n"]), path)
    return best


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coders", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--refused-pin", action="append", default=[])
    a = ap.parse_args()
    if a.out.exists():
        raise ScreenError(f"{a.out} exists; a screen is written once")
    with DICTIONARY.open(newline="") as f:
        dictionary = {(r["side"], r["name"]): r for r in csv.DictReader(f)}
    refused: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for item in a.refused_pin:
        place, row_id = item.rsplit("#", 1)
        coder, name = place.split("/", 1)
        refused[(coder, name.removesuffix(".json"))].add(row_id)
    a.out.mkdir(parents=True)
    summary: dict = {"refused_pins_named": sorted(a.refused_pin), "coders": {}}
    for coder in sorted(p for p in a.coders.glob("coder_*") if p.is_dir()):
        counts: collections.Counter = collections.Counter()
        audit_all, papers = {}, []
        for name, (n, path) in sorted(last_attempts(coder).items()):
            attempt = json.loads(path.read_text())
            given = json.loads((coder / "input" / f"{name}.json").read_text())
            marked, audit = screen_attempt(attempt, given, dictionary,
                                           refused.pop((coder.name, name), set()))
            counts["papers"] += 1
            counts["rows_screened"] += sum(
                r["value"] == NOT_STATED and r.get("unresolved_reason") == REASON
                for r in attempt["rows"])
            counts["rows_with_a_hit"] += len(audit)
            counts["rows_refused_pin"] += sum(REFUSED in r["reasons"] for r in marked)
            counts["rows_marked"] += len(marked)
            if not marked:
                continue
            counts["papers_marked"] += 1
            counts["papers_with_a_hit"] += bool(audit)
            target = coder / "screen" / f"{name}.attempt{n}.screen.json"
            if target.exists():
                raise ScreenError(f"{target} exists")
            target.parent.mkdir(exist_ok=True)
            target.write_text(json.dumps(
                {"record_id": given["record_id"], "coder_id": coder.name, "attempt": n,
                 "rows_to_reread": marked}, indent=1, ensure_ascii=False) + "\n")
            papers.append(f"{name}.json")
            if audit:
                audit_all[f"{name}.json"] = audit
        (a.out / f"{coder.name}.json").write_text(
            json.dumps(audit_all, indent=1, ensure_ascii=False) + "\n")
        summary["coders"][coder.name] = {**dict(sorted(counts.items())), "papers_marked_files":
                                         papers}
    if refused:
        raise ScreenError(f"refused pins of no attempt file: {sorted(refused)}")
    total: collections.Counter = collections.Counter()
    for c in summary["coders"].values():
        total.update({k: v for k, v in c.items() if isinstance(v, int)})
    summary["all"] = dict(sorted(total.items()))
    (a.out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({k: {x: y for x, y in v.items() if x != "papers_marked_files"}
                      for k, v in {**summary["coders"], "all": summary["all"]}.items()},
                     indent=1))


if __name__ == "__main__":
    main()
