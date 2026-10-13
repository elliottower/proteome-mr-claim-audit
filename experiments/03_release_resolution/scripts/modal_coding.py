"""Modal wrapper for the coding passes of the release-resolution follow-up: the packets
(scripts/coding_packets.py), the free token-count preflight, and the model requests
(scripts/coding_runner.py) of SA1, the full-text pass and the removed-chunk diagnostic. No logic
of the study is here. Built from scripts/modal_cut_supplements_v2.py.

Run from experiments/03_release_resolution, with the keys in the environment (the 1Password
pipe); a key is passed to Modal as a secret and never printed or written:

    modal run scripts/modal_coding.py::tests
    modal run scripts/modal_coding.py::inputs --queue <queue json> --screening <jsonl> [...]
    modal run scripts/modal_coding.py::packets --stage sa1|full|diagnostic --out <json>
    modal run scripts/modal_coding.py::preflight --stage sa1|full --out <json>
    modal run --detach scripts/modal_coding.py::code --stage sa1|full|diagnostic \\
        --model claude-sonnet-5-5|gpt-6.1-sol --approved "<the logged approval line>" --out <json>

Volume layout, /03_release_resolution/coding/:
    inputs/queue.json, inputs/abstracts.json (the abstracts and titles of the scope as Paper 1
        stored them; third-party text, on the volume only)
    packets/<stage>/<record>.<k>.json, packets/<stage>/manifest.json
    answers/<stage>/<model>/<record>.<k>.<key>.json (every exchange and answer)
    spend.jsonl (the stage's spend ledger; one ceiling across every pass)

`packets` writes the packets on the volume and returns counts only: packets, characters,
records, the exhaustive-chunk log (hashes and ranges) and, for the diagnostic, the seeded draw of
400 chunks (seed 20261012 for the first round) from the population frozen in
outputs/cut_v2_2026-10-13.json. `preflight` sends one packet per model to the vendors' free
token-counting endpoints (no model is run) and returns the counts. `code` sends a stage's packets
to one model and returns counts only; it refuses to start without the `--approved` text, which
must be the logged approval of that pass.

Client modal 1.4.3; image python 3.12 debian_slim.
"""

import json
import os
import pathlib

import modal

VOLUME = "proteome-mr-claim-audit-inputs"
MOUNT = pathlib.Path("/vol")
ROOT = MOUNT / "03_release_resolution"
CODING = ROOT / "coding"
LOCAL = pathlib.Path(__file__).resolve().parents[1]
PAPER1 = LOCAL.parent / "02_claims_meta"
IGNORE = ["__pycache__", "*.pyc", ".pytest_cache"]
DEFINITIONS = "outputs/manual_coding/2026-10-03/coders/dictionary_definitions.csv"
DIAGNOSTIC_SEED = 20261012
DIAGNOSTIC_N = 400
KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")

image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("httpx==0.28.1", "pydantic==2.13.5", "pyyaml==6.0.3", "pytest==8.4.2",
                      "jsonschema==4.26.0", "anthropic==1.13.0", "numpy==2.5.3")
         .env({"PYTHONPATH": "/exp03/scripts:/exp02/scripts"})
         .add_local_dir(LOCAL / "scripts", "/exp03/scripts", copy=True, ignore=IGNORE)
         .add_local_dir(LOCAL / "tests", "/exp03/tests", copy=True, ignore=IGNORE)
         .add_local_dir(LOCAL / "reference", "/exp03/reference", copy=True)
         .add_local_dir(LOCAL / "prompts", "/exp03/prompts", copy=True)
         .add_local_dir(PAPER1 / "scripts", "/exp02/scripts", copy=True, ignore=IGNORE)
         .add_local_file(PAPER1 / "dataset_dictionary.csv", "/exp02/dataset_dictionary.csv",
                         copy=True)
         .add_local_file(PAPER1 / "dataset_dictionary.csv",
                         "/02_claims_meta/dataset_dictionary.csv", copy=True)
         .add_local_file(PAPER1 / "verification" / "dataset_components.csv",
                         "/exp02/verification/dataset_components.csv", copy=True)
         .add_local_file(PAPER1 / DEFINITIONS, "/exp02/dictionary_definitions.csv", copy=True))
vol = modal.Volume.from_name(VOLUME)
SECRETS = ([modal.Secret.from_dict({k: os.environ[k] for k in KEYS})]
           if all(os.environ.get(k) for k in KEYS) else [])
app = modal.App("release-resolution-coding", image=image)

with image.imports():
    import random
    import subprocess

    import anthropic
    import httpx

    import coding_packets as cp
    import coding_runner as cr

TESTS = ["test_coding_queue.py", "test_coding_packets.py", "test_coding_runner.py",
         "test_cut_supplements_v2.py", "test_prompt_schemas.py"]


def fixed() -> tuple[str, dict]:
    prompt = cp.fixed_prompt(open("/exp03/prompts/coding_prompt_v2.md").read(),
                             open("/exp02/dictionary_definitions.csv").read())
    return prompt, json.loads(open("/exp03/prompts/output_schema.json").read())


def accessions():
    return cp.read_accessions("/exp03/reference/c1_scanner_patterns_v2.json",
                              "/exp03/reference/accession_releases.csv")


@app.function(timeout=1800, cpu=2.0)
def tests_job() -> dict:
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", *TESTS],
                         capture_output=True, text=True, cwd="/exp03/tests")
    return {"returncode": run.returncode, "output": run.stdout + run.stderr}


@app.function(volumes={str(MOUNT): vol}, timeout=1800)
def inputs_job(queue: dict, abstracts: dict) -> dict:
    (CODING / "inputs").mkdir(parents=True, exist_ok=True)
    for name, data in (("queue.json", queue), ("abstracts.json", abstracts)):
        path = CODING / "inputs" / name
        if path.exists():
            if json.loads(path.read_text()) != data:
                raise FileExistsError(f"{path} exists and differs; it is written once")
            continue
        path.write_text(json.dumps(data, ensure_ascii=False))
    vol.commit()
    return {"queue_rows": len(queue["queue"]), "abstracts": len(abstracts)}


def rows_by_record(queue: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in queue["queue"]:
        out.setdefault(r["record_id"], []).append(r)
    return out


@app.function(volumes={str(MOUNT): vol}, timeout=6 * 3600, memory=32768)
def packets_job(stage: str, population: list[dict]) -> dict:
    vol.reload()
    queue = json.loads((CODING / "inputs" / "queue.json").read_text())
    held = json.loads((CODING / "inputs" / "abstracts.json").read_text())
    acc = accessions()
    folder = CODING / "packets" / stage
    if (folder / "manifest.json").exists():
        raise FileExistsError(f"{folder} holds packets already")
    folder.mkdir(parents=True, exist_ok=True)
    manifest, log, drawn = [], [], []
    by_record = rows_by_record(queue)

    def write(name: str, p: dict) -> None:
        (folder / f"{name}.json").write_text(json.dumps(p, ensure_ascii=False))
        manifest.append({"name": name, "record_id": p["record_id"], "rows": len(p["rows"]),
                         "files": [{"file_id": f["file_id"], "kind": f["kind"],
                                    "characters": len(f["text"]),
                                    "sha256": cp.sha256(f["text"])} for f in p["files"]],
                         "accession_table_rows": len(p["accession_table_rows"]),
                         "packet_characters": len(json.dumps(p, ensure_ascii=False))})

    if stage == "sa1":
        for rec, rows in sorted(by_record.items()):
            p = cp.sa1_packets(rec, held[rec]["title"], rows, held[rec]["abstract"], acc)[0]
            write(f"{rec}.1", p)
    elif stage == "full":
        for rec, rows in sorted(by_record.items()):
            result = json.loads((ROOT / "retrieval" / rec / "result.json").read_text())
            full = [s for s in result["sources"] if s["route"] in ("R1", "R3")
                    and s.get("text")]
            supp_dir = ROOT / "cut_v2" / rec / "files"
            n = len([s for s in result["sources"] if s["route"] == "R2"
                     and s.get("text") is not None])
            supps = [json.loads((supp_dir / f"{k}.json").read_text()) for k in range(n)]
            packets, chunk_log = cp.fulltext_packets(rec, held[rec]["title"], rows,
                                                     held[rec]["abstract"], full, supps, acc)
            log += chunk_log
            for k, p in enumerate(packets, 1):
                write(f"{rec}.{k}", p)
    elif stage == "diagnostic":
        drawn = random.Random(DIAGNOSTIC_SEED).sample(population, min(DIAGNOSTIC_N,
                                                                      len(population)))
        for i, c in enumerate(drawn, 1):
            f = json.loads((ROOT / "cut_v2" / c["record_id"] / "files"
                            / f"{c['file']}.json").read_text())
            chunk = f["chunks"][c["chunk"]]
            if chunk["sha256"] != c["sha256"]:
                raise ValueError(f"chunk {c} differs from the frozen population")
            p = cp.diagnostic_packet(c["record_id"], held[c["record_id"]]["title"],
                                     by_record[c["record_id"]], chunk, i, acc)
            write(f"{c['record_id']}.d{i}", p)
    else:
        raise ValueError(f"unknown stage {stage}")
    (folder / "manifest.json").write_text(json.dumps(manifest))
    vol.commit()
    return {"stage": stage, "packets": len(manifest),
            "records": len({m["record_id"] for m in manifest}),
            "source_characters": sum(f["characters"] for m in manifest for f in m["files"]),
            "packet_characters": sum(m["packet_characters"] for m in manifest),
            "exhaustive_chunk_log": log,
            "diagnostic_draw": {"seed": DIAGNOSTIC_SEED, "drawn": drawn} if drawn else None,
            "manifest": manifest}


def load_packets(stage: str) -> list[tuple[str, dict]]:
    folder = CODING / "packets" / stage
    manifest = json.loads((folder / "manifest.json").read_text())
    return [(m["name"], json.loads((folder / f"{m['name']}.json").read_text()))
            for m in manifest]


@app.function(volumes={str(MOUNT): vol}, timeout=1800, secrets=SECRETS)
def preflight_job(stage: str) -> dict:
    """Free token counts of the stage's largest packet for each model; no model is run."""
    vol.reload()
    prompt, schema = fixed()
    packets = load_packets(stage)
    name, p = max(packets, key=lambda x: len(json.dumps(x[1], ensure_ascii=False)))
    out = {"stage": stage, "packet": name, "packets": len(packets)}
    claude = cr.claude_body(prompt, schema, p)
    count = {k: claude[k] for k in ("model", "system", "messages", "output_config")}
    with httpx.Client(timeout=600) as client:
        r = client.post("https://api.anthropic.com/v1/messages/count_tokens", json=count,
                        headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                                 "anthropic-version": "2023-06-01"})
        out[cr.CLAUDE] = {"status": r.status_code, "input_tokens": r.json().get("input_tokens")
                          if r.status_code == 200 else None,
                          "error": None if r.status_code == 200 else r.text[:1000]}
        sol = cr.sol_body(prompt, schema, p)
        sol.pop("max_output_tokens")
        sol.pop("store")
        r = client.post("https://api.openai.com/v1/responses/input_tokens", json=sol,
                        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"})
        out[cr.SOL] = {"status": r.status_code, "input_tokens": r.json().get("input_tokens")
                       if r.status_code == 200 else None,
                       "error": None if r.status_code == 200 else r.text[:1000]}
    out["characters"] = {"fixed_prompt": len(prompt),
                         "packet": len(json.dumps(p, ensure_ascii=False))}
    return out


@app.function(volumes={str(MOUNT): vol}, timeout=24 * 3600, secrets=SECRETS, memory=16384)
def code_job(stage: str, model: str, workers: int) -> dict:
    vol.reload()
    prompt, schema = fixed()
    ledger = cr.Ledger(CODING / "spend.jsonl", cr.CEILING_USD, persist=vol.commit)
    if model == cr.CLAUDE:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0,
                                     timeout=3600)
        send = lambda body: cr.call_claude(client, body)  # noqa: E731
    else:
        http = httpx.Client(timeout=3600)
        send = lambda body: cr.call_sol(http, os.environ["OPENAI_API_KEY"], body)  # noqa: E731
    runner = cr.Runner(model, prompt, schema, CODING / "answers" / stage / model, ledger,
                       send=send, persist=vol.commit, workers=workers)
    done = runner.run(load_packets(stage))
    vol.commit()
    return {k: v for k, v in done.items() if k != "results"} | {
        "failed": sorted(r["name"] for r in done["results"] if r["state"] == "failed"),
        "pending": sorted(r["name"] for r in done["results"] if r["state"] == "pending"),
        "models_returned": sorted({a["model_returned"] for r in done["results"]
                                   for a in r.get("attempts", []) if a.get("model_returned")})}


def write_once(out: str, data: dict) -> pathlib.Path:
    target = LOCAL / out
    if target.exists():
        raise FileExistsError(f"{target} exists; it is written once")
    target.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    return target


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-2500:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def inputs(queue: str, screening: str) -> None:
    q = json.loads((LOCAL / queue).read_text())
    wanted = {r["record_id"] for r in q["queue"]}
    held = {}
    for path in sorted(screening.split(",")):
        for line in (LOCAL / path).read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("pmid") in wanted and r["pmid"] not in held:
                    held[r["pmid"]] = {"title": r.get("title") or "",
                                       "abstract": r.get("abstract") or ""}
    missing = sorted(wanted - set(held))
    if missing:
        raise SystemExit(f"no stored abstract for {missing[:5]}")
    print(json.dumps(inputs_job.remote(q, held)))


@app.local_entrypoint()
def packets(stage: str, out: str, cut: str = "outputs/cut_v2_2026-10-13.json") -> None:
    population = (json.loads((LOCAL / cut).read_text())["removed_chunk_population"]
                  ["chunks_in_paper_and_file_order"] if stage == "diagnostic" else [])
    result = packets_job.remote(stage, population)
    write_once(out, result)
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("manifest", "exhaustive_chunk_log", "diagnostic_draw")}))


@app.local_entrypoint()
def preflight(stage: str, out: str) -> None:
    if not SECRETS:
        raise SystemExit("the keys are not in the environment")
    result = preflight_job.remote(stage)
    write_once(out, result)
    print(json.dumps(result, indent=1))


@app.local_entrypoint()
def code(stage: str, model: str, approved: str, out: str, workers: int = 8) -> None:
    log = (LOCAL / "PREREG.log").read_text()
    if not approved.strip() or approved not in log:
        raise SystemExit("the approval of this pass is not in PREREG.log")
    if not SECRETS:
        raise SystemExit("the keys are not in the environment")
    result = code_job.remote(stage, model, workers)
    write_once(out, result)
    print(json.dumps(result, indent=1))
