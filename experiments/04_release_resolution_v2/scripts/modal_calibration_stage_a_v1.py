"""Modal wrapper of the stage A calibration (scripts/calibration_stage_a_v1.py), on the image of
scripts/modal_judges_stage_a_v2.py (sealed, unchanged; its stores and `final` are reused). It
reads, for the calibration rows only, both judges' stored results, checks that each row was
decided alone (judge_v2.route_pair), and returns the joint choice and the stored files' sha256;
the score is computed locally from the author's marks, whose sha256 is checked against the logged
value first. No model is called.

    PYTHONPATH=../03_release_resolution/scripts modal run scripts/modal_calibration_stage_a_v1.py::tests
    ... modal run scripts/modal_calibration_stage_a_v1.py::calibrate --out <json>
"""

import hashlib
import json

import modal

from modal_coding_v2 import E3, MOUNT, vol
from modal_judges_stage_a_v2 import (LOCAL, PROMPT_V3, context, final, image, schema, system,
                                     task_requests, write_once)
from modal_retrieve_v2 import E4

import calibration_stage_a_v1 as cs

app = modal.App("release-resolution-v2-calibration", image=image)
PAGES = LOCAL.parent.parent / "planning" / "release_resolution_v2_stage_a_author_page_2026-10-20"
MARKS = PAGES / "stage_a_v2_author_marks.json"
KEY = PAGES / "stage_a_author_page_key.json"
MARKS_SHA256 = "7a27328ba6df34a5aa76176ca633def350d866fdaf2fd75814db64ebce375a87"
ROUTING = "outputs/stage_a_routing_2026-10-20.json"
VOID = "outputs/stage_a_fable_void_rows_2026-10-20.json"

with image.imports():
    import subprocess

    import judge_v2 as j2
    import judges_stage_a_v1 as js


@app.function(timeout=900)
def tests_job() -> dict:
    out, code = "", 0
    for cwd, files in ((f"{E4}/tests", ["test_calibration_stage_a_v1.py"]),
                       (f"{E3}/tests", ["test_sa1_calibration_v1.py"])):
        run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", *files],
                             capture_output=True, text=True, cwd=cwd)
        out += run.stdout + run.stderr
        code = code or run.returncode
    return {"returncode": code, "output": out}


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=16384)
def joint_job(v3: str, rows: dict[str, str], void: list[str]) -> dict:
    vol.reload()
    reqs = {rid: (t, req, gates) for t, rid, req, gates in task_requests(context())}
    sysx, sch = system(v3), schema()
    joint, hashes = {}, {}
    for rid, task in rows.items():
        t, req, gates = reqs[rid]
        if t != task:
            raise ValueError(f"{rid} is of another task")
        res = {m: final(m, rid, req, sysx, sch, set(void)) for m in j2.JUDGES}
        for m, r in res.items():
            hashes[f"{m}/{rid}"] = hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()
        if js.route(task, res, gates, "\n".join(f["text"] for f in req["files"])):
            raise ValueError(f"{rid} was not decided alone")
        joint[rid] = res[j2.JUDGES[0]]["decision"]["choice"]
    return {"joint": joint, "stored_results_sha256": hashes}


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-2500:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def calibrate(out: str) -> None:
    raw = MARKS.read_bytes()
    if hashlib.sha256(raw).hexdigest() != MARKS_SHA256:
        raise SystemExit("the marks file is not the logged one")
    saved = json.loads(raw)
    key = json.loads(KEY.read_text())
    routing = json.loads((LOCAL / ROUTING).read_text())
    rows = {rid: t for t in ("disagreement", "audit")
            for rid in routing["tasks"][t]["calibration_first"]}
    got = joint_job.remote((LOCAL / PROMPT_V3).read_text(), rows,
                           json.loads((LOCAL / VOID).read_text())["void_row_ids"])
    result = cs.calibrate(saved["marks"], key, routing, got["joint"])
    summary = {"script": "scripts/calibration_stage_a_v1.py (scorer sa1_calibration_v1.score)",
               "inputs": {"marks_sha256": MARKS_SHA256, "saved_at": saved["saved_at"],
                          "page": saved["page"],
                          "page_key_sha256": hashlib.sha256(KEY.read_bytes()).hexdigest(),
                          ROUTING: hashlib.sha256((LOCAL / ROUTING).read_bytes()).hexdigest(),
                          "judges_stored_results_sha256": got["stored_results_sha256"]},
               "seeds": {"disagreement": 20261038, "audit": 20261039, "page": 20261041,
                         "answer_order": 20261035},
               **result}
    write_once(out, summary)
    print("written", out)
