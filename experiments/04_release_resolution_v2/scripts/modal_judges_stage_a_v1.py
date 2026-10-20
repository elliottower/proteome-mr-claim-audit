"""Modal wrapper of the settling (scripts/settle_v1.py) and the judges (scripts/judges_stage_a_v1.py,
through scripts/judge_v4.py) of the second registration's stage A recode, on the image of
scripts/modal_recode_v1.py. Stops of scripts/spend_caps_v1.py on the one ledger (registration
new spend 300, Anthropic 170). Every judge exchange is stored as it ends and a stored answer is
never sent again; pending requests are sent again in up to ROUNDS rounds ROUND_WAIT seconds
apart.

    PYTHONPATH=../03_release_resolution/scripts modal run scripts/modal_judges_stage_a_v1.py::tests
    ... modal run scripts/modal_judges_stage_a_v1.py::settle --out <json>
    ... modal run scripts/modal_judges_stage_a_v1.py::plan --out <json>
    ... modal run --detach scripts/modal_judges_stage_a_v1.py::run --out <json>
    ... modal run scripts/modal_judges_stage_a_v1.py::route --out <json>

Volume, /04_release_resolution_v2/coding/: settled/stage_a.json; judges/stage_a/tasks.json,
judges/stage_a/<judge store>/ and judges/stage_a/routing.json. Outputs written locally hold row
ids, counts, seeds, reasons and hashes; no source text and no answer content.
"""

import collections
import json
import os
import time

import modal

from modal_coding_v2 import CODING, DEFINITIONS, E2, E3, MOUNT, SECRETS, vol
from modal_recode_v1 import FOLDER, LOCAL, PACKETS, PROMPT_V3, image, write_once
from modal_retrieve_v2 import E4

app = modal.App("release-resolution-v2-judges-stage-a", image=image)
ROUNDS = 6
ROUND_WAIT = 600
JUDGES = FOLDER / "judges" / "stage_a"
TESTS = ["test_settle_v1.py", "test_judges_stage_a_v1.py", "test_judge_v4.py",
         "test_spend_caps_v1.py"]
FIRST_TESTS = ["test_judge.py", "test_judge_v2.py", "test_judge_v3.py",
               "test_adjudication_pages.py", "test_pass_summary.py"]

with image.imports():
    import concurrent.futures
    import hashlib
    import subprocess

    import anthropic
    import httpx

    import coding_runner as cr
    import judge as jd
    import judge_v2 as j2
    import judge_v4 as j4
    import judges_stage_a_v1 as js
    import recode_v1 as rc
    import settle_v1 as st
    import spend_caps_v1 as caps


def sha(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def context() -> dict:
    manifest = json.loads((PACKETS / "manifest.json").read_text())
    packets = {m["name"]: json.loads((PACKETS / f"{m['name']}.json").read_text())
               for m in manifest}
    order = [r["row_id"] for m in manifest for r in packets[m["name"]]["rows"]]
    packet_of = {r["row_id"]: p for p in packets.values() for r in p["rows"]}
    answers, gates = {}, {}
    for m in js.MODELS:
        answers[m] = {}
        for path in sorted((FOLDER / "answers" / "stage_a" / m).glob("*.json")):
            if ".attempt" in path.name:
                continue
            f = json.loads(path.read_text())
            if f["state"] == "accepted":
                for row in f["answer"]["rows"]:
                    answers[m][row["row_id"]] = row
        gates[m] = json.loads((FOLDER / "gate" / "stage_a" / m / "rows.json").read_text())[
            "verdicts"]
    return {"order": order, "packet_of": packet_of, "answers": answers, "gates": gates}


def system(v3: str) -> str:
    return jd.system_text(open(f"{E3}/prompts/judge_prompt.md").read(), v3,
                          open(f"{E2}/{DEFINITIONS}").read())


def schema() -> dict:
    return json.loads(open(f"{E3}/prompts/judge_schema.json").read())


def store_of(model: str):
    return JUDGES / (model + j4.STORE_SUFFIX)


def task_requests(c: dict) -> list[tuple]:
    t = json.loads((JUDGES / "tasks.json").read_text())
    return js.requests(t, c["packet_of"], c["answers"], c["gates"])


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
def settle_job() -> dict:
    vol.reload()
    target = FOLDER / "settled" / "stage_a.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; settling is done once")
    c = context()
    a, b = js.MODELS
    out = st.split(c["order"], c["answers"][a], c["answers"][b], c["gates"][a], c["gates"][b])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out))
    vol.commit()
    return {"rule": "AMENDMENT_07 of the first registration, carried over by PREREG.md item 4",
            "rows": len(c["order"]), "agreed": len(out["agreed"]),
            "settled": len(out["settled"]), "disagreements_left": len(out["disagreements"]),
            "settled_by_attribution_pair": out["settled_by_attribution_pair"],
            "settled_row_ids": sorted(out["settled"]),
            "disagreement_row_ids": out["disagreements"],
            "settled_json_sha256": sha(target)}


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=16384)
def plan_job(v3: str) -> dict:
    vol.reload()
    target = JUDGES / "tasks.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; the tasks are drawn once")
    c = context()
    settled = json.loads((FOLDER / "settled" / "stage_a.json").read_text())
    t = js.tasks(c["order"], settled["agreed"], settled["disagreements"])
    JUDGES.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(t))
    vol.commit()
    reqs = task_requests(c)
    sysx = system(v3)
    bounds = {m: round(sum(j2.bound(m, sysx, r) for _, _, r, _ in reqs), 2) for m in j2.JUDGES}
    chars = sum(len(json.dumps(r, ensure_ascii=False)) for _, _, r, _ in reqs)
    estimate = {}
    for m in j2.JUDGES:
        p, ratio = j2.PRICE[m], j2.MIN_RATIO[m]
        body = sum(len(json.dumps(r, ensure_ascii=False)) for _, _, r, _ in reqs) / ratio
        estimate[m] = {str(o): round((len(sysx) / ratio * p["cached"] * len(reqs)
                                      + body * p["new"] + o * len(reqs) * p["output"]) / 1e6, 2)
                       for o in (1_500, 3_000, 8_192)}
    ledger = caps.CappedLedger(CODING / "spend.jsonl")
    return {"tasks": {k: len(v) for k, v in t.items()}, "audit_seed": js.AUDIT_SEED,
            "agreed_rows": len(settled["agreed"]), "audit_rule": "max(30, ceil(0.10 x agreed))",
            "audit_row_ids": t["audit"], "disagreement_row_ids": t["disagreement"],
            "requests_per_judge": len(reqs), "request_characters": chars,
            "system_characters": len(sysx),
            "system_sha256": hashlib.sha256(sysx.encode()).hexdigest(),
            "reserved_bound_usd": bounds, "estimate_usd": estimate,
            "stops": {"anthropic_spent_this_registration_usd":
                      round(ledger.provider_spent["anthropic"], 4),
                      "anthropic_cap_usd": caps.PROVIDER_CAPS_USD["anthropic"],
                      "registration_new_spend_usd": round(ledger.new_spend(), 4),
                      "registration_room_usd": round(ledger.ceiling - ledger.spent, 4)},
            "tasks_json_sha256": sha(target)}


@app.function(volumes={str(MOUNT): vol}, timeout=24 * 3600, secrets=SECRETS, memory=16384)
def run_job(v3: str, workers: int) -> dict:
    vol.reload()
    if rc.sha256(v3.encode()) != rc.V3_SHA256:
        raise rc.PreflightError("the coding prompt is not v3")
    c = context()
    reqs = task_requests(c)
    by_row = {rid: req for _, rid, req, _ in reqs}
    sysx, sch = system(v3), schema()
    ledger = caps.CappedLedger(CODING / "spend.jsonl", persist=vol.commit)
    start = ledger.spent
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0,
                                 timeout=1800)
    http = httpx.Client(timeout=1800)
    sends = {j2.FABLE: lambda body: j2.call_fable(client, body),
             j2.ASTRA: lambda body: j2.call_astra(http, os.environ["OPENAI_API_KEY"], body)}
    judges = {m: j4.Judge(m, sysx, sch, store_of(m), ledger.view(m), sends[m],
                          persist=vol.commit) for m in j2.JUDGES}
    order = js.send_order(list(by_row))
    rounds = []
    for k in range(ROUNDS):
        stopped = {"reason": None}

        def one(job):
            rid, m = job
            if stopped["reason"]:
                return m, {"state": "not_sent"}
            try:
                return m, judges[m].one(rid, by_row[rid])
            except cr.CeilingReached as e:
                stopped["reason"] = str(e)
                return m, {"state": "not_sent"}

        jobs = [(rid, m) for rid in order for m in j2.JUDGES]
        with concurrent.futures.ThreadPoolExecutor(workers) as pool:
            results = list(pool.map(one, jobs))
        vol.commit()
        states = {m: {s: sum(1 for mm, r in results if mm == m and r["state"] == s)
                      for s in ("accepted", "failed", "pending", "not_sent")} for m in j2.JUDGES}
        rounds.append({"round": k + 1, "states": states, "stopped": stopped["reason"]})
        print(f"{time.strftime('%H:%M:%S')} round {k + 1}: {json.dumps(states)}", flush=True)
        (JUDGES / "run.json").write_text(json.dumps({"rounds": rounds}))
        vol.commit()
        if stopped["reason"] or not any(s["pending"] for s in states.values()):
            break
        time.sleep(ROUND_WAIT)
    out = {"rounds": rounds, "requests_per_judge": len(order),
           "ledger_usd_at_start": round(start, 4), "ledger_usd_at_end": round(ledger.spent, 4),
           "spent_in_this_job_usd": round(ledger.spent - start, 4),
           "registration_new_spend_usd": round(ledger.new_spend(), 4),
           "anthropic_spent_this_registration_usd": round(ledger.provider_spent["anthropic"], 4),
           "openai_spent_this_registration_usd": round(ledger.provider_spent["openai"], 4)}
    (JUDGES / "run.json").write_text(json.dumps(out))
    vol.commit()
    return out


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=16384)
def route_job(v3: str) -> dict:
    vol.reload()
    target = JUDGES / "routing.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; routing is done once")
    c = context()
    reqs = task_requests(c)
    sysx, sch = system(v3), schema()
    out = {"tasks": {}}
    attempts = {m: [] for m in j2.JUDGES}
    for task in ("disagreement", "audit"):
        rows = [(rid, req, gates) for t, rid, req, gates in reqs if t == task]
        routed, lone, reasons = {}, [], collections.Counter()
        for rid, req, gates in rows:
            res = {}
            for m in j2.JUDGES:
                path = store_of(m) / f"{rid}.{j2.request_key(m, sysx, sch, req)}.json"
                res[m] = json.loads(path.read_text()) if path.exists() else None
                if res[m] is None or res[m]["state"] == "pending":
                    raise ValueError(f"{rid}: {m} has no final answer; run again first")
                attempts[m] += res[m].get("attempts") or []
            rs = js.route(task, res, gates, "\n".join(f["text"] for f in req["files"]))
            if rs:
                routed[rid] = rs
                reasons.update(rs)
            else:
                lone.append(rid)
        order = js.calibration(lone, task)
        out["tasks"][task] = {"rows": len(rows), "routed": len(routed), "lone": len(lone),
                              "routed_by_reason": dict(sorted(reasons.items())),
                              "routed_reasons": routed,
                              "seed": js.CALIBRATION_SEEDS[task], "calibration_order": order,
                              "calibration_first": order[:jd.CALIBRATION]}
    out["judges"] = {m: {"attempts": len(a),
                         "second_attempts": sum(1 for x in a if x.get("attempt") == 2),
                         "attempt_statuses": sorted({str(x.get("status")) for x in a}),
                         "models_returned": sorted({x["model_returned"] for x in a
                                                    if x.get("model_returned")}),
                         "usd": round(sum(x.get("usd") or 0 for x in a), 4)}
                     for m, a in attempts.items()}
    target.write_text(json.dumps(out))
    vol.commit()
    return out | {"routing_json_sha256": sha(target)}


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-3000:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def settle(out: str) -> None:
    result = settle_job.remote()
    write_once(out, result)
    print(json.dumps({k: v for k, v in result.items() if not k.endswith("row_ids")}, indent=1))


@app.local_entrypoint()
def plan(out: str) -> None:
    result = plan_job.remote((LOCAL / PROMPT_V3).read_text())
    write_once(out, result)
    print(json.dumps({k: v for k, v in result.items() if not k.endswith("row_ids")}, indent=1))


@app.local_entrypoint()
def run(approved: str, out: str, workers: int = 6) -> None:
    log = (LOCAL / "PREREG.log").read_text()
    if not approved.strip() or approved not in log:
        raise SystemExit("the approval of this pass is not in PREREG.log")
    if not SECRETS:
        raise SystemExit("the keys are not in the environment")
    result = run_job.remote((LOCAL / PROMPT_V3).read_text(), workers)
    write_once(out, result)
    print(json.dumps({k: v for k, v in result.items() if k != "rounds"}, indent=1))


@app.local_entrypoint()
def route(out: str) -> None:
    result = route_job.remote((LOCAL / PROMPT_V3).read_text())
    write_once(out, result)
    print("written", out)
