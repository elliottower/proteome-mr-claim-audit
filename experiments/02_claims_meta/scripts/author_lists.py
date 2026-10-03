# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.13.5"]
# ///
"""Protein lists supplied by the authors of two dataset source papers, and the stage-tied cutoff
that decides whether such a list replaces the registered background of its dictionary row.

Two rows of the attachment table (verification/platform_assay_attachments.csv) take a list the
authors could improve: SCALLOP CVD-I (Folkersen et al. 2020), whose table lists the 92 proteins
measured without marking the 2 that failed quality control, and AGES Reykjavik (Emilsson et al.
2018), which takes the list of Gudjonsson et al. 2022 as an annotation-linked proxy because
Table S1 is not served. Requests were sent to the authors on 2026-10-02 and 2026-10-03.

A list the authors supply is pinned (the source with its sha256, through `citations`), added to
the assay lists under its own list id, and entered as one row of
verification/author_supplied_lists.csv with the UTC time of its pin. The table is empty at the
freeze.

Cutoff. A supplied list replaces the row's registered background only when it was pinned before
the pathway enrichment first ran: before the earliest of (a) the ledger timestamp of the first
recorded stage-5 biology joins run (`s5_biology_<run>`) and (b) the `written_utc` of any
confirmatory `pathway_enrichment.json` already written under outputs/stage5_biology/. When
neither exists, the enrichment has not run and every pinned list is before the cutoff. A list
pinned after the cutoff leaves the registered background primary and is read only in the
sensitivity analysis `author_supplied_lists_after_cutoff`; it never replaces the primary.

`decide` writes author_list_decisions.json into the stage-5 inputs folder before the joins run;
the joins refuse to run when the table has a row and the decisions file is absent.

Usage: uv run scripts/author_lists.py decide --inputs outputs/registry/<run>_coded \
           --ledger "$(git rev-parse --show-toplevel)/.results/ledger.jsonl"
"""

import argparse
import csv
import datetime
import json
import pathlib

from pydantic import BaseModel

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
TABLE = EXP / "verification" / "author_supplied_lists.csv"
STAGE5_OUTPUTS = EXP / "outputs" / "stage5_biology"
DECISIONS = "author_list_decisions.json"
ELIGIBLE_ROWS = ("SCALLOP CVD-I (Folkersen 2020)", "AGES Reykjavik (Emilsson 2018)")
STAGE5_RUN_PREFIX = "s5_biology_"
LEVELS = ("analysed", "assayed")


class AuthorListError(Exception):
    """The author-list table or the decisions file is inconsistent."""


class AuthorList(BaseModel):
    dictionary_row: str
    list_id: str
    background_level: str
    source_claims: str
    sha256: str
    pinned_utc: datetime.datetime


def load_table(path: pathlib.Path = TABLE) -> list[AuthorList]:
    with path.open(newline="") as f:
        rows = [AuthorList.model_validate(r) for r in csv.DictReader(f)]
    for r in rows:
        if r.dictionary_row not in ELIGIBLE_ROWS:
            raise AuthorListError(f"{r.dictionary_row!r}: the registered rule covers only "
                                  f"{list(ELIGIBLE_ROWS)}")
        if r.background_level not in LEVELS:
            raise AuthorListError(f"{r.dictionary_row!r}: level {r.background_level!r}")
        if len(r.sha256) != 64:
            raise AuthorListError(f"{r.dictionary_row!r}: no sha256 of the pinned source")
        if r.pinned_utc.tzinfo is None:
            raise AuthorListError(f"{r.dictionary_row!r}: pin time without a time zone")
    if len({r.dictionary_row for r in rows}) != len(rows):
        raise AuthorListError("one supplied list per dictionary row")
    return rows


def ledger_cutoff(ledger: pathlib.Path) -> datetime.datetime | None:
    """Timestamp of the first recorded stage-5 biology joins run, or None."""
    if not ledger.exists():
        return None
    times = [datetime.datetime.fromisoformat(e["timestamp"])
             for e in map(json.loads, (l for l in ledger.read_text().splitlines() if l.strip()))
             if e.get("event") == "run" and e.get("run_id", "").startswith(STAGE5_RUN_PREFIX)]
    return min(times, default=None)


def output_cutoff(stage5: pathlib.Path) -> datetime.datetime | None:
    """Earliest `written_utc` of a confirmatory pathway_enrichment.json, or None."""
    times = []
    for p in sorted(stage5.glob("*/pathway_enrichment.json")) if stage5.exists() else []:
        d = json.loads(p.read_text())
        if d.get("window", "confirmatory") == "confirmatory":
            times.append(datetime.datetime.fromisoformat(d["written_utc"]))
    return min(times, default=None)


def cutoff(ledger: pathlib.Path, stage5: pathlib.Path = STAGE5_OUTPUTS
           ) -> tuple[datetime.datetime | None, str]:
    found = [(t, s) for t, s in ((ledger_cutoff(ledger), "ledger"),
                                 (output_cutoff(stage5), "outputs")) if t is not None]
    if not found:
        return None, "enrichment_not_yet_run"
    return min(found)


def decide(rows: list[AuthorList], cut: datetime.datetime | None) -> dict:
    """Rows pinned before the cutoff replace the registered list (`primary`); later rows are
    read only in the sensitivity analysis (`after_cutoff`). With no cutoff every row is before
    it."""
    primary, after = {}, {}
    for r in rows:
        entry = {"list_id": r.list_id, "background_level": r.background_level,
                 "pinned_utc": r.pinned_utc.isoformat()}
        if cut is None or r.pinned_utc < cut:
            primary[r.dictionary_row] = entry
        else:
            after[r.dictionary_row] = entry
    return {"primary": primary, "after_cutoff": after}


def overrides(decisions: dict, part: str) -> dict[str, tuple[str, str]]:
    return {row: (e["list_id"], e["background_level"]) for row, e in decisions[part].items()}


def load_decisions(inputs: pathlib.Path, table: pathlib.Path = TABLE) -> dict:
    """The decisions file of a stage-5 inputs folder; refused when the table has a row and the
    file is absent, or when the file disagrees with the table."""
    rows = load_table(table)
    path = inputs / DECISIONS
    if not path.exists():
        if rows:
            raise AuthorListError(f"{path} missing: run scripts/author_lists.py decide first")
        return {"primary": {}, "after_cutoff": {}}
    d = json.loads(path.read_text())
    if set(d["primary"]) | set(d["after_cutoff"]) != {r.dictionary_row for r in rows}:
        raise AuthorListError(f"{path}: rows differ from {table.name}")
    return d


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("decide")
    d.add_argument("--inputs", type=pathlib.Path, required=True)
    d.add_argument("--ledger", type=pathlib.Path, required=True,
                   help="the repository's .results/ledger.jsonl")
    a = ap.parse_args()
    target = a.inputs / DECISIONS
    if target.exists():
        raise FileExistsError(f"{target} exists; archive it before rerunning")
    if not a.ledger.exists():
        raise AuthorListError(f"{a.ledger}: no ledger")
    cut, source = cutoff(a.ledger)
    result = {"table": str(TABLE.relative_to(EXP)),
              "cutoff_utc": cut.isoformat() if cut else None, "cutoff_source": source,
              "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
              **decide(load_table(), cut)}
    target.write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
