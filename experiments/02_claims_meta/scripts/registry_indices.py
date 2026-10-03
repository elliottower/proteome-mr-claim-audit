# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""The descriptive registry indices that scripts/build_registry.py does not compute. No model is
called. Wilson 95% intervals are naive descriptive intervals; an estimate on fewer than 20 pairs
is labelled imprecise.

Papers per pair. The distribution of study families per registry pair.

Participant-overlap share (H2b). The classes, bounds, verdict and bootstrap replicates of
scripts/build_registry.py (`pair_overlap`, `tables`), repeated here with the registry indices:
`known_overlapping` (every comparison of every two of the pair's families on both sides
`overlapping`), `known_not_overlapping` (any `disjoint`), `unresolved` (otherwise); lower bound
= known_overlapping / all, upper bound = (known_overlapping + unresolved) / all, complete-case =
known_overlapping / (known_overlapping + known_not_overlapping). The verdict is read on the
observed bounds; the pair bootstrap is a resampling-stability display.

Within-family discordance. Family–pair records with direction `mixed`, split by whether the
discordant records differ in `claim_scope`: `scopes_differ` when no verified `raises` record of
the family on the pair has the `claim_scope` of any of its verified `lowers` records, else
`scope_shared`.

Contradiction sources. For each contradicting pair, the families on the `raises` side
(`raises`, `raises_with_nonsignificant`) are compared with the families on the `lowers` side,
field by field, each side read as the union over its families:

    pqtl, outcome   release identity of the two sides' dataset names (scripts/
                    dataset_relations.py `release_identity`): `differ` (not_identical), `same`
                    (identical), `not_stated` (a side with no stated name), `undetermined`
                    (otherwise, and whenever a family of either side has unclear attribution)
    platform        GPT-6.1 Sol's `platform` values on the families' claim records of the pair,
                    folded (lower case, non-alphanumerics removed): `not_stated` when a side
                    states none, `differ` when the two sets are not equal, else `same`
    ancestry        the same, on `ancestry`
    any             `differ` when any field is `differ`

Landscape. Eligible families per first-public year and per registered period (2019–2022,
2023–2025); registry proteins by number of families, pairs and claim records; pairs and claim
records per therapeutic area (scripts/therapeutic_areas.py; an outcome counts in each of its
areas, those that do not count toward a hub included, and under
`no_therapeutic_area` when it has none), with the pairs by the rule that gave their areas; claim
records per wording class.

Bounds on distinct pairs over `extraction_failed` families: the lower bound treats each as
contributing no new pair; the upper bound adds, for each, the median number of distinct pairs
of the eligible families whose extraction succeeded.

Usage: uv run scripts/registry_indices.py --claims <registry_claims.jsonl>
           --tags <claim_tags.jsonl> --families-meta <families_meta.json>
           --ontology-edges <ontology_edges.csv> --out <dir>
"""

import argparse
import collections
import datetime
import json
import pathlib
import statistics
from collections.abc import Callable, Mapping

from build_registry import (DIRECTIONAL, N_BOOT, SEED, FamilyPair, Registry, RegistryClaim, build,
                            effective, estimates, h2_verdict, pair_bootstrap, wilson)
from claim_tags import ClaimTags, load_tags
from dataset_relations import NameMapping, Row, load_rows, release_identity
from ontology_graph import load_graph
from therapeutic_areas import NO_AREA, all_areas_of, load_areas
from verify_claims import compact

PERIODS = ((2019, 2022), (2023, 2025))
FIELDS = ("pqtl", "outcome", "platform", "ancestry")
IMPRECISE_BELOW = 20


def papers_per_pair(registry: Registry) -> dict[str, int]:
    return {str(k): v for k, v in sorted(collections.Counter(
        len(f) for f in registry.values()).items())}


def participant_overlap(registry: Registry, n_boot: int, seed: int) -> dict:
    """The H2b table of scripts/build_registry.py: the same classes, the same bootstrap
    replicates as H2, and the same three-way verdict rule."""
    est = estimates(registry)
    boot = pair_bootstrap(est, n_boot, seed)
    n = est["h2_multi_family_pairs"]
    known, unresolved = est["h2b_known_overlapping"], est["h2b_unresolved"]
    return {"multi_family_pairs": n, "known_overlapping": known,
            "known_not_overlapping": est["h2b_known_not_overlapping"],
            "unresolved": unresolved, "lower": est["h2b_lower"], "upper": est["h2b_upper"],
            "complete_case": est["h2b_complete_case"],
            "wilson_descriptive": {"lower": wilson(known, n),
                                   "upper": wilson(known + unresolved, n)},
            "pair_bootstrap": {"lower": boot.get("h2b_lower"), "upper": boot.get("h2b_upper"),
                               "replicates": n_boot, "seed": seed},
            "h2b_verdict": h2_verdict(est, "h2b"),
            "imprecise_under_20_pairs": n < IMPRECISE_BELOW}


def by_family_pair(claims: list[RegistryClaim]) -> dict[tuple[str, str], dict[str, list]]:
    out: dict[tuple[str, str], dict[str, list]] = collections.defaultdict(
        lambda: collections.defaultdict(list))
    for c in claims:
        out[(c.protein_id, c.outcome_id)][c.family_id].append(c)
    return out


def within_family_discordance(registry: Registry, claims: list[RegistryClaim]) -> dict:
    records = by_family_pair(claims)
    counts: collections.Counter = collections.Counter()
    for pair, fams in registry.items():
        for fam, fp in fams.items():
            if fp.direction != "mixed":
                continue
            up = {c.claim_scope for c in records[pair][fam] if effective(c) == "raises"}
            down = {c.claim_scope for c in records[pair][fam] if effective(c) == "lowers"}
            counts["scopes_differ" if up.isdisjoint(down) else "scope_shared"] += 1
    return {"mixed_family_pair_records": sum(counts.values()),
            "scopes_differ": counts["scopes_differ"], "scope_shared": counts["scope_shared"]}


def _names(fps: list[FamilyPair], side: str) -> list[NameMapping]:
    seen: dict[str, NameMapping] = {}
    for fp in fps:
        for m in getattr(fp, side):
            seen[m.written] = m
    return [seen[k] for k in sorted(seen)]


def _dataset_field(up: list[NameMapping], down: list[NameMapping],
                   attribution_clear: bool = True) -> str:
    stated_up = [m for m in up if m.state != "not_stated"]
    stated_down = [m for m in down if m.state != "not_stated"]
    if not stated_up or not stated_down:
        return "not_stated"
    if not attribution_clear:
        return "undetermined"
    return {"identical": "same", "not_identical": "differ",
            "undetermined": "undetermined"}[release_identity(stated_up, stated_down)]


def _stated(values: set[str]) -> set[str]:
    return {compact(v) for v in values if v != "not_stated"} - {""}


def _text_field(up: set[str], down: set[str]) -> str:
    up, down = _stated(up), _stated(down)
    if not up or not down:
        return "not_stated"
    return "same" if up == down else "differ"


def contradiction_sources(registry: Registry, claims: list[RegistryClaim],
                          tags: Mapping[str, ClaimTags]) -> dict:
    records = by_family_pair(claims)
    table = {f: collections.Counter() for f in (*FIELDS, "any")}
    n = 0
    for pair, fams in registry.items():
        sides = {d: [fp for fp in fams.values() if DIRECTIONAL.get(fp.direction) == d]
                 for d in ("raises", "lowers")}
        if not sides["raises"] or not sides["lowers"]:
            continue
        n += 1

        def values(side: str, attr: str) -> set[str]:
            out: set[str] = set()
            for fp in sides[side]:
                for c in records[pair][fp.family_id]:
                    v = getattr(tags[c.claim_record_id], attr)
                    out |= set(v) if isinstance(v, tuple) else {v}
            return out

        clear = all(fp.attribution_clear for fps in sides.values() for fp in fps)
        result = {
            "pqtl": _dataset_field(_names(sides["raises"], "pqtl"),
                                   _names(sides["lowers"], "pqtl"), clear),
            "outcome": _dataset_field(_names(sides["raises"], "outcome"),
                                      _names(sides["lowers"], "outcome"), clear),
            "platform": _text_field(values("raises", "platform"), values("lowers", "platform")),
            "ancestry": _text_field(values("raises", "ancestry"), values("lowers", "ancestry")),
        }
        for f in FIELDS:
            table[f][result[f]] += 1
        states = set(result.values())
        table["any"]["differ" if "differ" in states else
                     "not_stated" if states == {"not_stated"} else "no_stated_difference"] += 1
    out: dict = {"contradicting_pairs": n, "imprecise_under_20_pairs": n < IMPRECISE_BELOW}
    for f, counter in table.items():
        out[f] = {**dict(sorted(counter.items())),
                  "share_differ": counter["differ"] / n if n else None,
                  "share_not_stated": counter["not_stated"] / n if n else None,
                  "wilson_descriptive_differ": wilson(counter["differ"], n)}
    return out


def landscape(claims: list[RegistryClaim], tags: Mapping[str, ClaimTags],
              families_meta: Mapping[str, dict],
              areas_of_outcome: Callable[[str], tuple[frozenset[str], str]]) -> dict:
    """`areas_of_outcome` gives an outcome's therapeutic areas and the rule that gave them
    (`therapeutic_areas.all_areas_of`)."""
    years = collections.Counter(int(m["first_public"]["value"][:4])
                                for m in families_meta.values())
    proteins: dict[str, dict[str, set]] = collections.defaultdict(
        lambda: {"families": set(), "pairs": set(), "claims": set()})
    for c in claims:
        p = proteins[c.protein_id]
        p["families"].add(c.family_id)
        p["pairs"].add(c.outcome_id)
        p["claims"].add(c.claim_record_id)
    ranked = sorted(({"protein_id": k, "families": len(v["families"]), "pairs": len(v["pairs"]),
                      "claim_records": len(v["claims"])} for k, v in proteins.items()),
                    key=lambda r: (-r["families"], -r["pairs"], r["protein_id"]))
    pairs = {(c.protein_id, c.outcome_id) for c in claims}
    def areas(outcome: str) -> list[str]:
        return sorted(areas_of_outcome(outcome)[0]) or [NO_AREA]

    pair_area = collections.Counter(a for _, o in pairs for a in areas(o))
    claim_area = collections.Counter(a for c in claims for a in areas(c.outcome_id))
    return {
        "eligible_families": len(families_meta),
        "families_per_year": {str(y): n for y, n in sorted(years.items())},
        "families_per_period": {f"{a}-{b}": sum(n for y, n in years.items() if a <= y <= b)
                                for a, b in PERIODS},
        "proteins": len(ranked), "most_claimed_proteins": ranked,
        "pairs_per_therapeutic_area": dict(sorted(pair_area.items())),
        "claim_records_per_therapeutic_area": dict(sorted(claim_area.items())),
        "pairs_by_area_rule": dict(sorted(collections.Counter(
            areas_of_outcome(o)[1] for _, o in pairs).items())),
        "claim_records_per_wording_class": dict(sorted(collections.Counter(
            tags[c.claim_record_id].wording_class for c in claims).items())),
    }


def extraction_failed_bounds(registry: Registry, families_meta: Mapping[str, dict]) -> dict:
    failed = sum(m["extraction"] == "extraction_failed" for m in families_meta.values())
    per_family = [m["n_pairs"] for m in families_meta.values() if m["extraction"] == "ok"]
    median = statistics.median(per_family) if per_family else None
    return {"distinct_pairs": len(registry), "extraction_failed_families": failed,
            "median_pairs_per_extracted_eligible_family": median,
            "distinct_pairs_lower": len(registry),
            "distinct_pairs_upper": len(registry) + failed * median if median is not None
            else None}


def indices(claims: list[RegistryClaim], tags: Mapping[str, ClaimTags], rows: list[Row],
            families_meta: Mapping[str, dict],
            areas_of_outcome: Callable[[str], tuple[frozenset[str], str]],
            n_boot: int, seed: int) -> dict:
    registry = build(claims, rows)
    return {"papers_per_pair": papers_per_pair(registry),
            "participant_overlap_share": participant_overlap(registry, n_boot, seed),
            "within_family_discordance": within_family_discordance(registry, claims),
            "contradiction_sources": contradiction_sources(registry, claims, tags),
            "landscape": landscape(claims, tags, families_meta, areas_of_outcome),
            "distinct_pair_bounds": extraction_failed_bounds(registry, families_meta)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims", type=pathlib.Path, required=True)
    ap.add_argument("--tags", type=pathlib.Path, required=True)
    ap.add_argument("--families-meta", type=pathlib.Path, required=True)
    ap.add_argument("--ontology-edges", type=pathlib.Path, required=True)
    ap.add_argument("--window", default="confirmatory", choices=["confirmatory", "update"])
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    claims = [RegistryClaim.model_validate_json(l) for l in a.claims.read_text().splitlines()
              if l.strip()]
    meta = {f: m for f, m in json.loads(a.families_meta.read_text()).items()
            if m["window"] == a.window}
    graph, areas = load_graph(a.ontology_edges), load_areas()
    result = {"claims_file": str(a.claims), "tags_file": str(a.tags), "window": a.window,
              "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
              **indices(claims, load_tags(a.tags), load_rows(), meta,
                        lambda o: all_areas_of(o, areas, graph), N_BOOT, SEED)}
    a.out.mkdir(parents=True, exist_ok=True)
    target = a.out / "registry_indices.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; archive it before rerunning")
    target.write_text(json.dumps(result, indent=1))
    print(json.dumps({k: v for k, v in result.items() if k != "landscape"}, indent=1))


if __name__ == "__main__":
    main()
