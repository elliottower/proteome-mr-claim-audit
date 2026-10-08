# Does reading full texts and supplements resolve whether repeated protein–outcome claims rest on the same data releases?

Sections use the [OSF Preregistration](https://osf.io/prereg/) question titles verbatim, so
this maps onto a registration without being rewritten. A question that does not apply is
answered **N/A** with the reason, never deleted.

**Status:** DRAFT, not frozen. Nothing in this stage has been fetched, coded or run.

This plan is a prospectively registered, post-results follow-up analysis of Paper 1 of
`proteome-mr-claim-audit` (`experiments/02_claims_meta/PREREG.md`, registered at
https://osf.io/zae8c). It is registered separately, in an OSF registration of its own linked to
that one. It is not a confirmatory analysis, a planned analysis of Paper 1, a validation or a
replication of Paper 1, or an amendment to its registration. Paper 1's H2 and H2b verdicts
remain the registered results.

It reuses Paper 1's definitions unchanged: canonical pair, study family, repeated pair, dataset
dictionary, set-valued dataset mapping, family datasets, dataset relation, release identity,
`known_identical`, `known_not_identical`, `known_overlapping`, `known_not_overlapping`,
`unresolved`, the bounds LB, UB, LB_b and UB_b, and the threshold of one half (§Research
questions, §Measured variables, §Indices and §Inference criteria of that plan). Four rules are
added to feed those definitions and are marked **added rule** where they stand. Where this
file is silent, Paper 1's plan governs.

## Research questions or hypotheses

Paper 1 classed repeated pairs from what abstracts state, and both verdicts came out
unresolved. How much release identity can be recovered from the full texts and supplements of
the same papers, and what are the H2 and H2b classifications then?

**H2-R.** Among the repeated pairs of Paper 1, more than half are `known_identical` when each
family's datasets are those identified by the primary rules below from the abstract, the full
text and the supplements.

**H2b-R.** Among the same pairs, more than half are `known_overlapping` under the same
resolution.

**H1-R.** Among the same pairs, the proportion whose `independent` edges all join families of
the same direction, under the same resolution; an estimate without a verdict, as H1 is.

**C1.** The coding pipeline recovers the release of control mentions whose release follows
mechanically from a hard identifier (positive control).

**C2.** The mechanical cut of sources into passages loses no release statement.

H2-R carries the design. C1 gates it: without C1, a rise in resolved pairs is consistent with a
pipeline that assigns releases wrongly. H2-R, H2b-R and H1-R are follow-up estimands defined
after Paper 1's results were seen.

Two registered outcomes would strengthen the papers under examination. A contradicted H2-R
shows, in Paper 1's sense, that at most half of repeated pairs rest on identical releases. A
high `confirmed` share among the abstract-to-full-text transitions shows that what abstracts
state about their data agrees with the full papers.

## Foreknowledge of data or evidence

The registered results of Paper 1 are seen. Amended primary analysis: 245 repeated pairs; H1,
0 pairs with an independent edge, no estimate; H2 unresolved, 0 known identical, 11 known not
identical, 234 unresolved, bounds 0.000 to 0.955; H2b unresolved, 8 known overlapping, 5 known
not overlapping, 232 unresolved, bounds 0.033 to 0.980. Originally registered analysis: 242
repeated pairs, the same verdicts, bounds 0.000 to 0.955 and 0.033 to 0.979.

A diagnostic made after those results is seen, in counts. For H2, 534 dataset mentions in 255
papers block the 234 unresolved pairs: 369 are sides on which the abstract names no dataset,
116 name a resource without an identified release, 46 name a dataset absent from the
dictionary, 3 have conflicting identifiers. 46 unresolved pairs have a family whose dataset
attribution is unclear. By pattern, among the 165 blocking mentions that name a dataset, the
stored passages hold a sample size or case and control count for 74 and a GWAS accession for
11. Among all mentions of the registry, 31 names as written hold a release number or an
accession (12 of them in repeated pairs).

An availability count from metadata is seen: of the 266 papers behind any repeated pair, 65
have a full text on disk, 84 more have an open-access full text in Europe PMC, 12 have a full
text there not flagged open access, 66 are open access by OpenAlex only, 37 are closed and 2
returned no status; Europe PMC lists supplementary files for 141.

The author and the coding agents have read passages of 242 full texts during the manual coding
of Paper 1, and the 197 codes that resulted. One external review of a first draft of this plan
has been read; it changed the rules below.

A calibration to choose the two models and to measure the passage cutter is planned on 24
papers outside the scope (§Study design); it has not been run. Its counts are written here
before the freeze.

Three files of one record (PPR989506) were downloaded by the author from an open page and are
stored unread. No full text has been read for this stage, no supplement has been fetched by a
script, and no rule below has been applied to any paper.

## Explanation of foreknowledge and managing unintended influences

This stage was designed after its motivating result was known: that H2 and H2b were unresolved,
and why. What that costs: its estimands are follow-up estimands, never confirmatory; every
table that shows them is labelled as the post-results follow-up; they are reported beside
Paper 1's registered verdicts and never replace them. The paper says so in these words or
close to them: "After the registered analyses produced unresolved H2 and H2b verdicts, a
separate follow-up analysis was preregistered to determine how much release identity could be
recovered from full texts and supplements. Its results do not replace the registered
abstract-based results."

What limits the influence: Paper 1's definitions and threshold are unchanged; the rules are
deterministic and frozen before any source is retrieved for this stage; every dataset side of
every paper behind a repeated pair is coded, whatever its class in Paper 1; coders, the checker
and the author never see a pair's other families, a relation class or any aggregate while
coding; and C1 is computed and logged before H2-R is opened.

## Study type

Observational, meta-research: a second coding of documents already in a registered corpus.

## Intention for causal interpretation

N/A — no causal claim.

## Blinding of experimental treatments

N/A — no treatment.

## Additional blinding during research or analysis

Coders and the checker receive, per row: the record, the side, the name as written or `not
stated`, for an outcome-side row the outcome as the claim writes it, the frozen retrieved files
of the record, the candidate dictionary rows and the two reference tables. They have no web
access and receive nothing else: no other family's assignment, no relation class, no
aggregate, no Paper 1 code. The author adjudicates and audits under the same blinding and does
not open H1-R, H2-R or H2b-R classes until every code is committed. Control rows are not
distinguishable from study rows.

## Study design

**Corpus.** The claim records, families and repeated pairs of Paper 1's amended primary
analysis (`outputs/registry/2026-10-03_amended_primary_coded_a`), fixed. No record is added or
removed. The originally registered corpus of Paper 1 (242 pairs) is rerun with the same codes
and reported beside it.

**Scope.** All 266 papers with a claim in a repeated pair; every dataset side of every such
claim, including names that already map to one release from the abstract. The corpus is not
widened to papers outside repeated pairs, except for control-only rows (C1).

**Unit.** One row per record, side and name as written; on a side where the abstract names no
dataset, one row per record and side (pQTL) or per record, side and outcome as written
(outcome). A row returns:

| field | values |
|---|---|
| identified releases | a set of dictionary rows, possibly empty |
| analysis role, per release | `primary`, `meta_analysis_component`, `replication`, `sensitivity` |
| attribution state | `explicit`, `paper_wide`, `unresolved` |
| unresolved reason, when the set is empty | `release_not_identified`, `conflicting_identifiers`, `dataset_absent_from_dictionary`, `attribution_unresolved`, `no_source`, `source_unreadable`, `version_not_linked` |

Only the sources that contribute to the estimate the claim states are coded. A meta-analysis
is coded to its dictionary meta-analysis row when there is one, else to the set of its
documented components; never to its first or largest cohort. Discovery, replication and
sensitivity datasets stay apart: a release enters with role `primary` or
`meta_analysis_component` only when it produced the estimate of the abstract's claim, and
replication or sensitivity releases enter only when the abstract's claim combines them. The
same holds on the pQTL side for instrument discovery and replication cohorts.

**Identification rules.** Every applicable rule is applied to every row; none stops at a first
match.

| evidence | status in the primary analysis |
|---|---|
| D1. An explicit release number or a dataset accession, attributed to the analyzed dataset of the side, that the pinned table `reference/accession_releases.csv` or the dictionary maps to one row | decisive |
| D2. A uniquely identifying citation or source DOI attributed to the analyzed dataset, whose cited analysis maps to exactly one dictionary row (reference entry verified by DOI, else PMID, else PMCID, as in Paper 1) | decisive |
| S1. Exact case and control counts, with the resource named and the endpoint identical under the endpoint scheme below, equal to those of releases in `reference/release_counts.csv` | candidate-supporting only |
| A total sample size; a rounded, maximum, effective, subset or post-quality-control count | decides nothing and supports nothing |

| combination | result |
|---|---|
| every decisive rule that applies names the same row (or the same set) | resolved to it |
| two decisive rules, or two passages under one rule, name different rows | `conflicting_identifiers` |
| a decisive row and count evidence S1 that excludes it | `conflicting_identifiers` |
| no decisive rule applies | unresolved in the primary analysis; S1 evidence is recorded as a count-only candidate set |

Count evidence confirms a decisive row, contradicts it, narrows a candidate set, and feeds the
count-inferred sensitivity analyses; it never creates a release identity in the primary
analysis.

**Abstract against full text**, for a name the abstract already resolves or states:

| situation | result | transition recorded |
|---|---|---|
| the full text names the same release | that release | `confirmed` |
| the full text gives a more specific release consistent with the abstract's name | the specific release | `refined` |
| abstract and full text identify different releases for the same analyzed estimate | `conflicting_identifiers` | `contradicted` |
| the full text describes several analyses and the abstract's estimate cannot be linked to one | unresolved | `unresolved` |
| a supplement gives the release for the exact analysis and the prose is generic | the supplement's release | `refined` |
| a later passage describes a sensitivity or replication analysis | does not replace the primary claim's dataset | none |

**Attribution (added rule 1).** In Paper 1 a family's attribution on a pair is `unclear` when
the extraction marks any of its records so. Here a record's attribution can be settled from
the full text, and only by an explicit link of a dataset to the analysis and side:

| the source says | attribution |
|---|---|
| protein instruments (pQTLs) were obtained from X | resolves the pQTL side |
| summary statistics for outcome Y were obtained from X | resolves the outcome side for Y |
| a methods table links phenotype, sample and source | resolves the rows it lists |
| "we used datasets X and Y", without side or phenotype | resolves neither |
| one paper-wide statement, and the paper reports one exposure source and one outcome source with no alternative | resolves all its claims (`paper_wide`) |
| several datasets jointly produced the estimate | the complete set is kept |
| several analyses, and the abstract's claim cannot be linked to one | stays unclear |

A record whose attribution is settled this way is read as clear when the family datasets are
formed; one that is not stays unclear, as in Paper 1. The 46 pairs held by unclear attribution
are not held by default.

**Feeding Paper 1's definitions.** Paper 1 forms a family's datasets on a pair as the union,
per side, of the names on its records, and compares the sets of releases two families name;
sets are already what its definitions compare. Three more rules are added, each only to put a
code into that union, and none changes a definition:

- **Added rule 2.** A row may be coded to several dictionary rows; each enters the family's
  side as a name that maps to that row. (Paper 1 coded one name to one row.)
- **Added rule 3.** A side on which the abstract names no dataset may be coded; its coded rows
  replace `not_stated`. (Paper 1 queued only ambiguous and unmatched names.)
- **Added rule 4.** Only releases with role `primary` or `meta_analysis_component` enter the
  family's side; `replication` and `sensitivity` releases are recorded and do not enter.

A meta-analysis coded to its components and the same meta-analysis coded elsewhere to its
dictionary row are different release sets under Paper 1's definition and are not
`known_identical`; such pairs are counted (`meta_analysis_row_against_components`). The
dictionary is Paper 1's and is not extended: a dataset with no row is
`dataset_absent_from_dictionary`.

**Endpoint identity for count evidence.** Counts support a release only for the identical
endpoint. Two endpoints are identical when all of these agree, and a field the source does not
state is a mismatch: disease or trait against subtype; incident against prevalent; sex; ancestry;
case definition (the resource's endpoint code where it has one); quantitative against binary;
single cohort against meta-analysis.

**Reference tables.** `reference/accession_releases.csv` and `reference/release_counts.csv`
are built from the resources' own per-release manifests and committed, with their sha256,
before the freeze and before any retrieval. Columns of both: resource; release identifier;
dictionary row; provenance (URL of the manifest, access date, sha256 of the stored file).
Further columns of the counts table: endpoint label; endpoint code; canonical outcome
identifier; count type (cases, controls) and scope; sex; ancestry; genome build where the
resource states one; and `duplicate_count`, the number of releases of the resource that hold
the same case and control counts for the endpoint. A resource with no pinned manifest gives no
count evidence. A later database manifest never rewrites what a paper used.

**Sources.** A source is eligible only when its provenance, version and sha256 are recorded
and it was obtained by one of these routes:

| route | what |
|---|---|
| R1 | the Europe PMC full-text XML of the record, rendered as in Paper 1; a full text stored for Paper 1 is eligible when its record of provenance and its sha256 match a fresh listing of the same Europe PMC file |
| R2 | the supplementary files Europe PMC lists for the record |
| R3 | for a record with no Europe PMC full text, the file at the open-access location OpenAlex gives, when a plain HTTP request returns it |
| R4 | a file the author downloaded by hand from an open page, with the URL, the date and the sha256 recorded in the log before it is read; used only where R1 to R3 return nothing for the record |

No publisher site is logged into, no paywalled copy is used, no browser is automated, no
request imitates a browser, and no request carries an e-mail address. A request is tried three
times, 60 seconds apart; a record with no file after that is `no_source`. Accepted types: JATS
XML, PDF, plain text, HTML, CSV, TSV, XLSX, XLS, DOCX, and ZIP archives of these. A PDF is
converted with `pdftotext -layout` (poppler, version pinned in the image); a file of another
type, a scanned PDF with no text layer, or a table over 50 MB is `source_unreadable`, counted,
and its rows are coded from the record's other sources.

**Versions.** The source of a record is the version tied to its study family by Paper 1's
version-linking rule (`scripts/link_families.py`), in this precedence: journal full text;
correction or erratum explicitly linked to it, which supersedes the passage it corrects;
supplement of that version; preprint of the same family; a repository README or deposit of the
same family. A record that is a data or code deposit of a study, or a later version under a
new title, takes the full text of the published version only when Paper 1's rule links the two
in one family. Where the rule does not link them, the record keeps only its own retrievable
files, its rows are coded from those or are `version_not_linked`, and nothing is merged by
hand; such records are listed.

**Checks.**

| step | who | what |
|---|---|---|
| first coding | a model of one family | every row, one paper at a time, from the frozen files |
| closed-packet check | a model of a different family | the same rows and files, without the first value |
| provenance and identifier gate | script | every accepted mapping: the quotation is pinned with `citations` in a frozen file of the record; the pinned text holds the decisive identifier; the identifier maps to the coded row in the table or dictionary; for D2 the reference entry verifies |
| adjudication | the author | every row on which the two models differ, after a blind reread |
| audit of agreements | the author | a seeded sample of 10% of the rows on which the two models agree, at least 30 rows |

A row is accepted only when the two models agree, or the adjudication settles it, and the gate
passes. Two or more substantive errors in the audit (a wrong row, a wrong role or a wrong
attribution state) escalate to the author's review of every agreed row. Every initial answer
and every changed decision is kept.

The first coder and the closed-packet checker are the two models the calibration below
selects, each called through its API with no tools and no web access, the model string
returned recorded with every response (open choice 1 lists the candidates and their cost).
The first coder is never a Claude model when the checker is one, and the two are never of one
family.

**What the models read (open choice 2; one option is deleted before the freeze).**

| option | full text | supplements |
|---|---|---|
| passages | mechanically cut passages | mechanically cut rows |
| whole text | the whole rendered full text | mechanically cut rows |

**Passage rule**, applied by a sealed script to every source, the same for both models. From
a full text: every section whose title matches methods, materials, data, statistical analysis,
study population, GWAS, Mendelian randomization, instrument, code or data availability,
acknowledgement or funding; every table and its caption; and, anywhere else, every sentence
that holds a term of the dictionary (Paper 1's term rule), an accession pattern, a release
pattern or a count with "cases" or "controls", with one sentence either side. From a
supplement: every sheet or table name; the header rows; and every row that holds a dictionary
term, an accession pattern or a release pattern, with its header. The reference entries a
passage cites are attached as in Paper 1.

**C2, cutter retention.** A seeded sample of 30 papers with a full text (and, of those, every
supplement) is also read whole by the first coder in a separate pass. A miss is a row for
which the whole-text pass finds decisive evidence (D1 or D2, gate passed) that the passages do
not hold. Under option `whole text` the check concerns supplements only.

**Calibration before the freeze (development step; not yet run).** The two models are chosen
by a calibration that the author checks, on papers of Paper 1's corpus outside the 266 papers
behind any repeated pair, so that no study row is read before the freeze.

| element | rule |
|---|---|
| papers | a seeded draw of 24 eligible families' papers outside the scope, 6 in each stratum: Europe PMC XML with a listed supplement; Europe PMC XML without; open-access PDF with a supplement; open-access PDF without; giving about 40 to 60 dataset mentions |
| use | excluded from every index of this stage and never used as positive controls |
| truth | the author marks each mention from the cut passages on a page like the check pages of Paper 1: release stated, accession, citation, not identifiable, and the dictionary row where one is identifiable; blind to every model's answer. A mention with a hard identifier also gets its mechanically derived release, and the two are compared |
| candidates | GPT-6.1 Sol, Claude Sonnet 5.5, Claude Fable 5.1, and "Astra" if its vendor and model identifier are established; each codes the same passages with the same prompt |
| per model | recovery (identifiable mentions coded to the author's row); contradictions (identifiable mentions coded to another row); false identifications (not-identifiable mentions coded to a row) |
| exclusion | a model with more than 1 false identification, or more than 1 contradiction, is out |
| selection | among the models left, the two with the highest recovery that are of different families; a tie is broken by lower cost; the one with the higher recovery is the first coder |
| no pair | if fewer than two families are left, nothing is frozen: the prompt or the passage rule is revised, a new sample is drawn with a new seed from papers not yet used, and the calibration is run again; every run is logged |
| cutter | each candidate also reads the 24 papers whole in a separate pass; a deciding sentence it proposes that is not in the passages is shown to the author, who confirms or rejects it; with the mechanical scan for hard identifiers, this gives the mentions identifiable from the whole source; the cutter passes when at least 0.95 of them have their deciding sentence in the passages |
| cutter fails | the passage rule is revised and the calibration repeated on a new sample, or the reading option `whole text` is taken |

The calibration, its counts per model and the cutter's share are stated in §Foreknowledge
before the freeze, and the frozen plan names the two chosen models, their identifiers and the
sha256 of the prompt each receives. Retrieval for the calibration papers follows the source
routes below and is logged; it touches no paper of the scope.

**C1, the positive control.** Control mentions are those with a hard identifier: an explicit
release number, a repository accession, an explicitly attributed source DOI that maps to one
analysis, or a release-specific label. Their expected release is derived by script from the
identifier and the resource manifest, never from Paper 1's manual codes. The set is frozen
before coding from three pools, in this order, until it holds 100 or the pools are exhausted:
(a) mentions of the scope whose name as written holds a release number or accession; (b) the
same among registry mentions outside repeated pairs and outside the calibration papers, coded
as control-only rows that enter no index; (c) mentions whose pinned sentence in Paper 1's citations folder holds a release number
or accession found by the frozen pattern, the expected row derived from that identifier alone.
Control rows are mixed with study rows and not marked. A control coded to another row is a
contradiction and gets a blinded mechanical review (does the frozen source hold a second hard
identifier for the same side and estimate); a contradiction the review explains by the source
is reported apart and still counts.

**Order.** Reference tables pinned; calibration run and checked by the author; models and
reading option fixed; plan frozen and
registered; sources retrieved and frozen; passages cut; control set and C2 sample frozen; rows
coded and checked; C2 computed and acted on; codes committed; C1 computed and logged; registry
assembled; estimands computed.

## Randomization

N/A — nothing is assigned; papers are dealt to coding sessions and the audit sample is drawn by seeded shuffles.

## Data collection procedures

New versioned scripts, each tested and sealed before it runs; inputs sealed with `results
seal`; retrieval and coding logged with `prereg log`. Anything longer than two minutes runs on
Modal with checkpoints inside the loop and resumes from them. Every retrieved file is stored
with its route, URL, date and sha256 under an ignored path and listed in a withheld-files
record; no third-party text is committed. A paper whose source cannot be retrieved is never
dropped: its rows are unresolved and counted by reason.

**Tooling reused from Paper 1.** The passage cutter, the pages the author marks and the
readers of his marks are new versioned copies of Paper 1's tools, tested and sealed before
use; the originals are not edited.

| page or step | new copy derived from |
|---|---|
| passage cutter | `scripts/manual_coding_passages_v3.py` (sealed) |
| table of rows the author marks | `scripts/manual_coding_check3_table_v2.py` (sealed) |
| page builder for the calibration page, the disagreement page and the audit page | the page script that built Paper 1's check pages, which was not sealed and is not in the repository; the copy made here is the first sealed version |
| seeded draws (calibration papers, audit sample) | `scripts/manual_coding_check3_sample.py` (sealed) |
| reader of the author's marks | `scripts/manual_coding_check3_followup_v2.py` and `scripts/manual_coding_final_tables.py` (sealed) |
| provenance and identifier gate | `scripts/manual_coding_gates_v2.py` and `scripts/pin_passage_occurrence_v2.py` (sealed) |

Every page shows, per row: the passages, with the identifier or release string that decides
highlighted; a link to the open page of the source; the row's hash; one-click marks and a note;
and a button that saves the marks as a JSON file, whose sha256 is logged before it is read.
The calibration page shows no model answer. The disagreement page shows the two answers
without saying which model gave which, in an order shuffled per row by a seed. The audit page
shows the agreed answer.

| Paper 1 manual-coding artifact | role here |
|---|---|
| passage cutter, gates, pin helper, table and marks scripts, page script | tooling: new versioned copies |
| coder instructions v6 and the settled rules A to I4 and C1 to C5 | tooling: the basis of the new prompt, which is a new file with its own sha256 |
| dataset dictionary and dictionary definitions | input, unchanged |
| the 65 full texts stored for scope papers, with their raw XML | input, where eligible under route R1 |
| the claims folders of pinned sentences | input to control pool (c) only |
| the queues, passages and coder attempt files | not used |
| the 197 accepted codes and their extended tables | comparison only: reported beside this stage's codes for the same mentions, never the truth, never given to a coder or the checker |
| the second-check packets and answers | not used |
| the author's marks of Paper 1 | not used |

## Data collection procedures - File upload

N/A — no file beyond the repository.

## Sample size

266 papers behind 245 repeated pairs; about 667 study rows (311 pQTL, 356 outcome) on the
abstract-level names, the exact number fixed when the queue is built. From metadata, a full
text is on disk or reachable for 227 papers and not for 39. H2-R is supported with 123 or more
`known_identical` pairs and contradicted with 123 or more `known_not_identical` pairs.

## Sample size rationale

The corpus is Paper 1's and is fixed; no power calculation applies to a census.

## Starting and stopping rules

Retrieval starts after the freeze; coding stops when every row has a result or an unresolved
reason; no estimand is computed before that.

## Manipulated variables

N/A — nothing is manipulated.

## Measured variables

Per row: the fields of §Study design, unit; each rule's evidence with its pinned quotation and
file; count evidence as written, its endpoint fields and the table rows it equals; the two
models' answers, the gate result, the adjudication and the audit mark; the abstract-to-full-text
transition; the attribution transition. Per paper: each source by route, type, version, date
and sha256, and each failure by reason; year, journal, document class and platform.

## Measured variables - File upload

N/A — the two reference tables are files of the repository, pinned before the freeze.

## Indices

M, KI, KN, U, LB, UB, KO, KD, U_b, LB_b, UB_b, the resolvable share and the H1 concordance are
Paper 1's, computed by the same functions on the registry with the accepted codes applied
before the family datasets are formed.

| index | numerator | denominator or categories |
|---|---|---|
| C1 recovery | controls coded to the expected row | controls whose record has an eligible source |
| C1 contradiction | controls coded to another row | the same |
| C2 misses | sampled papers with a row whose decisive evidence is in the whole source and not in its passages | the 30 sampled papers; and rows |
| full-text resolution yield | mentions unresolved from the abstract (ambiguous, unmatched, not stated) that are resolved here | all such mentions of the scope; also by side |
| incremental yield by source | resolved mentions whose decisive evidence is in the full text only, in a supplement only, in both | resolved mentions |
| abstract-to-full-text transitions | `confirmed`, `refined`, `contradicted`, `unresolved` | mentions the abstract resolves to one release, with an eligible source |
| attribution transitions | unclear to resolved; unclear and still unclear | records with unclear attribution in Paper 1; and the repeated pairs they hold |
| count-only candidate mappings | mentions with no decisive rule and S1 evidence equal to exactly one release; to several | mentions with no decisive rule |
| accessibility-stratified resolution | resolved mentions | mentions, by route of the record's source (R1, R2 present, R3, R4, none) |
| source availability | papers with an eligible source | papers, by year, journal, document class and platform |
| pairs unresolved for want of a source | unresolved pairs that every other mention would class and at least one `no_source` mention holds | unresolved pairs |
| agreement with Paper 1's codes | mentions coded here to the row Paper 1 accepted; to another row; unresolved here | the mentions among Paper 1's 197 accepted codes that are in the scope; comparison only |
| pair movement | repeated pairs by class in Paper 1 and class here (3 by 3) | M, for H2 and for H2b |
| H2-R and H2b-R among fully accessible pairs | the bounds over pairs whose every paper had an eligible source | those pairs; descriptive, no verdict |

## Indices - File upload

N/A — none.

## Statistical models

None beyond Paper 1's finite-corpus bounds and its resampling-stability displays, computed by
the same functions.

## Statistical models - File upload

N/A — none.

## Transformations

N/A — none beyond Paper 1's.

## Inference criteria

| estimand | holds when |
|---|---|
| H2-R supported | LB > 0.5 |
| H2-R contradicted | UB ≤ 0.5 |
| H2-R unresolved | neither |
| H2b-R supported | LB_b > 0.5 |
| H2b-R contradicted | UB_b ≤ 0.5 |
| H2b-R unresolved | neither |
| H1-R | no verdict; the estimate with its Wilson interval; labelled imprecise on fewer than 20 pairs; not estimable when no pair has an independent edge |
| C1 | recovery ≥ 0.90 and contradiction ≤ 0.02, on at least 50 controls with an eligible source |
| C2 | misses in at most 1 of the 30 sampled papers |

The C1 thresholds are conventional operating values, not derived from data, and the paper
says so.

**If C1 fails, or rests on fewer than 50 controls, every release-resolution estimate that
depends on the coding pipeline is void: H2-R, H2b-R, H1-R, the yields and the transitions.**

**If C2 fails, every source that was cut is coded again whole by both models before any
estimand is computed, and the passages' codes are kept and not used.**

**What stands when C1 fails: the source-availability and retrieval counts, Paper 1's registered
results, and the report of the failure itself.**

**A verdict on fewer than 20 repeated pairs carries the label imprecise.**

The results of this stage are reported beside Paper 1's registered verdicts, which stand, in
tables labelled as the post-results follow-up. The two verdicts are read together by Paper 1's
table. The analysis among fully accessible pairs is descriptive and is never read as an
estimate for papers that could not be read.

## Data inclusion and exclusion

Every repeated pair of the corpus is in M, whatever was retrieved. No paper, mention or pair is
excluded.

## Missing data

A row with no source, no decisive rule, conflicting evidence or unsettled checks is unresolved
and enters the bounds as Paper 1's unresolved names do, never by exclusion. Inaccessible
papers stay in every bound as unresolved and are counted by reason.

## Other planned analysis

Each reported beside the primary, none replacing it:

| sensitivity analysis | what changes |
|---|---|
| count-inferred, exact case and control counts | a mention with no decisive rule and S1 evidence equal to exactly one release (`duplicate_count` 1) is resolved to it |
| count-inferred, exact total sample size permitted | as above, and an exact total sample size equal to exactly one release of the named resource for the endpoint also resolves |
| all count-only mappings unresolved | equal to the primary analysis by construction; stated so in the table |
| Europe PMC sources only | routes R3 and R4 give no source |
| without attribution resolution | added rule 1 is not applied; Paper 1's attribution stands |
| originally registered corpus | Paper 1's 242 repeated pairs |

Anything else is labelled as made after the results.

## Context and additional information

Review before any freeze: external review rounds on this draft until one confirms it. The
freeze uses `prereg freeze` and an OSF registration of its own, linked to
https://osf.io/zae8c.

**Open choices to settle before the freeze.** (1) The models, settled by the calibration; the
author's leaning is passages for both models. Estimates for about 282
requests per model (266 papers and up to 16 control-only papers), from the lengths of the 65
stored full texts of the scope (mean 40,173 characters, about 10,000 tokens), a fixed prompt of
about 20,000 tokens (instructions and dictionary definitions, cached after the first request),
about 1,500 output tokens per paper, and list prices per million tokens of 2 and 10 US dollars
(GPT-6.1 Sol; Claude Sonnet 5.5) and 10 and 50 (Claude Fable 5.1); supplement text is not
measured yet and the figures can double:

| option | first coder + checker | different families | input tokens per model | output tokens per model | cost, US dollars | wall time on Modal |
|---|---|---|---|---|---|---|
| a | Sol + Sonnet 5.5, passages | yes (OpenAI, Anthropic) | about 1.6 million new, 5.7 million cached | about 0.4 million | about 8 + 8 = 16 | under 30 minutes |
| b | Sol + Sonnet 5.5, whole full texts | yes (OpenAI, Anthropic) | about 3.0 million new, 5.7 million cached | about 0.4 million | about 11 + 11 = 22 | under 30 minutes |
| c | Sol + Fable 5.1, passages | yes (OpenAI, Anthropic) | as a | as a | about 8 + 38 = 46 | under 30 minutes |
| d | Astra + Fable 5.1, passages | yes by the label, not established by a model identifier | as a | as a | not priced | not estimated |

Option d: the project's records name "Astra" once, as "Astra GPT-6 Thinking", a configuration
of the Perplexity web interface used in the second-check pilot of Paper 1; by that label it is
an OpenAI GPT-6 model and of another family than Fable (Anthropic). No record gives its API
model identifier or its price, and the environment holds an OpenAI key and no key named for
it, so it is not priced here and cannot be written into the plan until its identifier is
established.

(2) Passages or whole full texts. (3) Whether pool (c) of the control set is acceptable, given
that only 31 mentions of the registry carry a hard identifier in their name as written.

**Maximum claim under this registration.** Among this fixed corpus, using the retrieved
sources and registered identification rules, the share of Paper 1's 245 repeated pairs that
rest on identical releases lies between LB and UB, and the share that rest on identical
releases or documented shared participant-source components between LB_b and UB_b, each with
the verdict the one-half rule gives; these are results of a post-results follow-up analysis,
they are statements about the retrieved corpus, and they stand beside Paper 1's registered
unresolved verdicts without replacing them. The paper can also state, each with the
denominator registered above: the directional concordance of independently sourced pairs
under the same resolution, without a verdict, or that it is not estimable; the full-text
resolution yield, the number and proportion of mentions unresolved from the abstract that a
decisive rule resolved, by side; the incremental yield of the full text and of supplements;
how often the full text confirmed, refined or contradicted what the abstract stated about a
dataset; how many records with unclear attribution were settled by an explicit link and how
many stayed unclear; how many mentions had only count evidence, and the result when those
count-only mappings are admitted; resolution by route of access and source availability by
year, journal, document class and platform; how many repeated pairs changed class, how many
stayed unresolved, and how many of those for want of an accessible source; the bounds among
pairs whose every paper could be read, as a description; and that the coding pipeline
recovered hard-identifier controls at the registered rate, or that it did not and the
resolution estimates are void. It cannot state that a release was not reported anywhere
because the retrieved sources did not identify it, that repeated claims rest on the same or
on different participants, that count agreement identifies a release, anything about papers
that could not be read or papers outside the corpus, or that this analysis was confirmatory
or planned before the results of Paper 1 were seen.
