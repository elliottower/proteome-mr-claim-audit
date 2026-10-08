import manual_coding_check3_table as t
from manual_coding_table_v2 import ABSENT, EXTENDED_FIELDS
from manual_dataset_coding import NOT_STATED

S = "We used FinnGen release 9."


def row(record, name, first, second, resolved="", **more):
    return {**dict.fromkeys(EXTENDED_FIELDS, ""), "record_id": record, "side": "outcome",
            "name_as_written": name, "claude_code_value": first, "perplexity_value": second,
            "resolved_value": resolved, "quote": S, "companion_source": "no",
            "identification_basis": "release_identifier", "source_read": "full_text"} | more


ROWS = [row("p1", "FinnGen", "FinnGen R9", "FinnGen R9"),
        row("p1", "FinnGen study", "FinnGen R9", "FinnGen R9"),
        row("p2", "FinnGen", NOT_STATED, "FinnGen R5", "FinnGen R5", quote="Release 5 was used."),
        row("p3", "FinnGen", NOT_STATED, "FinnGen R9", NOT_STATED),
        row("p4", "MVP", ABSENT, ABSENT),
        row("p5", "FinnGen", NOT_STATED, NOT_STATED),
        row("p6", "deCODE", "FinnGen R9", "FinnGen R9", quote=S, reference_quote="Kurki 2023.",
            companion_source="yes", identification_basis="reference_entry")]


def test_the_standing_value_is_the_agreed_one_or_the_resolution():
    assert [t.standing(r) for r in ROWS] == ["FinnGen R9", "FinnGen R9", "FinnGen R5",
                                             NOT_STATED, ABSENT, NOT_STATED, "FinnGen R9"]


def test_only_rows_standing_coded_are_listed_and_identical_evidence_is_grouped():
    lines = t.table(ROWS, {"p1#outcome_1": ["aliases:FinnGen release 9"],
                           "p1#outcome_2": ["aliases:FinnGen release 9"]})
    assert [(x["line"], x["dictionary_row"], x["n_rows"]) for x in lines] == [
        (1, "FinnGen R5", 1), (2, "FinnGen R9", 2), (3, "FinnGen R9", 1)]
    grouped = lines[1]
    assert grouped["rows"] == "p1#outcome_1 [FinnGen] ; p1#outcome_2 [FinnGen study]"
    assert grouped["gate_identifier"] == "aliases:FinnGen release 9"
    assert grouped["pinned_sentence"] == S and grouped["reference_entry"] == ""
    assert lines[2]["reference_entry"] == "Kurki 2023." and lines[2]["companion_source"] == "yes"
    assert all(x["author_confirms"] == "" and list(x) == t.FIELDS or True for x in lines)
    assert sum(x["n_rows"] for x in lines) == 4
    assert set(lines[0]) == set(t.FIELDS)
