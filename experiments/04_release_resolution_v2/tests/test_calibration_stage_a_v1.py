import pytest

import calibration_stage_a_v1 as cs
import sa1_calibration_v1 as cal


def world(audit_marks, disagreement_marks=("answer_1", "answer_2")):
    d_rows = [f"d{i}" for i in range(len(disagreement_marks))]
    a_cal = [f"a{i:02d}" for i in range(len(audit_marks))]
    routing = {"tasks": {
        "disagreement": {"rows": 10, "routed": 8, "lone": len(d_rows), "seed": 20261038,
                         "routed_reasons": {"r1": ["x"]}, "calibration_order": d_rows,
                         "calibration_first": d_rows},
        "audit": {"rows": 69, "routed": 2, "lone": 41, "seed": 20261039,
                  "routed_reasons": {"ra": ["x"], "rb": ["y"]},
                  "calibration_order": a_cal + [f"z{i}" for i in range(21)],
                  "calibration_first": a_cal}}}
    key = {**{r: {"task": "disagreement", "why_on_page": "calibration", "answer_1": "m"}
              for r in d_rows},
           "r1": {"task": "disagreement", "why_on_page": "routed", "answer_1": "m"},
           **{r: {"task": "audit", "why_on_page": "calibration", "answer_1": None} for r in a_cal},
           "ra": {"task": "audit", "why_on_page": "routed", "answer_1": None},
           "rb": {"task": "audit", "why_on_page": "routed", "answer_1": None}}
    marks = ([{"row_id": r, "choice": c} for r, c in zip(d_rows, disagreement_marks)]
             + [{"row_id": "r1", "choice": "neither"}]
             + [{"row_id": r, "choice": c} for r, c in zip(a_cal, audit_marks)]
             + [{"row_id": "ra", "choice": "substantive_error"},
                {"row_id": "rb", "choice": "correct"}])
    joint = {**{r: "answer_1" for r in d_rows}, **{r: "correct" for r in a_cal}}
    return marks, key, routing, joint


def test_the_registered_verdicts_and_the_escalation_count_come_from_the_sealed_scorer():
    marks, key, routing, joint = world(["correct"] * 19 + ["substantive_error"])
    got = cs.calibrate(marks, key, routing, joint)
    assert got["tasks"]["disagreement"]["differences"] == 1
    assert got["tasks"]["disagreement"]["verdict"] == "pass"
    assert got["tasks"]["audit"]["differences"] == 1 and got["tasks"]["audit"]["verdict"] == "pass"
    assert got["escalation"]["author_substantive_errors"] == 2
    assert got["escalation"]["triggered"] is True


def test_three_audit_differences_fail_the_task_and_send_the_sample_to_the_author():
    marks, key, routing, joint = world(["other_issue"] * 3 + ["correct"] * 17)
    got = cs.calibrate(marks, key, routing, joint)
    assert got["tasks"]["audit"]["verdict"] == "fail"
    assert "whole audit sample goes to the author" in got["consequences"]["audit_judge_decisions"]


def test_a_page_whose_calibration_rows_are_not_the_registered_ones_is_refused():
    marks, key, routing, joint = world(["correct"] * 20)
    routing["tasks"]["audit"]["calibration_first"] = ["a00"]
    with pytest.raises(cal.CalibrationError):
        cs.calibrate(marks, key, routing, joint)
