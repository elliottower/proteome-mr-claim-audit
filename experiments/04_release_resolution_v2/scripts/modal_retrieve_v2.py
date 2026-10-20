"""Modal wrapper for the retrieval of the second release-resolution registration
(scripts/retrieve_sources_v2.py holds the logic). One record is one call; its result and the
files it fetched are stored on the volume and committed as soon as the record ends, and a record
already stored is never fetched again, so a stopped run resumes where it stopped. Texts stay on
the volume (third-party text); what is written locally holds ids, routes, statuses, counts and
sha256.

The image extends the coding image of the first registration
(experiments/03_release_resolution/scripts/modal_adjudication.py, sealed, unchanged), which
mirrors the repository under /repo, with poppler-utils and the converters of the retrieval, and
this folder at /repo/experiments/04_release_resolution_v2. Run from
experiments/04_release_resolution_v2 with the first registration's scripts on the local path:

    PYTHONPATH=../03_release_resolution/scripts modal run scripts/modal_retrieve_v2.py::tests
    PYTHONPATH=../03_release_resolution/scripts modal run --detach \\
        scripts/modal_retrieve_v2.py::retrieve
    PYTHONPATH=../03_release_resolution/scripts modal run scripts/modal_retrieve_v2.py::summary \\
        --out <json>

Volume folder: /04_release_resolution_v2/retrieval/<record id>/ (result.json, files/<sha256>).
"""

import collections
import hashlib
import json
import pathlib

import modal

from modal_adjudication import image as base
from modal_coding_v2 import E2, E3, MOUNT, R, vol

LOCAL = pathlib.Path(__file__).resolve().parents[1]
PAPER1 = LOCAL.parent / "02_claims_meta"
E4 = f"{R}/04_release_resolution_v2"
ROOT4 = MOUNT / "04_release_resolution_v2"
REMOTE = ROOT4 / "retrieval"
IGNORE = ["__pycache__", "*.pyc", ".pytest_cache"]
AVAILABILITY = "outputs/release_resolution/availability_2026-10-08.json"
FAMILIES = "outputs/registry/2026-10-03_amended_primary_coded_a/families.json"
CLAIMS = "outputs/registry/2026-10-03_amended_primary_coded_a/registry_claims.jsonl"
SEARCH_RECORDS = [f"outputs/screening/{d}/search_records.jsonl"
                  for d in ("2026-10-03", "chase_round_1", "chase_round_2", "chase_round_3")]
STORED = "outputs/manual_coding/2026-10-03/fulltext"

image = (base.apt_install("poppler-utils")
         .pip_install("xlrd==2.0.1", "python-docx==1.1.2")
         .env({"PYTHONPATH": f"{E4}/scripts:{E3}/scripts:{E2}/scripts"})
         .add_local_dir(LOCAL / "scripts", f"{E4}/scripts", copy=True, ignore=IGNORE)
         .add_local_dir(LOCAL / "tests", f"{E4}/tests", copy=True, ignore=IGNORE))
app = modal.App("release-resolution-v2-retrieval", image=image)

with image.imports():
    import subprocess

    import httpx

    import retrieval_summary
    import retrieve_sources_v2 as rs2

TESTS = ["test_retrieve_sources_v2.py"]
FIRST_TESTS = ["test_retrieve_sources.py"]


@app.function(timeout=1800)
def tests_job() -> dict:
    out, code = "", 0
    for cwd, files in ((f"{E4}/tests", TESTS), (f"{E3}/tests", FIRST_TESTS)):
        run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", *files],
                             capture_output=True, text=True, cwd=cwd)
        out += run.stdout + run.stderr
        code = code or run.returncode
    version = subprocess.run(["pdftotext", "-v"], capture_output=True, text=True)
    return {"returncode": code, "output": out,
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
        key = hashlib.sha256(data).hexdigest()
        (files / key).write_bytes(data)
        return key

    with httpx.Client(timeout=300, follow_redirects=True) as client:
        result = rs2.retrieve_record(client, rec, preprints, store)
    pdftotext = subprocess.run(["pdftotext", "-v"], capture_output=True, text=True)
    result["pdftotext"] = (pdftotext.stdout + pdftotext.stderr).strip()
    partial = out / "result.json.partial"
    partial.write_text(json.dumps(result) + "\n")
    partial.rename(out / "result.json")
    vol.commit()
    return {"record_id": rec["record_id"], "status": result["status"]}


@app.function(timeout=600)
def units_job(claim_lines: list[str], scope: list[str], search_lines: list[str],
              families: dict) -> list[dict]:
    search = {}
    for line in search_lines:
        if line.strip():
            r = json.loads(line)
            search[r["record_id"]] = r
    claims = [json.loads(line)["claim_record_id"] for line in claim_lines if line.strip()]
    return rs2.outside_scope(claims, scope, search, families)


@app.function(volumes={str(MOUNT): vol}, timeout=1800, memory=8192)
def summary_job(records: list[str], stored_text_sha256: dict[str, str]) -> dict:
    vol.reload()
    missing = [r for r in records if not (REMOTE / r / "result.json").exists()]
    if missing:
        raise FileNotFoundError(f"{len(missing)} records have no stored result: {missing[:5]}")
    results = [json.loads((REMOTE / r / "result.json").read_text()) for r in records]
    by_id = {r["record_id"]: r for r in results}
    compared = collections.Counter()
    for rid, digest in stored_text_sha256.items():
        fresh = [s for s in by_id[rid]["sources"] if s["route"] == "R1"
                 and s["version"] == by_id[rid]["kind"] and s.get("text")]
        if not fresh:
            compared["no_fresh_r1_text"] += 1
        elif any(s["text_sha256"] == digest for s in fresh):
            compared["fresh_r1_text_equals_stored_text"] += 1
        else:
            compared["fresh_r1_text_differs_from_stored_text"] += 1
    return {"summary": retrieval_summary.summary(results),
            "stored_paper1_full_texts": {"records": len(stored_text_sha256),
                                         **dict(sorted(compared.items()))},
            "records": [rs2.listing(r) for r in results],
            "result_json_sha256": {r: hashlib.sha256((REMOTE / r / "result.json").read_bytes())
                                   .hexdigest() for r in records}}


def read_inputs():
    claim_lines = (PAPER1 / CLAIMS).read_text().splitlines()
    scope = json.loads((PAPER1 / AVAILABILITY).read_text())["records"]
    search_lines = [line for p in SEARCH_RECORDS for line in (PAPER1 / p).read_text().splitlines()]
    return claim_lines, scope, search_lines, json.loads((PAPER1 / FAMILIES).read_text())


def file_sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-2500:])
    print(result["pdftotext"])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.function(timeout=24 * 3600)
def retrieve_job(units: list[dict]) -> dict:
    done = list(record_job.starmap([(u["record"], u["family_preprints"]) for u in units]))
    return {"records": len(done),
            "by_status": dict(sorted(collections.Counter(d["status"] for d in done).items()))}


@app.local_entrypoint()
def retrieve() -> None:
    units = units_job.remote(*read_inputs())
    print(json.dumps(retrieve_job.remote(units), indent=1))


@app.local_entrypoint()
def summary(out: str) -> None:
    target = LOCAL / out
    if target.exists():
        raise FileExistsError(f"{target} exists; it is written once")
    inputs = read_inputs()
    units = units_job.remote(*inputs)
    records = [u["record"]["record_id"] for u in units]
    status = {}
    for line in (PAPER1 / STORED / "fetch_status.jsonl").read_text().splitlines():
        if line.strip():
            s = json.loads(line)
            status[str(s["pmid"])] = s["record_id"]
    stored = {}
    for path in sorted((PAPER1 / STORED).glob("pmid*.jsonl")):
        rid = status[path.stem[4:]]
        if rid in records:
            body = json.loads(path.read_text().splitlines()[0])["body"]
            stored[rid] = hashlib.sha256(body.encode()).hexdigest()
    result = summary_job.remote(records, stored)
    result = {"rule": "PREREG.md, §Study design, item 1, Retrieval: routes R1 and R3 under the "
                      "first registration's retrieval rules, R2 not requested",
              "records_outside_scope": len(records), **result,
              "inputs_sha256": {f"../02_claims_meta/{p}": file_sha256(PAPER1 / p)
                                for p in (CLAIMS, AVAILABILITY, FAMILIES, *SEARCH_RECORDS)}}
    target.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: result[k] for k in ("records_outside_scope", "summary",
                                             "stored_paper1_full_texts")}, indent=1))
