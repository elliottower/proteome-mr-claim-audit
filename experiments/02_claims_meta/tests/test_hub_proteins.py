import pytest

from build_registry import RegistryClaim
from claim_tags import ClaimTags
from hub_proteins import gene_pattern, genes_named, hub_expectation, hubs

AREAS = {"O_cardio": {"cardio"}, "O_cancer": {"cancer"}, "O_lung": {"resp"}, "O_crp": set(),
         "O_odd": set(), "O_bmi": set(), "O_stroke": {"cardio", "neuro"},
         "O_ms": {"neuro", "immune"}, "O_ra": {"immune", "msk"}}
GENES = frozenset({"ABO", "APOE", "HLA-DRB1", "JMJD1C", "JMJD1C-AS1"})


def areas(outcome):
    return frozenset(AREAS[outcome])


def claim(rid, protein, outcome, family="F1", direction="raises"):
    return RegistryClaim(
        claim_record_id=rid, family_id=family, protein_id=protein, outcome_id=outcome,
        direction=direction, direction_verified=True, claim_scope="overall", context_key="",
        pqtl_datasets=("not_stated",), outcome_datasets=("not_stated",),
        dataset_attribution="whole_study")


def tag(rid, wording):
    return ClaimTags(claim_record_id=rid, pmid=rid.split(":")[0], wording_class=wording,
                     novelty_language=False, platform=("not_stated",), ancestry="not_stated")


def run(spec, abstracts=None, **kw):
    claims = [claim(rid, protein, outcome, family) for rid, protein, outcome, _, family in spec]
    tags = {rid: tag(rid, wording) for rid, _, _, wording, _ in spec}
    abstracts = abstracts or {rid.split(":")[0]: "" for rid, *_ in spec}
    return hubs(claims, tags, areas, abstracts, GENES, **kw)


def test_hub_needs_three_areas_from_causal_or_target_claims():
    spec = [("1:000", "P1", "O_cardio", "causal", "F1"), ("1:001", "P1", "O_cancer", "target", "F1"),
            ("1:002", "P1", "O_crp", "causal", "F1"), ("1:003", "P1", "O_odd", "causal", "F1"),
            ("2:000", "P1", "O_lung", "association", "F2")]
    records, summary = run(spec)
    assert records == [] and summary["proteins_by_areas_counted"] == {"2": 1}
    records, summary = run(spec + [("3:000", "P1", "O_lung", "causal", "F3")])
    assert [(h.protein_id, h.areas, h.minimum_areas, h.n_counted_outcomes,
             h.n_causal_or_target_claims, h.n_registry_claims, h.n_families)
            for h in records] == [("P1", ["cancer", "cardio", "resp"], 3, 3, 5, 6, 3)]
    assert summary["hubs"] == 1 and summary["rule"] == "minimum_cover"


def test_outcome_in_several_areas_adds_at_most_one_area():
    # Four distinct areas, but {neuro, immune} covers all three outcomes.
    spec = [("1:000", "P1", "O_stroke", "causal", "F1"), ("1:001", "P1", "O_ms", "causal", "F1"),
            ("1:002", "P1", "O_ra", "causal", "F1")]
    records, summary = run(spec)
    assert records == [] and summary["proteins_by_areas_counted"] == {"2": 1}
    distinct, summary = run(spec, distinct_areas=True)
    assert [(h.areas, h.minimum_areas, h.n_distinct_areas) for h in distinct] == [
        (["cardio", "immune", "msk", "neuro"], 2, 4)]
    assert summary["rule"] == "distinct_areas"
    # A fourth outcome in an area of its own makes three areas necessary.
    records, _ = run(spec + [("1:003", "P1", "O_cancer", "target", "F1")])
    assert [h.minimum_areas for h in records] == [3]


def test_claim_reporting_no_significant_estimate_does_not_count_toward_the_areas():
    claims = [claim("1:000", "P1", "O_cardio"), claim("1:001", "P1", "O_cancer"),
              claim("1:002", "P1", "O_lung", direction="reported_nonsignificant_or_null")]
    tags = {c.claim_record_id: tag(c.claim_record_id, "causal") for c in claims}
    records, summary = hubs(claims, tags, areas, {"1": ""}, GENES)
    assert records == [] and summary["proteins_by_areas_counted"] == {"2": 1}
    counted, _ = hubs(claims, tags, areas, {"1": ""}, GENES, count_null=True)
    assert [(h.areas, h.n_causal_or_target_claims) for h in counted] == [
        (["cancer", "cardio", "resp"], 3)]


def test_outcome_without_a_disease_area_does_not_count():
    spec = [("1:000", "P1", "O_cardio", "causal", "F1"), ("1:001", "P1", "O_cancer", "causal", "F1"),
            ("1:002", "P1", "O_bmi", "target", "F1")]
    records, summary = run(spec)
    assert records == [] and summary["proteins_by_areas_counted"] == {"2": 1}


@pytest.mark.parametrize("text, expected", [
    ("variants at the ABO locus", ["ABO"]),
    ("an ABO-related signal and APOE.", ["ABO", "APOE"]),
    ("the LABO and ABOX genes and abo", []),
    ("APOE4 carriers", []),
    ("HLA-DRB1 and JMJD1C-AS1", ["HLA-DRB1", "JMJD1C-AS1"]),
    ("(JMJD1C)", ["JMJD1C"]),
])
def test_genes_named_are_whole_case_sensitive_symbols(text, expected):
    assert genes_named(text, gene_pattern(GENES)) == expected


def test_pleiotropic_flag_reads_only_abstracts_holding_the_hubs_causal_or_target_claims():
    spec = [("1:000", "P1", "O_cardio", "causal", "F1"), ("1:001", "P1", "O_cancer", "causal", "F1"),
            ("2:000", "P1", "O_lung", "target", "F2"), ("3:000", "P1", "O_bmi", "association", "F3")]
    quiet = {"1": "no locus here", "2": "nor here", "3": "the APOE locus is pleiotropic"}
    records, summary = run(spec, quiet)
    assert not records[0].pleiotropic_locus_named and records[0].pleiotropic_genes_named == []
    assert summary["abstracts_with_pleiotropic_locus_named"] == 1
    named = {**quiet, "2": "instruments near ABO and APOE were excluded"}
    records, _ = run(spec, named)
    assert records[0].pleiotropic_locus_named
    assert records[0].pleiotropic_genes_named == ["ABO", "APOE"]


def test_empty_locus_list_is_refused():
    with pytest.raises(ValueError):
        gene_pattern(frozenset())


def test_family_pair_collapse_keeps_the_hubs_and_counts_one_unit_per_family_and_pair():
    spec = [("1:000", "P1", "O_cardio", "causal", "F1"), ("1:001", "P1", "O_cardio", "causal", "F1"),
            ("1:002", "P1", "O_cardio", "target", "F1"), ("1:003", "P1", "O_cancer", "causal", "F1"),
            ("2:000", "P1", "O_lung", "causal", "F2"), ("2:001", "P1", "O_cardio", "causal", "F2")]
    records, summary = run(spec)
    collapsed, collapsed_summary = run(spec, collapse=True)
    assert [h.protein_id for h in records] == [h.protein_id for h in collapsed] == ["P1"]
    assert (records[0].n_causal_or_target_claims, collapsed[0].n_causal_or_target_claims) == (6, 4)
    assert (summary["counted_unit"], collapsed_summary["counted_unit"]) == (
        "claim_record", "family_pair")


def test_family_pair_collapse_changes_what_the_volume_expectation_permutes():
    claims = [claim(f"1:{i:03d}", "P1", "O_cardio") for i in range(5)] + [
        claim("2:000", "P2", "O_cancer", "F2"), claim("3:000", "P3", "O_lung", "F3")]
    tags = {c.claim_record_id: tag(c.claim_record_id, "causal") for c in claims}
    plain = hub_expectation(claims, tags, areas, n_permutations=50)
    collapsed = hub_expectation(claims, tags, areas, n_permutations=50, collapse=True)
    assert plain["counted_claim_records_with_a_disease_area"] == 7
    assert collapsed["counted_claim_records_with_a_disease_area"] == 3
    # With five records on one protein the permutation can give it all three areas; with one
    # unit per protein it never can.
    assert plain["expected_hubs"] > 0 and collapsed["expected_hubs"] == 0
