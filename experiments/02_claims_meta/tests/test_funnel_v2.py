import pytest

import funnel as registered
import funnel_v2 as fn
import gate_audit as ga
from test_stage_reports import decision, extraction_row, mark, record

MARKED = [f"M{i:04d}" for i in range(700)]
BATCH_1 = ga.batch_ids(ga.draw_order(MARKED), 1)
OUTSIDE = [i for i in MARKED if i not in set(BATCH_1)]


def study(judged, sampled=(), positives=()):
    """A search of two records and one gated chase round of one unmarked record and 700 marked
    ones, of which `judged` have a decision (eligible for `positives`)."""
    runs = [fn.ScreeningRun(name="search", chase_round=None, counts={}, gated=False,
                            records=[record("A"), record("B")], marks=[mark("A"), mark("B")]),
            fn.ScreeningRun(name="chase_round_1", chase_round=1, counts={"round": 1}, gated=True,
                            records=[record("U"), *map(record, MARKED)],
                            marks=[mark("U"), *(mark(i, protein=False) for i in MARKED)],
                            gate_sampled=list(sampled))]
    decisions = [decision("A", "eligible"), decision("B", "ineligible"),
                 decision("U", "ineligible"),
                 *(decision(i, "eligible" if i in set(positives) else "ineligible")
                   for i in judged)]
    extraction = [extraction_row("A", 0), *(extraction_row(i, 0) for i in judged
                                            if i in set(positives))]
    return runs, decisions, extraction


def run(module, runs, decisions, extraction):
    return module.funnel(runs, decisions, extraction, [], [], [], {}, {})


def test_a_round_screened_in_full_without_a_sample_passes_and_says_so():
    args = study(MARKED, positives=MARKED[:3])
    with pytest.raises(registered.FunnelError):
        run(registered, *args)
    out = run(fn, *args)
    assert out["prefilter"]["chase_round_1"] == {
        "records": 701, "no_abstract_records_not_screened": 0, "marked": 700,
        "no_genetic_term": 0, "no_protein_term": 700,
        "marked_records_sampled_by_the_gate_audit": 0, "marked_records_not_screened": 0,
        "sent_to_screening": 701, "screened_in_full": True}
    assert out["eligibility"]["records_sent_to_screening"] == 703
    assert out["eligibility"]["to_extraction"] == 4
    assert out["prefiltered_citation_chasing_gate_audit"]["chase_round_1"] == {
        "sampled": 0, "no_abstract_records_of_the_round": 0, "screened_in_full": True,
        "marked_records_judged_in_full_screening": 700,
        "marked_records_judged_eligible_or_uncertain": 3}
    assert out["gate_audit_rounds_cap_reached_without_satisfying_tolerance"] == []
    assert out["prefilter"]["search"]["screened_in_full"] is False


def test_a_round_screened_in_full_after_an_unfinished_audit_passes_and_keeps_the_audit():
    args = study(MARKED, sampled=BATCH_1, positives=[BATCH_1[0], OUTSIDE[0]])
    with pytest.raises(registered.FunnelError, match="batch 2 has not been judged"):
        run(registered, *args)
    out = run(fn, *args)
    audit = out["prefiltered_citation_chasing_gate_audit"]["chase_round_1"]
    assert (audit["sampled"], audit["judged_eligible_or_uncertain"], audit["finished"]) == (
        600, 1, False)
    assert audit["screened_in_full"] and audit["marked_records_judged_eligible_or_uncertain"] == 2
    assert out["prefilter"]["chase_round_1"]["sent_to_screening"] == 701
    assert out["prefilter"]["chase_round_1"]["marked_records_sampled_by_the_gate_audit"] == 600


@pytest.mark.parametrize("judged,sampled,positives,message", [
    ([], [], [], "batch 1 has not been judged"),                  # neither audited nor screened
    (BATCH_1, BATCH_1, BATCH_1[:1], "batch 2 has not been judged"),  # audit not at its rule
    (MARKED[:-1], [], [], "batch 1 has not been judged"),         # one marked record not judged
])
def test_a_round_neither_audited_to_its_rule_nor_screened_in_full_still_raises(
        judged, sampled, positives, message):
    args = study(judged, sampled, positives)
    with pytest.raises(fn.FunnelError, match=message):
        run(fn, *args)
    with pytest.raises(registered.FunnelError):
        run(registered, *args)


def test_decisions_for_marked_records_outside_a_finished_sample_still_raise():
    args = study([*BATCH_1, OUTSIDE[0]], sampled=BATCH_1)
    with pytest.raises(fn.FunnelError, match="eligibility decisions"):
        run(fn, *args)


def test_a_round_audited_as_registered_reads_as_the_registered_script_reads_it():
    args = study(BATCH_1, sampled=BATCH_1)
    old, new = run(registered, *args), run(fn, *args)
    assert new["prefilter"]["chase_round_1"].pop("screened_in_full") is False
    assert new["prefilter"]["search"].pop("screened_in_full") is False
    assert new["prefiltered_citation_chasing_gate_audit"]["chase_round_1"].pop(
        "screened_in_full") is False
    assert new == old
    assert old["prefilter"]["chase_round_1"]["marked_records_not_screened"] == 100
    assert old["prefiltered_citation_chasing_gate_audit"]["chase_round_1"]["finished"]


def test_screened_in_full_needs_a_gate_marked_records_and_a_decision_for_each():
    held = {"a": "ineligible", "b": "eligible"}
    assert fn.screened_in_full(True, ["a", "b"], held)
    assert not fn.screened_in_full(True, ["a", "b", "c"], held)
    assert not fn.screened_in_full(False, ["a", "b"], held)
    assert not fn.screened_in_full(True, [], held)
