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
added to feed those definitions and are marked **added rule** where they stand. H2-R and H2b-R
reuse Paper 1's mathematical relation definitions but change their operational inputs through
the four prospectively registered full-text coding rules: they are augmented full-text coding
estimands, not Paper 1 rerun on longer documents. Where this file is silent, Paper 1's plan
governs.

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

**C1.** The coding pipeline extracts a hard identifier that a source states and maps it to the
dictionary row it denotes (positive control of identifier extraction and mapping; it does not
test attribution of a dataset to the right analysis).

**C2.** The mechanical cut of supplements that cannot be rendered whole loses no decisive
release statement.

H2-R carries the design. C1 gates it: without C1, a rise in resolved pairs is consistent with a
pipeline that misreads or mis-maps the identifiers it finds. Attribution to the right analysis
rests on the two independent models, the gate and the author's adjudication and audit, not on
C1. H2-R, H2b-R and H1-R are follow-up estimands defined
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
of Paper 1, and the 197 codes that resulted. Five external reviews of earlier drafts of this plan
have been read; they changed the rules below. An external answer proposing secondary analyses
has been read; four of the seven secondary analyses below come from it. The documents read to build the meta-analysis
expansion table are listed in it.

The two models were chosen by the author on cost and family, without a calibration test of
candidate models. The paper therefore cannot claim that the models were chosen on measured
performance against a reading of whole sources, and cannot report a rate of false
identification on mentions that are not identifiable measured before the stage; the error it
reports is the error found in the author's audit of agreements and in C1, which bounds errors
among accepted codes and says nothing about models not used.

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
of the record, the candidate dictionary rows, and the accession-table rows of every accession
the frozen accession patterns find in those files together with the OpenGWAS batch-prefix rows;
the dictionary definitions are part of the fixed prompt. The counts table is not given to them:
the count evidence they record is compared with it by script. They have no web
access and receive nothing else: no other family's assignment, no relation class, no
aggregate, no Paper 1 code. The author adjudicates and audits under the same blinding and does
not open H1-R, H2-R or H2b-R classes until every code is committed. Control rows are not
distinguishable from study rows. The abstract-only packets of secondary analysis SA1 hold the
record's abstract and nothing else, and are coded in requests separate from the full-text ones.

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
| ancestry, per release | as the source states it, or `not_stated` |
| attribution state | `explicit`, `paper_wide`, `unresolved` |
| unresolved reasons, every one that applies: any reason when the set is empty; `attribution_unresolved` also whenever the attribution state is `unresolved`, whatever the set | `release_not_identified`, `conflicting_identifiers`, `dataset_absent_from_dictionary`, `attribution_unresolved`, `no_source`, `source_unreadable`, `version_not_linked` |

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

**Abstract evidence.** Abstract evidence is available for every included record and is always
evaluated under D1 and D2, by the same frozen rules as the full text. Failure to retrieve an
eligible full text or supplement prevents refinement or confirmation but does not erase a
release decisively identified from the abstract. A row is `no_source` only when both hold: no
eligible source other than the abstract was retrieved for the record, and the abstract supplies
no decisive evidence. A row whose record has a readable retrieved source that holds no decisive
identifier is never `no_source`; it takes `release_not_identified` or another substantive
reason. Paper 1's accepted manual
codes are not inherited: the rules are applied afresh.

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

**Meta-analysis canonicalization.** When a set of component releases exactly equals the
frozen, exhaustive component expansion of one and only one dictionary meta-analysis row,
matching endpoint, ancestry, analysis version and component roles, the set is canonicalized to
that meta-analysis row before family relations are computed. Canonicalization is prohibited
when components are missing, additional components are present, versions are unresolved, or
more than one meta-analysis row is compatible. It harmonizes two encodings of one registered
analysis and does not redefine `known_identical`. Expansions are read only from the frozen table
`reference/meta_analysis_expansions_v2.csv`, one line per component, in the columns
`meta_analysis_row`, `component_dictionary_row`, `endpoint`, `ancestry`, `analysis_version`,
`component_role`, `provenance_url`, `access_date` and `documents_sha256`.
The table is built before the freeze, and every one of the 14 meta-analysis and combination
rows of Paper 1's dictionary is decided in it: a row is expanded only when every contributing
release, endpoint, ancestry, version and role is explicitly documented in the resource's own
documentation and every contributing release is a dictionary row; nothing is inferred from
cohort names, dates or counts. Omitted rows are listed with their reason in
`reference/meta_analysis_expansions_omitted_v2.csv`, frozen with the table, each with its basis:
a decision resting on the resource's documentation (`external_documentation`) carries the URL,
access date and sha256 of every document it rests on; a decision resting on the frozen
dictionary alone (`frozen_dictionary`) cites no document; every row carries the dictionary's
version and sha256. Built on 10 October 2026 (`scripts/meta_analysis_expansions_v2.py`,
decisions in `reference/meta_analysis_expansion_decisions_v5.json`, the 9 documents stored by
script under an ignored folder): none of the 14 rows is expanded; 11 omissions rest on
documentation and 3 on the dictionary. Three
are single-study releases with no component releases; ten have a contributing release that is
not a dictionary row (an author's own UK Biobank analysis, the Million Veteran Program, CIMBA,
SCALLOP cohorts, the CARDIoGRAMplusC4D Metabochip meta-analysis); in one (FinnGen R12 with UK
Biobank) the UK Biobank side is redefined for some endpoints and which endpoints is not in the
documentation. Canonicalization therefore changes no comparison in this stage, and the
sensitivity analysis without it equals the primary analysis by construction. The coder records, for
each release of a row, its ancestry as the source states it, so that the ancestry of a coded
set can be compared with an expansion. A comparison of a family side coded to a meta-analysis
row with another coded to a set of its components, where that row has no expansion, is
`representation_unresolved`, which enters the bounds as `unresolved`, never as
`known_not_identical`. The pairs affected by canonicalization and those left
`representation_unresolved` are counted, and a sensitivity analysis runs without
canonicalization. The dictionary is Paper 1's and is not extended: a dataset with no row is
`dataset_absent_from_dictionary`.

**Endpoint identity for count evidence.** Each of these fields is compared between the source
and the reference table: disease or trait against subtype; incident against prevalent; sex;
ancestry; case definition (the resource's endpoint code where it has one); quantitative against
binary; single cohort against meta-analysis. A field is `match` when both state it and agree,
`conflict` when both state it and disagree, and `unknown` when at least one does not state it.
Count evidence with any `conflict` supports nothing. Count evidence with an `unknown` field
enters only the compatible count sensitivity analysis and never confirms or contradicts a D1 or
D2 mapping; only count evidence whose every field is `match` may confirm or contradict one.

**Reference tables.** `reference/accession_releases.csv` and `reference/release_counts.csv`
are built from the resources' own per-release manifests and committed, with their sha256,
before the freeze and before any retrieval. Columns of both: resource; release identifier;
dictionary row; provenance (URL of the manifest, access date, sha256 of the stored file).
Further columns of the counts table: endpoint label; endpoint code; canonical outcome
identifier; count type (cases, controls) and scope; sex; ancestry; genome build where the
resource states one; and `duplicate_count`, the number of releases of the resource that hold
the same case and control counts for the endpoint. A resource with no pinned manifest gives no
count evidence. A later database manifest never rewrites what a paper used.

Built on 10 October 2026, before the freeze. `scripts/fetch_reference_sources.py` (sha256
4fc637d9733bcacc25184f6c0f9ae332ebcb66628969bb6db1395a7e80789dbb) stored the 189 documents listed
in or linked from `reference/reference_table_sources.json` (sha256
86a971d4c9b921948aa0ea35f9c6a0acdfe5bb1800457df034a2edef48ed0d5f), each manifest from the URL its
resource's documentation states; `scripts/build_reference_tables.py` (sha256
4ed52720d8d870f7286d90316f8b77106ff7bec2bfdd6a0d4bad0c4a86fac0b9) wrote the tables, a row only
where the stored document states the value.

| table | sha256 | rows | from |
|---|---|---|---|
| `reference/accession_releases.csv` | 5263df292a20b0762a3383a6a43aae92cbe1496884c3abb205623878b555156e | 11,937 | 5 OpenGWAS batch prefixes, by the batch list's own descriptions (`reference/opengwas_batch_rows.json`); 11,925 GWAS Catalog accessions of 28 publications; 7 OpenGWAS curated datasets of 6 publications |
| `reference/accession_releases_omitted.csv` | 7264672a4615476d448010b967627a6aec8c41114728a3f20e7bf763f7d100bd | 60 | publications and batches not mapped, with the reason |
| `reference/release_counts.csv` | b57fa5aaf7d68664973263a984186304ac60fecf8074d5ff4c69c9c79de1b753 | 60,565 | FinnGen R3 to R12 manifests; Neale lab round 2 phenotype summary files (both sexes, female, male; v1 and v2); Pan-UKB phenotype manifest (per ancestry group); UKB-SAIGE and UKB-TOPMed PheWebs; FinnGen R12 meta-analysis portals (totals); OpenGWAS metadata of the MRC-IEU `ukb-b` batch; COVID-19 HGI release 7 results page |

An accession maps only when its publication is the source of exactly one dictionary row and
every catalog study (or curated OpenGWAS dataset) of that publication states the same sample;
a publication whose deposits state several samples is omitted, because the deposit's analysis
cannot be told from the dictionary row without reading the deposit. A count row is written only
where the manifest states both a case and a control count. No manifest states a canonical
outcome identifier, so that column is `not_stated` throughout and the endpoint comparison rests
on the other fields. Neale lab round 1's documented phenotype summary is served as a web page,
not as the file, to a plain request, so round 1 gives no count evidence; GeneATLAS, the
consortium releases, the pQTL studies and deCODE publish no per-release count manifest and give
none. No two releases of one resource hold the same case and control counts for an endpoint
(`duplicate_count` is 1 in every row).

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
times, 60 seconds apart; a record with no file after that has no retrieved source, and its rows
are `no_source` when the abstract supplies no decisive evidence (§Study design, abstract
evidence). Accepted types: JATS
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

The two models are Claude Sonnet 5.5 (Anthropic, `claude-sonnet-5-5`), the nominal first
coder, and GPT-6.1 Sol (OpenAI, `gpt-6.1-sol`), the closed-packet checker. Both code every row
independently, with an identical prompt and identical sources; neither sees the other's answer
or any Paper 1 code; each is called through its API with no tools and no web access, and the
model string returned is recorded with every response. The two are never of one family. Both receive the same fixed prompt, `prompts/coding_prompt_v2.md`
(sha256 6b10c93ff232c6b1f763ef67cd1e03a7c8356585c59abea902004744c0615736) followed by Paper 1's
dictionary definitions
(`experiments/02_claims_meta/outputs/manual_coding/2026-10-03/coders/dictionary_definitions.csv`,
sha256 57f2c5bcef2b63d2d8526d4950c963a5e92e7d56cb75df215b7bbacff9f11e07), answer in the schema `prompts/output_schema.json` (sha256
7ee5f69808e6be83db2a1d0c5b584c4100adda1843bfc22ea89d1f507dab18cc), and differ only in the API
framing of `prompts/api_framing_v2.md` (sha256
69831ccbbcc26c26b006c527ed9a073d7c99f6790901ab20a974ea651723611c), which sets the maximum output
of both at 128,000 tokens. The final row data, with the reasons the pipeline adds (`no_source`,
`source_unreadable`, `version_not_linked`, which no model answer may carry), fit
`prompts/final_data_schema.json` (sha256
6873aef1c75049799f7bab1fdcdb3a7dacd00637b60e909500f6a7e26ffa9ecd). The models extract count
evidence only; whether it confirms, contradicts or only supports a release is decided by script
against the counts table. The prompt is built from the
rules of this plan and Paper 1's coder instructions v6, with no example drawn from a study
paper; the abstract-only packets of SA1 use the same prompt.

**What the models read.** Both models receive the whole rendered full text of the record. A
supplement is given whole where it renders to text under 200,000 characters; a larger one, or
a workbook of more than 20 sheets, is cut mechanically: every sheet or table name, the header
rows, and every row that holds a dictionary term (Paper 1's term rule), an accession pattern or
a release pattern, with its header.

**Input limit.** One request carries at most 400,000 characters of source text besides the
fixed prompt, for both models; the limit is frozen. Checked against the vendors' documentation
and token counters (`outputs/token_ratio_2026-10-10.json`, 12 stored full texts of Paper 1
papers outside the scope, counted by each vendor's counting endpoint): the context window is
1M tokens for Claude Sonnet 5.5 and 1,050,000 for GPT-6.1 Sol, the maximum output 128,000 for
both; at the smallest measured ratios (2.33 characters a token for Sonnet 5.5, 3.69 for Sol) a
full request is about 172,000 and 108,000 tokens of source, with about 35,000 and 22,000 tokens
of fixed prompt and an output well under 128,000, so under 340,000 tokens in all, a third of
either window.

**Exhaustive whole-supplement pass.** A rendered supplement that fits within the input limit is
given in one request. A larger one is divided deterministically into exhaustive chunks below
the limit: sheet names, table titles, column headers and footnotes are kept in every chunk
they apply to; a table row is never split and its headers are repeated in every chunk; prose
chunks overlap by two sentences; every chunk is processed, including chunks with no dictionary
term. The answers of the chunks are merged by union, and incompatible decisive mappings give
`conflicting_identifiers`. A log records, per supplement, the number of chunks, their character
ranges, their sheet or table identifiers and the sha256 of each chunk.

**C2, cut-supplement retention.** A seeded sample of 30 papers with a cut supplement (all of
them if fewer) is given to the checker a second time, in a separate pass, with each cut
supplement under the exhaustive whole-supplement pass. C2 compares the cut representation with
that exhaustive one. A miss is a row for which the exhaustive pass finds decisive evidence (D1
or D2, gate passed) that the cut does not hold; a miss is verified by the gate before it
counts.

**Model choice.** The two models are named without a model-selection calibration: no test of
candidate models against the author's reading of whole sources is run before the freeze. The
design relies instead on the mechanical control C1, the supplement check C2, the gate on every
accepted mapping, and the author's adjudication of every disagreement and audit of a seeded
10% of agreements.

**C1, the positive control.** Built by a frozen mechanical scanner, without reading any
source by hand: (1) the scanner and its patterns are frozen before retrieval
(`scripts/source_scanner_v2.py`, sha256
854b41d9063a2978fc58029c88964994307ac4e21b96f863dd783352114ba43c;
`reference/c1_scanner_patterns_v2.json`, sha256
69a57641e91f35e3ac9983e982ce687db8b6657ecbe6564791f3374132ba7eb4, which also holds the seed of
the draw; accessions match in any case and are put in their registry's case before lookup, and a
DOI loses terminal `.`, `,`, `;`, `:`, `)`, `]` and `}` before lookup); (2) after
retrieval it scans every eligible retrieved source, those of Paper 1 papers outside the scope
included, for explicit accessions,
numbered releases and uniquely mapped source identifiers; (3) a match is kept only when it maps
mechanically to exactly one dictionary row; (4) it must stand with enough local context to
establish a dataset mention of a side (a dataset, GWAS, summary-statistics, pQTL or outcome
term in the same sentence or table row), with no manual confirmation before coding; (5) the
selected controls, their expected rows and the selection log are frozen before either model
runs, up to 150 by seeded draw; (6) controls are mixed with study rows and not marked; a
control coded to another row gets a blinded mechanical review (does the frozen source hold a
second hard identifier for the same side and estimate), and a contradiction the review
explains by the source is reported apart and still counts. A control from a paper outside the
scope is a control-only row and enters no index. If the scan of the scope's sources and of the
retrieved out-of-scope sources yields fewer than 50 controls, the scan is extended to every
retrievable paper of Paper 1's corpus outside the scope before coding; the controls this gives
are the source-scanned controls.

**Manifest controls.** Deterministic control packets built from the pinned resource manifests
are a separate implementation check of the mapping and the software: they never enter the
source-scanned denominator, never count toward its minimum of 50, and are reported apart.

**Order.** Reference tables, the C1 scanner and the repository-link patterns pinned; plan
frozen and registered; sources retrieved and frozen; supplements cut where needed; cost
estimate written and approved; control set and C2 sample frozen; abstract-only rows (SA1, B)
coded, checked and adjudicated; full-text rows coded and checked; C2 computed and acted on;
codes committed; C1 computed and logged; registry assembled; estimands computed; secondary
analyses computed.

## Randomization

N/A — nothing is assigned; papers are dealt to coding sessions and the audit sample is drawn by seeded shuffles.

## Data collection procedures

New versioned scripts, each tested and sealed before it runs; inputs sealed with `results
seal`; retrieval and coding logged with `prereg log`. Anything longer than two minutes runs on
Modal with checkpoints inside the loop and resumes from them. Every retrieved file is stored
with its route, URL, date and sha256 under an ignored path and listed in a withheld-files
record; no third-party text is committed. A paper whose source cannot be retrieved is never
dropped: its rows are unresolved and counted by reason.

**Cost approval.** After retrieval and before any model request, the pipeline writes to a file
the measured character counts of every full text and supplement and the resulting cost estimate
per model, and stops. Coding starts only after the author approves that estimate, and the
approval is logged with `prereg log`. The author accepts a total of 30 to 100 US dollars; an
estimate above 100 US dollars needs his explicit approval.

**Tooling reused from Paper 1.** The supplement cutter, the pages the author marks and the
readers of his marks are new versioned copies of Paper 1's tools, tested and sealed before
use; the originals are not edited.

| page or step | new copy derived from |
|---|---|
| supplement cutter and the passages shown on the pages | `scripts/manual_coding_passages_v3.py` (sealed) |
| table of rows the author marks | `scripts/manual_coding_check3_table_v2.py` (sealed) |
| page builder for the disagreement page and the audit page | the page script that built Paper 1's check pages, which was not sealed and is not in the repository; the copy made here is the first sealed version |
| seeded draws (control set, C2 sample, audit sample) | `scripts/manual_coding_check3_sample.py` (sealed) |
| reader of the author's marks | `scripts/manual_coding_check3_followup_v2.py` and `scripts/manual_coding_final_tables.py` (sealed) |
| provenance and identifier gate | `scripts/manual_coding_gates_v2.py` and `scripts/pin_passage_occurrence_v2.py` (sealed) |

Every page shows, per row: the passages, with the identifier or release string that decides
highlighted; a link to the open page of the source; the row's hash; one-click marks and a note;
and a button that saves the marks as a JSON file, whose sha256 is logged before it is read.
The disagreement page shows the two answers
without saying which model gave which, in an order shuffled per row by a seed. The audit page
shows the agreed answer.

| Paper 1 manual-coding artifact | role here |
|---|---|
| passage cutter (as the supplement cutter), gates, pin helper, table and marks scripts, page script | tooling: new versioned copies |
| coder instructions v6 and the settled rules A to I4 and C1 to C5 | tooling: the basis of the new prompt, which is a new file with its own sha256 |
| dataset dictionary and dictionary definitions | input, unchanged |
| the 65 full texts stored for scope papers, with their raw XML | input, where eligible under route R1 |
| the claims folders of pinned sentences | not used |
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
transition; the attribution transition; for each decisive passage, its identifier type and its
location (abstract, main text, supplement); the abstract-only answers of SA1. Per paper: each source by route, type, version, date
and sha256, and each failure by reason; year, journal, document class and proteomic assay
platform (`proteomic_assay_platform`: `olink`, `somascan`, `other`, `mixed` or `not_stated`, the
family of the pQTL rows the paper's mentions map to, as in `verification/pqtl_row_attributes.csv`;
`not_stated` where no pQTL mention maps to one row); the repository links of SA7, by host and by
section. The retrieval route is recorded apart and
is never called platform.

## Measured variables - File upload

N/A — the two reference tables are files of the repository, pinned before the freeze.

## Indices

M, KI, KN, U, LB, UB, KO, KD, U_b, LB_b, UB_b, the resolvable share and the H1 concordance are
Paper 1's, computed by the same functions on the registry with the accepted codes applied
before the family datasets are formed.

| index | numerator | denominator or categories |
|---|---|---|
| C1 recovery, source-scanned | controls coded to the expected row | controls found by the scanner in retrieved scientific sources |
| C1 recovery, manifest | packets coded to the expected row | manifest packets; reported apart |
| C1 contradiction | controls coded to another row; packets coded to another row | each denominator above, apart |
| C2 misses | sampled papers with a gate-verified row whose decisive evidence is in a whole supplement and not in its cut | the sampled papers with a cut supplement; and rows |
| canonicalization | comparisons canonicalized; comparisons left `representation_unresolved`; and the repeated pairs they hold | comparisons of a meta-analysis row with a component set |
| full-text resolution yield | mentions unresolved from the abstract (ambiguous, unmatched, not stated) that are resolved here | all such mentions of the scope; also by side |
| incremental yield by source | resolved mentions whose decisive evidence is in the full text only, in a supplement only, in both | resolved mentions |
| abstract-to-full-text transitions | `confirmed`, `refined`, `contradicted`, `unresolved` | mentions the abstract resolves to one release, with an eligible source |
| attribution transitions | unclear to resolved; unclear and still unclear | records with unclear attribution in Paper 1; and the repeated pairs they hold |
| count-only candidate mappings | mentions with no decisive rule and S1 evidence equal to exactly one release; to several | mentions with no decisive rule |
| accessibility-stratified resolution | resolved mentions | mentions, by route of the record's source (R1, R2 present, R3, R4, none) |
| source availability | papers with an eligible source | papers, by year, journal, document class and proteomic assay platform |
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
| C1, source-scanned (the gate of H1-R, H2-R, H2b-R and the yields) | recovery ≥ 0.90 and contradiction ≤ 0.02, on at least 50 controls found by the scanner in retrieved scientific sources |
| C1, manifest (implementation check) | recovery ≥ 0.90 and contradiction ≤ 0.02 on the manifest packets, reported apart |
| C2 | at most 1 sampled paper with a gate-verified miss |

The C1 thresholds are conventional operating values, not derived from data, and the paper
says so.

**If the source-scanned C1 fails, or rests on fewer than 50 controls after the extended scan,
every release-resolution estimate that depends on the coding pipeline is void: H2-R, H2b-R,
H1-R, the yields and the transitions.**

**If the manifest check fails, the pipeline is void in the same way; if it passes, it rescues
neither a failure nor a shortfall of the source-scanned C1.**

**If C2 fails, both models code every cut supplement again under the exhaustive
whole-supplement pass before any estimand is opened; the codes made from cuts are kept and not
used.**

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

A row with no decisive evidence from the abstract or from an eligible retrieved source,
conflicting evidence or unsettled checks is unresolved and enters the bounds as Paper 1's
unresolved names do, never by exclusion. A release decisively identified from the abstract
stands when no full text is retrieved. Inaccessible papers stay in every bound, with their
abstract evidence, and are counted by reason.

## Other planned analysis

Each reported beside the primary, none replacing it:

| sensitivity analysis | what changes |
|---|---|
| count-inferred, strict | a mention with no decisive rule and S1 evidence equal to exactly one release (`duplicate_count` 1), every endpoint field `match`, is resolved to it |
| count-inferred, compatible | as strict, with `unknown` endpoint fields allowed and no field in `conflict` |
| count-inferred, exact total sample size permitted | as compatible, and an exact total sample size equal to exactly one release of the named resource for the endpoint also resolves |
| all count-only mappings unresolved | equal to the primary analysis by construction; stated so in the table |
| Europe PMC sources only | routes R3 and R4 give no source; abstract evidence stands |
| without attribution resolution | added rule 1 is not applied; Paper 1's attribution stands |
| without meta-analysis canonicalization | no component set is canonicalized; such comparisons are `representation_unresolved`; equal to the primary analysis while the expansion table holds no row, and stated so |
| originally registered corpus | Paper 1's 242 repeated pairs |

### Prespecified secondary analyses of the follow-up

Seven secondary analyses are prespecified. They are descriptive, use the fixed corpus, and
neither replace nor change the registered verdicts; none has a verdict, a threshold or a test.
Each is computed after the codes are committed and, where it uses coded rows, only when the
source-scanned C1 passes; SA7 involves no model and stands when C1 fails. Each writes
one file under `outputs/secondary/`, holding the whole result structure, its inputs' sha256 and
its seed where one is used. A "row" is a row of §Study design, unit (one dataset mention).

| analysis | unit | denominator | output file |
|---|---|---|---|
| SA1. Rules against evidence | row; repeated pair | the rows of the scope; M | `rules_vs_evidence.json` |
| SA2. Side-specific source relations | family comparison of a repeated pair | all family comparisons of M; and each pair weighted one | `side_relations.json` |
| SA3. Unresolved reasons | row; repeated pair | unresolved rows; unresolved pairs | `unresolved_reasons.json` |
| SA4. Decisive-identifier inventory | resolved row | rows resolved by a decisive rule | `identifier_inventory.json` |
| SA5. Within-study sample overlap | claim record; aggregated per study family | claim records of M; families of M | `within_study_overlap.json` |
| SA6. Reporting by year | row; paper | rows and papers of the scope, by year | `identification_by_year.json` |
| SA7. Code and data links | paper | papers with an eligible retrieved source, by year | `repository_links.json` |

**SA1. Rules against evidence.** Three results on the same rows and pairs: A, Paper 1's
registered result (its codes and pair classes, amended primary analysis); B, the follow-up's
rules applied to the abstract alone; C, the full follow-up. B is source-restricted: a separate
abstract-only packet per paper, holding the record's abstract as Paper 1 stored it and no other
file, is coded by both models with the frozen prompt, in requests separate from those of C, and
no full-text answer, code or passage is visible to either model. B gets the same checks as C:
the gate on a quotation pinned in the abstract, the author's adjudication of every row on which
the two models differ, and the author's audit of a seeded 10% of the rows on which they agree,
at least 30 rows, with the same escalation rule. All of it is done before any full-text row is
coded, so that no decision on B is made after a full text of the paper was read for this stage. A B code never enters C, and a C code never
counts as an abstract identification. Reported for A, B and C: per row, resolved to one
release set or unresolved by reason; per pair, the H2 and H2b class and the bounds; and the
contrasts A to B (associated with the changed coding procedure, which includes changed coders
and adjudication as well as the four added rules), B to C (associated with the added sources
under the same rules) and A to C, as 3 by 3 tables of pair classes and as counts of rows that
change state. The contrasts are descriptive and never read as causal effects of rules or
sources.

**SA2. Side-specific source relations.** For each comparison of two families on a repeated pair,
each side is classed by Paper 1's comparison of one side (`compare_side`, unchanged) on the
coded release sets: same identified release (`identical_release`); different releases with
documented shared participant-source components (`overlapping_participant_source`); documented
disjoint participant sources (`disjoint`); unresolved (`unclear`). Reported: the 4 by 4 table
of pQTL-side class against outcome-side class, in raw comparison counts and pair-weighted, each
repeated pair carrying total weight one shared equally among its comparisons. No cell is
called replication or a replication success; dataset provenance establishes neither analytical
nor biological replication.

**SA3. Unresolved reasons.** Multilabel: a row or pair carries every reason that applies, and no
single main reason is assigned. Categories, in four groups:

| group | category | from |
|---|---|---|
| access | no eligible source other than the abstract retrieved, and no decisive abstract evidence | `no_source` |
| access | retrieved source unreadable or incompletely rendered | `source_unreadable` |
| source does not establish | resource named, release not identified | `release_not_identified` |
| source does not establish | dataset not attributable to the claim's analysis | `attribution_unresolved` |
| source does not establish | conflicting identifiers | `conflicting_identifiers` |
| dictionary cannot represent | source identifies a dataset with no dictionary row | `dataset_absent_from_dictionary` |
| dictionary cannot represent | meta-analysis against component set, no expansion | `representation_unresolved` (pair level) |
| dictionary cannot represent | both sides identified, composition incomplete in the dictionary's components file, or Icelandic possible overlap | pair level, H2b only |
| version linking | record not linked to a readable version | `version_not_linked` |

At row level: the count of rows per category. At pair level, for H2 and for H2b separately: per
category, the count of unresolved pairs it affects (`attribution_unresolved` counts wherever an
unresolved attribution blocks a comparison, whether or not the row's release set is empty); the count where it is the only remaining
blocker, that is, every row or comparison that keeps the pair unresolved carries that category
and no other, built as the registered count of pairs unresolved for want of a source; and the
count with several blockers. Rows whose record has a readable source but a listed supplement
that could not be retrieved keep their substantive reason; they are counted beside the table,
from the retrieval log, and never as an access reason. The "dictionary cannot represent" group follows from the design's
choice not to extend the dictionary and is never reported as a reporting failure of the papers.

**SA4. Decisive-identifier inventory.** For every row resolved by D1 or D2, every decisive passage
the coding returns is classed by type: numbered release (D1, release pattern), repository
accession (D1, accession pattern), uniquely identifying citation or source DOI (D2), the type
assigned mechanically by the frozen scanner patterns on the pinned passage; and by location of
the passage: abstract (the record's abstract, or the abstract section of the full text), main
text (the full text outside its abstract), supplement.
Multilabel, type by location, with the count of rows whose passages hold several agreeing
types. No identifier is credited over another.

**SA5. Within-study sample overlap.** For each claim record of M, the record's pQTL-side coded
releases are compared with its outcome-side coded releases by Paper 1's participant-source
comparison (`compare_side`, components from `verification/dataset_components.csv`, both
unchanged): documented shared participant-source components; documented disjoint sources;
unresolved. Same release cannot arise, because every dictionary row belongs to one side (28
pQTL rows, 93 outcome rows); the category is kept and is empty by construction. The claim-record
classification is the within-analysis result. Per study family, the record classifications are
aggregated, never recomputed on unions of the family's releases: the counts of the family's
records in each class, and the family classed as all records sharing, all records disjoint,
mixed, or any record unresolved. Reported by record and by family, with the repeated pairs the
families hold. It needs nothing the coding unit does not already record: the coded release sets
per side and the attribution state of each record.

**SA6. Reporting by year.** By the family's first-public year, 2019 to 2025 (Paper 1's
confirmatory window): the share of rows with a decisive identification from any source (C), and
from the abstract alone (B); and the share of papers every row of which is so identified, from
any source and from the abstract alone. Each share with its 95% Wilson interval; intervals on rows
treat rows as independent and are descriptive. No trend test and no verdict.

**SA7. Code and data links.** A frozen mechanical scan, with no model, of every eligible retrieved
source (full text and supplements) for links to these hosts: github.com, gitlab.com,
bitbucket.org, sourceforge.net, zenodo.org and DOIs 10.5281/zenodo, figshare.com and DOIs
10.6084/m9.figshare, osf.io, datadryad.org and DOIs 10.5061/dryad, data.mendeley.com and DOIs
10.17632, codeocean.com, dataverse.harvard.edu and DOIs 10.7910/DVN, softwareheritage.org.
Matching is case-insensitive on the host or DOI prefix; the list and patterns are frozen with
this plan in `reference/repository_link_hosts.json` (sha256
4dfce00ead021e441980b4f4ccd32ca2c9f1985a982932fcefb7393a409a2f18) and run by
`scripts/source_scanner_v2.py`. Per paper: any link; any link inside a section whose title contains "data
availability", "code availability", "availability of data" or "data and code" (JATS
`sec-type` `data-availability` included); by host. Counted per paper by year; papers with no
eligible source are counted apart. Only a link's presence is recorded, never whether it
resolves, whether it is the authors' own deposit, or whether it holds the analysis.

**Added cost.** SA2 to SA7 use the committed codes or a mechanical scan and add no model request.
SA1 adds one abstract-only request per paper and model, about 266 each: with the cached fixed
prompt, abstracts under 3,000 characters and about 1,500 output tokens per paper, at the prices
of the cost table, about 5 US dollars for Claude Sonnet 5.5 and 5 for GPT-6.1 Sol, about 10 in
all, under 10 minutes on Modal; and the author's adjudication of B's disagreements and audit of
10% of its agreements. The measured abstract lengths enter the cost estimate the pipeline
writes before any request.

Anything else is labelled as made after the results.

## Context and additional information

Review before any freeze: external review rounds on this draft until one confirms it. The
freeze uses `prereg freeze` and an OSF registration of its own, linked to
https://osf.io/zae8c.

No choice is left open.

**Cost of the models**, for about 282 requests per model (266 papers and control-only papers),
from the lengths of the 65 stored full texts of the scope (mean 40,173 characters), a fixed
prompt of about 80,500 characters (instructions and dictionary definitions, cached after the
first request), about 1,500 output tokens per paper, the measured pooled ratios of 2.62
characters a token (Claude) and 4.28 (GPT-6.1 Sol), and list prices per million tokens of 2,
0.10 cached and 10 output (Claude Sonnet 5.5; GPT-6.1 Sol) and 10, 0.25 and 50 (Claude Fable
5.1). No supplement is stored, so supplement length cannot be measured; the last column gives
what each 25,000 characters of supplement per paper adds. The abstract-only coding of
secondary analysis SA1 adds about 10 US dollars (5 + 5) with the chosen models; the other
secondary analyses add no model request.

| models, whole full texts | different families | new input tokens | cached input tokens | output tokens | cost without supplements | added per 25,000 supplement characters per paper | wall time on Modal |
|---|---|---|---|---|---|---|---|
| Sonnet 5.5 + Sol (chosen) | yes (Anthropic, OpenAI) | about 4.3 and 2.7 million | about 8.7 and 5.3 million | about 0.4 million each | about 14 + 10 = 24 US dollars | about 5 + 3 = 8 | under 30 minutes |
| Fable 5.1 + Sol | yes (Anthropic, OpenAI) | about 4.3 and 2.7 million | about 8.7 and 5.3 million | about 0.4 million each | about 67 + 10 = 77 US dollars | about 27 + 3 = 30 | under 30 minutes |

**Maximum claim under this registration.** Among this fixed corpus, using the retrieved
sources and registered identification rules, the share of Paper 1's 245 repeated pairs that
rest on identical releases lies between LB and UB, and the share that rest on identical
releases or documented shared participant-source components between LB_b and UB_b, each with
the verdict the one-half rule gives; these are augmented full-text coding estimands of a
post-results follow-up analysis, computed with Paper 1's relation definitions on inputs
changed by four registered coding rules; they are statements about the retrieved corpus, and
they stand beside Paper 1's registered unresolved verdicts without replacing them. The paper can also state, each with the
denominator registered above: the directional concordance of independently sourced pairs
under the same resolution, without a verdict, or that it is not estimable; the full-text
resolution yield, the number and proportion of mentions unresolved from the abstract that a
decisive rule resolved, by side; the incremental yield of the full text and of supplements;
how often the full text confirmed, refined or contradicted what the abstract stated about a
dataset; how many records with unclear attribution were settled by an explicit link and how
many stayed unclear; how many mentions had only count evidence, and the result when those
count-only mappings are admitted; resolution by route of access and source availability by
year, journal, document class and proteomic assay platform; how many repeated pairs changed class, how many
stayed unresolved, and how many of those for want of an accessible source; the bounds among
pairs whose every paper could be read, as a description; how many meta-analysis comparisons
were canonicalized or left unresolved for want of an expansion; and that the coding pipeline
extracted and mapped hard identifiers found in the retrieved scientific sources at the
registered rate on at least 50 such controls, or that it did not and the resolution estimates
are void, with the manifest implementation check reported apart. As prespecified secondary
analyses of the follow-up, all descriptive and without verdicts, it can state: how rows and
pair classes differ between Paper 1's result, the follow-up rules on the abstract alone, and
the full follow-up, as contrasts associated with the coding procedure and with the added
sources; for each family comparison, whether the pQTL side and the outcome side were the same
release, shared documented participant sources, had documented disjoint sources, or were
unresolved, in raw and pair-weighted counts; how many unresolved rows and pairs each reason
affects, how many it alone holds and how many have several, with the limits of the dictionary
kept apart from what the sources do not establish; which types of decisive identifier were
found and where; whether the pQTL side and the outcome side of each claim record share documented
participant sources, and those record classifications counted per family; the share of mentions and papers decisively identified from any source and from the
abstract alone, by year, with intervals; and how many papers carry a link to a code or data
repository, by year. It cannot state that a release was not reported anywhere
because the retrieved sources did not identify it, that the controls validate attribution of a
dataset to the right analysis, that repeated claims rest on the same or
on different participants, that count agreement identifies a release, anything about papers
that could not be read or papers outside the corpus, or that this analysis was confirmatory
or planned before the results of Paper 1 were seen. Nor can it state that the changed rules or
the added sources caused a change in resolution; that any pair or comparison replicates
another, computationally, analytically or biologically; that a study's two-sample estimate is
biased by sample overlap, or that its sides share participants beyond the documented
components; that unresolved rows reflect poor reporting where the dictionary cannot represent
the dataset; that reporting improved or worsened over time; that adding an identifier makes a
study reproducible; or that a repository link works, belongs to the authors or holds the
analysis.
