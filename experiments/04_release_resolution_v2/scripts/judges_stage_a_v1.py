# /// script
# requires-python = ">=3.12"
# dependencies = ["anthropic==1.13.0", "httpx==0.28.1", "jsonschema==4.26.0"]
# ///
"""The judges of the second registration's stage A recode (the first registration's
Amendments 3 and 4, carried over by PREREG.md item 4, with this registration's seeds). No model
is called here; scripts/modal_judges_stage_a_v1.py sends the requests through scripts/judge_v4.py.

Rows judged (`tasks`): every disagreement left after the settling of Amendment 7 (task
`disagreement`), and an audit sample of the rows on which the coders agree (task `audit`): 10%,
at least 30, all if fewer, drawn by adjudication_pages.audit_draw (Paper 1's sealed draw) over
the agreed rows in packet order with seed AUDIT_SEED. Settled rows are neither.

Requests (`requests`): judge.judge_request (sealed, unchanged): the task, the record, the row as
the coders received it, every file of the row's packet, and the answers with their gate verdicts
(the gate of item 2); for a disagreement the two answers as Answer 1 and Answer 2, in an order
drawn per row by adjudication_pages.first_is_a with seed BLIND_SEED, never naming the coder.
System instruction: judge.system_text over the frozen judge prompt, coding prompt v3 (the coders'
prompt under this registration) and the dictionary definitions.

Send order (`send_order`): judge_v2.send_order with seed SEND_SEED, both judges' requests for a
row together. Routing (`route`): judge_v2.route_pair (Amendment 4 item 2). Calibration
(`calibration`): per task, the rows decided alone, judge.calibration_order with the task's seed;
the author marks the first 20.
"""

import adjudication_pages as ap
import judge as jd
import judge_v2 as j2

MODELS = ("claude-sonnet-5-5", "gpt-6.1-sol")
BLIND_SEED = 20261035
AUDIT_SEED = 20261036
SEND_SEED = 20261037
CALIBRATION_SEEDS = {"disagreement": 20261038, "audit": 20261039, "escalated": 20261040}
PAGE_SEED = 20261041


def as_queue_row(packet_row: dict) -> dict:
    return {"row_id": packet_row["row_id"], "side": packet_row["side"],
            "name_as_written": packet_row["name"],
            "outcomes_as_written": packet_row.get("outcomes_as_written", []),
            "candidates": packet_row["candidates"]}


def blinded(row_id: str) -> tuple[str, str]:
    a, b = MODELS
    return (a, b) if ap.first_is_a(row_id, BLIND_SEED) else (b, a)


def tasks(order: list[str], agreed: list[str], disagreements: list[str]) -> dict:
    agreed_in_order = [r for r in order if r in set(agreed)]
    return {"disagreement": [r for r in order if r in set(disagreements)],
            "audit": ap.audit_draw(agreed_in_order, AUDIT_SEED)}


def requests(task_rows: dict, packet_of: dict, answers: dict, gates: dict) -> list[tuple]:
    out = []
    for task in ("disagreement", "audit"):
        for rid in task_rows[task]:
            p = packet_of[rid]
            q = as_queue_row(next(r for r in p["rows"] if r["row_id"] == rid))
            if task == "disagreement":
                pairs = [(answers[m].get(rid), gates[m].get(rid, False)) for m in blinded(rid)]
            else:
                pairs = [(answers[MODELS[0]][rid], gates[MODELS[0]][rid])]
            out.append((task, rid, jd.judge_request(task, p, q, pairs), [g for _, g in pairs]))
    return out


def send_order(row_ids: list[str]) -> list[str]:
    return j2.send_order(row_ids, SEND_SEED)


def route(task: str, results: dict, gates: list[bool], files_text: str) -> list[str]:
    return j2.route_pair(task, results, gates, files_text)


def calibration(lone: list[str], task: str) -> list[str]:
    return jd.calibration_order(lone, CALIBRATION_SEEDS[task])
