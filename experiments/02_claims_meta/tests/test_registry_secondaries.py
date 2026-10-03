import csv
import datetime
import re

import pytest

import registry_secondaries as rs
from build_registry import READINGS, SEED, PublicDate, RegistryClaim, build
from claim_tags import ClaimTags
from dataset_relations import DICTIONARY, load_rows

SUN, FENLAND = ("Sun 2018",), ("Fenland SomaScan v4 (Pietzner 2021)",)
UKB_PPP, ZHENG = ("UKB-PPP discovery",), ("Zheng 2020 proteome-wide MR instrument set",)
R10, R12, PANUKB = ("FinnGen R10",), ("FinnGen R12",), ("Pan-UK Biobank",)
NONE = ("not_stated",)
NS = "reported_nonsignificant_or_null"
N_BOOT = 400


@pytest.fixture(scope="module")
def rows():
    return load_rows()


def claim(family, protein, direction="raises", pqtl=SUN, outcome=R10, outcome_id="O", n=0,
          attribution="whole_study"):
    return RegistryClaim(
        claim_record_id=f"{family}:{protein}:{outcome_id}:{n}", family_id=family,
        protein_id=protein, outcome_id=outcome_id, direction=direction, direction_verified=True,
        claim_scope="overall", context_key=str(n), pqtl_datasets=pqtl, outcome_datasets=outcome,
        dataset_attribution=attribution)


def tags(claims, platform=None, ancestry=None, wording=None, novelty=()):
    platform, ancestry, wording = platform or {}, ancestry or {}, wording or {}
    return {c.claim_record_id: ClaimTags(
        claim_record_id=c.claim_record_id, pmid=c.family_id,
        wording_class=wording.get(c.family_id, "association"),
        novelty_language=c.claim_record_id in novelty,
        platform=platform.get(c.family_id, ("not_stated",)),
        ancestry=ancestry.get(c.family_id, "not_stated")) for c in claims}


def meta(dates, claims=()):
    counts = {}
    for c in claims:
        counts[c.family_id] = counts.get(c.family_id, 0) + 1
    return {f: {"first_public": {"value": value, "resolution": resolution},
                "registry_records": [f], "dating_records": [],
                "n_registry_claims": counts.get(f, 0)}
            for f, (value, resolution) in dates.items()}


def claim_dates(dates, claims, overrides=None):
    """(family, pair) -> claim date: the family's date unless `overrides` names the pair."""
    overrides = overrides or {}
    out = {}
    for c in claims:
        key = (c.family_id, (c.protein_id, c.outcome_id))
        value, resolution = overrides.get(key, dates[c.family_id])
        out[key] = PublicDate(value=datetime.date.fromisoformat(value), resolution=resolution)
    return out


def novelty_of(dates, claims):
    """Novelty records carrying the claim dates, as scripts/novelty.py writes them."""
    by_pair = claim_dates(dates, claims)
    return {c.claim_record_id: {
        "claim_date": by_pair[(c.family_id, (c.protein_id, c.outcome_id))].model_dump(
            mode="json"), "novelty_language": False, "novelty_class": "no_earlier_in_registry"}
        for c in claims}


def record(rid, sources=("pubmed",), chase=None, journal="J", work=None, cited=None,
           kind="journal"):
    return rs.RecordMeta(
        record_id=rid, kind=kind, search_sources=sources, chase_round=chase, journal=journal,
        openalex_ids=(work or f"W_{rid}",),
        has_reference_list=None if cited is None else bool(cited),
        referenced_works=tuple(cited or ()), first_author_country=None)


EDGE_CLAIMS = [
    claim("A", "P1"), claim("B", "P1"),                                      # identical, agree
    claim("A", "P2"), claim("B", "P2", "lowers", outcome=R12),               # overlapping
    claim("A", "P3"), claim("B", "P3", pqtl=FENLAND, outcome=PANUKB),        # independent
    claim("A", "P4"), claim("B", "P4", pqtl=NONE, outcome=NONE),             # unclear
    claim("A", "P5"), claim("B", "P5", "lowers", pqtl=FENLAND, outcome=PANUKB),
    claim("C", "P5", pqtl=FENLAND, outcome=PANUKB),
]


def test_direction_agreement_is_counted_per_edge_class_with_the_identical_release_control(rows):
    out = rs.direction_agreement_by_edge_class(build(EDGE_CLAIMS, rows), N_BOOT, SEED)
    got = {c: (out[c]["edges"], out[c]["edges_agreeing"]) for c in rs.EDGE_CLASSES}
    assert got == {"identical_release": (2, 1), "overlapping": (1, 0), "unclear": (1, 1),
                   "independent": (3, 2)}
    assert out["identical_release"]["role"] == "positive_control"
    assert out["independent"]["share_agreeing"] == pytest.approx(2 / 3)
    assert out["independent_minus_overlapping"]["difference"] == pytest.approx(2 / 3)
    lo, hi = out["independent"]["pair_bootstrap"]
    assert 0.0 <= lo <= 2 / 3 <= hi <= 1.0


def test_edge_relations_count_every_family_edge_per_side_and_by_class(rows):
    out = rs.edge_relations(build(EDGE_CLAIMS, rows), N_BOOT, SEED)
    assert (out["multi_family_pairs"], out["edges"]) == (5, 7)
    assert {k: v["edges"] for k, v in out["pqtl_side"].items()} == {
        "identical_release": 3, "overlapping_participant_source": 0, "disjoint": 3, "unclear": 1}
    assert {k: v["edges"] for k, v in out["outcome_side"].items()} == {
        "identical_release": 2, "overlapping_participant_source": 1, "disjoint": 3, "unclear": 1}
    assert {k: v["edges"] for k, v in out["edge_class"].items()} == {
        "identical_release": 2, "overlapping": 1, "unclear": 1, "independent": 3}
    assert out["edge_class"]["independent"]["share"] == pytest.approx(3 / 7)


def test_an_edge_with_one_identical_side_only_is_overlapping_not_identical(rows):
    claims = [claim("A", "P1"), claim("B", "P1", pqtl=NONE)]
    fams = build(claims, rows)[("P1", "O")]
    assert rs.edge_class(fams["A"], fams["B"]) == "overlapping"


def test_significance_discordance_needs_a_directional_and_a_nonsignificant_only_family(rows):
    claims = [
        claim("A", "P1"), claim("B", "P1", NS, pqtl=FENLAND, outcome=PANUKB),   # discordant
        claim("A", "P2"), claim("B", "P2"),                                     # both directional
        claim("A", "P3"), claim("B", "P3", NS, n=1), claim("B", "P3", n=2),     # B directional
        claim("A", "P4", NS), claim("B", "P4", NS),                             # no direction
        claim("A", "P5"),                                                       # one family
    ]
    out = rs.significance_discordance(build(claims, rows), N_BOOT, SEED)
    assert (out["multi_family_pairs"], out["significance_discordant_pairs"]) == (4, 1)
    assert out["share"] == pytest.approx(0.25)
    assert out["edges_by_class"] == {"identical_release": 0, "overlapping": 0, "unclear": 0,
                                     "independent": 1}


def test_contradiction_fields_are_compared_on_discordant_and_on_concordant_edges(rows):
    claims = [
        claim("A", "P1"), claim("B", "P1", "lowers", pqtl=FENLAND),   # discordant, pQTL differs
        claim("A", "P2"), claim("C", "P2", "lowers"),                 # discordant, same datasets
        claim("A", "P3"), claim("B", "P3", pqtl=FENLAND),             # concordant, pQTL differs
        claim("A", "P4"), claim("C", "P4"),                           # concordant, same datasets
        claim("A", "P5"), claim("D", "P5"),                           # concordant, same datasets
    ]
    t = tags(claims, platform={"A": ("Olink",), "B": ("SomaScan",), "C": ("Olink",)},
             ancestry={"A": "European", "C": "East Asian", "D": "European"})
    out = rs.contradiction_source_comparison(build(claims, rows), claims, t, N_BOOT, SEED)
    assert (out["discordant_edges"], out["concordant_edges"]) == (2, 3)
    assert (out["pqtl"]["discordant_differ"], out["pqtl"]["concordant_differ"]) == (1, 1)
    assert out["pqtl"]["discordant_minus_concordant"]["difference"] == pytest.approx(1 / 2 - 1 / 3)
    assert (out["platform"]["discordant_differ"], out["platform"]["concordant_differ"]) == (1, 1)
    assert (out["ancestry"]["discordant_differ"], out["ancestry"]["concordant_differ"]) == (1, 1)
    assert (out["outcome"]["discordant_differ"], out["outcome"]["concordant_differ"]) == (0, 0)
    assert (out["any"]["discordant_differ"], out["any"]["concordant_differ"]) == (2, 2)
    assert out["any"]["concordant_share_differ"] == pytest.approx(2 / 3)


def test_a_dataset_difference_is_not_counted_when_a_family_attribution_is_unclear(rows):
    # B names another pQTL release; with clear attribution the discordant edge differs on the
    # pQTL side, with B's attribution unclear the comparison is undetermined.
    clear = [claim("A", "P1"), claim("B", "P1", "lowers", pqtl=FENLAND)]
    unclear = [claim("A", "P1"), claim("B", "P1", "lowers", pqtl=FENLAND, attribution="unclear")]
    a = rs.contradiction_source_comparison(build(clear, rows), clear, tags(clear), N_BOOT, SEED)
    b = rs.contradiction_source_comparison(build(unclear, rows), unclear, tags(unclear), N_BOOT,
                                           SEED)
    assert (a["pqtl"]["discordant_differ"], b["pqtl"]["discordant_differ"]) == (1, 0)


def test_first_claim_needs_a_strictly_earliest_family_and_compares_the_later_ones(rows):
    claims = [
        claim("A", "P1"), claim("B", "P1", "lowers"), claim("C", "P1"),   # A first; B no, C yes
        claim("A", "P2"), claim("D", "P2"),                               # tie at year resolution
        claim("B", "P3"), claim("C", "P3"),                               # B first; C yes
        claim("A", "P4"), claim("B", "P4", NS),                           # one directional family
    ]
    d = {"A": ("2020-03-01", "day"), "B": ("2021-01-01", "month"),
         "C": ("2022-06-01", "day"), "D": ("2020-01-01", "year")}
    out = rs.first_claim_concordance(build(claims, rows), claim_dates(d, claims), N_BOOT, SEED)
    assert (out["pairs_with_a_first_family"], out["pairs_tied_first"]) == (2, 1)
    assert (out["later_families"], out["later_families_same_direction"]) == (3, 2)
    assert out["share"] == pytest.approx(2 / 3)
    assert out["by_edge_class"]["identical_release"] == {
        "later_families": 3, "same_direction": 2, "share": pytest.approx(2 / 3)}


def test_the_first_claim_is_ordered_by_claim_date_not_by_the_familys_first_public_date(rows):
    # A is first public in 2019 by a preprint that does not hold P1; its journal abstract,
    # which does, is public in 2022, after B's 2021 claim. B is first on P1, and its direction
    # is the one later families are compared with.
    claims = [claim("A", "P1"), claim("B", "P1", "lowers"), claim("C", "P1", "lowers")]
    d = {"A": ("2019-03-01", "day"), "B": ("2021-01-01", "day"), "C": ("2023-01-01", "day")}
    by_family = rs.first_claim_concordance(build(claims, rows), claim_dates(d, claims),
                                           N_BOOT, SEED)
    by_claim = rs.first_claim_concordance(
        build(claims, rows),
        claim_dates(d, claims, {("A", ("P1", "O")): ("2022-01-01", "day")}), N_BOOT, SEED)
    # By A's first-public date A (raises) would be first and both later families disagree.
    assert by_family["later_families_same_direction"] == 0
    assert by_claim["later_families_same_direction"] == 1
    assert (by_family["share"], by_claim["share"]) == (0.0, pytest.approx(0.5))
    # With A's claim date the first family is B (lowers): C agrees and A does not.
    later = rs.first_claim_concordance(
        build(claims[:2], rows),
        claim_dates(d, claims[:2], {("A", ("P1", "O")): ("2022-01-01", "day")}), N_BOOT, SEED)
    assert later["by_edge_class"]["identical_release"]["same_direction"] == 0


def test_periods_date_a_pair_by_its_first_family_and_a_repeated_pair_by_its_second(rows):
    claims = [
        claim("A", "P1"), claim("B", "P1"),                       # repeated in 2021: identical
        claim("A", "P2"), claim("C", "P2", "lowers", pqtl=FENLAND, outcome=PANUKB),  # 2024
        claim("B", "P3"), claim("C", "P3"),                       # repeated in 2024: identical
        claim("C", "P4"),                                         # first claimed 2024
        claim("A", "P5"),                                         # first claimed 2019
    ]
    d = {"A": ("2019-05-01", "day"), "B": ("2021-01-01", "year"),
         "C": ("2024-02-01", "month")}
    out = rs.periods(build(claims, rows), claim_dates(d, claims), N_BOOT, SEED)
    early, late = out["2019-2022"], out["2023-2025"]
    assert (early["distinct_pairs"], late["distinct_pairs"]) == (4, 1)
    assert (early["multi_family_pairs"], late["multi_family_pairs"]) == (1, 2)
    assert (early["h2_lower"]["pairs"], early["h2_lower"]["share"]) == (1, 1.0)
    assert (late["h2_lower"]["pairs"], late["h2_lower"]["share"]) == (2, 0.5)
    assert late["contradicting_share"]["share"] == pytest.approx(0.5)
    assert late["h1_pair_concordance"] == {**late["h1_pair_concordance"], "pairs": 1,
                                           "share": 0.0}
    assert out["later_minus_earlier"]["h2_lower"]["difference"] == pytest.approx(-0.5)
    assert out["later_minus_earlier"]["h1_pair_concordance"]["difference"] is None


def test_periods_place_a_pair_by_the_claim_date_of_the_family_that_announced_it(rows):
    # A is first public in 2019, but its abstract holding P5 is public in 2023: P5 is first
    # claimed in the later period.
    claims = [claim("A", "P1"), claim("A", "P5")]
    d = {"A": ("2019-05-01", "day")}
    out = rs.periods(build(claims, rows),
                     claim_dates(d, claims, {("A", ("P5", "O")): ("2023-03-01", "day")}),
                     N_BOOT, SEED)
    assert (out["2019-2022"]["distinct_pairs"], out["2023-2025"]["distinct_pairs"]) == (1, 1)


def test_yearly_series_separates_new_pairs_from_pairs_already_claimed(rows):
    claims = [claim("A", "P1"), claim("A", "P2"), claim("B", "P1"), claim("B", "P3"),
              claim("C", "P1"), claim("C", "P2"), claim("C", "P3"), claim("C", "P4")]
    d = {"A": ("2020-01-01", "day"), "B": ("2022-01-01", "day"),
         "C": ("2022-07-01", "day"), "Z": ("2023-01-01", "day")}
    m = meta(d, claims)
    out = rs.yearly_series(build(claims, rows), claims, m, claim_dates(d, claims))
    assert out["2020"] == {"families": 1, "claim_records": 2, "pairs_claimed": 2, "new_pairs": 2,
                           "pairs_already_claimed_in_an_earlier_year": 0,
                           "share_already_claimed": 0.0}
    assert out["2022"] == {"families": 2, "claim_records": 6, "pairs_claimed": 4, "new_pairs": 2,
                           "pairs_already_claimed_in_an_earlier_year": 2,
                           "share_already_claimed": 0.5}
    assert out["2023"]["families"] == 1 and out["2023"]["share_already_claimed"] is None
    # A's P2 claim dated 2021 by its abstract: the family enters in 2020, the pair in 2021.
    shifted = rs.yearly_series(build(claims, rows), claims, m, claim_dates(
        d, claims, {("A", ("P2", "O")): ("2021-01-01", "day")}))
    assert (shifted["2020"]["families"], shifted["2020"]["pairs_claimed"]) == (1, 1)
    assert (shifted["2021"]["families"], shifted["2021"]["pairs_claimed"],
            shifted["2021"]["new_pairs"]) == (0, 1, 1)


def test_reporting_completeness_counts_named_and_unique_sides_per_family(rows):
    claims = [claim("A", "P1"), claim("A", "P2", pqtl=("UKB-PPP",)),
              claim("B", "P1", pqtl=NONE, outcome=PANUKB), claim("C", "P1", outcome=NONE)]
    t = tags(claims, platform={"A": ("Olink",)}, ancestry={"B": "European", "C": "European"})
    m = meta({"A": ("2020-01-01", "day"), "B": ("2020-01-01", "day"),
              "C": ("2020-01-01", "day"), "E": ("2020-01-01", "day")}, claims)
    out = rs.reporting_completeness(build(claims, rows), claims, t, m)
    got = {k: v["families"] for k, v in out.items() if isinstance(v, dict)}
    assert got == {"pqtl_dataset_named": 2, "outcome_dataset_named": 2, "pqtl_release_unique": 1,
                   "outcome_release_unique": 2, "both_releases_unique": 0, "platform_stated": 1,
                   "ancestry_stated": 2}
    assert out["families_with_a_registry_claim"] == 3
    assert out["eligible_families_without_a_registry_claim"] == 1
    assert out["outcome_dataset_named"]["share"] == pytest.approx(2 / 3)


def test_dataset_usage_counts_rows_ambiguous_labels_components_and_combinations(rows):
    claims = [claim("A", "P1"), claim("B", "P1"), claim("C", "P1", pqtl=("UKB-PPP",)),
              claim("D", "P1", pqtl=UKB_PPP, outcome=NONE)]
    out = rs.dataset_usage(build(claims, rows))
    labels = out["families_per_pqtl_label"]
    assert labels["INTERVAL SomaScan (Sun 2018)"] == 2 and labels["UKB-PPP discovery"] == 1
    assert [k for k in labels if k.startswith("one of: ")] and len(labels) == 3
    assert out["families_per_pqtl_component"] == {"INTERVAL": 2, "UKB": 2}
    assert out["commonest_pqtl_outcome_combinations"][0] == {
        "pqtl": "INTERVAL SomaScan (Sun 2018)", "outcome": "FinnGen R10", "families": 2}
    assert out["families_per_outcome_label"]["not_stated"] == 1


def test_h2_tables_by_families_per_pair_and_over_directional_families(rows):
    claims = [
        claim("A", "P1"), claim("B", "P1"),                                # k=2 identical
        claim("A", "P2"), claim("B", "P2", outcome=R12),                   # k=2 overlapping
        claim("A", "P3"), claim("B", "P3"), claim("C", "P3", NS, pqtl=FENLAND, outcome=PANUKB),
        claim("A", "P4"), claim("B", "P4"), claim("C", "P4"), claim("D", "P4", pqtl=NONE),
    ]
    reg = build(claims, rows)
    by_k = rs.h2_by_families_per_pair(reg, N_BOOT, SEED)
    two = by_k["2"]
    assert (two["h2_identical_release"]["pairs"], two["h2_identical_release"]["lower"],
            two["h2_identical_release"]["upper"]) == (2, 0.5, 0.5)
    assert (two["h2b_identical_or_overlapping"]["lower"],
            two["h2b_identical_or_overlapping"]["upper"]) == (1.0, 1.0)
    assert two["resolvable_pairs"] == 2
    assert by_k["3"]["h2_identical_release"]["known_not_identical"] == 1
    four = by_k["4_or_more"]["h2_identical_release"]
    assert (four["pairs"], four["lower"], four["upper"]) == (1, 0.0, 1.0)
    # P3's non-significant family is on other data; over its two directional families the pair
    # is identical.
    directional = rs.h2_directional_pairs(reg, N_BOOT, SEED)["h2_identical_release"]
    assert (directional["pairs"], directional["known_identical"],
            directional["known_not_identical"], directional["unresolved"]) == (4, 2, 1, 1)


def test_platform_pairing_reads_the_assay_family_of_the_dictionary_rows(rows):
    claims = [
        claim("A", "P1"), claim("B", "P1", pqtl=FENLAND),                  # SomaScan both, agree
        claim("A", "P2"), claim("B", "P2", "lowers", pqtl=UKB_PPP),        # cross, disagree
        claim("A", "P3"), claim("B", "P3", pqtl=UKB_PPP),                  # cross, agree
        claim("A", "P4"), claim("B", "P4", pqtl=ZHENG),                    # mixed -> unknown
        claim("A", "P5"), claim("B", "P5", pqtl=NONE),                     # not stated -> unknown
    ]
    out = rs.platform_pairing(build(claims, rows), rs.load_row_platforms(), N_BOOT, SEED)
    got = {k: (out[k]["edges"], out[k]["edges_agreeing"]) for k in
           ("same_platform", "cross_platform", "platform_unknown")}
    assert got == {"same_platform": (1, 1), "cross_platform": (2, 1), "platform_unknown": (2, 2)}
    assert out["cross_platform"]["discordant_edges"] == 1
    assert out["cross_minus_same"]["difference"] == pytest.approx(-0.5)


def test_every_pqtl_dictionary_row_has_an_assay_family_named_in_its_platform_string():
    with DICTIONARY.open(newline="") as f:
        platform = {r["name"]: r["platform"].lower() for r in csv.DictReader(f)
                    if r["side"] == "pqtl"}
    families = rs.load_row_platforms()
    assert set(families) == set(platform)
    keyword = {"olink": "olink", "somascan": "soma"}
    for row, family in families.items():
        assert family in ("olink", "somascan", "other", "mixed")
        if family in keyword:
            assert keyword[family] in platform[row]
        if family == "mixed":
            assert "olink" in platform[row] and "soma" in platform[row]
        if family == "other":
            assert "olink" not in platform[row] and "soma" not in platform[row]


def test_claims_per_family_quantiles_and_top_decile_share():
    m = {str(i): {"n_registry_claims": n} for i, n in enumerate(
        [0, 0, 1, 1, 2, 2, 3, 4, 7, 20, 60])}
    out = rs.claims_per_family(m)
    assert (out["eligible_families"], out["claim_records"]) == (11, 100)
    assert (out["families_with_zero_claims"], out["min"], out["max"]) == (2, 0, 60)
    assert (out["q25"], out["median"], out["q75"], out["q90"]) == (1.0, 2, 7.0, 20.0)
    assert (out["top_decile_families"], out["share_of_claim_records_from_top_decile"]) == (
        2, pytest.approx(0.8))


def test_top_lists_rank_by_families_then_ties(rows):
    claims = [claim("A", "P1"), claim("B", "P1"), claim("C", "P1"),
              claim("A", "P2", outcome_id="O2"), claim("B", "P2", outcome_id="O2"),
              claim("A", "P2", outcome_id="O2", n=1),
              claim("A", "P3"), claim("B", "P3"),
              claim("A", "P0", outcome_id="O3")]
    out = rs.top_lists(build(claims, rows), claims)
    assert [(p["protein_id"], p["outcome_id"], p["families"], p["claim_records"])
            for p in out["pairs"]] == [("P1", "O", 3, 3), ("P2", "O2", 2, 3), ("P3", "O", 2, 2),
                                       ("P0", "O3", 1, 1)]
    assert [(p["id"], p["families"], p["pairs"]) for p in out["proteins"]] == [
        ("P1", 3, 1), ("P2", 2, 1), ("P3", 2, 1), ("P0", 1, 1)]
    assert [(o["id"], o["families"], o["pairs"]) for o in out["outcomes"]] == [
        ("O", 3, 2), ("O2", 2, 1), ("O3", 1, 1)]


def test_top_lists_keep_twenty(rows):
    claims = [claim("A", f"P{i:02d}") for i in range(25)]
    out = rs.top_lists(build(claims, rows), claims)
    assert len(out["pairs"]) == len(out["proteins"]) == 20
    assert out["proteins"][-1]["id"] == "P19"


def test_wording_shares_by_families_per_pair_and_novelty_by_year(rows):
    claims = [claim("A", "P1"), claim("B", "P1"), claim("C", "P1"),
              claim("A", "P2"), claim("B", "P2"), claim("A", "P3")]
    t = tags(claims, wording={"A": "causal", "B": "target"},
             novelty={claims[0].claim_record_id, claims[3].claim_record_id})
    m = meta({"A": ("2020-01-01", "day"), "B": ("2021-01-01", "day"),
              "C": ("2021-06-01", "day")})
    out = rs.wording_by_repetition_and_year(build(claims, rows), claims, t, m)
    by_k = {k: {w: v[w]["claim_records"] for w in ("association", "causal", "target")}
            for k, v in out["by_families_per_pair"].items()}
    assert by_k == {"1": {"association": 0, "causal": 1, "target": 0},
                    "2": {"association": 0, "causal": 1, "target": 1},
                    "3_or_more": {"association": 1, "causal": 1, "target": 1}}
    assert out["by_year"]["2021"]["target"]["share"] == pytest.approx(2 / 3)
    assert out["novelty_language_by_year"]["2020"]["novelty_language"] == 2
    assert out["novelty_language_by_year"]["2020"]["share"] == pytest.approx(2 / 3)
    assert out["novelty_language_by_year"]["2021"]["novelty_language"] == 0


def test_a_later_family_cites_the_earlier_claim_through_any_of_its_records(rows):
    claims = [claim("A", "P1"), claim("B", "P1"), claim("C", "P1"), claim("D", "P1"),
              claim("A", "P2"), claim("E", "P2")]
    d = {"A": ("2019-01-01", "day"), "B": ("2020-01-01", "day"),
         "C": ("2021-01-01", "day"), "D": ("2022-01-01", "day"),
         "E": ("2019-01-01", "year")}
    m = meta(d)
    m["A"]["dating_records"] = ["PA"]
    records = {r.record_id: r for r in [
        record("A", cited=["W_OLD"]), record("PA", cited=["W_OLD"], kind="preprint"),
        record("B", cited=["W_PA"]),            # cites A's preprint
        record("C", cited=["W_D", "W_X"]),      # cites only a later family
        record("D", cited=[]),                  # an OpenAlex work with no reference list
        record("E", cited=["W_A"])]}            # tied with A: not a later family
    novelty = {c.claim_record_id: {"novelty_language": c.family_id in ("B", "C"),
                                   "novelty_class": "earlier_in_registry"
                                   if c.family_id == "B" else "no_earlier_in_registry"}
               for c in claims}
    out = rs.citation_of_earlier_claim(build(claims, rows), claim_dates(d, claims), m, records,
                                       novelty, claims)
    later = out["later_families"]
    assert (later["later_family_pair_records"], later["without_a_reference_list"],
            later["with_a_reference_list"], later["citing_an_earlier_family_of_the_pair"]) == (
        3, 1, 2, 1)
    assert later["share"] == pytest.approx(0.5)
    novel = out["later_families_with_novelty_language_and_an_earlier_registry_claim"]
    assert (novel["later_family_pair_records"], novel["citing_an_earlier_family_of_the_pair"],
            novel["share"]) == (1, 1, 1.0)
    assert out["eligible_families_with_a_reference_list"] == 4
    # With A's claim date on P1 after D's, A is a later family of P1 and D an earlier one.
    moved = rs.citation_of_earlier_claim(
        build(claims, rows), claim_dates(d, claims, {("A", ("P1", "O")): ("2023-01-01", "day")}),
        m, records, novelty, claims)["later_families"]
    assert moved["later_family_pair_records"] == 3
    assert moved["citing_an_earlier_family_of_the_pair"] == 0


def test_source_overlap_and_chase_only_families():
    m = meta({f: ("2020-01-01", "day") for f in "ABCD"})
    families = {"A": ["A", "PA"], "B": ["B"], "C": ["C"], "D": ["D"]}
    records = {r.record_id: r for r in [
        record("A", sources=("pubmed",)), record("PA", sources=("epmc", "openalex")),
        record("B", sources=("openalex",)), record("C", sources=(), chase=2),
        record("D", sources=(), chase=1)]}
    out = rs.source_overlap(m, families, records)
    assert out["by_search_sources"] == {"openalex": 1, "pubmed+epmc+openalex": 1}
    assert out["not_returned_by_any_query"] == {"chase_round_1": 1, "chase_round_2": 1}
    assert out["found_only_by_citation_chasing"] == 2
    assert out["share_found_only_by_citation_chasing"] == pytest.approx(0.5)


def test_document_classes_and_journals_of_the_registry_records():
    m = meta({f: ("2020-01-01", "day") for f in "ABCDE"})
    records = {r.record_id: r for r in [
        record("A", journal="Zeta"), record("B", journal="Alpha"), record("C", journal="Zeta"),
        record("D", journal="medRxiv", kind="preprint"), record("E", journal=None)]}
    out = rs.document_class_and_journals(m, records)
    assert out["families_by_document_class"] == {"journal": 4, "preprint": 1}
    assert out["preprint_only_share"] == pytest.approx(0.2)
    assert out["journals_with_most_families"] == [
        {"journal": "Zeta", "families": 2}, {"journal": "Alpha", "families": 1},
        {"journal": "journal_not_recorded", "families": 1}]


def test_accounting_names_every_denominator_and_what_left_it(rows):
    claims = [claim("A", "P1"), claim("B", "P1", "lowers", pqtl=FENLAND, outcome=PANUKB),
              claim("A", "P2"), claim("B", "P2", NS), claim("A", "P3")]
    d = {"A": ("2020-01-01", "day"), "B": ("2021-01-01", "day")}
    table = {r["index"]: r for r in rs.accounting(
        build(claims, rows), claims, {"registry": {"left_out_by_reason": {"x": 2}}},
        meta(d, claims), claim_dates(d, claims))}
    assert table["registry claim records"]["n"] == 5
    assert table["registry claim records"]["left"] == {"x": 2}
    assert table["distinct pairs; papers per pair"]["n"] == 3
    multi = table["H2; H2b; resolvable share"]
    assert (multi["n"], multi["left"]) == (2, {"pairs_with_one_family": 1})
    assert (table["H1"]["n"], table["H1"]["edge_n"]) == (1, 1)
    assert table["direction-based results"]["n"] == 4
    assert table["direction-based results"]["left"] == {"nonsignificant_only": 1}
    # P1 has one edge between directional families; P2 has a directional and a
    # nonsignificant_only family.
    assert (table["edge_relations"]["n"], table["edge_relations"]["edge_n"]) == (2, 2)
    edges = table["direction_agreement_by_edge_class; contradiction_source_comparison; "
                  "platform_pairing"]
    assert (edges["n"], edges["edge_n"]) == (1, 1)
    assert (table["significance_discordance"]["n"],
            table["significance_discordance"]["edge_n"]) == (2, 1)
    assert table["citation_of_earlier_claim"]["n"] == 2
    assert all(r["edge_denominator"] for r in table.values() if r["edge_n"] is not None)


def test_bootstrap_ratio_interval_brackets_the_estimate_and_counts_undefined_replicates():
    num, den = [1.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 0.0], [1.0] * 8
    lo, hi = rs.boot_ratio(num, den, 2000, SEED, 3)["interval"]
    assert 0.0 <= lo < 5 / 8 < hi <= 1.0
    sparse = rs.boot_ratio([1.0, 0.0, 0.0], [1.0, 0.0, 0.0], 2000, SEED, 3)
    assert sparse["interval"] == [1.0, 1.0]
    assert sparse["undefined_replicates"] == pytest.approx(2000 * (2 / 3) ** 3, rel=0.15)
    assert rs.boot_ratio([], [], 100, SEED, 3) == {"interval": None, "undefined_replicates": 0}


def test_bootstrap_difference_is_the_difference_of_the_two_ratios():
    out = rs.boot_difference([1.0, 1.0, 0.0, 0.0], [1.0, 1.0, 1.0, 1.0],
                             [0.0, 0.0, 0.0, 1.0], [1.0, 1.0, 1.0, 1.0], 2000, SEED, 4)
    assert out["difference"] == pytest.approx(0.25)
    lo, hi = out["interval"]
    assert -1.0 <= lo <= 0.25 <= hi <= 1.0


def test_secondaries_returns_every_registered_table(rows):
    claims = EDGE_CLAIMS
    d = {f: ("2020-01-01", "day") for f in "ABC"}
    m = meta(d, claims)
    records = {f: record(f, cited=["W_x"]) for f in "ABC"}
    out = rs.secondaries(claims, tags(claims), build(claims, rows), m,
                         lambda o: (frozenset({"area"}), "direct"),
                         {f: [f] for f in "ABC"}, records, novelty_of(d, claims),
                         n_boot=N_BOOT)
    assert set(out) == {
        "bootstrap", "reporting_completeness", "dataset_usage", "edge_relations",
        "h2_by_families_per_pair", "h2_directional_pairs", "direction_agreement_by_edge_class",
        "significance_discordance", "contradiction_source_comparison",
        "first_claim_concordance", "periods", "yearly_series", "therapeutic_areas",
        "platform_pairing", "claims_per_family", "top_lists", "wording_by_repetition_and_year",
        "citation_of_earlier_claim", "source_overlap", "document_class_and_journals",
        "accounting"}
    area = out["therapeutic_areas"]["area"]
    assert (area["pairs"], area["multi_family_pairs"], area["contradicting_pairs"]) == (5, 5, 2)


def test_the_registered_secondary_table_names_exactly_the_tables_the_script_writes(rows):
    text = (rs.EXP / "PREREG.md").read_text()
    table = text.split("**Registered secondary outcomes**")[1].split(
        "**Units and denominators of the indices.**")[0]
    registered = set(re.findall(r"^\| `(\w+)` \|", table, re.M))
    d = {f: ("2020-01-01", "day") for f in "ABC"}
    m = meta(d, EDGE_CLAIMS)
    written = set(rs.secondaries(
        EDGE_CLAIMS, tags(EDGE_CLAIMS), build(EDGE_CLAIMS, rows), m,
        lambda o: (frozenset({"area"}), "direct"), {f: [f] for f in "ABC"},
        {f: record(f, cited=["W_x"]) for f in "ABC"}, novelty_of(d, EDGE_CLAIMS),
        n_boot=50)) - {"bootstrap"}
    assert registered == written and len(registered) == 20


def test_secondaries_refuse_to_run_without_the_claim_dates(rows):
    d = {f: ("2020-01-01", "day") for f in "ABC"}
    with pytest.raises(ValueError):
        rs.secondaries(EDGE_CLAIMS, tags(EDGE_CLAIMS), build(EDGE_CLAIMS, rows),
                       meta(d, EDGE_CLAIMS), lambda o: (frozenset({"area"}), "direct"),
                       {f: [f] for f in "ABC"}, {}, None, n_boot=50)
    partial = novelty_of(d, EDGE_CLAIMS)
    partial.pop(EDGE_CLAIMS[0].claim_record_id)
    with pytest.raises(ValueError):
        rs.pair_claim_dates(EDGE_CLAIMS, partial)


def test_the_registered_reading_table_has_one_row_per_reachable_verdict_pair():
    text = (rs.EXP / "PREREG.md").read_text()
    table = text.split("**Reading the two verdicts.**")[1].split("Neither a contradicted")[0]
    rows_ = re.findall(r"^\| (supported|unresolved|contradicted) \| "
                       r"(supported|unresolved|contradicted) \|", table, re.M)
    assert set(rows_) == set(READINGS) and len(rows_) == 6


def test_accounting_counts_every_edge_of_a_pair_with_three_families(rows):
    claims = [claim("A", "P1"), claim("B", "P1"), claim("C", "P1")]
    d = {"A": ("2020-01-01", "day"), "B": ("2021-01-01", "day"), "C": ("2022-01-01", "day")}
    table = {r["index"]: r for r in rs.accounting(build(claims, rows), claims, None,
                                                   meta(d, claims), claim_dates(d, claims))}
    assert (table["edge_relations"]["n"], table["edge_relations"]["edge_n"]) == (1, 3)
    assert (table["first_claim_concordance"]["n"],
            table["first_claim_concordance"]["edge_n"]) == (1, 2)
    assert table["citation_of_earlier_claim"]["n"] == 2
