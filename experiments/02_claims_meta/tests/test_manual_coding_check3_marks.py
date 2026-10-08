import pytest

import manual_coding_check3_marks as m
import manual_coding_check3_table as t
from dataset_relations import load_rows
from manual_coding_table_v2 import EXTENDED_FIELDS, load_extended, registered_rows
from manual_dataset_coding import CODE_FIELDS, NOT_STATED, load_codes
from test_manual_coding_check3_table import ROWS
from test_manual_dataset_coding_reasons import write

DICTIONARY = load_rows()


def tables():
    rows = [dict(r, citations_claim="claims/x.yaml#outcome_1",
                 resolution_note="reread: release 5" if r["resolved_value"] else "",
                 unresolved_reason="" if t.standing(r) not in t.UNRESOLVED else
                 ("dataset_absent_from_dictionary" if "absent" in t.standing(r)
                  else "release_not_identified")) for r in ROWS[:6]]
    rows[1]["side"] = "outcome"
    return rows, [{k: str(v) for k, v in line.items()} for line in t.table(rows, {})]


def marked(lines, *answers):
    return [dict(line, author_confirms=a, author_note=n) for line, (a, n) in zip(lines, answers)]


def test_every_line_must_be_marked_and_nothing_else_may_change():
    _, lines = tables()
    with pytest.raises(m.MarksError):
        m.marks(marked(lines, ("yes", ""), ("", "")), lines)
    with pytest.raises(m.MarksError):
        m.marks(marked(lines, ("yes", ""), ("maybe", "")), lines)
    changed = marked(lines, ("yes", ""), ("yes", ""))
    changed[0]["dictionary_row"] = "FinnGen R12"
    with pytest.raises(m.MarksError):
        m.marks(changed, lines)
    got = m.marks(marked(lines, (" Yes ", ""), ("NO", "the  sentence gives release 6")), lines)
    assert got == {"p2#outcome_1": ("yes", ""),
                   "p1#outcome_1": ("no", "the sentence gives release 6"),
                   "p1#outcome_2": ("no", "the sentence gives release 6")}


def test_yes_keeps_the_code_and_no_makes_the_row_unresolved_with_the_note(tmp_path):
    rows, lines = tables()
    row_marks = m.marks(marked(lines, ("yes", "table 2 names it"), ("no", "wrong release")),
                        lines)
    out = m.apply(rows, row_marks)
    by = {(r["record_id"], r["name_as_written"]): r for r in out}
    confirmed, refused = by[("p2", "FinnGen")], by[("p1", "FinnGen")]
    assert (confirmed["author_confirms"], confirmed["status"]) == ("yes", "coded")
    assert confirmed["resolution_note"] == "reread: release 5 [author: table 2 names it]"
    assert (refused["author_confirms"], refused["status"]) == ("no", "unresolved")
    assert refused["unresolved_reason"] == m.NOT_CONFIRMED
    assert refused["resolution_note"] == "[author did not confirm: wrong release]"
    assert refused["claude_code_value"] == refused["perplexity_value"] == "FinnGen R9"
    left = by[("p5", "FinnGen")]
    assert (left["author_confirms"], left["status"]) == ("yes", "unresolved")
    codes, report = load_extended(write(tmp_path / "e.csv", EXTENDED_FIELDS, out), DICTIONARY)
    assert codes == {("p2", "outcome", "FinnGen"): "FinnGen R5"}
    assert report["coded"] == 1 and report["unresolved"] == 5
    view = write(tmp_path / "v.csv", CODE_FIELDS, registered_rows(out))
    assert load_codes(view, DICTIONARY)[0] == codes


def test_a_mark_for_a_row_that_does_not_stand_coded_or_a_missing_mark_is_refused():
    rows, lines = tables()
    good = m.marks(marked(lines, ("yes", ""), ("yes", "")), lines)
    with pytest.raises(m.MarksError):
        m.apply(rows, {**good, "p5#outcome_1": ("yes", "")})
    with pytest.raises(m.MarksError):
        m.apply(rows, {k: v for k, v in good.items() if k != "p2#outcome_1"})


def test_the_reading_view_holds_every_line_in_order_with_its_sentence_and_reference():
    lines = [{k: str(v) for k, v in line.items()} for line in t.table(ROWS, {})]
    text = m.view(lines)
    heads = [l for l in text.splitlines() if l.startswith("## Line ")]
    assert heads == [f"## Line {x['line']}: {x['dictionary_row']}" for x in lines]
    assert text.count("Pinned sentence:") == len(lines) and text.count("Reference entry:") == 1
    assert "> Kurki 2023." in text and "> We used FinnGen release 9." in text
