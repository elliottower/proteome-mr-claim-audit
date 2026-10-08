import openpyxl
import pytest

import manual_coding_check3_sample as s
import manual_coding_check3_table as t
import manual_coding_table_v3 as table
from dataset_relations import load_rows
from manual_dataset_coding import CODE_FIELDS, NOT_STATED, load_codes
from test_manual_coding_check3_table import row
from test_manual_dataset_coding_reasons import write

DICTIONARY = load_rows()


def test_the_draw_is_the_seeded_sample_of_file_positions_sorted():
    lines = list(range(1, 197))
    drawn = s.draw(lines, 20261008, 20)
    assert drawn == [8, 12, 23, 32, 40, 55, 56, 62, 72, 75, 80, 103, 105, 113, 120, 146, 173,
                     182, 184, 192]
    rest = [n for n in lines if n not in drawn]
    second = s.draw(rest, 20261009, 20)
    assert len(second) == 20 and not set(second) & set(drawn) and second == sorted(second)


def test_the_upper_bound_is_the_exact_one_sided_binomial_bound():
    assert s.upper_bound(0, 20) == pytest.approx(1 - 0.05 ** (1 / 20))
    assert s.upper_bound(0, 20) == pytest.approx(0.1391, abs=1e-4)
    assert s.upper_bound(1, 40) == pytest.approx(0.1127, abs=1e-3)
    assert s.upper_bound(20, 20) == 1.0
    assert s.upper_bound(0, 40) < s.upper_bound(0, 20) < s.upper_bound(2, 20)


def sheet(path, marks):
    book = openpyxl.Workbook()
    ws = book.active
    ws.append(["#", "", "", "", "", "Confirm? yes / no", "Note (optional)", "", "", "",
               "Table line"])
    for i, (line, (mark, note)) in enumerate(marks.items(), 1):
        ws.append([i, "", "", "", "", mark, note, "", "", "", str(line)])
    book.save(path)
    return path


def test_marks_are_read_by_table_line_and_a_blank_or_a_foreign_line_blocks(tmp_path):
    good = {3: (" Yes", ""), 5: ("NO", "release  6 in the sentence")}
    assert s.read_marks(sheet(tmp_path / "a.xlsx", good), [3, 5]) == {
        3: ("yes", ""), 5: ("no", "release 6 in the sentence")}
    with pytest.raises(s.SampleError):
        s.read_marks(sheet(tmp_path / "b.xlsx", {3: ("yes", ""), 5: (None, "")}), [3, 5])
    with pytest.raises(s.SampleError):
        s.read_marks(sheet(tmp_path / "c.xlsx", {3: ("yes", ""), 6: ("yes", "")}), [3, 5])
    with pytest.raises(s.SampleError):
        s.read_marks(sheet(tmp_path / "d.xlsx", {3: ("yes", "")}), [3, 5])


def marks(no=()):
    return {k: ("no" if k in no else "yes", "") for k in range(1, 5)}


def test_the_prespecified_consequences_of_the_marks():
    assert s.decide(marks(), None, False)["audit"] == "passed"
    with pytest.raises(s.SampleError):
        s.decide(marks({1}), None, False)
    second = {k: ("yes", "") for k in range(5, 9)}
    closed = s.decide(marks({1}), second, False)
    assert (closed["audit"], closed["marked_no"], closed["lines_read"]) == ("passed", 1, 8)
    with pytest.raises(s.SampleError):
        s.decide(marks({1, 2}), None, False)
    with pytest.raises(s.SampleError):
        s.decide(marks({1}), {**second, 5: ("no", "")}, False)
    with pytest.raises(s.SampleError):
        s.decide(marks(), second, False)
    assert s.decide(marks({1, 2}), None, True)["audit"] == "failed"


def tables():
    rows = [row("p1", "FinnGen", "FinnGen R9", "FinnGen R9", quote="Release 9 was used."),
            row("p2", "FinnGen", "FinnGen R5", "FinnGen R5", quote="Release 5 was used."),
            row("p3", "FinnGen", "FinnGen R8", "FinnGen R8", quote="N was 342,499 in 2022.",
                identification_basis="exact_n_with_platform_or_year"),
            row("p4", "FinnGen", "FinnGen R7", "FinnGen R7", quote="N was 309,154 in 2021.",
                identification_basis="exact_n_with_platform_or_year"),
            row("p5", "FinnGen", NOT_STATED, NOT_STATED,
                unresolved_reason="release_not_identified")]
    rows = [dict(r, citations_claim="claims/x.yaml#outcome_1") for r in rows]
    return rows, [{k: str(v) for k, v in line.items()} for line in t.table(rows, {})]


def by_record(rows):
    return {r["record_id"]: r for r in rows}


def test_only_marked_rows_are_recorded_as_the_authors_and_the_rest_as_machine_only(tmp_path):
    rows, lines = tables()
    line_of = {x["rows"].split("#")[0]: int(x["line"]) for x in lines}
    m = {line_of["p1"]: ("yes", "table 1"), line_of["p3"]: ("yes", "")}
    decision = {"audit": "passed", "lines_marked_no": []}
    out = by_record(s.apply(rows, lines, m, decision))
    assert (out["p1"]["third_check"], out["p1"]["author_confirms"]) == ("author_confirmed", "yes")
    assert out["p1"]["resolution_note"] == "[author: table 1]"
    assert (out["p2"]["third_check"], out["p2"]["author_confirms"], out["p2"]["status"]) == (
        "machine_gate_only", "not_read", "coded")
    assert (out["p5"]["third_check"], out["p5"]["author_confirms"], out["p5"]["status"]) == (
        "", "not_read", "unresolved")
    made = list(out.values())
    assert all(list(r) == table.EXTENDED_FIELDS for r in made)
    codes, report = table.load_extended(write(tmp_path / "e.csv", table.EXTENDED_FIELDS, made),
                                        DICTIONARY)
    assert set(codes.values()) == {"FinnGen R9", "FinnGen R5", "FinnGen R8", "FinnGen R7"}
    assert report["third_check_machine_gate_only"] == 2
    assert report["third_check_author_confirmed"] == 2
    view = table.registered_rows(made)
    assert [v["author_confirms"] for v in view] == ["yes", "yes", "yes", "yes", "not_read"]
    assert load_codes(write(tmp_path / "v.csv", CODE_FIELDS, view), DICTIONARY)[0] == codes


def test_a_row_marked_no_is_unresolved_and_a_failed_audit_unresolves_its_basis_class(tmp_path):
    rows, lines = tables()
    line_of = {x["rows"].split("#")[0]: int(x["line"]) for x in lines}
    m = {line_of["p1"]: ("yes", ""), line_of["p3"]: ("no", "N is post-exclusion")}
    one = by_record(s.apply(rows, lines, m, {"audit": "passed",
                                             "lines_marked_no": [line_of["p3"]]}))
    assert (one["p3"]["third_check"], one["p3"]["status"], one["p3"]["unresolved_reason"]) == (
        "author_did_not_confirm", "unresolved", "author_did_not_confirm")
    assert one["p3"]["resolution_note"] == "[author did not confirm: N is post-exclusion]"
    assert one["p3"]["claude_code_value"] == "FinnGen R8" == one["p3"]["perplexity_value"]
    assert one["p4"]["third_check"] == "machine_gate_only"
    failed = by_record(s.apply(rows, lines, m, {"audit": "failed",
                                                "lines_marked_no": [line_of["p3"]]}))
    assert (failed["p4"]["status"], failed["p4"]["unresolved_reason"]) == (
        "unresolved", "audit_failed_basis_class")
    assert failed["p2"]["third_check"] == "machine_gate_only"
    assert failed["p1"]["third_check"] == "author_confirmed"
    codes, _ = table.load_extended(write(tmp_path / "e.csv", table.EXTENDED_FIELDS,
                                         list(failed.values())), DICTIONARY)
    assert set(codes.values()) == {"FinnGen R9", "FinnGen R5"}


def test_the_registered_table_refuses_a_yes_the_author_did_not_give():
    rows, lines = tables()
    out = s.apply(rows, lines, {}, {"audit": "passed", "lines_marked_no": []})
    out[0]["author_confirms"] = "yes"
    with pytest.raises(table.ManualCodingError):
        table.registered_rows(out)
