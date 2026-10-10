# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1"]
# ///
"""Characters per token of stored full texts under each model's own token counter (release-
resolution plan, before its freeze), to check the frozen input limit against the models'
context windows. Counting only: no text is generated, and no text is written to the result.

A seeded draw of stored rendered full texts of Paper 1 papers outside the plan's scope is sent
to Anthropic's `POST /v1/messages/count_tokens` (model `claude-sonnet-5-5`) and to OpenAI's
`POST /v1/responses/input_tokens` (model `gpt-6.1-sol`), each text alone as one user message.
Keys come from the environment and are never written; no request carries an e-mail address.
The result holds, per text, the record id, its characters and the two token counts, and per
model the pooled ratio (sum of characters over sum of tokens) and the smallest ratio.

Usage: uv run scripts/token_ratio.py --fulltext <dir> --scope <availability json> \\
           --records <screening_records.jsonl> [...] --n 12 --seed 20261010 --out <json>
"""

import argparse
import datetime
import json
import os
import pathlib
import random

import httpx

ANTHROPIC = "https://api.anthropic.com/v1/messages/count_tokens"
OPENAI = "https://api.openai.com/v1/responses/input_tokens"
MODELS = {"anthropic": "claude-sonnet-5-5", "openai": "gpt-6.1-sol"}


def draw(candidates: list[str], n: int, seed: int) -> list[str]:
    order = sorted(candidates)
    random.Random(seed).shuffle(order)
    return sorted(order[:n])


def ratios(rows: list[dict], vendor: str) -> dict:
    chars = sum(r["characters"] for r in rows)
    tokens = sum(r[f"{vendor}_tokens"] for r in rows)
    return {"characters_per_token_pooled": chars / tokens,
            "characters_per_token_smallest": min(r["characters"] / r[f"{vendor}_tokens"]
                                                 for r in rows)}


def count(client: httpx.Client, vendor: str, text: str) -> int:
    if vendor == "anthropic":
        r = client.post(ANTHROPIC, headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                                            "anthropic-version": "2023-06-01"},
                        json={"model": MODELS[vendor],
                              "messages": [{"role": "user", "content": text}]})
        r.raise_for_status()
        return int(r.json()["input_tokens"])
    r = client.post(OPENAI, headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                    json={"model": MODELS[vendor], "input": text})
    r.raise_for_status()
    return int(r.json()["input_tokens"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fulltext", type=pathlib.Path, required=True)
    ap.add_argument("--scope", type=pathlib.Path, required=True)
    ap.add_argument("--records", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise FileExistsError(f"{a.out} exists; it is written once")
    scope = set(json.loads(a.scope.read_text())["records"])
    pmid_of = {}
    for path in a.records:
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("pmid"):
                    pmid_of.setdefault(str(r["pmid"]), r["record_id"])
    files = {pmid_of[p.stem[4:]]: p for p in a.fulltext.glob("pmid*.jsonl")
             if p.stem[4:] in pmid_of and pmid_of[p.stem[4:]] not in scope}
    rows = []
    with httpx.Client(timeout=120) as client:
        for rid in draw(list(files), a.n, a.seed):
            body = json.loads(files[rid].read_text().splitlines()[0])["body"]
            rows.append({"record_id": rid, "characters": len(body),
                         **{f"{v}_tokens": count(client, v, body) for v in MODELS}})
    result = {"written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
              "models": MODELS, "seed": a.seed, "candidates": len(files), "texts": rows,
              **{v: ratios(rows, v) for v in MODELS}}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "texts"}, indent=1))


if __name__ == "__main__":
    main()
