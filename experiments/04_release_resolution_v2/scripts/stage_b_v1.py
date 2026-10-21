# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""The stage B decision of the second registration (the first registration's Amendment 2,
item 1, carried over by PREREG.md item 4, where "the spend of stage A and SA1" reads as the new
spend of this registration). No model is called.

Records (`records`): among the records of the scope, every record that holds an unresolved row
(a row whose accepted code carries an unresolved reason, or that is not accepted) and a readable
supplement; and the resolved-record audit, a sample of 30 records whose rows are all resolved and
that hold a readable supplement, drawn by `random.Random(AUDIT_SEED).sample` over those records in
sorted order of record identifier (all of them if fewer than 30).

Bound (`bound`): every stage B packet of those records (every row of the record coded again from
the abstract, the full texts and the supplements under the cut of Amendment 1, every request
carrying the abstract and full texts; coding_packets_v2.fulltext_packets_carrying) priced for
both coders as the first registration priced stage B (audit_pricing.record_cost: preflight
characters per token, the fixed prompt read from the cache), with output per request the larger
of 6,000 tokens and each coder's mean output per request billed in stage A; plus the removed-chunk
diagnostic of Amendment 1 at its 400-chunk price.

Rule (`decide`): stage B runs if the bound is at most 470 US dollars and this registration's new
spend plus the bound is at most 560; otherwise it does not run, and stage A is the primary
analysis.
"""

import random

import audit_pricing as apr
import coding_packets_v2 as cp2

AUDIT_SEED = 20261042
AUDIT = 30
BOUND_MAX, TOTAL_MAX = 470.0, 560.0
OUTPUT_FLOOR = 6_000


def unresolved(accepted_row: dict) -> bool:
    if not accepted_row["accepted"]:
        return True
    return bool(accepted_row["unresolved_reasons"])


def records(rows_by_record: dict[str, list[str]], accepted: dict[str, dict],
            with_supplement: set[str]) -> dict:
    unres = sorted(r for r, rows in rows_by_record.items()
                   if r in with_supplement and any(unresolved(accepted[x]) for x in rows))
    resolved = sorted(r for r, rows in rows_by_record.items()
                      if r in with_supplement and not any(unresolved(accepted[x]) for x in rows))
    audit = sorted(random.Random(AUDIT_SEED).sample(resolved, min(AUDIT, len(resolved))))
    return {"unresolved_records": unres, "resolved_records_with_a_supplement": resolved,
            "audit_records": audit}


def record_cost(rec: dict, prompt: int, output: dict[str, int]) -> float:
    cost = cp2.layout_cost([rec], prompt, apr.PREFLIGHT, True)
    total = 0.0
    for model, p in cp2.PRICE.items():
        tokens = prompt / apr.PREFLIGHT[model]
        usd = cost[model]["usd"] - tokens * (p["write"] - p["cached"]) / 1e6
        usd += cost[model]["requests"] * (output[model] - cp2.OUTPUT_TOKENS) * p["output"] / 1e6
        total += usd
    return total


def bound(packets: dict[str, dict], chosen: list[str], prompt: int, output: dict[str, int],
          diagnostic: float) -> dict:
    per = {r: round(record_cost(packets[r], prompt, output), 4) for r in chosen}
    coding = sum(per.values())
    return {"records": len(chosen),
            "requests_per_model": sum(len(packets[r]["packets"]) for r in chosen),
            "coding_usd": round(coding, 2), "diagnostic_usd": diagnostic,
            "bound_usd": round(coding + diagnostic, 2), "per_record_usd": per}


def output_tokens(stage_a_means: dict[str, float]) -> dict[str, int]:
    return {m: max(OUTPUT_FLOOR, round(v)) for m, v in stage_a_means.items()}


def decide(bound_usd: float, new_spend: float) -> dict:
    runs = bound_usd <= BOUND_MAX and new_spend + bound_usd <= TOTAL_MAX
    return {"bound_usd": bound_usd, "bound_at_most": BOUND_MAX,
            "new_spend_usd": round(new_spend, 4), "total_at_most": TOTAL_MAX,
            "new_spend_plus_bound_usd": round(new_spend + bound_usd, 2),
            "stage_b_runs": runs,
            "primary_analysis": "staged estimate after stage B" if runs else "stage A"}
