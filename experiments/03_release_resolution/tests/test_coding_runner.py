import json
import pathlib

import pytest

import coding_runner as cr

HERE = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = json.loads((HERE / "prompts" / "output_schema.json").read_text())
PROMPT = "fixed prompt"


def packet(record="r1", rows=("a1", "b2")):
    return {"record_id": record, "title": "T",
            "rows": [{"row_id": r, "side": "pqtl", "name": "not stated", "candidates": []}
                     for r in rows], "files": [], "accession_table_rows": []}


def answer(p, rows=None):
    return {"record_id": p["record_id"], "rows": [{
        "row_id": r, "identified_releases": [], "roles": [], "ancestry": [],
        "attribution_state": "unresolved", "unresolved_reasons": ["attribution_unresolved"],
        "decisive_evidence": [], "count_evidence": [], "abstract_transition": "none",
        "attribution_passage": None, "note": "n"}
        for r in (rows or [x["row_id"] for x in p["rows"]])]}


def ok(text, model=cr.CLAUDE, usage=None):
    return {"status": 200, "model_returned": model + "-x", "stop_reason": "end_turn",
            "usage": usage or {"input_tokens": 1000, "output_tokens": 100}, "text": text,
            "request_id": "q"}


class Fake:
    def __init__(self, replies):
        self.replies, self.bodies = list(replies), []

    def __call__(self, body):
        self.bodies.append(body)
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def runner(tmp_path, send, model=cr.CLAUDE, ceiling=cr.CEILING_USD, spent=0.0):
    ledger_path = tmp_path / "ledger.jsonl"
    tmp_path.mkdir(parents=True, exist_ok=True)
    if spent:
        ledger_path.write_text(json.dumps({"usd": spent}) + "\n")
    ledger = cr.Ledger(ledger_path, ceiling)
    return cr.Runner(model, PROMPT, SCHEMA, tmp_path / "store", ledger, send=send,
                     sleep=lambda s: None)


def test_bodies_follow_the_framing():
    p = packet()
    c = cr.claude_body(PROMPT, SCHEMA, p)
    assert c["system"] == [{"type": "text", "text": PROMPT, "cache_control": {"type": "ephemeral"}}]
    assert c["max_tokens"] == 128_000 and "tools" not in c and "temperature" not in c
    assert json.loads(c["messages"][0]["content"]) == p
    assert c["output_config"]["format"] == {"type": "json_schema", "schema": SCHEMA}
    s = cr.sol_body(PROMPT, SCHEMA, p)
    assert s["instructions"] == PROMPT and json.loads(s["input"]) == p
    assert s["tools"] == [] and s["store"] is False and s["max_output_tokens"] == 128_000
    assert s["text"]["format"]["strict"] is True and s["text"]["format"]["schema"] == SCHEMA
    assert "reasoning" not in s and "@" not in json.dumps(s) + json.dumps(c)


def test_an_accepted_answer_is_stored_and_never_requested_again(tmp_path):
    p = packet()
    fake = Fake([ok(json.dumps(answer(p)))])
    r = runner(tmp_path, fake)
    first = r.one("r1.1", p)
    assert first["state"] == "accepted" and first["attempts"][0]["model_returned"] == "claude-sonnet-5-5-x"
    again = runner(tmp_path, Fake([])).one("r1.1", p)
    assert again == first and len(fake.bodies) == 1


def test_a_bad_answer_is_requested_once_more_then_failed(tmp_path):
    p = packet()
    wrong_rows = json.dumps(answer(p, rows=["b2", "a1"]))
    fake = Fake([ok("not json"), ok(wrong_rows)])
    got = runner(tmp_path, fake).one("r1.1", p)
    assert got["state"] == "failed" and len(fake.bodies) == 2
    assert "parse" in got["attempts"][0]["errors"][0]
    assert "order" in got["attempts"][1]["errors"][0]


def test_a_second_attempt_can_be_accepted(tmp_path):
    p = packet()
    fake = Fake([ok(json.dumps({"record_id": "r1"})), ok(json.dumps(answer(p)))])
    got = runner(tmp_path, fake).one("r1.1", p)
    assert got["state"] == "accepted" and len(got["attempts"]) == 2


def test_transport_failures_leave_the_request_pending_and_not_spent(tmp_path):
    p = packet()
    fake = Fake([{"status": 503, "body": "busy"}] * cr.HTTP_TRIES)
    r = runner(tmp_path, fake)
    got = r.one("r1.1", p)
    assert got["state"] == "pending" and r.ledger.spent == 0 and not r.ledger.reserved
    retry = runner(tmp_path, Fake([ok(json.dumps(answer(p)))])).one("r1.1", p)
    assert retry["state"] == "accepted"


def test_a_client_error_is_not_retried(tmp_path):
    fake = Fake([{"status": 400, "body": "bad request"}])
    got = runner(tmp_path, fake).one("r1.1", packet())
    assert got["state"] == "pending" and len(fake.bodies) == 1


def test_spend_is_the_reported_usage_at_the_listed_prices(tmp_path):
    usage = {"input_tokens": 1_000_000, "cache_creation_input_tokens": 0,
             "cache_read_input_tokens": 2_000_000, "output_tokens": 100_000}
    assert cr.usd(cr.CLAUDE, usage) == pytest.approx(2.0 + 0.4 + 1.0)
    sol = {"input_tokens": 3_000_000, "input_tokens_details": {"cached_tokens": 2_000_000},
           "output_tokens": 100_000}
    assert cr.usd(cr.SOL, sol) == pytest.approx(2.0 + 0.2 + 1.0)
    p = packet()
    r = runner(tmp_path, Fake([ok(json.dumps(answer(p)), usage=usage)]))
    r.one("r1.1", p)
    assert r.ledger.spent == pytest.approx(3.4)
    lines = (tmp_path / "ledger.jsonl").read_text().splitlines()
    assert json.loads(lines[-1])["usd"] == pytest.approx(3.4)


def test_no_request_is_sent_whose_bound_would_cross_the_ceiling(tmp_path):
    p = packet()
    b = cr.bound(cr.CLAUDE, PROMPT, p)
    assert b > 1.28
    fake = Fake([ok(json.dumps(answer(p)))])
    r = runner(tmp_path, fake, ceiling=10.0, spent=10.0 - b + 0.01)
    with pytest.raises(cr.CeilingReached):
        r.one("r1.1", p)
    assert fake.bodies == []
    result = runner(tmp_path / "x", Fake([]), ceiling=10.0, spent=10.0).run([("r1.1", p)])
    assert result["stopped"] and result["not_sent_ceiling"] == 1


def test_the_ledger_counts_spend_from_earlier_passes(tmp_path):
    path = tmp_path / "ledger.jsonl"
    path.write_text(json.dumps({"usd": 1.5}) + "\n" + json.dumps({"usd": 2.0}) + "\n")
    assert cr.Ledger(path).spent == pytest.approx(3.5)


def test_request_keys_change_with_the_packet_and_the_model():
    p, q = packet(), packet(rows=("a1",))
    assert cr.request_key(cr.CLAUDE, PROMPT, SCHEMA, p) != cr.request_key(cr.CLAUDE, PROMPT, SCHEMA, q)
    assert cr.request_key(cr.CLAUDE, PROMPT, SCHEMA, p) != cr.request_key(cr.SOL, PROMPT, SCHEMA, p)
