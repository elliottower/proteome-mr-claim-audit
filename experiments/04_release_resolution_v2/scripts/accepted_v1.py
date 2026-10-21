# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Accepted codes of the second registration's stage A, and the registered C1 on them (first
registration PREREG.md, §Study design, Checks: "A row is accepted only when the two models agree,
or the adjudication settles it, and the gate passes"; Amendments 3, 4 and 7; second registration
PREREG.md items 1, 4 and 5). No model is called.

Per row (`assemble`), in this order:
- `settled`: a release-concordant row settled by rule (Amendment 7); accepted, both answers having
  passed the gate;
- `agreed`: the two answers agree (pass_summary.differs); accepted with the answer of the first
  coder whose gate passes (the two agree on releases, roles, attribution and reasons); not
  accepted when neither answer passes the gate. The audit sample's marks change no agreed code
  here: every audit mark, the author's and the judges' lone decisions, is `correct`;
- `judges`: a disagreement decided by both judges alone (Amendment 4 item 2, the task's
  calibration passed): the chosen answer, accepted when its gate passes;
- `author`: a routed disagreement: the author's choice; Answer 1 or 2 maps to the coder by
  judges_stage_a_v1.blinded; accepted when the chosen answer's gate passes; `neither` is not
  accepted.
A row not accepted is unresolved, never dropped. An inferred release never enters a code.

C1 (`c1`): each drawn control against its expected row, on the accepted code: `recovered` (the
code identifies exactly the expected row), `contradicted` (it holds another row), `empty` (no
release), `not_accepted`. Recovery and contradiction are shares of every drawn control; the
thresholds are recovery at least 0.90 and contradiction at most 0.02 on at least 50 controls,
overall; reported overall and by identifier type, with the controls recovered through the inline
D2 rule.
"""

import pass_summary as ps
import judges_stage_a_v1 as js

RECOVERY_MIN, CONTRADICTION_MAX, MINIMUM = 0.90, 0.02, 50
KINDS = ("release", "accession", "source_identifier")


def assemble(order: list[str], answers: dict, gates: dict, settled: dict,
             judge_choice: dict[str, str], author_choice: dict[str, str]) -> dict[str, dict]:
    a, b = js.MODELS
    out = {}
    for rid in order:
        x, y = answers[a].get(rid), answers[b].get(rid)
        if rid in settled:
            out[rid] = {"source": "settled", "accepted": True, "code": settled[rid], "coder": None}
        elif x is not None and y is not None and not ps.differs(x, y):
            passing = [m for m in js.MODELS if gates[m].get(rid)]
            out[rid] = {"source": "agreed", "accepted": bool(passing),
                        "code": answers[passing[0]][rid] if passing else None,
                        "coder": passing[0] if passing else None}
        else:
            choice = judge_choice.get(rid) or author_choice.get(rid)
            src = "judges" if rid in judge_choice else "author" if rid in author_choice else None
            if src is None:
                raise ValueError(f"{rid}: a disagreement with no decision")
            if choice in ("answer_1", "answer_2"):
                m = js.blinded(rid)[0 if choice == "answer_1" else 1]
                ok = bool(gates[m].get(rid)) and answers[m].get(rid) is not None
                out[rid] = {"source": src, "accepted": ok, "choice": choice, "coder": m,
                            "code": answers[m][rid] if ok else None}
            else:
                out[rid] = {"source": src, "accepted": False, "choice": choice, "coder": None,
                            "code": None}
    return out


def outcome(expected: str, row: dict) -> str:
    if not row["accepted"]:
        return "not_accepted"
    found = set(row["code"]["identified_releases"])
    if found - {expected}:
        return "contradicted"
    return "recovered" if found else "empty"


def tally(outcomes: list[str], minimum: int) -> dict:
    n = len(outcomes)
    counts = {k: outcomes.count(k) for k in sorted(set(outcomes))}
    rec = counts.get("recovered", 0)
    con = counts.get("contradicted", 0)
    recovery = rec / n if n else None
    contradiction = con / n if n else None
    return {"controls": n, "counts": counts, "recovered": rec, "contradicted": con,
            "recovery": recovery, "contradiction": contradiction, "minimum_controls": minimum,
            "meets_thresholds": bool(n >= minimum and recovery is not None
                                     and recovery >= RECOVERY_MIN
                                     and contradiction <= CONTRADICTION_MAX)}


def c1(accepted: dict, expected: dict[str, str], kinds: dict[str, str],
       bases: dict[str, dict]) -> dict:
    per = {rid: outcome(e, accepted[rid]) for rid, e in expected.items()}
    out = {"overall": tally(list(per.values()), MINIMUM),
           "by_identifier_type": {k: tally([per[r] for r in expected if kinds[r] == k], 0)
                                  for k in KINDS},
           "thresholds": {"recovery_at_least": RECOVERY_MIN,
                          "contradiction_at_most": CONTRADICTION_MAX,
                          "minimum_controls": MINIMUM}}
    out["verdict"] = "pass" if out["overall"]["meets_thresholds"] else "fail"
    out["recovered_through_the_inline_d2_rule"] = sum(
        1 for rid, e in expected.items() if per[rid] == "recovered"
        and str(bases.get(accepted[rid]["coder"], {}).get(rid, {}).get(e, "")).startswith(
            "D2:inline"))
    out["per_control"] = per
    return out
