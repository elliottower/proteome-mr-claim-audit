"""Modal wrapper for scripts/verify_claims_whitespace.py, the corrected copy of the registered
claim verifier (PREREG.md log, 2026-10-07). `verify_claims_job` runs the copy as
`modal_biology_joins.py::verify_claims_job` runs scripts/verify_claims.py: the same image, the
same files sent, the same working folder and the same command but for the script's name.

Run from experiments/02_claims_meta:

    modal run --detach scripts/modal_verify_claims_whitespace.py::synthetic
    modal run --detach scripts/modal_verify_claims_whitespace.py::verify_claims \
        --extraction outputs/parsed/sol_extraction_<label>_<rev>.jsonl

`verify_claims` stores the verification folder it is sent and the copy's two results under
`/02_claims_meta/stage4_whitespace/<extraction file stem>/` and commits. The folder
`/02_claims_meta/stage4/<stem>/`, where the registered script's results lie, is read and never
written. Where the registered script completed for the same extraction file, the job compares
the two scripts' `claim_checks.jsonl` and `claim_summary.json` byte for byte, writes
`verifier_comparison.json` (hashes of the inputs of both runs and of the outputs of both, byte
equality per file, the command, the environment, the time) and copies the registered script's
two results into `registered_verifier_5f29a695/` beside the copy's, so the volume folder and the
local folder hold the same files. The local entrypoint refuses to start unless the registered
results were first moved into `outputs/verification/<stem>/registered_verifier_5f29a695/`, checks
that they have the bytes of the volume's, saves the copy's results and the comparison, and exits
non-zero if any byte differs. It prints paths, sizes and the equality results, and no summary.

`synthetic` reads no study record and writes nothing on the volume: on claim records written
below it checks that the registered script raises on a thin space in an exponent, that the copy
completes on the same file, that both scripts write the same bytes for a file without such a
space, and that the comparison reports a differing byte. Its result is saved under
outputs/tests/.

Client modal 1.4.3; image python 3.12 debian_slim with the pins of modal_biology_joins.py.
"""

import datetime
import json
import pathlib

import modal

VOLUME = "proteome-mr-claim-audit-inputs"
MOUNT = pathlib.Path("/vol")
REMOTE = MOUNT / "02_claims_meta"
REGISTERED = REMOTE / "stage4"
CORRECTED = REMOTE / "stage4_whitespace"
EXP = pathlib.Path("/exp")
LOCAL_EXP = pathlib.Path(__file__).resolve().parents[1]
IGNORE = ["__pycache__", "*.pyc", ".pytest_cache"]
REGISTERED_SCRIPT = "scripts/verify_claims.py"
CORRECTED_SCRIPT = "scripts/verify_claims_whitespace.py"
RESULTS = ("claim_checks.jsonl", "claim_summary.json")
ARCHIVE = "registered_verifier_5f29a695"
COMPARISON = "verifier_comparison.json"
PINS = ("httpx", "numpy", "openpyxl", "pyarrow", "pydantic", "pypdf", "pytest", "rapidfuzz")
THIN_SPACE = "\u2009"

image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("httpx==0.28.1", "numpy==2.5.3", "openpyxl==3.1.5", "pyarrow==21.0.0",
                      "pydantic==2.13.5", "pypdf==5.9.0", "pytest==8.4.2", "rapidfuzz==3.14.6")
         .env({"PYTHONPATH": str(EXP / "scripts")})
         .add_local_dir(LOCAL_EXP / "scripts", str(EXP / "scripts"), copy=True, ignore=IGNORE)
         .add_local_dir(LOCAL_EXP / "tests", str(EXP / "tests"), copy=True, ignore=IGNORE)
         .add_local_dir(LOCAL_EXP / "verification", str(EXP / "verification"), copy=True)
         .add_local_file(LOCAL_EXP / "dataset_dictionary.csv",
                         str(EXP / "dataset_dictionary.csv"), copy=True)
         .add_local_file(LOCAL_EXP / "reference" / "MANIFEST.json",
                         str(EXP / "reference" / "MANIFEST.json"), copy=True)
         .run_commands(f"ln -s {REMOTE / 'inputs'} {EXP / 'inputs'}",
                       f"ln -s {REMOTE / 'derived'} {EXP / 'derived'}"))
vol = modal.Volume.from_name(VOLUME)
app = modal.App("proteome-mr-verify-claims-whitespace", image=image)

with image.imports():
    import hashlib
    import importlib.metadata
    import platform
    import shutil
    import subprocess


def stamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")


def digest(content: bytes) -> dict:
    return {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}


def digests(files: dict[str, bytes]) -> dict[str, dict]:
    return {name: digest(content) for name, content in sorted(files.items())}


def command(script: str, extraction_name: str) -> list[str]:
    return ["python", script, "--extraction", f"outputs/parsed/{extraction_name}"]


def run_script(script: str, extraction_name: str, extraction: bytes,
               folder: dict[str, bytes]) -> tuple[int, str, dict[str, bytes]]:
    """The steps of modal_biology_joins.py::verify_claims_job for one script: the folder sent
    and the extraction file written under /exp/outputs, the script run from /exp. Returns the
    return code, the end of stderr and every file of the working folder."""
    stem = pathlib.Path(extraction_name).stem
    work = EXP / "outputs" / "verification" / stem
    work.mkdir(parents=True, exist_ok=True)
    for name, content in folder.items():
        (work / name).write_bytes(content)
    parsed = EXP / "outputs" / "parsed" / extraction_name
    parsed.parent.mkdir(parents=True, exist_ok=True)
    parsed.write_bytes(extraction)
    run = subprocess.run(command(script, extraction_name), cwd=EXP, capture_output=True,
                         text=True)
    files = {p.name: p.read_bytes() for p in sorted(work.iterdir()) if p.is_file()}
    return run.returncode, run.stderr[-4000:], files


def environment() -> dict:
    return {"python": platform.python_version(), "platform": platform.platform(),
            "image": "modal debian_slim, python 3.12",
            "packages": {name: importlib.metadata.version(name) for name in PINS}
                        | {"modal": modal.__version__},
            "scripts_sha256": {s: digest((EXP / s).read_bytes())["sha256"]
                               for s in (REGISTERED_SCRIPT, CORRECTED_SCRIPT)},
            "reference_manifest_sha256":
                digest((EXP / "reference" / "MANIFEST.json").read_bytes())["sha256"]}


def compare(extraction_name: str, extraction: bytes, registered_inputs: dict[str, bytes],
            corrected_inputs: dict[str, bytes], registered: dict[str, bytes],
            corrected: dict[str, bytes]) -> dict:
    """The comparison record of the two scripts' results for one extraction file."""
    equal = {name: registered[name] == corrected[name] for name in RESULTS}
    return {
        "written_utc": stamp(), "extraction_file": extraction_name,
        "extraction": digest(extraction),
        "registered": {"script": REGISTERED_SCRIPT, "inputs": digests(registered_inputs),
                       "outputs": digests({n: registered[n] for n in RESULTS})},
        "corrected": {"script": CORRECTED_SCRIPT,
                      "command": command(CORRECTED_SCRIPT, extraction_name),
                      "inputs": digests(corrected_inputs),
                      "outputs": digests({n: corrected[n] for n in RESULTS})},
        "inputs_identical": registered_inputs == corrected_inputs,
        "byte_identical": equal, "all_identical": all(equal.values())}


@app.function(volumes={str(MOUNT): vol}, timeout=24 * 3600, cpu=2.0, memory=8192)
def verify_claims_job(extraction_name: str, extraction: bytes, folder: dict[str, bytes]) -> dict:
    stem = pathlib.Path(extraction_name).stem
    out = CORRECTED / stem
    if (out / "claim_checks.jsonl").exists():
        raise FileExistsError(f"{out}/claim_checks.jsonl exists; results are never overwritten")
    code, stderr, files = run_script(CORRECTED_SCRIPT, extraction_name, extraction, folder)
    if code:
        raise RuntimeError(f"verify_claims_whitespace.py failed:\n{stderr}")
    out.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (out / name).write_bytes(content)
    vol.commit()
    result = {"volume_path": str(out), "files": {name: files[name] for name in RESULTS},
              "comparison": None, "registered_files": {}}
    held = REGISTERED / stem
    if (held / "claim_checks.jsonl").exists():
        before = {p.name: p.read_bytes() for p in sorted(held.iterdir()) if p.is_file()}
        record = compare(extraction_name, extraction,
                         {n: c for n, c in before.items() if n not in RESULTS}, folder,
                         before, files)
        record["environment"] = environment()
        record["registered"]["volume_folder"] = str(held)
        record["corrected"]["volume_folder"] = str(out)
        text = json.dumps(record, indent=1) + "\n"
        (out / ARCHIVE).mkdir()
        for name in RESULTS:
            (out / ARCHIVE / name).write_bytes(before[name])
        (out / COMPARISON).write_text(text)
        vol.commit()
        result["comparison"] = text
        result["registered_files"] = {name: before[name] for name in RESULTS}
    return result


def synthetic_rows(space: str) -> tuple[bytes, dict[str, bytes]]:
    """An extraction file of two claim records and its spans file. `space` is the character
    between the minus sign and the digit of the first record's P-value exponent."""
    spans = [f"Higher protein X was associated with coronary artery disease, OR 1.15 "
             f"(1.08-1.22; P = 2.0 × 10−{space}6).",
             "Genetically predicted protein Y lowered risk of asthma (OR 0.86 [95% CI "
             "0.79-0.94], p=0.001)."]
    claims = [{"protein_as_written": protein, "outcome_as_written": outcome,
               "direction": direction, "evidence_type": "mr_estimate", "evidence_span": span,
               "claim_scope": "overall", "analysis_context_as_written": "not_stated",
               "subgroup_as_written": "not_stated", "relation_ambiguous": False,
               "dataset_attribution": "whole_study", "pqtl_datasets": ["not_stated"],
               "outcome_datasets": ["not_stated"]}
              for protein, outcome, direction, span in (
                  ("protein X", "coronary artery disease", "raises", spans[0]),
                  ("protein Y", "asthma", "lowers", spans[1]))]
    row = {"pmid": "synthetic1", "status": "ok", "output": {"claims": claims}}
    span_rows = [{"pmid": "synthetic1", "claim_index": i, "passes": True} for i in range(2)]
    return ((json.dumps(row) + "\n").encode(),
            {"spans.jsonl": "".join(json.dumps(r) + "\n" for r in span_rows).encode()})


@app.function(volumes={str(MOUNT): vol}, timeout=3600, cpu=2.0, memory=8192)
def synthetic_job() -> dict:
    """Both scripts on synthetic claim records, in the container's own /exp/outputs. Nothing is
    written on the volume."""
    s = stamp()
    checks: dict = {"stamp": s, "environment": environment()}

    def fresh(name: str) -> None:
        shutil.rmtree(EXP / "outputs" / "verification" / pathlib.Path(name).stem,
                      ignore_errors=True)

    thin = f"synthetic_thin_space_{s}.jsonl"
    extraction, folder = synthetic_rows(THIN_SPACE)
    code, stderr, files = run_script(REGISTERED_SCRIPT, thin, extraction, folder)
    checks["registered_raises_on_thin_space"] = (
        code != 0 and "ValueError: invalid literal for int()" in stderr
        and "claim_checks.jsonl" not in files)
    fresh(thin)
    code, stderr, files = run_script(CORRECTED_SCRIPT, thin, extraction, folder)
    records = [json.loads(line) for line in files.get("claim_checks.jsonl", b"").splitlines()]
    checks["corrected_completes_on_thin_space"] = code == 0 and len(records) == 2
    checks["corrected_reads_the_estimate_on_thin_space"] = (
        [r["direction_method"] for r in records] == ["estimate", "estimate"]
        and [r["parsed_direction"] for r in records] == ["raises", "lowers"])

    plain = f"synthetic_ordinary_space_{s}.jsonl"
    extraction, folder = synthetic_rows(" ")
    code_r, _, registered = run_script(REGISTERED_SCRIPT, plain, extraction, folder)
    fresh(plain)
    code_c, _, corrected = run_script(CORRECTED_SCRIPT, plain, extraction, folder)
    checks["both_complete_on_ordinary_space"] = code_r == 0 and code_c == 0
    same = compare(plain, extraction, folder, folder, registered, corrected)
    checks["comparison_reports_identical_bytes"] = (
        same["all_identical"] and same["inputs_identical"]
        and same["registered"]["outputs"] == same["corrected"]["outputs"]
        and same["registered"]["outputs"]["claim_checks.jsonl"]["bytes"] > 0)
    changed = dict(corrected, **{"claim_checks.jsonl": corrected["claim_checks.jsonl"] + b" "})
    differs = compare(plain, extraction, folder, folder, registered, changed)
    checks["comparison_reports_a_differing_byte"] = (
        differs["byte_identical"] == {"claim_checks.jsonl": False, "claim_summary.json": True}
        and not differs["all_identical"])
    checks["same_command_but_for_the_script"] = (
        command(REGISTERED_SCRIPT, plain)[2:] == command(CORRECTED_SCRIPT, plain)[2:])
    checks["passed"] = all(v for k, v in checks.items() if isinstance(v, bool))
    return checks


def save_local(folder: str, name: str, content: str | bytes) -> pathlib.Path:
    path = LOCAL_EXP / folder / name
    if path.exists():
        raise FileExistsError(f"{path} exists; archive it before rerunning")
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content)
    return path


@app.local_entrypoint()
def synthetic() -> None:
    result = synthetic_job.remote()
    path = save_local("outputs/tests", f"verify_claims_whitespace_modal_{result['stamp']}.json",
                      json.dumps(result, indent=1) + "\n")
    print(path)
    print(json.dumps({k: v for k, v in result.items() if isinstance(v, bool)}, indent=1))
    if not result["passed"]:
        raise SystemExit("a synthetic check failed")


@app.local_entrypoint()
def verify_claims(extraction: str) -> None:
    path = pathlib.Path(extraction)
    folder = LOCAL_EXP / "outputs" / "verification" / path.stem
    if not (folder / "spans.jsonl").is_file():
        raise FileNotFoundError(f"{folder}/spans.jsonl missing; run scripts/verify_spans.py first")
    for name in RESULTS:
        if (folder / name).exists():
            raise FileExistsError(f"{folder / name} exists; move the registered script's "
                                  f"results into {folder / ARCHIVE} first")
    sent = {p.name: p.read_bytes() for p in sorted(folder.iterdir()) if p.is_file()}
    result = verify_claims_job.remote(path.name, path.read_bytes(), sent)
    for name, content in result["files"].items():
        save_local(f"outputs/verification/{path.stem}", name, content)
        print(name, len(content), "bytes")
    print(result["volume_path"])
    if result["comparison"] is None:
        print("no registered result on the volume for this file; nothing compared")
        return
    save_local(f"outputs/verification/{path.stem}", COMPARISON, result["comparison"])
    record = json.loads(result["comparison"])
    print(json.dumps({"byte_identical": record["byte_identical"],
                      "inputs_identical": record["inputs_identical"]}))
    for name, content in result["registered_files"].items():
        if (folder / ARCHIVE / name).read_bytes() != content:
            raise SystemExit(f"{folder / ARCHIVE / name} differs from the volume's registered "
                             f"result")
    if not (record["all_identical"] and record["inputs_identical"]):
        raise SystemExit("the corrected copy's results differ from the registered script's: stop")
