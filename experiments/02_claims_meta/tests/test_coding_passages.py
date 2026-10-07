import hashlib
import json

import pytest

import coding_assignment
import coding_passages as cp

ROW_R9 = {"side": "outcome", "name": "FinnGen R9", "aliases": "FinnGen R9|FinnGen release 9",
          "release": "R9", "sample_size": "377277", "platform": "NA",
          "source_citation": "Kurki MI et al. 2023. FinnGen provides genetic insights",
          "source_identifier": "DOI:10.1038/s41586-022-05473-8; PMID:36653562"}
ROW_R5 = {**ROW_R9, "name": "FinnGen R5", "aliases": "FinnGen R5|FinnGen release 5",
          "release": "R5", "sample_size": "218792"}
ROW_2018 = {**ROW_R9, "name": "MEGASTROKE (Malik 2018)", "aliases": "MEGASTROKE",
            "release": "2018", "sample_size": "67,162 cases; 454,450 controls",
            "source_citation": "Malik R et al. 2018. Multiancestry genome-wide association",
            "source_identifier": "doi:10.1038/s41588-018-0058-3"}
XML = b"""<article><front><abstract><p>Abstract with FinnGen.</p></abstract></front><body>
<sec><title>Methods</title>
<p>Proteins were measured first. Outcome data came from FinnGen.<xref ref-type="bibr" rid="R2">2</xref>
The release had 377,277 participants. Analyses used plink. Nothing here matters. Neither does this.</p>
<p>Unrelated paragraph one. Unrelated paragraph two.</p>
<table-wrap><label>Table 1</label><caption><p>Data sources</p></caption><table>
<thead><tr><th>Trait</th><th>Source</th></tr></thead>
<tbody><tr><td>Stroke</td><td>MEGASTROKE</td></tr><tr><td>Asthma</td><td>FinnGen release 9</td></tr></tbody>
</table></table-wrap></sec></body>
<back><ref-list><ref id="R1"><label>1.</label><mixed-citation>Other A. A paper. 2020.</mixed-citation></ref>
<ref id="R2"><label>2.</label><mixed-citation>Kurki MI. FinnGen provides genetic insights. Nature 2023.
<pub-id pub-id-type="doi">10.1038/s41586-022-05473-8</pub-id></mixed-citation></ref></ref-list></back></article>"""


def rendered(xml):
    root = cp.ET.fromstring(xml)
    cp.drop_abstracts(root)
    lines = []
    cp.render(root.find("body"), lines)
    return "\n".join(lines)


def mark(k):
    return f"{cp.MARK_OPEN}{k}{cp.MARK_CLOSE}"


def test_sentences_rejoin_to_the_paragraph_and_keep_abbreviations_whole():
    text = ("Sun B. et al. measured 2,923 proteins (Fig. 2). We used deCODE, i.e. the Icelandic "
            "data. Is it 0.5? Yes! \"Quoted end.\" Last one")
    parts = cp.sentences(text)
    assert " ".join(parts) == text
    assert parts == ["Sun B. et al. measured 2,923 proteins (Fig. 2).",
                     "We used deCODE, i.e. the Icelandic data.", "Is it 0.5?", "Yes!",
                     "\"Quoted end.\"", "Last one"]


def test_a_superscript_citation_after_the_full_stop_stays_with_its_sentence():
    text = f"We used deCODE data.14{mark(0)},15{mark(1)} The next sentence [3{mark(2)}]. End."
    assert [cp.strip_marks(s) for s in cp.sentences(text)] == [
        "We used deCODE data.14,15", "The next sentence [3].", "End."]


@pytest.mark.parametrize("term,sentence,found", [
    (("release", "R9"), "data from FinnGen (r9)", True),
    (("release", "R9"), "the CR90 assay and R95", False),
    (("sample_size", "377277"), "in 377 277 Finns", True),
    (("sample_size", "377277"), "in 377,277 Finns", True),
    (("sample_size", "377277"), "in 1377277 Finns", False),
    (("source_citation", "Kurki|2023"), "as in Kurki et al. (2023)", True),
    (("source_citation", "Kurki|2023"), "as in Kurki et al. (2021)", False),
    (("aliases", "FinnGen release 9"), "the ﬁnngen  Release 9 data", True),
    (("name_as_written", "UKB-PPP"), "the UKB–PPP study", True),
    (("source_identifier", "10.1038/s41586-022-05473-8"),
     "doi: 10.1038/s41586-022-05473-8.", True),
])
def test_a_term_matches_after_normalization_and_only_at_word_bounds(term, sentence, found):
    assert cp.matches(term, sentence) is found


def test_dictionary_terms_come_from_the_named_fields_only():
    terms = cp.dictionary_terms(ROW_R9)
    assert ("release", "R9") in terms and ("sample_size", "377277") in terms
    assert ("source_citation", "Kurki|2023") in terms
    assert ("source_identifier", "10.1038/s41586-022-05473-8") in terms
    assert ("source_identifier", "36653562") in terms
    assert {f for f, _ in terms} == {"name", "aliases", "release", "source_citation",
                                     "source_identifier", "sample_size"}
    assert "release" not in {f for f, _ in cp.dictionary_terms(ROW_2018)}
    assert {t for f, t in cp.dictionary_terms(ROW_2018) if f == "sample_size"} == {"67162",
                                                                                   "454450"}


def test_name_terms_split_at_parentheses():
    assert cp.name_terms("UK Biobank Pharma Proteomics Project (UKB-PPP)") == [
        (cp.NAME, "UK Biobank Pharma Proteomics Project (UKB-PPP)"),
        (cp.NAME, "UK Biobank Pharma Proteomics Project"), (cp.NAME, "UKB-PPP")]


def test_units_render_to_the_registered_body_and_carry_their_reference_entries():
    units, references = cp.full_text_units(XML, rendered(XML))
    assert [u["text"] for u in units if u["line"] == 1][:2] == [
        "Proteins were measured first.", "Outcome data came from FinnGen.2"]
    cited = units[1]
    assert cited["references"] == ["R2"] and cited["ends_in_citation"]
    assert cited["section"] == "Methods"
    assert references["R2"]["doi"] == "10.1038/s41586-022-05473-8"
    assert references["R2"]["label"] == "2"
    assert [u["kind"] for u in units].count("table") == 2
    body = rendered(XML)
    assert all(u["text"] in body for u in units)
    assert "Abstract with FinnGen" not in body


def test_units_refuse_an_xml_that_does_not_render_to_the_stored_body():
    with pytest.raises(cp.PassageError):
        cp.full_text_units(XML, rendered(XML) + " ")


def test_a_passage_is_the_matching_sentence_with_one_sentence_either_side():
    units, references = cp.full_text_units(XML, rendered(XML))
    found = cp.passages(units, "FinnGen", [ROW_R9, ROW_R5], references)
    prose = [p for p in found if p["kind"] == "prose"]
    assert len(prose) == 1
    assert prose[0]["sentences"] == ["Proteins were measured first.",
                                     "Outcome data came from FinnGen.2",
                                     "The release had 377,277 participants.",
                                     "Analyses used plink."]
    assert (prose[0]["first_sentence"], prose[0]["last_sentence"]) == (0, 3)
    assert prose[0]["section"] == "Methods"
    assert [m["sentence"] for m in prose[0]["matched"]] == [1, 2]
    assert prose[0]["matched"][1]["terms"] == [{"field": "sample_size", "term": "377277"}]
    assert [r["id"] for r in prose[0]["references"]] == ["R2"]
    assert "Nothing here matters." not in prose[0]["sentences"]


def test_the_fallback_adds_one_sentence_only_after_a_name_only_sentence_ending_in_a_citation():
    units, references = cp.full_text_units(XML, rendered(XML))
    alone = cp.passages(units, "FinnGen", [], references)
    prose = [p for p in alone if p["kind"] == "prose"][0]
    assert prose["sentences"][-1] == "Analyses used plink."
    assert (prose["first_sentence"], prose["last_sentence"]) == (0, 3)
    no_citation = [dict(u, ends_in_citation=False) for u in units]
    prose = [p for p in cp.passages(no_citation, "FinnGen", [], references)
             if p["kind"] == "prose"][0]
    assert (prose["first_sentence"], prose["last_sentence"]) == (0, 2)


def test_a_table_hit_is_the_row_line_alone_with_caption_and_headers():
    units, references = cp.full_text_units(XML, rendered(XML))
    tables = [p for p in cp.passages(units, "FinnGen", [ROW_R9], references)
              if p["kind"] == "table"]
    assert [p["sentences"] for p in tables] == [
        ["[Table 1. Data sources] Trait: Asthma | Source: FinnGen release 9"]]


def test_no_match_gives_no_passage_and_windows_never_cross_paragraphs():
    units, references = cp.full_text_units(XML, rendered(XML))
    assert cp.passages(units, "Million Veteran Program", [], references) == []
    found = cp.passages(units, "Unrelated paragraph one", [], references)
    assert found[0]["sentences"] == ["Unrelated paragraph one.", "Unrelated paragraph two."]


def test_overlapping_windows_are_merged_so_no_sentence_is_given_twice():
    units = cp.abstract_units("A one. FinnGen two. B three. FinnGen four. C five. D six. "
                              "E seven. FinnGen eight.")
    found = cp.passages(units, "FinnGen", [], {})
    assert [(p["first_sentence"], p["last_sentence"]) for p in found] == [(0, 4), (6, 7)]
    given = [s for p in found for s in p["sentences"]]
    assert len(given) == len(set(given))


def test_paper_writes_pinned_sources_whose_digest_is_the_files(tmp_path):
    (tmp_path / "sources").mkdir()
    (tmp_path / "claims").mkdir()
    fetched = {"body": rendered(XML), "source_url": "https://example.org/x"}
    rows = [{"side": "outcome", "name_as_written": "FinnGen", "mapping_state":
             "release_ambiguous", "candidates": "FinnGen R9|FinnGen R5|unlisted release of x"},
            {"side": "outcome", "name_as_written": "Million Veteran Program",
             "mapping_state": "unmatched", "candidates": ""}]
    dictionary = {("outcome", "FinnGen R9"): ROW_R9, ("outcome", "FinnGen R5"): ROW_R5}
    made = cp.paper("10.1/a b", rows, dictionary, "", fetched, XML, tmp_path)
    body = tmp_path / made["source"]["document"]
    assert hashlib.sha256(body.read_bytes()).hexdigest() == made["source"]["sha256"]
    assert body.read_text() == fetched["body"]
    refs = (tmp_path / made["source"]["references"]["document"]).read_text()
    assert "[ref 2] Kurki MI. FinnGen provides genetic insights. Nature 2023." in refs
    assert [r["status"] for r in made["rows"]] == ["passages", cp.NO_PASSAGE]
    assert made["rows"][0]["candidates"][-1] == "unlisted release of x"
    entry = made["rows"][0]["passages"][0]["references"][0]["entry"]
    assert entry in refs
    abstract = cp.paper("p2", rows[:1], dictionary, "We used FinnGen R9 data. Done.", None,
                        None, tmp_path)
    assert abstract["source"]["kind"] == "abstract" and abstract["source"]["references"] is None
    assert abstract["rows"][0]["passages"][0]["matched"][0]["terms"][0]["field"] == cp.NAME
    coder = coding_assignment.coder_input(made, "coder_2")
    assert coder["coder_id"] == "coder_2"
    with pytest.raises(coding_assignment.AssignmentError):
        coding_assignment.coder_input({**made, "family_id": "f1"}, "coder_2")
    json.dumps(coder)


def test_assignment_is_fixed_by_the_seed_and_gives_each_paper_one_coder():
    papers = [f"p{i}" for i in range(434)]
    first = coding_assignment.assign(papers, 20261007, 4)
    assert first == coding_assignment.assign(list(reversed(papers)), 20261007, 4)
    assert first != coding_assignment.assign(papers, 1, 4)
    assert set(first) == set(papers)
    sizes = sorted(list(first.values()).count(f"coder_{k}") for k in range(1, 5))
    assert sizes == [108, 108, 109, 109]


def test_a_single_capital_before_a_full_stop_does_not_end_a_sentence():
    assert cp.sentences("Analyses used R. Then we stopped. Sun B. wrote it.") == [
        "Analyses used R. Then we stopped.", "Sun B. wrote it."]


def test_a_body_the_citation_marks_would_change_is_used_unmarked_without_entries():
    xml = XML.replace(
        b"<thead><tr><th>Trait</th><th>Source</th></tr></thead>",
        b"<thead><tr><th>Trait</th><th>Source<xref ref-type=\"bibr\" rid=\"R1\">1</xref></th></tr>"
        b"<tr><th>Trait</th><th>Source<xref ref-type=\"bibr\" rid=\"R1\">1</xref></th></tr></thead>")
    units, references = cp.full_text_units(xml, rendered(xml))
    assert references == {} and all(u["references"] == [] for u in units)
    assert all(u["text"] in rendered(xml) for u in units)
    assert "Source1: FinnGen release 9" in units[-1]["text"]
