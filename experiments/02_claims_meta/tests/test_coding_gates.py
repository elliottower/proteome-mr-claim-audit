import yaml

import coding_gates as gates
from manual_dataset_coding import NOT_STATED
from manual_dataset_coding_reasons import ABSENT

R9 = {"side": "outcome", "name": "FinnGen R9", "aliases": "FinnGen R9|FinnGen release 9",
      "release": "R9", "sample_size": "377277", "platform": "NA",
      "source_citation": "Kurki MI et al. 2023. FinnGen provides genetic insights",
      "source_identifier": "DOI:10.1038/s41586-022-05473-8; PMID:36653562"}
R5 = {**R9, "name": "FinnGen R5", "aliases": "FinnGen R5|FinnGen release 5", "release": "R5",
      "sample_size": "218792"}
FERK = {"side": "pqtl", "name": "deCODE SomaScan v4 (Ferkingstad 2021)",
        "aliases": "deCODE|deCODE genetics|Ferkingstad 2021", "release":
        "Ferkingstad et al. 2021 (Nat Genet)", "sample_size": "35559",
        "platform": "SomaScan v4 (4,907 aptamers)",
        "source_citation": "Ferkingstad E et al. 2021 Nat Genet (Large-scale integration)",
        "source_identifier": "doi:10.1038/s41588-021-00978-w; PMID:34857953"}
ELDJ = {**FERK, "name": "deCODE SomaScan v4 (Eldjarn 2023 update)",
        "aliases": "deCODE|deCODE genetics|Eldjarn 2023", "release":
        "Eldjarn et al. 2023 (Nature), Iceland 36K", "sample_size": "35892",
        "source_citation": "Eldjarn GH et al. 2023 Nature (Large-scale plasma proteomics)",
        "source_identifier": "doi:10.1038/s41586-023-06563-x"}
DICTIONARY = {(r["side"], r["name"]): r for r in (R9, R5, FERK, ELDJ)}
SENTENCE = "Outcome data came from FinnGen release 9."
CITED = "pQTLs came from the deCODE study.14"
ENTRY = "Ferkingstad E. Large-scale integration of the plasma proteome. Nat Genet 2021."
SOURCE = f"Intro. {SENTENCE} {CITED} We measured 35,559 Icelanders on SomaScan v4."
REFS = f"[ref 14] {ENTRY}\n"


def given(side, name, candidates, passages):
    return {"side": side, "name_as_written": name, "mapping_state": "release_ambiguous",
            "candidates": candidates, "status": "passages" if passages else gates.NO_PASSAGE,
            "passages": passages}


def passage(sentences, references=()):
    return {"passage_id": "p001", "sentences": list(sentences), "references": list(references)}


def claims(tmp_path, **quotes):
    (tmp_path / "claims").mkdir(exist_ok=True)
    for name, held in quotes.items():
        (tmp_path / "claims" / f"{name}.yaml").write_text(yaml.safe_dump(
            {"source": {}, "claims": {k: {"quotes": [{"exact": v}]} for k, v in held.items()}}))
    return tmp_path


def coded(value, **more):
    return {"value": value, "unresolved_reason": None, "identification_basis":
            "release_identifier", "passage_id": "p001", "quote": SENTENCE,
            "citations_claim": "claims/x.yaml#outcome_1", "companion_source": False} | more


def run(code, row, tmp_path):
    return gates.gate_row(code, row, DICTIONARY, SOURCE, REFS, tmp_path)


def test_a_release_named_in_the_pinned_sentence_passes(tmp_path):
    root = claims(tmp_path, x={"outcome_1": SENTENCE})
    row = given("outcome", "FinnGen", ["FinnGen R9", "FinnGen R5"], [passage([SENTENCE])])
    result = run(coded("FinnGen R9"), row, root)
    assert result["passes"] and result["machine_basis"] == ["aliases:FinnGen release 9"]


def test_the_wrong_release_fails_for_want_of_its_identifier(tmp_path):
    root = claims(tmp_path, x={"outcome_1": SENTENCE})
    row = given("outcome", "FinnGen", ["FinnGen R9", "FinnGen R5"], [passage([SENTENCE])])
    result = run(coded("FinnGen R5"), row, root)
    assert result["failures"] == ["no_identifier_of_the_coded_row_in_the_pinned_material"]


def test_a_quote_that_was_not_given_or_not_pinned_fails(tmp_path):
    root = claims(tmp_path, x={"outcome_1": "Another sentence."})
    row = given("outcome", "FinnGen", ["FinnGen R9"], [passage(["Intro."])])
    result = run(coded("FinnGen R9"), row, root)
    assert result["failures"] == ["quote_is_not_a_sentence_of_a_passage_given",
                                  "quote_is_not_the_pinned_quotation"]
    outside = run(coded("FinnGen R9", quote="FinnGen release 9 elsewhere."), row, root)
    assert "quote_not_in_the_source_document" in outside["failures"]


def test_sample_size_alone_fails_and_with_its_platform_passes(tmp_path):
    alone, both = "We measured 35,559 Icelanders.", "We measured 35,559 Icelanders on SomaScan v4."
    root = claims(tmp_path, x={"pqtl_1": alone, "pqtl_2": both})
    row = given("pqtl", "deCODE", [FERK["name"], ELDJ["name"]], [passage([alone, both])])
    source = f"{alone} {both}"
    fail = gates.gate_row(coded(FERK["name"], quote=alone, citations_claim="claims/x.yaml#pqtl_1",
                                identification_basis="exact_n_with_platform_or_year"),
                          row, DICTIONARY, source, "", root)
    assert fail["failures"] == ["no_identifier_of_the_coded_row_in_the_pinned_material"]
    ok = gates.gate_row(coded(FERK["name"], quote=both, citations_claim="claims/x.yaml#pqtl_2",
                              identification_basis="exact_n_with_platform_or_year"),
                        row, DICTIONARY, source, "", root)
    assert ok["passes"] and ok["machine_basis"] == ["sample_size:35559+SomaScan v4"]


def companion(doi):
    reference = {"id": "R14", "label": "14", "entry": ENTRY, "doi": doi, "pmid": None}
    row = given("pqtl", "deCODE", [FERK["name"], ELDJ["name"]], [passage([CITED], [reference])])
    code = coded(FERK["name"], quote=CITED, citations_claim="claims/x.yaml#pqtl_1",
                 identification_basis="reference_entry", companion_source=True,
                 reference_label="14", reference_quote=ENTRY,
                 reference_citations_claim="claims/x.references.yaml#pqtl_1_ref")
    return code, row


def test_a_reference_entry_carries_the_code_when_its_doi_is_the_dictionary_sources(tmp_path):
    root = claims(tmp_path, x={"pqtl_1": CITED}, **{"x.references": {"pqtl_1_ref": ENTRY}})
    result = run(*companion("10.1038/S41588-021-00978-W"), root)
    assert result["passes"] and result["machine_basis"] == ["source_citation:Ferkingstad|2021"]
    other = run(*companion("10.1038/s41586-023-06563-x"), root)
    assert other["failures"] == ["reference_doi_differs_from_the_dictionary_source"]
    none = run(*companion(None), root)
    assert none["passes"] and none["warnings"] == ["no_stable_identifier"]


def test_a_companion_code_without_the_pinned_entry_fails(tmp_path):
    root = claims(tmp_path, x={"pqtl_1": CITED})
    code, row = companion("10.1038/s41588-021-00978-w")
    row["passages"][0]["references"] = []
    result = run(code, row, root)
    assert result["failures"] == ["reference_entry_not_listed_with_the_passage",
                                  "reference_entry_is_not_the_pinned_quotation"]
    code, row = companion("10.1038/s41588-021-00978-w")
    without_flag = run(dict(code, companion_source=False), row, root)
    assert without_flag["failures"] == ["no_identifier_of_the_coded_row_in_the_pinned_material"]


def test_unresolved_rows_need_the_reason_that_fits(tmp_path):
    root = claims(tmp_path, x={"outcome_1": "Data came from the Million Veteran Program."})
    with_passage = given("outcome", "MVP", [], [passage(
        ["Data came from the Million Veteran Program."])])
    blank = {"value": NOT_STATED, "unresolved_reason": "release_not_identified"}
    assert run(blank, with_passage, root)["passes"]
    assert not run(dict(blank, unresolved_reason=None), with_passage, root)["passes"]
    assert not run(dict(blank, unresolved_reason="no_local_passage_found"), with_passage,
                   root)["passes"]
    empty = given("outcome", "MVP", [], [])
    assert run(dict(blank, unresolved_reason="no_local_passage_found"), empty, root)["passes"]
    assert not run(blank, empty, root)["passes"]
    absent = {"value": ABSENT, "unresolved_reason": "dataset_absent_from_dictionary",
              "passage_id": "p001", "quote": "Data came from the Million Veteran Program.",
              "citations_claim": "claims/x.yaml#outcome_1",
              "dataset_named_in_source": "Million Veteran Program"}
    assert gates.gate_row(absent, with_passage, DICTIONARY, absent["quote"], "", root)["passes"]
    unnamed = gates.gate_row(dict(absent, dataset_named_in_source="FinnGen"), with_passage,
                             DICTIONARY, absent["quote"], "", root)
    assert unnamed["failures"] == ["named_dataset_not_in_the_quote"]
    assert run({"value": "FinnGen R99", "unresolved_reason": None}, with_passage,
               root)["failures"] == ["value_not_allowed"]


def test_an_attempt_must_code_every_row_given_once_and_by_its_coder(tmp_path):
    root = claims(tmp_path, x={"outcome_1": SENTENCE})
    (root / "sources").mkdir()
    (root / "sources" / "x.txt").write_text(SOURCE)
    paper = {"record_id": "p1", "coder_id": "coder_1",
             "source": {"document": "sources/x.txt", "references": None},
             "rows": [given("outcome", "FinnGen", ["FinnGen R9", "FinnGen R5"],
                            [passage([SENTENCE])]),
                      given("outcome", "MVP", [], [])]}
    rows = [dict(coded("FinnGen R9"), side="outcome", name_as_written="FinnGen"),
            {"side": "outcome", "name_as_written": "MVP", "value": NOT_STATED,
             "unresolved_reason": "no_local_passage_found"}]
    attempt = {"record_id": "p1", "coder_id": "coder_1", "attempt": 1, "rows": rows}
    assert gates.gate_attempt(attempt, paper, DICTIONARY, root)["passes"]
    short = gates.gate_attempt(dict(attempt, rows=rows[:1]), paper, DICTIONARY, root)
    assert not short["passes"] and short["rows_not_coded_once"] == [["outcome", "MVP"]]
    other = gates.gate_attempt(dict(attempt, coder_id="coder_2"), paper, DICTIONARY, root)
    assert not other["passes"] and other["wrong_coder"]
