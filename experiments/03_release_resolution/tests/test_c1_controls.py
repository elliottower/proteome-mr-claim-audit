import csv
import json
import pathlib

import pytest

import c1_controls as c1
import coding_packets as cp
import coding_queue as q
import source_scanner_v2 as scanner

HERE = pathlib.Path(__file__).resolve().parents[1]
DICTIONARY = HERE.parent / "02_claims_meta" / "dataset_dictionary.csv"
PATTERNS = json.loads((HERE / "reference" / "c1_scanner_patterns_v2.json").read_text())
TABLE = c1.read_table(HERE / "reference" / "accession_releases.csv")
ACC = cp.read_accessions(HERE / "reference" / "c1_scanner_patterns_v2.json",
                         HERE / "reference" / "accession_releases.csv")


@pytest.fixture(scope="module")
def dictionary():
    with DICTIONARY.open(newline="") as fh:
        return list(csv.DictReader(fh))


@pytest.fixture(scope="module")
def mapper(dictionary):
    return scanner.Mapper(PATTERNS, TABLE, dictionary)


def mapped_accession():
    return next(r for r in TABLE if r["identifier_type"] == "gwas_catalog")


def test_units_split_prose_by_sentence_and_keep_table_rows_whole():
    src = [{"route": "R1", "text": "## Methods\nWe used GWAS data. Second sentence here.\n"
                                   "[Table 1. Data] Source: FinnGen | GWAS ID: X"},
           {"route": "R2", "type": "CSV", "text": "trait\tid\nasthma\tGCST1"}]
    u = c1.units("r1", src)
    texts = [x["text"] for x in u]
    assert texts == ["We used GWAS data.", "Second sentence here.",
                     "[Table 1. Data] Source: FinnGen | GWAS ID: X", "trait\tid", "asthma\tGCST1"]
    assert u[0]["section_title"] == "Methods"
    assert u[-1]["header"] == "trait\tid"
    assert len({x["unit_id"] for x in u}) == len(u)


def test_reference_lists_of_pdfs_are_marked_and_jats_bodies_never_are():
    pdf = {"route": "R3", "type": "PDF", "text": "Body GWAS GCST1.\nReferences\n[1] Ref GWAS GCST2."}
    u = c1.units("r1", [pdf])
    assert [x["in_reference_list"] for x in u] == [False, True]
    jats = {"route": "R1", "text": "References\nGWAS GCST1."}
    assert not any(x["in_reference_list"] for x in c1.units("r1", [jats]))


def test_the_scan_finds_a_mapped_accession_in_context_and_draws_it(mapper):
    acc = mapped_accession()
    src = [{"route": "R1", "text": f"## Methods\nGWAS summary statistics ({acc['release_identifier']}) "
                                   "were downloaded.\nNo context word but "
                                   f"{acc['release_identifier']} here."}]
    got = c1.scan(c1.units("r1", src), PATTERNS, mapper)
    assert len(got["found"]) == 1 and got["found"][0]["expected_row"] == acc["dictionary_row"]
    assert got["drawn"] == got["found"] and got["extension_needed"] is True


def test_control_rows_look_like_study_rows_and_mix_in_by_row_id(dictionary):
    sides = q.side_rows(DICTIONARY)
    acc = mapped_accession()
    side = next(r["side"] for r in dictionary if r["name"] == acc["dictionary_row"])
    drawn = [{"record_id": "r1", "side": side, "identifier": acc["release_identifier"],
              "expected_row": acc["dictionary_row"], "source_key": "R1:1:x", "unit_id": "u"}]
    study = [{"row_id": "b" * 12, "record_id": "r1", "side": "outcome", "name_as_written": "x",
              "outcomes_as_written": ["asthma"], "candidates": ["c"], "kind": "study"}]
    rows = c1.control_rows(drawn, study, sides)
    assert rows[0]["candidates"] == sides[side] and rows[0]["name_as_written"] == acc["release_identifier"]
    if side == "outcome":
        assert rows[0]["outcomes_as_written"] == ["asthma"]
    merged = c1.merge(study, rows)
    assert [r["row_id"] for r in merged] == sorted(r["row_id"] for r in merged)
    shown = cp.shown_rows(merged)
    assert all(set(s) <= {"row_id", "side", "name", "outcomes_as_written", "candidates"}
               for s in shown)


def test_manifest_packets_take_one_identifier_per_mapped_row(dictionary):
    side_of = {r["name"]: r["side"] for r in dictionary}
    packets = c1.manifest_packets(TABLE, side_of, q.side_rows(DICTIONARY), ACC)
    rows = {r["dictionary_row"] for r in TABLE if r["identifier_type"] != "opengwas_batch"}
    assert {p["expected_row"] for p in packets} == rows
    for p in packets:
        assert p["identifier"] in p["packet"]["files"][0]["text"]
        assert any(a["release_identifier"] == p["identifier"]
                   for a in p["packet"]["accession_table_rows"])
        assert p["packet"]["rows"][0]["name"] == "not stated"
