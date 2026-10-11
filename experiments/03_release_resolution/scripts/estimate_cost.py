# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""The cost estimate the release-resolution plan requires after retrieval and before any model
request (PREREG.md, Data collection procedures, Cost approval). It reads the retrieval results
and counts characters only; no model is called and no text is read for content.

Per record: the characters of every readable full text and supplement. The estimate takes
every supplement whole (an upper bound: the mechanical cut of large supplements is applied
later and only shortens the input) and splits a record's source text into requests of at most
400,000 characters (the plan's input limit). Every request carries the fixed prompt (cached
after the first request) and returns OUTPUT_TOKENS. Characters become tokens by the pooled
ratios measured before the freeze (outputs/token_ratio_2026-10-10.json). Added: the
abstract-only requests of SA1 (one per record, the abstract's characters), the C2 pass (the
supplements of the 30 records with the most supplement characters, again, by the checker), and
the control-only papers of C1 (CONTROL_ONLY_PAPERS requests at the mean size of a record's
request; their number is fixed only when the control set is drawn).

Prices (USD per million tokens, from the plan's cost table): new input 2.00, cached input 0.10,
output 10.00, for both Claude Sonnet 5.5 and GPT-6.1 Sol. The plan's approval rule: 30 to 100
USD is accepted; above 100 needs the author's explicit approval.
"""

import argparse
import json
import math
import pathlib

LIMIT = 400_000
OUTPUT_TOKENS = 1_500
RATIO = {"claude-sonnet-5-5": 2.62, "gpt-6.1-sol": 4.28}
PRICE = {"new": 2.00, "cached": 0.10, "output": 10.00}
C2_PAPERS = 30
CONTROL_ONLY_PAPERS = 16
ACCEPTED_UP_TO = 100.0


class EstimateError(Exception):
    """An output exists already, or a result lacks a field."""


def record_characters(result: dict) -> dict:
    full = sum(s["characters"] for s in result["sources"]
               if s.get("text") is not None and s["route"] in ("R1", "R3"))
    supp = sum(s["characters"] for s in result["sources"]
               if s.get("text") is not None and s["route"] == "R2")
    return {"record_id": result["record_id"], "status": result["status"],
            "full_text_characters": full, "supplement_characters": supp,
            "requests": max(1, math.ceil((full + supp) / LIMIT))}


def model_cost(model: str, source_chars: int, requests: int, prompt_chars: int,
               prompt_new: bool = False) -> dict:
    """Tokens and USD of `requests` requests carrying `source_chars` characters of source in
    all; the fixed prompt is new input in the first request of the run (`prompt_new`) and cached
    input in every other."""
    ratio = RATIO[model]
    new = source_chars / ratio + (prompt_chars / ratio if prompt_new and requests else 0.0)
    cached = (requests - (1 if prompt_new else 0)) * prompt_chars / ratio if requests else 0.0
    output = requests * OUTPUT_TOKENS
    usd = (new * PRICE["new"] + cached * PRICE["cached"] + output * PRICE["output"]) / 1e6
    return {"requests": requests, "new_input_tokens": round(new), "cached_input_tokens":
            round(cached), "output_tokens": output, "usd": round(usd, 2)}


def estimate(results: list[dict], abstract_chars: dict[str, int], prompt_chars: int) -> dict:
    rows = [record_characters(r) for r in results]
    main_chars = sum(r["full_text_characters"] + r["supplement_characters"] for r in rows)
    main_requests = sum(r["requests"] for r in rows)
    c2 = sorted(rows, key=lambda r: -r["supplement_characters"])[:C2_PAPERS]
    c2_chars = sum(r["supplement_characters"] for r in c2)
    c2_requests = sum(max(1, math.ceil(r["supplement_characters"] / LIMIT)) for r in c2
                      if r["supplement_characters"])
    mean = main_chars / main_requests if main_requests else 0
    sa1_chars = sum(abstract_chars.values())
    parts = {}
    for model in RATIO:
        parts[model] = {
            "coding": model_cost(model, main_chars, main_requests, prompt_chars, True),
            "control_only_papers": model_cost(model, round(mean * CONTROL_ONLY_PAPERS),
                                              CONTROL_ONLY_PAPERS, prompt_chars),
            "sa1_abstract_only": model_cost(model, sa1_chars, len(abstract_chars), prompt_chars),
        }
    parts["gpt-6.1-sol"]["c2_exhaustive_pass"] = model_cost("gpt-6.1-sol", c2_chars,
                                                            c2_requests, prompt_chars)
    total = round(sum(p["usd"] for m in parts.values() for p in m.values()), 2)
    return {"records": len(rows), "by_status": {s: sum(r["status"] == s for r in rows)
                                                for s in sorted({r["status"] for r in rows})},
            "full_text_characters": sum(r["full_text_characters"] for r in rows),
            "supplement_characters": sum(r["supplement_characters"] for r in rows),
            "requests_per_model_for_coding": main_requests,
            "fixed_prompt_characters": prompt_chars,
            "abstract_characters": sa1_chars,
            "c2_papers": len(c2), "c2_supplement_characters": c2_chars,
            "assumptions": {"limit_characters": LIMIT, "output_tokens_per_request": OUTPUT_TOKENS,
                            "characters_per_token": RATIO, "usd_per_million_tokens": PRICE,
                            "supplements": "whole (upper bound; the cut is applied later)",
                            "control_only_papers": CONTROL_ONLY_PAPERS},
            "by_model": parts, "total_usd": total,
            "within_accepted_range": total <= ACCEPTED_UP_TO,
            "per_record": rows}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=pathlib.Path, required=True,
                    help="folder of <record>/result.json")
    ap.add_argument("--abstract-characters", type=pathlib.Path, required=True)
    ap.add_argument("--prompt", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise EstimateError(f"{a.out} exists; it is written once")
    results = [json.loads(p.read_text()) for p in sorted(a.results.glob("*/result.json"))]
    prompt_chars = sum(len(p.read_text()) for p in a.prompt)
    result = estimate(results, json.loads(a.abstract_characters.read_text()), prompt_chars)
    a.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "per_record"}, indent=1))


if __name__ == "__main__":
    main()
