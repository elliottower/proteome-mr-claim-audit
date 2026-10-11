"""Modal wrapper for the retrieval of the release-resolution follow-up (scripts/retrieve_sources.py,
which holds the logic). One record is one call; its result and the files it fetched are stored
on the volume and committed as soon as the record ends, and a record already stored is never
fetched again, so a stopped run resumes where it stopped.

Run from experiments/03_release_resolution:

    modal run scripts/modal_retrieve_sources.py::tests
    modal run --detach scripts/modal_retrieve_sources.py::retrieve
    modal run scripts/modal_retrieve_sources.py::estimate --abstract-characters <json> --out <json>

`retrieve` reads the scope (the 266 records of Paper 1's repeated pairs in
experiments/02_claims_meta/outputs/release_resolution/availability_2026-10-08.json), their
search records and Paper 1's families (amended primary assembly), sends one call per record,
and then copies each record's result and files to the ignored folder outputs/raw/retrieval/
(third-party text). It prints counts only. Volume folder:
/03_release_resolution/retrieval/<record id>/ (result.json, files/<sha256>).

Client modal 1.4.3; image python 3.12 debian_slim with poppler-utils from the image's apt.
"""

import json
import pathlib

import modal

VOLUME = "proteome-mr-claim-audit-inputs"
MOUNT = pathlib.Path("/vol")
REMOTE = MOUNT / "03_release_resolution" / "retrieval"
LOCAL = pathlib.Path(__file__).resolve().parents[1]
PAPER1 = LOCAL.parent / "02_claims_meta"
IGNORE = ["__pycache__", "*.pyc", ".pytest_cache"]
AVAILABILITY = PAPER1 / "outputs/release_resolution/availability_2026-10-08.json"
FAMILIES = PAPER1 / "outputs/registry/2026-10-03_amended_primary_coded_a/families.json"
SEARCH_RECORDS = [PAPER1 / f"outputs/screening/{d}/search_records.jsonl"
                  for d in ("2026-10-03", "chase_round_1", "chase_round_2", "chase_round_3")]

image = (modal.Image.debian_slim(python_version="3.12")
         .apt_install("poppler-utils")
         .pip_install("httpx==0.28.1", "openpyxl==3.1.5", "xlrd==2.0.1", "python-docx==1.1.2",
                      "pydantic==2.13.5", "pytest==8.4.2")
         .env({"PYTHONPATH": "/exp03/scripts:/exp02/scripts"})
         .add_local_dir(LOCAL / "scripts", "/exp03/scripts", copy=True, ignore=IGNORE)
         .add_local_dir(LOCAL / "tests", "/exp03/tests", copy=True, ignore=IGNORE)
         .add_local_dir(PAPER1 / "scripts", "/exp02/scripts", copy=True, ignore=IGNORE))
vol = modal.Volume.from_name(VOLUME)
app = modal.App("release-resolution-retrieval", image=image)

with image.imports():
    import subprocess

    import estimate_cost
    import httpx

    import retrieve_sources as rs


@app.function(timeout=1800)
def tests_job() -> dict:
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                          "test_retrieve_sources.py"], capture_output=True, text=True,
                         cwd="/exp03/tests")
    version = subprocess.run(["pdftotext", "-v"], capture_output=True, text=True)
    return {"returncode": run.returncode, "output": run.stdout + run.stderr,
            "pdftotext": (version.stdout + version.stderr).strip()}


@app.function(volumes={str(MOUNT): vol}, timeout=6 * 3600, cpu=1.0, memory=4096, retries=2,
              max_containers=8)
def record_job(rec: dict, preprints: list[dict]) -> dict:
    out = REMOTE / rec["record_id"]
    vol.reload()
    if (out / "result.json").exists():
        return {"record_id": rec["record_id"], "status": "stored"}
    files = out / "files"
    files.mkdir(parents=True, exist_ok=True)

    def store(data: bytes) -> str:
        key = rs.sha256(data)
        (files / key).write_bytes(data)
        return key

    with httpx.Client(timeout=300, follow_redirects=True) as client:
        result = rs.retrieve_record(client, rec, preprints, store)
    pdftotext = subprocess.run(["pdftotext", "-v"], capture_output=True, text=True)
    result["pdftotext"] = (pdftotext.stdout + pdftotext.stderr).strip()
    partial = out / "result.json.partial"
    partial.write_text(json.dumps(result) + "\n")
    partial.rename(out / "result.json")
    vol.commit()
    return {"record_id": rec["record_id"], "status": result["status"]}


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-1200:])
    print(result["pdftotext"])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.function(timeout=600)
def scope_job(availability: dict, search_lines: list[str], families: dict) -> list[dict]:
    search = {}
    for line in search_lines:
        if line.strip():
            r = json.loads(line)
            search[r["record_id"]] = r
    return rs.scope(availability, search, families)


@app.function(volumes={str(MOUNT): vol}, timeout=1800, memory=8192)
def estimate_job(abstract_characters: dict, prompts: list[str]) -> dict:
    vol.reload()
    results = [json.loads(p.read_text()) for p in sorted(REMOTE.glob("*/result.json"))]
    return estimate_cost.estimate(results, abstract_characters, sum(len(t) for t in prompts))


@app.local_entrypoint()
def retrieve() -> None:
    lines = [line for path in SEARCH_RECORDS for line in path.read_text().splitlines()]
    units = scope_job.remote(json.loads(AVAILABILITY.read_text()), lines,
                             json.loads(FAMILIES.read_text()))
    done = list(record_job.starmap([(u["record"], u["family_preprints"]) for u in units]))
    counts: dict = {}
    for d in done:
        counts[d["status"]] = counts.get(d["status"], 0) + 1
    print(json.dumps({"records": len(done), "by_status": counts}, indent=1))


@app.local_entrypoint()
def estimate(abstract_characters: str, out: str) -> None:
    target = LOCAL / out
    if target.exists():
        raise FileExistsError(f"{target} exists; it is written once")
    prompts = [(LOCAL / "prompts" / "coding_prompt_v2.md").read_text(),
               (PAPER1 / "outputs/manual_coding/2026-10-03/coders/dictionary_definitions.csv"
                ).read_text()]
    result = estimate_job.remote(json.loads((LOCAL / abstract_characters).read_text()), prompts)
    target.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "per_record"}, indent=1))
