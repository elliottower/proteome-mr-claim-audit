# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Second version of the keep-list calibration (scripts/calibrate_keeplist.py, sealed, unchanged
and imported): it adds the narrow keep list and measures the cost driver of the full one.
Counts only; no model is called and no text of a source is written.

- Narrow keep list: a line is kept when it matches a pattern of
  reference/release_language_patterns.json or a C1 identifier pattern; dictionary names and
  aliases are not on it, so their rows are left to the k = 1 table rule.
- Full keep list: as in the first version (those patterns, C1 identifiers, dictionary names and
  aliases).
- Groups: each pattern of the file, `dictionary_names`, `c1_identifiers`. For the lines the full
  keep list adds to the table rule, the characters of the lines each group matches (`any`, a line
  counted under every group it matches) and of the lines only that group matches (`only`).

Per cut file: characters read under the table rule alone, with the narrow list and with the full
list (header once per table), the retention measures of calibrate_dedup for each, the group
breakdown, and the chunk lengths of the text the narrow variant removes.
"""

import json
import re

import calibrate_cut as cc
import calibrate_dedup as cd
import calibrate_keeplist as ck
import cut_supplements as cs

VARIANTS = ("table_rule", "narrow_keep_list", "full_keep_list")


class Groups:
    """Which keep-list groups a line matches."""

    def __init__(self, path: str, names: cc.NameMatcher, patterns: dict):
        spec = json.loads(open(path).read())
        self.patterns = [(p["name"], re.compile(p["pattern"])) for p in spec["patterns"]]
        self.names = names
        self.c1 = patterns

    def __call__(self, line: str) -> set[str]:
        found = {name for name, p in self.patterns if p.search(line)}
        if cc.identifiers(line, self.c1):
            found.add("c1_identifiers")
        if self.names(line):
            found.add("dictionary_names")
        return found


def narrow(groups: set[str]) -> bool:
    return bool(groups - {"dictionary_names"})


def measure_file(entry: dict, matcher, termsets, patterns, mapper, groups: Groups) -> dict:
    text, kind = entry["text"], entry["type"]
    out = {"name": entry["name"], "type": kind, "characters_whole": len(text),
           "frozen_cut": cs.must_cut(entry), "groups_any": {}, "groups_only": {}}
    lines = text.split("\n")
    if not out["frozen_cut"]:
        base = cd.measure_file(entry, matcher, termsets, patterns, mapper)
        out["whole"] = base["whole"]
        for name in VARIANTS:
            out[name] = {"characters": len(text),
                         **{f"{m}_kept": base["whole"][m] for m in base["whole"]}}
        out["chunks"] = {str(s): [] for s in ck.SIZES}
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
    matched = {i: groups(l) for i, l in enumerate(lines) if l.strip()}
    keeps = {"table_rule": k1,
             "narrow_keep_list": sorted(set(k1) | {i for i, g in matched.items() if narrow(g)}),
             "full_keep_list": sorted(set(k1) | {i for i, g in matched.items() if g})}
    whole = cd.measures(range(len(lines)), info, table, decisive)
    out["whole"] = {k: len(v) for k, v in whole.items()}
    for name, keep in keeps.items():
        got = cd.measures(keep, info, table, decisive)
        out[name] = {"characters": len(ck.render(lines, keep, table, structural)),
                     **{f"{m}_kept": len(got[m] & whole[m]) for m in whole}}
    added = set(keeps["full_keep_list"]) - set(k1)
    for i in added:
        g, length = matched[i], len(lines[i]) + 1
        for name in g:
            out["groups_any"][name] = out["groups_any"].get(name, 0) + length
        if len(g) == 1:
            name = next(iter(g))
            out["groups_only"][name] = out["groups_only"].get(name, 0) + length
    kept = set(keeps["narrow_keep_list"])
    kept |= {table[i] for i in kept if table[i] >= 0}
    removed = [i for i in range(len(lines)) if i not in kept and lines[i].strip()]
    out["chunks"] = {str(s): ck.chunk_lengths(lines, removed, table, s) for s in ck.SIZES}
    return out


def aggregate(files_by_record: dict[str, list[dict]]) -> dict:
    out = {}
    for name in VARIANTS:
        pooled = dict.fromkeys(("characters_whole", "characters_read", "a1_whole", "a1_kept",
                                "a2_whole", "a2_kept", "b_whole", "b_kept", "c_whole",
                                "c_kept"), 0)
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
                                                if c["a1_kept"] < c["a1_whole"]),
                     "papers_losing_b": sorted(r for r, c in per_paper.items()
                                               if c["b_kept"] < c["b_whole"])}
    for key in ("groups_any", "groups_only"):
        total: dict[str, int] = {}
        for fs in files_by_record.values():
            for f in fs:
                for g, n in f[key].items():
                    total[g] = total.get(g, 0) + n
        out[key] = dict(sorted(total.items(), key=lambda x: -x[1]))
    out["chunks"] = {}
    for size in ck.SIZES:
        lengths = [n for fs in files_by_record.values() for f in fs for n in f["chunks"][str(size)]]
        out["chunks"][str(size)] = {"chunks": len(lengths), "characters": sum(lengths),
                                    "mean_characters": sum(lengths) / len(lengths)
                                    if lengths else 0,
                                    "papers": sum(any(f["chunks"][str(size)] for f in fs)
                                                  for fs in files_by_record.values())}
    return out
