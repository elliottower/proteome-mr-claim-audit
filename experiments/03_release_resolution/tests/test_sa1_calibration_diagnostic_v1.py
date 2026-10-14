import adjudication_pages as ap
import sa1_calibration_diagnostic_v1 as dg


def ans(rels=(), state="unresolved", reasons=("release_not_identified",)):
    return {"identified_releases": list(rels),
            "roles": [{"release": r, "role": "primary"} for r in rels],
            "ancestry": [{"release": r, "ancestry": "European & co"} for r in rels],
            "attribution_state": state, "unresolved_reasons": list(reasons),
            "decisive_evidence": [], "attribution_passage": None, "note": "n"}


def page_of(a, b, row="abc123abc123"):
    q = {"row_id": row, "side": "outcome", "name_as_written": "FinnGen", "record_id": "1",
         "outcomes_as_written": ["x"]}
    blocks = [("q1", a, {"passes": True}), ("q2", b, {"passes": False})]
    return ap.page("t", "i", [ap.card(1, 1, q, "Text.", blocks, "")], "k", [], "f.json")


def test_the_page_rendering_round_trips_to_the_request_fields_and_a_swap_is_seen():
    one, two = ans(["FinnGen R10"], "paper_wide", []), ans()
    shown = dg.page_answers(page_of(one, two), {"abc123abc123"})["abc123abc123"]
    request = [dg.request_view(one), dg.request_view(two)]
    assert dg.label_check(shown, request) == "in_order"
    assert dg.label_check(shown, request[::-1]) == "swapped"
    assert dg.label_check(shown, [request[0], dg.request_view(ans(["FinnGen R9"]))]) == "neither"
    missing = dg.page_answers(page_of(one, None), {"abc123abc123"})["abc123abc123"]
    assert dg.label_check(missing, [request[0], None]) == "in_order"


def test_the_direction_reads_the_authors_answer_on_the_page_and_the_judges_in_the_request():
    rel, none = ans(["FinnGen R10"], "paper_wide", []), ans()
    shown = dg.page_answers(page_of(none, rel), {"abc123abc123"})["abc123abc123"]
    request = [dg.request_view(none), dg.request_view(rel)]
    assert dg.direction("answer_1", "answer_2", shown, request) == "a"
    assert dg.direction("answer_2", "answer_1", shown, request) == "b"
    assert dg.direction("answer_1", "answer_1", shown, request[::-1]) == "a"
    other = ans(["FinnGen R9"], "paper_wide", [])
    shown = dg.page_answers(page_of(other, rel), {"abc123abc123"})["abc123abc123"]
    assert dg.direction("answer_1", "answer_2", shown, [dg.request_view(other), dg.request_view(rel)]) == "c"
    shown = dg.page_answers(page_of(none, ans(state="paper_wide")), {"abc123abc123"})["abc123abc123"]
    assert dg.direction("answer_1", "answer_2", shown,
                        [dg.request_view(none), dg.request_view(ans(state="paper_wide"))]) == "d"
    assert dg.direction("neither", "answer_2", shown, shown) == "other"
