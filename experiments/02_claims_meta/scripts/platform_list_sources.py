"""Published assay lists that no pinned package holds: fetch, check and read them.

`verification/platform_list_sources.csv` names, per list, the published supplementary file (its
URL, the member to take when the URL returns a zip archive, and its sha256), the sheet, the
identifier column, whether the column holds UniProt accessions or gene symbols, and a row filter
where the list is a subset of the sheet. The files are fetched straight to the Modal volume
(`/02_claims_meta/inputs/platform_assays_published/`); a file whose sha256 differs from the
table is not kept. No email address or other identifier is sent.

A list whose `file` is a `.csv` is read from a committed table that
scripts/derive_published_lists.py derived from published files
(`verification/published_lists_derived/`); it has no URL, and its sha256 is that of the
committed table. The published files those tables are derived from are named in
`verification/published_source_files.csv` (file, URL, zip member, sha256, source) and fetched to
the same folder of the volume. A zip member inside a zip member is written `outer.zip!inner`.

Reading. The header is the first row of the sheet that holds the identifier column's name; the
rows after it are the data. A row passes the filter when its filter cell, as text, equals the
filter value (a number written 1.0 reads "1"). `id_cells` returns the identifier cells of the
rows that pass.

The lists themselves are built in scripts/assay_backgrounds.py.
"""

import csv
import hashlib
import io
import pathlib
import zipfile

from pydantic import BaseModel, ConfigDict

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
SOURCES = EXP / "verification" / "platform_list_sources.csv"
SOURCE_FILES = EXP / "verification" / "published_source_files.csv"
DERIVED = EXP / "verification" / "published_lists_derived"


class ListSourceError(Exception):
    """A published list file has another checksum, sheet or column than the table says."""


class ListSource(BaseModel):
    model_config = ConfigDict(frozen=True)
    list_id: str
    file: str
    url: str
    zip_member: str
    sha256: str
    sheet: str
    id_column: str
    id_kind: str
    filter_column: str
    filter_value: str
    source: str


class SourceFile(BaseModel):
    """A published file that a derived table is built from."""
    model_config = ConfigDict(frozen=True)
    file: str
    url: str
    zip_member: str
    sha256: str
    source: str


def load_sources(path: pathlib.Path = SOURCES) -> list[ListSource]:
    with path.open(newline="") as f:
        sources = [ListSource(**r) for r in csv.DictReader(f)]
    if len({s.list_id for s in sources}) != len(sources):
        raise ListSourceError("a list id occurs twice")
    bad = [s.list_id for s in sources if s.id_kind not in ("uniprot", "gene_symbol")]
    if bad:
        raise ListSourceError(f"id_kind must be uniprot or gene_symbol: {bad}")
    bad = [s.list_id for s in sources if is_derived(s) == bool(s.url)]
    if bad:
        raise ListSourceError(f"a derived table has no URL and a published file has one: {bad}")
    return sources


def load_source_files(path: pathlib.Path = SOURCE_FILES) -> list[SourceFile]:
    with path.open(newline="") as f:
        files = [SourceFile(**r) for r in csv.DictReader(f)]
    if len({s.file for s in files}) != len(files):
        raise ListSourceError("a source file occurs twice")
    return files


def is_derived(source: ListSource) -> bool:
    return source.file.endswith(".csv")


def member_content(body: bytes, zip_member: str, sha256: str, label: str) -> bytes:
    """The file's bytes from a response body: the body itself, or the zip member named (a member
    of a member is written `outer.zip!inner`); refused when the sha256 differs."""
    for member in [m for m in zip_member.split("!") if m]:
        with zipfile.ZipFile(io.BytesIO(body)) as z:
            names = [n for n in z.namelist() if n.rsplit("/", 1)[-1] == member]
            if len(names) != 1:
                raise ListSourceError(f"{label}: {len(names)} members named {member}")
            body = z.read(names[0])
    found = hashlib.sha256(body).hexdigest()
    if found != sha256:
        raise ListSourceError(f"{label}: sha256 {found}, table says {sha256}")
    return body


def checked_content(source: ListSource | SourceFile, body: bytes) -> bytes:
    """The file's bytes from a response body (the zip member when one is named), refused when
    their sha256 differs from the table."""
    label = source.list_id if isinstance(source, ListSource) else source.file
    return member_content(body, source.zip_member, source.sha256, label)


def csv_rows(path: pathlib.Path) -> list[tuple]:
    """The rows of a derived table as tuples of cells, the header first."""
    with path.open(newline="") as f:
        return [tuple(r) for r in csv.reader(f)]


def text(cell) -> str:
    if cell is None:
        return ""
    if isinstance(cell, float) and cell.is_integer():
        return str(int(cell))
    return str(cell).strip()


def table(rows: list[tuple], source: ListSource) -> tuple[list[str], list[dict[str, str]]]:
    """(header, data rows as dictionaries) of a sheet given as tuples of cell values."""
    for i, row in enumerate(rows):
        header = [text(c) for c in row]
        if source.id_column in header:
            data = [dict(zip(header, (text(c) for c in r))) for r in rows[i + 1:]
                    if any(text(c) for c in r)]
            if source.filter_column and source.filter_column not in header:
                raise ListSourceError(f"{source.list_id}: no column {source.filter_column!r}")
            return header, data
    raise ListSourceError(f"{source.list_id}: no row holds the column {source.id_column!r}")


def id_cells(rows: list[tuple], source: ListSource) -> list[str]:
    """The identifier cells of the data rows that pass the source's filter."""
    _, data = table(rows, source)
    return [r[source.id_column] for r in data
            if not source.filter_column or r[source.filter_column] == source.filter_value]
