import pytest

from build_registry import RegistryClaim, build, denominator_report, estimates
from dataset_relations import load_rows
from hierarchy_relations import pair_families, pair_family_claims, recomputed, relations
from ontology_graph import OntologyGraph

# narrow -> mid -> broad; `other` is unrelated.
GRAPH = OntologyGraph([("narrow", "mid"), ("mid", "broad")])
# Sources chosen so that F1–F2 and F2–F3 are disjoint on both sides and F1–F3 overlap on the
# outcome side (FinnGen R10 and R12).
SOURCES = {"F1": (("Sun 2018",), ("FinnGen R10",)), "F2": (("Fenland SomaScan v4 (Pietzner 2021)",),
                                                           ("Pan-UK Biobank",)),
           "F3": (("deCODE 2023",), ("FinnGen R12",))}


@pytest.fixture(scope="module")
def rows():
    return load_rows()


def claim(family, outcome, direction, protein="P1"):
    pqtl, oc = SOURCES[family]
    return RegistryClaim(
        claim_record_id=f"{family}:{protein}:{outcome}", family_id=family, protein_id=protein,
        outcome_id=outcome, direction=direction, direction_verified=True, claim_scope="overall",
        context_key="", pqtl_datasets=pqtl, outcome_datasets=oc,
        dataset_attribution="whole_study")


CLAIMS = [claim("F1", "narrow", "raises"), claim("F2", "mid", "lowers"),
          claim("F3", "broad", "raises"), claim("F1", "other", "raises", protein="P2"),
          claim("F2", "narrow", "raises", protein="P2")]


def test_relations_record_every_ancestor_pair_of_one_protein_with_its_distance():
    pairs = {(c.protein_id, c.outcome_id) for c in CLAIMS}
    got = {(r.protein_id, r.narrower_outcome_id, r.broader_outcome_id, r.distance)
           for r in relations(pairs, GRAPH)}
    assert got == {("P1", "narrow", "mid", 1), ("P1", "mid", "broad", 1),
                   ("P1", "narrow", "broad", 2)}


def test_pair_family_is_the_anchor_and_its_one_step_relatives_only():
    pairs = {(c.protein_id, c.outcome_id) for c in CLAIMS}
    fams = pair_families(pairs, GRAPH)
    assert fams[("P1", "mid")] == [("P1", "mid"), ("P1", "broad"), ("P1", "narrow")]
    assert fams[("P1", "narrow")] == [("P1", "narrow"), ("P1", "mid")]
    assert fams[("P1", "broad")] == [("P1", "broad"), ("P1", "mid")]
    assert fams[("P2", "narrow")] == [("P2", "narrow")]


def test_rekeyed_claims_put_each_record_on_every_anchor_holding_its_pair(rows):
    rekeyed, _ = pair_family_claims(CLAIMS, GRAPH)
    reg = build(rekeyed, rows)
    assert set(reg[("P1", "narrow")]) == {"F1", "F2"}
    assert set(reg[("P1", "mid")]) == {"F1", "F2", "F3"}
    assert set(reg[("P1", "broad")]) == {"F2", "F3"}
    assert set(reg[("P2", "other")]) == {"F1"}


def test_contradictions_across_one_step_relatives_appear_only_in_pair_families(rows):
    exact = build(CLAIMS, rows)
    assert denominator_report(exact)["contradicting_pairs"] == 0
    assert estimates(exact)["h1_pairs"] == 0
    out = recomputed(CLAIMS, GRAPH, rows, n_boot=200)
    assert out["anchors"] == 5 and out["anchors_with_a_one_step_relative"] == 3
    assert out["pair_family_sizes"] == {"1": 2, "2": 2, "3": 1}
    assert out["denominators"]["contradicting_pairs"] == 3
    e = out["estimates"]
    assert (e["h1_pairs"], e["h1_pairs_agreeing"], e["h1_independent_edges"]) == (3, 0, 4)
    assert e["h2_multi_family_pairs"] == 3
