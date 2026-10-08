import json

import pytest

import manual_coding_reread as reread
from manual_coding_table_v2 import ABSENT, EXTENDED_FIELDS
from manual_dataset_coding import NOT_STATED
from test_coding_gates import DICTIONARY, SENTENCE, claims
from test_manual_coding_gates import given, passage

BARE = "Outcome data came from FinnGen."


def first(value, category=None, quote=None):
    return {"value": value, "category": category, "quote": quote}


def source_rows():
    return [{"row": "p1#outcome_1", "class": "disagree_first_unresolved_second_coded",
             "first_check": first(NOT_STATED, "release_not_identified"),
             "second_check": first("FinnGen R9", None, SENTENCE)},
            {"row": "p1#outcome_2", "class": "both_unresolved_different_value",
             "first_check": first(ABSENT, "dataset_absent_from_dictionary", BARE),
             "second_check": first(NOT_STATED, "release_not_identified")}]


def paper():
    return {"record_id": "p1", "coder_id": "coder_1",
            "source": {"document": "sources/x.txt", "references": None},
            "rows": [given("outcome", "FinnGen", ["FinnGen R9", "FinnGen R5"],
                           [passage([SENTENCE, BARE])]),
                     given("outcome", "FinnGen biobank", [], [passage([BARE])])]}


def folders(tmp_path, papers=1):
    coders, ingested = tmp_path / "coders", tmp_path / "ingested"
    (coders / "coder_1" / "input").mkdir(parents=True)
    ingested.mkdir()
    listed = {}
    for i in range(1, papers + 1):
        made = dict(paper(), record_id=f"p{i}")
        (coders / "coder_1" / "input" / f"p{i}.json").write_text(json.dumps(made))
        listed[f"p{i}.json"] = [dict(r, row=r["row"].replace("p1#", f"p{i}#"))
                                for r in source_rows()]
    (ingested / "disagreements_for_reread.json").write_text(json.dumps({"coder_1": listed}))
    return coders, ingested


def resolution(*rows):
    return {"record_id": "p1", "coder_id": "coder_1", "rows": list(rows)}


CODED = {"row": "outcome_1", "resolved_value": "FinnGen R9", "unresolved_reason": None,
         "resolution_note": "the sentence writes release 9", "source_read": "full_text",
         "identification_basis": "release_identifier", "passage_id": "p001", "quote": SENTENCE,
         "citations_claim": "claims/x.yaml#outcome_1_r", "companion_source": False}
LEFT = {"row": "outcome_2", "resolved_value": NOT_STATED,
        "unresolved_reason": "release_not_identified", "resolution_note": "a name alone"}


def test_the_order_of_the_two_answers_is_drawn_by_seed_and_kept_out_of_the_rereaders_file(
        tmp_path):
    coders, ingested = folders(tmp_path, papers=30)
    summary = reread.write(ingested, coders, tmp_path / "out", 7)
    assert summary["coders"]["coder_1"] == {"papers": 30, "shares": 3, "rows": 60}
    manifest = json.loads((tmp_path / "out" / "draw_manifest.json").read_text())
    shown_first = manifest["shown_as_answer_1"]
    assert shown_first == reread.draw(list(shown_first), 7) != reread.draw(list(shown_first), 8)
    assert set(shown_first.values()) == {"first_check", "second_check"}
    made = json.loads((tmp_path / "out" / "coder_1" / "input" /
                       "p1.disagreement.json").read_text())
    text = json.dumps(made)
    assert "first_check" not in text and "second_check" not in text and "class" not in text
    row = made["rows_in_disagreement"][0]
    values = {row["answer_1"]["value"], row["answer_2"]["value"]}
    assert values == {NOT_STATED, "FinnGen R9"} and row["name_as_written"] == "FinnGen"
    first_value = "FinnGen R9" if shown_first["p1#outcome_1"] == "second_check" else NOT_STATED
    assert row["answer_1"]["value"] == first_value
    shares = [json.loads((tmp_path / "out" / f"coder_1_share_{k:02d}.json").read_text())
              for k in (1, 2, 3)]
    assert [len(s) for s in shares] == [12, 12, 6]
    assert shares[0][0]["write_as"] == "coder_1/resolutions/p1.resolution.json"
    with pytest.raises(reread.RereadError):
        reread.write(ingested, coders, tmp_path / "out", 7)


def test_a_resolution_that_passes_the_gate_stands_and_one_that_fails_is_unresolved(tmp_path):
    root = claims(tmp_path, x={"outcome_1_r": SENTENCE, "outcome_2_r": BARE})
    (root / "sources").mkdir()
    (root / "sources" / "x.txt").write_text(f"{SENTENCE} {BARE}")
    good = reread.resolve_paper(source_rows(), resolution(CODED, LEFT), paper(), DICTIONARY,
                                root)
    assert [r["value_that_stands"] for r in good] == ["FinnGen R9", NOT_STATED]
    assert good[1]["unresolved_reason"] == "release_not_identified"
    assert good[0]["first_check"]["value"] == NOT_STATED
    assert good[0]["second_check"]["value"] == "FinnGen R9"
    wrong = dict(CODED, resolved_value="FinnGen R5")
    failed = reread.resolve_paper(source_rows(), resolution(wrong, LEFT), paper(), DICTIONARY,
                                  root)[0]
    assert failed["value_that_stands"] == NOT_STATED
    assert failed["unresolved_reason"] == "release_not_identified"
    assert "failed the gate" in failed["resolution_note"] and "FinnGen R5" in (
        failed["resolution_note"])
    assert failed["reread"]["resolved_value"] == "FinnGen R5"


def test_a_resolution_must_cover_exactly_the_rows_in_disagreement_and_carry_a_note(tmp_path):
    root = claims(tmp_path, x={"outcome_1_r": SENTENCE})
    (root / "sources").mkdir()
    (root / "sources" / "x.txt").write_text(f"{SENTENCE} {BARE}")
    for bad in (resolution(CODED), resolution(LEFT, CODED),
                resolution(CODED, LEFT, dict(LEFT, row="outcome_3")),
                resolution(CODED, dict(LEFT, resolution_note=" "))):
        with pytest.raises(reread.RereadError):
            reread.resolve_paper(source_rows(), bad, paper(), DICTIONARY, root)


def table_row(side_name, first_value, second_value, **more):
    return {**dict.fromkeys(EXTENDED_FIELDS, ""), "record_id": "p1", "side": "outcome",
            "name_as_written": side_name, "claude_code_value": first_value,
            "perplexity_value": second_value, "companion_source": "no"} | more


def test_apply_fills_the_resolution_and_leaves_both_original_answers(tmp_path):
    root = claims(tmp_path, x={"outcome_1_r": SENTENCE})
    (root / "sources").mkdir()
    (root / "sources" / "x.txt").write_text(f"{SENTENCE} {BARE}")
    done = reread.resolve_paper(source_rows(), resolution(CODED, LEFT), paper(), DICTIONARY,
                                root)
    table = [table_row("FinnGen", NOT_STATED, "FinnGen R9",
                       unresolved_reason="release_not_identified"),
             table_row("FinnGen biobank", ABSENT, NOT_STATED, quote=BARE,
                       citations_claim="claims/x.yaml#outcome_2",
                       unresolved_reason="dataset_absent_from_dictionary")]
    out = reread.apply(table, done)
    coded, left = out
    assert (coded["claude_code_value"], coded["perplexity_value"]) == (NOT_STATED, "FinnGen R9")
    assert coded["resolved_value"] == "FinnGen R9" and coded["quote"] == SENTENCE
    assert coded["citations_claim"] == "claims/x.yaml#outcome_1_r"
    assert coded["resolution_note"].endswith("[first-check pin: none]")
    assert coded["unresolved_reason"] == "" and coded["source_read"] == "full_text"
    assert (left["claude_code_value"], left["perplexity_value"]) == (ABSENT, NOT_STATED)
    assert left["resolved_value"] == NOT_STATED and left["quote"] == BARE
    assert left["unresolved_reason"] == "release_not_identified"
    assert left["resolution_note"].endswith("[first-check pin: claims/x.yaml#outcome_2]")
    assert all(list(r) == EXTENDED_FIELDS for r in out)
    with pytest.raises(reread.RereadError):
        reread.apply(table, done[:1])
    with pytest.raises(reread.RereadError):
        reread.apply(table[:1], done)


def test_read_refuses_while_a_resolution_file_is_missing(tmp_path):
    coders, ingested = folders(tmp_path)
    reread.write(ingested, coders, tmp_path / "out", 7)
    with pytest.raises(reread.RereadError):
        reread.read(tmp_path / "out", coders, tmp_path)
