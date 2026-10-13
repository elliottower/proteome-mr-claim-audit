# /// script
# requires-python = ">=3.12"
# dependencies = ["anthropic==1.13.0", "httpx==0.28.1", "jsonschema==4.26.0"]
# ///
"""The model requests of the release-resolution coding (PREREG.md, §Study design, Checks;
prompts/api_framing_v2.md; Amendment 1, the ceiling). Shared by every pass: SA1, the full-text
pass, the control-only papers and the removed-chunk diagnostic.

Framing (prompts/api_framing_v2.md). Claude Sonnet 5.5 (`claude-sonnet-5-5`) through the Messages
API: the fixed prompt as `system`, one text block with `cache_control` of type `ephemeral`; the
packet as one `user` message of JSON text; structured output with the schema
(`output_config.format`, type `json_schema`); no tools; sampling, thinking and effort left at the
API's defaults; `max_tokens` 128,000, streamed. GPT-6.1 Sol (`gpt-6.1-sol`) through the Responses
API: `instructions` the fixed prompt, `input` the packet as JSON text, `text.format` of type
`json_schema`, strict, with the schema; `tools` empty; `store` false; sampling and reasoning left
at the API's defaults; `max_output_tokens` 128,000. No request carries an e-mail address. The
model string each API returns is recorded with every response.

Answers. An answer is accepted when it parses, fits `prompts/output_schema.json`, names the
packet's `record_id` and returns every packet row once, in the packet's order. An answer that does
not is requested once more under the same framing; a second failure leaves the packet's rows
unresolved and is counted (`failed`). A transport failure (no response, HTTP 429 or 5xx) is not an
answer: it is retried with backoff up to HTTP_TRIES and, if it still fails, the request stays
pending and is sent again when the pass is resumed; no request is dropped.

Checkpoints. Every exchange is written to the store as soon as it ends, under the pass, the model
and the request key (the sha256 of model, fixed prompt, schema and packet); a request whose
accepted or failed answer is stored is not sent again, so a stopped pass resumes.

Ceiling. A spend ledger holds the cost of every request made in the stage, from the usage each API
reports, at the prices in PRICE. Before a request is sent, its bound (the packet and the fixed
prompt as new input at the smallest measured characters per token, and the maximum output) is
reserved; a request whose bound would take the spent and reserved total above the ceiling is not
sent, and the pass stops and reports. The reservation is replaced by the measured cost when the
response arrives.
"""

import concurrent.futures
import datetime
import hashlib
import json
import pathlib
import threading
import time

import anthropic
import httpx
import jsonschema

CLAUDE = "claude-sonnet-5-5"
SOL = "gpt-6.1-sol"
MODELS = (CLAUDE, SOL)
MAX_OUTPUT = 128_000
CEILING_USD = 350.0
SOL_ENDPOINT = "https://api.openai.com/v1/responses"
HTTP_TRIES = 6
# USD per million tokens. Claude Sonnet 5.5: the vendor's list prices (input 2, output 10, cache
# read 0.20, cache write 1.25 times input). GPT-6.1 Sol: the plan's cost table (2, 0.10, 10).
PRICE = {CLAUDE: {"new": 2.00, "cache_write": 2.50, "cached": 0.20, "output": 10.00},
         SOL: {"new": 2.00, "cached": 0.10, "output": 10.00}}
# The smallest measured characters per token (outputs/token_ratio_2026-10-10.json).
MIN_RATIO = {CLAUDE: 2.33, SOL: 3.69}


class CeilingReached(Exception):
    """The next request's bound would take the stage's spend above the ceiling."""


class RunnerError(Exception):
    """A pass is asked of an unknown model, or a stored exchange is malformed."""


def now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="milliseconds")


def request_key(model: str, prompt: str, schema: dict, packet: dict) -> str:
    blob = json.dumps({"model": model, "prompt": hashlib.sha256(prompt.encode()).hexdigest(),
                       "schema": schema, "packet": packet}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()[:24]


def claude_body(prompt: str, schema: dict, packet: dict) -> dict:
    return {"model": CLAUDE, "max_tokens": MAX_OUTPUT,
            "system": [{"type": "text", "text": prompt, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": json.dumps(packet, ensure_ascii=False)}],
            "output_config": {"format": {"type": "json_schema", "schema": schema}}}


def sol_body(prompt: str, schema: dict, packet: dict) -> dict:
    return {"model": SOL, "instructions": prompt,
            "input": json.dumps(packet, ensure_ascii=False), "tools": [], "store": False,
            "max_output_tokens": MAX_OUTPUT,
            "text": {"format": {"type": "json_schema", "name": "release_coding", "strict": True,
                                "schema": schema}}}


def usd(model: str, usage: dict) -> float:
    p = PRICE[model]
    if model == CLAUDE:
        cost = (usage.get("input_tokens", 0) * p["new"]
                + usage.get("cache_creation_input_tokens", 0) * p["cache_write"]
                + usage.get("cache_read_input_tokens", 0) * p["cached"]
                + usage.get("output_tokens", 0) * p["output"])
    else:
        cached = (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)
        cost = ((usage.get("input_tokens", 0) - cached) * p["new"] + cached * p["cached"]
                + usage.get("output_tokens", 0) * p["output"])
    return cost / 1e6


def bound(model: str, prompt: str, packet: dict) -> float:
    chars = len(prompt) + len(json.dumps(packet, ensure_ascii=False))
    p = PRICE[model]
    return (chars / MIN_RATIO[model] * p["new"] + MAX_OUTPUT * p["output"]) / 1e6


def check_answer(text: str, schema: dict, packet: dict) -> tuple[dict | None, list[str]]:
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        return None, [f"parse: {e}"]
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        return None, [f"schema: {e.message}"]
    errors = []
    if data["record_id"] != packet["record_id"]:
        errors.append("record_id differs from the packet's")
    if [r["row_id"] for r in data["rows"]] != [r["row_id"] for r in packet["rows"]]:
        errors.append("rows are not the packet's rows in the packet's order")
    return (data if not errors else None), errors


class Ledger:
    """The stage's spend, one JSON line per request with a measured cost, and the reservations
    of requests in flight. `persist` is called after every write (the volume commit)."""

    def __init__(self, path: pathlib.Path, ceiling: float = CEILING_USD, persist=lambda: None):
        self.path, self.ceiling, self.persist = path, ceiling, persist
        self.lock = threading.Lock()
        self.reserved: dict[str, float] = {}
        self.spent = 0.0
        if path.exists():
            for line in path.read_text().splitlines():
                if line.strip():
                    self.spent += json.loads(line)["usd"]

    def reserve(self, key: str, amount: float) -> None:
        with self.lock:
            if self.spent + sum(self.reserved.values()) + amount > self.ceiling:
                raise CeilingReached(f"spent {self.spent:.2f}, reserved "
                                     f"{sum(self.reserved.values()):.2f}, next bound "
                                     f"{amount:.2f}, ceiling {self.ceiling:.2f}")
            self.reserved[key] = amount

    def record(self, key: str, entry: dict) -> None:
        with self.lock:
            self.reserved.pop(key, None)
            self.spent += entry["usd"]
            with self.path.open("a") as fh:
                fh.write(json.dumps(entry) + "\n")
            self.persist()

    def release(self, key: str) -> None:
        with self.lock:
            self.reserved.pop(key, None)


def call_claude(client, body: dict) -> dict:
    with client.messages.stream(**body) as stream:
        message = stream.get_final_message()
    text = next((b.text for b in message.content if b.type == "text"), None)
    return {"status": 200, "model_returned": message.model, "stop_reason": message.stop_reason,
            "usage": message.usage.to_dict(), "text": text, "request_id": message._request_id}


def call_sol(client: httpx.Client, key: str, body: dict) -> dict:
    r = client.post(SOL_ENDPOINT, json=body, headers={"Authorization": f"Bearer {key}"})
    if r.status_code != 200:
        return {"status": r.status_code, "body": r.text[:4000]}
    parsed = r.json()
    texts = [c["text"] for item in parsed.get("output", []) if item.get("type") == "message"
             for c in item.get("content", []) if c.get("type") == "output_text"]
    return {"status": 200, "model_returned": parsed.get("model"),
            "stop_reason": parsed.get("status"), "usage": parsed.get("usage") or {},
            "text": texts[0] if len(texts) == 1 else None, "request_id": parsed.get("id")}


def transport(model: str, send, sleep=time.sleep) -> dict:
    """One answer from the API, retrying a transport failure; None when every try failed."""
    last = None
    for attempt in range(1, HTTP_TRIES + 1):
        try:
            got = send()
        except (anthropic.APIConnectionError, anthropic.RateLimitError,
                anthropic.InternalServerError, httpx.HTTPError) as e:
            got = {"status": None, "body": f"{type(e).__name__}: {e}"}
        except anthropic.APIStatusError as e:
            got = {"status": e.status_code, "body": str(e)[:4000]}
        got["http_try"] = attempt
        if got["status"] == 200:
            return got
        last = got
        if got["status"] is not None and got["status"] < 500 and got["status"] != 429:
            return got
        sleep(min(120, 2 ** attempt))
    return last


class Runner:
    """Sends the packets of one pass to one model, with checkpoints and the ceiling."""

    def __init__(self, model: str, prompt: str, schema: dict, store: pathlib.Path,
                 ledger: Ledger, send=None, persist=lambda: None, workers: int = 8,
                 sleep=time.sleep):
        if model not in MODELS:
            raise RunnerError(f"unknown model {model}")
        self.model, self.prompt, self.schema = model, prompt, schema
        self.store, self.ledger, self.persist, self.workers = store, ledger, persist, workers
        self.send, self.sleep = send, sleep
        self.stopped = threading.Event()
        store.mkdir(parents=True, exist_ok=True)

    def body(self, packet: dict) -> dict:
        return (claude_body if self.model == CLAUDE else sol_body)(self.prompt, self.schema,
                                                                    packet)

    def one(self, name: str, packet: dict) -> dict:
        key = request_key(self.model, self.prompt, self.schema, packet)
        final = self.store / f"{name}.{key}.json"
        if final.exists():
            return json.loads(final.read_text())
        attempts = []
        for attempt in (1, 2):
            if self.stopped.is_set():
                raise CeilingReached("the pass stopped at the ceiling")
            try:
                self.ledger.reserve(f"{key}:{attempt}", bound(self.model, self.prompt, packet))
            except CeilingReached:
                self.stopped.set()
                raise
            started = now()
            got = transport(self.model, lambda: self.send(self.body(packet)), self.sleep)
            got.update({"attempt": attempt, "started_utc": started, "finished_utc": now(),
                        "model_requested": self.model})
            (self.store / f"{name}.{key}.attempt{attempt}.json").write_text(
                json.dumps(got, ensure_ascii=False))
            if got["status"] != 200:
                self.ledger.release(f"{key}:{attempt}")
                self.persist()
                return {"name": name, "key": key, "state": "pending", "attempts": attempts + [
                    {k: got.get(k) for k in ("status", "http_try", "body")}]}
            cost = usd(self.model, got["usage"])
            self.ledger.record(f"{key}:{attempt}", {
                "request_key": key, "name": name, "model": self.model, "attempt": attempt,
                "model_returned": got["model_returned"], "usage": got["usage"], "usd": cost,
                "finished_utc": got["finished_utc"]})
            data, errors = check_answer(got.get("text"), self.schema, packet)
            attempts.append({"attempt": attempt, "errors": errors, "usd": cost,
                             "model_returned": got["model_returned"],
                             "stop_reason": got.get("stop_reason")})
            if data is not None:
                result = {"name": name, "key": key, "state": "accepted", "answer": data,
                          "attempts": attempts}
                break
        else:
            result = {"name": name, "key": key, "state": "failed", "answer": None,
                      "attempts": attempts}
        partial = final.with_suffix(".partial")
        partial.write_text(json.dumps(result, ensure_ascii=False))
        partial.rename(final)
        self.persist()
        return result

    def run(self, packets: list[tuple[str, dict]]) -> dict:
        """Every packet, in parallel, until done or the ceiling stops the pass."""
        results, stopped = [], None
        with concurrent.futures.ThreadPoolExecutor(self.workers) as pool:
            futures = {pool.submit(self.one, name, p): name for name, p in packets}
            for f in concurrent.futures.as_completed(futures):
                try:
                    results.append(f.result())
                except CeilingReached as e:
                    stopped = str(e)
        states = {s: sum(r["state"] == s for r in results)
                  for s in ("accepted", "failed", "pending")}
        return {"model": self.model, "packets": len(packets), "states": states,
                "not_sent_ceiling": len(packets) - len(results), "stopped": stopped,
                "spent_usd": round(self.ledger.spent, 4), "results": results}
