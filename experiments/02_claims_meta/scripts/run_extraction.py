# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "pydantic==2.13.5"]
# ///
"""Run the eligibility, extraction and full-text extraction prompts through GPT-6.1 Sol.

Each record's title and abstract (for `fulltext_extraction`, its title and the body text rendered
by fetch_fulltext.py, abstract removed) go to the OpenAI Responses API with the committed prompt as
instructions and the committed JSON schema as a strict structured-output format, with no tools
(so no web access) and `store: false`. The model does not accept `temperature`; the request
omits it and the response records the value the API applied.

Every HTTP exchange is written to outputs/raw/sol/<task>/<revision>/ before it is parsed:
request body (no key), status, response body, UTC timestamps of every call, requested and returned model
strings, and endpoint. A cached exchange is reused, so a stopped run resumes where it stopped.
The parsed file is written once, at the end; a label whose parsed file exists is refused.
A response that fails schema validation is re-run once; a second failure is recorded as
`extraction_failed`.

A record with no abstract of at least ABSTRACT_FLOOR characters (scripts/abstract_floor.py) is
never sent: the eligibility and extraction tasks refuse an input file that holds one, before
any request.

The API key is read from OPENAI_API_KEY and never printed or written.

Usage:
    uv run scripts/run_extraction.py --task eligibility --abstracts prompts/dev_abstracts.jsonl
    uv run scripts/run_extraction.py --task extraction  --abstracts prompts/dev_abstracts.jsonl
    uv run scripts/run_extraction.py --task fulltext_extraction --abstracts prompts/dev_fulltext.jsonl
"""

import argparse
import concurrent.futures
import datetime
import hashlib
import json
import os
import pathlib
import threading
import time
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from abstract_floor import refuse_no_abstract

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
PROMPTS = EXP / "prompts"
RAW = EXP / "outputs" / "raw" / "sol"
PARSED = EXP / "outputs" / "parsed"

ENDPOINT = "https://api.openai.com/v1/responses"
MODEL = "gpt-6.1-sol"
REASONING_EFFORT = "medium"
MAX_SCHEMA_ATTEMPTS = 2
MAX_HTTP_TRIES = 5
WORKERS = 6


class ExtractionRunError(Exception):
    """The run cannot proceed: a missing key, a malformed input file, an exhausted endpoint."""


class Record(BaseModel):
    pmid: str
    title: str
    abstract: str | None = None
    body: str | None = None


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


Criterion = Literal["yes", "no", "uncertain"]


class EligibilityOutput(Strict):
    genetic_instruments_for_circulating_proteins: Criterion
    states_protein_outcome_result: Criterion
    proteome_or_panel_wide_screen: Criterion
    n_proteins_tested: int | None
    n_proteins_tested_span: str | None
    count_other: int | None
    count_other_span: str | None
    exclusion: list[Literal["review", "protocol", "non_human", "tissue_or_csf_proteomics"]]
    also_tissue_or_csf: bool


def _named_or_not_stated(values: list[str]) -> list[str]:
    if not values or any(not v.strip() for v in values):
        raise ValueError("must be a non-empty list of non-empty names, or ['not_stated']")
    if "not_stated" in values and len(values) > 1:
        raise ValueError("'not_stated' must stand alone")
    if len(set(values)) != len(values):
        raise ValueError("each name at most once")
    return values


class Claim(Strict):
    protein_as_written: str = Field(min_length=1)
    outcome_as_written: str = Field(min_length=1)
    direction: Literal["raises", "lowers", "reported_nonsignificant_or_null", "not_stated"]
    evidence_type: Literal["mr_estimate", "observational", "experimental",
                           "variant_association", "other"]
    claim_scope: Literal["overall", "dataset_specific", "ancestry_specific",
                         "subgroup_specific", "sensitivity", "unclear"]
    analysis_context_as_written: str = Field(min_length=1)
    subgroup_as_written: str = Field(min_length=1)
    pqtl_datasets: list[str]
    outcome_datasets: list[str]
    dataset_attribution: Literal["claim_specific", "whole_study", "unclear"]
    platform: list[str]
    ancestry: str = Field(min_length=1)
    relation_ambiguous: bool
    evidence_span: str = Field(min_length=1)

    _check_lists = field_validator("pqtl_datasets", "outcome_datasets", "platform")(
        _named_or_not_stated
    )


class ExtractionOutput(Strict):
    claims: list[Claim]


class FullTextClaim(Claim):
    source_location: str = Field(min_length=1)
    colocalization: Literal["supports", "does_not_support", "not_reported"]
    replication: Literal["replicated", "not_replicated", "not_reported"]


class FullTextExtractionOutput(Strict):
    claims: list[FullTextClaim]


OUTPUT_MODEL: dict[str, type[Strict]] = {
    "eligibility": EligibilityOutput,
    "extraction": ExtractionOutput,
    "fulltext_extraction": FullTextExtractionOutput,
}


class Usage(BaseModel):
    requests: int = 0
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0


def now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="milliseconds")


def revision_id(task: str, prompt: str, schema: dict) -> str:
    blob = json.dumps({"task": task, "prompt": prompt, "schema": schema, "model": MODEL,
                       "reasoning_effort": REASONING_EFFORT}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


def user_message(rec: Record, task: str) -> str:
    if task == "fulltext_extraction":
        if rec.body is None:
            raise ExtractionRunError(f"{rec.pmid}: full-text record has no body")
        return f"Title: {rec.title}\n\nFull text (abstract removed):\n{rec.body}"
    if rec.abstract is None:
        raise ExtractionRunError(f"{rec.pmid}: record has no abstract")
    return f"Title: {rec.title}\n\nAbstract:\n{rec.abstract}"


def request_body(task: str, prompt: str, schema: dict, rec: Record) -> dict:
    return {
        "model": MODEL,
        "instructions": prompt,
        "input": user_message(rec, task),
        "tools": [],
        "store": False,
        "reasoning": {"effort": REASONING_EFFORT},
        "text": {"format": {"type": "json_schema", "name": task, "strict": True,
                            "schema": schema}},
    }


def output_text(body: dict) -> str:
    texts = [c["text"] for item in body.get("output", []) if item.get("type") == "message"
             for c in item.get("content", []) if c.get("type") == "output_text"]
    if len(texts) != 1:
        raise ValueError(f"expected one output_text, found {len(texts)}")
    return texts[0]


def post(client: httpx.Client, key: str, body: dict, cache: pathlib.Path) -> dict:
    """POST once per try until a 200 or a non-retryable status; cache every exchange."""
    for http_try in range(1, MAX_HTTP_TRIES + 1):
        started = now()
        try:
            r = client.post(ENDPOINT, json=body, headers={"Authorization": f"Bearer {key}"})
            status, text = r.status_code, r.text
        except httpx.HTTPError as e:
            status, text = None, f"{type(e).__name__}: {e}"
        exchange = {
            "endpoint": ENDPOINT, "model_requested": MODEL, "request": body,
            "started_utc": started, "finished_utc": now(), "http_try": http_try,
            "status": status, "response_text": text,
        }
        try:
            parsed = json.loads(text) if status is not None else None
        except json.JSONDecodeError:
            parsed = None
        exchange["model_returned"] = parsed.get("model") if isinstance(parsed, dict) else None
        exchange["temperature_applied"] = (parsed.get("temperature")
                                           if isinstance(parsed, dict) else None)
        target = cache if status == 200 else cache.with_suffix(f".http{http_try}.json")
        target.write_text(json.dumps(exchange, indent=1, ensure_ascii=False))
        if status == 200:
            return exchange
        if status is not None and status < 500 and status != 429:
            return exchange
        time.sleep(min(60, 2 ** http_try))
    return exchange


def run_one(client: httpx.Client, key: str, task: str, rev: str, prompt: str, schema: dict,
            rec: Record, usage: Usage, lock: threading.Lock, raw_root: pathlib.Path) -> dict:
    out_dir = raw_root / task / rev
    errors: list[str] = []
    for attempt in range(1, MAX_SCHEMA_ATTEMPTS + 1):
        cache = out_dir / f"{rec.pmid}_attempt{attempt}.json"
        if cache.exists():
            exchange = json.loads(cache.read_text())
        else:
            exchange = post(client, key, request_body(task, prompt, schema, rec), cache)
            if exchange["status"] == 200:
                u = json.loads(exchange["response_text"]).get("usage", {})
                with lock:
                    usage.requests += 1
                    usage.input_tokens += u.get("input_tokens", 0)
                    usage.cached_input_tokens += u.get("input_tokens_details", {}).get(
                        "cached_tokens", 0)
                    usage.output_tokens += u.get("output_tokens", 0)
                    usage.reasoning_tokens += u.get("output_tokens_details", {}).get(
                        "reasoning_tokens", 0)
        if exchange["status"] != 200:
            errors.append(f"attempt {attempt}: HTTP {exchange['status']}")
            continue
        try:
            body = json.loads(exchange["response_text"])
            data = json.loads(output_text(body))
            validated = OUTPUT_MODEL[task].model_validate(data)
        except (ValueError, ValidationError) as e:
            errors.append(f"attempt {attempt}: {type(e).__name__}: {str(e)[:400]}")
            continue
        return {"pmid": rec.pmid, "task": task, "revision": rev, "status": "ok",
                "attempts": attempt, "model_returned": exchange["model_returned"],
                "errors": errors, "output": validated.model_dump()}
    return {"pmid": rec.pmid, "task": task, "revision": rev, "status": "extraction_failed",
            "attempts": MAX_SCHEMA_ATTEMPTS, "model_returned": None, "errors": errors,
            "output": None}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", choices=["eligibility", "extraction", "fulltext_extraction"],
                    required=True)
    ap.add_argument("--abstracts", type=pathlib.Path, required=True)
    ap.add_argument("--label", required=True, help="revision label for REVISIONS.md, e.g. r1")
    ap.add_argument("--raw-root", type=pathlib.Path, default=RAW,
                    help="directory for raw exchanges (default outputs/raw/sol)")
    a = ap.parse_args()

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ExtractionRunError("OPENAI_API_KEY is not set")
    prompt = (PROMPTS / f"{a.task}_prompt.md").read_text()
    schema = json.loads((PROMPTS / "schema.json").read_text())[a.task]
    rev = revision_id(a.task, prompt, schema)
    records = [Record.model_validate_json(line) for line in a.abstracts.read_text().splitlines()
               if line.strip()]
    if not records:
        raise ExtractionRunError(f"no records in {a.abstracts}")

    out = PARSED / f"sol_{a.task}_{a.label}_{rev}.jsonl"
    if out.exists():
        raise ExtractionRunError(f"{out} exists; archive it or choose another label")
    if a.task != "fulltext_extraction":
        refuse_no_abstract([r.model_dump() for r in records], f"{a.task} of {a.abstracts}")

    (a.raw_root / a.task / rev).mkdir(parents=True, exist_ok=True)
    (a.raw_root / a.task / rev / "prompt.md").write_text(prompt)
    (a.raw_root / a.task / rev / "schema.json").write_text(json.dumps(schema, indent=1))
    PARSED.mkdir(parents=True, exist_ok=True)

    usage, lock = Usage(), threading.Lock()
    started = now()
    with httpx.Client(timeout=600) as client, \
            concurrent.futures.ThreadPoolExecutor(WORKERS) as pool:
        futures = [pool.submit(run_one, client, key, a.task, rev, prompt, schema, rec, usage,
                               lock, a.raw_root) for rec in records]
        results = [f.result() for f in futures]

    with out.open("w") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    meta = {
        "task": a.task, "label": a.label, "revision": rev, "model_requested": MODEL,
        "models_returned": sorted({r["model_returned"] for r in results if r["model_returned"]}),
        "reasoning_effort": REASONING_EFFORT, "endpoint": ENDPOINT,
        "abstracts": str(a.abstracts), "n_records": len(records),
        "n_ok": sum(r["status"] == "ok" for r in results),
        "n_extraction_failed": sum(r["status"] == "extraction_failed" for r in results),
        "n_needed_retry": sum(r["status"] == "ok" and r["attempts"] > 1 for r in results),
        "usage_new_requests_this_invocation": usage.model_dump(),
        "started_utc": started, "finished_utc": now(),
    }
    out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
