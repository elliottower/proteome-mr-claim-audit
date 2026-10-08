"""Modal wrapper for the stage 5 sensitivity run with checkpoints inside it (PREREG.md log,
2026-10-08). It runs scripts/sensitivity_analyses.py `run` as
scripts/modal_biology_joins.py::sensitivity does: the same image, the same inputs read the same
way, the same resources, the same result file. What differs: the three table builders of the
run store each result on the volume as it is computed (scripts/sensitivity_checkpoints.py), the
volume is committed after each, and a job that is restarted, by Modal or by hand under the same
run name with the same inputs, takes the stored results and computes only what is missing. A
run name whose stored inputs differ from the inputs sent is refused.

Run from experiments/02_claims_meta:

    modal run --detach scripts/modal_sensitivity_checkpointed.py::sensitivity --records <...> \\
        --decisions <...> --extraction <...> --checks <...> --run-name <run> \\
        --chase-records <chase search_records.jsonl, comma-separated> \\
        --manual-codes <manual_dataset_codes.csv>

Written on the volume under `/02_claims_meta/stage5/<run>/`: `sensitivity_checkpoints/` (one
file per table-builder call), `sensitivity_tables.json` (the registered result) and
`sensitivity_run.json` (the sha256 of every input, the calls with whether each was computed or
taken from the store, the number of resamples and the seed, the environment). The local
entrypoint saves the last two under `outputs/stage5_biology/<run>/` and prints paths and
hashes, no table.

Client modal 1.4.3; image python 3.12 debian_slim with the pins of modal_biology_joins.py.
"""

import datetime
import json
import pathlib

import modal

from smoke_guard import check_run_name

VOLUME = "proteome-mr-claim-audit-inputs"
MOUNT = pathlib.Path("/vol")
REMOTE = MOUNT / "02_claims_meta"
STAGE5 = REMOTE / "stage5"
EXP = pathlib.Path("/exp")
LOCAL_EXP = pathlib.Path(__file__).resolve().parents[1]
IGNORE = ["__pycache__", "*.pyc", ".pytest_cache"]
INPUTS = ("records", "decisions", "extraction", "checks", "chase_records", "manual_codes")
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
app = modal.App("proteome-mr-sensitivity-checkpointed", image=image)

with image.imports():
    import hashlib
    import importlib.metadata
    import platform

    import biology_joins
    import sensitivity_analyses
    import sensitivity_checkpoints
    from build_registry import N_BOOT, SEED, canonical_inputs
    from dataset_relations import load_rows
    from link_families import SearchRecord
    from manual_dataset_coding import load_codes
    from ontology_graph import load_graph


def stamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def manual_codes(text: str) -> dict:
    path = pathlib.Path("/tmp/manual_dataset_codes.csv")
    path.write_text(text)
    return load_codes(path, load_rows())[0]


@app.function(volumes={str(MOUNT): vol}, timeout=24 * 3600, cpu=4.0, memory=32768,
              retries=modal.Retries(max_retries=3, initial_delay=10.0, backoff_coefficient=1.0))
def sensitivity_job(files: dict[str, str], run_name: str) -> dict:
    folder = STAGE5 / run_name
    target, record_file = folder / "sensitivity_tables.json", folder / "sensitivity_run.json"
    held_inputs = folder / "sensitivity_inputs.json"
    sent = {name: sha256(files[name]) for name in INPUTS}
    vol.reload()
    folder.mkdir(parents=True, exist_ok=True)
    if held_inputs.exists():
        if json.loads(held_inputs.read_text()) != sent:
            raise FileExistsError(f"{folder} holds a run made from other inputs; choose a new "
                                  "run name")
    else:
        held_inputs.write_text(json.dumps(sent, indent=1) + "\n")
        vol.commit()
    if target.exists() and record_file.exists():
        return {"tables": target.read_text(), "record": record_file.read_text()}

    def lines(name: str) -> list[dict]:
        return [json.loads(l) for l in files[name].splitlines() if l.strip()]

    started = stamp()
    with sensitivity_checkpoints.checkpointed(folder / "sensitivity_checkpoints",
                                              vol.commit) as calls:
        result = sensitivity_analyses.run(
            [SearchRecord.model_validate(r) for r in lines("records")],
            {d["pmid"]: d for d in lines("decisions")},
            {r["pmid"]: r["status"] for r in lines("extraction")}, lines("checks"),
            *canonical_inputs(), load_graph(biology_joins.Resources().ontology_edges),
            load_rows(),
            chased=frozenset(r["record_id"] for r in lines("chase_records")),
            manual=manual_codes(files["manual_codes"]) if files["manual_codes"] else None)
    result = {"run_name": run_name, "written_utc": stamp(), **result}
    tables = json.dumps(result, indent=1)
    record = json.dumps({
        "run_name": run_name, "started_utc_of_the_last_attempt": started,
        "written_utc": result["written_utc"], "inputs_sha256": sent,
        "resamples": N_BOOT, "seed": SEED,
        "calls": [{"index": i, "function": name, "result": how} for i, name, how in calls],
        "calls_computed_in_the_last_attempt": sum(how == "computed" for _, _, how in calls),
        "calls_taken_from_the_store": sum(how == "stored" for _, _, how in calls),
        "sensitivity_tables_sha256": sha256(tables),
        "scripts_sha256": {s: hashlib.sha256((EXP / "scripts" / s).read_bytes()).hexdigest()
                           for s in ("sensitivity_analyses.py", "sensitivity_checkpoints.py",
                                     "build_registry.py", "assemble_registry.py",
                                     "modal_sensitivity_checkpointed.py")},
        "environment": {"python": platform.python_version(), "modal": modal.__version__,
                        "packages": {n: importlib.metadata.version(n) for n in PINS}},
        "volume_folder": str(folder)}, indent=1) + "\n"
    target.write_text(tables)
    record_file.write_text(record)
    vol.commit()
    return {"tables": tables, "record": record}


def save_local(folder: str, name: str, content: str) -> pathlib.Path:
    path = LOCAL_EXP / folder / name
    if path.exists():
        raise FileExistsError(f"{path} exists; archive it before rerunning")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


@app.local_entrypoint()
def sensitivity(records: str, decisions: str, extraction: str, checks: str, run_name: str,
                chase_records: str = "", manual_codes: str = "") -> None:
    check_run_name(run_name, "")

    def joined(paths: str) -> str:
        return "".join(pathlib.Path(p).read_text() for p in paths.split(",") if p)

    files = {"records": joined(records), "decisions": joined(decisions),
             "extraction": joined(extraction), "checks": joined(checks),
             "chase_records": joined(chase_records), "manual_codes": joined(manual_codes)}
    result = sensitivity_job.remote(files, run_name)
    path = save_local(f"outputs/stage5_biology/{run_name}", "sensitivity_tables.json",
                      result["tables"])
    save_local(f"outputs/stage5_biology/{run_name}", "sensitivity_run.json", result["record"])
    record = json.loads(result["record"])
    print(json.dumps({"path": str(path.relative_to(LOCAL_EXP)),
                      "sensitivity_tables_sha256": record["sensitivity_tables_sha256"],
                      "calls": len(record["calls"]),
                      "calls_taken_from_the_store": record["calls_taken_from_the_store"]}))
