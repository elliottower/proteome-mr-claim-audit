# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Second containment calibration (PREREG.log, 2026-10-13): the evidence unit of
scripts/calibrate_containment.py (sealed, unchanged and imported) extended by the row's
normalized non-numeric cell texts (calibrate_containment.cell_texts), so two rows that differ in
any text as written are two units. Counts only; no model is called and no text of a source is
written (a lost unit is reported by a hash and by the kind of its text).

Cuts of a file the registered threshold cuts (a file it does not cut is read whole):
- `registered`: the frozen selection;
- `narrow_k1`: the adopted cut, the narrow keep list with the k = 1 table rule;
- `k1_rowtext`: the narrow keep list, and of the other rows of the frozen selection every row
  whose extended unit is new in its table (the k = 1 rule with the row text in its signature).

For the adopted cut: the registered units it does not retain, per file, as units, rows and
characters, and the kinds of their text: for a tabular row, each non-numeric cell is classed by
its column header (KINDS, first match; `other` when none matches, `no_header` without one); a
line outside a table is `prose`.
"""

import hashlib
import re

import calibrate_containment as cn
import calibrate_cut as cc
import calibrate_dedup as cd
import calibrate_keeplist as ck
import calibrate_keeplist_v2 as k2
import cut_supplements as cs

VARIANTS = ("registered", "narrow_k1", "k1_rowtext")
KINDS = (("phenotype_or_trait", re.compile(r"(?i)phenotype|trait|outcome|disease|endpoint|"
                                           r"diagnos|icd|phecode|condition")),
         ("ancestry_or_population", re.compile(r"(?i)ancestr|population|ethnic|race|pop\b")),
         ("role", re.compile(r"(?i)role|stage|discovery|replication|validation|sensitivity|"
                             r"analysis|model|method")),
         ("cohort_or_study", re.compile(r"(?i)cohort|study|consortium|biobank|dataset|source|"
                                        r"sample|panel|platform|subcohort")),
         ("sex", re.compile(r"(?i)\bsex\b|gender|female|male")),
         ("protein_or_gene", re.compile(r"(?i)protein|gene|target|assay|aptamer|olink|soma|"
                                        r"uniprot|symbol")),
         ("variant_or_snp", re.compile(r"(?i)snp|rsid|variant|allele|chrom|position|locus")))


def kind_of(header_cell: str) -> str:
    for name, pattern in KINDS:
        if pattern.search(header_cell):
            return name
    return "other"


def lost_kinds(line: str, header: str | None) -> set[str]:
    if "\t" not in line:
        return {"prose"}
    if header is None:
        return {"no_header"}
    out = set()
    for name, value in zip(header.split("\t"), line.split("\t")):
        if value.strip() and not cn.NUMERIC.match(value):
            out.add(kind_of(name))
    return out or {"numeric_only"}


def measure_file(entry: dict, matcher, termsets, patterns, mapper, groups: k2.Groups) -> dict:
    text, kind = entry["text"], entry["type"]
    out = {"name": entry["name"], "characters_whole": len(text),
           "frozen_cut": cs.must_cut(entry)}
    if not out["frozen_cut"]:
        for v in VARIANTS:
            out[v] = {"characters": len(text), "units": 0}
        out["lost"] = {"units": 0, "rows": 0, "characters": 0, "kinds": {}, "unit_hashes": []}
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
    context = {t: hashlib.sha256(lines[t].encode()).hexdigest()[:16] if t >= 0 else "file"
               for t in set(table)}

    def unit(i):
        ids, terms, counts = info[i]
        if not (ids or terms or counts):
            return None
        return (table[i], context[table[i]], tuple(sorted(terms)), tuple(sorted(ids)),
                tuple(sorted(counts)), tuple(sorted(cn.cell_texts(lines[i], ids))))

    matched = {i: groups(l) for i, l in enumerate(lines) if l.strip()}
    listed = {i for i, g in matched.items() if k2.narrow(g)}
    id_rows = sorted(set(selected) | {i for i, v in info.items() if v[0]})
    k1 = cd.variant(id_rows, info, table, structural, 1, set(table))
    rowtext, seen = [], set()
    for i in sorted(set(selected) | listed):
        u = unit(i)
        if i in structural or i in listed or (u is not None and u not in seen):
            rowtext.append(i)
            if u is not None:
                seen.add(u)
    keeps = {"registered": selected, "narrow_k1": sorted(set(k1) | listed),
             "k1_rowtext": rowtext}
    units = {v: {unit(i) for i in keep} - {None} for v, keep in keeps.items()}
    for v, keep in keeps.items():
        out[v] = {"characters": cn.pack(lines, keep, table, structural), "units": len(units[v])}
    missing = units["registered"] - units["narrow_k1"]
    kept_adopted = set(keeps["narrow_k1"])
    lost_rows = [i for i in selected if i not in kept_adopted and unit(i) in missing]
    kinds: dict[str, int] = {}
    for i in lost_rows:
        header = lines[table[i]] if table[i] >= 0 and table[i] != i else None
        for k in lost_kinds(lines[i], header):
            kinds[k] = kinds.get(k, 0) + 1
    out["lost"] = {"units": len(missing),
                   "rows": len(lost_rows),
                   "characters": sum(len(lines[i]) + 1 for i in lost_rows),
                   "kinds": kinds,
                   "rowtext_variant_lost_units": len(units["registered"] - units["k1_rowtext"]),
                   "unit_hashes": sorted(hashlib.sha256(repr(u).encode()).hexdigest()[:16]
                                         for u in missing)[:200]}
    out["chunks"] = {}
    for v, keep in keeps.items():
        kept = set(keep) | {table[i] for i in keep if table[i] >= 0}
        removed = [i for i in range(len(lines)) if i not in kept and lines[i].strip()]
        out["chunks"][v] = ck.chunk_lengths(lines, removed, table, 10_000)
    return out


def aggregate(files_by_record: dict[str, list[dict]]) -> dict:
    out = {"lost_by_paper": {}, "variants": {}}
    pooled = {"units": 0, "rows": 0, "characters": 0, "kinds": {}, "rowtext_variant_lost_units": 0}
    for rec, files in sorted(files_by_record.items()):
        p = {"units": 0, "rows": 0, "characters": 0, "kinds": {}, "rowtext_variant_lost_units": 0}
        for f in files:
            for k in ("units", "rows", "characters"):
                p[k] += f["lost"][k]
            p["rowtext_variant_lost_units"] += f["lost"].get("rowtext_variant_lost_units", 0)
            for kind, n in f["lost"]["kinds"].items():
                p["kinds"][kind] = p["kinds"].get(kind, 0) + n
        if p["units"]:
            out["lost_by_paper"][rec] = p
        for k in ("units", "rows", "characters", "rowtext_variant_lost_units"):
            pooled[k] += p[k]
        for kind, n in p["kinds"].items():
            pooled["kinds"][kind] = pooled["kinds"].get(kind, 0) + n
    out["lost_pooled"] = pooled
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
