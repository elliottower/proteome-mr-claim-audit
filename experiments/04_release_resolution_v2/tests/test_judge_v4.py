import json
import pathlib

import coding_runner as cr
import judge_v2 as j2
import judge_v4 as j4

EXPERIMENTS = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = json.loads((EXPERIMENTS / "03_release_resolution/prompts/"
                     "control_validity_schema_v1.json").read_text())
CREDIT = ("Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', "
          "'message': 'Your credit balance is too low to access the Anthropic API.'}}")
ANSWER = json.dumps({"row_id": "r1", "mark": "valid", "reason": "x", "quotation": ""})


def judge(tmp_path, replies):
    sent = []

    def send(body):
        sent.append(body)
        return replies.pop(0)

    ledger = cr.Ledger(tmp_path / "spend.jsonl", 100.0)
    return j4.Judge(j2.FABLE, "S", SCHEMA, tmp_path / "store", ledger, send), sent, ledger


def ok():
    return {"status": 200, "model_returned": j2.FABLE, "stop_reason": "end_turn",
            "usage": {"input_tokens": 100, "output_tokens": 10}, "text": ANSWER}


def test_a_credit_refusal_is_no_attempt_and_the_request_stays_pending(tmp_path):
    jd, sent, ledger = judge(tmp_path, [{"status": 400, "body": CREDIT}])
    got = jd.one("r1", {"row_id": "r1"})
    assert got["state"] == "pending" and len(sent) == 1
    assert ledger.reserved == {} and ledger.spent == 0
    [refused] = list((tmp_path / "store").glob("r1.*.refused.*.json"))
    stored = json.loads(refused.read_text())
    assert stored["status_returned"] == 400 and stored["counts_as_attempt"] is False
    assert not list((tmp_path / "store").glob("r1.*.attempt*.json"))


def test_after_a_credit_refusal_the_next_answer_is_the_first_attempt(tmp_path):
    jd, sent, ledger = judge(tmp_path, [{"status": 400, "body": CREDIT}, ok()])
    assert jd.one("r1", {"row_id": "r1"})["state"] == "pending"
    got = jd.one("r1", {"row_id": "r1"})
    assert got["state"] == "accepted" and got["decision"]["mark"] == "valid"
    assert [a["attempt"] for a in got["attempts"]] == [1]
    assert ledger.spent == (100 * 10.0 + 10 * 50.0) / 1e6


def test_any_other_error_still_counts_as_an_attempt(tmp_path):
    other = {"status": 400, "body": "invalid_request_error: something else"}
    jd, sent, _ = judge(tmp_path, [other, dict(other)])
    got = jd.one("r1", {"row_id": "r1"})
    assert got["state"] == "failed" and len(sent) == 2
    assert [a["status"] for a in got["attempts"]] == [400, 400]


def test_the_anthropic_schema_still_drops_only_unsupported_keywords(tmp_path):
    jd, sent, _ = judge(tmp_path, [ok()])
    jd.one("r1", {"row_id": "r1"})
    assert sent[0]["output_config"]["format"]["schema"] == SCHEMA
