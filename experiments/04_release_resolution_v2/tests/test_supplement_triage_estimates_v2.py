import estimands_v1 as es
import supplement_triage_estimates_v2 as st
from build_registry import RegistryClaim
from dataset_relations import load_rows, map_name

BASE = {"family_id": "r1", "protein_id": "P1", "outcome_id": "EFO:1", "direction": "not_stated",
        "direction_verified": False, "claim_scope": "overall", "context_key": "x",
        "dataset_attribution": "whole_study", "hgnc_ids": ["HGNC:1"],
        "outcome_source_ids": ["EFO:1"], "manual_dataset_codes": []}


def claim(cid, pq, oc):
    return RegistryClaim.model_validate(BASE | {"claim_record_id": cid, "pqtl_datasets": pq,
                                                "outcome_datasets": oc})


def test_split_codes_each_claim_and_leaves_other_names_and_replication_rows_alone():
    written = {"r1:000": "AD", "r1:001": "AD"}
    plain = {c: {"pqtl_datasets": ["not_stated"], "outcome_datasets": ["UK Biobank", "FinnGen"]}
             for c in written}
    claims = [claim(c, ["not_stated"], ["UK Biobank", "FinnGen"]) for c in written]
    pq = es.row_key("r1:000", "pqtl", "not_stated", "AD")
    ukb = es.row_key("r1:000", "outcome", "UK Biobank", "AD")
    split = {
        pq: {"claims": {
            "r1:000": {"state": "resolved", "absent": [],
                       "releases": [{"release": "INTERVAL SomaScan (Sun 2018)", "role": "primary"}]},
            "r1:001": {"state": "absent", "releases": [], "absent": ["Yang CSF"]}}},
        ukb: {"claims": {c: {"state": "absent", "absent": ["x"], "releases": [{
            "release": "MRC-IEU UK Biobank GWAS pipeline (OpenGWAS ukb-b)", "role": "replication"}]}
            for c in written}}}
    out, stats = st.claim_level(claims, plain, written, split)
    a, b = out
    assert a.pqtl_datasets == ("INTERVAL SomaScan (Sun 2018)",)
    assert b.pqtl_datasets == (st.absent_name("Yang CSF"),)
    assert a.outcome_datasets == b.outcome_datasets == ("UK Biobank", "FinnGen")
    assert stats == {"claim_names_replaced|resolved": 1, "claim_names_replaced|absent": 1}
    rows = load_rows()
    assert map_name(st.absent_name("Yang CSF"), "pqtl", rows).state == "unmatched"
