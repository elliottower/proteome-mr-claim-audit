import json
import pathlib

import pytest

import coding_runner as cr
import coding_runner_v2 as cr2

HERE = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = json.loads((HERE / "prompts" / "output_schema.json").read_text())
PROMPT = "p" * 74_562


def packet(chars=18_000):
    return {"record_id": "r1", "title": "T", "files": [{"file_id": "abstract", "kind": "abstract",
                                                      "text": "x" * chars}],
            "rows": [{"row_id": "a1", "side": "pqtl", "name": "not stated", "candidates": []}],
            "accession_table_rows": []}


def answer(p):
    return {"record_id": p["record_id"], "rows": [{
        "row_id": "a1", "identified_releases": [], "roles": [], "ancestry": [],
        "attribution_state": "unresolved", "unresolved_reasons": ["attribution_unresolved"],
        "decisive_evidence": [], "count_evidence": [], "abstract_transition": "none",
        "attribution_passage": None, "note": "n"}]}


def test_the_bound_covers_the_preflight_ratios_as_new_input_plus_maximum_output():
    p = packet()
    chars = len(PROMPT) + len(json.dumps(p))
    for model, measured in ((cr.CLAUDE, 1.98), (cr.SOL, 3.11)):
        worst = (chars / measured * 2.00 + 128_000 * 10.00) / 1e6
        assert cr2.bound(model, PROMPT, p) >= worst
        assert cr2.bound(model, PROMPT, p) > cr.bound(model, PROMPT, p)


def test_claude_cache_reads_are_priced_at_the_vendor_list_price():
    assert cr.PRICE[cr.CLAUDE]["cached"] == pytest.approx(0.20)
    assert cr.usd(cr.CLAUDE, {"cache_read_input_tokens": 1_000_000}) == pytest.approx(0.20)


def test_the_second_version_answers_as_the_first(tmp_path):
    p = packet(100)
    reply = {"status": 200, "model_returned": "m", "stop_reason": "end_turn",
             "usage": {"input_tokens": 10, "output_tokens": 5}, "text": json.dumps(answer(p))}
    results = []
    for mod, sub in ((cr, "a"), (cr2, "b")):
        (tmp_path / sub).mkdir()
        ledger = cr.Ledger(tmp_path / sub / "ledger.jsonl")
        r = mod.Runner(cr.CLAUDE, PROMPT, SCHEMA, tmp_path / sub / "store", ledger,
                       send=lambda body: dict(reply), sleep=lambda s: None)
        results.append(r.one("r1.1", p))
        entry = json.loads((tmp_path / sub / "ledger.jsonl").read_text())
        assert set(entry) >= {"request_key", "usd", "usage", "model_returned"}
    assert results[0] == results[1]


def test_the_second_version_stops_where_its_own_bound_would_cross(tmp_path):
    p = packet()
    b1, b2 = cr.bound(cr.SOL, PROMPT, p), cr2.bound(cr.SOL, PROMPT, p)
    ledger = cr.Ledger(tmp_path / "ledger.jsonl", ceiling=b1 + (b2 - b1) / 2)
    sent = []
    r = cr2.Runner(cr.SOL, PROMPT, SCHEMA, tmp_path / "store", ledger,
                   send=lambda body: sent.append(body), sleep=lambda s: None)
    with pytest.raises(cr.CeilingReached):
        r.one("r1.1", p)
    assert sent == []
