# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "openpyxl==3.1.5", "xlrd==2.0.1", "python-docx==1.1.2"]
# ///
"""Retrieval of the sources of the release-resolution follow-up (PREREG.md, §Study design,
Sources and Versions; frozen, registered at https://osf.io/2s479). No model is called and no
source is read for content: a source is fetched, converted to text and counted.

Per record of the scope (`retrieve_record`):

- Europe PMC metadata of the record (`resultType=core`): its PMCID, its supplementary-file flag
  and the corrections it lists (`commentCorrectionList`, types in CORRECTION_TYPES).
- R1: the Europe PMC full-text XML of the record, rendered as in Paper 1
  (`fetch_fulltext.drop_abstracts` and `fetch_fulltext.render`, unchanged: the body only, one
  line per paragraph, one line per table row with caption and headers). Eligible when the XML
  has a body.
- R2: the supplementary files Europe PMC lists for the record (`hasSuppl` Y;
  `/supplementaryFiles`, a ZIP), each converted by type.
- R3: for a record with no Europe PMC full text, the file at the open-access location OpenAlex
  gives (`best_oa_location`: the PDF URL, else the landing page), when a plain request returns
  it.
- Versions: a correction or erratum Europe PMC links to the record is fetched by R1 as a
  source of version `correction`; a journal record with no full text by R1 or R3 takes, in
  turn, the preprint records of its study family (Paper 1's families), by the same routes.
- R4 (a file the author downloaded by hand) is not run here.

Every request is tried three times, 60 seconds apart; a source with no file after that is not
retrieved, and a record with no source is `no_source`. Accepted types: JATS XML, PDF, plain
text, HTML, CSV, TSV, XLSX, XLS, DOCX, and ZIP archives of these. A PDF is converted with
`pdftotext -layout`; a file of another type, a PDF with no text layer, or a table over 50 MB is
`source_unreadable`. No request carries an e-mail address and none imitates a browser.

The result of a record lists each source with its route, version, URL, date, type, the sha256
of the stored file and of its text, and its character count; and each failure with its reason.
"""

import datetime
import hashlib
import html.parser
import io
import json
import pathlib
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
import zipfile

import docx
import httpx
import openpyxl
import xlrd

import fetch_fulltext

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
OPENALEX = "https://api.openalex.org/works/"
CORRECTION_TYPES = ("Erratum in", "Corrected and republished in")
TABLE_LIMIT = 50 * 1024 * 1024
TRIES, WAIT = 3, 60
TEXT_TYPES = {".txt": "plain text", ".csv": "CSV", ".tsv": "TSV"}


class RetrievalError(Exception):
    """A record of the scope is missing from the search records."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")


def get(client, url: str, params: dict | None = None, sleep=time.sleep):
    """A response with status 200, or None after three tries 60 seconds apart."""
    for attempt in range(TRIES):
        try:
            r = client.get(url, params=params)
            if r.status_code == 200:
                return r
        except httpx.HTTPError:
            pass
        if attempt < TRIES - 1:
            sleep(WAIT)
    return None


class _Text(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        if tag in ("p", "div", "tr", "li", "br", "h1", "h2", "h3", "h4", "table"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_text(data: bytes) -> str:
    p = _Text()
    p.feed(data.decode("utf-8", errors="replace"))
    return "\n".join(" ".join(line.split()) for line in "".join(p.parts).splitlines()
                     if line.strip())


def pdf_text(data: bytes) -> str:
    with tempfile.TemporaryDirectory() as d:
        src = pathlib.Path(d) / "f.pdf"
        src.write_bytes(data)
        run = subprocess.run(["pdftotext", "-layout", str(src), "-"], capture_output=True)
        return run.stdout.decode("utf-8", errors="replace") if run.returncode == 0 else ""


def kind_of(name: str, data: bytes) -> str:
    suffix = pathlib.PurePath(name.lower()).suffix
    if data[:4] == b"%PDF" or suffix == ".pdf":
        return "PDF"
    if data[:2] == b"PK" and suffix in (".xlsx", ".xlsm"):
        return "XLSX"
    if data[:2] == b"PK" and suffix == ".docx":
        return "DOCX"
    if data[:2] == b"PK" and suffix == ".zip":
        return "ZIP"
    if suffix == ".xls":
        return "XLS"
    if suffix in (".html", ".htm"):
        return "HTML"
    if suffix == ".xml":
        return "XML"
    return TEXT_TYPES.get(suffix, "other")


def convert(name: str, data: bytes) -> list[dict]:
    """The text of one file, or of each member of a ZIP archive: one entry per file, with its
    type, its text (None when unreadable) and the reason when unreadable."""
    kind = kind_of(name, data)
    entry = {"name": name, "type": kind, "bytes": len(data), "sha256": sha256(data)}
    if kind == "ZIP":
        out = []
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for member in sorted(i.filename for i in z.infolist() if not i.is_dir()):
                out.extend(convert(f"{name}/{member}", z.read(member)))
        return out
    if kind in ("XLSX", "XLS", "CSV", "TSV") and len(data) > TABLE_LIMIT:
        return [entry | {"text": None, "reason": "table_over_50_mb"}]
    try:
        if kind == "PDF":
            text = pdf_text(data)
            if not text.strip():
                return [entry | {"text": None, "reason": "pdf_without_text_layer"}]
        elif kind == "XLSX":
            book = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            lines = []
            for sheet in book.worksheets:
                lines.append(f"## sheet {sheet.title}")
                for row in sheet.iter_rows(values_only=True):
                    if any(v is not None for v in row):
                        lines.append("\t".join("" if v is None else str(v) for v in row))
            text = "\n".join(lines)
            entry["sheets"] = len(book.worksheets)
        elif kind == "XLS":
            book = xlrd.open_workbook(file_contents=data)
            lines = []
            for sheet in book.sheets():
                lines.append(f"## sheet {sheet.name}")
                for i in range(sheet.nrows):
                    lines.append("\t".join(str(v) for v in sheet.row_values(i)))
            text = "\n".join(lines)
            entry["sheets"] = book.nsheets
        elif kind == "DOCX":
            document = docx.Document(io.BytesIO(data))
            lines = [p.text for p in document.paragraphs if p.text.strip()]
            for table in document.tables:
                for row in table.rows:
                    lines.append("\t".join(c.text for c in row.cells))
            text = "\n".join(lines)
        elif kind == "HTML":
            text = html_text(data)
        elif kind == "XML":
            text = "\n".join(" ".join(t.split()) for t in ET.fromstring(data).itertext()
                             if t.strip())
        elif kind in ("plain text", "CSV", "TSV"):
            text = data.decode("utf-8", errors="replace")
        else:
            return [entry | {"text": None, "reason": "type_not_accepted"}]
    except Exception as e:  # a file that the converter of its type cannot read
        return [entry | {"text": None, "reason": f"unreadable_{type(e).__name__}"}]
    return [entry | {"text": text}]


def render_xml(data: bytes) -> str | None:
    """Paper 1's rendering of a Europe PMC full-text XML, or None when it has no body."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return None
    fetch_fulltext.drop_abstracts(root)
    body = root.find("body")
    if body is None:
        return None
    lines: list[str] = []
    fetch_fulltext.render(body, lines)
    return "\n".join(lines)


def epmc_query(rec: dict) -> str:
    if rec.get("pmid"):
        return f"EXT_ID:{rec['pmid']} AND SRC:MED"
    if rec["record_id"].startswith("PPR"):
        return f"EXT_ID:{rec['record_id']} AND SRC:PPR"
    return f'DOI:"{rec["doi"]}"' if rec.get("doi") else ""


def epmc_meta(client, rec: dict, sleep) -> dict | None:
    query = epmc_query(rec)
    if not query:
        return None
    r = get(client, f"{EPMC}/search", {"query": query, "format": "json", "resultType": "core"},
            sleep)
    hits = r.json()["resultList"]["result"] if r is not None else []
    return hits[0] if len(hits) == 1 else None


def openalex_id(rec: dict) -> str | None:
    if rec["record_id"].startswith("W"):
        return rec["record_id"]
    if rec.get("doi"):
        return f"doi:{rec['doi']}"
    if rec.get("pmid"):
        return f"pmid:{rec['pmid']}"
    return None


def retrieve_version(client, rec: dict, version: str, store, sleep) -> tuple[list, list, dict]:
    """The sources of one version of a record by R1, R2 and R3, with failures and metadata."""
    sources, failures = [], []
    meta = epmc_meta(client, rec, sleep)
    pmcid = (meta or {}).get("pmcid") or (rec["record_id"] if rec["record_id"].startswith("PPR")
                                          else None)
    info = {"record_id": rec["record_id"], "version": version, "europe_pmc_record": meta is not None,
            "pmcid": pmcid, "europe_pmc_has_supplements": (meta or {}).get("hasSuppl"),
            "corrections": [c for c in ((meta or {}).get("commentCorrectionList") or {})
                            .get("commentCorrection", []) if c.get("type") in CORRECTION_TYPES]}
    full_text = False
    if pmcid:
        url = f"{EPMC}/{pmcid}/fullTextXML"
        r = get(client, url, sleep=sleep)
        text = render_xml(r.content) if r is not None else None
        if text:
            key = store(r.content)
            sources.append({"route": "R1", "version": version, "record_id": rec["record_id"],
                            "url": url, "retrieved_utc": now(), "type": "JATS XML",
                            "stored": key, "sha256": sha256(r.content), "text": text})
            full_text = True
        else:
            failures.append({"route": "R1", "version": version, "url": url,
                             "reason": "no_file" if r is None else "xml_without_body"})
    if pmcid and (meta or {}).get("hasSuppl") == "Y":
        url = f"{EPMC}/{pmcid}/supplementaryFiles"
        r = get(client, url, sleep=sleep)
        if r is not None and r.content:
            key = store(r.content)
            for part in convert("supplementaryFiles.zip", r.content):
                sources.append({"route": "R2", "version": version, "record_id": rec["record_id"],
                                "url": url, "retrieved_utc": now(), "archive": key, **part})
        else:
            failures.append({"route": "R2", "version": version, "url": url, "reason": "no_file"})
    if not full_text:
        work = openalex_id(rec)
        r = get(client, OPENALEX + work, sleep=sleep) if work else None
        loc = (r.json().get("best_oa_location") or {}) if r is not None else {}
        url = loc.get("pdf_url") or loc.get("landing_page_url")
        f = get(client, url, sleep=sleep) if url else None
        if f is not None:
            key = store(f.content)
            name = "oa.pdf" if f.content[:4] == b"%PDF" else (
                "oa.html" if b"<html" in f.content[:2000].lower() else "oa.bin")
            for part in convert(name, f.content):
                sources.append({"route": "R3", "version": version, "record_id": rec["record_id"],
                                "url": url, "retrieved_utc": now(), "stored": key, **part})
            full_text = any(s["route"] == "R3" and s.get("text") for s in sources)
        else:
            failures.append({"route": "R3", "version": version, "url": url,
                             "reason": "no_open_access_location" if not url else "no_file"})
    info["full_text"] = full_text
    return sources, failures, info


def retrieve_record(client, rec: dict, family_preprints: list[dict], store,
                    sleep=time.sleep) -> dict:
    """Every source of one record of the scope, with failures, by the registered routes."""
    versions, sources, failures = [], [], []
    s, f, info = retrieve_version(client, rec, "journal" if rec["kind"] == "journal"
                                  else rec["kind"], store, sleep)
    sources += s
    failures += f
    versions.append(info)
    for c in info["corrections"]:
        if c.get("source") == "MED" and c.get("id"):
            cs, cf, cinfo = retrieve_version(client, {"record_id": c["id"], "pmid": c["id"],
                                                      "kind": "correction"}, "correction",
                                             store, sleep)
            sources += [x for x in cs if x["route"] == "R1"]
            failures += [x for x in cf if x["route"] == "R1"]
            versions.append(cinfo)
    if rec["kind"] == "journal" and not info["full_text"]:
        for pre in family_preprints:
            ps, pf, pinfo = retrieve_version(client, pre, "preprint", store, sleep)
            sources += ps
            failures += pf
            versions.append(pinfo)
            if pinfo["full_text"]:
                break
    readable = [x for x in sources if x.get("text")]
    for x in sources:
        if x.get("text") is not None:
            x["text_sha256"] = sha256(x["text"].encode())
            x["characters"] = len(x["text"])
    return {"record_id": rec["record_id"], "kind": rec["kind"], "finished_utc": now(),
            "versions": versions, "sources": sources, "failures": failures,
            "status": "retrieved" if readable else (
                "source_unreadable" if sources else "no_source")}


def scope(availability: dict, search_records: dict[str, dict], families: dict) -> list[dict]:
    """The records of the scope, each with its search record and its family's preprints."""
    family_of = {r: f for f, rs in families["families"].items() for r in rs}
    out = []
    for rid in sorted(availability["records"]):
        if rid not in search_records:
            raise RetrievalError(f"{rid} is not a search record")
        members = families["families"][family_of[rid]]
        out.append({"record": search_records[rid],
                    "family_preprints": [search_records[m] for m in sorted(members)
                                         if m != rid and m in search_records
                                         and search_records[m]["kind"] == "preprint"]})
    return out
