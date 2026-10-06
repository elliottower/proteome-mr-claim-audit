# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "pydantic==2.13.5"]
# ///
"""Side check: compare stored `gpt-6-luna` and `gpt-6.1-sol` answers on the 30 development abstracts.

Reads raw exchanges only (Sol's read-only from the study's outputs/raw/sol/, Luna's from this
folder), validates each with the study's own response models, applies the study's own
eligibility rule, and writes the whole result structure to comparison.json before printing.
No model call is made.

Claims are matched on (protein_as_written, outcome_as_written) after lowercasing and collapsing
whitespace, with no other normalization. A key can hold several records per model (the prompt
gives one record per analysis context), so each field is compared as the set of values the key's
records carry, and the keys with exactly one record per model are also counted on their own.

Run from the repository root:
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=experiments/02_claims_meta/scripts \
        uv run side_checks/luna_dev_2026-10/compare.py
"""

import collections
import json
import pathlib

from pydantic import ValidationError

import run_extraction as rx
from apply_eligibility import decide

REPO = pathlib.Path.cwd()
STUDY = REPO / "experiments" / "02_claims_meta"
OUT = REPO / "side_checks" / "luna_dev_2026-10"
RAW = {"sol": STUDY / "outputs" / "raw" / "sol", "luna": OUT / "raw" / "luna"}
MODEL_NAME = {"sol": "gpt-6.1-sol", "luna": "gpt-6-luna"}
SOL_PARSED = {"eligibility": "sol_eligibility_r7_{rev}.jsonl",
              "extraction": "sol_extraction_r8_{rev}.jsonl"}
TASKS = ("eligibility", "extraction")
NULL = "reported_nonsignificant_or_null"

# USD per million tokens, as given for this side check.
PRICES = {
    "sol": {"input": 2.00, "cached_input": 0.10, "cache_write": 2.50, "output": 10.00},
    "luna": {"input": 0.10, "cached_input": 0.01, "cache_write": 0.125, "output": 0.50},
}
ELIGIBILITY_FIELDS = (
    "decision", "genetic_instruments_for_circulating_proteins", "states_protein_outcome_result",
    "proteome_or_panel_wide_screen", "n_proteins_tested", "count_other", "exclusion",
    "also_tissue_or_csf", "reasons", "flags",
)
CLAIM_FIELDS = ("direction", "null_flag", "pqtl_datasets", "outcome_datasets", "evidence_type")


def norm(text: str) -> str:
    return " ".join(text.lower().split())


def load(model: str, task: str, rev: str, pmids: list[str]) -> dict:
    """Per PMID: the first schema-valid output over the stored attempts, as the study reads them."""
    folder = RAW[model] / task / rev
    tokens = collections.Counter()
    records, first_attempt_valid, failed, non_200, models = {}, 0, [], 0, set()
    non_200 = len(list(folder.glob("*.http*.json")))
    for pmid in pmids:
        output, errors = None, []
        for attempt in range(1, rx.MAX_SCHEMA_ATTEMPTS + 1):
            path = folder / f"{pmid}_attempt{attempt}.json"
            if not path.exists():
                continue
            response = json.loads(json.loads(path.read_text())["response_text"])
            models.add(response.get("model"))
            u = response["usage"]
            tokens["requests"] += 1
            tokens["input_tokens"] += u["input_tokens"]
            tokens["cached_input_tokens"] += u["input_tokens_details"]["cached_tokens"]
            tokens["cache_write_tokens"] += u["input_tokens_details"]["cache_write_tokens"]
            tokens["output_tokens"] += u["output_tokens"]
            tokens["reasoning_tokens"] += u["output_tokens_details"]["reasoning_tokens"]
            if output is not None:
                continue
            try:
                output = rx.OUTPUT_MODEL[task].model_validate(
                    json.loads(rx.output_text(response))).model_dump()
                first_attempt_valid += attempt == 1
            except (ValueError, ValidationError) as e:
                errors.append(f"attempt {attempt}: {type(e).__name__}: {str(e)[:300]}")
        if output is None:
            failed.append({"pmid": pmid, "errors": errors})
        records[pmid] = output
    return {"records": records, "tokens": dict(tokens), "models_returned": sorted(models),
            "validity": {"n_records": len(pmids), "schema_valid_first_attempt": first_attempt_valid,
                         "needed_retry": len(pmids) - first_attempt_valid - len(failed),
                         "failed_schema_or_parse": len(failed), "failed": failed,
                         "non_200_exchanges_on_disk": non_200}}


def cost(model: str, tokens: dict) -> dict:
    p = PRICES[model]
    uncached = tokens["input_tokens"] - tokens["cached_input_tokens"] - tokens["cache_write_tokens"]
    parts = {
        "uncached_input": uncached * p["input"] / 1e6,
        "cached_input": tokens["cached_input_tokens"] * p["cached_input"] / 1e6,
        "cache_write": tokens["cache_write_tokens"] * p["cache_write"] / 1e6,
        "output": tokens["output_tokens"] * p["output"] / 1e6,
    }
    return {"uncached_input_tokens": uncached, "usd_parts": parts, "usd": sum(parts.values())}


def eligibility_row(output: dict | None) -> dict | None:
    if output is None:
        return None
    decision, reasons, flags = decide(output)
    return {**{f: output[f] for f in ELIGIBILITY_FIELDS if f in output},
            "exclusion": sorted(output["exclusion"]), "decision": decision,
            "reasons": sorted(reasons), "flags": sorted(flags)}


def compare_eligibility(sol: dict, luna: dict, pmids: list[str]) -> dict:
    rows = {p: {"sol": eligibility_row(sol[p]), "luna": eligibility_row(luna[p])} for p in pmids}
    fields = {}
    for f in ELIGIBILITY_FIELDS:
        diff = [{"pmid": p, "sol": r["sol"][f], "luna": r["luna"][f]} for p, r in rows.items()
                if r["sol"] is None or r["luna"] is None or r["sol"][f] != r["luna"][f]]
        fields[f] = {"agree": len(pmids) - len(diff), "of": len(pmids), "disagreements": diff}
    decisions = {m: dict(collections.Counter(r[m]["decision"] for r in rows.values() if r[m]))
                 for m in ("sol", "luna")}
    return {"decision_counts": decisions, "fields": fields, "per_abstract": rows}


def key_values(claims: list[dict]) -> dict:
    return {
        "n_records": len(claims),
        "direction": sorted({c["direction"] for c in claims}),
        "null_flag": sorted({c["direction"] == NULL for c in claims}),
        "pqtl_datasets": sorted({norm(d) for c in claims for d in c["pqtl_datasets"]}),
        "outcome_datasets": sorted({norm(d) for c in claims for d in c["outcome_datasets"]}),
        "evidence_type": sorted({c["evidence_type"] for c in claims}),
    }


def by_key(output: dict | None) -> dict[tuple[str, str], list[dict]]:
    keyed = collections.defaultdict(list)
    for c in (output or {"claims": []})["claims"]:
        keyed[(norm(c["protein_as_written"]), norm(c["outcome_as_written"]))].append(c)
    return keyed


def brief(pmid: str, c: dict) -> dict:
    return {"pmid": pmid, **{f: c[f] for f in (
        "protein_as_written", "outcome_as_written", "direction", "evidence_type", "claim_scope",
        "pqtl_datasets", "outcome_datasets", "evidence_span")}}


def agreement(matched: list[dict]) -> dict:
    return {f: {"agree": sum(m["agree"][f] for m in matched), "of": len(matched),
                "disagreements": [{k: m[k] for k in ("pmid", "protein", "outcome")}
                                  | {"sol": m["sol"][f], "luna": m["luna"][f]}
                                  for m in matched if not m["agree"][f]]}
            for f in CLAIM_FIELDS}


def compare_extraction(sol: dict, luna: dict, pmids: list[str], decisions: dict) -> dict:
    per_abstract, matched, only = {}, [], {"sol": [], "luna": []}
    for p in pmids:
        ks, kl = by_key(sol[p]), by_key(luna[p])
        per_abstract[p] = {
            "sol_eligibility_decision": decisions[p]["sol"]["decision"],
            "luna_eligibility_decision": decisions[p]["luna"]["decision"],
            "sol_records": sum(map(len, ks.values())), "luna_records": sum(map(len, kl.values())),
            "sol_keys": len(ks), "luna_keys": len(kl), "matched_keys": len(ks.keys() & kl.keys()),
        }
        for key in sorted(ks.keys() & kl.keys()):
            vs, vl = key_values(ks[key]), key_values(kl[key])
            matched.append({"pmid": p, "protein": key[0], "outcome": key[1], "sol": vs, "luna": vl,
                            "agree": {f: vs[f] == vl[f] for f in CLAIM_FIELDS}})
        only["sol"] += [brief(p, c) for key in sorted(ks.keys() - kl.keys()) for c in ks[key]]
        only["luna"] += [brief(p, c) for key in sorted(kl.keys() - ks.keys()) for c in kl[key]]
    one_to_one = [m for m in matched if m["sol"]["n_records"] == m["luna"]["n_records"] == 1]

    def subset(keep: list[str]) -> dict:
        ms = [m for m in matched if m["pmid"] in keep]
        return {
            "n_abstracts": len(keep), "pmids": keep,
            "sol_records": sum(per_abstract[p]["sol_records"] for p in keep),
            "luna_records": sum(per_abstract[p]["luna_records"] for p in keep),
            "sol_keys": sum(per_abstract[p]["sol_keys"] for p in keep),
            "luna_keys": sum(per_abstract[p]["luna_keys"] for p in keep),
            "matched_keys": len(ms),
            "sol_only_records": sum(c["pmid"] in keep for c in only["sol"]),
            "luna_only_records": sum(c["pmid"] in keep for c in only["luna"]),
            "agreement_all_matched_keys": agreement(ms),
        }

    eligible = [p for p in pmids if decisions[p]["sol"]["decision"] != "ineligible"]
    return {
        "matching_rule": "protein_as_written and outcome_as_written, lowercased, whitespace "
                         "collapsed; a field agrees when the sets of values over the key's "
                         "records are equal",
        "all_30_abstracts": subset(pmids),
        "abstracts_not_ineligible_in_sol_run": subset(eligible),
        "agreement_keys_with_one_record_per_model": {"n_keys": len(one_to_one),
                                                     **agreement(one_to_one)},
        "evidence_type_counts": {
            m: dict(collections.Counter(c["evidence_type"] for p in pmids
                                        for c in (recs[p] or {"claims": []})["claims"]))
            for m, recs in (("sol", sol), ("luna", luna))},
        "per_abstract": per_abstract, "matched_keys": matched,
        "sol_only_records": only["sol"], "luna_only_records": only["luna"],
    }


def main() -> None:
    dev = [json.loads(line) for line in
           (STUDY / "prompts" / "dev_abstracts.jsonl").read_text().splitlines() if line.strip()]
    late = [r["pmid"] for r in dev if r["first_public_date"] >= "2019-01-01"]
    if late or len(dev) != 30:
        raise ValueError(f"development file is not 30 pre-2019 records: {len(dev)}, {late}")
    pmids = [r["pmid"] for r in dev]

    data, revisions, checks = {}, {}, {}
    for task in TASKS:
        prompt = (rx.PROMPTS / f"{task}_prompt.md").read_text()
        schema = json.loads((rx.PROMPTS / "schema.json").read_text())[task]
        rev = revisions[task] = rx.revision_id(task, prompt, schema)
        data[task] = {m: load(m, task, rev, pmids) for m in ("sol", "luna")}
        parsed = [json.loads(line) for line in
                  (rx.PARSED / SOL_PARSED[task].format(rev=rev)).read_text().splitlines()]
        requests = {m: [json.loads((RAW[m] / task / rev / f"{p}_attempt1.json").read_text())
                        ["request"] for p in pmids] for m in ("sol", "luna")}
        checks[task] = {
            "current_prompt_equals_prompt_stored_with_sol_raw":
                (RAW["sol"] / task / rev / "prompt.md").read_text() == prompt,
            "sol_raw_equals_sol_parsed_file":
                {r["pmid"]: r["output"] for r in parsed} == data[task]["sol"]["records"],
            "sol_parsed_file": SOL_PARSED[task].format(rev=rev),
            "luna_request_equals_sol_request_except_model": all(
                {**lu, "model": None} == {**so, "model": None}
                for lu, so in zip(requests["luna"], requests["sol"])),
            "request_models": {m: sorted({r["model"] for r in requests[m]})
                               for m in ("sol", "luna")},
        }

    elig = compare_eligibility(data["eligibility"]["sol"]["records"],
                               data["eligibility"]["luna"]["records"], pmids)
    extr = compare_extraction(data["extraction"]["sol"]["records"],
                              data["extraction"]["luna"]["records"], pmids, elig["per_abstract"])

    costs = {}
    for m in ("sol", "luna"):
        per_task = {t: {"tokens": data[t][m]["tokens"], **cost(m, data[t][m]["tokens"])}
                    for t in TASKS}
        total = dict(sum((collections.Counter(data[t][m]["tokens"]) for t in TASKS),
                         collections.Counter()))
        costs[m] = {"prices_usd_per_million": PRICES[m], **per_task,
                    "both_tasks": {"tokens": total, **cost(m, total)}}
    costs["sol_over_luna_usd_ratio"] = {
        t: costs["sol"][t]["usd"] / costs["luna"][t]["usd"] for t in (*TASKS, "both_tasks")}
    costs["note"] = ("input_tokens includes cached_tokens and cache_write_tokens; the remainder "
                     "is charged at the input price. Usage is summed over every stored 200 "
                     "exchange of each run; caching state differed between the runs.")

    result = {
        "what": "Side check, not part of the registered study: gpt-6-luna against gpt-6.1-sol on "
                "the 30 pre-2019 development abstracts, same prompts, schema and request body.",
        "inputs": {"abstracts": "experiments/02_claims_meta/prompts/dev_abstracts.jsonl",
                   "n_abstracts": len(pmids), "pmids": pmids,
                   "first_public_date_max": max(r["first_public_date"] for r in dev),
                   "seed": None},
        "models": MODEL_NAME,
        "models_returned": {t: {m: data[t][m]["models_returned"] for m in ("sol", "luna")}
                            for t in TASKS},
        "prompt_revisions": {
            t: {"sol": revisions[t], "luna": f"same prompt and schema as Sol {revisions[t]} "
                                             "(the id itself hashes the Sol model name)"}
            for t in TASKS},
        "sol_runs": {"eligibility": "label r7 (r8 re-read the same cached exchanges), "
                                    "2026-09-30", "extraction": "label r8, 2026-09-30"},
        "consistency_checks": checks,
        "eligibility": elig,
        "extraction": extr,
        "validity": {t: {m: data[t][m]["validity"] for m in ("sol", "luna")} for t in TASKS},
        "cost": costs,
    }
    (OUT / "comparison.json").write_text(json.dumps(result, indent=1, ensure_ascii=False))

    print("checks", json.dumps(checks))
    for f, v in elig["fields"].items():
        print(f"eligibility {f}: {v['agree']}/{v['of']}", json.dumps(v["disagreements"]))
    print("decisions", elig["decision_counts"])
    for name in ("all_30_abstracts", "abstracts_not_ineligible_in_sol_run"):
        s = extr[name]
        print(name, {k: v for k, v in s.items() if k not in ("agreement_all_matched_keys", "pmids")},
              {f: f"{v['agree']}/{v['of']}" for f, v in s["agreement_all_matched_keys"].items()})
    o = extr["agreement_keys_with_one_record_per_model"]
    print("one record per model:", o["n_keys"],
          {f: f"{o[f]['agree']}/{o[f]['of']}" for f in CLAIM_FIELDS})
    print("evidence types", extr["evidence_type_counts"])
    print("validity", json.dumps(result["validity"]))
    for m in ("sol", "luna"):
        for t in (*TASKS, "both_tasks"):
            print(m, t, costs[m][t]["tokens"], f"uncached {costs[m][t]['uncached_input_tokens']}",
                  f"${costs[m][t]['usd']:.4f}")
    print("ratio", costs["sol_over_luna_usd_ratio"])


if __name__ == "__main__":
    main()
