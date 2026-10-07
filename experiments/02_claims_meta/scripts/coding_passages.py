# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "pydantic==2.13.5", "pyyaml==6.0.3"]
# ///
"""The local paper passages a coder receives for each row of the manual dataset-coding queue
(PREREG.md, §Manual coding of dataset names, items 2 and 6; log of 2026-10-07). No model is
called and no text is chosen by hand: the rule below is applied to every row.

Source document. The body of the paper's Europe PMC open-access full text as
scripts/fetch_fulltext.py rendered it (one line per section title, paragraph or table row),
where the paper has one; else the abstract that was extracted. Supplementary files are not
fetched and never enter a passage.

Sentences. Each paragraph is split by `sentences` below, the only segmenter used: a sentence
ends at `.`, `!` or `?` (with closing quotes or brackets, and any linked citation numbers
written straight after them) followed by white space and an
upper-case letter, a digit or an opening bracket or quote, except after one of ABBREVIATIONS or
a single capital letter. A section title is not a sentence. A table row line is one unit and
is never split.

Terms. A row's terms are (a) its name as written, whole, and each part of it inside and
outside parentheses, and (b) for each candidate that is a row of the dataset dictionary, terms
read from these fields of that row: `name` (whole); `aliases` (each alias); `release` (whole,
when it has at most two words and holds a letter and a digit, such as "R9" or "Release 7");
`source_citation` (each first-author surname with its year, which both must occur in the
sentence); `source_identifier` (each DOI, PMID, PMC identifier or address); `sample_size` (each
integer of four or more digits, matched with or without digit grouping). `platform` is not
searched. A term matches a sentence case-insensitively after Unicode normalization (NFKC, case
folding, every dash as "-", white space collapsed), bounded by characters that are not letters
or digits.

Passages. Each matching sentence is given with the sentence before and the sentence after it
in the same paragraph. One further sentence is added after the window only when the matching
sentence matched no term but the name as written and ends in a citation. Windows of one
paragraph that overlap or touch are merged, so no sentence is given twice. A matching table
row line is given alone: the registered rendering already writes the table's label and caption
and each cell's column header on the line. A row with no matching sentence or table line has
the status `no_local_passage_found`; the search is never widened.

Reference entries. The registered rendering drops the reference list. Where a sentence of a
passage carries a citation linked in the XML (`<xref ref-type="bibr">`, numeric or
author-year), the passage lists the linked entries of the paper's own reference list, each
with its label, its text and its DOI and PMID where the XML gives them. The entries are read
from the XML fetch_fulltext.py stored; nothing else is fetched. A paper whose body cannot be
rendered with its citation links kept apart (the links change the registered rendering of a
repeated table header) gets its passages without reference entries, and is counted.

Every passage keeps its section title, the indices of its first and last sentence in the
document, the line of the rendered body, and the terms each sentence matched; every paper file
keeps the sha256 of its source document and of its reference list.

Outputs. `--out`/<file name>.json per paper (the record, the source, and per queue row the
side, the name as written, the mapping state, the candidates and the passages: no protein,
outcome, family, pair, relation or count field); `--out`/passages_summary.json (counts);
`--citations`/sources/ and `--citations`/claims/ (the source document of each paper and its
reference list as pinned artifacts for the `citations` CLI, with empty claims files).

Usage: uv run scripts/coding_passages.py --queue <manual_coding_queue.csv> \\
           --records <search_records.jsonl> [...] --abstracts <eligible_abstracts.jsonl> [...] \\
           --fulltext <folder of fetch_fulltext.py --pmid outputs> \\
           --out outputs/manual_coding/<run>/passages --citations outputs/citations/manual_coding_<run>
"""

import argparse
import collections
import copy
import csv
import functools
import hashlib
import json
import pathlib
import re
import unicodedata
import xml.etree.ElementTree as ET

import yaml

from dataset_relations import DICTIONARY
from fetch_fulltext import RAW, drop_abstracts, render

ABBREVIATIONS = ("et al.", "e.g.", "i.e.", "vs.", "cf.", "Fig.", "Figs.", "Ref.", "Refs.",
                 "Eq.", "Eqs.", "No.", "no.", "Dr.", "St.", "Suppl.", "Supp.", "approx.")
MARK_OPEN, MARK_CLOSE = "", ""
MARKER = re.compile(f"{MARK_OPEN}(\\d+){MARK_CLOSE}")
# After the closing punctuation a sentence may carry linked citations (superscript numbers).
BOUNDARY = re.compile(f"[.!?][\"'”’)\\]]*(?:[\\d,;–-]*{MARK_OPEN}\\d+{MARK_CLOSE})*\\s+"
                      f"(?=[A-Z0-9\\[(\"“‘])")
DASHES = dict.fromkeys(map(ord, "‐‑‒–—−"), "-")
GROUPING = re.compile(r"(?<=\d)[,\s](?=\d{3}(?!\d))")
INTEGER = re.compile(r"\d{1,3}(?:,\d{3})+|\d{4,}")
AUTHOR_YEAR = re.compile(r"([A-Z][A-Za-z'’-]+) [A-Z]{1,3}(?: et al\.?)?,? ((?:19|20)\d{2})")
NAME = "name_as_written"
DEFINITION_FIELDS = ("side", "name", "aliases", "release", "cohort_components", "ancestry",
                     "sample_size", "platform", "source_citation", "source_identifier")
NO_PASSAGE = "no_local_passage_found"


class PassageError(Exception):
    """A source document is missing or does not have the bytes the fetch recorded."""


@functools.lru_cache(maxsize=8192)
def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(DASHES).casefold()
    return " ".join(text.split())


def strip_marks(text: str) -> str:
    return " ".join(MARKER.sub("", text).split())


def sentences(text: str) -> list[str]:
    """The sentences of one paragraph, in order; joined by one space they give the paragraph."""
    out, start = [], 0
    for m in BOUNDARY.finditer(text):
        head = strip_marks(text[start:m.end()])
        if head.endswith(ABBREVIATIONS) or re.search(r"(?:^|[\s(])[A-Z]\.$", head):
            continue
        out.append(text[start:m.end()].strip())
        start = m.end()
    if text[start:].strip():
        out.append(text[start:].strip())
    return out


def name_terms(name: str) -> list[tuple[str, str]]:
    parts = [name, *re.split(r"[()]", name)]
    return [(NAME, p) for p in dict.fromkeys(" ".join(p.split()) for p in parts) if len(p) >= 3]


def dictionary_terms(row: dict) -> list[tuple[str, str]]:
    """(field, term) pairs of one dictionary row. A `source_citation` term is "surname|year"."""
    terms = [("name", row["name"])]
    terms += [("aliases", a.strip()) for a in row["aliases"].split("|") if a.strip()]
    release = row["release"].strip()
    if (len(release.split()) <= 2 and re.search(r"[A-Za-z]", release)
            and re.search(r"\d", release)):
        terms.append(("release", release))
    terms += [("source_citation", f"{s}|{y}") for s, y in AUTHOR_YEAR.findall(row["source_citation"])]
    for part in row["source_identifier"].split(";"):
        part = re.sub(r"^(?:doi|pmid)\s*:\s*", "", part.strip(), flags=re.IGNORECASE)
        if part:
            terms.append(("source_identifier", part))
    terms += [("sample_size", n.replace(",", "")) for n in INTEGER.findall(row["sample_size"])]
    return list(dict.fromkeys(terms))


@functools.lru_cache(maxsize=None)
def bounded(term: str) -> re.Pattern:
    return re.compile(f"(?<![0-9a-z]){re.escape(normalize(term))}(?![0-9a-z])")


def matches(term: tuple[str, str], sentence: str) -> bool:
    """Whether the (field, term) pair occurs in the sentence."""
    field, text = term
    norm = normalize(sentence)
    if field == "sample_size":
        return bool(re.search(f"(?<![0-9]){text}(?![0-9])", GROUPING.sub("", norm)))
    if field == "source_citation":
        return all(bounded(part).search(norm) for part in text.split("|"))
    return bool(bounded(text).search(norm))


def reference_entries(root: ET.Element) -> dict[str, dict]:
    """The paper's reference list: entry id -> label, text, DOI and PMID."""
    out = {}
    for ref in root.iter("ref"):
        label = ref.find("label")
        cit = next((c for c in ref.iter() if c.tag in ("mixed-citation", "element-citation",
                                                       "citation")), ref)
        text = " ".join(" ".join(piece.split()) for piece in cit.itertext() if piece.strip())
        ids = {p.get("pub-id-type"): "".join(p.itertext()).strip() for p in ref.iter("pub-id")}
        shown = (" ".join("".join(label.itertext()).split()).strip(".[]() ")
                 if label is not None else "") or ref.get("id", "")
        out[ref.get("id", shown)] = {"label": shown, "entry": text, "doi": ids.get("doi"),
                                     "pmid": ids.get("pmid")}
    return out


def table_line(line: str) -> bool:
    """A line the registered rendering wrote for a table row or a table footnote."""
    if not line.startswith("[") or "]" not in line:
        return False
    label = line[1:line.index("]")]
    return label.casefold().startswith("tab") or label.endswith("footnote") or " | " in line


def full_text_units(xml: bytes, body: str) -> tuple[list[dict], dict[str, dict]]:
    """The units (sentences and table lines) of a rendered body, each with the reference-list
    entries its citations link to, and the reference list. Raises unless the XML renders to
    exactly `body`, the text the fetch stored. Where the body cannot be rendered with its
    citation links kept apart, the units carry no entries and the reference list is empty."""
    root = ET.fromstring(xml)
    references = reference_entries(root)
    drop_abstracts(root)
    marked = copy.deepcopy(root.find("body"))
    links: list[list[str]] = []
    for el in marked.iter("xref"):
        if el.get("ref-type") == "bibr":
            links.append((el.get("rid") or "").split())
            el.text = f"{el.text or ''}{MARK_OPEN}{len(links) - 1}{MARK_CLOSE}"
    plain: list[str] = []
    render(copy.deepcopy(root.find("body")), plain)
    if "\n".join(plain) != body:
        raise PassageError("the stored XML does not render to the stored body")
    lines: list[str] = []
    render(marked, lines)
    if "\n".join(strip_marks(line) for line in lines) != body:
        # The citation marks changed the rendering (a table header repeated with a citation):
        # the stored body is used as it is and the paper gets no reference entries.
        lines, references = plain, {}
    units, section = [], ""
    for number, line in enumerate(lines):
        if line.startswith("## "):
            section = strip_marks(line[3:])
            continue
        table = table_line(strip_marks(line))
        for part in ([line] if table else sentences(line)):
            cited = [rid for k in MARKER.findall(part) for rid in links[int(k)]]
            units.append({"index": len(units), "line": number, "section": section,
                          "kind": "table" if table else "prose", "text": strip_marks(part),
                          "ends_in_citation": bool(re.search(
                              f"{MARK_CLOSE}[.!?\"'”’)\\]\\s]*$", part)),
                          "references": list(dict.fromkeys(r for r in cited if r in references))})
    return units, references


def abstract_units(abstract: str) -> list[dict]:
    return [{"index": i, "line": 0, "section": "Abstract", "kind": "prose", "text": s,
             "ends_in_citation": False, "references": []}
            for i, s in enumerate(sentences(" ".join(abstract.split())))]


def passages(units: list[dict], name: str, candidate_rows: list[dict],
             references: dict[str, dict]) -> list[dict]:
    """The passages of one queue row: windows around every unit a term matches."""
    terms = name_terms(name) + [t for row in candidate_rows for t in dictionary_terms(row)]
    terms = list(dict.fromkeys(terms))
    hits = {u["index"]: [t for t in terms if matches(t, u["text"])] for u in units}
    hits = {i: found for i, found in hits.items() if found}
    windows: list[list[int]] = []
    for i in sorted(hits):
        unit = units[i]
        if unit["kind"] == "table":
            windows.append([i, i])
            continue

        def same(j: int) -> bool:
            return (0 <= j < len(units) and units[j]["line"] == unit["line"]
                    and units[j]["kind"] == "prose")

        lo = i - 1 if same(i - 1) else i
        hi = i + 1 if same(i + 1) else i
        only_name = all(field == NAME for field, _ in hits[i])
        if only_name and unit["ends_in_citation"] and same(i + 2):
            hi = i + 2
        last = windows[-1] if windows else None
        if last and units[last[0]]["kind"] == "prose" and same(last[1]) and lo <= last[1] + 1:
            last[1] = max(last[1], hi)
        else:
            windows.append([lo, hi])
    out = []
    for n, (lo, hi) in enumerate(windows, 1):
        inside = units[lo:hi + 1]
        cited = list(dict.fromkeys(r for u in inside for r in u["references"]))
        out.append({
            "passage_id": f"p{n:03d}", "kind": inside[0]["kind"], "section": inside[0]["section"],
            "line": inside[0]["line"], "first_sentence": lo, "last_sentence": hi,
            "sentences": [u["text"] for u in inside],
            "matched": [{"sentence": u["index"],
                         "terms": [{"field": f, "term": t} for f, t in hits[u["index"]]]}
                        for u in inside if u["index"] in hits],
            "references": [dict(references[r], id=r) for r in cited]})
    return out


def file_name(record_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", record_id)


def reference_text(references: dict[str, dict]) -> str:
    return "".join(f"[ref {r['label']}] {r['entry']}\n" for r in references.values())


def pinned(folder: pathlib.Path, name: str, text: str, note: str, url: str = "") -> dict:
    """Write one source document and its empty claims file; returns its description."""
    src = folder / "sources" / f"{name}.txt"
    src.write_text(text)
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    claims = folder / "claims" / f"{name}.yaml"
    claims.write_text(yaml.safe_dump({
        "source": {"citation": name, "local": f"sources/{src.name}", "sha256": digest,
                   **({"url": url} if url else {}), "note": note}, "claims": {}}, sort_keys=False, allow_unicode=True))
    return {"document": f"sources/{src.name}", "claims_file": f"claims/{claims.name}",
            "sha256": digest}


def paper(record_id: str, rows: list[dict], dictionary: dict[tuple[str, str], dict],
          abstract: str, fetched: dict | None, xml: bytes | None,
          citations: pathlib.Path) -> dict:
    """The coder's file for one paper."""
    name = file_name(record_id)
    if fetched:
        units, references = full_text_units(xml, fetched["body"])
        source = {"kind": "full_text", **pinned(
            citations, name, fetched["body"], "body as scripts/fetch_fulltext.py rendered it",
            fetched["source_url"])}
        source["references"] = None if not references else pinned(
            citations, f"{name}.references", reference_text(references),
            "reference list of the stored Europe PMC XML", fetched["source_url"])
    else:
        units, references = abstract_units(abstract), {}
        source = {"kind": "abstract", **pinned(citations, name, abstract,
                                               "abstract exactly as sent to the extractor")}
        source["references"] = None
    out_rows = []
    for r in rows:
        candidates = [c for c in r["candidates"].split("|") if c]
        found = passages(units, r["name_as_written"],
                         [dictionary[(r["side"], c)] for c in candidates
                          if (r["side"], c) in dictionary], references)
        out_rows.append({"side": r["side"], "name_as_written": r["name_as_written"],
                         "mapping_state": r["mapping_state"], "candidates": candidates,
                         "status": "passages" if found else NO_PASSAGE, "passages": found})
    return {"record_id": record_id, "source": source, "rows": out_rows}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", type=pathlib.Path, required=True)
    ap.add_argument("--records", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--abstracts", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--fulltext", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--citations", type=pathlib.Path, required=True)
    a = ap.parse_args()
    for folder in (a.out, a.citations):
        if folder.exists():
            raise PassageError(f"{folder} exists; passages are written once")
    with DICTIONARY.open(newline="") as f:
        dictionary = {(r["side"], r["name"]): r for r in csv.DictReader(f)}
    records: dict[str, dict] = {}
    for p in a.records:
        for line in p.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                records.setdefault(r["record_id"], r)
    abstracts = {r["pmid"]: r["abstract"] for p in a.abstracts
                 for r in map(json.loads, (l for l in p.read_text().splitlines() if l.strip()))}
    by_paper: dict[str, list[dict]] = collections.defaultdict(list)
    with a.queue.open(newline="") as f:
        for r in csv.DictReader(f):
            by_paper[r["record_id"]].append(r)
    if len({file_name(rid) for rid in by_paper}) != len(by_paper):
        raise PassageError("two records share a file name")
    a.out.mkdir(parents=True)
    (a.citations / "sources").mkdir(parents=True)
    (a.citations / "claims").mkdir()
    counts: collections.Counter = collections.Counter()
    for rid in sorted(by_paper):
        target = a.fulltext / f"pmid{records[rid].get('pmid')}.jsonl"
        fetched = json.loads(target.read_text().splitlines()[0]) if target.is_file() else None
        xml = None
        if fetched:
            xml = (RAW / f"{fetched['pmcid']}.xml").read_bytes()
            if hashlib.sha256(xml).hexdigest() != fetched["raw_sha256"]:
                raise PassageError(f"{rid}: the stored XML differs from the fetched one")
        made = paper(rid, by_paper[rid], dictionary, abstracts.get(rid, ""), fetched, xml,
                     a.citations)
        (a.out / f"{file_name(rid)}.json").write_text(
            json.dumps(made, indent=1, ensure_ascii=False) + "\n")
        kind = made["source"]["kind"]
        counts[f"papers_{kind}"] += 1
        counts["papers_full_text_without_reference_entries"] += (
            kind == "full_text" and made["source"]["references"] is None)
        for row in made["rows"]:
            counts[f"rows_{kind}"] += 1
            counts[f"rows_{row['status']}_{kind}"] += 1
            counts[f"rows_{row['status']}"] += 1
            counts["passages"] += len(row["passages"])
            counts["passages_with_a_reference_entry"] += sum(
                bool(p["references"]) for p in row["passages"])
            counts["rows_with_a_reference_entry"] += any(p["references"] for p in row["passages"])
    summary = {"queue": str(a.queue), "papers": len(by_paper),
               "rows": sum(map(len, by_paper.values())), **dict(sorted(counts.items()))}
    (a.out / "passages_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
