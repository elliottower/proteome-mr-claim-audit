# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Audit of the keyword gate on a citation-chasing round (prefiltered citation chasing). No
model is called here; this script draws the sample batches and reads the eligibility decisions
made on them.

The records the gate marks are not screened. A sample of them is judged by the eligibility
prompt, in batches, to bound how many eligible papers the gate leaves out:

    order      the marked record ids, sorted, shuffled once with `random.Random(20261001)`
    batch j    the next 600 ids of that order (fewer when fewer remain); batch 1 is written by
               keyword_prefilter.py --gate, a later batch by this script
    positive   a sampled record judged `eligible`, `eligible_count_not_stated` or `uncertain`.
               It enters the ordinary workflow like any screened record: extraction, family
               linking, the registry, and the seeds of the next round (select_eligible.py
               takes the gate decisions with the round's other decisions)
    bound      after each batch, the exact (Clopper–Pearson) one-sided 95% upper bound of the
               share of positives among the sampled records that were judged (a record whose
               eligibility call failed is sampled and not judged)
    stop       when every marked record has been sampled; else when the bound is below 0.005;
               else when 3,000 records have been sampled. Otherwise the next batch is drawn. A
               first batch of 600 holding one positive has a bound of 0.0079, so any positive
               in it draws a second batch

A record classed `no_abstract` (scripts/abstract_floor.py) is not among the marked records: it
leaves the round before the gate, so it is never sampled, never a positive and never in the
audit's denominator. The number of such records in the round is written beside the audit
(`no_abstract_records_of_the_round`), and a marked record below the floor raises.

Reported per round: records marked, sampled, judged, positives, the share and its bound, the
two-sided 95% Clopper–Pearson interval, and the estimated number of eligible records among the
marked records that were not judged (the share and its interval ends times their number), with
the stopping reason, the seed and the positives' ids. A round that stops at 3,000 sampled
records with the bound still at or above 0.005 is reported as "cap reached without satisfying
tolerance" (`cap_reached_without_satisfying_tolerance`).

Usage:
    uv run scripts/gate_audit.py --round-dir outputs/screening/chase_round_<k> \\
        --decisions <gate batch decisions.jsonl> [<...> ...]
"""

import argparse
import json
import math
import pathlib
import random

from abstract_floor import refuse_no_abstract

SEED = 20261001
BATCH = 600
MAX_SAMPLED = 3000
TOLERANCE = 0.005
ALPHA = 0.05
ELIGIBLE = ("eligible", "eligible_count_not_stated", "uncertain")
FAILED = "extraction_failed"


class GateAuditError(Exception):
    """The decisions do not cover whole batches of the registered order, or an output exists."""


def draw_order(ids: list[str], seed: int = SEED) -> list[str]:
    """The marked record ids in the order they are sampled."""
    if len(set(ids)) != len(ids):
        raise GateAuditError("a marked record id occurs twice")
    order = sorted(ids)
    random.Random(seed).shuffle(order)
    return order


def batch_ids(order: list[str], j: int) -> list[str]:
    """The ids of batch j (from 1): the next 600 of the order, up to 3,000 sampled in all."""
    return order[(j - 1) * BATCH:min(j * BATCH, MAX_SAMPLED)]


def binomial_cdf(x: int, n: int, p: float) -> float:
    """P(X <= x) for X binomial(n, p)."""
    if x >= n:
        return 1.0
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 0.0
    log_p, log_q = math.log(p), math.log1p(-p)
    return min(1.0, sum(math.exp(math.lgamma(n + 1) - math.lgamma(k + 1)
                                 - math.lgamma(n - k + 1) + k * log_p + (n - k) * log_q)
                        for k in range(x + 1)))


def solve(f, target: float) -> float:
    """p in [0, 1] with f(p) = target, for f decreasing in p."""
    low, high = 0.0, 1.0
    for _ in range(100):
        mid = (low + high) / 2
        if f(mid) > target:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def upper_bound(x: int, n: int, alpha: float = ALPHA) -> float | None:
    """Clopper–Pearson one-sided upper bound of a share x / n at confidence 1 - alpha."""
    if n == 0:
        return None
    if x >= n:
        return 1.0
    return solve(lambda p: binomial_cdf(x, n, p), alpha)


def lower_bound(x: int, n: int, alpha: float = ALPHA) -> float | None:
    """Clopper–Pearson one-sided lower bound of a share x / n at confidence 1 - alpha."""
    if n == 0:
        return None
    if x <= 0:
        return 0.0
    return solve(lambda p: binomial_cdf(x - 1, n, p), 1 - alpha)


def audit(marked_ids: list[str], decisions: dict[str, str], seed: int = SEED) -> dict:
    """The state of the audit after the batches judged so far. `decisions` maps a sampled
    record id to its eligibility decision; it must hold exactly the first batches of the
    order."""
    order = draw_order(marked_ids, seed)
    sampled: list[str] = []
    j = 0
    while len(sampled) < len(decisions):
        j += 1
        ids = batch_ids(order, j)
        if not ids:
            break
        sampled += ids
    if set(sampled) != set(decisions):
        raise GateAuditError(
            f"the decisions do not hold exactly the first {j} batches of the order: missing "
            f"{sorted(set(sampled) - set(decisions))[:5]}, outside "
            f"{sorted(set(decisions) - set(sampled))[:5]}")
    failed = sum(decisions[i] == FAILED for i in sampled)
    judged = len(sampled) - failed
    positives = sorted(i for i in sampled if decisions[i] in ELIGIBLE)
    bound = upper_bound(len(positives), judged)
    if len(sampled) == len(order):
        stop = "every_marked_record_sampled"
    elif not sampled:
        stop = None
    elif bound is not None and bound < TOLERANCE:
        stop = "upper_bound_below_tolerance"
    elif len(sampled) >= MAX_SAMPLED:
        stop = "maximum_sample_reached"
    else:
        stop = None
    not_judged = len(order) - judged
    share = len(positives) / judged if judged else None
    two_sided = (lower_bound(len(positives), judged, ALPHA / 2),
                 upper_bound(len(positives), judged, ALPHA / 2))

    def times(value: float | None) -> float | None:
        return None if value is None else value * not_judged

    return {
        "seed": seed, "batch_size": BATCH, "maximum_sampled": MAX_SAMPLED,
        "tolerance": TOLERANCE, "marked_records": len(order), "batches_judged": j if sampled
        else 0, "sampled": len(sampled), "eligibility_call_failed": failed, "judged": judged,
        "judged_eligible_or_uncertain": len(positives), "positive_record_ids": positives,
        "share": share, "upper_bound_one_sided_95": bound,
        "interval_two_sided_95_clopper_pearson": list(two_sided),
        "marked_records_not_judged": not_judged,
        "estimated_eligible_records_not_judged": times(share),
        "estimated_eligible_records_not_judged_upper_one_sided_95": times(bound),
        "estimated_eligible_records_not_judged_interval_two_sided_95": [
            times(two_sided[0]), times(two_sided[1])],
        "finished": stop is not None, "stopping_reason": stop,
        "cap_reached_without_satisfying_tolerance": stop == "maximum_sample_reached",
        "next_batch": None if stop is not None else (j if sampled else 0) + 1,
    }


def read_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def write_batch(folder: pathlib.Path, j: int, records: list[dict]) -> pathlib.Path:
    path = folder / f"gate_sample_batch_{j:02d}.jsonl"
    if path.exists():
        raise GateAuditError(f"{path} exists; a batch is drawn once")
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round-dir", type=pathlib.Path, required=True,
                    help="outputs/screening/chase_round_<k>, after keyword_prefilter.py --gate")
    ap.add_argument("--decisions", type=pathlib.Path, nargs="+", required=True,
                    help="the decisions files of the gate batches judged so far")
    a = ap.parse_args()
    gated = read_jsonl(a.round_dir / "gated_out.jsonl")
    refuse_no_abstract(gated, f"gate audit of {a.round_dir}")
    decided: dict[str, str] = {}
    for path in a.decisions:
        for d in read_jsonl(path):
            if d["pmid"] in decided:
                raise GateAuditError(f"record {d['pmid']} has two gate decisions")
            decided[d["pmid"]] = d["decision"]
    state = audit([r["pmid"] for r in gated], decided)
    target = a.round_dir / f"gate_audit_after_batch_{state['batches_judged']:02d}.json"
    if target.exists():
        raise GateAuditError(f"{target} exists; archive it before rerunning")
    without = a.round_dir / "no_abstract.jsonl"
    target.write_text(json.dumps(
        {"decisions": [str(p) for p in a.decisions], **state,
         "no_abstract_records_of_the_round": len(read_jsonl(without)) if without.exists()
         else 0}, indent=1))
    if not state["finished"]:
        ids = set(batch_ids(draw_order([r["pmid"] for r in gated]), state["next_batch"]))
        path = write_batch(a.round_dir, state["next_batch"],
                           [r for r in gated if r["pmid"] in ids])
        print(f"next batch: {path}")
    print(json.dumps({k: v for k, v in state.items() if k != "positive_record_ids"}, indent=1))


if __name__ == "__main__":
    main()
