# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.13.5"]
# ///
"""Hub proteins. No model is called.

Counted claims of a protein: its registry claims of wording class `causal` or `target`
(scripts/claim_tags.py) whose direction is not `reported_nonsignificant_or_null` (a claim
reporting no significant estimate asserts no effect; the sensitivity
`null_result_claims_counted` counts it, `count_null`).

Areas. Each outcome has the disease areas of scripts/therapeutic_areas.py (the Open Targets
26.09 therapeutic areas of its canonical term, without `measurement`, `phenotype`,
`biological_process`, `medical procedure`, `non-human animal disease` and `genetic, familial or
congenital disease`). An outcome with no disease area does not count.

A protein is a hub when the outcomes of its counted claims cannot all be covered by fewer than
3 disease areas (`therapeutic_areas.minimum_cover`): an outcome that lies in several areas adds
at most one. The sensitivity `distinct_therapeutic_areas` calls a protein a hub when its
counted outcomes lie in at least 3 distinct disease areas (`distinct_areas`).

`pleiotropic_locus_named` is set on an abstract when its text names a gene of the committed
pleiotropic-locus list (verification/pleiotropic_loci_eldjarn2023_ST36.csv, the close genes of
Eldjarn et al. 2023 ST36): the symbol occurs in the abstract, case-sensitively, with no letter
or digit on either side. A hub carries the flag when any abstract holding one of its counted
claims carries it; the genes named are listed.

Per hub: the disease areas of its counted outcomes, the minimum number of areas covering them,
the number of its counted claims, of all its registry claims and of the study families making
them, and the flag.

Expectation from claim volume (`hub_expectation`). A protein with many counted claims spans
three areas by volume alone. The outcomes of the counted claim records are permuted among those
records, which keeps each protein's number of counted records and each outcome's frequency, and
the hubs are counted again by the same rule: 1,000 permutations, `numpy.random.default_rng`
seeded `[20261001, 2]`. Reported: the observed number of hubs, the mean over the permutations,
their ratio and the 2.5th and 97.5th percentiles of the permuted counts. It is a descriptive
baseline of what volume alone gives, not a causal null model or a test, and it does not show
excess biological coherence.

Family–pair collapse (sensitivity `family_pair_collapsed`). A verbose abstract can give several
counted claim records on one pair. The sensitivity keeps one counted unit per family, protein and
outcome: the hub list is the same by construction (a hub depends on the set of counted
outcomes), the claim counts become counted family–pair records, and the expectation permutes
outcomes among those units.

Usage: uv run scripts/hub_proteins.py --claims <registry_claims.jsonl> --tags <claim_tags.jsonl>
           --ontology-edges <ontology_edges.csv> --abstracts <abstracts.jsonl> --out <dir>
"""

import argparse
import collections
import datetime
import json
import pathlib
import re
from collections.abc import Callable, Mapping

import numpy as np
from pydantic import BaseModel

from build_registry import SEED, RegistryClaim, quantiles
from claim_tags import ClaimTags, load_tags
from eldjarn_pleiotropic_loci import load_list
from ontology_graph import load_graph
from therapeutic_areas import HUB_MIN_AREAS, areas_of, load_areas, minimum_cover

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
LOCUS_LIST = EXP / "verification" / "pleiotropic_loci_eldjarn2023_ST36.csv"
HUB_WORDING = ("causal", "target")
NONSIG = "reported_nonsignificant_or_null"
N_PERMUTATIONS = 1000
PERMUTATION_STREAM = 2


class HubProtein(BaseModel):
    protein_id: str
    areas: list[str]
    minimum_areas: int
    n_distinct_areas: int
    n_counted_outcomes: int
    n_causal_or_target_claims: int
    n_registry_claims: int
    n_families: int
    pleiotropic_locus_named: bool
    pleiotropic_genes_named: list[str]


def gene_pattern(genes: frozenset[str]) -> re.Pattern:
    if not genes:
        raise ValueError("the pleiotropic-locus list is empty")
    alt = "|".join(re.escape(g) for g in sorted(genes, key=lambda g: (-len(g), g)))
    return re.compile(rf"(?<![A-Za-z0-9])(?:{alt})(?![A-Za-z0-9])")


def genes_named(text: str, pattern: re.Pattern) -> list[str]:
    """Genes of the list that the text names: case-sensitive, no letter or digit on either
    side."""
    return sorted(set(pattern.findall(text)))


def counted_claims(claims: list[RegistryClaim], tags: Mapping[str, ClaimTags],
                   count_null: bool = False, collapse: bool = False) -> list[RegistryClaim]:
    """The counted claims: wording class `causal` or `target`, direction not
    `reported_nonsignificant_or_null` unless `count_null`; with `collapse`, the first counted
    record of each family, protein and outcome only."""
    counted = [c for c in claims if tags[c.claim_record_id].wording_class in HUB_WORDING
               and (count_null or c.direction != NONSIG)]
    if not collapse:
        return counted
    seen: set[tuple[str, str, str]] = set()
    out = []
    for c in counted:
        key = (c.family_id, c.protein_id, c.outcome_id)
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def hubs(claims: list[RegistryClaim], tags: Mapping[str, ClaimTags],
         disease_areas_of: Callable[[str], frozenset[str]], abstracts: Mapping[str, str],
         genes: frozenset[str], count_null: bool = False, distinct_areas: bool = False,
         collapse: bool = False) -> tuple[list[HubProtein], dict]:
    """`disease_areas_of` gives an outcome's disease areas (possibly none)."""
    by_protein: dict[str, list[RegistryClaim]] = collections.defaultdict(list)
    for c in claims:
        by_protein[c.protein_id].append(c)
    pattern = gene_pattern(genes)
    named = {pmid: genes_named(text, pattern) for pmid, text in abstracts.items()}
    out = []
    sizes: collections.Counter = collections.Counter()
    for protein, recs in sorted(by_protein.items()):
        counted = counted_claims(recs, tags, count_null, collapse)
        sets = {o: disease_areas_of(o) for o in {c.outcome_id for c in counted}}
        sets = {o: a for o, a in sets.items() if a}
        distinct = sorted(set().union(*sets.values())) if sets else []
        cover = minimum_cover(list(sets.values()))
        size = len(distinct) if distinct_areas else cover
        sizes[size] += 1
        if size < HUB_MIN_AREAS:
            continue
        hub_genes = sorted({g for c in counted for g in named[tags[c.claim_record_id].pmid]})
        out.append(HubProtein(
            protein_id=protein, areas=distinct, minimum_areas=cover,
            n_distinct_areas=len(distinct), n_counted_outcomes=len(sets),
            n_causal_or_target_claims=len(counted), n_registry_claims=len(recs),
            n_families=len({c.family_id for c in recs}),
            pleiotropic_locus_named=bool(hub_genes), pleiotropic_genes_named=hub_genes))
    summary = {
        "rule": "distinct_areas" if distinct_areas else "minimum_cover",
        "counted_unit": "family_pair" if collapse else "claim_record",
        "proteins": len(by_protein), "hubs": len(out),
        "hubs_with_pleiotropic_locus_named": sum(h.pleiotropic_locus_named for h in out),
        "proteins_by_areas_counted": {str(k): v for k, v in sorted(sizes.items())},
        "abstracts": len(abstracts),
        "abstracts_with_pleiotropic_locus_named": sum(bool(v) for v in named.values()),
    }
    return out, summary


def count_hubs(proteins: list[str], area_sets: list[frozenset[str]],
               distinct_areas: bool = False) -> int:
    """Hubs among counted claim records given as parallel lists of protein and of the outcome's
    disease areas (records whose outcome has no disease area are left out by the caller)."""
    by_protein: dict[str, set[frozenset[str]]] = collections.defaultdict(set)
    for protein, areas in zip(proteins, area_sets):
        by_protein[protein].add(areas)
    n = 0
    for sets in by_protein.values():
        if distinct_areas:
            n += len(set().union(*sets)) >= HUB_MIN_AREAS
        elif len(sets) >= HUB_MIN_AREAS:
            # Fewer than three distinct area sets are always covered by fewer than three areas.
            n += minimum_cover(list(sets)) >= HUB_MIN_AREAS
    return n


def hub_expectation(claims: list[RegistryClaim], tags: Mapping[str, ClaimTags],
                    disease_areas_of: Callable[[str], frozenset[str]],
                    n_permutations: int = N_PERMUTATIONS, seed: int = SEED,
                    count_null: bool = False, distinct_areas: bool = False,
                    collapse: bool = False) -> dict:
    """Observed hubs beside the number expected when the outcomes of the counted units (claim
    records, or family–pair records with `collapse`) are permuted among those units."""
    counted = counted_claims(claims, tags, count_null, collapse)
    area_of = {o: disease_areas_of(o) for o in {c.outcome_id for c in counted}}
    counted = [c for c in counted if area_of[c.outcome_id]]
    proteins = [c.protein_id for c in counted]
    areas = [area_of[c.outcome_id] for c in counted]
    observed = count_hubs(proteins, areas, distinct_areas)
    rng = np.random.default_rng([seed, PERMUTATION_STREAM])
    permuted = np.array([count_hubs(proteins, [areas[i] for i in rng.permutation(len(areas))],
                                    distinct_areas) for _ in range(n_permutations)],
                        dtype=float) if counted else np.array([])
    expected = float(permuted.mean()) if len(permuted) else None
    return {"counted_unit": "family_pair" if collapse else "claim_record",
            "counted_claim_records_with_a_disease_area": len(counted),
            "observed_hubs": observed, "expected_hubs": expected,
            "observed_over_expected": observed / expected if expected else None,
            "permutation_interval": quantiles(permuted) if len(permuted) else None,
            "permutations": n_permutations, "seed": [seed, PERMUTATION_STREAM]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims", type=pathlib.Path, required=True)
    ap.add_argument("--tags", type=pathlib.Path, required=True)
    ap.add_argument("--ontology-edges", type=pathlib.Path, required=True)
    ap.add_argument("--abstracts", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    claims = [RegistryClaim.model_validate_json(l) for l in a.claims.read_text().splitlines()
              if l.strip()]
    graph, areas = load_graph(a.ontology_edges), load_areas()
    abstracts = {r["pmid"]: r["abstract"] for r in map(json.loads, (
        l for l in a.abstracts.read_text().splitlines() if l.strip()))}
    records, summary = hubs(claims, load_tags(a.tags),
                            lambda o: areas_of(o, areas, graph)[0], abstracts,
                            load_list(LOCUS_LIST))
    tags = load_tags(a.tags)
    result = {"claims_file": str(a.claims), "tags_file": str(a.tags),
              "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
              **summary, "hub_proteins": [h.model_dump() for h in records],
              "expected_from_claim_volume": hub_expectation(
                  claims, tags, lambda o: areas_of(o, areas, graph)[0])}
    a.out.mkdir(parents=True, exist_ok=True)
    target = a.out / "hub_proteins.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; archive it before rerunning")
    target.write_text(json.dumps(result, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
