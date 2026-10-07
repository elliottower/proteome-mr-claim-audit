import pathlib

import pytest

import manual_coding_passages_v2 as superseded
import manual_coding_passages_v3 as cp
from test_manual_coding_passages_v2 import XLINK

SCRIPTS = pathlib.Path(cp.__file__).resolve().parent
LOOKUP = ('Kurki M. Nature 2023. <ext-link xlink:href="https://doi.org/10.1038/s41586-022-05473-8">'
          'doi</ext-link> <ext-link xlink:href="http://scholar.google.com/scholar_lookup?'
          'doi=10.1038/s41586-022-05473-8&amp;title=FinnGen&amp;publication_year=2023">Scholar'
          "</ext-link>")
SAME_IN_BOTH = [
    'A. <pub-id pub-id-type="doi">10.1038/S41586-022-05473-8</pub-id>',
    'A. <ext-link xlink:href="https://doi.org/10.1038/s41586-022-05473-8">link</ext-link>',
    'A. <ext-link xlink:href="http://dx.doi.org/10.1016%2FS0140-6736%2820%2930183-5">x</ext-link>',
    "A. Nature 2023 (https://doi.org/10.1038/S41586-022-05473-8).",
    "A. Nature 2023; 613: 508-518. PMID: 36653562.",
    'A. Preprint doi:10.1101/2022.03.03.22271360. <pub-id pub-id-type="doi">10.1038/x1</pub-id>',
]


def entry(module, inner):
    xml = (f'<article {XLINK}><body><p>Text.</p></body><back><ref-list><ref id="R1">'
           f"<label>1.</label><mixed-citation>{inner}</mixed-citation></ref></ref-list></back>"
           "</article>").encode()
    return module.reference_entries(module.ET.fromstring(xml))["R1"]


def test_a_look_up_link_made_the_superseded_generator_read_two_dois():
    assert entry(superseded, LOOKUP)["doi_source"] == "conflicting"


def test_a_doi_in_a_look_up_link_ends_at_the_ampersand():
    found = entry(cp, LOOKUP)
    assert (found["doi"], found["doi_source"]) == ("10.1038/s41586-022-05473-8", "link")
    alone = entry(cp, 'A. <ext-link xlink:href="https://x.org/find?id=doi:10.1038/X1&amp;k=2">'
                      "f</ext-link>")
    assert (alone["doi"], alone["doi_source"]) == ("10.1038/x1", "link")
    encoded = entry(cp, 'A. <ext-link xlink:href="https://x.org/find?doi=10.1038%2FX1%26k=2">'
                        "f</ext-link>")
    assert encoded["doi"] == "10.1038/x1"


def test_two_different_dois_are_still_conflicting():
    found = entry(cp, LOOKUP + ' <ext-link xlink:href="https://doi.org/10.1101/2022.03.03">p'
                               "</ext-link>")
    assert (found["doi"], found["doi_source"]) == (None, "conflicting")


@pytest.mark.parametrize("inner", SAME_IN_BOTH)
def test_entries_without_an_ampersand_read_as_in_the_superseded_generator(inner):
    assert entry(cp, inner) == entry(superseded, inner)


def test_the_generator_differs_from_the_superseded_one_in_the_doi_pattern_only():
    new = (SCRIPTS / "manual_coding_passages_v3.py").read_text()
    old = (SCRIPTS / "manual_coding_passages_v2.py").read_text()
    code_new, code_old = (t[t.index('"""\n\nimport argparse'):] for t in (new, old))
    assert code_new.replace('[^\\s\\"<>&]+', '[^\\s\\"<>]+') == code_old
    assert code_new != code_old
