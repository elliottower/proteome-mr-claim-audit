# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Calibration of a replacement cut and of a chunk-sampled C2 for the release-resolution
follow-up, after retrieval and before any model request (PREREG.log, 2026-10-11). Counts only;
no model is called and no text of a source is written.

The frozen threshold decides which files are cut (scripts/cut_supplements.py, sealed,
unchanged); a file it does not cut is read whole. In a file it cuts, the candidate keeps:

- the k = 1 table rule of scripts/calibrate_dedup.py (sealed, unchanged: sheet and table names,
  header rows, every row with an identifier not yet kept from its table, the first row per
  signature, and any row with a new pair of term set and count value), over all tables;
- with `keep list`: every line that matches reference/release_language_patterns.json, holds a
  dictionary name or alias (calibrate_cut.NameMatcher), or matches a C1 identifier pattern
  (calibrate_cut.identifiers), whatever the table rule decides;
- shown with each table's header once, before the table's first kept row, never repeated
  (`render`).

The removed text of a file is its lines not kept. For C2 it is cut into chunks of at most SIZE
characters, in file order, a row never split, the table header carried at the head of each chunk
of that table (`chunk_lengths`).

Measures per file: characters whole and read under the candidate with and without the keep list,
characters the keep list adds, the retention measures of calibrate_dedup (a1, a2, b, c), and the
chunk counts and lengths of the removed text at each SIZE.
"""

import json
import math
import re

import calibrate_cut as cc
import calibrate_dedup as cd
import cut_supplements as cs

SIZES = (10_000, 20_000)
NS = (100, 200, 400)


class KeepList:
    def __init__(self, path: str, names: cc.NameMatcher, patterns: dict):
        spec = json.loads(open(path).read())
        self.patterns = [re.compile(p["pattern"]) for p in spec["patterns"]]
        self.names = names
        self.c1 = patterns

    def __call__(self, line: str) -> bool:
        return (any(p.search(line) for p in self.patterns) or self.names(line)
                or bool(cc.identifiers(line, self.c1)))


def render(lines: list[str], keep: list[int], table: list[int], structural: set[int]) -> str:
    """The kept lines in file order, each table's header shown once before its first kept row."""
    out, shown = [], set()
    head_of = {t: t for t in set(table) if t >= 0}
    for i in sorted(set(keep)):
        t = table[i]
        if i in structural:
            shown.add(i)
        elif t in head_of and t not in shown and t != i:
            out.append(t)
            shown.add(t)
        out.append(i)
    return "\n".join(lines[i] for i in out)


def chunk_lengths(lines: list[str], removed: list[int], table: list[int], size: int) -> list[int]:
    """Lengths of the chunks of the removed lines: at most `size` characters, a line never
    split (a longer line is a chunk of its own), the table's header at the head of each chunk."""
    out, current, current_table = [], 0, None
    for i in removed:
        t = table[i]
        header = len(lines[t]) + 1 if t >= 0 and t != i else 0
        length = len(lines[i]) + 1
        if current and (t != current_table or current + length > size):
            out.append(current)
            current = 0
        if not current:
            current = header
            current_table = t
        current += length
    if current:
        out.append(current)
    return out


def measure_file(entry: dict, matcher, termsets, patterns, mapper, keeplist: KeepList) -> dict:
    text, kind = entry["text"], entry["type"]
    out = {"name": entry["name"], "type": kind, "characters_whole": len(text),
           "frozen_cut": cs.must_cut(entry)}
    lines = text.split("\n")
    if not out["frozen_cut"]:
        base = cd.measure_file(entry, matcher, termsets, patterns, mapper)
        out["whole"] = base["whole"]
        for name in ("table_rule", "table_rule_keep_list"):
            out[name] = {"characters": len(text),
                         **{f"{m}_kept": base["whole"][m] for m in base["whole"]}}
        out["keep_list_added_characters"] = 0
        out["removed_characters"] = 0
        out["chunks"] = {str(s): [] for s in SIZES}
        return out
    info = {i: (frozenset(cc.identifiers(l, patterns)), termsets(l), cd.count_values(l))
            for i, l in enumerate(lines) if l.strip()}
    for i in range(len(lines)):
        info.setdefault(i, (frozenset(), frozenset(), frozenset()))
    all_ids = set().union(*(v[0] for v in info.values()))
    decisive = {x for x in all_ids if cd.decisive(x, mapper)}
    table = cd.tables(lines, kind)
    head = cs.headers(lines, kind)
    heads = {h for h in head if h is not None} | ({0} if kind in ("CSV", "TSV") and lines else set())
    selected = cd.frozen_selection(lines, kind, matcher)
    structural = {i for i in selected if cs.SHEET.match(lines[i]) or cs.TABLE_NAME.match(lines[i])
                  or i in heads}
    id_rows = sorted(set(selected) | {i for i, v in info.items() if v[0]})
    k1 = cd.variant(id_rows, info, table, structural, 1, set(table))
    listed = [i for i, l in enumerate(lines) if l.strip() and keeplist(l)]
    with_list = sorted(set(k1) | set(listed))
    whole = cd.measures(range(len(lines)), info, table, decisive)
    out["whole"] = {k: len(v) for k, v in whole.items()}
    for name, keep in (("table_rule", k1), ("table_rule_keep_list", with_list)):
        got = cd.measures(keep, info, table, decisive)
        out[name] = {"characters": len(render(lines, keep, table, structural)),
                     **{f"{m}_kept": len(got[m] & whole[m]) for m in whole}}
    out["keep_list_added_characters"] = (out["table_rule_keep_list"]["characters"]
                                         - out["table_rule"]["characters"])
    kept = set(with_list) | {table[i] for i in with_list if table[i] >= 0}
    removed = [i for i in range(len(lines)) if i not in kept and lines[i].strip()]
    out["removed_characters"] = sum(len(lines[i]) + 1 for i in removed)
    out["chunks"] = {str(s): chunk_lengths(lines, removed, table, s) for s in SIZES}
    return out


def upper_bound(misses: int, n: int, level: float = 0.05) -> float:
    """The exact one-sided upper confidence bound on a proportion (Clopper–Pearson): the largest
    p with P(X <= misses | n, p) >= level."""
    def cdf(p: float) -> float:
        return sum(math.comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(misses + 1))
    lo, hi = 0.0, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if cdf(mid) >= level:
            lo = mid
        else:
            hi = mid
    return lo


def aggregate(files_by_record: dict[str, list[dict]]) -> dict:
    """Pooled and per-paper counts of each candidate, the cut summaries the estimate reads, and
    the chunk population of the removed text at each size."""
    out = {}
    for name in ("table_rule", "table_rule_keep_list"):
        pooled = {k: 0 for k in ("characters_whole", "characters_read", "a1_whole", "a1_kept",
                                 "a2_whole", "a2_kept", "b_whole", "b_kept", "c_whole",
                                 "c_kept")}
        per_paper, cuts = {}, {}
        for rec, files in sorted(files_by_record.items()):
            c = dict.fromkeys(pooled, 0)
            for f in files:
                c["characters_whole"] += f["characters_whole"]
                c["characters_read"] += f[name]["characters"]
                for m in ("a1", "a2", "b", "c"):
                    c[f"{m}_whole"] += f["whole"][m]
                    c[f"{m}_kept"] += f[name][f"{m}_kept"]
            for k in pooled:
                pooled[k] += c[k]
            per_paper[rec] = c
            cuts[rec] = {"files": [{"cut": f["frozen_cut"],
                                    "characters_before": f["characters_whole"],
                                    "characters_after": f[name]["characters"]} for f in files]}
        out[name] = {"pooled": pooled, "per_paper": per_paper, "cuts": cuts,
                     "retention": {m: pooled[f"{m}_kept"] / pooled[f"{m}_whole"]
                                   if pooled[f"{m}_whole"] else None
                                   for m in ("a1", "a2", "b", "c")},
                     "papers_losing_a1": sorted(r for r, c in per_paper.items()
                                                if c["a1_kept"] < c["a1_whole"])}
    out["keep_list_added_characters"] = sum(f["keep_list_added_characters"]
                                            for fs in files_by_record.values() for f in fs)
    out["removed_characters"] = sum(f["removed_characters"]
                                    for fs in files_by_record.values() for f in fs)
    out["chunks"] = {}
    for size in SIZES:
        lengths = [n for fs in files_by_record.values() for f in fs for n in f["chunks"][str(size)]]
        out["chunks"][str(size)] = {"chunks": len(lengths), "characters": sum(lengths),
                                    "mean_characters": sum(lengths) / len(lengths)
                                    if lengths else 0,
                                    "papers": sum(any(f["chunks"][str(size)] for f in fs)
                                                  for fs in files_by_record.values())}
    return out


def c2_lines(chunks: dict, prompt: int, model_cost) -> dict:
    """Cost of the checker reading n chunks, and the one-sided 95% upper bounds on the share of
    chunks holding a decisive statement the cut removed, for 0 and 1 misses."""
    out = {}
    for size, pop in chunks.items():
        for n in NS:
            m = min(n, pop["chunks"])
            out[f"size{size}_n{n}"] = {
                "chunk_characters": int(size), "chunks_in_population": pop["chunks"],
                "sample": m, **model_cost("gpt-6.1-sol", round(pop["mean_characters"] * m), m,
                                          prompt),
                "upper_bound_0_misses": upper_bound(0, m) if m else None,
                "upper_bound_1_miss": upper_bound(1, m) if m else None}
    return out
