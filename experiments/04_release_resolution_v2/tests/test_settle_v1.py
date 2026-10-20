import settle_v1 as st


def answer(rid="r1", releases=("FinnGen R10",), state="explicit", reasons=(), ancestry="EUR",
           role="primary", quote="q"):
    return {"row_id": rid, "identified_releases": list(releases),
            "roles": [{"release": r, "role": role} for r in releases],
            "ancestry": [{"release": r, "ancestry": ancestry} for r in releases],
            "attribution_state": state, "unresolved_reasons": list(reasons),
            "decisive_evidence": [{"file_id": "full_text_1", "quote": quote, "rule": "D1",
                                   "release": r} for r in releases],
            "count_evidence": [], "abstract_transition": "none",
            "attribution_passage": {"file_id": "full_text_1", "quote": quote}, "note": ""}


def test_a_row_differing_only_in_attribution_is_settled_conservatively():
    a = answer(state="explicit", quote="qa")
    b = answer(state="paper_wide", quote="qb")
    out = st.split(["r1"], {"r1": a}, {"r1": b}, {"r1": True}, {"r1": True})
    assert out["agreed"] == [] and out["disagreements"] == []
    code = out["settled"]["r1"]
    assert code["attribution_state"] == "paper_wide"
    assert len(code["decisive_evidence"]) == 2 and len(code["attribution_passages"]) == 2
    assert out["settled_by_attribution_pair"] == {"explicit|paper_wide": 1}


def test_unresolved_adds_its_reason_to_the_union():
    a = answer(releases=(), state="unresolved", reasons=("release_not_identified",))
    b = answer(releases=(), state="explicit", reasons=("dataset_absent_from_dictionary",))
    code = st.split(["r1"], {"r1": a}, {"r1": b}, {"r1": True}, {"r1": True})["settled"]["r1"]
    assert code["attribution_state"] == "unresolved"
    assert code["unresolved_reasons"] == ["attribution_unresolved",
                                          "dataset_absent_from_dictionary",
                                          "release_not_identified"]


def test_rows_that_are_not_release_concordant_go_on_as_disagreements():
    base = answer()
    cases = [
        (answer(releases=("FinnGen R9",)), True, True),
        (answer(role="replication", state="paper_wide"), True, True),
        (answer(ancestry="EAS", state="paper_wide"), True, True),
        (answer(state="paper_wide", reasons=("conflicting_identifiers",)), True, True),
        (answer(state="paper_wide"), True, False),
    ]
    for other, ga, gb in cases:
        out = st.split(["r1"], {"r1": base}, {"r1": other}, {"r1": ga}, {"r1": gb})
        assert out["disagreements"] == ["r1"] and not out["settled"]


def test_agreed_and_missing_rows():
    a = answer()
    out = st.split(["r1", "r2"], {"r1": a, "r2": answer("r2")}, {"r1": answer(quote="other")},
                   {"r1": True}, {"r1": True})
    assert out["agreed"] == ["r1"] and out["disagreements"] == ["r2"]
