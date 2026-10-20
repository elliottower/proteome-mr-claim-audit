"""Second version of the Modal wrapper of the control screening (scripts/modal_control_screen_v1.py,
sealed, unchanged and imported). Two changes: (1) the Claude Fable 5.1 requests are sent through
scripts/judge_v4.py, which treats a credit-balance refusal as account-side and not an attempt,
and its exchanges are stored apart (c1_validity/judges/claude-fable-5-1_v4/), so every Fable
request of the first run, refused for want of credit, is sent again; GPT-6 Astra's 132 stored
answers (c1_validity/judges/gpt-6-astra/) stand and are not sent again. (2) The run stops before a
Fable request whose reserved bound would take this job's spend past FABLE_JOB_CAP, under the
ledger's ceiling of 386.09. The packets, prompt, schema, send order, attempt rule and
eligibility rule are unchanged. `combine` reads Fable's answers from the new store and Astra's
from the first, and writes the same structure as the first version, so the first version's
`draw` entrypoint reads it.

    PYTHONPATH=../03_release_resolution/scripts modal run scripts/modal_control_screen_v2.py::tests
    ... modal run --detach scripts/modal_control_screen_v2.py::run --out <json>
    ... modal run scripts/modal_control_screen_v2.py::combine --out <json> --raw outputs/raw/<json>
"""

import collections
import json
import os
import time

import modal

from modal_coding_v2 import CODING, E3, MOUNT, vol
from modal_control_screen_v1 import (CEILING, FOLDER, JUDGE_SECRETS, PROMPT, SCHEMA, E4,
                                     file_sha256, image, load_packets, schema, system,
                                     write_once)

app = modal.App("release-resolution-v2-control-screen-2", image=image)
FABLE_JOB_CAP = 7.00
ROUNDS = 6
ROUND_WAIT = 600
TESTS = ["test_judge_v4.py", "test_control_screen_v1.py"]
FIRST_TESTS = ["test_judge_v3.py", "test_judge_v2.py", "test_control_validity_v1.py"]

with image.imports():
    import concurrent.futures
    import subprocess

    import anthropic

    import coding_runner as cr
    import control_screen_v1 as cs
    import control_validity_v1 as cv
    import judge_v2 as j2
    import judge_v4 as j4


def store_of(model: str):
    return FOLDER / "judges" / (model + j4.STORE_SUFFIX if model == j2.FABLE else model)


@app.function(timeout=1800, cpu=2.0)
def tests_job() -> dict:
    out, code = "", 0
    for cwd, files in ((f"{E4}/tests", TESTS), (f"{E3}/tests", FIRST_TESTS)):
        run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", *files],
                             capture_output=True, text=True, cwd=cwd)
        out += run.stdout + run.stderr
        code = code or run.returncode
    return {"returncode": code, "output": out}


@app.function(volumes={str(MOUNT): vol}, timeout=12 * 3600, secrets=JUDGE_SECRETS, memory=8192)
def run_job(workers: int) -> dict:
    vol.reload()
    order, packets = load_packets()
    sysx, sch = system(), schema()
    start = cr.Ledger(CODING / "spend.jsonl", CEILING).spent
    ledger = cr.Ledger(CODING / "spend.jsonl", min(CEILING, start + FABLE_JOB_CAP),
                       persist=vol.commit)
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0,
                                 timeout=1800)
    judge = j4.Judge(j2.FABLE, sysx, sch, store_of(j2.FABLE), ledger,
                     lambda body: j2.call_fable(client, body), persist=vol.commit)
    rounds = []
    for k in range(ROUNDS):
        stopped = {"reason": None}

        def one(rid):
            if stopped["reason"]:
                return {"state": "not_sent"}
            try:
                return judge.one(rid, packets[rid])
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
        (FOLDER / "run_v2.json").write_text(json.dumps({"rounds": rounds}, indent=1))
        vol.commit()
        if stopped["reason"] or not states["pending"]:
            break
        time.sleep(ROUND_WAIT)
    out = {"rounds": rounds, "ledger_usd_at_start": round(start, 4),
           "ledger_usd_at_end": round(ledger.spent, 4),
           "spent_in_this_job_usd": round(ledger.spent - start, 4),
           "fable_job_cap_usd": FABLE_JOB_CAP, "ceiling_usd_on_the_ledger": CEILING}
    (FOLDER / "run_v2.json").write_text(json.dumps(out, indent=1))
    vol.commit()
    return out


@app.function(volumes={str(MOUNT): vol}, timeout=1800, memory=8192)
def combine_job() -> dict:
    vol.reload()
    order, packets = load_packets()
    rows = {r["row_id"]: r for r in json.loads((FOLDER / "candidates.json").read_text())
            ["candidates"]}
    sysx, sch = system(), schema()
    per, attempts = {}, {m: [] for m in j2.JUDGES}
    quotations = {rid: {} for rid in order}
    for rid in order:
        entry, results = {}, {}
        for m in j2.JUDGES:
            key = j2.request_key(m, sysx, sch, packets[rid])
            path = store_of(m) / f"{rid}.{key}.json"
            result = json.loads(path.read_text()) if path.exists() else None
            if result is None or result["state"] == "pending":
                raise ValueError(f"{rid}: {m} has no final answer; run again before combining")
            results[m] = result
            attempts[m] += result.get("attempts") or []
            d = result.get("decision") or {}
            text = "\n".join(x for x in (packets[rid]["passage"][f] for f in
                                         ("table_header", "before", "text", "after")) if x)
            quote = d.get("quotation")
            entry[m] = {"state": result["state"], "mark": cv.mark_of(result),
                        "reason": d.get("reason"),
                        "quotation_sha256": cv.sha256(quote.encode()) if quote else None,
                        "quotation_in_passage": (quote in text) if quote else None,
                        "request_key": key, "store": store_of(m).name}
            quotations[rid][m] = quote
        r = rows[rid]
        per[rid] = {"record_id": r["record_id"], "side": r["side"],
                    "identifier": r["name_as_written"], "identifier_kind": r["identifier_kind"],
                    "identifier_type": r["identifier_type"], "expected_row": r["expected_row"],
                    "route": r["control_source_key"].split(":")[0], **entry,
                    "label": cs.classify(results[j2.FABLE], results[j2.ASTRA])}
    labels = collections.Counter(e["label"] for e in per.values())
    pairs = collections.Counter(f"{e[j2.FABLE]['mark']}|{e[j2.ASTRA]['mark']}"
                                for e in per.values())
    marks = {m: {x: sum(1 for e in per.values() if e[m]["mark"] == x) for x in cv.MARKS}
             | {"failed": sum(1 for e in per.values() if e[m]["state"] == "failed")}
             for m in j2.JUDGES}
    judges = {m: {"attempts": len(a), "second_attempts": sum(1 for x in a if x.get("attempt") == 2),
                  "attempt_statuses": sorted({str(x.get("status")) for x in a}),
                  "models_returned": sorted({x["model_returned"] for x in a
                                             if x.get("model_returned")}),
                  "usd": round(sum(x.get("usd") or 0 for x in a), 4)} for m, a in attempts.items()}
    run = json.loads((FOLDER / "run_v2.json").read_text())
    eligible = [rid for rid, e in per.items() if e["label"] == "eligible"]
    by = collections.Counter

    def kinds(label):
        return dict(sorted(by(per[r]["identifier_kind"] for r in per
                              if per[r]["label"] == label).items()))

    return {"rule": "PREREG.md, §Study design, item 1, Eligibility: eligible only when both "
                    "judges mark valid; disputed, cannot_mark, invalid and failed-twice "
                    "candidates are excluded",
            "candidates": len(per), "labels": {x: labels.get(x, 0) for x in cs.LABELS},
            "mark_pairs_fable_then_astra": dict(sorted(pairs.items())),
            "eligible": len(eligible), "eligible_at_least_50": len(eligible) >= cs.MINIMUM,
            "eligible_by_kind": kinds("eligible"),
            "eligible_by_side": dict(sorted(by(per[r]["side"] for r in eligible).items())),
            "candidates_by_kind_and_label": {k: dict(sorted(by(
                e["label"] for e in per.values() if e["identifier_kind"] == k).items()))
                for k in sorted({e["identifier_kind"] for e in per.values()})},
            "marks_by_judge": marks, "judges": judges,
            "spend_usd_of_these_answers": round(sum(j["usd"] for j in judges.values()), 4),
            "ledger_usd_after": run.get("ledger_usd_at_end"),
            "ceiling_usd_on_the_ledger": CEILING, "seed": cs.SEND_SEED, "send_order": order,
            "inputs_sha256": {PROMPT: file_sha256(f"{E3}/{PROMPT}"),
                              SCHEMA: file_sha256(f"{E3}/{SCHEMA}"),
                              "volume:04_release_resolution_v2/c1_validity/packets/order.json":
                                  file_sha256(FOLDER / "packets" / "order.json"),
                              "volume:04_release_resolution_v2/c1_validity/candidates.json":
                                  file_sha256(FOLDER / "candidates.json")},
            "packets_sha256": {rid: file_sha256(FOLDER / "packets" / f"{rid}.json")
                               for rid in order},
            "candidates_marked": per, "quotations": quotations}


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-3000:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def run(out: str, workers: int = 4) -> None:
    if not JUDGE_SECRETS:
        raise SystemExit("the keys are not in the environment")
    result = run_job.remote(workers)
    write_once(out, result)
    print(json.dumps(result, indent=1))


@app.local_entrypoint()
def combine(out: str, raw: str) -> None:
    result = combine_job.remote()
    quotations = result.pop("quotations")
    write_once(raw, {"note": "the judges' quotations: third-party text; ignored location, never "
                             "committed", "quotations": quotations})
    write_once(out, result)
    print("written", out)
