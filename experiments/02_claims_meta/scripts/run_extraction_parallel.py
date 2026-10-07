# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "pydantic==2.13.5"]
# ///
"""Run run_extraction.py's requests with more simultaneous workers than its constant six.

The registered runner (`run_extraction.py`, sealed) sends each record's request, caches every
exchange per record and writes the parsed file at the end. This script changes one thing: how
many requests are in flight at once. It imports the runner and

1. sends the requests through the runner's own `run_one` (same prompt, schema, request body,
   retries and per-record cache files), with the number of simultaneous workers given by the
   environment variable SOL_WORKERS (default 16);
2. then calls the runner's own `main`, which finds every exchange in the cache and writes the
   parsed file and its meta file exactly as it always does.

Two operational rules, neither of which touches a decision:

- a rate-limit refusal (HTTP 429 that is not a billing refusal) halves the worker limit, down to
  MIN_WORKERS, at most once per COOLDOWN_SECONDS; the runner's own back-off answers the record;
- a billing refusal (HTTP 429 `insufficient_quota`) stops the run: requests in flight finish, no
  further request is sent, no parsed file is written, and `BillingStop` names how many records
  are answered and how many remain. A record without a 200 response has no cache file, so the
  same command resumes with exactly the unanswered records.

A record that has no 200 response after MAX_PASSES passes (any HTTP failure) is never written as
`extraction_failed`: the run stops with `Unanswered`, and the same command asks again. The
runner's own rule for a response that fails schema validation (one re-run, then
`extraction_failed`) is unchanged.

The command line is the runner's own (`--task`, `--abstracts`, `--label`, `--raw-root`).

Usage:
    SOL_WORKERS=16 uv run scripts/run_extraction_parallel.py --task eligibility \
        --label gateall1 --abstracts <...jsonl> --raw-root outputs/raw/sol_chase_full
"""

import argparse
import concurrent.futures
import json
import os
import pathlib
import threading
import time

import httpx

import run_extraction as rx
from abstract_floor import refuse_no_abstract

DEFAULT_WORKERS = 16
MIN_WORKERS = 2
COOLDOWN_SECONDS = 30.0
MAX_PASSES = 3
BILLING_CODES = ("insufficient_quota", "billing_hard_limit_reached", "billing_not_active")


class ParallelRunError(Exception):
    """The run cannot proceed."""


class BillingStop(ParallelRunError):
    """The API refused a request for billing reasons; the unanswered records stay queued."""


class Unanswered(ParallelRunError):
    """Records still have no 200 response after MAX_PASSES passes; nothing was finalized."""


class Limiter:
    """A worker limit that can be lowered while requests are in flight."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.active = 0
        self.history = [limit]
        self._last_cut = float("-inf")
        self._cond = threading.Condition()

    def acquire(self) -> None:
        with self._cond:
            while self.active >= self.limit:
                self._cond.wait()
            self.active += 1

    def release(self) -> None:
        with self._cond:
            self.active -= 1
            self._cond.notify_all()

    def halve(self) -> None:
        with self._cond:
            if time.monotonic() - self._last_cut < COOLDOWN_SECONDS or self.limit <= MIN_WORKERS:
                return
            self.limit = max(MIN_WORKERS, self.limit // 2)
            self.history.append(self.limit)
            self._last_cut = time.monotonic()


def make_client() -> httpx.Client:
    return httpx.Client(timeout=600)


def refusals(out_dir: pathlib.Path, pmid: str, known: set[str]) -> tuple[bool, bool]:
    """(billing refusal seen, rate-limit refusal seen) in this record's failed exchanges that
    are not in `known` (the failed-exchange files that existed before this pass)."""
    billing = rate = False
    for path in sorted(out_dir.glob(f"{pmid}_attempt*.http*.json")):
        if path.name in known:
            continue
        exchange = json.loads(path.read_text())
        if exchange["status"] != 429:
            continue
        try:
            error = json.loads(exchange["response_text"]).get("error") or {}
        except (json.JSONDecodeError, AttributeError):
            error = {}
        if error.get("code") in BILLING_CODES or error.get("type") in BILLING_CODES:
            billing = True
        else:
            rate = True
    return billing, rate


def answered(out_dir: pathlib.Path, pmid: str) -> bool:
    """The record has at least one cached 200 exchange."""
    return any((out_dir / f"{pmid}_attempt{n}.json").exists()
               for n in range(1, rx.MAX_SCHEMA_ATTEMPTS + 1))


def fetch_all(task: str, records: list[rx.Record], raw_root: pathlib.Path, key: str,
              workers: int) -> dict:
    """Fill the runner's cache for `records`; raise BillingStop or Unanswered, else a summary."""
    prompt = (rx.PROMPTS / f"{task}_prompt.md").read_text()
    schema = json.loads((rx.PROMPTS / "schema.json").read_text())[task]
    rev = rx.revision_id(task, prompt, schema)
    out_dir = raw_root / task / rev
    out_dir.mkdir(parents=True, exist_ok=True)
    limiter, stop = Limiter(workers), threading.Event()
    usage, lock = rx.Usage(), threading.Lock()
    started = rx.now()

    def one(rec: rx.Record) -> None:
        if stop.is_set():
            return
        limiter.acquire()
        try:
            if stop.is_set():
                return
            known = {p.name for p in out_dir.glob(f"{rec.pmid}_attempt*.http*.json")}
            rx.run_one(client, key, task, rev, prompt, schema, rec, usage, lock, raw_root)
            billing, rate = refusals(out_dir, rec.pmid, known)
            if billing:
                stop.set()
            elif rate:
                limiter.halve()
        finally:
            limiter.release()

    passes = 0
    with make_client() as client:
        pending = [r for r in records if not answered(out_dir, r.pmid)]
        cached_before = len(records) - len(pending)
        while pending and passes < MAX_PASSES and not stop.is_set():
            passes += 1
            with concurrent.futures.ThreadPoolExecutor(workers) as pool:
                for future in [pool.submit(one, rec) for rec in pending]:
                    future.result()
            pending = [r for r in pending if not answered(out_dir, r.pmid)]

    summary = {
        "task": task, "revision": rev, "raw_dir": str(out_dir), "records": len(records),
        "answered_before_this_invocation": cached_before,
        "answered": len(records) - len(pending), "unanswered": len(pending),
        "workers_requested": workers, "worker_limit_history": limiter.history,
        "passes": passes, "new_requests_with_200": usage.model_dump(),
        "started_utc": started, "finished_utc": rx.now(),
    }
    if stop.is_set():
        raise BillingStop(json.dumps(summary))
    if pending:
        raise Unanswered(json.dumps(summary))
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", choices=["eligibility", "extraction", "fulltext_extraction"],
                    required=True)
    ap.add_argument("--abstracts", type=pathlib.Path, required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--raw-root", type=pathlib.Path, default=rx.RAW)
    a = ap.parse_args()

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ParallelRunError("OPENAI_API_KEY is not set")
    workers = int(os.environ.get("SOL_WORKERS", DEFAULT_WORKERS))
    if workers < MIN_WORKERS:
        raise ParallelRunError(f"SOL_WORKERS must be at least {MIN_WORKERS}")
    records = [rx.Record.model_validate_json(line)
               for line in a.abstracts.read_text().splitlines() if line.strip()]
    if not records:
        raise ParallelRunError(f"no records in {a.abstracts}")
    if a.task != "fulltext_extraction":
        refuse_no_abstract([r.model_dump() for r in records], f"{a.task} of {a.abstracts}")
    prompt = (rx.PROMPTS / f"{a.task}_prompt.md").read_text()
    schema = json.loads((rx.PROMPTS / "schema.json").read_text())[a.task]
    out = rx.PARSED / f"sol_{a.task}_{a.label}_{rx.revision_id(a.task, prompt, schema)}.jsonl"
    if out.exists():
        raise ParallelRunError(f"{out} exists; archive it or choose another label")

    summary = fetch_all(a.task, records, a.raw_root, key, workers)
    rx.PARSED.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".parallel_run.json").write_text(json.dumps(summary, indent=1))
    rx.WORKERS = workers
    rx.main()


if __name__ == "__main__":
    main()
