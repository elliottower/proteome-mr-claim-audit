import csv
import json
import pathlib

import pytest

import calibrate_containment_v2 as c2
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


def test_rows_differing_in_text_are_lost_by_k1_and_kept_by_the_rowtext_variant(tools):
    rows = [f"IL6\t{t}\t{a}\tUKB-PPP discovery" for t in ("asthma", "eczema") for a in ("EUR", "AFR")]
    m = c2.measure_file(workbook(rows), *tools)
    assert m["lost"]["units"] == 3 and m["lost"]["rows"] == 3
    assert m["lost"]["kinds"] == {"protein_or_gene": 3, "phenotype_or_trait": 3,
                                  "ancestry_or_population": 3, "cohort_or_study": 3}
    assert m["lost"]["rowtext_variant_lost_units"] == 0
    assert m["narrow_k1"]["characters"] < m["k1_rowtext"]["characters"]


def test_identical_rows_are_one_unit_and_lose_nothing(tools):
    rows = ["IL6\tasthma\tEUR\tUKB-PPP discovery"] * 5
    m = c2.measure_file(workbook(rows), *tools)
    assert m["lost"]["units"] == 0
    assert m["k1_rowtext"]["characters"] == m["narrow_k1"]["characters"]


def test_kinds_by_header():
    assert c2.lost_kinds("a\tb", "Trait\tPopulation") == {"phenotype_or_trait", "ancestry_or_population"}
    assert c2.lost_kinds("free text line", None) == {"prose"}
    assert c2.lost_kinds("a\t1", None) == {"no_header"}
    assert c2.lost_kinds("1\t2", "x\ty") == {"numeric_only"}


def test_aggregate_pools_losses_by_paper():
    f = {"characters_whole": 10, "frozen_cut": True,
         "lost": {"units": 2, "rows": 3, "characters": 40, "kinds": {"prose": 3},
                  "rowtext_variant_lost_units": 0, "unit_hashes": []},
         "chunks": {v: [5] for v in c2.VARIANTS},
         **{v: {"characters": 7, "units": 1} for v in c2.VARIANTS}}
    out = c2.aggregate({"p": [f], "q": []})
    assert out["lost_pooled"]["rows"] == 3 and list(out["lost_by_paper"]) == ["p"]
    assert out["variants"]["narrow_k1"]["chunks"]["chunks"] == 1
