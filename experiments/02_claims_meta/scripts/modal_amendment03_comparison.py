"""Modal wrapper for stages 4L (assemblies) and 5L (the comparison) under
AMENDMENT_03_extraction_comparison_verification.md. Nothing here holds logic of the study:
scripts/assemble_registry.py and scripts/extraction_system_comparison.py run unchanged; the
comparison runs inside `extraction_system_comparison_checkpoints.checkpointed`, so each
agreement block and each H1/H2 table is stored on the volume as it is computed and a restarted
job computes only what is missing.

Run from experiments/02_claims_meta (the span step and the claim verifier of 4L are run before,
by scripts/modal_verify_spans_occurrence.py::span_step and
scripts/modal_verify_claims_amended.py::verify_claims with --label amendment03; RUNBOOK_amendment03.md):

    modal run --detach scripts/modal_amendment03_comparison.py::tests
    modal run --detach scripts/modal_amendment03_comparison.py::assemble --source comparator_check
    modal run --detach scripts/modal_amendment03_comparison.py::assemble --source luna_run1
    modal run --detach scripts/modal_amendment03_comparison.py::assemble --source luna_run2
    modal run --detach scripts/modal_amendment03_comparison.py::assemble --source sol_repeat
    modal run --detach scripts/modal_amendment03_comparison.py::compare --rule-label originally_registered \\
        --sol outputs/registry/2026-10-03_registered_with_27_coded_a/registry_claims.jsonl \\
        --sol-tables outputs/stage5_biology/2026-10-03_registered_with_27_a/sensitivity_tables.json

`assemble --source comparator_check` assembles the originally registered Sol analysis again from
the inputs named below into a scratch folder on the volume and stops unless every file equals
the committed assembly `outputs/registry/2026-10-03_registered_with_27_coded_a` byte for byte
(`registry_assembly.json` apart from its time stamp); it shows that the records, decisions and
code table named here are those of the comparator. The three other sources are assembled only
after it has passed. Each assembly is one call of the registered script, stored on the volume
when it ends and never recomputed.

`compare` first checks, in the container and before anything is computed, that the rule label,
the Sol registry and the Sol tables passed are the originally registered analysis's (path and
sha256, `extraction_system_comparison_checkpoints.comparator_check`); then it reproduces the Sol primary table from the Sol registry and stops unless it
equals the `primary` entry of the Sol tables; then it runs the comparison. Results are stored
under /02_claims_meta/amendment03/ on the volume and copied to
outputs/extraction_system_comparison/amendment03_originally_registered/. Nothing is overwritten.

Client modal 1.4.3; image python 3.12 debian_slim with the pins of pyproject.toml.
"""

import argparse
import datetime
import json
import pathlib
import subprocess

import modal

VOLUME = "proteome-mr-claim-audit-inputs"
MOUNT = pathlib.Path("/vol")
REMOTE = MOUNT / "02_claims_meta"
STORE = REMOTE / "amendment03"
EXP = pathlib.Path("/exp")
LOCAL_EXP = pathlib.Path(__file__).resolve().parents[1]
IGNORE = ["__pycache__", "*.pyc", ".pytest_cache"]
COMPARATOR_FOLDER = "outputs/registry/2026-10-03_registered_with_27_coded_a"
RUN_NAME = "amendment03_originally_registered"
LREV, REV = "e4e4ee731887", "0b97103cd7a4"
LABELS = ("search", "chase1", "chase2", "chase3")
RECORDS = [f"outputs/screening/{d}/search_records.jsonl"
           for d in ("2026-10-03", "chase_round_1", "chase_round_2", "chase_round_3")]
DECISIONS = [f"outputs/parsed/sol_eligibility_{d}_2811496ef424.decisions.jsonl"
             for d in ("search_complete", "chase1", "gate1b1", "gate1b2", "gate1b3", "gate1b4",
                       "gate1b5", "gateall1", "chase2", "gateall2", "gateall3")]
CODES = ("outputs/manual_coding/2026-10-03_registered_with_27/final_codes_every_coded_row_marked/"
         "manual_dataset_codes.csv")
ASSEMBLY_FILES = ("families.json", "families_meta.json", "record_dates.json",
                  "registry_claims.jsonl", "registry_claims_update.jsonl", "dating_claims.jsonl",
                  "dating_claims_update.jsonl", "registry_claims_without_manual_coding.jsonl",
                  "registry_claims_without_manual_coding_update.jsonl", "registry_assembly.json")


def checks_of(stem: str) -> str:
    return f"outputs/verification_amendment02/amendment03/{stem}/claim_checks.jsonl"


SOURCES = {
    "comparator_check": {
        "extraction": [f"outputs/parsed/sol_extraction_{l}_{REV}.jsonl" for l in LABELS],
        "checks": ["outputs/verification_amendment02/registered_with_27/"
                   f"sol_extraction_search_{REV}/claim_checks.jsonl"]
                  + [f"outputs/verification/sol_extraction_{l}_{REV}/claim_checks.jsonl"
                     for l in LABELS[1:]]},
    **{f"luna_run{k}": {
        "extraction": [f"outputs/parsed/luna_extraction_{l}_run{k}_{LREV}.jsonl" for l in LABELS],
        "checks": [checks_of(f"luna_extraction_{l}_run{k}_{LREV}") for l in LABELS]}
       for k in (1, 2)},
    "sol_repeat": {
        "extraction": [f"outputs/parsed/sol_extraction_{l}_repeat_{REV}.jsonl" for l in LABELS],
        "checks": [checks_of(f"sol_extraction_{l}_repeat_{REV}") for l in LABELS]},
}
REPEAT_SAMPLES = [f"outputs/parsed/sol_eligibility_{d}_2811496ef424.decisions.repeat_sample.json"
                  for d in ("search_complete", "round1_all", "round2_all", "round3_all")]
USAGE = {"sol": ("outputs/raw/sol/extraction/" + REV,
                 [f"outputs/parsed/sol_extraction_{l}_{REV}.jsonl" for l in LABELS]),
         **{f"luna_run{k}": (f"outputs/raw/luna/extraction/{LREV}/run{k}",
                             [f"outputs/parsed/luna_extraction_{l}_run{k}_{LREV}.jsonl"
                              for l in LABELS]) for k in (1, 2)}}
TESTS = ["test_extraction_system_comparison_checkpoints.py", "test_extraction_system_comparison.py"]

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
         .add_local_file(LOCAL_EXP / "reference" / "MANIFEST.json",
                         str(EXP / "reference" / "MANIFEST.json"), copy=True)
         .add_local_file(LOCAL_EXP / COMPARATOR_FOLDER / "registry_claims.jsonl",
                         str(EXP / COMPARATOR_FOLDER / "registry_claims.jsonl"), copy=True)
         .add_local_file(LOCAL_EXP / "outputs/stage5_biology/2026-10-03_registered_with_27_a/"
                                     "sensitivity_tables.json",
                         str(EXP / "outputs/stage5_biology/2026-10-03_registered_with_27_a/"
                                   "sensitivity_tables.json"), copy=True)
         .run_commands(f"ln -s {REMOTE / 'inputs'} {EXP / 'inputs'}",
                       f"ln -s {REMOTE / 'derived'} {EXP / 'derived'}"))
vol = modal.Volume.from_name(VOLUME)
app = modal.App("proteome-mr-amendment03-comparison", image=image)

with image.imports():
    import hashlib

    import extraction_system_comparison as ec
    import extraction_system_comparison_checkpoints as ck


def stamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")


def digest(content: bytes) -> dict:
    return {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}


def read(paths: list[str]) -> dict[str, bytes]:
    return {p: (LOCAL_EXP / p).read_bytes() for p in paths}


def save_local(path: pathlib.Path, content: bytes) -> None:
    if path.exists():
        raise FileExistsError(f"{path} exists; nothing is overwritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


@app.function(volumes={str(MOUNT): vol}, timeout=3600, cpu=4.0, memory=16384)
def tests_job() -> dict:
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", *TESTS],
                         capture_output=True, text=True, cwd=EXP / "tests")
    return {"stamp": stamp(), "returncode": run.returncode, "output": run.stdout + run.stderr}


@app.function(volumes={str(MOUNT): vol}, timeout=6 * 3600, cpu=4.0, memory=32768)
def assemble_job(source: str, inputs: dict[str, bytes]) -> dict:
    out = STORE / "assemblies" / source
    if (out / "DONE.json").exists():
        return {"record": json.loads((out / "DONE.json").read_text()),
                "files": {n: (out / n).read_bytes() for n in ASSEMBLY_FILES}}
    if source != "comparator_check" and not (
            STORE / "assemblies" / "comparator_check" / "DONE.json").exists():
        raise RuntimeError("the comparator check has not passed; no other source is assembled")
    for path, content in inputs.items():
        (EXP / path).parent.mkdir(parents=True, exist_ok=True)
        (EXP / path).write_bytes(content)
    spec = SOURCES[source]
    work = EXP / "outputs" / "registry" / f"amendment03_{source}"
    command = ["python", "scripts/assemble_registry.py", "--records", *RECORDS,
               "--decisions", *DECISIONS, "--extraction", *spec["extraction"],
               "--checks", *spec["checks"], "--manual-codes", CODES, "--out", str(work)]
    run = subprocess.run(command, cwd=EXP, capture_output=True, text=True)
    if run.returncode:
        raise RuntimeError(f"assemble_registry.py failed for {source}:\n{run.stderr[-4000:]}")
    files = {n: (work / n).read_bytes() for n in ASSEMBLY_FILES}
    record = {"source": source, "finished_utc": stamp(), "command": command,
              "inputs": {p: digest(c) for p, c in sorted(inputs.items())},
              "outputs": {n: digest(c) for n, c in files.items()}}
    if source == "comparator_check":
        committed = {n: (EXP / COMPARATOR_FOLDER / n).read_bytes() for n in ASSEMBLY_FILES}
        same = {n: files[n] == committed[n] for n in ASSEMBLY_FILES if n != "registry_assembly.json"}
        ours, theirs = (json.loads(x["registry_assembly.json"]) for x in (files, committed))
        same["registry_assembly.json without written_utc"] = (
            {k: v for k, v in ours.items() if k != "written_utc"}
            == {k: v for k, v in theirs.items() if k != "written_utc"})
        record["byte_identical_to_comparator"] = same
        if not all(same.values()):
            raise RuntimeError(f"the reassembled comparator differs from {COMPARATOR_FOLDER}: "
                               f"{sorted(k for k, v in same.items() if not v)}")
    out.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (out / name).write_bytes(content)
    (out / "DONE.json").write_text(json.dumps(record, indent=1) + "\n")
    vol.commit()
    return {"record": record, "files": files}


@app.function(volumes={str(MOUNT): vol}, timeout=24 * 3600, cpu=4.0, memory=32768)
def compare_job(rule_label: str, sol_path: str, tables_path: str, tables: bytes,
                files: dict[str, bytes], samples: list[bytes], usage: dict[str, bytes]) -> dict:
    out = STORE / "comparison" / RUN_NAME
    if (out / "extraction_system_comparison.json").exists():
        raise FileExistsError(f"{out}/extraction_system_comparison.json exists")
    checked = ck.comparator_check(rule_label, sol_path, files["sol"], tables_path, tables)
    work = pathlib.Path("/tmp/work")
    work.mkdir(parents=True)
    tables_file = work / "sensitivity_tables.json"
    tables_file.write_bytes(tables)
    paths = {}
    for name, content in files.items():
        paths[name] = work / f"{name}_registry_claims.jsonl"
        paths[name].write_bytes(content)
    sample_paths = []
    for i, content in enumerate(samples):
        sample_paths.append(work / f"repeat_sample_{i}.json")
        sample_paths[-1].write_bytes(content)
    usage_paths = {}
    for role, content in usage.items():
        usage_paths[role] = work / f"usage_{role}.json"
        usage_paths[role].write_bytes(content)
    with ck.checkpointed(out / "checkpoints", vol.commit) as calls:
        sol_table = ec.h1_h2(ec.read_claims(paths["sol"]), ec.load_rows(), ec.N_BOOT, ec.SEED)
        ec.check_primary(sol_table, json.loads(tables)["primary"])
        ec.main_compare(argparse.Namespace(
            sol=paths["sol"], luna_run1=paths["luna_run1"], luna_run2=paths["luna_run2"],
            sol_repeat=paths["sol_repeat"], repeat_sample=sample_paths,
            sol_tables=tables_file, usage_sol=usage_paths["sol"],
            usage_luna_run1=usage_paths["luna_run1"], usage_luna_run2=usage_paths["luna_run2"],
            n_boot=ec.N_BOOT, out=work / "out"))
    text = (work / "out" / "extraction_system_comparison.json").read_text()
    record = {"finished_utc": stamp(), "comparator": checked, "calls": calls,
              "inputs": {n: digest(c) for n, c in files.items()},
              "usage": {n: digest(c) for n, c in usage.items()},
              "repeat_samples": [digest(c) for c in samples]}
    (out / "extraction_system_comparison.json").write_text(text)
    (out / "comparison_run.json").write_text(json.dumps(record, indent=1) + "\n")
    vol.commit()
    return {"text": text, "record": record}


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    save_local(LOCAL_EXP / "outputs" / "tests" / f"pytest_amendment03_modal_{result['stamp']}.txt",
               result["output"].encode())
    print(result["output"][-1500:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def assemble(source: str) -> None:
    spec = SOURCES[source]
    target = LOCAL_EXP / "outputs" / "extraction_system_comparison" / RUN_NAME / f"{source}_registry"
    if target.exists():
        raise FileExistsError(f"{target} exists; nothing is overwritten")
    inputs = read([*RECORDS, *DECISIONS, CODES, *spec["extraction"], *spec["checks"]]
                  + ([f"{COMPARATOR_FOLDER}/{n}" for n in ASSEMBLY_FILES]
                     if source == "comparator_check" else []))
    result = assemble_job.remote(source, inputs)
    record = result["record"]
    for name, content in result["files"].items():
        save_local(target / name, content)
    save_local(target / "assembly_run.json", (json.dumps(record, indent=1) + "\n").encode())
    print(json.dumps({"source": source, "outputs": record["outputs"],
                      **({"byte_identical_to_comparator": record["byte_identical_to_comparator"]}
                         if source == "comparator_check" else {})}, indent=1))


@app.local_entrypoint()
def compare(rule_label: str, sol: str, sol_tables: str) -> None:
    folder = LOCAL_EXP / "outputs" / "extraction_system_comparison" / RUN_NAME
    target = folder / "extraction_system_comparison.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; nothing is overwritten")
    files = {"sol": (LOCAL_EXP / sol).read_bytes(),
             **{s: (folder / f"{s}_registry" / "registry_claims.jsonl").read_bytes()
                for s in ("luna_run1", "luna_run2", "sol_repeat")}}
    usage = {role: (folder / f"usage_{role}.json").read_bytes() for role in USAGE}
    result = compare_job.remote(rule_label, sol, sol_tables, (LOCAL_EXP / sol_tables).read_bytes(),
                                files,
                                [(LOCAL_EXP / p).read_bytes() for p in REPEAT_SAMPLES], usage)
    save_local(target, result["text"].encode())
    save_local(folder / "comparison_run.json",
               (json.dumps(result["record"], indent=1) + "\n").encode())
    print(target)
