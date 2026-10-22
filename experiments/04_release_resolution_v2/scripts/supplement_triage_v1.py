# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.13.5"]
# ///
"""Unregistered supplement triage of the second registration (PREREG.log of 22 October 2026):
a deterministic scan of the sources already retrieved for the 135 scope records that hold an
unresolved row after stage A (outputs/stage_b_decision_2026-10-21.json, unresolved_record_ids).
No model is called and nothing is fetched.

Sources. Every source of the record's retrieval (`result.json` of the first registration's
retrieval, outputs/raw/retrieval_dl/retrieval/<record>/): the R1 full text and every R2
supplement, read from the text the retrieval stored (its sha256 is the stored `text_sha256`).
A supplement the retrieval left without text is converted here when a local tool reads it: a
PDF by `pdftotext -layout`; a .doc by macOS `textutil`; a .pptx by the text runs of its slides;
R code, SVG and other plain files decoded as UTF-8; an HTML file whose stored text is empty, as
its raw markup. Anything else (images, a PDF with no text layer, a macOS resource fork) is
reported as not scanned with its reason, never dropped.

Patterns. (1) The frozen C1 scanner patterns (`reference/c1_scanner_patterns_v2.json`):
accessions, numbered releases, DOIs and PMIDs, mapped by the frozen scanner's Mapper
(`source_scanner_v2.Mapper`, the accession table and the dictionary). (2) Patterns added here
(`EXTRA`), each mapped only as stated in its entry: FinnGen file identifiers (`finngen_R10_X`,
which the frozen pattern misses because of the trailing underscore), release-before-resource
prose, OpenGWAS identifiers of every batch, UKB-PPP Synapse file identifiers, deCODE SomaScan
file identifiers, the deCODE summary-data URL, and author-year citations of the pQTL studies.
OpenGWAS identifiers outside the frozen table are given the dictionary rows whose PMID is the
dataset's PMID in the stored OpenGWAS metadata (`opengwas_gwasinfo`, `opengwas_batches`, stored
for the first registration's reference tables), reported apart from the frozen mapping.
(3) Resource terms (`RESOURCES`), counted. (4) The keep-list release language
(`reference/release_language_patterns_v2.json`), counted only on lines that also hold a resource
term. (5) Exact case and control counts: on a line holding a resource term, every ordered pair
of integers on the line equal to the cases and controls of a row of
`reference/release_counts.csv`.

Output. The committed file holds ids, file hashes, matched identifiers, mapped rows and counts.
The raw file (gitignored folder) adds, for the first three occurrences of each identifier in a
file, the line number, the sheet or page, and up to two neighbouring lines of context, and the
extracted text of every converted file.

    PYTHONPATH=scripts:../03_release_resolution/scripts:../02_claims_meta/scripts \\
        uv run python scripts/supplement_triage_v1.py --out outputs/supplement_triage_scan_2026-10-22.json \\
        --raw outputs/raw/supplement_triage_2026-10-22
"""

import argparse
import bisect
import collections
import csv
import hashlib
import io
import json
import pathlib
import re
import subprocess
import tempfile
import zipfile

from pydantic import BaseModel

import source_scanner_v2 as scanner

HERE = pathlib.Path(__file__).resolve().parent
E4 = HERE.parent
E3 = E4.parent / "03_release_resolution"
E2 = E4.parent / "02_claims_meta"
RETRIEVAL = E3 / "outputs" / "raw" / "retrieval_dl" / "retrieval"
DECISION = E4 / "outputs" / "stage_b_decision_2026-10-21.json"
PATTERNS = E3 / "reference" / "c1_scanner_patterns_v2.json"
KEEP = E3 / "reference" / "release_language_patterns_v2.json"
ACCESSIONS = E3 / "reference" / "accession_releases.csv"
COUNTS = E3 / "reference" / "release_counts.csv"
DICTIONARY = E2 / "dataset_dictionary.csv"
OG_INFO = E3 / "outputs" / "raw" / "reference_sources" / "opengwas_gwasinfo"
OG_BATCHES = E3 / "outputs" / "raw" / "reference_sources" / "opengwas_batches"

CONTEXT_OCCURRENCES = 3
CONTEXT_CHARS = 300
DISTINCT_KEPT = 200
MAX_NUMBERS_PER_LINE = 20
COUNT_LINE_CHARS = 2_000
COUNT_LINES = 5_000
COUNT_RESOURCE = r"(?i)finn\s?gen|uk\s?biobank|\bukbb?\b|neale|pan[- ]ukb|saige|topmed|host genetics"
TEXT_SUFFIXES = {".r", ".txt", ".svg", ".mdp", ".tsv", ".csv", ".linear", ".md"}
IMAGE_SUFFIXES = {".gif", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}

EXTRA = [
    {"name": "finngen_file_id", "pattern": r"(?i)\bfinngen_R(\d{1,2})_[A-Za-z0-9_]+",
     "row": "FinnGen R{n}", "mapping": "the FinnGen release the file name carries"},
    {"name": "release_before_finngen",
     "pattern": r"(?i)\b(?:R|round|release|version|freeze|data freeze|DF)\s*-?\s*(\d{1,2})\b"
                r"[^.;\n]{0,40}?\bFinnGen\b",
     "row": "FinnGen R{n}", "mapping": "the FinnGen release named before the resource"},
    {"name": "opengwas_any",
     "pattern": r"(?i)\b(?:prot-[a-d]|eqtl-a|met-[a-e]|ebi-a|ieu-a|ieu-b|finn-b|ukb-[a-e]|bbj-a)"
                r"-[A-Za-z0-9_.]*[A-Za-z0-9_]",
     "row": None, "mapping": "frozen Mapper, else the stored OpenGWAS metadata's PMID"},
    {"name": "ukb_ppp_file_id", "pattern": r"(?i)\bukb-ppp-[A-Za-z0-9.]+-OID\d+",
     "row": None, "mapping": "UKB-PPP (Sun 2023), which of its rows not fixed"},
    {"name": "decode_seq_id", "pattern": r"\b\d{4,5}_\d{1,3}_[A-Za-z0-9]+_[A-Za-z0-9]+\b",
     "row": None, "mapping": "deCODE SomaScan file name (Ferkingstad 2021 or Eldjarn 2023)"},
    {"name": "decode_seq_id_short", "pattern": r"\b\d{4,5}_[A-Z][A-Z0-9]{1,15}\b",
     "row": None, "mapping": "SomaScan sequence id with gene (deCODE or another SomaScan study)"},
    {"name": "decode_url", "pattern": r"(?i)decode\.com/summarydata", "row": None,
     "mapping": "deCODE summary data page"},
    {"name": "author_year",
     "pattern": r"\b(Ferkingstad|Eldjarn|Pietzner|Folkersen|Zheng|Sun|Suhre|Emilsson|Gudjonsson"
                r"|Yao|Hillary|Gilly|Png|Enroth|Katz|Zhang|Zhao|Koprulu|Dhindsa)"
                r"(?:\s+et\s+al\.?|\s+[A-Z]{1,2}\b)[^;\n\d]{0,30}?((?:19|20)\d\d)",
     "row": None, "mapping": "author and year, read by hand"},
]

RESOURCES = {
    "FinnGen": r"(?i)\bfinn\s?gen\b", "UK Biobank": r"(?i)\buk\s?biobank\b|\bUKBB?\b",
    "UKB-PPP": r"(?i)\bukb[- ]?ppp\b|pharma proteomics project",
    "deCODE": r"(?i)\bdecode\b|\bicelandic\b", "Fenland": r"(?i)\bfenland\b",
    "ARIC": r"(?i)\bARIC\b|atherosclerosis risk in communities", "INTERVAL": r"\bINTERVAL\b",
    "SCALLOP": r"(?i)\bscallop\b", "KORA": r"\bKORA\b", "AGES": r"\bAGES\b",
    "OpenGWAS": r"(?i)opengwas|\bieu\b|mr-base|mrbase", "GWAS Catalog": r"(?i)gwas\s+catalog",
    "eQTLGen": r"(?i)eqtlgen", "Neale": r"(?i)\bneale\b", "Pan-UKB": r"(?i)pan[- ]ukb",
    "SAIGE": r"(?i)\bsaige\b", "Biobank Japan": r"(?i)biobank japan|\bBBJ\b",
    "MVP": r"(?i)million veteran", "MEGASTROKE": r"(?i)megastroke|gigastroke",
    "CARDIoGRAM": r"(?i)cardiogram", "IGAP": r"(?i)\bIGAP\b", "PGC": r"\bPGC\b",
    "GIANT": r"\bGIANT\b", "COVID-19 HGI": r"(?i)covid-?19 hg|host genetics initiative",
    "Synapse": r"(?i)synapse\.org", "Olink": r"(?i)\bolink\b", "SomaScan": r"(?i)somascan|somalogic",
}


class TriageError(Exception):
    """An output exists already, or an input is missing."""


class FileScan(BaseModel):
    record_id: str
    route: str
    kind: str
    name: str
    type: str
    sha256: str | None
    text_sha256: str | None
    characters: int
    status: str
    reason: str | None
    identifiers: dict[str, dict]
    resource_terms: dict[str, int]
    release_language_on_resource_lines: dict[str, int]
    count_matches: list[dict]


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path: pathlib.Path) -> list[dict]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def member_bytes(archive: pathlib.Path, name: str) -> bytes:
    """The bytes of `name` ("supplementaryFiles.zip/a.zip/b.xlsx") inside the stored archive."""
    parts = name.split(".zip/")
    data = archive.read_bytes()
    if len(parts) == 1:
        return data
    for i, part in enumerate(parts[1:]):
        inner = part if i == len(parts) - 2 else part + ".zip"
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            data = z.read(inner)
    return data


def convert(name: str, data: bytes) -> tuple[str | None, str | None]:
    """Text of a file the retrieval left without text, or None and the reason."""
    base = name.rsplit("/", 1)[-1]
    suffix = pathlib.Path(base).suffix.lower()
    if base.startswith("._"):
        return None, "macos_resource_fork"
    if suffix in IMAGE_SUFFIXES:
        return None, "image"
    if data[:4] == b"%PDF" or suffix in (".pdf", ".ai"):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "f.pdf"
            p.write_bytes(data)
            run = subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True)
        text = run.stdout.decode("utf-8", "replace")
        return (text, None) if len(text.split()) >= 20 else (None, "pdf_without_text_layer")
    if suffix == ".doc":
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "f.doc"
            p.write_bytes(data)
            run = subprocess.run(["textutil", "-convert", "txt", "-stdout", str(p)],
                                 capture_output=True)
        text = run.stdout.decode("utf-8", "replace")
        return (text, None) if text.strip() else (None, "doc_unreadable")
    if suffix == ".pptx":
        out = []
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            slides = sorted((n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                            key=lambda n: int(re.search(r"(\d+)", n.rsplit("/", 1)[-1]).group(1)))
            for n in slides:
                runs = re.findall(r"<a:t>([^<]*)</a:t>", z.read(n).decode("utf-8", "replace"))
                out.append(f"## slide {n.rsplit('/', 1)[-1]}\n" + "\n".join(runs))
        return "\n".join(out), None
    if suffix in TEXT_SUFFIXES or suffix in (".html", ".htm"):
        return data.decode("utf-8", "replace"), None
    return None, "type_not_converted"


class Scanner:
    def __init__(self):
        self.patterns = json.loads(PATTERNS.read_text())
        self.mapper = scanner.Mapper(self.patterns, read_csv(ACCESSIONS), read_csv(DICTIONARY))
        self.frozen = []
        for p in self.patterns["accessions"]:
            self.frozen.append(("accession:" + p["type"], re.compile(p["pattern"]), p))
        for p in self.patterns["releases"]:
            self.frozen.append(("release:" + p["resource"], re.compile(p["pattern"]), p))
        for p in self.patterns["source_identifiers"]:
            self.frozen.append(("source_identifier:" + p["type"], re.compile(p["pattern"]), p))
        self.extra = [(e["name"], re.compile(e["pattern"]), e) for e in EXTRA]
        self.resources = {k: re.compile(v) for k, v in RESOURCES.items()}
        self.count_resource = re.compile(COUNT_RESOURCE)
        self.keep = [(p["name"], re.compile(p["pattern"]))
                     for p in json.loads(KEEP.read_text())["patterns"]]
        self.counts = collections.defaultdict(list)
        for r in read_csv(COUNTS):
            self.counts[(r["cases"], r["controls"])].append(
                {"dictionary_row": r["dictionary_row"], "endpoint_code": r["endpoint_code"]})
        self.pmid_rows = collections.defaultdict(set)
        for r in read_csv(DICTIONARY):
            for p in re.findall(r"PMID:\s*(\d+)", r["source_identifier"], re.I):
                self.pmid_rows[p].add(r["name"])
        info = json.loads(OG_INFO.read_text())
        self.og_pmid = {k: str(v.get("pmid") or "") for k, v in info.items()}
        self.og_batch_pmid = {}
        for b in json.loads(OG_BATCHES.read_text()):
            m = re.search(r"(?:pubmed/|pubmed\.ncbi\.nlm\.nih\.gov/)(\d+)", b.get("link") or "")
            pmc = re.search(r"(PMC\d+)", b.get("link") or "")
            if m:
                self.og_batch_pmid[b["id"]] = ("pmid", m.group(1))
            elif pmc:
                self.og_batch_pmid[b["id"]] = ("pmc", pmc.group(1))
        self.pmc_rows = collections.defaultdict(set)
        for r in read_csv(DICTIONARY):
            for p in re.findall(r"(PMC\d+)", r["source_identifier"]):
                self.pmc_rows[p].add(r["name"])

    def opengwas_rows(self, ident: str) -> tuple[list[str], str]:
        frozen = self.mapper.accession(ident)
        if frozen:
            return sorted(frozen), "frozen_table"
        pmid = self.og_pmid.get(ident)
        if pmid:
            return sorted(self.pmid_rows.get(pmid, set())), f"opengwas_metadata_pmid:{pmid}"
        batch = "-".join(ident.split("-", 2)[:2])
        kind, ref = self.og_batch_pmid.get(batch, (None, None))
        if kind == "pmid":
            return sorted(self.pmid_rows.get(ref, set())), f"opengwas_batch_pmid:{ref}"
        if kind == "pmc":
            return sorted(self.pmc_rows.get(ref, set())), f"opengwas_batch_pmc:{ref}"
        return [], "unmapped"

    def matches(self, text: str):
        """(start, end, pattern name, identifier, rows, mapping basis) for every match."""
        found = []
        for name, rx, p in self.frozen:
            for m in rx.finditer(text):
                if name == "accession:opengwas":
                    ident = scanner.canonical(m.group(0), p["canonical"])
                    rows, basis = self.opengwas_rows(ident)
                elif name.startswith("accession:"):
                    ident = scanner.canonical(m.group(0), p["canonical"])
                    rows, basis = sorted(self.mapper.accession(ident)), "frozen_table"
                elif name.startswith("release:"):
                    row = p["row"].format(n=int(m.group(1)))
                    ident, rows, basis = row, sorted(self.mapper.release(row)), "frozen_release"
                else:
                    term = self.patterns["doi_terminal_characters"]
                    key = (f"doi:{scanner.norm_doi(m.group(0), term)}" if p["type"] == "doi"
                           else f"pmid:{m.group(1)}")
                    ident = key
                    rows, basis = sorted(self.mapper.exact.get(key, set())), "frozen_source_id"
                found.append((m.start(), m.end(), name, ident, rows, basis))
        for name, rx, e in self.extra:
            for m in rx.finditer(text):
                if e["row"]:
                    row = e["row"].format(n=int(m.group(1)))
                    ident = m.group(0) if name == "finngen_file_id" else row
                    rows, basis = sorted(self.mapper.release(row)), "release_number"
                elif name == "opengwas_any":
                    ident = scanner.canonical(m.group(0), "opengwas")
                    rows, basis = self.opengwas_rows(ident)
                elif name == "author_year":
                    ident, rows, basis = f"{m.group(1)} {m.group(2)}", [], "by_hand"
                else:
                    ident, rows, basis = m.group(0), [], e["mapping"]
                found.append((m.start(), m.end(), "extra:" + name, ident, rows, basis))
        return found


def markers(text: str) -> tuple[list[int], list[str], list[int]]:
    sheet_pos, sheet_names = [], []
    for m in re.finditer(r"^## (?:sheet|slide) (.*)$", text, re.M):
        sheet_pos.append(m.start())
        sheet_names.append(m.group(1))
    pages = [m.start() for m in re.finditer("\f", text)]
    return sheet_pos, sheet_names, pages


def locate(pos: int, nl: list[int], sheets, pages) -> dict:
    line = bisect.bisect_right(nl, pos - 1) + 1
    out = {"line": line}
    if sheets[0]:
        i = bisect.bisect_right(sheets[0], pos) - 1
        out["sheet"] = sheets[1][i] if i >= 0 else None
    if pages:
        out["page"] = bisect.bisect_right(pages, pos) + 1
    return out


def context(text: str, nl: list[int], line: int) -> list[str]:
    out = []
    for ln in (line - 1, line, line + 1):
        if 1 <= ln <= len(nl) + 1:
            s = nl[ln - 2] + 1 if ln >= 2 else 0
            e = nl[ln - 1] if ln - 1 < len(nl) else len(text)
            out.append(f"{ln}: {text[s:e][:CONTEXT_CHARS]}")
    return out


def scan_text(sc: Scanner, text: str) -> tuple[dict, dict, dict, list, dict, dict]:
    nl = [m.start() for m in re.finditer("\n", text)]
    sheet_pos, sheet_names, pages = markers(text)
    sheets = (sheet_pos, sheet_names)
    found = sc.matches(text)
    og = sorted((s, e) for s, e, name, *_ in found
                if name in ("accession:opengwas", "extra:opengwas_any"))
    og_starts = [s for s, _ in og]
    frozen_og = {(s, e) for s, e, name, *_ in found if name == "accession:opengwas"}

    def in_opengwas(s: int, e: int) -> bool:
        i = bisect.bisect_right(og_starts, s) - 1
        return i >= 0 and og[i][1] >= e and og[i] != (s, e)

    idents: dict[str, dict] = {}
    raw: dict[str, list] = collections.defaultdict(list)
    for s, e, name, ident, rows, basis in sorted(found, key=lambda f: (f[0], f[2])):
        if name == "accession:gwas_catalog" and in_opengwas(s, e):
            continue
        if name == "extra:opengwas_any" and (s, e) in frozen_og:
            continue
        key = f"{name}|{ident}"
        d = idents.setdefault(key, {"pattern": name, "identifier": ident, "rows": rows,
                                    "basis": basis, "count": 0})
        d["count"] += 1
        if len(raw[key]) < CONTEXT_OCCURRENCES:
            loc = locate(s, nl, sheets, pages)
            raw[key].append(loc | {"context": context(text, nl, loc["line"])})
            if d["count"] == 1:
                d["first"] = {k: v for k, v in loc.items()}
    keep, keep_raw, count_matches = collections.Counter(), collections.defaultdict(list), []
    starts = [0] + [p + 1 for p in nl]
    counted = 0
    terms, positions = collections.Counter(), set()
    for k, rx in sc.resources.items():
        for m in rx.finditer(text):
            terms[k] += 1
            positions.add(m.start())
    resource_lines = sorted({bisect.bisect_right(nl, pos - 1) + 1 for pos in positions})
    for ln in resource_lines:
        s = starts[ln - 1]
        e = nl[ln - 1] if ln - 1 < len(nl) else len(text)
        line = text[s:e]
        for name, rx in sc.keep:
            if rx.search(line):
                keep[name] += 1
                if len(keep_raw[name]) < CONTEXT_OCCURRENCES:
                    keep_raw[name].append(locate(s, nl, sheets, pages)
                                          | {"context": context(text, nl, ln)})
        if not (sc.count_resource.search(line) and len(line) <= COUNT_LINE_CHARS
                and counted < COUNT_LINES):
            continue
        counted += 1
        nums = [n.replace(",", "") for n in re.findall(r"(?<![\d.])\d{1,3}(?:,\d{3})+(?![\d.])|"
                                                       r"(?<![\d.])\d{2,7}(?![\d.])", line)]
        nums = [n for n in nums if int(n) >= 50][:MAX_NUMBERS_PER_LINE]
        for i, a in enumerate(nums):
            for b in nums[i + 1:]:
                for hit in sc.counts.get((a, b), []):
                    loc = locate(s, nl, sheets, pages)
                    count_matches.append(hit | {"cases": a, "controls": b, "line": ln,
                                                **({"sheet": loc["sheet"]} if "sheet" in loc
                                                   else {})})
                    if len(keep_raw["count_match"]) < 50:
                        keep_raw["count_match"].append(loc | {"context": context(text, nl, ln)})
    return idents, dict(raw), dict(keep), count_matches, dict(keep_raw), dict(terms)


def compact(idents: dict) -> dict:
    """Identifiers grouped by pattern; at most DISTINCT_KEPT distinct identifiers per pattern."""
    by = collections.defaultdict(list)
    for d in idents.values():
        by[d["pattern"]].append(d)
    out = {}
    for pat, items in sorted(by.items()):
        items.sort(key=lambda d: (-d["count"], d["identifier"]))
        rows = collections.Counter()
        for d in items:
            rows["|".join(d["rows"]) or "unmapped"] += d["count"]
        out[pat] = {"distinct": len(items), "occurrences": sum(d["count"] for d in items),
                    "by_rows": dict(sorted(rows.items())),
                    "identifiers": [{k: d[k] for k in ("identifier", "rows", "basis", "count",
                                                       "first")} for d in items[:DISTINCT_KEPT]]}
    return out


def scan_record(sc: Scanner, rec: str, raw_dir: pathlib.Path) -> list[FileScan]:
    folder = RETRIEVAL / rec
    result = json.loads((folder / "result.json").read_text())
    out = []
    for src in result["sources"]:
        kind = "full_text" if src["route"] in ("R1", "R3") else "supplement"
        name = src.get("name") or src.get("url")
        text, reason, status = src.get("text"), src.get("reason"), "scanned_stored_text"
        sha = src.get("sha256")
        if text is not None and len(text) == 0 and src.get("type") == "HTML":
            text, reason = None, "html_text_empty"
        if text is None:
            archive = folder / "files" / src["archive"] if src.get("archive") else None
            if pathlib.Path(name).suffix.lower() in IMAGE_SUFFIXES:
                status, reason = "not_scanned", "image"
            elif archive is None or not archive.exists():
                status = "not_scanned"
                reason = reason or "file_not_stored"
            else:
                try:
                    data = member_bytes(archive, src["name"])
                except (KeyError, zipfile.BadZipFile) as exc:
                    data, reason = None, f"archive_member_unreadable:{type(exc).__name__}"
                text2, why = convert(src["name"], data) if data is not None else (None, reason)
                if text2 is None:
                    status, reason = "not_scanned", why
                else:
                    text, status = text2, "scanned_local_conversion"
                    reason = f"converted_here (retrieval: {src.get('reason')})"
                    tsha = hashlib.sha256(text.encode()).hexdigest()
                    (raw_dir / "converted").mkdir(parents=True, exist_ok=True)
                    (raw_dir / "converted" / f"{rec}_{tsha[:16]}.txt").write_text(text)
        tsha = (src.get("text_sha256") if status == "scanned_stored_text"
                else hashlib.sha256(text.encode()).hexdigest() if text is not None else None)
        if text is None:
            out.append(FileScan(record_id=rec, route=src["route"], kind=kind, name=name,
                                type=src.get("type") or "", sha256=sha, text_sha256=None,
                                characters=0, status=status, reason=reason, identifiers={},
                                resource_terms={}, release_language_on_resource_lines={},
                                count_matches=[]))
            continue
        idents, raw, keep, cm, keep_raw, terms = scan_text(sc, text)
        fs = FileScan(record_id=rec, route=src["route"], kind=kind, name=name,
                      type=src.get("type") or "", sha256=sha, text_sha256=tsha,
                      characters=len(text), status=status, reason=reason,
                      identifiers=compact(idents), resource_terms=terms,
                      release_language_on_resource_lines=keep, count_matches=cm)
        out.append(fs)
        rawrec = raw_dir / "records" / rec
        rawrec.mkdir(parents=True, exist_ok=True)
        with (rawrec / "hits.jsonl").open("a") as fh:
            fh.write(json.dumps({"file": name, "sha256": sha, "text_sha256": tsha,
                                 "identifier_contexts": raw, "language_and_count_contexts":
                                     keep_raw}, ensure_ascii=False) + "\n")
    return out


def inputs_sha256() -> dict[str, str]:
    files = [DECISION, PATTERNS, KEEP, ACCESSIONS, COUNTS, DICTIONARY, OG_INFO, OG_BATCHES,
             HERE / "supplement_triage_v1.py", E3 / "scripts" / "source_scanner_v2.py"]
    return {str(f.relative_to(E4.parent.parent)): sha256_file(f) for f in files}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--raw", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists() or a.raw.exists():
        raise TriageError(f"{a.out} or {a.raw} exists; each is written once")
    records = json.loads(DECISION.read_text())["unresolved_record_ids"]
    sc = Scanner()
    a.raw.mkdir(parents=True)
    scans = []
    for i, rec in enumerate(records):
        scans.extend(scan_record(sc, rec, a.raw))
        print(f"{i + 1}/{len(records)} {rec}", flush=True)
    status = collections.Counter(f"{s.kind}|{s.status}|{s.reason or ''}" for s in scans)
    per_record = collections.defaultdict(lambda: collections.Counter())
    for s in scans:
        for pat, d in s.identifiers.items():
            per_record[s.record_id][pat] += d["occurrences"]
    out = {"script": "scripts/supplement_triage_v1.py",
           "what": "unregistered supplement triage scan; ids, hashes, matched identifiers and "
                   "counts only (contexts in the gitignored raw folder)",
           "inputs_sha256": inputs_sha256(),
           "records": len(records),
           "files": len(scans),
           "files_by_kind_status_reason": dict(sorted(status.items())),
           "records_with_any_mapped_identifier": len({
               s.record_id for s in scans for d in s.identifiers.values()
               if any(i["rows"] for i in d["identifiers"])}),
           "occurrences_by_record_and_pattern": {r: dict(sorted(c.items()))
                                                 for r, c in sorted(per_record.items())},
           "scans": [s.model_dump() for s in scans]}
    a.out.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print("written", a.out)


if __name__ == "__main__":
    main()
