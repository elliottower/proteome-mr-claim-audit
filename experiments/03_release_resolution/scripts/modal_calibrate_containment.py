"""Modal wrapper for the containment calibration (scripts/calibrate_containment.py); built from
scripts/modal_calibrate_keeplist_v2.py. Earlier description of that wrapper: Modal wrapper for the calibration of the keep list, the k = 1 table rule with the header shown
once per table, and a chunk-sampled C2 (scripts/calibrate_keeplist.py, which holds the logic).
Per record, each readable supplement file is measured and stored on the volume as soon as it is
done (/03_release_resolution/calibration_containment/<record>/<n>.json), so a stopped run resumes;
then one job aggregates and computes the cost by line (scripts/estimate_cost_v2.py) and the C2
chunk-sample lines.

Run from experiments/03_release_resolution:

    modal run scripts/modal_calibrate_containment.py::tests
    modal run --detach scripts/modal_calibrate_containment.py::calibrate \\
        --abstract-characters outputs/abstract_characters_2026-10-11.json \\
        --out outputs/cut_containment_calibration_2026-10-13.json

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
         .add_local_file(PAPER1 / "dataset_dictionary.csv",
                         "/02_claims_meta/dataset_dictionary.csv", copy=True))
vol = modal.Volume.from_name(VOLUME)
app = modal.App("release-resolution-containment", image=image)

with image.imports():
    import csv
    import subprocess

    import calibrate_cut as cc
    import calibrate_dedup as cd
    import calibrate_keeplist as ck
    import calibrate_containment as cn
    import calibrate_keeplist_v2 as k2
    import cut_supplements as cs
    import estimate_cost_v2 as ev
    import source_scanner_v2 as scanner


def tools():
    with open("/exp02/dataset_dictionary.csv", newline="") as fh:
        rows = list(csv.DictReader(fh))
    with open("/exp03/reference/accession_releases.csv", newline="") as fh:
        accessions = list(csv.DictReader(fh))
    patterns = json.loads(open("/exp03/reference/c1_scanner_patterns_v2.json").read())
    matcher = cs.TermMatcher(rows, patterns)
    keep = k2.Groups("/exp03/reference/release_language_patterns_v2.json", cc.NameMatcher(rows),
                     patterns)
    return (matcher, cd.TermSets(matcher), patterns, scanner.Mapper(patterns, accessions, rows),
            keep)


@app.function(timeout=1800, cpu=2.0)
def tests_job() -> dict:
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                          "test_calibrate_containment.py", "test_calibrate_keeplist_v2.py", "test_calibrate_keeplist.py", "test_calibrate_dedup.py",
                          "test_calibrate_dedup_v2.py", "test_calibrate_cut.py",
                          "test_cut_supplements.py", "test_estimate_cost_v2.py"],
                         capture_output=True, text=True, cwd="/exp03/tests")
    return {"returncode": run.returncode, "output": run.stdout + run.stderr}


@app.function(volumes={str(MOUNT): vol}, timeout=12 * 3600, cpu=1.0, memory=32768, retries=2,
              max_containers=24)
def measure_record(record_id: str) -> dict:
    out = ROOT / "calibration_containment" / record_id
    vol.reload()
    if (out / "DONE.json").exists():
        return {"record_id": record_id, "state": "stored"}
    result = json.loads((ROOT / "retrieval" / record_id / "result.json").read_text())
    entries = [s for s in result["sources"] if s["route"] == "R2" and s.get("text") is not None]
    matcher, termsets, patterns, mapper, keep = tools()
    out.mkdir(parents=True, exist_ok=True)
    for n, entry in enumerate(entries):
        path = out / f"{n}.json"
        if not path.exists():
            partial = path.with_suffix(".partial")
            partial.write_text(json.dumps(cn.measure_file(entry, matcher, termsets, patterns,
                                                          mapper, keep)))
            partial.rename(path)
            vol.commit()
    (out / "DONE.json").write_text(json.dumps({"files": len(entries)}) + "\n")
    vol.commit()
    return {"record_id": record_id, "state": "measured", "files": len(entries)}


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=32768)
def calibrate_job(record_ids: list[str], abstract_characters: dict, prompt: int) -> dict:
    vol.reload()
    files = {}
    for rec in record_ids:
        folder = ROOT / "calibration_containment" / rec
        done = json.loads((folder / "DONE.json").read_text())
        files[rec] = [json.loads((folder / f"{n}.json").read_text())
                      for n in range(done["files"])]
    results = [json.loads((ROOT / "retrieval" / rec / "result.json").read_text())
               for rec in record_ids]
    agg = cn.aggregate(files)
    out = {"variants": {}}
    for name in cn.VARIANTS:
        level = agg[name]
        estimate = ev.estimate(results, level.pop("cuts"), abstract_characters, prompt)
        lines = {k: v for k, v in estimate["lines"].items()
                 if k not in ("c2_sampled_pass", "c2_failure_path_contingent")}
        c2 = ck.c2_lines({"10000": level["chunks"]}, prompt, ev.usd)["size10000_n400"]
        level["cost"] = {"lines": lines, "c2_chunk_sample_n400": c2,
                         "total_without_c2_usd": estimate["total_without_c2_usd"],
                         "total_with_c2_usd": round(estimate["total_without_c2_usd"]
                                                    + c2["usd"], 2),
                         "coding_requests_per_model": estimate["coding_requests_per_model"]}
        level["c2_hypergeometric"] = cn.c2_bounds(level["chunks"]["chunks"])
        out["variants"][name] = level
    out["file_measurements"] = files
    return out


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-1500:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def calibrate(abstract_characters: str, out: str) -> None:
    target = LOCAL / out
    if target.exists():
        raise FileExistsError(f"{target} exists; it is written once")
    records = sorted(json.loads((PAPER1 / "outputs/release_resolution/"
                                          "availability_2026-10-08.json").read_text())["records"])
    done = list(measure_record.map(records))
    prompt = len((LOCAL / "prompts" / "coding_prompt_v2.md").read_text()) + len(
        (PAPER1 / "outputs/manual_coding/2026-10-03/coders/dictionary_definitions.csv")
        .read_text())
    result = calibrate_job.remote(records, json.loads((LOCAL / abstract_characters).read_text()),
                                  prompt)
    result["measured"] = {s: sum(d["state"] == s for d in done)
                          for s in sorted({d["state"] for d in done})}
    target.write_text(json.dumps(result, indent=1) + "\n")
    for name, level in result["variants"].items():
        print(json.dumps({"variant": name, "containment_holds": level["containment_holds"],
                          "lost_units": level["lost_units"],
                          "characters_read": level["characters_read"],
                          "total_with_c2_usd": level["cost"]["total_with_c2_usd"],
                          "c2": level["c2_hypergeometric"]}))
