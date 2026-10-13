import json
import pathlib

import pytest

import adjudication_pages as ap
import coding_runner as cr
import judge as jd

HERE = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = json.loads((HERE / "prompts" / "judge_schema.json").read_text())


def decision(choice="answer_1", conf=0.9, human=False, quote=""):
    return {"row_id": "r1", "choice": choice, "confidence": conf, "needs_human": human,
            "reason": "x", "quotation": quote}


def accepted(**k):
    return {"state": "accepted", "decision": decision(**k)}


def test_the_system_text_is_the_judge_prompt_then_the_coding_rules_then_the_dictionary():
    got = jd.system_text("J\n", "C\n", "side,name\n")
    assert got == "J\n\n## Coding instructions\n\nC\n\n## Dictionary definitions\n\nside,name\n"


def test_the_request_shows_answers_by_label_and_never_a_model():
    packet = {"record_id": "1", "title": "T", "files": [{"file_id": "abstract", "kind": "abstract",
                                                        "text": "t"}]}
    q = {"row_id": "r1", "side": "pqtl", "name_as_written": "x", "outcomes_as_written": [],
         "candidates": ["A"], "family_id": "f", "claim_record_ids": ["1:000"]}
    req = jd.judge_request("disagreement", packet, q, [({"a": 1}, True), ({"b": 2}, False)])
    assert [a["label"] for a in req["answers"]] == ["Answer 1", "Answer 2"]
    assert req["row"] == {"row_id": "r1", "side": "pqtl", "name": "x", "candidates": ["A"]}
    body = jd.api_body("S", SCHEMA, req)
    assert "tools" not in body and "@" not in json.dumps(body)
    assert body["generationConfig"]["responseJsonSchema"] == SCHEMA
    assert "temperature" not in body["generationConfig"]


@pytest.mark.parametrize("task,result,gates,expected", [
    ("disagreement", accepted(), [True, True], []),
    ("disagreement", accepted(human=True), [True, True], ["needs_human"]),
    ("disagreement", accepted(conf=0.79), [True, True], ["confidence_below_0.80"]),
    ("disagreement", accepted(choice="neither"), [True, True], ["choice_neither"]),
    ("disagreement", accepted(choice="answer_2"), [True, False], ["chosen_answer_fails_the_gate"]),
    ("disagreement", accepted(choice="correct"), [True, True], ["choice_not_of_the_task"]),
    ("audit", accepted(choice="correct"), [True], []),
    ("audit", accepted(choice="correct"), [False], ["chosen_answer_fails_the_gate"]),
    ("audit", accepted(choice="substantive_error"), [True], ["choice_substantive_error"]),
    ("audit", accepted(choice="other_issue", conf=0.5), [True],
     ["confidence_below_0.80", "choice_other_issue"]),
    ("disagreement", accepted(quote="not there"), [True, True], ["quotation_not_in_the_files"]),
    ("disagreement", {"state": "failed"}, [True, True], ["request_failed_twice"]),
])
def test_routing_follows_item_2(task, result, gates, expected):
    assert jd.route(task, result, gates, "the files say this") == expected


def test_a_quotation_that_stands_in_the_files_does_not_route():
    assert jd.route("disagreement", accepted(quote="files say"), [True, True],
                    "the files say this") == []


def test_calibration_order_is_seeded_over_row_id_order():
    lone = [f"r{i:03d}" for i in range(60)]
    got = jd.calibration_order(list(reversed(lone)), 20261018)
    assert sorted(got) == lone and got == jd.calibration_order(lone, 20261018)
    assert got != jd.calibration_order(lone, 20261019)


def test_spend_follows_the_prompt_length_tier_and_the_bound_covers_it():
    low = {"promptTokenCount": 100_000, "cachedContentTokenCount": 50_000,
           "candidatesTokenCount": 1_000, "thoughtsTokenCount": 3_000}
    assert jd.usd(low) == pytest.approx((50_000 * 2 + 50_000 * 0.2 + 4_000 * 12) / 1e6)
    high = {**low, "promptTokenCount": 300_000}
    assert jd.usd(high) == pytest.approx((250_000 * 4 + 50_000 * 0.4 + 4_000 * 18) / 1e6)
    req = {"x": "y" * 30_000}
    assert jd.bound("s" * 120_000, req) > jd.usd({"promptTokenCount": 150_000 // 1,
                                                  "candidatesTokenCount": 32_768})


def test_the_blinded_order_is_the_pages_order():
    models = ("claude-sonnet-5-5", "gpt-6.1-sol")
    for rid in ("aa", "bb", "cc", "dd"):
        one, _ = jd.blinded(rid, models)
        assert (one == models[0]) == ap.first_is_a(rid, 20261017)


def test_a_judge_decision_is_stored_retried_once_and_not_requested_again(tmp_path):
    ledger = cr.Ledger(tmp_path / "l.jsonl")
    replies = [{"status": 200, "model_returned": "gemini-x", "usage": {"promptTokenCount": 10},
                "text": "no json"},
               {"status": 200, "model_returned": "gemini-x", "usage": {"promptTokenCount": 10},
                "text": json.dumps(decision())}]
    sent = []

    def send(body):
        sent.append(body)
        return dict(replies.pop(0))

    j = jd.Judge("S", SCHEMA, tmp_path / "store", ledger, send, sleep=lambda s: None)
    got = j.one("r1", {"task": "disagreement"})
    assert got["state"] == "accepted" and len(sent) == 2 and len(got["attempts"]) == 2
    again = jd.Judge("S", SCHEMA, tmp_path / "store", ledger, send).one("r1", {"task": "disagreement"})
    assert again == got and len(sent) == 2
    assert len((tmp_path / "l.jsonl").read_text().splitlines()) == 2


def test_a_transport_failure_stays_pending_and_releases_its_reservation(tmp_path):
    ledger = cr.Ledger(tmp_path / "l.jsonl")
    j = jd.Judge("S", SCHEMA, tmp_path / "store", ledger,
                 lambda body: {"status": 400, "body": "bad"}, sleep=lambda s: None)
    got = j.one("r1", {"task": "audit"})
    assert got["state"] == "pending" and not ledger.reserved and ledger.spent == 0
