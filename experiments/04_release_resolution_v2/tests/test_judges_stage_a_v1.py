import math
import random

import adjudication_pages as ap
import judges_stage_a_v1 as js


def packet(rid):
    return {"record_id": "rec", "title": "t",
            "files": [{"file_id": "abstract", "kind": "abstract", "text": "Text."}],
            "rows": [{"row_id": rid, "side": "outcome", "name": "not stated",
                      "outcomes_as_written": ["gout"], "candidates": ["FinnGen R10"]}],
            "accession_table_rows": []}


def test_the_seeds_are_this_registrations():
    assert (js.BLIND_SEED, js.AUDIT_SEED, js.SEND_SEED, js.PAGE_SEED) == (
        20261035, 20261036, 20261037, 20261041)
    assert js.CALIBRATION_SEEDS == {"disagreement": 20261038, "audit": 20261039,
                                    "escalated": 20261040}


def test_the_audit_draws_ten_percent_of_agreed_rows_in_packet_order_and_excludes_others():
    order = [f"r{i:03d}" for i in range(500)]
    agreed = order[:400]
    t = js.tasks(order, list(reversed(agreed)), order[450:])
    assert len(t["audit"]) == max(30, math.ceil(0.1 * 400))
    assert t["audit"] == ap.audit_draw(agreed, 20261036)
    assert set(t["audit"]) <= set(agreed)
    assert t["disagreement"] == order[450:]
    assert not set(t["disagreement"]) & set(t["audit"])


def test_a_disagreement_shows_both_answers_blinded_by_the_new_seed():
    a, b = js.MODELS
    mark = {a: "first coder", b: "second coder"}
    answers = {m: {"x1": {"from": mark[m]}} for m in (a, b)}
    gates = {a: {"x1": True}, b: {"x1": False}}
    [(task, rid, req, g)] = js.requests({"disagreement": ["x1"], "audit": []},
                                        {"x1": packet("x1")}, answers, gates)
    first = a if random.Random("20261035:x1").random() < 0.5 else b
    assert req["answers"][0]["answer"] == {"from": mark[first]}
    assert g == [gates[first]["x1"], gates[a if first == b else b]["x1"]]
    assert req["row"] == {"row_id": "x1", "side": "outcome", "name": "not stated",
                          "outcomes_as_written": ["gout"], "candidates": ["FinnGen R10"]}
    assert "claude" not in str(req) and "gpt" not in str(req)


def test_an_audit_request_carries_the_agreed_answer_and_its_gate():
    a, b = js.MODELS
    [(task, rid, req, g)] = js.requests({"disagreement": [], "audit": ["x1"]},
                                        {"x1": packet("x1")}, {a: {"x1": {"k": 1}}, b: {}},
                                        {a: {"x1": True}, b: {}})
    assert task == "audit" and req["agreed_answer"] == {"answer": {"k": 1}, "gate": True}


def test_send_and_calibration_orders_shuffle_sorted_ids_by_their_seeds():
    ids = [f"{i:04d}" for i in range(50)]
    s = sorted(ids)
    random.Random(20261037).shuffle(s)
    assert js.send_order(list(reversed(ids))) == s
    c = sorted(ids)
    random.Random(20261039).shuffle(c)
    assert js.calibration(list(reversed(ids)), "audit") == c
