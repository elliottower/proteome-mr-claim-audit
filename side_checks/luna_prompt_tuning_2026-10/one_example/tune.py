# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "pydantic==2.13.5"]
# ///
"""Side check, not part of the registered study: try prompt variants for `gpt-6-luna` on a few
pre-2019 development abstracts and compare each with the stored GPT-6.1 Sol extraction.

A variant is the frozen extraction prompt with one addendum appended (the frozen file is read,
never changed), optionally with another reasoning effort. Every exchange is written under
raw/<variant>/ before it is parsed; the comparison is written to results.json before printing.

Run from the repository root:
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=experiments/02_claims_meta/scripts \
        uv run side_checks/luna_prompt_tuning_2026-10/one_example/tune.py
"""

import argparse
import collections
import datetime
import json
import os
import pathlib

import httpx

import run_extraction as rx

LUNA_MODEL = "gpt-6-luna"
REPO = pathlib.Path.cwd()
STUDY = REPO / "experiments" / "02_claims_meta"
HERE = REPO / "side_checks" / "luna_prompt_tuning_2026-10" / "one_example"
SOL_PARSED = STUDY / "outputs" / "parsed" / "sol_extraction_r8_0b97103cd7a4.jsonl"
WINDOW_START = datetime.date(2019, 1, 1)

ENUMERATE = """

## Completeness (added for this model)

Before writing records, list for yourself every distinct analysis the abstract reports for each
protein–outcome pair: the main analysis, each subgroup, each combined or joint analysis ("when
present together", "in combination"), each replication, each sensitivity analysis. Write one
record for each protein × outcome × analysis. Copy the words that name the analysis into
`analysis_context_as_written`, and the subgroup into `subgroup_as_written`.
"""

NO_MERGE = ENUMERATE + """
Two sentences that report the same protein–outcome pair under different conditions are two
records, even when the direction is the same or is not stated. A result restricted to a subgroup
is a separate record from the overall result, with its own evidence span.
"""

EXAMPLE = NO_MERGE + """
Illustration (invented): "Variants in GENE1 and GENE2 were associated with lower risk of
disease A. The effect was limited to women. When present together, the variants had additive
effects on disease A." gives six records: GENE1–disease A and GENE2–disease A for the main
analysis; the same two pairs with the subgroup "women"; and the same two pairs with the analysis
context "When present together".
"""

SENTENCE_CHECK = """

## Final check (added for this model)

After drafting the records, reread every sentence of the Results and Conclusions. For each
sentence that reports a genetic result for a protein and an outcome, confirm that one record per
protein–outcome pair in that sentence cites it in `evidence_span`. If a sentence has no record,
add the records it supports, with the analysis context that sentence states.
"""

CARRY_OVER = NO_MERGE + """
Carried-over results. When a sentence says that results were similar, the same, comparable or
also seen for other outcomes, for another instrument or variant, or in another analysis, it
states those results too. Write one record for every protein–outcome pair it carries over, in
that analysis context, citing that sentence in `evidence_span`:
- "Results were similar for outcomes B, C and D" gives one record for each of B, C and D, of the
  same evidence type and direction as the result it refers to.
- "Results were similar using variant V" or "in a sensitivity analysis" gives one record for
  every protein–outcome pair of the main analysis, with that context.

Lists. "X was not associated with A, B, C or D" gives four null records, one per listed outcome.
A list of outcomes after one verb is never one record.
"""

CARRY_OVER_EXAMPLE = CARRY_OVER + """
Illustration (invented): "Genetically higher protein P lowered risk of disease A (OR 0.8) but was
not associated with traits B or C. Results were similar when restricted to variant V. Findings
were comparable for diseases D and E." gives eight records: P–A lowers, P–B null and P–C null in
the main analysis; the same three pairs with the analysis context "when restricted to variant V";
and P–D lowers and P–E lowers, citing the last sentence.
"""

VARIANTS = {
    "v6_carry_over": (CARRY_OVER, None),
    "v7_carry_over_example": (CARRY_OVER_EXAMPLE, None),
    "v0_frozen": ("", None),
    "v1_enumerate": (ENUMERATE, None),
    "v2_no_merge": (NO_MERGE, None),
    "v3_example": (EXAMPLE, None),
    "v4_no_merge_high": (NO_MERGE, "high"),
    "v5_sentence_check": (SENTENCE_CHECK, None),
}


class TuneError(Exception):
    """The side check cannot proceed."""


def key_of(claim: dict) -> tuple[str, str]:
    return (" ".join(claim["protein_as_written"].lower().split()),
            " ".join(claim["outcome_as_written"].lower().split()))


def load_records(pmids: list[str]) -> list[rx.Record]:
    rows = [json.loads(line) for line in
            (STUDY / "prompts" / "dev_abstracts.jsonl").read_text().splitlines() if line.strip()]
    chosen = [r for r in rows if str(r["pmid"]) in pmids]
    if len(chosen) != len(pmids):
        raise TuneError("a requested PMID is not a development abstract")
    for row in chosen:
        if datetime.date.fromisoformat(row["first_public_date"]) >= WINDOW_START:
            raise TuneError(f"{row['pmid']} is not first public before 2019")
    return [rx.Record.model_validate(r) for r in chosen]


def call(client: httpx.Client, key: str, name: str, prompt: str, effort: str | None,
         schema: dict, rec: rx.Record) -> list[dict]:
    cache = HERE / "raw" / name / f"{rec.pmid}.json"
    if not cache.exists():
        body = rx.request_body("extraction", prompt, schema, rec)
        body["model"] = LUNA_MODEL
        if effort is not None:
            body["reasoning"] = {"effort": effort}
        started = rx.now()
        r = client.post(rx.ENDPOINT, json=body, headers={"Authorization": f"Bearer {key}"})
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"variant": name, "request": body, "started_utc": started,
                                     "finished_utc": rx.now(), "status": r.status_code,
                                     "response_text": r.text}, indent=1, ensure_ascii=False))
    exchange = json.loads(cache.read_text())
    if exchange["status"] != 200:
        raise TuneError(f"{name} {rec.pmid}: HTTP {exchange['status']}")
    response = json.loads(exchange["response_text"])
    out = rx.OUTPUT_MODEL["extraction"].model_validate(json.loads(rx.output_text(response)))
    return out.model_dump()["claims"]


def compare(sol: list[dict], luna: list[dict]) -> dict:
    s, lu = collections.Counter(map(key_of, sol)), collections.Counter(map(key_of, luna))
    matched = sum((s & lu).values())
    return {"sol_records": len(sol), "luna_records": len(luna), "matched_records": matched,
            "sol_only": sum((s - lu).values()), "luna_only": sum((lu - s).values()),
            "luna_contexts": sorted({c["analysis_context_as_written"] for c in luna}),
            "luna_evidence_types": dict(collections.Counter(c["evidence_type"] for c in luna))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pmids", default="27959767")
    ap.add_argument("--variants", default=",".join(VARIANTS))
    a = ap.parse_args()
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise TuneError("OPENAI_API_KEY is not set")
    pmids = a.pmids.split(",")
    records = load_records(pmids)
    frozen = (rx.PROMPTS / "extraction_prompt.md").read_text()
    schema = json.loads((rx.PROMPTS / "schema.json").read_text())["extraction"]
    sol = {str(json.loads(line)["pmid"]): json.loads(line)["output"]["claims"]
           for line in SOL_PARSED.read_text().splitlines() if line.strip()}
    results: dict = {}
    with httpx.Client(timeout=600) as client:
        for name in a.variants.split(","):
            addendum, effort = VARIANTS[name]
            results[name] = {rec.pmid: compare(sol[rec.pmid], call(
                client, key, name, frozen + addendum, effort, schema, rec)) for rec in records}
    out = HERE / f"results_{'_'.join(pmids)}.json"
    out.write_text(json.dumps(results, indent=1, ensure_ascii=False))
    for name, per in results.items():
        for pmid, c in per.items():
            print(f"{name:<20} {pmid}  sol {c['sol_records']:>2}  luna {c['luna_records']:>2}  "
                  f"matched {c['matched_records']:>2}  sol-only {c['sol_only']:>2}  "
                  f"luna-only {c['luna_only']:>2}")


if __name__ == "__main__":
    main()
