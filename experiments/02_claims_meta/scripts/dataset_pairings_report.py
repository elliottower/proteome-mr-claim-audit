# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.13.5"]
# ///
"""How many pairs of dictionary releases the registered relation rules can classify.

For every two rows on the same side of the dataset dictionary, each named by its own row name
(so each maps `unique`), `dataset_relations.compare_side` gives `overlapping_participant_source`
(shared component), `disjoint` (both compositions complete, nothing shared, no possible-overlap
pair such as AGES_REYKJAVIK with DECODE_COHORT) or `unclear`. A row
compared with itself is not counted. This describes the dictionary only; no claim data is read.

Usage: uv run scripts/dataset_pairings_report.py --label after
       [--dictionary <csv> --components <csv>]   (defaults: the committed files)
Writes outputs/resource_counts/dataset_pairings_<label>.json.
"""

import argparse
import collections
import datetime
import hashlib
import itertools
import json
import pathlib

from dataset_relations import (COMPONENTS, DICTIONARY, EXP, compare_side, load_rows, map_name,
                               possibly_overlapping)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--dictionary", type=pathlib.Path, default=DICTIONARY)
    ap.add_argument("--components", type=pathlib.Path, default=COMPONENTS)
    a = ap.parse_args()
    rows = load_rows(a.dictionary, a.components)
    out: dict = {"label": a.label,
                 "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
                 "dictionary": str(a.dictionary), "dictionary_sha256": sha256(a.dictionary),
                 "components": str(a.components), "components_sha256": sha256(a.components),
                 "sides": {}}
    for side in ("pqtl", "outcome"):
        side_rows = [r for r in rows if r.side == side]
        maps = {r.name: map_name(r.name, side, rows) for r in side_rows}
        bad = [n for n, m in maps.items() if m.state != "unique"]
        if bad:
            raise ValueError(f"row names that do not map uniquely: {bad}")
        rel = collections.Counter()
        unclear_pairs = []
        for x, y in itertools.combinations(sorted(maps), 2):
            r = compare_side([maps[x]], [maps[y]])
            rel[r] += 1
            if r == "unclear":
                unclear_pairs.append([x, y])
        out["sides"][side] = {
            "rows": len(side_rows),
            "rows_complete": sum(r.complete for r in side_rows),
            "rows_incomplete": sorted(r.name for r in side_rows if not r.complete),
            "row_pairs": sum(rel.values()),
            "relations": dict(rel),
        }
    # pQTL row x outcome row: shared participants between a pQTL source and an outcome GWAS.
    pq = [r for r in rows if r.side == "pqtl"]
    oc = [r for r in rows if r.side == "outcome"]
    cross = collections.Counter()
    for p, o in itertools.product(pq, oc):
        if p.components & o.components:
            cross["shared_component"] += 1
        elif p.complete and o.complete and not possibly_overlapping(p.components, o.components):
            cross["disjoint"] += 1
        else:
            cross["unclear"] += 1
    out["pqtl_by_outcome"] = dict(cross)
    dest = EXP / "outputs" / "resource_counts" / f"dataset_pairings_{a.label}.json"
    if dest.exists():
        raise FileExistsError(f"{dest} exists; archive it before rerunning")
    dest.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
