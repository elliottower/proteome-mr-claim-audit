import adjudication_pages as ap

A, B = "claude-sonnet-5-5", "gpt-6.1-sol"


def ans(rels=(), quote=None, state="unresolved"):
    return {"row_id": "x", "identified_releases": list(rels),
            "roles": [{"release": r, "role": "primary"} for r in rels],
            "ancestry": [{"release": r, "ancestry": "not_stated"} for r in rels],
            "attribution_state": state, "unresolved_reasons": [] if rels else ["release_not_identified"],
            "decisive_evidence": [{"file_id": "abstract", "quote": quote, "rule": "D1",
                                   "release": rels[0]}] if quote else [],
            "count_evidence": [], "abstract_transition": "none", "attribution_passage": None,
            "note": "n"}


def test_the_audit_takes_ten_percent_at_least_thirty_and_all_when_fewer():
    assert len(ap.audit_draw([f"r{i}" for i in range(495)], 1)) == 50
    assert len(ap.audit_draw([f"r{i}" for i in range(100)], 1)) == 30
    assert len(ap.audit_draw([f"r{i}" for i in range(12)], 1)) == 12
    rows = [f"r{i}" for i in range(495)]
    assert ap.audit_draw(rows, 7) == ap.audit_draw(rows, 7) != ap.audit_draw(rows, 8)


def test_blinding_is_fixed_per_row_and_mixes_the_order():
    flips = [ap.first_is_a(f"row{i}", 5) for i in range(400)]
    assert flips == [ap.first_is_a(f"row{i}", 5) for i in range(400)]
    assert 150 < sum(flips) < 250


def test_quotes_are_marked_per_answer_and_where_they_meet():
    got = ap.highlight("We used FinnGen R10 data. Other.", {"q1": ["FinnGen R10 data."],
                                                           "q2": ["We used FinnGen"]})
    assert '<mark class="q2">We used </mark>' in got and '<mark class="both">FinnGen</mark>' in got
    assert '<mark class="q1"> R10 data.</mark>' in got


def test_pages_hold_every_disagreement_and_the_audit_and_never_name_a_model():
    order = ["r1", "r2", "r3"]
    queue = {r: {"row_id": r, "record_id": "123", "side": "outcome", "name_as_written": "x",
                 "outcomes_as_written": ["asthma"]} for r in order}
    answers = {A: {"r1": ans(["FinnGen R10"], "FinnGen R10"), "r2": ans(), "r3": ans()},
               B: {"r1": ans(), "r2": ans()}}
    verdicts = {A: {r: {"passes": True} for r in order}, B: {r: {"passes": True} for r in order}}
    got = ap.build("sa1", queue, {"123": "We used FinnGen R10."}, answers, verdicts, order,
                   (A, B), 1, 2)
    m = got["manifest"]
    assert m["disagreement_row_ids"] == ["r1", "r3"] and m["audit_row_ids"] == ["r2"]
    for html_page in got["pages"].values():
        assert A not in html_page and B not in html_page and "claude" not in html_page.lower()
        assert "gpt" not in html_page.lower() and "sonnet" not in html_page.lower()
    assert set(got["key"]) == {"r1", "r3"}
    assert {got["key"]["r1"]["answer_1"], got["key"]["r1"]["answer_2"]} == {A, B}
    assert "pubmed.ncbi.nlm.nih.gov/123/" in got["pages"]["disagreement"]
