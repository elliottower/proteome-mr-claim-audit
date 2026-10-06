# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "pydantic==2.13.5"]
# ///
"""Build one search folder from the registered search and a second request of named streams.

The registered runner (`run_search.py`) ended on a count gap: in two OpenAlex streams the
distinct works retrieved were one fewer than the count OpenAlex reported. Those streams were
requested a second time on the search date (`rerequest_openalex_stream.py`), and the logged
decision is that the screening set takes every work present in either request for those
streams and every other stream as first retrieved.

`assemble_screening_set.py` reads one search folder. This script writes that folder:

    <out>/manifest.jsonl   every line of the first request's manifest, unchanged and in order,
                           then the 200 lines of the second request, each with its `file`
                           moved under `openalex_second_request/` and `"request": "second"`
    <out>/...              every file the first manifest names, byte for byte, at its own path
    <out>/openalex_second_request/...   the second request's pages, byte for byte
    <out>/counts.json, run.json         copied from the first request
    <out>/union.json       the sha256 and origin of every file, and the count check

The count check replaces the runner's row-count check, and is explicit: per OpenAlex stream it
compares the distinct works of the folder with the count OpenAlex reported on every page (the
runner compared rows, which counts a work returned on two cursor pages twice). Every OpenAlex
stream must hold exactly the reported number of distinct works, and every PubMed and Europe PMC
stream of `counts.json` must have retrieved what it reported (`efetch_linked` aside, which is
outside the runner's check by design). Any difference raises and nothing is written.

No title or abstract is read: work identifiers and `meta.count` only. Nothing is requested.

Usage:
    uv run scripts/merge_search_requests.py --first outputs/raw/search/<date> \
        --second outputs/raw/search/<date>_openalex_q1_rerequest \
        --out outputs/raw/search/<date>_union
    uv run scripts/merge_search_requests.py --verify outputs/raw/search/<date>_union
"""

import argparse
import hashlib
import json
import pathlib
import shutil

from pydantic import BaseModel

import run_search as rs

SECOND_PREFIX = "openalex_second_request"
UNCHECKED_STREAMS = ("pubmed/efetch_linked",)


class UnionError(Exception):
    """The union cannot be built or no longer matches its record."""


class UnionFile(BaseModel):
    path: str
    sha256: str
    origin: str


class StreamCount(BaseModel):
    stream: str
    reported: int
    rows: int
    distinct_works: int
    second_request_used: bool


class UnionRecord(BaseModel):
    first_request: str
    second_request: str
    second_request_streams: list[str]
    read: str = "work identifiers and meta.count only"
    openalex_streams: list[StreamCount]
    other_streams_reported_equals_retrieved: dict[str, bool]
    files: list[UnionFile]


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pages(run_dir: pathlib.Path) -> list[dict]:
    return [l for l in rs.read_manifest(run_dir) if l.get("status") == 200]


def stream_counts(run_dir: pathlib.Path, manifest: list[dict],
                  second_streams: list[str]) -> list[StreamCount]:
    """Reported count, rows and distinct works of every OpenAlex stream of a manifest."""
    reported: dict[str, set[int]] = {}
    ids: dict[str, list[str]] = {}
    for line in manifest:
        if line.get("status") != 200 or line["source"] != "openalex":
            continue
        body = json.loads(rs.read_body(run_dir, line))
        reported.setdefault(line["stream"], set()).add(body["meta"]["count"])
        ids.setdefault(line["stream"], []).extend(w["id"] for w in body["results"])
    out = []
    for stream in sorted(ids):
        if len(reported[stream]) != 1:
            raise UnionError(f"openalex {stream}: pages report different counts "
                             f"{sorted(reported[stream])}")
        out.append(StreamCount(stream=stream, reported=reported[stream].pop(),
                               rows=len(ids[stream]), distinct_works=len(set(ids[stream])),
                               second_request_used=stream in second_streams))
    return out


def other_streams_ok(first: pathlib.Path) -> dict[str, bool]:
    counts = json.loads((first / "counts.json").read_text())["streams"]
    return {name: c["reported"] == c["retrieved"] for name, c in sorted(counts.items())
            if not name.startswith("openalex/") and name not in UNCHECKED_STREAMS}


def check_counts(openalex: list[StreamCount], others: dict[str, bool]) -> None:
    gaps = [f"openalex {s.stream}: {s.distinct_works} distinct works, {s.reported} reported"
            for s in openalex if s.distinct_works != s.reported]
    gaps += [f"{name}: retrieved differs from reported" for name, ok in others.items() if not ok]
    if gaps:
        raise UnionError("count gap in the union: " + "; ".join(gaps))


def build(first: pathlib.Path, second: pathlib.Path, out: pathlib.Path) -> UnionRecord:
    if out.exists():
        raise UnionError(f"{out} exists; a union folder is written once")
    first_manifest = (first / "manifest.jsonl").read_text()
    second_pages = pages(second)
    second_streams = sorted({l["stream"] for l in second_pages})
    if not second_pages or any(l["source"] != "openalex" for l in second_pages):
        raise UnionError("the second request must hold OpenAlex pages only, and at least one")
    for run_dir, lines in ((first, pages(first)), (second, second_pages)):
        for line in lines:
            rs.read_body(run_dir, line)  # raises when a stored page differs from its hash

    moved = [{**l, "file": f"{SECOND_PREFIX}/{l['file'].removeprefix('openalex/')}",
              "request": "second"} for l in second_pages]
    merged_text = first_manifest + "".join(json.dumps(l) + "\n" for l in moved)

    tmp = out.with_name(out.name + ".building")
    if tmp.exists():
        raise UnionError(f"{tmp} exists from an unfinished build; inspect and remove it")
    tmp.mkdir(parents=True)
    files: list[UnionFile] = []
    first_files = sorted({l["file"] for l in pages(first)} | {"counts.json", "run.json"})
    for rel in first_files:
        (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(first / rel, tmp / rel)
        files.append(UnionFile(path=rel, sha256=sha256_file(tmp / rel),
                               origin=f"{first.as_posix()}/{rel}"))
    for line, new in zip(second_pages, moved, strict=True):
        (tmp / new["file"]).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(second / line["file"], tmp / new["file"])
        files.append(UnionFile(path=new["file"], sha256=sha256_file(tmp / new["file"]),
                               origin=f"{second.as_posix()}/{line['file']}"))
    (tmp / "manifest.jsonl").write_text(merged_text)
    files.append(UnionFile(path="manifest.jsonl", sha256=sha256_file(tmp / "manifest.jsonl"),
                           origin="first manifest, then the second request's 200 lines"))

    record = UnionRecord(
        first_request=first.as_posix(), second_request=second.as_posix(),
        second_request_streams=second_streams,
        openalex_streams=stream_counts(tmp, rs.read_manifest(tmp), second_streams),
        other_streams_reported_equals_retrieved=other_streams_ok(first), files=files)
    try:
        check_counts(record.openalex_streams, record.other_streams_reported_equals_retrieved)
        verify_files(tmp, record)
    except UnionError:
        shutil.rmtree(tmp)
        raise
    (tmp / "union.json").write_text(record.model_dump_json(indent=1))
    tmp.rename(out)
    return record


def verify_files(folder: pathlib.Path, record: UnionRecord) -> None:
    """Every file of the union has the bytes recorded for it and the bytes of its origin."""
    for f in record.files:
        if sha256_file(folder / f.path) != f.sha256:
            raise UnionError(f"{f.path}: content differs from union.json")
        origin = pathlib.Path(f.origin)
        if f.path != "manifest.jsonl" and sha256_file(origin) != f.sha256:
            raise UnionError(f"{f.path}: content differs from its origin {f.origin}")
    first = pathlib.Path(record.first_request)
    merged = (folder / "manifest.jsonl").read_text()
    if not merged.startswith((first / "manifest.jsonl").read_text()):
        raise UnionError("the union manifest does not begin with the first request's manifest")


def verify(folder: pathlib.Path) -> UnionRecord:
    record = UnionRecord.model_validate_json((folder / "union.json").read_text())
    verify_files(folder, record)
    counts = stream_counts(folder, rs.read_manifest(folder), record.second_request_streams)
    if counts != record.openalex_streams:
        raise UnionError("the stream counts of the folder differ from union.json")
    check_counts(counts, record.other_streams_reported_equals_retrieved)
    return record


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", type=pathlib.Path)
    ap.add_argument("--second", type=pathlib.Path)
    ap.add_argument("--out", type=pathlib.Path)
    ap.add_argument("--verify", type=pathlib.Path, help="check an existing union folder")
    a = ap.parse_args()
    if a.verify:
        record = verify(a.verify)
    elif a.first and a.second and a.out:
        record = build(a.first, a.second, a.out)
    else:
        raise UnionError("give --first, --second and --out, or --verify")
    print(json.dumps({"openalex_streams": [s.model_dump() for s in record.openalex_streams],
                      "other_streams_reported_equals_retrieved":
                          record.other_streams_reported_equals_retrieved,
                      "files": len(record.files)}, indent=1))


if __name__ == "__main__":
    main()
