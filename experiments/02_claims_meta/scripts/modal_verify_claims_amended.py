"""Modal wrapper that runs scripts/verify_claims_whitespace.py, the claim verifier of the run,
unchanged, on the inputs of Amendment 2 (PREREG.md): an extraction file together with the span
results of the amended span step, given as a folder. The image, the files sent, the working
folder and the command are those of scripts/modal_verify_claims_whitespace.py; what differs is
where the span results come from and where the verifier's results go.

Run from experiments/02_claims_meta:

    modal run --detach scripts/modal_verify_claims_amended.py::verify_claims \
        --label <label> --extraction <extraction file> --spans-folder <folder with spans.jsonl>

The verifier reads `outputs/verification/<extraction file stem>/spans.jsonl`; the files of
`--spans-folder` are written there in the container. Results are stored under
`/02_claims_meta/amendment02/verification/<label>/<stem>/` on the volume and saved locally in
`outputs/verification_amendment02/<label>/<stem>/` with `verification_run.json` (hashes of the
extraction file and of every file sent, the command, the environment, the time). Nothing is
written into the folders of the registered run. It prints paths and sizes, and no summary.

Client modal 1.4.3; image python 3.12 debian_slim with the pins of modal_biology_joins.py.
"""

import datetime
import json
import pathlib

import modal

VOLUME = "proteome-mr-claim-audit-inputs"
MOUNT = pathlib.Path("/vol")
REMOTE = MOUNT / "02_claims_meta"
STORE = REMOTE / "amendment02" / "verification"
EXP = pathlib.Path("/exp")
LOCAL_EXP = pathlib.Path(__file__).resolve().parents[1]
IGNORE = ["__pycache__", "*.pyc", ".pytest_cache"]
CORRECTED_SCRIPT = "scripts/verify_claims_whitespace.py"
RESULTS = ("claim_checks.jsonl", "claim_summary.json")
RUN_RECORD = "verification_run.json"
PINS = ("httpx", "numpy", "openpyxl", "pyarrow", "pydantic", "pypdf", "pytest", "rapidfuzz")

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
app = modal.App("proteome-mr-verify-claims-amended", image=image)

with image.imports():
    import hashlib
    import importlib.metadata
    import platform
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
                               for s in (CORRECTED_SCRIPT,
                                         "scripts/modal_verify_claims_amended.py")},
            "reference_manifest_sha256":
                digest((EXP / "reference" / "MANIFEST.json").read_bytes())["sha256"]}


@app.function(volumes={str(MOUNT): vol}, timeout=24 * 3600, cpu=2.0, memory=8192)
def verify_claims_job(label: str, extraction_name: str, extraction: bytes,
                      folder: dict[str, bytes]) -> dict:
    stem = pathlib.Path(extraction_name).stem
    out = STORE / label / stem
    if (out / "claim_checks.jsonl").exists():
        raise FileExistsError(f"{out}/claim_checks.jsonl exists; results are never overwritten")
    code, stderr, files = run_script(CORRECTED_SCRIPT, extraction_name, extraction, folder)
    if code:
        raise RuntimeError(f"verify_claims_whitespace.py failed:\n{stderr}")
    record = {"written_utc": stamp(), "label": label, "extraction_file": extraction_name,
              "extraction": digest(extraction), "script": CORRECTED_SCRIPT,
              "command": command(CORRECTED_SCRIPT, extraction_name),
              "inputs": digests(folder),
              "outputs": digests({n: files[n] for n in RESULTS}),
              "environment": environment(), "volume_folder": str(out)}
    out.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (out / name).write_bytes(content)
    (out / RUN_RECORD).write_text(json.dumps(record, indent=1) + "\n")
    vol.commit()
    return {"record": record, "files": {name: files[name] for name in RESULTS}}


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
def verify_claims(label: str, extraction: str, spans_folder: str) -> None:
    path = pathlib.Path(extraction)
    folder = pathlib.Path(spans_folder)
    if not (folder / "spans.jsonl").is_file():
        raise FileNotFoundError(f"{folder}/spans.jsonl missing")
    target = f"outputs/verification_amendment02/{label}/{path.stem}"
    if (LOCAL_EXP / target).exists():
        raise FileExistsError(f"{target} exists; results are never overwritten")
    sent = {p.name: p.read_bytes() for p in sorted(folder.iterdir())
            if p.is_file() and p.name not in RESULTS}
    result = verify_claims_job.remote(label, path.name, path.read_bytes(), sent)
    for name, content in result["files"].items():
        save_local(target, name, content)
        print(name, len(content), "bytes")
    save_local(target, RUN_RECORD, json.dumps(result["record"], indent=1) + "\n")
    print(result["record"]["volume_folder"])
