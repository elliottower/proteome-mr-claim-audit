"""Modal wrapper for the whole test suite and the three synthetic dry runs. Nothing here holds
logic: it runs pytest over tests/ and scripts/dry_run_synthetic.py,
dry_run_biology_synthetic.py and dry_run_drug_synthetic.py in one container, so no test suite
runs on the laptop.

Run from experiments/02_claims_meta:

    modal run --detach scripts/modal_all_tests.py

Synthetic records, fixtures and committed tables only; the tests that read a pinned file
(HGNC, UniProt) read it on the volume `proteome-mr-claim-audit-inputs`. No claim, pair or
registry record exists or is read. The job writes its results to the volume
(`/02_claims_meta/prefreeze_checks/all_tests_<stamp>/`) and commits before returning; the local
entrypoint then copies them under outputs/tests/ and outputs/dry_run*/<stamp>/. An existing
result file is never overwritten.

The image holds a copy of scripts/, tests/, verification/, search/, prompts/, PREREG.md,
dataset_dictionary.csv and reference/MANIFEST.json under /exp, with /exp/inputs and
/exp/derived linked to the volume. Client modal 1.4.3; image python 3.12 debian_slim with the
pins of pyproject.toml.
"""

import datetime
import json
import pathlib
import subprocess

import modal

VOLUME = "proteome-mr-claim-audit-inputs"
MOUNT = pathlib.Path("/vol")
REMOTE = MOUNT / "02_claims_meta"
CHECKS = REMOTE / "prefreeze_checks"
EXP = pathlib.Path("/exp")
LOCAL_EXP = pathlib.Path(__file__).resolve().parents[1]
IGNORE = ["__pycache__", "*.pyc", ".pytest_cache"]
DRY_RUNS = {"dry_run": ["scripts/dry_run_synthetic.py"],
            "dry_run_biology": ["scripts/dry_run_biology_synthetic.py", "--out"],
            "dry_run_drug": ["scripts/dry_run_drug_synthetic.py", "--out"]}

image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("httpx==0.28.1", "numpy==2.5.3", "openpyxl==3.1.5", "pyarrow==21.0.0",
                      "pydantic==2.13.5", "pypdf==5.9.0", "pytest==8.4.2", "pyyaml==6.0.3",
                      "rapidfuzz==3.14.6")
         .env({"PYTHONPATH": str(EXP / "scripts")})
         .add_local_dir(LOCAL_EXP / "scripts", str(EXP / "scripts"), copy=True, ignore=IGNORE)
         .add_local_dir(LOCAL_EXP / "tests", str(EXP / "tests"), copy=True, ignore=IGNORE)
         .add_local_dir(LOCAL_EXP / "verification", str(EXP / "verification"), copy=True)
         .add_local_dir(LOCAL_EXP / "search", str(EXP / "search"), copy=True, ignore=IGNORE)
         .add_local_dir(LOCAL_EXP / "prompts", str(EXP / "prompts"), copy=True)
         .add_local_file(LOCAL_EXP / "PREREG.md", str(EXP / "PREREG.md"), copy=True)
         .add_local_file(LOCAL_EXP / "dataset_dictionary.csv",
                         str(EXP / "dataset_dictionary.csv"), copy=True)
         .add_local_file(LOCAL_EXP / "reference" / "MANIFEST.json",
                         str(EXP / "reference" / "MANIFEST.json"), copy=True)
         .run_commands(f"ln -s {REMOTE / 'inputs'} {EXP / 'inputs'}",
                       f"ln -s {REMOTE / 'derived'} {EXP / 'derived'}"))
vol = modal.Volume.from_name(VOLUME)
app = modal.App("proteome-mr-all-tests", image=image)


def stamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")


@app.function(volumes={str(MOUNT): vol}, timeout=3600, cpu=4.0, memory=16384)
def all_tests_job() -> dict:
    s = stamp()
    out = CHECKS / f"all_tests_{s}"
    out.mkdir(parents=True)
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rs",
                          f"--junitxml={out / 'pytest.xml'}"],
                         capture_output=True, text=True, cwd=EXP / "tests")
    (out / "pytest.txt").write_text(run.stdout + run.stderr)
    vol.commit()
    result: dict = {"stamp": s, "volume_path": str(out), "pytest_returncode": run.returncode,
                    "pytest_output": run.stdout + run.stderr, "dry_runs": {}}
    for name, command in DRY_RUNS.items():
        folder = pathlib.Path("/tmp") / name
        args = [*command, str(folder)] if command[-1] == "--out" else command
        dry = subprocess.run(["python", *args], capture_output=True, text=True, cwd=EXP)
        source = folder if command[-1] == "--out" else EXP / "outputs" / "dry_run"
        files = {str(p.relative_to(source)): p.read_text()
                 for p in sorted(source.rglob("*")) if p.is_file()} if source.exists() else {}
        result["dry_runs"][name] = {"returncode": dry.returncode,
                                    "output": dry.stdout + dry.stderr, "files": files}
        (out / f"{name}.stdout.txt").write_text(dry.stdout + dry.stderr)
        vol.commit()
    (out / "summary.json").write_text(json.dumps(
        {"stamp": s, "pytest_returncode": run.returncode,
         "dry_run_returncodes": {k: v["returncode"] for k, v in result["dry_runs"].items()}},
        indent=1))
    vol.commit()
    return result


def save_local(folder: str, name: str, text: str) -> pathlib.Path:
    path = LOCAL_EXP / "outputs" / folder / name
    if path.exists():
        raise FileExistsError(f"{path} exists; archive it before rerunning")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


@app.local_entrypoint()
def main() -> None:
    result = all_tests_job.remote()
    s = result["stamp"]
    save_local("tests", f"pytest_all_modal_{s}.txt", result["pytest_output"])
    for name, dry in result["dry_runs"].items():
        for file_name, text in dry["files"].items():
            # dry_run_synthetic.py writes its own <stamp>/ folder; the others write flat files.
            target = file_name if name == "dry_run" else f"{s}/{file_name}"
            save_local(name, target, text)
        save_local(name, f"{s}.stdout.txt" if name == "dry_run" else f"{s}/stdout.txt",
                   dry["output"])
    print(result["pytest_output"][-2500:])
    print(json.dumps({"stamp": s, "pytest_returncode": result["pytest_returncode"],
                      "dry_run_returncodes": {k: v["returncode"]
                                              for k, v in result["dry_runs"].items()},
                      "volume_path": result["volume_path"]}, indent=1))
