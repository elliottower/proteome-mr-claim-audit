import json
import pathlib

import pytest

import coding_packets as cp
import coding_queue as q
import packets_v1 as pk
from build_registry import RegistryClaim

EXPERIMENTS = pathlib.Path(__file__).resolve().parents[2]
E2 = EXPERIMENTS / "02_claims_meta"
REG = E2 / "outputs/registry/2026-10-03_amended_primary_coded_a"
CHECKS = ["outputs/verification_amendment02/amended_primary/"
          "sol_extraction_search_0b97103cd7a4_restored/claim_checks.jsonl",
          "outputs/verification_amendment02/amended_primary/"
          "sol_extraction_chase1_0b97103cd7a4_restored/claim_checks.jsonl",
          "outputs/verification/sol_extraction_chase2_0b97103cd7a4/claim_checks.jsonl",
          "outputs/verification/sol_extraction_chase3_0b97103cd7a4/claim_checks.jsonl"]
FROZEN_QUEUE = EXPERIMENTS / "03_release_resolution/outputs/coding_queue_2026-10-13.json"
ACC = cp.read_accessions(EXPERIMENTS / "03_release_resolution/reference/c1_scanner_patterns_v2.json",
                         EXPERIMENTS / "03_release_resolution/reference/accession_releases.csv")


def inputs():
    coded = [RegistryClaim.model_validate_json(line) for line in
             (REG / "registry_claims.jsonl").read_text().splitlines() if line.strip()]
    plain = {}
    for line in (REG / "registry_claims_without_manual_coding.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            plain[r["claim_record_id"]] = r
    written = {}
    for c in CHECKS:
        for line in (E2 / c).read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if "claim_record_id" in r:
                    written.setdefault(r["claim_record_id"], r["outcome_as_written"])
    return coded, plain, written


def test_on_the_claims_of_repeated_pairs_the_rule_gives_the_frozen_queue():
    coded, plain, written = inputs()
    frozen = json.loads(FROZEN_QUEUE.read_text())["queue"]
    wanted = {c for r in frozen for c in r["claim_record_ids"]}
    got = pk.queue_rows([c for c in coded if c.claim_record_id in wanted], plain, written)
    assert got == frozen
    assert got == q.queue(coded, plain, written)


def test_a_record_outside_the_scope_gets_rows_for_every_claim_record():
    coded, plain, written = inputs()
    frozen = json.loads(FROZEN_QUEUE.read_text())["queue"]
    scope = {r["record_id"] for r in frozen}
    rec = sorted({c.claim_record_id.rsplit(":", 1)[0] for c in coded} - scope)[0]
    mine = [c for c in coded if c.claim_record_id.rsplit(":", 1)[0] == rec]
    rows = pk.queue_rows(mine, plain, written)
    assert rows and {r["record_id"] for r in rows} == {rec}
    assert {c for r in rows for c in r["claim_record_ids"]} == {c.claim_record_id for c in mine}


def candidate(rec="r1", ident="FinnGen R10", side="outcome"):
    return {"row_id": q.row_id(rec, side, ident, "control"), "record_id": rec, "side": side,
            "name_as_written": ident, "expected_row": "FinnGen R10",
            "control_source_key": "R1:1:abc", "control_unit_id": "R1:1:abc:3:0"}


STUDY = [{"row_id": "000000000001", "record_id": "r1", "side": "outcome",
          "name_as_written": "not stated", "outcomes_as_written": ["gout", "asthma"],
          "candidates": ["FinnGen R10"], "kind": "study"}]
SIDES = {"outcome": ["FinnGen R10", "FinnGen R9"], "pqtl": ["P"]}


def test_control_rows_keep_the_candidate_row_id_and_take_the_record_outcomes():
    [row] = pk.control_rows([candidate()], STUDY, SIDES)
    assert row["row_id"] == candidate()["row_id"] and row["kind"] == "control"
    assert row["outcomes_as_written"] == ["gout", "asthma"]
    assert row["candidates"] == SIDES["outcome"]
    bad = candidate() | {"row_id": "ffffffffffff"}
    with pytest.raises(pk.PacketsError):
        pk.control_rows([bad], STUDY, SIDES)


def test_scope_packets_lose_only_the_listed_control_rows():
    p = {"record_id": "r1", "title": "t", "files": [{"file_id": "abstract", "kind": "abstract",
                                                    "text": "x"}],
         "accession_table_rows": [{"a": 1}],
         "rows": [{"row_id": "a"}, {"row_id": "b"}, {"row_id": "c"}]}
    got, removed = pk.scope_packet(p, {"b", "z"})
    assert removed == 1 and [r["row_id"] for r in got["rows"]] == ["a", "c"]
    assert got["files"] == p["files"] and got["accession_table_rows"] == p["accession_table_rows"]
    assert len(p["rows"]) == 3


def test_an_outside_packet_holds_abstract_and_full_texts_and_mixes_control_rows():
    controls = pk.control_rows([candidate()], STUDY, SIDES)
    sources = [{"route": "R1", "text": "Body with FinnGen R10."},
               {"route": "R3", "text": None}, {"route": "R3", "text": "Second text."}]
    [p] = pk.outside_packets("r1", "Title", "Abstract.", sources, STUDY, controls, ACC)
    assert [(f["file_id"], f["kind"]) for f in p["files"]] == [
        ("abstract", "abstract"), ("full_text_1", "full_text"), ("full_text_2", "full_text")]
    assert [r["row_id"] for r in p["rows"]] == sorted(r["row_id"] for r in STUDY + controls)
    assert all("kind" not in r and "expected_row" not in r for r in p["rows"])
    with pytest.raises(pk.PacketsError):
        pk.outside_packets("r1", "Title", "", sources, STUDY, controls, ACC)
