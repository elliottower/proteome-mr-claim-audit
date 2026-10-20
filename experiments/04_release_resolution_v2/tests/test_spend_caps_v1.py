import json

import pytest

import coding_runner as cr
import coding_runner_v3 as cr3
import spend_caps_v1 as caps

SCHEMA = {"type": "object", "required": ["record_id", "rows"],
          "properties": {"record_id": {"type": "string"},
                         "rows": {"type": "array", "items": {
                             "type": "object", "required": ["row_id"],
                             "properties": {"row_id": {"type": "string"}}}}}}
PACKET = {"record_id": "r1", "rows": [{"row_id": "a"}], "files": []}
CREDIT = ("Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', "
          "'message': 'Your credit balance is too low to access the Anthropic API.'}}")


def ledger_file(tmp_path, extra=()):
    path = tmp_path / "spend.jsonl"
    lines = [{"model": "gpt-6.1-sol", "usd": caps.BASELINE_USD / caps.BASELINE_LINES}
             for _ in range(caps.BASELINE_LINES)] + list(extra)
    path.write_text("".join(json.dumps(e) + "\n" for e in lines))
    return path


def test_the_baseline_must_be_the_first_registrations_lines(tmp_path):
    path = tmp_path / "spend.jsonl"
    path.write_text(json.dumps({"model": "gpt-6.1-sol", "usd": 1.0}) + "\n")
    with pytest.raises(caps.CapError):
        caps.CappedLedger(path)


def test_the_anthropic_stop_counts_this_registrations_lines_and_reservations(tmp_path):
    path = ledger_file(tmp_path, [{"model": "claude-fable-5-1", "usd": 160.0},
                                  {"model": "gpt-6-astra", "usd": 5.0}])
    led = caps.CappedLedger(path)
    assert led.provider_spent["anthropic"] == pytest.approx(160.0)
    assert led.new_spend() == pytest.approx(165.0)
    claude = led.view("claude-sonnet-5-5")
    claude.reserve("k1", 6.0)
    with pytest.raises(cr.CeilingReached, match="anthropic stop"):
        claude.reserve("k2", 4.5)
    led.view("gpt-6.1-sol").reserve("k3", 50.0)
    claude.release("k1")
    claude.reserve("k2", 9.9)


def test_the_registration_stop_holds_across_providers(tmp_path):
    path = ledger_file(tmp_path, [{"model": "gpt-6-astra", "usd": 299.0}])
    led = caps.CappedLedger(path)
    assert led.ceiling == pytest.approx(386.09)
    with pytest.raises(cr.CeilingReached, match="registration stop"):
        led.view("gpt-6.1-sol").reserve("k", 1.5)


def test_recorded_spend_moves_the_provider_total(tmp_path):
    led = caps.CappedLedger(ledger_file(tmp_path))
    v = led.view("claude-sonnet-5-5")
    v.reserve("k", 2.0)
    v.record("k", {"model": "claude-sonnet-5-5", "usd": 1.25})
    assert led.provider_spent["anthropic"] == pytest.approx(1.25)
    assert v.reserved == {} and v.spent == pytest.approx(caps.BASELINE_USD + 1.25)


def test_a_credit_refusal_in_the_sealed_coder_runner_is_no_attempt(tmp_path):
    replies = [{"status": 400, "body": CREDIT},
               {"status": 200, "model_returned": "claude-sonnet-5-5", "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 5},
                "text": json.dumps({"record_id": "r1", "rows": [{"row_id": "a"}]})}]
    led = caps.CappedLedger(ledger_file(tmp_path))
    runner = cr3.Runner("claude-sonnet-5-5", "P", SCHEMA, tmp_path / "store",
                        led.view("claude-sonnet-5-5"), send=lambda body: replies.pop(0),
                        sleep=lambda s: None)
    first = runner.one("r1.1", PACKET)
    assert first["state"] == "pending" and led.reserved == {}
    assert not [p for p in (tmp_path / "store").glob("r1.1.*.json") if ".attempt" not in p.name]
    second = runner.one("r1.1", PACKET)
    assert second["state"] == "accepted"
    assert [a["attempt"] for a in second["attempts"]] == [1]
    assert led.provider_spent["anthropic"] > 0
