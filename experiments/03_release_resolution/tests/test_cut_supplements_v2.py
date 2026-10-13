import csv
import json
import pathlib

import pytest

import calibrate_containment as cn
import calibrate_containment_v3 as c3
import calibrate_cut as cc
import calibrate_dedup as cd
import calibrate_keeplist as ck
import calibrate_keeplist_v2 as k2
import cut_supplements as cs
import cut_supplements_v2 as cv
import source_scanner_v2 as scanner

HERE = pathlib.Path(__file__).resolve().parents[1]
DICTIONARY = HERE.parent / "02_claims_meta" / "dataset_dictionary.csv"
PATTERNS = json.loads((HERE / "reference" / "c1_scanner_patterns_v2.json").read_text())
KEEP = HERE / "reference" / "release_language_patterns_v2.json"


@pytest.fixture(scope="module")
def tools():
    with DICTIONARY.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    matcher = cs.TermMatcher(rows, PATTERNS)
    groups = k2.Groups(str(KEEP), cc.NameMatcher(rows), PATTERNS)
    return matcher, groups, (matcher, cd.TermSets(matcher), PATTERNS,
                             scanner.Mapper(PATTERNS, [], rows), groups)


def workbook(body: str) -> dict:
    return {"name": "s.xlsx", "type": "XLSX", "sheets": 25, "sha256": "f" * 64, "version": "journal",
            "text": body}


BODIES = [
    "## sheet Table S1\nprotein\ttrait\tsource\tbeta\n"
    + "\n".join(f"IL6\t{t}\tUKB-PPP discovery\t{b}" for t in ("asthma", "eczema") for b in ("0.1", "0.2", "0.1"))
    + "\nnotes on the analysis\nsummary statistics were downloaded from FinnGen R10\n"
    + "## sheet Table S2\nprotein\toutcome\tsource\nIL6\tasthma\tUKB-PPP discovery\n"
    + "padding line without terms\n" * 40,
    "Supplementary Table 3 cohorts\nname\tn\nINTERVAL\t3301\nFenland\t10708\nother\t1\n"
    "free text about GCST90000123 and release R5 of FinnGen\n" + "x\ty\n" * 30,
]


@pytest.mark.parametrize("body", BODIES)
def test_the_cut_equals_the_calibrated_full_row_variant(tools, body):
    matcher, groups, measure_tools = tools
    entry = workbook(body)
    got = cv.cut(entry, matcher, groups)
    ref = c3.measure_file(entry, *measure_tools)
    assert got["characters_read"] == ref["full_rows"]["characters"]
    assert got["units_amended"] == ref["full_rows"]["units"]
    assert got["units_registered"] == ref["registered"]["units"]
    assert [c["characters"] for c in got["chunks"]] == ref["chunks"]["full_rows"]
    assert got["lost_units"] == 0


@pytest.mark.parametrize("body", BODIES)
def test_requests_count_the_characters_pack_counts(tools, body):
    matcher, groups, _ = tools
    entry = workbook(body)
    got = cv.cut(entry, matcher, groups)
    for budget in (cn.LIMIT, 120, 60):
        parts = cv.requests(got["rows"], budget)
        if budget == cn.LIMIT:
            assert sum(len(p) + 1 for p in parts) == got["characters_read"]
        assert all(len(p) + 1 <= budget or p.count("\n") <= 1 for p in parts)
        seen = [l for p in parts for l in p.split("\n")]
        assert all(r["line"] in seen for r in got["rows"])


def test_a_part_starting_mid_table_carries_the_header(tools):
    matcher, groups, _ = tools
    rows = [f"IL{i}\tasthma\tUKB-PPP discovery\t0.{i}" for i in range(1, 9)]
    entry = workbook("## sheet T\nprotein\ttrait\tsource\tbeta\n" + "\n".join(rows))
    got = cv.cut(entry, matcher, groups)
    parts = cv.requests(got["rows"], 90)
    assert len(parts) > 1
    for p in parts[1:]:
        assert p.split("\n")[0] == "protein\ttrait\tsource\tbeta"


def test_rows_equal_in_every_cell_are_dropped_and_nothing_else(tools):
    matcher, groups, _ = tools
    rows = ["IL6\tasthma\tUKB-PPP discovery\t0.1", "IL6\tAsthma \tUKB-PPP  discovery\t0.1",
            "IL6\tasthma\tUKB-PPP discovery\t0.2"]
    entry = workbook("## sheet T\nprotein\ttrait\tsource\tbeta\n" + "\n".join(rows))
    got = cv.cut(entry, matcher, groups)
    kept = [r["line"] for r in got["rows"] if not r["structural"]]
    assert kept == [rows[0], rows[2]]
    removed = "".join(c["text"] for c in got["chunks"])
    assert rows[1] in removed


def test_a_small_file_is_given_whole(tools):
    matcher, groups, _ = tools
    entry = {"name": "a.csv", "type": "CSV", "sha256": "e" * 64, "text": "a\tb\n1\t2"}
    got = cv.cut(entry, matcher, groups)
    assert got["cut"] is False and got["text"] == entry["text"] and got["chunks"] == []


def test_a_lost_unit_stops_the_stage(tools, monkeypatch):
    matcher, groups, _ = tools
    entry = workbook(BODIES[0])
    real = cv.select

    def losing(*a, **k):
        s = real(*a, **k)
        s["units"]["amended"] = set(list(s["units"]["amended"])[1:])
        return s

    monkeypatch.setattr(cv, "select", losing)
    with pytest.raises(cv.ContainmentError):
        cv.cut(entry, matcher, groups)


def test_removed_chunks_match_the_calibrated_lengths():
    lines = ["h1\th2", "a\tb", "c\td", "free", "e\tf"]
    table = [0, 0, 0, -1, -1]
    removed = [1, 2, 3, 4]
    for size in (5, 8, 100):
        texts = cv.removed_chunks(lines, removed, table, size)
        assert [len(t) for t in texts] == ck.chunk_lengths(lines, removed, table, size)
