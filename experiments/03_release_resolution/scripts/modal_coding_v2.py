"""Second version of the coding wrapper (scripts/modal_coding.py, sealed, unchanged). The image
mirrors the repository under /repo, so `dataset_relations` finds the dictionary and the
components file where it looks for them (the first versions mounted the components file where
`load_rows` does not read it) and scripts/coding_queue_v2.py finds the repository root. It adds
the C1 control set, the manifest controls, the pricing of the two full-text layouts, and the
second version of the runner; no logic of the study is here.

Run from experiments/03_release_resolution, with the keys in the environment (the 1Password
pipe, with MODAL_TOKEN_ID and MODAL_TOKEN_SECRET unset after loading it):

    modal run scripts/modal_coding_v2.py::tests
    modal run --detach scripts/modal_coding_v2.py::controls --out <json>
    modal run scripts/modal_coding_v2.py::manifest --out <json>
    modal run --detach scripts/modal_coding_v2.py::layouts --controls <json> --out <json>
    modal run --detach scripts/modal_coding_v2.py::code --stage sa1 \\
        --model claude-sonnet-5-5|gpt-6.1-sol --approved "<the logged approval line>" --out <json>

Volume, /03_release_resolution/coding/: c1/<record>.json (each record's scanner matches, written
as the record ends, so a stopped scan resumes); packets/manifest/; the rest as in the first
version. Outputs written locally hold counts, identifiers of public registries, hashes and
unit ids, never source text.

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
R = "/repo/experiments"
E3, E2 = f"{R}/03_release_resolution", f"{R}/02_claims_meta"
IGNORE = ["__pycache__", "*.pyc", ".pytest_cache"]
DEFINITIONS = "outputs/manual_coding/2026-10-03/coders/dictionary_definitions.csv"
REG = "outputs/registry/2026-10-03_amended_primary_coded_a"
CHECKS = ["outputs/verification_amendment02/amended_primary/"
          "sol_extraction_search_0b97103cd7a4_restored/claim_checks.jsonl",
          "outputs/verification_amendment02/amended_primary/"
          "sol_extraction_chase1_0b97103cd7a4_restored/claim_checks.jsonl",
          "outputs/verification/sol_extraction_chase2_0b97103cd7a4/claim_checks.jsonl",
          "outputs/verification/sol_extraction_chase3_0b97103cd7a4/claim_checks.jsonl"]
KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")

image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("httpx==0.28.1", "pydantic==2.13.5", "pyyaml==6.0.3", "pytest==8.4.2",
                      "jsonschema==4.26.0", "anthropic==1.13.0", "numpy==2.5.3",
                      "citations==0.5.5")
         .env({"PYTHONPATH": f"{E3}/scripts:{E2}/scripts"})
         .add_local_dir(LOCAL / "scripts", f"{E3}/scripts", copy=True, ignore=IGNORE)
         .add_local_dir(LOCAL / "tests", f"{E3}/tests", copy=True, ignore=IGNORE)
         .add_local_dir(LOCAL / "reference", f"{E3}/reference", copy=True)
         .add_local_dir(LOCAL / "prompts", f"{E3}/prompts", copy=True)
         .add_local_file(LOCAL / "outputs" / "coding_queue_2026-10-13.json",
                         f"{E3}/outputs/coding_queue_2026-10-13.json", copy=True)
         .add_local_dir(PAPER1 / "scripts", f"{E2}/scripts", copy=True, ignore=IGNORE)
         .add_local_file(PAPER1 / "dataset_dictionary.csv", f"{E2}/dataset_dictionary.csv",
                         copy=True)
         .add_local_file(PAPER1 / "verification" / "dataset_components.csv",
                         f"{E2}/verification/dataset_components.csv", copy=True)
         .add_local_file(PAPER1 / DEFINITIONS, f"{E2}/{DEFINITIONS}", copy=True)
         .add_local_file(PAPER1 / REG / "registry_claims.jsonl",
                         f"{E2}/{REG}/registry_claims.jsonl", copy=True)
         .add_local_file(PAPER1 / REG / "registry_claims_without_manual_coding.jsonl",
                         f"{E2}/{REG}/registry_claims_without_manual_coding.jsonl", copy=True))
for _c in CHECKS:
    image = image.add_local_file(PAPER1 / _c, f"{E2}/{_c}", copy=True)
vol = modal.Volume.from_name(VOLUME)
SECRETS = ([modal.Secret.from_dict({k: os.environ[k] for k in KEYS})]
           if all(os.environ.get(k) for k in KEYS) else [])
app = modal.App("release-resolution-coding-v2", image=image)

with image.imports():
    import csv
    import subprocess

    import anthropic
    import httpx

    import c1_controls as c1
    import coding_packets as cp
    import coding_packets_v2 as cp2
    import coding_queue as q
    import coding_runner as cr
    import coding_runner_v2 as cr2
    import source_scanner_v2 as scanner

TESTS = ["test_c1_controls.py", "test_coding_gate.py", "test_coding_runner_v2.py",
         "test_coding_packets_v2.py", "test_coding_queue_v2.py", "test_coding_queue.py",
         "test_coding_packets.py", "test_coding_runner.py", "test_cut_supplements_v2.py",
         "test_prompt_schemas.py", "test_source_scanner_v2.py"]


def reference():
    patterns = json.loads(open(f"{E3}/reference/c1_scanner_patterns_v2.json").read())
    with open(f"{E3}/reference/accession_releases.csv", newline="") as fh:
        table = list(csv.DictReader(fh))
    with open(f"{E2}/dataset_dictionary.csv", newline="") as fh:
        dictionary = list(csv.DictReader(fh))
    return patterns, table, dictionary


def fixed() -> tuple[str, dict]:
    prompt = cp.fixed_prompt(open(f"{E3}/prompts/coding_prompt_v2.md").read(),
                             open(f"{E2}/{DEFINITIONS}").read())
    return prompt, json.loads(open(f"{E3}/prompts/output_schema.json").read())


@app.function(timeout=3600, cpu=2.0)
def tests_job(files: list[str]) -> dict:
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", *files],
                         capture_output=True, text=True, cwd=f"{E3}/tests")
    return {"returncode": run.returncode, "output": run.stdout + run.stderr}


@app.function(volumes={str(MOUNT): vol}, timeout=12 * 3600, cpu=1.0, memory=32768, retries=2,
              max_containers=24)
def controls_record(record_id: str) -> dict:
    out = CODING / "c1" / f"{record_id}.json"
    vol.reload()
    if out.exists():
        return json.loads(out.read_text())
    patterns, table, dictionary = reference()
    mapper = scanner.Mapper(patterns, table, dictionary)
    result = json.loads((ROOT / "retrieval" / record_id / "result.json").read_text())
    units = c1.units(record_id, result["sources"])
    found = scanner.controls(units, patterns, mapper)
    readable = [s for s in result["sources"] if s.get("text")]
    r2 = [s for s in result["sources"] if s["route"] == "R2" and s.get("text") is not None]
    kept = {}
    for c in found:
        route, n = c["source_key"].split(":")[:2]
        src = readable[int(n) - 1]
        if route != "R2":
            kept[c["unit_id"]] = True
            continue
        f = json.loads((ROOT / "cut_v2" / record_id / "files"
                        / f"{r2.index(src)}.json").read_text())
        if not f["cut"]:
            kept[c["unit_id"]] = True
            continue
        line = src["text"].split("\n")[int(c["unit_id"].split(":")[3])]
        kept[c["unit_id"]] = line in {r["line"] for r in f["rows"]}
    held = {"record_id": record_id, "units": len(units), "found": found,
            "found_in_text_the_cut_keeps": kept}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(held))
    vol.commit()
    return held


@app.function(volumes={str(MOUNT): vol}, timeout=1800)
def manifest_job() -> dict:
    patterns, table, dictionary = reference()
    acc = cp.read_accessions(f"{E3}/reference/c1_scanner_patterns_v2.json",
                             f"{E3}/reference/accession_releases.csv")
    side_of = {r["name"]: r["side"] for r in dictionary}
    made = c1.manifest_packets(table, side_of, q.side_rows(pathlib.Path(
        f"{E2}/dataset_dictionary.csv")), acc)
    folder = CODING / "packets" / "manifest"
    if (folder / "manifest.json").exists():
        raise FileExistsError(f"{folder} holds packets already")
    folder.mkdir(parents=True, exist_ok=True)
    listing = []
    for m in made:
        name = f"{m['packet']['record_id']}.1"
        (folder / f"{name}.json").write_text(json.dumps(m["packet"]))
        listing.append({"name": name, "record_id": m["packet"]["record_id"],
                        "expected_row": m["expected_row"], "identifier": m["identifier"],
                        "row_id": m["packet"]["rows"][0]["row_id"]})
    (folder / "manifest.json").write_text(json.dumps(listing))
    vol.commit()
    return {"packets": len(listing), "listing": listing}


@app.function(volumes={str(MOUNT): vol}, timeout=6 * 3600, memory=32768)
def layouts_job(control_rows: list[dict]) -> dict:
    vol.reload()
    queue = json.loads((CODING / "inputs" / "queue.json").read_text())
    held = json.loads((CODING / "inputs" / "abstracts.json").read_text())
    acc = cp.read_accessions(f"{E3}/reference/c1_scanner_patterns_v2.json",
                             f"{E3}/reference/accession_releases.csv")
    by_record: dict[str, list[dict]] = {}
    for r in queue["queue"]:
        by_record.setdefault(r["record_id"], []).append(r)
    controls: dict[str, list[dict]] = {}
    for r in control_rows:
        controls.setdefault(r["record_id"], []).append(r)
    per = {"first_request_carries": [], "every_request_carries": []}
    for rec, rows in sorted(by_record.items()):
        rows = c1.merge(rows, controls.get(rec, []))
        result = json.loads((ROOT / "retrieval" / rec / "result.json").read_text())
        full = [s for s in result["sources"] if s["route"] in ("R1", "R3") and s.get("text")]
        n = len([s for s in result["sources"] if s["route"] == "R2"
                 and s.get("text") is not None])
        supps = [json.loads((ROOT / "cut_v2" / rec / "files" / f"{k}.json").read_text())
                 for k in range(n)]
        carried = len(held[rec]["abstract"]) + sum(len(s["text"]) for s in full)
        for name, build in (("first_request_carries", cp.fulltext_packets),
                            ("every_request_carries", cp2.fulltext_packets_carrying)):
            packets, _ = build(rec, held[rec]["title"], rows, held[rec]["abstract"], full,
                               supps, acc)
            per[name].append({"record_id": rec, "carried": carried,
                              "packets": [len(json.dumps(p, ensure_ascii=False))
                                          for p in packets],
                              "source_characters": [sum(len(f["text"]) for f in p["files"])
                                                    for p in packets]})
    prompt = len(fixed()[0])
    ratios = {"pooled_full_text_ratios_of_the_plan": {"claude-sonnet-5-5": 2.62,
                                                      "gpt-6.1-sol": 4.28},
              "preflight_ratios": {"claude-sonnet-5-5": 1.98, "gpt-6.1-sol": 3.11}}
    estimates = {}
    for layout, recs in per.items():
        estimates[layout] = {
            "requests_per_model": sum(len(r["packets"]) for r in recs),
            "records_with_several_requests": sum(len(r["packets"]) > 1 for r in recs),
            "packet_characters": sum(sum(r["packets"]) for r in recs),
            "by_ratio": {name: cp2.layout_cost(recs, prompt, ratio,
                                               carrying=layout == "every_request_carries")
                         for name, ratio in ratios.items()}}
    return {"fixed_prompt_characters": prompt, "control_rows_merged": len(control_rows),
            "output_tokens_per_request": cp2.OUTPUT_TOKENS, "prices": cp2.PRICE,
            "estimates": estimates, "note": "coding pass only; SA1, control-only papers, the "
            "manifest packets and the diagnostic are priced apart; output tokens exclude "
            "thinking and reasoning tokens, which the framing leaves at the API's defaults",
            "per_record": per}


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
    folder = CODING / "packets" / stage
    manifest = json.loads((folder / "manifest.json").read_text())
    packets = [(m["name"], json.loads((folder / f"{m['name']}.json").read_text()))
               for m in manifest]
    runner = cr2.Runner(model, prompt, schema, CODING / "answers" / stage / model, ledger,
                        send=send, persist=vol.commit, workers=workers)
    done = runner.run(packets)
    vol.commit()
    return {k: v for k, v in done.items() if k != "results"} | {
        "failed": sorted(r["name"] for r in done["results"] if r["state"] == "failed"),
        "pending": sorted(r["name"] for r in done["results"] if r["state"] == "pending"),
        "models_returned": sorted({a["model_returned"] for r in done["results"]
                                   for a in r.get("attempts", []) if a.get("model_returned")})}


def write_once(out: str, data: dict) -> None:
    target = LOCAL / out
    if target.exists():
        raise FileExistsError(f"{target} exists; it is written once")
    target.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


@app.local_entrypoint()
def tests(only: str = "") -> None:
    result = tests_job.remote(only.split(",") if only else TESTS)
    print(result["output"][-3000:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=16384)
def controls_summary_job(records: list[str], queue: dict) -> dict:
    vol.reload()
    patterns, table, dictionary = reference()
    held = [json.loads((CODING / "c1" / f"{r}.json").read_text()) for r in records]
    found = [c for h in held for c in h["found"]]
    drawn = scanner.draw(found, patterns)
    kept = {u: k for h in held for u, k in h["found_in_text_the_cut_keeps"].items()}
    rows = c1.control_rows(drawn, queue["queue"], q.side_rows(pathlib.Path(
        f"{E2}/dataset_dictionary.csv")))
    return {"records_scanned": len(held), "units": sum(h["units"] for h in held),
            "found": len(found), "unique_record_identifier_row": len(
                {(c["record_id"], c["identifier"], c["expected_row"]) for c in found}),
            "drawn": len(drawn), "minimum": patterns["draw"]["minimum"],
            "maximum": patterns["draw"]["maximum"], "seed": patterns["draw"]["seed"],
            "extension_needed": len(drawn) < patterns["draw"]["minimum"],
            "drawn_by_side": {s: sum(c["side"] == s for c in drawn)
                              for s in ("pqtl", "outcome")},
            "drawn_by_kind": {k: sum(c["kind"] == k for c in drawn)
                              for k in sorted({c["kind"] for c in drawn})},
            "drawn_records": len({c["record_id"] for c in drawn}),
            "drawn_in_text_the_cut_keeps": sum(kept.get(c["unit_id"], False) for c in drawn),
            "found_by_record": {h["record_id"]: len(h["found"]) for h in held if h["found"]},
            "drawn_controls": drawn, "control_rows": rows}


@app.local_entrypoint()
def controls(out: str) -> None:
    records = sorted(json.loads((PAPER1 / "outputs/release_resolution/"
                                          "availability_2026-10-08.json").read_text())["records"])
    list(controls_record.map(records))
    queue = json.loads((LOCAL / "outputs" / "coding_queue_2026-10-13.json").read_text())
    result = controls_summary_job.remote(records, queue)
    write_once(out, result)
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("drawn_controls", "control_rows", "found_by_record")}, indent=1))


@app.local_entrypoint()
def manifest(out: str) -> None:
    result = manifest_job.remote()
    write_once(out, result)
    print(json.dumps({"packets": result["packets"]}))


@app.local_entrypoint()
def layouts(controls: str, out: str) -> None:
    rows = json.loads((LOCAL / controls).read_text())["control_rows"]
    result = layouts_job.remote(rows)
    write_once(out, result)
    print(json.dumps({"estimates": result["estimates"]}, indent=1))


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
