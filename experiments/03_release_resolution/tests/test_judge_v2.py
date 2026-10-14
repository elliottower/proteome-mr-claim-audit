import json
import pathlib

import pytest

import coding_runner as cr
import judge_v2 as j2

HERE = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = json.loads((HERE / "prompts" / "judge_schema.json").read_text())


def decision(choice="answer_1", conf=0.9, human=False, quote="", rid="r1"):
    return {"row_id": rid, "choice": choice, "confidence": conf, "needs_human": human,
            "reason": "x", "quotation": quote}


def ok(text, model=j2.FABLE):
    return {"status": 200, "model_returned": model, "stop_reason": "end_turn",
            "usage": {"input_tokens": 100, "output_tokens": 50}, "text": text}


class Fake:
    def __init__(self, replies):
        self.replies, self.bodies = list(replies), []

    def __call__(self, body):
        self.bodies.append(body)
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return dict(r)


def judge(tmp_path, send, model=j2.FABLE, ceiling=100.0):
    ledger = cr.Ledger(tmp_path / "l.jsonl", ceiling)
    return j2.Judge(model, "S", SCHEMA, tmp_path / model, ledger, send, sleep=lambda s: None), ledger


def test_bodies_follow_the_amendment_and_never_carry_the_other_judge():
    req = {"task": "audit", "row": {"row_id": "r1"}}
    f = j2.fable_body("S", SCHEMA, req)
    assert f["max_tokens"] == 8192 and "tools" not in f and "thinking" not in f
    assert f["output_config"]["format"]["schema"] == SCHEMA
    a = j2.astra_body("S", SCHEMA, req)
    assert a["max_output_tokens"] == 8192 and a["tools"] == [] and "reasoning" not in a
    assert a["text"]["format"]["strict"] is True and "@" not in json.dumps([f, a])


def test_spend_at_the_recorded_list_prices():
    assert j2.usd(j2.FABLE, {"input_tokens": 1e6, "cache_creation_input_tokens": 1e6,
                             "cache_read_input_tokens": 1e6, "output_tokens": 1e6}) == pytest.approx(
        10 + 12.5 + 0.25 + 50)
    assert j2.usd(j2.ASTRA, {"input_tokens": 2e6, "input_tokens_details": {"cached_tokens": 1e6},
                             "output_tokens": 1e6}) == pytest.approx(10 + 1 + 50)


def test_the_bound_covers_input_at_the_preflight_ratio_and_the_full_output():
    req = {"x": "y" * 10_000}
    chars = 1 + len(json.dumps(req))
    assert j2.bound(j2.FABLE, "S", req) == pytest.approx((chars / 1.98 * 10 + 8192 * 50) / 1e6)
    assert j2.bound(j2.ASTRA, "S", req) == pytest.approx((chars / 3.11 * 10 + 8192 * 50) / 1e6)


def test_two_bad_attempts_fail_and_errors_count_as_attempts(tmp_path):
    fake = Fake([{"status": 500, "body": "x"}, ok("not json")])
    j, ledger = judge(tmp_path, fake)
    got = j.one("r1", {"task": "audit"})
    assert got["state"] == "failed" and len(fake.bodies) == 2 and not ledger.reserved
    assert len((tmp_path / "l.jsonl").read_text().splitlines()) == 1


def test_a_refusal_or_truncation_is_an_attempt_and_a_second_valid_answer_is_accepted(tmp_path):
    truncated = ok(None)
    truncated["stop_reason"] = "max_tokens"
    fake = Fake([truncated, ok(json.dumps(decision()))])
    j, _ = judge(tmp_path, fake)
    got = j.one("r1", {"task": "disagreement"})
    assert got["state"] == "accepted" and [a["attempt"] for a in got["attempts"]] == [1, 2]


@pytest.mark.parametrize("status", [402, 429])
def test_account_side_refusals_are_not_attempts_and_stay_pending(tmp_path, status):
    fake = Fake([{"status": status, "body": "no credit"}])
    j, ledger = judge(tmp_path, fake)
    got = j.one("r1", {"task": "audit"})
    assert got["state"] == "pending" and not ledger.reserved and ledger.spent == 0
    later = Fake([ok(json.dumps(decision(choice="correct")))])
    j2b, _ = judge(tmp_path, later)
    got = j2b.one("r1", {"task": "audit"})
    assert got["state"] == "accepted" and got["attempts"][0]["attempt"] == 1


def test_an_attempt_already_spent_is_counted_on_resume(tmp_path):
    ja, _ = judge(tmp_path, Fake([]))
    key = j2.request_key(j2.FABLE, "S", SCHEMA, {"task": "audit"})
    (ja.store / f"r1.{key}.attempt1.json").write_text(json.dumps({"counts_as_attempt": True,
                                                                   "attempt": 1, "status": 200}))
    resumed = Fake([ok("still bad")])
    jb, _ = judge(tmp_path, resumed)
    got = jb.one("r1", {"task": "audit"})
    assert got["state"] == "failed" and len(resumed.bodies) == 1


def test_the_ceiling_stops_before_a_request_whose_bound_would_cross(tmp_path):
    fake = Fake([ok(json.dumps(decision()))])
    j, _ = judge(tmp_path, fake, ceiling=0.1)
    with pytest.raises(cr.CeilingReached):
        j.one("r1", {"task": "disagreement"})
    assert fake.bodies == []


def test_send_order_is_seeded_over_row_id_order():
    rows = [f"r{i:03d}" for i in range(50)]
    got = j2.send_order(list(reversed(rows)))
    assert sorted(got) == rows and got == j2.send_order(rows) and got != rows


def acc(choice, **k):
    return {"state": "accepted", "decision": decision(choice=choice, **k)}


def test_a_row_stands_alone_only_when_both_judges_agree_unflagged():
    files = "the files say this"
    both = {j2.FABLE: acc("answer_1"), j2.ASTRA: acc("answer_1")}
    assert j2.route_pair("disagreement", both, [True, True], files) == []
    split = {j2.FABLE: acc("answer_1"), j2.ASTRA: acc("answer_2")}
    assert j2.route_pair("disagreement", split, [True, True], files) == ["judges_differ"]
    flagged = {j2.FABLE: acc("answer_1"), j2.ASTRA: acc("answer_1", conf=0.5)}
    assert j2.route_pair("disagreement", flagged, [True, True], files) == [
        "gpt-6-astra:confidence_below_0.80"]
    cut = {j2.FABLE: acc("correct"), j2.ASTRA: None}
    assert j2.route_pair("audit", cut, [True], files) == ["not_judged_by_both"]
    failed = {j2.FABLE: {"state": "failed"}, j2.ASTRA: acc("correct")}
    assert j2.route_pair("audit", failed, [True], files) == ["claude-fable-5-1:request_failed_twice"]
