"""Modal wrapper of the control screening of the second release-resolution registration
(PREREG.md, §Study design, item 1; scripts/control_screen_v1.py holds the logic). It reuses the
image of scripts/modal_retrieve_v2.py and the transport of the first registration's
scripts/judge_v3.py (sealed, unchanged): for Claude Fable 5.1 the schema sent drops the keywords
Anthropic does not accept, and every answer is validated locally against the full frozen schema;
HTTP 402 and 429 are not attempts and stay pending, sent again in up to ROUNDS rounds ROUND_WAIT
seconds apart; at most two attempts otherwise; at most 8,192 output tokens. The judges see only
the packet: no coder answer, recovery status or diagnostic, and not each other's mark.

Run from experiments/04_release_resolution_v2 with the first registration's scripts on the local
path (keys from the 1Password pipe, with MODAL_TOKEN_ID and MODAL_TOKEN_SECRET unset after
loading it):

    PYTHONPATH=../03_release_resolution/scripts modal run scripts/modal_control_screen_v1.py::tests
    ... modal run --detach scripts/modal_control_screen_v1.py::scan --out <json>
    ... modal run scripts/modal_control_screen_v1.py::packets --out <json>
    ... modal run scripts/modal_control_screen_v1.py::plan --out <json>
    ... modal run --detach scripts/modal_control_screen_v1.py::run --out <json>
    ... modal run scripts/modal_control_screen_v1.py::combine --out <json> --raw outputs/raw/<json>
    ... modal run scripts/modal_control_screen_v1.py::draw --marks <json> --out <json>

Volume, /04_release_resolution_v2/: c1/<record>.json (each record's scanner matches, written as
the record ends); c1_validity/candidates.json; c1_validity/packets/<row_id>.json and
packets/order.json (third-party text, never copied out); c1_validity/judges/<model>/ (every
exchange, written as it ends, so a stopped run resumes and a stored answer is never sent again);
c1_validity/run.json; c1a/control_set.json. Spend goes to the one ledger of both registrations
(/03_release_resolution/coding/spend.jsonl), whose ceiling here is the first registration's spend
(86.09 US dollars) plus this registration's 300. Outputs written locally hold row ids, record ids,
identifiers of public registries, marks, the judges' reasons, counts and hashes; the judges'
quotations go only to a file under the ignored outputs/raw/.
"""

import collections
import hashlib
import json
import os
import pathlib
import time

import modal

from modal_coding_v2 import CHECKS, CODING, E2, E3, MOUNT, vol
from modal_retrieve_v2 import CLAIMS, E4, LOCAL, PAPER1, REMOTE, ROOT4, image, read_inputs

app = modal.App("release-resolution-v2-control-screen", image=image)
KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")
JUDGE_SECRETS = ([modal.Secret.from_dict({k: os.environ[k] for k in KEYS})]
                 if all(os.environ.get(k) for k in KEYS) else [])
FIRST_REGISTRATION_SPEND = 86.09
NEW_SPEND_CEILING = 300.0
CEILING = FIRST_REGISTRATION_SPEND + NEW_SPEND_CEILING
ROUNDS = 6
ROUND_WAIT = 600
FOLDER = ROOT4 / "c1_validity"
PROMPT = "prompts/control_validity_prompt_v1.md"
SCHEMA = "prompts/control_validity_schema_v1.json"
FIRST_VALIDITY_RUN = "outputs/c1a_control_validity_2026-10-14.json"
TESTS = ["test_control_screen_v1.py"]
FIRST_TESTS = ["test_control_validity_v1.py", "test_judge_v3.py", "test_judge_v2.py",
               "test_c1_controls.py", "test_source_scanner_v2.py"]

with image.imports():
    import concurrent.futures
    import csv
    import subprocess

    import anthropic
    import httpx

    import coding_queue as q
    import coding_runner as cr
    import control_screen_v1 as cs
    import control_validity_v1 as cv
    import judge_v2 as j2
    import judge_v3 as j3
    import source_scanner_v2 as scanner


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


def ledger_lines() -> list[dict]:
    return [json.loads(line) for line in (CODING / "spend.jsonl").read_text().splitlines()
            if line.strip()]


@app.function(timeout=1800, cpu=2.0)
def tests_job() -> dict:
    out, code = "", 0
    for cwd, files in ((f"{E4}/tests", TESTS),
                       (f"{E3}/tests", FIRST_TESTS)):
        run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", *files],
                             capture_output=True, text=True, cwd=cwd)
        out += run.stdout + run.stderr
        code = code or run.returncode
    return {"returncode": code, "output": out}


def reference():
    patterns = json.loads(open(f"{E3}/reference/c1_scanner_patterns_v2.json").read())
    with open(f"{E3}/reference/accession_releases.csv", newline="") as fh:
        table = list(csv.DictReader(fh))
    with open(f"{E2}/dataset_dictionary.csv", newline="") as fh:
        dictionary = list(csv.DictReader(fh))
    return patterns, table, dictionary


@app.function(volumes={str(MOUNT): vol}, timeout=6 * 3600, cpu=1.0, memory=16384, retries=2,
              max_containers=16)
def scan_record_job(record_id: str) -> dict:
    out = ROOT4 / "c1" / f"{record_id}.json"
    vol.reload()
    if out.exists():
        held = json.loads(out.read_text())
        return {"record_id": record_id, "units": held["units"], "found": len(held["found"])}
    patterns, table, dictionary = reference()
    mapper = scanner.Mapper(patterns, table, dictionary)
    result = json.loads((REMOTE / record_id / "result.json").read_text())
    held = cs.scan_record(record_id, result["sources"], patterns, mapper)
    out.parent.mkdir(parents=True, exist_ok=True)
    partial = out.with_suffix(".partial")
    partial.write_text(json.dumps(held))
    partial.rename(out)
    vol.commit()
    return {"record_id": record_id, "units": held["units"], "found": len(held["found"])}


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=16384)
def candidates_job(records: list[str]) -> dict:
    vol.reload()
    target = FOLDER / "candidates.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; the candidates are built once")
    held = [json.loads((ROOT4 / "c1" / f"{r}.json").read_text()) for r in records]
    found = [c for h in held for c in h["found"]]
    rows = cs.candidates(found, q.side_rows(pathlib.Path(f"{E2}/dataset_dictionary.csv")))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"candidates": rows}))
    vol.commit()
    count = collections.Counter
    per_record = count(r["record_id"] for r in rows)
    return {"records_scanned": len(held), "units": sum(h["units"] for h in held),
            "matches": len(found), "records_with_a_match": len({c["record_id"] for c in found}),
            "candidates": len(rows), "records_with_a_candidate": len(per_record),
            "candidates_after_a_cap_of_5_per_record": sum(min(n, cs.PER_RECORD)
                                                          for n in per_record.values()),
            "by_side": dict(sorted(count(r["side"] for r in rows).items())),
            "by_identifier_kind": dict(sorted(count(r["identifier_kind"] for r in rows).items())),
            "by_identifier_type": dict(sorted(count(r["identifier_type"] for r in rows).items())),
            "by_kind_and_side": dict(sorted(count(f"{r['identifier_kind']}|{r['side']}"
                                                  for r in rows).items())),
            "by_route": dict(sorted(count(r["control_source_key"].split(":")[0]
                                          for r in rows).items())),
            "expected_rows": len({r["expected_row"] for r in rows}),
            "per_record": dict(sorted(per_record.items())),
            "candidate_rows": [{k: r[k] for k in ("row_id", "record_id", "side",
                                                   "name_as_written", "expected_row",
                                                   "identifier_kind", "identifier_type",
                                                   "control_source_key", "control_unit_id")}
                               for r in rows],
            "inputs_sha256": {f"volume:04_release_resolution_v2/c1/{r}.json":
                              file_sha256(ROOT4 / "c1" / f"{r}.json") for r in records}}


@app.function(timeout=24 * 3600)
def scan_job(records: list[str]) -> dict:
    done = list(scan_record_job.map(records))
    return candidates_job.remote(records) | {"scan_calls": len(done)}


@app.function(volumes={str(MOUNT): vol}, timeout=6 * 3600, memory=16384)
def packets_job(claim_record_ids: list[str]) -> dict:
    vol.reload()
    folder = FOLDER / "packets"
    if (folder / "order.json").exists():
        raise FileExistsError(f"{folder} holds packets already")
    rows = json.loads((FOLDER / "candidates.json").read_text())["candidates"]
    records = sorted({r["record_id"] for r in rows})
    checks = [json.loads(line) for c in CHECKS for line in open(f"{E2}/{c}").read().splitlines()
              if line.strip()]
    claims = cv.claims_of_records(cs.claim_queue(claim_record_ids, records), checks)
    folder.mkdir(parents=True, exist_ok=True)
    hashes, sources = {}, {}
    for r in rows:
        rec = r["record_id"]
        if rec not in sources:
            sources[rec] = json.loads((REMOTE / rec / "result.json").read_text())["sources"]
        data = cv.file_bytes(cv.packet(r, sources[rec], claims[rec]))
        (folder / f"{r['row_id']}.json").write_bytes(data)
        hashes[r["row_id"]] = cv.sha256(data)
    order = cs.order([r["row_id"] for r in rows])
    listing = {"seed": cs.SEND_SEED, "order": order,
               "packets_sha256": {rid: hashes[rid] for rid in order}}
    (folder / "order.json").write_text(json.dumps(listing, indent=1) + "\n")
    vol.commit()
    return {"candidates": len(rows), "records": len(records), "seed": cs.SEND_SEED,
            "order": order, "packets_sha256": listing["packets_sha256"],
            "order_json_sha256": file_sha256(folder / "order.json"),
            "claims_per_record": {r: len(claims[r]) for r in records},
            "packet_fields": sorted({k for rid in order for k in json.loads(
                (folder / f"{rid}.json").read_text())}),
            "inputs_sha256": {"volume:04_release_resolution_v2/c1_validity/candidates.json":
                              file_sha256(FOLDER / "candidates.json"),
                              **{f"../02_claims_meta/{c}": file_sha256(f"{E2}/{c}")
                                 for c in CHECKS},
                              **{f"volume:04_release_resolution_v2/retrieval/{r}/result.json":
                                 file_sha256(REMOTE / r / "result.json") for r in records}}}


@app.function(volumes={str(MOUNT): vol}, timeout=1800, memory=8192)
def plan_job(first_mean_usd: float) -> dict:
    vol.reload()
    order, packets = load_packets()
    sysx = system()
    bounds = {m: round(sum(j2.bound(m, sysx, packets[r]) for r in order), 4) for m in j2.JUDGES}
    entries = ledger_lines()
    spent = sum(e["usd"] for e in entries)
    chars = sum(len(json.dumps(p, ensure_ascii=False)) for p in packets.values())
    return {"candidates": len(order), "requests": 2 * len(order),
            "system_characters": len(sysx), "packet_characters": chars,
            "reserved_bound_usd": bounds, "reserved_bound_total_usd": round(sum(bounds.values()), 4),
            "estimate_usd": round(2 * len(order) * first_mean_usd, 4),
            "estimate_basis": "the first registration's validity marks: 3.00 US dollars for 140 "
                              "requests on the same prompt and schema "
                              f"({FIRST_VALIDITY_RUN}), {first_mean_usd:.5f} a request",
            "prices_usd_per_million": j2.PRICE, "min_characters_per_token": j2.MIN_RATIO,
            "max_output_tokens": j2.MAX_OUTPUT, "ledger_lines": len(entries),
            "ledger_usd_before": round(spent, 4),
            "first_registration_spend_usd": FIRST_REGISTRATION_SPEND,
            "ceiling_usd_on_the_ledger": CEILING, "new_spend_ceiling_usd": NEW_SPEND_CEILING}


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
           "spent_in_this_job_usd": round(ledger.spent - start, 4),
           "ceiling_usd_on_the_ledger": CEILING}
    (FOLDER / "run.json").write_text(json.dumps(out, indent=1))
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
            path = FOLDER / "judges" / m / f"{rid}.{key}.json"
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
                        "request_key": key}
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
    run = json.loads((FOLDER / "run.json").read_text())
    eligible = [rid for rid, e in per.items() if e["label"] == "eligible"]
    return {"rule": "PREREG.md, §Study design, item 1, Eligibility: eligible only when both "
                    "judges mark valid; disputed, cannot_mark, invalid and failed-twice "
                    "candidates are excluded",
            "candidates": len(per), "labels": {x: labels.get(x, 0) for x in cs.LABELS},
            "mark_pairs_fable_then_astra": dict(sorted(pairs.items())),
            "eligible": len(eligible), "eligible_at_least_50": len(eligible) >= cs.MINIMUM,
            "eligible_by_kind": dict(sorted(collections.Counter(
                per[r]["identifier_kind"] for r in eligible).items())),
            "eligible_by_side": dict(sorted(collections.Counter(
                per[r]["side"] for r in eligible).items())),
            "marks_by_judge": marks, "judges": judges,
            "spend_usd": round(sum(j["usd"] for j in judges.values()), 4),
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


@app.function(volumes={str(MOUNT): vol}, timeout=1800, memory=8192)
def draw_job(eligible_row_ids: list[str]) -> dict:
    vol.reload()
    target = ROOT4 / "c1a" / "control_set.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; the control set is frozen once")
    rows = {r["row_id"]: r for r in json.loads((FOLDER / "candidates.json").read_text())
            ["candidates"]}
    eligible = [rows[r] for r in eligible_row_ids]
    drawn = cs.draw(eligible)
    count = collections.Counter
    result = {"rule": "PREREG.md, §Study design, item 1, Draw and Minimum", "seed": cs.DRAW_SEED,
              "per_record": cs.PER_RECORD, "maximum": cs.MAXIMUM, "minimum": cs.MINIMUM,
              "eligible": len(eligible), "eligible_at_least_50": len(eligible) >= cs.MINIMUM,
              "drawn": len(drawn), "records": len({c["record_id"] for c in drawn}),
              "by_side": dict(sorted(count(c["side"] for c in drawn).items())),
              "by_identifier_kind": dict(sorted(count(c["identifier_kind"] for c in drawn).items())),
              "by_identifier_type": dict(sorted(count(c["identifier_type"] for c in drawn).items())),
              "expected_rows": len({c["expected_row"] for c in drawn}),
              "max_per_record": max(count(c["record_id"] for c in drawn).values(), default=0),
              "drawn_row_ids": [c["row_id"] for c in drawn], "control_rows": drawn}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result))
    vol.commit()
    return result | {"control_set_sha256": file_sha256(target)}


def write_once(out: str, data) -> None:
    target = LOCAL / out
    if target.exists():
        raise FileExistsError(f"{target} exists; it is written once")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-3000:])
    if result["returncode"]:
        raise SystemExit("tests failed")


def outside_records() -> list[str]:
    claim_lines, scope, _, _ = read_inputs()
    corpus = {json.loads(line)["claim_record_id"].rsplit(":", 1)[0]
              for line in claim_lines if line.strip()}
    return sorted(corpus - set(scope))


@app.local_entrypoint()
def scan(out: str) -> None:
    records = outside_records()
    result = scan_job.remote(records)
    write_once(out, result)
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("candidate_rows", "inputs_sha256", "per_record")}, indent=1))


@app.local_entrypoint()
def packets(out: str) -> None:
    claim_ids = [json.loads(line)["claim_record_id"]
                 for line in (PAPER1 / CLAIMS).read_text().splitlines() if line.strip()]
    result = packets_job.remote(claim_ids)
    result["inputs_sha256"][f"../02_claims_meta/{CLAIMS}"] = file_sha256(PAPER1 / CLAIMS)
    write_once(out, result)
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("order", "packets_sha256", "inputs_sha256",
                                   "claims_per_record")}, indent=1))


@app.local_entrypoint()
def plan(out: str) -> None:
    first = json.loads((LOCAL.parent / "03_release_resolution" / FIRST_VALIDITY_RUN).read_text())
    requests = sum(j["attempts"] for j in first["judges"].values())
    result = plan_job.remote(first["spend_usd"] / requests)
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
    write_once(raw, {"note": "the judges' quotations: third-party text; ignored location, never "
                             "committed", "quotations": quotations})
    write_once(out, result)
    print(json.dumps({k: v for k, v in result.items()
                      if k in ("candidates", "labels", "mark_pairs_fable_then_astra", "eligible",
                               "eligible_at_least_50", "marks_by_judge", "judges", "spend_usd",
                               "ledger_usd_after")}, indent=1))


@app.local_entrypoint()
def draw(marks: str, out: str) -> None:
    combined = json.loads((LOCAL / marks).read_text())
    eligible = sorted(r for r, e in combined["candidates_marked"].items()
                      if e["label"] == "eligible")
    result = draw_job.remote(eligible)
    result["inputs_sha256"] = {marks: file_sha256(LOCAL / marks)}
    write_once(out, result)
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("control_rows", "drawn_row_ids")}, indent=1))
