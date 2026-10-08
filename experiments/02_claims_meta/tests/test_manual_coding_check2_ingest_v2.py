import json

import pytest

import manual_coding_check2_ingest_v2 as ingest
from manual_coding_table import ABSENT, EXTENDED_FIELDS
from manual_dataset_coding import NOT_STATED

S1 = "We used FinnGen release 9 summary statistics."
S2 = "pQTLs came from deCODE."
TABLE = "[Table 1. Sources] Trait: Asthma | Source: FinnGen release 9"
NAMES = {("outcome", "FinnGen R9"), ("outcome", "FinnGen R5"),
         ("pqtl", "deCODE SomaScan v4 (Ferkingstad 2021)")}
EXPECTED = ["p1#outcome_1", "p1#pqtl_1", "p2#outcome_1"]
FOOT = "\n[^1_1]: batch_07.md\n\n[^1_2]: 01_PROMPT_check2_v4_closed_packet-3.md\n"
TAIL = "\nModel: Perplexity\nexternal sources used: none\n" + FOOT


def rows():
    return {"p1#outcome_1": {"record": "p1", "side": "outcome", "sentences": {S1, TABLE}},
            "p1#pqtl_1": {"record": "p1", "side": "pqtl", "sentences": {S2}},
            "p2#outcome_1": {"record": "p2", "side": "outcome", "sentences": {"Another one."}}}


def lines(*triples):
    return "\n\n".join(f"{r} | {a} | {q} | none | {why} [^1_1][^1_2]" for r, a, q, why in triples)


GOOD = lines(("p1\\#outcome_1", "FinnGen R9", S1, "release 9 is written"),
             ("p1\\#pqtl_1", NOT_STATED, "none", "release_not_identified: a name alone"),
             ("p2\\#outcome_1", ABSENT, "Another one.", "an unlisted accession")) + TAIL


def test_a_clean_file_passes_and_its_fields_are_read():
    result = ingest.check_file(GOOD, EXPECTED, rows(), NAMES)
    assert result["passes"] and result["failures"] == [] and result["warnings"] == []
    assert [a["row"] for a in result["answers"]] == EXPECTED
    first, second, third = result["answers"]
    assert (first["answer"], first["quote"], first["reference"]) == ("FinnGen R9", S1, "none")
    assert first["reasoning"] == "release 9 is written"
    assert second["unresolved_category"] == "release_not_identified"
    assert third["unresolved_category"] == "dataset_absent_from_dictionary"
    assert result["model_line"] == "Perplexity"


def test_a_table_line_holding_bars_is_read_as_the_quotation():
    text = lines(("p1#outcome_1", "FinnGen R9", TABLE, "the table | names release 9"),
                 ("p1#pqtl_1", NOT_STATED, "none", "conflicting_identifiers: two releases"),
                 ("p2#outcome_1", NOT_STATED, "none", "release_not_identified: nothing")) + TAIL
    result = ingest.check_file(text, EXPECTED, rows(), NAMES)
    assert result["passes"] and result["answers"][0]["quote"] == TABLE
    assert result["answers"][0]["reasoning"] == "the table | names release 9"
    assert result["answers"][1]["unresolved_category"] == "conflicting_identifiers"


@pytest.mark.parametrize("change,check", [
    (lambda t: t.replace("FinnGen R9 |", "FinnGen R10 |"), "answer_allowed"),
    (lambda t: t.replace(f"{NOT_STATED} | none", "deCODE SomaScan v4 (Ferkingstad 2021) | none"),
     "quote_supplied"),
    (lambda t: t.replace(S1, "We used FinnGen release 9."), "quote_supplied"),
    (lambda t: t.replace("external sources used: none", "external sources used: PubMed"),
     "closing_line_external_sources_none"),
    (lambda t: t + "\n[^1_3]: https://pubmed.ncbi.nlm.nih.gov/1/\n",
     "footnotes_name_attached_files_only"),
    (lambda t: t.replace("p2\\#outcome_1", "p3\\#outcome_1"),
     "rows_present_once_and_in_order"),
    (lambda t: t + "\n" + t.split("\n\n")[0], "rows_present_once_and_in_order"),
])
def test_each_defect_fails_its_check(change, check):
    result = ingest.check_file(change(GOOD), EXPECTED, rows(), NAMES)
    assert not result["passes"] and check in [f["check"] for f in result["failures"]]


def test_rows_out_of_order_or_a_dictionary_row_of_the_other_side_fail():
    blocks = GOOD.split("\n\n")
    swapped = "\n\n".join([blocks[1], blocks[0], *blocks[2:]])
    assert not ingest.check_file(swapped, EXPECTED, rows(), NAMES)["passes"]
    other_side = GOOD.replace("FinnGen R9 |", "deCODE SomaScan v4 (Ferkingstad 2021) |")
    assert not ingest.check_file(other_side, EXPECTED, rows(), NAMES)["passes"]


def test_a_sentence_of_another_row_of_the_paper_is_accepted_and_recorded():
    text = GOOD.replace(f"{NOT_STATED} | none | none | release_not_identified: a name alone",
                        f"{NOT_STATED} | {S1} | none | release_not_identified: a name alone")
    result = ingest.check_file(text, EXPECTED, rows(), NAMES)
    assert result["passes"]
    assert result["answers"][1]["quote_from_another_row"] == "p1#outcome_1"
    foreign = GOOD.replace("Another one.", S1)
    assert not ingest.check_file(foreign, EXPECTED, rows(), NAMES)["passes"]


def test_a_missing_category_is_a_warning_and_not_a_failure():
    text = GOOD.replace("release_not_identified: a name alone", "a name alone")
    result = ingest.check_file(text, EXPECTED, rows(), NAMES)
    assert result["passes"] and result["warnings"] == [
        {"warning": "unresolved_category_not_stated", "row": "p1#pqtl_1"}]


@pytest.mark.parametrize("first,second,expected", [
    ({"value": "FinnGen R9", "coded": True, "category": None},
     {"answer": "FinnGen R9", "unresolved_category": None}, "agree_same_dictionary_row"),
    ({"value": "FinnGen R9", "coded": True, "category": None},
     {"answer": "FinnGen R5", "unresolved_category": None},
     "disagree_both_coded_different_rows"),
    ({"value": "FinnGen R9", "coded": True, "category": None},
     {"answer": NOT_STATED, "unresolved_category": "release_not_identified"},
     "disagree_first_coded_second_unresolved"),
    ({"value": NOT_STATED, "coded": False, "category": "release_not_identified"},
     {"answer": "FinnGen R9", "unresolved_category": None},
     "disagree_first_unresolved_second_coded"),
    ({"value": NOT_STATED, "coded": False, "category": "release_not_identified"},
     {"answer": NOT_STATED, "unresolved_category": "release_not_identified"},
     "agree_unresolved_same_category"),
    ({"value": NOT_STATED, "coded": False, "category": "conflicting_identifiers"},
     {"answer": NOT_STATED, "unresolved_category": "release_not_identified"},
     "agree_unresolved_other_category"),
    ({"value": ABSENT, "coded": False, "category": "dataset_absent_from_dictionary"},
     {"answer": NOT_STATED, "unresolved_category": "release_not_identified"},
     "both_unresolved_different_value"),
    ({"value": ABSENT, "coded": False, "category": "dataset_absent_from_dictionary"},
     {"answer": ABSENT, "unresolved_category": "dataset_absent_from_dictionary"},
     "agree_unresolved_same_category"),
])
def test_rows_are_classed_against_the_first_check(first, second, expected):
    assert ingest.compare(first, second) == expected


def folders(tmp_path):
    coders, batches, answers = tmp_path / "coders", tmp_path / "batches", tmp_path / "answers"
    (coders / "coder_1" / "input").mkdir(parents=True)
    (coders / "coder_1" / "codes").mkdir()
    batches.mkdir()
    answers.mkdir()
    paper = {"record_id": "p1", "rows": [
        {"side": "outcome", "name_as_written": "FinnGen", "passages": [{"sentences": [S1]}]},
        {"side": "pqtl", "name_as_written": "deCODE", "passages": [{"sentences": [S2]}]}]}
    (coders / "coder_1" / "input" / "p1.json").write_text(json.dumps(paper))
    for n, value in ((1, "FinnGen R5"), (2, "FinnGen R9")):
        (coders / "coder_1" / "codes" / f"p1.attempt{n}.json").write_text(json.dumps(
            {"record_id": "p1", "coder_id": "coder_1", "attempt": n, "rows": [
                {"side": "outcome", "value": value, "unresolved_reason": None},
                {"side": "pqtl", "value": NOT_STATED,
                 "unresolved_reason": "release_not_identified"}]}))
    (batches / "batch_07.md").write_text("# b\n\n### Row p1#outcome_1\n\n### Row p1#pqtl_1\n")
    (batches / "batch_08.md").write_text("# b\n\n### Row p9#outcome_1\n")
    return coders, batches, answers


def test_ingest_counts_the_one_passing_file_and_lists_the_rest(tmp_path):
    coders, batches, answers = folders(tmp_path)
    good = lines(("p1\\#outcome_1", "FinnGen R9", S1, "release 9"),
                 ("p1\\#pqtl_1", ABSENT, S2, "an unlisted dataset")) + TAIL
    (answers / "batch_07_run1.md").write_text(good.replace("external sources used: none", "x"))
    (answers / "batch_07_run2.md").write_text(good)
    summary = ingest.ingest(answers, batches, coders, tmp_path / "out")
    assert summary["batches"]["07"]["passing"] == ["batch_07_run2.md"]
    assert summary["rerun"] == [] and summary["unanswered"] == ["08"]
    assert summary["comparison_counts"] == {"agree_same_dictionary_row": 1,
                                            "both_unresolved_different_value": 1}
    assert (summary["rows_with_a_counted_answer"], summary["rows_in_all_batches"]) == (2, 3)
    with pytest.raises(ingest.IngestError):
        ingest.ingest(answers, batches, coders, tmp_path / "out")
    table = [{**dict.fromkeys(EXTENDED_FIELDS, ""), "record_id": "p1", "side": s,
              "name_as_written": n} for s, n in (("outcome", "FinnGen"), ("pqtl", "deCODE"))]
    merged = ingest.merge(tmp_path / "out", table)
    assert [r["perplexity_value"] for r in merged] == ["FinnGen R9", ABSENT]
    with pytest.raises(ingest.IngestError):
        ingest.merge(tmp_path / "out", table + [dict(table[0], record_id="p9")])


def test_a_batch_with_only_failing_files_goes_to_rerun(tmp_path):
    coders, batches, answers = folders(tmp_path)
    (answers / "batch_07_run1.md").write_text("p1\\#outcome_1 | FinnGen R9 | none | none | x")
    summary = ingest.ingest(answers, batches, coders, tmp_path / "out")
    assert summary["rerun"] == ["07"] and summary["rows_with_a_counted_answer"] == 0


CITED = "pQTLs were taken from deCODE [14] at P < 5e-8 (see https://example.org/a_b)."


def test_the_exports_marks_are_undone_before_a_quotation_is_compared():
    exported = ("pQTLs were taken from deCODE [^1_14] at P &lt; 5e-8 "
                "(see <https://example.org/a\\_b>).")
    assert ingest.undo_export(exported) == CITED
    known = rows()
    known["p1#pqtl_1"]["sentences"] = {CITED}
    text = lines(("p1\\#outcome_1", "FinnGen R9", S1, "release 9"),
                 ("p1\\#pqtl_1", NOT_STATED, exported, "release_not_identified: a name"),
                 ("p2\\#outcome_1", ABSENT, "Another one.", "unlisted")) + TAIL
    result = ingest.check_file(text, EXPECTED, known, NAMES)
    assert result["passes"]
    first, second, _ = result["answers"]
    assert (first["quote_match"], second["quote_match"]) == ("as_written",
                                                              "export_marks_undone")
    assert second["sentence_supplied"] == CITED and second["quote"] == exported
    import manual_coding_check2_ingest as superseded
    assert not superseded.check_file(text, EXPECTED, known, NAMES)["passes"]


def test_a_fragment_or_an_altered_sentence_still_fails_after_the_marks_are_undone():
    known = rows()
    known["p1#pqtl_1"]["sentences"] = {CITED}
    for bad in ("pQTLs were taken from deCODE [^1_14]", CITED.replace("deCODE", "DECODE"),
                CITED.replace("[14]", "[15]")):
        text = lines(("p1#outcome_1", "FinnGen R9", S1, "release 9"),
                     ("p1#pqtl_1", NOT_STATED, bad, "release_not_identified: x"),
                     ("p2#outcome_1", ABSENT, "Another one.", "unlisted")) + TAIL
        assert not ingest.check_file(text, EXPECTED, known, NAMES)["passes"]


def test_files_the_first_version_passes_are_read_the_same():
    import manual_coding_check2_ingest as superseded
    new = ingest.check_file(GOOD, EXPECTED, rows(), NAMES)
    old = superseded.check_file(GOOD, EXPECTED, rows(), NAMES)
    assert new["passes"] and old["passes"]
    for a, b in zip(new["answers"], old["answers"], strict=True):
        assert {k: a[k] for k in b} == b


def test_a_coded_row_failing_its_gate_is_classed_both_ways_and_listed_for_reread(tmp_path):
    coders, batches, answers = folders(tmp_path)
    gates = coders / "coder_1" / ingest.GATES
    gates.mkdir()
    (gates / "p1.attempt2.gate.json").write_text(json.dumps(
        {"rows": [{"passes": False}, {"passes": True}]}))
    good = lines(("p1\\#outcome_1", "FinnGen R9", S1, "release 9"),
                 ("p1\\#pqtl_1", ABSENT, S2, "an unlisted dataset")) + TAIL
    (answers / "batch_07_run1.md").write_text(good)
    summary = ingest.ingest(answers, batches, coders, tmp_path / "out")
    assert summary["comparison_counts"] == {"agree_same_dictionary_row": 1,
                                            "both_unresolved_different_value": 1}
    assert summary["comparison_counts_under_gate_rule"] == {
        "both_unresolved_different_value": 1, "disagree_first_unresolved_second_coded": 1}
    reread = json.loads((tmp_path / "out" / "disagreements_for_reread.json").read_text())
    listed = reread["coder_1"]["p1.json"]
    assert [r["row"] for r in listed] == ["p1#outcome_1", "p1#pqtl_1"]
    assert listed[0]["first_check"]["coder_value_before_gate"] == "FinnGen R9"
    assert listed[0]["second_check"]["quote"] == S1
    assert summary["rows_to_reread"] == 2 and summary["papers_to_reread"] == {"coder_1": 1}
