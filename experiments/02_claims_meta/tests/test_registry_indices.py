import pytest

from build_registry import SEED, RegistryClaim, build
from claim_tags import ClaimTags
from dataset_relations import load_rows
from registry_indices import (contradiction_sources, extraction_failed_bounds, landscape,
                              papers_per_pair, participant_overlap, within_family_discordance)

SUN, FENLAND = ("Sun 2018",), ("Fenland SomaScan v4 (Pietzner 2021)",)
R10, R12, PANUKB = ("FinnGen R10",), ("FinnGen R12",), ("Pan-UK Biobank",)


@pytest.fixture(scope="module")
def rows():
    return load_rows()


def claim(family, pair, direction="raises", pqtl=SUN, outcome=R10, scope="overall", context="",
          verified=True, attribution="whole_study"):
    return RegistryClaim(
        claim_record_id=f"{family}:{pair}:{context}:{direction}", family_id=family,
        protein_id=pair[0], outcome_id=pair[1], direction=direction,
        direction_verified=verified, claim_scope=scope, context_key=context,
        pqtl_datasets=pqtl, outcome_datasets=outcome, dataset_attribution=attribution)


def tags(claims, platform=None, ancestry=None, wording=None):
    platform, ancestry, wording = platform or {}, ancestry or {}, wording or {}
    return {c.claim_record_id: ClaimTags(
        claim_record_id=c.claim_record_id, pmid="1",
        wording_class=wording.get(c.family_id, "association"), novelty_language=False,
        platform=platform.get(c.family_id, ("not_stated",)),
        ancestry=ancestry.get(c.family_id, "not_stated")) for c in claims}


def test_participant_overlap_three_way_classes_and_bounds(rows):
    claims = [
        claim("A", ("P1", "O")), claim("B", ("P1", "O")),                    # identical
        claim("A", ("P2", "O")), claim("B", ("P2", "O"), outcome=R12),       # overlapping
        claim("A", ("P3", "O")), claim("B", ("P3", "O"), pqtl=FENLAND, outcome=PANUKB),
        claim("A", ("P4", "O")), claim("B", ("P4", "O"), pqtl=("not_stated",)),
        claim("A", ("P5", "O")),
        claim("A", ("P6", "O")), claim("B", ("P6", "O"), pqtl=FENLAND),      # disjoint pQTL side
    ]
    out = participant_overlap(build(claims, rows), n_boot=500, seed=SEED)
    assert (out["multi_family_pairs"], out["known_overlapping"], out["known_not_overlapping"],
            out["unresolved"]) == (5, 2, 2, 1)
    assert out["lower"] == pytest.approx(0.4) and out["upper"] == pytest.approx(0.6)
    assert out["complete_case"] == pytest.approx(0.5)
    assert out["imprecise_under_20_pairs"] is True
    lo, hi = out["pair_bootstrap"]["lower"]
    assert 0.0 <= lo <= 0.4 <= hi <= 1.0


def test_papers_per_pair_distribution(rows):
    claims = [claim("A", ("P1", "O")), claim("B", ("P1", "O")), claim("C", ("P1", "O")),
              claim("A", ("P2", "O")), claim("A", ("P3", "O"))]
    assert papers_per_pair(build(claims, rows)) == {"1": 2, "3": 1}


def test_within_family_discordance_split_by_claim_scope(rows):
    claims = [
        claim("A", ("P1", "O")),
        claim("A", ("P1", "O"), "lowers", scope="subgroup_specific", context="in women"),
        claim("B", ("P2", "O"), scope="dataset_specific", context="discovery"),
        claim("B", ("P2", "O"), "lowers", scope="dataset_specific", context="replication"),
        claim("C", ("P3", "O")),
        claim("C", ("P3", "O"), "lowers", context="x", verified=False),
        claim("D", ("P4", "O")),
        claim("D", ("P4", "O"), scope="subgroup_specific", context="in men"),
        claim("D", ("P4", "O"), "lowers", context="second analysis"),
    ]
    out = within_family_discordance(build(claims, rows), claims)
    assert out == {"mixed_family_pair_records": 3, "scopes_differ": 1, "scope_shared": 2}


def test_contradiction_sources_compare_the_two_sides_field_by_field(rows):
    claims = [
        claim("A", ("P1", "O")), claim("B", ("P1", "O"), "lowers", pqtl=FENLAND),
        claim("A", ("P2", "O")), claim("C", ("P2", "O"), "lowers"),
        claim("A", ("P3", "O")), claim("B", ("P3", "O")),
    ]
    t = tags(claims, platform={"A": ("SomaScan",), "B": ("Soma-Scan",), "C": ("Olink",)},
             ancestry={"A": "European", "C": "East Asian"})
    out = contradiction_sources(build(claims, rows), claims, t)
    assert out["contradicting_pairs"] == 2
    assert out["pqtl"]["differ"] == 1 and out["pqtl"]["same"] == 1
    assert out["outcome"]["same"] == 2
    assert out["platform"]["same"] == 1 and out["platform"]["differ"] == 1
    assert out["ancestry"]["not_stated"] == 1 and out["ancestry"]["differ"] == 1
    assert out["any"]["differ"] == 2
    assert out["pqtl"]["share_differ"] == pytest.approx(0.5)
    assert out["ancestry"]["share_not_stated"] == pytest.approx(0.5)


def test_contradiction_with_nothing_stated_is_counted_as_not_stated(rows):
    none = ("not_stated",)
    claims = [claim("A", ("P1", "O"), pqtl=none, outcome=none),
              claim("B", ("P1", "O"), "lowers", pqtl=none, outcome=none)]
    out = contradiction_sources(build(claims, rows), claims, tags(claims))
    assert out["any"] == {"not_stated": 1, "share_differ": 0.0, "share_not_stated": 1.0,
                          "wilson_descriptive_differ": out["any"]["wilson_descriptive_differ"]}


def test_landscape_years_periods_proteins_and_therapeutic_areas():
    claims = [claim("A", ("P1", "O_heart")), claim("B", ("P1", "O_heart")),
              claim("A", ("P1", "O_lung")), claim("A", ("P2", "O_lung")),
              claim("A", ("P2", "O_bmi")), claim("A", ("P3", "O_rare"))]
    meta = {"A": {"first_public": {"value": "2021-03-01", "resolution": "day"}},
            "B": {"first_public": {"value": "2024-01-01", "resolution": "year"}},
            "Z": {"first_public": {"value": "2022-12-31", "resolution": "day"}}}
    areas = {"O_heart": (frozenset({"cardio"}), "direct"),
             "O_lung": (frozenset({"resp", "cancer"}), "nearest_ancestor"),
             "O_bmi": (frozenset({"measurement"}), "direct"),
             "O_rare": (frozenset(), "none")}
    out = landscape(claims, tags(claims, wording={"A": "causal"}), meta, areas.__getitem__)
    assert out["families_per_year"] == {"2021": 1, "2022": 1, "2024": 1}
    assert out["families_per_period"] == {"2019-2022": 2, "2023-2025": 1}
    assert out["most_claimed_proteins"] == [
        {"protein_id": "P1", "families": 2, "pairs": 2, "claim_records": 3},
        {"protein_id": "P2", "families": 1, "pairs": 2, "claim_records": 2},
        {"protein_id": "P3", "families": 1, "pairs": 1, "claim_records": 1}]
    # An outcome in two areas counts in both; an outcome with none is counted apart.
    assert out["pairs_per_therapeutic_area"] == {
        "cancer": 2, "cardio": 1, "measurement": 1, "no_therapeutic_area": 1, "resp": 2}
    assert out["claim_records_per_therapeutic_area"] == {
        "cancer": 2, "cardio": 2, "measurement": 1, "no_therapeutic_area": 1, "resp": 2}
    assert out["pairs_by_area_rule"] == {"direct": 2, "nearest_ancestor": 2, "none": 1}
    assert out["claim_records_per_wording_class"] == {"association": 1, "causal": 5}


def test_extraction_failed_bounds_use_the_median_extracted_family(rows):
    claims = [claim("A", ("P1", "O")), claim("B", ("P2", "O"))]
    meta = {"A": {"extraction": "ok", "n_pairs": 1}, "B": {"extraction": "ok", "n_pairs": 3},
            "C": {"extraction": "ok", "n_pairs": 10}, "D": {"extraction": "extraction_failed",
                                                              "n_pairs": 0},
            "E": {"extraction": "extraction_failed", "n_pairs": 0}}
    out = extraction_failed_bounds(build(claims, rows), meta)
    assert (out["distinct_pairs_lower"], out["distinct_pairs_upper"]) == (2, 8)
    assert out["median_pairs_per_extracted_eligible_family"] == 3


def test_contradiction_datasets_are_undetermined_when_a_family_attribution_is_unclear(rows):
    # The same names on both sides: `same` with clear attribution, `undetermined` when the
    # lowers-side family does not tie its datasets to the claim.
    clear = [claim("A", ("P1", "O")), claim("B", ("P1", "O"), "lowers")]
    unclear = [claim("A", ("P1", "O")), claim("B", ("P1", "O"), "lowers", attribution="unclear")]
    a = contradiction_sources(build(clear, rows), clear, tags(clear))
    b = contradiction_sources(build(unclear, rows), unclear, tags(unclear))
    assert (a["pqtl"].get("same"), a["outcome"].get("same")) == (1, 1)
    assert (b["pqtl"].get("undetermined"), b["outcome"].get("undetermined")) == (1, 1)
    assert b["pqtl"].get("same") is None


def test_participant_overlap_verdict_is_read_on_the_observed_bounds(rows):
    claims = [claim("A", ("P1", "O")), claim("B", ("P1", "O")),
              claim("A", ("P2", "O")), claim("B", ("P2", "O"), outcome=R12),
              claim("A", ("P3", "O")), claim("B", ("P3", "O"), pqtl=FENLAND, outcome=PANUKB)]
    out = participant_overlap(build(claims, rows), n_boot=500, seed=SEED)
    # Two of three pairs overlap and one is disjoint: lower = upper = 2/3 > 1/2.
    assert (out["lower"], out["upper"]) == (pytest.approx(2 / 3), pytest.approx(2 / 3))
    assert out["h2b_verdict"] == "supported"
