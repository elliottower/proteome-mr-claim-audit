import pathlib

import author_page_helper_v1 as helper
import estimands_v1 as es
import secondary_v1 as sv
from dataset_relations import load_rows

EXPERIMENTS = pathlib.Path(__file__).resolve().parents[2]
ROWS = load_rows()
DEFS = helper.load_dictionary(EXPERIMENTS / "02_claims_meta/outputs/manual_coding/2026-10-03/"
                              "coders/dictionary_definitions.csv")
ROW = {"resource": "FinnGen", "dictionary_row": "FinnGen R10", "endpoint_label": "Gout",
       "endpoint_code": "M13_GOUT", "sex": "both", "ancestry": "not_stated",
       "cases": "1000", "controls": "200000"}


def entry(**kw):
    e = {"resource": "FinnGen", "cases": "1,000", "controls": "200 000",
         "disease_or_subtype": "gout", "incident_or_prevalent": "not_stated", "sex": "not_stated",
         "ancestry": "European", "case_definition": "", "quantitative_or_binary": "binary",
         "single_cohort_or_meta_analysis": "single_cohort", "quote": ""}
    return e | kw


def test_fields_compare_only_what_both_state():
    f = sv.fields(entry(), ROW)
    assert f["disease_or_subtype"] == "match" and f["incident_or_prevalent"] == "unknown"
    assert f["sex"] == "unknown" and f["ancestry"] == "unknown"
    assert f["quantitative_or_binary"] == "match"
    assert f["single_cohort_or_meta_analysis"] == "match"
    assert sv.fields(entry(case_definition="FinnGen M13_GOUT"), ROW)["case_definition"] == "match"
    assert sv.fields(entry(case_definition="K11_GOUT2"), ROW)["case_definition"] == "conflict"
    assert sv.fields(entry(sex="female"), ROW)["sex"] == "conflict"
    assert sv.fields(entry(disease_or_subtype="gouty arthritis"), ROW)["disease_or_subtype"] == "unknown"


def test_counts_match_digit_for_digit_within_the_named_resource():
    index = {("1000", "200000"): [ROW]}
    got = sv.count_matches([entry()], "outcome", ROWS, index)
    assert len(got) == 1 and got[0]["compatible"] and not got[0]["strict"]
    assert sv.count_inferred(got, "compatible") == "FinnGen R10"
    assert sv.count_inferred(got, "strict") is None
    assert sv.count_matches([entry(resource="UK Biobank")], "outcome", ROWS, index) == []
    assert sv.count_matches([entry(cases="1001")], "outcome", ROWS, index) == []
    conflicting = sv.count_matches([entry(sex="male")], "outcome", ROWS, index)
    assert sv.count_inferred(conflicting, "compatible") is None


def test_the_size_flag_uses_the_sealed_page_aids():
    saige = next(d for d in DEFS if d["name"].startswith("UK Biobank SAIGE"))
    size = helper.documented_size(saige["sample_size"])
    text = f"Outcome data came from the UK Biobank SAIGE PheWeb with up to {int(size):,} participants."
    got = sv.size_flag(text, [saige["name"]], saige["side"], DEFS)
    assert got == {"flag": "size_match", "row": saige["name"]}
    assert sv.size_flag("No numbers here.", [saige["name"]], saige["side"], DEFS)["flag"] is None


def code(releases=(), reasons=(), evidence=(), passage=None, counts=()):
    return {"identified_releases": list(releases), "unresolved_reasons": list(reasons),
            "decisive_evidence": list(evidence), "attribution_passage": passage,
            "count_evidence": list(counts)}


def test_levels_follow_the_amendment_order():
    lv = lambda c, acc, name, res=(), ok=False: sv.level(c, acc, name, "outcome", list(res), ROWS,
                                                         lambda: ok)
    assert lv(code(reasons=["conflicting_identifiers"]), True, "FinnGen") == "conflict"
    assert lv(code(["FinnGen R10"]), True, "FinnGen", ok=True) == "L1 release identified"
    assert lv(code(reasons=["dataset_absent_from_dictionary"]), True, "x") \
        == "L4 dataset outside the dictionary"
    assert lv(code(reasons=["release_not_identified"]), True, "MEGASTROKE") \
        == "L2 one candidate in the frozen dictionary"
    assert lv(code(reasons=["release_not_identified"]), True, "FinnGen") \
        == "L3 several candidates in the frozen dictionary"
    assert lv(code(reasons=["release_not_identified", "attribution_unresolved"]), True,
              "not stated") == "L5 no dataset named"
    assert lv(None, False, "not stated") == "name status undetermined"


def test_sa3_pair_counts_split_only_and_several_blockers():
    got = sv.sa3_pairs({"p1": ["r1"], "p2": ["r1", "r2"], "p3": ["attribution_unresolved"]},
                       {"r1": {"no_source"}, "r2": {"release_not_identified"}})
    assert got["affected"] == {"attribution_unresolved": 1, "no_source": 2,
                               "release_not_identified": 1}
    assert got["only_blocker"] == {"attribution_unresolved": 1, "no_source": 1}
    assert got["several_blockers"] == 1


def test_family_classes():
    assert sv.family_class(["disjoint", "disjoint"]) == "all_records_disjoint"
    assert sv.family_class(["disjoint", "shared_participant_source"]) == "mixed"
    assert sv.family_class(["disjoint", "unresolved"]) == "any_record_unresolved"
    assert es.ENTERING == ("primary", "meta_analysis_component")
