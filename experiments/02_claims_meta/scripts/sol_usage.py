# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Sum the token usage of stored GPT-6.1 Sol exchanges and price it at list prices.

Reads the 200 exchanges (`<record>_attempt<n>.json`) in a raw folder for the records of one or
more input files (`pmid` per line), sums the `usage` block of each response, and writes the
totals with the cost. Failed exchanges (`.http<try>.json`) carry no usage and are counted only.
No model is called; no stored file is changed.

List prices per million tokens (OpenAI pricing table, short-context column, as given by the
author on 2026-10-05): input 2.00, cached input 0.10, cache writes 2.50, output 10.00.
`input_tokens` includes the cached and cache-write tokens, so the plain-input share is the
remainder.

Usage:
    uv run scripts/sol_usage.py --raw-dir outputs/raw/sol_chase_full/eligibility/<rev> \
        --records <abstracts.jsonl> [<...> ...] --out ../../docs/run/usage_<name>.json
"""

import argparse
import json
import pathlib

PRICES = {"input": 2.0, "cached_input": 0.1, "cache_write": 2.5, "output": 10.0}


class UsageError(Exception):
    """The output exists, or a record has no stored exchange."""


def cost(tokens: dict) -> float:
    plain = tokens["input"] - tokens["cached"] - tokens["cache_write"]
    return round((plain * PRICES["input"] + tokens["cached"] * PRICES["cached_input"]
                  + tokens["cache_write"] * PRICES["cache_write"]
                  + tokens["output"] * PRICES["output"]) / 1e6, 4)


def add(tokens: dict, usage: dict) -> None:
    details = usage.get("input_tokens_details") or {}
    tokens["requests"] += 1
    tokens["input"] += usage.get("input_tokens", 0)
    tokens["cached"] += details.get("cached_tokens", 0)
    tokens["cache_write"] += details.get("cache_write_tokens", 0)
    tokens["output"] += usage.get("output_tokens", 0)
    tokens["reasoning"] += (usage.get("output_tokens_details") or {}).get("reasoning_tokens", 0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=pathlib.Path, required=True)
    ap.add_argument("--records", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise UsageError(f"{a.out} exists")
    ids = [json.loads(line)["pmid"] for p in a.records
           for line in p.read_text().splitlines() if line.strip()]
    tokens = dict(requests=0, input=0, cached=0, cache_write=0, output=0, reasoning=0)
    failed_exchanges, without = 0, []
    for pmid in ids:
        answered = sorted(a.raw_dir.glob(f"{pmid}_attempt[0-9].json"))
        failed_exchanges += len(list(a.raw_dir.glob(f"{pmid}_attempt[0-9].http*.json")))
        if not answered:
            without.append(pmid)
        for path in answered:
            add(tokens, json.loads(json.loads(path.read_text())["response_text"]).get("usage") or {})
    result = {"records": len(ids), "records_without_a_200_exchange": len(without), **tokens,
              "failed_exchanges": failed_exchanges, "usd": cost(tokens),
              "prices_usd_per_million": PRICES, "raw_dir": str(a.raw_dir),
              "records_files": [str(p) for p in a.records]}
    a.out.write_text(json.dumps(result, indent=1))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
