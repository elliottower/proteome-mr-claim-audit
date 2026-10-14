"""Third version of the two-judge wrapper (scripts/modal_judge_v2.py, sealed, unchanged; its
image, plan helpers and page builder are reused). It sends only the Claude Fable 5.1 requests,
through scripts/judge_v3.py, storing them under judges/<stage>/claude-fable-5-1_v3 on the volume
(the first run's HTTP 400 rejections are void and stay where they were written); GPT-6 Astra's
answers of the first run are read where they stand and are not sent again. Routing, calibration
and the page are those of the second version, reading Fable from the third version's store.

    modal run scripts/modal_judge_v3.py::tests
    modal run scripts/modal_judge_v3.py::run --stage sa1 --limit 1 --out <outputs json>   (smoke)
    modal run --detach scripts/modal_judge_v3.py::run --stage sa1 --out <outputs json>
    modal run scripts/modal_judge_v3.py::route --stage sa1 --out <outputs json>
    modal run scripts/modal_judge_v3.py::author_page --stage sa1 --pages <planning dir> --out <outputs json>
"""

import json
import os

import modal

from modal_coding_v2 import CODING, E3, LOCAL, MOUNT, vol
from modal_judge import (MODELS, PAGE_SEED, SEEDS, context, image, requests_of, system,
                         write_once)

app = modal.App("release-resolution-judge-v3", image=image)
FABLE_SECRETS = ([modal.Secret.from_dict({"ANTHROPIC_API_KEY": os.environ["ANTHROPIC_API_KEY"]})]
                 if os.environ.get("ANTHROPIC_API_KEY") else [])
CEILING = 100.0

with image.imports():
    import concurrent.futures
    import random
    import subprocess

    import anthropic

    import adjudication_pages as ap
    import coding_runner as cr
    import judge as jd
    import judge_v2 as j2
    import judge_v3 as j3


def store_of(stage: str, model: str):
    sub = model + j3.STORE_SUFFIX if model == j2.FABLE else model
    return CODING / "judges" / stage / sub


@app.function(timeout=900)
def tests_job() -> dict:
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                          "test_judge_v3.py", "test_judge_v2.py", "test_judge.py",
                          "test_adjudication_pages.py"], capture_output=True, text=True,
                         cwd=f"{E3}/tests")
    return {"returncode": run.returncode, "output": run.stdout + run.stderr}


@app.function(volumes={str(MOUNT): vol}, timeout=12 * 3600, secrets=FABLE_SECRETS, memory=8192)
def run_job(stage: str, workers: int, limit: int) -> dict:
    vol.reload()
    reqs = requests_of(context(stage))
    by_row = {rid: req for _, rid, req, _ in reqs}
    schema = json.loads(open(f"{E3}/prompts/judge_schema.json").read())
    ledger = cr.Ledger(CODING / "spend.jsonl", CEILING, persist=vol.commit)
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0,
                                 timeout=1800)
    judge = j3.Judge(j2.FABLE, system(), schema, store_of(stage, j2.FABLE), ledger,
                     lambda body: j2.call_fable(client, body), persist=vol.commit)
    order = j2.send_order(list(by_row))
    if limit:
        order = order[:limit]
    stopped = {"reason": None}

    def one(rid):
        if stopped["reason"]:
            return {"row_id": rid, "state": "not_sent"}
        try:
            return judge.one(rid, by_row[rid])
        except cr.CeilingReached as e:
            stopped["reason"] = str(e)
            return {"row_id": rid, "state": "not_sent"}

    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        results = list(pool.map(one, order))
    vol.commit()
    attempts = [a for r in results for a in (r.get("attempts") or [])]
    return {"stage": stage, "judge": j2.FABLE, "rows_sent_order": len(order),
            "states": {s: sum(r["state"] == s for r in results)
                       for s in ("accepted", "failed", "pending", "not_sent")},
            "attempts": len(attempts),
            "second_attempts": sum(1 for a in attempts if a.get("attempt") == 2),
            "attempt_statuses": sorted({str(a.get("status")) for a in attempts}),
            "validation_failures": sum(1 for a in attempts if a.get("status") == 200
                                       and a.get("errors")),
            "models_returned": sorted({a["model_returned"] for a in attempts
                                       if a.get("model_returned")}),
            "usd": round(sum(a.get("usd") or 0 for a in attempts), 4),
            "stopped_at_ceiling": stopped["reason"], "ledger_spent_usd": round(ledger.spent, 4)}


def stored(stage, model, rid, req, schema, sysx):
    key = j2.request_key(model, sysx, schema, req)
    path = store_of(stage, model) / f"{rid}.{key}.json"
    return json.loads(path.read_text()) if path.exists() else None


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=8192)
def route_job(stage: str) -> dict:
    vol.reload()
    reqs = requests_of(context(stage))
    schema = json.loads(open(f"{E3}/prompts/judge_schema.json").read())
    sysx = system()
    out = {"stage": stage, "tasks": {}}
    for task in ("disagreement", "audit"):
        rows = [(rid, req, gates) for t, rid, req, gates in reqs if t == task]
        routed, lone, reasons = {}, [], {}
        for rid, req, gates in rows:
            res = {m: stored(stage, m, rid, req, schema, sysx) for m in j2.JUDGES}
            rs = j2.route_pair(task, res, gates, "\n".join(f["text"] for f in req["files"]))
            if rs:
                routed[rid] = rs
                for r in rs:
                    reasons[r] = reasons.get(r, 0) + 1
            else:
                lone.append(rid)
        order = jd.calibration_order(lone, SEEDS[stage][task])
        out["tasks"][task] = {"rows": len(rows), "routed": len(routed), "lone": len(lone),
                              "routed_by_reason": reasons, "routed_row_ids": sorted(routed),
                              "routed_reasons": routed, "seed": SEEDS[stage][task],
                              "calibration_order": order,
                              "calibration_first": order[:jd.CALIBRATION]}
    (CODING / "judges" / f"{stage}_routing.json").write_text(json.dumps(out))
    vol.commit()
    return out


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=8192)
def page_job(stage: str) -> dict:
    vol.reload()
    c = context(stage)
    routing = json.loads((CODING / "judges" / f"{stage}_routing.json").read_text())
    held = json.loads((CODING / "inputs" / "abstracts.json").read_text())
    rows = []
    for task in ("disagreement", "audit"):
        t = routing["tasks"][task]
        rows += [(task, rid, "routed") for rid in t["routed_row_ids"]]
        rows += [(task, rid, "calibration") for rid in t["calibration_first"]]
    order = sorted(rows, key=lambda x: x[1])
    random.Random(PAGE_SEED).shuffle(order)
    cards, key = [], {}
    for k, (task, rid, why) in enumerate(order, 1):
        q, p = c["queue"][rid], c["packet_of"][rid]
        abstract = held[p["record_id"]]["abstract"]
        if task == "disagreement":
            one, two = jd.blinded(rid, MODELS)
            blocks = [("q1", c["answers"][one].get(rid), {"passes": c["gates"][one].get(rid)}),
                      ("q2", c["answers"][two].get(rid), {"passes": c["gates"][two].get(rid)})]
            ctl = ap.controls(k, ap.DISAGREE, "reason (required for Neither)")
        else:
            blocks = [("agreed", c["answers"][MODELS[0]][rid],
                       {"passes": c["gates"][MODELS[0]][rid]})]
            ctl = ap.controls(k, ap.AUDIT, "note (what is wrong, if anything)")
        cards.append(ap.card(k, len(order), q, abstract, blocks, ctl))
        key[rid] = {"task": task, "why_on_page": why}
    intro = ("Each card is a dataset mention. Decide it from the abstract alone. On a card with "
             "two answers, the coders disagree: pick the answer the abstract supports, or Neither "
             "with a reason. On a card with one answer, the coders agree: mark it Correct, a "
             "Substantive error (a wrong release, role or attribution state), or Other issue. "
             "Blue and red mark each answer's quoted passages, yellow where they overlap.")
    html_page = ap.page(f"{stage.upper()}: rows for the author", intro, cards,
                        f"{stage}_author_page_amendment04", [], f"{stage}_author_marks.json")
    out = CODING / "adjudication" / stage
    (out / "author_page_amendment04.html").write_text(html_page)
    (out / "author_page_amendment04_key.json").write_text(json.dumps(key, indent=1))
    vol.commit()
    summary = {"stage": stage, "page_seed": PAGE_SEED, "rows_on_page": len(order),
               "by_task_and_why": {f"{t}_{w}": sum(1 for x in order if x[0] == t and x[2] == w)
                                   for t in ("disagreement", "audit")
                                   for w in ("routed", "calibration")},
               "row_ids_in_page_order": [x[1] for x in order]}
    return {"summary": summary, "page": html_page, "key": key}


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-2500:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def run(stage: str, out: str, workers: int = 4, limit: int = 0) -> None:
    if not FABLE_SECRETS:
        raise SystemExit("the key is not in the environment")
    result = run_job.remote(stage, workers, limit)
    write_once(out, result)
    print(json.dumps(result, indent=1))


@app.local_entrypoint()
def route(stage: str, out: str) -> None:
    result = route_job.remote(stage)
    write_once(out, result)
    print(json.dumps({t: {k: v for k, v in d.items() if k in ("rows", "routed", "lone",
                                                              "routed_by_reason")}
                      for t, d in result["tasks"].items()}, indent=1))


@app.local_entrypoint()
def author_page(stage: str, pages: str, out: str) -> None:
    made = page_job.remote(stage)
    folder = (LOCAL / pages).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{stage}_author_page.html").write_text(made["page"])
    (folder / f"{stage}_author_page_key.json").write_text(json.dumps(made["key"], indent=1))
    write_once(out, made["summary"])
    print(json.dumps({k: v for k, v in made["summary"].items() if k != "row_ids_in_page_order"},
                     indent=1))
    print(folder / f"{stage}_author_page.html")
