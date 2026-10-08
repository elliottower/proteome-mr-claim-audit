import json

import pytest
import yaml

import span_restoration as first
import span_restoration_tool_side as tool
import span_restoration_v2 as sr
import span_shards
from test_span_restoration import ABSTRACT, DROPPED, WHOLE, check, rows

THIN, NO_BREAK = " ", " "
GROUPED = (f"We studied 12{THIN}500 adults of European ancestry and 3{NO_BREAK}200 controls "
           "in the main analysis.")


@pytest.mark.parametrize("span,abstract", [
    (DROPPED, ABSTRACT),
    (DROPPED.upper().replace(" ", "  "), ABSTRACT),
    ("protein X was associated with lower risk of stro",
     "Higher apoprotein X was causally associated with lower risk of stroke."),
    ("Later we saw A B effect", "We saw A big B effect here. Later we saw A small B effect here."),
    ("with higher levels overall", "Risk fell with higher IL6R levels overall."),
])
def test_where_no_digits_are_grouped_the_two_copies_restore_the_same_passage(span, abstract):
    made, before = sr.restore_span(span, abstract), first.restore_span(span, abstract)
    assert made["passage"] == before["passage"] != span
    assert (made["start"], made["end"]) == (before["start"], before["end"])
    assert made["omitted_token_words"] == 1


@pytest.mark.parametrize("span", [
    WHOLE, WHOLE.replace("causally associated ", ""), DROPPED.replace("lower", "higher"),
    DROPPED.replace("0.90", "0.9"), DROPPED.replace("10−6", "106"),
    WHOLE.replace("(OR ", "("), "Higher protein Y raised LDL", "stroke"])
def test_what_was_not_eligible_stays_not_eligible(span):
    assert sr.restore_span(span, ABSTRACT) is None


def test_a_group_of_digits_is_one_token_left_out_whole_or_not_at_all():
    part = "We studied 12 adults of European ancestry"
    assert first.restore_span(part, GROUPED) is not None
    assert sr.restore_span(part, GROUPED) is None
    assert sr.restore_span("adults of European ancestry and 3 controls in the main",
                           GROUPED) is None
    assert sr.restore_span("adults of European ancestry and controls in the main", GROUPED)[
        "passage"] == f"adults of European ancestry and 3{NO_BREAK}200 controls in the main"
    made = sr.restore_span("We studied adults of European ancestry", GROUPED)
    assert made["passage"] == f"We studied 12{THIN}500 adults of European ancestry"
    assert made["omitted_token_words"] == 2 and first.restore_span(
        "We studied adults of European ancestry", GROUPED) is None
    assert sr.restore_span(f"12{THIN}500 adults European ancestry", GROUPED)["passage"] == (
        f"12{THIN}500 adults of European ancestry")


def test_an_ordinary_space_between_digits_groups_nothing():
    text = "We studied 12 500 adults of European ancestry in the main analysis."
    assert sr.restore_span("We studied 12 adults of European ancestry", text)["passage"] == (
        "We studied 12 500 adults of European ancestry")
    assert sr.tokens(GROUPED, list(sr.re.finditer(r"\S+", GROUPED)))[2] == (2, 4)


def test_a_record_left_as_written_is_in_the_map_and_keeps_its_span():
    repairs, restored = sr.restore_file(rows(), {"p1": ABSTRACT}, "abc", frozenset({"p1:000"}))
    assert repairs["p1:000"]["restored_passage_sha256"] == sr.sha(WHOLE)
    assert not repairs["p1:000"]["span_replaced_in_derived_file"]
    assert restored == rows()
    repairs, restored = sr.restore_file(rows(), {"p1": ABSTRACT}, "abc")
    assert repairs["p1:000"]["span_replaced_in_derived_file"]
    assert restored[0]["output"]["claims"][0]["evidence_span"] == WHOLE
    assert "protein" not in json.dumps(repairs)


def repair(passage, start=0):
    return {"restored_passage_sha256": sr.sha(passage),
            "source_offsets": [start, start + len(passage)], "source_sha256": "s"}


def test_the_crosscheck_needs_every_record_equal_in_every_source():
    ours = {"p1:000": repair("abc"), "p1:001": repair("def", 5)}
    plain = sr.other_hashes({"p1:000": sr.sha("abc"), "p1:001": sr.sha("def")}, "search")
    full = sr.other_hashes({"records": {
        "search:p1:000": {"restored_passage_sha256": sr.sha("abc"), "passage_start": 0,
                          "passage_end": 3, "source_sha256": "s"},
        "search:p1:001": {"restored_passage_sha256": sr.sha("def"), "passage_start": 5,
                          "passage_end": 8, "source_sha256": "s"},
        "chase1:p9:000": {"restored_passage_sha256": "x"}}}, "search")
    made = sr.crosscheck(ours, {"a": plain, "b": full})
    assert [v["differing_or_missing"] for v in made.values()] == [[], []]
    assert made["b"]["records_in_source"] == 2 and made["b"]["equal"] == 2
    for change in ({"restored_passage_sha256": "0"}, {"passage_end": 9}, {"source_sha256": "t"}):
        wrong = {**full, "p1:001": {**full["p1:001"], **change}}
        assert sr.crosscheck(ours, {"b": wrong})["b"]["differing_or_missing"] == ["p1:001"]
    assert sr.crosscheck(ours, {"a": {"p1:000": plain["p1:000"]}})["a"][
        "differing_or_missing"] == ["p1:001"]
    assert sr.crosscheck({"p1:000": ours["p1:000"]}, {"a": plain})["a"][
        "differing_or_missing"] == ["p1:001"]


def test_transitions_name_their_set_and_refuse_a_record_that_is_in_neither_run():
    before = [check("p1:000"), check("p1:001", enters_registry=True, first_failure=None)]
    after = [check("p1:000", enters_registry=True, first_failure=None), before[1]]
    made = sr.transition_counts(["p1:000"], before, after, "pinned")
    assert made["pinned_records"] == 1 and made["other_records_differing"] == []
    assert (made["pinned_entering_registry_before"], made["pinned_entering_registry_after"]) == (
        0, 1)
    assert made["transitions"]["first_failure"] == {"span_not_verified -> None": 1}
    with pytest.raises(sr.RestorationError):
        sr.transition_counts(["p7:000"], before, after, "pinned")


def fake_restore(passages):
    def main(argv):
        path, claim_id = tool.pathlib.Path(argv[0]), argv[2]
        doc = yaml.safe_load(path.read_text())
        original = doc["claims"][claim_id]["quotes"][0]["exact"]
        if original not in passages:
            print("refused")
            return 1
        side = path.with_name(f"{path.stem}.restored.yaml")
        held = yaml.safe_load(side.read_text()) if side.exists() else {
            "source": doc["source"], "claims": {}}
        held["claims"][f"{claim_id}-restored"] = {
            "restored": {"from": claim_id, "original": original,
                         "source": {"sha256": doc["source"]["sha256"]},
                         "text": {"sha256": "t"}, "passage": {"start": 3, "end": 9},
                         "omitted": [{"start": 4, "end": 5, "tokens": 1, "position": 2}],
                         "fittings": {"found": 1}, "rule": {"name": "bounded-passage"}},
            "quotes": [{"exact": passages[original]}]}
        side.write_text(yaml.safe_dump(held, allow_unicode=True))
        print("restored")
        return 0
    return main


def test_the_tool_side_reads_the_sidecar_and_leaves_the_claims_file_as_given(tmp_path, capsys):
    spans = {"p1:000": DROPPED, "p1:003": "another span − with a sign", "p2:001": "third"}
    files = tool.write_tree(tmp_path / "c", spans, {"p1": ABSTRACT, "p2": "second abstract"})
    assert files["p1:000"] == files["p1:003"] != files["p2:001"]
    doc = yaml.safe_load(files["p1:003"].read_text())
    assert doc["claims"]["c003"]["quotes"][0]["exact"] == spans["p1:003"]
    assert doc["source"]["sha256"] == tool.hashlib.sha256(ABSTRACT.encode()).hexdigest()
    given = files["p1:000"].read_bytes()
    made = tool.restore_all(files, fake_restore({DROPPED: WHOLE, spans["p1:003"]: "x − y",
                                                 "third": "the third"}))
    assert files["p1:000"].read_bytes() == given
    assert made["p1:000"]["restored_passage_sha256"] == sr.sha(WHOLE)
    assert made["p1:003"]["restored_passage_sha256"] == sr.sha("x − y")
    assert made["p1:000"]["original_span_sha256"] == sr.sha(DROPPED)
    assert (made["p2:001"]["passage_start"], made["p2:001"]["fittings"]) == (3, 1)
    assert capsys.readouterr().out == ""
    with pytest.raises(tool.ToolSideError):
        tool.restore_all(files, fake_restore({DROPPED: WHOLE}))


def test_the_commit_of_the_tool_side_build_is_read_from_its_install_record():
    assert tool.commit_of({"direct_url": {"vcs_info": {"commit_id": "abc"}}}) == "abc"
    assert tool.commit_of({"direct_url": {"dir_info": {"editable": True}}}) is None
    assert tool.commit_of({"direct_url": None}) is None


def span_line(pmid, index, passes=True, registered=True, pin="found", warnings=(), n=1):
    return json.dumps({"pmid": pmid, "claim_index": index, "claim_id": f"c{index:03d}",
                       "evidence_span": "x", "registered_check": registered,
                       "citations_pin": pin, "citations_warnings": list(warnings),
                       "n_sentences": n, "passes": passes})


def test_parts_are_consecutive_and_join_back_to_the_whole():
    lines = [json.dumps({"pmid": f"p{i}"}) for i in range(7)]
    for size in (1, 2, 3, 7, 50):
        parts = span_shards.split(lines, size)
        assert [x for part in parts for x in part] == lines
        assert all(len(part) <= size for part in parts)
    abstracts = [json.dumps({"pmid": f"p{i}", "abstract": str(i)}) for i in (3, 0, 9, 1, 0)]
    assert span_shards.abstracts_for(lines[:2], abstracts) == [abstracts[1], abstracts[3],
                                                               abstracts[4]]
    with pytest.raises(span_shards.ShardError):
        span_shards.split(lines, 0)
    assert span_shards.shard_stem("x", 3) == "x.shard0003"


def test_joined_spans_and_occurrences_refuse_a_record_in_two_parts_or_two_builds():
    a, b = [span_line("p1", 0), span_line("p1", 1)], [span_line("p2", 0)]
    assert span_shards.join_spans([a, b]) == a + b
    with pytest.raises(span_shards.ShardError):
        span_shards.join_spans([a, [span_line("p1", 1)]])
    head = {"citations_installed": {"version": "1"}, "citations_commit": "c", "rule": "r"}
    one = head | {"records_pinned_at_an_occurrence": {"p1:001": {"occurrence_count": 2}},
                  "stored_abstract_has_duplicated_passage": {"p9": 1}}
    two = head | {"records_pinned_at_an_occurrence": {"p2:000": {"occurrence_count": 3}},
                  "stored_abstract_has_duplicated_passage": {"p2": 2}}
    made = span_shards.join_occurrences([one, two])
    assert list(made["records_pinned_at_an_occurrence"]) == ["p1:001", "p2:000"]
    assert list(made["stored_abstract_has_duplicated_passage"]) == ["p2", "p9"]
    assert list(made) == list(one)
    with pytest.raises(span_shards.ShardError):
        span_shards.join_occurrences([one, one])
    with pytest.raises(span_shards.ShardError):
        span_shards.join_occurrences([one, two | {"citations_commit": "d"}])


def test_the_summary_counts_the_joined_lines_as_the_sealed_script_counts_its_results():
    lines = [span_line("p1", 0), span_line("p1", 1, False, True, "ambiguous"),
             span_line("p2", 0, False, False, "found", ["normalized"], 3),
             span_line("p3", 0, True, True, "found", ["normalized"])]
    made = span_shards.summary("outputs/parsed/x.jsonl", [json.loads(x) for x in lines], 0)
    assert list(made) == ["extraction", "n_claims", "registered_check_pass", "citations_pin_found",
                          "citations_found_only_after_punctuation_folding",
                          "citations_normalized_warning", "both_pass", "span_verification_rate",
                          "spans_over_two_sentences", "citations_verify_exit", "failing"]
    assert [made[k] for k in list(made)[1:10]] == [4, 3, 3, 1, 2, 2, 0.5, 1, 0]
    assert [f["claim_index"] for f in made["failing"]] == [1, 0]
    assert span_shards.summary("x", [], 2)["span_verification_rate"] is None
