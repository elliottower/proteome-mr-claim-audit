import pytest

import manual_coding_check3_second_look as look
import manual_coding_table_v5 as before
import manual_coding_table_v6 as table
from dataset_relations import load_rows
from manual_coding_check3_followup_v2 import FollowupError, add_context, row_ids, row_lines
from manual_dataset_coding import CODE_FIELDS, load_codes
from test_manual_coding_check3_followup import marks_file, tables
from test_manual_dataset_coding_reasons import write

DICTIONARY = load_rows()


def page_of_marked_and_unmarked():
    third, lines, sample = tables(60)
    made = add_context(third, lines, sample[:3])
    rest = [int(v["line"]) for v in lines if int(v["line"]) not in sample]
    return made, lines, sample[:4] + rest[:6], sample, rest


def test_a_second_yes_changes_no_value_and_a_first_yes_confirms_the_row(tmp_path):
    made, lines, page, sample, rest = page_of_marked_and_unmarked()
    items = {k: ("yes", "") for k in sample[:3] + rest[:3]} | {
        k: ("", "") for k in sample[3:4] + rest[3:6]}
    marks = look.read_marks(marks_file(tmp_path / "m.json", items), page)
    flagged = frozenset(sample[:4] + rest[:2] + rest[3:4])
    out, record = look.apply_second_look(made, lines, marks, flagged,
                                         frozenset({sample[0], rest[1]}))
    line_of = row_lines(lines)
    by = {line_of.get(i): r for i, r in row_ids(out)}
    was = {line_of.get(i): r for i, r in row_ids(made)}
    assert all(by[k] == was[k] for k in by if k not in rest[:3])
    assert [by[k]["third_check_context"] for k in rest[:3]] == [
        look.FLAGGED, look.FLAGGED + look.TALKED, look.UNFLAGGED]
    assert all(by[k]["third_check"] == "author_confirmed" for k in rest[:3])
    assert (record["yes_first_mark"], record["yes_second_mark"], record["yes_discussed"]) == (
        3, 3, 2)
    assert (record["flagged_rows"], record["flagged_marked_yes_on_this_page"],
            record["flagged_marked_once_only_elsewhere"], record["flagged_unmarked"]) == (
        7, 5, 1, 1)
    second = {y["table_line"]: y for y in record["lines_marked_yes"] if y["mark"] == "second"}
    assert sorted(second) == sorted(sample[:3])
    assert second[sample[0]]["discussed_with_coordinating_session"]
    assert second[sample[0]]["context_before"] == was[sample[0]]["third_check_context"] != ""
    full = load_codes(write(tmp_path / "a.csv", CODE_FIELDS, table.registered_rows(out)),
                      DICTIONARY)[0]
    only = load_codes(write(tmp_path / "b.csv", CODE_FIELDS,
                            table.registered_rows(out, author_marked_only=True)), DICTIONARY)[0]
    assert (len(full), len(only)) == (60, 23) and all(only[k] == full[k] for k in only)
    with pytest.raises(before.ManualCodingError):
        before.registered_rows(out)


@pytest.mark.parametrize("mark", ["no", "unsure"])
def test_a_second_mark_that_departs_from_the_first_blocks(tmp_path, mark):
    made, lines, page, sample, rest = page_of_marked_and_unmarked()
    items = {k: ("", "") for k in page} | {sample[0]: (mark, "")}
    marks = look.read_marks(marks_file(tmp_path / "m.json", items), page)
    with pytest.raises(FollowupError):
        look.apply_second_look(made, lines, marks, frozenset())


def test_a_no_for_an_unmarked_row_makes_only_that_row_unresolved(tmp_path):
    made, lines, page, sample, rest = page_of_marked_and_unmarked()
    items = {k: ("", "") for k in page} | {rest[0]: ("no", "wrong cohort")}
    marks = look.read_marks(marks_file(tmp_path / "m.json", items), page)
    out, record = look.apply_second_look(made, lines, marks, frozenset({rest[0]}))
    changed = [r for r, w in zip(out, made) if r != w]
    assert len(changed) == 1 and (changed[0]["status"], changed[0]["unresolved_reason"]) == (
        "unresolved", "author_did_not_confirm")
    assert record["flagged_unmarked"] == 0 and record["yes_first_mark"] == 0


@pytest.mark.parametrize("which", ["short", "discussed_blank", "flag_off_page"])
def test_marks_that_do_not_fit_the_page_block(tmp_path, which):
    made, lines, page, sample, rest = page_of_marked_and_unmarked()
    items = {k: ("yes", "") for k in page[:5]} | {k: ("", "") for k in page[5:]}
    if which == "short":
        with pytest.raises(FollowupError):
            look.read_marks(marks_file(tmp_path / "m.json", dict(list(items.items())[:-1])), page)
        return
    marks = look.read_marks(marks_file(tmp_path / "m.json", items), page)
    with pytest.raises(FollowupError):
        look.apply_second_look(
            made, lines, marks,
            frozenset({rest[20]}) if which == "flag_off_page" else frozenset(),
            frozenset({page[-1]}) if which == "discussed_blank" else frozenset())
