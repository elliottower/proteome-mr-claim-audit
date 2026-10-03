import itertools

import pytest

from dataset_relations import compare_side, edge_label, load_rows, map_name, release_identity


@pytest.fixture(scope="module")
def rows():
    return load_rows()


def names(rows, side, *written):
    return [map_name(w, side, rows) for w in written]


def test_ukb_ppp_without_subset_is_ambiguous_across_all_four_releases(rows):
    m = map_name("UKB-PPP", "pqtl", rows)
    assert m.state == "release_ambiguous"
    assert m.candidates == ("UKB-PPP ancestry-specific (non-European)",
                            "UKB-PPP discovery", "UKB-PPP full cohort (combined)",
                            "UKB-PPP replication", "unlisted release of ukb ppp")
    assert m.known_components == {"UKB"}
    assert m.composition_resolved


def test_generic_consortium_name_on_one_row_never_has_a_known_release(rows):
    m = map_name("CARDIoGRAMplusC4D", "outcome", rows)
    assert m.state == "release_ambiguous"
    assert "unlisted release of cardiogramplusc4d" in m.candidates
    assert release_identity([m], [m]) == "undetermined"
    interval = map_name("INTERVAL", "pqtl", rows)
    assert interval.state == "release_ambiguous" and interval.composition_resolved
    assert release_identity([interval], [interval]) == "undetermined"


def test_a_row_name_or_an_alias_with_a_release_is_unique(rows):
    assert map_name("GeneATLAS", "outcome", rows).state == "unique"
    assert map_name("Sun 2018", "pqtl", rows).state == "unique"


def test_ukb_ppp_discovery_is_unique(rows):
    m = map_name("UKB-PPP discovery", "pqtl", rows)
    assert (m.state, m.candidates) == ("unique", ("UKB-PPP discovery",))


def test_trailing_words_never_narrow_a_prefix_match(rows):
    m = map_name("UKB-PPP European", "pqtl", rows)
    assert m.state == "release_ambiguous"
    assert len(m.candidates) == 5


def test_generic_name_never_resolves_to_the_first_row(rows):
    m = map_name("Sun et al. 2023", "pqtl", rows)
    assert m.state == "release_ambiguous"
    disc = map_name("UKB-PPP discovery", "pqtl", rows)
    assert release_identity([m], [disc]) == "undetermined"
    assert compare_side([m], [disc]) == "overlapping_participant_source"


def test_finngen_release_specific_and_generic(rows):
    r10, r8, generic = names(rows, "outcome", "FinnGen R10", "FinnGen R8", "FinnGen")
    assert r10.state == "unique" and r8.state == "unique"
    # Ten FinnGen releases plus the two FinnGen R12 meta-analyses with UK Biobank (and MVP).
    assert generic.state == "release_ambiguous" and len(generic.candidates) == 12
    assert "FinnGen R12 + UK Biobank meta-analysis" in generic.candidates
    assert generic.rule == "generic"
    assert compare_side([r10], [r10]) == "identical_release"
    assert release_identity([r10], [r10]) == "identical"
    assert compare_side([r10], [r8]) == "overlapping_participant_source"
    assert release_identity([r10], [r8]) == "not_identical"
    assert compare_side([generic], [r10]) == "overlapping_participant_source"
    assert release_identity([generic], [r10]) == "undetermined"


def test_release_specific_finngen_with_resolved_composition_can_be_disjoint(rows):
    r10 = map_name("FinnGen R10", "outcome", rows)
    ukb = map_name("Pan-UKB", "outcome", rows)
    assert compare_side([r10], [ukb]) == "disjoint"
    assert release_identity([r10], [ukb]) == "not_identical"


def test_generic_finngen_is_never_disjoint_from_uk_biobank(rows):
    # Generic "FinnGen" may name a FinnGen + UK Biobank meta-analysis, so its composition is
    # not resolved; it shares FinnGen's own sources with every candidate.
    generic = map_name("FinnGen", "outcome", rows)
    ukb = map_name("Pan-UKB", "outcome", rows)
    assert not generic.composition_resolved
    assert compare_side([generic], [ukb]) == "unclear"
    assert compare_side([generic], [map_name("FinnGen R10", "outcome", rows)]) == (
        "overlapping_participant_source")


def test_finngen_legacy_cohorts_overlap_finrisk_studies(rows):
    r10 = map_name("FinnGen R10", "outcome", rows)
    nikpay = map_name("Nikpay 2015", "outcome", rows)  # MIGen includes FINRISK
    assert "FINRISK" in r10.known_components and "FINRISK" in nikpay.known_components
    assert compare_side([r10], [nikpay]) == "overlapping_participant_source"


def test_release_plus_another_dataset_maps_to_the_meta_analysis_row(rows):
    for written in ("FinnGen R12 and UK Biobank meta-analysis", "FinnGen R12 + UKBB",
                    "FinnGen R12 meta-analysis with UK Biobank"):
        m = map_name(written, "outcome", rows)
        assert (m.state, m.rule, m.candidates) == (
            "unique", "combination", ("FinnGen R12 + UK Biobank meta-analysis",)), written
    mvp = map_name("FinnGen R12 + MVP + UK Biobank", "outcome", rows)
    assert mvp.candidates == ("FinnGen R12 + MVP + UK Biobank meta-analysis",)


def test_release_plus_another_dataset_never_maps_to_the_leading_release_alone(rows):
    r12 = map_name("FinnGen R12", "outcome", rows)
    ukb = map_name("Pan-UKB", "outcome", rows)
    for written in ("FinnGen R10 and UK Biobank meta-analysis", "FinnGen R10 + UKB"):
        m = map_name(written, "outcome", rows)
        assert m.state == "release_ambiguous" and m.rule == "combination", written
        assert "FinnGen R10" in m.candidates and not m.composition_resolved
        assert "UKB" in m.known_components
        assert compare_side([m], [ukb]) == "overlapping_participant_source"
        assert release_identity([m], [map_name("FinnGen R10", "outcome", rows)]) == (
            "undetermined")
    m = map_name("FinnGen R10 meta-analysis", "outcome", rows)  # another cohort, unnamed
    assert m.state == "release_ambiguous" and not m.composition_resolved
    assert compare_side([m], [ukb]) == "unclear"
    assert compare_side([m], [r12]) == "overlapping_participant_source"


def test_consortium_plus_uk_biobank_is_ambiguous_and_never_the_consortium_alone(rows):
    m = map_name("CARDIoGRAMplusC4D and UK Biobank", "outcome", rows)
    assert m.state == "release_ambiguous"
    assert "UK Biobank + CARDIoGRAMplusC4D CAD (van der Harst 2018)" in m.candidates
    assert "CARDIoGRAMplusC4D 1000 Genomes CAD (Nikpay 2015)" not in m.candidates
    assert "UKB" in m.known_components
    nikpay = map_name("CARDIoGRAMplusC4D 2015 + UK Biobank", "outcome", rows)
    assert nikpay.state == "release_ambiguous"
    assert compare_side([nikpay], [map_name("Pan-UKB", "outcome", rows)]) == (
        "overlapping_participant_source")


def test_two_meta_analyses_sharing_uk_biobank_overlap(rows):
    a = map_name("van der Harst 2018", "outcome", rows)
    b = map_name("Yengo 2018", "outcome", rows)
    assert a.state == b.state == "unique"
    assert compare_side([a], [b]) == "overlapping_participant_source"
    assert release_identity([a], [b]) == "not_identical"


def test_one_family_using_two_pqtl_cohorts(rows):
    two = names(rows, "pqtl", "Sun 2018", "deCODE 2023")
    fenland = names(rows, "pqtl", "Fenland")
    interval = names(rows, "pqtl", "Sun 2018")
    assert compare_side(two, fenland) == "disjoint"
    assert compare_side(two, interval) == "overlapping_participant_source"
    assert release_identity(two, interval) == "not_identical"
    assert compare_side(two, list(reversed(two))) == "identical_release"


def test_exact_release_plus_unresolved_generic_alias(rows):
    a = names(rows, "pqtl", "UKB-PPP discovery", "deCODE")
    b = names(rows, "pqtl", "UKB-PPP discovery", "Ferkingstad 2021")
    c = names(rows, "pqtl", "UKB-PPP discovery", "Fenland")
    assert compare_side(a, b) == "overlapping_participant_source"
    assert release_identity(a, b) == "undetermined"
    assert release_identity(a, c) == "not_identical"


def test_consortium_with_unknown_membership_is_never_disjoint(rows):
    imsgc = map_name("IMSGC", "outcome", rows)
    finngen = map_name("FinnGen R10", "outcome", rows)
    assert not imsgc.composition_resolved
    assert compare_side([imsgc], [finngen]) == "unclear"


def test_complete_meta_analysis_without_icelandic_participants_is_disjoint_from_decode(rows):
    koprulu = map_name("Koprulu 2026", "pqtl", rows)
    decode = map_name("deCODE 2023", "pqtl", rows)
    assert koprulu.composition_resolved
    assert compare_side([koprulu], [decode]) == "disjoint"
    assert compare_side([koprulu], [map_name("INTERVAL", "pqtl", rows)]) == (
        "overlapping_participant_source")


def test_consortium_with_a_known_shared_component_overlaps(rows):
    glgc = map_name("GLGC 2021", "outcome", rows)
    saige = map_name("UKB-SAIGE", "outcome", rows)
    assert not glgc.composition_resolved
    assert compare_side([glgc], [saige]) == "overlapping_participant_source"


def test_ckdgen_2019_discovery_has_no_uk_biobank(rows):
    ckdgen = map_name("Wuttke 2019", "outcome", rows)
    saige = map_name("UKB-SAIGE", "outcome", rows)
    assert ckdgen.composition_resolved and "UKB" not in ckdgen.known_components
    assert compare_side([ckdgen], [saige]) == "disjoint"
    assert "INTERVAL" in ckdgen.known_components  # INTERVAL is a CKDGen discovery study


def test_ages_and_decode_are_separate_sources_whose_overlap_is_unclear(rows):
    ages = map_name("AGES-Reykjavik", "pqtl", rows)
    decode = map_name("deCODE 2023", "pqtl", rows)
    assert ages.composition_resolved and decode.composition_resolved
    assert ages.known_components == {"AGES_REYKJAVIK"}
    assert decode.known_components == {"DECODE_COHORT"}
    assert compare_side([ages], [decode]) == "unclear"
    assert compare_side([decode], [ages]) == "unclear"
    assert compare_side([decode], [map_name("Ferkingstad 2021", "pqtl", rows)]) == (
        "overlapping_participant_source")
    # Zheng 2020 instruments include AGES; deCODE alone shares no component with them.
    zheng = map_name("Zheng 2020", "pqtl", rows)
    assert "AGES_REYKJAVIK" in zheng.known_components
    assert compare_side([zheng], [decode]) == "unclear"
    assert compare_side([zheng], [ages]) == "overlapping_participant_source"


def test_icelandic_flag_without_a_named_icelandic_cohort_is_incomplete(rows):
    sle = next(r for r in rows if r.name == "SLE (Bentham 2015)")
    assert not sle.complete


def test_not_stated_and_unmatched_names_are_unclear(rows):
    ns = map_name("not_stated", "pqtl", rows)
    unknown = map_name("Qwerty Cohort", "pqtl", rows)
    interval = map_name("INTERVAL", "pqtl", rows)
    assert ns.state == "not_stated" and unknown.state == "unmatched"
    assert compare_side([ns], [interval]) == "unclear"
    assert compare_side([unknown], [interval]) == "unclear"
    assert release_identity([unknown], [interval]) == "undetermined"


def test_unmatched_name_still_overlaps_on_a_known_component(rows):
    unknown = map_name("Qwerty Cohort", "pqtl", rows)
    interval = map_name("INTERVAL", "pqtl", rows)
    assert compare_side([unknown, interval], [interval]) == "overlapping_participant_source"


def test_side_is_respected(rows):
    assert map_name("deCODE", "outcome", rows).candidates == (
        "deCODE genetics outcome GWAS (summary data)", "unlisted release of decode")


def test_unclear_attribution_on_either_side_makes_the_side_unclear(rows):
    a = [map_name("INTERVAL", "pqtl", rows)]
    b = [map_name("Fenland", "pqtl", rows)]
    assert compare_side(a, b) == "disjoint"
    assert compare_side(a, b, a_attribution_clear=False, b_attribution_clear=True) == "unclear"
    assert compare_side(a, b, a_attribution_clear=True, b_attribution_clear=False) == "unclear"
    assert compare_side(a, b, a_attribution_clear=False, b_attribution_clear=False) == "unclear"
    assert compare_side(a, b) == compare_side(b, a)


@pytest.mark.parametrize("side", ["pqtl", "outcome"])
def test_compare_side_and_release_identity_are_symmetric_over_every_dictionary_pair(rows, side):
    maps = [map_name(r.name, side, rows) for r in rows if r.side == side]
    flags = list(itertools.product([True, False], repeat=2))
    for x, y in itertools.combinations(maps, 2):
        for fa, fb in flags:
            assert compare_side([x], [y], fa, fb) == compare_side([y], [x], fb, fa), (
                x.written, y.written, fa, fb)
            if not (fa and fb):
                assert compare_side([x], [y], fa, fb) == "unclear"
        assert release_identity([x], [y]) == release_identity([y], [x])


def test_edge_labels():
    assert edge_label("disjoint", "disjoint") == "independent"
    assert edge_label("disjoint", "overlapping_participant_source") == "overlapping"
    assert edge_label("identical_release", "unclear") == "overlapping"
    assert edge_label("disjoint", "unclear") == "unclear"
