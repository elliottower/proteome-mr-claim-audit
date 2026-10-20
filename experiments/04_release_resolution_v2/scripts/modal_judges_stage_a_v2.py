"""Second version of the stage A judge wrapper (scripts/modal_judges_stage_a_v1.py, sealed,
unchanged and imported). Three changes:

- `run` sends only the Claude Fable 5.1 requests that the first run stored as failed twice when
  every one of their attempts was an account-side refusal (`void_rows`: HTTP 400 naming a credit
  balance or a usage limit), through scripts/judge_v5.py, with the same tasks, request bodies,
  system instruction and schema, the exchanges stored apart (claude-fable-5-1_v5); Fable's
  accepted answers of the first run and every GPT-6 Astra answer stand and are not sent again;
- `route` reads each Fable answer from the fifth version's store for a void row and from the
  first run's store otherwise; routing and calibration are judges_stage_a_v1's, unchanged;
- `author_page` builds the author's page (scripts/author_page_stage_a_v1.py) to the volume and to
  the ignored planning folder, with a counts-only summary in outputs/.

    PYTHONPATH=../03_release_resolution/scripts modal run scripts/modal_judges_stage_a_v2.py::tests
    ... modal run scripts/modal_judges_stage_a_v2.py::void --out <json>
    ... modal run --detach scripts/modal_judges_stage_a_v2.py::run --approved "<logged line>" --out <json>
    ... modal run scripts/modal_judges_stage_a_v2.py::route --out <json>
    ... modal run scripts/modal_judges_stage_a_v2.py::author_page --pages <planning dir> --out <json>
"""

import collections
import hashlib
import json
import os
import pathlib
import time

import modal

from modal_coding_v2 import CODING, E2, E3, MOUNT, SECRETS, vol
from modal_judges_stage_a_v1 import (JUDGES, LOCAL, PROMPT_V3, ROUNDS, ROUND_WAIT, context,
                                     image, schema, store_of, system, task_requests, write_once)
from modal_retrieve_v2 import E4

app = modal.App("release-resolution-v2-judges-stage-a-2", image=image)
TESTS = ["test_judge_v5.py", "test_author_page_stage_a_v1.py", "test_judges_stage_a_v1.py",
         "test_judge_v4.py", "test_spend_caps_v1.py"]
FIRST_TESTS = ["test_judge.py", "test_judge_v2.py", "test_judge_v3.py",
               "test_adjudication_pages.py", "test_author_page_helper_v1.py"]

with image.imports():
    import concurrent.futures
    import subprocess

    import anthropic

    import author_page_helper_v1 as helper
    import author_page_stage_a_v1 as page
    import coding_runner as cr
    import judge as jd
    import judge_v2 as j2
    import judge_v5 as j5
    import judges_stage_a_v1 as js
    import recode_v1 as rc
    import spend_caps_v1 as caps


def store_v5():
    return JUDGES / (j2.FABLE + j5.STORE_SUFFIX)


def void_rows(reqs: list[tuple], sysx: str, sch: dict) -> list[str]:
    out = []
    for _, rid, req, _ in reqs:
        key = j2.request_key(j2.FABLE, sysx, sch, req)
        path = store_of(j2.FABLE) / f"{rid}.{key}.json"
        if not path.exists():
            continue
        if json.loads(path.read_text())["state"] != "failed":
            continue
        bodies = [json.loads(p.read_text()) for p in
                  sorted(store_of(j2.FABLE).glob(f"{rid}.{key}.attempt*.json"))]
        if bodies and all(b.get("status") != 200 and j5.ACCOUNT_REFUSAL.search(
                str(b.get("body", ""))) for b in bodies):
            out.append(rid)
    return out


@app.function(timeout=1800, cpu=2.0, memory=8192)
def tests_job() -> dict:
    out, code = "", 0
    for cwd, files in ((f"{E4}/tests", TESTS), (f"{E3}/tests", FIRST_TESTS)):
        run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", *files],
                             capture_output=True, text=True, cwd=cwd)
        out += run.stdout + run.stderr
        code = code or run.returncode
    return {"returncode": code, "output": out}


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=16384)
def void_job(v3: str) -> dict:
    vol.reload()
    reqs = task_requests(context())
    sysx, sch = system(v3), schema()
    rows = void_rows(reqs, sysx, sch)
    failed = 0
    for _, rid, req, _ in reqs:
        path = store_of(j2.FABLE) / f"{rid}.{j2.request_key(j2.FABLE, sysx, sch, req)}.json"
        failed += path.exists() and json.loads(path.read_text())["state"] == "failed"
    return {"fable_failed_in_the_first_run": failed, "void_rows": len(rows),
            "void_row_ids": sorted(rows)}


@app.function(volumes={str(MOUNT): vol}, timeout=24 * 3600, secrets=SECRETS, memory=16384)
def run_job(v3: str, workers: int) -> dict:
    vol.reload()
    if rc.sha256(v3.encode()) != rc.V3_SHA256:
        raise rc.PreflightError("the coding prompt is not v3")
    reqs = task_requests(context())
    sysx, sch = system(v3), schema()
    rows = void_rows(reqs, sysx, sch)
    by_row = {rid: req for _, rid, req, _ in reqs if rid in set(rows)}
    ledger = caps.CappedLedger(CODING / "spend.jsonl", persist=vol.commit)
    start = ledger.spent
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0,
                                 timeout=1800)
    judge = j5.Judge(j2.FABLE, sysx, sch, store_v5(), ledger.view(j2.FABLE),
                     lambda body: j2.call_fable(client, body), persist=vol.commit)
    order = js.send_order(list(by_row))
    rounds = []
    for k in range(ROUNDS):
        stopped = {"reason": None}

        def one(rid):
            if stopped["reason"]:
                return {"state": "not_sent"}
            try:
                return judge.one(rid, by_row[rid])
            except cr.CeilingReached as e:
                stopped["reason"] = str(e)
                return {"state": "not_sent"}

        with concurrent.futures.ThreadPoolExecutor(workers) as pool:
            results = list(pool.map(one, order))
        vol.commit()
        states = {s: sum(1 for r in results if r["state"] == s)
                  for s in ("accepted", "failed", "pending", "not_sent")}
        rounds.append({"round": k + 1, "states": {j2.FABLE: states}, "stopped": stopped["reason"]})
        print(f"{time.strftime('%H:%M:%S')} round {k + 1}: {json.dumps(states)}", flush=True)
        (JUDGES / "run_v2.json").write_text(json.dumps({"rounds": rounds}))
        vol.commit()
        if stopped["reason"] or not states["pending"]:
            break
        time.sleep(ROUND_WAIT)
    out = {"rounds": rounds, "rows_sent": len(order), "ledger_usd_at_start": round(start, 4),
           "ledger_usd_at_end": round(ledger.spent, 4),
           "spent_in_this_job_usd": round(ledger.spent - start, 4),
           "registration_new_spend_usd": round(ledger.new_spend(), 4),
           "anthropic_spent_this_registration_usd": round(ledger.provider_spent["anthropic"], 4),
           "openai_spent_this_registration_usd": round(ledger.provider_spent["openai"], 4)}
    (JUDGES / "run_v2.json").write_text(json.dumps(out))
    vol.commit()
    return out


def final(model: str, rid: str, req: dict, sysx: str, sch: dict, void: set[str]) -> dict | None:
    folder = store_v5() if (model == j2.FABLE and rid in void) else store_of(model)
    path = folder / f"{rid}.{j2.request_key(model, sysx, sch, req)}.json"
    return json.loads(path.read_text()) if path.exists() else None


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=16384)
def route_job(v3: str, void: list[str]) -> dict:
    vol.reload()
    target = JUDGES / "routing.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; routing is done once")
    reqs = task_requests(context())
    sysx, sch = system(v3), schema()
    out = {"tasks": {}}
    attempts = {m: [] for m in j2.JUDGES}
    for task in ("disagreement", "audit"):
        rows = [(rid, req, gates) for t, rid, req, gates in reqs if t == task]
        routed, lone, reasons = {}, [], collections.Counter()
        for rid, req, gates in rows:
            res = {m: final(m, rid, req, sysx, sch, set(void)) for m in j2.JUDGES}
            for m, r in res.items():
                if r is None or r["state"] == "pending":
                    raise ValueError(f"{rid}: {m} has no final answer; run again first")
                attempts[m] += r.get("attempts") or []
            rs = js.route(task, res, gates, "\n".join(f["text"] for f in req["files"]))
            if rs:
                routed[rid] = rs
                reasons.update(rs)
            else:
                lone.append(rid)
        order = js.calibration(lone, task)
        out["tasks"][task] = {"rows": len(rows), "routed": len(routed), "lone": len(lone),
                              "routed_by_reason": dict(sorted(reasons.items())),
                              "routed_reasons": routed, "seed": js.CALIBRATION_SEEDS[task],
                              "calibration_order": order,
                              "calibration_first": order[:jd.CALIBRATION]}
    out["judges"] = {m: {"attempts": len(a),
                         "second_attempts": sum(1 for x in a if x.get("attempt") == 2),
                         "attempt_statuses": sorted({str(x.get("status")) for x in a}),
                         "models_returned": sorted({x["model_returned"] for x in a
                                                    if x.get("model_returned")}),
                         "usd": round(sum(x.get("usd") or 0 for x in a), 4)}
                     for m, a in attempts.items()}
    out["fable_rows_read_from_the_fifth_version"] = len(void)
    target.write_text(json.dumps(out))
    vol.commit()
    return out | {"routing_json_sha256": hashlib.sha256(target.read_bytes()).hexdigest()}


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=16384)
def page_job() -> dict:
    vol.reload()
    c = context()
    routing = json.loads((JUDGES / "routing.json").read_text())
    definitions = helper.load_dictionary(pathlib.Path(
        f"{E2}/outputs/manual_coding/2026-10-03/coders/dictionary_definitions.csv"))
    accessions = helper.load_accessions(pathlib.Path(f"{E3}/reference/accession_releases.csv"))
    html_page, key, counts = page.build(routing, c["packet_of"], c["answers"], c["gates"],
                                        definitions, accessions)
    out = JUDGES.parent.parent / "adjudication" / "stage_a"
    out.mkdir(parents=True, exist_ok=True)
    (out / "author_page.html").write_text(html_page)
    (out / "author_page_key.json").write_text(json.dumps(key, indent=1))
    vol.commit()
    by = collections.Counter((x["task"], x["why_on_page"]) for x in counts)
    summary = {"page_seed": js.PAGE_SEED, "rows_on_page": len(counts),
               "by_task_and_why": {f"{t}_{w}": n for (t, w), n in sorted(by.items())},
               "row_ids_in_page_order": [x["row_id"] for x in counts],
               "assisted_aids_totals": {k: sum(x[k] for x in counts)
                                        for k in ("numbers", "identifiers", "identifiers_mapped",
                                                  "size_match", "size_ambiguous",
                                                  "size_conflict", "size_question")},
               "page_sha256": hashlib.sha256(html_page.encode()).hexdigest(),
               "key_sha256": hashlib.sha256(json.dumps(key, indent=1).encode()).hexdigest(),
               "storage_key": page.KEY, "save_file": page.FILE_NAME,
               "routing_json_sha256": hashlib.sha256((JUDGES / "routing.json").read_bytes())
               .hexdigest()}
    return {"summary": summary, "page": html_page, "key": key}


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-3000:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def void(out: str) -> None:
    result = void_job.remote((LOCAL / PROMPT_V3).read_text())
    write_once(out, result)
    print(json.dumps({k: v for k, v in result.items() if k != "void_row_ids"}, indent=1))


@app.local_entrypoint()
def run(approved: str, out: str, workers: int = 4) -> None:
    log = (LOCAL / "PREREG.log").read_text()
    if not approved.strip() or approved not in log:
        raise SystemExit("the approval of this pass is not in PREREG.log")
    if not SECRETS:
        raise SystemExit("the keys are not in the environment")
    result = run_job.remote((LOCAL / PROMPT_V3).read_text(), workers)
    write_once(out, result)
    print(json.dumps({k: v for k, v in result.items() if k != "rounds"}, indent=1))


@app.local_entrypoint()
def route(void_listing: str, out: str) -> None:
    rows = json.loads((LOCAL / void_listing).read_text())["void_row_ids"]
    result = route_job.remote((LOCAL / PROMPT_V3).read_text(), rows)
    write_once(out, result)
    print(json.dumps({t: {k: v for k, v in d.items() if k in ("rows", "routed", "lone",
                                                              "routed_by_reason")}
                      for t, d in result["tasks"].items()}, indent=1))


@app.local_entrypoint()
def author_page(pages: str, out: str) -> None:
    made = page_job.remote()
    folder = (LOCAL.parent.parent / pages).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "stage_a_author_page.html").write_text(made["page"])
    (folder / "stage_a_author_page_key.json").write_text(json.dumps(made["key"], indent=1))
    write_once(out, made["summary"])
    print(json.dumps({k: v for k, v in made["summary"].items() if k != "row_ids_in_page_order"},
                     indent=1))
    print(folder / "stage_a_author_page.html")
