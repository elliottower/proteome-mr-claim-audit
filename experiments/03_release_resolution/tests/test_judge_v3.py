import json
import pathlib

import coding_runner as cr
import judge as jd
import judge_v2 as j2
import judge_v3 as j3

HERE = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = json.loads((HERE / "prompts" / "judge_schema.json").read_text())


def decision(conf):
    return {"row_id": "r1", "choice": "correct", "confidence": conf, "needs_human": False,
            "reason": "x", "quotation": ""}


def keywords(schema):
    found = set()
    if isinstance(schema, dict):
        for k, v in schema.items():
            found.add(k)
            found |= keywords(v)
    elif isinstance(schema, list):
        for v in schema:
            found |= keywords(v)
    return found


def test_the_anthropic_request_schema_has_no_unsupported_keyword():
    body = j3.fable_body("S", SCHEMA, {"task": "audit"})
    sent = body["output_config"]["format"]["schema"]
    assert not keywords(sent) & set(j3.UNSUPPORTED)
    assert "minimum" in keywords(SCHEMA) and "maximum" in keywords(SCHEMA)
    assert j3.removed_keywords(SCHEMA) == ["/properties/confidence/minimum",
                                           "/properties/confidence/maximum"]


def test_only_the_constraints_are_removed():
    sent = j3.transport_schema(SCHEMA)
    assert sent["required"] == SCHEMA["required"] and sent["additionalProperties"] is False
    assert sent["properties"]["choice"] == SCHEMA["properties"]["choice"]
    assert sent["properties"]["confidence"] == {"type": "number"}


def test_a_confidence_outside_zero_to_one_fails_local_validation():
    data, errors = jd.check(json.dumps(decision(1.5)), SCHEMA, "r1")
    assert data is None and errors and errors[0].startswith("schema")
    assert jd.check(json.dumps(decision(0.9)), SCHEMA, "r1")[0] is not None


def test_the_fable_judge_sends_the_transport_schema_and_validates_against_the_full_one(tmp_path):
    sent = []

    def send(body):
        sent.append(body)
        return {"status": 200, "model_returned": j2.FABLE, "stop_reason": "end_turn",
                "usage": {"input_tokens": 1, "output_tokens": 1},
                "text": json.dumps(decision(1.5 if len(sent) == 1 else 0.7))}

    ledger = cr.Ledger(tmp_path / "l.jsonl")
    j = j3.Judge(j2.FABLE, "S", SCHEMA, tmp_path / "f", ledger, send, sleep=lambda s: None)
    got = j.one("r1", {"task": "audit"})
    assert not keywords(sent[0]["output_config"]["format"]["schema"]) & set(j3.UNSUPPORTED)
    assert got["state"] == "accepted" and got["attempts"][0]["errors"][0].startswith("schema")


def test_astra_requests_are_unchanged():
    j = j3.Judge(j2.ASTRA, "S", SCHEMA, pathlib.Path("/tmp/unused_astra"), cr.Ledger(
        pathlib.Path("/tmp/unused_astra_ledger.jsonl")), lambda b: None)
    assert j.body("S", SCHEMA, {"x": 1}) == j2.astra_body("S", SCHEMA, {"x": 1})
