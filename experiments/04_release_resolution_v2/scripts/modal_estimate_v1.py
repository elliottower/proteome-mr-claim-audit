"""Modal wrapper of the cost estimate of the stage A recode (scripts/estimate_v1.py holds the
logic), on the image of scripts/modal_retrieve_v2.py. No model is called. It reads the 323 packets
on the volume (/04_release_resolution_v2/packets/stage_a/) and writes counts and US dollars only.

    PYTHONPATH=../03_release_resolution/scripts modal run scripts/modal_estimate_v1.py::tests
    ... modal run scripts/modal_estimate_v1.py::estimate --out <json>
"""

import hashlib
import json

import modal

from modal_coding_v2 import CODING, DEFINITIONS, E2, E3, MOUNT, vol
from modal_retrieve_v2 import E4, LOCAL, ROOT4, image

app = modal.App("release-resolution-v2-estimate", image=image)
PROMPT_V3 = "prompts/coding_prompt_v3.md"
CONTROLS = "outputs/control_set_2026-10-20.json"
FIRST_REGISTRATION_SPEND, NEW_SPEND_CEILING = 86.09, 300.0

with image.imports():
    import subprocess

    import coding_packets as cp
    import coding_runner_v2 as cr2
    import estimate_v1 as est
    import judge as jd


@app.function(timeout=1800, cpu=2.0)
def tests_job() -> dict:
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                          "test_estimate_v1.py"], capture_output=True, text=True,
                         cwd=f"{E4}/tests")
    return {"returncode": run.returncode, "output": run.stdout + run.stderr}


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=16384)
def estimate_job(prompt_v3: str, control_ids: list[str]) -> dict:
    vol.reload()
    folder = ROOT4 / "packets" / "stage_a"
    listing = (folder / "manifest.json").read_bytes()
    manifest = json.loads(listing)
    packets = [json.loads((folder / f"{m['name']}.json").read_text()) for m in manifest]
    definitions = open(f"{E2}/{DEFINITIONS}").read()
    prompt = cp.fixed_prompt(prompt_v3, definitions)
    system = jd.system_text(open(f"{E3}/prompts/judge_prompt.md").read(), prompt_v3, definitions)
    spent = sum(json.loads(line)["usd"] for line in (CODING / "spend.jsonl").read_text()
                .splitlines() if line.strip())
    bounds = {m: round(sum(cr2.bound(m, prompt, p) for p in packets), 2)
              for m in ("claude-sonnet-5-5", "gpt-6.1-sol")}
    return {"packets": len(packets),
            "packets_by_population": {k: sum(m["population"] == k for m in manifest)
                                      for k in ("scope", "outside_scope")},
            "packet_characters": sum(est.packet_chars(p) for p in packets),
            "fixed_prompt_characters": len(prompt),
            "coders": est.coders(packets, len(prompt)),
            "coders_sum_of_reservation_bounds_usd": bounds,
            "judges": est.judges(packets, set(control_ids), len(system)),
            "settling_step_usd": 0.0,
            "ledger_usd_now": round(spent, 4),
            "new_spend_so_far_usd": round(spent - FIRST_REGISTRATION_SPEND, 4),
            "new_spend_ceiling_usd": NEW_SPEND_CEILING,
            "room_under_the_ceiling_usd": round(FIRST_REGISTRATION_SPEND + NEW_SPEND_CEILING
                                                - spent, 4),
            "inputs_sha256": {"volume:04_release_resolution_v2/packets/stage_a/manifest.json":
                              hashlib.sha256(listing).hexdigest()}}


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-2500:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def estimate(out: str) -> None:
    target = LOCAL / out
    if target.exists():
        raise FileExistsError(f"{target} exists; it is written once")
    prompt = (LOCAL / PROMPT_V3).read_text()
    controls = json.loads((LOCAL / CONTROLS).read_text())["drawn_row_ids"]
    result = estimate_job.remote(prompt, controls)
    result["inputs_sha256"] |= {
        f"{x}": hashlib.sha256((LOCAL / x).read_bytes()).hexdigest() for x in (PROMPT_V3, CONTROLS)}
    target.write_text(json.dumps(result, indent=1) + "\n")
    print("written", out)
