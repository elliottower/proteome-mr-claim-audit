import csv
import json
import pathlib
import random

import author_page_helper_v1 as helper
import author_page_stage_a_v1 as page
import judges_stage_a_v1 as js

EXPERIMENTS = pathlib.Path(__file__).resolve().parents[2]
DEFINITIONS = helper.load_dictionary(EXPERIMENTS / "02_claims_meta/outputs/manual_coding/"
                                     "2026-10-03/coders/dictionary_definitions.csv")
ACCESSIONS = helper.load_accessions(EXPERIMENTS / "03_release_resolution/reference/"
                                    "accession_releases.csv")
A, B = js.MODELS
ABSTRACT = "We used FinnGen R10 summary statistics for gout in 412,181 participants."
FULL = ("Introduction line.\nOutcome data came from FinnGen R10 (gout).\nUnrelated line.\n"
        "Data availability: https://www.finngen.fi/en/access_results")


def packet(rid):
    return {"record_id": "36000000", "title": "t",
            "files": [{"file_id": "abstract", "kind": "abstract", "text": ABSTRACT},
                      {"file_id": "full_text_1", "kind": "full_text", "text": FULL}],
            "rows": [{"row_id": rid, "side": "outcome", "name": "not stated",
                      "outcomes_as_written": ["gout"], "candidates": ["FinnGen R10"]}],
            "accession_table_rows": []}


def answer(rid, quote, releases=("FinnGen R10",), note="NOTE"):
    return {"row_id": rid, "identified_releases": list(releases),
            "roles": [{"release": r, "role": "primary"} for r in releases],
            "ancestry": [{"release": r, "ancestry": "EUR"} for r in releases],
            "attribution_state": "explicit", "unresolved_reasons": [],
            "decisive_evidence": [{"file_id": "full_text_1", "quote": quote, "rule": "D1",
                                   "release": r} for r in releases],
            "count_evidence": [], "abstract_transition": "none", "attribution_passage": None,
            "note": note}


ROUTING = {"tasks": {
    "disagreement": {"routed_reasons": {"d1": ["claude-fable-5-1:confidence_below_0.80"]},
                     "calibration_order": [f"c{i:02d}" for i in range(25)]},
    "audit": {"routed_reasons": {"a1": ["judges_differ"]},
              "calibration_order": ["a2", "a3"]}}}


def world():
    rows = ["d1", "a1", "a2", "a3"] + [f"c{i:02d}" for i in range(25)]
    packet_of = {r: packet(r) for r in rows}
    answers = {A: {r: answer(r, "Outcome data came from FinnGen R10 (gout).") for r in rows},
               B: {r: answer(r, "Outcome data came from FinnGen R10", releases=()) for r in rows}}
    gates = {m: {r: True for r in rows} for m in js.MODELS}
    return packet_of, answers, gates


def test_the_page_holds_routed_rows_and_the_first_20_calibration_rows_in_seeded_order():
    order = page.page_rows(ROUTING)
    expected = ([("disagreement", "d1", "routed")]
                + [("disagreement", f"c{i:02d}", "calibration") for i in range(20)]
                + [("audit", "a1", "routed"), ("audit", "a2", "calibration"),
                   ("audit", "a3", "calibration")])
    expected = sorted(expected, key=lambda x: x[1])
    random.Random(20261041).shuffle(expected)
    assert order == expected and len(order) == 24


def test_shown_text_is_the_abstract_and_the_quoted_lines_with_their_place():
    p = packet("d1")
    text = page.shown_text(p, [answer("d1", "Outcome data came from FinnGen R10 (gout).")])
    assert text == ABSTRACT + "\n\n[full_text_1, line 2] Outcome data came from FinnGen R10 (gout)."
    assert "Unrelated line" not in text


def test_the_built_page_shows_passages_link_and_aids_and_no_judge_answer():
    packet_of, answers, gates = world()
    html_page, key, counts = page.build(ROUTING, packet_of, answers, gates, DEFINITIONS,
                                        ACCESSIONS)
    assert html_page.count('<section class="card"') == 24
    assert "[full_text_1, line " in html_page and "Unrelated line" not in html_page
    assert "https://pubmed.ncbi.nlm.nih.gov/36000000/" in html_page
    assert 'class="num"' in html_page and 'class="ident"' in html_page
    assert "Dictionary rows for the resources named" in html_page
    assert 'class="inferred"' in html_page
    for word in ("fable", "astra", "confidence_below", "judges_differ", "claude", "gpt-"):
        assert word not in html_page.lower()
    assert json.dumps(page.KEY) in html_page and json.dumps(helper.KEY) not in html_page
    assert json.dumps(page.FILE_NAME) in html_page
    assert "carried over" not in html_page
    assert set(key) == {x[1] for x in page.page_rows(ROUTING)}
    assert {c["task"] for c in counts} == {"disagreement", "audit"}


def test_a_disagreement_card_orders_answers_by_the_blinding_seed():
    packet_of, answers, gates = world()
    card = page.card(1, 1, "disagreement", "d1", packet_of["d1"], answers, gates)
    first = js.blinded("d1")[0]
    block_one = card[card.index("Answer 1"):card.index("Answer 2")]
    assert ("<b>FinnGen R10</b>" in block_one) == (first == A)
