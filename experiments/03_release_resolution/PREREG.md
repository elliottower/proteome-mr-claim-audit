# Does reading full texts and supplements resolve whether repeated protein–outcome claims rest on the same data releases?

Sections use the [OSF Preregistration](https://osf.io/prereg/) question titles verbatim, so
this maps onto a registration without being rewritten. A question that does not apply is
answered **N/A** with the reason, never deleted.

**Status:** DRAFT, not frozen. Nothing in this stage has been fetched, coded or run.

This plan is a follow-up to Paper 1 of `proteome-mr-claim-audit`
(`experiments/02_claims_meta/PREREG.md`, registered at https://osf.io/zae8c). It reuses that
plan's definitions unchanged: canonical pair, study family, repeated pair, dataset dictionary,
set-valued dataset mapping, family datasets, dataset relation, release identity,
`known_identical`, `known_not_identical`, `known_overlapping`, `known_not_overlapping`,
`unresolved`, the bounds LB, UB, LB_b and UB_b, and the threshold of one half (§Research
questions, §Measured variables, §Indices and §Inference criteria of that plan). Where this file
is silent, that plan governs.

## Research questions or hypotheses

Paper 1 classed repeated pairs from what abstracts state, and both verdicts came out
unresolved. Does reading the full texts and supplements of the same papers identify the data
releases, and what are the H2 and H2b verdicts then?

**H2-R.** Among the repeated pairs of Paper 1, more than half are `known_identical` when each
family's datasets are those named in the abstract or identified from its full text and
supplements by the rules below.

**H2b-R.** Among the same pairs, more than half are `known_overlapping` under the same
resolution.

**H1-R.** Among the same pairs, the proportion whose `independent` edges all join families of
the same direction, under the same resolution; an estimate without a verdict, as H1 is.

**C1.** The rules recover the release of dataset mentions whose release is already known
(positive control).

**C2.** Where a release is identified by rule 1 or rule 2, rule 3 applied to the same mention
names the same release.

H2-R carries the design. C1 gates it: without C1, a rise in resolved pairs is consistent with
rules that assign releases wrongly. A contradicted H2-R is the registered outcome favorable to
the papers under examination, in the sense of Paper 1: at most half of repeated pairs rest on
identical releases. A second favorable outcome is registered: the share of dataset mentions
that the full text or a supplement identifies to one release (reporting completeness of the
full papers).

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
11.

An availability count from metadata is seen: of the 266 papers behind any repeated pair, 65
have a full text on disk, 84 more have an open-access full text in Europe PMC, 12 have a full
text there not flagged open access, 66 are open access by OpenAlex only, 37 are closed and 2
returned no status; Europe PMC lists supplementary files for 141.

The author and the coding agents have read passages of 242 full texts during the manual coding
of Paper 1, and the 197 codes that resulted.

No full text has been read for this stage, no supplement has been fetched, and no rule below
has been applied to any paper.

## Explanation of foreknowledge and managing unintended influences

This stage was designed after its motivating result was known. Its design choices (which
sources to read, rule 3, the scope) were made knowing that H2 and H2b were unresolved and why.
What that costs: the stage cannot be presented as a planned part of Paper 1, its verdicts are
reported beside the registered verdicts and never replace them, and the paper states that the
follow-up was registered after the results of Paper 1.

What limits the influence: the definitions and the threshold are Paper 1's, unchanged; the
rules are deterministic and fixed here before any full text is read for this stage; coders and
the checker never see the pair's other families, the relation class or any aggregate; every
dataset side of every paper behind a repeated pair is coded, whatever its class in Paper 1
(§Study design, scope); and C1 and C2 are computed before H2-R is opened.

## Study type

Observational, meta-research: a second coding of documents already in a registered corpus.

## Intention for causal interpretation

N/A — no causal claim.

## Blinding of experimental treatments

N/A — no treatment.

## Additional blinding during research or analysis

Coders and the checker receive the record, the side, the name as written or `not stated`, for
an outcome-side row the outcome as the claim writes it, the stored passages and the candidate
dictionary rows; they do not receive other families' assignments, the relation class or any
aggregate. The registry is assembled with the new codes only after every code is committed.

## Study design

**Corpus.** The claim records, families and repeated pairs of Paper 1's amended primary
analysis (`outputs/registry/2026-10-03_amended_primary_coded_a`), fixed. No record is added or
removed. The originally registered analysis of Paper 1 is rerun with the same codes and
reported beside it.

**Scope (to be decided by the author before the freeze; one option is deleted).**

| option | papers coded | trade-off |
|---|---|---|
| A | the 262 papers with a dataset mention that blocks an unresolved pair | least work; pairs already classed (11 for H2, 13 for H2b) keep their abstract-based class, so resolution is applied only where the result was unresolved |
| B (recommended) | all 266 papers with a claim in a repeated pair, every dataset side of every such claim, including names that already map to one release | 4 more papers; resolution cannot be selective; already-mapped names become the positive control C1 and can reveal a full text that contradicts its abstract |

**Unit.** A dataset mention: one record, one side and one name as written; on a side where the
abstract names no dataset, one row per record and side (pQTL) or per record, side and outcome
as written (outcome).

**Sources, in this order, and no other.** (1) The Europe PMC full-text XML of the record,
rendered as in Paper 1. (2) The supplementary files Europe PMC lists for it. (3) For a record
with no Europe PMC full text and an open-access location in OpenAlex, the file at that location
when a plain HTTP request returns it. No publisher site is logged into, no paywalled copy is
used, no browser is automated, and no request carries an e-mail address.

**Resolution rules, applied in this order; the first that returns one dictionary row decides.**

| rule | condition | result |
|---|---|---|
| 1. Release stated | a sentence, table row or supplement cell attributes the analyzed data of the side to a release by one of Paper 1's settled identifiers (release number, source DOI or verified reference entry, uniquely identifying citation), under the coder instructions v6 of Paper 1 unchanged | that row |
| 2. Accession | the text or a supplement gives a dataset accession for the side that the pinned table `reference/accession_releases.csv` maps to exactly one dictionary row | that row |
| 3. Counts | the text or a supplement gives, for the side and (outcome side) the claim's outcome, a case count and a control count, or a total sample size, that equal those of exactly one release of the named resource for that endpoint in the pinned table `reference/release_counts.csv`; tolerance zero | that row |
| none | no rule returns a row, rule 3 returns more than one, or two rules or two passages return different rows | unresolved (`release_not_identified` or `conflicting_identifiers`), counted |

Rule 3 never applies when the resource is not named, and never across resources. A count that
the source describes as after exclusions, as an effective sample size or as a subset is not a
release-defining count (Paper 1, rule H).

The two reference tables are built from the resources' own per-release manifests, pinned by
sha256 and committed before the freeze; a resource with no pinned per-release counts has no
rule 3.

**Attribution.** A family whose dataset attribution is `unclear` in Paper 1 stays unclear. The
46 unresolved pairs with such a family stay unresolved and are counted.

**Checks.** First check: coding agents, one per paper, with the machine gate of Paper 1 (the
pinned quotation holds an identifier of the coded row that no other candidate has; for rule 3,
the pinned counts equal the table's). Second check: a closed-packet checker given the same rows
and passages without the first value. Third check: the author reads the rows on which the two
checks differ, after a blind reread, and no others. A row is coded only when the two checks
agree or the reread resolves it and the gate passes.

**Order.** Reference tables pinned; plan frozen; sources fetched; passages generated; C1 rows
and study rows coded together, indistinguishable to the coders; codes committed; C1 and C2
computed and logged; registry assembled; H2-R, H2b-R and H1-R computed.

## Randomization

N/A — nothing is assigned; papers are dealt to coders by a seeded shuffle.

## Data collection procedures

New versioned scripts, each tested and sealed before it runs; inputs sealed with `results
seal`; fetching and coding logged with `prereg log`; anything longer than two minutes runs on
Modal with checkpoints inside the loop and resumes from them. Every fetched file is stored
with its sha256 under an ignored path and listed in a withheld-files record; no third-party
text is committed. A paper whose full text or supplement cannot be fetched is never dropped:
its mentions stay unresolved and are counted by reason.

## Data collection procedures - File upload

N/A — no file beyond the repository.

## Sample size

266 papers (option B) behind 245 repeated pairs. From metadata, a full text is on disk or
reachable for 227 and not for 39. H2-R is supported with 123 or more `known_identical` pairs
and contradicted with 123 or more `known_not_identical` pairs. At least 46 pairs stay
unresolved, so at most 199 can be classed.

## Sample size rationale

The corpus is Paper 1's and is fixed; no power calculation applies to a census.

## Starting and stopping rules

Coding starts after the freeze and stops when every row has a code or an unresolved reason;
no result is computed before that.

## Manipulated variables

N/A — nothing is manipulated.

## Measured variables

For each dataset mention: the dictionary row or the unresolved reason; the rule that decided;
the source read (full text, supplement, open-access file); the pinned quotation; for rule 3
the counts as written and the table row matched; the two checks' values and any reread. For
each paper: which sources were obtained. Counts under rule 3 are recorded for every mention
that states them, also where rule 1 or 2 decided (for C2).

## Measured variables - File upload

N/A — the two reference tables are files of the repository, pinned before the freeze.

## Indices

M, KI, KN, U, LB, UB, KO, KD, U_b, LB_b, UB_b, the resolvable share and the H1 concordance are
Paper 1's, computed on the registry with the new codes applied before the family datasets are
formed.

| index | definition |
|---|---|
| C1 recovery | among control mentions (a name that maps to one release from the abstract, or one of Paper 1's 197 coded rows) whose paper has a source, the share coded to the known row |
| C1 contradiction | among the same, the share coded to another row |
| C2 agreement | among mentions decided by rule 1 or 2 for which rule 3 returns one row, the share where that row is the same |
| resolution rate | mentions coded to one row over all study mentions; by rule, by side and by source |
| full-text reporting completeness | papers for which every dataset side of every repeated-pair claim is coded to one row, over papers with a source |
| pair movement | repeated pairs by class in Paper 1 and class here (3 by 3, for H2 and for H2b) |
| unfetched | papers and mentions with no source, by reason |

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

| hypothesis | holds when |
|---|---|
| H2-R supported | LB > 0.5 |
| H2-R contradicted | UB ≤ 0.5 |
| H2-R unresolved | neither |
| H2b-R supported | LB_b > 0.5 |
| H2b-R contradicted | UB_b ≤ 0.5 |
| H2b-R unresolved | neither |
| H1-R | no verdict; the estimate with its Wilson interval; labelled imprecise on fewer than 20 pairs |
| C1 | recovery ≥ 0.90 and contradiction ≤ 0.02, on at least 50 control mentions |
| C2 | agreement ≥ 0.95, on at least 20 mentions |

**H2-R, H2b-R and H1-R are void if C1 fails.**

**If C2 fails, or rests on fewer than 20 mentions, rule 3 leaves the primary analysis: mentions
it alone decided are unresolved there, and the analysis with rule 3 is reported as a
sensitivity analysis.**

**A verdict on fewer than 20 repeated pairs carries the label imprecise.**

The verdicts of this stage are reported beside the registered verdicts of Paper 1, which
stand. The two verdicts are read together by Paper 1's table.

## Data inclusion and exclusion

Every repeated pair of the corpus is in M, whatever was fetched. No paper, mention or pair is
excluded.

## Missing data

A mention with no source, no decisive rule or disagreeing checks is unresolved and enters the
bounds as Paper 1's unresolved names do, never by exclusion. Unfetched papers are counted by
reason (closed, no status, request failed after the logged retries).

## Other planned analysis

Each reported beside the primary: without rule 3; with rule 3 at a tolerance of 1% on each
count; Europe PMC sources only; pairs whose every paper had a source; the originally
registered corpus of Paper 1 (242 pairs); option A's subset of papers, if option B is run.

Anything else is labelled as made after the results.

## Context and additional information

Review before any freeze: one external review round on this draft. The freeze uses `prereg
freeze` and an OSF registration of its own, linked to https://osf.io/zae8c.

**Maximum claim under this registration.** With the datasets of each family taken from the abstract or identified from the full text and
supplements by three fixed rules, the share of Paper 1's 245 repeated pairs that rest on
identical releases lies between LB and UB, and the share that rest on identical releases or
documented shared participant-source components between LB_b and UB_b, each with the verdict
the one-half rule gives; these are statements about the retrieved corpus and stand beside
Paper 1's registered unresolved verdicts without replacing them. The paper can also state: the
directional concordance of independently sourced pairs under the same resolution, without a
verdict; how many dataset mentions and papers the full text or a supplement identified to one
release, by rule, side and source; how many repeated pairs changed class and how many stayed
unresolved, with the 46 held by unclear attribution; that the rules recovered known releases
at the registered rate, or that they did not and the hypotheses are void; whether count
matching agreed with stated releases; and how many papers could not be read. It cannot state
that repeated claims rest on the same or on different participants, that a release was used
where no rule identified it, anything about papers outside the corpus, or that this stage was
planned before the results of Paper 1 were seen.
