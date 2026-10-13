"""Modal wrapper for the amended cut of supplements (scripts/cut_supplements_v2.py, Amendment 1);
built from scripts/modal_cut_supplements.py. No logic of the study is here.

Run from experiments/03_release_resolution:

    modal run scripts/modal_cut_supplements_v2.py::tests
    modal run --detach scripts/modal_cut_supplements_v2.py::cut_all \\
        --abstract-characters outputs/abstract_characters_2026-10-11.json \\
        --out outputs/cut_v2_2026-10-13.json

`cut_record` reads a record's retrieval result on the volume
(/03_release_resolution/retrieval/<record>/result.json) and writes, under
/03_release_resolution/cut_v2/<record>/, one file per readable supplement as soon as it is cut
(files/<n>.json: the kept rows, the removed chunks and the counts) and, when the record is done,
cut.json (counts, chunk hashes and lengths; no text). A file or record already stored is not cut
again, so a stopped run resumes. A file whose containment fails raises and stops that record.
`summary_job` reads every cut.json and writes the counts-only output: containment, characters,
files cut, the frozen removed-chunk population and the cost estimate of
scripts/estimate_cost_v2.py over the amended cut, with the diagnostic's line.

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
         .pip_install("httpx==0.28.1", "pydantic==2.13.5", "pyyaml==6.0.3", "pytest==8.4.2",
                      "jsonschema==4.26.0", "anthropic==1.13.0")
         .env({"PYTHONPATH": "/exp03/scripts:/exp02/scripts"})
         .add_local_dir(LOCAL / "scripts", "/exp03/scripts", copy=True, ignore=IGNORE)
         .add_local_dir(LOCAL / "tests", "/exp03/tests", copy=True, ignore=IGNORE)
         .add_local_dir(LOCAL / "reference", "/exp03/reference", copy=True)
         .add_local_dir(LOCAL / "prompts", "/exp03/prompts", copy=True)
         .add_local_dir(PAPER1 / "scripts", "/exp02/scripts", copy=True, ignore=IGNORE)
         .add_local_file(PAPER1 / "dataset_dictionary.csv", "/exp02/dataset_dictionary.csv",
                         copy=True)
         .add_local_file(PAPER1 / "dataset_dictionary.csv",
                         "/02_claims_meta/dataset_dictionary.csv", copy=True)
         .add_local_file(PAPER1 / "verification" / "dataset_components.csv",
                         "/02_claims_meta/verification/dataset_components.csv", copy=True))
vol = modal.Volume.from_name(VOLUME)
app = modal.App("release-resolution-cut-v2", image=image)

with image.imports():
    import csv
    import subprocess

    import calibrate_containment as cn
    import calibrate_cut as cc
    import calibrate_keeplist as ck
    import calibrate_keeplist_v2 as k2
    import cut_supplements as cs
    import cut_supplements_v2 as cv
    import estimate_cost_v2 as ev

TESTS = ["test_cut_supplements_v2.py", "test_coding_queue.py", "test_coding_packets.py",
         "test_coding_runner.py", "test_calibrate_containment_v3.py",
         "test_calibrate_containment.py", "test_calibrate_keeplist_v2.py",
         "test_calibrate_keeplist.py", "test_calibrate_dedup.py", "test_cut_supplements.py",
         "test_estimate_cost_v2.py", "test_prompt_schemas.py", "test_source_scanner_v2.py"]


def tools():
    with open("/exp02/dataset_dictionary.csv", newline="") as fh:
        rows = list(csv.DictReader(fh))
    patterns = json.loads(open("/exp03/reference/c1_scanner_patterns_v2.json").read())
    matcher = cs.TermMatcher(rows, patterns)
    groups = k2.Groups("/exp03/reference/release_language_patterns_v2.json",
                       cc.NameMatcher(rows), patterns)
    return matcher, groups


@app.function(timeout=1800, cpu=2.0)
def tests_job(files: list[str]) -> dict:
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", *files],
                         capture_output=True, text=True, cwd="/exp03/tests")
    return {"returncode": run.returncode, "output": run.stdout + run.stderr}


@app.function(volumes={str(MOUNT): vol}, timeout=12 * 3600, cpu=1.0, memory=32768, retries=2,
              max_containers=24)
def cut_record(record_id: str) -> dict:
    out = ROOT / "cut_v2" / record_id
    vol.reload()
    if (out / "cut.json").exists():
        return {"record_id": record_id, "state": "stored"}
    result = json.loads((ROOT / "retrieval" / record_id / "result.json").read_text())
    entries = [s for s in result["sources"] if s["route"] == "R2" and s.get("text") is not None]
    matcher, groups = tools()
    (out / "files").mkdir(parents=True, exist_ok=True)
    summary = []
    for n, entry in enumerate(entries):
        path = out / "files" / f"{n}.json"
        if path.exists():
            held = json.loads(path.read_text())
        else:
            held = cv.cut(entry, matcher, groups)
            partial = path.with_suffix(".partial")
            partial.write_text(json.dumps(held))
            partial.rename(path)
            vol.commit()
        summary.append({**{k: v for k, v in held.items() if k not in ("text", "rows", "chunks")},
                        "chunks": [{"sha256": c["sha256"], "characters": c["characters"]}
                                   for c in held["chunks"]]})
    (out / "cut.json").write_text(json.dumps({"record_id": record_id, "files": summary},
                                             indent=1) + "\n")
    vol.commit()
    return {"record_id": record_id, "state": "cut", "files": len(summary),
            "files_cut": sum(f["cut"] for f in summary)}


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=32768)
def summary_job(record_ids: list[str], abstract_characters: dict, prompt: int) -> dict:
    vol.reload()
    results = [json.loads((ROOT / "retrieval" / r / "result.json").read_text())
               for r in record_ids]
    cuts = {r: json.loads((ROOT / "cut_v2" / r / "cut.json").read_text()) for r in record_ids}
    files = [f for c in cuts.values() for f in c["files"]]
    population = [{"record_id": r, "file": n, "file_sha256": f["sha256"], "chunk": k,
                   "sha256": ch["sha256"], "characters": ch["characters"]}
                  for r in sorted(cuts) for n, f in enumerate(cuts[r]["files"])
                  for k, ch in enumerate(f["chunks"])]
    shaped = {r: {"files": [{"cut": f["cut"], "characters_before": f["characters_before"],
                             "characters_after": f["characters_read"]} for f in c["files"]]}
              for r, c in cuts.items()}
    estimate = ev.estimate(results, shaped, abstract_characters, prompt)
    lines = {k: v for k, v in estimate["lines"].items()
             if k not in ("c2_sampled_pass", "c2_failure_path_contingent")}
    mean = (sum(p["characters"] for p in population) / len(population)) if population else 0
    diagnostic = ck.c2_lines({"10000": {"chunks": len(population), "mean_characters": mean}},
                             prompt, ev.usd)["size10000_n400"]
    total = round(estimate["total_without_c2_usd"] + diagnostic["usd"], 2)
    return {
        "records": len(record_ids),
        "supplement_files": len(files),
        "supplement_files_cut": sum(f["cut"] for f in files),
        "records_with_a_cut_file": sum(any(f["cut"] for f in c["files"]) for c in cuts.values()),
        "containment": {"registered_units": sum(f["units_registered"] for f in files),
                        "amended_units": sum(f["units_amended"] for f in files),
                        "lost_units": sum(f["lost_units"] for f in files),
                        "papers_losing_units": sorted(r for r, c in cuts.items()
                                                      if any(f["lost_units"] for f in c["files"]))},
        "supplement_characters_before_cut": sum(f["characters_before"] for f in files),
        "supplement_characters_read": sum(f["characters_read"] for f in files),
        "removed_chunk_population": {
            "chunks": len(population), "characters": sum(p["characters"] for p in population),
            "papers": len({p["record_id"] for p in population}),
            "chunk_characters_at_most": cv.CHUNK,
            "bound_400": cn.c2_bounds(len(population)),
            "chunks_in_paper_and_file_order": population},
        "cost_estimate": {"lines": lines, "diagnostic_400_chunks": diagnostic,
                          "total_without_diagnostic_usd": estimate["total_without_c2_usd"],
                          "total_usd": total, "ceiling_usd": 350.0,
                          "coding_requests_per_model": estimate["coding_requests_per_model"],
                          "full_text_characters": estimate["full_text_characters"],
                          "assumptions": estimate["assumptions"]},
        "per_record": [{k: v for k, v in r.items()} for r in estimate["per_record"]]}


@app.local_entrypoint()
def tests(only: str = "") -> None:
    result = tests_job.remote(only.split(",") if only else TESTS)
    print(result["output"][-2500:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def cut_all(abstract_characters: str, out: str) -> None:
    target = LOCAL / out
    if target.exists():
        raise FileExistsError(f"{target} exists; it is written once")
    records = sorted(json.loads((PAPER1 / "outputs/release_resolution/"
                                          "availability_2026-10-08.json").read_text())["records"])
    done = list(cut_record.map(records))
    prompt = len((LOCAL / "prompts" / "coding_prompt_v2.md").read_text()) + len(
        (PAPER1 / "outputs/manual_coding/2026-10-03/coders/dictionary_definitions.csv")
        .read_text())
    result = summary_job.remote(records, json.loads((LOCAL / abstract_characters).read_text()),
                                prompt)
    result["cut_states"] = {s: sum(d["state"] == s for d in done)
                            for s in sorted({d["state"] for d in done})}
    target.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({"containment": result["containment"],
                      "supplement_files_cut": result["supplement_files_cut"],
                      "supplement_characters_read": result["supplement_characters_read"],
                      "removed_chunks": result["removed_chunk_population"]["chunks"],
                      "total_usd": result["cost_estimate"]["total_usd"]}, indent=1))
