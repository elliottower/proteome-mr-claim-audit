# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Calibration of the supplement cut threshold of the release-resolution follow-up, after
retrieval and before any model request (PREREG.log, 2026-10-11). Mechanical counts only; no
model is called and no text of a source is written.

The cut of a file does not depend on the threshold: scripts/cut_supplements.py (sealed,
unchanged) keeps the same lines whenever it cuts. The threshold decides only which files are
cut: a file is cut at (characters T, sheets S) when its text has at least T characters or its
workbook more than S sheets. So each file is cut once (`measure_file`, which applies the frozen
cut whatever the file's size) and every threshold is read from those measurements.

Per file, in the whole text and in the cut text:
- (a) hard identifiers: the distinct matches of the frozen C1 scanner patterns
  (reference/c1_scanner_patterns_v2.json: accessions in their canonical case, numbered releases,
  DOIs without terminal punctuation, PMIDs), as strings; retained when the cut holds it;
- (b) dictionary-name lines: lines holding a name or an alias of a row of Paper 1's dictionary
  (Paper 1's term rule, those two fields); retained when the cut keeps the line;
- (c) count lines: lines holding a sample-size or case and control count pattern (COUNT);
  retained when the cut keeps the line;
- characters of the whole and of the cut.

Thresholds: the registered one, (200,000 characters, 20 sheets), and lower ones with the sheet
limit scaled in proportion, S = max(1, ceil(20 T / 200,000)). For each: pooled and per-paper
retention of (a), (b) and (c), the papers losing a hard identifier, and the cost estimate by line
(scripts/estimate_cost_v2.py, sealed, unchanged).
"""

import collections
import math
import re

import cut_supplements as cs
import manual_coding_passages_v3 as passages
import source_scanner_v2 as scanner

REGISTERED = (200_000, 20)
GRID = (200_000, 100_000, 50_000, 25_000, 10_000)
COUNT = re.compile(r"(?i)\b(?:n\s*=\s*\d[\d,\s]*\d|\d[\d,\s]*\d\s*(?:cases|controls|participants|"
                   r"individuals|subjects|samples)|(?:cases|controls)\s*[:=]?\s*\d[\d,\s]*\d)")


def sheets_for(characters: int) -> int:
    return max(1, math.ceil(REGISTERED[1] * characters / REGISTERED[0]))


class NameMatcher:
    """Lines holding a dictionary name or alias (Paper 1's term rule, those fields only)."""

    def __init__(self, dictionary: list[dict]):
        terms = sorted({passages.normalize(t) for row in dictionary
                        for f, t in passages.dictionary_terms(row) if f in ("name", "aliases")},
                       key=len, reverse=True)
        self.pattern = re.compile("(?<![0-9a-z])(?:" + "|".join(map(re.escape, terms))
                                  + ")(?![0-9a-z])")

    def __call__(self, line: str) -> bool:
        return bool(self.pattern.search(passages.normalize(line)))


def identifiers(text: str, patterns: dict) -> set[str]:
    found = set()
    terminal = patterns["doi_terminal_characters"]
    for p in patterns["accessions"]:
        for m in re.finditer(p["pattern"], text):
            found.add(scanner.canonical(m.group(0), p["canonical"]))
    for p in patterns["releases"]:
        for m in re.finditer(p["pattern"], text):
            found.add(p["row"].format(n=int(m.group(1))))
    for p in patterns["source_identifiers"]:
        for m in re.finditer(p["pattern"], text):
            found.add(f"doi:{m.group(0).rstrip(terminal).lower()}" if p["type"] == "doi"
                      else f"pmid:{m.group(1)}")
    return found


def line_counts(lines: list[str], test) -> collections.Counter:
    return collections.Counter(line for line in lines if line.strip() and test(line))


def measure_file(entry: dict, matcher: cs.TermMatcher, names: NameMatcher,
                 patterns: dict) -> dict:
    whole = entry["text"]
    forced = cs.cut({**entry, "sheets": cs.SHEET_LIMIT + 1}, matcher)["text"]
    whole_lines, cut_lines = whole.split("\n"), forced.split("\n")
    ids_whole, ids_cut = identifiers(whole, patterns), identifiers(forced, patterns)
    name_whole, name_cut = line_counts(whole_lines, names), line_counts(cut_lines, names)
    count_whole = line_counts(whole_lines, COUNT.search)
    count_cut = line_counts(cut_lines, COUNT.search)
    return {"name": entry["name"], "sha256": entry["sha256"], "type": entry["type"],
            "sheets": entry.get("sheets", 0), "characters_whole": len(whole),
            "characters_cut": len(forced),
            "identifiers_whole": sorted(ids_whole),
            "identifiers_lost_when_cut": sorted(ids_whole - ids_cut),
            "name_lines_whole": sum(name_whole.values()),
            "name_lines_kept_when_cut": sum(min(n, name_cut[l]) for l, n in name_whole.items()),
            "count_lines_whole": sum(count_whole.values()),
            "count_lines_kept_when_cut": sum(min(n, count_cut[l])
                                             for l, n in count_whole.items())}


def is_cut(f: dict, characters: int, sheets: int) -> bool:
    return f["characters_whole"] >= characters or f["sheets"] > sheets


def share(kept: int, of: int) -> float | None:
    return kept / of if of else None


def at_threshold(files_by_record: dict[str, list[dict]], characters: int) -> dict:
    sheets = sheets_for(characters) if characters != REGISTERED[0] else REGISTERED[1]
    pooled = collections.Counter()
    per_paper, losing = {}, {}
    for rec, files in sorted(files_by_record.items()):
        c = collections.Counter()
        lost = set()
        for f in files:
            cut = is_cut(f, characters, sheets)
            c["files"] += 1
            c["files_cut"] += cut
            c["characters_read"] += f["characters_cut"] if cut else f["characters_whole"]
            c["identifiers_whole"] += len(f["identifiers_whole"])
            c["identifiers_kept"] += len(f["identifiers_whole"]) - (
                len(f["identifiers_lost_when_cut"]) if cut else 0)
            c["name_lines_whole"] += f["name_lines_whole"]
            c["name_lines_kept"] += f["name_lines_kept_when_cut"] if cut else f["name_lines_whole"]
            c["count_lines_whole"] += f["count_lines_whole"]
            c["count_lines_kept"] += (f["count_lines_kept_when_cut"] if cut
                                      else f["count_lines_whole"])
            if cut:
                lost |= set(f["identifiers_lost_when_cut"])
        pooled.update(c)
        per_paper[rec] = dict(c)
        if lost:
            losing[rec] = sorted(lost)
    return {"characters": characters, "sheets": sheets, "pooled": dict(pooled),
            "retention": {"hard_identifiers": share(pooled["identifiers_kept"],
                                                    pooled["identifiers_whole"]),
                          "dictionary_name_lines": share(pooled["name_lines_kept"],
                                                         pooled["name_lines_whole"]),
                          "count_lines": share(pooled["count_lines_kept"],
                                               pooled["count_lines_whole"])},
            "papers_losing_a_hard_identifier": losing, "per_paper": per_paper}


def cuts_at(files_by_record: dict[str, list[dict]], characters: int, sheets: int
            ) -> dict[str, dict]:
    """The cut summaries scripts/estimate_cost_v2.py reads, at one threshold."""
    return {rec: {"files": [{"cut": is_cut(f, characters, sheets),
                             "characters_before": f["characters_whole"],
                             "characters_after": f["characters_cut"]
                             if is_cut(f, characters, sheets) else f["characters_whole"]}
                            for f in files]}
            for rec, files in files_by_record.items()}
