# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Calibration of the amended cut after the review of the draft amendment (PREREG.log,
2026-10-13): exact containment of evidence units, an identifier rule by full signature, headers
repeated per request, and the hypergeometric bound of a chunk-sampled C2. Counts only; no model
is called and no text of a source is written (table context enters a unit as a hash).

Evidence unit of a line: (file sha256, table, sha256 of the table's header or name line, the
line's dictionary terms, its identifier values, its count values), for a line holding any of the
last three. A cut retains the units of the lines it keeps. Containment holds when every unit the
registered cut retains is retained by the amended cut.

Variants of a file the registered threshold cuts (a file it does not cut is read whole):
- `registered`: the frozen selection (scripts/cut_supplements.py via calibrate_dedup).
- `narrow_k1`: the k = 1 table rule with the narrow keep list (calibrate_keeplist_v2).
- `amended`: sheet and table names and headers; every line matching a release-language pattern
  of the keep list (not the C1 identifier patterns, whose rows this rule governs, nor the
  dictionary names); every row with an identifier that maps to no dictionary row; a row with mapped identifiers when its signature is
  new in its table; any other row of the frozen selection when its evidence unit is new in its
  table. The signature of an identifier row: the dictionary rows its identifiers map to, the
  set of its non-numeric cell texts (normalized; for a line without tabs, the line with numbers
  and identifiers removed), and its count definition (the count values with the header of the
  column each stands in, for columns whose header names a count). Role, phenotype, ancestry,
  subcohort, target linkage and conflict-bearing attributes have no column of their own that can
  be read mechanically across supplements; they enter the signature only through the cell texts,
  so two rows that differ in any of them as written differ in the signature.

Characters: the kept lines with each table's header once, packed in file order into requests of
at most 400,000 characters, the header repeated at the head of a request whose first row belongs
to that table (`pack`). The repeats are counted in characters and never as retained units.

C2: the removed lines of each variant cut into chunks (calibrate_keeplist.chunk_lengths); the
exact hypergeometric one-sided 95% upper bound on the number of chunks holding a miss, for n
sampled and 0 or 1 misses (`hypergeometric_upper`).
"""

import hashlib
import math
import re

import calibrate_cut as cc
import calibrate_dedup as cd
import calibrate_keeplist as ck
import calibrate_keeplist_v2 as k2
import cut_supplements as cs
import manual_coding_passages_v3 as passages

LIMIT = 400_000
COUNT_COLUMN = re.compile(r"(?i)^(?:n|n[_ ]?(?:cases?|controls?|total|eff(?:ective)?)|cases?|"
                          r"controls?|sample[_ ]?size|number of (?:cases|controls|participants|"
                          r"samples|individuals)|neff)$")
NUMERIC = re.compile(r"^[\s\d.,eE+\-−–×x^()%<>=]*$")
VARIANTS = ("registered", "narrow_k1", "amended")


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def cell_texts(line: str, ids: frozenset[str]) -> frozenset[str]:
    if "\t" in line:
        cells = line.split("\t")
    else:
        stripped = line
        for i in ids:
            stripped = stripped.replace(i, " ")
        cells = [re.sub(r"\d[\d.,]*", " ", stripped)]
    return frozenset(passages.normalize(c) for c in cells
                     if c.strip() and not NUMERIC.match(c))


def count_definition(line: str, header: str | None) -> frozenset:
    out = set(("pattern", v) for v in cd.count_values(line))
    if header is not None and "\t" in line:
        for name, value in zip(header.split("\t"), line.split("\t")):
            if COUNT_COLUMN.match(name.strip()) and value.strip():
                out.add((passages.normalize(name), value.strip()))
    return frozenset(out)


def pack(lines: list[str], keep: list[int], table: list[int], structural: set[int]) -> int:
    """Characters of the kept lines in requests of at most LIMIT, each table's header shown once
    in file order and again at the head of a request whose first row belongs to that table."""
    order, shown = [], set()
    for i in sorted(set(keep)):
        t = table[i]
        if i not in structural and t >= 0 and t not in shown and t != i:
            order.append(t)
            shown.add(t)
        if i in structural:
            shown.add(i)
        order.append(i)
    total, current = 0, 0
    for i in order:
        length = len(lines[i]) + 1
        if current and current + length > LIMIT:
            total += current
            current = 0
            t = table[i]
            if t >= 0 and t != i:
                current += len(lines[t]) + 1
        current += length
    return total + current


def hypergeometric_upper(misses: int, population: int, sample: int, level: float = 0.05) -> int:
    """The largest number K of affected chunks in the population with P(X <= misses) >= level,
    X the affected chunks in a simple random sample without replacement."""
    if sample == 0:
        return population

    def log_comb(a: int, b: int) -> float:
        if b < 0 or b > a:
            return -math.inf
        return math.lgamma(a + 1) - math.lgamma(b + 1) - math.lgamma(a - b + 1)

    def cdf(k: int) -> float:
        total = log_comb(population, sample)
        return sum(math.exp(log_comb(k, x) + log_comb(population - k, sample - x) - total)
                   for x in range(misses + 1))

    lo, hi = misses, population
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if cdf(mid) >= level:
            lo = mid
        else:
            hi = mid - 1
    return lo


def mapped(identifier: str, mapper) -> set[str]:
    """The dictionary rows an identifier maps to (empty when it maps to none)."""
    if identifier.startswith(("doi:", "pmid:")):
        return set(mapper.exact.get(identifier, set()))
    if identifier in mapper.rows:
        return {identifier}
    return set(mapper.accession(identifier))


def measure_file(entry: dict, matcher, termsets, patterns, mapper, groups: k2.Groups) -> dict:
    text, kind = entry["text"], entry["type"]
    out = {"name": entry["name"], "sha256": entry["sha256"], "characters_whole": len(text),
           "frozen_cut": cs.must_cut(entry)}
    if not out["frozen_cut"]:
        for v in VARIANTS:
            out[v] = {"characters": len(text), "units": None}
        out["lost_units"] = {v: [] for v in VARIANTS}
        out["chunks"] = {v: [] for v in VARIANTS}
        return out
    lines = text.split("\n")
    info = {i: (frozenset(cc.identifiers(l, patterns)), termsets(l), cd.count_values(l))
            for i, l in enumerate(lines) if l.strip()}
    for i in range(len(lines)):
        info.setdefault(i, (frozenset(), frozenset(), frozenset()))
    table = cd.tables(lines, kind)
    head = cs.headers(lines, kind)
    heads = {h for h in head if h is not None} | ({0} if kind in ("CSV", "TSV") and lines else set())
    selected = cd.frozen_selection(lines, kind, matcher)
    structural = {i for i in selected if cs.SHEET.match(lines[i]) or cs.TABLE_NAME.match(lines[i])
                  or i in heads}
    context = {t: digest(lines[t]) if t >= 0 else "file" for t in set(table)}

    def unit(i):
        ids, terms, counts = info[i]
        if not (ids or terms or counts):
            return None
        return (entry["sha256"][:16], table[i], context[table[i]], tuple(sorted(terms)),
                tuple(sorted(ids)), tuple(sorted(counts)))

    matched = {i: groups(l) for i, l in enumerate(lines) if l.strip()}
    listed = {i for i, g in matched.items() if k2.narrow(g)}
    language = {i for i, g in matched.items() if g - {"dictionary_names", "c1_identifiers"}}
    id_rows = sorted(set(selected) | {i for i, v in info.items() if v[0]})
    k1 = cd.variant(id_rows, info, table, structural, 1, set(table))
    selected_set = set(selected)
    amended, seen_units, seen_sigs = [], set(), set()
    for i in sorted(set(selected) | language | {i for i, v in info.items() if v[0]}):
        ids = info[i][0]
        u = unit(i)
        keep = i in structural or i in language
        if not keep and ids:
            rows = [mapped(x, mapper) for x in ids]
            if any(not r for r in rows):
                keep = True
            else:
                header = lines[table[i]] if table[i] >= 0 and table[i] != i else None
                sig = (table[i], frozenset().union(*rows), cell_texts(lines[i], ids),
                       count_definition(lines[i], header))
                if sig not in seen_sigs:
                    keep = True
                    seen_sigs.add(sig)
        if not keep and u is not None and u not in seen_units and i in selected_set:
            keep = True
        if keep:
            amended.append(i)
            if u is not None:
                seen_units.add(u)
    keeps = {"registered": selected,
             "narrow_k1": sorted(set(k1) | listed),
             "amended": amended}
    units = {v: {unit(i) for i in keep} - {None} for v, keep in keeps.items()}
    out["lost_units"] = {v: sorted([list(map(str, u)) for u in units["registered"] - units[v]])
                         for v in VARIANTS}
    for v, keep in keeps.items():
        out[v] = {"characters": pack(lines, keep, table, structural), "units": len(units[v])}
    out["chunks"] = {}
    for v, keep in keeps.items():
        kept = set(keep) | {table[i] for i in keep if table[i] >= 0}
        removed = [i for i in range(len(lines)) if i not in kept and lines[i].strip()]
        out["chunks"][v] = ck.chunk_lengths(lines, removed, table, 10_000)
    return out


def aggregate(files_by_record: dict[str, list[dict]]) -> dict:
    """Per variant: containment pooled and per paper (the lost units), characters, the cut
    summaries the estimate reads, and the chunk population of the removed text."""
    out = {}
    for v in VARIANTS:
        lost_by_paper = {rec: [u for f in files for u in f["lost_units"][v]]
                         for rec, files in sorted(files_by_record.items())}
        lengths = [n for fs in files_by_record.values() for f in fs for n in f["chunks"][v]]
        out[v] = {
            "containment_holds": not any(lost_by_paper.values()),
            "lost_units": sum(len(u) for u in lost_by_paper.values()),
            "papers_losing_units": sorted(r for r, u in lost_by_paper.items() if u),
            "lost_units_by_paper": {r: u for r, u in lost_by_paper.items() if u},
            "registered_units": sum(f["registered"]["units"] or 0
                                    for fs in files_by_record.values() for f in fs),
            "units": sum(f[v]["units"] or 0 for fs in files_by_record.values() for f in fs),
            "characters_read": sum(f[v]["characters"] for fs in files_by_record.values()
                                   for f in fs),
            "cuts": {rec: {"files": [{"cut": f["frozen_cut"],
                                      "characters_before": f["characters_whole"],
                                      "characters_after": f[v]["characters"]} for f in files]}
                     for rec, files in files_by_record.items()},
            "chunks": {"chunks": len(lengths), "characters": sum(lengths),
                       "mean_characters": sum(lengths) / len(lengths) if lengths else 0}}
    return out


def c2_bounds(chunks: int, sample: int = 400) -> dict:
    out = {"population": chunks, "sample": min(sample, chunks)}
    for misses in (0, 1):
        k = hypergeometric_upper(misses, chunks, out["sample"])
        out[f"upper_affected_chunks_{misses}_misses"] = k
        out[f"upper_rate_{misses}_misses"] = k / chunks if chunks else None
    return out
