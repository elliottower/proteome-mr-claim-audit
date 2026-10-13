# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Third containment calibration (PREREG.log, 2026-10-13): the evidence unit is the whole row,
every cell numeric and non-numeric, normalized (manual_coding_passages_v3.normalize per cell),
with its table and a hash of the table's header or name. Two rows of one table are one unit only
when every cell is equal after normalization. Counts only; no model is called and no text of a
source is written.

Cuts of a file the registered threshold cuts (a file it does not cut is read whole):
- `registered`: the frozen selection;
- `full_rows`: the narrow keep list, the structural lines, and of the other rows of the frozen
  selection the first row of each whole-row unit in its table, so only rows equal in every cell
  to a kept row of the same table are dropped.
"""

import hashlib

import calibrate_containment as cn
import calibrate_cut as cc
import calibrate_dedup as cd
import calibrate_keeplist as ck
import calibrate_keeplist_v2 as k2
import cut_supplements as cs
import manual_coding_passages_v3 as passages

VARIANTS = ("registered", "full_rows")


def row_unit(line: str, table: int, context: str) -> tuple:
    return (table, context, tuple(passages.normalize(c) for c in line.split("\t")))


def measure_file(entry: dict, matcher, termsets, patterns, mapper, groups: k2.Groups) -> dict:
    text, kind = entry["text"], entry["type"]
    out = {"name": entry["name"], "characters_whole": len(text),
           "frozen_cut": cs.must_cut(entry)}
    if not out["frozen_cut"]:
        for v in VARIANTS:
            out[v] = {"characters": len(text), "units": 0}
        out["lost_units"] = 0
        out["chunks"] = {v: [] for v in VARIANTS}
        return out
    lines = text.split("\n")
    table = cd.tables(lines, kind)
    head = cs.headers(lines, kind)
    heads = {h for h in head if h is not None} | ({0} if kind in ("CSV", "TSV") and lines else set())
    selected = cd.frozen_selection(lines, kind, matcher)
    structural = {i for i in selected if cs.SHEET.match(lines[i]) or cs.TABLE_NAME.match(lines[i])
                  or i in heads}
    context = {t: hashlib.sha256(lines[t].encode()).hexdigest()[:16] if t >= 0 else "file"
               for t in set(table)}

    def unit(i):
        if i in structural or not lines[i].strip():
            return None
        return row_unit(lines[i], table[i], context[table[i]])

    listed = {i for i, l in enumerate(lines) if l.strip() and k2.narrow(groups(l))}
    full, seen = [], set()
    for i in sorted(set(selected) | listed):
        u = unit(i)
        if i in structural or i in listed or (u is not None and u not in seen):
            full.append(i)
            if u is not None:
                seen.add(u)
    keeps = {"registered": sorted(selected), "full_rows": full}
    units = {v: {unit(i) for i in keep} - {None} for v, keep in keeps.items()}
    for v, keep in keeps.items():
        out[v] = {"characters": cn.pack(lines, keep, table, structural), "units": len(units[v])}
    out["lost_units"] = len(units["registered"] - units["full_rows"])
    out["chunks"] = {}
    for v, keep in keeps.items():
        kept = set(keep) | {table[i] for i in keep if table[i] >= 0}
        removed = [i for i in range(len(lines)) if i not in kept and lines[i].strip()]
        out["chunks"][v] = ck.chunk_lengths(lines, removed, table, 10_000)
    return out


def aggregate(files_by_record: dict[str, list[dict]]) -> dict:
    out = {"lost_by_paper": {}, "variants": {}}
    for rec, files in sorted(files_by_record.items()):
        lost = sum(f["lost_units"] for f in files)
        if lost:
            out["lost_by_paper"][rec] = lost
    out["lost_units"] = sum(out["lost_by_paper"].values())
    for v in VARIANTS:
        lengths = [n for fs in files_by_record.values() for f in fs for n in f["chunks"][v]]
        out["variants"][v] = {
            "units": sum(f[v]["units"] for fs in files_by_record.values() for f in fs),
            "characters_read": sum(f[v]["characters"] for fs in files_by_record.values()
                                   for f in fs),
            "cuts": {rec: {"files": [{"cut": f["frozen_cut"],
                                      "characters_before": f["characters_whole"],
                                      "characters_after": f[v]["characters"]} for f in files]}
                     for rec, files in files_by_record.items()},
            "chunks": {"chunks": len(lengths), "characters": sum(lengths),
                       "mean_characters": sum(lengths) / len(lengths) if lengths else 0}}
    return out
