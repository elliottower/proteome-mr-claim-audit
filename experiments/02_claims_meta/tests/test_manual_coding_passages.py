import hashlib

import pytest

import coding_assignment
import coding_passages_whitespace as superseded
import manual_coding_passages as cp
from test_coding_passages import ROW_R5, ROW_R9, XML, rendered
from test_coding_passages_whitespace import EMPTY_CELL, PARAGRAPHS

DICTIONARY = {("outcome", "FinnGen R9"): ROW_R9, ("outcome", "FinnGen R5"): ROW_R5}
ABSTRACT = ("Background here. Outcomes came from the Million Veteran Program and FinnGen. "
            "Twelve proteins were associated. Conclusions follow.")


def queue_row(name, candidates=""):
    return {"side": "outcome", "name_as_written": name, "mapping_state": "unmatched",
            "candidates": candidates}


def folders(tmp_path):
    (tmp_path / "sources").mkdir()
    (tmp_path / "claims").mkdir()
    return tmp_path


def without_pmcid(references):
    return {k: {f: v for f, v in r.items() if f != "pmcid"} for k, r in references.items()}


@pytest.mark.parametrize("xml", [XML, EMPTY_CELL])
def test_units_and_passages_are_those_of_the_corrected_copy(xml):
    body = rendered(xml)
    units, references = cp.full_text_units(xml, body)
    old_units, old_references = superseded.full_text_units(xml, body)
    assert units == old_units and without_pmcid(references) == old_references
    assert references["R2"]["pmcid"] is None
    assert (cp.passages(units, "FinnGen", [ROW_R9, ROW_R5], old_references)
            == superseded.passages(old_units, "FinnGen", [ROW_R9, ROW_R5], old_references))


@pytest.mark.parametrize("paragraph", PARAGRAPHS)
def test_sentences_are_those_of_the_corrected_copy(paragraph):
    assert cp.sentences(paragraph) == superseded.sentences(paragraph)


def test_a_reference_entry_keeps_its_pmc_identifier_and_its_best_identifier_is_named():
    xml = XML.replace(b"<pub-id pub-id-type=\"doi\">10.1038/s41586-022-05473-8</pub-id>",
                      b"<pub-id pub-id-type=\"pmcid\">PMC9849126</pub-id>")
    _, references = cp.full_text_units(xml, rendered(xml))
    assert references["R2"]["pmcid"] == "PMC9849126" and references["R2"]["doi"] is None
    assert [cp.reference_kind(e) for e in (
        {"doi": "10.1/x", "pmid": "1"}, {"doi": None, "pmid": "1", "pmcid": "PMC2"},
        {"doi": None, "pmid": None, "pmcid": "PMC2"}, {"doi": None, "pmid": None})] == [
        "doi", "pmid_only", "pmcid_only", "none"]


def test_a_full_text_row_without_a_passage_takes_the_same_rule_on_the_abstract(tmp_path):
    root = folders(tmp_path)
    fetched = {"body": rendered(XML), "source_url": "https://example.org/x"}
    rows = [queue_row("FinnGen", "FinnGen R9|FinnGen R5"), queue_row("Million Veteran Program"),
            queue_row("China Kadoorie Biobank")]
    made = cp.paper("p1", rows, DICTIONARY, ABSTRACT, fetched, XML, root)
    in_body, fallback, neither = made["rows"]
    assert {p["source_read"] for p in in_body["passages"]} == {"full_text"}
    assert {p["document"] for p in in_body["passages"]} == {"sources/p1.txt"}
    assert {p["claims_file"] for p in in_body["passages"]} == {"claims/p1.yaml"}
    assert fallback["status"] == "passages" and len(fallback["passages"]) == 1
    passage = fallback["passages"][0]
    assert passage["source_read"] == cp.FALLBACK == "abstract_fallback_after_fulltext_no_match"
    assert (passage["document"], passage["claims_file"]) == ("sources/p1.abstract.txt",
                                                             "claims/p1.abstract.yaml")
    assert passage["sentences"] == [
        "Background here.", "Outcomes came from the Million Veteran Program and FinnGen.",
        "Twelve proteins were associated."]
    assert passage == dict(cp.passages(cp.abstract_units(ABSTRACT), "Million Veteran Program",
                                       [], {})[0], source_read=cp.FALLBACK,
                           document="sources/p1.abstract.txt",
                           claims_file="claims/p1.abstract.yaml")
    assert passage["references"] == [] and passage["section"] == "Abstract"
    assert neither["status"] == cp.NO_PASSAGE and neither["passages"] == []
    held = made["source"]["abstract_fallback"]
    text = (root / held["document"]).read_bytes()
    assert text.decode() == ABSTRACT and hashlib.sha256(text).hexdigest() == held["sha256"]
    coding_assignment.coder_input(made, "coder_1")


def test_no_fallback_document_is_written_when_no_row_needs_it(tmp_path):
    root = folders(tmp_path)
    fetched = {"body": rendered(XML), "source_url": "https://example.org/x"}
    made = cp.paper("p1", [queue_row("FinnGen", "FinnGen R9")], DICTIONARY, ABSTRACT, fetched,
                    XML, root)
    assert made["source"]["abstract_fallback"] is None
    assert not (root / "sources" / "p1.abstract.txt").exists()
    alone = cp.paper("p2", [queue_row("FinnGen"), queue_row("China Kadoorie Biobank")],
                     DICTIONARY, ABSTRACT, None, None, root)
    assert alone["source"]["abstract_fallback"] is None
    assert [r["status"] for r in alone["rows"]] == ["passages", cp.NO_PASSAGE]
    assert {p["source_read"] for p in alone["rows"][0]["passages"]} == {"abstract"}
