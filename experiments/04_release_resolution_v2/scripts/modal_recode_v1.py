"""Modal wrapper of the stage A recode of the second release-resolution registration
(scripts/recode_v1.py holds the logic; scripts/spend_caps_v1.py the stops), on the image of
scripts/modal_retrieve_v2.py. Coders through the first registration's scripts/coding_runner_v3.py
(sealed, unchanged): a response that is not HTTP 200, a credit refusal among them, leaves its
request pending and is not an attempt; every exchange is stored on the volume as it ends and a
stored answer is never sent again; pending requests are sent again in up to ROUNDS rounds
ROUND_WAIT seconds apart.

    PYTHONPATH=../03_release_resolution/scripts modal run scripts/modal_recode_v1.py::tests
    ... modal run scripts/modal_recode_v1.py::preflight --out <json>
    ... modal run --detach scripts/modal_recode_v1.py::code --approved "<logged line>" --out <json>
    ... modal run scripts/modal_recode_v1.py::gate_and_count --out <json>

`code` refuses to start unless its approval line stands in PREREG.log and the coding prompt is v3.
Volume, /04_release_resolution_v2/coding/: answers/stage_a/<model>/; gate/stage_a/<model>/
(row verdicts, pinned quotes); runs/. The spend ledger is the one ledger of both registrations.
"""

import json
import os
import pathlib
import time

import modal

from modal_coding_v2 import CODING, DEFINITIONS, E2, E3, MOUNT, SECRETS, vol
from modal_retrieve_v2 import E4, LOCAL, ROOT4, image as base

image = base.add_local_dir(LOCAL / "prompts", f"{E4}/prompts", copy=True)
app = modal.App("release-resolution-v2-recode", image=image)
MODELS = ("claude-sonnet-5-5", "gpt-6.1-sol")
ROUNDS = 6
ROUND_WAIT = 600
FOLDER = ROOT4 / "coding"
PACKETS = ROOT4 / "packets" / "stage_a"
PROMPT_V3 = "prompts/coding_prompt_v3.md"
PACKETS_OUT = "outputs/stage_a_packets_2026-10-20.json"
CONTROLS = "outputs/control_set_2026-10-20.json"
ESTIMATE = "outputs/stage_a_cost_estimate_2026-10-20.json"
FIRST_CONTROLS = "../03_release_resolution/outputs/c1a_controls_2026-10-13.json"
RATIOS = {"claude-sonnet-5-5": 1.98, "gpt-6.1-sol": 3.11}
TESTS = ["test_recode_v1.py", "test_spend_caps_v1.py", "test_coding_gate_v2.py",
         "test_judge_v4.py"]
FIRST_TESTS = ["test_coding_runner_v3.py", "test_coding_runner_v2.py", "test_coding_runner.py",
               "test_stage_a_counts_v1.py", "test_coding_gate.py", "test_pass_summary.py"]

with image.imports():
    import collections
    import concurrent.futures
    import csv
    import hashlib
    import subprocess

    import anthropic
    import httpx

    import coding_gate as gate
    import coding_runner as cr
    import coding_runner_v3 as cr3
    import pass_summary as ps
    import recode_v1 as rc
    import source_scanner_v2 as scanner
    import spend_caps_v1 as caps
    import stage_a_counts_v1 as sc


def schema() -> dict:
    return json.loads(open(f"{E3}/prompts/output_schema.json").read())


def definitions() -> str:
    return open(f"{E2}/{DEFINITIONS}").read()


def load() -> list[tuple[str, dict]]:
    return [(m["name"], json.loads((PACKETS / f"{m['name']}.json").read_text()))
            for m in json.loads((PACKETS / "manifest.json").read_text())]


def file_sha256(path) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


@app.function(timeout=1800, cpu=2.0, memory=8192)
def tests_job() -> dict:
    out, code = "", 0
    for cwd, files in ((f"{E4}/tests", TESTS), (f"{E3}/tests", FIRST_TESTS)):
        run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", *files],
                             capture_output=True, text=True, cwd=cwd)
        out += run.stdout + run.stderr
        code = code or run.returncode
    return {"returncode": code, "output": out}


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=32768)
def preflight_job(v3: str, packet_sha256: dict, old_controls: list[str],
                  drawn_controls: list[str], estimate: dict) -> dict:
    vol.reload()
    prompt, sch, defs = rc.fixed_prompt(v3, definitions()), schema(), definitions()
    packets = load()
    bodies = {}
    for m in MODELS:
        runner = cr3.Runner(m, prompt, sch, pathlib.Path("/tmp/preflight") / m, None)
        bodies[m] = [(name, runner.body(p)) for name, p in packets]
    out = rc.preflight(bodies, v3, defs, sch, packet_sha256, set(old_controls),
                       set(drawn_controls))
    tokens = {}
    for m in MODELS:
        chars = [len(rc.embedded(m, b)[0]) + len(rc.embedded(m, b)[2]) for _, b in bodies[m]]
        prompt_tokens = len(prompt) / RATIOS[m]
        tokens[m] = {"characters_per_request_total": sum(chars),
                     "input_tokens_at_the_preflight_ratio": round(sum(chars) / RATIOS[m]),
                     "fixed_prompt_tokens_cached_after_the_first": round(prompt_tokens),
                     "new_input_tokens": round(sum(chars) / RATIOS[m]
                                               - prompt_tokens * (len(chars) - 1)),
                     "largest_request_input_tokens": round(max(chars) / RATIOS[m])}
    coders = estimate["coders"]["preflight_ratios"]
    judges = estimate["judges"]
    per_provider = {}
    for label, c_key, j_key in (("1500", "1500", "1500"), ("3000", "3000", "3000"),
                                ("6000_coders_8192_judges", "6000", "8192"),
                                ("measured_coders_1500_judges",
                                 "measured_output_of_the_first_stage_a", "1500")):
        a = coders[c_key]["claude-sonnet-5-5"] + judges[j_key]["claude-fable-5-1"]["expected_usd"]
        o = coders[c_key]["gpt-6.1-sol"] + judges[j_key]["gpt-6-astra"]["expected_usd"]
        per_provider[label] = {"anthropic_usd": round(a, 2), "openai_usd": round(o, 2),
                               "anthropic_coding_usd": coders[c_key]["claude-sonnet-5-5"],
                               "openai_coding_usd": coders[c_key]["gpt-6.1-sol"]}
    ledger = caps.CappedLedger(CODING / "spend.jsonl")
    out |= {"framing": "prompts/api_framing_v2.md as coding_runner.claude_body and sol_body "
                       "build it; bodies built by coding_runner_v3.Runner.body",
            "framing_sha256": file_sha256(f"{E3}/prompts/api_framing_v2.md"),
            "schema_file_sha256": file_sha256(f"{E3}/prompts/output_schema.json"),
            "schema_canonical_sha256": rc.sha256(json.dumps(sch, sort_keys=True).encode()),
            "definitions_file_sha256": file_sha256(f"{E2}/{DEFINITIONS}"),
            "max_output_tokens": {m: (b["max_tokens"] if m == cr.CLAUDE
                                      else b["max_output_tokens"])
                                  for m in MODELS for _, b in bodies[m][:1]},
            "models_in_bodies": {m: sorted({b["model"] for _, b in bodies[m]}) for m in MODELS},
            "tokens": tokens, "estimated_spend_by_provider": per_provider,
            "stops": {"registration_ceiling_on_the_ledger_usd": ledger.ceiling,
                      "registration_new_spend_so_far_usd": round(ledger.new_spend(), 4),
                      "registration_room_usd": round(ledger.ceiling - ledger.spent, 4),
                      "anthropic_cap_usd": caps.PROVIDER_CAPS_USD["anthropic"],
                      "anthropic_spent_this_registration_usd":
                          round(ledger.provider_spent["anthropic"], 4),
                      "openai_spent_this_registration_usd":
                          round(ledger.provider_spent["openai"], 4)},
            "packets_manifest_sha256": file_sha256(PACKETS / "manifest.json")}
    return out


@app.function(volumes={str(MOUNT): vol}, timeout=24 * 3600, secrets=SECRETS, memory=16384)
def code_job(v3: str, workers: int) -> dict:
    vol.reload()
    if rc.sha256(v3.encode()) != rc.V3_SHA256:
        raise rc.PreflightError("the coding prompt is not v3")
    prompt, sch = rc.fixed_prompt(v3, definitions()), schema()
    ledger = caps.CappedLedger(CODING / "spend.jsonl", persist=vol.commit)
    start = ledger.spent
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0,
                                 timeout=3600)
    http = httpx.Client(timeout=3600)
    sends = {"claude-sonnet-5-5": lambda body: cr3.call_claude(client, body),
             "gpt-6.1-sol": lambda body: cr.call_sol(http, os.environ["OPENAI_API_KEY"], body)}
    packets = load()
    rounds = []
    for k in range(ROUNDS):
        runners = {m: cr3.Runner(m, prompt, sch, FOLDER / "answers" / "stage_a" / m,
                                 ledger.view(m), send=sends[m], persist=vol.commit,
                                 workers=workers) for m in MODELS}
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            futures = {m: pool.submit(runners[m].run, packets) for m in MODELS}
            done = {m: f.result() for m, f in futures.items()}
        summary = {m: {key: v for key, v in d.items() if key != "results"} | {
            "pending": sorted(r["name"] for r in d["results"] if r["state"] == "pending"),
            "failed": sorted(r["name"] for r in d["results"] if r["state"] == "failed"),
            "models_returned": sorted({a["model_returned"] for r in d["results"]
                                       for a in r.get("attempts", []) if a.get("model_returned")})}
            for m, d in done.items()}
        rounds.append(summary)
        (FOLDER / "runs").mkdir(parents=True, exist_ok=True)
        (FOLDER / "runs" / "stage_a_code.json").write_text(json.dumps({"rounds": rounds}))
        vol.commit()
        print(f"{time.strftime('%H:%M:%S')} round {k + 1}: " + json.dumps(
            {m: s["states"] | {"not_sent": s["not_sent_ceiling"], "stopped": s["stopped"]}
             for m, s in summary.items()}), flush=True)
        if any(s["stopped"] for s in summary.values()):
            break
        if not any(s["pending"] for s in summary.values()):
            break
        time.sleep(ROUND_WAIT)
    out = {"rounds": rounds, "ledger_usd_at_start": round(start, 4),
           "ledger_usd_at_end": round(ledger.spent, 4),
           "spent_in_this_job_usd": round(ledger.spent - start, 4),
           "registration_new_spend_usd": round(ledger.new_spend(), 4),
           "anthropic_spent_this_registration_usd": round(ledger.provider_spent["anthropic"], 4),
           "openai_spent_this_registration_usd": round(ledger.provider_spent["openai"], 4)}
    (FOLDER / "runs" / "stage_a_code.json").write_text(json.dumps(out))
    vol.commit()
    return out


@app.function(volumes={str(MOUNT): vol}, timeout=6 * 3600, memory=32768)
def gate_and_count_job(controls: dict, kinds: dict) -> dict:
    vol.reload()
    patterns = json.loads(open(f"{E3}/reference/c1_scanner_patterns_v2.json").read())
    with open(f"{E3}/reference/accession_releases.csv", newline="") as fh:
        table = list(csv.DictReader(fh))
    dictionary = gate.dictionary_rows(f"{E2}/dataset_dictionary.csv")
    mapper = scanner.Mapper(patterns, table, list(dictionary.values()))
    manifest = json.loads((PACKETS / "manifest.json").read_text())
    packets = dict(load())
    population = {m["name"]: m["population"] for m in manifest}
    rows_of = {"scope_study": [], "outside_study": []}
    for name, p in packets.items():
        for r in p["rows"]:
            if r["row_id"] not in controls:
                rows_of["scope_study" if population[name] == "scope" else "outside_study"].append(
                    r["row_id"])
    answers, verdicts, bases, counts, keys = {}, {}, {}, {}, set()
    for model in MODELS:
        store = FOLDER / "answers" / "stage_a" / model
        folder = FOLDER / "gate" / "stage_a" / model
        if (folder / "rows.json").exists():
            raise FileExistsError(f"{folder} is gated already")
        finals = [json.loads(p.read_text()) for p in sorted(store.glob("*.json"))
                  if ".attempt" not in p.name]
        keys |= {f["key"] for f in finals}
        c, failures = collections.Counter(), collections.Counter()
        answers[model], verdicts[model], bases[model] = {}, {}, {}
        for f in finals:
            c[f["state"]] += 1
            if f["state"] != "accepted":
                continue
            p = packets[f["name"]]
            root = ROOT4 if population[f["name"]] == "outside_scope" else MOUNT / \
                "03_release_resolution"
            sources = json.loads((root / "retrieval" / p["record_id"] / "result.json")
                                 .read_text())["sources"]
            frozen = rc.frozen_files(p, sources)
            for rid, g in rc.gate_answers(p, f["answer"]["rows"], frozen, patterns, mapper,
                                          dictionary).items():
                row = next(r for r in f["answer"]["rows"] if r["row_id"] == rid)
                answers[model][rid] = row
                verdicts[model][rid] = g["passes"]
                bases[model][rid] = {rel: v["basis"] for rel, v in g["releases"].items()}
                c["rows_gated"] += 1
                c["rows_passing" if g["passes"] else "rows_failing"] += 1
                c["rows_passing_through_the_inline_d2_rule"] += any(
                    str(v["basis"]).startswith("D2:inline") for v in g["releases"].values())
                for rel in g["releases"].values():
                    for fl in rel["failures"]:
                        for e in (fl["errors"] if isinstance(fl, dict) else [fl]):
                            failures[e] += 1
                for n, q in enumerate(g["to_pin"], 1):
                    got = gate.pin(folder, frozen[q["file_id"]], f"{rid}_{n}", q["quote"])
                    c["quotes_pinned" if got["pinned"] else "quotes_refused_by_pin"] += 1
        verified = gate.verify(folder) if (folder / "claims").exists() else {"returncode": None}
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "rows.json").write_text(json.dumps({"verdicts": verdicts[model],
                                                      "bases": bases[model]}))
        vol.commit()
        counts[model] = {"answers": dict(c), "gate_failures_by_error": dict(failures),
                         "citations_verify_returncode": verified["returncode"]}
    first, second = (answers[m] for m in MODELS)
    out = {"gate": f"{rc.GATE.__module__}.{rc.GATE.__name__}", "gate_counts": counts,
           "agreement": {"scope_study_rows": sc.agreement(rows_of["scope_study"], first, second),
                         "outside_study_rows": sc.agreement(rows_of["outside_study"], first,
                                                            second),
                         "control_rows": sc.agreement(sorted(controls), first, second)},
           "c1_on_the_coders_answers": rc.c1_by_type(controls, kinds, answers, verdicts, bases),
           "note": "the coders' answers before any judge, settling or adjudication; the "
                   "registered C1 is computed on accepted codes"}
    adj = ps.adjudication_rows(rows_of["scope_study"] + rows_of["outside_study"]
                               + sorted(controls), first, second)
    (FOLDER / "gate" / "stage_a" / "adjudication_rows.json").write_text(json.dumps(adj))
    entries = [json.loads(line) for line in (CODING / "spend.jsonl").read_text().splitlines()
               if line.strip()]
    out["usage"] = ps.usage_summary([e for e in entries if e["request_key"] in keys])
    out["rows_to_adjudicate"] = {k: v for k, v in adj.items() if not isinstance(v, list)}
    vol.commit()
    return out


def write_once(out: str, data) -> None:
    target = LOCAL / out
    if target.exists():
        raise FileExistsError(f"{target} exists; it is written once")
    target.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def local_inputs():
    listing = json.loads((LOCAL / PACKETS_OUT).read_text())["manifest"]
    drawn = json.loads((LOCAL / CONTROLS).read_text())
    first = json.loads((LOCAL / FIRST_CONTROLS).read_text())
    return listing, drawn, first


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-3000:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def preflight(out: str) -> None:
    listing, drawn, first = local_inputs()
    v3 = (LOCAL / PROMPT_V3).read_text()
    result = preflight_job.remote(v3, {m["name"]: m["packet_sha256"] for m in listing},
                                  [r["row_id"] for r in first["control_rows"]],
                                  drawn["drawn_row_ids"],
                                  json.loads((LOCAL / ESTIMATE).read_text()))
    result["inputs_sha256"] = {p: file_sha256(LOCAL / p) for p in
                               (PROMPT_V3, PACKETS_OUT, CONTROLS, ESTIMATE, FIRST_CONTROLS)}
    write_once(out, result)
    print(json.dumps(result, indent=1))


@app.local_entrypoint()
def code(approved: str, out: str, workers: int = 8) -> None:
    log = (LOCAL / "PREREG.log").read_text()
    if not approved.strip() or approved not in log:
        raise SystemExit("the approval of this pass is not in PREREG.log")
    if not SECRETS:
        raise SystemExit("the keys are not in the environment")
    result = code_job.remote((LOCAL / PROMPT_V3).read_text(), workers)
    write_once(out, result)
    print(json.dumps({k: v for k, v in result.items() if k != "rounds"}, indent=1))


@app.local_entrypoint()
def gate_and_count(out: str) -> None:
    _, drawn, _ = local_inputs()
    controls = {r["row_id"]: r["expected_row"] for r in drawn["control_rows"]}
    kinds = {r["row_id"]: r["identifier_kind"] for r in drawn["control_rows"]}
    result = gate_and_count_job.remote(controls, kinds)
    write_once(out, result)
    print(json.dumps(result, indent=1)[:8000])
