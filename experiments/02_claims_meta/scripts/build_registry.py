# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""Build the pair registry from verified claim records and compute the H1 and H2 tables.

Input: one JSON line per registry claim record (a claim that passed span, evidence-type,
protein and outcome checks), carrying its study family, canonical pair and verification state
(`RegistryClaim` below). No model is called.

Pair. A pair is UniProt accession × canonical outcome identifier (`canonical_ids.py`). The
verifier's HGNC entries become one reviewed UniProt accession through the pinned HGNC
`uniprot_ids` and the pinned UniProt file, and its Mondo/EFO identifiers become one canonical
identifier through `verification/mondo_efo_collision_table.csv`. A record with more than one
accession (a complex, or a gene with several reviewed entries) or more than one canonical outcome
identifier gives no pair and is counted `pair_ambiguous`, with the reason; a record with no
reviewed accession is counted `protein_no_uniprot`. The HGNC and source outcome identifiers stay
on the record.

Family–pair records. Records of one family on one pair are deduplicated when their context key
and direction are identical. Each record's effective direction is Sol's direction when the
verifier agreed with it, else `unverified`. The family–pair direction is, first that applies:

    mixed                        at least one verified `raises` and one verified `lowers`
    raises / lowers              verified directional records all in one direction
    ..._with_nonsignificant      the same, and the family also has a verified
                                 `reported_nonsignificant_or_null` record on the pair
    nonsignificant_only          only verified `reported_nonsignificant_or_null` records
    unresolved                   otherwise (`not_stated` or unverified records only)

`context_unclear` is set on the family–pair when any record has `claim_scope` `unclear`; it never
changes the direction. The family–pair datasets are the union, per side, of the names on its
records; the family's attribution is clear only when no record has `dataset_attribution`
`unclear`. The names of its `claim_specific` records are kept apart as well.

H1 (descriptive). Directional families are those whose family–pair direction is `raises`,
`lowers` or either `_with_nonsignificant` form (read as its direction). Every two directional
families on a pair form an edge labelled by `dataset_relations.edge_label`. The H1 set is the
pairs with at least one `independent` edge. Pair-level concordance: the share of H1 pairs whose
independent edges all join families of the same direction. Edge-level concordance: the share of
independent edges joining families of the same direction. Liu-analogue (secondary): over pairs
with at least two directional families, C = (concordant − discordant) / (concordant +
discordant) over all edges between directional families, whatever their datasets, with the tiers
of Liu et al. 2025 (high ≥ 0.7, moderate 0.5–0.69, low 0.0–0.49, discordant < 0).

Release identity of two families on one side (`family_release_identity`): `undetermined`
when either family's attribution is unclear; otherwise scripts/dataset_relations.py
`release_identity` of their names.

H2. Multi-family pairs are pairs announced by at least two families (any direction). A pair is
`known_identical` when every two of its families have release identity `identical` on both
sides, `known_not_identical` when any two have `not_identical` on either side, `unresolved`
otherwise. Lower bound = known_identical / multi-family pairs; upper bound = (known_identical +
unresolved) / multi-family pairs; complete-case = known_identical / (known_identical +
known_not_identical).

H2b (`pair_overlap`). A comparison of two families on one side is `overlapping` when the
release identity is `identical` or the dataset relation is `identical_release` or
`overlapping_participant_source`; when a family's attribution is unclear, also when the names of
its `claim_specific` records (and the other family's names, or its `claim_specific` names when
its attribution is unclear too) have one of those two relations; `disjoint` when the relation is
`disjoint`; `unclear` otherwise. A pair is `known_overlapping` when every comparison of every
two of its families on both sides is `overlapping`, `known_not_overlapping` when any is
`disjoint`, `unresolved` otherwise; the bounds are H2's. Every `known_identical` pair is
`known_overlapping`.

Verdicts (finite corpus). The H2 verdict is read on the observed bounds: `supported` when the
lower bound is greater than 0.5, `contradicted` when the upper bound is at or below 0.5,
`unresolved` otherwise; H2b the same on its bounds. H1 has no verdict. `two_verdict_reading`
names the registered reading of the two verdicts together. The resolvable share is the share of
multi-family pairs in which every family's attribution is clear and every dataset name of every
family maps to one release on both sides; only such a pair can be `known_identical`, so it is
the largest value the H2 lower bound can take, and "H2 supported" is attainable only when it is
above 0.5 (`h2_supported_attainable`).

Resampling stability (sensitivity displays; none sets a verdict). Pair bootstrap: 10,000
replicates resampling the pairs of each estimand's denominator with replacement, seed 20261001;
the 2.5th and 97.5th percentiles by the inverted-CDF rule, so each endpoint is an attained
replicate value; H2b and the resolvable share are read on the same replicates as H2. It does not
model the dependence between pairs that share families, proteins or datasets. Family-deletion
range (`family_jackknife`): every estimate recomputed with each family removed in turn (a pair
can leave a denominator when a family is removed); the minimum, maximum and the family giving
each. Protein-cluster bootstrap: proteins are resampled with replacement and every pair of a
sampled protein enters; each estimate is the ratio of the summed numerators and denominators.
Wilson 95% intervals are naive descriptive intervals.

Usage: uv run scripts/build_registry.py --claims <registry_claims.jsonl> --out <dir>
"""

import argparse
import collections
import datetime
import hashlib
import itertools
import json
import math
import pathlib
from collections.abc import Mapping
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict

from canonical_ids import (canonical_outcomes, load_collision_table, load_hgnc_uniprot,
                           outcome_candidates, phenotype_term, protein_accession)
from dataset_relations import (NameMapping, Row, compare_side, edge_label, load_rows, map_name,
                               release_identity)

EXP = pathlib.Path(__file__).resolve().parent.parent
COLLISION_TABLE = EXP / "verification" / "mondo_efo_collision_table.csv"
SEED = 20261001
N_BOOT = 10_000
DIRECTIONAL = {"raises": "raises", "lowers": "lowers", "raises_with_nonsignificant": "raises",
               "lowers_with_nonsignificant": "lowers"}
NONSIG = "reported_nonsignificant_or_null"
LIU_TIERS = (("high", 0.7), ("moderate", 0.5), ("low", 0.0))
OVERLAP = ("identical_release", "overlapping_participant_source")
READINGS = {
    ("supported", "supported"): "majority_on_identical_releases",
    ("unresolved", "supported"): "majority_on_identical_or_overlapping_sources_identical_not_shown",
    ("contradicted", "supported"): "majority_on_overlapping_sources_identical_at_most_half",
    ("unresolved", "unresolved"): "neither_share_placed_on_one_side_of_one_half",
    ("contradicted", "unresolved"): "identical_at_most_half_overlap_not_placed",
    ("contradicted", "contradicted"): "at_most_half_on_identical_or_overlapping_sources",
}

Scope = Literal["overall", "dataset_specific", "ancestry_specific", "subgroup_specific",
                "sensitivity", "unclear"]
Attribution = Literal["claim_specific", "whole_study", "unclear"]


class RegistryClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    claim_record_id: str
    family_id: str
    protein_id: str
    outcome_id: str
    direction: Literal["raises", "lowers", "reported_nonsignificant_or_null", "not_stated"]
    direction_verified: bool
    claim_scope: Scope
    context_key: str
    pqtl_datasets: tuple[str, ...]
    outcome_datasets: tuple[str, ...]
    dataset_attribution: Attribution
    hgnc_ids: tuple[str, ...] = ()
    outcome_source_ids: tuple[str, ...] = ()
    manual_dataset_codes: tuple[str, ...] = ()


class FamilyPair(BaseModel):
    family_id: str
    pair: tuple[str, str]
    direction: str
    context_unclear: bool
    n_records: int
    pqtl: list[NameMapping]
    outcome: list[NameMapping]
    attribution_clear: bool
    pqtl_claim_specific: list[NameMapping] = []
    outcome_claim_specific: list[NameMapping] = []
    manually_coded: bool = False


ManualCodes = Mapping[tuple[str, str, str], str]


Registry = dict[tuple[str, str], dict[str, FamilyPair]]


class PinnedFileError(Exception):
    """A file named in reference/MANIFEST.json is absent or is not the pinned release."""


def pinned_file(spec: dict, root: pathlib.Path | None = None) -> pathlib.Path:
    """The path of a file named in reference/MANIFEST.json, present and with its sha256."""
    path = (root or EXP) / spec["file"]
    if not path.is_file():
        raise PinnedFileError(f"{spec['file']} missing; fetch it from the Modal volume "
                              "(inputs/README_MOVED_TO_MODAL.md)")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != spec["sha256"]:
        raise PinnedFileError(f"{spec['file']}: sha256 {digest[:12]} differs from "
                              f"reference/MANIFEST.json ({spec['sha256'][:12]})")
    return path


def canonical_inputs() -> tuple[dict[str, frozenset[str]], dict[str, frozenset[str]]]:
    """The pinned HGNC -> UniProt map (files named in reference/MANIFEST.json, each checked
    against the sha256 recorded there) and the committed collision table."""
    manifest = json.loads((EXP / "reference" / "MANIFEST.json").read_text())
    return (load_hgnc_uniprot(pinned_file(manifest["hgnc"]), pinned_file(manifest["uniprot"])),
            load_collision_table(COLLISION_TABLE))


def registry_claims_from_checks(checks: list[dict], family_of_pmid: dict[str, str],
                                hgnc_uniprot: dict[str, frozenset[str]],
                                collision: dict[str, frozenset[str]], mondo_first: bool = False,
                                manual: ManualCodes | None = None
                                ) -> tuple[list[RegistryClaim], dict[str, int], dict[str, int]]:
    """Registry claims from verify_claims.py records, keyed on UniProt accession × canonical
    outcome identifier. Returns the claims, the count of records left out by reason, and the
    `pair_ambiguous` records by reason. The last also counts, under
    `outcome_other_ontology_candidates_dropped`, the records that enter with one MONDO or EFO
    identifier after candidates from other ontologies were dropped, and under
    `outcome_phenotype_cross_reference_applied` the records whose phenotype identifiers were
    replaced by the disease term that cross-references them (canonical_ids.py).

    `manual` holds the manually coded dataset names (scripts/manual_dataset_coding.py): for a
    key (record id, side, name as written) the dictionary row the paper was read to use. The
    claim then carries the row's name in place of the written name, and lists the replacement
    in `manual_dataset_codes` (`side|name as written|row`)."""
    manual = manual or {}
    out, dropped, ambiguous = [], collections.Counter(), collections.Counter()
    for c in checks:
        if not c["enters_registry"]:
            dropped[c["first_failure"]] += 1
            continue
        acc, p_state, _ = protein_accession(c["protein_ids"], hgnc_uniprot)
        outcomes = canonical_outcomes(c["outcome_ids"], collision, mondo_first)
        if p_state in ("no_uniprot", "no_hgnc"):
            dropped[f"protein_{p_state}"] += 1
            continue
        if p_state == "multiple_uniprot" or len(outcomes) != 1:
            dropped["pair_ambiguous"] += 1
            if p_state == "multiple_uniprot":
                ambiguous["protein_multiple_uniprot"] += 1
            if len(outcomes) != 1:
                ambiguous["outcome_multiple_canonical"] += 1
            continue
        candidates = outcome_candidates(c["outcome_ids"], collision)
        if phenotype_term(candidates, collision) is not None:
            ambiguous["outcome_phenotype_cross_reference_applied"] += 1
        elif len(candidates) > 1:
            ambiguous["outcome_other_ontology_candidates_dropped"] += 1
        context = " ".join(f"{c['analysis_context_as_written']} | {c['subgroup_as_written']}"
                           .lower().split())
        datasets, coded = {}, []
        for side, field in (("pqtl", "pqtl_datasets"), ("outcome", "outcome_datasets")):
            names = []
            for name in c[field]:
                row = manual.get((c["pmid"], side, name))
                if row is not None:
                    coded.append(f"{side}|{name}|{row}")
                names.append(name if row is None else row)
            datasets[field] = tuple(dict.fromkeys(names))
        out.append(RegistryClaim(
            claim_record_id=c["claim_record_id"], family_id=family_of_pmid[c["pmid"]],
            protein_id=acc, outcome_id=outcomes[0],
            direction=c["direction"],
            direction_verified=c["direction_verification_state"] == "agrees",
            claim_scope=c["claim_scope"], context_key=context,
            pqtl_datasets=datasets["pqtl_datasets"],
            outcome_datasets=datasets["outcome_datasets"],
            dataset_attribution=c["dataset_attribution"],
            hgnc_ids=tuple(c["protein_ids"]), outcome_source_ids=tuple(c["outcome_ids"]),
            manual_dataset_codes=tuple(coded)))
    return out, dict(dropped), dict(ambiguous)


def effective(c: RegistryClaim) -> str:
    if c.direction == "not_stated":
        return "not_stated"
    return c.direction if c.direction_verified else "unverified"


def family_pair_direction(records: list[RegistryClaim]) -> str:
    dirs = {effective(c) for c in records}
    directional = dirs & {"raises", "lowers"}
    if len(directional) == 2:
        return "mixed"
    if directional:
        d = directional.pop()
        return f"{d}_with_nonsignificant" if NONSIG in dirs else d
    return "nonsignificant_only" if NONSIG in dirs else "unresolved"


def build(claims: list[RegistryClaim], rows: list[Row]) -> Registry:
    cache: dict[tuple[str, str], NameMapping] = {}

    def mapped(name: str, side: str) -> NameMapping:
        if (name, side) not in cache:
            cache[(name, side)] = map_name(name, side, rows)
        return cache[(name, side)]

    grouped: dict[tuple[str, str], dict[str, list[RegistryClaim]]] = collections.defaultdict(
        lambda: collections.defaultdict(list))
    every: dict[tuple[str, str], dict[str, list[RegistryClaim]]] = collections.defaultdict(
        lambda: collections.defaultdict(list))
    seen: set[tuple] = set()
    for c in claims:
        every[(c.protein_id, c.outcome_id)][c.family_id].append(c)
        key = (c.family_id, c.protein_id, c.outcome_id, c.context_key, effective(c))
        if key in seen:
            continue
        seen.add(key)
        grouped[(c.protein_id, c.outcome_id)][c.family_id].append(c)
    registry: Registry = {}
    for pair, fams in grouped.items():
        registry[pair] = {}
        for fam, recs in fams.items():
            # Deduplicated records set the direction; every record contributes its datasets.
            allrecs = every[pair][fam]
            pq = sorted({n for c in allrecs for n in c.pqtl_datasets})
            oc = sorted({n for c in allrecs for n in c.outcome_datasets})
            specific = [c for c in allrecs if c.dataset_attribution == "claim_specific"]
            pq_cs = sorted({n for c in specific for n in c.pqtl_datasets})
            oc_cs = sorted({n for c in specific for n in c.outcome_datasets})
            registry[pair][fam] = FamilyPair(
                family_id=fam, pair=pair, direction=family_pair_direction(recs),
                context_unclear=any(c.claim_scope == "unclear" for c in recs),
                n_records=len(recs), pqtl=[mapped(n, "pqtl") for n in pq],
                outcome=[mapped(n, "outcome") for n in oc],
                attribution_clear=all(c.dataset_attribution != "unclear" for c in allrecs),
                pqtl_claim_specific=[mapped(n, "pqtl") for n in pq_cs],
                outcome_claim_specific=[mapped(n, "outcome") for n in oc_cs],
                manually_coded=any(c.manual_dataset_codes for c in allrecs))
    return registry


def edge(a: FamilyPair, b: FamilyPair) -> str:
    pq = compare_side(a.pqtl, b.pqtl, a.attribution_clear, b.attribution_clear)
    oc = compare_side(a.outcome, b.outcome, a.attribution_clear, b.attribution_clear)
    return edge_label(pq, oc)


class PairH1(BaseModel):
    pair: tuple[str, str]
    families: list[str]
    n_directional_families: int
    independent_edges: int
    independent_agreeing: int
    all_edges: int
    all_concordant: int
    in_h1: bool
    agrees: bool | None
    liu_c: float | None


def pair_h1(fams: dict[str, FamilyPair]) -> PairH1 | None:
    d = sorted((f for f in fams.values() if f.direction in DIRECTIONAL),
               key=lambda f: f.family_id)
    if len(d) < 2:
        return None
    ind = ind_agree = conc = disc = 0
    for a, b in itertools.combinations(d, 2):
        same = DIRECTIONAL[a.direction] == DIRECTIONAL[b.direction]
        conc += same
        disc += not same
        if edge(a, b) == "independent":
            ind += 1
            ind_agree += same
    return PairH1(pair=d[0].pair, families=[f.family_id for f in d],
                  n_directional_families=len(d), independent_edges=ind,
                  independent_agreeing=ind_agree, all_edges=conc + disc, all_concordant=conc,
                  in_h1=ind > 0, agrees=(ind_agree == ind) if ind else None,
                  liu_c=(conc - disc) / (conc + disc))


def family_release_identity(a: FamilyPair, b: FamilyPair, side: str) -> str:
    """Release identity of two families on one side: `undetermined` when either family's
    attribution is unclear, so a name not tied to the claim never makes two families
    identical; otherwise the identity of their names."""
    if not (a.attribution_clear and b.attribution_clear):
        return "undetermined"
    return release_identity(getattr(a, side), getattr(b, side))


def pair_h2(fams: Mapping[str, FamilyPair]) -> str | None:
    if len(fams) < 2:
        return None
    ids = []
    for a, b in itertools.combinations(sorted(fams), 2):
        ids.append(family_release_identity(fams[a], fams[b], "pqtl"))
        ids.append(family_release_identity(fams[a], fams[b], "outcome"))
    if all(i == "identical" for i in ids):
        return "known_identical"
    if "not_identical" in ids:
        return "known_not_identical"
    return "unresolved"


def side_overlap(fa: FamilyPair, fb: FamilyPair, side: str) -> str:
    """`overlapping`, `disjoint` or `unclear` for two families on one side. When a family's
    attribution is unclear, overlap can still be established from the names of its
    `claim_specific` records, which are tied to the claim: a shared component among them is a
    shared component of the data. Disjointness is never read from such a subset."""
    na, nb = getattr(fa, side), getattr(fb, side)
    relation = compare_side(na, nb, fa.attribution_clear, fb.attribution_clear)
    if relation in OVERLAP or family_release_identity(fa, fb, side) == "identical":
        return "overlapping"
    if relation == "disjoint":
        return "disjoint"
    if not (fa.attribution_clear and fb.attribution_clear):
        sa = na if fa.attribution_clear else getattr(fa, f"{side}_claim_specific")
        sb = nb if fb.attribution_clear else getattr(fb, f"{side}_claim_specific")
        if sa and sb and compare_side(sa, sb) in OVERLAP:
            return "overlapping"
    return "unclear"


def pair_overlap(fams: Mapping[str, FamilyPair]) -> str | None:
    """H2b class of a pair: every comparison of every two families on both sides `overlapping`
    (`known_overlapping`), any `disjoint` (`known_not_overlapping`), else `unresolved`
    (`side_overlap`). Every `known_identical` pair is `known_overlapping`."""
    if len(fams) < 2:
        return None
    states = []
    for a, b in itertools.combinations(sorted(fams), 2):
        for side in ("pqtl", "outcome"):
            states.append(side_overlap(fams[a], fams[b], side))
    if all(s == "overlapping" for s in states):
        return "known_overlapping"
    return "known_not_overlapping" if "disjoint" in states else "unresolved"


def pair_resolvable(fams: Mapping[str, FamilyPair]) -> bool | None:
    """Whether every family of a multi-family pair has clear attribution and every dataset name
    of every family maps to one release on both sides; only such a pair can be
    `known_identical`."""
    if len(fams) < 2:
        return None
    return all(fp.attribution_clear and names and all(m.state == "unique" for m in names)
               for fp in fams.values() for names in (fp.pqtl, fp.outcome))


def wilson(k: int, n: int, z: float = 1.959963984540054) -> list[float] | None:
    if n == 0:
        return None
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [mid - half, mid + half]


def liu_tier(c: float) -> str:
    for name, lo in LIU_TIERS:
        if c >= lo:
            return name
    return "discordant"


def estimates(registry: Registry) -> dict:
    """Every H1 and H2 estimate, with the per-pair values the bootstrap resamples."""
    h1 = [p for p in (pair_h1(f) for f in registry.values()) if p is not None]
    h1_set = [p for p in h1 if p.in_h1]
    multi = {pair: f for pair, f in registry.items() if len(f) >= 2}
    h2 = [pair_h2(f) for f in multi.values()]
    h2b = [pair_overlap(f) for f in multi.values()]
    resolvable = [bool(pair_resolvable(f)) for f in multi.values()]
    n2 = len(h2)
    k_id, k_not = h2.count("known_identical"), h2.count("known_not_identical")
    k_un = h2.count("unresolved")
    b_id, b_not = h2b.count("known_overlapping"), h2b.count("known_not_overlapping")
    b_un = h2b.count("unresolved")
    not_nested = sum((a == "known_identical" and b != "known_overlapping")
                     or (a != "known_not_identical" and b == "known_not_overlapping")
                     for a, b in zip(h2, h2b))
    edges_ind = sum(p.independent_edges for p in h1_set)
    return {
        "h1_pairs": len(h1_set),
        "h1_pairs_agreeing": sum(bool(p.agrees) for p in h1_set),
        "h1_pair_concordance": (sum(bool(p.agrees) for p in h1_set) / len(h1_set)
                                if h1_set else None),
        "h1_independent_edges": edges_ind,
        "h1_independent_edges_agreeing": sum(p.independent_agreeing for p in h1_set),
        "h1_edge_concordance": (sum(p.independent_agreeing for p in h1_set) / edges_ind
                                if edges_ind else None),
        "liu_analogue_pairs": len(h1),
        "liu_analogue_tiers": dict(collections.Counter(liu_tier(p.liu_c) for p in h1)),
        "liu_analogue_share_not_discordant": (sum(p.liu_c >= 0 for p in h1) / len(h1)
                                              if h1 else None),
        "h2_multi_family_pairs": n2,
        "h2_known_identical": k_id,
        "h2_known_not_identical": k_not,
        "h2_unresolved": k_un,
        "h2_lower": k_id / n2 if n2 else None,
        "h2_upper": (k_id + k_un) / n2 if n2 else None,
        "h2_complete_case": k_id / (k_id + k_not) if (k_id + k_not) else None,
        "h2_resolvable_pairs": sum(resolvable),
        "h2_resolvable_share": sum(resolvable) / n2 if n2 else None,
        "h2b_known_overlapping": b_id,
        "h2b_known_not_overlapping": b_not,
        "h2b_unresolved": b_un,
        "h2b_lower": b_id / n2 if n2 else None,
        "h2b_upper": (b_id + b_un) / n2 if n2 else None,
        "h2b_complete_case": b_id / (b_id + b_not) if (b_id + b_not) else None,
        "h2_h2b_pairs_not_nested": not_nested,
        "_h1_set": h1_set,
        "_h2": h2,
        "_h2b": h2b,
        "_h2_resolvable": resolvable,
        "_h2_proteins": [pair[0] for pair in multi],
    }


def quantiles(x: np.ndarray, levels: tuple[float, float] = (0.025, 0.975)) -> list[float]:
    return [float(v) for v in np.quantile(x, list(levels), method="inverted_cdf")]


def pair_bootstrap(est: dict, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    rng = np.random.default_rng(seed)
    out: dict = {"replicates": n_boot, "seed": seed, "percentile_method": "inverted_cdf"}
    h1_set = est["_h1_set"]
    if h1_set:
        agree = np.array([bool(p.agrees) for p in h1_set], dtype=float)
        ind = np.array([p.independent_edges for p in h1_set], dtype=float)
        ind_ag = np.array([p.independent_agreeing for p in h1_set], dtype=float)
        idx = rng.integers(0, len(h1_set), size=(n_boot, len(h1_set)))
        out["h1_pair_concordance"] = quantiles(agree[idx].mean(axis=1))
        out["h1_edge_concordance"] = quantiles(ind_ag[idx].sum(axis=1) / ind[idx].sum(axis=1))
    h2 = est["_h2"]
    if h2:
        ident = np.array([c == "known_identical" for c in h2], dtype=float)
        upper = np.array([c in ("known_identical", "unresolved") for c in h2], dtype=float)
        idx = rng.integers(0, len(h2), size=(n_boot, len(h2)))
        replicates = {"h2_lower": ident[idx].mean(axis=1), "h2_upper": upper[idx].mean(axis=1)}
        # H2b and the resolvable share are read on the same replicates as H2.
        h2b = est.get("_h2b")
        if h2b:
            over = np.array([c == "known_overlapping" for c in h2b], dtype=float)
            over_up = np.array([c in ("known_overlapping", "unresolved") for c in h2b],
                               dtype=float)
            replicates["h2b_lower"] = over[idx].mean(axis=1)
            replicates["h2b_upper"] = over_up[idx].mean(axis=1)
        if est.get("_h2_resolvable"):
            res = np.array(est["_h2_resolvable"], dtype=float)
            replicates["h2_resolvable_share"] = res[idx].mean(axis=1)
        for key, values in replicates.items():
            out[key] = quantiles(values)
    return out


def protein_cluster_bootstrap(est: dict, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Sensitivity: proteins resampled with replacement, each with all its pairs; every
    estimate is the ratio of the summed numerators and denominators of the sampled proteins."""
    rng = np.random.default_rng([seed, 1])
    out: dict = {"replicates": n_boot, "seed": [seed, 1], "unit": "protein",
                 "percentile_method": "inverted_cdf"}

    def ratios(proteins: list[str], numerators: dict[str, list[float]],
               denominator: list[float]) -> dict[str, list[float]]:
        names = sorted(set(proteins))
        at = {p: i for i, p in enumerate(names)}
        den = np.zeros(len(names))
        num = {k: np.zeros(len(names)) for k in numerators}
        for j, p in enumerate(proteins):
            den[at[p]] += denominator[j]
            for k, values in numerators.items():
                num[k][at[p]] += values[j]
        idx = rng.integers(0, len(names), size=(n_boot, len(names)))
        total = den[idx].sum(axis=1)
        return {k: quantiles(v[idx].sum(axis=1) / total) for k, v in num.items()}

    h1_set = est["_h1_set"]
    if h1_set:
        proteins = [p.pair[0] for p in h1_set]
        out["h1_proteins"] = len(set(proteins))
        out.update(ratios(proteins, {"h1_pair_concordance": [float(bool(p.agrees))
                                                              for p in h1_set]},
                          [1.0] * len(h1_set)))
        out.update(ratios(proteins, {"h1_edge_concordance": [float(p.independent_agreeing)
                                                              for p in h1_set]},
                          [float(p.independent_edges) for p in h1_set]))
    h2 = est["_h2"]
    if h2 and est.get("_h2_proteins"):
        proteins = est["_h2_proteins"]
        out["h2_proteins"] = len(set(proteins))
        numerators = {"h2_lower": [float(c == "known_identical") for c in h2],
                      "h2_upper": [float(c in ("known_identical", "unresolved")) for c in h2]}
        if est.get("_h2b"):
            numerators["h2b_lower"] = [float(c == "known_overlapping") for c in est["_h2b"]]
            numerators["h2b_upper"] = [float(c in ("known_overlapping", "unresolved"))
                                       for c in est["_h2b"]]
        out.update(ratios(proteins, numerators, [1.0] * len(h2)))
    return out


def h2_verdict(est: Mapping, hypothesis: str = "h2") -> str:
    """The three-way verdict of `hypothesis` (`h2` or `h2b`) on its observed finite-corpus
    bounds: `supported` when the lower bound is greater than 0.5, `contradicted` when the upper
    bound is at or below 0.5, else `unresolved`."""
    lower, upper = est.get(f"{hypothesis}_lower"), est.get(f"{hypothesis}_upper")
    if lower is None or upper is None:
        return "no_multi_family_pairs"
    if lower > 0.5:
        return "supported"
    if upper <= 0.5:
        return "contradicted"
    return "unresolved"


def two_verdict_reading(h2: str, h2b: str) -> str:
    """The registered reading of the H2 and H2b verdicts together. H2 supported implies H2b
    supported and H2b contradicted implies H2 contradicted, so three combinations cannot occur;
    one that does is reported as `not_nested` with `h2_h2b_pairs_not_nested`."""
    if "no_multi_family_pairs" in (h2, h2b):
        return "no_multi_family_pairs"
    return READINGS.get((h2, h2b), "not_nested")


def family_jackknife(registry: Registry) -> dict:
    families = sorted({f for fams in registry.values() for f in fams})
    keys = ("h1_pair_concordance", "h1_edge_concordance", "h2_lower", "h2_upper", "h2b_lower",
            "h2b_upper", "h2_resolvable_share")
    values: dict[str, list[tuple[float, str]]] = {k: [] for k in keys}
    for drop in families:
        reduced = {pair: {f: fp for f, fp in fams.items() if f != drop}
                   for pair, fams in registry.items()}
        e = estimates(reduced)
        for k in keys:
            if e[k] is not None:
                values[k].append((e[k], drop))
    return {k: ({"min": min(v)[0], "min_when_dropping": min(v)[1], "max": max(v)[0],
                 "max_when_dropping": max(v)[1], "n_deletions": len(v)} if v else None)
            for k, v in values.items()}


class PublicDate(BaseModel):
    model_config = ConfigDict(frozen=True)
    value: datetime.date
    resolution: Literal["day", "month", "year"]


def date_order(a: PublicDate, b: PublicDate) -> Literal["earlier", "later", "tied_or_unknown"]:
    """Order of two first-public dates at the least precise resolution the two share."""
    res = min(a.resolution, b.resolution, key=("year", "month", "day").index)
    width = {"year": 1, "month": 2, "day": 3}[res]
    ka = (a.value.year, a.value.month, a.value.day)[:width]
    kb = (b.value.year, b.value.month, b.value.day)[:width]
    if ka == kb:
        return "tied_or_unknown"
    return "earlier" if ka < kb else "later"


def novelty_class(claim_date: PublicDate, other_family_dates: list[PublicDate]) -> str:
    """`earlier_in_registry` when another family's claim of the exact pair is strictly earlier;
    `tied_or_unknown_order` when none is earlier and at least one ties; else
    `no_earlier_in_registry`."""
    orders = [date_order(d, claim_date) for d in other_family_dates]
    if "earlier" in orders:
        return "earlier_in_registry"
    if "tied_or_unknown" in orders:
        return "tied_or_unknown_order"
    return "no_earlier_in_registry"


def denominator_report(registry: Registry) -> dict:
    fps = [fp for fams in registry.values() for fp in fams.values()]
    return {
        "family_pair_records": len(fps),
        "by_direction": dict(collections.Counter(fp.direction for fp in fps)),
        "context_unclear": sum(fp.context_unclear for fp in fps),
        "pairs": len(registry),
        "multi_family_pairs": sum(len(f) >= 2 for f in registry.values()),
        "contradicting_pairs": sum(
            {DIRECTIONAL[fp.direction] for fp in f.values() if fp.direction in DIRECTIONAL}
            == {"raises", "lowers"} for f in registry.values()),
        "family_pair_records_with_a_manually_coded_dataset": sum(fp.manually_coded for fp in fps),
        "multi_family_pairs_with_a_manually_coded_dataset": sum(
            len(f) >= 2 and any(fp.manually_coded for fp in f.values())
            for f in registry.values()),
        "h1_pairs_with_a_manually_coded_dataset": sum(
            (h := pair_h1(f)) is not None and h.in_h1 and any(
                fp.manually_coded for fp in f.values()) for f in registry.values()),
    }


def tables(registry: Registry, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    est = estimates(registry)
    boot = pair_bootstrap(est, n_boot, seed)
    public = {k: v for k, v in est.items() if not k.startswith("_")}
    return {
        "denominators": denominator_report(registry),
        "estimates": public,
        "wilson_descriptive": {
            "h1_pair_concordance": wilson(est["h1_pairs_agreeing"], est["h1_pairs"]),
            "h2_lower": wilson(est["h2_known_identical"], est["h2_multi_family_pairs"]),
            "h2_upper": wilson(est["h2_known_identical"] + est["h2_unresolved"],
                               est["h2_multi_family_pairs"]),
            "h2b_lower": wilson(est["h2b_known_overlapping"], est["h2_multi_family_pairs"]),
            "h2b_upper": wilson(est["h2b_known_overlapping"] + est["h2b_unresolved"],
                                est["h2_multi_family_pairs"]),
            "h2_resolvable_share": wilson(est["h2_resolvable_pairs"],
                                          est["h2_multi_family_pairs"]),
        },
        "verdict_rule": "finite_corpus_bounds",
        "h2_verdict": h2_verdict(est),
        "h2b_verdict": h2_verdict(est, "h2b"),
        "two_verdict_reading": two_verdict_reading(h2_verdict(est), h2_verdict(est, "h2b")),
        "h2_supported_attainable": (est["h2_resolvable_share"] is not None
                                    and est["h2_resolvable_share"] > 0.5),
        "resampling_stability": ["pair_bootstrap", "protein_cluster_bootstrap",
                                 "family_jackknife"],
        "pair_bootstrap": boot,
        "protein_cluster_bootstrap": protein_cluster_bootstrap(est, n_boot, seed),
        "family_jackknife": family_jackknife(registry),
        "imprecise_under_20_pairs": {"h1": est["h1_pairs"] < 20,
                                     "h2": est["h2_multi_family_pairs"] < 20},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    claims = [RegistryClaim.model_validate_json(l) for l in a.claims.read_text().splitlines()
              if l.strip()]
    registry = build(claims, load_rows())
    result = {"claims_file": str(a.claims), "n_claims": len(claims),
              "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
              **tables(registry)}
    a.out.mkdir(parents=True, exist_ok=True)
    out = a.out / "h1_h2_tables.json"
    if out.exists():
        raise FileExistsError(f"{out} exists; archive it before rerunning")
    out.write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
