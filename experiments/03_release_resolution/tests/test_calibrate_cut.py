import csv
import json
import pathlib

import pytest

import calibrate_cut as cc
import cut_supplements as cs

HERE = pathlib.Path(__file__).resolve().parents[1]
DICTIONARY = HERE.parent / "02_claims_meta" / "dataset_dictionary.csv"
PATTERNS = json.loads((HERE / "reference" / "c1_scanner_patterns_v2.json").read_text())


@pytest.fixture(scope="module")
def tools():
    with DICTIONARY.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    return cs.TermMatcher(rows, PATTERNS), cc.NameMatcher(rows)


def entry(text, kind="PDF", sheets=0):
    return {"name": "s", "sha256": "h", "type": kind, "sheets": sheets, "text": text}


def test_a_file_is_measured_whole_and_as_cut_whatever_its_size(tools):
    text = ("Supplementary Table 1. Cohorts\n"
            "We used FinnGen R10 (GCST90012345).\n"
            "see doi:10.9999/unlisted.paper).\n"
            "The study had 1,234 cases and 5,000 controls.\n"
            "plain line")
    m = cc.measure_file(entry(text), *tools, PATTERNS)
    assert m["characters_whole"] == len(text) and m["characters_cut"] < len(text)
    assert m["identifiers_whole"] == ["FinnGen R10", "GCST90012345", "doi:10.9999/unlisted.paper"]
    assert m["identifiers_lost_when_cut"] == ["doi:10.9999/unlisted.paper"]
    assert (m["name_lines_whole"], m["name_lines_kept_when_cut"]) == (1, 1)
    assert m["count_lines_whole"] == 1 and m["count_lines_kept_when_cut"] in (0, 1)


def test_the_threshold_decides_only_which_files_are_cut_and_scales_the_sheet_limit():
    files = {"p": [{"name": "a", "sheets": 0, "characters_whole": 150_000, "characters_cut": 1_000,
                    "identifiers_whole": ["x", "y"], "identifiers_lost_when_cut": ["y"],
                    "name_lines_whole": 4, "name_lines_kept_when_cut": 4,
                    "count_lines_whole": 10, "count_lines_kept_when_cut": 2},
                   {"name": "b", "sheets": 6, "characters_whole": 5_000, "characters_cut": 500,
                    "identifiers_whole": [], "identifiers_lost_when_cut": [],
                    "name_lines_whole": 0, "name_lines_kept_when_cut": 0,
                    "count_lines_whole": 0, "count_lines_kept_when_cut": 0}]}
    reg = cc.at_threshold(files, 200_000)
    assert reg["sheets"] == 20 and reg["pooled"]["files_cut"] == 0
    assert reg["retention"]["hard_identifiers"] == 1.0 and reg["papers_losing_a_hard_identifier"] == {}
    low = cc.at_threshold(files, 50_000)
    assert low["sheets"] == 5 and low["pooled"]["files_cut"] == 2
    assert low["retention"]["hard_identifiers"] == 0.5
    assert low["retention"]["count_lines"] == 0.2
    assert low["papers_losing_a_hard_identifier"] == {"p": ["y"]}
    assert low["pooled"]["characters_read"] == 1_500
    assert cc.sheets_for(10_000) == 1 and cc.sheets_for(100_000) == 10


def test_cuts_at_gives_the_estimate_its_summaries():
    files = {"p": [{"sheets": 0, "characters_whole": 150_000, "characters_cut": 1_000}]}
    assert cc.cuts_at(files, 100_000, 10) == {"p": {"files": [
        {"cut": True, "characters_before": 150_000, "characters_after": 1_000}]}}
    assert cc.cuts_at(files, 200_000, 20)["p"]["files"][0]["characters_after"] == 150_000


def test_count_pattern():
    for line in ("n = 12,345", "1,234 cases", "controls: 5000", "3301 participants"):
        assert cc.COUNT.search(line), line
    assert not cc.COUNT.search("table 3 of the paper")
