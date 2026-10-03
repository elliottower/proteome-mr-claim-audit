# Proposed rules for every open point of the stage-0 build (2026-10-01)

One rule per open point listed while the stage-0 scripts were built: search (S1–S27), drug joins
(D-A1–A12, D-B1–B13) and biology (B-A1–A23, B-B1–B9, B-C), and five points found while the build
was put together (N1–N5): 90 points. The three builders' lists are working files and are not in
this repository; each point's gap is restated below. These are the rules as of PREREG.md v14
(2026-10-01); the rules changed afterwards are recorded in PREREG.md and RELEASES.md, which
hold. Each rule takes the reading closest to the registered text
and, where two readings are equally close, the reading that makes the paper's counts smaller.
Where the other reading could move a headline number it is registered as a named sensitivity
analysis. Four points were decided by the author on 2026-10-01 and are marked **[decided]**:
therapeutic areas from Open Targets in place of hand-made categories (B-A1), the platform read
from each dataset's source paper with no abstract-based fallback (B-A3 to B-A5), the EpiGraphDB
trait mapping extended before the freeze (B-A11), and manual coding of unresolved dataset names
with three checks (N5). Every rule is in PREREG.md v14 and in the code; nothing has run on an
in-window record.

Tags: **[as built]** the code as first built already did this; **[changed]** the code was changed
to this rule; **[S: name]** registered sensitivity analysis; **[Q1–Q10]** a point that needs a
domain judgment (listed at the end).

All counts below come from resource files only (ontology files, ChEMBL 37, Open Targets 26.09,
the EpiGraphDB snapshot) or from records published before 2019. No claim, pair or registry
record exists.

## Search and screening

**S1. Document types.** Gap: OpenAlex and Europe PMC return conference abstracts, dissertations,
datasets, peer-review reports and patents (8 of 23 records in the Nov–Dec 2018 smoke run), and a
repository copy of an abstract would count as its own study. Rule: every record is screened and
takes a document class (`journal`, `preprint`, `other`); records of class `other` enter no
primary result; in the sensitivity analysis they are kept, and one that matches a journal or
preprint record by title and first author joins that family, never a second family. Why: the
population is papers. **[changed] [S: all_document_types]**

**S2. OpenAlex API key.** Settled in the prereg text (a key in the request header, never stored,
no email address); the key is `OPEN_ALEX_API_KEY`. Not reopened.

**S3. Citation-chasing scope.** Gap: "screened by the same procedure" sends every cited and
citing work to GPT-6.1 Sol, an estimated 50,000–80,000 records in round one. Rule: only works
with an OpenAlex publication date of 2019-01-01 or later are retrieved; the keyword prefilter
gates chased records, and only records it leaves unmarked go to GPT-6.1 Sol; per round, a
seeded sample of min(200, n) gated-out records is judged by the eligibility prompt apart, and
the share judged eligible or uncertain is reported; sampled records enter no result. In the
registered search the prefilter still never excludes a record. Why: an earlier work cannot be
first public in the window, and the gate's loss is measured. **[changed]
[S: without_citation_chasing] [Q6]**

**S4. Raw response storage.** Gap: a chase round is several hundred MB of responses. Rule: the
search responses are committed; the chase response bodies are stored on the Modal volume and
their manifest (URL, timestamps, byte count, sha256 of every body) is committed. Why: the
manifest fixes the content; the repository stays small. **[changed]**

**S5. Chase seeds.** Rule: the screening records judged `eligible`, `eligible_count_not_stated`
or `uncertain`, in either window; a round's seeds are the records the previous round added with
one of those decisions. Why: uncertain papers go to extraction as eligible. **[changed]**

**S6. Repeat-run pairing.** Gap: no rule paired run-1 with run-2 records. Rule: within an
abstract, records pair on folded protein, folded outcome and the context key; records left over
pair on protein and outcome alone; within a key, in output order; the share paired and per-field
exact agreement are reported (`scripts/repeat_run_agreement.py`). **[changed]**

**S7. Truncated phrases.** Europe PMC and OpenAlex do not accept a truncated phrase inside a
Boolean query. Rule: each is written out as listed completions (`search/queries.md`); the lists
are narrower than PubMed's truncation, and PubMed evaluates its own query. **[as built]**

**S8. Hyphenated spellings.** Rule: the Europe PMC and OpenAlex queries add the hyphenated forms
of `colocali*` and `repurpos*`, which PubMed's truncation already retrieves (Q4 on 2014–2018:
146 Europe PMC MEDLINE records without them, 288 with, 311 in PubMed). **[as built]**

**S9. MeSH.** Rule: Europe PMC `KW:"Mendelian Randomization Analysis"`; OpenAlex has no MeSH
filter, so the term is omitted there. **[as built]**

**S10. `[tiab]` scope.** PubMed's `[tiab]` reads author keywords and the other two sources'
title-and-abstract fields do not. Rule: not compensated; stated as a limit. **[as built]**

**S11. Dates.** Rule: `[dp]` is translated as Europe PMC `FIRST_PDATE` and OpenAlex
`from_/to_publication_date`. **[as built]**

**S12. Other settings.** Rule: Europe PMC `synonym=false`, `resultType=core`; OpenAlex
`title_and_abstract.search.exact`, the default corpus and a fixed `select`. **[as built]**

**S13. Translation fidelity.** Recorded as foreknowledge: hit counts of the four queries on
2014–2018 in the three sources (`docs/stage0_build/*_pre2019.json`). **[as built]**

**S14. "One day."** Rule: one UTC date; a resume on a later UTC date raises. **[as built]**

**S15. Abstract and metadata source.** Rule: PubMed, then Europe PMC, then OpenAlex; a PMID
returned only by the other two sources is fetched from PubMed. Why: OpenAlex abstracts are
reconstructed and can be wrong. **[as built]**

**S16. Records with no abstract.** Rule: they stay in the screening set and GPT-6.1 Sol reads
the title alone. Why: every retrieved record is screened. **[as built]**

**S17. Kind.** Superseded by S1. **[changed]**

**S18. First public date.** Rule: PubMed, the electronic article date, else the issue date at
its resolution; Europe PMC, the electronic date, else the issue date, and a preprint's first
publication date; OpenAlex, `publication_date`. **[as built]**

**S19. Preprint version.** Gap: the prereg dates and extracts "the preprint's version 1", and no
source used returns version 1 abstracts. Rule: the preprint abstract is the one Europe PMC holds
(else OpenAlex) and its date is the preprint's first publication date; the limit is stated (a
pair added in a later preprint version is dated to the first). Why: no registered source
separates versions. **[changed in text] [S: claim_dates_from_registry_abstracts_only] [Q7]**

**S20. Preprint-to-article links.** Rule: Europe PMC's "Preprint of" entries; a link to an
article that was not retrieved links to nothing. **[as built]**

**S21. OpenAlex first author.** Rule: the last word of the display name; a limit of fuzzy links
that depend on an OpenAlex-only record. **[as built]**

**S22. Record identifiers.** Rule: PMID, else the Europe PMC identifier, else the OpenAlex
identifier. **[as built]**

**S23. Count check.** Rule: the run raises when a stream retrieved a different number of records
than its source reported. **[as built]**

**S24. Prefilter terms.** Rule: the title-and-abstract terms of the registered blocks: genetic =
MR, GEN, LOCUS; protein = PROT, PQTLB. **[as built]**

**S25. Wording-class matching.** Rule: a keyword matches from the start of a word, any ending,
any case ("repurpos" is a stem; "because" is not "cause"). **[as built]**

**S26. Wording keywords inside outcome names.** "treatment-resistant depression" classes a span
`target`. Rule: the registered lists and spans are used unchanged; the limit is stated.
**[as built] [Q8]**

**S27. Repeat sample.** Rule: ceil(0.10 × n) of the records judged eligible,
`eligible_count_not_stated` or uncertain in the file given, ids sorted, seed 20261001.
**[as built]**

## Drug-development records

**D-A1. Status classes not exhaustive.** Gap: a pair can have a matching record and meet no
class (a ChEMBL phase of 0.5 or -1: 1,214 indication rows; a COMPLETED or UNKNOWN trial, 132,208
and 29,809 reports, sets a class only through a ChEMBL phase 1–4 row). Rule: an eighth class, `other_matching_record`, with its reason
stored. Why: such a pair has a record, so `no_matching_trial_or_indication_record` would be
false. **[changed: registered and renamed] [S: completed_trials_as_completed]**

**D-A2. Reports that are not trials.** 56,221 `clinical_report` rows come from regulators, labels
and nomenclature sources. Rule: they are records for a matching indication and never set a trial
class. Why: a pair with a label record is not without a record.
**[as built] [S: clinical_trial_reports_only] [Q3]**

**D-A3. SAFETY reports.** Rule: not read (2,744 rows whose `diseases` are adverse effects).
**[as built]**

**D-A4. Quality-control flags.** 104,698 reports carry a flag; Open Targets leaves them out of
its own aggregates. Rule: read, with the flags stored on every event. Why: the prereg reads
`clinical_report`. **[as built] [S: unflagged_reports_only] [Q3]**

**D-A5/A6. Combination and multi-disease reports.** Rule: a report counts for a pair when any of
its drugs acts on the protein and any of its diseases matches.
**[as built] [S: single_drug_single_disease_reports]**

**D-A7. Leaving the join.** Rule: a pair leaves only when its outcome identifier is absent from
the Open Targets disease index, the ChEMBL indication identifiers and the report disease
identifiers; a protein with no ChEMBL mechanism stays and has no drug. **[as built]**

**D-A8. "For a matching indication" / "for any indication".** Rule: a drug has a record for a
matching indication by a ChEMBL indication row or a `clinical_report` row; "any indication" is
every drug acting on the protein. **[as built]**

**D-A9. "Nominally aligned."** Rule: the drug's direction equals the claim's indicated change;
in a combination trial, any trial drug acting on the protein with that direction. **[as built]**

**D-A10. `target_drugged_elsewhere`.** Rule: phase 4 at any non-matching indication, one-step
relatives included; rows with no identifier or an ambiguous identifier do not count.
**[as built]**

**D-A11. Unit of claim-level outcomes.** Rule: claim records, as §Indices says. **[as built]**

**D-A12. One-step edges.** Rule: `verification/ontology_edges.csv` (B-A2). **[changed: wired]**

**D-B1–B13.** Adopted as built: Open Targets drug identifiers collapsed through the ChEMBL
hierarchy (B1); a molecule with no hierarchy row is its own parent (B2); a drug's action types
are the set over its qualifying mechanism rows (B3); component-level rows need no flag (B4);
`homologue` not filtered (B5); an indication identifier with several canonical identifiers
matches nothing (B6); a MeSH-only indication matches nothing (B7); a terminated or withdrawn
trial with no stop label is no stopped-trial event (B8); every suspended trial is counted apart
(B9); a trial with two labels is one event (B10); phases 1–3 inclusive (B11); claims without a
verified direction leave the alignment (B12, amended by N2 for null results); identifiers
outside MONDO and EFO are their own canonical identifier (B13).

## Biology and registry analyses

**B-A1. Disease categories.** Gap: no rule mapped a term to one of the 18 project categories.
Rule **[decided]**: the category of an outcome is its Open Targets 26.09 therapeutic area or
areas (`disease.therapeuticAreas`, 26 areas, every one of the 45,896 terms has at least one;
`verification/therapeutic_areas.csv`). An outcome the file does not carry takes the areas of its
nearest ancestors that are in it: 17,108 of the 24,954 MONDO human-disease terms are in the
file and 24,601 have an area under this rule. `measurement`, `phenotype` and
`biological_process` are not disease areas. A protein is a hub when the outcomes of its counted
claims cannot all be covered by fewer than 3 disease areas, so an outcome in several areas adds
at most one. Why: a published classification, and the smallest hub count.
**[changed] [S: distinct_therapeutic_areas] [Q4]**

**B-A2. Ontology edges.** Rule: the union of the unconditional `is_a` edges of the pinned MONDO
and EFO files, endpoints canonicalized (96,473 edges). **[as built]**

**B-A3. Assay-list attachments.** Gap: 14 of 28 pQTL dictionary rows named no pinned list.
Rule **[decided]**: no abstract-based fallback. Each of the 14 rows was resolved once from the
dataset's own source paper, with the sentence pinned (`PLATFORM_LOOKUPS.md`): 4 rows attach to
pinned lists or their unions, 10 to eight published list files, now on the Modal volume with
their sha256 (`verification/platform_list_sources.csv`). All 28 rows are attached. The list is
the whole panel or array as assayed, proteins dropped at quality control included, with the
quality-controlled count recorded. The 14 rows go through the three checks of N5 before the
freeze. **[changed] [Q5]**

**B-A3a. Zheng 2020 instrument set.** Rule: the background is the instrumented proteins of its
Supplementary Table 1 (1,725 reviewed accessions); the union of the five source studies' assay
lists is the alternative. **[changed] [S: alternative_assay_lists] [Q5]**

**B-A3b. Jackson Heart Study.** Rule: the pinned SomaScan 1.3k list (1,063 accessions against
1,297 on the assay as run), stated as an approximation. **[changed] [Q5]**

**B-A3c. Xu 2023.** The protein-level rows of Supplementary Data 2 number 304, the count in the
text. **[changed]**

**B-A3d. Small lists.** Lists of 70 to 304 accessions keep 0 to 21 pathways under the 10–500
rule. Rule: a list with no kept pathway has no per-list table; its proteins enter the pooled
analysis. **[changed]**

**B-A4. Source of the platform.** Rule **[decided]**: the claim's pQTL dataset row alone decides
the list; GPT-6.1 Sol's `platform` field is not read for the enrichment. **[changed]**

**B-A5. Generic dataset names.** Rule: a name gives a list only when all its dictionary rows
share one list. "AGES" and "KORA" now give a list; "SCALLOP" (three rows, three panel sets) and
"Fenland" (the full assay and a 179-protein subset) give none, are `release_ambiguous`, and go
to the manual-coding step (N5). **[as built] [S: any_candidate_row_attachment]**

**B-A6. Backgrounds.** Rule: every component accession of a multi-protein analyte enters;
accessions outside the pinned reviewed UniProt file are dropped; background proteins with no
pathway stay in the Fisher universe; Explore 1536 is read from the UK Biobank protein map.
**[as built]**

**B-A7. Benjamini–Hochberg family.** Rule: every pathway kept by the 10–500 rule on that list.
Why: the larger family. **[as built]**

**B-A8. Pooled analysis.** Rule: the union of the attached lists; the pooled claimed set is the
union of the per-list claimed sets, each within its background. **[as built]**

**B-A9. Pathway claim density.** Rule: every registry claim, every human lowest-level pathway.
**[as built]**

**B-A10. Direction of a returned estimate.** Rule: the sign of beta; a claim record is compared
by its own verified direction and a pair by the one direction its directional families share.
**[as built]**

**B-A11. EpiGraphDB trait mapping.** Gap: the verifier's tiers mapped 73 of 225 snapshot traits.
Rule **[decided]**: the reference screen is kept and the mapping extended on the snapshot's trait
names alone: (1) a committed alias table, resolved by script from a seed of 65 trait names and
term labels (`verification/epigraphdb_trait_alias_seed.csv`), is read first; (2) a trait name
that gives no identifier as written and contains ": " (the UK Biobank field names) is mapped
from the text after its last ": ", without a leading ICD-10 code. With N1, 187 traits map (79 as
written, 43 by the colon rule, 65 by alias), 38 stay unmapped (compound, questionnaire or
procedure traits with no single term) and none is ambiguous; estimates on mapped pairs rise
from 48,565 to 145,037 of 179,928. A pair on an unmapped trait is `mapping_failed`, never
`no_returned_record`. **[changed] [S: names_as_written_only] [Q9]**

**B-A12. `pleiotropic_locus_named`.** Rule: set when any abstract holding one of the hub's
counted claims names a list gene as a case-sensitive whole symbol; short symbols that are also
abbreviations are a stated limit. **[as built]**

**B-A13. Null results and hubs.** See N2. **[changed]**

**B-A14. `related_prior_claim`.** Rule: another family's strictly earlier claim on an ancestor
or descendant outcome at any distance. **[as built]**

**B-A15. Novelty unit.** Rule: claim records. **[as built]**

**B-A16. Pair families.** Rule: every registry pair is an anchor; the number with a one-step
relative is reported beside. **[as built]**

**B-A17. Within-family discordance.** Rule: scopes differ when no `raises` record shares a
`claim_scope` with a `lowers` record. **[as built]**

**B-A18. Contradiction sources.** Rule: side against side, each the union over its families;
datasets by release identity; `platform` and `ancestry` as folded strings. **[as built]**

**B-A19. Participant-overlap share.** Rule: `known_not_overlapping` when `disjoint` on either
side for at least two families. **[as built]**

**B-A20. Dictionary-failure sensitivity.** Rule: admits records whose only failure is
`protein_not_in_span` or `outcome_not_in_span`. **[as built]**

**B-A21. Family–pair removals.** Rule: removal drops the family's records on that pair.
**[as built]**

**B-A22. Registry record.** Rule: a family whose journal abstract is ineligible is not an
eligible family; the window is read from the family date. **[as built]**

**B-A23. Median for the bound.** Rule: over eligible families whose extraction succeeded,
zero-claim families included. **[as built]**

**B-B1–B9.** Adopted as built: every Homo sapiens row of the Reactome file (B1); 2,926 reviewed
accessions on Olink Explore 3072 (B2); one edge per canonical identifier (B3); EpiGraphDB
exposures through the verifier's protein tiers (B4); estimates of traits sharing an outcome
pooled (B5); the `mrres` responses (B6); families per year by family date (B7); the bootstrap
and the joins run on Modal (B8); a claim's date is the earliest family abstract holding the pair
(B9, with S19).

**B-C. Pathway-level direction.** The prereg stands: no direction at pathway level.

## Found while the build was put together

**N1. Outcome names that also label a phenotype term.** Gap: the verifier returns HP, OBA and
Orphanet terms that the EFO file imports, so "rheumatoid arthritis", "ischemic stroke",
"systemic lupus erythematosus", "amyotrophic lateral sclerosis", "eczema" and "autism" each gave
a MONDO and an HP identifier and would have been `pair_ambiguous`. Of 156,053 labels and exact
synonyms, 1,965 give several canonical identifiers. Rule: when a name gives at least one MONDO
or EFO identifier, its identifiers from other ontologies are dropped; this resolves 921 names.
Why: the registered canonical identifier is a MONDO or an EFO term. **[changed] [Q1]**

**N2. Claims reporting no significant estimate.** Gap: "no causal effect of X on asthma" is
wording class `causal`. Rule: a claim whose direction is `reported_nonsignificant_or_null` does
not count toward hubs, the enrichment claimed sets or claim–trial-history co-occurrence. Why: it
asserts no effect. **[changed] [S: null_result_claims_counted] [Q2]**

**N3. Names shared by a MONDO term and an EFO term.** 704 names are the label or exact synonym of
one MONDO term and one EFO-file term that the pinned files do not assert to be one concept
("lung adenocarcinoma", "acute cholecystitis", "uterine fibroids"); 238 give several MONDO terms
and 93 several EFO terms (mostly abbreviations and assay names). Rule: unchanged, they give no
pair and are counted `pair_ambiguous`. **[as registered] [S: shared_names_mondo_first] [Q1]**

**N4. Missing pieces of the run.** Built: the funnel across stages with stage-to-stage checks
(`funnel.py`); negative-control specificity per stratum (`negative_control_specificity.py`) and
the fetch of the control abstracts after the freeze; the selection of eligible records for
extraction and chasing (`select_eligible.py`); registry and sensitivity scripts that read the
search and every chase round; the stage-6 census of full texts with the registered family
statuses and a concordance entry point; one Modal job for the whole test suite and the three dry
runs; `RUNBOOK.md` with the order of every command. **[changed]**

**N5. Manual coding of unresolved dataset names.** Rule **[decided]**: (1) trigger: a dataset
name on a registry claim whose automatic mapping is `release_ambiguous` or `unmatched`;
(2) source: the paper's methods or data passage, open-access full text where available, else
the abstract; if neither states it the row stays unresolved and is counted; (3) record: the
quoted sentence pinned with `citations`, the coded dictionary row and a `manually_coded` flag;
(4) scope: dataset and platform identity only; (5) three checks, all recorded: Claude Code
codes, Perplexity checks without seeing the coded value, the author verifies; a row is coded
only when all three agree, a disagreement is resolved by rereading with the original answers
kept, and agreement at the second check is reported as a count; (6) reporting: the number of
manually coded rows per analysis. The 14 platform lookups are the first use.
**[changed] [S: without_manual_dataset_coding] [Q10]**

## Sensitivity analyses added (14 names, 16 analyses)

| name | changes | point |
|---|---|---|
| `all_document_types` | records of class `other` kept | S1 |
| `without_citation_chasing` | families found only by chasing removed | S3 |
| `claim_dates_from_registry_abstracts_only` | novelty dated without preprint abstracts | S19 |
| `shared_names_mondo_first` | one MONDO identifier beside EFO identifiers is taken | N3 |
| `without_manual_dataset_coding` | manual codes not applied (H1, H2, enrichment) | N5 |
| `clinical_trial_reports_only` | non-trial reports are not records | D-A2 |
| `unflagged_reports_only` | reports with a quality-control flag not read | D-A4 |
| `single_drug_single_disease_reports` | only one-drug, one-disease reports read | D-A5/A6 |
| `completed_trials_as_completed` | a COMPLETED trial sets `completed_no_later_record` | D-A1 |
| `null_result_claims_counted` | null-result claims count (co-occurrence, hubs, enrichment: three analyses) | N2 |
| `distinct_therapeutic_areas` | hub = at least 3 distinct disease areas | B-A1 |
| `any_candidate_row_attachment` | a name gives every list of any candidate row | B-A5 |
| `alternative_assay_lists` | Zheng 2020 background = union of the five studies' assays | B-A3a |
| `names_as_written_only` | reference screen with the traits that map as written | B-A11 |

The gate-sample share (S3) is reported beside the funnel. Together these cover the readings the
build left open: status classes, non-trial reports, flagged reports, combination and
multi-disease reports, document types, chase scope, disease categories, platform attachment and
EpiGraphDB coverage.

## Questions that need a domain judgment

- **Q1 (N1, N3).** Is dropping HP, OBA and Orphanet candidates beside a MONDO or EFO identifier
  right? Should a name shared by one MONDO term and one EFO term (704 names) take the MONDO term
  in the primary analysis? Should a name whose only match is an HP term ("hypertension" maps to
  HP:0000822 alone) be given a MONDO alias?
- **Q2 (N2).** Should a record reporting no significant estimate count as a `causal` or `target`
  claim for hubs, enrichment and trial-history co-occurrence?
- **Q3 (D-A2, D-A4).** Should non-trial reports and quality-flagged reports be read in the
  primary analysis, or only in a sensitivity analysis?
- **Q4 (B-A1).** Confirm the hub rule (outcomes not coverable by fewer than 3 disease areas),
  the three areas left out as not disease areas, and the nearest-ancestor rule for the 31% of
  MONDO disease terms the Open Targets file does not carry.
- **Q5 (B-A3).** The 14 platform lookups: answer the blind question file before reading our
  values. Is the instrumented-protein universe right for the Zheng 2020 set, and is the pinned
  1.3k list an acceptable approximation for the Jackson Heart Study?
- **Q6 (S3).** Is the prefilter gate with a measured sample acceptable for chased records?
- **Q7 (S19).** Is dating a preprint's claims by its first publication date, with the abstract
  Europe PMC holds, acceptable?
- **Q8 (S26).** Should a wording keyword that occurs only inside the record's
  `outcome_as_written` be ignored?
- **Q9 (B-A11).** Are the 65 trait aliases right, and are the 38 traits left unmapped rightly
  left?
- **Q10 (N5).** Is the manual-coding rule sound as registered, and does it leave H1 and H2
  confirmatory?
