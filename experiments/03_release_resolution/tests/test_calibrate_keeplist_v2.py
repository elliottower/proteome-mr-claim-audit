import csv
import json
import pathlib

import pytest

import calibrate_cut as cc
import calibrate_dedup as cd
import calibrate_keeplist as ck
import calibrate_keeplist_v2 as k2
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
    names = cc.NameMatcher(rows)
    return (matcher, cd.TermSets(matcher), PATTERNS, scanner.Mapper(PATTERNS, [], rows),
            k2.Groups(str(KEEP), names, PATTERNS), ck.KeepList(str(KEEP), names, PATTERNS))


@pytest.mark.parametrize("line,groups", [
    ("UKB-PPP discovery", {"dictionary_names"}),
    ("summary statistics were downloaded", {"summary_statistics", "downloaded"}),
    ("GCST90012345", {"c1_identifiers"}),
    ("genotype build GRCh37", {"build_word"}),
    ("beta 0.12", set())])
def test_groups_and_the_narrow_list(tools, line, groups):
    got = tools[4](line)
    assert got == groups
    assert k2.narrow(got) == bool(groups - {"dictionary_names"})
    assert bool(got) == tools[5](line)


def workbook():
    rows = [f"P{i}\tUKB-PPP discovery\t" for i in range(30)]
    rows += [f"Q{i}\tq\tz" for i in range(30)] + ["note\tsummary statistics downloaded\t"]
    return {"name": "s.xlsx", "type": "XLSX", "sheets": 25, "sha256": "h",
            "text": "## sheet Table S1\nprotein\tsource\tn\n" + "\n".join(rows)}


def test_the_narrow_list_leaves_dictionary_rows_to_the_table_rule(tools):
    matcher, termsets, patterns, mapper, groups, _ = tools
    m = k2.measure_file(workbook(), matcher, termsets, patterns, mapper, groups)
    t, n, f = (m[v]["characters"] for v in k2.VARIANTS)
    assert t < n < f
    assert m["narrow_keep_list"]["b_kept"] == m["whole"]["b"]
    assert m["groups_only"]["dictionary_names"] == sum(len(f"P{i}\tUKB-PPP discovery\t") + 1
                                                      for i in range(1, 30))
    assert m["groups_any"]["summary_statistics"] == m["groups_any"]["downloaded"]


def test_aggregate_names_losses_and_sums_groups():
    f = {"characters_whole": 100, "frozen_cut": True, "whole": {"a1": 2, "a2": 3, "b": 4, "c": 5},
         "groups_any": {"x": 5}, "groups_only": {"x": 3}, "chunks": {"10000": [10], "20000": [10]},
         **{v: {"characters": 10, "a1_kept": 2, "a2_kept": 3, "b_kept": 3, "c_kept": 5}
            for v in k2.VARIANTS}}
    out = k2.aggregate({"p": [f], "q": []})
    assert out["narrow_keep_list"]["papers_losing_b"] == ["p"]
    assert out["narrow_keep_list"]["papers_losing_a1"] == []
    assert out["groups_any"] == {"x": 5} and out["chunks"]["10000"]["chunks"] == 1
