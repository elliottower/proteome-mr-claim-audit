# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Therapeutic areas of canonical outcome identifiers, from the pinned Open Targets 26.09
`disease` file. No model is called, and nothing here reads a claim.

Table. Each row of the `disease` file gives a term (`id`) and its therapeutic areas
(`therapeuticAreas`, a list of term identifiers; a term can have several, and a term that is
itself a therapeutic area lists itself). Identifiers are written PREFIX:N and replaced by their
canonical identifier (the committed collision table; an identifier with several canonical
identifiers gives its areas to each). The committed table `verification/therapeutic_areas.csv`
holds, per canonical outcome identifier, the union of the areas of the `disease` rows that map
to it; `verification/therapeutic_area_names.csv` holds each area's identifier and name.

An outcome that is not in the table (a MONDO term the `disease` file does not carry) takes the
areas of its nearest ancestors in the registered ontology graph that are in the table: the union
over the ancestors at the smallest distance that have any. An outcome with no such ancestor has
no area (`no_therapeutic_area`). Which rule gave the areas is recorded (`direct`,
`nearest_ancestor`, `none`), and `area_assignment` stores, per outcome, whether its areas are the
file's own (`direct`) or `inherited`, the distance to the nearest ancestors that gave them, those
ancestors, and whether several ancestors are equally near.

Areas that do not count toward a hub (NOT_DISEASE_AREAS) are kept in the table: measurement,
phenotype and biological process (traits, signs and processes), medical procedure, non-human
animal disease, and `genetic, familial or congenital disease`, which groups disorders by cause
across every organ system and would add an area to many of them. `injury, poisoning or other
complication` counts.

Hub rule. A protein's counted outcomes are the outcomes of its counted claims that have at
least one disease area. The protein is a hub when those outcomes cannot all be covered by fewer
than 3 disease areas: no set of 1 or 2 areas contains an area of every counted outcome
(`minimum_cover`). An outcome in several areas therefore never adds more than one area to the
count. The sensitivity reading counts the distinct disease areas over the outcomes instead.
"""

import collections
import csv
import itertools
import pathlib
from collections.abc import Collection, Iterable, Mapping

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
AREAS = EXP / "verification" / "therapeutic_areas.csv"
AREA_NAMES = EXP / "verification" / "therapeutic_area_names.csv"
NO_AREA = "no_therapeutic_area"
# Open Targets therapeutic areas that do not count toward hub breadth: measurement, phenotype,
# biological process, medical procedure, non-human animal disease, and genetic, familial or
# congenital disease.
NOT_DISEASE_AREAS = frozenset({"EFO:0001444", "EFO:0000651", "GO:0008150", "EFO:0002571",
                               "MONDO:0005583", "OTAR:0000018"})
HUB_MIN_AREAS = 3
COVER_LIMIT = 6


class AreaError(Exception):
    """The disease file or a committed table is missing a field or is inconsistent."""


def normalize_id(raw: str) -> str:
    """`EFO_0000685` (Open Targets) and `EFO:0000685` (the ontology files) are one identifier."""
    raw = raw.strip()
    return raw if ":" in raw else raw.replace("_", ":", 1)


def build_table(disease_rows: Iterable[dict], collision: Mapping[str, frozenset[str]]
                ) -> tuple[dict[str, frozenset[str]], dict[str, str], dict]:
    """(canonical outcome identifier -> area identifiers, area identifier -> name, counts)."""
    areas: dict[str, set[str]] = collections.defaultdict(set)
    names: dict[str, str] = {}
    flagged: set[str] = set()
    counts: collections.Counter = collections.Counter()
    for r in disease_rows:
        if "therapeuticAreas" not in r:
            raise AreaError("the disease file has no `therapeuticAreas` field")
        counts["disease_rows"] += 1
        term = normalize_id(r["id"])
        own = {normalize_id(a) for a in r["therapeuticAreas"] or ()}
        counts["rows_without_area"] += not own
        counts["rows_with_several_areas"] += len(own) > 1
        names[term] = r["name"]
        if (r.get("ontology") or {}).get("isTherapeuticArea"):
            flagged.add(term)
        for canonical in collision.get(term, frozenset({term})):
            areas[canonical] |= own
    used = set().union(*areas.values()) if areas else set()
    unnamed = sorted(used - set(names))
    if unnamed:
        raise AreaError(f"areas that are not rows of the disease file: {unnamed[:5]}")
    counts["canonical_terms"] = len(areas)
    counts["canonical_terms_with_an_area"] = sum(bool(v) for v in areas.values())
    counts["areas"] = len(used)
    counts["areas_flagged_is_therapeutic_area"] = len(used & flagged)
    counts["flagged_areas_never_used"] = len(flagged - used)
    return ({k: frozenset(v) for k, v in areas.items()}, {a: names[a] for a in sorted(used)},
            dict(counts))


def write_table(areas: Mapping[str, frozenset[str]], names: Mapping[str, str],
                table: pathlib.Path, name_table: pathlib.Path) -> None:
    with table.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["canonical_id", "therapeutic_areas"])
        w.writerows((k, "|".join(sorted(v))) for k, v in sorted(areas.items()) if v)
    with name_table.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["area_id", "name", "disease_area"])
        w.writerows((a, n, int(a not in NOT_DISEASE_AREAS)) for a, n in sorted(names.items()))


def load_areas(path: pathlib.Path = AREAS) -> dict[str, frozenset[str]]:
    with path.open(newline="") as f:
        return {r["canonical_id"]: frozenset(r["therapeutic_areas"].split("|"))
                for r in csv.DictReader(f)}


def load_names(path: pathlib.Path = AREA_NAMES) -> dict[str, str]:
    with path.open(newline="") as f:
        return {r["area_id"]: r["name"] for r in csv.DictReader(f)}


def all_areas_of(outcome: str, areas: Mapping[str, frozenset[str]], graph
                 ) -> tuple[frozenset[str], str]:
    """(the outcome's therapeutic areas, the rule that gave them). `graph` is an
    `ontology_graph.OntologyGraph`."""
    if areas.get(outcome):
        return areas[outcome], "direct"
    by_distance: dict[int, set[str]] = collections.defaultdict(set)
    for ancestor, d in graph.ancestors(outcome).items():
        if areas.get(ancestor):
            by_distance[d] |= areas[ancestor]
    if not by_distance:
        return frozenset(), "none"
    return frozenset(by_distance[min(by_distance)]), "nearest_ancestor"


def area_assignment(outcome: str, areas: Mapping[str, frozenset[str]], graph) -> dict:
    """How an outcome got its areas: `direct` (its own row of the disease file), `inherited`
    (from its nearest ancestors that have any, with their distance and identifiers) or `none`."""
    found, rule = all_areas_of(outcome, areas, graph)
    record = {"areas": sorted(found), "disease_areas": sorted(found - NOT_DISEASE_AREAS),
              "assignment": {"direct": "direct", "nearest_ancestor": "inherited",
                             "none": "none"}[rule],
              "ancestor_distance": None, "nearest_ancestors": [],
              "several_equally_near_ancestors": False}
    if rule == "nearest_ancestor":
        with_areas = {a: d for a, d in graph.ancestors(outcome).items() if areas.get(a)}
        nearest = min(with_areas.values())
        record["ancestor_distance"] = nearest
        record["nearest_ancestors"] = sorted(a for a, d in with_areas.items() if d == nearest)
        record["several_equally_near_ancestors"] = len(record["nearest_ancestors"]) > 1
    return record


def areas_of(outcome: str, areas: Mapping[str, frozenset[str]], graph
             ) -> tuple[frozenset[str], str]:
    """(the outcome's disease areas, the rule that gave its areas)."""
    found, rule = all_areas_of(outcome, areas, graph)
    return found - NOT_DISEASE_AREAS, rule


def minimum_cover(area_sets: Collection[frozenset[str]], limit: int = COVER_LIMIT) -> int:
    """The smallest number of areas such that every set holds at least one of them; empty sets
    are ignored. 0 with no non-empty set. Sizes above `limit` are returned as `limit`."""
    sets = [s for s in set(area_sets) if s]
    if not sets:
        return 0
    universe = sorted(set().union(*sets))
    for k in range(1, limit):
        for chosen in itertools.combinations(universe, k):
            picked = set(chosen)
            if all(s & picked for s in sets):
                return k
    return limit
