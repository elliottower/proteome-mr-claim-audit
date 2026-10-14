# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Counts of the stage A coding pass and of the manifest packets that run with it
(AMENDMENT_02_staged_reading.md, items 1 and 3). Counts only: no estimand, no resolution rate of
study rows and no relation class is computed here, and no answer's content is written out.

- `agreement`: for study rows and for control rows apart, the rows both models answered, the
  rows on which their answers agree and differ (pass_summary.differs, sealed, unchanged: the
  identified releases, the role of each, the attribution state, the unresolved reasons), and the
  rows without an accepted answer from a model.
- `c1_scores`: the C1 controls (C1-A, or the manifest packets) against their expected rows, per
  model and for the two models together. Per control:
    recovered     the identified releases are exactly {expected row} and the gate passes;
    contradicted  the identified releases hold a row other than the expected one, gate or not
                  (the plan's "coded to another row");
    empty         no release identified;
    expected_gate_failed  exactly {expected row}, but the gate fails;
    missing       no accepted answer.
  "Both models" counts a control recovered only when both recover it, contradicted when either
  contradicts it. Recovery and contradiction are shares of every control in the set; the
  thresholds are those of PREREG.md, §Inference criteria: recovery at least 0.90 and
  contradiction at most 0.02, on at least 50 controls for the source-scanned set (no minimum
  for the manifest packets). These are the coders' answers before any judge or adjudication; the
  registered C1 is computed on the accepted codes.
"""

import pass_summary as ps

RECOVERY_MIN = 0.90
CONTRADICTION_MAX = 0.02
SOURCE_SCANNED_MINIMUM = 50


def agreement(row_ids: list[str], first: dict[str, dict], second: dict[str, dict]) -> dict:
    both = [r for r in row_ids if r in first and r in second]
    differ = [r for r in both if ps.differs(first[r], second[r])]
    return {"rows": len(row_ids), "answered_by_both": len(both),
            "agree": len(both) - len(differ), "differ": len(differ),
            "without_an_accepted_answer_from_a_model": len(row_ids) - len(both)}


def outcome(expected: str, row: dict | None, gate_passes: bool | None) -> str:
    if row is None:
        return "missing"
    found = set(row["identified_releases"])
    if found - {expected}:
        return "contradicted"
    if not found:
        return "empty"
    return "recovered" if gate_passes else "expected_gate_failed"


def joint(a: str, b: str) -> str:
    if "contradicted" in (a, b):
        return "contradicted"
    if a == b == "recovered":
        return "recovered"
    if "missing" in (a, b):
        return "missing"
    return "not_recovered_by_both"


def tally(outcomes: list[str], minimum: int) -> dict:
    n = len(outcomes)
    counts = {k: outcomes.count(k) for k in sorted(set(outcomes))}
    recovery = counts.get("recovered", 0) / n if n else None
    contradiction = counts.get("contradicted", 0) / n if n else None
    passes = (n >= minimum and recovery is not None and recovery >= RECOVERY_MIN
              and contradiction <= CONTRADICTION_MAX)
    return {"controls": n, "counts": counts, "recovery": recovery,
            "contradiction": contradiction, "minimum_controls": minimum,
            "meets_thresholds": passes}


def c1_scores(expected: dict[str, str], answers: dict[str, dict[str, dict]],
              gate: dict[str, dict[str, bool]], minimum: int) -> dict:
    """`expected`: control row id -> expected dictionary row; `answers`: model -> row id ->
    accepted answer row; `gate`: model -> row id -> whether the row passes the gate."""
    models = sorted(answers)
    per = {m: {rid: outcome(exp, answers[m].get(rid), gate[m].get(rid))
               for rid, exp in expected.items()} for m in models}
    out = {m: tally(list(per[m].values()), minimum) for m in models}
    if len(models) == 2:
        a, b = models
        out["both_models"] = tally([joint(per[a][r], per[b][r]) for r in expected], minimum)
    out["thresholds"] = {"recovery_at_least": RECOVERY_MIN,
                         "contradiction_at_most": CONTRADICTION_MAX}
    return out
