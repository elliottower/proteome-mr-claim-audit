# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Collect the prompt-development metrics for one prompt revision into one file.

Reads the parsed eligibility and extraction outputs of a revision label, the eligibility
decisions, the span and claim verification summaries, and every cached raw exchange of those
revisions (for tokens and cost). Writes outputs/dev_metrics/<label>.json.

Cost uses the per-token prices in PRICES_USD_PER_MTOK, which are the figures in
OPEN_QUESTIONS.md item 24 and are not confirmed against an invoice. Cached input tokens are
charged at the full input price, so the figure is an upper bound under those prices.

With `--fulltext`, reports the full-text extraction of that label instead (no eligibility step),
from outputs/parsed/sol_fulltext_extraction_<label>_<rev>.jsonl.

Usage: uv run scripts/dev_report.py --label r2
       uv run scripts/dev_report.py --label ft1 --fulltext
"""

import argparse
import collections
import datetime
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
PARSED = EXP / "outputs" / "parsed"
RAW = EXP / "outputs" / "raw" / "sol"
PRICES_USD_PER_MTOK = {"input": 2.0, "output": 10.0}


class ReportError(Exception):
    """A revision label names no output, or names more than one."""


def one(pattern: str) -> pathlib.Path:
    """The single parsed output `sol_<task>_<label>_<12 hex>.jsonl`; other labels sharing the
    prefix (`r4_known_items`) are not matched."""
    stem = re.compile(re.escape(pattern.removesuffix("*.jsonl")) + r"[0-9a-f]{12}\.jsonl")
    hits = sorted(p for p in PARSED.glob(pattern) if stem.fullmatch(p.name))
    if len(hits) != 1:
        raise ReportError(f"{pattern}: expected one file, found {[h.name for h in hits]}")
    return hits[0]


def raw_usage(task: str, rev: str) -> dict:
    u = collections.Counter()
    models = set()
    for f in (RAW / task / rev).glob("*.json"):
        if f.name == "schema.json":
            continue
        ex = json.loads(f.read_text())
        u["exchanges"] += 1
        if ex["status"] != 200:
            u["http_errors"] += 1
            continue
        body = json.loads(ex["response_text"])
        models.add(body.get("model"))
        usage = body.get("usage", {})
        u["input_tokens"] += usage.get("input_tokens", 0)
        u["cached_input_tokens"] += usage.get("input_tokens_details", {}).get("cached_tokens", 0)
        u["output_tokens"] += usage.get("output_tokens", 0)
        u["reasoning_tokens"] += usage.get("output_tokens_details", {}).get(
            "reasoning_tokens", 0)
    cost = (u["input_tokens"] * PRICES_USD_PER_MTOK["input"]
            + u["output_tokens"] * PRICES_USD_PER_MTOK["output"]) / 1e6
    return {**u, "models_returned": sorted(m for m in models if m), "cost_usd_upper": cost}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--fulltext", action="store_true")
    a = ap.parse_args()
    if a.fulltext:
        extr = one(f"sol_fulltext_extraction_{a.label}_*.jsonl")
        rows = [json.loads(l) for l in extr.read_text().splitlines()]
        ver = EXP / "outputs" / "verification" / extr.stem
        spans = json.loads((ver / "span_summary.json").read_text())
        report = {
            "label": a.label, "written_utc": datetime.datetime.now(datetime.UTC).isoformat(
                timespec="seconds"),
            "extraction_file": str(extr.relative_to(EXP)), "revision": rows[0]["revision"],
            "pmids": [r["pmid"] for r in rows],
            "status": dict(collections.Counter(r["status"] for r in rows)),
            "spans": {k: v for k, v in spans.items() if k != "failing"},
            "claim_checks": json.loads((ver / "claim_summary.json").read_text()),
            "usage": raw_usage("fulltext_extraction", rows[0]["revision"]),
            "prices_usd_per_mtok": PRICES_USD_PER_MTOK,
        }
        out = EXP / "outputs" / "dev_metrics" / f"{a.label}.json"
        out.write_text(json.dumps(report, indent=1))
        print(json.dumps(report, indent=1))
        return

    roles = {r["pmid"]: r["role"] for r in map(json.loads, (
        EXP / "prompts" / "dev_abstracts.jsonl").read_text().splitlines())}
    elig = one(f"sol_eligibility_{a.label}_*.jsonl")
    extr = one(f"sol_extraction_{a.label}_*.jsonl")
    decisions_file = elig.with_name(elig.stem + ".decisions.jsonl")
    decisions = {d["pmid"]: d for d in map(json.loads, decisions_file.read_text().splitlines())}
    elig_rows = [json.loads(l) for l in elig.read_text().splitlines()]
    extr_rows = [json.loads(l) for l in extr.read_text().splitlines()]
    ver = EXP / "outputs" / "verification" / extr.stem
    spans = json.loads((ver / "span_summary.json").read_text())
    claims = json.loads((ver / "claim_summary.json").read_text())

    by_role = collections.defaultdict(collections.Counter)
    for pmid, d in decisions.items():
        by_role[roles[pmid]][d["decision"]] += 1
    elig_rev, extr_rev = elig_rows[0]["revision"], extr_rows[0]["revision"]
    usage = {"eligibility": raw_usage("eligibility", elig_rev),
             "extraction": raw_usage("extraction", extr_rev)}
    report = {
        "label": a.label, "written_utc": datetime.datetime.now(datetime.UTC).isoformat(
            timespec="seconds"),
        "eligibility_file": str(elig.relative_to(EXP)),
        "extraction_file": str(extr.relative_to(EXP)),
        "revisions": {"eligibility": elig_rev, "extraction": extr_rev},
        "n_abstracts": len(extr_rows),
        "schema_validity": {
            "eligibility_ok": sum(r["status"] == "ok" for r in elig_rows),
            "eligibility_needed_retry": sum(r["attempts"] > 1 for r in elig_rows
                                            if r["status"] == "ok"),
            "eligibility_failed": sum(r["status"] != "ok" for r in elig_rows),
            "extraction_ok": sum(r["status"] == "ok" for r in extr_rows),
            "extraction_needed_retry": sum(r["attempts"] > 1 for r in extr_rows
                                           if r["status"] == "ok"),
            "extraction_failed": sum(r["status"] != "ok" for r in extr_rows),
        },
        "eligibility_by_role": {k: dict(v) for k, v in sorted(by_role.items())},
        "eligibility_reasons": dict(collections.Counter(
            r for d in decisions.values() for r in d["reasons"])),
        "claims_per_abstract_by_role": {
            role: sum(len(r["output"]["claims"]) for r in extr_rows
                      if r["status"] == "ok" and roles[r["pmid"]] == role)
            for role in sorted(set(roles.values()))},
        "direction_values": dict(collections.Counter(
            c["direction"] for r in extr_rows if r["status"] == "ok"
            for c in r["output"]["claims"])),
        "spans": {k: v for k, v in spans.items() if k != "failing"},
        "claim_checks": claims,
        "usage": usage,
        "prices_usd_per_mtok": PRICES_USD_PER_MTOK,
    }
    out = EXP / "outputs" / "dev_metrics" / f"{a.label}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
