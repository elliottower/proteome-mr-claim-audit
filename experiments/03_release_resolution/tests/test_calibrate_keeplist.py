import csv
import json
import pathlib

import pytest

import calibrate_cut as cc
import calibrate_dedup as cd
import calibrate_keeplist as ck
import cut_supplements as cs
import source_scanner_v2 as scanner

HERE = pathlib.Path(__file__).resolve().parents[1]
DICTIONARY = HERE.parent / "02_claims_meta" / "dataset_dictionary.csv"
PATTERNS = json.loads((HERE / "reference" / "c1_scanner_patterns_v2.json").read_text())
KEEP = HERE / "reference" / "release_language_patterns.json"


@pytest.fixture(scope="module")
def tools():
    with DICTIONARY.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    matcher = cs.TermMatcher(rows, PATTERNS)
    return (matcher, cd.TermSets(matcher), PATTERNS, scanner.Mapper(PATTERNS, [], rows),
            ck.KeepList(str(KEEP), cc.NameMatcher(rows), PATTERNS))


@pytest.mark.parametrize("line,kept", [
    ("summary statistics were downloaded", True), ("data from release 7", True),
    ("FinnGen R10 outcome", True), ("genotype build GRCh37", True), ("v2.1 of the panel", True),
    ("GCST90012345", True), ("UKB-PPP discovery", True), ("Data availability", True),
    ("beta 0.12 se 0.03", False), ("participants were recruited", False)])
def test_the_keep_list(tools, line, kept):
    assert tools[4](line) == kept


def test_the_header_is_shown_once_per_table():
    lines = ["## sheet A", "h1\th2", "a\t1", "b\t2", "c\t3"]
    table = [-1, 1, 1, 1, 1]
    assert ck.render(lines, [0, 2, 4], table, {0}) == "## sheet A\nh1\th2\na\t1\nc\t3"
    assert ck.render(lines, [0, 1, 2, 4], table, {0, 1}) == "## sheet A\nh1\th2\na\t1\nc\t3"


def test_chunks_never_split_a_row_and_carry_the_header():
    lines = ["h", "x" * 9, "y" * 9, "z" * 30]
    table = [0, 0, 0, 0]
    assert ck.chunk_lengths(lines, [1, 2, 3], table, 25) == [2 + 10 + 10, 2 + 31]


def test_the_keep_list_adds_to_the_table_rule_and_a_small_file_is_whole(tools):
    matcher, termsets, patterns, mapper, keep = tools
    rows = [f"P{i}\tFinnGen R10\t" for i in range(20)] + [f"Q{i}\tq\tz" for i in range(20)]
    rows += ["note\tsummary statistics were downloaded\t"]
    e = {"name": "s.xlsx", "type": "XLSX", "sheets": 25, "sha256": "h",
         "text": "## sheet Table S1\nprotein\tsource\tn\n" + "\n".join(rows)}
    m = ck.measure_file(e, matcher, termsets, patterns, mapper, keep)
    assert m["table_rule_keep_list"]["characters"] > m["table_rule"]["characters"]
    assert m["keep_list_added_characters"] > 0
    assert m["table_rule_keep_list"]["a1_kept"] == m["whole"]["a1"]
    assert m["removed_characters"] > 0 and all(n <= 10_000 for n in m["chunks"]["10000"])
    small = {"name": "s.pdf", "type": "PDF", "sheets": 0, "sha256": "h", "text": "FinnGen R10."}
    s = ck.measure_file(small, matcher, termsets, patterns, mapper, keep)
    assert s["table_rule_keep_list"]["characters"] == len(small["text"]) and s["chunks"]["10000"] == []


def test_the_upper_bounds_are_exact():
    assert ck.upper_bound(0, 100) == pytest.approx(1 - 0.05 ** (1 / 100), abs=1e-9)
    p = ck.upper_bound(1, 200)
    assert (1 - p) ** 200 + 200 * p * (1 - p) ** 199 == pytest.approx(0.05, abs=1e-9)
