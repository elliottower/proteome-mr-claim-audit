import csv
import json
import pathlib

import pytest

import calibrate_dedup as cd
import cut_supplements as cs
import source_scanner_v2 as scanner

HERE = pathlib.Path(__file__).resolve().parents[1]
DICTIONARY = HERE.parent / "02_claims_meta" / "dataset_dictionary.csv"
PATTERNS = json.loads((HERE / "reference" / "c1_scanner_patterns_v2.json").read_text())


@pytest.fixture(scope="module")
def tools():
    with DICTIONARY.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    matcher = cs.TermMatcher(rows, PATTERNS)
    accessions = [{"release_identifier": "GCST000123", "identifier_type": "gwas_catalog",
                   "dictionary_row": "FinnGen R10"}]
    return matcher, cd.TermSets(matcher), scanner.Mapper(PATTERNS, accessions, rows)


def workbook(rows, extra=""):
    body = "\n".join(rows)
    return {"name": "s.xlsx", "type": "XLSX", "sheets": 25,
            "text": "## sheet Table S1\nprotein\tsource\tn\n" + body + extra}


def test_the_frozen_selection_gives_the_frozen_cut_text(tools):
    matcher, termsets, mapper = tools
    e = workbook([f"P{i % 7}\tq\tx" for i in range(50)] + ["IL6\tFinnGen R10\t1,000 cases"])
    lines = e["text"].split("\n")
    sel = cd.frozen_selection(lines, "XLSX", matcher)
    assert cd.text_of(lines, sel, cs.headers(lines, "XLSX")) == cs.cut(e, matcher)["text"]


def test_dedup_keeps_new_identifiers_k_rows_per_signature_and_new_count_pairs(tools):
    matcher, termsets, mapper = tools
    repeats = [f"P{i}\tFinnGen R10\t" for i in range(20)]
    rows = repeats + ["Q1\tGCST000123\t", "Q2\tGCST000123\t", "Q3\tFinnGen R10\t5000 cases",
                      "Q4\tsee doi:10.9999/x.y\t"]
    m = cd.measure_file(workbook(rows), matcher, termsets, PATTERNS, mapper)
    assert m["frozen_cut"]
    v1, v3, fr = m["variants"]["k1_all"], m["variants"]["k3_all"], m["variants"]["frozen"]
    assert v1["characters"] < v3["characters"] < fr["characters"] + len("Q4\tsee doi:10.9999/x.y\t") + 1
    whole = m["whole"]
    assert whole["a1"] == 2 and whole["a2"] == 3
    for v in (v1, v3):
        assert v["a1_kept"] == 2 and v["a2_kept"] == 3
        assert v["b_kept"] == whole["b"] and v["c_kept"] == whole["c"]
    assert fr["a2_kept"] == 2


def test_the_large_variant_leaves_small_tables_as_the_frozen_cut_keeps_them(tools):
    matcher, termsets, mapper = tools
    rows = [f"P{i}\tFinnGen R10\t" for i in range(30)]
    m = cd.measure_file(workbook(rows), matcher, termsets, PATTERNS, mapper)
    assert m["variants"]["k1_large"]["characters"] == m["variants"]["frozen"]["characters"]
    assert m["variants"]["k1_all"]["characters"] < m["variants"]["frozen"]["characters"]


def test_a_file_the_frozen_rule_does_not_cut_is_whole_under_every_variant(tools):
    matcher, termsets, mapper = tools
    e = {"name": "s.pdf", "type": "PDF", "sheets": 0, "text": "We used FinnGen R10.\nother"}
    m = cd.measure_file(e, matcher, termsets, PATTERNS, mapper)
    assert not m["frozen_cut"]
    assert {v["characters"] for v in m["variants"].values()} == {len(e["text"])}
    assert set(m["variants"]) == {"frozen", "k1_all", "k3_all", "k10_all", "k1_large",
                                  "k3_large", "k10_large"}


def test_aggregate_pools_and_names_papers_losing_a_decisive_identifier():
    f = {"characters_whole": 100, "frozen_cut": True,
         "whole": {"a1": 2, "a2": 3, "b": 4, "c": 5},
         "variants": {"k1_all": {"characters": 10, "a1_kept": 1, "a2_kept": 3, "b_kept": 4,
                                 "c_kept": 5}}}
    out = cd.aggregate({"p": [f]})["k1_all"]
    assert out["retention"]["a1"] == 0.5 and out["papers_losing_a1"] == ["p"]
    assert out["cuts"]["p"]["files"][0] == {"cut": True, "characters_before": 100,
                                            "characters_after": 10}
