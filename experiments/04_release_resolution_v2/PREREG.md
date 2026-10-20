# With a positive control screened before coding, how much release identity do full texts and supplements recover for repeated protein–outcome claims?

Sections use the [OSF Preregistration](https://osf.io/prereg/) question titles verbatim. A question
that does not apply is answered **N/A** with the reason.

This is the second registration of the release-resolution follow-up of Paper 1 of
`proteome-mr-claim-audit` (`experiments/02_claims_meta/PREREG.md`, https://osf.io/zae8c). The first
registration is `experiments/03_release_resolution/PREREG.md` (frozen 10 October 2026,
https://osf.io/2s479), with Amendments 1 to 7 and Deviations 1 and 2 in that folder, called **the
first registration** below. Its stage A was coded, its positive control failed, and its log entry
of 20 October 2026 (commit 3ed2c7567) treats every coding-dependent estimate as void, as
registered.

Every definition, rule, model, prompt, schema, check, threshold, ceiling rule and procedure of the
first registration as amended carries over unchanged, except the five changes of §Study design.
Where this file is silent, the first registration governs. Every seed is replaced (§Randomization).

## Research questions or hypotheses

The questions are those of the first registration. The hypotheses keep its definitions; their
labels there are given in brackets.

**H1.** [H2-R] Among Paper 1's 245 repeated pairs, more than half are `known_identical` under the
primary rules.

**H2.** [H2b-R] Among the same pairs, more than half are `known_overlapping`.

**H3.** [H1-R] The proportion of pairs whose `independent` edges all join families of the same
direction, estimated without a verdict.

**H4.** [C1] The coding pipeline recovers, on accepted codes, the expected dictionary row of hard
identifiers that the source attributes to the dataset of the control's own side, at a rate of at
least 0.90 with contradiction at most 0.02, on at least 50 controls.

**H5.** [manifest check] The gate's mapping functions return the expected dictionary row for each
of the 31 manifest accessions.

H1 carries the design. H4 and H5 gate H1 to H3: without them, a rise in resolved pairs is
consistent with a pipeline that misreads or mis-maps the identifiers it finds.

Two registered outcomes would strengthen the papers under examination, as in the first
registration: a contradicted H1, and a high `confirmed` share among abstract-to-full-text
transitions.

## Foreknowledge of data or evidence

Authors have observed the data, but have not performed the proposed analyses

## Explanation of foreknowledge and managing unintended influences

Everything the first registration and its amendments state as seen is seen. In addition, under
the first registration, by 20 October 2026:

- **Retrieval, cut and costs.** All counts in `PREREG.log` of the first registration: retrieval,
  seven cut calibrations, the amended cut, the cost estimates and pricings.
- **SA1.** Coded, gated, judged and routed; the author marked 42 SA1 rows on assisted pages and read
  their abstracts; the judges' calibration scored 4 of 20 on disagreement adjudication (failed)
  and 20 of 20 on agreement audit (passed); the calibration diagnostic, the attribution states and
  reasons of the 16 differing rows, and the author's reasons on his 42 marks were read.
- **Stage A counts.** Both models coded all 266 packets and 31 manifest packets. Study rows: 657,
  agree 510, differ 147. Control rows: 70, agree 45, differ 25. Gate failures: Claude 64 study and
  9 control rows, Sol 55 and 5. C1-A on raw answers: Claude 49 of 70, Sol 53 of 70, both 47,
  at least one 55; contradiction 0. Manifest: 10 of 31 per model, 3 by both, at least one 17;
  contradiction 0. Spend under the first registration: 86.09 US dollars.
- **Control diagnostic** (`outputs/stage_a_control_diagnostic_2026-10-14.json`). Every expected
  identifier stands in its packet. Of the 23 C1-A controls not recovered by both models: 9 carry
  an identifier the source attributes to something other than the claim's dataset (an exposure, a
  meta-analysis component, a combined FinnGen and UK Biobank meta-analysis, a secondary analysis);
  5 are a DOI or PMID written inline (a table cell, a data-availability sentence) that both models
  coded to the expected row and the gate rejected for want of a reference entry; 9 are coder
  misses, quotations not verbatim, or sources giving two identifiers for one outcome. Manifest
  packets carry no title, abstract or claim, so D1 attribution is impossible in them. The
  diagnostic lists, per model, the row ids of the recovered controls; these lists were read while
  drafting this registration. The agent that ran the diagnostic read each control's source context
  and the models' reason codes and quotations for the control rows.
- **Validity marks** (`outputs/c1a_control_validity_2026-10-14.json`, prompt
  `prompts/control_validity_prompt_v1.md`, sha256
  b451722be37ca8ddea41ffa777c7d6d8be17207d6cb2e7318bbe44ceb7eeadfa). Of 70 controls: 22 valid by
  both judges, 34 invalid by both, 14 disputed (one or both `cannot_mark`; no valid against
  invalid). By judge: Claude Fable 5.1 28 valid, 37 invalid, 5 `cannot_mark`; GPT-6 Astra 23, 34,
  13. The per-control marks and reasons are stored; whether anyone read them by control is not
  recorded, so they are treated as seen.
- **Mapping script** (`outputs/manifest_mapping_check_2026-10-14.json`): 31 of 31 under the first
  registration's gate.
- **Candidate count before the freeze** (`experiments/04_release_resolution_v2/outputs/candidate_count_2026-10-19.json`, by `scripts/candidate_count_v1.py`),
  counts only, given under §Sample size: the frozen scanner over the full texts stored for Paper 1
  of 117 records outside the scope. No candidate's text, context or mark has been seen.

Not seen: no stage A study-row answer has been read for content; no judge has run on stage A; no
stage A row has been adjudicated; no estimand, yield or transition has been computed under either
registration; no candidate from a record outside the scope has been read or marked.

What this costs: the eligibility rule (both judges valid; disputed and `cannot_mark` excluded) was
chosen after the first registration's minimum was missed on the rule that retained disputed
controls, and the inline-identifier rule after 5 controls failed on it. Both rules are fixed in
this preregistration and apply only to candidates no one has read or marked. The 70 controls of
the first registration and their marks are not used. The estimates of this preregistration are
reported as a second registration made after the first failed, beside the first's failure, never
as the first's results.

What limits the influence: the controls come only from records outside the scope, none of whose
candidates has been read or marked; eligibility is decided by the judges' marks alone, never by
recovery; every control is drawn and frozen before any coding request of this preregistration;
stage A is coded again from scratch and no answer from the first registration's stage A enters any
estimate or check; the remaining safeguards of the first registration apply.

## Study type

Non-randomized study
Descriptive study

## Intention for causal interpretation

No causal relationship inferred

## Blinding of experimental treatments

No blinding is involved.

## Additional blinding during research or analysis

As in the first registration. Judges marking validity see no coder answer, recovery status or
diagnostic, and not each other's mark. The author, who has seen the diagnostic, marks no control.
The validity judges are also the adjudication judges of Amendment 4; adjudication and audit
packets carry no validity mark.

## Study design

As in the first registration, with these changes only.

**1. Control set, built and screened before any coding.**

- **Records.** Only the 468 records of Paper 1's amended primary corpus (734 records with claims)
  outside the 266 of the scope, the extension the first registration provides (§Study design, C1).
  The scope's 70 candidates and their frozen validity marks are not used.
- **Retrieval.** Before any candidate is marked, every one of the 468 records is retrieved by
  routes R1 and R3 under the first registration's retrieval rules, unchanged, with R2 not
  requested: the 351 with no stored full text, and the 117 whose full text is stored for Paper 1,
  which is eligible under R1 as the first registration states.
- **Candidates.** The frozen scanner (`scripts/source_scanner_v2.py`, patterns
  `reference/c1_scanner_patterns_v2.json`, units by `scripts/c1_controls.py`, all unchanged) over
  the retrieved texts, one candidate per record and identifier as in Amendment 2, item 3.
- **Marks.** Every candidate is marked by the two judges of Amendment 4 (`claude-fable-5-1`,
  `gpt-6-astra`) under the frozen validity prompt v1 and schema v1, with the packet, attempts and
  blinding of Deviation 2, item 2. A packet's claims are the record's Paper 1 claim records
  (protein, outcome and direction from the first claim check of each).
- **Eligibility**, fixed here before any candidate is marked. A candidate is eligible only when
  both judges mark it valid. Disputed, `cannot_mark`, invalid and failed-twice candidates are
  excluded.
- **Draw.** Eligible candidates in sorted order of row id, shuffled by
  `random.Random(20261033).shuffle`, taken in that order, at most 5 per record and 150 in all.
- **Minimum.** If fewer than 50 candidates are eligible, stage A does not run, and the paper
  reports the stop and the counts.
- **Packets.** Scope packets are the frozen stage A packets (volume manifest sha256
  fef6b59516082495b62c2233659661f325fb602d29020a66168db29bb93aa7ed) with their 70 control rows
  removed; they carry study rows only, with files unchanged. Control rows appear only in packets
  of records outside the scope, and only a record outside the scope with a drawn control gets a
  packet; the other records outside the scope are retrieved, scanned and marked, and are not
  coded. Such a packet holds the record's abstract and R1 and R3 full texts, its rows built by
  the frozen queue rule from its Paper 1 claim records (coded, entering no index), and its control
  rows, so that control rows stay indistinguishable from study rows. Control rows are built as in
  Amendment 2, item 3. The sha256 of every rebuilt and new packet is logged before any coding
  request.

**2. Gate: inline source identifiers under D2** (primary rule). D2 also accepts a DOI or PMID
written in the paper's own text (a table cell, a data-availability or key-resources statement)
and attributed there to the analyzed dataset, with no reference entry. The gate passes such a D2
passage when its quote holds the DOI or PMID, the quote stands outside a reference list (as
`c1_controls.units` marks it), and Paper 1's reference check verifies the identifier against the
coded row's `source_identifier`; every other gate condition is unchanged. Attribution is checked,
as for any D2 passage, by the coders, the judges and the author, not by the script. Deviation 2's
inline sensitivity analysis is superseded.

The coding prompt v2 conditions D2 on a reference entry ("the reference entry resolves to one
bibliographic record ... Give the reference entry as a second passage"), so a coder that follows
it leaves an inline identifier unidentified. Coding prompt v3 (`prompts/coding_prompt_v3.md`,
sha256 logged before the freeze) is v2 with that bullet replaced by:

> - A citation identifies a release only when the passage explicitly attributes the analysed
>   dataset to it and its identifier is the source identifier of exactly one dictionary row. The
>   identifier is the DOI, else the PMID, else the PMC identifier of the reference entry the
>   passage cites, when that entry resolves to one bibliographic record; or a DOI or PMID written
>   in the paper's own text (a table cell, a data-availability or key-resources statement) and
>   attributed there to the analysed dataset. If the cited source has several dictionary rows, the
>   citation identifies one of them only with an attribute of the same analysed dataset in the
>   same passage that matches exactly one (ancestry, subcohort, panel, platform), with no conflict.
>   A citation of a general cohort description identifies no release. Give the reference entry,
>   when there is one, as a second passage with rule `D2_reference_entry`; an identifier written
>   in the text is quoted in the D2 passage itself.

Nothing else in the prompt, the schema or the API framing changes.

**3. Manifest check.** The mapping script of Deviation 2, item 3, run with the functions of the
gate of item 2 on the 31 manifest accessions, must return the expected row for all 31. The coded
manifest packets are not run.

**4. Stage A coded again.** Both coders (`claude-sonnet-5-5`, `gpt-6.1-sol`) code every packet of
item 1 from scratch under prompt v3 and the gate of item 2. No answer, gate verdict or count from
the first registration's stage A is used. The following carry over by reference: the judges of
Amendments 3 and 4, the settling rule of Amendment 7, routing, calibration and its consequences,
the assisted author pages of Amendment 5, stage B and its cost rule (Amendment 2), the removed-chunk
diagnostic (Amendment 1), the levels and recovery pass (Amendment 6). SA1's abstract-only codes (B)
were made under the first registration and are void with it; SA1 reports A, C and the A-to-C
contrast.

**5. C1 thresholds.** Unchanged: recovery at least 0.90 and contradiction at most 0.02 on at
least 50 drawn controls, on accepted codes. Recovered means coded to exactly the expected row with
the gate passing.

## Randomization

N/A — nothing is assigned; every seeded draw uses a new seed, listed here:

| draw | first registration | this registration |
|---|---|---|
| control draw | 20261011 | 20261033 |
| send order of validity packets | 20261032 | 20261034 |
| answer order on disagreement pages and judge requests | 20261017 | 20261035 |
| audit sample of agreements (10%, at least 30) | none for stage A | 20261036 |
| judge send order | 20261028 | 20261037 |
| stage A calibration: disagreement, audit, escalated review | 20261021, 20261022, 20261023 | 20261038, 20261039, 20261040 |
| author page order | 20261027 | 20261041 |
| stage B resolved-record audit | 20261015 | 20261042 |
| stage B calibration: disagreement, audit, escalated review | 20261024, 20261025, 20261026 | 20261043, 20261044, 20261045 |
| removed-chunk diagnostic rounds | 20261012, 20261013, 20261014 | 20261046, 20261047, 20261048 |
| recovery: author check, trial, order | 20261029, 20261030, 20261031 | 20261049, 20261050, 20261051 |

## Data collection procedures

As in the first registration. New script versions (retrieval without R2, validity packets for
records outside the scope, the draw, packets, gate, mapping check) are tested and sealed before
they run; each step is logged with `prereg log` before it runs. Order: freeze and register;
retrieve all 468 records outside the scope; scan; build and freeze the validity packets; mark every
candidate; draw and freeze the control set, or stop if fewer than 50 are eligible; mapping check;
build packets; write the cost estimate and stop for the author's approval; code stage A; then the
first registration's order from the gate onward. Retrieval, scanning and marking run whatever the
number of candidates turns out to be.

**Cost.** One ledger with the first registration's (86.09 US dollars spent). The ceiling for this
registration's validity marks, stage A coding and its checks is 300 US dollars of new spend. In
Amendment 2's stage B rule, "the spend of stage A and SA1" reads as the new spend of this
registration.

## Data collection procedures - File upload

N/A — no file beyond the repository.

## Sample size

The corpus is unchanged: 266 papers, 245 repeated pairs, 657 study rows.

Controls. Of the 468 records outside the scope, 117 have a full text stored for Paper 1. The
frozen scanner, run on those texts before this preregistration (counts only; no candidate text,
context or mark seen), finds 54 candidates in 31 records, 0.46 per record (54 of 117); 52 after
the cap of 5 per record. They are 51 outcome-side and 3 pQTL-side; 35 FinnGen numbered releases,
13 OpenGWAS and 1 GWAS Catalog accessions, 3 PMIDs and 2 DOIs; 12 expected rows. The other 351
records have not been retrieved.

Projection, not a measurement. In the first registration 22 of 70 candidates were marked valid by
both judges (Wilson 95% interval 0.22 to 0.43). If all 351 records yield a full text at 0.46
candidates each, the 468 give 216 candidates and 68 eligible at 22 of 70; if they yield full texts
at the scope's rate (204 of 266 records), 178 candidates and 56 eligible. At the lower end of the
interval these become 47 and 39. The expected eligible count is near 50, and the stage may not
run. Retrieval of the 351 records and the marking of every candidate happen regardless. If fewer
than 50 candidates are eligible, stage A does not run, and the stop and the counts are reported.

## Sample size rationale

The corpus is fixed; the control minimum of 50 is the first registration's.

## Starting and stopping rules

The stage starts after the freeze. Retrieval of the 468 records and the marking of every
candidate run in full. If fewer than 50 candidates are eligible, the stage stops before any coding
request. Otherwise as in the first registration.

## Manipulated variables

N/A — nothing is manipulated.

## Measured variables

As in the first registration, and per candidate: record, retrieval route, identifier type,
expected row, each judge's mark and reason, eligibility, and whether it was drawn.

## Measured variables - File upload

N/A — none.

## Indices

As in the first registration, with C1 computed on the drawn controls of item 1. C1 recovery and
contradiction are reported overall and, beside it, by identifier type (numbered release;
accession; source identifier, DOI or PMID), with the number of controls of each type. Added
counts: records retrieved by route; candidates; marks per judge; eligible and drawn; drawn
controls recovered through the inline D2 rule; study rows resolved through it.

## Indices - File upload

N/A — none.

## Statistical models

N/A — none beyond the first registration's.

## Statistical models - File upload

N/A — none.

## Transformations

N/A — none beyond the first registration's.

## Inference criteria

| hypothesis | holds when |
|---|---|
| H1 supported | LB > 0.5 |
| H1 contradicted | UB ≤ 0.5 |
| H2 supported | LB_b > 0.5 |
| H2 contradicted | UB_b ≤ 0.5 |
| H3 | no verdict; estimate with Wilson interval |
| H4 | recovery ≥ 0.90 and contradiction ≤ 0.02 on ≥ 50 drawn controls, accepted codes |
| H5 | 31 of 31 accessions return the expected row |

H1 and H2 are unresolved when neither condition holds.

**The stage does not run if fewer than 50 candidates are eligible.**

**H1 to H3, the yields, the transitions and the coding-dependent secondary analyses are void if
H4 or H5 fails.**

**No answer from the first registration's stage A enters any estimate or check.**

What stands when they are void is what the first registration lists.

## Data inclusion and exclusion

As in the first registration. Candidates are excluded from the control set only by the
eligibility rule of item 1.

## Missing data

As in the first registration.

## Other planned analysis

As in the first registration as amended, with SA1 as in item 4 and Deviation 2's analyses
superseded by items 1 to 3.

## Context and additional information

Registered on OSF as a registration of its own, linked to https://osf.io/2s479 and
https://osf.io/zae8c. The paper reports the first registration's control failure (raw C1-A at
most 55 of 70, manifest at most 17 of 31, 36 valid controls under Deviation 2) beside this
registration's results.

**Maximum claim under this registration.** If at least 50 candidates are eligible and H4 and H5
hold, the paper can state what the first registration's Maximum claim allows, as amended by
Amendments 1 to 7, with three changes. First, the estimates come from a second registration, made
after the first registration's positive control failed and its estimates were void, and that
failure is reported beside them. Second, the positive control is recovery of hard identifiers on
controls drawn only from Paper 1's papers outside the scope, which two judges marked, before
coding, as attributed to the dataset of the claim's own side; it tests extraction and mapping of
attributed identifiers by the same rules and models on those papers, with the result reported
overall and by identifier type, and says nothing about identifiers the judges marked invalid or
disputed. Third, a DOI or PMID written in the paper's own text and attributed there to the
analyzed dataset is decisive under D2. It cannot state that the first registration's estimates
hold, that the pipeline passed an unscreened control set, that the judges' marks are correct,
that the controls test the reading of the scope's own papers, or that a pass validates the extraction of an
identifier type represented by few controls. If fewer than 50 candidates are eligible, or H4 or H5
fails, it can state what the first registration says stands when C1 fails, the counts of records
retrieved, candidates, marks and eligible controls, and the stop or the failure.
