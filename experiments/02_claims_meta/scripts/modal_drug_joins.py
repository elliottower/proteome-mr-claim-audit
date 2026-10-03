"""Modal wrapper for the drug-development joins (logic in scripts/drug_tables.py,
scripts/drug_joins.py and scripts/drug_schema_check.py). Nothing here reads a pinned table on
the laptop: ChEMBL 37 (`/chembl_37/tables/`, shared and read-only by convention) and Open
Targets 26.09 (`/02_claims_meta/inputs/opentargets_26.09/`) are read on the volume
`proteome-mr-claim-audit-inputs`.

Run from experiments/02_claims_meta:

    modal run --detach scripts/modal_drug_joins.py::schema        # before the freeze
    modal run --detach scripts/modal_drug_joins.py::unit_tests    # before the freeze
    modal run --detach scripts/modal_drug_joins.py::index_counts  # before the freeze
    modal run --detach scripts/modal_drug_joins.py::joins --claims <registry_claims.jsonl> \
        --wording <claim_tags.jsonl> --run-name <name>                             # stage 5

`--wording` is the claim-tag file of scripts/claim_tags.py (`claim_record_id`, `wording_class`
per line; the file the biology joins read). `--ontology-edges` defaults to the committed
verification/ontology_edges.csv (scripts/ontology_graph.py), the one-step edges that
`related_indication` reads.

Adding `--synthetic` to `joins` runs the same job on synthetic claims before the freeze: it
writes under `/02_claims_meta/prefreeze_checks/wiring/` and outputs/dry_run_drug/, never under
stage 5.

`schema` and `index_counts` read resource files only: no claim, pair or registry record.
Every function writes its result to the volume and commits before returning it; the local
entrypoint then copies the result under outputs/. The index is built once
(`/02_claims_meta/stage5/drug_index_<code hash>.json`, named by the sha256 of drug_tables.py and
drug_joins.py, so an index built by other code is never reused) and reused; the pair joins take
seconds, so one commit follows them. An existing result file is never overwritten.

Client modal 1.4.3; image python 3.12 debian_slim with the pins below.
"""

import datetime
import hashlib
import json
import pathlib
import subprocess

import modal

from smoke_guard import check_smoke_output

VOLUME = "proteome-mr-claim-audit-inputs"
MOUNT = pathlib.Path("/vol")
CHEMBL_TABLES = MOUNT / "chembl_37" / "tables"
OPEN_TARGETS = MOUNT / "02_claims_meta" / "inputs" / "opentargets_26.09"
CHECKS = MOUNT / "02_claims_meta" / "prefreeze_checks"
STAGE5 = MOUNT / "02_claims_meta" / "stage5"
TESTS = "/root/tests"
COLLISION_TABLE = pathlib.Path("/root/verification/mondo_efo_collision_table.csv")
LOCAL_EXP = pathlib.Path(__file__).resolve().parents[1]

image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("pyarrow==21.0.0", "pydantic==2.13.5", "pytest==8.4.2")
         .add_local_python_source("drug_joins", "drug_tables", "drug_schema_check",
                                  "canonical_ids", "dry_run_drug_synthetic", "smoke_guard")
         .add_local_file(LOCAL_EXP / "tests" / "test_drug_joins.py",
                         f"{TESTS}/test_drug_joins.py")
         .add_local_file(LOCAL_EXP / "tests" / "test_drug_tables.py",
                         f"{TESTS}/test_drug_tables.py")
         .add_local_file(LOCAL_EXP / "verification" / "mondo_efo_collision_table.csv",
                         str(COLLISION_TABLE)))
vol = modal.Volume.from_name(VOLUME)
app = modal.App("proteome-mr-drug-joins", image=image)

with image.imports():
    import pyarrow.parquet as pq

    import drug_joins
    import drug_schema_check
    import drug_tables
    from canonical_ids import load_collision_table


def stamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")


def write_new(path: pathlib.Path, text: str) -> None:
    if path.exists():
        raise FileExistsError(f"{path} exists; results are never overwritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    vol.commit()


def code_hash() -> str:
    h = hashlib.sha256()
    for module in (drug_tables, drug_joins):
        h.update(pathlib.Path(module.__file__).read_bytes())
    return h.hexdigest()[:12]


def report_rows():
    pf = pq.ParquetFile(OPEN_TARGETS / "clinical_report.parquet")
    for batch in pf.iter_batches(batch_size=20_000, columns=drug_tables.OT_REPORT_COLUMNS):
        yield from batch.to_pylist()


def build_index() -> "drug_joins.DrugIndex":
    wanted = {d for r in report_rows() for d in drug_tables.report_drug_ids(r)}
    diseases = [r["id"] for b in pq.ParquetFile(OPEN_TARGETS / "disease.parquet")
                .iter_batches(columns=["id"]) for r in b.to_pylist()]
    sums = (CHEMBL_TABLES / "SHA256SUMS").read_text()
    return drug_tables.build_index(
        CHEMBL_TABLES, report_rows(), diseases, wanted,
        {"built_utc": stamp(), "chembl_tables": str(CHEMBL_TABLES),
         "chembl_tables_sha256sums": sums, "open_targets": str(OPEN_TARGETS)})


@app.function(volumes={str(MOUNT): vol}, timeout=24 * 3600, cpu=2.0, memory=8192)
def schema_check() -> dict:
    result = drug_schema_check.run(CHEMBL_TABLES, OPEN_TARGETS)
    result["volume_path"] = str(CHECKS / f"drug_schema_check_{stamp()}.json")
    write_new(pathlib.Path(result["volume_path"]), json.dumps(result, indent=1))
    return result


@app.function(volumes={str(MOUNT): vol}, timeout=24 * 3600, cpu=2.0, memory=8192)
def index_counts_job() -> dict:
    """Build the index from the real files and return its provenance counts only. The index
    itself is not kept: stage 5 builds it after the freeze."""
    index = build_index()
    result = {"provenance": index.provenance, "mechanisms": len(index.mechanisms),
              "indications": len(index.indications), "trials": len(index.trials),
              "resource_disease_ids": len(index.resource_disease_ids),
              "index_json_bytes": len(index.model_dump_json()),
              "inputs": "resource files only; no claim, pair or registry record read"}
    result["volume_path"] = str(CHECKS / f"drug_index_counts_{stamp()}.json")
    write_new(pathlib.Path(result["volume_path"]), json.dumps(result, indent=1))
    return result


@app.function(timeout=3600, cpu=2.0, memory=4096)
def unit_tests_job() -> dict:
    run = subprocess.run(["python", "-m", "pytest", TESTS, "-q", "-p", "no:cacheprovider"],
                         capture_output=True, text=True, cwd="/root")
    dry = subprocess.run(["python", "-m", "dry_run_drug_synthetic", "--out", "/tmp/dry"],
                         capture_output=True, text=True, cwd="/root")
    files = {p.name: p.read_text() for p in pathlib.Path("/tmp/dry").glob("*")}
    return {"pytest_returncode": run.returncode, "pytest_output": run.stdout + run.stderr,
            "dry_run_returncode": dry.returncode, "dry_run_output": dry.stdout + dry.stderr,
            "dry_run_files": files}


@app.function(volumes={str(MOUNT): vol}, timeout=24 * 3600, cpu=2.0, memory=8192)
def joins_job(claims_jsonl: str, wording_jsonl: str, edges_csv: str, run_name: str,
              synthetic: bool) -> dict:
    base = CHECKS / "wiring" if synthetic else STAGE5
    out = base / run_name
    if (out / "drug_tables.json").exists():
        raise FileExistsError(f"{out} holds a finished run; choose a new run name")
    index_path = base / f"drug_index_{code_hash()}.json"
    if not index_path.exists():
        write_new(index_path, build_index().model_dump_json())
    index_text = index_path.read_text()
    index = drug_joins.DrugIndex.model_validate_json(index_text)
    out.mkdir(parents=True, exist_ok=True)
    for name, text in (("registry_claims.jsonl", claims_jsonl), ("wording.jsonl", wording_jsonl),
                       ("ontology_edges.csv", edges_csv)):
        (out / name).write_text(text)
    vol.commit()
    look = drug_joins.Lookup(index, load_collision_table(COLLISION_TABLE),
                             drug_joins.load_edges(out / "ontology_edges.csv"))
    claims = drug_joins.load_claims(out / "registry_claims.jsonl", out / "wording.jsonl")
    result, pairs, claim_records = drug_joins.tables(claims, look)
    header = {"run_name": run_name, "synthetic": synthetic, "written_utc": stamp(),
              "index_file": str(index_path),
              "index_sha256": hashlib.sha256(index_text.encode()).hexdigest(),
              "index_provenance": index.provenance,
              "n_claims": len(claims)}
    drug_joins.write_outputs(out, header, result, pairs, claim_records)
    vol.commit()
    return {**header, "levels": result, "volume_path": str(out),
            "files": {n: (out / n).read_text() for n in
                      ("drug_tables.json", "drug_pair_records.jsonl",
                       "drug_claim_records.jsonl")}}


def save_local(folder: str, name: str, text: str) -> pathlib.Path:
    path = LOCAL_EXP / "outputs" / folder / name
    if path.exists():
        raise FileExistsError(f"{path} exists; archive it before rerunning")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


@app.local_entrypoint()
def schema() -> None:
    result = schema_check.remote()
    path = save_local("resource_counts", pathlib.Path(result["volume_path"]).name,
                      json.dumps(result, indent=1))
    print(path, "ok" if result["ok"] else "NOT OK", result["missing_required_columns"])


@app.local_entrypoint()
def index_counts() -> None:
    result = index_counts_job.remote()
    path = save_local("resource_counts", pathlib.Path(result["volume_path"]).name,
                      json.dumps(result, indent=1))
    print(path)


@app.local_entrypoint()
def unit_tests() -> None:
    result = unit_tests_job.remote()
    s = stamp()
    save_local("tests", f"pytest_drug_joins_modal_{s}.txt", result["pytest_output"])
    for name, text in result["dry_run_files"].items():
        save_local(f"dry_run_drug/{s}", name, text)
    save_local(f"dry_run_drug/{s}", "stdout.txt", result["dry_run_output"])
    print(result["pytest_output"][-600:])
    print("dry run return code", result["dry_run_returncode"], result["dry_run_output"][-400:])


@app.local_entrypoint()
def joins(claims: str, wording: str, run_name: str,
          ontology_edges: str = str(LOCAL_EXP / "verification" / "ontology_edges.csv"),
          synthetic: bool = False) -> None:
    if not synthetic:
        # A smoke registry's joins go under its smoke label, and no other registry's do.
        check_smoke_output(pathlib.Path(claims).parent, run_name)
    result = joins_job.remote(pathlib.Path(claims).read_text(),
                              pathlib.Path(wording).read_text(),
                              pathlib.Path(ontology_edges).read_text(), run_name, synthetic)
    folder = f"dry_run_drug/modal_wiring_{run_name}" if synthetic else f"stage5_drug/{run_name}"
    for name, text in result.pop("files").items():
        save_local(folder, name, text)
    print(json.dumps(result["levels"], indent=1))
