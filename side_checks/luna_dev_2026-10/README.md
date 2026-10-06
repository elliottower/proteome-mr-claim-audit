# Luna against Sol on the 30 development abstracts

Run on 2026-10-06.

A side check. It compares `gpt-6-luna` with the study's registered model, `gpt-6.1-sol`, on the 30
development abstracts in `experiments/02_claims_meta/prompts/dev_abstracts.jsonl`. Every one of
the 30 was first public before 2019-01-01, outside the study window (latest
`first_public_date`: 2018-08-15). It is not part of the registered study and is not reported in
Paper 1.

**No results ledger entry was made, because no paper reports this.** Nothing here was sealed
with `results seal`, run under `results run` or bound with `results claim`. If any number below
is ever to be reported, the check must be rerun under a record first.

Nothing under `experiments/02_claims_meta/` or `.results/` was written. No record from 2019 or
later was read, fetched or sent.

## What was sent

| | Sol (stored) | Luna (this check) |
|---|---|---|
| model requested and returned | `gpt-6.1-sol` | `gpt-6-luna` |
| eligibility prompt and schema | revision `2811496ef424` (label r7, run 2026-09-30) | the same prompt and schema |
| extraction prompt and schema | revision `0b97103cd7a4` (label r8, run 2026-09-30) | the same prompt and schema |
| endpoint | `https://api.openai.com/v1/responses` | the same |
| reasoning | `{"effort": "medium"}` | the same, accepted unchanged |
| tools, store, output format | `[]`, `false`, strict JSON schema | the same |
| abstracts | 30 | 30 |

Both revisions are the current frozen prompts: `run_extraction.revision_id` on the prompt and
schema files as they stand gives `2811496ef424` and `0b97103cd7a4`, and the prompt text stored
beside Sol's raw exchanges equals the current files. The stored Sol runs on the development
abstracts therefore used the frozen prompts, not an older revision. (The r8 eligibility label
re-read the r7 exchanges from the cache; one set of 30 Sol eligibility exchanges exists.)

The Luna request body is built by the study's `run_extraction.request_body`, imported, with
`body["model"]` replaced. `compare.py` checks that each of the 60 Luna request bodies equals the
stored Sol request body for the same abstract and task in every field except `model`; all 60
do. The API rejected no parameter, so nothing else differed. The revision id hashes the model
name, so the Luna folders carry the Sol revision id only as a name for the prompt and schema.

## Commands

From the repository root, with `OPENAI_API_KEY` exported in a subshell from the credentials
pipe:

```
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=experiments/02_claims_meta/scripts
uv run side_checks/luna_dev_2026-10/run_luna.py --task eligibility --probe 29875488
uv run side_checks/luna_dev_2026-10/run_luna.py --task eligibility
uv run side_checks/luna_dev_2026-10/run_luna.py --task extraction
uv run side_checks/luna_dev_2026-10/compare.py
```

The probe sent one eligibility request to learn whether Luna accepts the request as built; its
exchange was reused by the full run, so 60 requests were sent in all (30 per task, 4 at a
time). `compare.py` makes no model call.

## Files

- `run_luna.py`: sends the requests. Refuses any record whose `first_public_date`, or whose
  earliest issue, electronic or PubMed entry date, is on or after 2019-01-01.
- `raw/luna/<task>/<revision>/<pmid>_attempt1.json`: one file per HTTP exchange (request body,
  status, response text, timestamps), written before parsing. No key is stored.
- `parsed/luna_<task>_<revision>.jsonl` and `.meta.json`: validated outputs and run metadata.
- `compare.py`: reads Sol's raw exchanges read-only and Luna's, validates both with the study's
  response models, applies the study's `apply_eligibility.decide`, and writes `comparison.json`.
- `comparison.json`: the whole result structure, including every per-abstract row, every matched
  claim key and every unmatched record.

## Results

All numbers are in `comparison.json`.

**Validity.** Both models: 30 of 30 schema-valid at the first attempt on each task, no retry, no
parse failure, no non-200 response.

**Eligibility (30 abstracts).**

| field | agree |
|---|---|
| decision under the registered rule | 30/30 |
| `genetic_instruments_for_circulating_proteins` | 30/30 |
| `states_protein_outcome_result` | 27/30 |
| `proteome_or_panel_wide_screen` | 29/30 |
| `n_proteins_tested` | 27/30 |
| `count_other` | 27/30 |
| `exclusion` | 30/30 |
| `also_tissue_or_csf` | 28/30 |

Each model gives 1 `eligible_count_not_stated` (PMID 29875488) and 29 ineligible. Disagreements
(Sol, Luna):

- `states_protein_outcome_result`: 29258991, 22421340, 22421339 (yes, no).
- `proteome_or_panel_wide_screen`: 27989323 (uncertain, yes).
- `n_proteins_tested`: 29191953, 25350643, 24246360 (null, 1).
- `count_other`: 25726324, 29728394 (null, 1); 27225428 (null, 4).
- `also_tissue_or_csf`: 29258991, 22421339 (true, false).

None changes a decision: every abstract concerned is ineligible for both models on another
criterion. The reasons differ on 9 abstracts and the flags on 3.

**Extraction (30 abstracts).** The study's dev runs extract from all 30, eligible or not.

| | Sol | Luna |
|---|---|---|
| claim records | 141 | 109 |
| distinct protein and outcome keys | 84 | 71 |
| abstracts with at least one record | 17 | 17 |
| `mr_estimate` records | 77 | 68 |

Claims are matched on `protein_as_written` and `outcome_as_written`, lowercased with whitespace
collapsed, nothing else. 61 keys match. A key can hold several records per model, so a field
agrees when the two models' sets of values over the key's records are equal.

| field, over matched keys | all 61 keys | the 29 keys with one record per model |
|---|---|---|
| direction | 56/61 | 29/29 |
| null flag (`reported_nonsignificant_or_null`) | 56/61 | 29/29 |
| pQTL datasets | 52/61 | 21/29 |
| outcome datasets | 60/61 | 29/29 |
| evidence type | 56/61 | 28/29 |

The 5 direction and null-flag disagreements are keys where Sol gives two records (one `raises`,
one null) and Luna gives one: 19509380 lipoprotein(a) and MI, and four CRP keys of 24246360,
where Luna returns `not_stated`. The 9 pQTL-dataset disagreements are all PMID 25350643: Sol
names the Canadian Multicentre Osteoporosis Study, Luna returns `not_stated`. The outcome-dataset
disagreement is the same abstract ("Canadian Multicentre Osteoporosis Study (CaMos)" against
"CaMos").

Unmatched: 25 Sol records in 9 abstracts and 13 Luna records in 5 abstracts, listed in
`comparison.json`. Eleven of the 25 are variant-association records of PMID 22421339, where Sol
gives 12 records and Luna 1. Six of the 13 Luna records fail to match only on the protein
wording (Luna writes "CETP concentration" and "DBP levels" where Sol writes "CETP" and "DBP");
the corresponding Sol records are among the 25. Luna gives 3 records for PMID 18464913, where Sol gives none.

**Cost (usage summed over the 60 stored exchanges of each model).**

| | Sol | Luna |
|---|---|---|
| input tokens | 138,600 | 138,600 |
| of which cached | 109,051 | 107,735 |
| of which cache writes | 29,369 | 30,685 |
| output tokens | 53,036 | 72,238 |
| of which reasoning | 8,862 | 39,687 |
| cost, USD | 0.6150 | 0.0410 |

Sol costs 14.98 times Luna (eligibility 10.37 times, extraction 16.11 times). Prices per million
tokens: Sol input 2.00, cached input 0.10, cache writes 2.50, output 10.00; Luna 0.10, 0.01,
0.125, 0.50. `input_tokens` contains the cached and cache-write tokens; the remainder (180
tokens per model) is charged at the input price.

## Limits

- 30 abstracts, chosen by title for prompt development, none from the study window.
- One abstract is eligible in Sol's run (PMID 29875488), and both models extract zero claims
  from it. Extraction agreement on eligible abstracts therefore rests on 0 claims. All 61 matched
  keys come from 15 abstracts that both models judge ineligible.
- One run per model at the API's applied temperature of 1.0. This check does not separate
  between-model differences from between-run differences of one model.
- Matching is on exact normalized wording, so a claim worded differently by the two models
  counts as two unmatched records.
- No span check, ontology mapping or direction verification (`verify_claims.py`) was run on
  Luna's output.
- The cost comparison reflects the caching state of each run and the stated prices.
