import json

import pytest

import manual_coding_gates as sealed
import manual_coding_gates_v2 as gates
from test_coding_gates import (CITED, DICTIONARY, ELDJ, ENTRY, FERK, R5, R9, REFS, SENTENCE,
                               SOURCE, claims)
from test_manual_coding_gates import coded, given, passage

R11 = {**R9, "name": "FinnGen R11", "aliases": "FinnGen R11|FinnGen release 11|finngen_R11|"
       "FinnGen DF11", "release": "R11", "sample_size": "453733"}
EA = {"side": "pqtl", "name": "ARIC European American (Zhang 2022)", "aliases": "ARIC EA",
      "release": "Zhang et al. 2022 (Nat Genet), EA", "ancestry": "European American",
      "sample_size": "7213", "platform": "SomaScan v4",
      "source_citation": "Zhang J et al. 2022 Nat Genet (Plasma proteome analyses)",
      "source_identifier": "doi:10.1038/s41588-022-01051-w; PMID:35501419"}
AA = {**EA, "name": "ARIC African American (Zhang 2022)", "aliases": "ARIC AA",
      "release": "Zhang et al. 2022 (Nat Genet), AA", "ancestry": "African American",
      "sample_size": "1871"}
TABLE = {**DICTIONARY, ("outcome", "FinnGen R11"): R11, ("pqtl", EA["name"]): EA,
         ("pqtl", AA["name"]): AA}

ACCEPTED = [
    "Outcome data came from FinnGen DF 11.", "We used FinnGen (Data Freeze 11) statistics.",
    "Data were from the 11th release of the FinnGen study.",
    "We took the eleventh version of the FinnGen consortium data.",
    "Summary statistics were finngen-r11 files.", "R11 data from the FinnGen study were used.",
    "The FinnGen Study, data freeze 11, provided outcomes.", "FinnGen round 11 was used.",
]
REFUSED = [
    "We used the latest release of FinnGen.", "We used FinnGen release 10.",
    "We used UK Biobank release 11 and FinnGen.", "UK Biobank release 11, FinnGen.",
    "FinnGen, UK Biobank round 11.", "FinnGen had 11 releases.",
    "FinnGen data were used; 11 loci were found in the release.",
    "We used FinnGen release 11 and FinnGen release 12.",
]


@pytest.mark.parametrize("sentence", ACCEPTED)
def test_a_numbered_release_written_in_another_form_is_read(sentence):
    assert gates.release_number_basis(R11, sentence) == ["release_number:finngen 11"]
    assert gates.release_number_basis(R9, sentence) == []


@pytest.mark.parametrize("sentence", REFUSED)
def test_forms_that_do_not_state_the_rows_release_are_refused(sentence):
    assert gates.release_number_basis(R11, sentence) == []


def test_a_row_without_a_numbered_name_has_no_release_number():
    assert gates.numbered_names(FERK) == set()
    assert gates.numbered_names(R11) == {(("finngen",), 11)}
    assert gates.release_number_basis(FERK, "deCODE release 4 was used.") == []


def row_for(sentence, tmp_path):
    root = claims(tmp_path, x={"outcome_1": sentence})
    row = given("outcome", "FinnGen", ["FinnGen R9", "FinnGen R5", "FinnGen R11"],
                [passage([sentence])])
    args = (coded("FinnGen R11", quote=sentence), row, TABLE, {"sources/x.txt": sentence}, "",
            root)
    return sealed.gate_row(*args), gates.gate_row(*args)


def test_the_sealed_gate_fails_a_spaced_release_label_and_this_gate_passes_it(tmp_path):
    old, new = row_for("Outcome data came from FinnGen DF 11.", tmp_path)
    assert old["failures"] == ["no_identifier_of_the_coded_row_in_the_pinned_material"]
    assert new["passes"] and new["machine_basis"] == ["release_number:finngen 11"]


def test_a_refused_form_still_fails(tmp_path):
    old, new = row_for("We used the latest release of FinnGen.", tmp_path)
    assert old["failures"] == new["failures"] == [
        "no_identifier_of_the_coded_row_in_the_pinned_material"]


def companion(sentence, row, tmp_path, doi="10.1038/s41588-022-01051-w"):
    entry = "Zhang J. Plasma proteome analyses in individuals. Nat Genet."
    root = claims(tmp_path, x={"pqtl_1": sentence}, **{"x.references": {"pqtl_1_ref": entry}})
    reference = {"id": "R13", "label": "13", "entry": entry, "doi": doi, "pmid": None,
                 "pmcid": None}
    g = given("pqtl", "ARIC", [EA["name"], AA["name"]], [passage([sentence], [reference])])
    code = coded(row["name"], quote=sentence, citations_claim="claims/x.yaml#pqtl_1",
                 identification_basis="reference_entry", companion_source=True,
                 reference_label="13", reference_quote=entry,
                 reference_citations_claim="claims/x.references.yaml#pqtl_1_ref")
    args = (code, g, TABLE, {"sources/x.txt": sentence}, f"[ref 13] {entry}\n", root)
    return sealed.gate_row(*args), gates.gate_row(*args)


def test_a_shared_source_with_a_separating_attribute_in_the_sentence_passes(tmp_path):
    old, new = companion("pQTLs were from 7,213 ARIC participants.13", EA, tmp_path)
    assert old["failures"] == ["no_identifier_of_the_coded_row_in_the_pinned_material"]
    assert new["passes"] and new["machine_basis"] == ["citation+sample_size:7213"]
    _, by_ancestry = companion("pQTLs were from African American ARIC participants.13", AA,
                               tmp_path)
    assert by_ancestry["machine_basis"] == ["citation+ancestry:African American"]


def test_a_shared_source_without_a_separating_attribute_or_with_the_others_fails(tmp_path):
    _, bare = companion("pQTLs were from the ARIC study on SomaScan v4.13", EA, tmp_path)
    assert bare["failures"] == ["no_identifier_of_the_coded_row_in_the_pinned_material"]
    _, wrong = companion("pQTLs were from 1,871 African American participants.13", EA, tmp_path)
    assert wrong["failures"] == ["no_identifier_of_the_coded_row_in_the_pinned_material"]
    _, unverified = companion("pQTLs were from 7,213 ARIC participants.13", EA, tmp_path,
                              doi="10.1000/another")
    assert "reference_doi_differs_from_the_dictionary_source" in unverified["failures"]
    assert "no_identifier_of_the_coded_row_in_the_pinned_material" in unverified["failures"]


def test_the_attribute_must_be_in_the_sentence_not_only_in_the_reference_entry(tmp_path):
    assert gates.separating_attribute_basis(EA, [EA, AA], "pQTLs came from ARIC.13") == []
    assert gates.separating_attribute_basis(EA, [EA], "7,213 participants") == []


CASES = [
    (coded("FinnGen R9"), given("outcome", "FinnGen", ["FinnGen R9", "FinnGen R5"],
                                [passage([SENTENCE])]), {"outcome_1": SENTENCE}),
    (coded("FinnGen R5"), given("outcome", "FinnGen", ["FinnGen R9", "FinnGen R5"],
                                [passage([SENTENCE])]), {"outcome_1": SENTENCE}),
    (coded(FERK["name"], quote=CITED, citations_claim="claims/x.yaml#pqtl_1",
           identification_basis="reference_entry", companion_source=True, reference_label="14",
           reference_quote=ENTRY,
           reference_citations_claim="claims/x.references.yaml#pqtl_1_ref"),
     given("pqtl", "deCODE", [FERK["name"], ELDJ["name"]],
           [passage([CITED], [{"id": "R14", "label": "14", "entry": ENTRY,
                               "doi": "10.1038/s41588-021-00978-w", "pmid": None,
                               "pmcid": None}])]), {"pqtl_1": CITED}),
    ({"value": "not_stated_in_source", "unresolved_reason": "release_not_identified"},
     given("outcome", "FinnGen", [], [passage([SENTENCE])]), {}),
]


@pytest.mark.parametrize("code,row,pins", CASES)
def test_what_the_sealed_gate_decides_this_gate_decides_too(code, row, pins, tmp_path):
    root = claims(tmp_path, x=pins, **{"x.references": {"pqtl_1_ref": ENTRY}})
    args = (code, row, DICTIONARY, {"sources/x.txt": SOURCE}, REFS, root)
    old, new = sealed.gate_row(*args), gates.gate_row(*args)
    assert (old["passes"], old["failures"], old["warnings"]) == (
        new["passes"], new["failures"], new["warnings"])
    assert old["machine_basis"] == new["machine_basis"]


def test_the_coders_gate_file_holds_no_coded_value():
    result = {"record_id": "p1", "coder_id": "coder_1", "attempt": 2, "passes": False,
              "rows_not_coded_once": [], "rows_not_given": [],
              "rows": [{"side": "outcome", "name_as_written": "FinnGen", "value": "FinnGen R9",
                        "passes": False, "failures": ["x"], "warnings": [],
                        "machine_basis": ["aliases:FinnGen release 9"]},
                       {"side": "pqtl", "name_as_written": "deCODE", "value": FERK["name"],
                        "passes": True, "failures": [], "warnings": [], "machine_basis": []}]}
    shown = gates.for_coder(result)
    assert shown["failing_rows"] == [{"side": "outcome", "name_as_written": "FinnGen",
                                      "failures": ["x"]}]
    assert "FinnGen R9" not in json.dumps(shown) and FERK["name"] not in json.dumps(shown)
    assert R5["name"] not in json.dumps(shown)


def test_a_sentence_of_a_passage_given_for_another_row_of_the_paper_is_accepted_when_named(
        tmp_path):
    sentence = "Outcome data came from FinnGen release 11."
    root = claims(tmp_path, x={"outcome_2": sentence})
    (root / "sources").mkdir()
    (root / "sources" / "x.txt").write_text(f"Intro. {sentence}")
    other = given("outcome", "FinnGen", ["FinnGen R11", "FinnGen R9"], [passage([sentence])])
    mine = given("outcome", "FinnGen biobank", ["FinnGen R11", "FinnGen R9"],
                 [passage(["The FinnGen biobank was used."])])
    paper = {"record_id": "p1", "coder_id": "coder_1",
             "source": {"document": "sources/x.txt", "references": None}, "rows": [other, mine]}
    first = dict(coded("FinnGen R11", quote=sentence, citations_claim="claims/x.yaml#outcome_2"),
                 side="outcome", name_as_written="FinnGen")
    second = dict(first, name_as_written="FinnGen biobank", passage_id="outcome_1:p001")
    attempt = {"record_id": "p1", "coder_id": "coder_1", "attempt": 3, "rows": [first, second]}
    result = gates.gate_attempt(attempt, paper, TABLE, root)
    assert result["passes"]
    assert result["rows"][1]["warnings"] == ["passage_given_for_another_row"]
    unnamed = dict(second, passage_id="p001")
    failed = gates.gate_attempt(dict(attempt, rows=[first, unnamed]), paper, TABLE, root)
    assert failed["rows"][1]["failures"] == ["quote_is_not_a_sentence_of_a_passage_given"]
    missing = dict(second, passage_id="pqtl_9:p001")
    assert not gates.gate_attempt(dict(attempt, rows=[first, missing]), paper, TABLE,
                                  root)["passes"]
