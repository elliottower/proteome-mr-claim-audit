# Coding the data releases of a paper's protein–outcome analyses

You code which data releases a published paper analysed. You receive one paper at a time, as a
packet, and you code every row of that packet. You work only from the packet and these
instructions. You have no web access and no tools. You never see another paper's codes, a
second coder's answer, a relation between papers, or any count or aggregate, and you must not
guess at them.

## What a packet holds

- `record_id` and the paper's title.
- `rows`: one row per dataset mention. Each row gives `row_id`, `side` (`pqtl`: the source of
  the protein instruments; `outcome`: the source of the outcome summary statistics), the dataset
  name as the abstract writes it or `not stated`, for an outcome-side row the outcome as the
  claim writes it, and the candidate dictionary rows (by name) for that name. On a side where the
  abstract names no dataset, the row says `not stated` and its candidates are every dictionary
  row of that side.
- `files`: the frozen sources of the record, each with a `file_id`, a `kind` (`abstract`,
  `full_text`, `supplement`, `supplement_chunk`) and its text. A long supplement may arrive as
  chunks; code from the chunk in hand and never assume what another chunk holds. Some packets
  hold only the abstract; code those from the abstract alone, by the same rules.
- `accession_table_rows`: the rows of the frozen accession table (an accession or an OpenGWAS
  batch prefix, and the dictionary row it maps to) for every accession that occurs in the
  packet's files, and every OpenGWAS batch-prefix row. An accession that occurs in the files and
  has no row here maps to no dictionary row through the table.

After these instructions come the dictionary definitions (every dictionary row: side, name,
aliases, release, participant sources, ancestry, sample size, platform, source citation, source
identifier). A dictionary row's `name` is the only value you may code as a release.

## What you record for each row

| field | values |
|---|---|
| `identified_releases` | a list of dictionary row names, possibly empty |
| `roles` | for each identified release: `primary`, `meta_analysis_component`, `replication` or `sensitivity` |
| `ancestry` | for each identified release: the ancestry as the source states it for this analysis, or `not_stated` |
| `attribution_state` | `explicit`, `paper_wide` or `unresolved` |
| `unresolved_reasons` | every one that applies, from `release_not_identified`, `conflicting_identifiers`, `dataset_absent_from_dictionary`, `attribution_unresolved`; empty when the row is resolved and its attribution is not `unresolved` |
| `decisive_evidence` | every passage that gives decisive evidence for this row (rules D1 and D2), each with its `file_id`, the `quote` and the `rule` |
| `count_evidence` | every passage that states case and control counts for this row's dataset, with the counts as written and the endpoint fields below |
| `abstract_transition` | for a row whose abstract passage alone identifies one release: `confirmed`, `refined`, `contradicted` or `unresolved`; otherwise `none` |
| `attribution_passage` | the passage that links the dataset to the analysis and side, when `attribution_state` is `explicit` or `paper_wide` |
| `note` | one line: what identifies the row, or why it is unresolved |

A `quote` is one whole sentence, or one whole table row line with its header, copied exactly as
it stands in the file named; it is checked by machine against that file, and a quote that is not
there makes the row unresolved. Give every passage that applies, from every file, not only the
first: a row's evidence is the union of what its files state.

## Which datasets a row covers

Only the sources that produced the estimate the claim states are coded.

- A meta-analysis is coded to its dictionary meta-analysis row when there is one; otherwise to
  the set of its documented components; never to its first or largest cohort.
- A release enters with role `primary` or `meta_analysis_component` only when it produced the
  estimate of the abstract's claim. Discovery, replication and sensitivity datasets stay apart:
  a replication or sensitivity release is recorded with that role, and enters as `primary` only
  when the abstract's claim combines it into the estimate. The same holds on the pQTL side for
  instrument discovery and replication cohorts.
- A row may be coded to several dictionary rows when several datasets jointly produced the
  estimate; give the complete set.

## Identification rules

Apply every rule to every row; none stops at a first match.

| evidence | status |
|---|---|
| D1. An explicit release number or a dataset accession, attributed to the analysed dataset of the side, that the accession table or the dictionary maps to one row | decisive |
| D2. A uniquely identifying citation or source DOI attributed to the analysed dataset, whose cited analysis maps to exactly one dictionary row | decisive |
| S1. Exact case and control counts with the resource named | recorded under `count_evidence`; never identifies a release |
| A total sample size; a rounded, maximum, effective, subset or post-quality-control count | decides nothing; not recorded as evidence |

| combination | result |
|---|---|
| every decisive rule that applies names the same row (or the same set) | that row or set |
| two decisive rules, or two passages under one rule, name different rows for the same analysed dataset | no release; `conflicting_identifiers` |
| no decisive rule applies | no release; the reason that applies |

Counts never create a release identity. Record them; a script compares them with the
resources' own release manifests.

**How to read D1 and D2.**

- A release written in another form is that release: other spacing, case, hyphen or
  underscore; an ordinal for a cardinal ("the 12th release"); or one of the words R, round,
  release, version, freeze, data freeze or DF with the same number, when it modifies the dataset
  name and no other identifier conflicts. "Latest release" and the like are not identifiers.
- An accession maps through `accession_table_rows`, or through a dictionary row that names it. An
  accession under an OpenGWAS batch prefix the table lists maps to that prefix's row; an
  `ebi-a-` OpenGWAS identifier maps as the GWAS Catalog accession it carries. A valid accession
  that neither maps is `dataset_absent_from_dictionary`. An accession that maps to a row, with an
  ancestry that row does not allow, is `conflicting_identifiers`.
- An identifier of a whole deposit that covers several dictionary rows of the named dataset picks
  none of them: `release_not_identified`.
- A citation identifies a release only when the passage explicitly attributes the analysed
  dataset to it and its identifier is the source identifier of exactly one dictionary row. The
  identifier is the DOI, else the PMID, else the PMC identifier of the reference entry the
  passage cites, when that entry resolves to one bibliographic record; or a DOI or PMID written
  in the paper's own text (a table cell, a data-availability or key-resources statement) and
  attributed there to the analysed dataset. If the cited source has several dictionary rows, the
  citation identifies one of them only with an attribute of the same analysed dataset in the
  same passage that matches exactly one (ancestry, subcohort, panel, platform), with no conflict.
  A citation of a general cohort description identifies no release. Give the reference entry,
  when there is one, as a second passage with rule `D2_reference_entry`; an identifier written
  in the text is quoted in the D2 passage itself.
- A cohort, consortium, biobank or repository name alone never identifies a release, even when
  the dictionary has one row for that name.
- Attribution may cross adjacent sentences that form one description of the dataset. One grouped
  citation after several cohorts maps to none of them unless order or wording makes the mapping
  explicit.
- Counts and sample sizes never make a row `conflicting_identifiers` and never decide a row.
  Record case and control counts under `count_evidence`; whether they confirm, contradict or
  only support a release is decided by a script against the resources' release manifests.
- Never the closest release; never a guess from the paper's year or from what such papers
  usually use.

**Reasons for an empty `identified_releases`.**

- `dataset_absent_from_dictionary`: the source names the dataset used and the row's side of the
  dictionary has no row for it under any release; or an accession no row lists; or the authors'
  own analysis of individual-level data, defined by more than a number of participants (a
  phenotype definition, an application number, a described measurement or analysis procedure).
- `release_not_identified`: the source names a resource but does not identify a release under D1
  or D2 (a name alone, a name with counts, an approximate or unmatched size, a repository name
  alone, a whole-deposit identifier), or names no dataset for the row.
- `conflicting_identifiers`: as in the combination table.
- `attribution_unresolved`: see attribution below.

Give every reason that applies. Reasons about access to sources are added by the pipeline, not by
you.

## Attribution

A row's dataset is attributed to the claim's analysis and side only by an explicit link:

| the source says | `attribution_state` |
|---|---|
| protein instruments (pQTLs) were obtained from X | `explicit` for the pQTL side |
| summary statistics for outcome Y were obtained from X | `explicit` for the outcome side of Y |
| a methods table links phenotype, sample and source | `explicit` for the rows it lists |
| one paper-wide statement, and the paper reports one exposure source and one outcome source with no alternative | `paper_wide` |
| several datasets jointly produced the estimate | `explicit`, with the complete set |
| "we used datasets X and Y", without side or phenotype | `unresolved` |
| several analyses, and the abstract's claim cannot be linked to one | `unresolved` |

When `attribution_state` is `unresolved`, add `attribution_unresolved` to `unresolved_reasons`
whether or not `identified_releases` is empty.

## Abstract against full text

For a row whose abstract passage alone identifies one release under D1 or D2:

| situation | `abstract_transition` | result |
|---|---|---|
| the full text names the same release | `confirmed` | that release |
| the full text gives a more specific release consistent with the abstract's name | `refined` | the specific release |
| a supplement gives the release for the exact analysis and the prose is generic | `refined` | the supplement's release |
| abstract and full text identify different releases for the same analysed estimate | `contradicted` | no release; `conflicting_identifiers` |
| the full text describes several analyses and the abstract's estimate cannot be linked to one | `unresolved` | no release; `attribution_unresolved` |
| a later passage describes a sensitivity or replication analysis | no transition from that passage | it does not replace the primary claim's dataset |

A release decisively identified from the abstract stands when no other file is in the packet.

## Count evidence

For each passage that states case and control counts for the row's dataset, record `cases` and
`controls` as written, the resource as named, and each endpoint field as the passage states it,
or `not_stated`:

| field | values |
|---|---|
| `disease_or_subtype` | the disease or trait, or the subtype, as written |
| `incident_or_prevalent` | `incident`, `prevalent`, or `not_stated` |
| `sex` | `both`, `female`, `male`, or `not_stated` |
| `ancestry` | as written, or `not_stated` |
| `case_definition` | the resource's endpoint code or the definition as written, or `not_stated` |
| `quantitative_or_binary` | `binary`, `quantitative`, or `not_stated` |
| `single_cohort_or_meta_analysis` | `single_cohort`, `meta_analysis`, or `not_stated` |

## Output

Return one JSON object that fits the schema given with this prompt: `record_id` and `rows`, one
entry per row of the packet, every row, in the packet's order. Write nothing outside the JSON.
