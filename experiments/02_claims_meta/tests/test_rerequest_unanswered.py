import pytest

import rerequest_unanswered as ru


def ok(pmid, value="yes"):
    return {"pmid": pmid, "status": "ok", "attempts": 1, "errors": [], "output": {"v": value}}


def failed(pmid, errors):
    return {"pmid": pmid, "status": "extraction_failed", "attempts": 2, "errors": errors,
            "output": None}


NO_CREDIT = ["attempt 1: HTTP 429", "attempt 2: HTTP 429"]
BAD_SCHEMA = ["attempt 1: ValidationError: x", "attempt 2: ValidationError: x"]
MIXED = ["attempt 1: HTTP 429", "attempt 2: ValidationError: x"]


def test_only_rows_without_any_answer_are_unanswered():
    rows = [ok("a"), failed("b", NO_CREDIT), failed("c", BAD_SCHEMA), failed("d", MIXED),
            failed("e", ["attempt 1: HTTP None", "attempt 2: HTTP 503"]), failed("f", [])]
    assert ru.unanswered(rows) == ["b", "e"]


def test_merge_replaces_exactly_the_unanswered_rows_in_place():
    first = [ok("a", "first"), failed("b", NO_CREDIT), ok("c", "first"), failed("d", NO_CREDIT)]
    second = [ok("d", "second"), failed("b", NO_CREDIT)]
    rows, replaced = ru.merge(first, second)
    assert replaced == ["b", "d"]
    assert [r["pmid"] for r in rows] == ["a", "b", "c", "d"]
    assert rows[0] == first[0] and rows[2] == first[2]
    assert rows[1] == second[1] and rows[3] == second[0]


def test_merge_refuses_a_second_answer_for_an_answered_row():
    first = [ok("a"), failed("b", NO_CREDIT)]
    with pytest.raises(ru.RerequestError):
        ru.merge(first, [ok("a", "other"), ok("b")])


def test_merge_refuses_a_second_request_for_a_schema_failure():
    first = [ok("a"), failed("b", BAD_SCHEMA)]
    with pytest.raises(ru.RerequestError):
        ru.merge(first, [ok("b")])


def test_merge_refuses_a_missing_or_repeated_record():
    first = [failed("a", NO_CREDIT), failed("b", NO_CREDIT)]
    with pytest.raises(ru.RerequestError):
        ru.merge(first, [ok("a")])
    with pytest.raises(ru.RerequestError):
        ru.merge(first, [ok("a"), ok("b"), ok("b")])


def test_stored_answers_finds_a_200_exchange_and_ignores_failed_ones(tmp_path):
    (tmp_path / "a_attempt1.http1.json").write_text("{}")
    (tmp_path / "b_attempt1.http5.json").write_text("{}")
    (tmp_path / "b_attempt2.json").write_text("{}")
    assert ru.stored_answers(tmp_path, ["a", "b"]) == ["b"]
