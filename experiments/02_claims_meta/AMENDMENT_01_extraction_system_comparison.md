# Amendment 1: comparison of the registered Sol extraction with a tuned Luna extraction system

Amendment to `PREREG.md` (frozen at `02bb006f3e55`, plan sha256
`9f06131af9936cc7c3556e87d77dcec65d034e4665be023eedf39948082d417b`, registered at
https://osf.io/zae8c). It takes effect when the log of `PREREG.md` names the sha256 of this file
and of `prompts/luna_extraction_prompt.md`; `scripts/run_extraction_luna.py` refuses to run
before that.

## What is added

An extraction-system comparison. Every abstract the registered extraction (GPT-6.1 Sol with the
frozen extraction prompt) extracts is also extracted, in two separate runs, by a second
extraction system: `gpt-6-luna` (OpenAI) with `prompts/luna_extraction_prompt.md`. The verified
registry entries of the two systems are compared. The comparison is descriptive. It has no
hypothesis and no verdict.

## What is unchanged

GPT-6.1 Sol with the frozen prompt remains the extraction tool of every registered result. The
search, the eligibility decisions, the registered extraction and its repeat run, verification,
manual dataset coding, the registry, H1, H2, H2b, every index, every registered secondary
outcome and every sensitivity analysis are computed as registered, from GPT-6.1 Sol's records
only. No Luna output enters any of them, and no result of this amendment replaces one of them.

**Sentence amended.** §Data collection procedures, Tool: "No second model enters any stage"
now reads: no second model enters any registered primary or secondary result; a second
extraction system, `gpt-6-luna` with its own prompt, extracts the same abstracts for the
extraction-system comparison of Amendment 1.

## Limitation

This comparison contrasts two model–prompt configurations, not models under identical instructions. Differences therefore cannot be attributed uniquely to model identity. The Luna addendum was selected for agreement with Sol on seven pre-2019 development abstracts; agreement in the study corpus is descriptive transfer of that Sol-targeted configuration, not independent validation or evidence that either extraction is correct.

A difference between the two systems combines the model, the prompt addendum, their
interaction and run-to-run variation. The paper attributes no difference to the model alone.

## Procedure

1. **Records.** Each file of eligible abstracts GPT-6.1 Sol extracts at stage 3 (the search,
   each chase round, each gate batch) is extracted by the Luna system. The runner refuses unless
   the record ids equal those of Sol's parsed extraction of that file. The update set is
   extracted with the rest and is not compared.
2. **Request.** The study's request (Responses API, reasoning effort `medium`, no tools, `store`
   false, the committed `extraction` schema as strict output, title and abstract only) with two
   differences: the model string, and the instructions, which are
   `prompts/luna_extraction_prompt.md`. That file is the frozen `prompts/extraction_prompt.md`
   followed by one addendum on enumerating analyses, carried-over results and lists; the runner
   refuses a prompt that does not begin with the frozen prompt. A response that fails the schema
   is re-run once, then recorded `extraction_failed`.
3. **Two runs.** Run 1 and run 2 are separate runs of the same request, with separate raw
   folders. They are separate API calls with separately stored exchanges; their statistical
   independence is not assumed. Every request and response is stored and committed, as for Sol.
4. **Verification.** Each Luna extraction file passes `verify_spans.py` and `verify_claims.py`
   unchanged. The second GPT-6.1 Sol run on the 10% stability sample passes them too.
5. **Registry claims.** `assemble_registry.py`, with the records, eligibility decisions and
   manual dataset codes of the primary registry, is applied to Luna run 1's checks, to Luna
   run 2's and to the second Sol run's, each into its own folder. A manual code applies where
   the record, side and name as written are those it was coded for; no name is coded for the
   comparison.
6. **Comparison.** `scripts/extraction_system_comparison.py`, on Modal, after the stage-5 tables
   of the primary registry are committed. It raises unless the tables it computes from the Sol
   claims file equal the registered `primary` table, and unless it is given the usage of all
   three extraction runs (Sol, Luna run 1, Luna run 2) over the same abstracts.

## Unit and run-1-first completion

The unit is the family–pair registry entry of the confirmatory window: study family × UniProt
accession × canonical outcome identifier, as `build_registry.build` forms it from verified claim
records (family–pair direction; null flag: the family has a verified
`reported_nonsignificant_or_null` record on the pair; mapped dataset names per side). It is the
unit that enters H1 and H2. A share over this unit is family–pair coverage or agreement; it does
not measure whether a system returned every subgroup analysis, sensitivity analysis, dataset
attribution, null result or evidence span of a pair.

`luna_run1_completed` ("Luna run 1, completed by run 2 for missing family–pairs") is every claim
record of run 1, and the claim records of run 2 on the family–pairs run 1 lacks. A family–pair
present in both runs keeps run 1's records: a run-2 context, null result or dataset name never
supplements a family–pair already present in run 1. It is not the pooled records of the two
runs.

## Reported quantities

Each share is count / denominator, with a Wilson 95% interval (naive, descriptive) and the
registered pair bootstrap over canonical pairs (10,000 replicates, seed 20261001, generator
streams 100 to 154, one per share, inverted-CDF 2.5th and 97.5th percentiles). No P value, no
verdict. A share on fewer than 20 records is printed and labeled imprecise.

| quantity | definition |
|---|---|
| Sol in Luna run 1 | the share of the registered extraction's verified family–pair registry entries represented in the Luna-derived registry (run 1) |
| Luna run 1 in Sol | the share of Luna run 1's verified family–pair registry entries represented in the registered extraction's registry |
| Sol in Luna run 1 completed; Luna run 1 completed in Sol | the same two shares for `luna_run1_completed` |
| direction class | among shared entries, share with the same family–pair direction class |
| direction | among shared entries directional in both sources, share with the same direction (a `_with_nonsignificant` form read as its direction); the opposite-direction entries are counted |
| null flag | among shared entries, share with the same null flag |
| release identity | among shared entries, per side, the two sources' names by `release_identity`: `identical`, `not_identical`, `undetermined` (counts) |
| Luna run 1 against run 2 | the shares above between the two Luna runs |
| repeat sample | on the claim records of the abstracts of the 10% stability sample only: the shares above for Sol run 1 against the second Sol run, Sol run 1 against Luna run 1, and Luna run 1 against Luna run 2 |
| H1, H2, H2b by source | `build_registry.tables` applied to Sol's claims, to Luna run 1's and to `luna_run1_completed`'s: H1 pair and edge concordance, the H2 and H2b counts, LB, UB, LB_b, UB_b, the resolvable share, the denominators, with the registered intervals; for the two Luna-derived registries, each estimate also as its difference from the registered Sol estimate |
| verification by source | per extraction file: claim records, span-check pass, `mr_estimate` records, records entering the registry by first failing check, direction verified, `extraction_failed` abstracts (the summaries the registered scripts write) |
| cost | extraction requests only, per extraction run: tokens and USD summed over the responses that carry usage (HTTP 200), divided by every abstract the run attempted (the records of its parsed extraction files, whether or not a request succeeded); abstracts with no billable response and `extraction_failed` abstracts are counted separately; stored exchanges of records outside those files are counted and not priced. List prices in USD per million tokens, as given by the author on 2026-10-05 from OpenAI's pricing table, short-context column: GPT-6.1 Sol input 2.00, cached input 0.10, cache writes 2.50, output 10.00; `gpt-6-luna` 0.10, 0.01, 0.125, 0.50. `input_tokens` is read as including cached and cache-write tokens |

Threshold classifications remain exclusively those of the registered Sol analysis. For Luna-derived registries, only descriptive estimates, bounds and denominators are reported.

## Reading

| observation | reading |
|---|---|
| Sol in Luna, beside Sol in the second Sol run on the repeat sample | the share of the registered extraction's family–pair registry entries the tuned Luna system represents, beside the share GPT-6.1 Sol represents of its own |
| the shares of Luna run 1 completed beside run 1's | what a second run of the Luna system adds on family–pairs run 1 lacks |
| Luna in Sol | the share of the Luna-derived registry's entries the registered extraction also holds |
| direction among shared entries | whether the two extraction systems assign one direction to one family–pair |
| H1 estimates and H2, H2b bounds by source | how far the estimates and bounds move when the registry is built from the tuned Luna extraction; no threshold classification is read from them |

Because the Luna addendum was selected against Sol outputs on the development subset, agreement with Sol is an optimized descriptive outcome; it is not an independent convergence test.

Neither system's output is labeled against a reference, so no quantity here says which
extraction is correct or how complete either is. High agreement is the outcome favorable to the
registered extraction.

## Reporting

One table, headed "Extraction-system comparison", in the fixed supplement after the sensitivity
tables, emitted whatever its result. The main text may state its shares in one sentence. Nothing
from this amendment enters the abstract (§Indices, the list of outcomes the abstract may state,
is unchanged). The paper does not call the comparison validation or replication, does not call
it a comparison of models, and attributes no difference to model identity alone.

## Foreknowledge

- The Luna prompt was tuned on 2026-10-06 on seven development abstracts first public before
  2019 (`prompts/dev_abstracts.jsonl`), the seven of the 30 with the largest difference between
  Sol's and Luna's records under the frozen prompt. Eight variants were run, one run each, and
  scored on those same abstracts by records matching Sol's on protein and outcome as written:
  frozen prompt 29 of 66; the registered Luna prompt 48 of 66 (`mr_estimate` records 15 and 18
  of 23); four other variants on all seven, 36, 36, 39 and 40 of 66; two variants on one
  abstract only (one with reasoning effort `high`). The last two variants written, the
  registered prompt among them, were written after the outputs of the earlier ones were read.
  The registered prompt is the highest-scoring variant, selected on the abstracts it was tuned
  on.
- On the 30 development abstracts, with the frozen prompts (2026-10-06): the same eligibility
  decision on 30 of 30; claim records Sol 141, Luna 109.
- Files: `side_checks/luna_dev_2026-10/`, `side_checks/luna_prompt_tuning_2026-10/`. No record
  first public in 2019 or later was sent to either model in this work.
- When this amendment was written the registered search had run (2026-10-03). Of its responses
  only work identifiers and counts had been read. No record had been screened, and no claim
  extracted.

## Files

| file | role |
|---|---|
| `prompts/luna_extraction_prompt.md` | sha256 `bf02041d287666f6104db8d756cbef3300ab50c8a9640c795b5cac39709b2f40`; revision `e4e4ee731887` (the study's revision formula with the model string `gpt-6-luna`) |
| `scripts/run_extraction_luna.py` | the Luna runner |
| `scripts/extraction_system_comparison.py` | usage totals and the comparison |
| `scripts/modal_extraction_system_comparison.py` | Modal wrapper |
| `scripts/dry_run_extraction_system_comparison_synthetic.py` | synthetic dry run, every quantity against a hand-worked value |
| `tests/test_run_extraction_luna.py`, `tests/test_extraction_system_comparison.py` | unit tests |

The prompt, the scripts and the tests are sealed in the results ledger when the amendment is
logged, before any Luna run.

**Maximum claim under this amendment.** For the abstracts of this census, the share of the
registered extraction's verified family–pair registry entries represented in the registry
derived from the tuned Luna extraction system, in one run and in run 1 completed by run 2; the
share of the Luna-derived entries the registered extraction holds; the agreement of the two
extraction systems on direction, null results and datasets among shared entries; the same
shares between two runs of each system; the H1 estimates and the H2 and H2b bounds computed
from the Luna-derived registries, with their differences from the registered estimates and no
threshold classification; and the cost of each extraction run per attempted abstract. Nothing
about which extraction is right, about how complete either is, about the effect of the model
apart from its prompt, or about any other model or prompt.
