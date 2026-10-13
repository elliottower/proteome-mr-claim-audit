"""Modal wrapper for the judge of Amendment 3 on a pass (scripts/judge.py), the routing and
calibration samples, and the author's one page of routed and calibration rows
(scripts/adjudication_pages.py). It reuses the image of scripts/modal_adjudication.py; no logic of
the study is here.

    modal run scripts/modal_judge.py::tests
    modal run --detach scripts/modal_judge.py::run --stage sa1 --out <outputs json>
    modal run scripts/modal_judge.py::route --stage sa1 --out <outputs json>
    modal run scripts/modal_judge.py::author_page --stage sa1 --pages <planning dir> --out <outputs json>

The judge's decisions (which quote sources) stay on the volume; outputs hold counts, row ids,
routing reasons and seeds. The page holds abstracts and goes to the volume and the ignored
planning folder only, with its key (which rows are routed, which are calibration, the judge's
answers' hashes) beside it.
"""

import json
import os

import modal

from modal_adjudication import image
from modal_coding_v2 import CODING, E2, E3, LOCAL, MOUNT, vol

app = modal.App("release-resolution-judge", image=image)
MODELS = ("claude-sonnet-5-5", "gpt-6.1-sol")
SEEDS = {"sa1": {"disagreement": 20261018, "audit": 20261019, "escalated": 20261020},
         "stage_a": {"disagreement": 20261021, "audit": 20261022, "escalated": 20261023},
         "stage_b": {"disagreement": 20261024, "audit": 20261025, "escalated": 20261026}}
PAGE_SEED = 20261027
JUDGE_SECRETS = ([modal.Secret.from_dict({"GEMINI_API_KEY": os.environ["GEMINI_API_KEY"]})]
                 if os.environ.get("GEMINI_API_KEY") else [])

with image.imports():
    import concurrent.futures
    import csv
    import hashlib
    import random
    import subprocess

    import httpx

    import adjudication_pages as ap
    import coding_gate as gate
    import coding_runner as cr
    import judge as jd
    import source_scanner_v2 as scanner


@app.function(timeout=900)
def tests_job() -> dict:
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                          "test_judge.py", "test_adjudication_pages.py", "test_coding_runner.py"],
                         capture_output=True, text=True, cwd=f"{E3}/tests")
    return {"returncode": run.returncode, "output": run.stdout + run.stderr}


def context(stage: str) -> dict:
    patterns = json.loads(open(f"{E3}/reference/c1_scanner_patterns_v2.json").read())
    with open(f"{E3}/reference/accession_releases.csv", newline="") as fh:
        table = list(csv.DictReader(fh))
    dictionary = gate.dictionary_rows(f"{E2}/dataset_dictionary.csv")
    mapper = scanner.Mapper(patterns, table, list(dictionary.values()))
    queue = {r["row_id"]: r for r in json.loads((CODING / "inputs" / "queue.json").read_text())["queue"]}
    folder = CODING / "packets" / stage
    packets = {m["name"]: json.loads((folder / f"{m['name']}.json").read_text())
               for m in json.loads((folder / "manifest.json").read_text())}
    packet_of = {r["row_id"]: p for p in packets.values() for r in p["rows"]}
    answers, gates = {}, {}
    for model in MODELS:
        answers[model], gates[model] = {}, {}
        for path in sorted((CODING / "answers" / stage / model).glob("*.json")):
            if ".attempt" in path.name:
                continue
            f = json.loads(path.read_text())
            if f["state"] != "accepted":
                continue
            p = packets[f["name"]]
            frozen = {x["file_id"]: {"key": x["file_id"], "sha256": "", "text": x["text"]}
                      for x in p["files"]}
            sides = {r["row_id"]: r["side"] for r in p["rows"]}
            for row in f["answer"]["rows"]:
                answers[model][row["row_id"]] = row
                gates[model][row["row_id"]] = gate.gate_row(row, sides[row["row_id"]], p, frozen,
                                                            patterns, mapper, dictionary)["passes"]
    manifest = json.loads((CODING / "adjudication" / stage / "manifest.json").read_text())
    return {"queue": queue, "packet_of": packet_of, "answers": answers, "gates": gates,
            "disagreement": manifest["disagreement_row_ids"], "audit": manifest["audit_row_ids"]}


def requests_of(c: dict) -> list[tuple[str, str, dict, list[bool]]]:
    out = []
    for task in ("disagreement", "audit"):
        for rid in c[task]:
            p, q = c["packet_of"][rid], c["queue"][rid]
            if task == "disagreement":
                one, two = jd.blinded(rid, MODELS)
                pairs = [(c["answers"][m].get(rid), c["gates"][m].get(rid, False)) for m in (one, two)]
            else:
                pairs = [(c["answers"][MODELS[0]][rid], c["gates"][MODELS[0]][rid])]
            out.append((task, rid, jd.judge_request(task, p, q, pairs), [g for _, g in pairs]))
    return out


def system() -> str:
    return jd.system_text(open(f"{E3}/prompts/judge_prompt.md").read(),
                          open(f"{E3}/prompts/coding_prompt_v2.md").read(),
                          open(f"{E2}/outputs/manual_coding/2026-10-03/coders/"
                               "dictionary_definitions.csv").read())


@app.function(volumes={str(MOUNT): vol}, timeout=12 * 3600, secrets=JUDGE_SECRETS, memory=8192)
def run_job(stage: str, workers: int) -> dict:
    vol.reload()
    c = context(stage)
    schema = json.loads(open(f"{E3}/prompts/judge_schema.json").read())
    ledger = cr.Ledger(CODING / "spend.jsonl", 100.0, persist=vol.commit)
    http = httpx.Client(timeout=1800)
    judge = jd.Judge(system(), schema, CODING / "judge" / stage, ledger,
                     lambda body: jd.call(http, os.environ["GEMINI_API_KEY"], body),
                     persist=vol.commit)
    results, stopped, errors = [], None, []
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        futures = {pool.submit(judge.one, rid, req): (task, rid) for task, rid, req, _ in requests_of(c)}
        for f in concurrent.futures.as_completed(futures):
            try:
                results.append(f.result())
            except cr.CeilingReached as e:
                stopped = str(e)
            except Exception as e:
                errors.append({"row_id": futures[f][1], "error": f"{type(e).__name__}: {e}"[:300]})
    vol.commit()
    attempts = [a for r in results for a in r.get("attempts", [])]
    return {"stage": stage, "requests": len(futures),
            "states": {s: sum(r["state"] == s for r in results) for s in ("accepted", "failed", "pending")},
            "not_sent_ceiling": len(futures) - len(results), "stopped": stopped, "errors": errors,
            "models_returned": sorted({a["model_returned"] for a in attempts if a.get("model_returned")}),
            "re_requests": sum(a["attempt"] > 1 for a in attempts if "attempt" in a),
            "judge_usd": round(sum(a.get("usd", 0) for a in attempts), 4),
            "ledger_spent_usd": round(ledger.spent, 4)}


def judged(stage: str, c: dict) -> dict:
    out = {}
    for task, rid, req, gates in requests_of(c):
        key = jd.request_key(system(), json.loads(open(f"{E3}/prompts/judge_schema.json").read()), req)
        path = CODING / "judge" / stage / f"{rid}.{key}.json"
        result = json.loads(path.read_text()) if path.exists() else {"state": "pending"}
        files = "\n".join(f["text"] for f in req["files"])
        out[rid] = {"task": task, "result": result, "reasons": jd.route(task, result, gates, files)}
    return out


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=8192)
def route_job(stage: str) -> dict:
    vol.reload()
    c = context(stage)
    j = judged(stage, c)
    out = {"stage": stage, "tasks": {}}
    for task in ("disagreement", "audit"):
        rows = {rid: v for rid, v in j.items() if v["task"] == task}
        routed = {rid: v["reasons"] for rid, v in rows.items() if v["reasons"]}
        lone = sorted(rid for rid, v in rows.items() if not v["reasons"])
        order = jd.calibration_order(lone, SEEDS[stage][task])
        reasons = {}
        for rs in routed.values():
            for r in rs:
                reasons[r] = reasons.get(r, 0) + 1
        out["tasks"][task] = {"rows": len(rows), "routed": len(routed), "lone": len(lone),
                              "routed_by_reason": reasons, "routed_row_ids": sorted(routed),
                              "routed_reasons": routed, "seed": SEEDS[stage][task],
                              "calibration_order": order,
                              "calibration_first": order[:jd.CALIBRATION]}
    (CODING / "judge" / f"{stage}_routing.json").write_text(json.dumps(out))
    vol.commit()
    return out


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=8192)
def page_job(stage: str) -> dict:
    vol.reload()
    c = context(stage)
    routing = json.loads((CODING / "judge" / f"{stage}_routing.json").read_text())
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
            blocks = [("agreed", c["answers"][MODELS[0]][rid], {"passes": c["gates"][MODELS[0]][rid]})]
            ctl = ap.controls(k, ap.AUDIT, "note (what is wrong, if anything)")
        cards.append(ap.card(k, len(order), q, abstract, blocks, ctl))
        key[rid] = {"task": task, "why_on_page": why}
    intro = ("Each card is a dataset mention. On a card with two answers, the coders disagree: "
             "pick the answer the abstract supports, or Neither with a reason. On a card with one "
             "answer, the coders agree: mark it Correct, a Substantive error (a wrong release, "
             "role or attribution state), or Other issue. Blue and red mark each answer's quoted "
             "passages, yellow where they overlap.")
    html_page = ap.page(f"{stage.upper()}: rows for the author", intro, cards,
                        f"{stage}_author_page_amendment03", [], f"{stage}_author_marks.json")
    out = CODING / "adjudication" / stage
    (out / "author_page_amendment03.html").write_text(html_page)
    (out / "author_page_amendment03_key.json").write_text(json.dumps(key, indent=1))
    vol.commit()
    summary = {"stage": stage, "page_seed": PAGE_SEED, "rows_on_page": len(order),
               "by_task_and_why": {f"{t}_{w}": sum(1 for x in order if x[0] == t and x[2] == w)
                                   for t in ("disagreement", "audit") for w in ("routed", "calibration")},
               "row_ids_in_page_order": [x[1] for x in order],
               "key_sha256": hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()}
    return {"summary": summary, "page": html_page, "key": key}


def write_once(out: str, data) -> None:
    target = LOCAL / out
    if target.exists():
        raise FileExistsError(f"{target} exists; it is written once")
    target.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-2500:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def run(stage: str, out: str, workers: int = 8) -> None:
    if not JUDGE_SECRETS:
        raise SystemExit("GEMINI_API_KEY is not in the environment")
    result = run_job.remote(stage, workers)
    write_once(out, result)
    print(json.dumps(result, indent=1))


@app.local_entrypoint()
def route(stage: str, out: str) -> None:
    result = route_job.remote(stage)
    write_once(out, result)
    print(json.dumps({t: {k: v for k, v in d.items() if k in ("rows", "routed", "lone", "routed_by_reason")}
                      for t, d in result["tasks"].items()}, indent=1))


@app.local_entrypoint()
def author_page(stage: str, pages: str, out: str) -> None:
    made = page_job.remote(stage)
    folder = (LOCAL / pages).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{stage}_author_page.html").write_text(made["page"])
    (folder / f"{stage}_author_page_key.json").write_text(json.dumps(made["key"], indent=1))
    write_once(out, made["summary"])
    print(json.dumps({k: v for k, v in made["summary"].items() if k != "row_ids_in_page_order"}, indent=1))
    print(folder / f"{stage}_author_page.html")
