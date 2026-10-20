import csv
import json
import pathlib

import coding_gate as gate
import coding_gate_v2 as gate2
import source_scanner_v2 as scanner

EXPERIMENTS = pathlib.Path(__file__).resolve().parents[2]
PATTERNS = json.loads((EXPERIMENTS / "03_release_resolution/reference/"
                       "c1_scanner_patterns_v2.json").read_text())
with (EXPERIMENTS / "03_release_resolution/reference/accession_releases.csv").open(newline="") as f:
    TABLE = list(csv.DictReader(f))
ROWS = gate.dictionary_rows(EXPERIMENTS / "02_claims_meta/dataset_dictionary.csv")
MAPPER = scanner.Mapper(PATTERNS, TABLE, list(ROWS.values()))
FERK = "deCODE SomaScan v4 (Ferkingstad 2021)"
DOI, PMID = "10.1038/s41588-021-00978-w", "34857953"
OTHER = "UKB-PPP discovery"
ACC = next(r for r in TABLE if r["identifier_type"] == "gwas_catalog")
INLINE = f"pQTL summary statistics were obtained from deCODE (https://doi.org/{DOI})."


def packet(text):
    return {"record_id": "r1", "rows": [], "accession_table_rows": [],
            "files": [{"file_id": "full_text_1", "kind": "full_text", "text": text}]}


def frozen(text, route=None):
    return {"full_text_1": {"key": "k", "sha256": "", "text": text}
            | ({"route": route} if route else {})}


def answer(release, quote, rule="D2"):
    return {"row_id": "a1", "identified_releases": [release],
            "decisive_evidence": [{"file_id": "full_text_1", "quote": quote, "rule": rule,
                                   "release": release}]}


def test_an_inline_doi_attributed_in_the_text_passes_and_fails_the_first_gate():
    text = "Methods.\n" + INLINE + "\nMore."
    args = ("pqtl", packet(text), frozen(text), PATTERNS, MAPPER, ROWS)
    assert not gate.gate_row(answer(FERK, INLINE), *args)["passes"]
    got = gate2.gate_row(answer(FERK, INLINE), *args)
    assert got["passes"] and got["releases"][FERK]["basis"] == "D2:inline:doi"
    assert got["to_pin"] == [{"file_id": "full_text_1", "quote": INLINE}]


def test_an_inline_pmid_passes_and_a_pmcid_alone_does_not():
    q = f"Protein data came from the deCODE study (PMID: {PMID})."
    assert gate2.gate_row(answer(FERK, q), "pqtl", packet(q), frozen(q), PATTERNS, MAPPER,
                          ROWS)["releases"][FERK]["basis"] == "D2:inline:pmid"
    q2 = "Protein data came from the deCODE study (PMC8715432)."
    assert not gate2.gate_row(answer(FERK, q2), "pqtl", packet(q2), frozen(q2), PATTERNS, MAPPER,
                              ROWS)["passes"]


def test_an_inline_identifier_of_another_source_fails():
    got = gate2.gate_row(answer(OTHER, INLINE), "pqtl", packet(INLINE), frozen(INLINE), PATTERNS,
                         MAPPER, ROWS)
    assert not got["passes"]
    assert any("inline:reference_doi_differs_from_the_dictionary_source" in f["errors"]
               for f in got["releases"][OTHER]["failures"] if isinstance(f, dict))


def test_the_same_quote_inside_a_reference_list_of_an_r3_file_fails():
    text = "Methods text.\nReferences\n" + INLINE
    got = gate2.gate_row(answer(FERK, INLINE), "pqtl", packet(text), frozen(text, "R3"),
                         PATTERNS, MAPPER, ROWS)
    assert not got["passes"]
    outside = "Methods text.\n" + INLINE + "\nReferences\nOne entry."
    assert gate2.gate_row(answer(FERK, INLINE), "pqtl", packet(outside), frozen(outside, "R3"),
                          PATTERNS, MAPPER, ROWS)["passes"]


def test_a_quote_not_in_the_frozen_file_fails():
    got = gate2.gate_row(answer(FERK, INLINE), "pqtl", packet(INLINE), frozen("other text"),
                         PATTERNS, MAPPER, ROWS)
    assert not got["passes"]


def test_d1_results_equal_the_first_gate():
    side = ROWS[ACC["dictionary_row"]]["side"]
    q = f"Summary statistics were obtained from the GWAS Catalog ({ACC['release_identifier']})."
    for release in (ACC["dictionary_row"], OTHER if side == "pqtl" else "FinnGen R10"):
        a = answer(release, q, "D1")
        args = (side, packet(q), frozen(q), PATTERNS, MAPPER, ROWS)
        assert gate2.gate_row(a, *args) == gate.gate_row(a, *args)
    assert gate2.identifiers_mapping is gate.identifiers_mapping
