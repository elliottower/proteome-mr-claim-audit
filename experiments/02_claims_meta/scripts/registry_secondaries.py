# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""The registered descriptive secondaries of the registry (PREREG.md, §Indices, "Registered
secondary outcomes"). No model is called.

Every secondary is an estimate with an interval. None carries a P value or a verdict; a
contrast between two strata is a difference with a bootstrap interval; a cell on fewer than 20
units is labelled imprecise. Intervals over pairs come from a pair bootstrap (10,000 replicates
of the units named in each function, seed 20261001 with one stream number per secondary, 2.5th
and 97.5th percentiles by the inverted-CDF rule); replicates in which a denominator is zero are
dropped and counted. Wilson intervals beside counts are naive descriptive intervals.

Edge class of two families on a pair (`edge_class`): `identical_release` when the pQTL and the
outcome relation are both `identical_release`; otherwise the registered label of
scripts/dataset_relations.py `edge_label` (`independent`, `overlapping`, `unclear`).

    reporting_completeness           families whose registry records name a dataset, a unique
                                     release, a platform and an ancestry
    dataset_usage                    families per dictionary row and per participant component,
                                     and the ten commonest pQTL x outcome combinations
    edge_relations                   family–family edges on multi-family pairs by dataset
                                     relation, per side and by edge class
    h2_by_families_per_pair          the H2 and H2b bounds for pairs with 2, 3 and 4 or more
                                     families
    h2_directional_pairs             the H2 and H2b bounds over the directional families of
                                     pairs with at least two
    direction_agreement_by_edge_class  agreement of directional families per edge class;
                                     `identical_release` is the positive control
    significance_discordance         pairs with a directional and a `nonsignificant_only` family
    contradiction_source_comparison  the contradiction-source fields on discordant and on
                                     concordant edges, and their difference
    first_claim_concordance          later directional families against the earliest, by
                                     claim date
    periods                          the registry indices for the pairs first claimed (or first
                                     repeated) in 2019–2022 and in 2023–2025, by claim date
    yearly_series                    families and claim records per family first-public year;
                                     pairs claimed, new and already claimed per claim-date year
    therapeutic_areas                repetition, H2, H2b and contradiction per therapeutic area
    platform_pairing                 agreement on same-platform and cross-platform edges
    claims_per_family                distribution of registry claim records per eligible family
    top_lists                        the 20 pairs, proteins and outcomes with most families
    wording_by_repetition_and_year   wording classes by families per pair and by year
    citation_of_earlier_claim        whether a later family's reference list holds a family
                                     with an earlier claim date on the pair
    source_overlap                   eligible families by the sources that returned them
    document_class_and_journals      eligible families by document class and journal
    accounting                       every index with its unit, denominator and what left it

Claim date. A family's claim date on a pair is the date scripts/novelty.py gives the pair in
that family: the public date of the earliest of the family's abstracts (registry or preprint
dating record) whose verified claim records hold the pair (`pair_claim_dates`). Every ordering
of families on a pair (the first claim, the period in which a pair was first claimed or became
repeated, the earlier family a later one may cite) uses claim dates, so a family is never
called first for a pair it had not yet announced. A family's first-public date is used only for
family entry (families and claim records per year).

Usage: computed by scripts/biology_joins.py (`registry_secondaries.json`).
"""

import collections
import csv
import itertools
import math
import pathlib
import statistics
from collections.abc import Callable, Mapping

import numpy as np
from pydantic import BaseModel, ConfigDict

from build_registry import (DIRECTIONAL, N_BOOT, SEED, FamilyPair, PublicDate, Registry,
                            RegistryClaim, date_order, pair_h1, pair_h2, pair_overlap,
                            pair_resolvable, quantiles, wilson)
from claim_tags import ClaimTags
from dataset_relations import compare_side, edge_label
from registry_indices import (FIELDS, IMPRECISE_BELOW, PERIODS, _dataset_field, _text_field,
                              by_family_pair)
from therapeutic_areas import NO_AREA

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
ROW_ATTRIBUTES = EXP / "verification" / "pqtl_row_attributes.csv"
EDGE_CLASSES = ("identical_release", "overlapping", "unclear", "independent")
RELATIONS = ("identical_release", "overlapping_participant_source", "disjoint", "unclear")
K_STRATA = ("2", "3", "4_or_more")
SEARCH_SOURCES = ("pubmed", "epmc", "openalex")
TOP_N = 20
STREAMS = {name: i for i, name in enumerate(
    ("edge_relations", "h2_by_families_per_pair", "h2_directional_pairs",
     "direction_agreement_by_edge_class", "significance_discordance",
     "contradiction_source_comparison", "first_claim_concordance", "periods_early",
     "periods_late", "therapeutic_areas", "platform_pairing"), start=10)}
Pair = tuple[str, str]


class RecordMeta(BaseModel):
    """What the search and OpenAlex hold about one screening record
    (scripts/record_metadata.py)."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    record_id: str
    kind: str
    search_sources: tuple[str, ...]
    chase_round: int | None
    journal: str | None
    openalex_ids: tuple[str, ...]
    has_reference_list: bool | None
    referenced_works: tuple[str, ...]
    first_author_country: str | None


def load_record_meta(path: pathlib.Path) -> dict[str, RecordMeta]:
    return {m.record_id: m for m in (RecordMeta.model_validate_json(l)
                                     for l in path.read_text().splitlines() if l.strip())}


def edge_class(a: FamilyPair, b: FamilyPair) -> str:
    pq = compare_side(a.pqtl, b.pqtl, a.attribution_clear, b.attribution_clear)
    oc = compare_side(a.outcome, b.outcome, a.attribution_clear, b.attribution_clear)
    if pq == oc == "identical_release":
        return "identical_release"
    return edge_label(pq, oc)


def share(k: int, n: int) -> float | None:
    return k / n if n else None


def boot_ratio(num: list[float], den: list[float], n_boot: int, seed: int, stream: int
               ) -> dict:
    """Percentile interval of sum(num) / sum(den) over units resampled with replacement."""
    if not num or sum(den) == 0:
        return {"interval": None, "undefined_replicates": 0}
    rng = np.random.default_rng([seed, stream])
    n, d = np.array(num, dtype=float), np.array(den, dtype=float)
    idx = rng.integers(0, len(n), size=(n_boot, len(n)))
    total = d[idx].sum(axis=1)
    defined = total > 0
    return {"interval": quantiles(n[idx].sum(axis=1)[defined] / total[defined]),
            "undefined_replicates": int((~defined).sum())}


def boot_difference(num_a: list[float], den_a: list[float], num_b: list[float],
                    den_b: list[float], n_boot: int, seed: int, stream: int) -> dict:
    """Percentile interval of sum(num_a)/sum(den_a) − sum(num_b)/sum(den_b), the four lists
    indexed by the same units, resampled together."""
    if not num_a or sum(den_a) == 0 or sum(den_b) == 0:
        return {"difference": None, "interval": None, "undefined_replicates": 0}
    rng = np.random.default_rng([seed, stream])
    arrays = [np.array(x, dtype=float) for x in (num_a, den_a, num_b, den_b)]
    idx = rng.integers(0, len(num_a), size=(n_boot, len(num_a)))
    na, da, nb, db = (x[idx].sum(axis=1) for x in arrays)
    defined = (da > 0) & (db > 0)
    diff = na[defined] / da[defined] - nb[defined] / db[defined]
    return {"difference": sum(num_a) / sum(den_a) - sum(num_b) / sum(den_b),
            "interval": quantiles(diff) if defined.any() else None,
            "undefined_replicates": int((~defined).sum())}


ClaimDates = Mapping[tuple[str, Pair], PublicDate]


def year_of(meta: Mapping[str, dict], family: str) -> int:
    """A family's first-public year: family entry only."""
    return int(meta[family]["first_public"]["value"][:4])


def pair_claim_dates(claims: list[RegistryClaim], novelty: Mapping[str, dict]
                     ) -> dict[tuple[str, Pair], PublicDate]:
    """(family, pair) -> the family's claim date on the pair, from the novelty records of
    scripts/novelty.py. Every registry claim record must have one, and the records of one family
    on one pair carry one date."""
    out: dict[tuple[str, Pair], PublicDate] = {}
    for c in claims:
        record = novelty.get(c.claim_record_id)
        if record is None:
            raise ValueError(f"{c.claim_record_id}: no novelty record, so no claim date")
        d = PublicDate.model_validate(record["claim_date"])
        key = (c.family_id, (c.protein_id, c.outcome_id))
        if out.setdefault(key, d) != d:
            raise ValueError(f"{key}: two claim dates")
    return out


def multi_family(registry: Registry) -> dict[Pair, dict[str, FamilyPair]]:
    return {pair: fams for pair, fams in registry.items() if len(fams) >= 2}


def edges(fams: Mapping[str, FamilyPair], keep: Callable[[FamilyPair], bool] = lambda f: True
          ) -> list[tuple[FamilyPair, FamilyPair]]:
    kept = sorted((f for f in fams.values() if keep(f)), key=lambda f: f.family_id)
    return list(itertools.combinations(kept, 2))


def directional(fp: FamilyPair) -> bool:
    return fp.direction in DIRECTIONAL


# --- reporting completeness and dataset usage -------------------------------------------------

def family_names(registry: Registry) -> dict[str, dict[str, dict]]:
    """family -> side -> written name -> mapping, over every pair of the family."""
    out: dict[str, dict[str, dict]] = collections.defaultdict(lambda: {"pqtl": {}, "outcome": {}})
    for fams in registry.values():
        for fam, fp in fams.items():
            for side in ("pqtl", "outcome"):
                for m in getattr(fp, side):
                    out[fam][side][m.written] = m
    return out


def reporting_completeness(registry: Registry, claims: list[RegistryClaim],
                           tags: Mapping[str, ClaimTags], meta: Mapping[str, dict]) -> dict:
    """Unit: eligible family with at least one registry claim record. A side is named when one
    of its names is not `not_stated`; its release is unique when it has a name and every name
    maps to one release."""
    names = family_names(registry)
    stated: dict[str, dict[str, bool]] = collections.defaultdict(
        lambda: {"platform": False, "ancestry": False})
    for c in claims:
        t = tags[c.claim_record_id]
        stated[c.family_id]["platform"] |= any(p != "not_stated" for p in t.platform)
        stated[c.family_id]["ancestry"] |= t.ancestry != "not_stated"
    fields: collections.Counter = collections.Counter()
    for fam, sides in names.items():
        named = {s: any(m.state != "not_stated" for m in sides[s].values()) for s in sides}
        unique = {s: bool(sides[s]) and all(m.state == "unique" for m in sides[s].values())
                  for s in sides}
        fields["pqtl_dataset_named"] += named["pqtl"]
        fields["outcome_dataset_named"] += named["outcome"]
        fields["pqtl_release_unique"] += unique["pqtl"]
        fields["outcome_release_unique"] += unique["outcome"]
        fields["both_releases_unique"] += unique["pqtl"] and unique["outcome"]
        fields["platform_stated"] += stated[fam]["platform"]
        fields["ancestry_stated"] += stated[fam]["ancestry"]
    n = len(names)
    return {"families_with_a_registry_claim": n,
            "eligible_families_without_a_registry_claim": sum(
                f not in names for f in meta),
            "imprecise_under_20": n < IMPRECISE_BELOW,
            **{k: {"families": fields[k], "share": share(fields[k], n),
                   "wilson_descriptive": wilson(fields[k], n)}
               for k in ("pqtl_dataset_named", "outcome_dataset_named", "pqtl_release_unique",
                         "outcome_release_unique", "both_releases_unique", "platform_stated",
                         "ancestry_stated")}}


def name_label(m) -> str:
    """The dictionary row of a unique name; the candidate rows of an ambiguous one."""
    if m.state == "unique":
        return m.candidates[0]
    if m.state == "release_ambiguous":
        return "one of: " + " / ".join(m.candidates)
    return m.state


def dataset_usage(registry: Registry) -> dict:
    """Families per dictionary row (names that map to one release), per label of an ambiguous
    name, and per participant component known for a name whichever release is meant; the ten
    commonest pQTL x outcome label combinations a family names on one pair."""
    names = family_names(registry)
    out: dict = {"families": len(names)}
    for side in ("pqtl", "outcome"):
        labels: collections.Counter = collections.Counter()
        components: collections.Counter = collections.Counter()
        for sides in names.values():
            labels.update({name_label(m) for m in sides[side].values()})
            components.update({c for m in sides[side].values() for c in m.known_components})
        out[f"families_per_{side}_label"] = dict(sorted(
            labels.items(), key=lambda kv: (-kv[1], kv[0])))
        out[f"families_per_{side}_component"] = dict(sorted(
            components.items(), key=lambda kv: (-kv[1], kv[0])))
    combos: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for fams in registry.values():
        for fam, fp in fams.items():
            for p in fp.pqtl:
                for o in fp.outcome:
                    combos[(name_label(p), name_label(o))].add(fam)
    ranked = sorted(combos.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:10]
    out["commonest_pqtl_outcome_combinations"] = [
        {"pqtl": p, "outcome": o, "families": len(f)} for (p, o), f in ranked]
    return out


# --- edges ------------------------------------------------------------------------------------

def edge_relations(registry: Registry, n_boot: int, seed: int) -> dict:
    """Unit: every two families of a multi-family pair, whatever their directions."""
    per_pair = []
    for fams in multi_family(registry).values():
        counts: collections.Counter = collections.Counter()
        for a, b in edges(fams):
            pq = compare_side(a.pqtl, b.pqtl, a.attribution_clear, b.attribution_clear)
            oc = compare_side(a.outcome, b.outcome, a.attribution_clear, b.attribution_clear)
            counts[f"pqtl:{pq}"] += 1
            counts[f"outcome:{oc}"] += 1
            counts[f"class:{edge_class(a, b)}"] += 1
            counts["edges"] += 1
        per_pair.append(counts)
    n_edges = sum(c["edges"] for c in per_pair)
    den = [float(c["edges"]) for c in per_pair]

    def table(prefix: str, values: tuple[str, ...]) -> dict:
        out = {}
        for v in values:
            k = sum(c[f"{prefix}:{v}"] for c in per_pair)
            out[v] = {"edges": k, "share": share(k, n_edges),
                      "pair_bootstrap": boot_ratio([float(c[f"{prefix}:{v}"]) for c in per_pair],
                                                   den, n_boot, seed,
                                                   STREAMS["edge_relations"])["interval"]}
        return out

    return {"multi_family_pairs": len(per_pair), "edges": n_edges,
            "imprecise_under_20_pairs": len(per_pair) < IMPRECISE_BELOW,
            "pqtl_side": table("pqtl", RELATIONS), "outcome_side": table("outcome", RELATIONS),
            "edge_class": table("class", EDGE_CLASSES)}


def bounds(classes: list[str | None], known: str, known_not: str, n_boot: int, seed: int,
           stream: int) -> dict:
    """Three-way counts, bounds and pair-bootstrap intervals of a list of pair classes."""
    classes = [c for c in classes if c is not None]
    n, k, k_not = len(classes), classes.count(known), classes.count(known_not)
    unresolved = n - k - k_not
    ones = [1.0] * n
    return {"pairs": n, known: k, known_not: k_not, "unresolved": unresolved,
            "lower": share(k, n), "upper": share(k + unresolved, n),
            "pair_bootstrap_lower": boot_ratio([float(c == known) for c in classes], ones,
                                               n_boot, seed, stream)["interval"],
            "pair_bootstrap_upper": boot_ratio([float(c != known_not) for c in classes], ones,
                                               n_boot, seed, stream)["interval"],
            "imprecise_under_20_pairs": n < IMPRECISE_BELOW}


def h2_tables(pairs: list[Mapping[str, FamilyPair]], n_boot: int, seed: int, stream: int
              ) -> dict:
    return {"h2_identical_release": bounds([pair_h2(f) for f in pairs], "known_identical",
                                           "known_not_identical", n_boot, seed, stream),
            "h2b_identical_or_overlapping": bounds(
                [pair_overlap(f) for f in pairs], "known_overlapping", "known_not_overlapping",
                n_boot, seed, stream),
            "resolvable_pairs": sum(bool(pair_resolvable(f)) for f in pairs)}


def k_stratum(n_families: int) -> str:
    return "4_or_more" if n_families >= 4 else str(n_families)


def h2_by_families_per_pair(registry: Registry, n_boot: int, seed: int) -> dict:
    strata: dict[str, list] = {k: [] for k in K_STRATA}
    for fams in multi_family(registry).values():
        strata[k_stratum(len(fams))].append(fams)
    return {k: h2_tables(v, n_boot, seed, STREAMS["h2_by_families_per_pair"])
            for k, v in strata.items()}


def h2_directional_pairs(registry: Registry, n_boot: int, seed: int) -> dict:
    """The H2 and H2b classes read over the directional families only, for the pairs with at
    least two; no verdict."""
    pairs = [{f: fp for f, fp in fams.items() if directional(fp)} for fams in registry.values()]
    return h2_tables([p for p in pairs if len(p) >= 2], n_boot, seed,
                     STREAMS["h2_directional_pairs"])


def directional_edges(registry: Registry) -> list[dict]:
    """Per pair with at least two directional families: its directional edges with class and
    agreement."""
    out = []
    for pair, fams in registry.items():
        found = [{"a": a, "b": b, "class": edge_class(a, b),
                  "agree": DIRECTIONAL[a.direction] == DIRECTIONAL[b.direction]}
                 for a, b in edges(fams, directional)]
        if found:
            out.append({"pair": pair, "edges": found})
    return out


def direction_agreement_by_edge_class(registry: Registry, n_boot: int, seed: int) -> dict:
    """Share of edges between directional families that join families of the same direction,
    per edge class. `identical_release` is a positive control: the same pQTL release and the
    same outcome release should give the same direction, so a share below 1 measures extraction
    or direction-coding error, or analytic flexibility."""
    pairs = directional_edges(registry)
    stream = STREAMS["direction_agreement_by_edge_class"]

    def arrays(cls: str) -> tuple[list[float], list[float]]:
        return ([float(sum(e["agree"] for e in p["edges"] if e["class"] == cls)) for p in pairs],
                [float(sum(e["class"] == cls for e in p["edges"])) for p in pairs])

    out: dict = {"pairs_with_a_directional_edge": len(pairs)}
    for cls in EDGE_CLASSES:
        num, den = arrays(cls)
        k, n = int(sum(num)), int(sum(den))
        out[cls] = {"edges": n, "edges_agreeing": k, "share_agreeing": share(k, n),
                    "pairs": sum(d > 0 for d in den),
                    "wilson_descriptive": wilson(k, n),
                    "pair_bootstrap": boot_ratio(num, den, n_boot, seed, stream)["interval"],
                    "imprecise_under_20_pairs": sum(d > 0 for d in den) < IMPRECISE_BELOW}
    out["identical_release"]["role"] = "positive_control"
    out["independent_minus_overlapping"] = boot_difference(
        *arrays("independent"), *arrays("overlapping"), n_boot, seed, stream)
    return out


def significance_discordance(registry: Registry, n_boot: int, seed: int) -> dict:
    """Pairs with at least one directional family and at least one `nonsignificant_only` family,
    over multi-family pairs; and the directional × `nonsignificant_only` edges by edge class."""
    multi = multi_family(registry)
    flags, by_class = [], collections.Counter()
    for fams in multi.values():
        up = [f for f in fams.values() if directional(f)]
        null = [f for f in fams.values() if f.direction == "nonsignificant_only"]
        flags.append(float(bool(up) and bool(null)))
        for a in up:
            for b in null:
                by_class[edge_class(a, b)] += 1
    k, n = int(sum(flags)), len(flags)
    return {"multi_family_pairs": n, "significance_discordant_pairs": k, "share": share(k, n),
            "wilson_descriptive": wilson(k, n),
            "pair_bootstrap": boot_ratio(flags, [1.0] * n, n_boot, seed,
                                         STREAMS["significance_discordance"])["interval"],
            "edges_by_class": {c: by_class[c] for c in EDGE_CLASSES},
            "imprecise_under_20_pairs": n < IMPRECISE_BELOW}


def contradiction_source_comparison(registry: Registry, claims: list[RegistryClaim],
                                    tags: Mapping[str, ClaimTags], n_boot: int, seed: int
                                    ) -> dict:
    """The four contradiction-source fields compared between the two families of every edge
    between directional families: `differ`, `same`, `not_stated`, `undetermined`. Discordant
    edges (opposite directions) against concordant edges (same direction), with the difference
    in the share that differ."""
    records = by_family_pair(claims)

    def values(pair: Pair, fp: FamilyPair, attr: str) -> set[str]:
        out: set[str] = set()
        for c in records[pair][fp.family_id]:
            v = getattr(tags[c.claim_record_id], attr)
            out |= set(v) if isinstance(v, tuple) else {v}
        return out

    pairs = []
    for p in directional_edges(registry):
        rows = []
        for e in p["edges"]:
            a, b = e["a"], e["b"]
            clear = a.attribution_clear and b.attribution_clear
            fields = {"pqtl": _dataset_field(a.pqtl, b.pqtl, clear),
                      "outcome": _dataset_field(a.outcome, b.outcome, clear),
                      "platform": _text_field(values(p["pair"], a, "platform"),
                                              values(p["pair"], b, "platform")),
                      "ancestry": _text_field(values(p["pair"], a, "ancestry"),
                                              values(p["pair"], b, "ancestry"))}
            fields["any"] = "differ" if "differ" in fields.values() else "no_stated_difference"
            rows.append((e["agree"], fields))
        pairs.append(rows)
    out: dict = {"pairs_with_a_directional_edge": len(pairs),
                 "discordant_edges": sum(not agree for rows in pairs for agree, _ in rows),
                 "concordant_edges": sum(agree for rows in pairs for agree, _ in rows)}
    for field in (*FIELDS, "any"):
        def arrays(agree: bool) -> tuple[list[float], list[float]]:
            return ([float(sum(a == agree and f[field] == "differ" for a, f in rows))
                     for rows in pairs],
                    [float(sum(a == agree for a, _ in rows)) for rows in pairs])
        (dn, dd), (cn, cd) = arrays(False), arrays(True)
        out[field] = {
            "discordant_differ": int(sum(dn)), "concordant_differ": int(sum(cn)),
            "discordant_share_differ": share(int(sum(dn)), int(sum(dd))),
            "concordant_share_differ": share(int(sum(cn)), int(sum(cd))),
            "discordant_minus_concordant": boot_difference(
                dn, dd, cn, cd, n_boot, seed, STREAMS["contradiction_source_comparison"])}
    out["imprecise_under_20_pairs"] = (
        sum(any(not a for a, _ in rows) for rows in pairs) < IMPRECISE_BELOW)
    return out


def first_claim_concordance(registry: Registry, dates: ClaimDates, n_boot: int,
                            seed: int) -> dict:
    """Among pairs with at least two directional families: the first family is the one whose
    claim date on the pair is strictly earlier than every other directional family's, at the
    resolution each two dates share. A pair without one is `tied_first`. The index is the share
    of later directional families whose direction equals the first family's, overall and by the
    edge class of the first family with the later one."""
    num, den, tied = [], [], 0
    by_class = {c: [0, 0] for c in EDGE_CLASSES}
    for pair, fams in registry.items():
        d = [f for f in fams.values() if directional(f)]
        if len(d) < 2:
            continue
        first = [f for f in d if all(
            date_order(dates[(f.family_id, pair)], dates[(g.family_id, pair)])
            == "earlier" for g in d if g is not f)]
        if not first:
            tied += 1
            continue
        later = [g for g in d if g is not first[0]]
        same = [DIRECTIONAL[g.direction] == DIRECTIONAL[first[0].direction] for g in later]
        num.append(float(sum(same)))
        den.append(float(len(later)))
        for g, s in zip(later, same):
            cls = edge_class(first[0], g)
            by_class[cls][0] += s
            by_class[cls][1] += 1
    k, n = int(sum(num)), int(sum(den))
    return {"pairs_with_a_first_family": len(num), "pairs_tied_first": tied,
            "later_families": n, "later_families_same_direction": k, "share": share(k, n),
            "wilson_descriptive": wilson(k, n),
            "pair_bootstrap": boot_ratio(num, den, n_boot, seed,
                                         STREAMS["first_claim_concordance"])["interval"],
            "by_edge_class": {c: {"later_families": v[1], "same_direction": v[0],
                                  "share": share(v[0], v[1])} for c, v in by_class.items()},
            "imprecise_under_20_pairs": len(num) < IMPRECISE_BELOW}


# --- periods, years, areas, platforms ---------------------------------------------------------

def period_of(year: int) -> str | None:
    return next((f"{a}-{b}" for a, b in PERIODS if a <= year <= b), None)


def contradicting(fams: Mapping[str, FamilyPair]) -> bool:
    return {DIRECTIONAL[f.direction] for f in fams.values() if directional(f)} == {
        "raises", "lowers"}


def significance_discordant(fams: Mapping[str, FamilyPair]) -> bool:
    return (any(directional(f) for f in fams.values())
            and any(f.direction == "nonsignificant_only" for f in fams.values()))


def period_rows(registry: Registry, dates: ClaimDates) -> dict[str, dict[str, list]]:
    """Per period, the per-pair values of each index. A pair is dated by the year of its
    earliest claim date, the year it was first claimed in the registry; a multi-family pair by
    the year of its second-earliest claim date, the year it became repeated."""
    out: dict[str, dict[str, list]] = {f"{a}-{b}": collections.defaultdict(list)
                                       for a, b in PERIODS}
    for pair, fams in registry.items():
        years = sorted(dates[(f, pair)].value.year for f in fams)
        first = period_of(years[0])
        if first:
            out[first]["distinct_pairs"].append(1.0)
        if len(fams) < 2 or period_of(years[1]) is None:
            continue
        rows = out[period_of(years[1])]
        rows["multi_family_pairs"].append(1.0)
        h2, h2b = pair_h2(fams), pair_overlap(fams)
        rows["h2_lower"].append(float(h2 == "known_identical"))
        rows["h2_upper"].append(float(h2 != "known_not_identical"))
        rows["h2b_lower"].append(float(h2b == "known_overlapping"))
        rows["h2b_upper"].append(float(h2b != "known_not_overlapping"))
        rows["resolvable_share"].append(float(bool(pair_resolvable(fams))))
        rows["significance_discordant_share"].append(float(significance_discordant(fams)))
        if sum(directional(f) for f in fams.values()) >= 2:
            rows["contradicting_share"].append(float(contradicting(fams)))
        h1 = pair_h1(fams)
        if h1 is not None and h1.in_h1:
            rows["h1_pair_concordance"].append(float(bool(h1.agrees)))
    return out


def periods(registry: Registry, dates: ClaimDates, n_boot: int, seed: int) -> dict:
    """Each index for the pairs first claimed (and the pairs first repeated) in 2019–2022 and in
    2023–2025, with the later-minus-earlier difference and its interval from independent pair
    bootstraps of the two periods."""
    rows = period_rows(registry, dates)
    (early, late) = (f"{a}-{b}" for a, b in PERIODS)
    out: dict = {early: {}, late: {}, "later_minus_earlier": {}}
    for label in (early, late):
        out[label]["distinct_pairs"] = len(rows[label]["distinct_pairs"])
        out[label]["multi_family_pairs"] = len(rows[label]["multi_family_pairs"])
    shares = ("h2_lower", "h2_upper", "h2b_lower", "h2b_upper", "resolvable_share",
              "significance_discordant_share", "contradicting_share", "h1_pair_concordance")
    for key in shares:
        replicates = {}
        for label, stream in ((early, STREAMS["periods_early"]),
                              (late, STREAMS["periods_late"])):
            values = rows[label][key]
            n = len(values)
            out[label][key] = {"pairs": n, "share": share(int(sum(values)), n),
                               "pair_bootstrap": boot_ratio(values, [1.0] * n, n_boot, seed,
                                                            stream)["interval"],
                               "imprecise_under_20_pairs": n < IMPRECISE_BELOW}
            if n:
                rng = np.random.default_rng([seed, stream])
                idx = rng.integers(0, n, size=(n_boot, n))
                replicates[label] = np.array(values)[idx].mean(axis=1)
        if len(replicates) == 2:
            out["later_minus_earlier"][key] = {
                "difference": out[late][key]["share"] - out[early][key]["share"],
                "interval": quantiles(replicates[late] - replicates[early])}
        else:
            out["later_minus_earlier"][key] = {"difference": None, "interval": None}
    return out


def yearly_series(registry: Registry, claims: list[RegistryClaim], meta: Mapping[str, dict],
                  dates: ClaimDates) -> dict:
    """Family entry per first-public year: eligible families and their registry claim records.
    Pairs per claim-date year: the pairs claimed that year (a family's claim date on the pair
    falls in it), those first claimed in the registry that year, and those a family already
    claimed in an earlier year."""
    families = collections.Counter(year_of(meta, f) for f in meta)
    records = collections.Counter(year_of(meta, c.family_id) for c in claims)
    claimed: dict[int, set[Pair]] = collections.defaultdict(set)
    first: dict[Pair, int] = {}
    for pair, fams in registry.items():
        years = [dates[(f, pair)].value.year for f in fams]
        for y in years:
            claimed[y].add(pair)
        first[pair] = min(years)
    years = sorted(set(families) | set(claimed))
    out = {}
    for y in years:
        already = sum(first[p] < y for p in claimed[y])
        out[str(y)] = {"families": families[y], "claim_records": records[y],
                       "pairs_claimed": len(claimed[y]),
                       "new_pairs": sum(first[p] == y for p in claimed[y]),
                       "pairs_already_claimed_in_an_earlier_year": already,
                       "share_already_claimed": share(already, len(claimed[y]))}
    return out


def therapeutic_areas(registry: Registry,
                      areas_of_outcome: Callable[[str], tuple[frozenset[str], str]],
                      n_boot: int, seed: int) -> dict:
    """Per therapeutic area (an outcome counts in each of its areas): pairs, multi-family pairs,
    the H2 and H2b bounds and the contradicting pairs. An area with fewer than 20 multi-family
    pairs is printed, labelled imprecise and not interpreted."""
    by_area: dict[str, list] = collections.defaultdict(list)
    for (protein, outcome), fams in registry.items():
        for area in sorted(areas_of_outcome(outcome)[0]) or [NO_AREA]:
            by_area[area].append(fams)
    out = {}
    for area, pairs in sorted(by_area.items()):
        multi = [f for f in pairs if len(f) >= 2]
        with_two = [f for f in multi if sum(directional(x) for x in f.values()) >= 2]
        k = sum(contradicting(f) for f in with_two)
        out[area] = {"pairs": len(pairs), "multi_family_pairs": len(multi),
                     "multi_family_share": share(len(multi), len(pairs)),
                     **h2_tables(multi, n_boot, seed, STREAMS["therapeutic_areas"]),
                     "pairs_with_two_directional_families": len(with_two),
                     "contradicting_pairs": k,
                     "contradicting_share": share(k, len(with_two)),
                     "imprecise_under_20_pairs": len(multi) < IMPRECISE_BELOW}
    return out


def load_row_platforms(path: pathlib.Path = ROW_ATTRIBUTES) -> dict[str, str]:
    """pQTL dictionary row -> its assay family (`olink`, `somascan`, `other`, or `mixed` for an
    instrument set pooled over assay families), from the committed table."""
    with path.open(newline="") as f:
        return {r["dictionary_row"]: r["platform_family"] for r in csv.DictReader(f)}


def family_platform(fp: FamilyPair, row_platform: Mapping[str, str]) -> str | None:
    """The one assay family of a family's pQTL names on a pair: every name must give one, and
    all must agree. A name gives an assay family when every candidate is a dictionary row and
    all share one family other than `mixed`."""
    found = set()
    for m in fp.pqtl:
        of_rows = {row_platform[c] for c in m.candidates if c in row_platform}
        if (len(of_rows) != 1 or "mixed" in of_rows
                or any(c not in row_platform for c in m.candidates)):
            return None
        found |= of_rows
    return next(iter(found)) if len(found) == 1 else None


def platform_pairing(registry: Registry, row_platform: Mapping[str, str], n_boot: int,
                     seed: int) -> dict:
    """Edges between directional families by whether the two families' pQTL datasets are on the
    same assay family (verification/pqtl_row_attributes.csv: Olink, SomaScan, other): agreement
    share and discordant edges."""
    labels = ("same_platform", "cross_platform", "platform_unknown")
    pairs = []
    for p in directional_edges(registry):
        counts: collections.Counter = collections.Counter()
        for e in p["edges"]:
            pa, pb = (family_platform(f, row_platform) for f in (e["a"], e["b"]))
            label = ("platform_unknown" if pa is None or pb is None
                     else "same_platform" if pa == pb else "cross_platform")
            counts[(label, "edges")] += 1
            counts[(label, "agree")] += e["agree"]
        pairs.append(counts)
    out: dict = {"pairs_with_a_directional_edge": len(pairs)}

    def arrays(label: str) -> tuple[list[float], list[float]]:
        return ([float(c[(label, "agree")]) for c in pairs],
                [float(c[(label, "edges")]) for c in pairs])

    for label in labels:
        num, den = arrays(label)
        k, n = int(sum(num)), int(sum(den))
        out[label] = {"edges": n, "edges_agreeing": k, "discordant_edges": n - k,
                      "share_agreeing": share(k, n), "wilson_descriptive": wilson(k, n),
                      "pair_bootstrap": boot_ratio(num, den, n_boot, seed,
                                                   STREAMS["platform_pairing"])["interval"],
                      "imprecise_under_20_pairs": sum(d > 0 for d in den) < IMPRECISE_BELOW}
    out["cross_minus_same"] = boot_difference(*arrays("cross_platform"),
                                              *arrays("same_platform"), n_boot, seed,
                                              STREAMS["platform_pairing"])
    return out


# --- descriptives -----------------------------------------------------------------------------

def quantile(values: list[int], q: float) -> float:
    """The inverted-CDF quantile of a sorted list: the smallest value with at least a share q
    of the values at or below it."""
    return float(values[max(0, math.ceil(q * len(values)) - 1)])


def claims_per_family(meta: Mapping[str, dict]) -> dict:
    """Registry claim records per eligible family, zero-claim families included."""
    counts = sorted(m["n_registry_claims"] for m in meta.values())
    if not counts:
        return {"eligible_families": 0}
    top = sorted(counts, reverse=True)[:math.ceil(0.10 * len(counts))]
    total = sum(counts)
    return {"eligible_families": len(counts), "claim_records": total,
            "families_with_zero_claims": counts.count(0),
            "min": counts[0], "q25": quantile(counts, 0.25), "median": statistics.median(counts),
            "q75": quantile(counts, 0.75), "q90": quantile(counts, 0.90), "max": counts[-1],
            "top_decile_families": len(top),
            "share_of_claim_records_from_top_decile": share(sum(top), total)}


def top_lists(registry: Registry, claims: list[RegistryClaim]) -> dict:
    """The 20 pairs, proteins and outcomes with the most study families. Ties: pairs by claim
    records, then identifier; proteins and outcomes by pairs, then identifier."""
    per_pair = collections.Counter((c.protein_id, c.outcome_id) for c in claims)
    pairs = sorted(registry, key=lambda p: (-len(registry[p]), -per_pair[p], p))[:TOP_N]

    def ranked(index: int) -> list[dict]:
        families: dict[str, set] = collections.defaultdict(set)
        n_pairs: collections.Counter = collections.Counter()
        records: collections.Counter = collections.Counter()
        for pair, fams in registry.items():
            families[pair[index]] |= set(fams)
            n_pairs[pair[index]] += 1
        for c in claims:
            records[(c.protein_id, c.outcome_id)[index]] += 1
        keys = sorted(families, key=lambda k: (-len(families[k]), -n_pairs[k], k))
        return [{"id": k, "families": len(families[k]), "pairs": n_pairs[k],
                 "claim_records": records[k]} for k in keys[:TOP_N]]

    return {"pairs": [{"protein_id": p[0], "outcome_id": p[1], "families": len(registry[p]),
                       "claim_records": per_pair[p]} for p in pairs],
            "proteins": ranked(0), "outcomes": ranked(1)}


def wording_by_repetition_and_year(registry: Registry, claims: list[RegistryClaim],
                                   tags: Mapping[str, ClaimTags], meta: Mapping[str, dict]
                                   ) -> dict:
    """Claim records by wording class for pairs with 1, 2 and 3 or more families, and per
    first-public year of the family; the share with novelty language per year."""
    by_k: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    by_year: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    novelty: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    for c in claims:
        t = tags[c.claim_record_id]
        k = len(registry[(c.protein_id, c.outcome_id)])
        by_k["3_or_more" if k >= 3 else str(k)][t.wording_class] += 1
        year = str(year_of(meta, c.family_id))
        by_year[year][t.wording_class] += 1
        novelty[year][0] += t.novelty_language
        novelty[year][1] += 1

    def shares(counter: collections.Counter) -> dict:
        n = sum(counter.values())
        return {"claim_records": n, **{w: {"claim_records": counter[w],
                                           "share": share(counter[w], n)}
                                       for w in ("association", "causal", "target")}}

    return {"by_families_per_pair": {k: shares(v) for k, v in sorted(by_k.items())},
            "by_year": {y: shares(v) for y, v in sorted(by_year.items())},
            "novelty_language_by_year": {
                y: {"claim_records": n, "novelty_language": k, "share": share(k, n),
                    "wilson_descriptive": wilson(k, n)}
                for y, (k, n) in sorted(novelty.items())}}


# --- records: citations, sources, journals ----------------------------------------------------

def family_records(meta: Mapping[str, dict], record_meta: Mapping[str, RecordMeta],
                   family: str) -> list[RecordMeta]:
    ids = [*meta[family]["registry_records"], *meta[family]["dating_records"]]
    return [record_meta[i] for i in ids if i in record_meta]


def citation_of_earlier_claim(registry: Registry, dates: ClaimDates, meta: Mapping[str, dict],
                              record_meta: Mapping[str, RecordMeta],
                              novelty: Mapping[str, dict] | None = None,
                              claims: list[RegistryClaim] | None = None) -> dict:
    """Unit: a later family on a repeated pair, that is, a family with at least one other family
    of the pair strictly earlier by claim date on the pair. It cites the earlier claim when the
    OpenAlex reference list of any of its registry or preprint records holds an OpenAlex work of
    an earlier family of that pair. Later families with no reference list are counted apart and
    enter no share. The second table restricts the unit to later families holding a
    novelty-language claim of the pair that is `earlier_in_registry`."""
    refs = {f: {w for r in family_records(meta, record_meta, f) for w in r.referenced_works}
            for f in meta}
    listed = {f: any(r.has_reference_list for r in family_records(meta, record_meta, f))
              for f in meta}
    works = {f: {w for r in family_records(meta, record_meta, f) for w in r.openalex_ids}
             for f in meta}
    novel: set[tuple[Pair, str]] = set()
    for c in claims or []:
        n = (novelty or {}).get(c.claim_record_id)
        if n and n["novelty_language"] and n["novelty_class"] == "earlier_in_registry":
            novel.add(((c.protein_id, c.outcome_id), c.family_id))
    units = []
    for pair, fams in multi_family(registry).items():
        for later in sorted(fams):
            earlier = [f for f in fams if f != later and date_order(
                dates[(f, pair)], dates[(later, pair)]) == "earlier"]
            if earlier:
                cites = any(refs[later] & works[e] for e in earlier)
                units.append((pair, later, listed[later], cites))

    def table(rows: list[tuple]) -> dict:
        with_list = [r for r in rows if r[2]]
        k, n = sum(r[3] for r in with_list), len(with_list)
        return {"later_family_pair_records": len(rows),
                "later_families": len({r[1] for r in rows}),
                "without_a_reference_list": len(rows) - n, "with_a_reference_list": n,
                "citing_an_earlier_family_of_the_pair": k, "share": share(k, n),
                "wilson_descriptive": wilson(k, n), "imprecise_under_20": n < IMPRECISE_BELOW}

    with_any = sum(listed.values())
    return {"eligible_families": len(meta), "eligible_families_with_a_reference_list": with_any,
            "share_with_a_reference_list": share(with_any, len(meta)),
            "later_families": table(units),
            "later_families_with_novelty_language_and_an_earlier_registry_claim": table(
                [u for u in units if (u[0], u[1]) in novel])}


def source_overlap(meta: Mapping[str, dict], families: Mapping[str, list[str]],
                   record_meta: Mapping[str, RecordMeta]) -> dict:
    """Eligible families by the sources whose registered queries returned any of their records
    (PubMed, Europe PMC, OpenAlex), and the families no query returned (found only by citation
    chasing, by round)."""
    combos: collections.Counter = collections.Counter()
    rounds: collections.Counter = collections.Counter()
    for fam in meta:
        records = [record_meta[r] for r in families.get(fam, []) if r in record_meta]
        sources = sorted({s for r in records for s in r.search_sources},
                         key=SEARCH_SOURCES.index)
        if sources:
            combos["+".join(sources)] += 1
        else:
            chase = [r.chase_round for r in records if r.chase_round is not None]
            rounds[f"chase_round_{min(chase)}" if chase else "no_record_metadata"] += 1
    n, only_chase = len(meta), sum(v for k, v in rounds.items() if k.startswith("chase_"))
    return {"eligible_families": n, "by_search_sources": dict(sorted(combos.items())),
            "found_only_by_citation_chasing": only_chase,
            "share_found_only_by_citation_chasing": share(only_chase, n),
            "wilson_descriptive": wilson(only_chase, n),
            "not_returned_by_any_query": dict(sorted(rounds.items()))}


def document_class_and_journals(meta: Mapping[str, dict],
                                record_meta: Mapping[str, RecordMeta]) -> dict:
    """Eligible families by the document class of their registry record, the share with a
    preprint registry record only, and the 20 journals with the most families (the journal
    title of the family's journal registry record; counts only)."""
    classes: collections.Counter = collections.Counter()
    journals: collections.Counter = collections.Counter()
    for fam, m in meta.items():
        records = [record_meta[r] for r in m["registry_records"] if r in record_meta]
        kinds = {r.kind for r in records}
        kind = ("journal" if "journal" in kinds else "preprint" if "preprint" in kinds
                else "other" if kinds else "no_record_metadata")
        classes[kind] += 1
        if kind == "journal":
            titles = sorted({r.journal for r in records if r.kind == "journal" and r.journal})
            journals[titles[0] if titles else "journal_not_recorded"] += 1
    n = len(meta)
    ranked = sorted(journals.items(), key=lambda kv: (-kv[1], kv[0]))
    return {"eligible_families": n, "families_by_document_class": dict(sorted(classes.items())),
            "preprint_only_share": share(classes["preprint"], n),
            "wilson_descriptive_preprint_only": wilson(classes["preprint"], n),
            "journals": len(journals),
            "journals_with_most_families": [{"journal": j, "families": k}
                                            for j, k in ranked[:TOP_N]]}


# --- accounting -------------------------------------------------------------------------------

def accounting(registry: Registry, claims: list[RegistryClaim],
               assembly_report: Mapping | None = None,
               meta: Mapping[str, dict] | None = None,
               dates: ClaimDates | None = None) -> list[dict]:
    """One row per index and per registered secondary: its unit, its denominator, the count in
    it and what left it. An index read over edges has a pair-level count (`n`, the pairs that
    hold the edges, which the pair bootstrap resamples) and an edge-level count (`edge_n`)
    with their own denominators."""
    multi = multi_family(registry)
    two_dir = [f for f in registry.values() if sum(directional(x) for x in f.values()) >= 2]
    h1 = [h for h in (pair_h1(f) for f in registry.values()) if h is not None and h.in_h1]
    fps = [fp for fams in registry.values() for fp in fams.values()]
    left_claims = dict((assembly_report or {}).get("registry", {}).get("left_out_by_reason", {}))
    dir_edges = directional_edges(registry)
    n_dir_edges = sum(len(p["edges"]) for p in dir_edges)
    multi_edges = sum(len(edges(f)) for f in multi.values())
    null_edges = sum(sum(directional(a) for a in f.values())
                     * sum(b.direction == "nonsignificant_only" for b in f.values())
                     for f in multi.values())
    later_dir = sum(len([f for f in fams.values() if directional(f)]) - 1
                    for fams in registry.values()
                    if sum(directional(f) for f in fams.values()) >= 2)
    families_with_claims = len({c.family_id for c in claims})
    n_families = len(meta) if meta is not None else None
    later_units = None
    if dates is not None:
        later_units = sum(
            any(f != g and date_order(dates[(f, pair)], dates[(g, pair)]) == "earlier"
                for f in fams)
            for pair, fams in multi.items() for g in fams)

    def row(index: str, unit: str, denominator: str, n: int | None, left: dict | None = None,
            edge_denominator: str | None = None, edge_n: int | None = None) -> dict:
        return {"index": index, "unit": unit, "denominator": denominator, "n": n,
                "left": left or {}, "edge_denominator": edge_denominator, "edge_n": edge_n}

    return [
        row("registry claim records", "claim record",
            "verified claim records of registry abstracts with a pair", len(claims), left_claims),
        row("distinct pairs; papers per pair", "pair", "registry pairs", len(registry)),
        row("H2; H2b; resolvable share", "pair",
            "pairs with at least two families, any direction value", len(multi),
            {"pairs_with_one_family": len(registry) - len(multi)}),
        row("family–pair direction counts", "family–pair record", "family–pair records",
            len(fps)),
        row("contradicting pairs; Liu-analogue", "pair",
            "pairs with at least two directional families", len(two_dir),
            {"pairs_with_fewer_than_two_directional_families": len(registry) - len(two_dir)}),
        row("H1", "pair",
            "pairs with at least one independent edge between directional families", len(h1),
            {"pairs_with_two_directional_families_and_no_independent_edge":
             len(two_dir) - len(h1)},
            "independent edges between directional families",
            sum(h.independent_edges for h in h1)),
        row("direction-based results", "family–pair record", "directional family–pair records",
            sum(directional(fp) for fp in fps),
            dict(sorted(collections.Counter(
                fp.direction for fp in fps if not directional(fp)).items()))),
        row("reporting_completeness; dataset_usage", "study family",
            "eligible families with a registry claim record", families_with_claims,
            {"eligible_families_without_a_registry_claim":
             n_families - families_with_claims} if n_families is not None else None),
        row("edge_relations", "edge", "pairs with at least two families", len(multi), None,
            "every two families of those pairs", multi_edges),
        row("h2_by_families_per_pair", "pair", "pairs with at least two families", len(multi)),
        row("h2_directional_pairs", "pair", "pairs with at least two directional families",
            len(two_dir)),
        row("direction_agreement_by_edge_class; contradiction_source_comparison; "
            "platform_pairing", "edge", "pairs with at least one edge between directional "
            "families", len(dir_edges), None, "edges between directional families",
            n_dir_edges),
        row("significance_discordance", "pair", "pairs with at least two families", len(multi),
            None, "edges between a directional and a nonsignificant_only family", null_edges),
        row("first_claim_concordance", "later directional family on a pair",
            "pairs with at least two directional families (a pair with no strictly earliest "
            "claim date is tied_first)", len(two_dir), None,
            "directional families other than one per pair", later_dir),
        row("periods; therapeutic_areas: distinct pairs", "pair",
            "registry pairs, each in the period of its first claim date or in each area of its "
            "outcome", len(registry)),
        row("periods; therapeutic_areas: repeated-pair indices", "pair",
            "pairs with at least two families, each in the period of its second claim date or "
            "in each area of its outcome", len(multi)),
        row("yearly_series; claims_per_family; source_overlap; document_class_and_journals",
            "study family", "eligible families", n_families),
        row("top_lists", "pair, protein, outcome", "registry pairs", len(registry)),
        row("wording_by_repetition_and_year", "claim record", "registry claim records",
            len(claims)),
        row("citation_of_earlier_claim", "later family on a repeated pair",
            "family–pair records with another family strictly earlier by claim date",
            later_units),
    ]


def secondaries(claims: list[RegistryClaim], tags: Mapping[str, ClaimTags], registry: Registry,
                meta: Mapping[str, dict],
                areas_of_outcome: Callable[[str], tuple[frozenset[str], str]],
                families: Mapping[str, list[str]], record_meta: Mapping[str, RecordMeta],
                novelty: Mapping[str, dict] | None = None,
                assembly_report: Mapping | None = None,
                row_platform: Mapping[str, str] | None = None,
                n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Every registered secondary of the registry. `families` maps a family to its record ids
    (families.json), `record_meta` a record id to its metadata, `novelty` a claim record id to
    its novelty record (scripts/novelty.py), which carries the claim date every ordering of
    families on a pair uses."""
    row_platform = load_row_platforms() if row_platform is None else row_platform
    if novelty is None:
        raise ValueError("the novelty records are required: they carry the claim dates")
    dates = pair_claim_dates(claims, novelty)
    return {
        "bootstrap": {"replicates": n_boot, "seed": seed, "streams": STREAMS,
                      "percentile_method": "inverted_cdf"},
        "reporting_completeness": reporting_completeness(registry, claims, tags, meta),
        "dataset_usage": dataset_usage(registry),
        "edge_relations": edge_relations(registry, n_boot, seed),
        "h2_by_families_per_pair": h2_by_families_per_pair(registry, n_boot, seed),
        "h2_directional_pairs": h2_directional_pairs(registry, n_boot, seed),
        "direction_agreement_by_edge_class": direction_agreement_by_edge_class(
            registry, n_boot, seed),
        "significance_discordance": significance_discordance(registry, n_boot, seed),
        "contradiction_source_comparison": contradiction_source_comparison(
            registry, claims, tags, n_boot, seed),
        "first_claim_concordance": first_claim_concordance(registry, dates, n_boot, seed),
        "periods": periods(registry, dates, n_boot, seed),
        "yearly_series": yearly_series(registry, claims, meta, dates),
        "therapeutic_areas": therapeutic_areas(registry, areas_of_outcome, n_boot, seed),
        "platform_pairing": platform_pairing(registry, row_platform, n_boot, seed),
        "claims_per_family": claims_per_family(meta),
        "top_lists": top_lists(registry, claims),
        "wording_by_repetition_and_year": wording_by_repetition_and_year(
            registry, claims, tags, meta),
        "citation_of_earlier_claim": citation_of_earlier_claim(
            registry, dates, meta, record_meta, novelty, claims),
        "source_overlap": source_overlap(meta, families, record_meta),
        "document_class_and_journals": document_class_and_journals(meta, record_meta),
        "accounting": accounting(registry, claims, assembly_report, meta, dates),
    }
