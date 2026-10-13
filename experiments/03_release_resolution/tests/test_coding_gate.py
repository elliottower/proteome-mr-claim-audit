import csv
import hashlib
import json
import pathlib
import shutil

import pytest

import coding_gate as gate
import source_scanner_v2 as scanner

HERE = pathlib.Path(__file__).resolve().parents[1]
DICTIONARY = HERE.parent / "02_claims_meta" / "dataset_dictionary.csv"
PATTERNS = json.loads((HERE / "reference" / "c1_scanner_patterns_v2.json").read_text())
with (HERE / "reference" / "accession_releases.csv").open(newline="") as fh:
    TABLE = list(csv.DictReader(fh))
ROWS = gate.dictionary_rows(DICTIONARY)
MAPPER = scanner.Mapper(PATTERNS, TABLE, list(ROWS.values()))
ACC = next(r for r in TABLE if r["identifier_type"] == "gwas_catalog")
RELEASE = ACC["dictionary_row"]
SIDE = ROWS[RELEASE]["side"]
OTHER = next(n for n, r in ROWS.items() if r["side"] == SIDE and n != RELEASE)
SENTENCE = f"Summary statistics were obtained from the GWAS Catalog ({ACC['release_identifier']})."


def packet(text):
    return {"record_id": "r1", "rows": [], "accession_table_rows": [],
            "files": [{"file_id": "supplement_1_part_2", "kind": "supplement_chunk", "text": text}]}


FROZEN = {"supplement_1_part_2": {"key": "R2-1", "sha256": "0" * 64,
                                  "text": "Header.\n" + SENTENCE + "\nMore."}}


def row(release, evidence):
    return {"row_id": "a1", "identified_releases": [release], "decisive_evidence": evidence}


def test_a_d1_accession_that_maps_to_the_coded_row_passes():
    e = {"file_id": "supplement_1_part_2", "quote": SENTENCE, "rule": "D1", "release": RELEASE}
    got = gate.gate_row(row(RELEASE, [e]), SIDE, packet(SENTENCE), FROZEN, PATTERNS, MAPPER, ROWS)
    assert got["passes"] and got["releases"][RELEASE]["basis"] == "D1:identifier"
    assert got["to_pin"] == [{"file_id": "supplement_1_part_2", "quote": SENTENCE}]


def test_the_same_accession_coded_to_another_row_fails():
    e = {"file_id": "supplement_1_part_2", "quote": SENTENCE, "rule": "D1", "release": OTHER}
    got = gate.gate_row(row(OTHER, [e]), SIDE, packet(SENTENCE), FROZEN, PATTERNS, MAPPER, ROWS)
    assert not got["passes"]
    assert "no_identifier_mapping_to_the_coded_row" in got["releases"][OTHER]["failures"][0]["errors"]


def test_a_quote_not_in_the_files_fails_even_with_the_identifier():
    e = {"file_id": "supplement_1_part_2", "quote": SENTENCE + " Extra", "rule": "D1",
         "release": RELEASE}
    got = gate.gate_row(row(RELEASE, [e]), SIDE, packet(SENTENCE), FROZEN, PATTERNS, MAPPER, ROWS)
    errors = got["releases"][RELEASE]["failures"][0]["errors"]
    assert not got["passes"] and "quote_not_in_packet_file" in errors
    assert "quote_not_in_frozen_file" in errors


def test_a_row_naming_no_release_passes_and_a_wrong_side_fails():
    assert gate.gate_row({"row_id": "a", "identified_releases": [], "decisive_evidence": []},
                         SIDE, packet(""), FROZEN, PATTERNS, MAPPER, ROWS)["passes"]
    wrong = "pqtl" if SIDE == "outcome" else "outcome"
    e = {"file_id": "supplement_1_part_2", "quote": SENTENCE, "rule": "D1", "release": RELEASE}
    got = gate.gate_row(row(RELEASE, [e]), wrong, packet(SENTENCE), FROZEN, PATTERNS, MAPPER, ROWS)
    assert not got["passes"]


def test_d2_passes_only_with_a_verified_reference_entry():
    target = next((n, r) for n, r in ROWS.items()
                  if r["side"] == SIDE and gate.DOI.search(r["source_identifier"]))
    name, drow = target
    doi = gate.DOI.search(drow["source_identifier"]).group(0).rstrip(".")
    cite = "Summary statistics for the outcome were obtained from Smith et al. [12]."
    ref = f"12. Smith J. A study. Nature. 2020. doi:{doi}"
    text = cite + "\n" + ref
    frozen = {"full_text_1": {"key": "R1-1", "sha256": "1" * 64, "text": text}}
    pk = {"files": [{"file_id": "full_text_1", "kind": "full_text", "text": text}]}
    ev = [{"file_id": "full_text_1", "quote": cite, "rule": "D2", "release": name},
          {"file_id": "full_text_1", "quote": ref, "rule": "D2_reference_entry", "release": name}]
    got = gate.gate_row(row(name, ev), SIDE, pk, frozen, PATTERNS, MAPPER, ROWS)
    assert got["passes"] and got["releases"][name]["basis"] == "D2:doi"
    bad = [ev[0], {**ev[1], "quote": "12. Smith J. A study. Nature. 2020. doi:10.9999/none"}]
    frozen_bad = {"full_text_1": {**frozen["full_text_1"], "text": cite + "\n" + bad[1]["quote"]}}
    pk_bad = {"files": [{"file_id": "full_text_1", "kind": "full_text",
                         "text": frozen_bad["full_text_1"]["text"]}]}
    assert not gate.gate_row(row(name, bad), SIDE, pk_bad, frozen_bad, PATTERNS, MAPPER,
                             ROWS)["passes"]
    assert not gate.gate_row(row(name, ev[:1]), SIDE, pk, frozen, PATTERNS, MAPPER,
                             ROWS)["passes"]


def test_a_diagnostic_report_is_a_miss_only_when_verified_and_absent_from_the_cut():
    e = {"file_id": "supplement_1_part_2", "quote": SENTENCE, "rule": "D1", "release": RELEASE}
    r = row(RELEASE, [e])
    g = gate.gate_row(r, SIDE, packet(SENTENCE), FROZEN, PATTERNS, MAPPER, ROWS)
    assert gate.diagnostic_miss(g, r, kept_text="other text")
    assert not gate.diagnostic_miss(g, r, kept_text="x " + SENTENCE + " y")


@pytest.mark.skipif(shutil.which("citations") is None, reason="citations CLI not installed")
def test_pinning_resolves_with_the_citations_tool(tmp_path):
    text = FROZEN["supplement_1_part_2"]["text"]
    source = {"key": "R2-1", "sha256": hashlib.sha256(text.encode()).hexdigest(), "text": text}
    got = gate.pin(tmp_path, source, "a1_1", SENTENCE)
    assert got["pinned"], got["message"]
    refused = gate.pin(tmp_path, source, "a1_2", "a sentence the source does not hold")
    assert not refused["pinned"]
    assert gate.verify(tmp_path)["returncode"] == 0
