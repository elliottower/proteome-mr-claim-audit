# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""The control set of the second release-resolution registration, built and screened before any
coding (PREREG.md, §Study design, item 1; frozen 19 October 2026). No model is called here and no
source is read by hand; the two judges are called by scripts/modal_control_screen_v1.py through
the first registration's scripts/judge_v3.py.

Scan (`scan_record`). The frozen scanner (source_scanner_v2.controls, with its patterns,
reference/c1_scanner_patterns_v2.json) over the units of a record's readable retrieved sources
(c1_controls.units), all of the first registration, imported unchanged.

Candidates (`candidates`), as in Amendment 2, item 3: among the matches in text of routes R1 and
R3, one per record and identifier, the first in sorted order of source and unit. Each becomes a
control row by c1_controls.control_rows (row id from coding_queue.row_id over record, side,
identifier and `control`); every candidate is marked, whatever its record's number of candidates.

Packets. Deviation 2, item 2, by control_validity_v1.packet (sealed, unchanged): the row id, side,
identifier, the scanner's unit with the units before and after it and a table row's header, and
the record's claims. A record outside the scope has no coding queue, so its claims are those of
every Paper 1 claim record of the record (`claim_queue`), each with protein, outcome and direction
from its first claim check (control_validity_v1.claims_of_records, unchanged). Send order: the
sorted row ids shuffled by `random.Random(SEND_SEED).shuffle`.

Eligibility (`classify`): eligible only when both judges mark the candidate valid. Every other
outcome is excluded and labelled: `invalid` (both invalid), `disputed` (one valid, one invalid),
`cannot_mark` (either marks cannot_mark, neither request failed), `failed_twice` (either judge's
request failed twice).

Draw (`draw`): the eligible candidates in sorted order of row id, shuffled by
`random.Random(DRAW_SEED).shuffle`, taken in that order, at most PER_RECORD per record and MAXIMUM
in all. Stage A runs only if at least MINIMUM candidates are eligible.
"""

import random

import c1_controls as c1
import control_validity_v1 as cv
import source_scanner_v2 as scanner

ROUTES = ("R1", "R3")
DRAW_SEED = 20261033
SEND_SEED = 20261034
PER_RECORD = 5
MAXIMUM = 150
MINIMUM = 50
LABELS = ("eligible", "invalid", "disputed", "cannot_mark", "failed_twice")


class ScreenError(Exception):
    """Two candidates share a row id, or a judge's request has no final answer."""


def scan_record(record_id: str, sources: list[dict], patterns: dict,
                mapper: scanner.Mapper) -> dict:
    units = c1.units(record_id, sources)
    return {"record_id": record_id, "units": len(units),
            "found": scanner.controls(units, patterns, mapper)}


def route(match: dict) -> str:
    return match["source_key"].split(":")[0]


def first_per_identifier(found: list[dict]) -> list[dict]:
    first: dict[tuple, dict] = {}
    for c in sorted(found, key=lambda c: (c["record_id"], c["identifier"], c["source_key"],
                                          c["unit_id"])):
        if route(c) in ROUTES:
            first.setdefault((c["record_id"], c["identifier"]), c)
    return list(first.values())


def candidates(found: list[dict], side_rows: dict[str, list[str]]) -> list[dict]:
    chosen = first_per_identifier(found)
    rows = c1.control_rows(chosen, [], side_rows)
    for row, c in zip(rows, chosen):
        row["identifier_kind"], row["identifier_type"] = c["kind"], c["type"]
    ids = [r["row_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise ScreenError("two candidates share a row id")
    return sorted(rows, key=lambda r: r["row_id"])


def claim_queue(claim_record_ids: list[str], records: list[str]) -> list[dict]:
    wanted = set(records)
    by_record: dict[str, list[str]] = {}
    for cid in claim_record_ids:
        rec = cid.rsplit(":", 1)[0]
        if rec in wanted:
            by_record.setdefault(rec, []).append(cid)
    return [{"record_id": r, "claim_record_ids": sorted(c)} for r, c in sorted(by_record.items())]


def order(row_ids: list[str]) -> list[str]:
    return cv.order(row_ids, SEND_SEED)


def classify(first: dict | None, second: dict | None) -> str:
    for r in (first, second):
        if r is None or r.get("state") not in ("accepted", "failed"):
            raise ScreenError("a judge's request has no final answer")
    if "failed" in (first["state"], second["state"]):
        return "failed_twice"
    marks = {cv.mark_of(first), cv.mark_of(second)}
    if marks == {"valid"}:
        return "eligible"
    if marks == {"invalid"}:
        return "invalid"
    if "cannot_mark" in marks:
        return "cannot_mark"
    return "disputed"


def draw(eligible: list[dict]) -> list[dict]:
    pool = sorted(eligible, key=lambda r: r["row_id"])
    random.Random(DRAW_SEED).shuffle(pool)
    taken, per = [], {}
    for c in pool:
        if len(taken) == MAXIMUM:
            break
        if per.get(c["record_id"], 0) < PER_RECORD:
            taken.append(c)
            per[c["record_id"]] = per.get(c["record_id"], 0) + 1
    return taken
