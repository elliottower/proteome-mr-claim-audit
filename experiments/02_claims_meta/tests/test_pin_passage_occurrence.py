import subprocess

import pytest
import yaml

import pin_passage_occurrence as helper

SENTENCES = ["Some intro text.", "We used data from release R9 of the study.",
             "Final words here."]
PASSAGE = {"passage_id": "p002", "sentences": SENTENCES, "claims_file": "claims/x.yaml"}
PAPER = {"record_id": "p1", "rows": [
    {"side": "outcome", "passages": [{"passage_id": "p001", "sentences": ["A."]}]},
    {"side": "pqtl", "passages": []}, {"side": "outcome", "passages": [PASSAGE]}]}


def folder(tmp_path, claims=None):
    (tmp_path / "claims").mkdir()
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources" / "x.txt").write_text("Alpha. " + SENTENCES[1] + " Omega.\n"
                                                + " ".join(SENTENCES))
    (tmp_path / "claims" / "x.yaml").write_text(yaml.safe_dump(
        {"source": {"citation": "x", "local": "sources/x.txt", "sha256": "0"},
         "claims": claims or {}}, sort_keys=False))
    return tmp_path


def runner(pin_out, pin_code, verify_code, calls):
    def run(args, cwd):
        calls.append((args, cwd))
        if args[0] == "pin":
            return subprocess.CompletedProcess(args, pin_code, pin_out, "")
        return subprocess.CompletedProcess(args, verify_code, "report", "")
    return run


def held(root):
    return yaml.safe_load((root / "claims" / "x.yaml").read_text())["claims"]


def test_the_row_and_passage_are_found_by_side_order_and_passage_id():
    assert helper.find_passage(PAPER, "outcome_2", "p002") is PASSAGE
    with pytest.raises(helper.PinError):
        helper.find_passage(PAPER, "outcome_2", "p001")
    with pytest.raises(helper.PinError):
        helper.find_passage(PAPER, "outcome_3", "p002")


def test_prefix_and_suffix_are_the_whole_sentences_either_side():
    assert helper.occurrence_quote(PASSAGE, 2) == {
        "exact": SENTENCES[1], "prefix": SENTENCES[0], "suffix": SENTENCES[2]}
    assert helper.occurrence_quote(PASSAGE, 1) == {"exact": SENTENCES[0],
                                                   "suffix": SENTENCES[1]}
    assert helper.occurrence_quote(PASSAGE, 3) == {"exact": SENTENCES[2],
                                                   "prefix": SENTENCES[1]}
    with pytest.raises(helper.PinError):
        helper.occurrence_quote(PASSAGE, 4)


def test_a_sentence_the_tool_accepts_is_pinned_by_the_tool_and_nothing_is_written(tmp_path):
    root, calls = folder(tmp_path), []
    assert helper.pin(PASSAGE, 2, "outcome_2_a3", root, runner("found", 0, 0, calls)) == "pinned"
    assert calls == [(["pin", "claims/x.yaml", "--id", "outcome_2_a3", "--quote", SENTENCES[1]],
                      root)]
    assert held(root) == {}


def test_an_ambiguous_sentence_is_written_with_prefix_and_suffix_once_verified(tmp_path):
    root, calls = folder(tmp_path, {"old": {"quotes": [{"exact": "Alpha."}]}}), []
    state = helper.pin(PASSAGE, 2, "outcome_2_a3", root,
                       runner("ambiguous  We used ...", 1, 0, calls))
    assert state == "pinned_with_prefix_and_suffix"
    assert held(root) == {"old": {"quotes": [{"exact": "Alpha."}]}, "outcome_2_a3": {"quotes": [
        {"exact": SENTENCES[1], "prefix": SENTENCES[0], "suffix": SENTENCES[2]}]}}
    assert calls[1][0] == ["verify", "--claims", "claims", "--strict"] and calls[1][1] != root


def test_nothing_is_written_when_the_occurrence_is_still_not_single(tmp_path):
    root = folder(tmp_path)
    with pytest.raises(helper.PinError):
        helper.pin(PASSAGE, 2, "outcome_2_a3", root, runner("ambiguous  We used", 1, 1, []))
    assert held(root) == {}


def test_a_line_with_no_sentence_either_side_or_another_refusal_raises(tmp_path):
    root = folder(tmp_path)
    alone = {"passage_id": "p009", "sentences": [SENTENCES[1]], "claims_file": "claims/x.yaml"}
    with pytest.raises(helper.PinError):
        helper.pin(alone, 1, "outcome_2_a3", root, runner("ambiguous  We used", 1, 0, []))
    with pytest.raises(helper.PinError):
        helper.pin(PASSAGE, 2, "outcome_2_a3", root, runner("not found  We used", 1, 0, []))
    assert held(root) == {}


def test_a_claim_id_already_in_the_file_is_refused_before_the_tool_runs(tmp_path):
    root, calls = folder(tmp_path, {"outcome_2_a3": {"quotes": [{"exact": "Alpha."}]}}), []
    with pytest.raises(helper.PinError):
        helper.pin(PASSAGE, 2, "outcome_2_a3", root, runner("found", 0, 0, calls))
    assert calls == []
