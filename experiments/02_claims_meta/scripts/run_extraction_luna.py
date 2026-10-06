# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "pydantic==2.13.5"]
# ///
"""Extraction-system comparison (AMENDMENT_01_extraction_system_comparison.md): extract the
abstracts GPT-6.1 Sol extracted a second time with the tuned Luna extraction system
(`gpt-6-luna` with its own prompt). GPT-6.1 Sol with the frozen prompt stays the registered
extraction; nothing written here enters a registered primary or secondary result.

The request is the study's own (`run_extraction.request_body`: Responses API, no tools, `store`
false, reasoning effort `medium`, the committed `extraction` schema as strict structured output)
with two differences: the model is `gpt-6-luna`, and the instructions are
`prompts/luna_extraction_prompt.md`, which is the frozen `prompts/extraction_prompt.md` followed
by one addendum. The script refuses a Luna prompt that does not begin with the frozen prompt.

Records. `--abstracts` is the file GPT-6.1 Sol extracted (stage 3) and `--sol-extraction` its
parsed output; the script refuses unless the two hold the same record ids, so Luna extracts
exactly the abstracts Sol extracted. A record without an abstract of at least ABSTRACT_FLOOR
characters is refused, as in the study.

Runs. `--run 1` and `--run 2` are two separate runs of the same request. Each has its own
raw folder, outputs/raw/luna/extraction/<revision>/run<k>/, so no exchange of one run is reused
by the other; within a run a cached exchange is reused, so a stopped run resumes where it
stopped. Every HTTP exchange is written before it is parsed. The parsed file,
outputs/parsed/luna_extraction_<label>_run<k>_<revision>.jsonl, is written once, at the end; an
existing one is refused. Its rows have the fields of the study's extraction rows, so
verify_spans.py, verify_claims.py and assemble_registry.py read it unchanged. A response that
fails schema validation is re-run once; a second failure is recorded as `extraction_failed`.

Gate. The script refuses to run unless the log of PREREG.md names the sha256 of the amendment
file and of the Luna prompt as they are on disk (`prereg log` writes that line when the
amendment is logged). `--dev` lifts the gate for prompts/dev_abstracts.jsonl only (development
abstracts first public before 2019).

The API key is read from OPENAI_API_KEY and never printed or written.

Usage:
    uv run scripts/run_extraction_luna.py --abstracts <...eligible_abstracts.jsonl> \
        --sol-extraction outputs/parsed/sol_extraction_<label>_<rev>.jsonl --label <label> --run 1
"""

import argparse
import concurrent.futures
import hashlib
import json
import os
import pathlib
import threading
import time

import httpx
from pydantic import BaseModel, ValidationError

import run_extraction as rx
from abstract_floor import refuse_no_abstract

LUNA_MODEL = "gpt-6-luna"
TASK = "extraction"
RUNS = (1, 2)
FROZEN_PROMPT = rx.PROMPTS / "extraction_prompt.md"
LUNA_PROMPT = rx.PROMPTS / "luna_extraction_prompt.md"
AMENDMENT = rx.EXP / "AMENDMENT_01_extraction_system_comparison.md"
PREREG = rx.EXP / "PREREG.md"
DEV_ABSTRACTS = rx.PROMPTS / "dev_abstracts.jsonl"
RAW = rx.EXP / "outputs" / "raw" / "luna"
LOG_HEADING = "\n## Log"


class LunaRunError(Exception):
    """The run cannot proceed: the amendment is not logged, the records differ from Sol's, the
    prompt does not hold the frozen prompt, or an output exists."""


class Usage(BaseModel):
    requests: int = 0
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def luna_revision_id(prompt: str, schema: dict) -> str:
    """The study's revision id (`run_extraction.revision_id`) with the Luna model string."""
    blob = json.dumps({"task": TASK, "prompt": prompt, "schema": schema, "model": LUNA_MODEL,
                       "reasoning_effort": rx.REASONING_EFFORT}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


def check_prompt(luna_prompt: str, frozen_prompt: str) -> None:
    """The Luna prompt is the frozen prompt followed by an addendum, and nothing else."""
    if not luna_prompt.startswith(frozen_prompt) or len(luna_prompt) <= len(frozen_prompt):
        raise LunaRunError("the Luna prompt is not the frozen extraction prompt followed by an "
                           "addendum")


def require_logged(prereg_text: str, amendment_sha256: str, prompt_sha256: str) -> None:
    """Refuse unless the log of the plan names both digests."""
    if LOG_HEADING not in prereg_text:
        raise LunaRunError("PREREG.md has no log")
    log = prereg_text.rsplit(LOG_HEADING, 1)[1]
    missing = [name for name, digest in (("the amendment file", amendment_sha256),
                                         ("the Luna prompt", prompt_sha256))
               if digest not in log]
    if missing:
        raise LunaRunError(f"the log of PREREG.md does not name the sha256 of "
                           f"{' or of '.join(missing)}; the amendment is logged with "
                           "`prereg log` before any Luna run")


def check_same_records(record_ids: list[str], sol_rows: list[dict]) -> None:
    """Luna extracts exactly the records of the Sol extraction file."""
    if len(set(record_ids)) != len(record_ids):
        raise LunaRunError("a record id occurs twice in the abstracts file")
    sol_ids = [r["pmid"] for r in sol_rows]
    only_here, only_sol = sorted(set(record_ids) - set(sol_ids)), sorted(set(sol_ids)
                                                                         - set(record_ids))
    if only_here or only_sol or len(sol_ids) != len(record_ids):
        raise LunaRunError(f"the abstracts differ from the Sol extraction: {len(only_here)} "
                           f"records only here {only_here[:5]}, {len(only_sol)} only in Sol's "
                           f"{only_sol[:5]}")


def luna_body(prompt: str, schema: dict, rec: rx.Record) -> dict:
    body = rx.request_body(TASK, prompt, schema, rec)
    body["model"] = LUNA_MODEL
    return body


def add_usage(usage: Usage, response: dict) -> None:
    u = response.get("usage", {})
    details = u.get("input_tokens_details", {})
    usage.requests += 1
    usage.input_tokens += u.get("input_tokens", 0)
    usage.cached_input_tokens += details.get("cached_tokens", 0)
    usage.cache_write_tokens += details.get("cache_write_tokens", 0)
    usage.output_tokens += u.get("output_tokens", 0)
    usage.reasoning_tokens += u.get("output_tokens_details", {}).get("reasoning_tokens", 0)


def post(client: httpx.Client, key: str, body: dict, cache: pathlib.Path) -> dict:
    """POST once per try until a 200 or a non-retryable status; cache every exchange."""
    for http_try in range(1, rx.MAX_HTTP_TRIES + 1):
        started = rx.now()
        try:
            r = client.post(rx.ENDPOINT, json=body, headers={"Authorization": f"Bearer {key}"})
            status, text = r.status_code, r.text
        except httpx.HTTPError as e:
            status, text = None, f"{type(e).__name__}: {e}"
        try:
            parsed = json.loads(text) if status is not None else None
        except json.JSONDecodeError:
            parsed = None
        exchange = {
            "endpoint": rx.ENDPOINT, "model_requested": LUNA_MODEL, "request": body,
            "started_utc": started, "finished_utc": rx.now(), "http_try": http_try,
            "status": status, "response_text": text,
            "model_returned": parsed.get("model") if isinstance(parsed, dict) else None,
            "temperature_applied": (parsed.get("temperature")
                                    if isinstance(parsed, dict) else None),
        }
        target = cache if status == 200 else cache.with_suffix(f".http{http_try}.json")
        target.write_text(json.dumps(exchange, indent=1, ensure_ascii=False))
        if status == 200 or (status is not None and status < 500 and status != 429):
            return exchange
        time.sleep(min(60, 2 ** http_try))
    return exchange


def run_one(client: httpx.Client, key: str, rev: str, run: int, prompt: str, schema: dict,
            rec: rx.Record, usage: Usage, lock: threading.Lock, out_dir: pathlib.Path) -> dict:
    errors: list[str] = []
    for attempt in range(1, rx.MAX_SCHEMA_ATTEMPTS + 1):
        cache = out_dir / f"{rec.pmid}_attempt{attempt}.json"
        if cache.exists():
            exchange = json.loads(cache.read_text())
        else:
            exchange = post(client, key, luna_body(prompt, schema, rec), cache)
            if exchange["status"] == 200:
                with lock:
                    add_usage(usage, json.loads(exchange["response_text"]))
        if exchange["status"] != 200:
            errors.append(f"attempt {attempt}: HTTP {exchange['status']}")
            continue
        try:
            response = json.loads(exchange["response_text"])
            validated = rx.OUTPUT_MODEL[TASK].model_validate(json.loads(rx.output_text(response)))
        except (ValueError, ValidationError) as e:
            errors.append(f"attempt {attempt}: {type(e).__name__}: {str(e)[:400]}")
            continue
        return {"pmid": rec.pmid, "task": TASK, "revision": rev, "model": LUNA_MODEL, "run": run,
                "status": "ok", "attempts": attempt,
                "model_returned": exchange["model_returned"], "errors": errors,
                "output": validated.model_dump()}
    return {"pmid": rec.pmid, "task": TASK, "revision": rev, "model": LUNA_MODEL, "run": run,
            "status": "extraction_failed", "attempts": rx.MAX_SCHEMA_ATTEMPTS,
            "model_returned": None, "errors": errors, "output": None}


def parsed_path(label: str, run: int, rev: str) -> pathlib.Path:
    return rx.PARSED / f"luna_extraction_{label}_run{run}_{rev}.jsonl"


def run_folder(rev: str, run: int) -> pathlib.Path:
    """The raw folder of one run; the two runs never share an exchange."""
    return RAW / TASK / rev / f"run{run}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--abstracts", type=pathlib.Path, required=True)
    ap.add_argument("--sol-extraction", type=pathlib.Path, required=True,
                    help="the parsed GPT-6.1 Sol extraction of the same abstracts")
    ap.add_argument("--label", required=True)
    ap.add_argument("--run", type=int, choices=RUNS, required=True)
    ap.add_argument("--dev", action="store_true",
                    help="prompts/dev_abstracts.jsonl only: run without the logged amendment")
    a = ap.parse_args()

    prompt = LUNA_PROMPT.read_text()
    check_prompt(prompt, FROZEN_PROMPT.read_text())
    if a.dev:
        if a.abstracts.resolve() != DEV_ABSTRACTS.resolve():
            raise LunaRunError("--dev is for prompts/dev_abstracts.jsonl only")
    else:
        require_logged(PREREG.read_text(), hashlib.sha256(AMENDMENT.read_bytes()).hexdigest(),
                       hashlib.sha256(LUNA_PROMPT.read_bytes()).hexdigest())
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise LunaRunError("OPENAI_API_KEY is not set")
    schema = json.loads((rx.PROMPTS / "schema.json").read_text())[TASK]
    rev = luna_revision_id(prompt, schema)
    records = [rx.Record.model_validate_json(line)
               for line in a.abstracts.read_text().splitlines() if line.strip()]
    if not records:
        raise LunaRunError(f"no records in {a.abstracts}")
    check_same_records([r.pmid for r in records],
                       [json.loads(line) for line in a.sol_extraction.read_text().splitlines()
                        if line.strip()])
    refuse_no_abstract([r.model_dump() for r in records], f"luna extraction of {a.abstracts}")
    out = parsed_path(a.label, a.run, rev)
    if out.exists():
        raise LunaRunError(f"{out} exists; archive it or choose another label")

    out_dir = run_folder(rev, a.run)
    rev_dir = out_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in (("prompt.md", prompt), ("schema.json", json.dumps(schema, indent=1))):
        stored = rev_dir / name
        if stored.exists() and stored.read_text() != text:
            raise LunaRunError(f"{stored} differs from the prompt or schema of this run")
        stored.write_text(text)
    rx.PARSED.mkdir(parents=True, exist_ok=True)

    usage, lock = Usage(), threading.Lock()
    started = rx.now()
    with httpx.Client(timeout=600) as client, \
            concurrent.futures.ThreadPoolExecutor(rx.WORKERS) as pool:
        futures = [pool.submit(run_one, client, key, rev, a.run, prompt, schema, rec, usage, lock,
                               out_dir) for rec in records]
        results = [f.result() for f in futures]

    with out.open("w") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    meta = {
        "task": TASK, "label": a.label, "run": a.run, "revision": rev,
        "model_requested": LUNA_MODEL,
        "models_returned": sorted({r["model_returned"] for r in results if r["model_returned"]}),
        "reasoning_effort": rx.REASONING_EFFORT, "endpoint": rx.ENDPOINT,
        "prompt": str(LUNA_PROMPT.relative_to(rx.EXP)), "prompt_sha256": sha256_text(prompt),
        "abstracts": str(a.abstracts), "sol_extraction": str(a.sol_extraction),
        "development_run": a.dev, "n_records": len(records),
        "n_ok": sum(r["status"] == "ok" for r in results),
        "n_extraction_failed": sum(r["status"] == "extraction_failed" for r in results),
        "n_needed_retry": sum(r["status"] == "ok" and r["attempts"] > 1 for r in results),
        "usage_new_requests_this_invocation": usage.model_dump(),
        "started_utc": started, "finished_utc": rx.now(),
    }
    out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
