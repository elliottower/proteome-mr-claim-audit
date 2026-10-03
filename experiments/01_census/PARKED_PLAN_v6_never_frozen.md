# What evidence do published proteome-wide MR drug-target studies report for their claims?

**Status:** DRAFT — not frozen.

Sections use the [OSF Preregistration](https://osf.io/prereg/) question titles verbatim, so
this maps onto a registration without being rewritten. A question that does not apply is
answered **N/A** with the reason, never deleted.

This registration covers Phase 1 only: a census of proteome-wide Mendelian randomization (MR)
papers identified by the registered sources and procedures, the claims they make, and the
claim frame for the later re-analysis audit. The re-analysis (colocalization, cohort
and platform replication, overlap and direction checks) is registered separately, before any
claim is re-run.

## Research questions or hypotheses

What do proteome-wide MR papers claim about proteins as causes of disease or as drug targets,
and what evidence do they report alongside each claim?

The census is descriptive. Its registered outcomes are the proportions listed under §Indices.
Two co-primary descriptive hypotheses are registered on top of them, with no familywise claim.

**H1.** The prevalence of claim-specific colocalization reporting for at least one headline
claim is higher among papers first publicly available in 2024–2025 than among papers first
publicly available in 2019–2022.

**H2.** Among eligible papers using UK Biobank Pharma Proteomics Project (UKB-PPP) pQTLs
(`uses_ukbppp`), the proportion that state, for every outcome GWAS they use, whether it
includes UK Biobank participants (paper-level `ukb_inclusion_paper_status` = `all_include`,
`all_exclude` or `mixed`) is below 0.50.

H1 is the registered outcome favorable to the field; H2 is the outcome that counts against it.
H1 is a temporal contrast and is not interpreted as an effect of UKB-PPP publication or of
published methodological critiques.

## Foreknowledge of data or evidence

Read before this document was written:

1. The Perplexity report `planning/source_reports/perplexity_report_2026-09-30.md` and the
   passages it quotes, including its scoop verdict that no systematic claim-level re-analysis
   of published proteome-wide MR claims exists.
2. The general-MR reporting audit that report cites (BMJ Evidence-Based Medicine 2023, 116 UK
   Biobank MR papers), including its figures: overall reporting completeness 55%, multiple
   testing addressed 17%, complete code 11%.
3. The critiques of mass-produced MR: Stender, Gellert-Kristensen and Davey Smith 2024;
   Munafò, Brown, Hefler and Davey Smith 2024.
4. Cross-platform pQTL comparisons: Pietzner et al. 2021, Sun et al. 2023, Eldjarn et al.
   2023, Katz et al. 2022, and their replication figures.
5. The author's own work: a 143-pair cis-pQTL MR pilot evaluated against Phase III outcomes
   (`pqtl-mr-domain-of-validity`) and the V8 registration in that repository, which built the
   colocalization and harmonization design the later audit will reuse.
6. An unknown number of individual proteome-wide MR papers, read over 2025–2026 in the course
   of that work. None was read with the extraction form below, and no count of any census
   field has been made.
7. An independent verification of item 1 (`docs/source_verification/`), which
   read in full the MR re-analysis and appraisal literature it found, including Nguyen, Terry
   and Guggenheim 2025, Liu et al. 2025 (MR-KG), Yang et al. 2025 and Sobczyk et al. 2023,
   and which found three cross-platform figures in the Perplexity report attributed to the wrong
   source. None of these figures enters this registration.
8. A second Perplexity review of an earlier draft of this document
   (`planning/perplexity_census_review/01_REVIEW_full.md`), which quotes individual
   proteome-wide MR papers for their protein counts: Chen L et al. 2022, Nat Commun (308
   proteins) and Yoshikawa et al. 2024 (735 proteins). No other census field of those papers was
   read.
9. Woolf et al. 2022 (IJE, PMC9749715), a preregistered reporting audit of 87 two-sample MR
   studies, which reported the sample-overlap item in fewer than 40% of studies, analysis code
   in fewer than 10%, and multiple-testing correction in just under half.
10. A check of the references in item 8 (`planning/perplexity_census_review/references/`),
    which read studies validating model-assisted screening and extraction against human
    reviewers (Khan et al. 2025, Gartlehner et al. 2025, Oami et al. 2026, Clark et al. 2025,
    Chen et al. 2026) and two reviews of drug-target MR (Nibali et al. 2026, Fan et al. 2024).
11. PubMed result counts for the registered queries, run 2026-09-30 for 2020-01-01 to
    2025-12-31, counts only, with no title, abstract or other record content read
    (`docs/feasibility/query_counts_2026-09-30.json`,
    `docs/feasibility/query_union_counts_2026-09-30.json`): Q1 1,309; Q2 332; Q3 as first
    drafted, without the GEN block, 6,590, of which 5,748 retrieved by no other query; Q3 with
    the GEN block 814; union of Q1, Q2, Q4 and the GEN-restricted Q3, 2,089. These counts led to
    the GEN block in Q3. The confirmatory window has since moved to 2019-01-01 (item 12); no
   count for the 2019 records has been run.
12. While the development set was built, the first public date (bioRxiv, 2019-05-05) and the
    number of proteins tested in MR (1,002) of Zheng et al. 2020 (Nat Genet,
    10.1038/s41588-020-0682-6) were read; no other census field of that paper was read or coded.
    With the window starting 2019-01-01 that paper is census-eligible, and it was removed from
    the development set.

No search in §Data collection procedures has been run, and no paper has been screened or
extracted.

## Explanation of foreknowledge and managing unintended influences

Items 2–4 and 9 anchor the expectation behind H2, and items 2–4 motivate H1. Both hypotheses were written after
reading them and are stated as directional predictions only. Every eligibility, headline-claim
and extraction rule below is applied by a fixed prompt or script, not by the author's judgment
of which papers or claims look weak. The author adjudicates disagreements and verifies
exclusions from the full text, and each decision is logged with its evidence. Items 6, 8, 11 and 12
cannot be undone; the census covers every eligible record retrieved, so familiarity cannot
select which papers enter. Papers already encountered may enter the known-item set
(§Data collection procedures), which is used only to test search recall.

The start of the confirmatory window, 2019-01-01, was set before any search was run or any
paper coded, and it was moved from 2020-01-01 so that Zheng et al. 2020 (first public
2019-05-05) enters the census (item 12). The date is a scope decision taken with that paper
known, not a boundary chosen independently of the literature; its substantive reason is that
high-throughput proteome-wide MR first appears in 2019. A registered sensitivity table
(§Other planned analysis) reports every census outcome for first public 2020–2025.

## Study type

Observational: a meta-research census of published literature.

## Intention for causal interpretation

N/A — the census describes reporting; no causal claim is made.

## Blinding of experimental treatments

N/A — no treatment is assigned.

## Additional blinding during research or analysis

Claude Code extracts its check sample without access to the OpenAI output. The screening
check sample, the Claude Code check sample and the validation sample are drawn before any
aggregate proportion is computed. No census proportion is computed until extraction,
adjudication and validation of every eligible paper are complete and committed. The audit frame
is taken from the committed census file, with every claim identifier frozen.

## Study design

Six stages, each committed before the next begins:

0. **Before the freeze.** The known-item set, the self-PRESS checklist, the development set
   with the author's development labels, the census and reconstruction prompts and their JSON
   schemas, the coding manual, the outcome decisions table, the field acceptance thresholds and
   the analysis scripts are committed. The freeze commit follows.
1. **Search.** The registered queries run on each source on one day, within 14 days after the
   freeze commit. Citation chasing follows (§Data collection procedures). Raw responses,
   result counts, timestamps and checksums are committed.
2. **Screening.** The keyword rule, then the OpenAI model on title and abstract, then full-text
   eligibility, with the checks in §Data collection procedures.
3. **Census extraction.** The OpenAI model fills the census extraction form (§Measured
   variables) for every eligible paper, outcome GWAS and claim; the Claude Code check sample and
   the validation sample are then drawn and checked.
4. **Reconstruction extraction.** A second pass by the same registered model, with its own
   committed prompt and schema, records the reconstruction fields (§Measured variables) for
   every `interpreted_causal` and `interpreted_target` claim, one row per claim and instrument
   variant. It runs after the census pass is committed and is validated separately.
5. **Audit frame.** Every `interpreted_causal` and `interpreted_target` claim in the committed
   census, with its identifiers frozen, is passed to the audit registration.

**Dates.** A paper's date is its first public appearance, assigned mechanically in this order:
(1) the earliest public version that contains the eligible analysis; (2) a preprint's version 1
only if version 1 already contains it; (3) otherwise the journal online-first date; (4)
otherwise the issue date. Corrections and later preprint versions do not reset the date; when a
preprint adds the qualifying proteome-wide analysis in a later version, the date is that
version's. The issue date is recorded separately. The confirmatory
census covers first public dates 2019-01-01 to 2025-12-31. Papers first public from 2026-01-01
to the search date form a separate update set, reported apart and excluded from H1, H2 and the
audit frame.

**Study families.** A preprint and its journal version, or several reports of one analysis,
form one study family, dated by its earliest public appearance; the journal version is the
canonical record for extraction when its full text is accessible. Candidate families are
generated by script from DOI, PMID, PMCID and preprint links and explicit supersession
statements, then by fuzzy matching: title token-set ratio ≥ 0.8, or a shared first or last
author together with the same pQTL source and outcome. The author adjudicates every fuzzy
candidate from both records; both records are preserved, and every match is logged with its
rule. Matching datasets alone never merge two papers. A correction or erratum notice is a member
of its article's family and is not extracted separately.

## Randomization

Three samples are drawn at random within strata: the Claude Code check sample (seed
`20260930`), the screening check sample (seed `20260931`) and the validation sample (seed
`20260932`). Nothing else is randomized.

## Data collection procedures

**Sources.** PubMed; Europe PMC (covering medRxiv and bioRxiv); OpenAlex. Embase, Web of Science
and Scopus: N/A — no institutional access. OpenAlex requests carry no email address or other
personal identifier.

**Query architecture.** Four queries per source; none requires therapeutic language, which is
an eligibility decision made from full text. PubMed text is given here. The Europe PMC and
OpenAlex versions are block-for-block translations committed in `search/queries.md` before the
freeze. `SEARCH_DATE` is the date the search runs, recorded in the committed output.

Shared blocks:

```text
MR     = "Mendelian Randomization Analysis"[Mesh] OR "Mendelian randomization"[tiab]
         OR "Mendelian randomisation"[tiab]
PROT   = proteome-wide[tiab] OR "proteome wide"[tiab] OR protein-wide[tiab]
         OR proteomic*[tiab] OR "plasma proteom*"[tiab] OR "circulating proteom*"[tiab]
         OR "plasma protein*"[tiab] OR "serum protein*"[tiab] OR "circulating protein*"[tiab]
         OR pQTL[tiab] OR pQTLs[tiab] OR "protein quantitative trait*"[tiab]
         OR "protein QTL*"[tiab] OR "genetically proxied protein*"[tiab]
         OR "genetically predicted protein*"[tiab]
         OR "genetically predicted plasma protein*"[tiab]
PLAT   = SomaScan[tiab] OR SomaLogic[tiab] OR Olink[tiab] OR Fenland[tiab] OR "UKB-PPP"[tiab]
         OR "UK Biobank Pharma Proteomics"[tiab] OR deCODE[tiab] OR SCALLOP[tiab]
         OR "INTERVAL study"[tiab] OR ARIC[tiab]
TARGET = "drug target*"[tiab] OR "therapeutic target*"[tiab] OR druggable[tiab]
         OR repurpos*[tiab] OR "target prioriti*"[tiab] OR "therapeutic prioriti*"[tiab]
         OR "drug-target MR"[tiab]
LOCUS  = "summary-data-based Mendelian randomization"[tiab] OR SMR[tiab] OR colocali*[tiab]
         OR "cis-MR"[tiab] OR "cis Mendelian randomization"[tiab]
PQTLB  = pQTL[tiab] OR pQTLs[tiab] OR "protein quantitative trait*"[tiab] OR "protein QTL*"[tiab]
         OR "plasma protein*"[tiab] OR proteom*[tiab]
GEN    = (MR) OR pQTL[tiab] OR pQTLs[tiab] OR "protein quantitative trait*"[tiab]
         OR "genetically predicted"[tiab] OR "genetically proxied"[tiab] OR "cis-MR"[tiab]
DATE   = "2019/01/01"[dp] : "2025/12/31"[dp]
UPDATE = "2026/01/01"[dp] : "SEARCH_DATE"[dp]
```

Queries: **Q1** `(MR) AND (PROT) AND DATE`; **Q2** `(MR) AND (PLAT) AND DATE`;
**Q3** `(TARGET) AND (PQTLB) AND (GEN) AND DATE`; **Q4** `(LOCUS) AND (PQTLB) AND DATE`. SMR
appears only in Q4, combined with protein terms. The update set runs the same four queries with
UPDATE in place of DATE.

The union across queries and sources, deduplicated by PMID, PMCID and DOI, is the screening
set. Source-specific and query-specific yields are reported.

**Citation chasing.** Backward (references) and forward (citing works) citations of every
included paper are retrieved from OpenAlex and screened by the same procedure. Chasing repeats
from newly included papers until a round adds no eligible paper, to a maximum of three rounds.

**Search validation.** Before the freeze the author completes a self-PRESS checklist
(translation of the question, Boolean operators, subject headings, text words, syntax, limits)
and assembles a known-item set of at least 20 papers that appear to be eligible, spanning
years, platforms, terminology and journals, drawn from reference lists and papers already
encountered, without extracting any census field. Every known item must be retrieved by at
least one registered query. A missed item prompts a query change, logged below the line with
the item that prompted it. The known-item set is listed by DOI in `search/known_items.md`.

**Screening.** Two steps. (1) A fixed keyword rule, applied by a committed script to title and
abstract, excludes records that carry no term for MR or genetic instruments or no term for
proteins or pQTLs; the rule contains no term for any census reporting outcome (colocalization,
replication, overlap, code, data), so it cannot select on those outcomes, and its exclusions are
counted by reason. (2) Every remaining record is screened from title and abstract by the
registered model with the committed prompt; a record advances on include or uncertain.
Advancing records are assessed for eligibility from full text by the same model, and the author
verifies every full-text exclusion. The screening check sample (the larger of 10% or 50 records
excluded at step 1 or at step 2, stratified by step, query and year, seed `20260931`) is read by
the author before any aggregate is computed; its false-exclusion rates and the screening-error
correction in §Statistical models are reported beside the observed census counts, which they
never replace.

**Extraction.** Every eligible paper is extracted by the registered model from the
committed prompt and schema. Every non-deterministic field returns at least one evidence span;
an output without one fails validation. A span records: the source file's name, SHA-256
checksum, document version and stable URL where one exists; printed page and PDF page;
section, table (row, column, footnote) or figure (panel); a verbatim quotation of about 40
words, at most 80, long enough to carry the antecedent that names the protein or outcome and any
qualification or negation in the adjacent sentence; the evidence role (`supports`,
`contradicts`, `qualifies`, `absence_search`); the evidence type (prose, table cell, figure,
legend, metadata, repository, external mapping); the text-extraction method (native text, XML,
PDF text, OCR, manual transcription); for numeric values, the structured cell (value, label,
unit) in place of prose; and a short coder rationale kept apart from the quotation. A composite
field carries one span per component. A `not_reported` value carries an absence-search manifest:
the documents, sections, tables and supplements searched, the terms or concepts searched for,
whether text extraction was reliable, and whether likely locations were inspected by eye.
Independent check: Claude Code (Anthropic) extracts a random sample of at most 50
eligible papers (seed `20260930`, stratified by first-public period and platform) from the same
prompt and schema, without access to the OpenAI output. The author adjudicates every
disagreement from the full text and logs it with its evidence.

**Reconstruction pass.** After the census extraction is committed, the registered model reads
each paper again with a separate committed prompt and schema and records, for every
`interpreted_causal` and `interpreted_target` claim, the fields a re-analysis needs
(§Measured variables, "Reconstruction fields"), one row per claim and instrument variant. The
reconstruction pass has its own development labels on the development set's interpreted claims,
its own acceptance thresholds (the census thresholds, applied to its fields) and its own
validation on the interpreted claims of the validation sample; its metrics are reported
separately from the census pass.

**Records.** Every request and response is cached and committed with its date, including failed
and invalid outputs. Every extracted value keeps four immutable columns: the model's value, the
adjudicated value, any author-proposed value (§Author feedback) and the final analysis value,
with the basis of the value (`stated`, `calculated`, `mapped`, `inferred`), the extraction
timestamp and whether its source text was OCR-derived. Recorded for each tool: provider, model snapshot string, API date and
endpoint (standard or batch), prompt, temperature where settable, seed where supported,
PDF-to-text and OCR software with version, and the checksum of every input. A record that fails
schema validation is re-run once and otherwise marked `extraction_failed`. If a model is retired
during the census, completed work is frozen, the replacement is documented below the line, and
versions are never mixed within a stage without that record.

**Development set, acceptance thresholds and model choice.** Prompts and schema are developed
only on papers that cannot enter the census: pQTL-MR papers first public before 2019-01-01, papers
testing fewer than 100 proteins in MR, and papers otherwise ineligible. The author codes every development paper by hand
before any model output is compared; the development papers are listed by DOI in the committed
prompt file. The screening and extraction prompts are then engineered against these
hand-labelled examples: the author, with Claude Code and Perplexity, revises the prompt and
schema until the model's output on the development set matches the hand labels, and every
prompt revision and its development-set results are committed. The prompt in force at the
freeze is the registered prompt. The coding manual that defines every extraction field for the
author, with allowed values, edge-case rules and the evidence-span format, is committed with the
prompts before the freeze; the author's development-set labels follow it. No paper that could satisfy the eligibility rules is read with the prompts before
the freeze. The development set tunes the prompts only; its labels are development labels,
and results on it are not performance estimates. The validation sample (below) is opened only
after the prompt is frozen at the freeze commit, no prompt revision follows its opening, and
its metrics are the registered performance estimates.

Acceptance criteria, per consequential field (eligibility; protein; outcome; dataset;
direction; colocalization; each replication type; sample overlap; UK Biobank inclusion;
reconstructable), estimated on the validation sample with Wilson 95% intervals: for binary
fields, sensitivity ≥ 0.95 and positive predictive value ≥ 0.95 for the positive class, with
specificity and negative predictive value reported; for multi-valued fields, macro-averaged
agreement across values ≥ 0.95, with per-value sensitivity reported. Claim enumeration is
evaluated separately as claim recall (≥ 0.95), against the author's enumeration of every claim
in each validation paper. A field is evaluated only if the validation sample holds at least 10
positive and 10 negative instances of it. The
registered model for screening and extraction is GPT-6.1 Sol (OpenAI), snapshot
`[MODEL SNAPSHOT — set before freeze]`. It is run on the development set before the freeze, and
its field-level results there are committed with the prompts. The batch endpoint may be used. A
field that misses its threshold on the development set or in the validation sample, or that has
fewer than 10 positive or 10 negative instances in the validation sample, is verified by the
author for every eligible paper; if claim recall misses its threshold, the author enumerates the
claims of every eligible paper.

**Validation sample.** The larger of 20% of eligible papers or 30 papers (all papers if fewer
than 30), stratified by first-public period, platform, access status and paper size (main text
plus supplement page count, above or below the median), drawn with seed `20260932` after
extraction and before any aggregate is computed. The author enumerates every claim in each
validation paper and checks every field against the source, including fields on which the
OpenAI model and Claude Code agree, and checks each evidence span for correctness (the quotation
is in the source at the stated location) and sufficiency (it supports the value on its own). The fields the audit
uses to re-run claims are among those checked, and their error rates are reported with the
audit's results.

**Deterministic fields.** DOI, PMID, PMCID, journal, first public date, issue date, preprint
identifier and author list come from source metadata by script. STROBE-MR citation is detected
by script from the reference list by DOI (10.1001/jama.2021.18236; 10.1136/bmj.n2233) or
normalized title match. Code and data links are detected by script and tested on one fixed
date during extraction; the tested date, HTTP status and repository commit hash are recorded.

**Full-text access cascade.** Searched in this order until full text is found: (1) PubMed
Central or Europe PMC full text; (2) publisher open version; (3) preprint server; (4)
Unpaywall-listed repository copy; (5) institutional repository or accepted manuscript; (6)
author-maintained repository linked from ORCID or the paper; (7) open supplement; (8) one
standardized request to the corresponding author, with a 21-day response window. The version
extracted is recorded as `document_version` and `supplement_status`. A journal abstract is never combined with a preprint full text without
recording both versions and their dates. A paper without full text after the cascade is
`not_accessible`.

**Author feedback.** Primary census values are the uniformly extracted and adjudicated records
for every paper. After the census file is frozen, the corresponding author of each paper in the
validation sample and the Claude Code check sample receives the extracted claim records and may
point out factual errors, with evidence. Author feedback is reported as a separate validation
analysis (errors reported, errors confirmed against the source) and never modifies primary
values.

## Data collection procedures - File upload

N/A — the queries, known-item set, prompts, schema, thresholds and scripts are committed in the
repository before the freeze.

## Sample size

Every record returned by the registered queries and citation chasing is screened; every
eligible paper and claim enters the census. There is no target n.

## Sample size rationale

N/A — a census of the eligible records retrieved.

## Starting and stopping rules

The search runs once, within 14 days after the freeze commit; citation chasing stops by the
rule above. Records indexed after the search date are not added. No interim analysis.

## Manipulated variables

N/A — nothing is manipulated.

## Measured variables

**Eligibility (all required).** Eligible studies (1) analyse human plasma or serum proteins
measured by an affinity or mass-spectrometry platform; (2) test at least 100 distinct protein
analytes in the paper's MR analysis, selected without reference to the study outcome; (3) use
genetic instruments for protein concentrations in MR or an equivalent instrumental-variable
estimate of a protein's effect on an outcome; (4) evaluate at least one clinical disease,
disease liability, clinical quantitative trait or adverse event; and (5) interpret at least one
protein–outcome result as potentially causal, intervention-relevant, therapeutic, preventive,
harmful, druggable or repurposable, anywhere in the article or its supplement. Analyses of
100–499 and at least 500 proteins tested in MR are prespecified strata.

Criterion 2. The count is of distinct protein analytes for which at least one protein-to-outcome
instrumental-variable estimate was computed; proteins only measured, only instrumented, or only
looked up at a locus are not counted. The count is taken as the paper states it, or computed
deterministically from a complete machine-readable results table; otherwise it is
`not_reported`, and a paper that states conflicting counts is `multiple_definitions` and is
resolved by the author from the results table. Selection is outcome-independent when the
authors analysed every eligible protein on a pre-existing platform, panel or pQTL resource, or
applied a prespecified filter not based on the study outcome; any selection within a panel or
resource by prior association with the outcome fails. A paper that analyses a whole commercial
panel assembled around a disease area (for example Olink Cardiovascular or Inflammation)
satisfies the criterion, carries `themed_panel` = yes and `panel_theme_matches_outcome`, and is
reported as a separate stratum, not as an agnostic proteome-wide screen.

Criterion 3. The paper must report a protein-oriented instrument, variant–protein effects,
variant–outcome effects, and an instrumental-variable ratio, multi-variant MR or SMR estimate
on the protein-exposure scale. Overlap of a pQTL with a disease locus, a look-up of pQTL
variants in a disease GWAS, and a genetic score aligned to disease-risk alleles do not qualify.

Criterion 4. Outcomes are classified by a frozen hierarchy applied to the exact outcome
construct: (i) a disease, disease liability, diagnosed condition or adverse event is eligible;
(ii) a quantitative measurement is an eligible clinical quantitative trait when a named clinical
guideline uses it directly for diagnosis, risk classification, treatment initiation, treatment
target or dose adjustment, with the guideline and its version recorded; (iii) a molecular or
physiological measurement used only as an aetiological intermediate or research biomarker is a
biomarker and is not eligible on its own; (iv) a case the hierarchy does not settle is decided
by the author and entered in the outcome decisions table before any aggregate is computed.
The decisions table is public and is committed before the freeze, seeded with LDL cholesterol,
HDL cholesterol, triglycerides, total cholesterol, systolic and diastolic blood pressure, eGFR,
serum creatinine, bone mineral density, HbA1c, fasting glucose, BMI, waist-hip ratio, FEV1, FVC,
FEV1/FVC, QT interval, heart rate, platelet count, haemoglobin and uric acid, each with its
guideline. A paper whose only outcomes are biomarkers fails criterion 4.

Criterion 5. The paper must contain a sentence that predicates causality, intervention
relevance, prevention, harm or target status of a named protein–outcome pair. A generic statement
that MR can assess causality does not qualify.

**Exclusions.** Papers testing fewer than 100 proteins in MR (counted in the funnel with their
protein count); single-protein or candidate-list papers; eQTL-only analyses; protein biomarker
studies without genetic instruments; proteome prediction scores without protein-level causal
claims; pQTL discovery studies with no disease claim; reviews, editorials, protocols and methods
papers without an applied screen; non-human studies; tissue or CSF proteomics (counted as a
separate stratum, not in the census proportions).

**Observation status.** Every field that depends on reading the paper carries an observation
status separate from its substantive value: `observed` (the paper reports it; the value column
holds what it reports), `not_reported` (the author confirms it absent, with an absence-search
manifest), `not_accessible` (no full text after the access cascade), `supplement_unavailable`
(main text read, supplement not obtainable, and the field could only be settled from the
supplement) or `not_applicable` (the field has no meaning here). A value column is filled only
when the status is `observed`; integer and identifier fields never carry a status word as their
value.

**Claim.** A unique combination of protein analyte (`biological_target`, `protein_form` and
`assay_identifier`), outcome dataset and phenotype, original pQTL source, instrument set,
estimand and analysis population, for a protein → outcome estimate. Separate aptamers or
antibodies for one named protein are separate claims unless the paper combines them. Reverse MR
(outcome → protein) and transcript → protein analyses are not claims; reverse MR run for a claim
is recorded on that claim (`reverse_mr_attempted`, `reverse_mr_result`,
`reverse_mr_supported_forward_interpretation`, `reverse_mr_same_outcome_definition`). Direction
is an attribute of each estimate, not part of the claim's identity: the primary estimate and
each sensitivity estimate of one claim (for example MR-Egger or weighted median on the same
instrument set) carry their own recorded direction.

**Interpretation predicates and category.** Two predicates are recorded for every claim:
`predicate_causal` (a sentence predicates causality of this protein–outcome pair) and
`predicate_target` (a sentence proposes this protein, or an intervention acting on it, as a
potential therapeutic, preventive, harmful, druggable or repurposing target for this outcome).
"Warrants further investigation", "may be relevant", "could have implications", "requires
validation" and statements of biological involvement satisfy neither predicate. The category
is derived: `interpreted_target` if `predicate_target` holds, otherwise `interpreted_causal` if
`predicate_causal` holds, otherwise `reported_association`. `hedge_strength` records the
strongest interpretive wording (`asserted`, `supported`, `potential`, `speculative`). A result
shown only in a main-text figure is a `reported_association`; it is an interpreted claim only
when the figure's title, legend, label or annotation attributes causality or target status to
that pair, and a section heading classifies figure entries only when the legend says every entry
shown meets the interpretation. Colour, arrows, emphasis and placement do not establish an
interpreted claim. The claims recorded for a paper are every interpreted claim wherever it
appears, and every protein → outcome result reported in the main text; results reported only in
the supplement and not interpreted are counted in `n_supplement_uninterpreted_results` and not
enumerated. The audit frame is `interpreted_causal` and `interpreted_target` claims. `location`
is `main_text`, `supplement_only` or `both_main_and_supplement`.

**Counting results.** `n_results_reported` and `n_supplement_uninterpreted_results` count
deduplicated protein × outcome × instrument-specification units: several estimators of one unit
count once; the same result shown in more than one table or figure counts once; null results
count; variants of one instrument specification that differ only in a significance threshold
count once.

**Headline claim.** An `interpreted_causal` or `interpreted_target` claim meeting the first
applicable level, where at every level the location must carry the claim's full proposition
(this protein, this outcome, and the causal or target interpretation), not the protein name
alone: (1) the title states it; (2) the abstract states it; (3) a main-text table or figure
explicitly labelled causal, final, prioritized, druggable, therapeutic or recommended for
follow-up presents it; (4) the last paragraph of the Results that reports findings, or the
concluding paragraph of the Discussion, states it. A claim appearing only
in the supplement is never a headline claim. Each headline classification stores the level,
page, section or table/figure, and an evidence span.

**Reporting fields, operational definitions.**

| field | reported when |
|---|---|
| colocalization | a method testing a shared causal signal was applied to the exact claim: same protein analyte, same outcome phenotype and dataset, same locus, and the directionally corresponding MR analysis; method class HEIDI (including SMR-HEIDI), Bayesian regional single-signal (e.g. coloc.abf), multi-signal (e.g. coloc-SuSiE, PWCoCo, eCAVIAR) or other (e.g. enloc); anything else is recorded in `coloc_target_relation` (`exact`, `nested_subtype`, `broader_phenotype`, `related_phenotype`, `different_outcome`, `expression_only`) and only `exact` counts |
| colocalization applicability and result (H1) | per headline claim: `coloc_applicable` (`yes`; `no` for trans-only instruments or no regional data; `unclear`), and when reported the numeric result, whether the threshold was prespecified, whether the claim passed the authors' threshold, the locus, the data source and the method version; paper level: `n_headline_claims`, `n_headline_claims_with_coloc` |
| independent-cohort replication | recorded separately for pQTL/exposure, outcome-GWAS and complete MR replication, each as attempted or not; `independence` is `independent` only when the association was re-estimated in participants disjoint from the discovery participants, `internal_holdout` for a random or temporal split of the same recruited cohort (recorded as a separate validation design, not as independent replication), and `independence_unclear` when overlap cannot be established; exposure-cohort overlap and outcome-cohort overlap are recorded separately; per claim the result is `supported` (direction concordant and meets the paper's replication threshold), `not_supported` (fails it without significant discordance), `discordant` (incompatible direction or significant heterogeneity), `inconclusive` (insufficient precision, assay failure, unavailable analyte or no valid instrument) or `not_assessable`, with the replication estimate's direction, interval and the paper's own label; at paper level the counts of claims in each result category are reported |
| cross-platform replication | the analyte relation (`same_analyte`, `compatible_nonidentical`, `ambiguous`), the technology relation, the highest stage reproduced (`protein_measurement`, `pqtl_association`, `mr_estimate`, `mr_plus_coloc`) and the result (values as for independent-cohort replication); when the two assays target different isoforms, complexes or epitopes, or map ambiguously, the second assay defines a separate claim, not a replication |
| multiple-testing correction | the test family, number of hypotheses, correction method, threshold, analysis stage, and whether the claim survives it; value `applied`, `none_applied`, `method_without_family` or `family_without_method`; coded at paper level, and at claim level for survival |
| sample-overlap statement | an explicit statement about participant overlap between exposure and outcome samples (states none / states partial / states unknown), with any overlap estimate and N and where the statement appears; "two-sample MR" alone is not a statement; coded per outcome GWAS |
| outcome UK Biobank inclusion | per outcome GWAS: `outcome_contains_ukb` = `yes`, `no`, `partly`, `unclear` or `not_stated`, with the UK Biobank component, release and participant count where given; naming UK Biobank as a source counts as `yes` only when the outcome GWAS is a UK Biobank GWAS itself, and a consortium or meta-analysis GWAS needs an explicit statement; paper-level `ukb_inclusion_paper_status` is derived: `all_include` (every outcome GWAS stated `yes` or `partly`), `all_exclude` (every one stated `no`), `mixed` (every one stated, some including and some excluding), `partly_not_stated` (at least one `unclear` or `not_stated` and at least one stated) or `all_not_stated`; independent of the sample-overlap statement |
| code available | a publicly accessible, analysis-relevant script or executable workflow reachable on the test date; a software-package citation or dead link is not code |
| summary statistics available | classed by what the paper states, separately for exposure statistics, outcome statistics, complete MR output and regional data for colocalization, each as openly downloadable / query-only / controlled access / registration required / embargoed / on request / partially available / dead link / unavailable / not stated, with `access_not_tested` until the fixed-date link test; "on request" is not public |
| reconstructable | derived per claim from the reconstruction pass: every reconstruction component the re-analysis needs is `observed` |
| STROBE-MR cited | by script, as above |

**Paper-level fields.** Identifiers and study family; journal; first public date and its basis;
issue date; protein-count stratum; `themed_panel`; `panel_theme_matches_outcome`; numbers of
proteins measured, instrumented and tested in MR, each with its observation status;
`n_results_reported`; `n_supplement_uninterpreted_results`; number of claims by category and
headline status; `uses_ukbppp`; `ukb_inclusion_paper_status` (derived); pQTL source(s) and
platform(s); cis/trans policy (`cis_only`, `cis_and_trans`, `trans_only`,
`local_not_gene_centric`, `protein_specific`, `multiple_policies`); the reporting fields above;
full-text status; `document_version` (publisher version, PMC version, author manuscript,
preprint); `supplement_status` (read, not available, none published); source-file checksums;
text-extraction method; extraction timestamp.

**Outcome-level fields** (one row per outcome GWAS a paper uses). Outcome label as reported;
GWAS identifier and release (`multiple_releases_combined`, `release_ambiguous` and
`custom_meta_analysis` where they apply); ancestry; case and control counts; the outcome mapping
(below); the criterion-4 class; `outcome_contains_ukb` and its details; the sample-overlap
statement for that outcome.

**Claim-level fields.** Protein name as reported; UniProt accession (or `multiple_possible`,
`complex`, `isoform_specific`, `nonhuman_mapping`, `unmapped`); `biological_target`;
`protein_form`; assay identifier (Olink OID, SomaScan SeqId, or other); pQTL source, platform
and cohort; cis/trans; number of instruments and the lead variant; the outcome row it uses;
estimand (analysis population, estimate type, effect scale and any transformation, exposure and
outcome units, model, interval type); the primary MR estimate, interval and p-value and each
sensitivity estimate, each with its direction (`raises`, `lowers`, `null_reported`,
`heterogeneous`, `nonlinear`, `bidirectional_by_outcome`, `not_estimable`, `ambiguous`);
`predicate_causal`; `predicate_target`; `hedge_strength`; claim category; headline level;
`location`; claim family (claims of one protein whose outcomes are nested, one outcome's
EFO/Mondo term an ancestor of the other's); the reporting fields above as applied to this
claim; the reverse-MR fields; evidence spans.

**Reconstruction fields** (reconstruction pass; one row per interpreted claim and instrument
variant). Claim-level: exposure GWAS identifier, release, ancestry, sample size and assay
identifier; outcome GWAS identifier, release, ancestry, case and control counts and phenotype
code; instrument-selection threshold, cis window, clumping threshold and window, LD reference
panel and proxy policy; harmonization rule, palindromic-variant rule and allele-frequency
threshold; MR estimator and software with version; whether estimates come from individual
cohorts or a meta-analysis; the discovery–replication relation (winner's curse); the
sample-overlap estimate for the exposure–outcome pair; the multiplicity family and whether the
claim survives it; colocalization locus boundaries, priors, LD source, number of signals allowed
and posterior threshold; cross-platform analyte equivalence and cohort independence.
Variant-level: variant identifier, chromosome, position and build; effect and other allele;
effect-allele frequency; variant–protein beta, standard error and unit; variant–outcome beta,
standard error and unit; the table or file the values come from. Each component carries an
observation status, and `reproducibility_status` and the blocking reasons below are derived
from them.

**Outcome mapping.** The exact reported outcome label and GWAS identifier with release are
kept; the outcome is mapped by script to a versioned EFO or Mondo identifier with its mapping
relation (exact, narrower, broader, related, unmapped); a project category is derived from the
ontology term: cardiovascular; neoplasm; neurological; psychiatric; endocrine/metabolic;
immune/inflammatory; respiratory; gastrointestinal/hepatic; renal/urological;
musculoskeletal; dermatological; infectious; reproductive; hematological; ophthalmic; clinical
quantitative trait; biomarker; adverse event; other/unmapped. The mapping table and the
ontology release checksum are published.

**Reproducibility status and blocking reasons** (per interpreted claim; derived from the
reconstruction pass's components in the census and tested in the audit): `reproducibility_status` (`reconstructable`,
`partially_reconstructable`, `not_reconstructable`, `not_assessed`); `primary_blocking_reason`,
one of `exposure_statistics_unavailable`, `outcome_statistics_unavailable`,
`instrument_definition_ambiguous`, `protein_mapping_ambiguous`,
`ld_or_allele_frequency_unavailable`, `assay_absent_from_replication_platform`,
`replication_resource_underpowered`, `requires_author_contact`, `analysis_rule_unreported`,
`other_technical_failure`; `all_blocking_reasons`, every applicable label from the same list;
and `status_basis` (`inferred_from_reporting` in the census, `tested_in_audit` in the audit).
No blocking reason is counted as failed replication.

## Measured variables - File upload

N/A — the JSON schema is committed with the prompts.

## Indices

Registered census outcomes. For full-text-dependent fields the primary denominator is papers
(or claims) with accessible full text; each is also reported across all eligible papers as
lower and upper bounds, treating `not_accessible` papers as all not reported and as all
reported. Supplement-dependent fields follow the same rule for `supplement_unavailable`: the
primary denominator excludes those papers, and the bounds treat them as all not reported and
as all reported. Every outcome is also reported in the ≥ 500-protein subset, and separately for
themed-panel papers.

| outcome | unit |
|---|---|
| colocalization reported (claim-specific, by method class) | papers; headline claims; headline claims with `coloc_applicable` = yes |
| independent-cohort replication attempted, its independence and its result (by type) | papers; headline claims |
| cross-platform replication reported (by stage, analyte relation and result) | papers; headline claims |
| cis-only instruments | papers |
| sample-overlap statement present | UKB-PPP papers; papers using any UK Biobank-derived pQTL source; all papers |
| `ukb_inclusion_paper_status` (H2: `all_include`, `all_exclude` or `mixed`) | UKB-PPP papers; papers using any UK Biobank-derived pQTL source; all papers |
| multiple-testing correction applied, and headline claims surviving it | papers; headline claims |
| reverse MR attempted | headline claims |
| code available | papers |
| summary statistics available (by class and type) | papers |
| STROBE-MR cited | papers |
| `reproducibility_status` = `reconstructable` | interpreted claims; headline claims; papers (every interpreted claim reconstructable) |
| `not_accessible` | papers (an access outcome) |

Also reported: papers per year, claims per paper by category, journals, and pQTL sources and
outcome GWAS reused across papers.

## Indices - File upload

N/A — no index file.

## Statistical models

Proportions with Wilson 95% intervals; claim-level proportions with a paper-clustered bootstrap
(10,000 resamples of papers). H1: difference in paper-level proportions, 2024–2025 minus
2019–2022, with a Newcombe 95% interval. H2: paper-level proportion with a one-sided 95% Wilson
upper bound. The census enumerates a finite set of retrieved records; intervals quantify
uncertainty about the underlying publication-generating process, not about that finite set.

**Screening-error correction.** Within each stratum of the screening check sample (step ×
query × first-public year), the estimated number of false exclusions is the number of audited
exclusions found eligible divided by that stratum's sampling fraction; the estimates are summed
across strata and added to the observed included count. A 95% interval comes from a stratified
bootstrap of 10,000 resamples of the audited records within strata. Reported: the observed
included count, the audited false-exclusion rate by stage, the estimated missed count and its
interval. Where a stratum has fewer than 10 audited exclusions, bounds are reported instead of a
point estimate for that stratum: a lower bound assuming all its unaudited exclusions are correct
and an upper bound applying the upper 95% Wilson limit of its audited false-exclusion rate.

## Statistical models - File upload

N/A — the analysis script is committed before the freeze.

## Transformations

First public year grouped as 2019–2022, 2023, 2024–2025. Protein count grouped as 100–499 and
≥ 500. Outcomes mapped to the project categories as in §Measured variables.

## Inference criteria

| hypothesis | holds when |
|---|---|
| H1 | 2024–2025 minus 2019–2022 proportion > 0, with the Newcombe 95% interval excluding 0 |
| H2 | one-sided 95% Wilson upper bound of the proportion of UKB-PPP papers with `ukb_inclusion_paper_status` = `all_include`, `all_exclude` or `mixed` < 0.50 |

**Each estimate is reported whatever its size; a group with fewer than 20 papers is labelled
imprecise.** H1 and H2 are co-primary descriptive hypotheses; no familywise conclusion is
drawn from them.

## Data inclusion and exclusion

As §Measured variables. The funnel reports records retrieved per source and query, records
added by each citation-chasing round, duplicates removed, title/abstract exclusions by reason,
full-text exclusions by reason, keyword-rule exclusions by reason, study families merged, papers without full text, and eligible
papers by window, protein-count stratum and themed-panel status.

## Missing data

Every paper-dependent field carries an observation status (§Measured variables): `observed`,
`not_reported`, `not_accessible`, `supplement_unavailable` or `not_applicable`. A field the
OpenAI model does not extract from accessible full text is `not_reported` only once the author
confirms it absent and records the absence-search manifest; nothing is inferred. Papers that
are `not_accessible`, and papers whose needed supplement is `supplement_unavailable` for a
supplement-dependent field, remain in bibliometric counts and enter those reporting proportions
only through the bounds in §Indices. A record that fails schema validation twice is excluded and
counted.

## Other planned analysis

**Extraction performance.** Reported per field against the author's checks, for the OpenAI
model and for Claude Code separately, and for the census and reconstruction passes separately,
with Wilson 95% intervals: sensitivity, specificity, positive and negative predictive value for
binary fields and macro-averaged agreement for multi-valued fields, with denominators; claim
recall (claims missed per validation paper); evidence-span correctness and sufficiency;
sensitivity and specificity of eligibility,
false-exclusion rates at the keyword rule and at title/abstract screening, exact agreement
between the OpenAI model and Claude Code, accuracy among fields on which they agree,
missingness, hallucination rate (a value unsupported by its evidence span), correction rate,
and the author's adjudication count. Errors are also tabulated by PDF text quality (native text
or OCR), supplement length (above or below the median page count), presentation (table-heavy or
prose-heavy, by the share of claims whose primary evidence is a table cell), number of claims in
the paper (above or below the median) and access status.

**Audit frame.** Every `interpreted_causal` and `interpreted_target` claim in the committed
confirmatory census enters the audit; no claims are sampled. The audit registration re-runs all
of them through one pipeline and attempts exact reproduction of every claim whose paper reports
enough detail, with a `reproducibility_status` and blocking reasons (§Measured variables) for
every claim it cannot re-run. The
extraction error rates above are reported with the audit's results.

**Window sensitivity.** Every census outcome, and H1 and H2, is also reported for papers first
public 2020–2025, in a separate table.

**Update set.** The 2026 papers are reported with the same indices in a separate table.

Any analysis not listed here is exploratory and labeled so wherever it appears.

## Context and additional information

The re-analysis audit is registered separately, before any claim is re-run. It will reuse the
colocalization and harmonization pipeline of `pqtl-mr-domain-of-validity` V8.

Limitation stated here: screening and extraction have one human researcher, not two human
reviewers. The OpenAI model screens and extracts, Claude Code independently extracts a check
sample of at most 50 papers, and every extracted value carries a quoted passage from its source;
the researcher adjudicates disagreements, verifies all full-text exclusions and a sample of
screening exclusions, and checks a stratified validation sample field by field to estimate
false exclusions and field-level error.

Novelty statement, checked against a search of Europe PMC (including preprints), PubMed and
Semantic Scholar, 2019 to 2026-09-30 (`docs/source_verification/VERIFICATION.md`;
OpenAlex to be re-run before the freeze): no previous study is known to have systematically
collected published proteome-wide pQTL–disease MR claims for claim-level re-analysis under a
uniform pipeline. The closest precedent re-ran eight published myopia MR
analyses by other groups against a different outcome GWAS, without proteomic exposures,
colocalization, or cohort, platform or overlap checks (Nguyen, Terry and Guggenheim 2025,
`@nguyen2025myopia`). Chen, Zhao and Fu 2025 (Eur Heart J, 10.1093/eurheartj/ehaf186) appraise
proteomic MR targets for myocardial infarction and are to be read before the freeze.

### Maximum claim under this registration

The paper can state, for proteome-wide MR papers retrieved by the registered PubMed, Europe PMC
and OpenAlex queries and citation chasing, first public 2019–2025, testing at least 100
proteins in MR and meeting the registered eligibility rules, the proportion that report
colocalization, independent-cohort replication, cross-platform replication, a sample-overlap
statement, multiple-testing correction, code, summary statistics and a STROBE-MR citation,
among papers with accessible full text and as bounds across all eligible papers, in all
eligible papers and in the ≥ 500-protein subset, with the proportion of interpreted claims, and of
headline claims, that are reconstructable from public data; that colocalization reporting was or was not higher in
papers first public in 2024–2025 than in 2019–2022 (H1), without attributing a cause; and that
fewer than half of UKB-PPP papers do or do not state, for every outcome GWAS they use, whether it
includes UK Biobank participants (H2). It cannot state
whether any claim is true, whether any claim replicates, or anything about papers outside the
registered sources, the eligibility rules or the window. Replication, colocalization and
survival of claims belong to the audit registration.

---

## Log

Append only. Never edit above the line.

The last column is what distinguishes an amendment from a deviation, so you do not have to
decide which word to use: `nothing run`, `no results seen`, `results not opened`, `results seen`.

```
2026-09-30  created                              nothing run
2026-09-30  prompt-development rule added (development papers only from outside the census: pre-2020 or <500 proteins); defaults kept as drafted per Elliot   nothing run
2026-09-30  scoop verification folded in: novelty statement now cites Nguyen 2025 as closest precedent; foreknowledge item 7 added; Chen 2025 EHJ and OpenAlex re-run pending   nothing run
2026-09-30  Perplexity round-1 review applied (planning/perplexity_census_review/01_REVIEW_full.md): panel-wide eligibility with 100-protein floor and 100-499 / >=500 strata; claim categories and headline hierarchy; operational reporting definitions; four-query architecture, OpenAlex, citation chasing, self-PRESS, known-item recall test; model passes as automation aids with evidence spans, conservative screening, verified exclusions, development gold set, field thresholds, validation sample max(20%, 30); three-state missing full text with bounds and access cascade; H1 non-causal by first public date, H2 one-sided bound, void rules removed; study-family and author-correction rules; EFO/Mondo outcome taxonomy replaces ICD-10; 12-stratum audit with pilot-based size rule; foreknowledge item 8   nothing run
2026-09-30  workflow wording: screening and extraction described as Claude Code extraction, independent Perplexity check, author verification; no design change   nothing run
2026-09-30  Perplexity second pass specified as the desktop application in batched threads (titles/abstracts only for screening; PDFs plus form for extraction), every thread exported and committed; no API   nothing run
2026-09-30  Perplexity second pass via its API (Sonar), web search disabled for extraction; supersedes the desktop-batch wording above   nothing run
2026-09-30  PubMed result counts for the registered queries seen before the freeze (counts only, no record content): Q1 1,309; Q2 332; Q3 6,590 (5,748 unique); Q3 with GEN 814; union with GEN-restricted Q3 2,089; foreknowledge item 11   no results seen
2026-09-30  Elliot's decisions after v2: keyword-rule screening then the OpenAI model; OpenAI extraction with a Claude Code check sample of at most 50 papers; Perplexity removed from screening and extraction; GPT-6.1 Sol registered for screening and extraction, run on the development set before the freeze; Q3 requires the GEN block and the confirmatory date bound is 2025-12-31; eligibility counts proteins tested in MR; foreknowledge items 9-11 and the Chen L correction; audit sampling replaced by an audit frame of every interpreted claim, with random samples kept only for checking   nothing run
2026-09-30  prompt engineering against the author's hand-labelled development set made explicit (author with Claude Code and Perplexity; every revision committed; prompt at freeze is registered)   nothing run
2026-09-30  coding manual registered: committed with the prompts before the freeze   nothing run
2026-09-30  codebook rulings applied: confirmatory window starts 2019-01-01 (H1 early period 2019-2022; Zheng 2020 now eligible, removed from the development set, foreknowledge item 12); H2 redefined on outcome_ukb_inclusion_stated; new fields n_results_reported, n_supplement_uninterpreted_results, uses_ukbppp, outcome_ukb_inclusion_stated, panel_theme_matches_outcome; replication attempted plus result; missing states not_applicable and supplement_unavailable; summary statistics by paper statement with not stated; criterion 3 and 4 rules; protein-to-outcome claims only; claim unit rule; category precedence; headline levels 3 and 4 clarified; multiple testing and overlap paper level unless claim-specific; correction notices in families   nothing run
2026-09-30  codebook review round 1 applied (planning/perplexity_codebook_review/02_ADJUDICATION.md): claim identity by instrument set and estimand with direction per estimate; development labels, validation opened only after the freeze; per-field sensitivity/PPV/macro agreement with Wilson intervals and a 10-positive minimum; author feedback as a separate validation analysis; design-weighted screening-error correction with stratified bootstrap; supplement_unavailable bounds; reproducibility status and blocking-reason flags replace the disposition ladder; headline levels require the full proposition; result-counting protocol; document_version and supplement_status; replication result aggregation; claim-level reconstructability; UK Biobank inclusion rule; clinical quantitative trait whitelist   nothing run
2026-09-30  codebook review round 2 applied (the six questions; planning/perplexity_codebook_review/03_ADJUDICATION.md): replacement rules for disagreement-prone fields; edge-case rules (independence by participant non-overlap, internal holdout, coloc_target_relation, figure-only claims, interpretation predicates and hedge_strength, reverse-MR fields, outcome hierarchy with a public decisions table seeded by the trait list, themed-panel stratum, criterion-3 requirements, replication results supported/not_supported/discordant/inconclusive/not_assessable, multi-assay rules); observation status separated from value (observed/not_reported/not_accessible/supplement_unavailable/not_applicable); mechanical first-public hierarchy and 2020-2025 window sensitivity; H1 applicability fields; UK Biobank inclusion per outcome GWAS with derived paper status and H2 restated on it; outcome-level rows; auditability and immutable value columns; reconstruction pass with its own prompt, schema and validation; evidence-span fields, 80-word ceiling and absence-search manifest; claim recall, NPV, span correctness and error stratification in validation   nothing run
```
