# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""The cost estimate of the release-resolution follow-up after the registered cut of
supplements (PREREG.md, Data collection procedures, Cost approval). Second version: it reads the
cut (scripts/cut_supplements.py) and separates the lines below. Counts characters only; no model
is called. Prices, characters per token, the input limit, the output per request and the fixed
prompt are those of scripts/estimate_cost.py (sealed, imported unchanged).

Lines.
- coding: both models, every record, its readable full texts (R1, R3) and its supplements as the
  models read them (whole under the cut rule, else cut), in requests of at most 400,000
  characters.
- sa1_abstract_only: both models, one request per record with its stored abstract.
- control_only_papers: both models, CONTROL_ONLY_PAPERS requests at the mean coding request size
  (their number is fixed only when the control set is drawn).
- c2_sampled_pass: the checker (GPT-6.1 Sol), for a seeded sample of 30 papers with a cut
  supplement (all if fewer), every cut supplement of the paper again whole, in chunks of at most
  400,000 characters. The plan names no seed for this draw, so the line gives the expected cost
  over draws (the sample mean, exact by linearity), the cheapest and the dearest possible
  samples, and the 5th and 95th percentiles over DRAWS draws with seed DRAW_SEED.
- c2_failure_path (contingent; only if C2 fails): both models, every cut supplement of every
  paper again whole, in chunks.

A record whose only full text is a page under SHORT_PAGE characters (an OpenAlex landing page
taken by route R3) is counted as the plan counts it, a retrieved source of an accepted type,
and is listed apart.
"""

import argparse
import json
import math
import pathlib
import random

import estimate_cost as base

C2_PAPERS = 30
DRAWS = 10_000
DRAW_SEED = 20261011
SHORT_PAGE = 1_000
SOL = "gpt-6.1-sol"


class EstimateError(Exception):
    """An output exists already, or a cut is missing for a record."""


def chunks(characters: int) -> int:
    return math.ceil(characters / base.LIMIT) if characters else 0


def usd(model: str, characters: int, requests: int, prompt: int, prompt_new: bool = False) -> dict:
    return base.model_cost(model, characters, requests, prompt, prompt_new)


def per_record(result: dict, cut: dict) -> dict:
    full = sum(s["characters"] for s in result["sources"]
               if s.get("text") is not None and s["route"] in ("R1", "R3"))
    short = bool(full) and all(s["characters"] < SHORT_PAGE for s in result["sources"]
                               if s.get("text") is not None and s["route"] in ("R1", "R3"))
    files = cut.get("files", [])
    read = sum(f["characters_after"] for f in files)
    whole_of_cut = sum(f["characters_before"] for f in files if f["cut"])
    return {"record_id": result["record_id"], "status": result["status"],
            "full_text_characters": full, "full_text_is_a_short_page_only": short,
            "supplement_files": len(files),
            "supplement_files_cut": sum(f["cut"] for f in files),
            "supplement_characters_before_cut": sum(f["characters_before"] for f in files),
            "supplement_characters_read": read,
            "cut_supplement_characters_whole": whole_of_cut,
            "coding_requests": max(1, chunks(full + read)),
            "c2_chunks": sum(chunks(f["characters_before"]) for f in files if f["cut"])}


def estimate(results: list[dict], cuts: dict[str, dict], abstract_chars: dict[str, int],
             prompt: int) -> dict:
    missing = sorted(r["record_id"] for r in results if r["record_id"] not in cuts)
    if missing:
        raise EstimateError(f"no cut for {missing[:5]}")
    rows = [per_record(r, cuts[r["record_id"]]) for r in results]
    chars = sum(r["full_text_characters"] + r["supplement_characters_read"] for r in rows)
    requests = sum(r["coding_requests"] for r in rows)
    mean = chars / requests if requests else 0
    lines: dict = {"coding": {}, "sa1_abstract_only": {}, "control_only_papers": {}}
    for model in base.RATIO:
        lines["coding"][model] = usd(model, chars, requests, prompt, True)
        lines["sa1_abstract_only"][model] = usd(model, sum(abstract_chars.values()),
                                                len(abstract_chars), prompt)
        lines["control_only_papers"][model] = usd(model, round(mean * base.CONTROL_ONLY_PAPERS),
                                                  base.CONTROL_ONLY_PAPERS, prompt)
    cut_papers = [r for r in rows if r["supplement_files_cut"]]
    cost = {r["record_id"]: usd(SOL, r["cut_supplement_characters_whole"], r["c2_chunks"],
                                prompt)["usd"] for r in cut_papers}
    n = min(C2_PAPERS, len(cut_papers))
    values = sorted(cost.values())
    rng = random.Random(DRAW_SEED)
    ids = sorted(cost)
    draws = sorted(sum(cost[i] for i in rng.sample(ids, n)) for _ in range(DRAWS)) if n else [0.0]
    lines["c2_sampled_pass"] = {
        "model": SOL, "papers_with_a_cut_supplement": len(cut_papers), "sample_size": n,
        "expected_usd": round(n / len(values) * sum(values), 2) if values else 0.0,
        "cheapest_sample_usd": round(sum(values[:n]), 2),
        "dearest_sample_usd": round(sum(values[-n:]), 2) if n else 0.0,
        "percentile_5_usd": round(draws[int(0.05 * (len(draws) - 1))], 2),
        "percentile_95_usd": round(draws[int(0.95 * (len(draws) - 1))], 2),
        "draws": DRAWS, "draw_seed": DRAW_SEED}
    whole = sum(r["cut_supplement_characters_whole"] for r in cut_papers)
    req = sum(r["c2_chunks"] for r in cut_papers)
    lines["c2_failure_path_contingent"] = {m: usd(m, whole, req, prompt) for m in base.RATIO}
    base_total = round(sum(v["usd"] for k in ("coding", "sa1_abstract_only",
                                              "control_only_papers")
                           for v in lines[k].values()), 2)
    expected = round(base_total + lines["c2_sampled_pass"]["expected_usd"], 2)
    return {
        "records": len(rows),
        "records_by_status": {s: sum(r["status"] == s for r in rows)
                              for s in sorted({r["status"] for r in rows})},
        "records_whose_only_full_text_is_a_page_under_1000_characters": sorted(
            r["record_id"] for r in rows if r["full_text_is_a_short_page_only"]),
        "full_text_characters": sum(r["full_text_characters"] for r in rows),
        "supplement_files": sum(r["supplement_files"] for r in rows),
        "supplement_files_cut": sum(r["supplement_files_cut"] for r in rows),
        "supplement_characters_before_cut": sum(r["supplement_characters_before_cut"]
                                                for r in rows),
        "supplement_characters_read": sum(r["supplement_characters_read"] for r in rows),
        "coding_requests_per_model": requests, "fixed_prompt_characters": prompt,
        "assumptions": {"limit_characters": base.LIMIT,
                        "output_tokens_per_request": base.OUTPUT_TOKENS,
                        "characters_per_token": base.RATIO,
                        "usd_per_million_tokens": base.PRICE,
                        "control_only_papers": base.CONTROL_ONLY_PAPERS,
                        "c2": "the checker reads each cut supplement of a sampled paper whole, in "
                              "chunks of at most 400,000 characters; the paper's full text is "
                              "not counted again"},
        "lines": lines,
        "total_without_c2_usd": base_total,
        "total_with_expected_c2_usd": expected,
        "total_with_dearest_c2_usd": round(base_total
                                           + lines["c2_sampled_pass"]["dearest_sample_usd"], 2),
        "contingent_c2_failure_path_usd": round(sum(
            v["usd"] for v in lines["c2_failure_path_contingent"].values()), 2),
        "approval_line_usd": base.ACCEPTED_UP_TO,
        "per_record": rows}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=pathlib.Path, required=True)
    ap.add_argument("--cuts", type=pathlib.Path, required=True)
    ap.add_argument("--abstract-characters", type=pathlib.Path, required=True)
    ap.add_argument("--prompt", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise EstimateError(f"{a.out} exists; it is written once")
    results = [json.loads(p.read_text()) for p in sorted(a.results.glob("*/result.json"))]
    cuts = {p.parent.name: json.loads(p.read_text()) for p in a.cuts.glob("*/cut.json")}
    out = estimate(results, cuts, json.loads(a.abstract_characters.read_text()),
                   sum(len(p.read_text()) for p in a.prompt))
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "per_record"}, indent=1))


if __name__ == "__main__":
    main()
