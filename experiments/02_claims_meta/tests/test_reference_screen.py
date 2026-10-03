import pytest

from build_registry import RegistryClaim
from dataset_relations import load_rows
from reference_screen import (TRAIT_FIELDS, Snapshot, after_last_colon, first_tier, icd10_code,
                              load_mapping, load_trait_aliases, map_exposure, map_trait, screen,
                              write_mapping)

PROTEINS = {"IL6R": "P_IL6R", "F11": "P_F11", "APOB": "P_APOB", "CPLX": None}
TRAITS = {"Coronary heart disease": "MONDO:chd", "Myocardial infarction": "MONDO:mi",
          "CHD (second GWAS)": "MONDO:chd", "Odd trait": None, "Stroke": "MONDO:stroke"}
ESTIMATES = [
    {"expID": "IL6R", "outID": "Coronary heart disease", "beta": -0.2},
    {"expID": "IL6R", "outID": "CHD (second GWAS)", "beta": -0.1},
    {"expID": "F11", "outID": "Coronary heart disease", "beta": 0.3},
    {"expID": "F11", "outID": "CHD (second GWAS)", "beta": -0.3},
    {"expID": "APOB", "outID": "Coronary heart disease", "beta": 0.0},
    {"expID": "APOB", "outID": "Myocardial infarction", "beta": 0.4},
    {"expID": "APOB", "outID": "Odd trait", "beta": 0.9},
    {"expID": "CPLX", "outID": "Stroke", "beta": 0.5},
]


@pytest.fixture()
def snapshot():
    return Snapshot(PROTEINS, TRAITS, ESTIMATES)


@pytest.mark.parametrize("pair, direction, expected", [
    (("P_IL6R", "MONDO:chd"), "lowers", "present_same"),
    (("P_IL6R", "MONDO:chd"), "raises", "present_opposite"),
    (("P_IL6R", "MONDO:chd"), None, "present_nondirectional_or_ambiguous"),
    (("P_F11", "MONDO:chd"), "raises", "present_nondirectional_or_ambiguous"),
    (("P_APOB", "MONDO:chd"), "raises", "present_nondirectional_or_ambiguous"),
    (("P_APOB", "MONDO:mi"), "raises", "present_same"),
    (("P_IL6R", "MONDO:mi"), "raises", "no_returned_record"),
    (("P_IL6R", "MONDO:stroke"), "raises", "no_returned_record"),
    (("P_OTHER", "MONDO:chd"), "raises", "mapping_failed"),
    (("P_IL6R", "MONDO:unmapped"), "raises", "mapping_failed"),
])
def test_reference_classes(snapshot, pair, direction, expected):
    assert snapshot.classify(pair, direction) == expected


def test_estimates_on_unmapped_names_create_no_record(snapshot):
    assert snapshot.records == 8 and snapshot.records_on_mapped_pairs == 6
    assert ("P_APOB", None) not in snapshot.directions
    assert snapshot.proteins == {"P_IL6R", "P_F11", "P_APOB"}
    assert snapshot.outcomes == {"MONDO:chd", "MONDO:mi", "MONDO:stroke"}


def test_first_tier_stops_at_the_first_tier_with_a_hit():
    tiers = [{"chd": {"MONDO:1"}}, {"chd": {"EFO:9"}, "mi": {"MONDO:2", "MONDO:3"}}]
    assert first_tier({"chd", "mi"}, tiers) == (["MONDO:1"], 0)
    assert first_tier({"mi"}, tiers) == (["MONDO:2", "MONDO:3"], 1)
    assert first_tier({"none"}, tiers) == ([], None)


def test_trait_mapping_uses_the_outcome_variants_and_the_collision_table():
    tiers = [{}, {"bodymassindex": {"EFO:bmi"}, "asthma": {"MONDO:asthma", "EFO:asthma"},
                  "height": {"EFO:h1", "EFO:h2"}}, {}]
    collision = {"EFO:asthma": frozenset({"MONDO:asthma"})}
    assert map_trait("Body mass index (BMI)", tiers, collision)["canonical_id"] == "EFO:bmi"
    merged = map_trait("Asthma", tiers, collision)
    assert (merged["state"], merged["canonical_id"]) == ("mapped", "MONDO:asthma")
    assert map_trait("Height", tiers, collision)["state"] == "ambiguous"
    assert map_trait("Asthma", tiers, collision)["name_rule"] == "as_written"
    assert map_trait("Weight", tiers, collision)["name_rule"] is None


@pytest.mark.parametrize("name, tail", [
    ("Non-cancer illness code  self-reported: asthma", "asthma"),
    ("Diagnoses - main ICD10: K80 Cholelithiasis", "Cholelithiasis"),
    ("Underlying (primary) cause of death: ICD10: E85.4 Organ-limited amyloidosis",
     "Organ-limited amyloidosis"),
    ("Hearing difficulty or problems: Yes", "Yes"),
    ("Asthma", None), ("Ratio 2:1 of something", None)])
def test_text_after_the_last_colon_without_its_icd_code(name, tail):
    assert after_last_colon(name) == tail


def test_field_name_is_mapped_from_the_text_after_its_last_colon_only_when_unmapped_as_written():
    tiers = [{}, {"asthma": {"MONDO:asthma"}, "cholelithiasis": {"MONDO:gallstones"},
                  "eyeproblemsordisorderscataract": {"EFO:field"},
                  "cataract": {"MONDO:cataract"}}, {}]
    field = map_trait("Non-cancer illness code  self-reported: asthma", tiers, {})
    assert (field["state"], field["canonical_id"], field["name_rule"]) == (
        "mapped", "MONDO:asthma", "after_last_colon")
    icd = map_trait("Diagnoses - main ICD10: K80 Cholelithiasis", tiers, {})
    assert (icd["canonical_id"], icd["name_rule"]) == ("MONDO:gallstones", "after_last_colon")
    whole = map_trait("Eye problems or disorders: Cataract", tiers, {})
    assert (whole["canonical_id"], whole["name_rule"]) == ("EFO:field", "as_written")
    none = map_trait("Hearing difficulty or problems: Yes", tiers, {})
    assert (none["state"], none["name_rule"]) == ("unmapped", None)


def alias(term, relation="normalized_equivalent"):
    return {"term_id": term, "alias_relation": relation}


def test_alias_table_is_read_before_the_label_rules():
    tiers = [{}, {"height": {"EFO:h1", "EFO:h2"}, "lungadenocarcinoma": {"EFO:1", "MONDO:2"},
                  "serumcreatinine": {"OBA:creatinine"}, "asthma": {"MONDO:asthma"}}, {}]
    aliases = {"Height": alias("OBA:body_height"), "Lung adenocarcinoma": alias("MONDO:2"),
               "Serum creatinine (eGFRcrea)": alias("OBA:gfr", "derived_measurement"),
               "Weight": alias("EFO:weight", "broader_proxy")}
    assert map_trait("Height", tiers, {})["state"] == "ambiguous"
    height = map_trait("Height", tiers, {}, aliases)
    assert (height["state"], height["canonical_id"], height["name_rule"], height["tier"],
            height["alias_relation"]) == ("mapped", "OBA:body_height", "alias_table", None,
                                          "normalized_equivalent")
    assert map_trait("Lung adenocarcinoma", tiers, {}, aliases)["canonical_id"] == "MONDO:2"
    # Its words alone would map the trait to serum creatinine.
    assert map_trait("Serum creatinine (eGFRcrea)", tiers, {})["canonical_id"] == (
        "OBA:creatinine")
    gfr = map_trait("Serum creatinine (eGFRcrea)", tiers, {}, aliases)
    assert (gfr["canonical_id"], gfr["name_rule"], gfr["alias_relation"]) == (
        "OBA:gfr", "alias_table", "derived_measurement")
    asthma = map_trait("Asthma", tiers, {}, aliases)
    assert (asthma["canonical_id"], asthma["name_rule"], asthma["alias_relation"]) == (
        "MONDO:asthma", "as_written", "")
    weight = map_trait("Weight", tiers, {}, aliases)
    assert (weight["canonical_id"], weight["alias_relation"]) == ("EFO:weight", "broader_proxy")
    assert map_trait("height", tiers, {}, aliases)["name_rule"] == "as_written"
    merged = map_trait("Height", tiers, {"OBA:body_height": frozenset({"EFO:canon"})}, aliases)
    assert merged["canonical_id"] == "EFO:canon"


@pytest.mark.parametrize("name, code", [
    ("Diagnoses - main ICD10: K80 Cholelithiasis", "K80"),
    ("Underlying (primary) cause of death: ICD10: E85.4 Organ-limited amyloidosis", "E85.4"),
    ("Non-cancer illness code  self-reported: asthma", None),
    ("Asthma", None), ("Diagnoses - main ICD10: K80", "K80"),
    ("Diagnoses - main ICD10: K80x", None)])
def test_icd10_code_is_read_from_the_field_name(name, code):
    assert icd10_code(name) == code


def test_icd10_cross_reference_comes_first_when_exactly_one_term_carries_the_code():
    tiers = [{}, {"cholelithiasis": {"MONDO:label"}, "acuteappendicitis": set()}, {}]
    icd10 = {"K80": frozenset({"MONDO:gallstones"}),
             "I50": frozenset({"MONDO:hf", "MONDO:chf"}), "K35": frozenset({"MONDO:append"})}
    one = map_trait("Diagnoses - main ICD10: K80 Cholelithiasis", tiers, {}, None, icd10)
    assert (one["state"], one["canonical_id"], one["name_rule"], one["source_ids"]) == (
        "mapped", "MONDO:gallstones", "icd10_cross_reference", ["ICD10:K80"])
    assert map_trait("Diagnoses - main ICD10: K80 Cholelithiasis", tiers, {})[
        "canonical_id"] == "MONDO:label"
    # Two terms carry I50, so the code decides nothing and the label rules are read.
    two = map_trait("Diagnoses - main ICD10: I50 Heart failure", tiers, {}, None, icd10)
    assert (two["state"], two["name_rule"], sorted(two["canonical_ids"])) == (
        "ambiguous", "icd10_cross_reference", ["MONDO:chf", "MONDO:hf"])
    labelled = map_trait("Diagnoses - main ICD10: I50 Cholelithiasis", tiers, {}, None, icd10)
    assert (labelled["canonical_id"], labelled["name_rule"]) == ("MONDO:label",
                                                                 "after_last_colon")
    aliased = map_trait("Diagnoses - main ICD10: K35 Acute appendicitis", tiers, {},
                        {"Diagnoses - main ICD10: K35 Acute appendicitis": alias("MONDO:x")},
                        icd10)
    assert (aliased["canonical_id"], aliased["name_rule"]) == ("MONDO:append",
                                                               "icd10_cross_reference")
    assert map_trait("Diagnoses - main ICD10: Z99 Other", tiers, {}, None, icd10)[
        "state"] == "unmapped"


def trait_row(name, rule, relation="", state="mapped"):
    return {"name": name, "state": state, "tier": 1, "name_rule": rule,
            "alias_relation": relation, "source_ids": ["MONDO:a"], "canonical_ids": ["MONDO:a"],
            "canonical_id": "MONDO:a"}


def test_as_written_only_leaves_out_names_mapped_by_any_other_rule(tmp_path):
    rows = [trait_row("Asthma", "as_written"), trait_row("Illness: asthma", "after_last_colon"),
            trait_row("ICD10: J45 Asthma", "icd10_cross_reference"),
            trait_row("Asthma (doctor)", "alias_table", "normalized_equivalent")]
    path = tmp_path / "traits.csv"
    write_mapping(rows, path, TRAIT_FIELDS)
    assert set(load_mapping(path, "canonical_id").values()) == {"MONDO:a"}
    assert load_mapping(path, "canonical_id", as_written_only=True) == {
        "Asthma": "MONDO:a", "Illness: asthma": None, "ICD10: J45 Asthma": None,
        "Asthma (doctor)": None}


def test_proxy_aliases_are_read_only_in_the_sensitivity_join(tmp_path):
    rows = [trait_row("Exact", "alias_table", "exact_equivalent"),
            trait_row("Normalized", "alias_table", "normalized_equivalent"),
            trait_row("Broader", "alias_table", "broader_proxy"),
            trait_row("Derived", "alias_table", "derived_measurement"),
            trait_row("Label", "as_written"),
            trait_row("Unmapped", "alias_table", "exact_equivalent", state="unmapped")]
    path = tmp_path / "traits.csv"
    write_mapping(rows, path, TRAIT_FIELDS)
    assert load_mapping(path, "canonical_id") == {
        "Exact": "MONDO:a", "Normalized": "MONDO:a", "Broader": None, "Derived": None,
        "Label": "MONDO:a", "Unmapped": None}
    with_proxies = load_mapping(path, "canonical_id", proxy_aliases=True)
    assert with_proxies["Broader"] == with_proxies["Derived"] == "MONDO:a"
    assert with_proxies["Unmapped"] is None
    assert load_mapping(path, "canonical_id", as_written_only=True, proxy_aliases=True)[
        "Broader"] is None


def test_trait_alias_table_is_read_by_surface(tmp_path):
    path = tmp_path / "aliases.csv"
    path.write_text("surface,term_id,term_label,rule,alias_relation,source,rationale\n"
                    "Height,OBA:1,body height,hand_alias,normalized_equivalent,t,common name\n")
    assert load_trait_aliases(path)["Height"]["alias_relation"] == "normalized_equivalent"
    assert load_trait_aliases(path)["Height"]["term_id"] == "OBA:1"


def test_exposure_mapping_needs_exactly_one_reviewed_accession():
    tiers = [{"il6r": {"HGNC:1"}, "gnas": {"HGNC:2"}, "orf": {"HGNC:3"}}, {}, {}]
    hgnc_uniprot = {"HGNC:1": frozenset({"P08887"}), "HGNC:2": frozenset({"Q1", "Q2"}),
                    "HGNC:3": frozenset()}
    assert map_exposure("IL6R", tiers, hgnc_uniprot)["accession"] == "P08887"
    assert map_exposure("GNAS", tiers, hgnc_uniprot)["state"] == "multiple_uniprot"
    assert map_exposure("ORF", tiers, hgnc_uniprot)["state"] == "no_uniprot"
    assert map_exposure("XYZ", tiers, hgnc_uniprot)["state"] == "no_hgnc"


def test_mapping_tables_round_trip_only_mapped_names(tmp_path):
    rows = [{"name": "IL6R", "state": "mapped", "tier": 0, "hgnc_ids": ["HGNC:1"],
             "accession": "P08887"},
            {"name": "GNAS", "state": "multiple_uniprot", "tier": 0, "hgnc_ids": ["HGNC:2"],
             "accession": None}]
    path = tmp_path / "proteins.csv"
    write_mapping(rows, path, ("hgnc_ids", "accession"))
    assert load_mapping(path, "accession") == {"IL6R": "P08887", "GNAS": None}


def claim(rid, family, protein, outcome, direction, verified=True):
    return RegistryClaim(
        claim_record_id=rid, family_id=family, protein_id=protein, outcome_id=outcome,
        direction=direction, direction_verified=verified, claim_scope="overall",
        context_key="", pqtl_datasets=("not_stated",), outcome_datasets=("not_stated",),
        dataset_attribution="whole_study")


def test_screen_classifies_claims_by_their_own_direction_and_pairs_by_the_shared_one(snapshot):
    claims = [claim("1:000", "F1", "P_IL6R", "MONDO:chd", "lowers"),
              claim("2:000", "F2", "P_IL6R", "MONDO:chd", "raises"),
              claim("1:001", "F1", "P_APOB", "MONDO:mi", "raises"),
              claim("2:001", "F2", "P_APOB", "MONDO:mi", "raises", verified=False),
              claim("1:002", "F1", "P_OTHER", "MONDO:chd", "raises"),
              claim("1:003", "F1", "P_IL6R", "MONDO:stroke", "reported_nonsignificant_or_null")]
    novelty = {"1:000": {"novelty_language": True, "novelty_class": "no_earlier_in_registry"},
               "2:000": {"novelty_language": True, "novelty_class": "earlier_in_registry"},
               "1:001": {"novelty_language": False, "novelty_class": "no_earlier_in_registry"},
               "2:001": {"novelty_language": False, "novelty_class": "tied_or_unknown_order"},
               "1:002": {"novelty_language": True, "novelty_class": "no_earlier_in_registry"},
               "1:003": {"novelty_language": False, "novelty_class": "no_earlier_in_registry"}}
    summary, records, pairs = screen(claims, snapshot, novelty, load_rows())
    assert [r.reference_class for r in records] == [
        "present_same", "present_opposite", "present_same",
        "present_nondirectional_or_ambiguous", "mapping_failed", "no_returned_record"]
    assert pairs == {"P_APOB|MONDO:mi": "present_same",
                     "P_IL6R|MONDO:chd": "present_nondirectional_or_ambiguous",
                     "P_IL6R|MONDO:stroke": "no_returned_record",
                     "P_OTHER|MONDO:chd": "mapping_failed"}
    assert summary["pairs_matched_to_snapshot"] == 3
    assert summary["claim_records_by_novelty_language"]["true"] == {
        "present_same": 1, "present_opposite": 1, "present_nondirectional_or_ambiguous": 0,
        "no_returned_record": 0, "mapping_failed": 1}
    assert summary["claim_records_by_novelty_class"]["earlier_in_registry"]["present_opposite"] == 1
    assert summary["claim_records_by_novelty_class"]["tied_or_unknown_order"][
        "present_nondirectional_or_ambiguous"] == 1
