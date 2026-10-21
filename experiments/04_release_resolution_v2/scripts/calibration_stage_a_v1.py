# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Calibration of the stage A judges against the author's marks, and the consequences and
escalation of the first registration's Amendment 3 (items 3 and 4), carried over by the second
registration's PREREG.md item 4. The scoring is the first registration's
scripts/sa1_calibration_v1.score (sealed, imported unchanged): verdict per task (0 or 1
differences among the first 20 pass, 3 or more fail, exactly 2 needs the next 20), exact 95%
interval, consequences, and the escalation count of the author's own substantive-error marks
(2 or more trigger the review of every agreed row).

Two adapters only, with no change to the rule (`calibrate`): the page key keeps only `task` and
`why_on_page` per row (this registration's key also records the blinding order), and the routing
output gains `routed_row_ids`, the sorted keys of its `routed_reasons`, under each task. The
page's Answer 1 and Answer 2 and the judges' are both ordered by judges_stage_a_v1.blinded (seed
20261035), so the labels compare as they stand.
"""

import sa1_calibration_v1 as cal


def adapt(key: dict, routing: dict) -> tuple[dict, dict]:
    k = {rid: {"task": v["task"], "why_on_page": v["why_on_page"]} for rid, v in key.items()}
    r = {"tasks": {t: d | {"routed_row_ids": sorted(d["routed_reasons"])}
                   for t, d in routing["tasks"].items()}}
    return k, r


def calibrate(marks: list[dict], key: dict, routing: dict, joint: dict[str, str]) -> dict:
    k, r = adapt(key, routing)
    return cal.score(marks, k, r, joint)
