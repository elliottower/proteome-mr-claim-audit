"""Third version of the stage A wrapper (scripts/modal_stage_a_v2.py, sealed, unchanged), for the
stage A coding pass and the manifest packets that run with it (AMENDMENT_02_staged_reading.md,
items 1 to 3). Two changes, and nothing else:

- the ceiling of stage A and SA1 is 300 US dollars, as the author set it on 14 October 2026
  (PREREG.log, deviation from Amendment 2, item 5), in place of the 100 the second version holds;
  the ledger is the stage's one spend ledger (/03_release_resolution/coding/spend.jsonl), which
  holds SA1's coding and judges, so the ceiling counts every request of stage A and SA1;
- the gate keeps each row's verdict on the volume and the pass's counts are made by
  scripts/stage_a_counts_v1.py: agreement of the two models on study rows and on control rows,
  gate failures, C1-A against its expected rows and the manifest controls against theirs.

The coding is the second version's: scripts/coding_runner_v3.py (sealed), the frozen prompt,
dictionary definitions and schema, both models in one container sharing the ledger, each
request reserved by the bound of scripts/coding_runner_v2.py before it is sent, every exchange
stored on the volume as it ends, a stored answer never sent again. A request left pending (a
transport failure, HTTP 402 or 429) is sent again in a later round of the same job, up to
ROUNDS rounds ROUND_WAIT seconds apart, and in any later launch.

Run from experiments/03_release_resolution (keys from the 1Password pipe, with MODAL_TOKEN_ID and
MODAL_TOKEN_SECRET unset after loading it):

    modal run scripts/modal_stage_a_v3.py::tests
    modal run --detach scripts/modal_stage_a_v3.py::code --approved "<logged line>" --out <json>
    modal run scripts/modal_stage_a_v3.py::gate_and_count --out <json>

Outputs hold counts, row ids, identifiers and hashes, never source text or an answer's content.
"""

import json
import os
import pathlib
import time

import modal

from modal_coding_v2 import (CODING, E2, E3, LOCAL, MOUNT, SECRETS, image, vol)

app = modal.App("release-resolution-stage-a-v3", image=image)
CEILING_STAGE_A_SA1 = 300.0
MODELS = ("claude-sonnet-5-5", "gpt-6.1-sol")
STAGES = ("stage_a", "manifest")
ROUNDS = 6
ROUND_WAIT = 600

with image.imports():
    import collections
    import concurrent.futures
    import csv
    import hashlib
    import subprocess

    import anthropic
    import httpx

    import coding_gate as gate
    import coding_packets as cp
    import coding_runner as cr
    import coding_runner_v3 as cr3
    import pass_summary as ps
    import source_scanner_v2 as scanner
    import stage_a_counts_v1 as sc

TESTS = ["test_stage_a_counts_v1.py", "test_coding_runner_v3.py", "test_coding_runner_v2.py",
         "test_coding_runner.py", "test_pass_summary.py", "test_coding_gate.py",
         "test_coding_packets_v2.py", "test_coding_packets.py", "test_c1_controls.py",
         "test_prompt_schemas.py"]


def fixed():
    prompt = cp.fixed_prompt(open(f"{E3}/prompts/coding_prompt_v2.md").read(),
                             open(f"{E2}/outputs/manual_coding/2026-10-03/coders/"
                                  "dictionary_definitions.csv").read())
    return prompt, json.loads(open(f"{E3}/prompts/output_schema.json").read())


def load(stage: str) -> list[tuple[str, dict]]:
    folder = CODING / "packets" / stage
    return [(m["name"], json.loads((folder / f"{m['name']}.json").read_text()))
            for m in json.loads((folder / "manifest.json").read_text())]


def file_sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@app.function(timeout=1800, cpu=2.0)
def tests_job() -> dict:
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", *TESTS],
                         capture_output=True, text=True, cwd=f"{E3}/tests")
    return {"returncode": run.returncode, "output": run.stdout + run.stderr}


def summary(d: dict) -> dict:
    return {k: v for k, v in d.items() if k != "results"} | {
        "failed": sorted(r["name"] for r in d["results"] if r["state"] == "failed"),
        "pending": sorted(r["name"] for r in d["results"] if r["state"] == "pending"),
        "models_returned": sorted({a["model_returned"] for r in d["results"]
                                   for a in r.get("attempts", []) if a.get("model_returned")})}


@app.function(volumes={str(MOUNT): vol}, timeout=24 * 3600, secrets=SECRETS, memory=16384)
def code_job(workers: int) -> dict:
    vol.reload()
    prompt, schema = fixed()
    ledger = cr.Ledger(CODING / "spend.jsonl", CEILING_STAGE_A_SA1, persist=vol.commit)
    start_spend = ledger.spent
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0,
                                 timeout=3600)
    http = httpx.Client(timeout=3600)
    sends = {"claude-sonnet-5-5": lambda body: cr3.call_claude(client, body),
             "gpt-6.1-sol": lambda body: cr.call_sol(http, os.environ["OPENAI_API_KEY"], body)}
    out = {"ceiling_usd": CEILING_STAGE_A_SA1, "ledger_usd_at_start": round(start_spend, 4),
           "stages": {}}
    for stage in STAGES:
        packets = load(stage)
        rounds = []
        for k in range(ROUNDS):
            runners = {m: cr3.Runner(m, prompt, schema, CODING / "answers" / stage / m, ledger,
                                     send=sends[m], persist=vol.commit, workers=workers)
                       for m in MODELS}
            with concurrent.futures.ThreadPoolExecutor(2) as pool:
                futures = {m: pool.submit(runners[m].run, packets) for m in MODELS}
                done = {m: summary(f.result()) for m, f in futures.items()}
            vol.commit()
            rounds.append(done)
            print(f"{time.strftime('%H:%M:%S')} {stage} round {k + 1}: "
                  + json.dumps({m: d["states"] | {"not_sent_ceiling": d["not_sent_ceiling"]}
                                for m, d in done.items()}), flush=True)
            if any(d["stopped"] for d in done.values()):
                break
            if not any(d["pending"] for d in done.values()):
                break
            time.sleep(ROUND_WAIT)
        out["stages"][stage] = {"rounds": len(rounds), "last_round": rounds[-1],
                                "errors_by_round": [{m: d["errors"] for m, d in r.items()}
                                                    for r in rounds]}
        (CODING / "runs").mkdir(parents=True, exist_ok=True)
        (CODING / "runs" / f"stage_a_v3_{stage}.json").write_text(json.dumps(out["stages"][stage]))
        vol.commit()
        if any(d["stopped"] for d in rounds[-1].values()):
            break
    out["ledger_usd_at_end"] = round(ledger.spent, 4)
    out["spent_in_this_job_usd"] = round(ledger.spent - start_spend, 4)
    return out


def gate_stage(stage: str, patterns, mapper, dictionary) -> tuple[dict, dict, dict, set]:
    """Gate every accepted answer of one stage for both models; each row's verdict kept on the
    volume. Returns the counts, the accepted rows and the verdicts per model, and the request
    keys of the stage's stored answers."""
    packets = dict(load(stage))
    counts_out, answers, verdicts, keys = {}, {}, {}, set()
    for model in MODELS:
        store = CODING / "answers" / stage / model
        folder = CODING / "gate" / stage / model
        if (folder / "rows.json").exists():
            raise FileExistsError(f"{folder} is gated already")
        finals = [json.loads(p.read_text()) for p in sorted(store.glob("*.json"))
                  if ".attempt" not in p.name]
        keys |= {f["key"] for f in finals}
        counts, failures = collections.Counter(), collections.Counter()
        answers[model], verdicts[model] = {}, {}
        for f in finals:
            counts[f["state"]] += 1
            if f["state"] != "accepted":
                continue
            p = packets[f["name"]]
            sides = {r["row_id"]: r["side"] for r in p["rows"]}
            frozen = {file["file_id"]: {
                "key": (f"{p['record_id']}-abstract" if file["kind"] == "abstract"
                        else f"{p['record_id']}-{file['file_id']}"),
                "sha256": cp.sha256(file["text"]), "text": file["text"]} for file in p["files"]}
            for row in f["answer"]["rows"]:
                answers[model][row["row_id"]] = row
                g = gate.gate_row(row, sides[row["row_id"]], p, frozen, patterns, mapper,
                                  dictionary)
                verdicts[model][row["row_id"]] = g["passes"]
                counts["rows_gated"] += 1
                counts["rows_passing" if g["passes"] else "rows_failing"] += 1
                counts["rows_naming_a_release"] += bool(row["identified_releases"])
                for rel in g["releases"].values():
                    for fl in rel["failures"]:
                        for e in (fl["errors"] if isinstance(fl, dict) else [fl]):
                            failures[e] += 1
                for n, pinq in enumerate(g["to_pin"], 1):
                    got = gate.pin(folder, frozen[pinq["file_id"]], f"{row['row_id']}_{n}",
                                   pinq["quote"])
                    counts["quotes_pinned" if got["pinned"] else "quotes_refused_by_pin"] += 1
        verified = gate.verify(folder) if (folder / "claims").exists() else {"returncode": None}
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "rows.json").write_text(json.dumps(verdicts[model]))
        vol.commit()
        counts_out[model] = {"answers": dict(counts), "gate_failures_by_error": dict(failures),
                             "citations_verify_returncode": verified["returncode"]}
    return counts_out, answers, verdicts, keys


@app.function(volumes={str(MOUNT): vol}, timeout=6 * 3600, memory=16384)
def gate_and_count_job() -> dict:
    vol.reload()
    patterns = json.loads(open(f"{E3}/reference/c1_scanner_patterns_v2.json").read())
    with open(f"{E3}/reference/accession_releases.csv", newline="") as fh:
        table = list(csv.DictReader(fh))
    dictionary = gate.dictionary_rows(f"{E2}/dataset_dictionary.csv")
    mapper = scanner.Mapper(patterns, table, list(dictionary.values()))
    queue_path = CODING / "inputs" / "queue.json"
    controls_path = CODING / "c1a" / "control_set.json"
    manifest_path = CODING / "packets" / "manifest" / "manifest.json"
    study_ids = sorted(r["row_id"] for r in json.loads(queue_path.read_text())["queue"])
    c1a = {r["row_id"]: r["expected_row"]
           for r in json.loads(controls_path.read_text())["control_rows"]}
    man = {m["row_id"]: m["expected_row"] for m in json.loads(manifest_path.read_text())}
    stage_rows = sorted(r["row_id"] for _, p in load("stage_a") for r in p["rows"])
    if stage_rows != sorted(study_ids + list(c1a)):
        raise ValueError("the stage A packets' rows are not the queue's rows and the C1-A rows")
    out = {"inputs_sha256": {
        "volume:coding/inputs/queue.json": file_sha256(queue_path),
        "volume:coding/c1a/control_set.json": file_sha256(controls_path),
        "volume:coding/packets/stage_a/manifest.json":
            file_sha256(CODING / "packets" / "stage_a" / "manifest.json"),
        "volume:coding/packets/manifest/manifest.json": file_sha256(manifest_path),
        "prompts/coding_prompt_v2.md": file_sha256(pathlib.Path(
            f"{E3}/prompts/coding_prompt_v2.md")),
        "prompts/output_schema.json": file_sha256(pathlib.Path(
            f"{E3}/prompts/output_schema.json"))}}
    keys = set()
    gated = {}
    for stage in STAGES:
        counts, answers, verdicts, k = gate_stage(stage, patterns, mapper, dictionary)
        keys |= k
        gated[stage] = (answers, verdicts)
        out[f"gate_{stage}"] = counts
    answers, verdicts = gated["stage_a"]
    first, second = (answers[m] for m in MODELS)
    out["rows_coded_per_model"] = {
        m: {"study_rows": sum(r in answers[m] for r in study_ids),
            "control_rows": sum(r in answers[m] for r in c1a)} for m in MODELS}
    out["agreement_stage_a"] = {"study_rows": sc.agreement(study_ids, first, second),
                                "c1a_control_rows": sc.agreement(sorted(c1a), first, second)}
    out["gate_failing_rows_stage_a"] = {
        m: {"study_rows": sum(not verdicts[m][r] for r in study_ids if r in verdicts[m]),
            "control_rows": sum(not verdicts[m][r] for r in c1a if r in verdicts[m])}
        for m in MODELS}
    out["c1a_source_scanned"] = sc.c1_scores(c1a, answers, verdicts, sc.SOURCE_SCANNED_MINIMUM)
    m_answers, m_verdicts = gated["manifest"]
    out["c1_manifest"] = sc.c1_scores(man, m_answers, m_verdicts, 0)
    out["agreement_manifest"] = sc.agreement(sorted(man), *(m_answers[m] for m in MODELS))
    entries = [json.loads(l) for l in (CODING / "spend.jsonl").read_text().splitlines()
               if l.strip()]
    out["usage_stage_a_and_manifest"] = ps.usage_summary(
        [e for e in entries if e["request_key"] in keys])
    out["ledger_spend_all_stages_usd"] = round(sum(e["usd"] for e in entries), 4)
    out["ceiling_usd"] = CEILING_STAGE_A_SA1
    out["note"] = ("coders' answers before any judge or adjudication; C1 as registered is "
                   "computed on accepted codes")
    adj = ps.adjudication_rows(study_ids + sorted(c1a), first, second)
    (CODING / "gate" / "stage_a" / "adjudication_rows.json").write_text(json.dumps(adj))
    vol.commit()
    return out


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
def code(approved: str, out: str, workers: int = 8) -> None:
    log = (LOCAL / "PREREG.log").read_text()
    if not approved.strip() or approved not in log:
        raise SystemExit("the approval of this pass is not in PREREG.log")
    if not SECRETS:
        raise SystemExit("the keys are not in the environment")
    result = code_job.remote(workers)
    write_once(out, result)
    print(json.dumps(result, indent=1)[:6000])


@app.local_entrypoint()
def gate_and_count(out: str) -> None:
    result = gate_and_count_job.remote()
    write_once(out, result)
    print(json.dumps(result, indent=1))
