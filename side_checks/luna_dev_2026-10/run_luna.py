# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "pydantic==2.13.5"]
# ///
"""Side check: send the study's eligibility and extraction requests to `gpt-6-luna`.

Not part of the registered study. Reads only `prompts/dev_abstracts.jsonl` (30 development
abstracts, all first public before 2019-01-01) and the committed prompts and schema; writes only
under `side_checks/luna_dev_2026-10/`.

The request body is built by the study's own `run_extraction.request_body`; the single change is
`body["model"]`. Any further change (only if the API rejects a parameter for Luna) is passed on
the command line and recorded in every exchange and in the run's meta file.

Every HTTP exchange is written to raw/luna/<task>/<sol_revision>/ before it is parsed. A cached
exchange is reused. As in the study, a response that fails schema validation is re-run once.

Run from the repository root:
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=experiments/02_claims_meta/scripts \
        uv run side_checks/luna_dev_2026-10/run_luna.py --task eligibility
"""

import argparse
import concurrent.futures
import datetime
import json
import os
import pathlib
import time

import httpx
from pydantic import ValidationError

import run_extraction as rx
from abstract_floor import refuse_no_abstract

LUNA_MODEL = "gpt-6-luna"
WINDOW_START = datetime.date(2019, 1, 1)
PUBLIC_DATE_FIELDS = ("issue", "article_electronic", "pubmed_entrez")
WORKERS = 4
N_DEV = 30

REPO = pathlib.Path.cwd()
STUDY = REPO / "experiments" / "02_claims_meta"
DEV = STUDY / "prompts" / "dev_abstracts.jsonl"
OUT = REPO / "side_checks" / "luna_dev_2026-10"


class SideCheckError(Exception):
    """The side check cannot proceed."""


def load_dev_records() -> list[rx.Record]:
    """The 30 development records, each verified first public before 2019 from its own fields."""
    if not DEV.exists() or not OUT.exists():
        raise SideCheckError("run from the repository root")
    rows = [json.loads(line) for line in DEV.read_text().splitlines() if line.strip()]
    if len(rows) != N_DEV:
        raise SideCheckError(f"expected {N_DEV} development records, found {len(rows)}")
    for row in rows:
        stated = datetime.date.fromisoformat(row["first_public_date"])
        earliest = min(datetime.date.fromisoformat(row["dates"][f])
                       for f in PUBLIC_DATE_FIELDS if f in row["dates"])
        if stated >= WINDOW_START or earliest >= WINDOW_START or stated != earliest:
            raise SideCheckError(
                f"{row['pmid']}: first_public_date {stated}, earliest listed date {earliest}; "
                "refusing a record not verifiably first public before 2019")
    refuse_no_abstract(rows, "luna side check")
    return [rx.Record.model_validate(row) for row in rows]


def luna_body(task: str, prompt: str, schema: dict, rec: rx.Record,
              reasoning_effort: str | None, omit_reasoning: bool) -> dict:
    body = rx.request_body(task, prompt, schema, rec)
    body["model"] = LUNA_MODEL
    if omit_reasoning:
        del body["reasoning"]
    elif reasoning_effort is not None:
        body["reasoning"] = {"effort": reasoning_effort}
    return body


def post(client: httpx.Client, key: str, body: dict, cache: pathlib.Path,
         differences: list[str]) -> dict:
    for http_try in range(1, rx.MAX_HTTP_TRIES + 1):
        started = rx.now()
        try:
            r = client.post(rx.ENDPOINT, json=body, headers={"Authorization": f"Bearer {key}"})
            status, text = r.status_code, r.text
        except httpx.HTTPError as e:
            status, text = None, f"{type(e).__name__}: {e}"
        exchange = {
            "endpoint": rx.ENDPOINT, "model_requested": LUNA_MODEL,
            "differences_from_study_request": differences, "request": body,
            "started_utc": started, "finished_utc": rx.now(), "http_try": http_try,
            "status": status, "response_text": text,
        }
        target = cache if status == 200 else cache.with_suffix(f".http{http_try}.json")
        target.write_text(json.dumps(exchange, indent=1, ensure_ascii=False))
        if status == 200 or (status is not None and status < 500 and status != 429):
            return exchange
        time.sleep(min(60, 2 ** http_try))
    return exchange


def run_one(client: httpx.Client, key: str, task: str, rev: str, prompt: str, schema: dict,
            rec: rx.Record, a: argparse.Namespace, differences: list[str]) -> dict:
    out_dir = OUT / "raw" / "luna" / task / rev
    errors: list[str] = []
    for attempt in range(1, rx.MAX_SCHEMA_ATTEMPTS + 1):
        cache = out_dir / f"{rec.pmid}_attempt{attempt}.json"
        if cache.exists():
            exchange = json.loads(cache.read_text())
        else:
            body = luna_body(task, prompt, schema, rec, a.reasoning_effort, a.omit_reasoning)
            exchange = post(client, key, body, cache, differences)
        if exchange["status"] != 200:
            errors.append(f"attempt {attempt}: HTTP {exchange['status']}")
            continue
        try:
            response = json.loads(exchange["response_text"])
            validated = rx.OUTPUT_MODEL[task].model_validate(json.loads(rx.output_text(response)))
        except (ValueError, ValidationError) as e:
            errors.append(f"attempt {attempt}: {type(e).__name__}: {str(e)[:400]}")
            continue
        return {"pmid": rec.pmid, "task": task, "sol_revision": rev, "status": "ok",
                "attempts": attempt, "model_returned": response.get("model"),
                "errors": errors, "output": validated.model_dump()}
    return {"pmid": rec.pmid, "task": task, "sol_revision": rev, "status": "extraction_failed",
            "attempts": rx.MAX_SCHEMA_ATTEMPTS, "model_returned": None, "errors": errors,
            "output": None}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", choices=["eligibility", "extraction"], required=True)
    ap.add_argument("--probe", help="run this one PMID only and write no parsed file")
    ap.add_argument("--reasoning-effort", help="replace the study's reasoning effort")
    ap.add_argument("--omit-reasoning", action="store_true", help="drop the reasoning setting")
    a = ap.parse_args()

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise SideCheckError("OPENAI_API_KEY is not set")
    records = load_dev_records()
    prompt = (rx.PROMPTS / f"{a.task}_prompt.md").read_text()
    schema = json.loads((rx.PROMPTS / "schema.json").read_text())[a.task]
    rev = rx.revision_id(a.task, prompt, schema)  # the Sol revision these prompts carry
    differences = [f"model: {rx.MODEL} -> {LUNA_MODEL}"]
    if a.omit_reasoning:
        differences.append(f"reasoning: {{'effort': '{rx.REASONING_EFFORT}'}} -> omitted")
    elif a.reasoning_effort is not None:
        differences.append(f"reasoning.effort: {rx.REASONING_EFFORT} -> {a.reasoning_effort}")

    if a.probe:
        records = [r for r in records if r.pmid == a.probe]
        if not records:
            raise SideCheckError(f"{a.probe} is not a development PMID")
    out = OUT / "parsed" / f"luna_{a.task}_{rev}.jsonl"
    if out.exists() and not a.probe:
        raise SideCheckError(f"{out} exists; archive it before rerunning")
    (OUT / "raw" / "luna" / a.task / rev).mkdir(parents=True, exist_ok=True)
    out.parent.mkdir(parents=True, exist_ok=True)

    started = rx.now()
    with httpx.Client(timeout=600) as client, \
            concurrent.futures.ThreadPoolExecutor(WORKERS) as pool:
        futures = [pool.submit(run_one, client, key, a.task, rev, prompt, schema, rec, a,
                               differences) for rec in records]
        results = [f.result() for f in futures]

    meta = {
        "task": a.task, "model_requested": LUNA_MODEL,
        "models_returned": sorted({r["model_returned"] for r in results if r["model_returned"]}),
        "sol_revision_of_prompt_and_schema": rev,
        "differences_from_study_request": differences, "endpoint": rx.ENDPOINT,
        "abstracts": str(DEV.relative_to(REPO)), "n_records": len(records),
        "n_ok": sum(r["status"] == "ok" for r in results),
        "n_extraction_failed": sum(r["status"] == "extraction_failed" for r in results),
        "n_needed_retry": sum(r["status"] == "ok" and r["attempts"] > 1 for r in results),
        "started_utc": started, "finished_utc": rx.now(),
    }
    if a.probe:
        print(json.dumps({**meta, "errors": results[0]["errors"]}, indent=1))
        return
    with out.open("w") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
