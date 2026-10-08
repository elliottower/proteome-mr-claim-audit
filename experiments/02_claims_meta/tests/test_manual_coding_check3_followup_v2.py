import pytest

import manual_coding_check3_followup_v2 as f
import manual_coding_check3_sample as s
import manual_coding_table_v4 as before
import manual_coding_table_v5 as table
from dataset_relations import load_rows
from manual_dataset_coding import CODE_FIELDS, load_codes
from test_manual_coding_check3_followup import marks_file, tables
from test_manual_dataset_coding_reasons import write

DICTIONARY = load_rows()
PAGE, PAGE_DISCUSSED = f.SETS["remaining_rows"]


def after_the_seeded_sample(tmp_path):
    third, lines, sample = tables(60)
    made = f.add_context(third, lines, sample[:3])
    rest = [int(v["line"]) for v in lines if int(v["line"]) not in sample]
    drawn = s.draw(rest, 20261010, 30)
    first = {k: ("yes", "") for k in drawn[:27]} | {k: ("", "") for k in drawn[27:]}
    marks = f.read_voluntary(marks_file(tmp_path / "s.json", first), lines, 20261010, 30)
    out = f.apply_voluntary(made, lines, marks)
    page = [k for k in rest if k not in drawn[:27]]
    return out, lines, page, drawn


def test_marks_on_the_page_of_remaining_rows_take_their_own_contexts_and_change_no_other_row(
        tmp_path):
    made, lines, page, drawn = after_the_seeded_sample(tmp_path)
    items = {k: ("yes" if i < 5 else "", "") for i, k in enumerate(page)}
    marks = f.read_voluntary(marks_file(tmp_path / "p.json", items), lines, page=page)
    out = f.apply_voluntary(made, lines, marks, frozenset(page[:1]), f.SETS["remaining_rows"])
    line_of = f.row_lines(lines)
    by = {line_of.get(i): r for i, r in f.row_ids(out)}
    was = {line_of.get(i): r for i, r in f.row_ids(made)}
    assert by[page[0]]["third_check_context"] == PAGE_DISCUSSED
    assert [by[k]["third_check_context"] for k in page[1:5]] == [PAGE] * 4
    assert all(by[k]["third_check"] == "author_confirmed" for k in page[:5])
    assert all(by[k] == was[k] for k in by if k not in page[:5])
    assert all(by[k]["third_check_context"] == f.VOLUNTARY for k in drawn[:27])
    assert sum(r["third_check"] == "author_confirmed" for r in out) == 20 + 27 + 5
    full = load_codes(write(tmp_path / "a.csv", CODE_FIELDS, table.registered_rows(out)),
                      DICTIONARY)[0]
    only = load_codes(write(tmp_path / "b.csv", CODE_FIELDS,
                            table.registered_rows(out, author_marked_only=True)), DICTIONARY)[0]
    assert (len(full), len(only)) == (60, 52) and all(only[k] == full[k] for k in only)
    with pytest.raises(before.ManualCodingError):
        before.registered_rows(out)


def test_a_marks_file_that_is_not_the_page_blocks(tmp_path):
    made, lines, page, drawn = after_the_seeded_sample(tmp_path)
    short = marks_file(tmp_path / "p.json", {k: ("yes", "") for k in page[:-1]})
    with pytest.raises(f.FollowupError):
        f.read_voluntary(short, lines, page=page)


def test_a_mark_for_a_row_the_author_had_already_marked_blocks(tmp_path):
    made, lines, page, drawn = after_the_seeded_sample(tmp_path)
    marks = f.read_voluntary(marks_file(tmp_path / "p.json", {drawn[0]: ("yes", "")}), lines)
    with pytest.raises(f.FollowupError):
        f.apply_voluntary(made, lines, marks, frozenset(), f.SETS["remaining_rows"])
