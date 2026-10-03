"""Modal wrapper for the registry assembly checks and the stage 5 biology joins (logic in
scripts/biology_resource_tables.py, biology_joins.py, sensitivity_analyses.py,
eldjarn_pleiotropic_loci.py and the modules they import). Nothing here reads a pinned file or
runs a test suite on the laptop: the ontology files, Reactome 97, the assay lists, the EpiGraphDB
snapshot and the Eldjarn workbook are read on the volume `proteome-mr-claim-audit-inputs` under
`/02_claims_meta/inputs/`.

Run from experiments/02_claims_meta:

    modal run --detach scripts/modal_biology_joins.py::workbook_heads                # before the freeze
    modal run --detach scripts/modal_biology_joins.py::pleiotropic_loci              # before the freeze
    modal run --detach scripts/modal_biology_joins.py::fetch_platform_lists          # before the freeze
    modal run --detach scripts/modal_biology_joins.py::derive_lists                  # before the freeze
    modal run --detach scripts/modal_biology_joins.py::resource_tables --label <l>   # before the freeze
    modal run --detach scripts/modal_biology_joins.py::unit_tests                    # before the freeze
    modal run --detach scripts/modal_biology_joins.py::verify_claims \
        --extraction outputs/parsed/sol_extraction_<label>_<rev>.jsonl               # stage 4
    modal run --detach scripts/modal_biology_joins.py::joins --inputs <dir> \
        --abstracts <abstracts.jsonl> --run-name <name> [--window update]            # stage 5
    modal run --detach scripts/modal_biology_joins.py::sensitivity --records <search_records.jsonl> \
        --decisions <decisions.jsonl> --extraction <extraction.jsonl> \
        --checks <claim_checks.jsonl> --run-name <name> \
        [--chase-records <chase search_records.jsonl>] \
        [--manual-codes <manual_dataset_codes.csv>] [--smoke-label <label>]          # stage 5
    (each file argument takes one path or several joined by commas: the search and each
    citation-chasing round)

The entrypoints marked "before the freeze" read resource files and synthetic records only: no
claim, pair or registry record. `verify_claims` (stage 4) stores the verification folder it is
sent and its two results under `/02_claims_meta/stage4/<extraction file stem>/`. Every function
writes each result to the volume and commits
before going on; `resource_tables` and `joins` skip a table or analysis whose result is already
on the volume under the same label or run name, so a stopped run resumes. The local entrypoint
then copies the results under verification/ or outputs/. An existing result file is never
overwritten.

The image holds a copy of scripts/, tests/, verification/, dataset_dictionary.csv and
reference/MANIFEST.json under /exp, with /exp/inputs and /exp/derived linked to the volume, so
every script finds its files where it does locally. Client modal 1.4.3; image python 3.12
debian_slim with the pins below.
"""

import datetime
import json
import pathlib

import modal

from smoke_guard import check_run_name, check_smoke_output

VOLUME = "proteome-mr-claim-audit-inputs"
MOUNT = pathlib.Path("/vol")
REMOTE = MOUNT / "02_claims_meta"
CHECKS = REMOTE / "prefreeze_checks"
STAGE4 = REMOTE / "stage4"
STAGE5 = REMOTE / "stage5"
WORKBOOK = REMOTE / "inputs" / "eldjarn2023" / "eldjarn2023_MOESM3.xlsx"
EXP = pathlib.Path("/exp")
LOCAL_EXP = pathlib.Path(__file__).resolve().parents[1]
IGNORE = ["__pycache__", "*.pyc", ".pytest_cache"]
TESTS = ["test_claim_tags.py", "test_ontology_graph.py", "test_hierarchy_relations.py",
         "test_hub_proteins.py", "test_pathway_enrichment.py", "test_reference_screen.py",
         "test_novelty.py", "test_registry_indices.py", "test_assay_backgrounds.py",
         "test_assemble_and_sensitivity.py", "test_registry.py", "test_dataset_relations.py",
         "test_canonical_ids.py", "test_fulltext_concordance.py"]
RESOURCE_FILES = ("ontology_edges.csv", "ontology_edges.meta.json", "platform_assay_lists.csv",
                  "platform_assay_lists.meta.json", "epigraphdb_protein_mapping.csv",
                  "epigraphdb_trait_mapping.csv", "epigraphdb_trait_aliases.csv",
                  "therapeutic_areas.csv", "therapeutic_area_names.csv", "outcome_aliases.csv",
                  "phenotype_cross_references.csv", "phenotype_cross_references.meta.json",
                  "obsolete_label_replacements.csv", "obsolete_label_replacements.meta.json")
PUBLISHED = REMOTE / "inputs" / "platform_assays_published"
ASSAYS = REMOTE / "inputs" / "platform_assays"
DERIVED_TABLES = ("improve_folkersen2017_S3.csv", "nsphs_enroth2014_analysed.csv",
                  "scallop_koprulu2026_S5_targets.csv", "jhs_katz2022_soma13k_reagents.csv",
                  "published_lists_derived.meta.json")
DISEASE_FILE = REMOTE / "inputs" / "opentargets_26.09" / "disease.parquet"
DISEASE_COLUMNS = ["id", "name", "therapeuticAreas", "ontology"]

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
app = modal.App("proteome-mr-biology-joins", image=image)

with image.imports():
    import hashlib
    import shutil
    import subprocess

    import httpx
    import openpyxl
    import pyarrow.parquet as pq

    import biology_joins
    import biology_resource_tables
    import build_outcome_aliases
    import derive_published_lists
    import platform_list_sources
    import eldjarn_pleiotropic_loci
    import sensitivity_analyses
    from build_registry import canonical_inputs
    from dataset_relations import load_rows
    from link_families import SearchRecord
    from manual_dataset_coding import load_codes
    from ontology_graph import load_graph


def stamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")


def write_new(path: pathlib.Path, text: str) -> None:
    if path.exists():
        raise FileExistsError(f"{path} exists; results are never overwritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    vol.commit()


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@app.function(volumes={str(MOUNT): vol}, timeout=3600, cpu=2.0, memory=16384)
def workbook_heads_job() -> dict:
    wb = openpyxl.load_workbook(WORKBOOK, read_only=True)
    result = {"workbook": str(WORKBOOK), "sha256": sha256(WORKBOOK),
              "bytes": WORKBOOK.stat().st_size,
              "sheets": eldjarn_pleiotropic_loci.sheet_heads(wb)}
    result["volume_path"] = str(CHECKS / f"eldjarn2023_workbook_heads_{stamp()}.json")
    write_new(pathlib.Path(result["volume_path"]), json.dumps(result, indent=1, default=str))
    return result


@app.function(volumes={str(MOUNT): vol}, timeout=3600, cpu=2.0, memory=16384)
def pleiotropic_loci_job() -> dict:
    wb = openpyxl.load_workbook(WORKBOOK, read_only=True)
    counts, provenance = eldjarn_pleiotropic_loci.close_genes(wb)
    out = CHECKS / f"pleiotropic_loci_{stamp()}"
    out.mkdir(parents=True)
    eldjarn_pleiotropic_loci.write_list(counts, out / "pleiotropic_loci_eldjarn2023_ST36.csv")
    meta = {"workbook": WORKBOOK.name, "workbook_sha256": sha256(WORKBOOK), **provenance,
            "list_sha256": sha256(out / "pleiotropic_loci_eldjarn2023_ST36.csv"),
            "inputs": "the workbook only; no claim, pair or registry record read"}
    write_new(out / "pleiotropic_loci_eldjarn2023_ST36.meta.json",
              json.dumps(meta, indent=1, default=str))
    return {"volume_path": str(out), "meta": meta,
            "csv": (out / "pleiotropic_loci_eldjarn2023_ST36.csv").read_bytes()}


@app.function(volumes={str(MOUNT): vol}, timeout=6 * 3600, cpu=2.0, memory=16384)
def resource_tables_job(label: str) -> dict:
    out = CHECKS / f"biology_resource_tables_{label}"
    def disease_rows():
        pf = pq.ParquetFile(DISEASE_FILE)
        for batch in pf.iter_batches(batch_size=5_000, columns=DISEASE_COLUMNS):
            yield from batch.to_pylist()

    result = biology_resource_tables.run(EXP, out, vol.commit, disease_rows, DISEASE_FILE)
    derived = REMOTE / "derived" / "epigraphdb_mrres_estimates.jsonl"
    if not derived.exists():
        derived.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out / "mrres_estimates.jsonl", derived)
        vol.commit()
    result["derived_estimates"] = {"volume_path": str(derived), "sha256": sha256(derived)}
    # Bytes, not text: the committed tables must have the sha256 the job recorded.
    return {"volume_path": str(out), "result": result,
            "files": {n: (out / n).read_bytes() for n in RESOURCE_FILES}}


@app.function(volumes={str(MOUNT): vol}, timeout=3600, cpu=2.0, memory=8192)
def fetch_platform_lists_job() -> dict:
    """Fetch the published assay-list files of verification/platform_list_sources.csv and the
    files of verification/published_source_files.csv to the volume, each checked against its
    sha256 and committed before the next, and describe the sheet each list is read from.
    Resource files only."""
    PUBLISHED.mkdir(parents=True, exist_ok=True)
    result: dict = {}
    with httpx.Client(timeout=300, follow_redirects=True) as client:
        for extra in platform_list_sources.load_source_files(
                EXP / "verification" / "published_source_files.csv"):
            target = PUBLISHED / extra.file
            fetched_now = not target.exists()
            if fetched_now:
                r = client.get(extra.url)
                r.raise_for_status()
                target.write_bytes(platform_list_sources.checked_content(extra, r.content))
                vol.commit()
            if sha256(target) != extra.sha256:
                raise platform_list_sources.ListSourceError(
                    f"{target}: sha256 differs from the table")
            result[f"source_file:{extra.file}"] = {
                "file": extra.file, "volume_path": str(target), "fetched_now": fetched_now,
                "bytes": target.stat().st_size, "sha256": extra.sha256}
        for source in platform_list_sources.load_sources(
                EXP / "verification" / "platform_list_sources.csv"):
            if platform_list_sources.is_derived(source):
                continue
            target = PUBLISHED / source.file
            fetched_now = not target.exists()
            if fetched_now:
                r = client.get(source.url)
                r.raise_for_status()
                target.write_bytes(platform_list_sources.checked_content(source, r.content))
                vol.commit()
            if sha256(target) != source.sha256:
                raise platform_list_sources.ListSourceError(
                    f"{target}: sha256 differs from the table")
            wb = openpyxl.load_workbook(target, read_only=True, data_only=True)
            sheet = source.sheet or wb.sheetnames[0]
            rows = list(wb[sheet].iter_rows(values_only=True))
            header, data = platform_list_sources.table(rows, source)
            cells = platform_list_sources.id_cells(rows, source)
            result[source.list_id] = {
                "file": source.file, "volume_path": str(target), "fetched_now": fetched_now,
                "bytes": target.stat().st_size, "sha256": source.sha256,
                "sheets": wb.sheetnames, "sheet_read": sheet, "header": header,
                "data_rows": len(data), "rows_passing_filter": len(cells),
                "distinct_id_cells": len(set(cells)), "empty_id_cells": cells.count(""),
                "first_id_cells": cells[:8],
                "first_data_rows": [{k: v for k, v in list(r.items())[:12]} for r in data[:3]]}
    path = CHECKS / f"platform_list_files_{stamp()}.json"
    write_new(path, json.dumps(result, indent=1))
    return {"volume_path": str(path), "lists": result}


@app.function(volumes={str(MOUNT): vol}, timeout=3600, cpu=2.0, memory=8192)
def derive_lists_job() -> dict:
    """Derive the tables of scripts/derive_published_lists.py from the published files on the
    volume. Resource files only."""
    out = CHECKS / f"published_lists_derived_{stamp()}"
    meta = derive_published_lists.run(PUBLISHED, ASSAYS, out)
    vol.commit()
    return {"volume_path": str(out), "meta": meta,
            "files": {n: (out / n).read_bytes() for n in DERIVED_TABLES}}


@app.function(volumes={str(MOUNT): vol}, timeout=3600, cpu=2.0, memory=8192)
def label_search_job(queries: list[str]) -> dict:
    """Labels of the pinned MONDO and EFO files matching each query (for authoring an alias
    seed). Resource files only."""
    manifest = json.loads((EXP / "reference" / "MANIFEST.json").read_text())
    terms = build_outcome_aliases.load_terms([EXP / manifest["mondo"]["file"],
                                              EXP / manifest["efo"]["file"]])
    return build_outcome_aliases.search(terms, queries)


@app.function(volumes={str(MOUNT): vol}, timeout=3600, cpu=2.0, memory=8192)
def unit_tests_job() -> dict:
    run = subprocess.run(["python", "-m", "pytest", *TESTS, "-q", "-p", "no:cacheprovider"],
                         capture_output=True, text=True, cwd=EXP / "tests")
    dry = subprocess.run(["python", str(EXP / "scripts" / "dry_run_biology_synthetic.py"),
                          "--out", "/tmp/dry"], capture_output=True, text=True, cwd=EXP)
    files = {str(p.relative_to("/tmp/dry")): p.read_text()
             for p in sorted(pathlib.Path("/tmp/dry").rglob("*")) if p.is_file()}
    return {"pytest_returncode": run.returncode, "pytest_output": run.stdout + run.stderr,
            "dry_run_returncode": dry.returncode, "dry_run_output": dry.stdout + dry.stderr,
            "dry_run_files": files}


@app.function(volumes={str(MOUNT): vol}, timeout=24 * 3600, cpu=2.0, memory=8192)
def verify_claims_job(extraction_name: str, extraction: bytes, folder: dict[str, bytes]) -> dict:
    """scripts/verify_claims.py against the pinned HGNC, UniProt, MONDO and EFO files of the
    volume. The verification folder sent (spans.jsonl and the span check's other files) is
    stored beside the results, so the volume folder and the local folder hold the same bytes."""
    stem = pathlib.Path(extraction_name).stem
    out = STAGE4 / stem
    if (out / "claim_checks.jsonl").exists():
        raise FileExistsError(f"{out}/claim_checks.jsonl exists; results are never overwritten")
    work = EXP / "outputs" / "verification" / stem
    work.mkdir(parents=True, exist_ok=True)
    for name, content in folder.items():
        (work / name).write_bytes(content)
    parsed = EXP / "outputs" / "parsed" / extraction_name
    parsed.parent.mkdir(parents=True, exist_ok=True)
    parsed.write_bytes(extraction)
    run = subprocess.run(["python", "scripts/verify_claims.py", "--extraction",
                          f"outputs/parsed/{extraction_name}"], cwd=EXP, capture_output=True,
                         text=True)
    if run.returncode:
        raise RuntimeError(f"verify_claims.py failed:\n{run.stderr[-4000:]}")
    out.mkdir(parents=True, exist_ok=True)
    files = {p.name: p.read_bytes() for p in sorted(work.iterdir()) if p.is_file()}
    for name, content in files.items():
        (out / name).write_bytes(content)
    vol.commit()
    return {"volume_path": str(out),
            "files": {name: files[name] for name in ("claim_checks.jsonl", "claim_summary.json")}}


@app.function(volumes={str(MOUNT): vol}, timeout=24 * 3600, cpu=4.0, memory=32768)
def joins_job(files: dict[str, str], run_name: str, window: str) -> dict:
    inputs = STAGE5 / run_name / "biology_inputs"
    out = STAGE5 / run_name / f"biology_{window}"
    inputs.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        if not (inputs / name).exists():
            (inputs / name).write_text(text)
    vol.commit()
    summaries = biology_joins.run_all(inputs, inputs / "abstracts.jsonl", out,
                                      biology_joins.Resources(), vol.commit, window)
    return {"volume_path": str(out), "summaries": summaries,
            "files": {p.name: p.read_text() for p in sorted(out.iterdir())}}


@app.function(volumes={str(MOUNT): vol}, timeout=24 * 3600, cpu=4.0, memory=32768)
def sensitivity_job(files: dict[str, str], run_name: str, smoke_window: bool = False) -> dict:
    target = STAGE5 / run_name / "sensitivity_tables.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; choose a new run name")

    def lines(name: str) -> list[dict]:
        return [json.loads(l) for l in files[name].splitlines() if l.strip()]

    result = sensitivity_analyses.run(
        [SearchRecord.model_validate(r) for r in lines("records")],
        {d["pmid"]: d for d in lines("decisions")},
        {r["pmid"]: r["status"] for r in lines("extraction")}, lines("checks"),
        *canonical_inputs(), load_graph(biology_joins.Resources().ontology_edges), load_rows(),
        chased=frozenset(r["record_id"] for r in lines("chase_records")),
        manual=manual_codes(files["manual_codes"]) if files["manual_codes"] else None,
        smoke_window=smoke_window)
    result = {"run_name": run_name, "written_utc": stamp(), **result}
    write_new(target, json.dumps(result, indent=1))
    return result


def manual_codes(text: str) -> dict:
    path = pathlib.Path("/tmp/manual_dataset_codes.csv")
    path.write_text(text)
    return load_codes(path, load_rows())[0]


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
def workbook_heads() -> None:
    result = workbook_heads_job.remote()
    path = save_local("outputs/resource_counts", pathlib.Path(result["volume_path"]).name,
                      json.dumps(result, indent=1, default=str))
    print(path, len(result["sheets"]), "sheets")


@app.local_entrypoint()
def pleiotropic_loci() -> None:
    result = pleiotropic_loci_job.remote()
    save_local("verification", "pleiotropic_loci_eldjarn2023_ST36.csv", result["csv"])
    path = save_local("verification", "pleiotropic_loci_eldjarn2023_ST36.meta.json",
                      json.dumps(result["meta"], indent=1, default=str))
    print(path, result["meta"]["distinct_genes"], "genes", result["meta"]["variant_rows"],
          "variant rows")


@app.local_entrypoint()
def resource_tables(label: str) -> None:
    result = resource_tables_job.remote(label)
    for name, text in result["files"].items():
        save_local("verification", name, text)
    path = save_local("outputs/resource_counts", f"biology_resource_tables_{label}.json",
                      json.dumps(result["result"], indent=1))
    print(path)


@app.local_entrypoint()
def fetch_platform_lists() -> None:
    result = fetch_platform_lists_job.remote()
    path = save_local("outputs/resource_counts", pathlib.Path(result["volume_path"]).name,
                      json.dumps(result["lists"], indent=1))
    print(path)
    for list_id, r in result["lists"].items():
        print(list_id, r["bytes"], "bytes;", r.get("rows_passing_filter"), "rows;",
              r.get("distinct_id_cells"), "distinct identifier cells")


@app.local_entrypoint()
def derive_lists() -> None:
    result = derive_lists_job.remote()
    for name, content in result["files"].items():
        save_local("verification/published_lists_derived", name, content)
    print(json.dumps(result["meta"], indent=1))


@app.local_entrypoint()
def label_search(queries: str, out: str) -> None:
    """`queries`: a text file, one query per line. `out`: the JSON file to write."""
    target = pathlib.Path(out)
    if target.exists():
        raise FileExistsError(f"{target} exists")
    lines = [q.strip() for q in pathlib.Path(queries).read_text().splitlines() if q.strip()]
    target.write_text(json.dumps(label_search_job.remote(lines), indent=1))
    print(target)


@app.local_entrypoint()
def unit_tests() -> None:
    result = unit_tests_job.remote()
    s = stamp()
    save_local("outputs/tests", f"pytest_biology_modal_{s}.txt", result["pytest_output"])
    for name, text in result["dry_run_files"].items():
        save_local(f"outputs/dry_run_biology/{s}", name, text)
    save_local(f"outputs/dry_run_biology/{s}", "stdout.txt", result["dry_run_output"])
    print(result["pytest_output"][-1500:])
    print("pytest return code", result["pytest_returncode"])
    print("dry run return code", result["dry_run_returncode"], result["dry_run_output"][-1500:])


@app.local_entrypoint()
def verify_claims(extraction: str) -> None:
    path = pathlib.Path(extraction)
    folder = LOCAL_EXP / "outputs" / "verification" / path.stem
    if not (folder / "spans.jsonl").is_file():
        raise FileNotFoundError(f"{folder}/spans.jsonl missing; run scripts/verify_spans.py first")
    sent = {p.name: p.read_bytes() for p in sorted(folder.iterdir()) if p.is_file()}
    result = verify_claims_job.remote(path.name, path.read_bytes(), sent)
    for name, content in result["files"].items():
        save_local(f"outputs/verification/{path.stem}", name, content)
    print(result["volume_path"])
    print(result["files"]["claim_summary.json"].decode())


def joined_files(paths: str) -> str:
    """The text of the comma-separated files, each ending in a newline, as one."""
    texts = [pathlib.Path(p).read_text() for p in paths.split(",") if p]
    return "".join(t if t.endswith("\n") or not t else t + "\n" for t in texts)


@app.local_entrypoint()
def joins(inputs: str, abstracts: str, run_name: str, window: str = "confirmatory") -> None:
    folder = pathlib.Path(inputs)
    # A smoke registry's tables go under its smoke label, and no other registry's do.
    check_smoke_output(folder, run_name)
    files = {p.name: p.read_text() for p in sorted(folder.iterdir()) if p.is_file()}
    files["abstracts.jsonl"] = joined_files(abstracts)
    result = joins_job.remote(files, run_name, window)
    for name, text in result["files"].items():
        save_local(f"outputs/stage5_biology/{run_name}/{window}", name, text)
    print(json.dumps({k: {x: y for x, y in v.items() if not isinstance(y, (list, dict))}
                      for k, v in result["summaries"].items()}, indent=1))


@app.local_entrypoint()
def sensitivity(records: str, decisions: str, extraction: str, checks: str,
                run_name: str, chase_records: str = "", manual_codes: str = "",
                smoke_label: str = "") -> None:
    """`smoke_label` (before the freeze only): the smoke switch of
    scripts/assemble_registry.py; the run name must start with the label, and a run name that
    starts with `smoke_` needs the label."""
    check_run_name(run_name, smoke_label)

    def joined(paths: str) -> str:
        return "".join(pathlib.Path(p).read_text() for p in paths.split(",") if p)

    files = {"records": joined(records), "decisions": joined(decisions),
             "extraction": joined(extraction), "checks": joined(checks),
             "chase_records": joined(chase_records), "manual_codes": joined(manual_codes)}
    result = sensitivity_job.remote(files, run_name, bool(smoke_label))
    path = save_local(f"outputs/stage5_biology/{run_name}", "sensitivity_tables.json",
                      json.dumps(result, indent=1))
    print(path)
