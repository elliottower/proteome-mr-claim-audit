# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""The C1 positive control of the release-resolution follow-up (PREREG.md, §Study design, C1
and Manifest controls; frozen, https://osf.io/2s479). No model is called and nothing is read by
hand. The scanner, its patterns and its draw are the frozen ones (scripts/source_scanner_v2.py,
reference/c1_scanner_patterns_v2.json, imported unchanged); this module builds the scanner's
input, turns the drawn controls into packet rows and builds the manifest packets.

Units (`units`). Every eligible retrieved source of a record (routes R1, R2, R3, every readable
file, whole as retrieved; not the cut), one unit per sentence of a prose line and one per table
row:
- a line with a tab is a table row; its unit is the row, and the header line of its table is
  kept in `header` (calibrate_dedup.tables); a rendered JATS table row (`[Table ...] h: v | ...`)
  is one unit;
- any other line is divided into sentences (coding_packets.SENTENCE), each a unit;
- `section_title` is the last heading before the line: a rendered JATS section title
  (`## <title>`), else a line that is one of the heading words of HEADING;
- `in_reference_list` is true for the lines after a reference-list heading (REFERENCES) in a
  file of routes R2 or R3; the rendered JATS body holds no reference list;
- `source_key` is `<route>:<n>:<sha256 of the text, 16 hex digits>`, n the source's place among
  the record's readable sources; `unit_id` is `<source_key>:<line>:<sentence>`.

Scan and draw. `source_scanner_v2.controls` over the units (a match outside a reference list,
mapping to exactly one dictionary row, its unit holding a context term), then
`source_scanner_v2.draw`: one control per record, identifier and expected row, shuffled by the
frozen seed, up to the frozen maximum (150). If fewer than the frozen minimum (50) are drawn, the
plan extends the scan to every retrievable paper of Paper 1's corpus outside the scope before
coding (`extension_needed`).

Control rows (`control_rows`). A drawn control from a record of the scope becomes one row of
that record's packets: `side` the expected row's side; `name_as_written` the identifier as the
source writes it; `outcomes_as_written` (outcome side) the outcomes as written of the record's
outcome-side study rows; `candidates` every dictionary row of the side; `row_id` from
coding_queue.row_id over (record, side, identifier, `control`). Rows of a packet are ordered by
`row_id`, so control rows stand among study rows and are not marked.

Manifest controls (`manifest_packets`). For each dictionary row that the pinned accession table
(reference/accession_releases.csv, built from the resources' manifests) maps a non-batch
identifier to, the first such identifier in sorted order; one packet per such identifier, whose
one file is the table's line for it (resource and identifier, tab-separated under their header)
and whose one row is a `not stated` row of the dictionary row's side with every row of that side
as candidates. They are reported apart and never enter the source-scanned denominator.
"""

import csv
import hashlib
import re

import calibrate_dedup as cd
import coding_packets as cp
import coding_queue as q
import source_scanner_v2 as scanner

HEADING = re.compile(r"(?i)^\s*(?:\d+(?:\.\d+)*\.?\s+)?(abstract|introduction|background|methods?|"
                     r"materials and methods|results|discussion|conclusions?|data availability|"
                     r"code availability|availability of data(?: and materials)?|"
                     r"data and code availability|acknowledg(?:e)?ments?|references|"
                     r"supplementary (?:methods|note|information|material))\s*:?\s*$")
REFERENCES = re.compile(r"(?i)^\s*(references|bibliography|literature cited|reference list)\s*$")
TABULAR = ("XLSX", "XLS", "CSV", "TSV")


def source_key(route: str, n: int, text: str) -> str:
    return f"{route}:{n}:{hashlib.sha256(text.encode()).hexdigest()[:16]}"


def units(record_id: str, sources: list[dict]) -> list[dict]:
    """The scanner's units of one record's readable retrieved sources."""
    out = []
    readable = [s for s in sources if s.get("text")]
    for n, s in enumerate(readable, 1):
        key = source_key(s["route"], n, s["text"])
        lines = s["text"].split("\n")
        kind = s.get("type", "")
        table = cd.tables(lines, kind if kind in TABULAR else "")
        title, in_refs = None, False
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            if line.startswith("## ") and s["route"] == "R1":
                title = line[3:].strip()
                continue
            if HEADING.match(line):
                title = line.strip().rstrip(":")
            if REFERENCES.match(line) and s["route"] in ("R2", "R3"):
                in_refs = True
                continue
            base = {"record_id": record_id, "source_key": key, "section_title": title,
                    "sec_type": None, "in_reference_list": in_refs}
            if "\t" in line or (line.startswith("[") and "] " in line and " | " in line):
                t = table[i]
                out.append(base | {"unit_id": f"{key}:{i}:0", "text": line,
                                   "header": lines[t] if t >= 0 and t != i else None})
                continue
            for k, sentence in enumerate(cp.SENTENCE.split(line)):
                out.append(base | {"unit_id": f"{key}:{i}:{k}", "text": sentence,
                                   "header": None})
    return out


def scan(all_units: list[dict], patterns: dict, mapper: scanner.Mapper) -> dict:
    found = scanner.controls(all_units, patterns, mapper)
    drawn = scanner.draw(found, patterns)
    return {"found": found, "drawn": drawn,
            "extension_needed": len(drawn) < patterns["draw"]["minimum"]}


def control_rows(drawn: list[dict], queue_rows: list[dict],
                 side_rows: dict[str, list[str]]) -> list[dict]:
    outcomes: dict[str, list[str]] = {}
    for r in queue_rows:
        if r["side"] == "outcome":
            for o in r["outcomes_as_written"]:
                outcomes.setdefault(r["record_id"], [])
                if o not in outcomes[r["record_id"]]:
                    outcomes[r["record_id"]].append(o)
    out = []
    for c in drawn:
        rec, side = c["record_id"], c["side"]
        out.append({"row_id": q.row_id(rec, side, c["identifier"], "control"), "record_id": rec,
                    "side": side, "name_as_written": c["identifier"],
                    "outcomes_as_written": outcomes.get(rec, []) if side == "outcome" else [],
                    "candidates": side_rows[side], "kind": "control",
                    "expected_row": c["expected_row"], "control_source_key": c["source_key"],
                    "control_unit_id": c["unit_id"]})
    return out


def merge(study: list[dict], controls: list[dict]) -> list[dict]:
    return sorted(study + controls, key=lambda r: r["row_id"])


def manifest_packets(table: list[dict], side_of: dict[str, str],
                     side_rows: dict[str, list[str]], accessions: cp.Accessions) -> list[dict]:
    first: dict[str, dict] = {}
    for r in sorted(table, key=lambda r: r["release_identifier"]):
        if r["identifier_type"] != "opengwas_batch" and r["dictionary_row"] not in first:
            first[r["dictionary_row"]] = r
    out = []
    for row_name, r in sorted(first.items()):
        side = side_of[row_name]
        rid = "manifest_" + hashlib.sha256(r["release_identifier"].encode()).hexdigest()[:12]
        rows = [{"row_id": q.row_id(rid, side, "not_stated", ""), "record_id": rid,
                 "side": side, "name_as_written": q.SHOWN_NOT_STATED, "outcomes_as_written": [],
                 "candidates": side_rows[side], "kind": "manifest",
                 "expected_row": row_name}]
        text = f"resource\trelease_identifier\n{r['resource']}\t{r['release_identifier']}"
        p = cp.packet(rid, "", rows, [{"file_id": "supplement_1", "kind": "supplement",
                                       "text": text}], accessions)
        out.append({"packet": p, "expected_row": row_name, "identifier": r["release_identifier"]})
    return out


def read_table(path) -> list[dict]:
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))
