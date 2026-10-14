import pytest

import stage_a_counts_v1 as sc


def row(rels=(), state="unresolved", reasons=("release_not_identified",)):
    return {"identified_releases": list(rels),
            "roles": [{"release": r, "role": "primary"} for r in rels],
            "attribution_state": state, "unresolved_reasons": list(reasons)}


def test_agreement_counts_agree_differ_and_missing_rows():
    first = {"a": row(), "b": row(["X"]), "c": row(["X"])}
    second = {"a": {**row(), "note": "other"}, "b": row(["Y"])}
    got = sc.agreement(["a", "b", "c", "d"], first, second)
    assert got == {"rows": 4, "answered_by_both": 2, "agree": 1, "differ": 1,
                   "without_an_accepted_answer_from_a_model": 2}


def test_a_control_is_recovered_only_when_exactly_the_expected_row_passes_the_gate():
    assert sc.outcome("X", row(["X"]), True) == "recovered"
    assert sc.outcome("X", row(["X"]), False) == "expected_gate_failed"
    assert sc.outcome("X", row(["X", "Y"]), True) == "contradicted"
    assert sc.outcome("X", row(["Y"]), False) == "contradicted"
    assert sc.outcome("X", row(), True) == "empty"
    assert sc.outcome("X", None, None) == "missing"


def test_both_models_recover_only_together_and_contradict_if_either_does():
    assert sc.joint("recovered", "recovered") == "recovered"
    assert sc.joint("recovered", "empty") == "not_recovered_by_both"
    assert sc.joint("recovered", "contradicted") == "contradicted"
    assert sc.joint("missing", "recovered") == "missing"


def test_thresholds_and_minimum_decide_the_verdict():
    expected = {f"c{i}": "X" for i in range(50)}
    good = {rid: row(["X"]) for rid in expected}
    gate = {rid: True for rid in expected}
    one_wrong = dict(good, c0=row(["Y"]))
    got = sc.c1_scores(expected, {"m1": good, "m2": one_wrong}, {"m1": gate, "m2": gate}, 50)
    assert got["m1"]["recovery"] == pytest.approx(1.0) and got["m1"]["meets_thresholds"]
    assert got["m2"]["contradiction"] == pytest.approx(0.02) and got["m2"]["meets_thresholds"]
    assert got["both_models"]["counts"] == {"contradicted": 1, "recovered": 49}
    two_wrong = dict(one_wrong, c1=row(["Y"]))
    got = sc.c1_scores(expected, {"m1": good, "m2": two_wrong}, {"m1": gate, "m2": gate}, 50)
    assert not got["m2"]["meets_thresholds"]
    short = {f"c{i}": "X" for i in range(49)}
    got = sc.c1_scores(short, {"m1": good, "m2": good}, {"m1": gate, "m2": gate}, 50)
    assert got["m1"]["recovery"] == pytest.approx(1.0) and not got["m1"]["meets_thresholds"]


def test_recovery_below_ninety_percent_fails_without_any_contradiction():
    expected = {f"c{i}": "X" for i in range(100)}
    answers = {rid: (row() if i < 11 else row(["X"])) for i, rid in enumerate(expected)}
    gate = {rid: True for rid in expected}
    got = sc.c1_scores(expected, {"m1": answers}, {"m1": gate}, 50)
    assert got["m1"]["recovery"] == pytest.approx(0.89)
    assert got["m1"]["contradiction"] == pytest.approx(0.0)
    assert not got["m1"]["meets_thresholds"]
