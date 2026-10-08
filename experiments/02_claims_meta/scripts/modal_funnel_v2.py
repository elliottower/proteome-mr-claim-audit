"""Modal wrapper for scripts/funnel_v2.py (PREREG.md log, 2026-10-08), so that the funnel does
not run on the author's laptop. The script is run unchanged, from a copy of the experiment
folder's layout: every file it reads is sent at its path relative to the experiment folder and
written there in the container, and the command is the local one.

Run from experiments/02_claims_meta:

    modal run --detach scripts/modal_funnel_v2.py::funnel --run-name <run> \\
        --screening-dirs <dir,dir,...> --decisions <f,f,...> --extraction <f,f,...> \\
        --spans <f,f,...> --checks <f,f,...> --assembly <registry dir>

Of a screening folder only the files the funnel reads are sent (`screening_records.jsonl`,
`prefilter_marks.jsonl`, `prefilter_counts.json`, `chase_counts.json` or `funnel.json`,
`gate_sample_batch_*.jsonl`); of the assembly `families.json`, `families_meta.json` and
`registry_assembly.json`. Nothing is written on the volume: the files sent include stored
third-party text, which stays in the container. The result is saved locally as
`outputs/funnel/<run>/funnel.json` with `funnel_run.json` (the sha256 of every file sent, the
command, the script hashes, the environment). The funnel is one pass of about a minute and a
half with no loop to checkpoint; a stopped job is started again. It prints paths and hashes,
no count.

Client modal 1.4.3; image python 3.12 debian_slim.
"""

import datetime
import json
import pathlib

import modal

EXP = pathlib.Path("/exp")
LOCAL_EXP = pathlib.Path(__file__).resolve().parents[1]
IGNORE = ["__pycache__", "*.pyc", ".pytest_cache"]
SCREENING_FILES = ("screening_records.jsonl", "prefilter_marks.jsonl", "prefilter_counts.json",
                   "chase_counts.json", "funnel.json")
ASSEMBLY_FILES = ("families.json", "families_meta.json", "registry_assembly.json")
SCRIPT = "scripts/funnel_v2.py"

image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("numpy==2.5.3", "pydantic==2.13.5")
         .env({"PYTHONPATH": str(EXP / "scripts"), "PYTHONUTF8": "1"})
         .add_local_dir(LOCAL_EXP / "scripts", str(EXP / "scripts"), copy=True, ignore=IGNORE)
         .add_local_dir(LOCAL_EXP / "search", str(EXP / "search"), copy=True,
                        ignore=["*.jsonl", "*.xml", "raw", "pages"]))
app = modal.App("proteome-mr-funnel-v2", image=image)

with image.imports():
    import hashlib
    import importlib.metadata
    import platform
    import subprocess


def stamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")


def command(run_name: str, groups: dict[str, list[str]]) -> list[str]:
    out = ["python", SCRIPT]
    for folder in groups["screening_dirs"]:
        out += ["--screening-dir", folder]
    for name in ("decisions", "extraction", "spans", "checks"):
        out += [f"--{name}", *groups[name]]
    return [*out, "--assembly", groups["assembly"][0], "--out", f"outputs/funnel/{run_name}"]


@app.function(timeout=3600, cpu=2.0, memory=8192)
def funnel_job(run_name: str, groups: dict[str, list[str]], files: dict[str, bytes]) -> dict:
    for path, content in files.items():
        target = EXP / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    cmd = command(run_name, groups)
    done = subprocess.run(cmd, cwd=EXP, capture_output=True, text=True)
    if done.returncode:
        return {"returncode": done.returncode, "stderr_end": done.stderr[-1500:]}
    result = (EXP / "outputs" / "funnel" / run_name / "funnel.json").read_text()
    record = {
        "run_name": run_name, "written_utc": stamp(), "command": cmd,
        "inputs_sha256": {p: hashlib.sha256(c).hexdigest() for p, c in sorted(files.items())},
        "funnel_sha256": hashlib.sha256(result.encode()).hexdigest(),
        "scripts_sha256": {s: hashlib.sha256((EXP / "scripts" / s).read_bytes()).hexdigest()
                           for s in ("funnel_v2.py", "gate_audit.py", "keyword_prefilter.py",
                                     "abstract_floor.py", "modal_funnel_v2.py")},
        "environment": {"python": platform.python_version(), "modal": modal.__version__,
                        "packages": {n: importlib.metadata.version(n)
                                     for n in ("numpy", "pydantic")}}}
    return {"returncode": 0, "funnel": result, "record": json.dumps(record, indent=1) + "\n"}


def save_local(folder: str, name: str, content: str) -> pathlib.Path:
    path = LOCAL_EXP / folder / name
    if path.exists():
        raise FileExistsError(f"{path} exists; archive it before rerunning")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


@app.local_entrypoint()
def funnel(run_name: str, screening_dirs: str, decisions: str, extraction: str, spans: str,
           checks: str, assembly: str) -> None:
    if (LOCAL_EXP / "outputs" / "funnel" / run_name).exists():
        raise FileExistsError(f"outputs/funnel/{run_name} exists; a funnel is written once")
    groups = {"screening_dirs": screening_dirs.split(","), "decisions": decisions.split(","),
              "extraction": extraction.split(","), "spans": spans.split(","),
              "checks": checks.split(","), "assembly": [assembly]}
    files: dict[str, bytes] = {}
    for folder in groups["screening_dirs"]:
        names = [n for n in SCREENING_FILES if (LOCAL_EXP / folder / n).is_file()]
        names += sorted(p.name for p in (LOCAL_EXP / folder).glob("gate_sample_batch_*.jsonl"))
        for name in names:
            files[f"{folder}/{name}"] = (LOCAL_EXP / folder / name).read_bytes()
    for name in ("decisions", "extraction", "spans", "checks"):
        for path in groups[name]:
            files[path] = (LOCAL_EXP / path).read_bytes()
    for name in ASSEMBLY_FILES:
        files[f"{assembly}/{name}"] = (LOCAL_EXP / assembly / name).read_bytes()
    result = funnel_job.remote(run_name, groups, files)
    if result["returncode"]:
        print(json.dumps({"returncode": result["returncode"],
                          "stderr_end": result["stderr_end"]}, indent=1))
        raise SystemExit("funnel_v2.py stopped: nothing is written")
    path = save_local(f"outputs/funnel/{run_name}", "funnel.json", result["funnel"])
    save_local(f"outputs/funnel/{run_name}", "funnel_run.json", result["record"])
    print(json.dumps({"path": str(path.relative_to(LOCAL_EXP)),
                      "funnel_sha256": json.loads(result["record"])["funnel_sha256"],
                      "files_sent": len(files)}))
