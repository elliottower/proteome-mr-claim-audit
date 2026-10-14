"""Modal wrapper for the SA1 calibration (scripts/sa1_calibration_v1.py). It reuses the image,
context and requests of scripts/modal_judge.py and the judges' stores of
scripts/modal_judge_v3.py (both sealed, unchanged). On the volume it reads, for each calibration
row of the routing output, both judges' stored results, checks that the row was decided alone
(judge_v2.route_pair gives no reason, so the two choices are one), and returns only that choice
and the sha256 of each stored file; the judges' reasons and quotations stay on the volume. The
local entrypoint scores the author's marks and writes a counts-only summary to outputs/.

    modal run scripts/modal_sa1_calibration_v1.py::tests
    modal run scripts/modal_sa1_calibration_v1.py::calibrate --marks <marks json> --key <page key json> \\
        --routing outputs/sa1_two_judges_routing_2026-10-14.json --out <outputs json>
"""

import hashlib
import json

import modal

from modal_coding_v2 import E3, LOCAL, MOUNT, vol
from modal_judge import PAGE_SEED, SEEDS, context, image, requests_of, system, write_once
from modal_judge_v3 import store_of

import sa1_calibration_v1 as cal

app = modal.App("release-resolution-sa1-calibration-v1", image=image)

with image.imports():
    import subprocess

    import judge_v2 as j2


@app.function(timeout=900)
def tests_job() -> dict:
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                          "test_sa1_calibration_v1.py"], capture_output=True, text=True,
                         cwd=f"{E3}/tests")
    return {"returncode": run.returncode, "output": run.stdout + run.stderr}


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=8192)
def joint_job(stage: str, rows: dict[str, str]) -> dict:
    """`rows`: row id -> task. Returns row id -> the joint choice, and the stored files' sha256."""
    vol.reload()
    reqs = {rid: (task, req, gates) for task, rid, req, gates in requests_of(context(stage))}
    schema = json.loads(open(f"{E3}/prompts/judge_schema.json").read())
    sysx = system()
    joint, hashes = {}, {}
    for rid, task in rows.items():
        t, req, gates = reqs[rid]
        if t != task:
            raise cal.CalibrationError("a calibration row is of another task")
        res = {}
        for m in j2.JUDGES:
            path = store_of(stage, m) / f"{rid}.{j2.request_key(m, sysx, schema, req)}.json"
            raw = path.read_bytes()
            hashes[f"{m}/{path.name}"] = hashlib.sha256(raw).hexdigest()
            res[m] = json.loads(raw)
        if j2.route_pair(task, res, gates, "\n".join(f["text"] for f in req["files"])):
            raise cal.CalibrationError("a calibration row was not decided alone")
        joint[rid] = res[j2.JUDGES[0]]["decision"]["choice"]
    return {"joint": joint, "stored_sha256": hashes}


def sha(path) -> str:
    return hashlib.sha256((LOCAL / path).read_bytes()).hexdigest()


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-2500:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def calibrate(marks: str, key: str, routing: str, out: str) -> None:
    saved = json.loads((LOCAL / marks).read_text())
    page_key = json.loads((LOCAL / key).read_text())
    routed = json.loads((LOCAL / routing).read_text())
    rows = {rid: task for task in ("disagreement", "audit")
            for rid in routed["tasks"][task]["calibration_first"]}
    got = joint_job.remote(routed["stage"], rows)
    result = cal.score(saved["marks"], page_key, routed, got["joint"])
    summary = {"stage": routed["stage"], "script": "scripts/sa1_calibration_v1.py",
               "inputs": {"marks": {"path": marks, "sha256": sha(marks),
                                    "saved_at": saved["saved_at"], "page": saved["page"]},
                          "page_key": {"path": key, "sha256": sha(key)},
                          "routing": {"path": routing, "sha256": sha(routing)},
                          "judges_stored_results_sha256": got["stored_sha256"]},
               "seeds": {"disagreement": SEEDS["sa1"]["disagreement"],
                         "audit": SEEDS["sa1"]["audit"], "page": PAGE_SEED,
                         "answer_order": 20261017},
               **result}
    write_once(out, summary)
    print(json.dumps({t: {k: v for k, v in d.items() if k != "differing_row_ids"}
                      for t, d in result["tasks"].items()}, indent=1))
    print(json.dumps({k: result[k] for k in ("stop_for_next_20", "consequences", "escalation",
                                              "marks")}, indent=1))
