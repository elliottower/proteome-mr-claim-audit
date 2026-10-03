"""The pleiotropic-locus list: the close genes of Eldjarn et al. 2023 Supplementary Table ST36.

Source: the Supplementary Tables workbook of Eldjarn et al. 2023 (Nature,
10.1038/s41586-023-06563-x; `eldjarn2023_MOESM3.xlsx`, sha256 in RELEASES.md). The sheet whose
name begins `ST36` lists highly pleiotropic pQTL variants; each of its three `close genes`
columns (Olink, SomaScan SMP-normalized, SomaScan non-normalized) holds the gene symbols near a
variant, separated by commas, semicolons or spaces. The list is every distinct symbol in those
columns, with the number of sheet rows naming it.

The workbook is read on Modal (scripts/modal_biology_joins.py::pleiotropic_loci); openpyxl is
imported there.
"""

import collections
import csv
import pathlib
import re

SHEET_PREFIX = "ST36"
GENE_COLUMN = "close genes"
SPLIT = re.compile(r"[,;\s]+")


class WorkbookError(Exception):
    """The workbook does not have the expected sheet or columns."""


def sheet_heads(workbook, n_rows: int = 4) -> dict[str, list[list]]:
    """The first rows of every sheet (title line and header), for the record of what each is."""
    return {ws.title: [list(r) for r in ws.iter_rows(min_row=1, max_row=n_rows,
                                                     values_only=True)]
            for ws in workbook.worksheets}


def close_genes(workbook) -> tuple[dict[str, int], dict]:
    """(gene symbol -> number of sheet rows naming it, provenance of the read)."""
    sheets = [ws for ws in workbook.worksheets if ws.title.startswith(SHEET_PREFIX)]
    if len(sheets) != 1:
        raise WorkbookError(f"expected one sheet beginning {SHEET_PREFIX!r}, found "
                            f"{[ws.title for ws in sheets]}")
    ws = sheets[0]
    rows = ws.iter_rows(values_only=True)
    lead: list[list] = []
    header: list[str] | None = None
    for r in rows:
        cells = ["" if v is None else " ".join(str(v).split()) for v in r]
        if any(GENE_COLUMN in c.lower() for c in cells):
            header = cells
            break
        lead.append(cells)
    if header is None:
        raise WorkbookError(f"sheet {ws.title!r} has no column containing {GENE_COLUMN!r}")
    cols = [i for i, c in enumerate(header) if GENE_COLUMN in c.lower()]
    counts: collections.Counter = collections.Counter()
    n_rows = 0
    for r in rows:
        if all(v is None for v in r):
            continue
        n_rows += 1
        named = {g for i in cols if i < len(r) and r[i] is not None
                 for g in SPLIT.split(str(r[i]).strip()) if g and g.upper() != "NA"}
        counts.update(named)
    provenance = {"sheet": ws.title, "lines_before_header": lead, "header": header,
                  "gene_columns": [header[i] for i in cols], "variant_rows": n_rows,
                  "distinct_genes": len(counts)}
    return dict(counts), provenance


def write_list(counts: dict[str, int], path: pathlib.Path) -> None:
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["gene", "variant_rows"])
        w.writerows(sorted(counts.items()))


def load_list(path: pathlib.Path) -> frozenset[str]:
    with path.open(newline="") as f:
        return frozenset(r["gene"] for r in csv.DictReader(f))
