import json

import pytest

import manual_coding_check3_followup as f
import manual_coding_check3_sample as s
import manual_coding_check3_table as t
import manual_coding_table_v4 as table
from dataset_relations import load_rows
from manual_dataset_coding import CODE_FIELDS, NOT_STATED, load_codes
from test_manual_coding_check3_table import row
from test_manual_dataset_coding_reasons import write

DICTIONARY = load_rows()
RELEASES = ["FinnGen R3", "FinnGen R4", "FinnGen R5", "FinnGen R6", "FinnGen R7", "FinnGen R8",
            "FinnGen R9", "FinnGen R10", "FinnGen R11", "FinnGen R12"]


def tables(n=30):
    rows = [dict(row(f"p{i:02d}", "FinnGen", RELEASES[i % 10], RELEASES[i % 10],
                     quote=f"Sentence {i} names the release."),
                 citations_claim="claims/x.yaml#outcome_1") for i in range(n)]
    rows.append(row("p99", "FinnGen", NOT_STATED, NOT_STATED,
                    unresolved_reason="release_not_identified"))
    lines = [{k: str(v) for k, v in line.items()} for line in t.table(rows, {})]
    sample = s.draw([int(x["line"]) for x in lines], s.SEED, s.N)
    third = s.apply(rows, lines, {n_: ("yes", "") for n_ in sample},
                    {"audit": "passed", "lines_marked_no": []})
    return third, lines, sample


def test_the_context_marks_the_discussed_rows_of_the_sample_and_no_other_row():
    third, lines, sample = tables()
    made = f.add_context(third, lines, sample[:3])
    counts = {}
    for r in made:
        counts[r["third_check_context"]] = counts.get(r["third_check_context"], 0) + 1
    assert counts == {f.DISCUSSED: 3, f.NOT_DISCUSSED: 17, "": 11}
    assert all(list(r) == table.EXTENDED_FIELDS for r in made)
    assert all({k: v for k, v in a.items()} == {k: b[k] for k in a}
               for a, b in zip(third, made))
    outside = next(int(x["line"]) for x in lines if int(x["line"]) not in sample)
    with pytest.raises(f.FollowupError):
        f.add_context(third, lines, [outside])
    with pytest.raises(f.FollowupError):
        f.add_context(third, lines, [sample[0], sample[0]])


def marks_file(path, items):
    path.write_text(json.dumps({"marks": [
        {"table_line": str(k), "author_mark": m, "author_note": n} for k, (m, n) in items.items()]}))
    return path


def test_voluntary_marks_change_only_their_own_rows(tmp_path):
    third, lines, sample = tables()
    made = f.add_context(third, lines, sample[:3])
    rest = [int(x["line"]) for x in lines if int(x["line"]) not in sample]
    path = marks_file(tmp_path / "m.json", {rest[0]: ("yes", "table 2"), rest[1]: ("NO", "R6"),
                                             rest[2]: ("unsure", "hard to say"), rest[3]: ("", "")})
    marks = f.read_voluntary(path, lines)
    out = f.apply_voluntary(made, lines, marks)
    line_of = f.row_lines(lines)
    by = {line_of.get(i): r for i, r in f.row_ids(out)}
    assert (by[rest[0]]["third_check"], by[rest[0]]["third_check_context"]) == (
        "author_confirmed", f.VOLUNTARY)
    assert (by[rest[1]]["status"], by[rest[1]]["unresolved_reason"]) == (
        "unresolved", "author_did_not_confirm")
    assert by[rest[1]]["resolution_note"] == "[author did not confirm: R6]"
    for k in (rest[2], rest[3], rest[4]):
        assert (by[k]["third_check"], by[k]["third_check_context"], by[k]["status"]) == (
            "machine_gate_only", "", "coded")
    assert sum(r["status"] == "coded" for r in out) == 29
    codes, report = table.load_extended(write(tmp_path / "e.csv", table.EXTENDED_FIELDS, out),
                                        DICTIONARY)
    assert len(codes) == 29 and report["third_check_author_confirmed"] == 21
    view = table.registered_rows(out)
    assert load_codes(write(tmp_path / "v.csv", CODE_FIELDS, view), DICTIONARY)[0] == codes


@pytest.mark.parametrize("which", ["in_sample", "unknown_line", "bad_mark"])
def test_a_voluntary_mark_that_does_not_belong_blocks(tmp_path, which):
    third, lines, sample = tables()
    rest = [int(x["line"]) for x in lines if int(x["line"]) not in sample]
    items = {"in_sample": {sample[0]: ("yes", "")}, "unknown_line": {999: ("yes", "")},
             "bad_mark": {rest[0]: ("maybe", "")}}[which]
    with pytest.raises(f.FollowupError):
        f.read_voluntary(marks_file(tmp_path / "m.json", items), lines)


def test_the_author_marked_only_table_codes_the_marked_rows_and_keeps_every_row(tmp_path):
    third, lines, sample = tables()
    made = f.add_context(third, lines, sample[:3])
    full = load_codes(write(tmp_path / "a.csv", CODE_FIELDS, table.registered_rows(made)),
                      DICTIONARY)[0]
    only = table.registered_rows(made, author_marked_only=True)
    marked = load_codes(write(tmp_path / "b.csv", CODE_FIELDS, only), DICTIONARY)[0]
    assert (len(full), len(marked), len(only)) == (30, 20, 31)
    assert set(marked) <= set(full) and all(marked[k] == full[k] for k in marked)
    assert sum(r["status"] == "unresolved" for r in only) == 11


def test_a_context_without_an_authors_mark_is_refused():
    third, lines, sample = tables()
    made = f.add_context(third, lines, sample[:3])
    wrong = [dict(r) for r in made]
    target = next(r for r in wrong if r["third_check"] == "machine_gate_only")
    target["third_check_context"] = f.DISCUSSED
    with pytest.raises(table.ManualCodingError):
        table.registered_rows(wrong)


def test_a_seeded_voluntary_sample_must_be_exactly_the_draw_and_discussed_rows_are_flagged(
        tmp_path):
    third, lines, sample = tables(60)
    made = f.add_context(third, lines, sample[:3])
    rest = [int(v["line"]) for v in lines if int(v["line"]) not in sample]
    drawn = s.draw(rest, 20261010, 30)
    good = marks_file(tmp_path / "g.json", {k: ("yes", "") for k in drawn})
    marks = f.read_voluntary(good, lines, 20261010, 30)
    assert sorted(marks) == drawn
    with pytest.raises(f.FollowupError):
        f.read_voluntary(marks_file(tmp_path / "b.json", {k: ("yes", "") for k in drawn[:29]}),
                         lines, 20261010, 30)
    out = f.apply_voluntary(made, lines, marks, frozenset(drawn[:2]))
    contexts = {}
    for r in out:
        contexts[r["third_check_context"]] = contexts.get(r["third_check_context"], 0) + 1
    assert contexts[f.VOLUNTARY_DISCUSSED] == 2 and contexts[f.VOLUNTARY] == 28
    assert sum(r["third_check"] == "author_confirmed" for r in out) == 50
    table.registered_rows(out)
    with pytest.raises(f.FollowupError):
        f.apply_voluntary(made, lines, marks, frozenset({sample[0]}))


def test_a_seeded_sample_of_one_basis_is_drawn_from_that_basis_only(tmp_path):
    third, lines, sample = tables(60)
    for i, line in enumerate(lines):
        line["identification_basis"] = "reference_entry" if i % 2 else "release_identifier"
    stratum = [int(v["line"]) for v in lines if int(v["line"]) not in sample
               and v["identification_basis"] == "reference_entry"]
    drawn = s.draw(stratum, 20261011, 10)
    good = marks_file(tmp_path / "g.json", {k: ("yes", "") for k in drawn})
    assert sorted(f.read_voluntary(good, lines, 20261011, 10, "reference_entry")) == drawn
    with pytest.raises(f.FollowupError):
        f.read_voluntary(good, lines, 20261011, 10)
    with pytest.raises(f.FollowupError):
        f.read_voluntary(good, lines, 20261011, 10, "release_identifier")
