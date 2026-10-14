import hashlib

import stage_a_control_diagnostic_v1 as dg


def test_presence_is_found_after_normalization_and_not_without_the_identifier():
    files = [{"file_id": "abstract", "kind": "abstract", "text": "Nothing here."},
             {"file_id": "full_text_1", "kind": "full_text",
              "text": "Outcome data came from the FinnGen cohort (R9 – 2023) GWAS."}]
    occ = dg.occurrences("FinnGen cohort (R9", files)
    assert [o["file_id"] for o in occ] == ["full_text_1"]
    assert occ[0]["count"] == 1 and len(occ[0]["context"]) <= dg.CONTEXT
    assert dg.occurrences("FinnGen R10", files) == []


def test_the_control_source_is_located_by_its_hash_and_line():
    text = "Line zero.\nSummary statistics: ukb-b-19393 for fat mass."
    key = f"R1:1:{hashlib.sha256(text.encode()).hexdigest()[:16]}"
    files = [{"file_id": "full_text_1", "kind": "full_text", "text": text}]
    got = dg.source_in_packet(key, f"{key}:1:0", "ukb-b-19393", files)
    assert got == {"in_packet": True, "file_id": "full_text_1", "identifier_in_control_line": True}
    assert dg.source_in_packet("R1:1:0000000000000000", "R1:1:0000000000000000:1:0",
                               "ukb-b-19393", files)["in_packet"] is False


def test_classes_follow_presence_then_outcome():
    assert dg.classify(True, "recovered") is None
    assert dg.classify(False, "empty") == "a"
    assert dg.classify(True, "empty") == "b"
    assert dg.classify(True, "expected_gate_failed") == "c"
    assert dg.classify(True, "contradicted") == "d"
    assert dg.classify(True, "missing") == "d"


def test_gate_causes_name_a_layout_quote_and_an_inline_d2_identifier():
    files = [{"file_id": "full_text_1", "kind": "full_text",
              "text": "Data are in the pQTL study (doi:\n\n10.1038/ncomms14357).\n9. Suhre K. Nat Commun. 8:14357."}]
    row = {"decisive_evidence": [
        {"release": "KORA", "rule": "D2", "file_id": "full_text_1",
         "quote": "Data are in the pQTL study (doi: 10.1038/ncomms14357)."},
        {"release": "KORA", "rule": "D2_reference_entry", "file_id": "full_text_1",
         "quote": "9. Suhre K. Nat Commun. 8:14357."}]}
    checks = dg.passage_checks(row, "KORA", "10.1038/ncomms14357", files, ".,;:)]}")
    assert [c["verbatim_in_file"] for c in checks] == [False, True]
    assert checks[0]["in_file_after_normalization"] and checks[0]["holds_the_identifier"]
    assert checks[1]["holds_a_stable_identifier"] is False
    assert dg.gate_causes({"passages_of_the_expected_row": checks}) == [
        "quote_differs_only_after_normalization", "d2_identifier_inline_not_in_a_reference_entry"]
