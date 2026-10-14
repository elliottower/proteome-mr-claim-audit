# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Calibration of the two judges' joint lone decisions on SA1 against the author's marks
(Amendment 3, items 3 and 4; Amendment 4, item 3; Deviation 1, item 2; Amendment 5, item 4).

Per task (disagreement adjudication, seed 20261018; agreement audit, seed 20261019), the rows on
the author's page whose key says `why_on_page: calibration` must be the first 20 of the routing
output's calibration order for that task. On each, the author's choice is compared with the
judges' joint choice (both judges gave it; a lone decision). The page's Answer 1 and Answer 2 are
the judges' Answer 1 and Answer 2: both the page and the judges' requests order the two coders'
answers by judge.blinded (adjudication_pages.first_is_a, seed 20261017), so the labels are
compared as they stand.

Verdict (item 3): 0 or 1 differences among the first 20, the task passes; 3 or more, it fails;
exactly 2, the author marks the next 20 of the same order and the task passes only with at most 3
differences among the 40 (`needs_next_20` until those marks exist). Agreement is reported with its
exact (Clopper-Pearson) binomial 95% interval.

Consequences (item 4; Deviation 1): a failed disagreement task leaves none of its lone decisions
standing (they are not accepted and count as unresolved unless the author adjudicates them); a
failed audit task returns the whole registered audit sample to the author, blind. The routed audit
rows take the author's marks as final. Escalation counts only the author's own substantive-error
marks: two or more, among every audit row he marked, trigger the registered review of every agreed
row.

Marks flagged `entered_before_aids` (Amendment 5, item 4) are counted, never dropped.
"""

import math

CALIBRATION = 20
ESCALATION = 2
DISAGREE = ("answer_1", "answer_2", "neither")
AUDIT = ("correct", "substantive_error", "other_issue")


class CalibrationError(Exception):
    """The inputs do not describe the registered calibration samples."""


def verdict(first: int, second: int | None = None) -> str:
    """`first`: differences among the first 20; `second`: among the next 20, when marked."""
    if first <= 1:
        return "pass"
    if first >= 3:
        return "fail"
    if second is None:
        return "needs_next_20"
    return "pass" if first + second <= 3 else "fail"


def _upper_tail(k: int, n: int, p: float) -> float:
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def _bisect(f, lo: float = 0.0, hi: float = 1.0) -> float:
    """The root of an increasing function on [lo, hi]."""
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(mid) < 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    lower = 0.0 if k == 0 else _bisect(lambda p: _upper_tail(k, n, p) - alpha / 2)
    upper = 1.0 if k == n else _bisect(lambda p: alpha / 2 - (1 - _upper_tail(k + 1, n, p)))
    return lower, upper


def task_score(task: str, rows: list[str], marks: dict[str, dict], joint: dict[str, str]) -> dict:
    allowed = DISAGREE if task == "disagreement" else AUDIT
    for rid in rows:
        if marks.get(rid, {}).get("choice") not in allowed:
            raise CalibrationError(f"a {task} calibration row has no valid mark")
        if joint.get(rid) not in allowed:
            raise CalibrationError(f"a {task} calibration row has no joint judge choice")
    differ = sorted(rid for rid in rows if marks[rid]["choice"] != joint[rid])
    n, agree = len(rows), len(rows) - len(differ)
    lo, hi = clopper_pearson(agree, n)
    return {"rows": n, "differences": len(differ), "agreements": agree,
            "agreement": agree / n, "agreement_ci95_exact": [round(lo, 4), round(hi, 4)],
            "verdict": verdict(len(differ)), "differing_row_ids": differ}


def score(marks: list[dict], key: dict[str, dict], routing: dict, joint: dict[str, str]) -> dict:
    """`marks`: the saved marks; `key`: the page key (row id -> task, why_on_page); `routing`:
    the routing output; `joint`: row id -> the judges' joint choice on each calibration row."""
    by_row = {m["row_id"]: m for m in marks}
    out = {"tasks": {}}
    for task in ("disagreement", "audit"):
        t = routing["tasks"][task]
        rows = [rid for rid in by_row if key[rid] == {"task": task, "why_on_page": "calibration"}]
        if sorted(rows) != sorted(t["calibration_first"]) or len(rows) != min(CALIBRATION, t["lone"]):
            raise CalibrationError(f"the page's {task} calibration rows are not the registered first 20")
        if t["calibration_order"][:CALIBRATION] != t["calibration_first"]:
            raise CalibrationError("the routing output's calibration order is inconsistent")
        out["tasks"][task] = {"seed": t["seed"], "lone": t["lone"], "routed": t["routed"],
                              **task_score(task, rows, by_row, joint)}
    routed_audit = sorted(rid for rid in by_row if key[rid] == {"task": "audit", "why_on_page": "routed"})
    if routed_audit != sorted(routing["tasks"]["audit"]["routed_row_ids"]):
        raise CalibrationError("the page's routed audit rows are not the routing output's")
    audit_marked = [rid for rid in by_row if key[rid]["task"] == "audit"]
    if any(by_row[rid]["choice"] not in AUDIT for rid in audit_marked):
        raise CalibrationError("an audit row has no valid mark")
    errors = sum(1 for rid in audit_marked if by_row[rid]["choice"] == "substantive_error")
    d, a = out["tasks"]["disagreement"]["verdict"], out["tasks"]["audit"]["verdict"]
    out["stop_for_next_20"] = "needs_next_20" in (d, a)
    out["consequences"] = {
        "disagreement_lone_decisions": (
            "pending the next 20" if d == "needs_next_20" else
            "stand" if d == "pass" else "not accepted, unresolved unless the author adjudicates them"),
        "disagreement_lone_count": routing["tasks"]["disagreement"]["lone"],
        "audit_judge_decisions": (
            "pending the next 20" if a == "needs_next_20" else
            "stand" if a == "pass" else "do not stand; the whole audit sample goes to the author, blind"),
        "audit_sample": routing["tasks"]["audit"]["rows"],
        "routed_audit_rows_final_by_author": len(routed_audit),
        "routed_audit_marks": {c: sum(1 for r in routed_audit if by_row[r]["choice"] == c) for c in AUDIT}}
    out["escalation"] = {"audit_rows_marked_by_author": len(audit_marked),
                         "author_substantive_errors": errors, "threshold": ESCALATION,
                         "triggered": errors >= ESCALATION,
                         "complete": a != "fail",
                         "note": ("the author has reviewed only the rows above; a failed audit task "
                                  "sends the whole sample to him and the rule is applied to that review")
                         if a == "fail" else "the rule is applied to the author's marks above"}
    out["marks"] = {"rows": len(marks),
                    "entered_before_aids": sum(1 for m in marks if m.get("entered_before_aids")),
                    "changed_after_aids_from_a_pre_aid_mark": sum(
                        1 for m in marks if m.get("entered_before_aids") and m.get("before_aids")
                        and m["before_aids"].get("choice") != m.get("choice")),
                    "by_choice": {c: sum(1 for m in marks if m["choice"] == c) for c in DISAGREE + AUDIT}}
    return out
