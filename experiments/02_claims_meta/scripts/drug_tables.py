"""Build the `DrugIndex` of scripts/drug_joins.py from the pinned ChEMBL 37 table CSVs and the
Open Targets 26.09 `clinical_report` and `disease` rows.

The index is independent of the registry: it holds every human drug mechanism the registered
rules use, the indications of those drugs and the clinical reports naming them, with every
molecule collapsed to its parent. ChEMBL tables are read as streamed CSV rows; Open Targets rows
arrive as dictionaries (the Modal wrapper reads the parquet files), so this module needs the
standard library and pydantic only.

    drug_mechanism       mec_id, molregno, tid, action_type, direct_interaction,
                         molecular_mechanism
    target_dictionary    tid, target_type, organism
    target_components    tid, component_id, homologue
    component_sequences  component_id, accession
    molecule_hierarchy   molregno, parent_molregno
    molecule_dictionary  molregno, chembl_id
    drug_indication      molregno, max_phase_for_ind, efo_id
    clinical_report      id, drugs.drugId, diseases.diseaseId, trialOverallStatus,
                         trialStopReasonCategories, qualityControls, source, type
    disease              id

A molecule with no `molecule_hierarchy` row, or with an empty `parent_molregno`, is its own
parent, counted in the provenance. Mechanism and indication rows with no `molregno` are counted
and dropped. Only reports of `type` INDICATION are read: a SAFETY report (a drug warning) lists
adverse effects under `diseases`, not indications, and is counted and dropped. A clinical report
is kept when at least one of its drugs collapses to a parent that has a mechanism in the index.
The kept reports are counted by source and by quality-control flag (the primary joins read the
unflagged reports only; scripts/drug_joins.py).
"""

import collections
import csv
import pathlib
from collections.abc import Iterable, Iterator

from drug_joins import DrugIndex, Indication, Mechanism, Trial

HUMAN = "Homo sapiens"
PRIMARY_TYPE = "SINGLE PROTEIN"
COMPONENT_LEVEL_TYPES = ("PROTEIN COMPLEX", "PROTEIN COMPLEX GROUP", "PROTEIN FAMILY",
                         "SELECTIVITY GROUP", "CHIMERIC PROTEIN", "PROTEIN-PROTEIN INTERACTION")
CHEMBL_REQUIRED = {
    "drug_mechanism": ("mec_id", "molregno", "tid", "action_type", "direct_interaction",
                       "molecular_mechanism"),
    "target_dictionary": ("tid", "target_type", "organism"),
    "target_components": ("tid", "component_id", "homologue"),
    "component_sequences": ("component_id", "accession"),
    "molecule_hierarchy": ("molregno", "parent_molregno"),
    "molecule_dictionary": ("molregno", "chembl_id"),
    "drug_indication": ("molregno", "max_phase_for_ind", "efo_id"),
}
OT_REQUIRED = {
    "clinical_report": ("id", "drugs.drugId", "diseases.diseaseId", "trialOverallStatus",
                        "trialStopReasonCategories", "qualityControls", "source", "type"),
    "disease": ("id",),
}
OT_REPORT_COLUMNS = ["id", "drugs", "diseases", "trialOverallStatus",
                     "trialStopReasonCategories", "qualityControls", "source", "type"]
INDICATION_REPORT = "INDICATION"
CSV_FIELD_LIMIT = 1 << 24


def rows(path: pathlib.Path) -> Iterator[dict[str, str]]:
    csv.field_size_limit(CSV_FIELD_LIMIT)
    with path.open(newline="") as f:
        yield from csv.DictReader(f)


def normalize_id(raw: str) -> str:
    """`EFO_0000685` (Open Targets) and `EFO:0000685` (ChEMBL, the ontology files) are one
    identifier, written PREFIX:N."""
    raw = raw.strip()
    return raw if ":" in raw else raw.replace("_", ":", 1)


def id_prefix(raw: str | None) -> str:
    if not raw:
        return ""
    return normalize_id(raw).split(":", 1)[0]


def flag(value: str) -> int | None:
    return int(float(value)) if value.strip() else None


def phase_value(value: str) -> float | None:
    return float(value) if value.strip() else None


class ParentMap:
    """molregno -> parent molregno through `molecule_hierarchy`."""

    def __init__(self, hierarchy: pathlib.Path) -> None:
        self.parent: dict[int, int] = {}
        self.empty_parent = 0
        for r in rows(hierarchy):
            if r["parent_molregno"].strip():
                self.parent[int(r["molregno"])] = int(r["parent_molregno"])
            else:
                self.empty_parent += 1
        self.no_row: set[int] = set()

    def of(self, molregno: int) -> int:
        if molregno not in self.parent:
            self.no_row.add(molregno)
            return molregno
        return self.parent[molregno]


def load_mechanisms(tables: pathlib.Path, parents: ParentMap) -> tuple[list[Mechanism], dict]:
    target_type = {int(r["tid"]): r["target_type"] for r in rows(tables / "target_dictionary.csv")
                   if r["organism"] == HUMAN
                   and r["target_type"] in (PRIMARY_TYPE, *COMPONENT_LEVEL_TYPES)}
    accession = {int(r["component_id"]): r["accession"].strip()
                 for r in rows(tables / "component_sequences.csv") if r["accession"].strip()}
    components: dict[int, list[tuple[str, int | None]]] = collections.defaultdict(list)
    for r in rows(tables / "target_components.csv"):
        tid, cid = int(r["tid"]), int(r["component_id"])
        if tid in target_type and cid in accession:
            components[tid].append((accession[cid], flag(r["homologue"])))
    out: list[Mechanism] = []
    counts: collections.Counter = collections.Counter()
    for r in rows(tables / "drug_mechanism.csv"):
        counts["drug_mechanism_rows"] += 1
        if not r["tid"].strip() or int(r["tid"]) not in target_type:
            counts["rows_not_on_a_used_human_target"] += 1
            continue
        tid = int(r["tid"])
        direct, molecular = flag(r["direct_interaction"]), flag(r["molecular_mechanism"])
        if target_type[tid] == PRIMARY_TYPE:
            if direct != 1 or molecular != 1:
                counts["single_protein_rows_failing_direct_or_molecular"] += 1
                continue
            level = "single_protein"
        else:
            level = "component_level_mapping"
        if not r["molregno"].strip():
            counts["rows_without_molregno"] += 1
            continue
        if not components.get(tid):
            counts["rows_on_target_without_component_accession"] += 1
            continue
        counts[f"rows_{level}"] += 1
        molregno = int(r["molregno"])
        for acc, homologue in components[tid]:
            out.append(Mechanism(
                mec_id=int(r["mec_id"]), molregno=molregno, parent_molregno=parents.of(molregno),
                accession=acc, tid=tid, target_type=target_type[tid], level=level,
                action_type=r["action_type"].strip() or None, direct_interaction=direct,
                molecular_mechanism=molecular, homologue=homologue))
    return out, dict(counts)


def load_indications(tables: pathlib.Path, parents: ParentMap, drug_parents: set[int]
                     ) -> tuple[list[Indication], set[str], dict]:
    """The indications of the index's drugs, one per parent and identifier with the highest
    phase among the parent's forms; and every indication identifier in the table."""
    best: dict[tuple[int, str | None], float | None] = {}
    all_ids: set[str] = set()
    counts: collections.Counter = collections.Counter()
    for r in rows(tables / "drug_indication.csv"):
        counts["drug_indication_rows"] += 1
        ind = normalize_id(r["efo_id"]) if r["efo_id"].strip() else None
        if ind is not None:
            all_ids.add(ind)
        if not r["molregno"].strip():
            counts["rows_without_molregno"] += 1
            continue
        parent = parents.of(int(r["molregno"]))
        if parent not in drug_parents:
            continue
        counts["rows_of_index_drugs"] += 1
        counts["rows_of_index_drugs_without_efo_id"] += ind is None
        key, phase = (parent, ind), phase_value(r["max_phase_for_ind"])
        if key not in best or (phase is not None and (best[key] is None or phase > best[key])):
            best[key] = phase
    out = [Indication(parent_molregno=p, indication_id=i, max_phase=ph)
           for (p, i), ph in sorted(best.items(), key=lambda kv: (kv[0][0], kv[0][1] or ""))]
    return out, all_ids, dict(counts)


def load_chembl_ids(tables: pathlib.Path, wanted: set[str]) -> dict[str, int]:
    """chembl_id -> molregno for the identifiers in `wanted` (`molecule_dictionary`)."""
    return {r["chembl_id"]: int(r["molregno"]) for r in rows(tables / "molecule_dictionary.csv")
            if r["chembl_id"] in wanted}


def report_drug_ids(report: dict) -> list[str]:
    return sorted({d["drugId"] for d in report["drugs"] or () if d.get("drugId")})


def load_trials(reports: Iterable[dict], molregno_of: dict[str, int], parents: ParentMap,
                drug_parents: set[int]) -> tuple[list[Trial], set[str], dict]:
    out: list[Trial] = []
    all_ids: set[str] = set()
    counts: collections.Counter = collections.Counter()
    by_source: collections.Counter = collections.Counter()
    by_flag: collections.Counter = collections.Counter()
    flagged_by_source: collections.Counter = collections.Counter()
    seen: set[str] = set()
    for r in reports:
        counts["clinical_report_rows"] += 1
        if r["id"] in seen:
            raise ValueError(f"clinical_report id {r['id']} occurs more than once")
        seen.add(r["id"])
        if r["type"] != INDICATION_REPORT:
            counts["reports_not_type_indication"] += 1
            continue
        diseases = sorted({normalize_id(d["diseaseId"]) for d in r["diseases"] or ()
                           if d.get("diseaseId")})
        all_ids.update(diseases)
        drug_ids = report_drug_ids(r)
        counts["report_drug_ids_not_in_molecule_dictionary"] += sum(
            d not in molregno_of for d in drug_ids)
        mapped = sorted({parents.of(molregno_of[d]) for d in drug_ids if d in molregno_of}
                        & drug_parents)
        if not mapped:
            continue
        counts["reports_kept"] += 1
        flags = sorted(set(r["qualityControls"] or ()))
        by_source[str(r["source"])] += 1
        by_flag.update(flags)
        flagged_by_source[str(r["source"])] += bool(flags)
        out.append(Trial(
            report_id=r["id"], n_drugs=len(r["drugs"] or ()),
            parent_molregnos=tuple(mapped), disease_ids=tuple(diseases),
            status=r["trialOverallStatus"],
            stop_labels=tuple(sorted(set(r["trialStopReasonCategories"] or ()))),
            quality_controls=tuple(sorted(set(r["qualityControls"] or ()))),
            source=r["source"],
            report_type=r["type"]))
    kept = {"reports_kept": counts["reports_kept"],
            "reports_kept_with_a_quality_control_flag": sum(flagged_by_source.values()),
            "reports_kept_not_trials": sum(t.status is None for t in out),
            "by_source": dict(sorted(by_source.items())),
            "flagged_by_source": {k: v for k, v in sorted(flagged_by_source.items()) if v},
            "by_flag": dict(sorted(by_flag.items()))}
    return out, all_ids, {**counts, "kept_reports_by_flag_and_source": kept}


def build_index(tables: pathlib.Path, reports: Iterable[dict], disease_ids: Iterable[str],
                wanted_chembl_ids: set[str], provenance: dict) -> DrugIndex:
    """`reports` is iterated once; `wanted_chembl_ids` is every `drugs.drugId` in the reports
    (a first pass by the caller), so `molecule_dictionary` is streamed and only those kept."""
    parents = ParentMap(tables / "molecule_hierarchy.csv")
    mechanisms, mech_counts = load_mechanisms(tables, parents)
    drug_parents = {m.parent_molregno for m in mechanisms}
    indications, ind_ids, ind_counts = load_indications(tables, parents, drug_parents)
    molregno_of = load_chembl_ids(tables, wanted_chembl_ids)
    trials, trial_ids, trial_counts = load_trials(reports, molregno_of, parents, drug_parents)
    resource_ids = sorted(ind_ids | trial_ids | {normalize_id(d) for d in disease_ids})
    return DrugIndex(
        mechanisms=mechanisms, indications=indications, trials=trials,
        resource_disease_ids=resource_ids,
        provenance={**provenance, "mechanisms": mech_counts, "indications": ind_counts,
                    "trials": {k: v for k, v in trial_counts.items()
                               if k != "kept_reports_by_flag_and_source"},
                    "kept_reports_by_flag_and_source":
                        trial_counts["kept_reports_by_flag_and_source"],
                    "hierarchy_rows_with_empty_parent": parents.empty_parent,
                    "molecules_without_hierarchy_row": len(parents.no_row),
                    "index_parent_drugs": len(drug_parents),
                    "index_accessions": len({m.accession for m in mechanisms})})
