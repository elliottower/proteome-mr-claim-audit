"""Modal wrapper for the two judges of Amendment 4 on a pass (scripts/judge_v2.py), their
routing and calibration samples, and the author's one page. Second version of
scripts/modal_judge.py (sealed, unchanged; its context, request and page helpers are imported).

    modal run scripts/modal_judge_v2.py::tests
    modal run scripts/modal_judge_v2.py::plan --stage sa1 --out <outputs json>
    modal run --detach scripts/modal_judge_v2.py::run --stage sa1 --out <outputs json>
    modal run scripts/modal_judge_v2.py::route --stage sa1 --out <outputs json>
    modal run scripts/modal_judge_v2.py::author_page --stage sa1 --pages <planning dir> --out <outputs json>

`plan` writes, with no request, the reserved bound of every planned request. `run` sends the
rows in the order of seed 20261028, both judges' requests for a row together, each exchange stored
on the volume as it ends, and stops before a request whose bound would cross the ceiling of 100
US dollars; a second run resumes. Outputs hold counts, row ids, routing reasons and seeds; the
judges' answers stay on the volume.
"""

import json
import os

import modal

from modal_coding_v2 import CODING, E3, LOCAL, MOUNT, vol
from modal_judge import (MODELS, PAGE_SEED, SEEDS, context, image, requests_of, system,
                         write_once)

app = modal.App("release-resolution-judge-v2", image=image)
KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")
JUDGE_SECRETS = ([modal.Secret.from_dict({k: os.environ[k] for k in KEYS})]
                 if all(os.environ.get(k) for k in KEYS) else [])
CEILING = 100.0

with image.imports():
    import concurrent.futures
    import random
    import subprocess

    import anthropic
    import httpx

    import adjudication_pages as ap
    import coding_runner as cr
    import judge as jd
    import judge_v2 as j2


@app.function(timeout=900)
def tests_job() -> dict:
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                          "test_judge_v2.py", "test_judge.py", "test_adjudication_pages.py",
                          "test_coding_runner.py"], capture_output=True, text=True,
                         cwd=f"{E3}/tests")
    return {"returncode": run.returncode, "output": run.stdout + run.stderr}


def planned(stage: str) -> tuple[dict, list]:
    c = context(stage)
    return c, requests_of(c)


@app.function(volumes={str(MOUNT): vol}, timeout=1800, memory=8192)
def plan_job(stage: str) -> dict:
    vol.reload()
    _, reqs = planned(stage)
    sysx = system()
    bounds = {m: round(sum(j2.bound(m, sysx, req) for _, _, req, _ in reqs), 2) for m in j2.JUDGES}
    entries = [json.loads(l) for l in (CODING / "spend.jsonl").read_text().splitlines() if l.strip()]
    return {"stage": stage, "rows": len(reqs), "requests": 2 * len(reqs),
            "rows_by_task": {t: sum(1 for x in reqs if x[0] == t) for t in ("disagreement", "audit")},
            "reserved_bound_usd": bounds, "reserved_bound_total_usd": round(sum(bounds.values()), 2),
            "system_characters": len(sysx), "prices_usd_per_million": j2.PRICE,
            "min_characters_per_token": j2.MIN_RATIO, "max_output_tokens": j2.MAX_OUTPUT,
            "ledger_usd_before": round(sum(e["usd"] for e in entries), 4), "ceiling_usd": CEILING}


@app.function(volumes={str(MOUNT): vol}, timeout=12 * 3600, secrets=JUDGE_SECRETS, memory=8192)
def run_job(stage: str, workers: int) -> dict:
    vol.reload()
    _, reqs = planned(stage)
    by_row = {rid: req for _, rid, req, _ in reqs}
    schema = json.loads(open(f"{E3}/prompts/judge_schema.json").read())
    ledger = cr.Ledger(CODING / "spend.jsonl", CEILING, persist=vol.commit)
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0,
                                 timeout=1800)
    http = httpx.Client(timeout=1800)
    sends = {j2.FABLE: lambda body: j2.call_fable(client, body),
             j2.ASTRA: lambda body: j2.call_astra(http, os.environ["OPENAI_API_KEY"], body)}
    sysx = system()
    judges = {m: j2.Judge(m, sysx, schema, CODING / "judges" / stage / m, ledger, sends[m],
                          persist=vol.commit) for m in j2.JUDGES}
    stopped = {"reason": None}
    results: dict[str, dict] = {}

    def row(rid: str) -> dict:
        if stopped["reason"]:
            return {"row_id": rid, "not_sent": True}
        out = {"row_id": rid}
        with concurrent.futures.ThreadPoolExecutor(2) as pair:
            fs = {m: pair.submit(judges[m].one, rid, by_row[rid]) for m in j2.JUDGES}
            for m, f in fs.items():
                try:
                    out[m] = f.result()
                except cr.CeilingReached as e:
                    stopped["reason"] = str(e)
                    out[m] = None
        return out

    order = j2.send_order(list(by_row))
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        for r in pool.map(row, order):
            results[r["row_id"]] = r
    vol.commit()
    counts = {m: {s: sum(1 for r in results.values() if (r.get(m) or {}).get("state") == s)
                  for s in ("accepted", "failed", "pending")} for m in j2.JUDGES}
    for m in j2.JUDGES:
        counts[m]["not_sent_ceiling"] = sum(1 for r in results.values()
                                            if r.get("not_sent") or (m in r and r[m] is None))
        attempts = [a for r in results.values() for a in ((r.get(m) or {}).get("attempts") or [])]
        counts[m]["attempts"] = len(attempts)
        counts[m]["second_attempts"] = sum(1 for a in attempts if a.get("attempt") == 2)
        counts[m]["models_returned"] = sorted({a["model_returned"] for a in attempts
                                               if a.get("model_returned")})
        counts[m]["usd"] = round(sum(a.get("usd") or 0 for a in attempts), 4)
    return {"stage": stage, "rows": len(order), "send_seed": j2.SEND_SEED, "judges": counts,
            "stopped_at_ceiling": stopped["reason"], "ledger_spent_usd": round(ledger.spent, 4)}


def stored(stage: str, model: str, rid: str, req: dict, schema: dict, sysx: str) -> dict | None:
    key = j2.request_key(model, sysx, schema, req)
    path = CODING / "judges" / stage / model / f"{rid}.{key}.json"
    return json.loads(path.read_text()) if path.exists() else None


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=8192)
def route_job(stage: str) -> dict:
    vol.reload()
    _, reqs = planned(stage)
    schema = json.loads(open(f"{E3}/prompts/judge_schema.json").read())
    sysx = system()
    out = {"stage": stage, "tasks": {}}
    for task in ("disagreement", "audit"):
        rows = [(rid, req, gates) for t, rid, req, gates in reqs if t == task]
        routed, lone, reasons = {}, [], {}
        for rid, req, gates in rows:
            res = {m: stored(stage, m, rid, req, schema, sysx) for m in j2.JUDGES}
            files = "\n".join(f["text"] for f in req["files"])
            rs = j2.route_pair(task, res, gates, files)
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
def plan(stage: str, out: str) -> None:
    result = plan_job.remote(stage)
    write_once(out, result)
    print(json.dumps(result, indent=1))


@app.local_entrypoint()
def run(stage: str, out: str, workers: int = 4) -> None:
    if not JUDGE_SECRETS:
        raise SystemExit("the keys are not in the environment")
    result = run_job.remote(stage, workers)
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
