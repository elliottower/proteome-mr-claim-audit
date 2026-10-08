import json

import pytest

import queue_rebuild_comparison_v2 as q


def row(record, side="pqtl", name="deCODE", state="release_ambiguous", candidates="a|b",
        family="F1", claims="2"):
    return {"record_id": record, "side": side, "name_as_written": name, "family_id": family,
            "mapping_state": state, "candidates": candidates, "claim_records": claims}


CODED = [row("p1"), row("p1", "outcome", "FinnGen"), row("p2")]


def passages(rows, text="A sentence."):
    return {(r["record_id"], r["side"], r["name_as_written"]):
            ["passages_found", [{"sentences": [text], "line": 3, "references": []}]]
            for r in rows}


def test_new_rows_are_counted_and_coded_rows_must_be_unchanged():
    rebuilt = [CODED[0], row("p1", "outcome", "FinnGen", claims="5"), CODED[2],
               row("p2", "outcome", "UK Biobank", "unmatched", ""), row("p9")]
    made = q.compare(CODED, rebuilt, None, None)
    assert made["holds"] and (made["coded_rows"], made["rebuilt_rows"], made["new_rows"]) == (
        3, 5, 2)
    assert made["coded_rows_whose_claim_record_count_changed"] == 1
    assert made["new_rows_by_side"] == {"outcome": 1, "pqtl": 1}
    assert made["new_rows_by_state"] == {"unmatched": 1, "release_ambiguous": 1}
    assert (made["new_rows_papers"], made["new_rows_papers_already_in_the_coded_queue"]) == (2, 1)
    assert [r["paper_already_in_the_coded_queue"] for r in made["new_rows_list"]] == [True, False]


@pytest.mark.parametrize("change", [{"candidates": "a|c"}, {"mapping_state": "unmatched"},
                                    {"family_id": "F2"}])
def test_a_changed_field_of_a_coded_row_fails(change):
    made = q.compare(CODED, [CODED[0], {**CODED[1], **change}, CODED[2]], None, None)
    assert not made["holds"] and not made["every_coded_row_unchanged"]
    assert made["coded_rows_changed"] == [["p1", "outcome", "FinnGen"]]


def test_a_missing_coded_row_fails_and_a_row_held_twice_raises():
    made = q.compare(CODED, CODED[:2], None, None)
    assert not made["holds"] and made["coded_rows_missing"] == [["p2", "pqtl", "deCODE"]]
    with pytest.raises(ValueError):
        q.compare(CODED, [*CODED, CODED[0]], None, None)


def test_a_changed_passage_of_a_coded_row_fails_and_passages_are_read_per_row(tmp_path):
    same = q.compare(CODED, [*CODED, row("p9")], passages(CODED),
                     passages([*CODED, row("p9")]))
    assert same["holds"] and same["passages_in_the_hash"] and same["new_rows"] == 1
    other = passages(CODED) | passages([CODED[2]], "Another sentence.")
    made = q.compare(CODED, CODED, passages(CODED), other)
    assert made["coded_rows_changed"] == [["p2", "pqtl", "deCODE"]]
    for folder, rows in (("a", CODED[:2]), ("b", CODED[2:])):
        (tmp_path / folder).mkdir()
    (tmp_path / "a" / "p1.json").write_text(json.dumps({
        "record_id": "p1", "rows": [{"side": r["side"], "name_as_written": r["name_as_written"],
                                     "status": "passages_found", "passages": [{"line": i}]}
                                    for i, r in enumerate(CODED[:2])]}))
    (tmp_path / "a" / "passages_summary.json").write_text(json.dumps({"papers": 1, "rows": 2}))
    read = q.read_passages(tmp_path / "a")
    assert read == {("p1", "pqtl", "deCODE"): ["passages_found", [{"line": 0}]],
                    ("p1", "outcome", "FinnGen"): ["passages_found", [{"line": 1}]]}
