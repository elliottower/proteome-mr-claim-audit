import json

import pytest

import citations_fold_digest as fd
import span_failure_followup_counts as counts
import span_step_comparison as comparison
from manual_dataset_coding import ManualCodingError, check_cover


def row(pmid, index, passes, registered=None, pin="found"):
    registered = passes if registered is None else registered
    return json.dumps({"pmid": pmid, "claim_index": index, "evidence_span": f"span {index}",
                       "registered_check": registered, "citations_pin": pin, "passes": passes})


OLD = [row("p1", 0, True), row("p1", 1, False, True, "ambiguous"),
       row("p2", 0, False, False, "not found"), row("p2", 1, True)]
NEW = [OLD[0], row("p1", 1, True, True, "found"), row("p2", 0, False, False, "omission"), OLD[3]]
PERMITTED = {"pinned_at_first_occurrence_and_passing": ["p1:001"], "still_failing": ["p2:000"]}
USED = {"records_pinned_at_an_occurrence": {"p1:001": {"pin_method": "occurrence_1",
                                                       "occurrence_count": 2,
                                                       "state": "found"}},
        "stored_abstract_has_duplicated_passage": {"p1": 1}}


def test_the_permitted_change_and_nothing_else_holds():
    made = comparison.compare_file(OLD, NEW, PERMITTED, USED)
    assert made["holds"] and made["differing_records"] == ["p1:001", "p2:000"]
    assert (made["passing_registered"], made["passing_corrected"]) == (2, 3)
    assert made["occurrence_counts"] == [2]


@pytest.mark.parametrize("new,used,failing", [
    ([row("p1", 0, True, True, "found "), *NEW[1:]], USED, "diff_within_permitted"),
    ([NEW[0], OLD[1], *NEW[2:]], USED, "duplicated_now_pass"),
    ([*NEW[:2], row("p2", 0, True, False, "found"), NEW[3]], USED, "joined_still_fail"),
    (NEW, {**USED, "records_pinned_at_an_occurrence": {
        **USED["records_pinned_at_an_occurrence"],
        "p2:000": {"pin_method": "occurrence_1", "occurrence_count": 2, "state": "found"}}},
     "occurrence_only_there"),
    (NEW, {**USED, "records_pinned_at_an_occurrence": {}}, "occurrence_only_there"),
    (NEW[:3], USED, "same_records"),
])
def test_each_departure_fails_its_assertion(new, used, failing):
    made = comparison.compare_file(OLD, new, PERMITTED, used)
    assert not made["holds"] and made[failing] is False


def test_a_file_with_no_permitted_record_must_be_byte_identical():
    none = {"pinned_at_first_occurrence_and_passing": [], "still_failing": []}
    empty = {"records_pinned_at_an_occurrence": {}, "stored_abstract_has_duplicated_passage": {}}
    same = [OLD[0], OLD[3]]
    assert comparison.compare_file(same, same, none, empty)["holds"]
    changed = comparison.compare_file(same, [same[0], same[1] + " "], none, empty)
    assert not changed["holds"] and changed["unaffected_files_equal"] is False


def test_fold_parity_holds_only_for_identical_digests():
    texts = {"abstract:p1": "Naïve  β-cell text", "span:search:p1:000": "β-cell"}
    old = fd.digest(texts, {"passage_fold": str.lower, "skeleton": str.casefold})
    new = fd.digest(texts, {"passage_fold": str.lower, "skeleton": str.casefold})
    other = fd.digest(texts, {"passage_fold": str.upper, "skeleton": str.casefold})
    for d in (old, new, other):
        d["citations"] = {"version": "x", "direct_url": None}
    assert old["sha256"] == new["sha256"] != other["sha256"]
    assert "β" not in json.dumps(old) and "text" not in json.dumps(old["items"])
    assert comparison.fold_parity(old, new)["holds"]
    parity = comparison.fold_parity(old, other)
    assert not parity["holds"] and parity["differing_texts"] == 2


ABSTRACT = ("Higher protein X raised risk of stroke in Europeans but not in East Asians, in "
            "contrast to earlier reports, and lowered risk of asthma in both groups.")


def test_the_text_left_out_between_two_pieces_is_found_and_its_tokens_counted():
    span = "Higher protein X raised risk of stroke and lowered risk of asthma in both groups."
    left_out = counts.omitted(span, ABSTRACT)
    assert left_out[:3] == ["in", "europeans", "but"] and left_out[-1] == "reports"
    assert counts.contrast_tokens(left_out) == ["not", "but", "in contrast"]
    assert counts.contrast_tokens(["notable", "nothing", "butter", "contrast"]) == []
    assert counts.contrast_tokens(["Without", "it"]) == ["without"]
    assert counts.omitted("Higher protein X raised risk of stroke", ABSTRACT) is None


def check(protein, outcome, direction, p_ids, o_ids, ok=True):
    return {"protein_as_written": protein, "outcome_as_written": outcome, "direction": direction,
            "protein_ids": p_ids, "outcome_ids": o_ids, "evidence_type": "mr_estimate",
            "protein_check": "pass" if ok else "protein_unmapped", "outcome_check": "pass",
            "relation_ambiguous": False}


def test_repeated_claims_are_counted_as_written_and_after_mapping():
    made = counts.duplicate_counts([
        check("IL6R", "CAD", "lowers", ["HGNC:1"], ["EFO:1"]),
        check("IL-6R", "coronary disease", "lowers", ["HGNC:1"], ["EFO:1"]),
        check("IL6R", "CAD", "lowers", ["HGNC:1"], ["EFO:1"]),
        check("PCSK9", "CAD", "raises", ["HGNC:2"], ["EFO:1"], ok=False)])
    assert made == {"records": 4, "distinct_as_written": 3, "distinct_after_mapping": 2,
                    "records_passing_the_other_criteria": 3,
                    "distinct_after_mapping_among_those": 1}


def test_a_code_for_a_row_outside_the_primary_queue_is_refused(tmp_path):
    fields = ["record_id", "side", "name_as_written"]
    primary = [{"record_id": "p1", "side": "outcome", "name_as_written": "FinnGen"}]
    codes = tmp_path / "codes.csv"
    codes.write_text("record_id,side,name_as_written\np1,outcome,FinnGen\n")
    check_cover(codes, primary)
    codes.write_text("record_id,side,name_as_written\np1,outcome,FinnGen\n"
                     "p9,outcome,FinnGen study\n")
    with pytest.raises(ManualCodingError):
        check_cover(codes, primary)
    assert fields == list(primary[0])
