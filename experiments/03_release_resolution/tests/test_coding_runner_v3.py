import json
import pathlib

import coding_runner as cr
import coding_runner_v3 as cr3

HERE = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = json.loads((HERE / "prompts" / "output_schema.json").read_text())


def packet(rid="a1"):
    return {"record_id": "r1", "title": "T", "files": [],
            "rows": [{"row_id": rid, "side": "pqtl", "name": "not stated", "candidates": []}],
            "accession_table_rows": []}


def answer(rid="a1"):
    return {"record_id": "r1", "rows": [{
        "row_id": rid, "identified_releases": [], "roles": [], "ancestry": [],
        "attribution_state": "unresolved", "unresolved_reasons": ["attribution_unresolved"],
        "decisive_evidence": [], "count_evidence": [], "abstract_transition": "none",
        "attribution_passage": None, "note": "n"}]}


class Parsed:
    """A streamed structured-output message: no `_request_id`, a `to_dict`."""

    def __init__(self, text):
        self.text = text

    def to_dict(self):
        return {"id": "msg_1", "model": "claude-sonnet-5-5", "stop_reason": "end_turn",
                "content": [{"type": "thinking", "thinking": ""}, {"type": "text", "text": self.text}],
                "usage": {"input_tokens": 5, "output_tokens": 7}}

    def __getattr__(self, name):
        raise AttributeError(name)


class Stream:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self.message


class Client:
    def __init__(self, text):
        self.messages = self
        self.text = text

    def stream(self, **body):
        return Stream(Parsed(self.text))


def test_a_parsed_message_is_read_without_a_request_id():
    got = cr3.call_claude(Client(json.dumps(answer())), {"model": "x"})
    assert got["status"] == 200 and got["request_id"] == "msg_1"
    assert got["usage"] == {"input_tokens": 5, "output_tokens": 7}
    assert json.loads(got["text"]) == answer()


def test_an_exception_in_one_request_leaves_it_pending_and_the_pass_goes_on(tmp_path):
    ledger = cr.Ledger(tmp_path / "ledger.jsonl")

    def send(body):
        if "bad" in body["messages"][0]["content"]:
            raise ValueError("defect")
        return cr3.call_claude(Client(json.dumps(answer())), body)

    r = cr3.Runner(cr.CLAUDE, "p", SCHEMA, tmp_path / "store", ledger, send=send,
                   sleep=lambda s: None, workers=2)
    bad = packet()
    bad["title"] = "bad"
    done = r.run([("good.1", packet()), ("bad.1", bad)])
    assert done["states"] == {"accepted": 1, "failed": 0, "pending": 1}
    assert done["errors"][0]["name"] == "bad.1" and not ledger.reserved
    assert len((tmp_path / "ledger.jsonl").read_text().splitlines()) == 1
