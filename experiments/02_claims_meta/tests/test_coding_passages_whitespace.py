import pathlib

import pytest

import coding_passages as sealed
import coding_passages_whitespace as corrected
from test_coding_passages import ROW_R5, ROW_R9, XML, mark, rendered

SCRIPTS = pathlib.Path(sealed.__file__).resolve().parent
EMPTY_CELL = XML.replace(b"<tr><td>Stroke</td><td>MEGASTROKE</td></tr>",
                         b"<tr><td>Stroke</td><td></td></tr>")
PARAGRAPHS = [
    "Sun B. et al. measured 2,923 proteins (Fig. 2). We used deCODE, i.e. the Icelandic data.",
    f"We used deCODE data.14{mark(0)},15{mark(1)} The next sentence [3{mark(2)}]. End.",
    "Analyses used R. Then we stopped. Is it 0.5? Yes!",
]


def test_the_registered_rendering_writes_two_spaces_for_an_empty_cell():
    assert "Source: " in rendered(EMPTY_CELL) and "  " not in rendered(XML)


def test_the_sealed_generator_loses_the_reference_entries_of_a_body_with_an_empty_cell():
    units, references = sealed.full_text_units(EMPTY_CELL, rendered(EMPTY_CELL))
    assert references == {} and all(u["references"] == [] for u in units)


def test_the_corrected_copy_keeps_them_and_every_unit_is_text_of_the_body():
    body = rendered(EMPTY_CELL)
    units, references = corrected.full_text_units(EMPTY_CELL, body)
    assert references["R2"]["doi"] == "10.1038/s41586-022-05473-8"
    assert units[1]["references"] == ["R2"] and units[1]["ends_in_citation"]
    assert all(u["text"] in body for u in units)
    assert "[Table 1. Data sources] Trait: Stroke | Source: " in [u["text"] for u in units]
    found = corrected.passages(units, "FinnGen", [ROW_R9, ROW_R5], references)
    assert [r["id"] for r in found[0]["references"]] == ["R2"]


def test_both_give_the_same_units_and_passages_for_a_body_without_an_empty_cell():
    body = rendered(XML)
    assert corrected.full_text_units(XML, body) == sealed.full_text_units(XML, body)
    units, references = corrected.full_text_units(XML, body)
    assert (corrected.passages(units, "FinnGen", [ROW_R9, ROW_R5], references)
            == sealed.passages(units, "FinnGen", [ROW_R9, ROW_R5], references))
    assert (corrected.abstract_units("We used FinnGen R9. Sun B. et al. did too. End.")
            == sealed.abstract_units("We used FinnGen R9. Sun B. et al. did too. End."))


@pytest.mark.parametrize("paragraph", PARAGRAPHS)
def test_both_split_a_paragraph_into_the_same_sentences(paragraph):
    assert corrected.sentences(paragraph) == sealed.sentences(paragraph)


def test_the_copy_refuses_an_xml_that_does_not_render_to_the_stored_body():
    with pytest.raises(corrected.PassageError):
        corrected.full_text_units(EMPTY_CELL, rendered(EMPTY_CELL) + " ")


def test_the_copy_differs_from_the_sealed_script_in_strip_marks_only():
    text = (SCRIPTS / "coding_passages_whitespace.py").read_text()
    start = text.index("# Corrected copy of coding_passages.py")
    end = text.index("def strip_marks(text: str) -> str:")
    undone = (text[:start] + text[end:]).replace(
        '    return MARKER.sub("", text)\n',
        '    return " ".join(MARKER.sub("", text).split())\n').replace(
        "head = strip_marks(text[start:m.end()]).rstrip()",
        "head = strip_marks(text[start:m.end()])")
    assert undone == (SCRIPTS / "coding_passages.py").read_text()
