# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "pydantic==2.13.5"]
# ///
"""Run the registered queries on PubMed, Europe PMC and OpenAlex and keep every raw response.

Streams, per source:

    pubmed    one `esearch` response per query and window (all PMIDs), then `efetch` XML for
              the union of the PMIDs in batches of 200; after the other two sources, `efetch`
              again (`efetch_linked`) for the PMIDs they returned that no PubMed query did, so
              that every record with a PMID has its PubMed abstract
    epmc      `search`, resultType=core, synonym=false, pageSize=1000, cursorMark paging
    openalex  `/works`, the query as the `title_and_abstract.search.exact` filter, a fixed
              `select`, per_page=100, cursor paging

Every HTTP exchange is written to the run directory before it is parsed: the response body as
its own gzip file (written with mtime 0, so equal bodies give equal files), and one line of
`manifest.jsonl` with the stream, page, URL, status, UTC start and finish times, and the byte
count and sha256 of the uncompressed body. A failed exchange is kept the same way. The manifest
is the checkpoint: a stopped run resumes each stream after its last stored page (Europe PMC and
OpenAlex from the cursor that page returned), and a completed stream is never requested again.
`counts.json` is rewritten after every stream: the count each source reported, the records
retrieved and the pages, per query and window.

The search runs on one day. The UTC date of the first start is the search date (the end of the
update window); a resume on a later UTC date raises. The run refuses to start while PREREG.md
is not frozen, unless `--smoke` runs the same code on a window that ends before 2019: the months
of SMOKE_WINDOW, or the dates given by `--smoke-start` and `--smoke-end`, which must lie between
SMOKE_EARLIEST and SMOKE_LATEST. A smoke run is stored under outputs/raw/search_smoke/, in the
folder named by `--smoke-label` (default: the UTC date).

No email address is sent. An OpenAlex API key, if OPEN_ALEX_API_KEY is set, travels in the
Authorization header and is never written.

Usage:
    uv run scripts/run_search.py                 (after the freeze)
    uv run scripts/run_search.py --smoke         (pre-2019 records only)
    uv run scripts/run_search.py --smoke --smoke-start 2018-06-01 --smoke-end 2018-06-30 \
        --smoke-label <label>
"""

import argparse
import datetime
import gzip
import hashlib
import json
import os
import pathlib
import time
import xml.etree.ElementTree as ET
from typing import Callable

import httpx
from pydantic import BaseModel

import search_queries as sq

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
PREREG = EXP / "PREREG.md"
RAW = EXP / "outputs" / "raw" / "search"
RAW_SMOKE = EXP / "outputs" / "raw" / "search_smoke"

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
OPENALEX = "https://api.openalex.org/works"
OPENALEX_SELECT = ("id,doi,ids,display_name,publication_date,publication_year,type,language,"
                   "authorships,primary_location,abstract_inverted_index")
PUBMED_MAX_IDS = 9999
EFETCH_BATCH = 200
EPMC_PAGE = 1000
OPENALEX_PAGE = 100
MAX_TRIES = 5
PAUSE = {"pubmed": 0.4, "epmc": 0.3, "openalex": 0.2}
SMOKE_WINDOW = (datetime.date(2018, 11, 1), datetime.date(2018, 12, 31))
SMOKE_EARLIEST, SMOKE_LATEST = datetime.date(2014, 1, 1), datetime.date(2018, 12, 31)


class SearchRunError(Exception):
    """The run cannot proceed: not frozen, a date change, an exhausted endpoint, a count gap."""


class Exchange(BaseModel):
    source: str
    stream: str
    page: int
    url: str
    status: int | None
    started_utc: str
    finished_utc: str
    bytes: int
    sha256: str
    file: str


class StreamDone(BaseModel):
    source: str
    stream: str
    event: str = "stream_complete"
    reported: int
    retrieved: int
    pages: int


def now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="milliseconds")


def read_manifest(run_dir: pathlib.Path) -> list[dict]:
    path = run_dir / "manifest.jsonl"
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() \
        else []


def append_manifest(run_dir: pathlib.Path, line: BaseModel) -> None:
    with (run_dir / "manifest.jsonl").open("a") as f:
        f.write(line.model_dump_json() + "\n")
        f.flush()
        os.fsync(f.fileno())


def fetch(client: httpx.Client, run_dir: pathlib.Path, source: str, stream: str, page: int,
          url: str, params: dict, suffix: str) -> bytes:
    """One GET, retried on 429, 5xx and transport errors; every attempt is stored."""
    headers = {}
    if source == "openalex" and os.environ.get("OPEN_ALEX_API_KEY"):
        headers["Authorization"] = f"Bearer {os.environ['OPEN_ALEX_API_KEY']}"
    request = client.build_request("GET", url, params=params, headers=headers)
    if source == "openalex" and len(str(request.url).encode()) > sq.OPENALEX_MAX_URL_BYTES:
        raise SearchRunError(f"{stream}: OpenAlex request URL exceeds "
                             f"{sq.OPENALEX_MAX_URL_BYTES} bytes")
    for attempt in range(1, MAX_TRIES + 1):
        started = now()
        try:
            response = client.send(request)
            status, body = response.status_code, response.content
        except httpx.HTTPError as e:
            status, body = None, f"{type(e).__name__}: {e}".encode()
        ok = status == 200
        name = f"page_{page:04d}{suffix}" if ok else f"page_{page:04d}.try{attempt}.failed"
        target = run_dir / source / stream / f"{name}.gz"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(gzip.compress(body, mtime=0))
        append_manifest(run_dir, Exchange(
            source=source, stream=stream, page=page, url=str(request.url), status=status,
            started_utc=started, finished_utc=now(), bytes=len(body),
            sha256=hashlib.sha256(body).hexdigest(),
            file=str(target.relative_to(run_dir))))
        time.sleep(PAUSE[source])
        if ok:
            return body
        if status is not None and status < 500 and status != 429:
            break
        time.sleep(min(60, 2 ** attempt))
    raise SearchRunError(f"{source} {stream} page {page}: no 200 after {attempt} tries "
                         f"(last status {status})")


def read_body(run_dir: pathlib.Path, line: dict) -> bytes:
    """The stored response body of a manifest line, checked against the manifest hash."""
    body = gzip.decompress((run_dir / line["file"]).read_bytes())
    if hashlib.sha256(body).hexdigest() != line["sha256"]:
        raise SearchRunError(f"{line['file']}: content differs from the manifest hash")
    return body


def stored_pages(manifest: list[dict], run_dir: pathlib.Path, source: str,
                 stream: str) -> list[bytes]:
    """Bodies of the stream's stored pages, in page order."""
    lines = sorted((l for l in manifest if l.get("source") == source
                    and l.get("stream") == stream and l.get("status") == 200),
                   key=lambda l: l["page"])
    if [l["page"] for l in lines] != list(range(1, len(lines) + 1)):
        raise SearchRunError(f"{source} {stream}: stored pages are not 1..n")
    return [read_body(run_dir, l) for l in lines]


def is_done(manifest: list[dict], source: str, stream: str) -> dict | None:
    return next((l for l in manifest if l.get("event") == "stream_complete"
                 and l["source"] == source and l["stream"] == stream), None)


def run_paged(client: httpx.Client, run_dir: pathlib.Path, source: str, stream: str, url: str,
              first: dict, read: Callable[[bytes], tuple[int, int, dict | None]]) -> dict:
    """Page a stream to its end. `read(body)` returns (reported total, records on the page,
    parameters that replace the cursor for the next page, or None at the end)."""
    manifest = read_manifest(run_dir)
    done = is_done(manifest, source, stream)
    if done:
        return done
    bodies = stored_pages(manifest, run_dir, source, stream)
    params, reported, retrieved = dict(first), 0, 0
    for body in bodies:
        reported, n, nxt = read(body)
        retrieved += n
        params = {**first, **nxt} if nxt else None
    page = len(bodies)
    while params is not None:
        page += 1
        body = fetch(client, run_dir, source, stream, page, url, params, ".json")
        total, n, nxt = read(body)
        reported = total if page == 1 else reported
        retrieved += n
        params = {**first, **nxt} if nxt else None
    done = StreamDone(source=source, stream=stream, reported=reported, retrieved=retrieved,
                      pages=page)
    append_manifest(run_dir, done)
    return done.model_dump()


def read_epmc(body: bytes) -> tuple[int, int, dict | None]:
    d = json.loads(body)
    results = d.get("resultList", {}).get("result", [])
    nxt = d.get("nextCursorMark")
    more = bool(results) and nxt and nxt != d.get("request", {}).get("cursorMark")
    return d["hitCount"], len(results), ({"cursorMark": nxt} if more else None)


def read_openalex(body: bytes) -> tuple[int, int, dict | None]:
    d = json.loads(body)
    nxt = d["meta"].get("next_cursor")
    return d["meta"]["count"], len(d["results"]), ({"cursor": nxt} if nxt and d["results"]
                                                   else None)


def run_pubmed_esearch(client: httpx.Client, run_dir: pathlib.Path, stream: str,
                       term: str) -> dict:
    manifest = read_manifest(run_dir)
    done = is_done(manifest, "pubmed", stream)
    if done:
        return done
    bodies = stored_pages(manifest, run_dir, "pubmed", stream)
    body = bodies[0] if bodies else fetch(
        client, run_dir, "pubmed", stream, 1, ESEARCH,
        {"db": "pubmed", "term": term, "retmode": "json", "retmax": PUBMED_MAX_IDS}, ".json")
    result = json.loads(body)["esearchresult"]
    if "ERROR" in result or result.get("errorlist", {}).get("phrasesnotfound"):
        raise SearchRunError(f"pubmed {stream}: esearch reported {result.get('ERROR')} "
                             f"{result.get('errorlist')}")
    reported = int(result["count"])
    if reported > PUBMED_MAX_IDS:
        raise SearchRunError(f"pubmed {stream}: {reported} records exceed one esearch page")
    done = StreamDone(source="pubmed", stream=stream, reported=reported,
                      retrieved=len(result["idlist"]), pages=1)
    append_manifest(run_dir, done)
    return done.model_dump()


def pubmed_ids(run_dir: pathlib.Path) -> list[str]:
    """The union of the PMIDs in the stored esearch responses, in numeric order."""
    ids: set[str] = set()
    for l in read_manifest(run_dir):
        if l.get("source") == "pubmed" and l.get("status") == 200 \
                and l["stream"].startswith("esearch_"):
            ids.update(json.loads(read_body(run_dir, l))["esearchresult"]["idlist"])
    return sorted(ids, key=int)


def linked_pmids(run_dir: pathlib.Path) -> list[str]:
    """PMIDs on the stored Europe PMC and OpenAlex pages that no PubMed query returned."""
    found: set[str] = set()
    for l in read_manifest(run_dir):
        if l.get("status") != 200 or l["source"] == "pubmed":
            continue
        body = json.loads(read_body(run_dir, l))
        if l["source"] == "epmc":
            found.update(r["pmid"] for r in body.get("resultList", {}).get("result", [])
                         if r.get("pmid"))
        else:
            found.update(w["ids"]["pmid"].rstrip("/").rsplit("/", 1)[-1]
                         for w in body["results"] if (w.get("ids") or {}).get("pmid"))
    return sorted(found - set(pubmed_ids(run_dir)), key=int)


def run_pubmed_efetch(client: httpx.Client, run_dir: pathlib.Path, ids: list[str],
                      stream: str = "efetch") -> dict:
    manifest = read_manifest(run_dir)
    done = is_done(manifest, "pubmed", stream)
    if done:
        return done
    bodies = stored_pages(manifest, run_dir, "pubmed", stream)
    batches = [ids[i:i + EFETCH_BATCH] for i in range(0, len(ids), EFETCH_BATCH)]
    for page in range(len(bodies) + 1, len(batches) + 1):
        bodies.append(fetch(client, run_dir, "pubmed", stream, page, EFETCH,
                            {"db": "pubmed", "id": ",".join(batches[page - 1]),
                             "retmode": "xml"}, ".xml"))
    retrieved = sum(len(ET.fromstring(b).findall("./PubmedArticle"))
                    + len(ET.fromstring(b).findall("./PubmedBookArticle")) for b in bodies)
    done = StreamDone(source="pubmed", stream=stream, reported=len(ids), retrieved=retrieved,
                      pages=len(batches))
    append_manifest(run_dir, done)
    return done.model_dump()


def check_frozen() -> None:
    if not any(l.startswith("**Status:** FROZEN") for l in PREREG.read_text().splitlines()):
        raise SearchRunError("PREREG.md is not frozen; the search runs after the freeze")


def smoke_window(start: datetime.date | None, end: datetime.date | None
                 ) -> tuple[datetime.date, datetime.date]:
    """The window of a smoke run: SMOKE_WINDOW, or the two dates given, which must both lie
    before the registered window (SMOKE_EARLIEST to SMOKE_LATEST)."""
    if start is None and end is None:
        return SMOKE_WINDOW
    if start is None or end is None:
        raise SearchRunError("a smoke window needs both --smoke-start and --smoke-end")
    if not SMOKE_EARLIEST <= start <= end <= SMOKE_LATEST:
        raise SearchRunError(f"a smoke window lies between {SMOKE_EARLIEST} and {SMOKE_LATEST}; "
                             f"got {start} to {end}")
    return start, end


def start_run(run_dir: pathlib.Path, today: datetime.date, smoke: bool,
              window: tuple[datetime.date, datetime.date] | None = None) -> datetime.date:
    """Record the search date on the first start; refuse a resume on another UTC date, or a
    resume of a smoke run with another window."""
    meta = run_dir / "run.json"
    smoke_dates = [d.isoformat() for d in window] if window else None
    if meta.exists():
        stored = json.loads(meta.read_text())
        search_date = datetime.date.fromisoformat(stored["search_date_utc"])
        if search_date != today:
            raise SearchRunError(f"the run started on {search_date} (UTC) and today is {today}; "
                                 "the registered search runs on one day")
        if stored.get("smoke_window") != smoke_dates:
            raise SearchRunError(f"the run was started with smoke window "
                                 f"{stored.get('smoke_window')}, not {smoke_dates}")
        return search_date
    run_dir.mkdir(parents=True, exist_ok=True)
    meta.write_text(json.dumps({
        "search_date_utc": today.isoformat(), "started_utc": now(), "smoke": smoke,
        "smoke_window": smoke_dates,
        "openalex_select": OPENALEX_SELECT, "openalex_key_sent": bool(
            os.environ.get("OPEN_ALEX_API_KEY")),
        "scripts_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in (HERE / "run_search.py", HERE / "search_queries.py")},
    }, indent=1))
    return today


def run(client: httpx.Client, run_dir: pathlib.Path, today: datetime.date,
        smoke: bool = False,
        window: tuple[datetime.date, datetime.date] | None = None) -> dict:
    """`window` is read by a smoke run only (default SMOKE_WINDOW); the registered search
    takes its windows from the search date."""
    if window is not None and not smoke:
        raise SearchRunError("a window is given to a smoke run only")
    chosen = (window or SMOKE_WINDOW) if smoke else None
    search_date = start_run(run_dir, today, smoke, chosen)
    windows = {"smoke": chosen} if smoke else sq.windows(search_date)
    counts: dict = {"search_date_utc": search_date.isoformat(), "windows": {
        w: [a.isoformat(), b.isoformat()] for w, (a, b) in windows.items()}, "streams": {}}

    def record(done: dict) -> None:
        counts["streams"][f"{done['source']}/{done['stream']}"] = {
            k: done[k] for k in ("reported", "retrieved", "pages")}
        (run_dir / "counts.json").write_text(json.dumps(counts, indent=1))

    for window, (start, end) in windows.items():
        for q in sq.QUERIES:
            record(run_pubmed_esearch(client, run_dir, f"esearch_{q}_{window}",
                                      sq.pubmed_query(q, start, end)))
    record(run_pubmed_efetch(client, run_dir, pubmed_ids(run_dir)))
    for window, (start, end) in windows.items():
        for q in sq.QUERIES:
            record(run_paged(client, run_dir, "epmc", f"{q}_{window}", EPMC, {
                "query": sq.epmc_query(q, start, end), "format": "json", "resultType": "core",
                "synonym": "false", "pageSize": EPMC_PAGE, "cursorMark": "*"}, read_epmc))
    for window, (start, end) in windows.items():
        for q in sq.QUERIES:
            record(run_paged(client, run_dir, "openalex", f"{q}_{window}", OPENALEX, {
                "filter": sq.openalex_filter(q, start, end), "select": OPENALEX_SELECT,
                "per_page": OPENALEX_PAGE, "cursor": "*"}, read_openalex))
    record(run_pubmed_efetch(client, run_dir, linked_pmids(run_dir), "efetch_linked"))
    counts["finished_utc"] = now()
    gaps = {k: v for k, v in counts["streams"].items()
            if v["reported"] != v["retrieved"] and k != "pubmed/efetch_linked"}
    counts["streams_with_count_gap"] = sorted(gaps)
    (run_dir / "counts.json").write_text(json.dumps(counts, indent=1))
    if gaps:
        raise SearchRunError(f"retrieved differs from reported in {sorted(gaps)}; "
                             "see counts.json")
    return counts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true",
                    help="run on a pre-2019 window only (default: the months of SMOKE_WINDOW)")
    ap.add_argument("--smoke-start", type=datetime.date.fromisoformat)
    ap.add_argument("--smoke-end", type=datetime.date.fromisoformat)
    ap.add_argument("--smoke-label", help="folder name of the smoke run (default: the UTC date)")
    a = ap.parse_args()
    if not a.smoke and (a.smoke_start or a.smoke_end or a.smoke_label):
        ap.error("--smoke-start, --smoke-end and --smoke-label go with --smoke")
    if not a.smoke:
        check_frozen()
    window = smoke_window(a.smoke_start, a.smoke_end) if a.smoke else None
    today = datetime.datetime.now(datetime.UTC).date()
    run_dir = (RAW_SMOKE / (a.smoke_label or today.isoformat())) if a.smoke \
        else RAW / today.isoformat()
    existing = sorted(p.name for p in (RAW_SMOKE if a.smoke else RAW).glob("*") if p.is_dir())
    if existing and existing != [today.isoformat()] and not a.smoke:
        raise SearchRunError(f"a search run exists for {existing}; the registered search runs "
                             "once, on one day")
    with httpx.Client(timeout=120) as client:
        counts = run(client, run_dir, today, a.smoke, window)
    print(json.dumps(counts, indent=1))


if __name__ == "__main__":
    main()
