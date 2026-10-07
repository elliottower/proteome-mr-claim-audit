import pytest

import manual_coding_passages as superseded
import manual_coding_passages_v2 as cp
from test_coding_passages import ROW_R5, ROW_R9, XML, rendered
from test_coding_passages_whitespace import EMPTY_CELL, PARAGRAPHS
from test_manual_coding_passages import ABSTRACT, DICTIONARY, folders, queue_row

IDENTIFIERS = ("doi", "doi_source", "pmid", "pmid_source", "pmcid")
XLINK = 'xmlns:xlink="http://www.w3.org/1999/xlink"'


def entry(inner):
    xml = (f'<article {XLINK}><body><p>Text.</p></body><back><ref-list><ref id="R1">'
           f"<label>1.</label><mixed-citation>{inner}</mixed-citation></ref></ref-list></back>"
           "</article>").encode()
    return cp.reference_entries(cp.ET.fromstring(xml))["R1"]


def text_only(references):
    return {k: {f: v for f, v in r.items() if f in ("label", "entry")}
            for k, r in references.items()}


@pytest.mark.parametrize("inner,doi,source", [
    ('Kurki M. Nature 2023. <pub-id pub-id-type="doi">10.1038/S41586-022-05473-8</pub-id>',
     "10.1038/s41586-022-05473-8", "pub_id"),
    ('Kurki M. Nature 2023. <ext-link ext-link-type="doi" '
     'xlink:href="https://doi.org/10.1038/s41586-022-05473-8">link</ext-link>',
     "10.1038/s41586-022-05473-8", "link"),
    ('Kurki M. Nature 2023. <ext-link ext-link-type="doi">10.1038/s41586-022-05473-8</ext-link>',
     "10.1038/s41586-022-05473-8", "link"),
    ('Kurki M. Nature 2023. <ext-link ext-link-type="uri" '
     'xlink:href="http://dx.doi.org/10.1016%2FS0140-6736%2820%2930183-5">x</ext-link>',
     "10.1016/s0140-6736(20)30183-5", "link"),
    ("Kurki M. Nature 2023. doi:10.1038/s41586-022-05473-8.", "10.1038/s41586-022-05473-8",
     "text"),
    ("Kurki M. Nature 2023 (https://doi.org/10.1038/S41586-022-05473-8).",
     "10.1038/s41586-022-05473-8", "text"),
    ("Kurki M. Nature 2023 [DOI: 10.1038/s41586-022-05473-8];", "10.1038/s41586-022-05473-8",
     "text"),
    ("Kurki M. Nature 2023; 613: 508-518.", None, None),
])
def test_a_doi_is_read_from_the_tag_then_a_link_then_the_text_and_normalized(inner, doi, source):
    found = entry(inner)
    assert (found["doi"], found["doi_source"]) == (doi, source)


def test_the_same_doi_in_several_sources_is_one_doi_from_the_first_source():
    found = entry('Kurki M. https://doi.org/10.1038/S41586-022-05473-8. '
                  '<ext-link xlink:href="https://doi.org/10.1038/s41586-022-05473-8">x</ext-link>'
                  '<pub-id pub-id-type="doi">10.1038/s41586-022-05473-8</pub-id>')
    assert (found["doi"], found["doi_source"]) == ("10.1038/s41586-022-05473-8", "pub_id")
    assert cp.reference_kind(found) == "doi_from_pub_id"


def test_different_dois_in_one_entry_leave_it_conflicting_with_no_identifier():
    found = entry('Kurki M. Preprint doi:10.1101/2022.03.03.22271360. '
                  '<pub-id pub-id-type="doi">10.1038/s41586-022-05473-8</pub-id>'
                  '<pub-id pub-id-type="pmid">36653562</pub-id>'
                  '<pub-id pub-id-type="pmcid">PMC9849126</pub-id>')
    assert {f: found[f] for f in IDENTIFIERS} == {
        "doi": None, "doi_source": "conflicting", "pmid": None, "pmid_source": None,
        "pmcid": None}
    assert cp.reference_kind(found) == "conflicting"
    two_printed = entry("A. 10.1101/2022.03.03.22271360 and 10.1038/s41586-022-05473-8")
    assert two_printed["doi_source"] == "conflicting"


@pytest.mark.parametrize("inner,pmid,source", [
    ('A. <pub-id pub-id-type="pmid">36653562</pub-id>', "36653562", "pub_id"),
    ('A. <ext-link xlink:href="https://pubmed.ncbi.nlm.nih.gov/36653562/">PubMed</ext-link>',
     "36653562", "link"),
    ('A. <ext-link xlink:href="http://www.ncbi.nlm.nih.gov/pubmed/36653562">x</ext-link>',
     "36653562", "link"),
    ("A. Nature 2023. PMID: 36653562.", "36653562", "text"),
    ("A. Nature 2023. pmid 36653562", "36653562", "text"),
    ("A. Nature 2023; 613: 36653562.", None, None),
])
def test_a_pmid_is_read_from_the_tag_then_a_pubmed_link_then_the_text(inner, pmid, source):
    found = entry(inner)
    assert (found["pmid"], found["pmid_source"]) == (pmid, source)
    assert cp.reference_kind(found) == ("pmid_only" if pmid else "none")


def test_a_conflicting_pmid_leaves_the_doi_and_nothing_else():
    inner = ('A. PMID: 11111111. <pub-id pub-id-type="pmid">36653562</pub-id>'
             '<pub-id pub-id-type="pmcid">PMC9849126</pub-id>')
    found = entry(inner)
    assert {f: found[f] for f in IDENTIFIERS} == {
        "doi": None, "doi_source": None, "pmid": None, "pmid_source": "conflicting",
        "pmcid": None}
    assert cp.reference_kind(found) == "conflicting"
    with_doi = entry(inner + '<pub-id pub-id-type="doi">10.1038/x1</pub-id>')
    assert (with_doi["doi"], with_doi["pmid"]) == ("10.1038/x1", None)
    assert cp.reference_kind(with_doi) == "doi_from_pub_id"


def test_a_pmc_identifier_is_kept_from_its_tag():
    found = entry('A. <pub-id pub-id-type="pmcid">PMC9849126</pub-id>')
    assert found["pmcid"] == "PMC9849126" and cp.reference_kind(found) == "pmcid_only"


@pytest.mark.parametrize("xml", [XML, EMPTY_CELL])
def test_units_passages_and_entry_texts_are_those_of_the_superseded_generator(xml):
    body = rendered(xml)
    units, references = cp.full_text_units(xml, body)
    old_units, old_references = superseded.full_text_units(xml, body)
    assert units == old_units and text_only(references) == text_only(old_references)
    assert references["R2"]["doi"] == old_references["R2"]["doi"]
    assert references["R2"]["doi_source"] == "pub_id"
    assert (cp.passages(units, "FinnGen", [ROW_R9, ROW_R5], old_references)
            == superseded.passages(old_units, "FinnGen", [ROW_R9, ROW_R5], old_references))


@pytest.mark.parametrize("paragraph", PARAGRAPHS)
def test_sentences_are_those_of_the_superseded_generator(paragraph):
    assert cp.sentences(paragraph) == superseded.sentences(paragraph)


def test_the_abstract_fallback_is_that_of_the_superseded_generator(tmp_path):
    fetched = {"body": rendered(XML), "source_url": "https://example.org/x"}
    rows = [queue_row("FinnGen", "FinnGen R9|FinnGen R5"), queue_row("Million Veteran Program"),
            queue_row("China Kadoorie Biobank")]
    (tmp_path / "new").mkdir()
    (tmp_path / "old").mkdir()
    made = cp.paper("p1", rows, DICTIONARY, ABSTRACT, fetched, XML, folders(tmp_path / "new"))
    old = superseded.paper("p1", rows, DICTIONARY, ABSTRACT, fetched, XML,
                           folders(tmp_path / "old"))
    assert made["source"] == old["source"]
    assert [r["status"] for r in made["rows"]] == ["passages", "passages", cp.NO_PASSAGE]
    for new_row, old_row in zip(made["rows"], old["rows"]):
        strip = [[{k: v for k, v in p.items() if k != "references"} for p in r["passages"]]
                 for r in (new_row, old_row)]
        assert strip[0] == strip[1]
    assert made["rows"][1]["passages"][0]["source_read"] == cp.FALLBACK


def test_the_generator_differs_from_the_superseded_one_in_the_reference_identifiers_only():
    scripts = cp.pathlib.Path(cp.__file__).resolve().parent
    new = (scripts / "manual_coding_passages_v2.py").read_text()
    old = (scripts / "manual_coding_passages.py").read_text()

    def body(text, first, last):
        return text[text.index(first):text.index(last)]

    for first, last in (("def normalize(", "def reference_entries("),
                        ("def table_line(", "def reference_kind("),
                        ("def main(", "if __name__")):
        start = "def dois(" if last == "def reference_entries(" else last
        assert body(new, first, start) == body(old, first, last)
