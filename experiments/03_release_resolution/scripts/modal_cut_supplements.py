"""Modal wrapper for the registered cut of supplements (scripts/cut_supplements.py) and the cost
estimate after the cut (scripts/estimate_cost_v2.py). No logic of the study is here.

Run from experiments/03_release_resolution:

    modal run scripts/modal_cut_supplements.py::tests
    modal run --detach scripts/modal_cut_supplements.py::cut_all
    modal run scripts/modal_cut_supplements.py::estimate --abstract-characters <json> --out <json>

`cut_all` reads each record's retrieval result on the volume
(/03_release_resolution/retrieval/<record>/result.json) and writes, under
/03_release_resolution/cut/<record>/, one file per readable supplement as soon as it is cut
(files/<n>.json, the text the models read and its counts) and, when the record is done,
cut.json (counts only). A file or record already stored is not cut again, so a stopped run
resumes. `estimate` reads the results and cut.json files on the volume and writes the estimate
locally. Both print counts only.

Client modal 1.4.3; image python 3.12 debian_slim.
"""

import json
import pathlib

import modal

VOLUME = "proteome-mr-claim-audit-inputs"
MOUNT = pathlib.Path("/vol")
ROOT = MOUNT / "03_release_resolution"
LOCAL = pathlib.Path(__file__).resolve().parents[1]
PAPER1 = LOCAL.parent / "02_claims_meta"
IGNORE = ["__pycache__", "*.pyc", ".pytest_cache"]

image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("httpx==0.28.1", "pydantic==2.13.5", "pyyaml==6.0.3", "pytest==8.4.2")
         .env({"PYTHONPATH": "/exp03/scripts:/exp02/scripts"})
         .add_local_dir(LOCAL / "scripts", "/exp03/scripts", copy=True, ignore=IGNORE)
         .add_local_dir(LOCAL / "tests", "/exp03/tests", copy=True, ignore=IGNORE)
         .add_local_dir(LOCAL / "reference", "/exp03/reference", copy=True)
         .add_local_dir(PAPER1 / "scripts", "/exp02/scripts", copy=True, ignore=IGNORE)
         .add_local_file(PAPER1 / "dataset_dictionary.csv", "/exp02/dataset_dictionary.csv",
                         copy=True)
         # tests/test_cut_supplements.py reads the dictionary beside its experiment folder
         .add_local_file(PAPER1 / "dataset_dictionary.csv", "/02_claims_meta/dataset_dictionary.csv",
                         copy=True))
vol = modal.Volume.from_name(VOLUME)
app = modal.App("release-resolution-cut", image=image)

with image.imports():
    import subprocess

    import cut_supplements as cs
    import estimate_cost_v2 as ev


@app.function(timeout=1800, cpu=2.0)
def tests_job() -> dict:
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                          "test_cut_supplements.py", "test_estimate_cost_v2.py"],
                         capture_output=True, text=True, cwd="/exp03/tests")
    return {"returncode": run.returncode, "output": run.stdout + run.stderr}


@app.function(volumes={str(MOUNT): vol}, timeout=12 * 3600, cpu=1.0, memory=16384, retries=2,
              max_containers=24)
def cut_record(record_id: str) -> dict:
    out = ROOT / "cut" / record_id
    vol.reload()
    if (out / "cut.json").exists():
        return {"record_id": record_id, "state": "stored"}
    result = json.loads((ROOT / "retrieval" / record_id / "result.json").read_text())
    entries = [s for s in result["sources"] if s["route"] == "R2" and s.get("text") is not None]
    matcher = cs.load_matcher("/exp02/dataset_dictionary.csv",
                              "/exp03/reference/c1_scanner_patterns_v2.json")
    (out / "files").mkdir(parents=True, exist_ok=True)
    summary = []
    for n, entry in enumerate(entries):
        path = out / "files" / f"{n}.json"
        if path.exists():
            held = json.loads(path.read_text())
        else:
            done = cs.cut(entry, matcher)
            held = {"name": entry["name"], "sha256": entry["sha256"], "type": entry["type"],
                    "version": entry["version"], **done}
            partial = path.with_suffix(".partial")
            partial.write_text(json.dumps(held))
            partial.rename(path)
            vol.commit()
        summary.append({k: v for k, v in held.items() if k != "text"})
    (out / "cut.json").write_text(json.dumps({"record_id": record_id, "files": summary},
                                             indent=1) + "\n")
    vol.commit()
    return {"record_id": record_id, "state": "cut", "files": len(summary),
            "files_cut": sum(f["cut"] for f in summary)}


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=32768)
def estimate_job(abstract_characters: dict, prompt_characters: int) -> dict:
    vol.reload()
    results = [json.loads(p.read_text())
               for p in sorted((ROOT / "retrieval").glob("*/result.json"))]
    cuts = {p.parent.name: json.loads(p.read_text())
            for p in (ROOT / "cut").glob("*/cut.json")}
    return ev.estimate(results, cuts, abstract_characters, prompt_characters)


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-1500:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def cut_all() -> None:
    availability = json.loads((PAPER1 / "outputs/release_resolution/"
                                        "availability_2026-10-08.json").read_text())
    done = list(cut_record.map(sorted(availability["records"])))
    print(json.dumps({"records": len(done),
                      "by_state": {s: sum(d["state"] == s for d in done)
                                   for s in sorted({d["state"] for d in done})},
                      "files": sum(d.get("files", 0) for d in done),
                      "files_cut": sum(d.get("files_cut", 0) for d in done)}, indent=1))


@app.local_entrypoint()
def estimate(abstract_characters: str, out: str) -> None:
    target = LOCAL / out
    if target.exists():
        raise FileExistsError(f"{target} exists; it is written once")
    prompt = len((LOCAL / "prompts" / "coding_prompt_v2.md").read_text()) + len(
        (PAPER1 / "outputs/manual_coding/2026-10-03/coders/dictionary_definitions.csv")
        .read_text())
    result = estimate_job.remote(json.loads((LOCAL / abstract_characters).read_text()), prompt)
    target.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "per_record"}, indent=1))
