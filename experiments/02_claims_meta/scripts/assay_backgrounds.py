"""Per-platform assay lists mapped to UniProt accessions, from the pinned assay files.

Each list is the set of UniProt accessions printed in the accession column of its pinned file
(RELEASES.md), kept when the accession is an entry of the pinned UniProtKB human reviewed file
(the identifier a registry pair carries). A cell naming several proteins (a complex or a
multi-protein analyte, written with spaces, `|`, `_`, `,` or `;`) contributes every accession in
it. An Olink Target 96 panel list is the rows of the Target 96 file whose `Panel` cell names
that panel.

    olink_explore_3072     UKB-PPP protein map (Synapse syn52364558 v1), column `UniProt`
    olink_explore_1536     UKB-PPP protein map (Synapse syn51396732 v1), column `UniProt`
    olink_target_96        pQTLdata 0.6 Olink Target 96, column `UniProt`
    olink_target_96:<P>    the same, rows of panel <P>
    somascan_v4            Eldjarn et al. 2023 ST2, column `uniprot`
    somascan_1.3k          the same, rows with `on_1.2k` True
    somascan_160410        pQTLdata 0.6 SomaScan160410 (INTERVAL, Sun et al. 2018), `UniProt`
    somascan_v4.1          pQTLdata 0.6 SomaScanV4.1, column `UniProt.ID`

Published lists. An assay that no pinned package holds (a custom array, a discontinued panel,
a non-commercial method, a stated subset) takes its list from the supplementary table of the
dataset's own source paper (verification/platform_list_sources.csv, scripts/
platform_list_sources.py; the files are on the Modal volume with their sha256):

    fenland_covid_179            Pietzner et al. 2020 Supplementary Data 1, SOMAmer targets
    olink_target_96:CVD I        Folkersen et al. 2020 Supplementary Table 1, rows of panel CVD I
    somascan_ages_custom         Gudjonsson et al. 2022 Supplementary Data 6 (gene symbols)
    somascan_v3.2_kora           Suhre et al. 2017 Supplementary Dataset 2
    fhs_luminex_71               Yao et al. 2018 Supplementary Data 1 (gene symbols)
    zheng2020_instrumented_1699  Zheng et al. 2020 Supplementary Table 1
    olink_proseek_oncology_I     Enroth et al. 2014 Supplementary Data 1
    gnhs_swath_ms_304            Xu et al. 2023 Supplementary Data 2, protein-level rows

Analysed lists. Where a source marks the proteins that entered its pQTL analysis, the list of
those proteins is built beside the whole panel, from the paper's own table or from a table
derived from it (scripts/derive_published_lists.py, verification/published_lists_derived/):

    olink_cvd1_improve_analysed       Folkersen et al. 2017 S3 Table, rows with Included = yes
    olink_manolis_gilly2020_analysed  Gilly et al. 2020 Supplementary Data 7, rows not excluded
    olink_helic_png2021               Png et al. 2021 Supplementary Data 8 (all analysed)
    olink_oncology_I_nsphs_analysed   Enroth et al. 2014 Supplementary Data 1, the analytes of
                                      the 77 phenotypes of Supplementary Data 2
    scallop_koprulu2026_analysed      Koprulu et al. 2026 Table S5, the 1,161 targets, through
                                      the Olink identifiers of the UKB-PPP 1.5k protein map
    somascan_1.3k_jhs_katz2022        Katz et al. 2022 (Sci Adv) Table S2, the 1,301 SomaScan
                                      1.3k reagents measured in the Jackson Heart Study

Which list a dictionary row takes, and at which level of the registered hierarchy (analysed,
assayed, platform, unavailable), is in verification/platform_assay_attachments.csv. A column of
gene symbols enters through the verifier's protein tiers (approved symbol; approved
name; alias and previous symbols; first tier with a hit) and the registered HGNC-to-UniProt
step, every accession of every symbol in the cell; symbols that map to no reviewed accession
are listed in the provenance.

The lists are built on Modal (scripts/modal_biology_joins.py::resource_tables) and committed as
verification/platform_assay_lists.csv (`list_id`, `accession`) with their provenance in
verification/platform_assay_lists.meta.json.
"""

import collections
import csv
import hashlib
import pathlib
import re
from collections.abc import Callable

import openpyxl

from platform_list_sources import DERIVED, ListSource, csv_rows, id_cells, is_derived

ACCESSION = re.compile(r"(?<![A-Z0-9])(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|"
                       r"[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})(?![A-Z0-9])")
SOURCES = {
    "olink_explore_3072": ("olink_protein_map_3k_v1.tsv", "UniProt", 0),
    "olink_explore_1536": ("olink_protein_map_1.5k_v1.tsv", "UniProt", 0),
    "olink_target_96": ("pQTLdata_0.6_Olink_Target_96.tsv", "UniProt", 0),
    "somascan_v4": ("eldjarn2023_ST2_soma_assays.tsv", "uniprot", 2),
    "somascan_160410": ("pQTLdata_0.6_SomaScan160410.tsv", "UniProt", 0),
    "somascan_v4.1": ("pQTLdata_0.6_SomaScanV4.1.tsv", "UniProt.ID", 0),
}
PANEL_COLUMN = "Panel"
SUBSET_1K = ("somascan_1.3k", "somascan_v4", "on_1.2k", "True")


class AssayListError(Exception):
    """A pinned assay file is missing a column or a committed list file is inconsistent."""


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path: pathlib.Path, skip: int) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        for _ in range(skip):
            next(f)
        return list(csv.DictReader(f, delimiter="\t"))


def accessions(cell: str | None) -> set[str]:
    return set(ACCESSION.findall(cell or ""))


def build_lists(assay_dir: pathlib.Path, reviewed: frozenset[str]
                ) -> tuple[dict[str, frozenset[str]], dict]:
    lists: dict[str, frozenset[str]] = {}
    meta: dict = {}

    def add(list_id: str, rows: list[dict[str, str]], column: str, source: str) -> None:
        if rows and column not in rows[0]:
            raise AssayListError(f"{source}: no column {column!r}")
        printed = set().union(*(accessions(r[column]) for r in rows)) if rows else set()
        lists[list_id] = frozenset(printed & reviewed)
        meta[list_id] = {"source_file": source, "column": column, "rows": len(rows),
                         "rows_without_accession": sum(not accessions(r[column]) for r in rows),
                         "accessions_printed": len(printed),
                         "accessions_in_reviewed_uniprot": len(lists[list_id]),
                         "accessions_not_in_reviewed_uniprot": sorted(printed - reviewed)}

    for list_id, (name, column, skip) in SOURCES.items():
        path = assay_dir / name
        rows = read_rows(path, skip)
        add(list_id, rows, column, name)
        meta[list_id]["source_sha256"] = sha256(path)
        if list_id == "olink_target_96":
            panels = sorted({p.strip() for r in rows for p in r[PANEL_COLUMN].split(",")})
            for panel in panels:
                add(f"{list_id}:{panel}",
                    [r for r in rows if panel in {p.strip() for p in r[PANEL_COLUMN].split(",")}],
                    column, name)
                meta[f"{list_id}:{panel}"]["source_sha256"] = meta[list_id]["source_sha256"]
        if list_id == SUBSET_1K[1]:
            sub_id, _, flag, value = SUBSET_1K
            add(sub_id, [r for r in rows if r[flag] == value], column, name)
            meta[sub_id]["source_sha256"] = meta[list_id]["source_sha256"]
            meta[sub_id]["row_filter"] = f"{flag} == {value}"
    return lists, meta


SYMBOL_SEPARATOR = re.compile(r"[\s|,;/]+")


def published_list(cells: list[str], source: ListSource, reviewed: frozenset[str],
                   symbol_accessions: Callable[[str], frozenset[str]]
                   ) -> tuple[frozenset[str], dict]:
    """(the reviewed accessions of a published list's identifier cells, its provenance)."""
    filled = [c for c in cells if c]
    if source.id_kind == "uniprot":
        printed = set().union(*(accessions(c) for c in filled)) if filled else set()
        unmapped = sorted(c for c in filled if not accessions(c) & reviewed)
    else:
        symbols = sorted({t for c in filled for t in SYMBOL_SEPARATOR.split(c) if t})
        by_symbol = {t: symbol_accessions(t) for t in symbols}
        printed = set().union(*by_symbol.values()) if by_symbol else set()
        unmapped = sorted(t for t, a in by_symbol.items() if not a & reviewed)
    kept = frozenset(printed & reviewed)
    return kept, {"source": source.source, "source_file": source.file,
                  "source_sha256": source.sha256, "sheet": source.sheet or "first sheet",
                  "column": source.id_column, "id_kind": source.id_kind,
                  "row_filter": f"{source.filter_column} == {source.filter_value}"
                  if source.filter_column else None,
                  "rows": len(cells), "rows_without_identifier": len(cells) - len(filled),
                  "distinct_identifier_cells": len(set(filled)),
                  "accessions_printed": len(printed),
                  "accessions_in_reviewed_uniprot": len(kept),
                  "cells_or_symbols_without_reviewed_accession": unmapped}


def build_published(folder: pathlib.Path, sources: list[ListSource], reviewed: frozenset[str],
                    symbol_accessions: Callable[[str], frozenset[str]],
                    derived: pathlib.Path = DERIVED) -> tuple[dict[str, frozenset[str]], dict]:
    """`folder` holds the published files (the Modal volume); `derived` the committed tables
    derived from published files."""
    lists: dict[str, frozenset[str]] = {}
    meta: dict = {}
    for source in sources:
        path = (derived if is_derived(source) else folder) / source.file
        if sha256(path) != source.sha256:
            raise AssayListError(f"{path.name}: sha256 differs from the source table")
        if is_derived(source):
            rows = csv_rows(path)
        else:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            rows = list(wb[source.sheet or wb.sheetnames[0]].iter_rows(values_only=True))
        lists[source.list_id], meta[source.list_id] = published_list(
            id_cells(rows, source), source, reviewed, symbol_accessions)
    return lists, meta


def write_lists(lists: dict[str, frozenset[str]], path: pathlib.Path) -> None:
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["list_id", "accession"])
        for list_id in sorted(lists):
            w.writerows((list_id, a) for a in sorted(lists[list_id]))


def load_lists(path: pathlib.Path) -> dict[str, frozenset[str]]:
    out: dict[str, set[str]] = collections.defaultdict(set)
    with path.open(newline="") as f:
        for r in csv.DictReader(f):
            out[r["list_id"]].add(r["accession"])
    return {k: frozenset(v) for k, v in out.items()}
