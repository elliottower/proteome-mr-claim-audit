import datetime
import random

import pytest

from build_registry import (READINGS, PublicDate, RegistryClaim, build, estimates,
                            family_jackknife, family_pair_direction, h2_verdict, novelty_class,
                            pair_bootstrap, protein_cluster_bootstrap, tables,
                            two_verdict_reading)
from dataset_relations import load_rows

# Complete, mutually disjoint pQTL sources; the complete outcome sources in the dictionary are
# FinnGen and UK Biobank-only GWAS, so rows 0 and 2 overlap on the outcome side.
DISJOINT = [(("Sun 2018",), ("FinnGen R10",)), (("Fenland",), ("Pan-UKB",)),
            (("deCODE 2023",), ("FinnGen R12",))]


@pytest.fixture(scope="module")
def rows():
    return load_rows()


def claim(family, pair=("P1", "O1"), direction="raises", verified=True, scope="overall",
          context="", pqtl=("Sun 2018",), outcome=("FinnGen R10",),
          attribution="whole_study", rid=None):
    return RegistryClaim(
        claim_record_id=rid or f"{family}-{pair}-{context}-{direction}", family_id=family,
        protein_id=pair[0], outcome_id=pair[1], direction=direction,
        direction_verified=verified, claim_scope=scope, context_key=context,
        pqtl_datasets=pqtl, outcome_datasets=outcome, dataset_attribution=attribution)


def test_family_pair_direction_rules():
    ns = "reported_nonsignificant_or_null"
    assert family_pair_direction([claim("A"), claim("A", context="x")]) == "raises"
    assert family_pair_direction([claim("A"), claim("A", direction="lowers")]) == "mixed"
    assert family_pair_direction([claim("A"), claim("A", direction=ns)]) == (
        "raises_with_nonsignificant")
    assert family_pair_direction([claim("A", direction=ns)]) == "nonsignificant_only"
    assert family_pair_direction([claim("A", verified=False)]) == "unresolved"
    assert family_pair_direction([claim("A", direction="not_stated")]) == "unresolved"
    assert family_pair_direction([claim("A"), claim("A", direction="lowers",
                                                    verified=False)]) == "raises"


def test_identical_records_deduplicate_but_distinct_contexts_are_kept(rows):
    reg = build([claim("A"), claim("A", rid="dup"), claim("A", context="FinnGen")], rows)
    assert reg[("P1", "O1")]["A"].n_records == 2


def test_context_unclear_is_flagged_not_merged(rows):
    reg = build([claim("A"), claim("A", scope="unclear", context="y")], rows)
    fp = reg[("P1", "O1")]["A"]
    assert fp.context_unclear and fp.n_records == 2 and fp.direction == "raises"


def test_pair_with_three_families(rows):
    claims = [claim(f, direction=d, pqtl=pq, outcome=oc)
              for f, d, (pq, oc) in zip("ABC", ["raises", "raises", "lowers"], DISJOINT)]
    e = estimates(build(claims, rows))
    assert e["h1_pairs"] == 1 and e["h1_pairs_agreeing"] == 0
    assert e["h1_independent_edges"] == 2 and e["h1_independent_edges_agreeing"] == 1
    assert e["liu_analogue_tiers"] == {"discordant": 1}


def test_mixed_family_leaves_h1_and_is_counted(rows):
    claims = [claim("A"), claim("A", direction="lowers", context="sub"),
              claim("B", pqtl=DISJOINT[1][0], outcome=DISJOINT[1][1])]
    t = tables(build(claims, rows), n_boot=200)
    assert t["denominators"]["by_direction"] == {"mixed": 1, "raises": 1}
    assert t["estimates"]["h1_pairs"] == 0


def test_overlapping_or_unclear_edges_never_enter_h1(rows):
    claims = [claim("A"), claim("B", direction="lowers"),
              claim("C", pqtl=("not_stated",), outcome=("FinnGen R12",))]
    e = estimates(build(claims, rows))
    assert e["h1_pairs"] == 0
    assert e["liu_analogue_pairs"] == 1


def test_h2_classes_and_bounds(rows):
    claims = [
        claim("A", pair=("P1", "O1")), claim("B", pair=("P1", "O1")),
        claim("A", pair=("P2", "O1")), claim("B", pair=("P2", "O1"), outcome=("FinnGen R12",)),
        claim("A", pair=("P3", "O1")), claim("B", pair=("P3", "O1"), outcome=("FinnGen",)),
        claim("A", pair=("P4", "O1")),
    ]
    e = estimates(build(claims, rows))
    assert (e["h2_multi_family_pairs"], e["h2_known_identical"], e["h2_known_not_identical"],
            e["h2_unresolved"]) == (3, 1, 1, 1)
    assert e["h2_lower"] == pytest.approx(1 / 3)
    assert e["h2_upper"] == pytest.approx(2 / 3)
    assert e["h2_complete_case"] == pytest.approx(1 / 2)


def test_one_family_with_many_pairs_dominates_the_jackknife(rows):
    claims = []
    for i in range(30):
        pair = (f"P{i}", "O1")
        claims += [claim("BIG", pair=pair), claim(f"S{i}", pair=pair)]
    for i in range(30, 40):
        pair = (f"P{i}", "O1")
        claims += [claim(f"X{i}", pair=pair, outcome=("FinnGen R12",)),
                   claim(f"Y{i}", pair=pair)]
    reg = build(claims, rows)
    e = estimates(reg)
    assert e["h2_lower"] == pytest.approx(30 / 40)
    jk = family_jackknife(reg)
    assert jk["h2_lower"]["min"] == pytest.approx(0.0)
    assert jk["h2_lower"]["min_when_dropping"] == "BIG"


def test_pair_bootstrap_resamples_pairs_not_families(rows):
    claims = [claim("A"), claim("B", pqtl=DISJOINT[1][0], outcome=DISJOINT[1][1])]
    boot = pair_bootstrap(estimates(build(claims, rows)), n_boot=2000)
    assert boot["h1_pair_concordance"] == [1.0, 1.0]
    assert boot["h1_edge_concordance"] == [1.0, 1.0]


def test_pair_bootstrap_distribution_on_two_pairs(rows):
    claims = [claim("A", pair=("P1", "O1")),
              claim("B", pair=("P1", "O1"), pqtl=DISJOINT[1][0], outcome=DISJOINT[1][1]),
              claim("A", pair=("P2", "O1")),
              claim("B", pair=("P2", "O1"), direction="lowers", pqtl=DISJOINT[1][0],
                    outcome=DISJOINT[1][1])]
    e = estimates(build(claims, rows))
    assert e["h1_pair_concordance"] == pytest.approx(0.5)
    boot = pair_bootstrap(e, n_boot=10_000)
    assert boot["h1_pair_concordance"] == [0.0, 1.0]


def test_h2_verdict_reads_the_observed_bounds_with_strict_inequality_at_one_half():
    assert h2_verdict({"h2_lower": 0.5, "h2_upper": 0.7}) == "unresolved"
    assert h2_verdict({"h2_lower": 0.51, "h2_upper": 0.7}) == "supported"
    assert h2_verdict({"h2_lower": 0.1, "h2_upper": 0.5}) == "contradicted"
    assert h2_verdict({"h2_lower": 0.1, "h2_upper": 0.51}) == "unresolved"
    assert h2_verdict({"h2_lower": None, "h2_upper": None}) == "no_multi_family_pairs"


def test_verdict_is_set_by_the_bounds_not_by_the_bootstrap(rows):
    # 11 of 20 pairs identical and the rest known not identical: lower = upper = 0.55. The
    # bootstrap 2.5th percentile of the lower bound falls below one half; the verdict does not
    # read it.
    claims = []
    for i in range(20):
        pair = (f"P{i}", "O1")
        other = ("FinnGen R10",) if i < 11 else ("FinnGen R12",)
        claims += [claim("A", pair=pair), claim("B", pair=pair, outcome=other)]
    t = tables(build(claims, rows), n_boot=2000)
    assert (t["estimates"]["h2_lower"], t["estimates"]["h2_upper"]) == (0.55, 0.55)
    assert t["pair_bootstrap"]["h2_lower"][0] < 0.5
    assert t["h2_verdict"] == "supported" and t["verdict_rule"] == "finite_corpus_bounds"


def test_novelty_same_day_and_mixed_resolution():
    d = lambda y, m, dd, r: PublicDate(value=datetime.date(y, m, dd), resolution=r)
    claim_date = d(2022, 5, 10, "day")
    assert novelty_class(claim_date, [d(2022, 5, 10, "day")]) == "tied_or_unknown_order"
    assert novelty_class(claim_date, [d(2022, 5, 9, "day")]) == "earlier_in_registry"
    assert novelty_class(claim_date, [d(2022, 5, 1, "month")]) == "tied_or_unknown_order"
    assert novelty_class(claim_date, [d(2022, 4, 1, "month")]) == "earlier_in_registry"
    assert novelty_class(claim_date, [d(2022, 1, 1, "year")]) == "tied_or_unknown_order"
    assert novelty_class(claim_date, [d(2023, 1, 1, "day")]) == "no_earlier_in_registry"


def test_h2b_classes_bounds_and_resolvable_share(rows):
    ppp, generic = ("UKB-PPP discovery",), ("UKB-PPP",)
    claims = [
        claim("A", pair=("P1", "O1")), claim("B", pair=("P1", "O1")),                # identical
        claim("A", pair=("P2", "O1")), claim("B", pair=("P2", "O1"), outcome=("FinnGen R12",)),
        claim("A", pair=("P3", "O1")), claim("B", pair=("P3", "O1"), pqtl=("Fenland",),
                                             outcome=("Pan-UK Biobank",)),           # disjoint
        claim("A", pair=("P4", "O1"), pqtl=ppp), claim("B", pair=("P4", "O1"), pqtl=generic),
        claim("A", pair=("P5", "O1")), claim("B", pair=("P5", "O1"), pqtl=("not_stated",)),
        claim("A", pair=("P6", "O1")),
    ]
    e = estimates(build(claims, rows))
    assert (e["h2_known_identical"], e["h2_known_not_identical"], e["h2_unresolved"]) == (1, 2, 2)
    assert (e["h2b_known_overlapping"], e["h2b_known_not_overlapping"],
            e["h2b_unresolved"]) == (3, 1, 1)
    assert (e["h2b_lower"], e["h2b_upper"]) == (pytest.approx(0.6), pytest.approx(0.8))
    assert e["h2b_complete_case"] == pytest.approx(0.75)
    # "Fenland" names no release, so only P1 and P2 name one release on every side.
    assert (e["h2_resolvable_pairs"], e["h2_resolvable_share"]) == (2, pytest.approx(0.4))
    assert e["h2_lower"] <= e["h2_resolvable_share"]
    assert e["h2_h2b_pairs_not_nested"] == 0


def test_unclear_attribution_makes_release_identity_undetermined_and_the_pair_unresolvable(rows):
    claims = [claim("A"), claim("B", attribution="unclear")]
    e = estimates(build(claims, rows))
    assert (e["h2_known_identical"], e["h2_known_not_identical"], e["h2_unresolved"]) == (0, 0, 1)
    assert (e["h2b_known_overlapping"], e["h2b_known_not_overlapping"],
            e["h2b_unresolved"]) == (0, 0, 1)
    assert (e["h2_resolvable_pairs"], e["h2_h2b_pairs_not_nested"]) == (0, 0)


def test_unclear_attribution_on_either_family_is_symmetric(rows):
    one = estimates(build([claim("A", attribution="unclear"), claim("B")], rows))
    two = estimates(build([claim("A"), claim("B", attribution="unclear")], rows))
    keys = ("h2_known_identical", "h2_unresolved", "h2b_known_overlapping", "h2b_unresolved",
            "h2_resolvable_pairs")
    assert [one[k] for k in keys] == [two[k] for k in keys] == [0, 1, 0, 1, 0]


def test_claim_specific_names_can_establish_overlap_but_never_identity_or_disjointness(rows):
    # B has an unclear record and a claim-specific record naming Sun 2018 and FinnGen R10, the
    # releases A names: the claim-specific names share components with A's on both sides.
    shared = [claim("A"), claim("B", attribution="unclear", context="x"),
              claim("B", attribution="claim_specific", context="y")]
    e = estimates(build(shared, rows))
    assert (e["h2_known_identical"], e["h2_unresolved"]) == (0, 1)
    assert (e["h2b_known_overlapping"], e["h2b_unresolved"]) == (1, 0)
    # A claim-specific record on disjoint releases does not make the pair disjoint.
    apart = [claim("A"), claim("B", attribution="unclear", context="x"),
             claim("B", attribution="claim_specific", context="y", pqtl=("Fenland",),
                   outcome=("Pan-UK Biobank",))]
    e = estimates(build(apart, rows))
    assert (e["h2b_known_overlapping"], e["h2b_known_not_overlapping"],
            e["h2b_unresolved"]) == (0, 0, 1)


def test_h2b_is_nested_in_h2_on_random_registries(rows):
    rng = random.Random()
    names = [(("Sun 2018",), ("FinnGen R10",)), (("Sun 2018",), ("FinnGen R12",)),
             (("Fenland",), ("Pan-UK Biobank",)), (("UKB-PPP",), ("FinnGen",)),
             (("UKB-PPP discovery",), ("Pan-UKB",)), (("not_stated",), ("FinnGen R10",)),
             (("deCODE 2023",), ("not_stated",)), (("INTERVAL",), ("UK Biobank",))]
    readings = set(READINGS.values())
    for _ in range(40):
        claims = []
        for p in range(rng.randint(3, 14)):
            for f in rng.sample("ABCDEF", rng.randint(2, 4)):
                pq, oc = rng.choice(names)
                claims.append(claim(f, pair=(f"P{p}", "O1"), pqtl=pq, outcome=oc,
                                    attribution=rng.choice(["whole_study", "claim_specific",
                                                            "unclear"])))
        est = estimates(build(claims, rows))
        boot = pair_bootstrap(est, n_boot=300)
        assert est["h2_h2b_pairs_not_nested"] == 0
        assert est["h2b_lower"] >= est["h2_lower"] and est["h2b_upper"] >= est["h2_upper"]
        assert boot["h2b_lower"][0] >= boot["h2_lower"][0]
        assert boot["h2b_upper"][1] >= boot["h2_upper"][1]
        assert boot["h2_resolvable_share"][0] >= boot["h2_lower"][0]
        assert est["h2_resolvable_share"] >= est["h2_lower"]
        assert two_verdict_reading(h2_verdict(est), h2_verdict(est, "h2b")) in readings


def test_h2b_verdict_uses_the_same_three_way_rule():
    assert h2_verdict({"h2b_lower": 0.51, "h2b_upper": 0.95}, "h2b") == "supported"
    assert h2_verdict({"h2b_lower": 0.5, "h2b_upper": 0.95}, "h2b") == "unresolved"
    assert h2_verdict({"h2b_lower": 0.1, "h2b_upper": 0.5}, "h2b") == "contradicted"
    assert h2_verdict({"h2_lower": 0.6, "h2_upper": 0.9}, "h2b") == "no_multi_family_pairs"


def test_two_verdict_reading_names_the_six_combinations_that_can_occur():
    assert two_verdict_reading("supported", "supported") == "majority_on_identical_releases"
    assert two_verdict_reading("unresolved", "unresolved") == (
        "neither_share_placed_on_one_side_of_one_half")
    assert two_verdict_reading("contradicted", "supported") == (
        "majority_on_overlapping_sources_identical_at_most_half")
    assert len(READINGS) == 6
    for impossible in (("supported", "unresolved"), ("supported", "contradicted"),
                       ("unresolved", "contradicted")):
        assert impossible not in READINGS
        assert two_verdict_reading(*impossible) == "not_nested"
    assert two_verdict_reading("no_multi_family_pairs", "no_multi_family_pairs") == (
        "no_multi_family_pairs")


def test_tables_report_both_verdicts_their_reading_and_the_resampling_displays(rows):
    claims = []
    for i in range(30):
        pair = (f"P{i}", "O1")
        claims += [claim(f"A{i}", pair=pair), claim(f"B{i}", pair=pair,
                                                    outcome=("FinnGen R12",))]
    t = tables(build(claims, rows), n_boot=500)
    # Every pair names FinnGen R10 against R12: never identical, always overlapping.
    assert (t["h2_verdict"], t["h2b_verdict"]) == ("contradicted", "supported")
    assert t["two_verdict_reading"] == "majority_on_overlapping_sources_identical_at_most_half"
    assert "two_verdicts_at_bonferroni_level" not in t
    assert "bonferroni_two_verdicts" not in t["pair_bootstrap"]
    assert t["resampling_stability"] == ["pair_bootstrap", "protein_cluster_bootstrap",
                                         "family_jackknife"]
    assert t["estimates"]["h2_resolvable_share"] == 1.0 and t["h2_supported_attainable"] is True


def test_protein_cluster_bootstrap_resamples_proteins_with_all_their_pairs(rows):
    claims = []
    for i in range(9):
        claims += [claim("A", pair=("P1", f"O{i}")), claim("B", pair=("P1", f"O{i}"))]
    claims += [claim("A", pair=("P2", "O1")), claim("B", pair=("P2", "O1"),
                                                    outcome=("FinnGen R12",))]
    est = estimates(build(claims, rows))
    assert est["h2_lower"] == pytest.approx(0.9)
    cluster = protein_cluster_bootstrap(est, n_boot=4000)
    # Two proteins: both P1 gives 1, both P2 gives 0, one of each gives 0.9; each of the first
    # two has probability 1/4, so the 2.5th and 97.5th percentiles are 0 and 1.
    assert cluster["h2_lower"] == [0.0, 1.0]
    assert (cluster["h2_proteins"], cluster["unit"]) == (2, "protein")
    assert pair_bootstrap(est, n_boot=4000)["h2_lower"][0] >= 0.5


def test_bootstrap_bounds_of_fully_unresolved_pairs_are_zero_and_one(rows):
    claims = []
    for i in range(12):
        pair = (f"P{i}", "O1")
        claims += [claim("A", pair=pair), claim("B", pair=pair, pqtl=("not_stated",),
                                                outcome=("not_stated",))]
    t = tables(build(claims, rows), n_boot=300)
    boot = t["pair_bootstrap"]
    for hypothesis in ("h2", "h2b"):
        assert boot[f"{hypothesis}_lower"] == [0.0, 0.0]
        assert boot[f"{hypothesis}_upper"] == [1.0, 1.0]
    assert boot["h2_resolvable_share"] == [0.0, 0.0]
    assert (t["h2_verdict"], t["h2b_verdict"]) == ("unresolved", "unresolved")
    assert t["two_verdict_reading"] == "neither_share_placed_on_one_side_of_one_half"
    assert t["h2_supported_attainable"] is False


def test_h2_supported_is_unattainable_when_at_most_half_the_pairs_are_resolvable(rows):
    claims = []
    for i in range(10):
        pair = (f"P{i}", "O1")
        named = ("Sun 2018",) if i < 5 else ("not_stated",)
        claims += [claim("A", pair=pair), claim("B", pair=pair, pqtl=named)]
    t = tables(build(claims, rows), n_boot=300)
    assert t["estimates"]["h2_resolvable_share"] == pytest.approx(0.5)
    assert t["estimates"]["h2_lower"] == pytest.approx(0.5)
    assert t["h2_supported_attainable"] is False
