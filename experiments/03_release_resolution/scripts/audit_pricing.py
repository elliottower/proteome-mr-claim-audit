# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Pricing of the resolved-record audit and of the escalation of a draft second amendment
(post-results planning; nothing here is registered). Counts only; no model is called.

Input: the per-record stage B packets of outputs/staged_design_pricing_2026-10-13.json (every
record with a readable supplement, every request carrying the abstract and full texts). Each
record is priced alone by coding_packets_v2.layout_cost (its first request writes the carried
prefix to the cache and later requests read it; the fixed prompt is read from the cache), at the
preflight's characters per token, for both models, at 1,500, 3,000 and 6,000 output tokens a
request.

- Audit, upper bound: the AUDIT records that cost most.
- Audit, expected: the mean cost per record times AUDIT (a seeded sample of AUDIT records drawn
  from the records with a readable supplement).
- Escalation: every record with a readable supplement.

The removed-chunk diagnostic (400 chunks) is priced apart from the cut output.

Usage: uv run scripts/audit_pricing.py --staged <json> --cut <json> --out <json>
"""

import argparse
import json
import pathlib

import coding_packets_v2 as cp2
import stage_pricing as sp

AUDIT = 30
PREFLIGHT = {"claude-sonnet-5-5": 1.98, "gpt-6.1-sol": 3.11}


class AuditPricingError(Exception):
    """The output exists already."""


def record_cost(rec: dict, prompt: int) -> dict:
    """US dollars for both models at each output length, the fixed prompt read from the cache."""
    cost = cp2.layout_cost([rec], prompt, PREFLIGHT, True)
    # layout_cost writes the prompt in the first request of its run; within a stage the prompt is
    # already cached, so the write is priced as a cache read.
    for model, p in cp2.PRICE.items():
        tokens = prompt / PREFLIGHT[model]
        cost[model]["usd"] = round(cost[model]["usd"] - tokens * (p["write"] - p["cached"]) / 1e6,
                                   6)
    return {o: v["total_usd"] for o, v in sp.with_outputs(cost).items()}


def price(records: list[dict], prompt: int, audit: int = AUDIT) -> dict:
    costs = sorted((record_cost(r, prompt) for r in records),
                   key=lambda c: c["6000"], reverse=True)
    out = {"records_with_a_readable_supplement": len(records), "audit_size": audit}
    for o in ("1500", "3000", "6000"):
        values = sorted((c[o] for c in costs), reverse=True)
        mean = sum(values) / len(values)
        out[o] = {"audit_upper_bound_usd": round(sum(values[:audit]), 2),
                  "audit_expected_usd": round(mean * min(audit, len(values)), 2),
                  "escalation_all_records_usd": round(sum(values), 2),
                  "mean_per_record_usd": round(mean, 4),
                  "most_expensive_record_usd": round(values[0], 2)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--staged", type=pathlib.Path, required=True)
    ap.add_argument("--cut", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise AuditPricingError(f"{a.out} exists; it is written once")
    staged = json.loads(a.staged.read_text())
    cut = json.loads(a.cut.read_text())
    result = price(staged["per_record"]["stage_b_upper_bound"], staged["fixed_prompt_characters"])
    result["diagnostic_400_chunks_usd"] = cut["cost_estimate"]["diagnostic_400_chunks"]["usd"]
    result["preflight_ratios"] = PREFLIGHT
    result["inputs"] = {"staged": str(a.staged), "cut": str(a.cut)}
    a.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
