import datetime
import pathlib

import pytest

import assemble_screening_set as ass
from assemble_registry import FamilyMeta
from build_registry import PublicDate, RegistryClaim, build
from claim_tags import ClaimTags
from dataset_relations import load_rows
from drug_joins import alignment_expectation
from hub_proteins import count_hubs, hub_expectation
from pathway_enrichment import enrich
from reference_screen import load_zheng_source_rows, source_group
from sensitivity_analyses import claim_specific_names_only, stated_tested_count

FIX = pathlib.Path(__file__).resolve().parent / "fixtures" / "search"
AREAS = {"O_cad": {"cardio", "genetic"}, "O_heart": {"cardio"}, "O_lung": {"cancer"},
         "O_asthma": {"resp"}, "O_crp": set()}


@pytest.fixture(scope="module")
def rows():
    return load_rows()


def claim(rid, protein, outcome="O", direction="raises", pqtl=("not_stated",),
          attribution="whole_study", family="F"):
    return RegistryClaim(
        claim_record_id=rid, family_id=family, protein_id=protein, outcome_id=outcome,
        direction=direction, direction_verified=True, claim_scope="overall", context_key=rid,
        pqtl_datasets=pqtl, outcome_datasets=("FinnGen R10",), dataset_attribution=attribution)


def tags(claims, wording="causal"):
    return {c.claim_record_id: ClaimTags(
        claim_record_id=c.claim_record_id, pmid="1", wording_class=wording,
        novelty_language=False, platform=("not_stated",), ancestry="not_stated") for c in claims}


def areas(outcome):
    return frozenset(AREAS[outcome])


def test_hub_expectation_matches_the_exact_share_of_outcome_assignments():
    # P1 holds four of seven counted records; it is a hub when its four outcomes include lung
    # cancer, asthma and a cardiovascular outcome: 16 of the 35 choices of four records.
    spec = [("P1", "O_cad"), ("P1", "O_lung"), ("P1", "O_asthma"), ("P1", "O_cad"),
            ("P2", "O_heart"), ("P2", "O_cad"), ("P5", "O_asthma"), ("P3", "O_crp")]
    claims = [claim(str(i), p, o) for i, (p, o) in enumerate(spec)]
    out = hub_expectation(claims, tags(claims), areas, n_permutations=4000)
    assert out["counted_claim_records_with_a_disease_area"] == 7
    assert out["observed_hubs"] == 1
    assert out["expected_hubs"] == pytest.approx(16 / 35, abs=0.03)
    assert out["observed_over_expected"] == pytest.approx(35 / 16, rel=0.08)


def test_hub_expectation_equals_the_observed_count_when_permutation_changes_nothing():
    claims = [claim(str(i), "P1", o) for i, o in enumerate(["O_heart", "O_lung", "O_asthma"])]
    out = hub_expectation(claims, tags(claims), areas, n_permutations=200)
    assert (out["observed_hubs"], out["expected_hubs"], out["observed_over_expected"]) == (
        1, 1.0, 1.0)
    assert out["permutation_interval"] == [1.0, 1.0]


def test_hub_expectation_leaves_out_association_and_null_result_claims():
    claims = [claim("0", "P1", "O_heart"), claim("1", "P1", "O_lung"),
              claim("2", "P1", "O_asthma", direction="reported_nonsignificant_or_null")]
    out = hub_expectation(claims, tags(claims), areas, n_permutations=50)
    assert (out["counted_claim_records_with_a_disease_area"], out["observed_hubs"]) == (2, 0)
    assert hub_expectation(claims, tags(claims, "association"), areas, n_permutations=50)[
        "counted_claim_records_with_a_disease_area"] == 0
    counted = hub_expectation(claims, tags(claims), areas, n_permutations=50, count_null=True)
    assert counted["observed_hubs"] == 1


def test_count_hubs_needs_three_areas_to_cover_a_proteins_outcomes():
    cad, heart, lung, asthma = (frozenset(AREAS[o]) for o in
                                ("O_cad", "O_heart", "O_lung", "O_asthma"))
    assert count_hubs(["P1"] * 3, [cad, heart, lung]) == 0
    assert count_hubs(["P1"] * 3, [cad, lung, asthma]) == 1
    assert count_hubs(["P1", "P1", "P2"], [cad, lung, asthma]) == 0
    assert count_hubs(["P1"] * 2, [cad, lung], distinct_areas=True) == 1


def test_alignment_expectation_from_the_two_margins():
    rows = [("decrease", "concordant")] * 3 + [("increase", "concordant"),
                                               ("decrease", "discordant"),
                                               ("decrease", "mixed"), ("increase", "no_drug"),
                                               (None, None)]
    out = alignment_expectation(rows)
    assert out["claims_concordant_or_discordant"] == 5
    assert out["share_of_claims_indicating_a_decrease"] == pytest.approx(0.8)
    assert out["share_of_claims_whose_drugs_decrease"] == pytest.approx(0.6)
    assert out["observed_concordant_share"] == pytest.approx(0.8)
    assert out["expected_concordant_share"] == pytest.approx(0.8 * 0.6 + 0.2 * 0.4)


def test_alignment_expectation_is_one_when_every_claim_and_drug_point_one_way():
    out = alignment_expectation([("decrease", "concordant")] * 4)
    assert (out["observed_concordant_share"], out["expected_concordant_share"]) == (1.0, 1.0)
    assert alignment_expectation([("decrease", "no_drug")])["expected_concordant_share"] is None


def test_a_pathway_is_named_only_with_q_below_005_and_three_claimed_proteins():
    background = frozenset(f"B{i:03d}" for i in range(400))
    pathways = {"X": frozenset(f"B{i:03d}" for i in range(10)),
                "Y": frozenset(f"B{i:03d}" for i in range(10, 20))}
    names = {"X": "x", "Y": "y"}
    two, _ = enrich("list", {"B000", "B001"}, background, pathways, names)
    by_id = {r.pathway_id: r for r in two}
    assert by_id["X"].q_benjamini_hochberg < 0.05 and by_id["X"].claimed_in_pathway == 2
    assert by_id["X"].named_in_text is False
    three, _ = enrich("list", {"B000", "B001", "B002"}, background, pathways, names)
    by_id = {r.pathway_id: r for r in three}
    assert by_id["X"].named_in_text is True and by_id["Y"].named_in_text is False
    spread, _ = enrich("list", {"B000", "B010", "B020", "B030"}, background, pathways, names)
    assert not any(r.named_in_text for r in spread)
    # Three claimed proteins in a pathway that holds two thirds of a small background: q is
    # far above 0.05, so the pathway is not named.
    small = frozenset(f"B{i:03d}" for i in range(30))
    wide = {"W": frozenset(f"B{i:03d}" for i in range(20))}
    row, = enrich("list", {"B000", "B001", "B002", "B029"}, small, wide, {"W": "w"})[0]
    assert row.claimed_in_pathway == 3 and row.q_benjamini_hochberg > 0.05
    assert row.named_in_text is False


def test_reference_screen_groups_claims_by_whether_the_pqtl_source_is_a_snapshot_source(rows):
    zheng = load_zheng_source_rows()
    assert zheng == {"INTERVAL SomaScan (Sun 2018)", "KORA (Suhre 2017)",
                     "AGES Reykjavik (Emilsson 2018)", "IMPROVE (Folkersen 2017)",
                     "Framingham Heart Study (Yao 2018)",
                     "Zheng 2020 proteome-wide MR instrument set"}
    names = {"shared": ("Sun 2018",), "instrument_set": ("Zheng 2020",),
             "other": ("UKB-PPP discovery",), "ambiguous_other": ("UKB-PPP",),
             "ambiguous_shared": ("AGES",), "none": ("not_stated",),
             "unmatched": ("a cohort no dictionary row names",),
             "both": ("UKB-PPP discovery", "KORA")}
    claims = [claim(k, "P1", pqtl=v, family=k) for k, v in names.items()]
    fams = build(claims, rows)[("P1", "O")]
    got = {k: source_group(fams[k], zheng) for k in names}
    assert got == {"shared": "shared_pqtl_source", "instrument_set": "shared_pqtl_source",
                   "other": "other_pqtl_source", "ambiguous_other": "other_pqtl_source",
                   "ambiguous_shared": "shared_pqtl_source",
                   "none": "pqtl_not_stated_or_unmatched",
                   "unmatched": "pqtl_not_stated_or_unmatched", "both": "shared_pqtl_source"}


def test_claim_specific_names_only_blanks_names_not_tied_to_the_result():
    kept = claim("0", "P1", pqtl=("Sun 2018",), attribution="claim_specific")
    blanked = [claim("1", "P1", pqtl=("Sun 2018",), attribution="whole_study"),
               claim("2", "P1", pqtl=("Sun 2018",), attribution="unclear")]
    out = claim_specific_names_only([kept, *blanked])
    assert out[0] == kept
    assert [(c.pqtl_datasets, c.outcome_datasets) for c in out[1:]] == [
        (("not_stated",), ("not_stated",))] * 2
    assert [c.claim_record_id for c in out] == ["0", "1", "2"]


def test_tested_count_is_the_largest_count_a_familys_registry_abstracts_state():
    def family(records):
        return FamilyMeta(
            family_id="F", window="confirmatory", eligibility="eligible",
            first_public=PublicDate(value=datetime.date(2021, 1, 1), resolution="day"),
            also_tissue_or_csf=False, extraction="ok", fuzzy_linked=False,
            registry_records=records, dating_records=[])

    decisions = {"r1": {"n_proteins_tested": None}, "r2": {"n_proteins_tested": 1200},
                 "r3": {"n_proteins_tested": 999}, "r4": {}}
    assert stated_tested_count(family(["r1", "r2", "r3"]), decisions) == 1200
    assert stated_tested_count(family(["r1", "r4"]), decisions) is None
    assert stated_tested_count(family(["r3"]), decisions) == 999


def test_journal_title_is_read_from_pubmed_and_carried_to_the_screening_record():
    parsed = {r.pmid: r for r in ass.parse_pubmed((FIX / "pubmed_efetch.xml").read_bytes())}
    assert parsed["29875488"].journal == "Nature"
    assert parsed["30111768"].journal == "Nature communications"
    other = ass.RetrievedRecord(
        source="openalex", source_id="W1", pmid="29875488", pmcid=None, doi=None,
        kind="journal", source_type="article", title="t", abstract="",
        first_author_surname="Sun", journal="A repository",
        first_public=PublicDate(value=datetime.date(2018, 6, 6), resolution="day"))
    screening, = ass.deduplicate([other, parsed["29875488"]])
    assert screening.journal == "Nature"
    bare, = ass.deduplicate([other.model_copy(update={"pmid": None, "journal": None})])
    assert bare.journal is None
