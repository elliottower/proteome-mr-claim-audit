"""Second version of scripts/modal_stage_a.py (sealed, unchanged): the passes use
scripts/coding_runner_v3.py, whose Claude call reads the streamed structured message without
`_request_id` and whose pass survives a defect in one request.

Earlier description: Modal wrapper for the C1-A control set, the stage A packets, the estimate of SA1 and stage A,
the coding passes under the ceiling of 100 US dollars, and the gate on a pass
(AMENDMENT_02_staged_reading.md). It reuses the image and volume of scripts/modal_coding_v2.py
(sealed, unchanged); no logic of the study is here.

Run from experiments/03_release_resolution (keys from the 1Password pipe, with MODAL_TOKEN_ID and
MODAL_TOKEN_SECRET unset after loading it):

    modal run scripts/modal_stage_a_v2.py::tests
    modal run scripts/modal_stage_a_v2.py::freeze_controls --out outputs/c1a_controls_2026-10-13.json
    modal run scripts/modal_stage_a_v2.py::stage_a_packets --controls <json> --out <json>
    modal run scripts/modal_stage_a_v2.py::estimate --out <json>
    modal run --detach scripts/modal_stage_a_v2.py::code --stage sa1 --approved "<logged line>" --out <json>
    modal run scripts/modal_stage_a_v2.py::gate_pass --stage sa1 --out <json>

`code` sends a stage's packets to both models at once in one container, so the two runners share
one spend ledger (/03_release_resolution/coding/spend.jsonl) and one ceiling of 100 US dollars
for stage A and SA1; each request is reserved by the bound of scripts/coding_runner_v2.py and
every exchange is stored as it ends. `gate_pass` runs scripts/coding_gate.py on every accepted answer
of a stage, pins the passing quotes with the citations tool in a folder on the volume, verifies
them, and returns counts with the usage and the rows to adjudicate (scripts/pass_summary.py).
Outputs hold counts, row ids, identifiers and hashes, never source text.
"""

import json
import os
import pathlib

import modal

from modal_coding_v2 import (CODING, E2, E3, LOCAL, MOUNT, PAPER1, ROOT, SECRETS, image, vol)

app = modal.App("release-resolution-stage-a-v2", image=image)
CEILING_STAGE_A_SA1 = 100.0
MODELS = ("claude-sonnet-5-5", "gpt-6.1-sol")

with image.imports():
    import collections
    import concurrent.futures
    import csv
    import hashlib
    import subprocess

    import anthropic
    import httpx

    import c1_controls as c1
    import coding_gate as gate
    import coding_packets as cp
    import coding_packets_v2 as cp2
    import coding_queue as q
    import coding_runner as cr
    import coding_runner_v2 as cr2
    import coding_runner_v3 as cr3
    import pass_summary as ps
    import source_scanner_v2 as scanner
    import stage_pricing as sp

RATIOS = {"preflight_ratios": {"claude-sonnet-5-5": 1.98, "gpt-6.1-sol": 3.11},
          "pooled_full_text_ratios_of_the_plan": {"claude-sonnet-5-5": 2.62, "gpt-6.1-sol": 4.28}}


def fixed():
    prompt = cp.fixed_prompt(open(f"{E3}/prompts/coding_prompt_v2.md").read(),
                             open(f"{E2}/outputs/manual_coding/2026-10-03/coders/"
                                  "dictionary_definitions.csv").read())
    return prompt, json.loads(open(f"{E3}/prompts/output_schema.json").read())


def accessions():
    return cp.read_accessions(f"{E3}/reference/c1_scanner_patterns_v2.json",
                              f"{E3}/reference/accession_releases.csv")


def load(stage: str) -> list[tuple[str, dict]]:
    folder = CODING / "packets" / stage
    return [(m["name"], json.loads((folder / f"{m['name']}.json").read_text()))
            for m in json.loads((folder / "manifest.json").read_text())]


@app.function(timeout=1800, cpu=2.0)
def tests_job() -> dict:
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                          "test_coding_runner_v3.py", "test_pass_summary.py", "test_coding_gate.py", "test_stage_pricing.py",
                          "test_coding_runner_v2.py", "test_coding_runner.py",
                          "test_coding_packets.py", "test_c1_controls.py"],
                         capture_output=True, text=True, cwd=f"{E3}/tests")
    return {"returncode": run.returncode, "output": run.stdout + run.stderr}


@app.function(volumes={str(MOUNT): vol}, timeout=1800)
def freeze_controls_job(records: list[str], queue: dict) -> dict:
    vol.reload()
    target = CODING / "c1a" / "control_set.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; the control set is frozen once")
    patterns = json.loads(open(f"{E3}/reference/c1_scanner_patterns_v2.json").read())
    found = [c for r in records
             for c in json.loads((CODING / "c1" / f"{r}.json").read_text())["found"]]
    drawn = sp.stratified_draw(found, patterns["draw"]["seed"], patterns["draw"]["maximum"])
    rows = c1.control_rows(drawn, queue["queue"],
                           q.side_rows(pathlib.Path(f"{E2}/dataset_dictionary.csv")))
    result = {"rule": "Amendment 2, item 3", "seed": patterns["draw"]["seed"],
              "maximum": patterns["draw"]["maximum"], "minimum": patterns["draw"]["minimum"],
              "per_record": sp.PER_RECORD, "drawn": len(drawn),
              "records": len({c["record_id"] for c in drawn}),
              "by_side": dict(collections.Counter(c["side"] for c in drawn)),
              "by_identifier_type": dict(collections.Counter(c["type"] for c in drawn)),
              "by_kind": dict(collections.Counter(c["kind"] for c in drawn)),
              "expected_rows": len({c["expected_row"] for c in drawn}),
              "drawn_controls": drawn, "control_rows": rows}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result))
    vol.commit()
    return result


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=16384)
def stage_a_packets_job(control_rows: list[dict]) -> dict:
    vol.reload()
    folder = CODING / "packets" / "stage_a"
    if (folder / "manifest.json").exists():
        raise FileExistsError(f"{folder} holds packets already")
    folder.mkdir(parents=True, exist_ok=True)
    queue = json.loads((CODING / "inputs" / "queue.json").read_text())
    held = json.loads((CODING / "inputs" / "abstracts.json").read_text())
    acc = accessions()
    by_record: dict[str, list[dict]] = {}
    for r in queue["queue"]:
        by_record.setdefault(r["record_id"], []).append(r)
    ctrl: dict[str, list[dict]] = {}
    for r in control_rows:
        ctrl.setdefault(r["record_id"], []).append(r)
    manifest = []
    for rec, rows in sorted(by_record.items()):
        result = json.loads((ROOT / "retrieval" / rec / "result.json").read_text())
        full = [s for s in result["sources"] if s["route"] in ("R1", "R3") and s.get("text")]
        packets, _ = cp2.fulltext_packets_carrying(rec, held[rec]["title"],
                                                   c1.merge(rows, ctrl.get(rec, [])),
                                                   held[rec]["abstract"], full, [], acc)
        for k, p in enumerate(packets, 1):
            name = f"{rec}.{k}"
            (folder / f"{name}.json").write_text(json.dumps(p, ensure_ascii=False))
            manifest.append({"name": name, "record_id": rec, "rows": len(p["rows"]),
                             "control_rows": len(ctrl.get(rec, [])),
                             "files": [{"file_id": f["file_id"], "kind": f["kind"],
                                        "characters": len(f["text"]),
                                        "sha256": cp.sha256(f["text"])} for f in p["files"]],
                             "packet_characters": len(json.dumps(p, ensure_ascii=False))})
    (folder / "manifest.json").write_text(json.dumps(manifest))
    vol.commit()
    return {"packets": len(manifest), "records": len({m["record_id"] for m in manifest}),
            "rows": sum(m["rows"] for m in manifest),
            "control_rows": sum(len(v) for v in ctrl.values()),
            "records_with_a_full_text": sum(any(f["kind"] == "full_text" for f in m["files"])
                                            for m in manifest),
            "packet_characters": sum(m["packet_characters"] for m in manifest),
            "manifest": manifest}


@app.function(volumes={str(MOUNT): vol}, timeout=1800)
def estimate_job() -> dict:
    vol.reload()
    prompt, _ = fixed()
    out = {"fixed_prompt_characters": len(prompt), "ceiling_usd": CEILING_STAGE_A_SA1,
           "stages": {}}
    for stage, carrying in (("sa1", False), ("stage_a", True), ("manifest", False)):
        folder = CODING / "packets" / stage
        manifest = json.loads((folder / "manifest.json").read_text())
        recs = [{"record_id": m["record_id"], "carried": 0,
                 "packets": [m["packet_characters"] if "packet_characters" in m else
                             len((folder / f"{m['name']}.json").read_text())]}
                for m in manifest]
        bound = {model: round(sum(cr2.bound(model, prompt, json.loads(
            (folder / f"{m['name']}.json").read_text())) for m in manifest), 2)
            for model in MODELS}
        out["stages"][stage] = {
            "requests_per_model": len(recs),
            "packet_characters": sum(r["packets"][0] for r in recs),
            "cost": {name: sp.with_outputs(cp2.layout_cost(recs, len(prompt), ratio, carrying))
                     for name, ratio in RATIOS.items()},
            "sum_of_reservation_bounds_usd": bound}
    for name in RATIOS:
        out[f"total_{name}"] = {o: round(sum(s["cost"][name][o]["total_usd"]
                                             for s in out["stages"].values()), 2)
                                for o in ("1500", "3000", "6000")}
    return out


@app.function(volumes={str(MOUNT): vol}, timeout=24 * 3600, secrets=SECRETS, memory=16384)
def code_job(stage: str, workers: int) -> dict:
    vol.reload()
    prompt, schema = fixed()
    ledger = cr.Ledger(CODING / "spend.jsonl", CEILING_STAGE_A_SA1, persist=vol.commit)
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0,
                                 timeout=3600)
    http = httpx.Client(timeout=3600)
    sends = {"claude-sonnet-5-5": lambda body: cr3.call_claude(client, body),
             "gpt-6.1-sol": lambda body: cr.call_sol(http, os.environ["OPENAI_API_KEY"], body)}
    packets = load(stage)
    runners = {m: cr3.Runner(m, prompt, schema, CODING / "answers" / stage / m, ledger,
                             send=sends[m], persist=vol.commit, workers=workers) for m in MODELS}
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        futures = {m: pool.submit(runners[m].run, packets) for m in MODELS}
        done = {m: f.result() for m, f in futures.items()}
    vol.commit()
    return {m: {k: v for k, v in d.items() if k != "results"} | {
        "failed": sorted(r["name"] for r in d["results"] if r["state"] == "failed"),
        "pending": sorted(r["name"] for r in d["results"] if r["state"] == "pending"),
        "models_returned": sorted({a["model_returned"] for r in d["results"]
                                   for a in r.get("attempts", []) if a.get("model_returned")})}
        for m, d in done.items()} | {"spent_usd": round(ledger.spent, 4)}


@app.function(volumes={str(MOUNT): vol}, timeout=6 * 3600, memory=16384)
def gate_job(stage: str) -> dict:
    vol.reload()
    patterns = json.loads(open(f"{E3}/reference/c1_scanner_patterns_v2.json").read())
    with open(f"{E3}/reference/accession_releases.csv", newline="") as fh:
        table = list(csv.DictReader(fh))
    dictionary = gate.dictionary_rows(f"{E2}/dataset_dictionary.csv")
    mapper = scanner.Mapper(patterns, table, list(dictionary.values()))
    packets = dict(load(stage))
    result = {"stage": stage, "models": {}}
    answers: dict[str, dict[str, dict]] = {}
    keys: dict[str, set] = {}
    for model in MODELS:
        store = CODING / "answers" / stage / model
        finals = [json.loads(p.read_text()) for p in sorted(store.glob("*.json"))
                  if ".attempt" not in p.name]
        keys[model] = {f["key"] for f in finals}
        folder = CODING / "gate" / stage / model
        counts = collections.Counter()
        failures = collections.Counter()
        answers[model] = {}
        for f in finals:
            counts[f["state"]] += 1
            if f["state"] != "accepted":
                continue
            p = packets[f["name"]]
            sides = {r["row_id"]: r["side"] for r in p["rows"]}
            frozen = {}
            for file in p["files"]:
                if file["kind"] == "abstract":
                    frozen[file["file_id"]] = {"key": f"{p['record_id']}-abstract",
                                               "sha256": cp.sha256(file["text"]),
                                               "text": file["text"]}
                else:
                    frozen[file["file_id"]] = {"key": f"{p['record_id']}-{file['file_id']}",
                                               "sha256": cp.sha256(file["text"]),
                                               "text": file["text"]}
            for row in f["answer"]["rows"]:
                answers[model][row["row_id"]] = row
                g = gate.gate_row(row, sides[row["row_id"]], p, frozen, patterns, mapper,
                                  dictionary)
                counts["rows_gated"] += 1
                counts["rows_passing" if g["passes"] else "rows_failing"] += 1
                counts["rows_naming_a_release"] += bool(row["identified_releases"])
                for rel in g["releases"].values():
                    for fl in rel["failures"]:
                        for e in (fl["errors"] if isinstance(fl, dict) else [fl]):
                            failures[e] += 1
                for n, pinq in enumerate(g["to_pin"], 1):
                    src = frozen[pinq["file_id"]]
                    got = gate.pin(folder, src, f"{row['row_id']}_{n}", pinq["quote"])
                    counts["quotes_pinned" if got["pinned"] else "quotes_refused_by_pin"] += 1
        verified = gate.verify(folder) if (folder / "claims").exists() else {"returncode": None}
        result["models"][model] = {"answers": dict(counts),
                                   "gate_failures_by_error": dict(failures),
                                   "citations_verify_returncode": verified["returncode"]}
    vol.commit()
    entries = [json.loads(l) for l in (CODING / "spend.jsonl").read_text().splitlines()
               if l.strip()]
    mine = [e for e in entries if e["request_key"] in keys[e["model"]]]
    row_ids = [r["row_id"] for _, p in sorted(packets.items()) for r in p["rows"]]
    adj = ps.adjudication_rows(row_ids, answers[MODELS[0]], answers[MODELS[1]])
    (CODING / "gate" / stage / "adjudication_rows.json").write_text(json.dumps(adj))
    vol.commit()
    return result | {"usage": ps.usage_summary(mine),
                     "ledger_spend_all_stages_usd": round(sum(e["usd"] for e in entries), 4),
                     "adjudication": adj}


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
def freeze_controls(out: str) -> None:
    records = sorted(json.loads((PAPER1 / "outputs/release_resolution/"
                                          "availability_2026-10-08.json").read_text())["records"])
    queue = json.loads((LOCAL / "outputs" / "coding_queue_2026-10-13.json").read_text())
    result = freeze_controls_job.remote(records, queue)
    write_once(out, result)
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("drawn_controls", "control_rows")}, indent=1))


@app.local_entrypoint()
def stage_a_packets(controls: str, out: str) -> None:
    rows = json.loads((LOCAL / controls).read_text())["control_rows"]
    result = stage_a_packets_job.remote(rows)
    write_once(out, result)
    print(json.dumps({k: v for k, v in result.items() if k != "manifest"}, indent=1))


@app.local_entrypoint()
def estimate(out: str) -> None:
    result = estimate_job.remote()
    write_once(out, result)
    print(json.dumps(result, indent=1)[:5000])


@app.local_entrypoint()
def code(stage: str, approved: str, out: str, workers: int = 8) -> None:
    log = (LOCAL / "PREREG.log").read_text()
    if not approved.strip() or approved not in log:
        raise SystemExit("the approval of this pass is not in PREREG.log")
    if not SECRETS:
        raise SystemExit("the keys are not in the environment")
    result = code_job.remote(stage, workers)
    write_once(out, result)
    print(json.dumps(result, indent=1))


@app.local_entrypoint()
def gate_pass(stage: str, out: str) -> None:
    result = gate_job.remote(stage)
    write_once(out, result)
    print(json.dumps({k: v for k, v in result.items()} | {"adjudication": {
        k: v for k, v in result["adjudication"].items() if k != "row_ids_to_adjudicate"}},
        indent=1))
