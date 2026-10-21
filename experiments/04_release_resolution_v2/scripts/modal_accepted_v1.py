"""Modal wrapper of the accepted codes and the registered C1 of the second registration's stage A
(scripts/accepted_v1.py), on the image of scripts/modal_judges_stage_a_v2.py (sealed, unchanged;
its stores and `final` are reused). No model is called. The author's marks are read locally after
their sha256 is checked against the logged value; only each routed disagreement row's choice is
sent to the job.

    PYTHONPATH=../03_release_resolution/scripts modal run scripts/modal_accepted_v1.py::tests
    ... modal run scripts/modal_accepted_v1.py::accept --codes <json> --c1 <json>

Volume: coding/accepted/stage_a.json (every row's accepted code, quotations included; never
copied out). Outputs written locally hold row ids, sources, acceptance, release names, attribution
states, reasons, counts and hashes; no quotation.
"""

import collections
import hashlib
import json

import modal

from modal_coding_v2 import E3, MOUNT, vol
from modal_judges_stage_a_v1 import FOLDER
from modal_judges_stage_a_v2 import (JUDGES, LOCAL, PROMPT_V3, context, final, image, schema,
                                     system, task_requests, write_once)
from modal_calibration_stage_a_v1 import KEY, MARKS, MARKS_SHA256, ROUTING, VOID
from modal_retrieve_v2 import E4

app = modal.App("release-resolution-v2-accepted", image=image)
CONTROLS = "outputs/control_set_2026-10-20.json"
CALIBRATION = "outputs/stage_a_calibration_2026-10-21.json"

with image.imports():
    import subprocess

    import accepted_v1 as ac
    import judge_v2 as j2
    import judges_stage_a_v1 as js


@app.function(timeout=900)
def tests_job() -> dict:
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                          "test_accepted_v1.py", "test_settle_v1.py", "test_judges_stage_a_v1.py"],
                         capture_output=True, text=True, cwd=f"{E4}/tests")
    return {"returncode": run.returncode, "output": run.stdout + run.stderr}


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=16384)
def accept_job(v3: str, author_choice: dict[str, str], routed: list[str], void: list[str],
               controls: dict[str, str], kinds: dict[str, str]) -> dict:
    vol.reload()
    target = FOLDER / "accepted" / "stage_a.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; it is written once")
    c = context()
    gates_raw = {m: json.loads((FOLDER / "gate" / "stage_a" / m / "rows.json").read_text())
                 for m in js.MODELS}
    bases = {m: gates_raw[m]["bases"] for m in js.MODELS}
    settled = json.loads((FOLDER / "settled" / "stage_a.json").read_text())
    reqs = {rid: (t, req, gates) for t, rid, req, gates in task_requests(context())}
    tasks = json.loads((JUDGES / "tasks.json").read_text())
    sysx, sch = system(v3), schema()
    judge_choice = {}
    for rid in tasks["disagreement"]:
        if rid in set(routed):
            continue
        res = {m: final(m, rid, reqs[rid][1], sysx, sch, set(void)) for m in j2.JUDGES}
        if js.route("disagreement", res, reqs[rid][2],
                    "\n".join(f["text"] for f in reqs[rid][1]["files"])):
            raise ValueError(f"{rid} was routed, not decided alone")
        judge_choice[rid] = res[j2.JUDGES[0]]["decision"]["choice"]
    missing = [r for r in routed if r not in author_choice]
    if missing:
        raise ValueError(f"routed disagreements without an author mark: {missing}")
    accepted = assemble_codes(c, settled, judge_choice, author_choice)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(accepted))
    vol.commit()
    by = collections.Counter
    rows = {rid: {"source": a["source"], "accepted": a["accepted"],
                  "choice": a.get("choice"),
                  "identified_releases": (a["code"] or {}).get("identified_releases"),
                  "attribution_state": (a["code"] or {}).get("attribution_state"),
                  "unresolved_reasons": (a["code"] or {}).get("unresolved_reasons")}
            for rid, a in accepted.items()}
    study = [r for r in accepted if r not in controls]
    counts = {"rows": len(accepted),
              "by_source": dict(by(a["source"] for a in accepted.values())),
              "accepted_by_source": dict(by(a["source"] for a in accepted.values()
                                            if a["accepted"])),
              "not_accepted_by_source": dict(by(a["source"] for a in accepted.values()
                                                if not a["accepted"])),
              "study_rows": len(study), "control_rows": len(controls),
              "study_rows_accepted": sum(accepted[r]["accepted"] for r in study),
              "study_rows_accepted_with_a_release": sum(
                  1 for r in study if accepted[r]["accepted"]
                  and accepted[r]["code"]["identified_releases"]),
              "judge_lone_disagreement_choices": dict(by(judge_choice.values())),
              "author_disagreement_choices": dict(by(author_choice[r] for r in routed))}
    return {"counts": counts, "rows": rows,
            "c1": ac.c1(accepted, controls, kinds, bases),
            "accepted_json_sha256": hashlib.sha256(target.read_bytes()).hexdigest()}


def assemble_codes(c: dict, settled: dict, judge_choice: dict, author_choice: dict) -> dict:
    return ac.assemble(c["order"], c["answers"], c["gates"], settled["settled"], judge_choice,
                       author_choice)


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-2500:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def accept(codes: str, c1: str) -> None:
    raw = MARKS.read_bytes()
    if hashlib.sha256(raw).hexdigest() != MARKS_SHA256:
        raise SystemExit("the marks file is not the logged one")
    marks = {m["row_id"]: m["choice"] for m in json.loads(raw)["marks"]}
    key = json.loads(KEY.read_text())
    routing = json.loads((LOCAL / ROUTING).read_text())
    calibration = json.loads((LOCAL / CALIBRATION).read_text())
    if (calibration["tasks"]["disagreement"]["verdict"] != "pass"
            or calibration["tasks"]["audit"]["verdict"] != "pass"
            or calibration["escalation"]["triggered"]):
        raise SystemExit("calibration did not pass cleanly; the registered consequences apply first")
    routed = sorted(routing["tasks"]["disagreement"]["routed_reasons"])
    author_choice = {r: marks[r] for r in routed}
    drawn = json.loads((LOCAL / CONTROLS).read_text())["control_rows"]
    controls = {r["row_id"]: r["expected_row"] for r in drawn}
    kinds = {r["row_id"]: r["identifier_kind"] for r in drawn}
    got = accept_job.remote((LOCAL / PROMPT_V3).read_text(), author_choice, routed,
                            json.loads((LOCAL / VOID).read_text())["void_row_ids"], controls,
                            kinds)
    inputs = {"marks_sha256": MARKS_SHA256,
              "page_key_sha256": hashlib.sha256(KEY.read_bytes()).hexdigest(),
              **{p: hashlib.sha256((LOCAL / p).read_bytes()).hexdigest()
                 for p in (ROUTING, CALIBRATION, CONTROLS, VOID)},
              "volume:04_release_resolution_v2/coding/accepted/stage_a.json":
                  got["accepted_json_sha256"]}
    write_once(codes, {"script": "scripts/accepted_v1.py", "inputs": inputs,
                       "counts": got["counts"], "rows": got["rows"]})
    write_once(c1, {"script": "scripts/accepted_v1.py",
                    "rule": "first registration PREREG.md §Inference criteria, C1, on accepted "
                            "codes; second registration PREREG.md item 5",
                    "inputs": inputs, **got["c1"]})
    print("written", codes, c1)
