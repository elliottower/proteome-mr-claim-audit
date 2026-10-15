import hashlib
import json
import pathlib
import random

import pytest

import control_validity_v1 as cv

HERE = pathlib.Path(__file__).resolve().parents[1]
PROMPT = (HERE / "prompts" / "control_validity_prompt_v1.md").read_text()
SCHEMA = json.loads((HERE / "prompts" / "control_validity_schema_v1.json").read_text())
RUBRIC = ("A control is valid when its source sentence or table row attributes its identifier to "
          "the dataset of the control's own side for the record's claim: for an outcome-side "
          "control, the dataset of the claim's outcome; for a pQTL-side control, the pQTL dataset "
          "of the claim's exposure protein. It is invalid when the identifier belongs to another "
          "role on that side (an exposure or covariate for an outcome-side control, another "
          "outcome, a replication or secondary analysis), or when it names one component of a "
          "meta-analysis or combined dataset while the claim's dataset for that side is the "
          "combined one. An identifier of a component the claim analysed alone is valid.")

PROSE = ("Introduction text. Exposure data came from the INTERVAL study. Outcome data came from "
         "FinnGen R9 for glaucoma. Results follow.\nNext line here.")
TABLE = "Trait\tSource\nGlaucoma\tfinn-b-H7_GLAUCOMA\nAsthma\tukb-b-1"


def key(route, n, text):
    return f"{route}:{n}:{hashlib.sha256(text.encode()).hexdigest()[:16]}"


SOURCES = [{"route": "R2", "type": "PDF", "text": None},
           {"route": "R1", "type": "XML", "text": PROSE},
           {"route": "R3", "type": "TSV", "text": TABLE}]
K1, K3 = key("R1", 1, PROSE), key("R3", 2, TABLE)


def flat(text):
    return " ".join(text.split())


def test_the_prompt_holds_the_rubric_verbatim():
    assert RUBRIC in flat(PROMPT)


def test_the_prompt_says_nothing_of_recovery_coders_or_the_diagnostic():
    low = PROMPT.lower()
    for word in ("recover", "coder", "diagnostic", "gate", "answer", "expected", "deviation"):
        assert word not in low


def test_the_schema_marks_are_the_three_of_the_task():
    assert SCHEMA["properties"]["mark"]["enum"] == list(cv.MARKS)
    assert set(SCHEMA["required"]) == {"row_id", "mark", "reason", "quotation"}


def test_a_sentence_unit_is_given_with_the_sentences_on_either_side():
    got = cv.passage("r1", SOURCES, K1, f"{K1}:0:2")
    assert got == {"text": "Outcome data came from FinnGen R9 for glaucoma.",
                   "before": "Exposure data came from the INTERVAL study.",
                   "after": "Results follow.", "table_header": None}
    last = cv.passage("r1", SOURCES, K1, f"{K1}:1:0")
    assert last["before"] == "Results follow." and last["after"] is None


def test_a_table_row_is_given_with_its_header_and_neighbouring_rows():
    got = cv.passage("r1", SOURCES, K3, f"{K3}:1:0")
    assert got["text"] == "Glaucoma\tfinn-b-H7_GLAUCOMA"
    assert got["table_header"] == "Trait\tSource"
    assert got["after"] == "Asthma\tukb-b-1"


def test_a_source_key_whose_digest_or_route_differs_is_refused():
    with pytest.raises(cv.PacketError):
        cv.passage("r1", SOURCES, "R1:1:0000000000000000", "R1:1:0000000000000000:0:2")
    with pytest.raises(cv.PacketError):
        cv.passage("r1", SOURCES, K1.replace("R1", "R3", 1), f"{K1.replace('R1', 'R3', 1)}:0:2")
    with pytest.raises(cv.PacketError):
        cv.passage("r1", SOURCES, K1, f"{K1}:0:9")


def test_claims_come_from_the_first_check_of_each_claim_record_of_the_record():
    queue = [{"record_id": "r1", "claim_record_ids": ["r1:000", "r1:001"]},
             {"record_id": "r1", "claim_record_ids": ["r1:001"]},
             {"record_id": "r2", "claim_record_ids": ["r2:000"]}]
    checks = [{"claim_record_id": "r1:001", "protein_as_written": "IL6R",
               "outcome_as_written": "CAD", "direction": "lowers"},
              {"claim_record_id": "r1:001", "protein_as_written": "LATER",
               "outcome_as_written": "LATER", "direction": "raises"},
              {"claim_record_id": "r1:000", "protein_as_written": "IL6R",
               "outcome_as_written": "CAD", "direction": "lowers"},
              {"claim_record_id": "r2:000", "protein_as_written": "PCSK9",
               "outcome_as_written": "MI", "direction": "not_stated"}]
    got = cv.claims_of_records(queue, checks)
    assert got["r1"] == [{"protein": "IL6R", "outcome": "CAD", "direction": "lowers"}]
    assert got["r2"] == [{"protein": "PCSK9", "outcome": "MI", "direction": "not_stated"}]


def test_a_packet_holds_only_the_fields_the_deviation_allows():
    control = {"row_id": "c1", "record_id": "r1", "side": "outcome",
               "name_as_written": "FinnGen R9", "outcomes_as_written": ["glaucoma"],
               "candidates": ["FinnGen R9"], "kind": "control", "expected_row": "FinnGen R9",
               "control_source_key": K1, "control_unit_id": f"{K1}:0:2"}
    p = cv.packet(control, SOURCES, [{"protein": "X", "outcome": "glaucoma", "direction": "raises"}])
    assert set(p) == {"row_id", "side", "identifier", "passage", "claims"}
    assert "FinnGen R9" not in json.dumps(p["claims"]) and "expected" not in json.dumps(p)
    assert cv.file_bytes(p) == cv.file_bytes(json.loads(cv.file_bytes(p)))


def test_the_order_is_the_sorted_ids_shuffled_by_the_seed():
    ids = [f"{i:012x}" for i in range(70)]
    expected = sorted(ids)
    random.Random(20261032).shuffle(expected)
    assert cv.SEED == 20261032
    assert cv.order(list(reversed(ids))) == expected


def test_only_agreement_decides_and_every_other_pair_is_retained_as_valid():
    assert cv.combine("valid", "valid") == "valid"
    assert cv.combine("invalid", "invalid") == "invalid"
    for pair in [("valid", "invalid"), ("invalid", "valid"), ("cannot_mark", "cannot_mark"),
                 ("invalid", "cannot_mark"), ("invalid", None), (None, None)]:
        assert cv.combine(*pair) == "disputed_retained_valid"
    assert cv.mark_of({"state": "failed", "decision": None}) is None
    assert cv.mark_of({"state": "accepted", "decision": {"mark": "invalid"}}) == "invalid"


def test_counts_add_disputed_controls_to_the_valid_ones():
    got = cv.counts({"a": "valid", "b": "invalid", "c": "disputed_retained_valid"})
    assert got == {"controls": 3, "both_valid": 1, "both_invalid": 1,
                   "disputed_retained_valid": 1, "valid_controls": 2}
