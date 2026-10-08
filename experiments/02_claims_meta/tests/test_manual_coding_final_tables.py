import json

import pytest

import manual_coding_check3_table_v2 as lines_of
import manual_coding_final_tables as ft
import manual_coding_table_v7 as table
from dataset_relations import load_rows
from manual_dataset_coding import CODE_FIELDS, NOT_STATED, check_cover, load_codes
from test_manual_coding_check3_followup import marks_file
from test_manual_coding_check3_table import row as narrow
from test_manual_dataset_coding_reasons import write

DICTIONARY = load_rows()


def wide(record, name, first, second, **more):
    made = {**dict.fromkeys(table.EXTENDED_FIELDS, ""), **narrow(record, name, first, second)}
    return made | {"citations_claim": "claims/x.yaml#outcome_1"} | more


def new_table():
    return [wide("n1", "FinnGen", "FinnGen R9", "FinnGen R9", quote="Release 9 was used."),
            wide("n1", "MVP", table.ABSENT, table.ABSENT,
                 unresolved_reason="dataset_absent_from_dictionary"),
            wide("n2", "FinnGen", "FinnGen R5", "FinnGen R5", quote="Release 5 was used."),
            wide("n3", "FinnGen", NOT_STATED, NOT_STATED,
                 unresolved_reason="release_not_identified")]


def author_lines(rows):
    return [{k: str(v) for k, v in x.items()} for x in lines_of.table(rows, {}, 197)]


@pytest.mark.parametrize("mark,third,status,context", [
    ("yes", "author_confirmed", "coded", ft.CONTEXT),
    ("", "machine_gate_only", "coded", ""),
    ("unsure", "machine_gate_only", "coded", ""),
    ("no", "author_did_not_confirm", "unresolved", ft.CONTEXT)])
def test_a_mark_on_a_new_coded_row_is_read_by_the_rule_of_the_authors_marks(
        tmp_path, mark, third, status, context):
    rows = new_table()
    lines = author_lines(rows)
    assert [x["line"] for x in lines] == ["197", "198"]
    marks = ft.read_marks(marks_file(tmp_path / "m.json", {197: (mark, "a note"), 198: ("yes", "")}),
                          lines)
    made = ft.new_rows(rows, lines, marks)
    by = {(r["record_id"], r["name_as_written"]): r for r in made}
    first = by[("n2", "FinnGen")]          # line 197: FinnGen R5 sorts before FinnGen R9
    assert (first["third_check"], first["status"], first["third_check_context"]) == (
        third, status, context)
    assert (first["author_confirms"] == "yes") == (mark == "yes")
    assert by[("n1", "FinnGen")]["third_check"] == "author_confirmed"
    for unresolved in (by[("n1", "MVP")], by[("n3", "FinnGen")]):
        assert (unresolved["status"], unresolved["third_check"], unresolved["author_confirms"],
                unresolved["third_check_context"]) == ("unresolved", "", "not_read", "")
    table.registered_rows(made)


def test_marks_that_are_not_the_tables_lines_and_an_unresolved_disagreement_stop(tmp_path):
    rows = new_table()
    lines = author_lines(rows)
    with pytest.raises(ft.FinalTableError):
        ft.read_marks(marks_file(tmp_path / "a.json", {197: ("yes", "")}), lines)
    with pytest.raises(ft.FinalTableError):
        ft.read_marks(marks_file(tmp_path / "b.json", {197: ("maybe", ""), 198: ("yes", "")}),
                      lines)
    differ = [*rows, wide("n4", "FinnGen", "FinnGen R9", NOT_STATED)]
    with pytest.raises(ft.FinalTableError):
        ft.new_rows(differ, lines, {197: ("yes", ""), 198: ("yes", "")})


def decided(tmp_path, rows):
    lines = author_lines(rows)
    return ft.new_rows(rows, lines, {int(x["line"]): ("yes", "") for x in lines})


def queue_of(rows):
    return [{"record_id": r["record_id"], "side": r["side"],
             "name_as_written": r["name_as_written"]} for r in rows]


def test_the_merged_table_follows_the_queue_and_carries_the_first_run_unchanged(tmp_path):
    first = decided(tmp_path, [wide("p1", "FinnGen", "FinnGen R9", "FinnGen R9"),
                               wide("p2", "MVP", NOT_STATED, NOT_STATED,
                                    unresolved_reason="release_not_identified")])
    new = decided(tmp_path, new_table())
    queue = queue_of([new[0], first[1], new[3], first[0]])
    made, counts = ft.merge(first, new, queue)
    assert [(r["record_id"], r["name_as_written"]) for r in made] == [
        ("n1", "FinnGen"), ("p2", "MVP"), ("n3", "FinnGen"), ("p1", "FinnGen")]
    assert made[1] is first[1] and counts["first_run_rows_carried_unchanged"]
    assert (counts["rows"], counts["new_rows_in_the_queue"],
            counts["new_rows_outside_the_queue"]) == (4, 2, 2)
    assert counts["by_status"] == {"coded": 2, "unresolved": 2}
    assert counts["unresolved_by_reason"] == {"release_not_identified": 2}
    for wrong in (queue_of([first[0], new[0]]),                      # a first-run row left out
                  queue_of([*first, new[0], wide("p9", "x", "", "")]),  # a row coded nowhere
                  queue_of([*first, new[0], new[0]])):                 # a row twice
        with pytest.raises(ft.FinalTableError):
            ft.merge(first, new, wrong)
    with pytest.raises(ft.FinalTableError):
        ft.merge(first, [*new, first[0]], queue_of(first))


def test_the_three_registered_tables_code_all_the_marked_and_no_row_and_cover_the_queue(
        tmp_path):
    rows = new_table()
    lines = author_lines(rows)
    made = ft.new_rows(rows, lines, {197: ("yes", ""), 198: ("", "")})
    queue = queue_of(made)
    codes = {}
    for name, kw in (("a", {}), ("b", {"author_marked_only": True}), ("c", {"none": True})):
        path = write(tmp_path / f"{name}.csv", CODE_FIELDS, table.registered_rows(made, **kw))
        check_cover(path, queue)
        codes[name] = load_codes(path, DICTIONARY)[0]
    assert (len(codes["a"]), len(codes["b"]), len(codes["c"])) == (2, 1, 0)
    assert codes["b"].items() <= codes["a"].items()
    assert list(codes["b"]) == [("n2", "outcome", "FinnGen")]
    wrong = [dict(r) for r in made]
    wrong[0]["third_check_context"] = "another context"
    with pytest.raises(table.ManualCodingError):
        table.registered_rows(wrong)
