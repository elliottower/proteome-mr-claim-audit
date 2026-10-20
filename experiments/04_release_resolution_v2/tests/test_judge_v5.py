import json
import pathlib

import pytest

import coding_runner as cr
import judge_v2 as j2
import judge_v4 as j4
import judge_v5 as j5

EXPERIMENTS = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = json.loads((EXPERIMENTS / "03_release_resolution/prompts/"
                     "control_validity_schema_v1.json").read_text())
USAGE = ("Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', "
         "'message': 'You have reached your specified API usage limits. You will regain access "
         "on 2026-11-01 at 00:00 UTC.'}}")
CREDIT = ("Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', "
          "'message': 'Your credit balance is too low to access the Anthropic API.'}}")
ANSWER = json.dumps({"row_id": "r1", "mark": "valid", "reason": "x", "quotation": ""})


def ok():
    return {"status": 200, "model_returned": j2.FABLE, "stop_reason": "end_turn",
            "usage": {"input_tokens": 100, "output_tokens": 10}, "text": ANSWER}


def judge(tmp_path, replies):
    sent = []

    def send(body):
        sent.append(body)
        return replies.pop(0)

    ledger = cr.Ledger(tmp_path / "spend.jsonl", 100.0)
    return j5.Judge(j2.FABLE, "S", SCHEMA, tmp_path / "store", ledger, send), sent, ledger


@pytest.mark.parametrize("refusal", [
    {"status": 400, "body": USAGE}, {"status": 400, "body": CREDIT},
    {"status": 402, "body": "payment required"}, {"status": 429, "body": "rate limited"},
    {"status": 403, "body": "Your account has reached its monthly Usage Limit."}])
def test_every_account_refusal_is_no_attempt_and_the_next_answer_is_the_first(tmp_path, refusal):
    jd, sent, ledger = judge(tmp_path, [refusal, ok()])
    assert jd.one("r1", {"row_id": "r1"})["state"] == "pending"
    assert ledger.reserved == {} and ledger.spent == 0
    [refused] = list((tmp_path / "store").glob("r1.*.refused.*.json"))
    assert json.loads(refused.read_text())["status_returned_by_api"] == refusal["status"]
    got = jd.one("r1", {"row_id": "r1"})
    assert got["state"] == "accepted" and [a["attempt"] for a in got["attempts"]] == [1]


def test_any_other_error_still_counts_as_an_attempt(tmp_path):
    other = {"status": 400, "body": "invalid_request_error: max_tokens too large"}
    jd, sent, _ = judge(tmp_path, [other, dict(other)])
    got = jd.one("r1", {"row_id": "r1"})
    assert got["state"] == "failed" and len(sent) == 2


def test_the_store_suffix_differs_from_the_fourth_version():
    assert j5.STORE_SUFFIX != j4.STORE_SUFFIX
