"""Schema check of the pinned ChEMBL 37 and Open Targets 26.09 files against the columns the
drug-development join reads (logic for the `schema_check` function of scripts/modal_drug_joins.py).

The check reads resource files only. No claim, pair or registry record is an input, and nothing
is joined to any. It reports, per file: the columns present, the required columns missing, and
the distinct values of the categorical columns the registered rules name (target types, action
types, phase values, trial statuses, stop-reason labels, identifier prefixes), each compared
with the values the rules expect. It raises nothing itself; `ok` is false when any required
column is missing or any registered value set differs from the file.
"""

import collections
import csv
import datetime
import pathlib
import re
from collections.abc import Iterable, Iterator

import pyarrow.parquet as pq

from drug_joins import ACTIVE_STATUSES, STOP_LABELS, SUSPENDED
from drug_tables import (CHEMBL_REQUIRED, COMPONENT_LEVEL_TYPES, HUMAN, OT_REQUIRED, PRIMARY_TYPE,
                         id_prefix)

CSV_FIELD_LIMIT = 1 << 24


def csv_rows(path: pathlib.Path) -> Iterator[dict[str, str]]:
    csv.field_size_limit(CSV_FIELD_LIMIT)
    with path.open(newline="") as f:
        yield from csv.DictReader(f)


def csv_header(path: pathlib.Path) -> list[str]:
    with path.open(newline="") as f:
        return next(csv.reader(f))


def parquet_columns(path: pathlib.Path) -> dict[str, str]:
    """Top-level and one-level nested field paths (`drugs.drugId`) with their Arrow types."""
    out: dict[str, str] = {}
    for field in pq.read_schema(path):
        out[field.name] = str(field.type)
        t = field.type
        inner = getattr(t, "value_type", t)
        for i in range(getattr(inner, "num_fields", 0)):
            out[f"{field.name}.{inner.field(i).name}"] = str(inner.field(i).type)
    return out


def parquet_rows(path: pathlib.Path, columns: list[str]) -> Iterator[dict]:
    pf = pq.ParquetFile(path)
    for batch in pf.iter_batches(batch_size=20_000, columns=columns):
        yield from batch.to_pylist()


def counter(values: Iterable) -> dict[str, int]:
    return dict(sorted(collections.Counter("" if v is None else str(v) for v in values).items()))


def chembl_report(tables: pathlib.Path) -> dict:
    files = {}
    for table, cols in CHEMBL_REQUIRED.items():
        header = csv_header(tables / f"{table}.csv")
        files[table] = {"columns": header, "required": list(cols),
                        "missing": [c for c in cols if c not in header]}
    if any(f["missing"] for f in files.values()):
        return {"files": files, "values": None}
    human_tids, types = set(), {}
    for r in csv_rows(tables / "target_dictionary.csv"):
        if r["organism"] == HUMAN:
            human_tids.add(r["tid"])
            types[r["tid"]] = r["target_type"]
    mech = list(csv_rows(tables / "drug_mechanism.csv"))
    human_mech = [m for m in mech if m["tid"] in human_tids]
    primary = [m for m in human_mech if types[m["tid"]] == PRIMARY_TYPE
               and m["direct_interaction"] == "1" and m["molecular_mechanism"] == "1"]
    component = [m for m in human_mech if types[m["tid"]] in COMPONENT_LEVEL_TYPES]
    used_tids = {m["tid"] for m in primary} | {m["tid"] for m in component}
    homologue = collections.Counter()
    comp_types = collections.Counter()
    comp_of = {r["component_id"]: r for r in csv_rows(tables / "component_sequences.csv")}
    for r in csv_rows(tables / "target_components.csv"):
        if r["tid"] in used_tids:
            homologue[r["homologue"]] += 1
            c = comp_of.get(r["component_id"])
            comp_types[(c.get("component_type", ""), c.get("db_source", "")) if c
                       else ("missing", "")] += 1
    indications = list(csv_rows(tables / "drug_indication.csv"))
    hierarchy_molregnos, self_parent, n_hier = set(), 0, 0
    for r in csv_rows(tables / "molecule_hierarchy.csv"):
        n_hier += 1
        hierarchy_molregnos.add(r["molregno"])
        self_parent += r["molregno"] == r["parent_molregno"]
    used_molregnos = {m["molregno"] for m in human_mech} | {i["molregno"] for i in indications}
    return {"files": files, "values": {
        "drug_mechanism.rows": len(mech),
        "drug_mechanism.human_rows_by_target_type": counter(types[m["tid"]] for m in human_mech),
        "drug_mechanism.primary_rule_rows": len(primary),
        "drug_mechanism.component_level_rows": len(component),
        "drug_mechanism.component_level_rows_by_flags": counter(
            f"direct_interaction={m['direct_interaction']},molecular_mechanism="
            f"{m['molecular_mechanism']}" for m in component),
        "drug_mechanism.empty_molregno": sum(not m["molregno"] for m in mech),
        "drug_mechanism.action_type_primary_and_component": counter(
            m["action_type"] for m in primary + component),
        "target_components.homologue_on_used_targets": counter(homologue.elements()),
        "component_sequences.type_and_source_on_used_targets": counter(
            f"{t}|{s}" for (t, s), n in comp_types.items() for _ in range(n)),
        "drug_indication.rows": len(indications),
        "drug_indication.max_phase_for_ind": counter(i["max_phase_for_ind"] for i in indications),
        "drug_indication.efo_id_prefix": counter(id_prefix(i["efo_id"]) for i in indications),
        "drug_indication.empty_molregno": sum(not i["molregno"] for i in indications),
        "molecule_hierarchy.rows": n_hier,
        "molecule_hierarchy.self_parent_rows": self_parent,
        "molecule_hierarchy.mechanism_or_indication_molregnos_without_row": len(
            {m for m in used_molregnos if m and m not in hierarchy_molregnos}),
    }}


def open_targets_report(ot: pathlib.Path) -> dict:
    files = {}
    for name, cols in OT_REQUIRED.items():
        present = parquet_columns(ot / f"{name}.parquet")
        files[name] = {"columns": present, "required": list(cols),
                       "missing": [c for c in cols if c not in present]}
    if any(f["missing"] for f in files.values()):
        return {"files": files, "values": None}
    status = collections.Counter()
    labels = collections.Counter()
    label_status = collections.Counter()
    drug_prefix, disease_prefix = collections.Counter(), collections.Counter()
    n_drugs, n_diseases = collections.Counter(), collections.Counter()
    qc, source, rtype, ids = (collections.Counter(), collections.Counter(), collections.Counter(),
                              collections.Counter())
    qc_values, type_status = collections.Counter(), collections.Counter()
    for r in parquet_rows(ot / "clinical_report.parquet",
                          ["id", "drugs", "diseases", "trialOverallStatus",
                           "trialStopReasonCategories", "source", "type", "qualityControls"]):
        ids[r["id"]] += 1
        status[r["trialOverallStatus"]] += 1
        for lab in r["trialStopReasonCategories"] or ():
            labels[lab] += 1
            label_status[f"{r['trialOverallStatus']}|{lab}"] += 1
        drugs, diseases = r["drugs"] or [], r["diseases"] or []
        n_drugs[min(len(drugs), 3)] += 1
        n_diseases[min(len(diseases), 3)] += 1
        for d in drugs:
            drug_prefix[re.match(r"[A-Za-z]*", d["drugId"] or "").group()] += 1
        for d in diseases:
            disease_prefix[id_prefix(d["diseaseId"])] += 1
        qc["flagged" if r["qualityControls"] else "none"] += 1
        for q in r["qualityControls"] or ():
            qc_values[q] += 1
        kind = "ClinicalTrials.gov" if r["source"] == "ClinicalTrials.gov" else "other_source"
        type_status[f"{r['type']}|{kind}|{r['trialOverallStatus']}"] += 1
        source[r["source"]] += 1
        rtype[r["type"]] += 1
    return {"files": files, "values": {
        "clinical_report.rows": sum(ids.values()),
        "clinical_report.duplicate_ids": sum(n > 1 for n in ids.values()),
        "clinical_report.trialOverallStatus": counter(status.elements()),
        "clinical_report.trialStopReasonCategories": counter(labels.elements()),
        "clinical_report.status_by_stop_label": counter(label_status.elements()),
        "clinical_report.drugs_per_report_capped_at_3": counter(n_drugs.elements()),
        "clinical_report.diseases_per_report_capped_at_3": counter(n_diseases.elements()),
        "clinical_report.drugId_prefix": counter(drug_prefix.elements()),
        "clinical_report.diseaseId_prefix": counter(disease_prefix.elements()),
        "clinical_report.qualityControls": counter(qc.elements()),
        "clinical_report.qualityControls_values": counter(qc_values.elements()),
        "clinical_report.type_by_source_kind_by_status": counter(type_status.elements()),
        "clinical_report.source": counter(source.elements()),
        "clinical_report.type": counter(rtype.elements()),
        "disease.rows": sum(1 for _ in parquet_rows(ot / "disease.parquet", ["id"])),
    }}


def registered_value_checks(chembl: dict, ot: dict) -> dict:
    """The value sets the registered rules name, against the files."""
    if chembl["values"] is None or ot["values"] is None:
        return {}
    v, c = ot["values"], chembl["values"]
    found_labels = set(v["clinical_report.trialStopReasonCategories"])
    statuses = set(v["clinical_report.trialOverallStatus"])
    types = set(c["drug_mechanism.human_rows_by_target_type"])
    labelled_statuses = {k.split("|")[0] for k in v["clinical_report.status_by_stop_label"]}
    return {
        "stop_labels_equal_registered_13": {
            "ok": found_labels == set(STOP_LABELS),
            "in_file_not_registered": sorted(found_labels - set(STOP_LABELS)),
            "registered_not_in_file": sorted(set(STOP_LABELS) - found_labels)},
        "active_and_suspended_statuses_present": {
            "ok": (set(ACTIVE_STATUSES) | {SUSPENDED}) <= statuses,
            "missing": sorted((set(ACTIVE_STATUSES) | {SUSPENDED}) - statuses)},
        "target_types_present": {
            "ok": ({PRIMARY_TYPE} | set(COMPONENT_LEVEL_TYPES)) <= types,
            "missing": sorted(({PRIMARY_TYPE} | set(COMPONENT_LEVEL_TYPES)) - types)},
        "primary_rule_rows_equal_registered_4477": {
            "ok": c["drug_mechanism.primary_rule_rows"] == 4477,
            "found": c["drug_mechanism.primary_rule_rows"]},
        "component_level_rows_equal_registered_1248": {
            "ok": c["drug_mechanism.component_level_rows"] == 1248,
            "found": c["drug_mechanism.component_level_rows"]},
        "report_ids_unique": {"ok": v["clinical_report.duplicate_ids"] == 0},
        "statuses_carrying_stop_labels": sorted(labelled_statuses),
    }


def run(chembl_tables: pathlib.Path, open_targets: pathlib.Path) -> dict:
    chembl = chembl_report(chembl_tables)
    ot = open_targets_report(open_targets)
    checks = registered_value_checks(chembl, ot)
    missing = {name: f["missing"] for part in (chembl, ot) for name, f in part["files"].items()
               if f["missing"]}
    return {
        "checked_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "inputs": "resource files only; no claim, pair or registry record read",
        "chembl_tables": str(chembl_tables), "open_targets": str(open_targets),
        "ok": not missing and all(c["ok"] for c in checks.values() if isinstance(c, dict)),
        "missing_required_columns": missing,
        "registered_value_checks": checks,
        "chembl": chembl, "open_targets": ot,
    }
