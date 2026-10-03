# /// script
# requires-python = ">=3.12"
# dependencies = ["openpyxl==3.1.5", "pypdf==5.9.0"]
# ///
"""Tables derived from published supplementary files, for the assay lists whose analysed
proteins are not one column of one sheet. Resource files of dataset source papers only: no
claim, pair or registry record is read. Run on Modal
(scripts/modal_biology_joins.py::derive_lists); the tables are committed under
verification/published_lists_derived/ with one metadata file, and read by
scripts/assay_backgrounds.py through verification/platform_list_sources.csv.

    improve_folkersen2017_S3.csv        Folkersen et al. 2017 S3 Table (a PDF): gene symbol and
                                        the `Included` cell of each of the 92 proteins of the
                                        ProSeek CVD array I
    nsphs_enroth2014_analysed.csv       Enroth et al. 2014: the 92 analytes of Supplementary
                                        Data 1, each marked analysed when it is one of the
                                        phenotypes of Supplementary Data 2
    scallop_koprulu2026_S5_targets.csv  Koprulu et al. 2026 Table S5: the protein targets of the
                                        meta-analysis, each with the UniProt cell of the UKB-PPP
                                        1.5k protein map row that carries its Olink Explore
                                        identifier
    jhs_katz2022_soma13k_reagents.csv   Katz et al. 2022 (Sci Adv) Table S2: one row per
                                        SomaScan 1.3k reagent and UniProt cell, with the target,
                                        the number of table rows and the number of UniProt
                                        cells the reagent has

Each table is checked against the count its source paper states (EXPECTED); a table whose count
differs is not written.

The S3 Table is read from the text of the PDF, line by line. A row starts on a line that
begins with a gene symbol (capitals, digits and hyphens) followed by two or more spaces and the
protein name; its `Included` cell is the first `yes` or `no` on that line or the lines after
it. A row with no such cell before the next row starts is refused.
"""

import collections
import csv
import hashlib
import io
import json
import pathlib
import re

import openpyxl
from pypdf import PdfReader


class DeriveError(Exception):
    """A published file does not have the rows or the count its paper states."""


# Counts stated by the source papers (the pinned sentences are named in
# verification/platform_assay_attachments.csv).
EXPECTED = {
    "improve": {"rows": 92, "included": 83},
    "nsphs": {"analytes": 92, "analysed": 77},
    "scallop": {"targets": 1161},
    "jhs": {"reagents": 1301, "uniprot_cells": 1297},
}
IMPROVE_ROW_START = re.compile(r"([A-Z][A-Z0-9-]{1,9})\s{2,}\S")
INCLUDED_CELL = re.compile(r"(?<![A-Za-z])(yes|no)(?![A-Za-z])")
UNICODE_HYPHEN = "\u2010"
NSPHS_NAME_COLUMNS = ("Name", "OlinkShortName", "HGNC")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pdf_text(path: pathlib.Path) -> str:
    reader = PdfReader(io.BytesIO(path.read_bytes()))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def sheet_rows(path: pathlib.Path, sheet: str | None = None) -> list[list[str]]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet] if sheet else wb[wb.sheetnames[0]]
    return [["" if c is None else str(c).strip() for c in r]
            for r in ws.iter_rows(values_only=True)]


def records(rows: list[list[str]], column: str) -> list[dict[str, str]]:
    """The data rows of a sheet as dictionaries; the header is the first row holding `column`."""
    for i, row in enumerate(rows):
        if column in row:
            return [dict(zip(row, r)) for r in rows[i + 1:] if any(r)]
    raise DeriveError(f"no row holds the column {column!r}")


def improve_s3(text: str, rows: int = EXPECTED["improve"]["rows"],
               included: int = EXPECTED["improve"]["included"]) -> list[dict[str, str]]:
    """(gene, included) of every row of the S3 Table, from the text of its PDF."""
    text = text.replace(UNICODE_HYPHEN, "-")
    found: list[tuple[str, str]] = []
    gene: str | None = None
    for line in text.splitlines():
        line = line.strip()
        start = IMPROVE_ROW_START.match(line)
        if start:
            if gene is not None:
                raise DeriveError(f"S3 Table: no Included cell for {gene}")
            gene, line = start.group(1), line[start.end(1):]
        cell = INCLUDED_CELL.search(line) if gene is not None else None
        if cell:
            found.append((gene, cell.group(1)))
            gene = None
    if gene is not None:
        raise DeriveError(f"S3 Table: no Included cell for {gene}")
    genes = [g for g, _ in found]
    if len(set(genes)) != len(genes):
        raise DeriveError(f"S3 Table: a gene symbol read twice: "
                          f"{sorted(g for g, n in collections.Counter(genes).items() if n > 1)}")
    cells = len(INCLUDED_CELL.findall(text))
    yes = sum(v == "yes" for _, v in found)
    if (len(found), yes, cells) != (rows, included, rows):
        raise DeriveError(f"S3 Table: {len(found)} rows, {yes} included, {cells} Included "
                          f"cells; the paper states {included} of {rows}")
    return [{"gene": g, "included": v} for g, v in found]


def nsphs_analysed(analytes: list[dict[str, str]], phenotypes: list[str],
                   n_analytes: int = EXPECTED["nsphs"]["analytes"],
                   n_analysed: int = EXPECTED["nsphs"]["analysed"]) -> list[dict[str, str]]:
    """The analytes of Supplementary Data 1, marked analysed when a phenotype of Supplementary
    Data 2 names them. A phenotype names an analyte when it equals its `Name`,
    `OlinkShortName` or `HGNC` cell; it must name exactly one."""
    matched: dict[int, str] = {}
    for phenotype in phenotypes:
        hits = [i for i, a in enumerate(analytes)
                if phenotype in {a.get(c, "") for c in NSPHS_NAME_COLUMNS}]
        if len(hits) != 1:
            raise DeriveError(f"phenotype {phenotype!r} names {len(hits)} analytes")
        if hits[0] in matched:
            raise DeriveError(f"phenotypes {matched[hits[0]]!r} and {phenotype!r} name one "
                              "analyte")
        matched[hits[0]] = phenotype
    if (len(analytes), len(matched)) != (n_analytes, n_analysed):
        raise DeriveError(f"{len(matched)} of {len(analytes)} analytes analysed; the paper "
                          f"states {n_analysed} of {n_analytes}")
    return [{"name": a["Name"], "uniprot": a["UniprotID"], "phenotype": matched.get(i, ""),
             "analysed": "yes" if i in matched else "no"} for i, a in enumerate(analytes)]


def scallop_targets(phenos: list[str], ukb_map: list[dict[str, str]],
                    n_targets: int = EXPECTED["scallop"]["targets"]) -> list[dict[str, str]]:
    """The targets of Table S5 (`<Target 96 Olink id>_<Explore Olink id>`), each with the
    UniProt cell of the UKB-PPP 1.5k protein map rows that carry its Explore identifier. The
    map can list an Olink identifier on several rows; a target whose rows disagree on the
    UniProt cell raises."""
    by_id: dict[str, set[str]] = collections.defaultdict(set)
    for r in ukb_map:
        by_id[r["OlinkID"]].add(r["UniProt"])
    if len(set(phenos)) != len(phenos) or len(phenos) != n_targets:
        raise DeriveError(f"Table S5: {len(phenos)} targets ({len(set(phenos))} distinct); the "
                          f"paper states {n_targets}")
    out = []
    for pheno in phenos:
        explore = pheno.rsplit("_", 1)[-1]
        if explore not in by_id:
            raise DeriveError(f"{pheno}: {explore} is not in the UKB-PPP protein map")
        if len(by_id[explore]) != 1:
            raise DeriveError(f"{pheno}: the UKB-PPP protein map gives {explore} the UniProt "
                              f"cells {sorted(by_id[explore])}")
        out.append({"pheno": pheno, "explore_olink_id": explore,
                    "uniprot": next(iter(by_id[explore]))})
    return out


def jhs_reagents(rows: list[dict[str, str]], n_reagents: int = EXPECTED["jhs"]["reagents"],
                 n_uniprot: int = EXPECTED["jhs"]["uniprot_cells"]) -> list[dict[str, str]]:
    """One row per SomaScan 1.3k reagent and UniProt cell of Table S2. A reagent paired with
    several Olink reagents has several table rows, and a reagent for a multi-protein target has
    a row per component; both are kept in the table (`table_rows`,
    `uniprot_cells_of_reagent`)."""
    n_rows: collections.Counter = collections.Counter()
    first: dict[tuple[str, str], dict[str, str]] = {}
    for r in rows:
        if not r["SomamerId"]:
            continue
        key = (r["SomamerId"], r["UniProt.x"])
        n_rows[key] += 1
        first.setdefault(key, {"somamer_id": r["SomamerId"], "soma_id": r["SomaId"],
                               "target": r["Soma Target"], "uniprot": r["UniProt.x"]})
    reagents = collections.Counter(s for s, _ in first)
    cells = {u for _, u in first if u}
    if (len(reagents), len(cells)) != (n_reagents, n_uniprot):
        raise DeriveError(f"Table S2: {len(reagents)} reagents, {len(cells)} UniProt cells; the "
                          f"papers state {n_reagents} and {n_uniprot}")
    return [{**first[k], "table_rows": str(n_rows[k]),
             "uniprot_cells_of_reagent": str(reagents[k[0]])} for k in sorted(first)]


def write_table(path: pathlib.Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def run(published: pathlib.Path, assays: pathlib.Path, out: pathlib.Path) -> dict:
    """Write the four tables and their metadata to `out`. `published` holds the fetched
    supplementary files and `assays` the pinned assay files (both on the Modal volume)."""
    out.mkdir(parents=True, exist_ok=True)
    improve = improve_s3(pdf_text(published / "folkersen2017_S3.pdf"))
    analytes = records(sheet_rows(published / "enroth2014_SD1.xlsx", "Analytes"), "UniprotID")
    phenotypes = [r["Phenotype"] for r in records(
        sheet_rows(published / "enroth2014_SD2.xlsx", "Supplementary Table 2"), "Phenotype")
        if r["Phenotype"]]
    nsphs = nsphs_analysed(analytes, phenotypes)
    s5 = sheet_rows(published / "koprulu2026_S5.xlsx")
    with (assays / "olink_protein_map_1.5k_v1.tsv").open(newline="") as f:
        ukb_map = list(csv.DictReader(f, delimiter="\t"))
    scallop = scallop_targets([r["pheno"] for r in records(s5, "pheno") if r["pheno"]], ukb_map)
    jhs = jhs_reagents(records(sheet_rows(published / "katz2022sciadv_tables_S1_S6.xlsx",
                                          "Table S2"), "SomamerId"))
    tables = {"improve_folkersen2017_S3.csv": improve, "nsphs_enroth2014_analysed.csv": nsphs,
              "scallop_koprulu2026_S5_targets.csv": scallop,
              "jhs_katz2022_soma13k_reagents.csv": jhs}
    for name, rows in tables.items():
        write_table(out / name, rows)
    sources = {"improve_folkersen2017_S3.csv": ["folkersen2017_S3.pdf"],
               "nsphs_enroth2014_analysed.csv": ["enroth2014_SD1.xlsx", "enroth2014_SD2.xlsx"],
               "scallop_koprulu2026_S5_targets.csv": ["koprulu2026_S5.xlsx"],
               "jhs_katz2022_soma13k_reagents.csv": ["katz2022sciadv_tables_S1_S6.xlsx"]}
    meta = {
        "inputs": "published supplementary files and the pinned UKB-PPP 1.5k protein map; no "
                  "claim, pair or registry record read",
        "expected_counts_from_the_source_papers": EXPECTED,
        "tables": {name: {
            "rows": len(rows), "sha256": sha256(out / name),
            "source_files": {f: sha256(published / f) for f in sources[name]}}
            for name, rows in tables.items()},
        "improve_not_included": sorted(r["gene"] for r in improve if r["included"] == "no"),
        "nsphs_not_analysed": sorted(r["name"] for r in nsphs if r["analysed"] == "no"),
        "scallop_distinct_uniprot_cells": len({r["uniprot"] for r in scallop}),
        "scallop_targets_sharing_a_uniprot_cell": len(scallop) - len(
            {r["uniprot"] for r in scallop}),
        "ukb_protein_map_sha256": sha256(assays / "olink_protein_map_1.5k_v1.tsv"),
        "jhs_reagents": len({r["somamer_id"] for r in jhs}),
        "jhs_uniprot_cells": len({r["uniprot"] for r in jhs if r["uniprot"]}),
        "jhs_reagents_with_several_uniprot_cells": len(
            {r["somamer_id"] for r in jhs if r["uniprot_cells_of_reagent"] != "1"}),
        "jhs_uniprot_cells_with_several_reagents": sum(
            n > 1 for n in collections.Counter(r["uniprot"] for r in jhs).values()),
    }
    (out / "published_lists_derived.meta.json").write_text(json.dumps(meta, indent=1))
    return meta
