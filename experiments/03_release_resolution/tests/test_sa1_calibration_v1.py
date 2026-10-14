import math
import random

import pytest

import sa1_calibration_v1 as cal


def test_the_verdict_follows_amendment_3_item_3():
    assert [cal.verdict(d) for d in range(5)] == ["pass", "pass", "needs_next_20", "fail", "fail"]
    assert cal.verdict(2, 1) == "pass" and cal.verdict(2, 2) == "fail"


def test_the_exact_interval_matches_clopper_pearson_and_covers_at_the_nominal_rate():
    assert cal.clopper_pearson(20, 20)[0] == pytest.approx(0.8316, abs=1e-4)
    lo, hi = cal.clopper_pearson(19, 20)
    assert (lo, hi) == (pytest.approx(0.7513, abs=1e-4), pytest.approx(0.9987, abs=1e-4))
    n, intervals = 20, [cal.clopper_pearson(k, 20) for k in range(21)]
    for p in [random.random() for _ in range(200)]:
        cover = sum(math.comb(n, k) * p ** k * (1 - p) ** (n - k)
                    for k, (lo, hi) in enumerate(intervals) if lo <= p <= hi)
        assert cover >= 0.95 - 1e-9


def setup(disagree_marks, audit_marks, routed_marks, joint_d, joint_a):
    dis = [f"d{i:02d}" for i in range(20)]
    aud = [f"a{i:02d}" for i in range(20)]
    rout = ["r0", "r1"]
    key = {r: {"task": "disagreement", "why_on_page": "calibration"} for r in dis}
    key |= {r: {"task": "audit", "why_on_page": "calibration"} for r in aud}
    key |= {r: {"task": "audit", "why_on_page": "routed"} for r in rout}
    choices = dict(zip(dis, disagree_marks)) | dict(zip(aud, audit_marks)) | dict(zip(rout, routed_marks))
    marks = [{"row_id": r, "choice": c, "entered_before_aids": r == "d00", "before_aids": None}
             for r, c in choices.items()]
    routing = {"tasks": {
        "disagreement": {"seed": 20261018, "lone": 33, "routed": 129, "rows": 162,
                         "calibration_first": dis, "calibration_order": dis + ["x"] * 13,
                         "routed_row_ids": []},
        "audit": {"seed": 20261019, "lone": 48, "routed": 2, "rows": 50, "calibration_first": aud,
                  "calibration_order": aud + ["y"] * 28, "routed_row_ids": rout}}}
    joint = dict(zip(dis, joint_d)) | dict(zip(aud, joint_a))
    return marks, key, routing, joint


def test_labels_are_compared_as_they_stand_and_a_failure_has_its_consequence():
    marks, key, routing, joint = setup(["answer_1"] * 17 + ["answer_2", "neither", "answer_1"],
                                       ["correct"] * 20, ["correct", "substantive_error"],
                                       ["answer_1"] * 20, ["correct"] * 20)
    out = cal.score(marks, key, routing, joint)
    d = out["tasks"]["disagreement"]
    assert (d["differences"], d["verdict"]) == (2, "needs_next_20") and out["stop_for_next_20"]
    marks[0]["choice"] = "answer_2"
    out = cal.score(marks, key, routing, joint)
    assert out["tasks"]["disagreement"]["verdict"] == "fail"
    assert out["consequences"]["disagreement_lone_decisions"].startswith("not accepted")
    assert out["tasks"]["audit"]["verdict"] == "pass" and out["marks"]["entered_before_aids"] == 1


def test_only_the_authors_substantive_errors_count_toward_escalation():
    marks, key, routing, joint = setup(["answer_1"] * 20, ["correct"] * 19 + ["substantive_error"],
                                       ["correct", "substantive_error"], ["answer_1"] * 20,
                                       ["correct"] * 20)
    out = cal.score(marks, key, routing, joint)
    assert out["escalation"]["author_substantive_errors"] == 2 and out["escalation"]["triggered"]
    assert out["tasks"]["audit"]["differences"] == 1
    marks, key, routing, joint = setup(["answer_1"] * 20, ["correct"] * 20, ["other_issue", "correct"],
                                       ["answer_1"] * 20, ["correct"] * 20)
    assert not cal.score(marks, key, routing, joint)["escalation"]["triggered"]


def test_a_page_whose_calibration_rows_are_not_the_registered_first_20_is_refused():
    marks, key, routing, joint = setup(["answer_1"] * 20, ["correct"] * 20, ["correct"] * 2,
                                       ["answer_1"] * 20, ["correct"] * 20)
    routing["tasks"]["audit"]["calibration_first"] = routing["tasks"]["audit"]["calibration_first"][1:] + ["zz"]
    with pytest.raises(cal.CalibrationError):
        cal.score(marks, key, routing, joint)
