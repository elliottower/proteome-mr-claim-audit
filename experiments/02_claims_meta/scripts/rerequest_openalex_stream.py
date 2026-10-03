# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "pydantic==2.13.5"]
# ///
"""Request named OpenAlex streams of the registered search a second time, on the search date.

The registered runner (`run_search.py`) never requests a completed stream again. This script
requests the streams given again with the runner's own query builder, filters, `select`, page
size, headers and paging (`run_search.run_paged`), and stores every response in its own folder,
`outputs/raw/search/<search date>_openalex_q1_rerequest/`, beside the first request and never
inside it. It refuses on any UTC date other than the search date of the first request.

It then compares the two requests by work identifier and `meta.count` only (no title, no
abstract is read) and writes `comparison.json`: per stream the reported count, the distinct
works and duplicates of each request, and the works found by one request and not the other.

Whether the second request is used is not decided here.

Usage:
    uv run scripts/rerequest_openalex_stream.py Q1_confirmatory Q1_update
"""

import argparse
import datetime
import hashlib
import json
import os
import pathlib

import httpx
from pydantic import BaseModel

import run_search as rs
import search_queries as sq

SUFFIX = "_openalex_q1_rerequest"


class RerequestError(Exception):
    """The second request cannot run: wrong date, unknown stream, a changed stored page."""


class StreamComparison(BaseModel):
    stream: str
    first_reported: int
    first_distinct: int
    first_duplicates: int
    second_reported: int
    second_distinct: int
    second_duplicates: int
    only_in_first: list[str]
    only_in_second: list[str]


def work_ids(run_dir: pathlib.Path, stream: str) -> tuple[int, list[str]]:
    """The reported count of page 1 and the work identifiers of every stored page, in order."""
    manifest = rs.read_manifest(run_dir)
    bodies = rs.stored_pages(manifest, run_dir, "openalex", stream)
    if not bodies:
        raise RerequestError(f"{run_dir.name}: no stored page for openalex {stream}")
    reported = json.loads(bodies[0])["meta"]["count"]
    return reported, [w["id"] for b in bodies for w in json.loads(b)["results"]]


def compare(first_dir: pathlib.Path, second_dir: pathlib.Path, stream: str) -> StreamComparison:
    r1, ids1 = work_ids(first_dir, stream)
    r2, ids2 = work_ids(second_dir, stream)
    s1, s2 = set(ids1), set(ids2)
    return StreamComparison(
        stream=stream, first_reported=r1, first_distinct=len(s1),
        first_duplicates=len(ids1) - len(s1), second_reported=r2, second_distinct=len(s2),
        second_duplicates=len(ids2) - len(s2), only_in_first=sorted(s1 - s2),
        only_in_second=sorted(s2 - s1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("streams", nargs="+", help="e.g. Q1_confirmatory Q1_update")
    a = ap.parse_args()
    rs.check_frozen()
    today = datetime.datetime.now(datetime.UTC).date()
    first_dir = rs.RAW / today.isoformat()
    if not (first_dir / "run.json").exists():
        raise RerequestError(f"no first request for {today} (UTC); a second request is made on "
                             "the search date only")
    search_date = datetime.date.fromisoformat(
        json.loads((first_dir / "run.json").read_text())["search_date_utc"])
    if search_date != today:
        raise RerequestError(f"the search date is {search_date} and today is {today} (UTC)")
    windows = sq.windows(search_date)
    second_dir = rs.RAW / f"{today.isoformat()}{SUFFIX}"
    second_dir.mkdir(parents=True, exist_ok=True)
    meta = second_dir / "run.json"
    if not meta.exists():
        meta.write_text(json.dumps({
            "search_date_utc": search_date.isoformat(), "started_utc": rs.now(),
            "second_request_of": str(first_dir.relative_to(rs.EXP)), "streams": a.streams,
            "openalex_select": rs.OPENALEX_SELECT,
            "openalex_key_sent": bool(os.environ.get("OPEN_ALEX_API_KEY")),
            "scripts_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (
                rs.HERE / "run_search.py", rs.HERE / "search_queries.py",
                rs.HERE / "rerequest_openalex_stream.py")},
        }, indent=1))
    with httpx.Client(timeout=120) as client:
        for stream in a.streams:
            q, _, window = stream.partition("_")
            if q not in sq.QUERIES or window not in windows:
                raise RerequestError(f"unknown stream {stream}")
            start, end = windows[window]
            if datetime.datetime.now(datetime.UTC).date() != search_date:
                raise RerequestError("the UTC date changed; the second request stops")
            done = rs.run_paged(client, second_dir, "openalex", stream, rs.OPENALEX, {
                "filter": sq.openalex_filter(q, start, end), "select": rs.OPENALEX_SELECT,
                "per_page": rs.OPENALEX_PAGE, "cursor": "*"}, rs.read_openalex)
            print(json.dumps(done))
    out = {"finished_utc": rs.now(), "first_request": str(first_dir.relative_to(rs.EXP)),
           "second_request": str(second_dir.relative_to(rs.EXP)),
           "read": "work identifiers and meta.count only",
           "streams": [compare(first_dir, second_dir, s).model_dump() for s in a.streams]}
    target = second_dir / "comparison.json"
    if target.exists():
        raise RerequestError(f"{target} exists; it is not overwritten")
    target.write_text(json.dumps(out, indent=1))
    print(json.dumps({s["stream"]: {k: (len(v) if isinstance(v, list) else v)
                                    for k, v in s.items() if k != "stream"}
                      for s in out["streams"]}, indent=1))


if __name__ == "__main__":
    main()
