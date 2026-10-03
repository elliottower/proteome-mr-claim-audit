import pytest

from dataset_relations import load_rows
from fulltext_concordance import concordance, family_statuses, match_family

# HGNC-style protein IDs P1..P9 map to one reviewed accession Q1..Q9; no outcome collisions.
MAPS = ({f"P{i}": frozenset({f"Q{i}"}) for i in range(1, 10)}, {})


def rec(pmid, i, protein, direction="raises", scope="overall", context="not_stated",
        verified=True, pqtl=("Sun 2018",), outcome=("FinnGen R10",), enters=True, **extra):
    return {"pmid": pmid, "claim_index": i, "claim_record_id": f"{pmid}:{i:03d}",
            "protein_ids": [protein], "outcome_ids": ["MONDO:1"], "direction": direction,
            "claim_scope": scope, "analysis_context_as_written": context,
            "subgroup_as_written": "not_stated", "dataset_attribution": "whole_study",
            "pqtl_datasets": list(pqtl), "outcome_datasets": list(outcome),
            "direction_verification_state": "agrees" if verified else "direction_unverified",
            "enters_registry": enters, "first_failure": None if enters else "x", **extra}


def test_matched_unmatched_and_context_ambiguous():
    ab = [rec("A", 0, "P1"), rec("A", 1, "P2"),
          rec("A", 2, "P3", scope="dataset_specific", context="in the replication cohort")]
    ft = [rec("A", 0, "P1"),
          rec("A", 1, "P3", scope="dataset_specific", context="in the discovery cohort"),
          rec("A", 2, "P3", scope="dataset_specific", context="in the discovery cohort (n=1)")]
    out = match_family(ab, ft, MAPS)
    assert [r["status"] for r in out["records"]] == ["matched", "unmatched", "context_ambiguous"]
    assert out["records"][0]["direction"] == "agree"


def test_direction_agreement_needs_verified_directions_on_both_sides():
    ab = [rec("A", 0, "P1"), rec("A", 1, "P2")]
    ft = [rec("A", 0, "P1", direction="lowers"), rec("A", 1, "P2", verified=False)]
    out = match_family(ab, ft, MAPS)
    assert [r["direction"] for r in out["records"]] == ["disagree", None]


def test_additional_body_claims_and_full_text_only_datasets():
    ab = [rec("A", 0, "P1")]
    ft = [rec("A", 0, "P1", pqtl=("Sun 2018", "deCODE 2023")), rec("A", 1, "P9"),
          rec("A", 2, "P8", enters=False)]
    out = match_family(ab, ft, MAPS)
    assert out["additional_body_pairs"] == [["Q9", "MONDO:1"]]
    assert out["datasets_only_in_full_text"] == ["deCODE 2023"]


def test_population_and_h2_within_the_extracted_subset():
    ab = [rec("A", 0, "P1", pqtl=("Sun 2018",)), rec("B", 0, "P1", pqtl=("Sun 2018",)),
          rec("C", 0, "P1", pqtl=("Fenland",))]
    ft = [rec("a", 0, "P1", pqtl=("Sun 2018", "deCODE 2023")), rec("b", 0, "P1")]
    family = {"A": "A", "B": "B", "C": "C", "a": "A", "b": "B"}
    status = {"A": "extracted", "B": "extracted", "C": "no_open_access_full_text"}
    out = concordance(ab, ft, family, status, load_rows(), MAPS)
    assert out["population"] == {"extracted": 2, "no_open_access_full_text": 1}
    assert out["record_status"] == {"matched": 2}
    assert out["share_of_abstract_claims_matched_to_extracted_body_records"] == pytest.approx(1)
    assert out["h2_within_extracted_subset"] == {
        "abstract_only": {"known_identical": 1},
        "abstract_and_full_text": {"known_not_identical": 1}}
    # With the full text, family A adds a deCODE release: no longer identical, still on the
    # INTERVAL participants.
    assert out["h2b_within_extracted_subset"] == {
        "abstract_only": {"known_overlapping": 1},
        "abstract_and_full_text": {"known_overlapping": 1}}


def test_family_statuses_split_fetched_families_by_the_full_text_extraction():
    fetch = {"A": {"status": "fetched", "window": "confirmatory", "full_text_record": "1"},
             "B": {"status": "fetched", "window": "confirmatory", "full_text_record": "2"},
             "C": {"status": "version_unmatched", "window": "confirmatory",
                   "full_text_record": None},
             "D": {"status": "no_open_access_full_text", "window": "confirmatory",
                   "full_text_record": None},
             "E": {"status": "fetched", "window": "update", "full_text_record": "5"},
             "F": {"status": "fetched", "window": "confirmatory", "full_text_record": "6"}}
    extraction = {"1": "ok", "2": "extraction_failed", "5": "ok"}
    assert family_statuses(fetch, extraction, "confirmatory") == {
        "A": "extracted", "B": "extraction_failed", "C": "version_unmatched",
        "D": "no_open_access_full_text", "F": "extraction_failed"}
    assert family_statuses(fetch, extraction, "update") == {"E": "extracted"}
