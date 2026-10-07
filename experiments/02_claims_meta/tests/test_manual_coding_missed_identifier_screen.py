import json

import pytest

import manual_coding_missed_identifier_screen as screen
from manual_coding_table import ABSENT, NOT_STATED
from test_coding_gates import DICTIONARY, ELDJ, ENTRY, FERK

BARE = "Outcome data came from FinnGen."
NAMED = "We used FinnGen release 9 summary statistics."
N_ALONE = "We measured 35,559 Icelanders."
N_PLATFORM = "We measured 35,559 Icelanders on SomaScan v4."
CITED = "pQTLs came from the deCODE study.14"


def passage(sentences, references=(), pid="p001"):
    return {"passage_id": pid, "sentences": list(sentences), "references": list(references)}


def given(side, name, candidates, passages):
    return {"side": side, "name_as_written": name, "candidates": candidates,
            "passages": passages}


def reference(doi=None, pmid=None, entry="A paper without author or year."):
    return {"id": "R14", "label": "14", "entry": entry, "doi": doi, "pmid": pmid, "pmcid": None}


def unresolved(reason="release_not_identified", value=NOT_STATED):
    return {"value": value, "unresolved_reason": reason}


def test_a_release_named_in_a_sentence_the_coder_may_not_have_seen_is_a_hit():
    row = given("outcome", "FinnGen", ["FinnGen R9", "FinnGen R5"],
                [passage([BARE]), passage([BARE, "Filler.", NAMED], pid="p002")])
    hits = screen.row_hits(row, DICTIONARY)
    assert hits == [{"passage_id": "p002", "via": "sentence", "sentence": 2,
                     "dictionary_row": "FinnGen R9", "basis": ["aliases:FinnGen release 9"]}]


def test_a_bare_name_a_sample_size_alone_or_a_platform_alone_is_no_hit():
    assert screen.row_hits(given("outcome", "FinnGen", ["FinnGen R9", "FinnGen R5"],
                                 [passage([BARE])]), DICTIONARY) == []
    decode = [FERK["name"], ELDJ["name"]]
    assert screen.row_hits(given("pqtl", "deCODE", decode, [passage(
        [N_ALONE, "Proteins were measured on SomaScan v4 elsewhere."])]), DICTIONARY) == []
    hits = screen.row_hits(given("pqtl", "deCODE", decode, [passage([N_PLATFORM])]), DICTIONARY)
    assert [(h["dictionary_row"], h["basis"]) for h in hits] == [
        (FERK["name"], ["sample_size:35559+SomaScan v4"])]


def test_a_reference_entry_is_a_hit_by_its_identifier_or_by_its_text():
    decode = [FERK["name"], ELDJ["name"]]
    by_doi = screen.row_hits(given("pqtl", "deCODE", decode, [passage(
        [CITED], [reference(doi="10.1038/s41588-021-00978-w")])]), DICTIONARY)
    assert [(h["via"], h["dictionary_row"], h["verified_by"]) for h in by_doi] == [
        ("reference_entry", FERK["name"], "doi")]
    by_pmid = screen.row_hits(given("pqtl", "deCODE", decode, [passage(
        [CITED], [reference(pmid="34857953")])]), DICTIONARY)
    assert [h["verified_by"] for h in by_pmid] == ["pmid"]
    by_text = screen.row_hits(given("pqtl", "deCODE", decode, [passage(
        [CITED], [reference(entry=ENTRY)])]), DICTIONARY)
    assert [(h["dictionary_row"], h["basis"], h["verified_by"]) for h in by_text] == [
        (FERK["name"], ["source_citation:Ferkingstad|2021"], None)]
    assert screen.row_hits(given("pqtl", "deCODE", decode, [passage(
        [CITED], [reference(doi="10.1000/another")])]), DICTIONARY) == []


def test_a_row_with_no_candidate_is_compared_with_every_row_of_its_side():
    hits = screen.row_hits(given("outcome", "FinnGen study", [], [passage([NAMED])]), DICTIONARY)
    assert [h["dictionary_row"] for h in hits] == ["FinnGen R9"]
    assert screen.row_hits(given("pqtl", "FinnGen", [], [passage([NAMED])]), DICTIONARY) == []


def test_only_release_not_identified_rows_are_screened_and_refused_pins_are_marked():
    rows = [given("outcome", "FinnGen", ["FinnGen R9", "FinnGen R5"], [passage([NAMED])])] * 4
    rows.append(given("pqtl", "deCODE", [], [passage([BARE])]))
    paper = {"record_id": "p1", "rows": rows}
    attempt = {"rows": [unresolved(), unresolved("conflicting_identifiers"),
                        unresolved("dataset_absent_from_dictionary", ABSENT),
                        {"value": "FinnGen R5", "unresolved_reason": None}, unresolved()]}
    marked, audit = screen.screen_attempt(attempt, paper, DICTIONARY, {"outcome_2", "pqtl_1"})
    assert marked == [
        {"row": "outcome_1", "side": "outcome", "name_as_written": "FinnGen",
         "reasons": ["missed_identifier_screen"]},
        {"row": "outcome_2", "side": "outcome", "name_as_written": "FinnGen",
         "reasons": ["refused_pin"]},
        {"row": "pqtl_1", "side": "pqtl", "name_as_written": "deCODE",
         "reasons": ["refused_pin"]}]
    assert [a["row"] for a in audit] == ["outcome_1"]
    assert "FinnGen R9" not in json.dumps(marked) and "FinnGen R9" in json.dumps(audit)
    with pytest.raises(screen.ScreenError):
        screen.screen_attempt(attempt, paper, DICTIONARY, {"pqtl_2"})
