import gzip
import hashlib
import json
import pathlib

import pytest

import assemble_screening_set as ass
import merge_search_requests as mr


def work(n: int) -> dict:
    return {"id": f"https://openalex.org/W{n}", "doi": f"https://doi.org/10.1/w{n}",
            "ids": {"openalex": f"https://openalex.org/W{n}"}, "display_name": f"work {n}",
            "publication_date": "2021-05-04", "type": "article", "authorships": [],
            "primary_location": None, "abstract_inverted_index": {"word": list(range(1))}}


def write_run(run: pathlib.Path, streams: dict[str, tuple[int, list[list[int]]]],
              counts: dict | None = None) -> None:
    run.mkdir(parents=True)
    lines = []
    for stream, (reported, page_ids) in streams.items():
        for page, ids in enumerate(page_ids, 1):
            body = json.dumps({"meta": {"count": reported},
                               "results": [work(n) for n in ids]}).encode()
            rel = f"openalex/{stream}/page_{page:04d}.json.gz"
            (run / rel).parent.mkdir(parents=True, exist_ok=True)
            (run / rel).write_bytes(gzip.compress(body))
            lines.append({"source": "openalex", "stream": stream, "page": page, "url": "u",
                          "status": 200, "bytes": len(body),
                          "sha256": hashlib.sha256(body).hexdigest(), "file": rel})
        lines.append({"source": "openalex", "stream": stream, "event": "stream_complete"})
    (run / "manifest.jsonl").write_text("".join(json.dumps(l) + "\n" for l in lines))
    (run / "counts.json").write_text(json.dumps({"streams": counts or {
        "pubmed/esearch_Q1": {"reported": 4, "retrieved": 4, "pages": 1},
        "pubmed/efetch_linked": {"reported": 9, "retrieved": 7, "pages": 1}}}))
    (run / "run.json").write_text(json.dumps({"search_date_utc": "2026-10-03"}))


@pytest.fixture
def runs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    first, second = pathlib.Path("first"), pathlib.Path("second")
    # stream A: reported 4; the first request holds W1 W2 W2 W4 (W3 never arrives, W2 twice),
    # the second holds W1 W3 W2 (W4 never arrives). Stream B: reported 2, complete, W5 twice.
    write_run(first, {"A": (4, [[1, 2], [2, 4]]), "B": (2, [[5, 6], [5]])})
    write_run(second, {"A": (4, [[1, 3], [2]])})
    return first, second


def test_union_holds_every_work_of_either_request_and_passes_the_count_check(runs):
    first, second = runs
    record = mr.build(first, second, pathlib.Path("union"))
    by_stream = {s.stream: s for s in record.openalex_streams}
    assert (by_stream["A"].reported, by_stream["A"].rows, by_stream["A"].distinct_works) == (4, 7, 4)
    assert (by_stream["B"].reported, by_stream["B"].rows, by_stream["B"].distinct_works) == (2, 3, 2)
    assert by_stream["A"].second_request_used and not by_stream["B"].second_request_used
    ids = sorted(r.source_id for r in ass.load_run(pathlib.Path("union")))
    assert ids == ["W1", "W2", "W3", "W4", "W5", "W6"]
    streams = {r.source_id: r.streams for r in ass.load_run(pathlib.Path("union"))}
    assert streams["W3"] == ["A"] and streams["W4"] == ["A"] and streams["W5"] == ["B"]


def test_first_request_files_are_byte_identical_and_its_manifest_leads_the_union(runs):
    first, second = runs
    mr.build(first, second, pathlib.Path("union"))
    for path in sorted(p for p in first.rglob("*") if p.is_file() and p.name != "manifest.jsonl"):
        assert (pathlib.Path("union") / path.relative_to(first)).read_bytes() == path.read_bytes()
    merged = pathlib.Path("union/manifest.jsonl").read_text()
    assert merged.startswith((first / "manifest.jsonl").read_text())
    added = [json.loads(l) for l in merged[len((first / "manifest.jsonl").read_text()):].splitlines()]
    assert [l["file"] for l in added] == ["openalex_second_request/A/page_0001.json.gz",
                                         "openalex_second_request/A/page_0002.json.gz"]
    assert all(l["request"] == "second" and l["stream"] == "A" for l in added)


def test_a_work_missing_from_both_requests_is_a_count_gap(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_run(pathlib.Path("first"), {"A": (4, [[1, 2], [2, 4]])})
    write_run(pathlib.Path("second"), {"A": (4, [[1, 2], [4]])})
    with pytest.raises(mr.UnionError, match="openalex A: 3 distinct works, 4 reported"):
        mr.build(pathlib.Path("first"), pathlib.Path("second"), pathlib.Path("union"))
    assert not pathlib.Path("union").exists() and not pathlib.Path("union.building").exists()


def test_a_stream_not_requested_again_must_already_be_complete(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_run(pathlib.Path("first"), {"A": (4, [[1, 2], [2, 4]]), "B": (3, [[5, 6]])})
    write_run(pathlib.Path("second"), {"A": (4, [[1, 3], [2]])})
    with pytest.raises(mr.UnionError, match="openalex B: 2 distinct works, 3 reported"):
        mr.build(pathlib.Path("first"), pathlib.Path("second"), pathlib.Path("union"))


def test_a_pubmed_or_epmc_stream_short_of_its_reported_count_is_a_count_gap(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_run(pathlib.Path("first"), {"A": (4, [[1, 2], [2, 4]])},
              counts={"epmc/Q1": {"reported": 5, "retrieved": 4, "pages": 1}})
    write_run(pathlib.Path("second"), {"A": (4, [[1, 3], [2]])})
    with pytest.raises(mr.UnionError, match="epmc/Q1: retrieved differs from reported"):
        mr.build(pathlib.Path("first"), pathlib.Path("second"), pathlib.Path("union"))


def test_an_altered_first_request_page_is_refused_before_anything_is_written(runs):
    first, second = runs
    page = first / "openalex/A/page_0001.json.gz"
    page.write_bytes(gzip.compress(json.dumps({"meta": {"count": 4},
                                               "results": [work(1), work(9)]}).encode()))
    with pytest.raises(Exception, match="content differs from the manifest hash"):
        mr.build(first, second, pathlib.Path("union"))
    assert not pathlib.Path("union").exists()


def test_verify_reports_a_union_file_or_an_origin_changed_after_the_build(runs):
    first, second = runs
    union = pathlib.Path("union")
    mr.build(first, second, union)
    assert mr.verify(union).second_request_streams == ["A"]
    original = (union / "openalex/B/page_0001.json.gz").read_bytes()
    (union / "openalex/B/page_0001.json.gz").write_bytes(original + b"x")
    with pytest.raises(mr.UnionError, match="content differs from union.json"):
        mr.verify(union)
    (union / "openalex/B/page_0001.json.gz").write_bytes(original)
    (second / "openalex/A/page_0002.json.gz").write_bytes(b"changed")
    with pytest.raises(mr.UnionError, match="differs from its origin"):
        mr.verify(union)


def test_a_union_folder_is_written_once(runs):
    first, second = runs
    mr.build(first, second, pathlib.Path("union"))
    with pytest.raises(mr.UnionError, match="written once"):
        mr.build(first, second, pathlib.Path("union"))
