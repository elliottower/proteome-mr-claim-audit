"""Modal wrapper for the SA1 calibration diagnostic (scripts/sa1_calibration_diagnostic_v1.py).
The local entrypoint parses the coders' two answers of each disagreement calibration row from the
page the author marked and sends them, with his choices, to the volume; there the stored judge
request's Answer 1 and Answer 2 and the judges' joint choice are read (scripts/modal_judge.py and
scripts/modal_judge_v3.py, sealed, unchanged), and only counts come back. The judges' reasons and
quotations are never read.

    modal run scripts/modal_sa1_calibration_diagnostic_v1.py::tests
    modal run scripts/modal_sa1_calibration_diagnostic_v1.py::diagnose --page <page html> \\
        --marks <marks json> --calibration outputs/sa1_calibration_2026-10-14.json \\
        --routing outputs/sa1_two_judges_routing_2026-10-14.json --out <outputs json>
"""

import hashlib
import json

import modal

from modal_coding_v2 import E3, LOCAL, MOUNT, vol
from modal_judge import context, image, requests_of, system, write_once
from modal_judge_v3 import store_of

import sa1_calibration_diagnostic_v1 as dg

app = modal.App("release-resolution-sa1-calibration-diagnostic-v1", image=image)

with image.imports():
    import subprocess

    import judge_v2 as j2


@app.function(timeout=900)
def tests_job() -> dict:
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                          "test_sa1_calibration_diagnostic_v1.py"], capture_output=True, text=True,
                         cwd=f"{E3}/tests")
    return {"returncode": run.returncode, "output": run.stdout + run.stderr}


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=8192)
def diagnose_job(stage: str, page: dict[str, list], choices: dict[str, str], differing: list[str]) -> dict:
    vol.reload()
    reqs = {rid: req for task, rid, req, _ in requests_of(context(stage)) if task == "disagreement"}
    schema = json.loads(open(f"{E3}/prompts/judge_schema.json").read())
    sysx = system()
    labels, directions = {}, {}
    for rid, shown in page.items():
        request = [dg.request_view(a["answer"]) for a in reqs[rid]["answers"]]
        lab = dg.label_check(shown, request)
        labels[lab] = labels.get(lab, 0) + 1
        if rid in differing:
            got = [json.loads((store_of(stage, m) / f"{rid}.{j2.request_key(m, sysx, schema, reqs[rid])}.json")
                              .read_text())["decision"]["choice"] for m in j2.JUDGES]
            if got[0] != got[1]:
                raise ValueError("a calibration row has no joint choice")
            d = dg.direction(choices[rid], got[0], shown, request)
            directions[d] = directions.get(d, 0) + 1
    return {"label_check": labels, "direction": directions}


def sha(path) -> str:
    return hashlib.sha256((LOCAL / path).read_bytes()).hexdigest()


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-2500:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def diagnose(page: str, marks: str, calibration: str, routing: str, out: str) -> None:
    routed = json.loads((LOCAL / routing).read_text())
    rows = routed["tasks"]["disagreement"]["calibration_first"]
    cal = json.loads((LOCAL / calibration).read_text())
    differing = cal["tasks"]["disagreement"]["differing_row_ids"]
    shown = dg.page_answers((LOCAL / page).read_text(), set(rows))
    if sorted(shown) != sorted(rows):
        raise ValueError("the page does not hold every disagreement calibration row")
    choices = {m["row_id"]: m["choice"] for m in json.loads((LOCAL / marks).read_text())["marks"]}
    got = diagnose_job.remote(routed["stage"], shown, {r: choices[r] for r in rows}, differing)
    summary = {"stage": routed["stage"], "script": "scripts/sa1_calibration_diagnostic_v1.py",
               "diagnostic_only": "changes no verdict of outputs/sa1_calibration_2026-10-14.json",
               "inputs": {p: sha(p) for p in (page, marks, calibration, routing)},
               "disagreement_calibration_rows": len(rows), "differing_rows": len(differing),
               "label_check": {k: got["label_check"].get(k, 0) for k in ("in_order", "swapped", "neither")},
               "direction": {k: got["direction"].get(k, 0) for k in ("a", "b", "c", "d", "other")},
               "direction_classes": {
                   "a": "author's answer identifies no release, the judges' identifies one or more",
                   "b": "author's answer identifies one or more releases, the judges' none",
                   "c": "both identify releases, different ones",
                   "d": "both identify none, differing in attribution or reasons only",
                   "other": "a neither choice or a missing answer"}}
    write_once(out, summary)
    print(json.dumps({k: summary[k] for k in ("label_check", "direction")}, indent=1))
