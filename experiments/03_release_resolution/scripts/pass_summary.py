# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Counts of a coding pass of the release-resolution follow-up, for the author's adjudication and
for the cost rule of Amendment 2 (AMENDMENT_02_staged_reading.md). Counts only: no estimand,
no resolution rate and no relation class is computed here.

- `usage_summary`: per model, from the stage's spend ledger, the requests billed, the attempts
  that were re-requests, the input tokens (new, cache written, cache read), the output tokens
  (thinking and reasoning included, as billed) and the reasoning tokens Sol reports apart, the
  mean output per request and the spend.
- `differs`: whether the two models' accepted answers for one row differ in what the author
  adjudicates: the identified releases, the role of each, the attribution state or the set of
  unresolved reasons.
- `adjudication_rows`: the rows to adjudicate, those on which the answers differ or for which
  either model has no accepted answer.
"""

import collections


def usage_summary(entries: list[dict]) -> dict:
    out = {}
    for model in sorted({e["model"] for e in entries}):
        es = [e for e in entries if e["model"] == model]
        c = collections.Counter()
        for e in es:
            u = e["usage"]
            c["output_tokens"] += u.get("output_tokens", 0)
            if model.startswith("claude"):
                c["new_input_tokens"] += u.get("input_tokens", 0)
                c["cache_write_tokens"] += u.get("cache_creation_input_tokens", 0) or 0
                c["cache_read_tokens"] += u.get("cache_read_input_tokens", 0) or 0
            else:
                cached = (u.get("input_tokens_details") or {}).get("cached_tokens", 0)
                c["new_input_tokens"] += u.get("input_tokens", 0) - cached
                c["cache_read_tokens"] += cached
                c["reasoning_tokens"] += (u.get("output_tokens_details") or {}).get(
                    "reasoning_tokens", 0)
        out[model] = {"requests_billed": len(es),
                      "re_requests": sum(e.get("attempt", 1) > 1 for e in es),
                      **dict(c),
                      "mean_output_tokens_per_request": round(c["output_tokens"] / len(es), 1),
                      "usd": round(sum(e["usd"] for e in es), 4)}
    out["total_usd"] = round(sum(v["usd"] for k, v in out.items() if k != "total_usd"), 4)
    return out


def key(row: dict) -> tuple:
    return (frozenset(row["identified_releases"]),
            frozenset((r["release"], r["role"]) for r in row["roles"]),
            row["attribution_state"], frozenset(row["unresolved_reasons"]))


def differs(a: dict, b: dict) -> bool:
    return key(a) != key(b)


def adjudication_rows(row_ids: list[str], first: dict[str, dict],
                      second: dict[str, dict]) -> dict:
    """`first`, `second`: row id -> accepted answer row of each model (missing when none)."""
    disagree, missing = [], []
    for rid in row_ids:
        if rid not in first or rid not in second:
            missing.append(rid)
        elif differs(first[rid], second[rid]):
            disagree.append(rid)
    return {"rows": len(row_ids), "rows_answered_by_both": len(row_ids) - len(missing),
            "rows_where_the_models_differ": len(disagree),
            "rows_without_an_accepted_answer_from_a_model": len(missing),
            "rows_to_adjudicate": len(disagree) + len(missing),
            "row_ids_to_adjudicate": sorted(disagree + missing)}
