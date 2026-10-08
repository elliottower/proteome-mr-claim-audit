import pathlib

import manual_coding_check2_ingest_v2 as superseded
import manual_coding_check2_ingest_v3 as ingest
from manual_dataset_coding import NOT_STATED
from manual_coding_table import ABSENT
from test_manual_coding_check2_ingest import EXPECTED, GOOD, NAMES, S1, TAIL, lines, rows

URL = "Data are at https://www.finngen.fi/en/access_results (release R9) [14]."
EXPORTED = ("Data are at [https://www.finngen.fi/en/access\\_results]"
            "(https://www.finngen.fi/en/access_results) (release R9) [^1_14].")


def packet(quote):
    known = rows()
    known["p1#pqtl_1"]["sentences"] = {URL}
    text = lines(("p1#outcome_1", "FinnGen R9", S1, "release 9"),
                 ("p1#pqtl_1", NOT_STATED, quote, "release_not_identified: x"),
                 ("p2#outcome_1", ABSENT, "Another one.", "unlisted")) + TAIL
    return text, known


def test_an_address_exported_as_a_markdown_link_is_read_as_its_text():
    assert ingest.undo_export(EXPORTED) == URL
    text, known = packet(EXPORTED)
    result = ingest.check_file(text, EXPECTED, known, NAMES)
    assert result["passes"] and result["answers"][1]["quote_match"] == "export_marks_undone"
    assert not superseded.check_file(text, EXPECTED, known, NAMES)["passes"]


def test_a_link_around_other_words_or_a_cut_sentence_still_fails():
    for bad in (EXPORTED.replace("(release R9) ", ""), EXPORTED.replace("Data are at ", "")):
        text, known = packet(bad)
        assert not ingest.check_file(text, EXPECTED, known, NAMES)["passes"]


def test_what_the_second_version_reads_this_version_reads_the_same():
    exported = "pQTLs were taken from deCODE [^1_14] at P &lt; 5e-8."
    for quote in (exported, S1, "none"):
        assert ingest.undo_export(quote) == superseded.undo_export(quote)
    assert (ingest.check_file(GOOD, EXPECTED, rows(), NAMES)
            == superseded.check_file(GOOD, EXPECTED, rows(), NAMES))


def test_the_script_differs_from_the_second_version_in_the_link_only():
    scripts = pathlib.Path(ingest.__file__).resolve().parent
    new = (scripts / "manual_coding_check2_ingest_v3.py").read_text()
    old = (scripts / "manual_coding_check2_ingest_v2.py").read_text()
    code = lambda t: t[t.index('"""\n\nimport argparse'):]
    undone = code(new).replace('LINK = re.compile(r"\\[([^\\]]+)\\]\\((https?://[^)\\s]+)\\)")\n', "")
    undone = undone.replace('LINK.sub(r"\\1", quote)', "quote").replace(
        "footnote marks, markdown links, backslash escapes,\n    HTML entities",
        "footnote marks, backslash escapes, HTML entities")
    assert undone.replace("\n", " ").split() == code(old).replace("\n", " ").split()
