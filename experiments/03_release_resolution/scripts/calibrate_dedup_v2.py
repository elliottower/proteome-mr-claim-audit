# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Second version of the aggregation of scripts/calibrate_dedup.py (sealed, unchanged and still
used for every measurement): `aggregate` there raised on a paper with no readable supplement
file, whose per-paper counts are empty. Here every count of such a paper is 0. Nothing else
differs.
"""

import collections

FIELDS = ("characters_whole", "characters_read", "a1_whole", "a1_kept", "a2_whole", "a2_kept",
          "b_whole", "b_kept", "c_whole", "c_kept")


def aggregate(files_by_record: dict[str, list[dict]]) -> dict:
    names = sorted({v for fs in files_by_record.values() for f in fs for v in f["variants"]})
    out = {}
    for name in names:
        pooled = collections.Counter({k: 0 for k in FIELDS})
        per_paper, cuts = {}, {}
        for rec, files in sorted(files_by_record.items()):
            c = collections.Counter({k: 0 for k in FIELDS})
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

