import json

import pytest

import span_restoration as sr

ABSTRACT = ("Background comes first.\nHigher protein X was causally associated with lower risk "
            "of stroke (OR 0.90, P = 3 × 10−6). Higher protein Y raised LDL cholesterol.")
WHOLE = "Higher protein X was causally associated with lower risk of stroke (OR 0.90, P = 3 × 10−6)."
DROPPED = WHOLE.replace("causally ", "")


def test_a_span_missing_one_whole_token_is_restored_from_the_abstract_by_offset():
    made = sr.restore_span(DROPPED, ABSTRACT)
    assert made["passage"] == WHOLE == ABSTRACT[made["start"]:made["end"]]
    assert made["omitted_after_span_token"] == 4
    assert ABSTRACT.split()[made["omitted_token_index_in_abstract"]] == "causally"


def test_case_and_white_space_differences_do_not_matter_and_the_source_text_is_returned():
    made = sr.restore_span(DROPPED.upper().replace(" ", "  "), ABSTRACT)
    assert made["passage"] == WHOLE
    partial = "protein X was associated with lower risk of stro"
    assert sr.restore_span(partial, "Higher apoprotein X was causally associated with lower "
                                    "risk of stroke.")["passage"] == (
        "protein X was causally associated with lower risk of stro")


@pytest.mark.parametrize("span", [
    WHOLE,                                                      # passes the registered check
    WHOLE.replace("causally associated ", ""),                  # two tokens left out
    DROPPED.replace("lower", "higher"),                         # a substituted word
    DROPPED.replace("0.90", "0.9"),                             # a truncated number
    DROPPED.replace("10−6", "106"),                             # a changed sign
    WHOLE.replace("(OR ", "("),                                 # a token cut inside a compound
    "Higher protein Y raised LDL",                              # one stretch of the abstract
    "Sortilin was associated with another outcome entirely.",   # no counterpart
    "stroke",                                                   # a single token
])
def test_anything_else_is_not_eligible(span):
    assert sr.restore_span(span, ABSTRACT) is None


def test_an_alignment_that_can_be_made_twice_is_not_eligible():
    twice = "We saw A big B effect here. Later we saw A small B effect here."
    assert sr.restore_span("saw A B effect", twice) is None
    assert sr.restore_span("We saw A B effect", twice) is None
    assert sr.restore_span("Later we saw A B effect", twice)["passage"] == (
        "Later we saw A small B effect")


def test_the_junction_tokens_must_be_whole():
    text = "Risk fell with higher IL6R levels overall."
    assert sr.restore_span("with higher levels overall", text)["passage"] == (
        "with higher IL6R levels overall")
    assert sr.restore_span("igher levels overall", text) is None
    assert sr.restore_span("with higher level", text) is None


def rows():
    return [{"pmid": "p1", "status": "ok", "output": {"claims": [
        {"evidence_span": DROPPED, "direction": "lowers"},
        {"evidence_span": "Higher protein Y raised LDL cholesterol.", "direction": "raises"}]}},
        {"pmid": "p2", "status": "extraction_failed", "output": None}]


def test_only_the_eligible_span_changes_and_the_map_holds_hashes_not_text():
    repairs, restored = sr.restore_file(rows(), {"p1": ABSTRACT}, "abc")
    assert list(repairs) == ["p1:000"]
    entry = repairs["p1:000"]
    assert entry["restored_passage_sha256"] == sr.sha(WHOLE)
    assert entry["original_span_sha256"] == sr.sha(DROPPED)
    assert entry["source_sha256"] == sr.sha(ABSTRACT) and entry["rule"] == sr.RULE
    assert ABSTRACT[entry["source_offsets"][0]:entry["source_offsets"][1]] == WHOLE
    assert "protein" not in json.dumps(repairs)
    original = rows()
    assert restored[0]["output"]["claims"][0] == {"evidence_span": WHOLE, "direction": "lowers"}
    assert restored[0]["output"]["claims"][1] == original[0]["output"]["claims"][1]
    assert restored[1] == original[1]


def check(rid, **more):
    base = {"claim_record_id": rid, "protein_mapping_state": "mapped",
            "outcome_mapping_state": "mapped", "parsed_direction": "lowers",
            "direction_method": "estimate", "enters_registry": False,
            "enters_direction_results": False, "direction_check": "agrees",
            "first_failure": "span_not_verified", "protein_ids": ["HGNC:1"],
            "outcome_ids": ["EFO:1"]}
    return base | more


def test_transitions_are_counted_for_restored_records_and_differences_listed_for_others():
    before = [check("p1:000"), check("p1:001", enters_registry=True, first_failure=None),
              check("p2:000", enters_registry=True, first_failure=None)]
    after = [check("p1:000", enters_registry=True, enters_direction_results=True,
                   first_failure=None, direction_method="lexicon"),
             check("p1:001", enters_registry=True, first_failure=None,
                   direction_method="lexicon_mixed_span"),
             before[2]]
    made = sr.transition_counts({"p1:000": {}}, before, after)
    assert made["restored_records"] == 1
    assert made["transitions"]["enters_registry"] == {"False -> True": 1}
    assert made["transitions"]["direction_method"] == {"estimate -> lexicon": 1}
    assert made["transitions"]["protein_ids"] == {"same": 1}
    assert (made["restored_entering_registry_before"],
            made["restored_entering_registry_after"]) == (0, 1)
    assert made["other_records"] == 2 and made["other_records_differing"] == ["p1:001"]
    assert made["other_records_differing_share_a_paper_with_a_restored_record"] == 1
    with pytest.raises(sr.RestorationError):
        sr.transition_counts({"p1:000": {}}, before, after[:2])
