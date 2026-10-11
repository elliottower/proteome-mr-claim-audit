# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""The mechanical cut of supplements of the release-resolution follow-up (PREREG.md, §Study
design, What the models read; frozen, https://osf.io/2s479):

    A supplement is given whole where it renders to text under 200,000 characters; a larger
    one, or a workbook of more than 20 sheets, is cut mechanically: every sheet or table name,
    the header rows, and every row that holds a dictionary term (Paper 1's term rule), an
    accession pattern or a release pattern, with its header.

Applied to every readable supplement file of the retrieval (one converted file of
scripts/retrieve_sources.py, route R2). Nothing is read for content beyond the rule.

Rows. A row is one line of the converted text. A sheet name is a line `## sheet <name>` that
the converter writes for each sheet of a workbook; a table name is a line that begins with a
table label (`Table`, `Supplementary Table`, `Supplemental Table`, `eTable`, with a number or
`S` and a number). The header row of a sheet is its first non-empty row after the sheet name; of
a CSV or TSV file, its first line; of any other file, the first line of each run of consecutive
lines that hold a tab (a table the converter wrote cell by cell). Lines outside such a run have
no header.

Terms. Paper 1's term rule (scripts/manual_coding_passages_v3.py, sealed: `dictionary_terms`
and `matches`, unchanged) over every row of Paper 1's dictionary; the accession and release
patterns of reference/c1_scanner_patterns_v2.json (accessions in any case). `TermMatcher`
gives the same answer as `matches` applied to every term, computed with one combined pattern
per kind of term (tests/test_cut_supplements.py checks the two agree).

A kept row is preceded by its header when the header is not the line just kept. Kept lines
are in file order; nothing is added or changed.
"""

import csv
import json
import re

import manual_coding_passages_v3 as passages

WHOLE_BELOW = 200_000
SHEET_LIMIT = 20
SHEET = re.compile(r"^## sheet ")
TABLE_NAME = re.compile(r"^\s*(?:supplementa(?:ry|l)\s+)?e?table\s+s?\d+", re.I)
TABULAR = ("XLSX", "XLS", "CSV", "TSV")
YEAR = re.compile(r"(?<![0-9])(?:19|20)\d{2}(?![0-9])")


class CutError(Exception):
    """A supplement entry lacks its text or type."""


class TermMatcher:
    """Whether a line holds any dictionary term (Paper 1's term rule), accession or release."""

    def __init__(self, dictionary: list[dict], patterns: dict):
        terms = list(dict.fromkeys(t for row in dictionary
                                   for t in passages.dictionary_terms(row)))
        plain = sorted({passages.normalize(t) for f, t in terms
                        if f not in ("sample_size", "source_citation")}, key=len, reverse=True)
        sizes = sorted({t for f, t in terms if f == "sample_size"}, key=len, reverse=True)
        self.plain = re.compile("(?<![0-9a-z])(?:" + "|".join(map(re.escape, plain))
                                + ")(?![0-9a-z])") if plain else None
        self.sizes = re.compile("(?<![0-9])(?:" + "|".join(map(re.escape, sizes))
                                + ")(?![0-9])") if sizes else None
        self.citations: dict[str, list[str]] = {}
        for f, t in terms:
            if f == "source_citation":
                surname, year = t.split("|")
                self.citations.setdefault(year, []).append(surname)
        self.patterns = [re.compile(p["pattern"]) for p in patterns["accessions"]] + [
            re.compile(p["pattern"]) for p in patterns["releases"]]

    def term(self, line: str) -> bool:
        norm = passages.normalize(line)
        if self.plain is not None and self.plain.search(norm):
            return True
        if self.sizes is not None and self.sizes.search(passages.GROUPING.sub("", norm)):
            return True
        for year in set(YEAR.findall(norm)):
            for surname in self.citations.get(year, ()):
                if passages.bounded(surname).search(norm):
                    return True
        return False

    def __call__(self, line: str) -> bool:
        return self.term(line) or any(p.search(line) for p in self.patterns)


def must_cut(entry: dict) -> bool:
    return len(entry["text"]) >= WHOLE_BELOW or entry.get("sheets", 0) > SHEET_LIMIT


def headers(lines: list[str], kind: str) -> list[int | None]:
    """For each line, the index of its header row, or None."""
    out: list[int | None] = []
    if kind in ("CSV", "TSV"):
        return [0 if i else None for i in range(len(lines))]
    header = None
    awaiting = False
    for i, line in enumerate(lines):
        if kind in ("XLSX", "XLS"):
            if SHEET.match(line):
                header, awaiting = None, True
                out.append(None)
                continue
            if awaiting and line.strip():
                header, awaiting = i, False
                out.append(None)
                continue
            out.append(header)
            continue
        if "\t" in line:
            if i == 0 or "\t" not in lines[i - 1]:
                header = i
                out.append(None)
                continue
            out.append(header)
        else:
            header = None
            out.append(None)
    return out


def cut(entry: dict, matcher: TermMatcher) -> dict:
    """The text a model reads of one supplement file, and counts."""
    if entry.get("text") is None or "type" not in entry:
        raise CutError(f"{entry.get('name')}: no text or type")
    text = entry["text"]
    if not must_cut(entry):
        return {"cut": False, "text": text, "characters_before": len(text),
                "characters_after": len(text), "lines_kept": None}
    lines = text.split("\n")
    head = headers(lines, entry["type"])
    is_header = {h for h in head if h is not None}
    if entry["type"] in ("CSV", "TSV") and lines:
        is_header.add(0)
    keep: list[int] = []
    for i, line in enumerate(lines):
        name = bool(SHEET.match(line) or TABLE_NAME.match(line))
        if name or i in is_header or (line.strip() and matcher(line)):
            if head[i] is not None and (not keep or keep[-1] != head[i]):
                keep.append(head[i])
            keep.append(i)
    kept = "\n".join(lines[i] for i in keep)
    return {"cut": True, "text": kept, "characters_before": len(text),
            "characters_after": len(kept), "lines_kept": len(keep), "lines": len(lines)}


def load_matcher(dictionary_path, patterns_path) -> TermMatcher:
    with open(dictionary_path, newline="") as fh:
        dictionary = list(csv.DictReader(fh))
    return TermMatcher(dictionary, json.loads(open(patterns_path).read()))
