# /// script
# requires-python = ">=3.12"
# dependencies = ["anthropic==1.13.0", "httpx==0.28.1", "jsonschema==4.26.0"]
# ///
"""The two judges of Amendment 4 (AMENDMENT_04_two_judges.md): Claude Fable 5.1
(`claude-fable-5-1`, Anthropic Messages API) and GPT-6 Astra (`gpt-6-astra`, OpenAI Responses
API). Second version of scripts/judge.py (sealed, unchanged and imported: the system instruction,
the request, the answer check, the routing conditions of Amendment 3 item 2, the calibration
order and the pages' answer order).

Each judge receives, as its own request, the frozen judge prompt and schema with the same system
instruction as the first version, never the other judge's answer; no tools; sampling and
reasoning at the vendor's defaults; structured output with the frozen schema; at most
MAX_OUTPUT output tokens, reasoning included; the returned model string recorded.

Attempts. At most two per judge and row. An attempt that returns no valid answer (a transport
error, an HTTP error, a refusal, a truncated response, a malformed or off-schema answer) counts.
HTTP 402 and 429 are not attempts: the request stays `pending` and is sent again on a later run
of the stage (`ACCOUNT_SIDE`).

Spend. From the usage each API reports, at the list prices of PRICE, read from the vendors' own
pricing pages on 14 October 2026 (Anthropic: platform.claude.com/docs/en/about-claude/pricing;
OpenAI: platform.openai.com/docs/pricing, standard tier, short context), reasoning billed as
output. Before each request its bound (every character of the system instruction and the request
as new input at the preflight's characters per token, MIN_RATIO, plus MAX_OUTPUT at the output
price) is reserved against the stage's ceiling.

Order. Rows are sent in the order of `random.Random(SEND_SEED).shuffle` over the rows in order of
row id, both judges' requests for a row together (`send_order`).

Routing (`route_pair`, Amendment 4 item 2). A row is decided without the author only when both
judges' answers are accepted, they make the same choice, and neither meets a condition of
Amendment 3 item 2 (judge.route). Otherwise it goes to the author with every reason that holds,
among them `judges_differ` and `not_judged_by_both` (a request not sent because of the ceiling, or
still pending).
"""

import datetime
import hashlib
import json
import pathlib
import random
import threading
import time

import anthropic
import httpx

import coding_runner as cr
import judge as jd

FABLE, ASTRA = "claude-fable-5-1", "gpt-6-astra"
JUDGES = (FABLE, ASTRA)
MAX_OUTPUT = 8_192
SEND_SEED = 20261028
ACCOUNT_SIDE = (402, 429)
OPENAI_ENDPOINT = "https://api.openai.com/v1/responses"
PRICE = {FABLE: {"new": 10.00, "cache_write": 12.50, "cached": 0.25, "output": 50.00},
         ASTRA: {"new": 10.00, "cached": 1.00, "output": 50.00}}
MIN_RATIO = {FABLE: 1.98, ASTRA: 3.11}


def now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="milliseconds")


def fable_body(system: str, schema: dict, request: dict) -> dict:
    return {"model": FABLE, "max_tokens": MAX_OUTPUT,
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": json.dumps(request, ensure_ascii=False)}],
            "output_config": {"format": {"type": "json_schema", "schema": schema}}}


def astra_body(system: str, schema: dict, request: dict) -> dict:
    return {"model": ASTRA, "instructions": system,
            "input": json.dumps(request, ensure_ascii=False), "tools": [], "store": False,
            "max_output_tokens": MAX_OUTPUT,
            "text": {"format": {"type": "json_schema", "name": "judge", "strict": True,
                                "schema": schema}}}


def call_fable(client, body: dict) -> dict:
    try:
        with client.messages.stream(**body) as stream:
            message = stream.get_final_message()
    except anthropic.APIStatusError as e:
        return {"status": e.status_code, "body": str(e)[:2000]}
    raw = message.to_dict()
    text = next((b.get("text") for b in raw.get("content", []) if b.get("type") == "text"), None)
    stop = raw.get("stop_reason")
    return {"status": 200, "model_returned": raw.get("model"), "stop_reason": stop,
            "usage": raw.get("usage") or {}, "text": text if stop == "end_turn" else None,
            "request_id": raw.get("id")}


def call_astra(client: httpx.Client, key: str, body: dict) -> dict:
    r = client.post(OPENAI_ENDPOINT, json=body, headers={"Authorization": f"Bearer {key}"})
    if r.status_code != 200:
        return {"status": r.status_code, "body": r.text[:2000]}
    data = r.json()
    texts = [c["text"] for item in data.get("output", []) if item.get("type") == "message"
             for c in item.get("content", []) if c.get("type") == "output_text"]
    status = data.get("status")
    return {"status": 200, "model_returned": data.get("model"), "stop_reason": status,
            "usage": data.get("usage") or {},
            "text": texts[0] if len(texts) == 1 and status == "completed" else None,
            "request_id": data.get("id")}


def usd(model: str, usage: dict) -> float:
    p = PRICE[model]
    if model == FABLE:
        cost = (usage.get("input_tokens", 0) * p["new"]
                + (usage.get("cache_creation_input_tokens", 0) or 0) * p["cache_write"]
                + (usage.get("cache_read_input_tokens", 0) or 0) * p["cached"]
                + usage.get("output_tokens", 0) * p["output"])
    else:
        cached = (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)
        cost = ((usage.get("input_tokens", 0) - cached) * p["new"] + cached * p["cached"]
                + usage.get("output_tokens", 0) * p["output"])
    return cost / 1e6


def bound(model: str, system: str, request: dict) -> float:
    chars = len(system) + len(json.dumps(request, ensure_ascii=False))
    p = PRICE[model]
    return (chars / MIN_RATIO[model] * p["new"] + MAX_OUTPUT * p["output"]) / 1e6


def request_key(model: str, system: str, schema: dict, request: dict) -> str:
    blob = json.dumps({"model": model, "system": hashlib.sha256(system.encode()).hexdigest(),
                       "schema": schema, "request": request}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()[:24]


def send_order(row_ids: list[str], seed: int = SEND_SEED) -> list[str]:
    order = sorted(row_ids)
    random.Random(seed).shuffle(order)
    return order


class Judge:
    """One judge's requests, with checkpoints, the attempt rule and the ceiling."""

    def __init__(self, model: str, system: str, schema: dict, store: pathlib.Path,
                 ledger: cr.Ledger, send, persist=lambda: None, sleep=time.sleep):
        self.model, self.system, self.schema, self.store = model, system, schema, store
        self.ledger, self.send, self.persist, self.sleep = ledger, send, persist, sleep
        self.body = fable_body if model == FABLE else astra_body
        store.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def attempts_so_far(self, row_id: str, key: str) -> list[dict]:
        return [json.loads(p.read_text()) for p in
                sorted(self.store.glob(f"{row_id}.{key}.attempt*.json"))
                if json.loads(p.read_text()).get("counts_as_attempt")]

    def one(self, row_id: str, request: dict) -> dict:
        key = request_key(self.model, self.system, self.schema, request)
        final = self.store / f"{row_id}.{key}.json"
        if final.exists():
            return json.loads(final.read_text())
        done = self.attempts_so_far(row_id, key)
        body = self.body(self.system, self.schema, request)
        result = None
        for attempt in range(len(done) + 1, 3):
            self.ledger.reserve(f"{self.model}:{key}:{attempt}",
                                bound(self.model, self.system, request))
            started = now()
            try:
                got = self.send(body)
            except Exception as e:  # a transport defect is an attempt without an answer
                got = {"status": None, "body": f"{type(e).__name__}: {e}"[:2000]}
            got.update({"model_requested": self.model, "started_utc": started,
                        "finished_utc": now(), "attempt": attempt})
            if got["status"] in ACCOUNT_SIDE:
                self.ledger.release(f"{self.model}:{key}:{attempt}")
                got["counts_as_attempt"] = False
                (self.store / f"{row_id}.{key}.refused.{started}.json").write_text(
                    json.dumps(got, ensure_ascii=False))
                self.persist()
                return {"row_id": row_id, "model": self.model, "key": key, "state": "pending",
                        "refused_status": got["status"]}
            got["counts_as_attempt"] = True
            if got["status"] == 200:
                got["usd"] = usd(self.model, got.get("usage") or {})
                self.ledger.record(f"{self.model}:{key}:{attempt}", {
                    "request_key": key, "name": row_id, "model": self.model, "attempt": attempt,
                    "model_returned": got.get("model_returned"), "usage": got.get("usage"),
                    "usd": got["usd"], "finished_utc": got["finished_utc"]})
                data, errors = jd.check(got.get("text"), self.schema, row_id)
            else:
                self.ledger.release(f"{self.model}:{key}:{attempt}")
                data, errors = None, [f"http {got['status']}"]
            got["errors"] = errors
            (self.store / f"{row_id}.{key}.attempt{attempt}.json").write_text(
                json.dumps(got, ensure_ascii=False))
            self.persist()
            done.append(got)
            if data is not None:
                result = {"row_id": row_id, "model": self.model, "key": key,
                          "state": "accepted", "decision": data}
                break
        if result is None:
            result = {"row_id": row_id, "model": self.model, "key": key, "state": "failed",
                      "decision": None}
        result["attempts"] = [{k: a.get(k) for k in ("attempt", "status", "stop_reason",
                                                     "model_returned", "usd", "errors")}
                              for a in done]
        partial = final.with_suffix(".partial")
        partial.write_text(json.dumps(result, ensure_ascii=False))
        partial.rename(final)
        self.persist()
        return result


def route_pair(task: str, results: dict[str, dict | None], gates: list[bool],
               files_text: str) -> list[str]:
    """Amendment 4 item 2. `results[judge]`: the judge's stored result, or None when its
    request was not sent (the ceiling)."""
    reasons = []
    for judge in JUDGES:
        r = results.get(judge)
        if r is None or r.get("state") == "pending":
            reasons.append("not_judged_by_both")
            continue
        reasons += [f"{judge}:{x}" for x in jd.route(task, r, gates, files_text)]
    if all((results.get(j) or {}).get("state") == "accepted" for j in JUDGES):
        a, b = (results[j]["decision"]["choice"] for j in JUDGES)
        if a != b:
            reasons.append("judges_differ")
    return sorted(set(reasons))
