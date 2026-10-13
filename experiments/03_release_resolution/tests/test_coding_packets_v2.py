import pathlib

import pytest

import coding_packets as cp
import coding_packets_v2 as cp2

HERE = pathlib.Path(__file__).resolve().parents[1]
ACC = cp.read_accessions(HERE / "reference" / "c1_scanner_patterns_v2.json",
                         HERE / "reference" / "accession_releases.csv")
ROWS = [{"row_id": "a1", "record_id": "r1", "side": "pqtl", "name_as_written": "not stated",
         "outcomes_as_written": [], "candidates": []}]


def cut_file(n):
    return {"cut": True, "type": "XLSX", "sha256": "e" * 64, "text": None,
            "rows": [{"table": 0, "line": f"v{i}\tw{i}", "header": "h1\th2", "structural": False}
                     for i in range(n)]}


def test_every_carrying_request_holds_the_full_text_and_stays_within_the_limit(monkeypatch):
    monkeypatch.setattr(cp, "LIMIT", 300)
    abstract, full = "A" * 40, [{"text": "F" * 100}]
    packets, _ = cp2.fulltext_packets_carrying("r1", "T", ROWS, abstract, full, [cut_file(40)], ACC)
    assert len(packets) > 1
    for p in packets:
        kinds = [f["kind"] for f in p["files"]]
        assert kinds[:2] == ["abstract", "full_text"]
        assert sum(len(f["text"]) for f in p["files"]) <= 300
    text = "\n".join(f["text"] for p in packets for f in p["files"])
    assert all(f"v{i}\tw{i}" in text for i in range(40))


def test_layout_cost_caches_the_prompt_after_the_first_request_and_the_carried_prefix():
    recs = [{"packets": [1000, 1000], "carried": 600}]
    ratio = {m: 1.0 for m in cp2.PRICE}
    a = cp2.layout_cost(recs, 100, ratio, carrying=False)
    b = cp2.layout_cost(recs, 100, ratio, carrying=True)
    c = a["claude-sonnet-5-5"]
    assert c["cache_write_tokens"] == 100 and c["cached_input_tokens"] == 100
    assert c["new_input_tokens"] == 2000
    d = b["claude-sonnet-5-5"]
    assert d["cache_write_tokens"] == 700 and d["cached_input_tokens"] == 700
    assert d["new_input_tokens"] == 800
    expected = (800 * 2 + 700 * 2.5 + 700 * 0.2 + 2 * 1500 * 10) / 1e6
    assert d["usd"] == pytest.approx(round(expected, 2))


def test_a_single_request_record_caches_nothing_of_its_own():
    recs = [{"packets": [500], "carried": 400}]
    ratio = {m: 1.0 for m in cp2.PRICE}
    assert cp2.layout_cost(recs, 0, ratio, True) == cp2.layout_cost(recs, 0, ratio, False)
