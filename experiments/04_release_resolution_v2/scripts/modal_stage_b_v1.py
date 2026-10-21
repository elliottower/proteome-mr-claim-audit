"""Modal wrapper of the stage B decision (scripts/stage_b_v1.py), on the image of
scripts/modal_recode_v1.py. No model is called. It reads, for the 266 records of the scope, the
first registration's retrieval results (readable supplements), its cut of Amendment 1 (cut_v2),
its stage A queue rows and stored abstracts, all on the volume; builds the stage B packets of the
records stage B would read; prices them; and applies the rule to this registration's new spend.

    PYTHONPATH=../03_release_resolution/scripts modal run scripts/modal_stage_b_v1.py::tests
    ... modal run scripts/modal_stage_b_v1.py::decide --out <json>
"""

import hashlib
import json

import modal

from modal_coding_v2 import CODING, DEFINITIONS, E2, E3, MOUNT, ROOT, vol
from modal_recode_v1 import LOCAL, PROMPT_V3, image, write_once
from modal_retrieve_v2 import E4

app = modal.App("release-resolution-v2-stage-b-decision", image=image)
ACCEPTED = "outputs/stage_a_accepted_codes_2026-10-21.json"
GATE_COUNTS = "outputs/stage_a_gate_counts_2026-10-20.json"
CUT = "../03_release_resolution/outputs/cut_v2_2026-10-13.json"

with image.imports():
    import subprocess

    import coding_packets as cp
    import coding_packets_v2 as cp2
    import spend_caps_v1 as caps
    import stage_b_v1 as sb


@app.function(timeout=900)
def tests_job() -> dict:
    out, code = "", 0
    for cwd, files in ((f"{E4}/tests", ["test_stage_b_v1.py"]),
                       (f"{E3}/tests", ["test_audit_pricing.py", "test_coding_packets_v2.py"])):
        run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", *files],
                             capture_output=True, text=True, cwd=cwd)
        out += run.stdout + run.stderr
        code = code or run.returncode
    return {"returncode": code, "output": out}


@app.function(volumes={str(MOUNT): vol}, timeout=6 * 3600, memory=32768)
def decide_job(v3: str, accepted: dict, means: dict, diagnostic: float) -> dict:
    vol.reload()
    queue = json.loads((CODING / "inputs" / "queue.json").read_text())["queue"]
    held = json.loads((CODING / "inputs" / "abstracts.json").read_text())
    rows_by_record: dict[str, list[dict]] = {}
    for r in queue:
        rows_by_record.setdefault(r["record_id"], []).append(r)
    with_supp, n_supp = set(), {}
    for rec in rows_by_record:
        result = json.loads((ROOT / "retrieval" / rec / "result.json").read_text())
        n = len([s for s in result["sources"] if s["route"] == "R2" and s.get("text") is not None])
        n_supp[rec] = n
        if any(s["route"] == "R2" and s.get("text") for s in result["sources"]):
            with_supp.add(rec)
    chosen = sb.records({r: [x["row_id"] for x in rows] for r, rows in rows_by_record.items()},
                        accepted, with_supp)
    acc = cp.read_accessions(f"{E3}/reference/c1_scanner_patterns_v2.json",
                             f"{E3}/reference/accession_releases.csv")
    prompt = len(cp.fixed_prompt(v3, open(f"{E2}/{DEFINITIONS}").read()))
    packets = {}
    for rec in chosen["unresolved_records"] + chosen["audit_records"]:
        result = json.loads((ROOT / "retrieval" / rec / "result.json").read_text())
        full = [s for s in result["sources"] if s["route"] in ("R1", "R3") and s.get("text")]
        supps = [json.loads((ROOT / "cut_v2" / rec / "files" / f"{k}.json").read_text())
                 for k in range(n_supp[rec])]
        built, _ = cp2.fulltext_packets_carrying(rec, held[rec]["title"], rows_by_record[rec],
                                                 held[rec]["abstract"], full, supps, acc)
        carried = len(held[rec]["abstract"]) + sum(len(s["text"]) for s in full)
        packets[rec] = {"record_id": rec, "carried": carried,
                        "packets": [len(json.dumps(p, ensure_ascii=False)) for p in built]}
    output = sb.output_tokens(means)
    unres = sb.bound(packets, chosen["unresolved_records"], prompt, output, 0.0)
    audit = sb.bound(packets, chosen["audit_records"], prompt, output, 0.0)
    total = round(unres["coding_usd"] + audit["coding_usd"] + diagnostic, 2)
    ledger = caps.CappedLedger(CODING / "spend.jsonl")
    return {"records_of_the_scope": len(rows_by_record),
            "records_with_a_readable_supplement": len(with_supp),
            "unresolved_records_with_a_supplement": len(chosen["unresolved_records"]),
            "resolved_records_with_a_supplement": len(chosen["resolved_records_with_a_supplement"]),
            "audit_records": chosen["audit_records"], "audit_seed": sb.AUDIT_SEED,
            "unresolved_record_ids": chosen["unresolved_records"],
            "output_tokens_per_request": output, "stage_a_mean_output_per_request": means,
            "fixed_prompt_characters": prompt,
            "unresolved_records_bound": {k: v for k, v in unres.items() if k != "per_record_usd"},
            "audit_bound": {k: v for k, v in audit.items() if k != "per_record_usd"},
            "diagnostic_usd": diagnostic,
            "per_record_usd": unres["per_record_usd"] | audit["per_record_usd"],
            "decision": sb.decide(total, ledger.new_spend())}


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-2500:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def decide(out: str) -> None:
    accepted = json.loads((LOCAL / ACCEPTED).read_text())["rows"]
    usage = json.loads((LOCAL / GATE_COUNTS).read_text())["usage"]
    means = {m: usage[m]["mean_output_tokens_per_request"]
             for m in ("claude-sonnet-5-5", "gpt-6.1-sol")}
    cut = json.loads((LOCAL / CUT).read_text())
    diagnostic = cut["cost_estimate"]["diagnostic_400_chunks"]["usd"]
    result = decide_job.remote((LOCAL / PROMPT_V3).read_text(), accepted, means, diagnostic)
    result["inputs_sha256"] = {p: hashlib.sha256((LOCAL / p).read_bytes()).hexdigest()
                               for p in (ACCEPTED, GATE_COUNTS, CUT, PROMPT_V3)}
    write_once(out, result)
    print("written", out)
