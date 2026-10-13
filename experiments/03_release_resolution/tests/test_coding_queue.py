import pytest

import coding_queue as q
from build_registry import RegistryClaim


def claim(cid, family, pqtl, outcome, protein="P1", outcome_id="MONDO:1"):
    return RegistryClaim(claim_record_id=cid, family_id=family, protein_id=protein,
                         outcome_id=outcome_id, direction="raises", direction_verified=True,
                         claim_scope="overall", context_key="x", pqtl_datasets=tuple(pqtl),
                         outcome_datasets=tuple(outcome), dataset_attribution="whole_study",
                         hgnc_ids=("HGNC:1",), outcome_source_ids=(outcome_id,),
                         manual_dataset_codes=())


def plain_of(claims, rename=None):
    rename = rename or {}
    return {c.claim_record_id: {"pqtl_datasets": rename.get(c.claim_record_id, list(c.pqtl_datasets)),
                                "outcome_datasets": list(c.outcome_datasets)} for c in claims}


def test_rows_follow_the_registered_unit_and_skip_unrepeated_pairs():
    claims = [claim("r1:000", "f1", ["not_stated"], ["not_stated"]),
              claim("r1:001", "f1", ["not_stated"], ["not_stated"], outcome_id="MONDO:1"),
              claim("r2:000", "f2", ["UKB-PPP"], ["FinnGen R10", "not_stated"]),
              claim("r3:000", "f3", ["deCODE"], ["FinnGen"], protein="P9")]
    written = {"r1:000": "asthma", "r1:001": "allergic asthma", "r2:000": "asthma",
               "r3:000": "gout"}
    rows = q.queue(claims, plain_of(claims), written)
    keys = {(r["record_id"], r["side"], r["name_as_written"], tuple(r["outcomes_as_written"]))
            for r in rows}
    assert keys == {("r1", "pqtl", "not stated", ()),
                    ("r1", "outcome", "not stated", ("asthma",)),
                    ("r1", "outcome", "not stated", ("allergic asthma",)),
                    ("r2", "pqtl", "UKB-PPP", ()),
                    ("r2", "outcome", "FinnGen R10", ("asthma",)),
                    ("r2", "outcome", "not stated", ("asthma",))}
    one_pqtl = next(r for r in rows if r["record_id"] == "r1" and r["side"] == "pqtl")
    assert one_pqtl["claim_record_ids"] == ["r1:000", "r1:001"]


def test_names_come_from_the_plain_assembly_not_the_manual_codes():
    claims = [claim("r1:000", "f1", ["UKB-PPP discovery"], ["not_stated"]),
              claim("r2:000", "f2", ["UKB-PPP"], ["not_stated"])]
    rows = q.queue(claims, plain_of(claims, {"r1:000": ["UK Biobank proteomics"]}),
                   {"r1:000": "a", "r2:000": "a"})
    assert {r["name_as_written"] for r in rows if r["side"] == "pqtl"} == {
        "UK Biobank proteomics", "UKB-PPP"}


def test_candidates_are_dictionary_rows_only():
    claims = [claim("r1:000", "f1", ["UKB-PPP"], ["not_stated"]),
              claim("r2:000", "f2", ["INTERVAL"], ["not_stated"])]
    rows = q.queue(claims, plain_of(claims), {"r1:000": "a", "r2:000": "a"})
    names = q.side_rows()
    for r in rows:
        assert set(r["candidates"]) <= set(names[r["side"]])
        assert not any(c.startswith("unlisted") for c in r["candidates"])
    not_stated = next(r for r in rows if r["side"] == "outcome")
    assert not_stated["candidates"] == names["outcome"]


def test_row_ids_are_stable_and_distinct():
    a = q.row_id("r1", "outcome", "not_stated", "asthma")
    assert a == q.row_id("r1", "outcome", "not_stated", "asthma")
    assert a != q.row_id("r1", "outcome", "not_stated", "eczema")
    assert len(a) == 12


def test_a_claim_without_its_outcome_as_written_stops_the_queue():
    claims = [claim("r1:000", "f1", ["x"], ["y"]), claim("r2:000", "f2", ["x"], ["y"])]
    with pytest.raises(q.QueueError):
        q.queue(claims, plain_of(claims), {"r1:000": "a"})
