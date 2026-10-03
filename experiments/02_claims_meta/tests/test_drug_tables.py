import csv

import pytest

from drug_joins import Lookup, join_pair
from drug_tables import build_index, id_prefix, normalize_id, phase_value

TABLES = {
    "target_dictionary": [
        {"tid": 1, "target_type": "SINGLE PROTEIN", "organism": "Homo sapiens"},
        {"tid": 2, "target_type": "PROTEIN COMPLEX", "organism": "Homo sapiens"},
        {"tid": 3, "target_type": "SINGLE PROTEIN", "organism": "Mus musculus"},
        {"tid": 4, "target_type": "NUCLEIC-ACID", "organism": "Homo sapiens"},
        {"tid": 5, "target_type": "SINGLE PROTEIN", "organism": "Homo sapiens"},
    ],
    "component_sequences": [
        {"component_id": 1, "accession": "P1"}, {"component_id": 2, "accession": "P2"},
        {"component_id": 3, "accession": "P3"}, {"component_id": 5, "accession": "P5"},
    ],
    "target_components": [
        {"tid": 1, "component_id": 1, "homologue": 0},
        {"tid": 2, "component_id": 1, "homologue": 0},
        {"tid": 2, "component_id": 2, "homologue": 1},
        {"tid": 3, "component_id": 3, "homologue": 0},
        {"tid": 5, "component_id": 5, "homologue": 0},
    ],
    "molecule_hierarchy": [
        {"molregno": 10, "parent_molregno": 10}, {"molregno": 11, "parent_molregno": 10},
        {"molregno": 20, "parent_molregno": 20}, {"molregno": 30, "parent_molregno": 30},
    ],
    "molecule_dictionary": [
        {"molregno": 10, "chembl_id": "CHEMBL10"}, {"molregno": 11, "chembl_id": "CHEMBL11"},
        {"molregno": 20, "chembl_id": "CHEMBL20"}, {"molregno": 30, "chembl_id": "CHEMBL30"},
        {"molregno": 40, "chembl_id": "CHEMBL40"},
    ],
    "drug_mechanism": [
        {"mec_id": 1, "molregno": 11, "tid": 1, "action_type": "INHIBITOR",
         "direct_interaction": 1, "molecular_mechanism": 1},
        {"mec_id": 2, "molregno": 10, "tid": 1, "action_type": "ANTAGONIST",
         "direct_interaction": 0, "molecular_mechanism": 1},
        {"mec_id": 3, "molregno": 20, "tid": 2, "action_type": "AGONIST",
         "direct_interaction": 0, "molecular_mechanism": 1},
        {"mec_id": 4, "molregno": 30, "tid": 3, "action_type": "INHIBITOR",
         "direct_interaction": 1, "molecular_mechanism": 1},
        {"mec_id": 5, "molregno": 30, "tid": 4, "action_type": "INHIBITOR",
         "direct_interaction": 1, "molecular_mechanism": 1},
        {"mec_id": 6, "molregno": 40, "tid": 5, "action_type": "",
         "direct_interaction": 1, "molecular_mechanism": 1},
        {"mec_id": 7, "molregno": "", "tid": 1, "action_type": "INHIBITOR",
         "direct_interaction": 1, "molecular_mechanism": 1},
        {"mec_id": 8, "molregno": 30, "tid": "", "action_type": "INHIBITOR",
         "direct_interaction": 1, "molecular_mechanism": 1},
    ],
    "drug_indication": [
        {"molregno": 10, "max_phase_for_ind": 2, "efo_id": "EFO:0000001"},
        {"molregno": 11, "max_phase_for_ind": 4, "efo_id": "EFO:0000001"},
        {"molregno": 11, "max_phase_for_ind": "", "efo_id": "EFO:0000002"},
        {"molregno": 10, "max_phase_for_ind": 3, "efo_id": ""},
        {"molregno": 11, "max_phase_for_ind": 0.5, "efo_id": ""},
        {"molregno": 30, "max_phase_for_ind": 4, "efo_id": "MONDO:0000005"},
        {"molregno": "", "max_phase_for_ind": 4, "efo_id": "MONDO:0000006"},
    ],
}
REPORTS = [
    {"id": "r1", "drugs": [{"drugId": "CHEMBL11"}], "diseases": [{"diseaseId": "EFO_0000001"}],
     "trialOverallStatus": "TERMINATED", "trialStopReasonCategories": ["Negative", "Negative"],
     "qualityControls": None, "source": "ClinicalTrials.gov", "type": "INDICATION"},
    {"id": "r2", "drugs": [{"drugId": "CHEMBL30"}], "diseases": [{"diseaseId": "MONDO_0000007"}],
     "trialOverallStatus": "RECRUITING", "trialStopReasonCategories": None,
     "qualityControls": None, "source": "ClinicalTrials.gov", "type": "INDICATION"},
    {"id": "r3", "drugs": [{"drugId": "CHEMBL999"}, {"drugId": "CHEMBL20"},
                           {"drugId": "CHEMBL10"}],
     "diseases": None, "trialOverallStatus": None, "trialStopReasonCategories": [],
     "qualityControls": ["PHASE_IV_NOT_APPROVED"], "source": "EMA", "type": "INDICATION"},
    {"id": "r4", "drugs": None, "diseases": [{"diseaseId": "MONDO_0000008"}],
     "trialOverallStatus": "COMPLETED", "trialStopReasonCategories": None,
     "qualityControls": [], "source": "ClinicalTrials.gov", "type": "INDICATION"},
    {"id": "r5", "drugs": [{"drugId": "CHEMBL10"}, {"drugId": None}],
     "diseases": [{"diseaseId": "EFO_0000001"}, {"diseaseId": "MONDO_0000009"}],
     "trialOverallStatus": None, "trialStopReasonCategories": None,
     "qualityControls": None, "source": "FDA", "type": "SAFETY"},
]
WANTED = {"CHEMBL11", "CHEMBL30", "CHEMBL999", "CHEMBL20", "CHEMBL10"}


@pytest.fixture
def tables_dir(tmp_path):
    for name, table in TABLES.items():
        with (tmp_path / f"{name}.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(table[0]))
            w.writeheader()
            w.writerows(table)
    return tmp_path


@pytest.fixture
def index(tables_dir):
    return build_index(tables_dir, iter(REPORTS), ["EFO_0000001", "Orphanet_12"], WANTED, {})


def test_identifier_normalization():
    assert normalize_id("EFO_0000001") == "EFO:0000001"
    assert normalize_id("EFO:0000001") == "EFO:0000001"
    assert normalize_id("Orphanet_12") == "Orphanet:12"
    assert id_prefix("MONDO_0000007") == "MONDO" and id_prefix("") == "" and id_prefix(None) == ""
    assert phase_value("0.5") == pytest.approx(0.5) and phase_value("-1") == pytest.approx(-1.0)
    assert phase_value(" ") is None


def test_mechanisms_follow_the_primary_and_component_level_rules(index):
    got = sorted((m.mec_id, m.molregno, m.parent_molregno, m.accession, m.level, m.action_type,
                  m.homologue) for m in index.mechanisms)
    assert got == [
        (1, 11, 10, "P1", "single_protein", "INHIBITOR", 0),
        (3, 20, 20, "P1", "component_level_mapping", "AGONIST", 0),
        (3, 20, 20, "P2", "component_level_mapping", "AGONIST", 1),
        (6, 40, 40, "P5", "single_protein", None, 0),
    ]
    assert index.provenance["mechanisms"] == {
        "drug_mechanism_rows": 8, "rows_single_protein": 2, "rows_component_level_mapping": 1,
        "single_protein_rows_failing_direct_or_molecular": 1,
        "rows_not_on_a_used_human_target": 3, "rows_without_molregno": 1}
    assert index.provenance["molecules_without_hierarchy_row"] == 1
    assert index.provenance["index_parent_drugs"] == 3
    assert index.provenance["index_accessions"] == 3


def test_parent_takes_the_highest_phase_among_its_forms_per_indication(index):
    got = {(i.parent_molregno, i.indication_id): i.max_phase for i in index.indications}
    assert got == {(10, "EFO:0000001"): pytest.approx(4.0), (10, "EFO:0000002"): None,
                   (10, None): pytest.approx(3.0)}
    assert index.provenance["indications"] == {
        "drug_indication_rows": 7, "rows_of_index_drugs": 5,
        "rows_of_index_drugs_without_efo_id": 2, "rows_without_molregno": 1}


def test_reports_collapse_drugs_to_parents_and_keep_only_index_drugs(index):
    got = [(t.report_id, t.n_drugs, t.parent_molregnos, t.disease_ids, t.status, t.stop_labels,
            t.quality_controls) for t in index.trials]
    assert got == [("r1", 1, (10,), ("EFO:0000001",), "TERMINATED", ("Negative",), ()),
                   ("r3", 3, (10, 20), (), None, (), ("PHASE_IV_NOT_APPROVED",))]
    assert index.provenance["trials"] == {
        "clinical_report_rows": 5, "report_drug_ids_not_in_molecule_dictionary": 1,
        "reports_not_type_indication": 1, "reports_kept": 2}


def test_kept_reports_are_counted_by_source_and_quality_control_flag(index):
    assert index.provenance["kept_reports_by_flag_and_source"] == {
        "reports_kept": 2, "reports_kept_with_a_quality_control_flag": 1,
        "reports_kept_not_trials": 1, "by_source": {"ClinicalTrials.gov": 1, "EMA": 1},
        "flagged_by_source": {"EMA": 1}, "by_flag": {"PHASE_IV_NOT_APPROVED": 1}}


def test_resource_disease_ids_cover_every_table(index):
    assert index.resource_disease_ids == [
        "EFO:0000001", "EFO:0000002", "MONDO:0000005", "MONDO:0000006", "MONDO:0000007",
        "MONDO:0000008", "Orphanet:12"]


def test_duplicate_report_id_raises(tables_dir):
    with pytest.raises(ValueError, match="r1"):
        build_index(tables_dir, iter([REPORTS[0], REPORTS[0]]), [], WANTED, {})


def test_salt_form_records_reach_the_pair_through_the_parent(index):
    look = Lookup(index, {}, {})
    primary = join_pair(look, "P1", "EFO:0000001", "primary")
    assert primary.highest_status == "approved"
    assert [(d.parent_molregno, d.direction, d.max_phase_matching) for d in primary.drugs] == [
        (10, "decrease", pytest.approx(4.0))]
    assert [e.report_id for e in primary.stopped_trial_events] == ["r1"]
    sens = join_pair(look, "P1", "EFO:0000001", "with_component_level")
    assert [(d.parent_molregno, d.direction) for d in sens.drugs] == [
        (10, "decrease"), (20, "increase")]
    assert join_pair(look, "P2", "EFO:0000001", "primary").drugs == []
