# Prompt revisions

Development set: `dev_abstracts.jsonl`, 30 PubMed abstracts, every one first public before
2019-01-01 (earliest of issue, electronic article and PubMed entry dates; `fetch_dev_abstracts.py`
raises on any date on or after that day). Selected by title before any abstract was read:

| role | n | PMIDs |
|---|---|---|
| multi-protein pQTL study with disease links | 7 | 29875488, 28240269, 28369058, 30072576, 30111768, 29258991, 27989323 |
| MR of one or a few circulating proteins | 14 | 22421340, 22421339, 21325005, 25726324, 19509380, 25938632, 29728394, 29191953, 27882376, 27327646, 27225428, 26886630, 25350643, 24246360 |
| eQTL-only SMR | 2 | 27019110, 27506385 |
| pQTL discovery, no MR | 3 | 18464913, 23487758, 22595970 |
| review | 3 | 29226067, 29040597, 28569269 |
| gene-score MR, not protein levels | 1 | 27959767 |

DOIs are in `dev_abstracts.jsonl`. The development PMIDs and DOIs are listed here and in
`dev_abstracts.jsonl`, never in the prompt text the model receives.

Model: `gpt-6.1-sol` (Responses API, `reasoning.effort = "medium"`, no tools, `store: false`,
strict JSON-schema output). The API returns the model string `gpt-6.1-sol` and exposes no dated
snapshot; it rejects `temperature` and reports 1.0 applied. Every revision below ran on all 30
abstracts for both tasks (extraction also on ineligible abstracts, to exercise the schema).

Revision ids are the first 12 hex digits of sha256 over task, prompt text, schema, model and
reasoning effort (`run_extraction.revision_id`). The prompt and schema text of each revision are
kept beside its raw exchanges in `outputs/raw/sol/<task>/<revision>/`. Metrics per label are in
`outputs/dev_metrics/<label>.json`; all labels are scored with the final `verify_claims.py`.

## r1 — eligibility `eaaf2dc0f105`, extraction `d47b02ccde28`

First drafts.

| metric | eligibility | extraction |
|---|---|---|
| schema-valid, first attempt | 30/30 | 30/30 |
| eligible under the registered rule | 0/30 | — |
| claims | — | 71 |
| spans passing the registered quote check and `citations pin` | — | 71/71 |
| protein check pass | — | 67/71 |
| outcome check pass | — | 45/71 |
| claims entering the registry | — | 43/71 |
| directional claims: lexicon agrees / unverified / disagrees | — | 25 / 29 / 1 |

Defects read from the output: (1) background sentences extracted as claims (PMIDs 22421340,
27882376, 26886630: "A high circulating concentration of interleukin 6 is associated with...");
(2) a clinical description returned as ancestry ("individuals with multiple CVD risk factors",
28369058); (3) PMID 25350643 (serum vitamin D binding protein, rs2282679 instrument) scored as
not using circulating-protein instruments because the abstract names no matrix.

## r2 — eligibility `2bc87f34898a`, extraction `826f3bd1ebb9`

Eligibility: protein levels described as circulating, blood, plasma or serum, or measured in
participants with no tissue named, count as plasma or serum. Extraction: claims only from the
paper's own analyses, never background, prior studies or hypotheses; ancestry restricted to
ancestry, ethnicity or national population.

| metric | eligibility | extraction |
|---|---|---|
| schema-valid, first attempt | 30/30 | 30/30 |
| eligible under the registered rule | 0/30 | — |
| claims | — | 69 |
| spans passing both checks | — | 69/69 |
| protein check pass | — | 61/69 |
| outcome check pass | — | 45/69 |
| claims entering the registry | — | 40/69 |
| directional claims: agrees / unverified / disagrees | — | 21 / 29 / 0 |

Background claims gone; 25350643 now passes criterion 1. New defect: four claims of PMID
24246360 quote a span ("These results were similar to those for risk of cancer ...") that does
not name the protein, so the protein check fails.

## r3 — eligibility `2bc87f34898a` (unchanged), extraction `8723098b8018`

Extraction: the span must itself name the protein and the outcome in the words returned in
`protein_as_written` and `outcome_as_written`; a second sentence only when one does not hold both.

| metric | eligibility | extraction |
|---|---|---|
| schema-valid, first attempt | 30/30 | 30/30 |
| eligible under the registered rule | 0/30 | — |
| claims | — | 66 |
| spans passing both checks | — | 66/66 |
| protein check pass | — | 62/66 |
| outcome check pass | — | 42/66 |
| claims entering the registry | — | 40/66 |
| directional claims: agrees / unverified / disagrees | — | 22 / 29 / 0 |

`protein_not_in_span` is gone. The remaining protein failures are names with no HGNC entry
("phosphatase 1G", "IL-1α/β"). The outcome failures (23 unmapped, 1 not in span) are phrases the
label-and-exact-synonym route does not reach: measurement traits ("fasting glucose", "serum
albumin level"), composite or contrast outcomes ("CAD/MI", "high vs. low grade disease") and
outcomes that are themselves proteins ("CRP", "interleukin 6" as outcomes). These are mapping
gaps for the committed alias tables, not prompt defects.

r3 was the candidate for the freeze until r4.

## r4 — eligibility `2bc87f34898a` (unchanged, cached), extraction `63c728dcdc37`

Extraction: new field `evidence_type` (`mr_estimate`, `observational`, `experimental`,
`variant_association`, `other`); every protein–outcome result is extracted and labelled, and
only `mr_estimate` claims enter the registry. Direction: a non-significant estimate (printed
interval includes 1 for a ratio or 0 for a difference, or P >= 0.05 with no interval, or called
non-significant) is `null` whatever the side of its point estimate.

Verifier (same run, no model call): outcome mapping tries the committed alias table
`verification/outcome_aliases.csv` first (58 surfaces resolved against the pinned Mondo and EFO
by `scripts/build_outcome_aliases.py` from `verification/outcome_alias_seed.csv`: clinical
abbreviations and the r3 misses), then labels and EXACT synonyms, then RELATED synonyms; "log",
"circulating", "serum" and "plasma" are stripped as leading words. Direction is read by an
estimate parser that assigns the estimate printed nearest the outcome mention to the claim and
reads sign, ratio, interval and P value; the lexicon is the fallback.

| metric | r3 | r4 |
|---|---|---|
| schema-valid, first attempt (extraction) | 30/30 | 30/30 |
| eligible under the registered rule | 0/30 | 0/30 |
| claims | 66 | 76 |
| evidence type mr / observational / variant / experimental / other | — | 43 / 9 / 19 / 2 / 3 |
| spans passing both checks | 66/66 | 75/76 |
| protein check pass | 62/66 | 72/76 |
| outcome check pass | 42/66 | 70/76 |
| directional claims: agrees / unverified / disagrees | 22 / 29 / 0 | 52 / 5 / 2 |
| MR-estimate directional claims: agrees / unverified / disagrees | — | 36 / 4 / 0 |
| claims entering the registry | 40/66 | 37/76 (33 not `mr_estimate`) |
| of which enter direction-based results | 13 | 33 |
| cost, extraction exchanges of the revision (upper bound, USD) | 0.30 | 0.37 |

The failing span (PMID 19509380) joins two non-adjacent sentences; the quote check rejects it as
registered. The two direction disagreements are non-MR claims (observational CRP–depression, a
variant-level claim). The four unverified MR claims have no estimate assigned to the outcome
(a list "lipids or diabetes" with no estimate; "ORs were 1.12 and .98" with no way to tell the
genetic one; one span that failed the quote check). Remaining outcome misses: "high vs. low grade
disease", "low-grade inflammation", "lipids", "psoriatic osteoarthritis" (no named ontology
term; left unmapped rather than guessed) and "apolipoprotein E transcription".

r4 is the current candidate for the freeze.

## Verifier changes during development

`verify_claims.py` was revised twice while reading r2; the superseded outputs are kept in
`outputs/verification/sol_extraction_r2_826f3bd1ebb9/superseded_verifier_v{1,2}/`.

1. EFO obo writes ids as `efo:EFO_0004340`; they are now canonicalized to `EFO:0004340`
   (before, every EFO-only term was dropped). Outcome names are also tried with " measurement"
   appended. Protein mapping is tiered (approved symbol, then approved and UniProt names, then
   aliases and previous symbols), which cut multi-entry matches from 42 to 3.
2. Printed ratios are read only for a span supporting one claim; a span shared by claims of both
   `raises` and `lowers` is `direction_unverified`; "knockdown", "knock-down", "silencing" added
   as down cues; a matched key from Sol's own name counts for the span check, and a trailing
   " measurement" is ignored there.

## r5 — eligibility prompt only (revision d36485111906), 2026-09-30

Extraction prompt unchanged (r4). Changes, prompted by the r4 eligibility-only known-item check
(8 of 25 known items judged not eligible, 6 traced to the prompt):

1. Criterion 2 (`states_protein_outcome_result`) counts any stated result of the protein analysis
   on an outcome, including counts of significant protein–outcome pairs and null results; a named
   protein is no longer required.
2. `tissue_or_csf_proteomics` applies only when none of the proteins analysed are measured in
   plasma or serum; new boolean `also_tissue_or_csf` flags mixed-matrix papers. Criterion 1 is
   `yes` when at least some instrumented proteins are plasma or serum.
3. Criteria 1–3 answered `yes` / `no` / `uncertain` (schema enums); `scripts/apply_eligibility.py`
   returns `uncertain` when no criterion is `no`, no exclusion applies and any criterion is
   `uncertain`.

Results:

| set | r4 | r5 |
|---|---|---|
| 30 pre-2019 development abstracts | 0 eligible | 1 eligible (PMID 29875488, Sun 2018 Genomic atlas; abstract states MR evidence for "protein biomarkers" without naming one; count field 1,478 = proteins with pQTLs, not MR-tested; outside the window by date) |
| 25 known items | 15 eligible + 2 count_not_stated | 20 eligible + 3 count_not_stated + 1 uncertain; 1 not eligible (PMID 35300523, 90 proteins; count field returned 44, the number associated, not tested) |

Cost r5 (both runs): 79,107 input and 7,624 output tokens, about $0.23 at $2 / $10 per million.

## r6 — eligibility prompt only (revision c9264cb0ec34), 2026-09-30

Extraction prompt unchanged (r4). Change, prompted by r5 returning counts that were not the
number tested in MR (PMID 35300523: 44 associated of 90 tested; PMID 29875488: 1,478 with pQTLs):

1. `n_proteins_tested` holds a number only when the abstract states it as the number of proteins
   tested in the MR or other genetically proxied analysis; any other stated count (measured,
   assayed, with pQTLs, instrumented) goes to new fields `count_other` / `count_other_span`, and
   the tested count is null (`count_not_stated`). The 100 floor applies to the tested count only.
   Schema, `EligibilityOutput` and `apply_eligibility.py` (decisions now also record both counts)
   updated.

Known-item set reduced to 24: PMID 35300523 removed (90 proteins tested; genuine ineligibility).

Results:

| set | r5 | r6 |
|---|---|---|
| known items | 24 of 25 pass (20 eligible, 3 count_not_stated, 1 uncertain; 1 ineligible) | 24 of 24 pass (12 eligible, 11 count_not_stated, 1 uncertain) |
| 30 pre-2019 development abstracts | 1 eligible | 3 eligible_count_not_stated (29875488 count_other 1,478; 28369058 count_other 83; 30111768 count_other 71) |

Nine known items moved from eligible to `count_not_stated` because their stated number is now
read as measured or with pQTLs rather than tested. Two development abstracts (28369058, 30111768)
that r5 excluded as fewer than 100 proteins now pass, because their stated counts (83, 71) are
not stated as tested, so the floor no longer applies to them. Cost r6 (both runs, 54 calls):
85,892 input (60,526 cached) and 8,666 output tokens, about $0.26 at $2 / $10 per million.

## r7 — eligibility prompt only (revision 2811496ef424), 2026-09-30

Extraction prompt unchanged (r4). Change, prompted by PMID 36510323, whose r6 `count_other` of 58
was the number of proteins associated with phenotypes ("we identified a total of 58 CSF, 32
plasma, and nine brain proteins associated with 58, 44, and 16 phenotypes"), not a denominator:

1. `n_proteins_tested` means entered the MR analysis, not found significant; `count_other` holds
   only proteins measured, assayed, with pQTLs/instruments, or available for analysis. Neither
   field ever holds a count of proteins associated with, significant for, or causally linked to an
   outcome; with only such result counts both are null. Prompt items 4 and 5a and the schema
   field descriptions updated.

Results (deterministic floor rule applied by `apply_eligibility.py`):

| set | r6 (floor rule) | r7 |
|---|---|---|
| 24 known items | 23 pass (12 eligible, 10 count_not_stated, 1 uncertain); 1 ineligible (36510323) | 24 pass (12 eligible, 11 count_not_stated, 1 uncertain) |
| 30 pre-2019 development abstracts | 1 eligible (29875488) | 1 eligible (29875488, count_other 1,478) |

Only change against r6: 36510323 ineligible → eligible_count_not_stated (both counts now null,
flag `also_tissue_or_csf`). Cost r7 (both runs, 54 calls): 95,288 input (69,748 cached) and 8,523
output tokens, at most about $0.28 at $2 / $10 per million with cached input charged in full.

## r8 — extraction prompt (revision 0b97103cd7a4), 2026-09-30

Eligibility prompt unchanged (r7, `2811496ef424`; the r8 eligibility run was served from the
cache). Changes, from the round-4 review (`planning/perplexity_paper1_final/01_REVIEW_round4.md`):

1. Claim record per analysis context: repeated statements merge only when direction, dataset,
   ancestry, subgroup and analysis context are the same; distinct contexts give separate
   records. New fields `claim_scope`, `analysis_context_as_written`, `subgroup_as_written`,
   `dataset_attribution`, `relation_ambiguous`.
2. Cartesian guard: several proteins and outcomes in one sentence give every combination only
   when the wording applies each protein to each outcome or pairs them ("respectively");
   otherwise the record is flagged `relation_ambiguous` (kept out of the registry by the
   verifier).
3. Direction value `null` renamed `reported_nonsignificant_or_null`.
4. Lists: each name once, `not_stated` alone; the schema adds `minItems: 1` (accepted by the
   strict structured-output mode: 30 of 30 schema-valid at the first attempt) and the response
   validator rejects repeated names.

Metrics (`outputs/dev_metrics/r4.json`, `r8.json`; both scored with the final verifier and the
registered reference files):

| metric | r4 | r8 |
|---|---|---|
| schema-valid, first attempt (extraction) | 30/30 | 30/30 |
| claim records | 76 | 141 |
| evidence type mr / observational / variant / experimental / other | 43 / 9 / 19 / 2 / 3 | 77 / 20 / 41 / 2 / 1 |
| claim scope overall / dataset / ancestry / subgroup / sensitivity | — | 95 / 13 / 2 / 3 / 28 |
| dataset attribution whole study / claim specific / unclear | — | 124 / 13 / 4 |
| relation_ambiguous | — | 0 |
| spans passing both checks | 75/76 | 129/141 |
| protein check pass | 72/76 | 137/141 |
| outcome check pass | 70/76 | 124/141 |
| directional records: agrees / unverified / disagrees | 52 / 5 / 2 | 64 / 23 / 20 |
| MR-estimate directional records: agrees / unverified / disagrees | 36 / 4 / 0 | 45 / 13 / 9 |
| records entering the registry | 37 | 63 |
| of which enter direction-based results | 33 | 43 |
| cost, extraction exchanges of the revision (upper bound, USD) | 0.37 | 0.66 |

"Directional" counts every record whose direction is not `not_stated`. The nine MR disagreements
are all PMID 27327646: heterogeneity-adjusted sensitivity records whose spans quote the
main-analysis sentence, where the verifier reads the main estimate. The twelve failing spans (PMIDs
19509380, 25938632, 24246360) join two sentences that are each in the abstract but not
adjacent. The rise in records is the context split: 27327646 alone went from 14 to 33 records.

## Verifier changes during round 4

1. Registered reference files (HGNC 2026-09-04, UniProt 2026_03 `620d646a96c0`, MONDO
   v2026-09-01, EFO v3.93.0), re-hashed before use; the r4 outputs re-scored under them give the
   same per-claim results as under EFO v3.94.0 and the three-column UniProt file.
2. Set-valued dataset mapping (`scripts/dataset_relations.py`) replaces the alias lookup; every
   record carries its mapping provenance.
3. `relation_ambiguous` records fail; outputs before r8 are read with `null` renamed and the r8
   fields marked `not_in_revision`.
4. A full-text table row is read cell by header, and the "95% CI" label is masked before scale
   cues are read (it was read as a percentage unit, making hazard ratios differences). Neither
   change alters any r4 or r8 result.

Superseded outputs: `outputs/verification/<run>/superseded_*` and `outputs/superseded/`.

## Full-text prompt ft1 (revision 5fb585754e99), 2026-09-30

`prompts/fulltext_extraction_prompt.md`, schema `fulltext_extraction`: the r8 definitions and
fields, with full-text instructions (Results, tables and the Discussion's statements of the
paper's own findings; one record per table row and outcome; context from captions and headers),
spans that are sentences of one paragraph line or a whole table row line, and three added
fields (`source_location`, `colocalization`, `replication`). Text rendered by
`scripts/fetch_fulltext.py` from the Europe PMC open-access XML, abstract and supplements
excluded.

Development test on one pre-2019 open-access paper, PMID 30111768 (Yao et al. 2018, Nat Commun,
PMC6093935, 8,514 words; `prompts/dev_fulltext.jsonl`; `outputs/dev_metrics/ft1.json`): 45
records (26 from Table 2, 10 from Table 1, 9 from the text), 45 of 45 spans pinned; evidence
type observational 26, variant 10, MR 6, other 3; 6 records enter the registry. Directional
records: 27 agree, 1 unverified, 1 disagrees (an MR sentence, "lower BCHE to be causal for CHD",
where the lexicon reads the cue words the other way). No record reports colocalization or
replication. Cost 17,071 input and 13,559 output tokens, at most USD 0.17.
