import csv
import json
import math
import pathlib

import pytest

import calibrate_cut as cc
import calibrate_containment as cn
import calibrate_dedup as cd
import calibrate_keeplist_v2 as k2
import cut_supplements as cs
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
    accessions = [{"release_identifier": "GCST000123", "identifier_type": "gwas_catalog",
                   "dictionary_row": "FinnGen R10"}]
    return (matcher, cd.TermSets(matcher), PATTERNS, scanner.Mapper(PATTERNS, accessions, rows),
            k2.Groups(str(KEEP), cc.NameMatcher(rows), PATTERNS))


def workbook(rows):
    return {"name": "s.xlsx", "type": "XLSX", "sheets": 25, "sha256": "f" * 64,
            "text": "## sheet Table S1\nprotein\ttrait\tsource\tbeta\n" + "\n".join(rows)}


def test_the_amended_cut_contains_every_registered_unit_and_k1_may_not(tools):
    rows = [f"P{i}\tasthma\tUKB-PPP discovery\tn = {1000 + i}" for i in range(10)]
    rows += [f"Q{i}\tasthma\tUKB-PPP discovery\t" for i in range(10)]
    m = cn.measure_file(workbook(rows), *tools)
    assert m["lost_units"]["amended"] == [] and m["lost_units"]["registered"] == []
    assert len(m["lost_units"]["narrow_k1"]) > 0
    assert m["amended"]["characters"] <= m["registered"]["characters"]


def test_identifier_rows_keep_one_per_signature_and_every_unmapped_identifier(tools):
    rows = [f"IL6\tasthma\tGCST000123\t0.{i}" for i in range(5)]
    rows += [f"IL6\teczema\tGCST000123\t0.{i}" for i in range(3)]
    rows += [f"CRP\tasthma\tGCST000123\t0.9"]
    rows += [f"IL6\tasthma\tGCST99999{i}\t0.1" for i in range(4)]
    m = cn.measure_file(workbook(rows), *tools)
    kept = m["amended"]["characters"]
    one_each = len("## sheet Table S1\nprotein\ttrait\tsource\tbeta\n")
    one_each += len("IL6\tasthma\tGCST000123\t0.0\n") + len("IL6\teczema\tGCST000123\t0.0\n")
    one_each += len("CRP\tasthma\tGCST000123\t0.9\n")
    one_each += sum(len(f"IL6\tasthma\tGCST99999{i}\t0.1\n") for i in range(4))
    assert kept == one_each and kept < m["characters_whole"]


def test_the_header_is_repeated_at_the_head_of_each_request(monkeypatch):
    monkeypatch.setattr(cn, "LIMIT", 30)
    lines = ["h\tx", "a" * 10, "b" * 10, "c" * 10]
    table = [0, 0, 0, 0]
    assert cn.pack(lines, [0, 1, 2, 3], table, {0}) == 4 + 11 + 11 + (4 + 11)


def test_the_hypergeometric_bound_is_the_largest_k_with_the_cdf_at_least_005():
    N, n = 2_000, 400
    k = cn.hypergeometric_upper(0, N, n)
    p = lambda k: math.comb(N - k, n) / math.comb(N, n)
    assert p(k) >= 0.05 > p(k + 1)
    k1 = cn.hypergeometric_upper(1, N, n)
    q = lambda k: (math.comb(N - k, n) + k * math.comb(N - k, n - 1)) / math.comb(N, n)
    assert q(k1) >= 0.05 > q(k1 + 1) and k1 > k


def test_a_file_the_registered_threshold_does_not_cut_is_whole(tools):
    e = {"name": "s.pdf", "type": "PDF", "sheets": 0, "sha256": "a" * 64, "text": "FinnGen R10."}
    m = cn.measure_file(e, *tools)
    assert {m[v]["characters"] for v in cn.VARIANTS} == {len(e["text"])}


def test_a_count_column_value_makes_the_signature_differ(tools):
    rows = [f"IL6\tasthma\tGCST000123\t{1000 + i}" for i in range(4)]
    e = {"name": "s.xlsx", "type": "XLSX", "sheets": 25, "sha256": "f" * 64,
         "text": "## sheet Table S1\nprotein\ttrait\tsource\tN_cases\n" + "\n".join(rows)}
    m = cn.measure_file(e, *tools)
    assert m["amended"]["characters"] == m["registered"]["characters"]
