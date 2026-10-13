import csv
import json
import pathlib

import pytest

import calibrate_containment_v3 as c3
import calibrate_cut as cc
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
    return (matcher, cd.TermSets(matcher), PATTERNS, scanner.Mapper(PATTERNS, [], rows),
            k2.Groups(str(KEEP), cc.NameMatcher(rows), PATTERNS))


def workbook(rows):
    return {"name": "s.xlsx", "type": "XLSX", "sheets": 25, "sha256": "f" * 64,
            "text": "## sheet Table S1\nprotein\ttrait\tancestry\tsource\n" + "\n".join(rows)}


def test_rows_differing_only_in_a_numeric_cell_are_both_kept(tools):
    rows = [f"IL6\tasthma\tEUR\tUKB-PPP discovery\t{beta}" for beta in ("0.12", "0.31", "-0.05")]
    m = c3.measure_file(workbook(rows), *tools)
    assert m["registered"]["units"] == 3 and m["full_rows"]["units"] == 3
    assert m["lost_units"] == 0


def test_rows_equal_in_every_cell_after_normalization_are_one_unit(tools):
    rows = ["IL6\tasthma\tEUR\tUKB-PPP discovery\t0.12", "IL6\tAsthma \tEUR\tUKB-PPP  discovery\t0.12"]
    m = c3.measure_file(workbook(rows), *tools)
    assert m["registered"]["units"] == 1 and m["lost_units"] == 0
    one = c3.measure_file(workbook(rows[:1]), *tools)
    assert m["full_rows"]["characters"] == one["full_rows"]["characters"]


def test_the_same_row_in_two_tables_is_two_units(tools):
    entry = workbook(["IL6\tasthma\tEUR\tUKB-PPP discovery"])
    entry["text"] += "\n## sheet Table S2\nprotein\toutcome\tancestry\tsource\nIL6\tasthma\tEUR\tUKB-PPP discovery"
    m = c3.measure_file(entry, *tools)
    assert m["registered"]["units"] == 2 and m["full_rows"]["units"] == 2 and m["lost_units"] == 0


def test_aggregate_counts_losses_by_paper():
    f = {"characters_whole": 10, "frozen_cut": True, "lost_units": 2,
         "chunks": {v: [5] for v in c3.VARIANTS},
         **{v: {"characters": 7, "units": 1} for v in c3.VARIANTS}}
    out = c3.aggregate({"p": [f], "q": []})
    assert out["lost_units"] == 2 and out["lost_by_paper"] == {"p": 2}
    assert out["variants"]["full_rows"]["chunks"]["chunks"] == 1
