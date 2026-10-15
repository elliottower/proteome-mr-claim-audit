import csv
import json
import pathlib

import coding_gate as gate
import manifest_mapping_check_v1 as mc
import source_scanner_v2 as scanner

HERE = pathlib.Path(__file__).resolve().parents[1]
PATTERNS = json.loads((HERE / "reference" / "c1_scanner_patterns_v2.json").read_text())
with (HERE / "reference" / "accession_releases.csv").open(newline="") as fh:
    TABLE = list(csv.DictReader(fh))
ROWS = gate.dictionary_rows(HERE.parent / "02_claims_meta" / "dataset_dictionary.csv")
MAPPER = scanner.Mapper(PATTERNS, TABLE, list(ROWS.values()))
ACC = next(r for r in TABLE if r["identifier_type"] == "gwas_catalog")
RELEASE = ACC["dictionary_row"]
SIDE = ROWS[RELEASE]["side"]
OTHER = next(n for n, r in ROWS.items() if r["side"] == SIDE and n != RELEASE)


def packet(identifier, side=SIDE):
    return {"record_id": "manifest_x", "title": "", "accession_table_rows": [],
            "rows": [{"row_id": "m1", "side": side, "name": "not stated"}],
            "files": [{"file_id": "supplement_1", "kind": "supplement",
                       "text": f"resource\trelease_identifier\nGWAS Catalog\t{identifier}"}]}


def entry(expected, identifier=ACC["release_identifier"]):
    return {"row_id": "m1", "identifier": identifier, "expected_row": expected}


def test_an_accession_of_the_table_returns_its_row_by_every_check():
    got = mc.check(entry(RELEASE), packet(ACC["release_identifier"]), PATTERNS, MAPPER, ROWS)
    assert got["returned_row_identifier"] == [RELEASE] == got["returned_row_packet_file"]
    assert got["pass"] and all(got["checks"].values())


def test_a_wrong_expected_row_fails_every_check():
    got = mc.check(entry(OTHER), packet(ACC["release_identifier"]), PATTERNS, MAPPER, ROWS)
    assert got["returned_row_identifier"] == [RELEASE]
    assert not any(got["checks"].values()) and not got["pass"]


def test_an_accession_absent_from_the_table_returns_no_row():
    got = mc.check(entry(RELEASE, "GCST999999999"), packet("GCST999999999"), PATTERNS, MAPPER,
                   ROWS)
    assert got["returned_row_identifier"] == [] and not got["pass"]


def test_a_row_of_the_other_side_fails_the_gate():
    other_side = next(s for s in ("outcome", "pqtl") if s != SIDE)
    got = mc.check(entry(RELEASE), packet(ACC["release_identifier"], other_side), PATTERNS,
                   MAPPER, ROWS)
    assert got["checks"]["identifier"] and not got["checks"]["gate_row"] and not got["pass"]
