import datetime

import pytest

from build_registry import PublicDate, RegistryClaim
from claim_tags import ClaimTags
from novelty import claim_dates, classify, index
from ontology_graph import OntologyGraph

GRAPH = OntologyGraph([("narrow", "broad")])


def date(text, resolution="day"):
    return PublicDate(value=datetime.date.fromisoformat(text), resolution=resolution)


def claim(record, i, family, outcome, protein="P1"):
    return RegistryClaim(
        claim_record_id=f"{record}:{i:03d}", family_id=family, protein_id=protein,
        outcome_id=outcome, direction="raises", direction_verified=True, claim_scope="overall",
        context_key="", pqtl_datasets=("not_stated",), outcome_datasets=("not_stated",),
        dataset_attribution="whole_study")


def tags(claims, novel=()):
    return {c.claim_record_id: ClaimTags(
        claim_record_id=c.claim_record_id, pmid=c.claim_record_id.split(":")[0],
        wording_class="causal", novelty_language=c.claim_record_id in novel,
        platform=("not_stated",), ancestry="not_stated") for c in claims}


DATES = {"JA": date("2022-05-10"), "PA": date("2021-03-01"), "JB": date("2021-06-15"),
         "JC": date("2022-05-01", "month"), "JD": date("2020-01-01", "year")}


def test_claim_date_is_the_earliest_family_abstract_holding_the_pair():
    registry = [claim("JA", 0, "A", "narrow"), claim("JA", 1, "A", "broad")]
    dating = [claim("PA", 0, "A", "narrow"), claim("PA", 1, "A", "other")]
    dated = claim_dates(registry, dating, DATES)
    assert dated == {("A", ("P1", "narrow")): DATES["PA"], ("A", ("P1", "broad")): DATES["JA"]}


def test_exact_pair_classes_and_the_tie_rule():
    registry = [claim("JA", 0, "A", "narrow"), claim("JB", 0, "B", "narrow"),
                claim("JC", 0, "C", "narrow"),
                claim("JA", 1, "A", "solo")]
    dated = claim_dates(registry, [], DATES)
    got = {r.claim_record_id: r.novelty_class
           for r in classify(registry, tags(registry), dated, GRAPH)}
    assert got == {"JA:000": "earlier_in_registry",   # B is earlier by day
                   "JB:000": "no_earlier_in_registry",
                   "JC:000": "earlier_in_registry",   # B (2021-06) precedes 2022-05
                   "JA:001": "no_earlier_in_registry"}
    tie = [claim("JA", 0, "A", "narrow"), claim("JC", 0, "C", "narrow")]
    got = {r.claim_record_id: r.novelty_class
           for r in classify(tie, tags(tie), claim_dates(tie, [], DATES), GRAPH)}
    assert got == {"JA:000": "tied_or_unknown_order", "JC:000": "tied_or_unknown_order"}


def test_preprint_date_moves_a_family_ahead():
    registry = [claim("JA", 0, "A", "narrow"), claim("JB", 0, "B", "narrow")]
    dating = [claim("PA", 0, "A", "narrow")]
    dated = claim_dates(registry, dating, DATES)
    got = {r.claim_record_id: r.novelty_class
           for r in classify(registry, tags(registry), dated, GRAPH)}
    assert got == {"JA:000": "no_earlier_in_registry", "JB:000": "earlier_in_registry"}


def test_related_prior_claim_is_recorded_apart_and_never_sets_the_exact_class():
    registry = [claim("JA", 0, "A", "narrow"), claim("JD", 0, "D", "broad"),
                claim("JA", 1, "A", "broad"), claim("JB", 0, "B", "narrow", protein="P2")]
    dated = claim_dates(registry, [], DATES)
    got = {r.claim_record_id: (r.novelty_class, r.related_prior_claim)
           for r in classify(registry, tags(registry), dated, GRAPH)}
    assert got == {
        "JA:000": ("no_earlier_in_registry", True),    # D claimed the broader pair in 2020
        "JD:000": ("no_earlier_in_registry", False),   # A's narrower claim is later
        "JA:001": ("earlier_in_registry", False),      # the family's own narrower claim is not prior
        "JB:000": ("no_earlier_in_registry", False),   # another protein
    }


def test_a_familys_own_earlier_related_claim_is_not_a_prior_claim():
    registry = [claim("JA", 0, "A", "narrow"), claim("JA", 1, "A", "broad")]
    dating = [claim("PA", 0, "A", "narrow")]
    dated = claim_dates(registry, dating, DATES)
    assert dated[("A", ("P1", "narrow"))] == DATES["PA"]
    assert [r.related_prior_claim for r in classify(registry, tags(registry), dated, GRAPH)] == [
        False, False]


def test_index_counts_novelty_language_claims_only():
    registry = [claim("JA", 0, "A", "narrow"), claim("JB", 0, "B", "narrow"),
                claim("JA", 1, "A", "solo")]
    dated = claim_dates(registry, [], DATES)
    records = classify(registry, tags(registry, novel={"JA:000", "JA:001"}), dated, GRAPH)
    out = index(records)
    assert out["novelty_language_claims"] == 2
    assert out["novelty_language_earlier_in_registry"] == 1
    assert out["novelty_language_earlier_in_registry_share"] == pytest.approx(0.5)
    assert out["novelty_language_by_class"] == {"earlier_in_registry": 1,
                                                "no_earlier_in_registry": 1}
    assert out["imprecise_under_20"] is True
