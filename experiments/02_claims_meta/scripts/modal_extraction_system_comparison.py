"""Modal wrapper for the extraction-system comparison
(AMENDMENT_01_extraction_system_comparison.md). Nothing here holds logic: `tests` runs the
comparison's unit tests, its synthetic dry run and its mutation check in one container, and
`compare` runs scripts/extraction_system_comparison.py on the registry claim files and the three
usage files it is sent, so neither the bootstraps nor a test suite run on the laptop.

Run from experiments/02_claims_meta:

    modal run --detach scripts/modal_extraction_system_comparison.py::tests
    modal run --detach scripts/modal_extraction_system_comparison.py::compare --run-name <run> \
        --sol outputs/registry/<run>_coded/registry_claims.jsonl \
        --luna-run1 <out>/luna_run1_registry/registry_claims.jsonl \
        --luna-run2 <out>/luna_run2_registry/registry_claims.jsonl \
        --sol-repeat <out>/sol_repeat_registry/registry_claims.jsonl \
        --repeat-sample <...repeat_sample.json, comma-separated> \
        --sol-tables outputs/stage5_biology/<run>/sensitivity_tables.json \
        --usage-sol <out>/usage_sol.json --usage-luna-run1 <out>/usage_luna_run1.json \
        --usage-luna-run2 <out>/usage_luna_run2.json

with <out> = outputs/extraction_system_comparison/<run>. The three usage files are required.

`tests` reads synthetic records, fixtures and committed tables only. `compare` stores its
result on the volume `proteome-mr-claim-audit-inputs` under
/02_claims_meta/extraction_system_comparison/<run>/ and commits before returning; the local
entrypoint then copies it to
outputs/extraction_system_comparison/<run>/extraction_system_comparison.json. An existing result
is never overwritten, on the volume or locally.

Client modal 1.4.3; image python 3.12 debian_slim with the pins of pyproject.toml.
"""

import datetime
import json
import pathlib
import subprocess

import modal

VOLUME = "proteome-mr-claim-audit-inputs"
MOUNT = pathlib.Path("/vol")
REMOTE = MOUNT / "02_claims_meta"
RESULTS = REMOTE / "extraction_system_comparison"
CHECKS = REMOTE / "prefreeze_checks"
EXP = pathlib.Path("/exp")
LOCAL_EXP = pathlib.Path(__file__).resolve().parents[1]
MUTATION_CHECK = LOCAL_EXP.parent.parent / "docs" / "run" / "mutation_check_amendment01.py"
IGNORE = ["__pycache__", "*.pyc", ".pytest_cache"]
TESTS = ["test_extraction_system_comparison.py", "test_run_extraction_luna.py"]

image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("httpx==0.28.1", "numpy==2.5.3", "openpyxl==3.1.5", "pyarrow==21.0.0",
                      "pydantic==2.13.5", "pypdf==5.9.0", "pytest==8.4.2", "pyyaml==6.0.3",
                      "rapidfuzz==3.14.6")
         .env({"PYTHONPATH": str(EXP / "scripts")})
         .add_local_dir(LOCAL_EXP / "scripts", str(EXP / "scripts"), copy=True, ignore=IGNORE)
         .add_local_dir(LOCAL_EXP / "tests", str(EXP / "tests"), copy=True, ignore=IGNORE)
         .add_local_dir(LOCAL_EXP / "verification", str(EXP / "verification"), copy=True)
         .add_local_dir(LOCAL_EXP / "prompts", str(EXP / "prompts"), copy=True)
         .add_local_file(LOCAL_EXP / "dataset_dictionary.csv",
                         str(EXP / "dataset_dictionary.csv"), copy=True)
         .add_local_file(MUTATION_CHECK, str(EXP / MUTATION_CHECK.name), copy=True))
vol = modal.Volume.from_name(VOLUME)
app = modal.App("proteome-mr-extraction-system-comparison", image=image)


def stamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")


def save_local(path: pathlib.Path, text: str) -> pathlib.Path:
    if path.exists():
        raise FileExistsError(f"{path} exists; archive it before rerunning")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


@app.function(volumes={str(MOUNT): vol}, timeout=3600, cpu=4.0, memory=16384)
def tests_job() -> dict:
    s = stamp()
    out = CHECKS / f"amendment01_tests_{s}"
    out.mkdir(parents=True)
    test = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rs",
                           *TESTS], capture_output=True, text=True, cwd=EXP / "tests")
    dry_dir = pathlib.Path("/tmp/dry_run_extraction_system_comparison")
    dry = subprocess.run(["python", "scripts/dry_run_extraction_system_comparison_synthetic.py",
                          "--out", str(dry_dir)], capture_output=True, text=True, cwd=EXP)
    mutation_file = pathlib.Path("/tmp/mutation_check_amendment01.json")
    mutation = subprocess.run(["python", MUTATION_CHECK.name, "--out", str(mutation_file)],
                              capture_output=True, text=True, cwd=EXP)
    result = {
        "stamp": s, "volume_path": str(out),
        "pytest_returncode": test.returncode, "pytest_output": test.stdout + test.stderr,
        "dry_run_returncode": dry.returncode, "dry_run_output": dry.stdout + dry.stderr,
        "dry_run_files": {str(p.relative_to(dry_dir)): p.read_text()
                          for p in sorted(dry_dir.rglob("*")) if p.is_file()}
        if dry_dir.exists() else {},
        "mutation_returncode": mutation.returncode,
        "mutation_output": (mutation.stdout + mutation.stderr)[-4000:],
        "mutation_result": mutation_file.read_text() if mutation_file.exists() else None,
    }
    (out / "pytest.txt").write_text(result["pytest_output"])
    (out / "dry_run.stdout.txt").write_text(result["dry_run_output"])
    if result["mutation_result"] is not None:
        (out / "mutation_check_amendment01.json").write_text(result["mutation_result"])
    vol.commit()
    return result


@app.function(volumes={str(MOUNT): vol}, timeout=24 * 3600, cpu=4.0, memory=32768)
def compare_job(run_name: str, files: dict[str, str], samples: list[str], usage: dict[str, str],
                sol_tables: str | None) -> dict:
    out = RESULTS / run_name
    if (out / "extraction_system_comparison.json").exists():
        raise FileExistsError(f"{out}/extraction_system_comparison.json exists; results are never "
                              "overwritten")
    work = pathlib.Path("/tmp/work")
    work.mkdir(parents=True)
    args = ["python", "scripts/extraction_system_comparison.py", "compare", "--out",
            str(work / "out")]
    for name, text in files.items():
        (work / f"{name}_registry_claims.jsonl").write_text(text)
        args += [f"--{name.replace('_', '-')}", str(work / f"{name}_registry_claims.jsonl")]
    if samples:
        args.append("--repeat-sample")
        for i, text in enumerate(samples):
            (work / f"repeat_sample_{i}.json").write_text(text)
            args.append(str(work / f"repeat_sample_{i}.json"))
    for role, text in usage.items():
        (work / f"usage_{role}.json").write_text(text)
        args += [f"--usage-{role.replace('_', '-')}", str(work / f"usage_{role}.json")]
    if sol_tables is not None:
        (work / "sensitivity_tables.json").write_text(sol_tables)
        args += ["--sol-tables", str(work / "sensitivity_tables.json")]
    run = subprocess.run(args, cwd=EXP, capture_output=True, text=True)
    if run.returncode:
        raise RuntimeError(f"extraction_system_comparison.py failed:\n{run.stderr[-4000:]}")
    text = (work / "out" / "extraction_system_comparison.json").read_text()
    out.mkdir(parents=True, exist_ok=True)
    (out / "extraction_system_comparison.json").write_text(text)
    vol.commit()
    return {"volume_path": str(out), "extraction_system_comparison": text, "output": run.stdout}


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    s = result["stamp"]
    save_local(LOCAL_EXP / "outputs" / "tests" / f"pytest_amendment01_modal_{s}.txt",
               result["pytest_output"])
    for name, text in result["dry_run_files"].items():
        save_local(LOCAL_EXP / "outputs" / "dry_run_extraction_system_comparison" / s / name, text)
    save_local(LOCAL_EXP / "outputs" / "dry_run_extraction_system_comparison" / s / "stdout.txt",
               result["dry_run_output"])
    if result["mutation_result"] is not None:
        save_local(MUTATION_CHECK.with_name(f"mutation_check_amendment01_{s}.json"),
                   result["mutation_result"])
    print(result["pytest_output"][-1500:])
    print(result["mutation_output"][-600:])
    print(json.dumps({k: result[k] for k in ("stamp", "volume_path", "pytest_returncode",
                                             "dry_run_returncode", "mutation_returncode")},
                     indent=1))


@app.local_entrypoint()
def compare(run_name: str, sol: str, luna_run1: str, luna_run2: str, sol_repeat: str = "",
            usage_sol: str = "", usage_luna_run1: str = "", usage_luna_run2: str = "",
            repeat_sample: str = "", sol_tables: str = "") -> None:
    target = (LOCAL_EXP / "outputs" / "extraction_system_comparison" / run_name
              / "extraction_system_comparison.json")
    if target.exists():
        raise FileExistsError(f"{target} exists; archive it before rerunning")
    usage = {"sol": usage_sol, "luna_run1": usage_luna_run1, "luna_run2": usage_luna_run2}
    if not all(usage.values()):
        raise ValueError("the usage files of the three extraction runs are required: "
                         "--usage-sol, --usage-luna-run1, --usage-luna-run2")
    files = {"sol": sol, "luna_run1": luna_run1, "luna_run2": luna_run2}
    if sol_repeat:
        files["sol_repeat"] = sol_repeat
    result = compare_job.remote(
        run_name, {name: pathlib.Path(path).read_text() for name, path in files.items()},
        [pathlib.Path(p).read_text() for p in repeat_sample.split(",") if p],
        {role: pathlib.Path(path).read_text() for role, path in usage.items()},
        pathlib.Path(sol_tables).read_text() if sol_tables else None)
    save_local(target, result["extraction_system_comparison"])
    print(result["volume_path"])
    print(result["output"])
