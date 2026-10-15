"""Modal wrapper of the valid-control marks of C1-A (DEVIATION_02_c1_controls.md, item 2;
scripts/control_validity_v1.py). It reuses the image of scripts/modal_adjudication.py (the
coding image with openpyxl, which the judge modules import) and the
transport of scripts/judge_v3.py (sealed, unchanged): for Claude Fable 5.1 the schema sent drops
the keywords Anthropic does not accept, every answer is validated locally against the full frozen
schema; HTTP 402 and 429 are not attempts and stay pending; at most two attempts otherwise; at
most 8,192 output tokens. No logic of the study is here.

Run from experiments/03_release_resolution (keys from the 1Password pipe, with MODAL_TOKEN_ID and
MODAL_TOKEN_SECRET unset after loading it):

    modal run scripts/modal_control_validity_v1.py::tests
    modal run scripts/modal_control_validity_v1.py::packets --out <json>
    modal run scripts/modal_control_validity_v1.py::plan --out <json>
    modal run --detach scripts/modal_control_validity_v1.py::run --out <json>
    modal run scripts/modal_control_validity_v1.py::combine --out <json> --raw outputs/raw/<json>

Volume, /03_release_resolution/coding/c1a_validity/: packets/<row_id>.json and packets/order.json
(third-party text; never copied out); judges/<model>/ (every exchange, written as it ends, so a
stopped run resumes and a stored answer is never sent again); run.json. The stage's one spend
ledger (coding/spend.jsonl) and its ceiling of 300 US dollars hold these requests. Outputs written
locally hold row ids, marks, the judges' reasons, counts and hashes; the judges' quotations go
only to a file under the ignored outputs/raw/.
"""

import json
import os
import pathlib
import time

import modal

from modal_adjudication import image
from modal_coding_v2 import CHECKS, CODING, E2, E3, LOCAL, MOUNT, vol

app = modal.App("release-resolution-control-validity-v1", image=image)
KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")
JUDGE_SECRETS = ([modal.Secret.from_dict({k: os.environ[k] for k in KEYS})]
                 if all(os.environ.get(k) for k in KEYS) else [])
CEILING = 300.0
ROUNDS = 6
ROUND_WAIT = 600
FOLDER = CODING / "c1a_validity"
PROMPT = "prompts/control_validity_prompt_v1.md"
SCHEMA = "prompts/control_validity_schema_v1.json"
QUEUE = "outputs/coding_queue_2026-10-13.json"
TESTS = ["test_control_validity_v1.py", "test_manifest_mapping_check_v1.py", "test_judge_v3.py",
         "test_judge_v2.py", "test_c1_controls.py", "test_coding_gate.py"]

with image.imports():
    import concurrent.futures
    import hashlib
    import subprocess

    import anthropic
    import httpx

    import coding_runner as cr
    import control_validity_v1 as cv
    import judge_v2 as j2
    import judge_v3 as j3


def file_sha256(path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def system() -> str:
    return open(f"{E3}/{PROMPT}").read()


def schema() -> dict:
    return json.loads(open(f"{E3}/{SCHEMA}").read())


def load_packets() -> tuple[list[str], dict[str, dict]]:
    order = json.loads((FOLDER / "packets" / "order.json").read_text())["order"]
    return order, {rid: json.loads((FOLDER / "packets" / f"{rid}.json").read_text())
                   for rid in order}


@app.function(timeout=1800, cpu=2.0)
def tests_job() -> dict:
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", *TESTS],
                         capture_output=True, text=True, cwd=f"{E3}/tests")
    return {"returncode": run.returncode, "output": run.stdout + run.stderr}


@app.function(volumes={str(MOUNT): vol}, timeout=6 * 3600, memory=32768)
def packets_job() -> dict:
    vol.reload()
    folder = FOLDER / "packets"
    if (folder / "order.json").exists():
        raise FileExistsError(f"{folder} holds packets already")
    controls_path = CODING / "c1a" / "control_set.json"
    controls = json.loads(controls_path.read_text())["control_rows"]
    queue = json.loads(open(f"{E3}/{QUEUE}").read())["queue"]
    checks = [json.loads(l) for c in CHECKS for l in open(f"{E2}/{c}").read().splitlines()
              if l.strip()]
    claims = cv.claims_of_records(queue, checks)
    folder.mkdir(parents=True, exist_ok=True)
    hashes, sources = {}, {}
    for c in controls:
        rec = c["record_id"]
        if rec not in sources:
            sources[rec] = json.loads((CODING.parent / "retrieval" / rec / "result.json")
                                      .read_text())["sources"]
        data = cv.file_bytes(cv.packet(c, sources[rec], claims[rec]))
        (folder / f"{c['row_id']}.json").write_bytes(data)
        hashes[c["row_id"]] = cv.sha256(data)
    order = cv.order([c["row_id"] for c in controls])
    listing = {"seed": cv.SEED, "order": order,
               "packets_sha256": {rid: hashes[rid] for rid in order}}
    (folder / "order.json").write_text(json.dumps(listing, indent=1) + "\n")
    vol.commit()
    return {"controls": len(controls), "records": len(sources), "seed": cv.SEED,
            "order": order, "packets_sha256": listing["packets_sha256"],
            "packet_fields": sorted({k for rid in order for k in json.loads(
                (folder / f"{rid}.json").read_text())}),
            "inputs_sha256": {"volume:coding/c1a/control_set.json": file_sha256(controls_path),
                              QUEUE: file_sha256(f"{E3}/{QUEUE}"),
                              **{f"../02_claims_meta/{c}": file_sha256(f"{E2}/{c}")
                                 for c in CHECKS},
                              **{f"volume:retrieval/{r}/result.json": file_sha256(
                                  CODING.parent / "retrieval" / r / "result.json")
                                  for r in sorted(sources)}}}


@app.function(volumes={str(MOUNT): vol}, timeout=1800, memory=8192)
def plan_job() -> dict:
    vol.reload()
    order, packets = load_packets()
    sysx = system()
    bounds = {m: round(sum(j2.bound(m, sysx, packets[r]) for r in order), 4) for m in j2.JUDGES}
    entries = [json.loads(l) for l in (CODING / "spend.jsonl").read_text().splitlines()
               if l.strip()]
    sa1 = {m: [e["usd"] for e in entries if e.get("model") == m] for m in j2.JUDGES}
    mean = {m: round(sum(v) / len(v), 4) if v else None for m, v in sa1.items()}
    return {"controls": len(order), "requests": 2 * len(order),
            "system_characters": len(sysx),
            "packet_characters": sum(len(json.dumps(p, ensure_ascii=False))
                                     for p in packets.values()),
            "reserved_bound_usd": bounds, "reserved_bound_total_usd": round(sum(bounds.values()), 4),
            "estimate_usd_from_sa1_mean_per_request": {
                "mean_per_request_sa1": mean,
                "total": round(sum(len(order) * (v or 0) for v in mean.values()), 4),
                "note": "SA1 judge requests carried a system instruction of 77,798 characters; "
                        "this one is far shorter, so the estimate is an upper reading"},
            "prices_usd_per_million": j2.PRICE, "min_characters_per_token": j2.MIN_RATIO,
            "max_output_tokens": j2.MAX_OUTPUT,
            "ledger_usd_before": round(sum(e["usd"] for e in entries), 4), "ceiling_usd": CEILING}


@app.function(volumes={str(MOUNT): vol}, timeout=12 * 3600, secrets=JUDGE_SECRETS, memory=8192)
def run_job(workers: int) -> dict:
    vol.reload()
    order, packets = load_packets()
    sysx, sch = system(), schema()
    ledger = cr.Ledger(CODING / "spend.jsonl", CEILING, persist=vol.commit)
    start = ledger.spent
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0,
                                 timeout=1800)
    http = httpx.Client(timeout=1800)
    sends = {j2.FABLE: lambda body: j2.call_fable(client, body),
             j2.ASTRA: lambda body: j2.call_astra(http, os.environ["OPENAI_API_KEY"], body)}
    judges = {m: j3.Judge(m, sysx, sch, FOLDER / "judges" / m, ledger, sends[m],
                          persist=vol.commit) for m in j2.JUDGES}
    rounds = []
    for k in range(ROUNDS):
        stopped = {"reason": None}

        def one(job):
            rid, m = job
            if stopped["reason"]:
                return rid, m, {"state": "not_sent"}
            try:
                return rid, m, judges[m].one(rid, packets[rid])
            except cr.CeilingReached as e:
                stopped["reason"] = str(e)
                return rid, m, {"state": "not_sent"}

        jobs = [(rid, m) for rid in order for m in j2.JUDGES]
        with concurrent.futures.ThreadPoolExecutor(workers) as pool:
            results = list(pool.map(one, jobs))
        vol.commit()
        states = {m: {s: sum(1 for _, mm, r in results if mm == m and r["state"] == s)
                      for s in ("accepted", "failed", "pending", "not_sent")}
                  for m in j2.JUDGES}
        rounds.append({"round": k + 1, "states": states, "stopped": stopped["reason"]})
        print(f"{time.strftime('%H:%M:%S')} round {k + 1}: {json.dumps(states)}", flush=True)
        (FOLDER / "run.json").write_text(json.dumps({"rounds": rounds}, indent=1))
        vol.commit()
        if stopped["reason"] or not any(s["pending"] for s in states.values()):
            break
        time.sleep(ROUND_WAIT)
    out = {"rounds": rounds, "ledger_usd_at_start": round(start, 4),
           "ledger_usd_at_end": round(ledger.spent, 4),
           "spent_in_this_job_usd": round(ledger.spent - start, 4)}
    (FOLDER / "run.json").write_text(json.dumps(out, indent=1))
    vol.commit()
    return out


@app.function(volumes={str(MOUNT): vol}, timeout=1800, memory=8192)
def combine_job() -> dict:
    vol.reload()
    order, packets = load_packets()
    sysx, sch = system(), schema()
    per, combined, attempts = {}, {}, {m: [] for m in j2.JUDGES}
    quotations = {rid: {} for rid in order}
    for rid in order:
        entry = {}
        for m in j2.JUDGES:
            key = j2.request_key(m, sysx, sch, packets[rid])
            path = FOLDER / "judges" / m / f"{rid}.{key}.json"
            result = json.loads(path.read_text()) if path.exists() else None
            if result is None or result["state"] == "pending":
                raise ValueError(f"{rid}: {m} has no final answer; run again before combining")
            attempts[m] += result.get("attempts") or []
            d = result.get("decision") or {}
            text = "\n".join(x for x in (packets[rid]["passage"][f] for f in
                                         ("table_header", "before", "text", "after")) if x)
            quote = d.get("quotation")
            entry[m] = {"state": result["state"], "mark": cv.mark_of(result),
                        "reason": d.get("reason"),
                        "quotation_sha256": cv.sha256(quote.encode()) if quote else None,
                        "quotation_in_passage": (quote in text) if quote else None,
                        "request_key": key}
            quotations[rid][m] = quote
        combined[rid] = cv.combine(*(entry[m]["mark"] for m in j2.JUDGES))
        per[rid] = entry | {"combined": combined[rid]}
    marks = {m: {x: sum(1 for e in per.values() if e[m]["mark"] == x) for x in cv.MARKS}
             | {"failed": sum(1 for e in per.values() if e[m]["state"] == "failed")}
             for m in j2.JUDGES}
    judges = {m: {"attempts": len(a), "second_attempts": sum(1 for x in a if x.get("attempt") == 2),
                  "attempt_statuses": sorted({str(x.get("status")) for x in a}),
                  "models_returned": sorted({x["model_returned"] for x in a
                                             if x.get("model_returned")}),
                  "usd": round(sum(x.get("usd") or 0 for x in a), 4)} for m, a in attempts.items()}
    run = json.loads((FOLDER / "run.json").read_text())
    return {"rule": "DEVIATION_02_c1_controls.md, item 2: valid when both judges mark valid, "
                    "invalid when both mark invalid; any other pair retained as valid",
            "counts": cv.counts(combined), "valid_controls_at_least_50": cv.counts(
                combined)["valid_controls"] >= 50,
            "marks_by_judge": marks, "judges": judges,
            "spend_usd": round(sum(j["usd"] for j in judges.values()), 4),
            "ledger_usd_after": run.get("ledger_usd_at_end"), "ceiling_usd": CEILING,
            "seed": cv.SEED, "send_order": order,
            "inputs_sha256": {PROMPT: file_sha256(f"{E3}/{PROMPT}"),
                              SCHEMA: file_sha256(f"{E3}/{SCHEMA}"),
                              "volume:coding/c1a_validity/packets/order.json":
                                  file_sha256(FOLDER / "packets" / "order.json"),
                              "volume:coding/c1a/control_set.json":
                                  file_sha256(CODING / "c1a" / "control_set.json")},
            "packets_sha256": {rid: file_sha256(FOLDER / "packets" / f"{rid}.json")
                               for rid in order},
            "controls": per, "quotations": quotations}


def write_once(out: str, data) -> None:
    target = LOCAL / out
    if target.exists():
        raise FileExistsError(f"{target} exists; it is written once")
    target.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-3000:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def packets(out: str) -> None:
    result = packets_job.remote()
    write_once(out, result)
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("order", "packets_sha256", "inputs_sha256")}, indent=1))


@app.local_entrypoint()
def plan(out: str) -> None:
    result = plan_job.remote()
    write_once(out, result)
    print(json.dumps(result, indent=1))


@app.local_entrypoint()
def run(out: str, workers: int = 8) -> None:
    if not JUDGE_SECRETS:
        raise SystemExit("the keys are not in the environment")
    result = run_job.remote(workers)
    write_once(out, result)
    print(json.dumps(result, indent=1))


@app.local_entrypoint()
def combine(out: str, raw: str) -> None:
    result = combine_job.remote()
    quotations = result.pop("quotations")
    (LOCAL / raw).parent.mkdir(parents=True, exist_ok=True)
    write_once(raw, {"note": "the judges' quotations: third-party text; ignored location, never "
                             "committed", "quotations": quotations})
    write_once(out, result)
    print(json.dumps({k: v for k, v in result.items()
                      if k in ("counts", "valid_controls_at_least_50", "marks_by_judge",
                               "judges", "spend_usd", "ledger_usd_after")}, indent=1))
