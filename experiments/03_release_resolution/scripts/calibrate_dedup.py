# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Calibration of a change to what the supplement cut keeps in large tables, after retrieval and
before any model request (PREREG.log, 2026-10-11). Counts only; no model is called and no text
of a source is written.

The frozen cut (scripts/cut_supplements.py, sealed, unchanged) applies at its registered
threshold. A file it does not cut is read whole under every variant. In a file it cuts, the
frozen rule selects the sheet and table names, the header rows and every row holding a
dictionary term, an accession or a release (`frozen_selection`, the same selection as `cs.cut`;
the tests check the two give the same text). The candidate rule then keeps, table by table:

- the sheet and table names and the header rows;
- every row holding a hard identifier (a match of the C1 accession, release, DOI or PMID
  patterns, scripts/calibrate_cut.identifiers) of which one is not yet kept from that table;
- of the other selected rows, the first k per signature (the set of dictionary terms the row
  matches and the set of its identifier values), and also any row whose pair of term set and
  count value is new in the table.

A table is the rows under one header (a sheet, a CSV or TSV file, a run of tab-separated lines),
else the lines after one table name, else the file. Variants: k = 1, 3, 10, applied to every
table (`all`) or only to tables of more than LARGE rows (`large`); in a table the rule does not
apply to, the frozen selection is kept. A kept row is preceded by its header when the header is
not the line just kept, as in the frozen cut.

Measures, against the whole file, on distinct values within the file:
- a1: identifiers that can decide a release: accessions and numbered releases that map to a
  dictionary row (scripts/source_scanner_v2.Mapper over the frozen accession table and the
  dictionary), DOIs and PMIDs that are the source identifier of a dictionary row;
- a2: all identifiers;
- b: (table, set of dictionary terms) pairs, for non-empty sets;
- c: (table, set of dictionary terms, count value) triples, a count value being a number in a
  match of calibrate_cut.COUNT, digit grouping removed;
- characters.
"""

import collections
import re

import calibrate_cut as cc
import cut_supplements as cs
import manual_coding_passages_v3 as passages
import source_scanner_v2 as scanner

KS = (1, 3, 10)
LARGE = 1_000
NUMBER = re.compile(r"\d[\d,\s]*\d|\d")


class TermSets:
    """The dictionary terms a line matches (Paper 1's term rule), as a set."""

    def __init__(self, matcher: cs.TermMatcher):
        self.m = matcher

    def __call__(self, line: str) -> frozenset[str]:
        norm = passages.normalize(line)
        found = set()
        if self.m.plain is not None:
            found |= {m.group(0) for m in self.m.plain.finditer(norm)}
        if self.m.sizes is not None:
            found |= {f"n:{m.group(0)}"
                      for m in self.m.sizes.finditer(passages.GROUPING.sub("", norm))}
        for year in set(cs.YEAR.findall(norm)):
            for surname in self.m.citations.get(year, ()):
                if passages.bounded(surname).search(norm):
                    found.add(f"{surname}|{year}")
        return frozenset(found)


def count_values(line: str) -> frozenset[str]:
    return frozenset(re.sub(r"[,\s]", "", n) for m in cc.COUNT.finditer(line)
                     for n in NUMBER.findall(m.group(0)))


def decisive(identifier: str, mapper: scanner.Mapper) -> bool:
    if identifier.startswith(("doi:", "pmid:")):
        return bool(mapper.exact.get(identifier))
    if identifier in mapper.rows:
        return True
    return bool(mapper.accession(identifier))


def frozen_selection(lines: list[str], kind: str, matcher: cs.TermMatcher) -> list[int]:
    head = cs.headers(lines, kind)
    is_header = {h for h in head if h is not None}
    if kind in ("CSV", "TSV") and lines:
        is_header.add(0)
    return [i for i, line in enumerate(lines)
            if cs.SHEET.match(line) or cs.TABLE_NAME.match(line) or i in is_header
            or (line.strip() and matcher(line))]


def tables(lines: list[str], kind: str) -> list[int]:
    """The table of each line: its header's index, else the last table name's, else -1."""
    head = cs.headers(lines, kind)
    headers_of = {h for h in head if h is not None}
    if kind in ("CSV", "TSV") and lines:
        headers_of.add(0)
    out, name = [], -1
    for i, line in enumerate(lines):
        if cs.SHEET.match(line) or cs.TABLE_NAME.match(line):
            name = i
        out.append(head[i] if head[i] is not None else (i if i in headers_of else name))
    return out


def text_of(lines: list[str], keep: list[int], head: list) -> str:
    out = []
    for i in keep:
        if head[i] is not None and (not out or out[-1] != head[i]):
            out.append(head[i])
        out.append(i)
    return "\n".join(lines[i] for i in out)


def variant(selected: list[int], info: dict, table: list[int], structural: set[int],
            k: int, applies: set[int]) -> list[int]:
    keep, seen_ids = [], collections.defaultdict(set)
    per_signature = collections.Counter()
    seen_pairs = collections.defaultdict(set)
    for i in selected:
        t = table[i]
        ids, terms, counts = info[i]
        if i in structural or t not in applies:
            keep.append(i)
            seen_ids[t] |= ids
            continue
        if ids - seen_ids[t]:
            keep.append(i)
            seen_ids[t] |= ids
            continue
        pairs = {(terms, c) for c in counts}
        signature = (t, terms, frozenset(ids))
        if per_signature[signature] < k or pairs - seen_pairs[t]:
            keep.append(i)
            per_signature[signature] += 1
            seen_pairs[t] |= pairs
            seen_ids[t] |= ids
    return keep


def measures(indices, info, table, decisive_ids) -> dict:
    a1, a2, b, c = set(), set(), set(), set()
    for i in indices:
        ids, terms, counts = info[i]
        a2 |= ids
        a1 |= ids & decisive_ids
        if terms:
            b.add((table[i], terms))
        c |= {(table[i], terms, v) for v in counts}
    return {"a1": a1, "a2": a2, "b": b, "c": c}


def measure_file(entry: dict, matcher: cs.TermMatcher, termsets: TermSets, patterns: dict,
                 mapper: scanner.Mapper) -> dict:
    text, kind = entry["text"], entry["type"]
    out = {"name": entry["name"], "type": kind, "characters_whole": len(text),
           "frozen_cut": cs.must_cut(entry)}
    lines = text.split("\n")
    info = {i: (frozenset(cc.identifiers(line, patterns)), termsets(line), count_values(line))
            for i, line in enumerate(lines) if line.strip()}
    for i in range(len(lines)):
        info.setdefault(i, (frozenset(), frozenset(), frozenset()))
    all_ids = set().union(*(v[0] for v in info.values()))
    decisive_ids = {x for x in all_ids if decisive(x, mapper)}
    table = tables(lines, kind)
    whole = measures(range(len(lines)), info, table, decisive_ids)
    out["whole"] = {k: len(v) for k, v in whole.items()}
    head = cs.headers(lines, kind)
    selected = frozen_selection(lines, kind, matcher)
    names = ["frozen"] + [f"k{k}_{scope}" for scope in ("all", "large") for k in KS]
    candidates = {"frozen": selected}
    if out["frozen_cut"]:
        rows = collections.Counter(table)
        structural = {i for i in selected if cs.SHEET.match(lines[i])
                      or cs.TABLE_NAME.match(lines[i]) or i in {h for h in head if h is not None}
                      or (kind in ("CSV", "TSV") and i == 0)}
        id_rows = sorted(set(selected) | {i for i, v in info.items() if v[0]})
        for scope in ("all", "large"):
            applies = set(rows) if scope == "all" else {t for t, n in rows.items() if n > LARGE}
            for k in KS:
                candidates[f"k{k}_{scope}"] = variant(id_rows, info, table, structural, k,
                                                      applies)
    out["variants"] = {}
    for name in names:
        if not out["frozen_cut"]:
            got, chars = whole, len(text)
        else:
            keep = candidates[name]
            got = measures(keep, info, table, decisive_ids)
            chars = len(text_of(lines, keep, head))
        out["variants"][name] = {"characters": chars,
                                 **{f"{m}_kept": len(got[m] & whole[m]) for m in whole}}
    return out


def aggregate(files_by_record: dict[str, list[dict]]) -> dict:
    """Pooled and per-paper retention of each variant, and the cut summaries the estimate reads."""
    names = sorted({v for fs in files_by_record.values() for f in fs for v in f["variants"]})
    out = {}
    for name in names:
        pooled = collections.Counter()
        per_paper = {}
        cuts = {}
        for rec, files in sorted(files_by_record.items()):
            c = collections.Counter()
            summaries = []
            for f in files:
                v = f["variants"][name]
                c["characters_whole"] += f["characters_whole"]
                c["characters_read"] += v["characters"]
                for m in ("a1", "a2", "b", "c"):
                    c[f"{m}_whole"] += f["whole"][m]
                    c[f"{m}_kept"] += v[f"{m}_kept"]
                summaries.append({"cut": f["frozen_cut"],
                                  "characters_before": f["characters_whole"],
                                  "characters_after": v["characters"]})
            pooled.update(c)
            per_paper[rec] = dict(c)
            cuts[rec] = {"files": summaries}
        retention = {m: (pooled[f"{m}_kept"] / pooled[f"{m}_whole"]
                         if pooled[f"{m}_whole"] else None) for m in ("a1", "a2", "b", "c")}
        losing_a1 = sorted(r for r, c in per_paper.items() if c["a1_kept"] < c["a1_whole"])
        out[name] = {"pooled": dict(pooled), "retention": retention,
                     "papers_losing_a1": losing_a1, "per_paper": per_paper, "cuts": cuts}
    return out
