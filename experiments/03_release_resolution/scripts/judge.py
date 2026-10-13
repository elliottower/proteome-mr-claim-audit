# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "jsonschema==4.26.0"]
# ///
"""The judge of Amendment 3 (AMENDMENT_03_judge.md): Gemini 3.1 Pro (`gemini-3.1-pro-preview`)
decides each disagreement and each audit row of a pass, one request per row; then the routing of
item 2 and the calibration samples of item 3. No coder model is called here.

Request (`judge_request`). The system instruction is prompts/judge_prompt.md, a line
`## Coding instructions`, prompts/coding_prompt_v2.md, a line `## Dictionary definitions`, and
Paper 1's dictionary definitions, joined by blank lines (`system_text`). The body is the JSON
object the judge prompt describes: the task, the record, the row as the coders received it, the
files the coders received, and the answers (Answer 1 and Answer 2 in the pages' order, drawn by
adjudication_pages.first_is_a with seed 20261017) or the agreed answer, each with its gate
verdict. Gemini's generateContent with `x-goog-api-key` (never written), structured output
(`responseMimeType` application/json, `responseJsonSchema` the frozen schema), no tools, sampling
at the vendor's defaults, at most MAX_OUTPUT output tokens; the returned `modelVersion` is
recorded.

Answers. Accepted when it parses, fits prompts/judge_schema.json and names the row; otherwise
requested once more; a second failure is `failed`. A transport failure leaves the request pending.
Every exchange is stored as it ends; a stored decision is not requested again.

Spend. From the usage the API reports (`promptTokenCount`, `cachedContentTokenCount`,
`candidatesTokenCount`, `thoughtsTokenCount`, thinking billed as output), at the list prices of
PRICE by prompt length (third-party listings; the vendor's own page was not read), recorded in the
stage's ledger (coding_runner.Ledger). Before each request its bound (every character of the
request as input at MIN_RATIO characters a token at the upper tier's price, plus MAX_OUTPUT at
the upper tier's output price) is reserved against the ceiling.

Routing (`route`, item 2): a row goes to the author when `needs_human` is true; the confidence
is below 0.80; the choice is `neither` (a disagreement) or `substantive_error` or `other_issue`
(an audit row); the answer the judge chose fails the gate (Answer 1 or 2, or the agreed answer
for `correct`); the quotation, when not empty, does not stand verbatim in the files; or the
request failed twice. Every reason that holds is listed.

Calibration (`calibration_order`, item 3): the task's rows the judge decided alone, in order of
row id, shuffled by `random.Random(seed).shuffle`; the author marks the first 20.
"""

import datetime
import hashlib
import json
import pathlib
import random
import threading
import time

import httpx
import jsonschema

import adjudication_pages as ap
import coding_runner as cr

MODEL = "gemini-3.1-pro-preview"
ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
MAX_OUTPUT = 32_768
MIN_RATIO = 1.5
TIER = 200_000
PRICE = {"low": {"new": 2.00, "cached": 0.20, "output": 12.00},
         "high": {"new": 4.00, "cached": 0.40, "output": 18.00}}
CONFIDENCE = 0.80
CALIBRATION = 20


class JudgeError(Exception):
    """A row has no answer to judge, or a stored exchange is malformed."""


def now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="milliseconds")


def system_text(judge_prompt: str, coding_prompt: str, definitions: str) -> str:
    return (judge_prompt.rstrip("\n") + "\n\n## Coding instructions\n\n" + coding_prompt.rstrip("\n")
            + "\n\n## Dictionary definitions\n\n" + definitions)


def shown_row(qrow: dict) -> dict:
    out = {"row_id": qrow["row_id"], "side": qrow["side"], "name": qrow["name_as_written"]}
    if qrow["side"] == "outcome":
        out["outcomes_as_written"] = qrow["outcomes_as_written"]
    out["candidates"] = qrow["candidates"]
    return out


def judge_request(task: str, packet: dict, qrow: dict, answers: list[tuple[dict, bool]]) -> dict:
    """`answers`: for a disagreement, [(Answer 1, its gate), (Answer 2, its gate)]; for an audit,
    [(the agreed answer, its gate)]."""
    body = {"task": task, "record_id": packet["record_id"], "title": packet["title"],
            "row": shown_row(qrow),
            "files": [{"file_id": f["file_id"], "kind": f["kind"], "text": f["text"]}
                      for f in packet["files"]]}
    if task == "disagreement":
        body["answers"] = [{"label": f"Answer {i}", "answer": a, "gate": g}
                           for i, (a, g) in enumerate(answers, 1)]
    else:
        body["agreed_answer"] = {"answer": answers[0][0], "gate": answers[0][1]}
    return body


def api_body(system: str, schema: dict, request: dict) -> dict:
    return {"systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user",
                          "parts": [{"text": json.dumps(request, ensure_ascii=False)}]}],
            "generationConfig": {"responseMimeType": "application/json",
                                 "responseJsonSchema": schema,
                                 "maxOutputTokens": MAX_OUTPUT}}


def call(client: httpx.Client, key: str, body: dict) -> dict:
    r = client.post(ENDPOINT, json=body, headers={"x-goog-api-key": key})
    if r.status_code != 200:
        return {"status": r.status_code, "body": r.text[:4000]}
    data = r.json()
    parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    return {"status": 200, "model_returned": data.get("modelVersion"),
            "stop_reason": (data.get("candidates") or [{}])[0].get("finishReason"),
            "usage": data.get("usageMetadata") or {}, "text": text,
            "request_id": data.get("responseId")}


def usd(usage: dict) -> float:
    prompt = usage.get("promptTokenCount", 0)
    p = PRICE["low" if prompt <= TIER else "high"]
    cached = usage.get("cachedContentTokenCount", 0)
    out = usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0)
    return ((prompt - cached) * p["new"] + cached * p["cached"] + out * p["output"]) / 1e6


def bound(system: str, request: dict) -> float:
    chars = len(system) + len(json.dumps(request, ensure_ascii=False))
    p = PRICE["high"]
    return (chars / MIN_RATIO * p["new"] + MAX_OUTPUT * p["output"]) / 1e6


def check(text: str, schema: dict, row_id: str) -> tuple[dict | None, list[str]]:
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        return None, [f"parse: {e}"]
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        return None, [f"schema: {e.message}"]
    if data["row_id"] != row_id:
        return None, ["row_id differs from the request's"]
    return data, []


def request_key(system: str, schema: dict, request: dict) -> str:
    blob = json.dumps({"model": MODEL, "system": hashlib.sha256(system.encode()).hexdigest(),
                       "schema": schema, "request": request}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()[:24]


class Judge:
    def __init__(self, system: str, schema: dict, store: pathlib.Path, ledger: cr.Ledger,
                 send, persist=lambda: None, workers: int = 8, sleep=time.sleep):
        self.system, self.schema, self.store, self.ledger = system, schema, store, ledger
        self.send, self.persist, self.workers, self.sleep = send, persist, workers, sleep
        self.stopped = threading.Event()
        store.mkdir(parents=True, exist_ok=True)

    def one(self, row_id: str, request: dict) -> dict:
        key = request_key(self.system, self.schema, request)
        final = self.store / f"{row_id}.{key}.json"
        if final.exists():
            return json.loads(final.read_text())
        attempts = []
        body = api_body(self.system, self.schema, request)
        for attempt in (1, 2):
            if self.stopped.is_set():
                raise cr.CeilingReached("the pass stopped at the ceiling")
            try:
                self.ledger.reserve(f"{key}:{attempt}", bound(self.system, request))
            except cr.CeilingReached:
                self.stopped.set()
                raise
            started = now()
            try:
                got = cr.transport(MODEL, lambda: self.send(body), self.sleep)
            except Exception as e:
                got = {"status": None, "body": f"{type(e).__name__}: {e}"[:2000]}
            got.update({"attempt": attempt, "started_utc": started, "finished_utc": now()})
            (self.store / f"{row_id}.{key}.attempt{attempt}.json").write_text(
                json.dumps(got, ensure_ascii=False))
            if got["status"] != 200:
                self.ledger.release(f"{key}:{attempt}")
                self.persist()
                return {"row_id": row_id, "key": key, "state": "pending",
                        "attempts": attempts + [{k: got.get(k) for k in ("status", "body")}]}
            cost = usd(got["usage"])
            self.ledger.record(f"{key}:{attempt}", {
                "request_key": key, "name": row_id, "model": MODEL, "attempt": attempt,
                "model_returned": got["model_returned"], "usage": got["usage"], "usd": cost,
                "finished_utc": got["finished_utc"]})
            data, errors = check(got.get("text"), self.schema, row_id)
            attempts.append({"attempt": attempt, "errors": errors, "usd": cost,
                             "model_returned": got["model_returned"],
                             "stop_reason": got.get("stop_reason")})
            if data is not None:
                result = {"row_id": row_id, "key": key, "state": "accepted", "decision": data,
                          "attempts": attempts}
                break
        else:
            result = {"row_id": row_id, "key": key, "state": "failed", "decision": None,
                      "attempts": attempts}
        partial = final.with_suffix(".partial")
        partial.write_text(json.dumps(result, ensure_ascii=False))
        partial.rename(final)
        self.persist()
        return result


def route(task: str, result: dict, gates: list[bool], files_text: str) -> list[str]:
    """The reasons of item 2 that send the row to the author; empty: the judge's decision stands
    alone. `gates`: the gate verdict of Answer 1 and 2, or of the agreed answer."""
    if result["state"] != "accepted":
        return ["request_failed_twice" if result["state"] == "failed" else "request_pending"]
    d, reasons = result["decision"], []
    if d["needs_human"]:
        reasons.append("needs_human")
    if d["confidence"] < CONFIDENCE:
        reasons.append("confidence_below_0.80")
    if (task == "disagreement" and d["choice"] == "neither") or (
            task == "audit" and d["choice"] in ("substantive_error", "other_issue")):
        reasons.append("choice_" + d["choice"])
    if (task == "disagreement" and d["choice"] not in ("answer_1", "answer_2", "neither")) or (
            task == "audit" and d["choice"] not in ("correct", "substantive_error", "other_issue")):
        reasons.append("choice_not_of_the_task")
    chosen = {"answer_1": 0, "answer_2": 1, "correct": 0}.get(d["choice"])
    if chosen is not None and chosen < len(gates) and not gates[chosen]:
        reasons.append("chosen_answer_fails_the_gate")
    if d["quotation"] and d["quotation"] not in files_text:
        reasons.append("quotation_not_in_the_files")
    return reasons


def calibration_order(lone: list[str], seed: int) -> list[str]:
    order = sorted(lone)
    random.Random(seed).shuffle(order)
    return order


def blinded(row_id: str, models: tuple[str, str]) -> tuple[str, str]:
    a, b = models
    return (a, b) if ap.first_is_a(row_id, 20261017) else (b, a)
