# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "pydantic==2.13.5"]
# ///
"""Fetch the open-access full text of a paper and render its body and main tables as the text
the full-text prompt receives, with the abstract removed.

Source: the Europe PMC open-access XML (`/rest/<PMCID>/fullTextXML`) of the paper's PubMed
record, the only registered full-text source (no publisher website or preprint server).
Rendering, fixed so that evidence spans can be pinned:

    - only `<body>` is read; `<front>` (title page and abstract), `<back>` (references,
      acknowledgements, notes) and every `<abstract>` element wherever it occurs are dropped;
      supplementary files are not fetched;
    - each section title becomes a line `## <title>`; each paragraph becomes one line;
    - each main-text table becomes one line per body row, `[<label>. <caption>] <header>:
      <cell> | <header>: <cell> | ...`, so every row line carries its caption and column
      headers (row and column spans expanded; stacked header rows joined with " / ");
      table footnotes become one line `[<label> footnote] <text>`;
    - whitespace inside a line is collapsed to single spaces.

`--before 2019-01-01` refuses any paper whose Europe PMC first publication date is on or after
that day (the development rule). The raw XML is written to outputs/raw/fulltext/ with its sha256;
the rendered records go to the output file, one JSON line per paper (pmid, pmcid, title, body,
body_sha256, source_url, raw_sha256, first_publication_date, retrieved_utc).

No email or other identifier is sent.

Census (`--census`, stage 6, after the freeze): for every eligible family of
`families_meta.json`, each registry record takes a status. A record that is not a journal record
with a PMID has no PubMed record to match: `no_open_access_full_text`. A record whose extracted
abstract did not come from PubMed is `version_unmatched`. Any other record is requested, and is
`fetched` or, when Europe PMC flags no open access, gives no PMCID, returns no XML or the XML
has no body, `no_open_access_full_text`. A family is `fetched` when any of its registry records
is (the first in record order is used), else `version_unmatched` when any is, else
`no_open_access_full_text`. Each record's result is written before the next request
(`<out>/records/<record id>.json`), so a stopped run resumes; `fulltext_bodies.jsonl` (the input
of run_extraction.py --task fulltext_extraction; `pmid` holds the record id) and
`fulltext_status.json` are written at the end. `--census --before 2019-01-01` runs the census
before the freeze on records that are all first public before that day (the smoke run): a
record first public on or after it raises before any request.

Usage: uv run scripts/fetch_fulltext.py --pmid 30111768 --before 2019-01-01 \
           --out prompts/dev_fulltext.jsonl
       uv run scripts/fetch_fulltext.py --census --families-meta <families_meta.json> \
           --screening-records <screening_records.jsonl> [...] --out outputs/fulltext/<run>
"""

import argparse
import datetime
import hashlib
import json
import pathlib
import xml.etree.ElementTree as ET

import httpx

from run_search import check_frozen
from smoke_guard import check_smoke_output

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
RAW = EXP / "outputs" / "raw" / "fulltext"
SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
FULLTEXT = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"


FETCHED = "fetched"
NO_FULL_TEXT = "no_open_access_full_text"
VERSION_UNMATCHED = "version_unmatched"


class FullTextError(Exception):
    """A date outside the allowed range, an ambiguous record, or an output that exists."""


class NoOpenAccess(FullTextError):
    """Europe PMC holds no open-access full text with a body for the record."""


def text_of(el: ET.Element) -> str:
    return " ".join("".join(el.itertext()).split())


def drop_abstracts(root: ET.Element) -> None:
    for parent in root.iter():
        for child in list(parent):
            if child.tag == "abstract":
                parent.remove(child)


def grid(rows: list[ET.Element]) -> list[list[str]]:
    """Expand rowspan and colspan so every row has one text per column."""
    out: list[list[str]] = []
    carry: dict[int, tuple[str, int]] = {}
    for tr in rows:
        row: list[str] = []
        cells = [c for c in tr if c.tag in ("th", "td")]
        col = 0
        while cells or col in carry:
            if col in carry:
                text, left = carry.pop(col)
                row.append(text)
                if left > 1:
                    carry[col] = (text, left - 1)
                col += 1
                continue
            c = cells.pop(0)
            text = text_of(c)
            span = int(c.get("colspan", "1") or 1)
            down = int(c.get("rowspan", "1") or 1)
            for _ in range(span):
                row.append(text)
                if down > 1:
                    carry[col] = (text, down - 1)
                col += 1
        out.append(row)
    return out


def render_table(tw: ET.Element) -> list[str]:
    label = text_of(tw.find("label")) if tw.find("label") is not None else "Table"
    cap_el = tw.find("caption")
    caption = text_of(cap_el) if cap_el is not None else ""
    prefix = f"[{label}. {caption}]" if caption else f"[{label}]"
    lines = []
    table = tw.find(".//table")
    if table is not None:
        head = table.find("thead")
        head_grid = grid(head.findall("tr")) if head is not None else []
        n_cols = max((len(r) for r in head_grid), default=0)
        headers = []
        for i in range(n_cols):
            parts = []
            for r in head_grid:
                if i < len(r) and r[i] and r[i] not in parts:
                    parts.append(r[i])
            headers.append(" / ".join(parts))
        body_rows = [tr for tb in table.findall("tbody") for tr in tb.findall("tr")]
        if not body_rows:
            body_rows = [tr for tr in table.findall("tr")]
        for cells in grid(body_rows):
            parts = [f"{headers[i]}: {c}" if i < len(headers) and headers[i] else c
                     for i, c in enumerate(cells)]
            lines.append(f"{prefix} " + " | ".join(parts))
    foot = tw.find("table-wrap-foot")
    if foot is not None and text_of(foot):
        lines.append(f"[{label} footnote] {text_of(foot)}")
    return lines


def render(el: ET.Element, out: list[str]) -> None:
    for child in el:
        if child.tag == "sec":
            t = child.find("title")
            if t is not None and text_of(t):
                out.append(f"## {text_of(t)}")
            render(child, out)
        elif child.tag == "p":
            inner_tables = child.findall(".//table-wrap")
            for tw in inner_tables:
                for p in child.iter():
                    if tw in list(p):
                        p.remove(tw)
            if text_of(child):
                out.append(text_of(child))
            for tw in inner_tables:
                out.extend(render_table(tw))
        elif child.tag == "table-wrap":
            out.extend(render_table(child))
        elif child.tag in ("title", "fig", "fig-group", "supplementary-material"):
            continue
        else:
            render(child, out)


def fetch_one(client: httpx.Client, pmid: str, before: datetime.date | None = None) -> dict:
    """The rendered record of one PubMed record's open-access full text. Raises
    `NoOpenAccess` when Europe PMC holds no open-access full text with a body for it."""
    r = client.get(SEARCH, params={"query": f"EXT_ID:{pmid} AND SRC:MED",
                                   "format": "json", "resultType": "core"})
    r.raise_for_status()
    hits = r.json()["resultList"]["result"]
    if len(hits) != 1:
        raise FullTextError(f"{pmid}: {len(hits)} Europe PMC records")
    meta = hits[0]
    first = datetime.date.fromisoformat(meta["firstPublicationDate"])
    if before and first >= before:
        raise FullTextError(f"{pmid}: first public {first}, not before {before}")
    if meta.get("isOpenAccess") != "Y" or not meta.get("pmcid"):
        raise NoOpenAccess(f"{pmid}: no open-access full text in Europe PMC")
    url = FULLTEXT.format(pmcid=meta["pmcid"])
    x = client.get(url)
    if x.status_code == 404:
        raise NoOpenAccess(f"{pmid}: Europe PMC returns no full-text XML for {meta['pmcid']}")
    x.raise_for_status()
    raw_sha = hashlib.sha256(x.content).hexdigest()
    RAW.mkdir(parents=True, exist_ok=True)
    target = RAW / f"{meta['pmcid']}.xml"
    if target.exists() and target.read_bytes() != x.content:
        raise FullTextError(f"{target} exists with other bytes; archive it before refetching")
    target.write_bytes(x.content)
    root = ET.fromstring(x.content)
    drop_abstracts(root)
    body = root.find("body")
    if body is None:
        raise NoOpenAccess(f"{pmid}: XML has no <body>")
    lines: list[str] = []
    render(body, lines)
    text = "\n".join(lines)
    return {"pmid": pmid, "pmcid": meta["pmcid"], "title": meta["title"], "body": text,
            "body_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "source_url": url, "raw_sha256": raw_sha,
            "first_publication_date": first.isoformat(),
            "retrieved_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")}


def record_status(record: dict) -> str | None:
    """The status a registry record takes without any request, or None when its full text is
    to be requested: a record that is not a journal record with a PMID has no PubMed record to
    match (`no_open_access_full_text`); a record whose extracted abstract did not come from
    PubMed is not the version Europe PMC's full text belongs to (`version_unmatched`)."""
    if record["kind"] != "journal" or not record.get("pmid"):
        return NO_FULL_TEXT
    if record.get("abstract_source") != "pubmed":
        return VERSION_UNMATCHED
    return None


def family_status(statuses: list[str]) -> str:
    """A family's status from its registry records': `fetched` when any was fetched, else
    `version_unmatched` when any is, else `no_open_access_full_text`."""
    for status in (FETCHED, VERSION_UNMATCHED):
        if status in statuses:
            return status
    return NO_FULL_TEXT


def census(client: httpx.Client, meta: dict[str, dict], records: dict[str, dict],
           out: pathlib.Path, before: datetime.date | None = None) -> dict:
    """Fetch the full text of every eligible family's registry records. Each record's result
    is written before the next request, and a record already written is not requested again.
    `before` (the smoke run) refuses, ahead of any request, a census holding a registry record
    first public on or after that day."""
    if before:
        late = sorted(rid for m in meta.values() for rid in m["registry_records"]
                      if datetime.date.fromisoformat(records[rid]["first_public"]["value"])
                      >= before)
        if late:
            raise FullTextError(f"records first public on or after {before}: {late[:5]}")
    done = out / "records"
    done.mkdir(parents=True, exist_ok=True)
    families: dict[str, dict] = {}
    for fam, m in sorted(meta.items()):
        results = []
        for rid in m["registry_records"]:
            target = done / f"{rid}.json"
            if not target.exists():
                status = record_status(records[rid])
                result: dict = {"record_id": rid, "status": status, "reason": None}
                if status is None:
                    try:
                        body = fetch_one(client, records[rid]["pmid"], before)
                        result |= {"status": FETCHED, "body": {**body, "pmid": rid}}
                    except NoOpenAccess as e:
                        result |= {"status": NO_FULL_TEXT, "reason": str(e)}
                target.write_text(json.dumps(result, ensure_ascii=False))
            results.append(json.loads(target.read_text()))
        fetched = [r for r in results if r["status"] == FETCHED]
        families[fam] = {"status": family_status([r["status"] for r in results]),
                         "window": m["window"],
                         "full_text_record": fetched[0]["record_id"] if fetched else None,
                         "records": [{k: r[k] for k in ("record_id", "status", "reason")}
                                     for r in results]}
    bodies = [json.loads((done / f"{f['full_text_record']}.json").read_text())["body"]
              for f in families.values() if f["full_text_record"]]
    (out / "fulltext_bodies.jsonl").write_text(
        "".join(json.dumps(b, ensure_ascii=False) + "\n" for b in bodies))
    counts: dict[str, dict[str, int]] = {}
    for f in families.values():
        by = counts.setdefault(f["window"], {})
        by[f["status"]] = by.get(f["status"], 0) + 1
    status = {"written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
              "families_by_window_and_status": counts, "families": families}
    (out / "fulltext_status.json").write_text(json.dumps(status, indent=1))
    return status


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pmid", action="append")
    ap.add_argument("--before", type=datetime.date.fromisoformat)
    ap.add_argument("--census", action="store_true",
                    help="stage 6: every eligible family of --families-meta")
    ap.add_argument("--families-meta", type=pathlib.Path)
    ap.add_argument("--screening-records", type=pathlib.Path, nargs="*", default=[])
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.census:
        if not a.before or a.before > datetime.date(2019, 1, 1):
            check_frozen()
        # The census of a smoke registry goes under its smoke label, and no other census does.
        check_smoke_output(a.families_meta.parent, a.out.resolve().name)
        records = {r["record_id"]: r for p in a.screening_records
                   for r in map(json.loads, (l for l in p.read_text().splitlines() if l.strip()))}
        with httpx.Client(timeout=120, follow_redirects=True) as client:
            status = census(client, json.loads(a.families_meta.read_text()), records, a.out,
                            a.before)
        print(json.dumps(status["families_by_window_and_status"], indent=1))
        return
    if not a.pmid:
        ap.error("--pmid or --census is required")
    if a.out.exists():
        raise FullTextError(f"{a.out} exists; records are never overwritten")
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        records = [fetch_one(client, pmid, a.before) for pmid in a.pmid]
    a.out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
    for r in records:
        print(r["pmid"], r["pmcid"], len(r["body"].split()), "words", r["body_sha256"][:12])


if __name__ == "__main__":
    main()
