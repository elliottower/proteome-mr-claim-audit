# How often do proteome-wide Mendelian-randomization abstracts repeat and contradict one another's protein–outcome claims, and how often do repeated claims rest on the same source data?

**Status:** FROZEN at `02bb006f3e55`
**Plan sha256:** `9f06131af9936cc7c3556e87d77dcec65d034e4665be023eedf39948082d417b`
**Log:** 170 entries, head `c0e3866e`
**Frozen:** 2026-10-03

Sections use the [OSF Preregistration](https://osf.io/prereg/) question titles verbatim. A
question that does not apply is answered **N/A** with the reason, never deleted.

This registration covers Paper 1: a meta-study of the protein–outcome claims stated in the
abstracts of proteome-wide Mendelian randomization (MR) papers. Nothing is re-run. The rerun of
the claims (Paper 2) is registered separately. A secondary abstract–full-text concordance
analysis of Europe PMC open-access full texts (§Other planned analysis) is reported beside the primary
results and cannot change them.

## Research questions or hypotheses

How many distinct protein–outcome claims do proteome-wide MR abstracts make, how often is the
same claim announced by more than one study family, how often do families contradict one
another, and when families announce the same protein–outcome pair from independent data
sources, how often do their announced directions agree? What indication-specific
drug-development records exist for the claimed pairs, how many claims worded as novel had an
earlier claim of the same pair in the registry, and how do the claims sit on the disease
ontology, on biological pathways and against a published systematic protein–outcome MR screen?

The registered outcomes are the counts and proportions under §Indices. H2 and H2b carry
verdicts; H1 is a registered estimate without one; every other outcome is descriptive.

**H1.** Among canonical protein–outcome pairs for which at least two study families announce
verified directional MR claims and at least one pair of those families uses datasets classified
as disjoint on both the pQTL and outcome sides, we estimate the proportion whose independently
sourced directional family records agree (abstract-level directional concordance).

**H2.** Among repeated pairs, more than half are `known_identical`: for every two of the pair's
study families, the sets of pQTL releases the two families name are equal and the sets of
outcome GWAS releases they name are equal (§Indices).

**H2b.** Among repeated pairs, more than half are `known_overlapping`: for every two of the
pair's study families and on both sides, the families name identical releases or documented
shared participant-source components (§Indices).

H2 carries the design and is the primary hypothesis. H2 quantifies the extent to which repeated
abstract claims represent reuse of the same source releases rather than new source data. H2b is
a second registered hypothesis, nested in H2: every `known_identical` pair is
`known_overlapping`, so H2 supported implies H2b supported and H2b contradicted implies H2
contradicted. H2b measures documented overlap of participant-source components (cohorts named
in the pinned composition of each release), not person-level overlap: one shared component can
be a small part of either analysis. Both verdicts are reported whatever they are; no secondary
outcome carries a verdict. A contradicted H2 is the registered outcome favorable to the
evidential independence of the literature under examination only in this sense: it shows that
at most half of repeated pairs rest on identical release sets. It does not show that they rest
on disjoint participants. The two verdicts are read together by the table in §Inference
criteria. H1 is
reported without a verdict: the closest published figure (Liu et al. 2025, general MR abstracts)
uses a different unit, null rule and trait matching (§Explanation of foreknowledge), so it is
reported beside H1 as context and is not a benchmark. H1 measures agreement among announced
abstract claims; it is not replication. H1 is conditional on both families reporting a
statistically significant estimate, so agreement under that condition is expected to be high;
it is read beside the agreement on identical-release edges, which is a control, and the
significance discordance (§Indices).

**Reserved words.** In the paper's results, tables and abstract, each of these words is used
only in this sense when it describes pairs, edges, families or data sources of the registry.

| word | meaning |
|---|---|
| announce | a family announces a pair when it has a registry claim record of the pair, whatever the record's direction value (null results and `direction_unverified` included) |
| repeated | a pair announced by at least two study families |
| independent | of an edge, or of the data sources of two families: the pQTL relation and the outcome relation are both `disjoint` (§Units) |
| contradicting | a pair with a family–pair direction `raises` (or `raises_with_nonsignificant`) and one `lowers` (or `lowers_with_nonsignificant`) |
| supported, contradicted, unresolved | the three verdicts of H2 and of H2b, and nothing else |
| overlapping (of data sources) | identical releases or documented shared participant-source components; never person-level overlap |

The paper does not use the phrases "independent replication" or "same participants": H1 measures
directional agreement among independently sourced abstract claims, and H2b documented
participant-source overlap, not verified person-level overlap.

## Foreknowledge of data or evidence

Authors have observed the data, but have not performed the proposed analyses

## Explanation of foreknowledge and managing unintended influences

Read before this document was written (paths under `planning/` name the author's working files:
review documents, the source report and census development notes, which are not in the public
repository):

1. A Perplexity report on auditing proteome-wide MR claims
   (`planning/source_reports/perplexity_report_2026-09-30.md`) and an independent verification
   of it (`docs/source_verification/`), which read in full the MR re-analysis and
   appraisal literature it found (Nguyen, Terry and Guggenheim 2025; Liu et al. 2025, MR-KG;
   Yang et al. 2025; Sobczyk et al. 2023). Liu et al. 2025 report direction discordance across
   published MR abstracts for general exposure–outcome pairs (20.2% of 2,075 pairs); their
   full text was read for the unit and direction rule (§Explanation of foreknowledge).
2. The general-MR reporting audits: Gibson et al. 2023 (BMJ Evidence-Based Medicine, 116 UK
   Biobank MR papers) and Woolf et al. 2022 (IJE, PMC9749715, 87 two-sample MR studies).
3. The critiques of mass-produced MR: Stender, Gellert-Kristensen and Davey Smith 2024;
   Munafò, Brown, Hefler and Davey Smith 2024.
4. Cross-platform pQTL comparisons: Pietzner et al. 2021, Sun et al. 2023, Eldjarn et al. 2023,
   Katz et al. 2022.
5. The author's own work: a 143-pair cis-pQTL MR pilot (`pqtl-mr-domain-of-validity`) and the V8
   registration in that repository.
6. An unknown number of individual proteome-wide MR papers read over 2025–2026 in that work.
   None was read with the extraction schema below.
7. A parked reporting-quality census of the same literature (`experiments/01_census/`), whose
   design documents and reviews quote two in-window papers for their protein counts (Chen L et
   al. 2022, Nat Commun, 308; Yoshikawa et al. 2024, 735) and record the first public date
   (2019-05-05) and protein count (1,002) of Zheng et al. 2020 (Nat Genet). The start of this
   window, 2019-01-01, was set with Zheng et al. 2020 known. Eight development papers for that
   census (`planning/development_set/`) were read for dates and protein counts only.
8. PubMed result counts only, run 2026-09-30 for 2020-01-01 to 2025-12-31, with no record
   content read (`docs/feasibility/`): Q1 1,309; Q2 332; Q3 without the GEN block 6,590;
   Q3 with the GEN block 814; union of the four queries with the GEN-restricted Q3, 2,089. No
   count for 2019 has been run.
9. From the author's V8 work: Karim et al. 2026 (medRxiv 10.64898/2026.02.23.26346731), whose
   23 launched pQTL-supported target–indication pairs come from 12 targets (APOB, CSF3, CSF3R,
   EGLN1, F2, FLT3, IL12B, IL4R, KIT, PCSK9, SERPINA1, VWF); the direction token rule of
   `pqtl-mr-domain-of-validity/experiments/PREREG_direction_concordance.md` §3.2–3.4, run once
   unblinded on that repository's pilot pairs and adopted verbatim below; and EpiGraphDB's pQTL
   MR catalog, from which the pilot drew instruments, so its content for the pilot's genes is
   known.
10. Eldjarn et al. 2023 (Nature) Supplementary Table ST36 (highly pleiotropic pQTL variants and
    their close genes), whose header row and first row were displayed; its gene list is adopted
    below as the pleiotropic-locus list.
11. A Perplexity review of an earlier draft of this document
    (`planning/perplexity_paper1_review/01_REVIEW.md`), which quotes the documentation of
    ChEMBL (`max_phase_for_ind`), Open Targets stop-reason classes and EpiGraphDB (the pQTL
    browser's 989 proteins × 225 traits; the xQTL browser's 1,740 proteins × 576 phenotypes),
    and Razuvayevskaya et al. 2024 (Nat Genet). No record of any in-window paper was read.

No Open Targets, ChEMBL, Reactome, platform panel or EpiGraphDB query has been run on any claim
or pair; items 14 and 15 list what was counted in the resource files alone.

12. The scoop rerun of 2026-09-30 (`docs/source_verification/SCOOP_RERUN_2026-09-30.md`),
    which read in full Wu et al. 2024 (Heart), including its drug-development counts (3 of 291
    protein–disease pairs with an approved matching indication, 288 without a record) and its
    heterogeneity figure (14.2% of pooled MR pairs with I² ≥ 80%); Zheng et al. 2025 (DMRdb);
    and Sobczyk and Gaunt 2026 (Sci Rep), a 2026 pQTL-MR paper that may enter the update set.
    The known-item calibration set was assembled from titles and metadata only, and its recall
    was checked by record counts only. GPT-6.1 Sol then read the titles and abstracts of the
    known items, which lie in the window (25 items, 24 after one was found ineligible), with the
    eligibility prompt only, in four runs (prompt revisions r4 to r7); the decisions changed the
    eligibility prompt and one query block (§Search calibration). The eligibility-only runs
    extracted the three eligibility criteria, tested and other protein counts, supporting
    sentences, and exclusion flags. They did not request or record any named protein identity,
    named outcome identity, protein–outcome claim record, effect direction, dataset assignment,
    or registered Paper-1 outcome.
13. Prompt and verifier development on records outside the window, after the round-4 review
    (`planning/perplexity_paper1_final/01_REVIEW_round4.md`): extraction prompt r8 run on the 30
    pre-2019 development abstracts; the full-text prompt run on the body of one pre-2019
    open-access development paper (PMID 30111768, Yao et al. 2018, Nat Commun); the Europe PMC
    open-access flags of the 30 development PMIDs; the titles of the 50 pre-2019 negative-control
    records (§Search calibration), whose abstracts were not fetched; and counts of ChEMBL 37 human
    drug mechanisms by target type (§Measured variables). No in-window record was read in this
    development apart from the known-item eligibility check of item 12.
14. Stage-0 build checks, made while the scripts were written, on resource files and on records
    published before 2019 only (`docs/stage0_build/`, `outputs/resource_counts/`):
    - *Search.* Hit counts of the four queries and of single terms for 2014–2018 in the three
      sources (Q1: 41 PubMed, 36 Europe PMC MEDLINE, 92 OpenAlex; Q4: 311, 288, 522); a smoke
      search for 2018-11-01 to 2018-12-31 (43 source records, 23 screening records, 8 of them
      OpenAlex conference abstracts, dissertations, a peer-review report and a dataset); one
      citation-chasing round on development PMIDs 28240269 and 30111768 with citing works capped
      at 2018-12-31 (186 new records, 172 marked by the prefilter). Metadata and stored
      abstracts; none was read with a prompt. Six of the stored records are dated in January to
      March 2019 by PubMed (PMIDs 30451371, 30586346 and 30601998 in the smoke search; 30239796,
      30307499 and 30423114 in the chase round): their abstracts are stored, the keyword
      prefilter and a length count ran over them, and they were read by no person and no model.
    - *Drug resources.* Value counts of the ChEMBL 37 and Open Targets 26.09 columns the joins
      read and of the drug index built from them: 4,107 parent drugs on 1,457 proteins, 36,131
      indications, 173,850 reports; 56,221 `clinical_report` rows that are not trials; 104,698
      rows with a quality-control flag; 95,830 rows naming two or more drugs; 1,214 indication
      rows of phase 0.5 or -1.
    - *Ontology and therapeutic areas.* 96,473 ontology edges; of 156,053 labels and exact
      synonyms, 1,965 give several canonical identifiers: 921 a MONDO or EFO identifier beside
      HP, OBA or Orphanet identifiers, 704 one MONDO and one EFO identifier. The Open Targets
      `disease` file gives 26 therapeutic areas to its 45,896 terms; 17,108 of the 24,954 MONDO
      human-disease terms are in it, and 24,601 have an area through their nearest ancestors.
    - *Assay lists.* The platform of the 14 pQTL dictionary rows whose platform string names no
      pinned list was read from each dataset's own source paper
      (`docs/stage0_build/PLATFORM_LOOKUPS.md`; sentences pinned with `citations`), and the
      published list files were fetched to the Modal volume. The sizes of the lists and the
      pathways each keeps under the 10–500 rule are in item 15.
    - *EpiGraphDB.* 973 of 989 exposures map to one accession; the trait counts are in item 15.
    - *Pleiotropic loci.* The 386 genes of the 69 variant rows of Eldjarn ST36.
    No claim, pair, registry record or in-window record was read.
15. The round-6 review (`planning/perplexity_paper1_final/05_REVIEW_round6.md`), which gave
    blind readings of the 14 platform rows and asked for six changes, and the resource files
    read to make them (`outputs/resource_counts/biology_resource_tables_2026-10-02_round6_fixes_b.json`,
    `verification/published_lists_derived/published_lists_derived.meta.json`):
    - *Analysed lists.* The supplementary tables that mark the proteins each pQTL study
      analysed: Folkersen et al. 2017 S3 Table (83 of 92 included), Gilly et al. 2020
      Supplementary Data 7 (257 of 275 not excluded), Png et al. 2021 Supplementary Data 8
      (184), Enroth et al. 2014 Supplementary Data 2 (77 phenotypes), Koprulu et al. 2026
      Table S5 (1,161 targets, 1,032 UniProt cells), and Katz et al. 2022 (Sci Adv) Table S2
      (1,301 SomaScan 1.3k reagents, 1,297 UniProt cells). The supplement of Katz et al. 2022
      (Circulation) is not open access and was not read; Folkersen et al. 2020 Supplementary
      Table 1 does not mark the 2 of 92 proteins that failed quality control.
    - *List sizes* (reviewed accessions; pathways kept): Olink Explore 3072, 2,926 and 222;
      SomaScan v4, 4,717 and 584; the INTERVAL list, 3,592 and 456; the AGES custom array,
      4,146 and 513; KORA SOMAscan V3.2, 1,124 and 151; the Jackson Heart Study reagents, 1,296
      and 213 (the commercial 1.3k list, 1,063 and 116); the Zheng 2020 instrument set, 1,725
      and 123; the SCALLOP meta-analysis targets, 1,034 and 53 (the 13-panel union, 1,071 and
      55); the ten lists of 70 to 304 accessions, 0 to 21 pathways each; pooled, 6,117
      accessions and 717 pathways (6,119 and 718 with whole panels). Of the 28 pQTL rows, 12
      take an analysed list, 11 an assayed list and 5 a platform list.
    - *Outcome names.* 47,734 labels and exact synonyms give no MONDO or EFO identifier; 247 HP
      terms are cross-referenced by exactly one canonical disease term in the pinned MONDO
      file, which completes 282 of those names. 901 labels of obsolete EFO terms have one live
      replacement and are not live names.
    - *EpiGraphDB traits.* Of the 225 traits, 191 map: 11 by an ICD-10 cross-reference, 66
      through the alias table, 79 as written and 35 by the after-colon rule; 34 stay unmapped.
      16 are mapped through a `broader_proxy` or `derived_measurement` alias, so the primary
      join reads 175 traits and 135,001 of the 179,928 estimates (147,819 with the proxy
      aliases).
    - *Open Targets flags.* The counts of item 14 (104,698 flagged rows; 56,221 rows that are
      not trials).
    No claim, pair, registry record or in-window record was read.
16. A pre-mortem of this document (`planning/premortem/PREMORTEM_2026-10-02.md`), which read
    the registrations and reviews of three other papers of the author and asked of every
    registered outcome whether it can fail, whether its rule has one reading, whether the
    abstract will state it, and which choices it depends on. It added H2b, the resolvable
    share, the registered secondary outcomes, the accounting table and the reserved words. To
    pin two published study lists as an outside check of the search, two fetches were tried
    with a plain client: the online supplement of Wu et al. 2024 (Heart) answered HTTP 403, and
    the download address of the DMRdb file of published pQTL–disease MR results answered with a
    303-byte notice that its files are moving to another host (the notice was removed from the
    volume). The scripts of the DMRdb web page were read for its file names. No list, no study
    identifier and no in-window record was read.
17. A live smoke run of the pipeline on records first public before 2019, 2026-10-02
    (`docs/stage0_build/LIVE_SMOKE_2026-10-02.md`): the registered queries on 2018-06-01 to
    2018-06-30 (18 screening records) and one citation-chasing round from its one eligible
    record (97 screening records; 86 marked by the keyword gate, all 86 judged in the gate
    audit). GPT-6.1 Sol received 122 requests on 115 records, all first public before 2019.
    Five records were judged eligible or uncertain, three of them gate-sample records whose
    abstract is empty or three characters long, each judged `uncertain`. Three claim records
    were extracted from one 2018 abstract, verified, and joined to every stage 5 resource
    under a smoke-only switch that treats families first public before 2019 as inside the
    window. One record dated 2018 by OpenAlex and 2019-01-10 by PubMed (PMID 30239796) came
    back in the stored chase responses; its abstract was not read and went to no model.
18. The `no_abstract` rule (§Data collection procedures), fixed on records first public before
    2019 only (`docs/stage0_build/NO_ABSTRACT_FLOOR_2026-10-02.md`): the abstract lengths of the
    313 such records held from items 13, 14 and 17, of which the four shortest non-empty texts
    (3, 151, 408 and 430 characters) were read; and the lengths, and nothing else, of the 24
    known-item abstracts (shortest 1,014 characters). The smoke round of item 17 was
    re-assembled under the rule from its stored responses and decisions, with no request and no
    model call: 3 of its 115 screening records are `no_abstract`, 112 are judged, 2 records go
    to extraction (5 before), the gate audit has 0 positives in 83 sampled records (3 in 86
    before), and 2 eligible families hold the same 3 claim records (5 families before).
19. The round-8 review (`planning/perplexity_paper1_final/11_REVIEW_round8.md`), which asked for
    verdicts read on the finite-corpus bounds, release identity undetermined under unclear
    attribution, claim-specific dates for the orderings of families on a pair, the removal of
    the outside check of the search (no list was obtained), and no country table. Each change
    was made on synthetic records and committed tables, with no claim extracted and no
    in-window record read.
20. Requests to the authors of two dataset source papers: on 2026-10-02 to the authors of
    Emilsson et al. 2018 for Table S1 (the protein list of the AGES array), and on 2026-10-03 to
    the corresponding author of Folkersen et al. 2020 for the 2 of the 92 SCALLOP CVD-I proteins
    that failed quality control. No reply had been received when this document was frozen.

No registered search (§Data collection procedures) has been run, and no eligibility decision
other than those of item 12 and no extraction has been made on any record in the window.
Searches, eligibility decisions and extraction have been run on records first public before
2019, as items 13, 14 and 17 state, and the eligibility prompt alone on the known items, which
lie in the window, as item 12 states. The stored responses of the pre-2019 runs hold six
records that PubMed dates in 2019 (items 14 and 17); none was read or sent to a model.

Item 1 bears on H1. Liu et al. 2025 "analysed 2,075 unique exposure‑outcome trait pairs
investigated by two or more independent studies", scored each pair by Cdirection =
(n_concordant − n_discordant) / (n_concordant + n_discordant) over pairwise study comparisons,
state that "Pairs involving null directions are excluded from calculation", classify an effect
by the sign of its point estimate as "positive (β > 0), negative (β < 0), or null (β = 0 or
missing)", include trait pairs matched by embedding similarity ("fuzzy matches (different
labels matched via embedding similarity exceeding 0.70"), and call a pair discordant when C is
below 0 ("20.2 percent (n=419) demonstrate discordant results"); their Figure 5 legend states a
different rule ("+1 if both report same direction, ‑1 if opposite directions, 0 if either is
null"). Their "independent studies" are different studies, not studies on disjoint data, and
their null is not `reported_nonsignificant_or_null`. Their unit cannot be reproduced exactly, so
H1 has no benchmark; the Liu-analogue in §Indices is descriptive, with these differences stated
beside it. The quotations are pinned in
`claims/liu2025mrkg.yaml`. Items 2–3 anchor H2. Item 11 is
a review of an earlier draft of this document. Item 9 bears on the drug-status and
reference-screen outcomes for a handful of named targets; those outcomes are descriptive and
computed by script for every pair. H2 is directional. Item 13 touched no in-window record.
Item 14 bears on the rules that name its counts (document classes, citation-chasing scope, the
status classes and report rules, the outcome-ontology rule, therapeutic areas, assay-list
attachments, the trait mapping): each was fixed with those resource counts known and no claim
extracted, and where a count showed that the other reading could move a result, that reading is
a registered sensitivity analysis. Item 15 bears on the enrichment backgrounds, the
quality-control flag rule, the name rule of the wording class, the gate audit of citation
chasing, the alias relations, the disease-level cross-reference mappings of phenotype terms
and the obsolete-label replacements: each was fixed
after the round-6 review, with those resource counts known and no claim extracted. Item 16
bears on H2b and on every registered secondary outcome: each was defined with no search run, no
claim extracted and no in-window record read, on synthetic records only. Item 18 bears on the
`no_abstract` rule: its floor was fixed on the lengths of pre-2019 abstracts, with no abstract
in the window read. Item 19 bears on the verdict rule, the attribution rule of H2, H2b and the
resolvable share, the claim dates of the date-ordered secondaries and the country variable:
each was fixed with no search run and no claim extracted. Every eligibility, extraction,
mapping and counting rule is applied by a committed prompt or script; no person judges any
abstract. The one manual step is the coding of dataset names that the automatic mapping leaves
unresolved (§Measured variables), which concerns dataset and platform identity only. The window's start is a scope decision taken with Zheng et al. 2020 known (item 7); its
substantive reason is that high-throughput proteome-wide MR first appears in 2019, and every
outcome is also reported for 2020–2025 (§Other planned analysis).

## Study type

Non-randomized study
Descriptive study

## Intention for causal interpretation

No causal relationship inferred

## Blinding of experimental treatments

No blinding is involved.

## Additional blinding during research or analysis

GPT-6.1 Sol reads each abstract without access to any other abstract's output, and the
verification script runs without access to any aggregate. No aggregate count is computed until
extraction, quotation pinning, verification and mapping of every abstract are complete and
committed. Manual dataset coding works from the queue of unresolved names, before any H1, H2 or
enrichment table is computed.

## Study design

Seven stages, each committed before the next begins:

0. **Before the freeze.** The queries in all three sources, the search, screening-set,
   citation-chasing and gate-audit scripts, the known-item calibration set, the
   negative-control set, the keyword prefilter and its term lists, the extraction prompt, the
   full-text prompt and the JSON schema (with the prompt-development results), the
   wording-class and novelty keyword lists, the dataset dictionary, the mapping script with
   pinned ontology and UniProt releases, the verification script with its pinned HGNC/UniProt
   name and alias tables, EFO/MONDO label and exact-synonym tables and direction lexicon, the join scripts with pinned releases of Open Targets
   Platform, ChEMBL, Reactome, the per-platform assay lists and the EpiGraphDB pQTL MR resource,
   the canonical-identifier collision table, the ontology edge table, the therapeutic-area
   table, the assay-list source and attachment tables with the tables derived from published
   supplementary files, the outcome alias table with its relations, the phenotype
   cross-reference and obsolete-label tables, the EpiGraphDB mapping and alias tables,
   the pleiotropic-locus list, the dataset components
   table and relation rules with their unit tests, the manual dataset-coding script and table
   layout, the registry builder, the funnel, repeat-run, negative-control and analysis scripts
   with their synthetic tests, the scripts of the registered secondary outcomes and of the record
   metadata, the `no_abstract` floor
   (`scripts/abstract_floor.py`), the table of pQTL row attributes, the run
   order (`RUNBOOK.md`), and a complete dry run on synthetic
   records are committed. The tests and dry runs show that the scripts do what the registered
   rules say; they do not show that the rules are valid. The freeze commit follows.
1. **Search.** The registered queries run on each source on one day (one UTC date), within 14
   days after the freeze. Citation chasing follows. Raw responses, counts, timestamps and
   checksums are committed; the citation-chasing response bodies are stored on the Modal volume
   and their manifest (URL, timestamps, byte count and sha256 of every body) is committed.
2. **Eligibility.** The keyword prefilter orders the screening set; GPT-6.1 Sol decides
   eligibility from title and abstract for every record in it that has an abstract
   (§Data collection procedures, records without an abstract).
3. **Extraction.** GPT-6.1 Sol extracts every claim from every eligible abstract.
4. **Verification and mapping.** Every abstract is pinned as a source artifact and every
   evidence span as a quotation with the `citations` CLI; the verification script checks each
   claim against its span, maps proteins and outcomes and builds the claim registry. Dataset
   names the mapping leaves unresolved are then coded manually and the registry is assembled
   with the codes.
5. **Joins.** Scripts join the committed registry to the pinned Open Targets Platform, ChEMBL,
   Reactome, platform panel and EpiGraphDB releases, and look up the OpenAlex record of every
   registry and preprint record of the eligible families (§Data collection procedures, record
   metadata). Every response and file checksum is committed.
6. **Full-text concordance (secondary).** After the primary results are committed, the
   Europe PMC open-access full texts of eligible families are fetched, extracted with the full-text prompt,
   verified and compared with the abstract records (§Other planned analysis).

**Dates.** A family's date is its first public appearance: the earliest public version whose own
abstract is judged eligible or `eligibility_uncertain` under the registered eligibility rule (a
preprint's first publication date when its abstract is; otherwise the journal online-first date;
otherwise the issue date), taken from source metadata by script: PubMed's electronic article
date, else its issue date; Europe PMC's electronic publication date, else its issue date, and
for a preprint its first publication date; OpenAlex's publication date. Title-level family linkage alone never
dates a family by a version whose abstract does not describe the protein analysis. Dates keep
the resolution the source gives (day, month or year). The confirmatory window is first
public 2019-01-01 to 2025-12-31. Papers first public from 2026-01-01 to the search date form a
separate update set, reported apart and excluded from H1 and H2.

**Study families.** A preprint and its journal version form one study family, linked by script
from DOI, PMID, PMCID and preprint "published as" links, and by fuzzy matching (title token-set
ratio ≥ 0.9 and the same first author). A fuzzy link joins only a preprint and a journal record,
never two journal articles or two preprints; never a record whose explicit identifiers link it to
a different record (a preprint whose "published as" DOI names another article, or a journal
record already linked to another preprint); and only when the preprint's first public date is
not later than the journal record's at the resolution the two dates share
(`scripts/link_families.py`). The journal version's abstract is the record extracted;
the family's date is its earliest, and it sets the family's position in the landscape counts. A
family's preprint abstract is extracted as well, for dating only. No registered source separates
the versions of a preprint: the preprint abstract is the one Europe PMC holds (else OpenAlex),
dated by the preprint's first publication date, so a pair first stated in a later preprint
version is dated to the first. The variable is therefore the earliest family publication date
applied to the retrievable preprint abstract, reported under that name and never as the date a
claim first appeared; a sensitivity analysis dates claims from registry abstracts only.
A family's claim date on a pair is the public date of the earliest family abstract (preprint
or journal) whose verified claim records hold that exact canonical pair; a family with a
journal abstract only dates its claims by the journal abstract's public date. Claim dates, and
never the family's first public date, order families on a pair: novelty, the first claim of a
pair, the period in which a pair was first claimed or became repeated, the pairs claimed per
year, and the earlier family a later one may cite. A family's first public date is used for
family entry only (families and claim records per year, the landscape). A family whose journal
abstract is judged not eligible is not an eligible family. A family whose journal record is
`no_abstract` takes its eligible preprint record as its registry record. A family counts once
in every result. Every link is logged with its rule; fuzzy links are counted and a sensitivity analysis
drops them.

**Document class.** Each record is `journal` (a PubMed record that is not a preprint; a Europe
PMC record of source MED or PMC; an OpenAlex work of type article, review, letter or
editorial), `preprint` (PubMed publication type Preprint; Europe PMC source PPR; OpenAlex type
preprint) or `other` (conference abstracts, dissertations, datasets and repository copies,
peer-review reports, patents and every other type), read from the first source that holds the
record in the order PubMed, Europe PMC, OpenAlex. Records of every class that have an abstract
are screened. Records
of class `other` are counted and enter no primary result. A sensitivity analysis keeps them:
such a record joins the family of the journal and preprint records that share its title (same
ratio) and first author when those records are in one family, adding nothing to it, and is a
family of its own otherwise.

## Randomization

N/A — nothing is sampled or assigned.

## Data collection procedures

**Sources and queries.** PubMed; Europe PMC (covering medRxiv and bioRxiv); OpenAlex. OpenAlex
requests carry an API key in the request header, never stored in any output, and no email
address. PubMed text is given; the Europe
PMC and OpenAlex versions are block-for-block translations committed in `search/queries.md`.
Neither accepts a truncated phrase inside a Boolean query, so each truncated phrase is written
out as its listed completions, and the hyphenated forms of `colocali*` and `repurpos*`, which
PubMed's truncation retrieves, are added. The MeSH term is Europe PMC's `KW` field and is
omitted in OpenAlex; `[dp]` is Europe PMC `FIRST_PDATE` and OpenAlex `from_/to_publication_date`.
PubMed's `[tiab]` also reads author keywords, which the other two fields do not; this is not
compensated. A record found in several sources takes its title, first author, date and document
class from PubMed, else Europe PMC, else OpenAlex, and the first abstract in that order of at
least 200 characters; a PMID returned only by Europe PMC or OpenAlex is fetched from PubMed.

**Records without an abstract.** A record for which the sources hold no abstract of at least 200
characters (counted after runs of whitespace are collapsed) is `no_abstract`
(`scripts/abstract_floor.py`). The census reads abstracts, and such a record states no abstract
claim. It is classed by script when a screening set is assembled, before the keyword prefilter
and before eligibility:

| stage | a `no_abstract` record |
|---|---|
| keyword prefilter, gate, gate audit | is not read: never marked, never sampled, never a positive, outside the audit's denominator |
| eligibility and extraction | is not sent to GPT-6.1 Sol and has no decision |
| citation chasing | is never a seed |
| study families | is linked like any record and adds nothing: it never dates the family and is never the registry record, which is chosen among the family's records that have an abstract |
| negative controls | is counted, not judged, and outside the specificity denominator |
| funnel | is counted per screening set (the search and each chase round) |

A family with no eligible record that has an abstract is not an eligible family. The floor is a
convention fixed on records first public before 2019 only (foreknowledge item 18;
`docs/stage0_build/NO_ABSTRACT_FLOOR_2026-10-02.md`): of the 313 such records held, 7 have no
abstract in any source, 2 have a stub of 3 and 151 characters, and the other 304 have 408
characters or more; 200 lies above both stubs and at about half the shortest abstract. Every
known item has an abstract of at least 1,014 characters. The floor has no sensitivity analysis:
criterion 2 of the eligibility rule cannot be answered from a title, and every record below the
floor judged before the freeze was `uncertain` with no claim record. Its reach is reported
instead: the funnel lists the `no_abstract` records with no text and with a stub, by document
class, and those whose title alone holds a genetic term and a protein term of the keyword
prefilter.

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
         OR (plasma[tiab] AND protein*[tiab])
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

**Q1** `(MR) AND (PROT) AND DATE`; **Q2** `(MR) AND (PLAT) AND DATE`; **Q3**
`(TARGET) AND (PQTLB) AND (GEN) AND DATE`; **Q4** `(LOCUS) AND (PQTLB) AND DATE`. The update
set runs the same queries with UPDATE. The union across queries and sources, deduplicated by
PMID, PMCID and DOI, is the screening set.

**Prefiltered citation chasing.** Backward and forward citations of every screening record
judged eligible, `count_not_stated` or `eligibility_uncertain`, in either window, are retrieved
from OpenAlex, restricted to works with an OpenAlex publication date of 2019-01-01 or later,
repeating until a round adds no eligible paper, to a maximum of three rounds. Chased records
that have an abstract are gated by the keyword prefilter: the records it leaves unmarked are screened by the same
procedure, and the marked records are not screened, so the chase is prefiltered and is never
called exhaustive. A sample of the marked records audits the gate in each round
(`scripts/gate_audit.py`). It is judged by the eligibility prompt in batches of 600 records,
taken in one fixed order: the marked ids, sorted, shuffled once with `random.Random(20261001)`.
A sampled record judged eligible or uncertain enters the ordinary workflow: extraction, family
linking, the registry and the seeds of the next round. After each batch the exact
(Clopper–Pearson) one-sided 95% upper bound of the share of judged sampled records that are
eligible or uncertain is computed. Sampling stops when every marked record has been sampled,
when that bound is below 0.5%, or 3,000 records have been sampled in the round; otherwise the
next batch is drawn. One positive in a first batch of 600 gives a bound of 0.79%, so any
positive draws a second batch. Per round the funnel reports the records marked, sampled and
judged, the positives, the share with its bound and its two-sided 95% interval, the
estimated number of eligible records among the marked records not judged (the share and its
interval ends times their number), and the `no_abstract` records of the round beside them. A round that stops at 3,000 sampled records with the bound
not below 0.5% is reported as "cap reached without satisfying tolerance". A sensitivity analysis removes the families found only by
chasing.

**Search calibration.** Before the freeze, a known-item calibration set of at least 20 papers that appear to be
proteome-wide MR analyses, spanning years, platforms and journals, is assembled by title from
reference lists without extracting any field, and listed by DOI in `search/known_items.md`. At
least a quarter of the known items have titles that do not contain "proteome-wide" or
"proteome". Before the freeze every known item must be retrieved by at least one registered
query and judged eligible under the registered eligibility prompt. The eligibility check is the
one exception to the rule that no abstract in the window is read with a prompt before the freeze:
GPT-6.1 Sol receives each known item's title and abstract with the eligibility prompt only,
returns only the eligibility fields (the three criteria, the stated tested and other protein
counts and their sentences, the exclusion categories and the `also_tissue_or_csf` flag), and no claim, direction, dataset or outcome is requested or
recorded, so no registered outcome is exposed. Only the decision and its reason codes are read.
A miss at either step prompts a query or prompt change before the freeze, logged below the line
with the item that prompted it; a known item the check shows to be genuinely ineligible is moved
to a removed section of `search/known_items.md` with its reason, and the set is 24 items after
the removal of PMID 35300523 (90 proteins tested). The eligibility prompt was revised until every
retained known item passed, so the 24 of 24 result is calibration and does not estimate the
sensitivity of the search or of the eligibility prompt. The known items are a calibration and
known-item retrieval check, not independent validation of the search. No published study list
was obtained as an outside check (foreknowledge item 16), and the search has none. Claim
verification of the known items is reported with the census, after the freeze.

**Negative-control set.** Before the freeze, 50 records first public 2014–2018 were drawn by
`scripts/assemble_negative_controls.py`, 10 from each of five PubMed queries that make a record
ineligible by construction: MR of a non-protein exposure; plasma or serum proteomics with no
genetic term; reviews of MR; pQTL mapping with no MR, causal or SMR term; protein or proteome QTL
studies in animals or plants. The draw uses `random.Random(20261001)` over each query's sorted
PMIDs after removing the development abstracts and known items; the PMIDs and titles are in
`search/negative_controls.jsonl`, with the queries and hit counts in
`search/negative_controls_meta.json`. No abstract of these records was fetched before the
freeze. After the freeze the frozen eligibility prompt and rule are run once on the 50 records,
and the share judged not eligible is reported per stratum as specificity for those five record
types only. A control record classed `no_abstract` is counted and not judged. The set is never
used to revise a prompt.

**Record metadata.** At stage 5, every registry and preprint record of every eligible family is
looked up in OpenAlex by DOI, else PMID, else OpenAlex identifier
(`select=id,doi,ids,referenced_works,authorships`; responses stored and checkpointed as the
search's; `scripts/record_metadata.py`). Per record the script keeps the sources whose
registered queries returned it (from the search's query streams), the citation-chasing round
that added it, its journal title (PubMed, else Europe PMC, else OpenAlex), its OpenAlex works,
whether the looked-up work has a reference list, the works it cites, and the country code of the
first listed institution of its first author (§Measured variables), which is collected and not
tabulated.

**Keyword prefilter.** A committed script marks records whose title and abstract contain no MR or
genetic-instrument term or no protein or pQTL term; the two lists are the title-and-abstract
terms of the registered blocks (MR, GEN and LOCUS; PROT and PQTLB;
`search/prefilter_terms.json`). For the registered search the mark orders the screening queue
and is reported; it never excludes a record, and every record the queries retrieve that has an
abstract goes to GPT-6.1 Sol. For citation chasing it is the gate described above.

**Tool.** GPT-6.1 Sol (OpenAI) is the only extraction tool. It is called through the Responses
API as model `gpt-6.1-sol`, with reasoning effort `medium`, no tools (so no web access), `store`
false and strict JSON-schema output. The API accepts no temperature parameter and exposes no
dated snapshot: the model string it returns is recorded with every response, together with the
UTC date and time of every call. It receives the title and abstract only, with the committed
prompt and JSON schema; it decides eligibility and extracts claims. No second model enters
any stage, and no Claude Code reading or human coding enters eligibility, extraction,
verification, direction or the mapping of proteins and outcomes. The one manual step is the
coding of unresolved dataset names (§Measured variables). Every request, response (including
failed and invalid ones), model string, endpoint and date is cached and committed. A response
that fails schema validation is re-run once and otherwise recorded as `extraction_failed`: a
technical missing outcome, never an exclusion, and claim counts are bounded over the failures
(§Missing data). Repeat-run stability: GPT-6.1 Sol is run a second time, with the same prompt,
on a random 10% of eligible abstracts (seed `20261001`), and field-level agreement between the
two runs is reported; the first run is the registered extraction. The sample is ceil(0.10 × n)
of the records judged eligible, `count_not_stated` or uncertain, ids sorted. Within an abstract
the records of the two runs pair on folded protein, folded outcome and context key, then the
records left over pair on protein and outcome alone, each in output order; the share of records
paired and the exact agreement per field among paired records are reported
(`scripts/repeat_run_agreement.py`).

**Prompt development.** The prompt and schema are developed on abstracts first public before
2019-01-01 only, listed by PMID and DOI in `prompts/dev_abstracts.jsonl` and
`prompts/REVISIONS.md` (never in the prompt text the model receives), and revised until
GPT-6.1 Sol returns schema-valid output whose evidence spans pass the quotation and verification
checks; every revision and its development-set metrics are committed in `prompts/REVISIONS.md`.
The development metrics are internal consistency checks (schema validity, quotation
verification, mapper/verifier acceptance rate); the development set is not labeled, so they do
not estimate extraction recall or precision. The full-text prompt is developed on pre-2019
open-access papers only (`prompts/dev_fulltext.jsonl`).
The prompt at the freeze is the registered prompt. Apart from the eligibility-only known-item
check (§Search calibration), no abstract in the window is read with any prompt before the
freeze.

**Reference resources.** Queried by committed script after the registry is committed (stage 5),
never by a tool reading abstracts. Releases, dates and checksums are listed in `RELEASES.md`:
ChEMBL `chembl_37` (`drug_mechanism` with `direct_interaction` and `molecular_mechanism`,
`target_dictionary.target_type`, `target_components`, `component_sequences`,
`molecule_hierarchy`, `molecule_dictionary`, `drug_indication`, `max_phase_for_ind`,
`action_type`);
Open Targets Platform 26.09 (`clinical_report`: `id`, `drugs.drugId`, `diseases.diseaseId`,
`trialOverallStatus`, `trialStopReasonCategories`, `qualityControls`, `source`, `type`;
`disease`: `id`, `name`, `therapeuticAreas`); Reactome release 97 (UniProt-to-lowest-level-pathway
mapping); MONDO v2026-09-01 and EFO v3.93.0, the EFO release on which Open Targets 26.09 was built
(EFO v3.94.0 is recorded in `RELEASES.md` but not used); per-platform assay lists mapped to UniProt
(Olink Explore 3072 and 1536 from the UK Biobank Pharma Proteomics Project protein maps;
SomaScan v4 from Eldjarn et al. 2023 Supplementary Table 2; earlier Olink and SomaScan panels
from the pinned pQTLdata package; and the lists that no package holds, from the supplementary
tables of the datasets' own source papers, `verification/platform_list_sources.csv`, with the
files that feed derived tables in `verification/published_source_files.csv`), each pQTL
row of the dataset dictionary attached to its list by the committed table
`verification/platform_assay_attachments.csv` (§Pathways); and
EpiGraphDB's pQTL MR resource (Zheng et al. 2020; 989 proteins × 225 traits). EpiGraphDB offers
no bulk file, so the resource is frozen as a snapshot of its API with the p-value filter lifted,
retrieved 2026-09-30 by `scripts/pin_epigraphdb_pqtl.py`: 179,928 of the 222,525 possible
protein–trait pairs. The pQTL resource is chosen over the xQTL browser (1,740 proteins × 576
phenotypes) because it is the published systematic screen of Zheng et al. 2020 that the field
cites as its reference. Each release string, download date and file checksum is committed.

## Data collection procedures - File upload

N/A — queries, prompt, schema, dictionaries and scripts are committed before the freeze.

## Sample size

Every record retrieved that has an abstract is screened; every eligible abstract and claim
enters. There is no target n. The PubMed union for 2020–2025 was 2,089 records (foreknowledge item 8).

## Sample size rationale

N/A — every eligible record retrieved is included.

## Starting and stopping rules

The search runs once, within 14 days after the freeze; citation chasing stops by the rule above.
Records indexed after the search date are not added.

## Manipulated variables

N/A — nothing is manipulated.

## Measured variables

**Eligibility (GPT-6.1 Sol, from title and abstract).** GPT-6.1 Sol answers three criteria `yes`,
`no` or `uncertain`: (1) the paper uses genetic instruments for plasma or serum protein levels in
MR or SMR, answered `yes` when at least some of the instrumented proteins are measured in plasma or
serum; (2) the abstract states at least one result of the protein analysis on a disease, trait or
other outcome, including a count of significant protein–outcome pairs or a null result, with no
requirement that a protein be named; (3) the abstract describes a proteome-wide or panel-wide
screen. A committed script applies the rule: a paper is not eligible when any criterion is `no`,
an exclusion applies, or the applicable protein count is below 100; otherwise it is
`eligibility_uncertain` when any criterion is `uncertain`, and eligible when all three are `yes`.
The tested count is the number of proteins the abstract states were tested as exposures in the
MR or other genetically proxied analysis; a number of proteins measured, assayed, with pQTLs or
instrumented, or available for analysis, not stated as tested, is recorded as `count_other`.
Neither field ever holds a number of proteins associated with, significant for, or causally
linked to an outcome: such numbers are results, not denominators, and when the abstract gives
only such result counts both fields are empty. The value 100 is a scope convention, a round number chosen
when the study was designed to separate broad screens from single-target or small
candidate-protein studies; it is not a natural boundary in proteomics or in MR methodology. No
analysis informed it, and the known-item runs did not change it (they changed which stated
count it applies to, as logged). Its effect is that a study of one 92-protein panel is not
eligible, and a sensitivity analysis keeps only the
families stating at least 1,000 proteins tested. The 100-protein floor applies
to the tested count when the abstract states one. When it states no tested count but states a
`count_other`, the floor applies to `count_other`: below 100 the paper is not eligible
(`fewer_than_100_proteins`); at 100 or more it is classed `count_not_stated` and stays eligible.
When the abstract states neither count, the paper is classed `count_not_stated` and stays
eligible. An `eligibility_uncertain` paper goes to extraction as eligible, counted and removed in
a sensitivity analysis. Reviews, protocols and non-human studies are excluded, and so is tissue
or CSF proteomics when none of the proteins analysed are measured in plasma or serum. A paper that
analyses plasma or serum proteins together with tissue, CSF or cell proteins is eligible and
flagged `also_tissue_or_csf`. An eligible paper whose extraction yields no claim naming a protein
(for example, one that reports only counts of significant pairs) enters the paper-level counts
with zero claims and is counted as `eligible_no_named_claims`.

**Claim record.** A claim record is one explicitly stated genetically proxied protein–outcome
result for one analysis context. Statements repeated without a distinct direction, dataset,
ancestry, subgroup or analysis context are merged. Distinct results for the same canonical
protein–outcome pair are retained separately when the abstract distinguishes their direction or
analytic context. A genetically proxied result is an MR, SMR or other estimate that uses genetic
variants (cis variants, pQTLs or a genetic score for the protein) as instruments for the
protein. GPT-6.1 Sol extracts every protein–outcome result the abstract states and labels its
`evidence_type`; only `mr_estimate` records are claims. Observational associations,
experimental results, associations of a variant with the outcome that the abstract does not
state as the protein's effect, and other results are counted by type and excluded. A sentence
naming several proteins and several outcomes gives one record per combination only when its
wording applies every protein to every outcome or pairs them explicitly ("respectively");
otherwise the record is flagged `relation_ambiguous`. Fields (prompt revision r8):

| field | values |
|---|---|
| `protein_as_written` | verbatim |
| `outcome_as_written` | verbatim |
| `direction` | `raises` (higher protein, higher risk or trait), `lowers`, `reported_nonsignificant_or_null`, `not_stated`; an estimate that is not statistically significant is `reported_nonsignificant_or_null` whatever the side of its point estimate: its printed confidence interval includes the null value (1 for an odds, hazard or risk ratio; 0 for a difference, beta or change), or with no interval its printed P value is 0.05 or larger, or the abstract calls it non-significant; a stated absence of association takes the same value |
| `evidence_type` | `mr_estimate`, `observational`, `experimental`, `variant_association`, `other` |
| `claim_scope` | `overall`, `dataset_specific`, `ancestry_specific`, `subgroup_specific`, `sensitivity`, `unclear` |
| `analysis_context_as_written` | the words that set the record's analysis apart, verbatim, or `not_stated` |
| `subgroup_as_written` | the subgroup or ancestry the result is restricted to, verbatim, or `not_stated` |
| `pqtl_datasets` | names and releases as written, each once, or `not_stated` alone |
| `outcome_datasets` | names and releases as written, each once, or `not_stated` alone |
| `dataset_attribution` | `claim_specific` (named for this result or its stage), `whole_study` (named for the paper's analysis as a whole), `unclear` (named, but not tied to this result) |
| `platform` | `Olink`, `SomaScan`, `mass_spectrometry`, other as written, each once, or `not_stated` alone |
| `ancestry` | as written, or `not_stated` |
| `relation_ambiguous` | true when the wording does not link this protein to this outcome |
| `evidence_span` | one sentence, or two adjacent sentences, of the abstract that together state the record, verbatim |
| `claim_record_id` | assigned by script: `<pmid>:<record index>` |

`reported_nonsignificant_or_null` means that the abstract reports no statistically significant
estimate, or states no association, for the record. It is never read as evidence of no effect,
and every output table carries the value's full name. The schema requires at least one entry in
each list; the response validator rejects a repeated entry and `not_stated` beside a name, and a
response that fails is re-run once and otherwise recorded as `extraction_failed`.

**Quotation check.** Every abstract is saved as a source artifact, pinned by checksum with the
`citations` CLI, and every `evidence_span` is pinned as a quotation of it; `citations verify`
must find each span in its abstract. A claim whose span does not verify is dropped and counted.

**Wording class.** Assigned by script from `evidence_span` with committed keyword lists, first
match wins: `target` (target, druggable, therapeutic, drug, repurpos, treatment, intervention),
then `causal` (causal, causally, cause, effect of), otherwise `association`. A keyword matches
from the start of a word, with any ending, in any case ("repurposing" matches `repurpos`;
"because" does not match `cause`). Names are not wording: a keyword match that lies wholly
inside an occurrence of the record's `outcome_as_written` or `protein_as_written` in the span
is dropped ("treatment" in "treatment-resistant depression", "drug" in "drug-induced liver
injury"), the class is read from the matches that remain, and a record with no target keyword
left is `causal` when a causal keyword remains and `association` otherwise. A name occurs in
the span where its words follow one another, in any case, separated by spaces, hyphens or
dashes. Every match is stored with its position and the name it lay in, and the class without
this rule is stored beside the class and reported with the wording-class distribution.

**Mapping.** Proteins to a UniProt accession through the HGNC symbol route, with committed alias
tables: the verifier's HGNC entries take the `uniprot_ids` of the pinned HGNC complete set that
are entries of the pinned UniProtKB human reviewed file, and the record's accession is the union
over its HGNC entries (`scripts/canonical_ids.py`). One accession gives the protein identifier;
more than one (a complex or heteromer named as one analyte, or a gene with several reviewed
entries) gives no pair and is counted `pair_ambiguous`; none is counted `protein_no_uniprot`.
The verifier also returns terms that the EFO file imports from HP, OBA and Orphanet: when an
outcome name gives at least one MONDO or EFO identifier, its identifiers from those ontologies
are dropped ("rheumatoid arthritis" labels MONDO:0008383 and HP:0001370; the outcome is
MONDO:0008383). This is a priority among ontologies for one name, not a judgment that
phenotype or trait terms are worse: an OBA term remains the identifier of a quantitative trait
that has no MONDO or EFO term. A name that gives no MONDO or EFO identifier takes the disease
term that the pinned MONDO file cross-references to its phenotype terms, when the committed
table `verification/phenotype_cross_references.csv` gives every identifier of the name the same
single term ("hypertension" labels HP:0000822 only; MONDO:0005044, hypertensive disorder,
carries `xref: HP:0000822`); the table lists the HP terms that exactly one canonical MONDO or
EFO term cross-references with the source tag `MONDO:otherHierarchy` or `MONDO:equivalentTo`
(`scripts/outcome_alias_completion.py`). These are disease-level cross-reference mappings and
are reported under that name; they are not ontology equivalences, in particular where the
source tag is `MONDO:otherHierarchy`. Otherwise the name keeps its identifiers. Two MONDO or EFO
identifiers are never resolved against each other: a name that is the label or exact synonym of
a MONDO term and of an EFO-file term the pinned files do not assert to be one concept gives no
pair and is counted `pair_ambiguous`; a sensitivity analysis takes the MONDO identifier when
the name gives exactly one. Terms that the pinned files do assert to be one concept are merged
by the collision table before this rule is reached.
Outcomes to a single canonical identifier: a Mondo term for diseases and an EFO term for
non-disease traits, through the pinned EFO v3.93.0–MONDO v2026-09-01 cross-references and the
committed collision table `verification/mondo_efo_collision_table.csv`
(`scripts/build_collision_table.py`), which lists every MONDO term and EFO-file term that the
pinned files assert to be one concept with both terms live, takes the MONDO term when MONDO
places the concept under disease or injury and the EFO-file term otherwise, and lists conflicts
(one-to-many equivalences, branch disagreements) beside the choice. The six rows with a branch
disagreement (MONDO and EFO on opposite sides of the disease/trait line) are not merged: both
identifiers stay separate canonical identifiers. An identifier outside the
table is its own canonical identifier. The HGNC and source outcome identifiers are kept on
every record, and pair identity uses the canonical fields only. Unmapped values are counted.

**Therapeutic areas.** The disease category of an outcome is its Open Targets 26.09 therapeutic
area or areas, read from the `therapeuticAreas` field of the pinned `disease` file (26 areas;
a term can lie in several) and committed per canonical identifier
(`verification/therapeutic_areas.csv`, `scripts/therapeutic_areas.py`). An outcome that the
file does not carry takes the areas of its nearest ancestors in the ontology graph (§Units)
that are in it: the union over the ancestors at the smallest distance that have any. An outcome
with no such ancestor has no area and is counted `no_therapeutic_area`; the rule that gave each
outcome its areas is recorded: whether they are the file's own (`direct`) or `inherited`, the
distance to the nearest ancestors that gave them, those ancestors, and whether several
ancestors were equally near. Six areas do not count toward hub breadth and are not disease
areas: `measurement`, `phenotype`, `biological_process`, `medical procedure`, `non-human animal
disease`, and `genetic, familial or congenital disease`, which groups disorders by cause across
every organ system. `injury, poisoning or other complication` is a disease area.

**Claim verification.** A committed deterministic script checks each claim against its
verified `evidence_span`:
- **protein:** `protein_as_written` maps to a UniProt accession through the pinned HGNC/UniProt
  name and alias tables, and a name or alias of that accession occurs in the span;
- **evidence type:** `evidence_type` is `mr_estimate`; any other type is `not_mr_estimate`;
- **outcome:** `outcome_as_written` maps to the canonical identifier through, in order, the
  committed alias table `verification/outcome_aliases.csv`, the pinned EFO/MONDO labels and
  exact synonyms, the labels of obsolete EFO terms, and the related synonyms, stopping at the
  first that matches; and the matched name or a label or synonym of the identifier occurs in the
  span. The alias table is the only hand-written alias source: clinical abbreviations and the
  outcome names the development set failed to map, each resolved to a live term of the pinned
  files by `scripts/build_outcome_aliases.py` from the committed seed
  `verification/outcome_alias_seed.csv`, and each with its source, its rationale and its
  relation to the term: `exact_equivalent`, `normalized_equivalent`, `broader_proxy` or
  `derived_measurement`. The relation of the alias that mapped a record is stored on the record
  and the records are counted by relation. An obsolete label stands for the live term that the
  EFO file names as the retired term's single replacement ("mean corpuscular volume", once
  EFO:0004526, is OBA:0003460), and only when it is not a label or exact synonym of any live
  term (`verification/obsolete_label_replacements.csv`, built from the pinned files by
  `scripts/outcome_alias_completion.py`). No rule uses the similarity of two names;
- **direction:** a committed parser reads the effect estimate printed nearest the outcome's
  mention in the span (an odds, hazard or risk ratio, or a difference such as a beta or a unit
  change, with its confidence interval and/or P value). The estimate gives `raises` or `lowers`
  from its side of the null value (1 for ratios, 0 for differences), and
  `reported_nonsignificant_or_null` when the printed interval includes the null value or, with
  no interval, when P is 0.05 or larger. Tie-breaking: each estimate claims the text on one side
  of it (the text after it when that text begins with "for", "in" or "on", otherwise the text
  since the previous estimate); an outcome mention inside several estimates' text is resolved to
  the estimate preceded by an MR cue; if several remain, their directions must agree, else no
  estimate is assigned. When no estimate can be assigned to the outcome, the committed direction
  lexicon reads the span's cue words; the lexicon never reads printed ratios, a span stating no
  association reads `reported_nonsignificant_or_null`, and a lexicon reading of a span shared by
  records of both directions is `direction_unverified`. When neither decides, the record is
  `direction_unverified`;
- **datasets:** each dataset name is mapped, on its side, to its candidate rows of the dataset
  dictionary (§Units); the mapping state and candidates are recorded, and no name is ever
  resolved to a first match;
- **relation:** a record flagged `relation_ambiguous` fails.

A claim enters the registry only when its span verifies, its evidence type is `mr_estimate`, its
protein and outcome both match, and it is not `relation_ambiguous`. Its direction enters
direction-based results only when the parser or lexicon returns the same value as GPT-6.1 Sol;
otherwise the claim stays in the registry with direction `direction_unverified`. A registry
record whose protein or outcome maps to more than one identifier after the collision table gives
no pair and is counted `pair_ambiguous`. Every failure is counted by reason. Every record,
passing or failing, is written with GPT-6.1 Sol's fields unchanged and with its mapping
provenance: `protein_mapping_state` and `outcome_mapping_state` (`mapped`, `ambiguous`,
`unmapped`, `not_in_span`), `dataset_mapping_state`, `direction_verification_state`,
`mapping_rule_used` (the tier or rule that matched, per field), `candidate_identifier_count` (per
field) and `first_failure`.

**Units.**
- **Pair:** UniProt accession × canonical outcome identifier (§Mapping). Every join and match uses
  exact pairs.
- **Family–pair records:** a family's claim records on one pair. Records with the same folded
  context key (`analysis_context_as_written` and `subgroup_as_written`) and the same effective
  direction are deduplicated; every other record is retained. A record's effective direction is
  GPT-6.1 Sol's direction when the verifier agreed with it, else `direction_unverified`.
- **Family–pair direction**, first that applies: `mixed` (at least one verified `raises` and one
  verified `lowers` record); `raises` or `lowers` (verified directional records all in one
  direction); `raises_with_nonsignificant` or `lowers_with_nonsignificant` (the same, with a
  verified `reported_nonsignificant_or_null` record as well); `nonsignificant_only`; `unresolved`
  (only `not_stated` or `direction_unverified` records). `context_unclear` is set when any record
  has `claim_scope` `unclear`; it never changes the direction. `mixed` is reported as
  within-family discordance and leaves H1; the `_with_nonsignificant` values count as their
  direction in H1 and are removed in a sensitivity analysis. The counts of every value are
  reported before H1 is computed.
- **Ontology graph:** the union of the unconditional `is_a` edges of the pinned MONDO and EFO
  files between outcome terms, each end replaced by its canonical identifier
  (`verification/ontology_edges.csv`, 96,473 edges); the distance between an ancestor and a
  descendant is the shortest path.
- **Hierarchy relations:** for two pairs of one protein whose outcome terms stand in an
  ancestor–descendant relation in the ontology graph, the relation is recorded as
  `claim_broader` or `claim_narrower` with the ontology distance. They are reported separately
  and never set a primary result. A pair family is an anchor pair with its one-step parent and
  child pairs only; no transitive chains.
- **Dataset dictionary:** a committed table (`dataset_dictionary.csv`, 121 rows) mapping dataset
  names and aliases to releases, with each release's participant sources in
  `verification/dataset_components.csv` (component identifiers, whether the composition is
  complete, and the `citations` claims files that pin each composition to the paper's methods or
  cohort tables); `UKB` is added to every release with UK Biobank participants. Icelandic cohorts
  are separate components, `AGES_REYKJAVIK` and `DECODE_COHORT`; a release with Icelandic
  participants whose components name neither is incomplete. `AGES_REYKJAVIK` is added to a
  deCODE release only where a pinned source places AGES participants in it. Components are cohorts, control sources included, never consortium names; a
  composition is complete only when the study-level list of the released stage was read, and a
  public release that differs from the paper's meta-analysis (without 23andMe, without UK
  Biobank, one ancestry) is its own row. Every FinnGen release carries the FinnGen legacy cohorts
  (Kurki et al. 2023) and every EPIC centre or sub-study carries EPIC. FinnGen R6–R12 are complete
  for the registered overlap flags (UK Biobank, Icelandic cohorts, the named pQTL cohorts) on the
  stated basis that FinnGen comprises participants of Finnish biobanks only; Kurki et al. 2023
  list the legacy cohorts to R5, and Finnish cohorts added after R5 cannot overlap a non-Finnish
  source. SWEBIC and STANLEY are separate components. A cohort listed in a release's pinned
  cohort table stays a component even where a footnote limits its role (in GIGASTROKE, `WHI`,
  "not included in global meta-analysis"; in MAGIC, `OXFORD_BIOBANK`, `UKHLS`, `VIKING` and
  `WHITEHALL2`, "VarExp only"); keeping such a cohort can move a pair only away from `disjoint`.
- **Dataset mapping** is set-valued (`scripts/dataset_relations.py`). A name maps, on its side,
  to zero, one or several candidate rows: first by exact match to a row name or alias; else
  through the longest alias that begins the name (later words never narrow the candidates); else
  as the beginning of aliases ("FinnGen" of "FinnGen R10"). A name whose later words name another
  dataset ("+", and, plus, with, meta-analysis, UK Biobank, MVP, Biobank Japan) never maps to the
  leading release alone: it maps to the meta-analysis rows carrying the leading alias and the
  named sources, preferring rows that name no further source ("FinnGen R12 and UK Biobank
  meta-analysis" → the FinnGen R12 + UK Biobank row), and with no such row it is
  `release_ambiguous` over the leading release and an unlisted combination whose known
  components include the named sources and whose composition is never resolved. A bare
  "FinnGen" is `release_ambiguous` over the FinnGen releases and the FinnGen meta-analysis rows,
  so it is never `disjoint`. A name matched through an alias
  without a digit that is not a row's own name ("INTERVAL", "CARDIoGRAMplusC4D") names no
  release and also takes the candidate `unlisted release of <alias>`. A name is `unique` with
  one candidate, `release_ambiguous` with several, `unmatched` with none, or `not_stated`. Its
  known components are those shared by every candidate; its composition is resolved when every
  candidate is complete and all have the same component set. No rule ever chooses one row out
  of several.
- **Family datasets:** for a family on a pair, the union per side of the names on all its
  records for that pair; names mentioned elsewhere in the abstract enter only through the
  records' `whole_study` attribution. A family's attribution on a pair is unclear when any of
  its records there has `dataset_attribution` `unclear`; it is then `unclear` in every relation,
  and the names of its `claim_specific` records are kept apart for the overlap rule below.
- **Manual coding of dataset names.** Where the automatic mapping does not resolve which
  release or assay platform a paper used, the paper is read and the name is coded
  (`scripts/manual_dataset_coding.py`).
  1. *Trigger:* a dataset name on a registry claim record whose mapping state is
     `release_ambiguous` or `unmatched`; one queue row per record, side and name as written.
  2. *Source read:* the paper's methods or data passage, in the Europe PMC open-access full
     text where there is one, else the abstract. When neither states the release or platform
     the row stays unresolved and is counted.
  3. *Record:* the quoted sentence pinned with `citations`, the dictionary row coded, and a
     `manually_coded` flag on the claim and on its family–pair record.
  4. *Scope:* dataset and platform identity only; never direction, significance, eligibility,
     protein or outcome.
  5. *Checks:* Claude Code codes, Perplexity checks, the author verifies. Claude Code reads
     the paper and codes the value with the pinned sentence; Perplexity is given the paper
     reference and the question without the coded value, and its answer is recorded; the author
     confirms each row against the pinned sentence. The author's check is a literal match: the
     pinned sentence, or the table it names, states the coded dataset name, release or count.
     It is not a judgment of the paper, and a row where the coded value is taken from a
     supplementary table or a companion source and not from the pinned sentence is recorded as
     such. A row is coded only when all three agree.
     A disagreement is resolved by rereading the source, and the resolution and the two
     original answers are kept; a row that cannot be resolved stays unresolved and is counted.
     Agreement at the second check is reported as a count.
  6. *What the coder and the checker see:* Manual coders and checkers receive only the
     unresolved dataset string, its local paper passage and candidate dictionary definitions;
     they do not receive the canonical protein–outcome pair, other families' dataset
     assignments, the resulting relation class, or any H1/H2 aggregate.
  7. *Rules for a code:* every code is committed before the registry is assembled with the
     codes. The source must identify the release: a name is never coded to the closest
     available release, and a row whose source does not identify one is `unresolved`. The two
     original answers stay in the committed table, and so does every disagreement.
  8. *Use:* a coded name is replaced by its dictionary row before the family datasets are
     formed. The number of manually coded claim records, family–pair records, H1 pairs,
     multi-family pairs and enrichment claims is reported, and a sensitivity analysis reruns
     H1, H2 and the pathway enrichment without the codes.

  The same three checks apply, before the freeze, to the 14 dictionary rows whose assay list
  was read from the dataset's source paper (§Pathways).
- **Dataset relation** between two families for one side (pQTL or outcome):
  `identical_release` (every name on both sides `unique` and the two release sets equal);
  `overlapping_participant_source` (not identical, and the known components of the two sides
  share at least one component, e.g. FinnGen R8 and R10, or two meta-analyses both containing UK
  Biobank); `disjoint` (every name on both sides has a resolved composition, no component is
  shared, and the two sides do not hold `AGES_REYKJAVIK` and `DECODE_COHORT` one on each side);
  `unclear` (anything else, including any `not_stated` or `unmatched` name, a side whose
  attribution is `unclear` in either family, and AGES-Reykjavik against deCODE with no shared
  component, whose participant overlap is possible but undocumented). The relation does not
  depend on the order of the two families.
- **Release identity** (for H2) between two families for one side: `undetermined` when either
  family's attribution is unclear, because name equality is not provenance when the abstract
  does not tie the named dataset to the claim; otherwise `identical` (every name on both sides
  `unique` and the two sets of releases equal; a family naming a discovery and a replication
  release has a two-release set, which equals a one-release set never), `not_identical` (every
  name matched, and no choice of one candidate per name makes the two release sets equal),
  `undetermined` (otherwise). The rule is symmetric in the two families.
- **Overlap** (for H2b) between two families for one side: `overlapping` (release identity
  `identical`, or dataset relation `identical_release` or `overlapping_participant_source`; or,
  when a family's attribution is unclear, the names of that family's `claim_specific` records,
  read against the other family's names (its `claim_specific` names when its attribution is
  unclear too), have relation `identical_release` or `overlapping_participant_source`: a
  component shared by names tied to the claim is a component of the claim's data), `disjoint`
  (dataset relation `disjoint`, which needs clear attribution on both families), `unclear`
  (otherwise). Disjointness is never read from the `claim_specific` names alone.
- **Independence edges:** for each pair, every two families with a directional family–pair
  direction form an edge labelled `independent` (pQTL and outcome relations both `disjoint`),
  `overlapping` (either side `identical_release` or `overlapping_participant_source`), or
  `unclear` (otherwise).
- **Edge class** (registered secondary outcomes): `identical_release` when the pQTL relation
  and the outcome relation are both `identical_release`; otherwise the independence-edge label
  (`independent`, `overlapping`, `unclear`). Two families on the same pQTL release and the same
  outcome release share their source data, so their directions are expected to agree, and
  agreement on `identical_release` edges is a positive control. It is not fixed by
  construction: the same releases can give different directions through instrument selection,
  harmonization, model choice, subgrouping or extraction error, and a share below 1 measures
  those.

**Novelty and prior claims.** `novelty_language` is set by script when `evidence_span` contains,
case-insensitively as whole words or phrases, novel, newly, "previously unreported", "not
previously", "for the first time" or "first evidence". The name rule of the wording class
applies: a match that lies wholly inside an occurrence of the record's `outcome_as_written` or
`protein_as_written` in the span is dropped ("novel" in "novel coronavirus infection"), and the
flag is set when a match remains. Every match is stored with its position and the name it lay
in, and the flag without this rule is stored beside the flag and reported with it.
`earlier_in_registry` is set when another
family's claim of the exact canonical pair has a strictly earlier claim date (§Study design).
Two dates are compared at the least precise resolution they share; dates equal at that
resolution, same-day dates included, are contemporaneous, and neither is earlier. A claim with no
earlier date and at least one such tie is `tied_or_unknown_order`; otherwise
`no_earlier_in_registry`. A hierarchy-related earlier pair (another family's strictly earlier
claim of the same protein on an ancestor or descendant outcome, at any distance) is recorded
separately as `related_prior_claim` and never sets `earlier_in_registry`. The unit is the claim
record. The registry holds eligible
2019–2025 abstracts only: pre-2019 papers, full texts, single-protein MR, smaller panels and
non-MR evidence are not searched, so `earlier_in_registry` says nothing about novelty in the
literature.

**Drug-development records of each pair.** Drugs acting on the protein, primary rule: ChEMBL
`drug_mechanism` records with `direct_interaction` = 1 and `molecular_mechanism` = 1 whose target
is a `SINGLE PROTEIN` of organism Homo sapiens mapped through `target_components` to the
protein's UniProt accession. Mechanisms on a `PROTEIN COMPLEX`, `PROTEIN COMPLEX GROUP`,
`PROTEIN FAMILY`, `SELECTIVITY GROUP`, `CHIMERIC PROTEIN` or `PROTEIN-PROTEIN INTERACTION` target
that has the accession among its components are recorded as `component_level_mapping` and enter
only a sensitivity analysis; other target types are not used. In ChEMBL 37, 4,477 human
drug-mechanism records meet the primary rule and 1,248 have a component-level target
(`outputs/resource_counts/chembl37_mechanism_target_types.json`). An indication matches the pair when its
canonical identifier equals the pair's outcome identifier; an indication one step broader or
narrower in the ontology graph is recorded separately as `related_indication` and never sets a
primary class. An indication identifier with several canonical identifiers, or a ChEMBL row
with a MeSH identifier only, matches nothing and is counted. Two separate outputs are computed.

A `clinical_report` row is a trial when it has a `trialOverallStatus` (every ClinicalTrials.gov
row of the pinned file and no other row). Rows of `type` SAFETY list adverse effects, not
indications, and are not read. Rows from regulator, label and nomenclature sources are records
for a matching indication and never set a trial class; they are never called trials, and each
pair's matching reports are listed by source. Rows carrying a `qualityControls` flag are not
read in the primary analysis (Open Targets leaves them out of its own aggregates); the flagged
reports that would have matched a pair are counted by flag and by source, and a sensitivity
analysis reads them and counts the pairs whose highest status changes. A report counts for a pair when any of its
drugs acts on the protein and any of its diseases matches. Open Targets drug identifiers are
collapsed to parents through the same ChEMBL hierarchy. A pair leaves this join only when its
outcome identifier is absent from the Open Targets disease index, the ChEMBL indication
identifiers and the report disease identifiers; a protein with no ChEMBL mechanism stays in the
join and has no drug.

Development phase comes from ChEMBL `max_phase_for_ind` only. Open Targets 26.09 `clinical_report`
supplies trial events only: each trial's `trialOverallStatus`, its `trialStopReasonCategories` and
its indications. Where the two sources differ on phase, ChEMBL's value is used. Before any
ChEMBL phase or action type is read, every molecule is collapsed to its parent through
`molecule_hierarchy` (`parent_molregno`), so salts and other forms of one drug count as one
molecule; a parent takes the highest `max_phase_for_ind` among its forms for each indication.

*Highest development status*, first that applies:

| class | condition |
|---|---|
| `approved` | a drug acting on the protein has ChEMBL `max_phase_for_ind` = 4 for a matching indication |
| `in_clinical_trials` | a trial of such a drug for a matching indication has `trialOverallStatus` RECRUITING, ACTIVE_NOT_RECRUITING, NOT_YET_RECRUITING or ENROLLING_BY_INVITATION |
| `stopped_negative_or_safety` | a trial for a matching indication whose `trialOverallStatus` is not SUSPENDED carries the stop-reason label `Negative` or `Safety_Sideeffects` |
| `stopped_other` | a trial for a matching indication whose `trialOverallStatus` is not SUSPENDED carries any other stop-reason label |
| `suspended` | a trial for a matching indication has `trialOverallStatus` SUSPENDED; suspended trials are not counted as stopped, whatever stop-reason label they carry |
| `completed_no_later_record` | completed or phase-recorded with no later record in the pinned resources: a drug for a matching indication has ChEMBL `max_phase_for_ind` 1–3 and no trial above is active, stopped or suspended; this is a statement about the pinned resources, not evidence that development ended |
| `other_matching_record` | a drug acting on the protein has a record for a matching indication and no class above applies: a ChEMBL phase of 0.5, -1 or none; a matching trial that is COMPLETED, of UNKNOWN status, an expanded-access record, or TERMINATED or WITHDRAWN with no stop-reason label; or a matching report that is not a trial; the reason is stored |
| `no_matching_trial_or_indication_record` | no drug acting on the protein has any record for a matching indication in the pinned releases |

The stop-reason labels are the 13 values of `trialStopReasonCategories` in the pinned 26.09 file,
used verbatim: `Another_Study`, `Business_Administrative`, `Covid19`, `Insufficient_Enrollment`,
`Invalid_Reason`, `Logistics_Resources`, `Negative`, `No_Context`, `Regulatory`,
`Safety_Sideeffects`, `Study_Design`, `Study_Staff_Moved`, `Uncategorised`. The negative-or-safety
subset is `Negative` and `Safety_Sideeffects`.

*Stopped-trial events*: every trial of a drug acting on the protein for a matching indication that
carries a stop-reason label and whose `trialOverallStatus` is not SUSPENDED, with its label stored verbatim, counted per pair whatever the pair's
highest status. Suspended trials are counted separately, with their labels stored verbatim. Collapsed classes map source labels by a
committed table; no source label is renamed silently.

`target_drugged_elsewhere` records whether a drug acting on the protein is approved for any other
indication (one-step related indications included; rows with no identifier or an ambiguous one
not). **Claim–trial-history co-occurrence** is the set of claims of wording class `causal`
or `target`, whose direction is not `reported_nonsignificant_or_null`, whose pair has any
stopped-trial event; a record reporting no significant estimate asserts no effect, whatever
keyword its span holds. A **directionally relevant stopped trial** is
a stopped-trial event at a matching indication with the label `Negative` or `Safety_Sideeffects`
whose drug's action is nominally aligned with the claim (below). Only these are called conflicts
with trial history, and never evidence that a claim is false.

**Nominal abundance–action alignment under the registered direction proxy.** The proxy maps a
genetic association with circulating protein abundance onto a pharmacological direction: a
claim with direction `raises` indicates decreasing the protein; `lowers` indicates increasing it. Each drug acting on the protein takes a direction from
its ChEMBL `action_type` by this rule, adopted verbatim from
`pqtl-mr-domain-of-validity/experiments/PREREG_direction_concordance.md` §3.2–3.4:

1. Parse: an empty field has no tokens; otherwise split on the delimiter, strip whitespace,
   uppercase, collapse internal whitespace, deduplicate.
2. Classify each token by the first tier that matches. Tier 1, exact: `INVERSE AGONIST` and
   `NEGATIVE ALLOSTERIC MODULATOR` → BLOCKING; `POSITIVE ALLOSTERIC MODULATOR` and
   `PARTIAL AGONIST` → ACTIVATING. Tier 2, contains `INHIBITOR`, `ANTAGONIST`, `BLOCKER`,
   `DEGRADER`, `DISRUPT` or `SUPPRESSOR` → BLOCKING. Tier 3, contains `AGONIST`, `ACTIVATOR`,
   `OPENER`, `STABILISER`, `STABILIZER` or `RELEASING AGENT` → ACTIVATING. Tier 4, anything else
   → AMBIGUOUS.
3. Drop AMBIGUOUS tokens; if at least one remains and all agree, BLOCKING is `decrease` and
   ACTIVATING is `increase`; otherwise the drug's direction is `ambiguous`.

The rule is used unchanged. ChEMBL 37's `POSITIVE MODULATOR` and `NEGATIVE MODULATOR` match no tier
before tier 4 and are therefore AMBIGUOUS.

Per claim, computed separately over the drugs with a record for a matching indication (a ChEMBL
indication row or a `clinical_report` row) and over every drug acting on the protein:
`concordant` (every directional drug matches the indicated change), `discordant`
(every directional drug opposes it), `mixed`, `ambiguous_only`, or `no_drug`. A drug's action
types are those of its qualifying mechanism rows on the protein. Claims without a verified
`raises` or `lowers` direction leave the alignment and are counted. The unit of the claim-level
drug outcomes is the claim record. The `concordant` share has an expected value set by its two
margins (it is high whenever most claims raise risk and most drugs block): among claims classed
`concordant` or `discordant`, the share indicating a decrease times the share whose drugs
decrease the protein, plus the product of the two complements. That value is reported beside
the observed share (`alignment_expected_from_margins`) as a descriptive baseline: it is not a
causal null model.

**Hub proteins.** A protein's counted claims are its registry claims of wording class `causal`
or `target` whose direction is not `reported_nonsignificant_or_null`, and its counted outcomes
are the outcomes of those claims that have at least one disease area (§Therapeutic areas). A
protein is a hub when its counted outcomes cannot all be covered by fewer than 3 disease areas:
no set of one or two areas holds an area of every counted outcome. An outcome that lies in
several areas therefore adds at most one. `pleiotropic_locus_named` is set when an abstract
holding one of the hub's counted claims names a gene from the committed pleiotropic-locus list
(the close genes of Eldjarn et al. 2023 ST36), as a case-sensitive whole symbol; list symbols
that are also common abbreviations are a stated limit. A protein with many counted claims
spans three areas by volume alone, so the number of hubs is reported beside the number expected
when the outcomes of the counted claim records are permuted among those records, which keeps
each protein's number of counted records and each outcome's frequency (1,000 permutations,
`numpy` generator seeded `[20261001, 2]`): the observed count, the mean of the permuted counts,
their ratio and the 2.5th and 97.5th percentiles of the permuted counts. The expectation is a
descriptive baseline of what claim volume alone gives; it is not a causal null model and does
not establish excess biological coherence. A verbose abstract can give several counted claim
records on one pair, so a sensitivity analysis (`family_pair_collapsed_hubs`) keeps one counted
unit per family, protein and outcome: the hub list does not change (a hub depends on the set of
its counted outcomes), the claim counts become family–pair counts, and the expectation permutes
outcomes among those units.

**Pathways.** Each UniProt accession maps to its Reactome lowest-level pathways (pinned mapping
file; every Homo sapiens row). Pathways with fewer than 10 or more than 500 background proteins
are dropped. Primary enrichment is platform-specific: for each assay list, the background is
the reviewed UniProt accessions on the list (every component of a multi-protein analyte) and
the claimed set is the distinct accessions with at least one `causal` or `target` claim, not
reporting a null result, from families using that list, restricted to its background.

The platform of a claim is decided by its pQTL dataset alone; GPT-6.1 Sol's `platform` field is
not read for the enrichment and no abstract-based fallback is used. Each pQTL row of the dataset
dictionary is attached to one assay list or to the union of several
(`verification/platform_assay_attachments.csv`): 14 rows by a platform string that names a
pinned list, and 14 rows by reading the dataset's own source paper once, with the sentence
pinned with `citations` and the three checks of §Manual coding of dataset names.

The background of a row is the proteins that could enter that release's pQTL analysis, taken
at the highest level its sources allow and recorded per row: `analysed` (the study's own list
of the proteins that entered its analysis; 12 rows), `assayed` (a study-specific list of the
proteins assayed, where the analysed proteins are not marked; 11 rows), `platform` (a
commercial platform list, where no study-specific list is pinned; 5 rows) or `unavailable` (no
list; no row at the freeze). An assayed or platform list is used only when its reviewed
accessions number at least 90% of the unique targets its source reports (a coverage of 90 per
cent, not 90 accessions); below that the row is `unavailable`, gives no list, and its claims
enter no enrichment and are counted. The 90% threshold is a pragmatic completeness rule and
does not show that the targets a list lacks are spread evenly over pathways. For every row
the table records the assay reagents, the unique targets reported and the targets analysed as
the source states them, and the reviewed accessions on its list are counted when the lists are
built. An analysed list that is not one column of one published sheet is derived by script from
the published files (`scripts/derive_published_lists.py`,
`verification/published_lists_derived/`) and refused when its count differs from the count the
paper states: the 83 of 92 proteins of IMPROVE, the 77 of 92 of NSPHS, the 1,161 targets of the
SCALLOP meta-analysis of Koprulu et al. 2026 and the 1,301 SomaScan 1.3k reagents of the
Jackson Heart Study. The Jackson Heart Study list is a companion-paper, study-specific analysis-eligible
background: Table S2 of the same authors' paper on the cohort (Katz et al. 2022, Sci Adv: 1,301
reagents, 1,297 UniProt identifiers, 1,296 reviewed accessions), which states that the pQTL
study used those reagents. The supplement of the pQTL paper is not open access, so the final
quality-control status of each reagent in the pQTL analysis is not confirmed from that
supplement. The pinned commercial SomaScan 1.3k list (1,063 accessions, 82% of
the 1,297) is below the 90% rule and is read only in a sensitivity analysis. The SCALLOP CVD-I
row of Folkersen et al. 2020 stays at the assayed level: its table lists the 92 proteins
measured and does not mark the 2 that failed quality control. The AGES row of Emilsson et al.
2018 takes, as an annotation-linked proxy, the list of Gudjonsson et al. 2022 for the same
array and samples (4,118 targets against 4,137 proteins). For these two rows the authors were
asked for the missing list (§Explanation of foreknowledge, item 20). A list they supply replaces
the row's background only when it is pinned (source and sha256, with `citations`), entered in
`verification/author_supplied_lists.csv` and logged with `prereg log` before the pathway
enrichment first runs, that is, before the first stage-5 biology joins run recorded in the
ledger or the earliest confirmatory enrichment output written, whichever is earlier
(`scripts/author_lists.py` decides this before the joins run). A list pinned later leaves the
registered background primary and is read only in the sensitivity analysis
`author_supplied_lists_after_cutoff`. The Zheng et al. 2020 instrument set
takes the 1,699 instrumented proteins of its Supplementary Table 1 (1,725 reviewed accessions),
the proteins a paper using the set can test. A sensitivity analysis gives each row its whole
panel or array as assayed, proteins dropped at quality control included.

A family uses, on a pair, every list given by its dataset names; a name gives a
list only when all its candidate rows of the dictionary are attached to that one list, so a
name covering rows with different lists ("SCALLOP", "Fenland") gives none unless it is coded
manually. Claims whose datasets give no list enter no enrichment and are counted. A list on
which no pathway is kept by the size rule has no per-list table, and its proteins enter the
pooled analysis. A
secondary pooled analysis uses the union of the attached lists as background and is labelled as
open to platform-composition confounding. Pathway claim density is the number of families and
distinct proteins per pathway × outcome identifier, over every registry claim and every human
lowest-level pathway. No direction is assigned at pathway level. Every pathway row is
tabulated; a pathway is named in the paper's text only when its q is below 0.05 and at least 3
claimed proteins lie in it (`named_in_text`). A background is the proteins a release could
analyse, not the proteins that have a cis instrument, and proteins with cis-pQTLs are not a
random subset of an assay list: enrichment can reflect which proteins have instruments, and the
paper says so beside every enrichment result.

**EpiGraphDB reference screen.** Each pair is looked up in the frozen EpiGraphDB snapshot
(§Data collection procedures). Its exposures are mapped by the verifier's protein tiers. Each
outcome trait name is mapped by the first of four rules that gives exactly one canonical
identifier, each applied to the snapshot's trait names alone: (1) the name holds an ICD-10 code
that exactly one canonical term carries as an equivalent cross-reference in the pinned MONDO
file; (2) the committed alias table of trait names (`verification/epigraphdb_trait_aliases.csv`,
66 rows, resolved by script from a seed of trait name and term label), each alias with its
source, its rationale and its relation to the term; (3) the verifier's outcome tiers on the
name; (4) the same tiers on the text after the name's last ": " (the UK Biobank field names),
without a leading ICD-10 code. A hand-written alias comes before the label rules because it is
written only where they give nothing or mislead ("Serum creatinine (eGFRcrea)" is the
glomerular filtration rate estimated from creatinine). No trait is forced to map. The primary
join reads the traits mapped by rules 1, 3 and 4 and by aliases of relation `exact_equivalent`
or `normalized_equivalent`; a trait mapped through a `broader_proxy` or `derived_measurement`
alias is read only in a sensitivity analysis. The rule that mapped each
trait is recorded. The direction of a returned estimate is the sign of its beta. A claim record
is compared by its own verified direction and a pair by the one direction its directional
families share; a pair whose directional families contradict one another, or that has none, has
no direction to compare and takes `present_nondirectional_or_ambiguous` when a record is
returned.
Classes: `present_same` (a returned estimate in the claim's direction), `present_opposite` (a
returned estimate in the opposite direction), `present_nondirectional_or_ambiguous` (a returned
record with no usable direction), `no_returned_record` (the protein and outcome both map, but the
snapshot has no record for the pair), and `mapping_failed` (the pair's protein or outcome does not
map to the snapshot). `tested_nonsignificant` is never used: the API returns an estimate only when
a matching sensitivity-analysis record exists and omits pairs with P exactly 1, so the snapshot
does not list every tested pair, and absence is never read as a null result. The resource shares
pQTL data with many of the papers; agreement with it is not independent confirmation. The claim
records are therefore also tabulated by whether the claim's family names, for the pair, a pQTL
dataset that is a source of the snapshot (`verification/pqtl_row_attributes.csv`: the five
source studies of Zheng et al. 2020 and its instrument set, as a candidate row of any pQTL
name): `shared_pqtl_source`, `other_pqtl_source` (every name matched, none such a row),
`pqtl_not_stated_or_unmatched`.

**Record metadata and country.** Per record of an eligible family (§Data collection
procedures): query sources, chase round, journal title, OpenAlex works, reference list. The
country of a record is the `country_code` of the first listed institution of the first author
of its OpenAlex work (the first authorship with `author_position` first; with no institution
listed, the first of that authorship's `countries`; else none). It is never read as the
authors' nationality. Country is collected, and no table of it is generated: it enters no
registered outcome and does not appear in the paper, because it is confounded with the journal
and with access to public summary data. A table is made only if a reviewer requests one after
submission, and it is then reported as requested.

## Measured variables - File upload

N/A — the schema, keyword lists and dictionary are committed with the prompt.

## Indices

| outcome | definition |
|---|---|
| distinct pairs | number of registry pairs |
| papers per pair | distribution of study families per pair |
| repeated pairs (M) | pairs announced by ≥ 2 study families, whatever the direction values of their records |
| identical-release share (H2) | over M: KI = `known_identical` (release identity `identical` on both sides for every two of the pair's families), KN = `known_not_identical` (release identity `not_identical` on either side for at least two of its families), U = M − KI − KN (`unresolved`); LB = KI / M; UB = (KI + U) / M; complete-case = KI / (KI + KN), secondary |
| participant-overlap share (H2b) | over M: KO = `known_overlapping` (overlap `overlapping` on both sides for every two of the pair's families), KD = `known_not_overlapping` (overlap `disjoint` on either side for at least two of its families), U_b = M − KO − KD; LB_b = KO / M; UB_b = (KO + U_b) / M; complete-case = KO / (KO + KD), secondary. KI ⊆ KO and KD ⊆ KN, so LB_b ≥ LB and UB_b ≥ UB; the pairs for which this fails are counted (`h2_h2b_pairs_not_nested`, expected 0) |
| resolvable share | over M: the pairs in which every family's attribution is clear and every dataset name of every family maps to one release on both sides, divided by M. Only such a pair can be `known_identical`, so LB ≤ resolvable share: it is the ceiling, imposed by what abstracts report, on how many repeated pairs can be classed known identical. It is not a ceiling on UB or on the prevalence of release reuse. When it is at or below 0.5, "H2 supported" was unattainable, and the tables say so (`h2_supported_attainable`) |
| family–pair direction counts | reported before H1: family–pair records by direction (`raises`, `lowers`, `raises_with_nonsignificant`, `lowers_with_nonsignificant`, `mixed`, `nonsignificant_only`, `unresolved`), with `context_unclear` counts; claim records by direction value and by `direction_unverified` |
| contradicting pairs | pairs with at least one family–pair direction `raises` (or `raises_with_nonsignificant`) and one `lowers` (or `lowers_with_nonsignificant`) |
| within-family discordance | family–pair records with direction `mixed`, split by whether the discordant records differ in `claim_scope` |
| contradiction sources | among contradicting pairs, the families on the `raises` side against the families on the `lowers` side, each side the union over its families, field by field: pQTL and outcome datasets `differ` when the release identity of the two sides' names is `not_identical`, are `same` when it is `identical`, `not_stated` when a side states no name, else `undetermined` (always when a family of either side has unclear attribution); platform and ancestry (GPT-6.1 Sol's values, folded) `differ` when the two sets of stated values are unequal and are `not_stated` when a side states none; `any` differs when any field does; each field reported separately with its `not_stated` proportion; the denominator of every proportion is the contradicting pairs |
| abstract-level directional concordance (H1) | pair level (primary): among pairs with at least one `independent` edge between directional families, the proportion whose `independent` edges all join families of the same direction; edge level: the proportion of `independent` edges joining families of the same direction |
| Liu-analogue (descriptive) | over pairs with at least two directional families, C = (concordant − discordant) / (concordant + discordant) over all edges between directional families whatever their datasets, tabulated in the tiers of Liu et al. 2025 (high ≥ 0.7, moderate 0.5–0.69, low 0.0–0.49, discordant < 0); reported beside Liu et al.'s 20.2% discordant with the differences stated: family edges rather than study pairs, verified significance-based directions rather than point-estimate signs, exact canonical pairs rather than embedding-matched traits |
| landscape | families per year; the 20 proteins with the most families (ties by pairs, then identifier); pairs and claim records per therapeutic area (an outcome counts in each of its areas); wording classes |
| drug-development records | distinct pairs by highest development status (eight classes); stopped-trial events by source stop-reason label; `target_drugged_elsewhere`; `related_indication` counts |
| claim–trial-history co-occurrence | claims of class `causal` or `target` whose pair has any stopped-trial event; the subset with a directionally relevant stopped trial |
| novelty language with an earlier registry claim | among `novelty_language` claims, proportion that are `earlier_in_registry` in the 2019–2025 registry, with `tied_or_unknown_order` reported beside it; `related_prior_claim` reported separately |
| nominal abundance–action alignment | claims by `concordant` / `discordant` / `mixed` / `ambiguous_only` / `no_drug`, for matching indications and for any indication; the `concordant` share among `concordant` and `discordant` claims beside the share its two margins give |
| hierarchy relations | contradicting pairs and directional concordance recomputed over pair families (anchor plus one-step parent and child pairs) |
| hub proteins | hub list with the disease areas of the counted outcomes, the minimum number of areas covering them, claim counts and `pleiotropic_locus_named`; the number of hubs beside the number expected from claim volume |
| pathway enrichment | per assay list and pathway: claimed and background counts, one-sided Fisher exact p, Benjamini–Hochberg q, `named_in_text`; pooled analysis secondary |
| pathway claim density | families and distinct proteins per pathway × outcome identifier |
| reference-screen agreement | pairs by EpiGraphDB class; claim records by class, cross-tabulated with `novelty_language` and `earlier_in_registry`, and split by `shared_pqtl_source` / `other_pqtl_source` / `pqtl_not_stated_or_unmatched` |

**Registered secondary outcomes** (`scripts/registry_secondaries.py`; the unit is the pair
unless the row names another). Each is an estimate with an interval. None carries a P value or
a verdict: "supported", "contradicted" and "unresolved" belong to H2 and H2b, and "significant"
to the enrichment q values. A contrast between two strata is a difference with a
pair-bootstrap interval and is not a test. A cell on fewer than 20 units is printed, labelled
imprecise and not interpreted in the text. Every one of the 20 tables is emitted whatever its
result, empty and imprecise tables included. The main paper carries `reporting_completeness`,
`edge_relations`, `direction_agreement_by_edge_class`, `significance_discordance`,
`first_claim_concordance` and `periods`; a fixed supplement carries the other 14 in the order of
this table, then every sensitivity table in the order of §Other planned analysis. The abstract
may state only the corpus size (eligible families, claim records, distinct pairs), the H1
estimate, the H2 and H2b verdicts with their bounds, the resolvable share and reporting
completeness; no other outcome enters it.

| secondary | definition | reports |
|---|---|---|
| `reporting_completeness` | unit: eligible family with a registry claim record. Shares whose records name a pQTL dataset; an outcome dataset; one release for every pQTL name; one release for every outcome name; both; a platform; an ancestry | proportions, Wilson |
| `dataset_usage` | families per dictionary row (names that map to one release), per candidate set of an ambiguous name, and per participant component known for a name whichever release is meant; the 10 commonest pQTL × outcome combinations a family names on one pair | counts |
| `edge_relations` | unit: every two families of a repeated pair. Dataset relation per side; edge class | proportions, pair bootstrap |
| `h2_by_families_per_pair` | the H2 and H2b classes for repeated pairs with 2, 3, and 4 or more families | bounds, pair bootstrap |
| `h2_directional_pairs` | the H2 and H2b classes read over the directional families only, for pairs with at least two | bounds, pair bootstrap |
| `direction_agreement_by_edge_class` | unit: edge between two directional families. Share joining families of the same direction, per edge class; `identical_release` is the positive control; `independent` minus `overlapping` | proportions, Wilson, pair bootstrap; difference with interval |
| `significance_discordance` | repeated pairs with at least one directional family and at least one `nonsignificant_only` family; those family–family edges by edge class. Abstracts under-report null results, so the count is a lower bound | count, proportion of M, pair bootstrap |
| `contradiction_source_comparison` | unit: edge between two directional families. The four contradiction-source fields compared between the two families; share `differ` on discordant edges (opposite directions), on concordant edges, and discordant minus concordant | proportions; difference with interval |
| `first_claim_concordance` | pairs with at least two directional families of which one is strictly earliest by claim date on the pair (§Study design, Dates) at the resolution each two dates share (a pair without one is `tied_first`, counted). Share of the later directional families with the first family's direction, overall and by the edge class of the first family with the later one. "First" means first in the registry, by claim date | proportion, Wilson, pair bootstrap |
| `periods` | the period in which a pair was first claimed or became repeated in the registry, by claim date: for 2019–2022 and 2023–2025, distinct pairs (a pair in the year of its earliest claim date); and, with a repeated pair in the year of its second-earliest claim date, repeated pairs, LB, UB, LB_b, UB_b, resolvable share, significance-discordant share, contradicting share among pairs with two directional families, and H1 pair concordance; later minus earlier | two columns; differences with intervals from independent pair bootstraps of the two periods |
| `yearly_series` | family entry per first-public year: eligible families and their claim records; per claim-date year: pairs claimed, pairs first claimed in the registry that year, and pairs a family already claimed in an earlier year, with their share | counts |
| `therapeutic_areas` | per therapeutic area (an outcome counts in each of its areas): pairs, repeated pairs, the H2 and H2b bounds, contradicting pairs among pairs with two directional families | table |
| `platform_pairing` | unit: edge between two directional families. Whether the two families' pQTL rows are of one assay family (`verification/pqtl_row_attributes.csv`: Olink, SomaScan, other; a `mixed` row, a name whose candidate rows differ and an unmatched name are unknown): agreement share and discordant edges for same-platform and cross-platform edges; cross minus same | proportions, Wilson, pair bootstrap; difference with interval |
| `claims_per_family` | unit: eligible family. Registry claim records per family: quantiles, families with none, share of the records from the top tenth of families | quantiles |
| `top_lists` | the 20 pairs, the 20 proteins and the 20 outcomes with the most families (ties: pairs by claim records then identifier; proteins and outcomes by pairs then identifier) | lists |
| `wording_by_repetition_and_year` | unit: claim record. Wording-class shares for pairs with 1, 2, and 3 or more families, and per first-public year; `novelty_language` share per year | proportions, Wilson |
| `citation_of_earlier_claim` | unit: a later family on a repeated pair (another family of the pair is strictly earlier by claim date on the pair). Share whose OpenAlex reference list, from any of its registry or preprint records, holds a work of an earlier family of the pair; the same for later families holding a `novelty_language` claim of the pair that is `earlier_in_registry`. Families with no reference list are counted apart and enter no share; the share of eligible families with any reference list is reported | proportions, Wilson |
| `source_overlap` | unit: eligible family. The sources (PubMed, Europe PMC, OpenAlex) whose registered queries returned any of its records; families no query returned, by the chase round that found them | counts; Wilson for the chase-only share |
| `document_class_and_journals` | unit: eligible family. Document class of the registry record; preprint-only share; the 20 journals with the most families | counts |
| `accounting` | every index and every secondary with its unit, its pair-level denominator and count, its edge-level denominator and count where it is read over edges, and the counts that left it | table |

**Units and denominators of the indices.**

| index | unit | pair-level denominator | edge-level denominator |
|---|---|---|---|
| distinct pairs; papers per pair; top lists | pair | registry pairs | — |
| H2, H2b, resolvable share; `h2_by_families_per_pair` | pair | repeated pairs (M) | — |
| `h2_directional_pairs` | pair | pairs with at least two directional families | — |
| `significance_discordance` | pair | repeated pairs (M) | edges between a directional and a `nonsignificant_only` family |
| family–pair direction counts; within-family discordance | family–pair record | family–pair records | — |
| contradicting pairs; Liu-analogue | pair | pairs with at least two directional families | Liu-analogue: edges between directional families |
| `first_claim_concordance` | later directional family on a pair | pairs with at least two directional families | later directional families (all but the first per pair) |
| contradiction sources | pair | contradicting pairs | — |
| H1 | pair (edge, secondary) | pairs with at least one `independent` edge between directional families | `independent` edges between directional families |
| `edge_relations` | edge | repeated pairs (M) | every two families of those pairs |
| `direction_agreement_by_edge_class`; `contradiction_source_comparison`; `platform_pairing` | edge | pairs with an edge between directional families | edges between directional families |
| `periods`; `therapeutic_areas` | pair | registry pairs (distinct pairs) and repeated pairs (the other indices), each in its period or area | — |
| `citation_of_earlier_claim` | later family on a repeated pair | family–pair records with a strictly earlier family by claim date | — |
| novelty; alignment; claim–trial-history co-occurrence; reference screen by claim; wording; `wording_by_repetition_and_year` | claim record | registry claim records (those with the named property) | — |
| drug-development records; reference screen by pair | pair | registry pairs matched to the resource | — |
| hub proteins | protein | registry proteins | — |
| pathway enrichment | protein | reviewed accessions of the assay list | — |
| `reporting_completeness`; `dataset_usage` | study family | eligible families with a registry claim record | — |
| `source_overlap`; `document_class_and_journals`; `claims_per_family`; `yearly_series` (families) | study family | eligible families | — |
| `no_abstract` records | record | screening records of the search and of each chase round | — |
| eligibility decisions; gate audit | record | screening records that have an abstract (for the audit, the marked ones sampled and judged) | — |

**Internal consistency checks.** Span verification rate (`citations verify`); mapper/verifier
acceptance rates for proteins, outcomes and dataset names (by mapping state); direction-verifier
agreement with GPT-6.1 Sol and the `direction_unverified` count; `relation_ambiguous` and
`pair_ambiguous` counts; `extraction_failed` rate; `eligibility_uncertain` count; repeat-run
stability per field on the 10% stability sample; negative-control specificity per stratum; the
gate audit of each chase round; the `no_abstract` records per screening set; outcome records by mapping tier and by alias relation; the
wording classes that the name rule changes; matching `clinical_report` rows by source and by
quality-control flag; the manual dataset-coding
counts (queued, coded, unresolved, agreement at the second check);
wording-class distribution; match rates of the registry to ChEMBL, Open Targets, Reactome, the
panel lists and EpiGraphDB. None of these estimates extraction recall or precision.

## Indices - File upload

N/A — no index file.

## Statistical models

The primary results are finite-corpus counts and proportions over the retrieved and eligible
set, and the H2 and H2b verdicts are read on those finite-corpus bounds (§Inference criteria).
No superpopulation estimand or sampling model is defined, so no interval sets a verdict. Wilson
95% intervals are reported beside the estimates as naïve pair-level descriptive intervals,
without a coverage claim, since pairs share papers, proteins, datasets and instruments.

Three resampling-stability displays are reported beside the estimates; none sets a verdict and
none has a coverage claim. They probe three concentration structures and do not jointly model
the cross-classified dependence among families, proteins, outcomes and datasets. The pair
bootstrap (`scripts/build_registry.py`): 10,000 replicates, seed 20261001. For H1, each
bootstrap replicate resamples with replacement the canonical pairs containing at least one
independent edge. For H2, each replicate resamples with
replacement all multi-family canonical pairs. Each sampled pair retains the value computed from
the full registry. The interval is the 2.5th and 97.5th
percentile of the replicate proportions (for H2, of each bound) by the inverted-CDF rule, so each
endpoint is an attained replicate value. H2b and the resolvable share are read on the same
replicates as H2, so in every replicate LB_b ≥ LB and the resolvable share ≥ LB. The pair
bootstrap does not model the dependence between
pairs that share families, proteins or datasets. The family-deletion range (`family_jackknife`
in the output): every estimate is recomputed with each study family removed in turn (a pair leaves a
denominator when the removal leaves it without the required families), and the minimum, maximum
and the family giving each are reported. It is the range of each estimate over single-family
deletions, not an interval. The protein-cluster bootstrap: proteins are
resampled with replacement, each with all its pairs, and each estimate is the ratio of the
summed numerators and denominators (10,000 replicates, `numpy` generator seeded
`[20261001, 1]`). The paper's abstract states the H2 and H2b verdicts with their bounds; the
resampling-stability displays are reported beside them in the results. The registered secondary
outcomes use the same pair bootstrap over
the units each names (one generator stream per secondary, recorded in the output; replicates
with an empty denominator are dropped and counted). Synthetic tests (`tests/test_registry.py`) fix the
behavior for a family reporting many pairs, a pair with three families and repeated draws of one
pair; resampling pairs never creates an edge between two copies of one family. Pathway enrichment uses
one-sided Fisher exact tests with Benjamini–Hochberg adjustment within each assay list, over
every pathway the size rule keeps on that list, reported as description, not as a hypothesis
test.

## Statistical models - File upload

N/A — the analysis script is committed before the freeze.

## Transformations

Years grouped as 2019–2022 and 2023–2025 for the landscape (by family first-public year) and
for the `periods` secondary (by claim-date year), and for nothing else. Proteins and outcomes
mapped as in §Measured variables.

## Inference criteria

| hypothesis | holds when |
|---|---|
| H1 | no verdict: the pair-level and edge-level concordance are reported with the resampling-stability displays and Wilson intervals |
| H2 supported | LB > 0.5 |
| H2 contradicted | UB ≤ 0.5 |
| H2 unresolved | neither |
| H2b supported | LB_b > 0.5 |
| H2b contradicted | UB_b ≤ 0.5 |
| H2b unresolved | neither |

LB, UB, LB_b and UB_b are the observed finite-corpus bounds of §Indices. A bound equal to
exactly 0.5 does not support a hypothesis and does contradict it, as the two inequalities state.
One half is an interpretable majority convention, not an externally estimated scientific
threshold: each hypothesis asks whether most repeated pairs rest on identical releases (H2) or
on identical releases or documented shared participant-source components (H2b). H2 is the
primary hypothesis and H2b the second registered hypothesis; both verdicts are statements about
the retrieved corpus, not inferences to a population, so no multiplicity correction applies to
them, and no secondary outcome carries a verdict.

**Reading the two verdicts.** Both are reported whatever they are, and neither replaces the
other. H2 supported implies H2b supported and H2b contradicted implies H2 contradicted, so six
combinations can occur:

| H2 | H2b | registered reading |
|---|---|---|
| supported | supported | most repeated pairs rest on identical releases |
| unresolved | supported | most repeated pairs rest on identical releases or documented shared participant-source components; identical releases are not shown for most |
| contradicted | supported | most repeated pairs rest on documented shared participant-source components, and at most half on identical releases |
| unresolved | unresolved | Neither share is placed on one side of one-half under the registered rule; the resolvable share and reporting-completeness table show how much source ambiguity contributed. |
| contradicted | unresolved | at most half of repeated pairs rest on identical releases; overlap is not placed |
| contradicted | contradicted | at most half of repeated pairs rest on identical releases or documented shared participant-source components |

Neither a contradicted nor an unresolved verdict shows that repeated claims rest on independent
participants.

**Each estimate is reported whatever its size; an estimate on fewer than 20 pairs is labelled
imprecise, and a verdict on fewer than 20 repeated pairs is reported with that label.**

## Data inclusion and exclusion

As §Measured variables. The funnel (`scripts/funnel.py`, which raises when two stages disagree
on the records they hold) reports records per source and query, citation-chasing
additions, the `no_abstract` records of the search and of each chase round (with no text, with a
stub below the floor, by document class, and with a title holding both term groups of the
prefilter), the chased records the prefilter gated out and those the gate audit sampled,
duplicates and family links, records
by document class, records marked by the prefilter, eligibility decisions (eligible, `eligibility_uncertain`,
not eligible, with `also_tissue_or_csf` and `eligible_no_named_claims` counts), `extraction_failed` records, quotation-check and verification failures by reason,
and eligible families by window. The registry covers families GPT-6.1 Sol judges eligible or
uncertain; the paper's population is stated in those terms.

## Missing data

A field GPT-6.1 Sol does not extract is `not_stated`. A claim with direction `not_stated`,
`reported_nonsignificant_or_null` or `direction_unverified` stays in the repetition counts and
leaves direction-based results, counted. An
edge labelled `unclear` never counts as independent; a pair with no `independent` edge leaves
H1, counted. Unresolved dataset identity enters H2 and H2b through their bounds, never by
exclusion. A later family with no OpenAlex reference list enters no citation share and is
counted. An
eligible family with `extraction_failed` contributes no claims; counts of distinct pairs are
reported with the number of such families beside them and a bound that treats each as
contributing no new pair and, alternatively, as many pairs as the median eligible family whose
extraction succeeded (zero-claim families included). A pair whose protein or outcome is unmapped, or
that a reference resource does not match, is counted in each join's match rate and leaves that
join's outcome; it is never assigned `no_matching_trial_or_indication_record` or
`no_returned_record` for want of a mapping.

## Other planned analysis

**Sensitivity analyses,** each reported beside the primary: removing `eligibility_uncertain`
papers; removing `also_tissue_or_csf` papers; including claims that fail only direction
verification with GPT-6.1 Sol's direction; separately, including claims that fail protein or
outcome dictionary matching; including `relation_ambiguous` records; family–pair direction from
`overall`-scope records only, where a family has any; removing `_with_nonsignificant`
family–pair records from H1; removing family–pair records flagged `context_unclear`; pair
families in place of pairs; dropping fuzzy family links; treating `unclear` edges as independent
(H1); drug-development
records including `component_level_mapping` drugs; first public 2020–2025 only; excluding
`count_not_stated` papers; pooled-background pathway enrichment.

Added with the stage-0 rules and the round-6 review, each the other reading of a rule above:

| sensitivity analysis | what changes |
|---|---|
| `all_document_types` | records of document class `other` are kept |
| `without_citation_chasing` | families found only by citation chasing are removed |
| `claim_dates_from_registry_abstracts_only` | novelty dated without preprint abstracts |
| `shared_names_mondo_first` | an outcome name giving exactly one MONDO identifier beside EFO identifiers takes the MONDO identifier |
| `without_manual_dataset_coding` | the manual dataset codes are not applied (H1, H2, pathway enrichment) |
| `clinical_trial_reports_only` | `clinical_report` rows that are not trials are not records |
| `quality_flagged_reports_included` | rows carrying a `qualityControls` flag are read |
| `single_drug_single_disease_reports` | only reports naming one drug and one disease are read |
| `completed_trials_as_completed` | a matching COMPLETED trial sets `completed_no_later_record` |
| `null_result_claims_counted` | claims reporting no significant estimate count as `causal` or `target` claims (co-occurrence, hubs, enrichment) |
| `distinct_therapeutic_areas` | a hub is a protein whose counted outcomes lie in at least 3 distinct disease areas |
| `any_candidate_row_attachment` | a dataset name gives every assay list attached to any of its candidate rows |
| `alternative_assay_lists` | the Zheng et al. 2020 instrument set takes the union of the five source studies' assay lists as background |
| `names_as_written_only` | the reference screen with only the snapshot traits that map as written |
| `proxy_trait_aliases_included` | the reference screen also reads the snapshot traits mapped through a `broader_proxy` or `derived_measurement` alias |
| `whole_panel_backgrounds` | each dictionary row takes its whole panel or array as assayed, proteins dropped at quality control included, where the primary background is the analysed list; the Jackson Heart Study row takes the incomplete commercial SomaScan 1.3k list |
| `author_supplied_lists_after_cutoff` | only when a list the authors supply for the SCALLOP CVD-I or AGES (Emilsson 2018) row is pinned after the pathway enrichment first ran: that row takes the supplied list |
| `without_phenotype_cross_references` | an outcome name that gives phenotype identifiers only keeps them |
| `claim_specific_dataset_names_only` | dataset names of records whose attribution is not `claim_specific` are read as `not_stated` (H1, H2, H2b) |
| `tested_count_1000_or_more` | only families whose registry abstract states at least 1,000 proteins tested |
| `protein_cluster_bootstrap` | resampling-stability display from resampling proteins with all their pairs (H1, H2, H2b); never a verdict |
| `family_pair_collapsed_hubs` | hub claim counts and the volume expectation over one counted unit per family, protein and outcome |

No sensitivity analysis replaces a primary result, and no analysis set is promoted on the basis
of its result. Each sensitivity table is reported beside the primary table whatever it shows.

**Abstract–full-text concordance (secondary, descriptive).** Run after the primary results are
committed; it cannot change them and is reported beside them. It is not ground truth and not a
test of any claim.

- *Population.* Every eligible study family whose PubMed record has an open-access full text in
  Europe PMC (open-access flag set, with a PMCID, and an XML with a body), retrieved as Europe
  PMC / PubMed Central open-access XML by `scripts/fetch_fulltext.py`. A registry record that is
  not a journal record with a PMID has no PubMed record to match. No other source is used: no publisher website,
  no preprint server and no paywalled access. The extracted journal abstract is compared with the
  full text of the same PubMed record; a family whose extracted abstract is not that record's
  abstract is counted `version_unmatched` and not compared, and a family with no such full text
  (including every preprint-only family) is counted `no_open_access_full_text`. The population is
  therefore the Europe PMC open-access subset, narrower than all publicly available full texts.
  The Europe PMC open-access rate and the successful-extraction coverage (families extracted
  without `extraction_failed`, over eligible families) are both reported, and no output is
  generalized to families outside the subset.
- *Text.* The body and the main-text tables, rendered by `scripts/fetch_fulltext.py`: the
  embedded abstract, front matter, references and supplementary files are excluded; each table
  row is one line carrying its caption and column headers.
- *Extraction.* The frozen full-text prompt (`prompts/fulltext_extraction_prompt.md`, schema
  `fulltext_extraction`): the same claim-record definition, fields and direction rules as the
  abstract prompt, with registered instructions for full text, context linkage and tables, and
  three added fields: `source_location`, `colocalization` (`supports`, `does_not_support`,
  `not_reported`) and `replication` (`replicated`, `not_replicated`, `not_reported`). The same
  `citations` span pinning and deterministic verifier apply. Span pinning shows that each span
  occurs in the text; it does not show that the extraction found every result.
- *Matching* (`scripts/fulltext_concordance.py`). An abstract registry record is `matched` when
  full-text registry records of the same family share its exact canonical pair and have a
  compatible context (same `claim_scope`, and for a scope other than `overall` one folded
  context key contains the other) with a single context key; `context_ambiguous` when full-text
  records share the pair but none has a compatible context, or the compatible records carry more
  than one context key; `unmatched` when no full-text record shares the pair.
  `extraction_failed` and `version_unmatched` families are counted separately.
- *Outputs.* Per family and pooled: the share of abstract claims matched to extracted body
  records; context-ambiguous and unmatched counts; direction agreement between abstract and full
  text, computed only among matched records whose directions were verified on both sides;
  additional extracted body claims (canonical pairs extracted from the body with no abstract
  record in the family); dataset names found only in the full text, and the H2 and H2b
  classifications recomputed with abstract and full-text datasets together, beside the
  abstract-only classifications, both within the same open-access subset (descriptive; no
  verdict is read in the subset); records
  whose full text reports colocalization or replication.
- *Cost.* About USD 0.17 per paper of 8,500 words at the registered settings (development run,
  `outputs/dev_metrics/ft1.json`); USD 30–50 for the census, re-estimated when the open-access
  count is known.

**Update set.** The 2026 papers reported with the same indices in a separate table.

Any analysis not listed here is exploratory and labelled so wherever it appears.

## Context and additional information

Planned paper title: "Repeated and discordant protein–outcome claims in proteome-wide
Mendelian-randomization abstracts: a meta-research census". The registration is stated once in
the abstract and once in the methods, by this sentence: "Queries, eligibility and extraction
rules, mappings and every index were registered before the search was run; the eligibility
prompt was calibrated on 24 in-window abstracts read for eligibility only."

Paper 2, a calibrated rerun of the registry's claims through the V8 pipeline of
`pqtl-mr-domain-of-validity`, is registered separately before any claim is rerun.

Study type: observational, a meta-research study of published abstracts. Intention for causal
interpretation: the study describes what abstracts assert; no causal claim is made. Blinding of
experimental treatments: no treatment is assigned.

Limitation stated here: the primary study reads abstracts only, and no person checks the
extraction; one tool, GPT-6.1 Sol, extracts, and quality rests on the `citations` quotation
check, the deterministic verification script, a repeat-run stability check, a negative-control
set and automated mapping, each reported. Dataset names the mapping leaves unresolved, and the
assay lists of 14 dictionary rows, are checked and coded by reading the paper: Claude Code
codes, Perplexity checks, the author verifies that the pinned sentence states the coded value. The development exercises are calibration and
internal consistency checks: the known-item calibration set was used to revise the eligibility
prompt, and the development abstracts are not labeled, so the semantic recall and precision of
eligibility and extraction cannot be estimated from them. Citation chasing is prefiltered:
the gate audit bounds, and does not remove, the eligible papers it leaves out. The search has
no outside validation: the study lists of Wu et al. 2024 and of DMRdb were sought as an outside
check and could not be obtained (foreknowledge item 16), and the 24 known items, on which the
eligibility prompt was revised, are a calibration and retrieval check, not independent
validation. A list obtained after the freeze would be reported as a dated addendum, not as part
of this registration.

Novelty statement. Searches of PubMed, Europe PMC (including preprints), Semantic Scholar and
OpenAlex, 2019 to 2026-09-30 (`docs/source_verification/VERIFICATION.md`,
`SCOOP_RERUN_2026-09-30.md`), identified no study that assembled protein–outcome claims from the
abstracts of proteome-wide plasma or serum pQTL-MR papers across diseases and quantified
exact-pair repetition, directional contradiction, directional concordance among families on
independent data sources and reuse of identical source datasets under prespecified automated
rules. The closest precedents are Wu et
al. 2024, which pooled published MR estimates for protein–cardiometabolic disease pairs from 35
studies and looked up their drug-development status; Liu et al. 2025 (MR-KG), which measured
direction discordance across general MR abstracts; Zheng et al. 2025 (DMRdb), which curates
causal pairs from 166 published eQTL and pQTL MR studies; and Nguyen, Terry and Guggenheim 2025,
Sobczyk et al. 2023 and Liu and Gaunt 2024. Chen, Zhao and Fu 2025 (Eur Heart J) is a closed
two-page letter responding to one paper; its full text was not read.

**Maximum claim under this registration.** For proteome-wide MR papers (journal articles and
preprints) with an abstract in a registered source, retrieved by the registered PubMed, Europe
PMC and OpenAlex queries and prefiltered citation chasing, first public 2019–2025, judged eligible by GPT-6.1 Sol, as extracted from
abstracts by GPT-6.1 Sol and verified against the abstract text, the paper can state: how many
distinct protein–outcome pairs the abstracts claim and how many study families announce each;
which datasets the families name and how often abstracts name a release at all; the share of
repeated pairs, with missingness bounds, whose families name exactly identical releases with
attribution to the claim, whether that share is above half, at or below half, or unresolved
(H2), read on the finite-corpus bounds, and the largest value its lower bound could have taken
given what abstracts report; the same share and verdict for identical releases or documented
shared participant-source components (H2b), with the registered reading of the two verdicts
together; both shares per family–family edge, by number of families per pair, by period and by
therapeutic area, with the dataset names the rules leave unresolved coded by reading the paper;
how many pairs are claimed in opposite directions, how many are reported as significant by one
family and as non-significant by another, how many family–pair records are mixed within a
family, and how discordant and concordant families differ in stated pQTL source, platform,
outcome GWAS and ancestry; the directional agreement of families on identical, overlapping,
unclear and independent sources, where agreement on identical releases is a control and
agreement on independent sources (H1) carries no verdict and is conditional on both families
reporting a significant estimate, with a Liu-analogue tabulation beside Liu et al. 2025 as
context; whether later claims of a pair agree with the first claim in the registry, by claim date;
yearly counts of families, claims and repeated pairs; and the internal consistency checks, the
negative-control specificity and the source overlap. Descriptively, it can state the indication-specific phase and
trial-event records of the pairs in the pinned ChEMBL and Open Targets releases, and how many
causal or target claims concern pairs whose matching trials carry registered stop-reason
classes; the nominal abundance–action alignment beside the value its margins imply; novelty
wording with an earlier registry claim, and whether the later family cites the earlier; how the
counts change over one-step ontology relations; hub proteins beside the number expected from
claim volume; pathway enrichment relative to the proteins each pQTL release could analyse;
agreement with EpiGraphDB, split by shared pQTL source; and, for the Europe PMC open-access
subset only, the abstract–full-text concordance, with the Europe PMC open-access rate and
extraction coverage beside it. It cannot state whether any claim is true; that agreement among
abstracts is replication; that a repeated claim on non-identical releases rests on independent
participants; that families with documented shared participant-source components share
individual participants; that the search has been validated against an outside list; that a contradicted or unresolved H2 or H2b shows independence; that a stopped
trial shows a claim false or that development ended; that agreement with EpiGraphDB confirms a
claim or that no returned record is a null result; that a claim is novel in the literature;
that a family that does not cite an earlier claim was unaware of it; that enrichment reflects
biology and not which proteins have instruments; anything about pathway-level direction, the
recall or precision of the extraction or of the search, differences between strata as tested
effects, the country of the authors or their nationality, whether any claim replicates when rerun, or families
outside the Europe PMC open-access subset.
Rerunning the claims belongs to the Paper 2 registration.

---

## Log

Append only. Never edit above the line.

The last column is what distinguishes an amendment from a deviation: `nothing run`,
`no results seen`, `results not opened`, `results seen`.

```
2026-09-30  created                              nothing run
2026-09-30  H1 set against the 0.8 benchmark (three-way criterion); descriptive outcomes added: drug-development status and trial-conflict claims (ChEMBL, Open Targets), novel-already-claimed, direction against existing drugs (direction token rule copied from pqtl-mr-domain-of-validity), tree-linked consistency (one-step parent-child), hub proteins (k = 3; Eldjarn ST36 locus list), Reactome pathway enrichment against the Olink Explore 3072 + SomaScan v4 background, EpiGraphDB reference screen; foreknowledge items 9-10   nothing run
2026-09-30  Perplexity serious-issues review applied (planning/perplexity_paper1_review/01_REVIEW.md): H1 three-way rule against a non-exchangeable 0.8 benchmark with family-bootstrap verdicts (Wilson descriptive only); family-pair direction and independence edges; dataset relations and H2 all-pair bounds on identical release; canonical MONDO/EFO identifiers, exact matching primary, hierarchy relations separate, pair family = anchor plus one hop; novelty on exact pairs with claim-level dates, bare 'new' removed; drug classes renamed, highest status and stopped-trial events separate, conflict reserved for directionally relevant negative/safety stops; nominal abundance-action alignment; pathway direction removed, platform-specific backgrounds; EpiGraphDB frozen pQTL file with returned-record classes; two-sentence evidence spans; prefilter orders only; known items pass the whole pipeline; extraction_failed bounded; contradiction sources split; novelty sentence and maximum claim revised; foreknowledge item 11   nothing run
2026-09-30  GPT-6.1 Sol made the only extraction tool (Gemini removed; no second model): abstracts and evidence spans pinned with the citations CLI; deterministic verification script (HGNC/UniProt names, EFO/MONDO labels and synonyms, direction lexicon, dataset aliases); uncertain eligibility extracted and flagged; repeat-run stability on 10%; sensitivity analyses for direction-only and dictionary failures; two-tool matching removed throughout   nothing run
2026-09-30  scoop rerun folded in (Wu 2024 and DMRdb added as precedents; drug-development records removed from the novelty claim; foreknowledge item 12); Q1 protein block gains (plasma[tiab] AND protein*[tiab]) after the known-item test missed PMID 36864689 (Lin 2023, Brain); counts only, +163 PubMed records   no results seen
2026-09-30  prompt r4 and verifier changes before the freeze: claim restricted to genetically proxied estimates (evidence_type, only mr_estimate registered); non-significant estimates are null; committed outcome alias table and related-synonym tier; estimate parser for direction with lexicon fallback; eligibility-only known-item check carved out of the no-in-window-reading rule (not yet run); API settings stated (gpt-6.1-sol, Responses API, reasoning medium, no tools, store false, no temperature parameter, no dated snapshot, call dates recorded); r4 run on the 30 pre-2019 development abstracts only   nothing run
2026-09-30  eligibility-only known-item check run: r4 eligibility prompt (2bc87f34898a) on the 25 items of search/known_items.md, titles and abstracts from PubMed E-utilities (scripts/fetch_known_item_abstracts.py); raw exchanges in outputs/raw/sol_known_items/, decisions in outputs/known_items/eligibility_known_items_r4.jsonl; 17 eligible (2 count_not_stated), 8 ineligible; eligibility decisions only; no claim fields extracted   no results seen
2026-09-30  eligibility prompt r5 (revision d36485111906): criteria answered yes/no/uncertain; criterion 2 counts any stated result of the protein analysis on an outcome, including counts of significant pairs, without a named protein; tissue/CSF exclusion only when no plasma or serum proteins are analysed, with an also_tissue_or_csf flag and sensitivity analysis; eligible_no_named_claims defined; r5 run on the 30 pre-2019 development abstracts   nothing run
2026-09-30  eligibility-only known-item check rerun with r5 (d36485111906) on the 25 items of search/known_items.md; raw exchanges in outputs/raw/sol_known_items/, decisions in outputs/known_items/eligibility_known_items_r5.jsonl; 20 eligible, 3 count_not_stated, 1 eligibility_uncertain, 1 not eligible (fewer than 100 proteins); eligibility decisions only; no claim fields extracted   no results seen
2026-09-30  eligibility prompt r6: protein-count field holds only a count stated as tested in the MR analysis, other counts go to `count_other`; known-item set reduced to 24 (PMID 35300523 removed: 90 proteins tested, genuine ineligibility found by the r5 check)   nothing run
2026-09-30  eligibility-only check r6 on the 24 known items and the 30 pre-2019 development abstracts: eligibility decisions only; no claim fields extracted; 24 of 24 known items pass   no results seen
2026-09-30  protein-count floor made deterministic in scripts/apply_eligibility.py: floor on the tested count when stated, else on count_other (below 100 ineligible, 100 or more count_not_stated), else count_not_stated; decision script re-applied to existing r6 eligibility outputs, no new tool calls   nothing run
2026-09-30  eligibility prompt r7: tested count and `count_other` exclude counts of proteins associated with, significant for, or causally linked to an outcome (prompted by PMID 36510323, whose r6 `count_other` of 58 was an association count); schema descriptions and count wording updated   nothing run
2026-09-30  eligibility prompt r7 (2811496ef424) run on the 24 known items and 30 development abstracts; eligibility decisions only; no claim fields extracted; known items 24/24 pass (12 eligible, 11 count_not_stated, 1 uncertain); development abstracts 1/30 eligible (PMID 29875488, pre-2019)   no results seen
2026-09-30  pinned-release defaults: EFO v3.93.0 registered (Open Targets 26.09 build; v3.94.0 recorded only); phase from ChEMBL max_phase_for_ind, Open Targets 26.09 clinical_report for trial events, status and stop reasons only; SUSPENDED its own class, not stopped; the 13 stop-reason labels verbatim, negative/safety = Negative and Safety_Sideeffects; EpiGraphDB frozen as the unfiltered API snapshot (179,928 of 222,525 pairs), tested_nonsignificant never used; direction rule unchanged, POSITIVE/NEGATIVE MODULATOR ambiguous   nothing run
2026-09-30  inputs moved to the Modal volume proteome-mr-claim-audit-inputs (/02_claims_meta/): 2,051 files, local sha256 in modal_inputs_manifest.json, recomputed on Modal in modal_inputs_verification.json, 2,051 of 2,051 match; ChEMBL 37 read from the SQLite package chembl_37_sqlite.tar.gz (same release as the PostgreSQL dump; packaging only), sha256 matches the publisher's checksums.txt, stored at /chembl_37/ with the extracted database and table CSVs (hashes in RELEASES.md); no join or query of claim data   nothing run
2026-09-30  ChEMBL parent collapsing via molecule_hierarchy added to the drug-status rules (raised by the V8 session); ChEMBL 37 now the verified SQLite package on Modal (RELEASES.md)   nothing run
2026-09-30  round-4 review applied (planning/perplexity_paper1_final/01_REVIEW_round4.md; item-by-item in 02_ADJUDICATION_round4.md): title; claim records per analysis context (claim_scope, analysis_context_as_written, subgroup_as_written, dataset_attribution, relation_ambiguous; claim_record_id by script) with deterministic family-pair aggregation; direction value null renamed reported_nonsignificant_or_null; parser tie-breaking stated; H1 rewritten as abstract-level directional concordance among announced claims with no verdict, Liu et al. 2025 as context only (unit not reproducible) with a descriptive Liu-analogue; H2 wording and strict inequality; set-valued dataset mapping, dataset components table, relation and release-identity rules; pair bootstrap primary, family jackknife, Wilson descriptive; family-link safeguards and version-1 dating rule; earlier_in_registry with the tie rule; ChEMBL single-protein primary rule with component_level_mapping sensitivity; completed_no_later_record wording; calibration and internal-consistency language and the recall/precision limitation; mapping-provenance fields; schema minItems and validator uniqueness   nothing run
2026-09-30  pre-freeze checks on development and synthetic data only: unit tests (tests/, 35 pass); verifier rerun on the r4 development outputs with the registered HGNC 2026-09-04, UniProt 2026_03 (620d646a96c0), MONDO v2026-09-01 and EFO v3.93.0 files and the dataset dictionary (metrics unchanged from the EFO v3.94.0 run); outcome alias table rebuilt against EFO v3.93.0 (identical); verifier reads full-text table rows cell by header and masks the '95% CI' label before reading scale cues; synthetic dry run from search records to the H1/H2 tables (outputs/dry_run/); negative-control set drawn (50 pre-2019 PMIDs and titles; no abstract fetched)   nothing run
2026-09-30  Sol development rerun: extraction prompt r8 (0b97103cd7a4) on the 30 pre-2019 development abstracts; eligibility r7 (2811496ef424) reused from cache, no new eligibility calls   nothing run
2026-09-30  abstract-full-text concordance registered as a secondary descriptive analysis (version matching, separate full-text prompt and schema, matching rules, open-access population with availability and coverage reported); full-text prompt (5fb585754e99) run once on the body of one pre-2019 open-access development paper (PMID 30111768)   nothing run
2026-09-30  canonical identifiers and dataset compositions: title restated as a question (planned paper title kept in Context); HGNC -> UniProt step in the registry builder (scripts/canonical_ids.py: pinned HGNC uniprot_ids within the pinned reviewed UniProt file, union over HGNC entries, more than one accession pair_ambiguous, none protein_no_uniprot); MONDO-EFO collision table committed (verification/mondo_efo_collision_table.csv, 1,427 rows, 14 with conflicts); dataset dictionary 95 -> 121 rows, compositions read from the papers' cohort tables and pinned with citations (4,424 quotes), complete rows 44 -> 72, FinnGen legacy cohorts and EPIC added as components; unit tests 50 pass; synthetic dry run outputs/dry_run/20261001T004513Z   nothing run
2026-09-30  pre-freeze defaults for OPEN_QUESTIONS 41-45: a dataset name whose later words name another dataset maps to the matching meta-analysis row, else release_ambiguous with an unlisted combination (never the leading release alone); bare 'FinnGen' stays release_ambiguous and never disjoint; FinnGen R6-R12 complete for the registered overlap flags on the basis that FinnGen comprises Finnish biobank participants only; the six collision-table branch disagreements left unmerged; SWEBIC and STANLEY kept separate; unit tests 53 pass; dataset pairings unchanged (outputs/resource_counts/dataset_pairings_round5_*); synthetic dry run outputs/dry_run/20261001T005219Z identical to the previous run   nothing run
2026-10-01  round-5 review applied (planning/perplexity_paper1_final/03_REVIEW_round5.md; 04_ADJUDICATION_round5.md): Icelandic cohorts split into AGES_REYKJAVIK and DECODE_COHORT, ICELAND component removed, AGES against deCODE unclear unless a pinned source documents shared recruitment; compare_side attribution condition written per side with symmetry tests over every dictionary row pair; full-text concordance narrowed to Europe PMC/PMC open-access XML (publisher and preprint routes removed); bootstrap denominator sentence replaced; unit tests 56 pass; dataset pairings outputs/resource_counts/dataset_pairings_round5_*_iceland_split.json; synthetic dry run outputs/dry_run/20261001T152922Z identical to the previous run   nothing run
2026-10-01  stage-0 build, search stage: search/queries.md with the Europe PMC and OpenAlex translations (truncated phrases written out; hyphenated forms of colocali* and repurpos* added), search runner, screening-set assembly, citation chasing, keyword prefilter and term file, wording lexicon and tagger, repeat-run sampler; translation checks by hit counts on records published 2014-2018 in the three sources (planning/build_stage0/*_pre2019.json); smoke search for 2018-11-01 to 2018-12-31 (43 source records, 23 screening records) and one chase round on development PMIDs 28240269 and 30111768 with citing works capped at 2018-12-31 (186 records); metadata and stored abstracts of pre-2019 records only, none read with a prompt; OpenAlex requests carry an API key in the header and no email address   nothing run
2026-10-01  stage-0 build, drug joins: drug_joins.py, drug_tables.py, drug_schema_check.py, modal_drug_joins.py, dry_run_drug_synthetic.py; schema and value counts of ChEMBL 37 and Open Targets 26.09 and the drug index counts on Modal (outputs/resource_counts/drug_schema_check_*, drug_index_counts_*): resource files only, no pair or claim looked up   nothing run
2026-10-01  stage-0 build, biology and registry analyses: ontology graph, hierarchy relations, hub proteins, assay backgrounds, pathway enrichment, reference screen, novelty, registry indices, sensitivity analyses, registry assembly, claim tags; resource tables on Modal (ontology edges, assay lists, EpiGraphDB mapping tables, pleiotropic-locus list from Eldjarn ST36, workbook sha256 cb93f441...84284): resource files only   nothing run
2026-10-01  stage-0 consolidation (planning/build_stage0/PROPOSED_RULES.md, 90 points): funnel, repeat-run agreement, negative-control specificity, eligible-record selection, stage-6 full-text census and concordance entry point, manual dataset-coding script, RUNBOOK.md, pyproject.toml and uv.lock; rules registered for every open point of the build: document classes, other types out of the primary results; citation chasing restricted to works published from 2019 and gated by the prefilter, with a gate sample; chase response bodies on the Modal volume with a committed manifest; eighth status class other_matching_record; outcome identifiers of HP, OBA and Orphanet dropped beside a MONDO or EFO identifier; null-result claims not counted in hubs, enrichment and trial-history co-occurrence; repeat-run pairing rule; 14 sensitivity analyses added   nothing run
2026-10-01  decisions by the author on the stage-0 rules: (1) disease categories are the Open Targets 26.09 therapeutic areas of the pinned disease file (26 areas; nearest-ancestor rule for terms the file does not carry; hub = counted outcomes not coverable by fewer than 3 disease areas), replacing the 18 project categories; (2) the platform of a claim is decided by its pQTL dataset row alone, with no abstract-based fallback: the 14 dictionary rows whose platform string names no pinned list were read from each dataset's source paper (planning/build_stage0/PLATFORM_LOOKUPS.md, sentences pinned with citations), eight published list files fetched to the Modal volume with sha256 checked (verification/platform_list_sources.csv), all 28 pQTL rows attached; (3) EpiGraphDB trait mapping extended by a committed alias table (65 traits) and the after-colon rule: 187 of 225 traits mapped, 145,037 of 179,928 estimates on mapped pairs; (4) dataset names the automatic mapping leaves unresolved are coded by reading the paper, with three recorded checks (Claude Code codes, Perplexity checks, the author verifies) and a sensitivity analysis without the codes; resource tables outputs/resource_counts/biology_resource_tables_2026-10-01_round6b.json; resource files only, no claim, pair or in-window record read   nothing run
2026-10-01  pre-freeze checks on synthetic records, fixtures and resource files only: unit tests on Modal, 464 pass (outputs/tests/pytest_all_modal_20261001T180113Z.txt); synthetic dry runs of the registry, the biology joins and the drug joins pass (outputs/dry_run/, outputs/dry_run_biology/20261001T180113Z, outputs/dry_run_drug/20261001T180113Z); drug joins run end to end on Modal with synthetic claims, the claim-tag file and the committed ontology edges (outputs/dry_run_drug/modal_wiring_synthetic_round6); 48 deliberate rule changes each made a test fail (planning/build_stage0/mutation_check_round6.py)   nothing run
2026-10-01  committed resource tables (ontology edges, assay lists, therapeutic areas, EpiGraphDB mapping and alias tables, pleiotropic-locus list) replaced by byte-exact copies of the files the build jobs wrote on the Modal volume, so each has the sha256 its job recorded (the earlier copies differed in line endings only); unit tests and the three synthetic dry runs rerun on Modal, 464 pass (outputs/tests/pytest_all_modal_20261001T180435Z.txt)   nothing run
2026-10-02  round-6 review applied (planning/perplexity_paper1_final/05_REVIEW_round6.md; item-by-item in 06_ADJUDICATION_round6.md): (1) enrichment backgrounds follow a recorded hierarchy (analysed, assayed, platform, unavailable; a proxy list needs 90% of the reported targets), with analysed lists for IMPROVE (83), MANOLIS (257), HELIC (184), NSPHS (77), the SCALLOP meta-analysis of Koprulu 2026 (1,161 targets) and the Jackson Heart Study, and whole panels in the sensitivity analysis whole_panel_backgrounds; (2) the Jackson Heart Study background is the 1,301 reagents of Katz 2022 (Sci Adv) Table S2, the commercial 1.3k list read only in that sensitivity analysis; (3) Open Targets reports carrying a quality-control flag are not read in the primary analysis (sensitivity quality_flagged_reports_included), matching reports listed by source; (4) wording keywords inside the record's outcome or protein name do not count; (5) prefiltered citation chasing with an adaptive gate audit (batches of 600, sampled positives enter the workflow, stop at a one-sided 95% upper bound below 0.5% or 3,000 sampled); (6) outcome aliases carry a relation, source and rationale, phenotype-only disease names take the disease term the pinned MONDO file cross-references (247 terms; sensitivity without_phenotype_cross_references), labels of obsolete EFO terms stand for their live replacement (901 labels), EpiGraphDB traits map by ICD-10 cross-reference, alias, label, after-colon in that order, and proxy aliases are read only in the sensitivity proxy_trait_aliases_included; also: the coder and checker of dataset names see only the name, its passage and the candidate definitions; six therapeutic areas do not count toward hubs and area assignments are stored as direct or inherited; the preprint date variable is named; resource files and supplementary tables of dataset source papers only, no claim, pair or in-window record read   nothing run
2026-10-02  pre-freeze checks on synthetic records, fixtures and resource files only: published list files fetched to the Modal volume with sha256 checked (verification/published_source_files.csv, platform_list_sources.csv; modal_inputs_manifest.json, 2,066 files); derived tables verification/published_lists_derived/ (counts equal the papers'); resource tables rebuilt on Modal (outputs/resource_counts/biology_resource_tables_2026-10-02_round6_fixes_b.json); unit tests on Modal, 564 pass (outputs/tests/pytest_all_modal_20261002T143504Z.txt); the three synthetic dry runs pass (outputs/dry_run/, outputs/dry_run_biology/20261002T143504Z, outputs/dry_run_drug/20261002T143504Z); 55 deliberate changes of the round-6 rules each made a test fail (planning/build_stage0/mutation_check_round6_fixes.py)   nothing run
2026-10-02  OSF layout, no rule changed: the numbered foreknowledge list moved under "Explanation of foreknowledge and managing unintended influences"; a placeholder under "Foreknowledge of data or evidence" until the author chooses the OSF option; Study type, Intention for causal interpretation and Blinding of experimental treatments answered with OSF option text, their sentences moved to Context; Maximum claim made a bold run-in in Context; OSF dry run (osf.build_draft, sends nothing) refuses only the foreknowledge placeholder; unit tests and the three synthetic dry runs rerun on Modal on the layout text, 564 pass (outputs/tests/pytest_all_modal_20261002T144530Z.txt)   nothing run
2026-10-02  foreknowledge items 12 and 13 corrected to state the eligibility-only known-item check on in-window abstracts (already described in §Search calibration and logged 2026-09-30); no rule changed   nothing run
2026-10-02  OSF foreknowledge option chosen by the author: "Authors have observed the data, but have not performed the proposed analyses" (the eligibility-only known-item check of foreknowledge item 12); no rule changed   nothing run
2026-10-02  round-7 confirmation (planning/perplexity_paper1_final/07_REVIEW_round7.md): foreknowledge item 12 states what the eligibility-only runs extracted, in the reviewer's wording; no rule changed   nothing run
2026-10-02  round-7 review applied (planning/perplexity_paper1_final/07_REVIEW_round7.md; item-by-item in 08_ADJUDICATION_round7.md): novelty terms wholly inside the record's outcome or protein name no longer set novelty_language, raw matches and the flag without the rule kept (scripts/tag_wording.py); wording only, no rule changed: the 90% rule stated as coverage and as a pragmatic completeness rule, phenotype-derived mappings named disease-level cross-reference mappings, a gate audit stopping at the cap above the tolerance reported as 'cap reached without satisfying tolerance', the Jackson Heart Study list labelled a companion-paper, study-specific analysis-eligible background; three earlier log lines of 2026-10-02 moved inside the log block; unit tests on Modal, 576 pass, and the three synthetic dry runs pass (outputs/tests/pytest_all_modal_20261002T150722Z.txt); 13 deliberate changes of the new rules each made a test fail (planning/build_stage0/mutation_check_round7_fixes.json); synthetic records, fixtures and resource files only  nothing run  ·b0e2d076
2026-10-02  three-gates pass, no rule changed: results ledger started (.results/ at the repository root, committed); stages are recorded through scripts/stage_record.py (RUNBOOK.md, Results ledger), run once on synthetic claims (run prefreeze_ledger_proof_20261002: stage-5 drug joins on Modal, the 3 local copies equal to the volume files); pinned quotations moved to claims/ and the evidence the plan cites to docs/ (source texts not committed); paths in the body updated and one sentence added saying that paths under planning/ are working files outside the public repository; earlier log lines keep their paths: planning/source_reports/verification/ (claims, compositions, VERIFICATION.md, SCOOP_RERUN_2026-09-30.md) is now claims/ and docs/source_verification/, planning/feasibility/ is docs/feasibility/, and the cited files of planning/build_stage0/ are in docs/stage0_build/  nothing run  ·9dedd47d
2026-10-02  quotations read, no rule changed: the 26 truncated, 5 normalized and 1,541 short quotations that citations verify warns about were read against their sources (docs/source_verification/QUOTE_WARNINGS_2026-10-02.md); 29 claims added, none edited; 4,499 quotations, all found; two component lists hold cohorts whose own table row limits their contribution (OPEN_QUESTIONS 82), tables unchanged; citations fetch on an empty copy of claims/: 2 fetched, 156 differ, 41 unavailable of 199, because the pins are on extracted texts; unit tests on Modal, 585 pass, and the three synthetic dry runs pass (outputs/tests/pytest_all_modal_20261002T160140Z.txt); the OSF dry run accepts the text (docs/stage0_build/osf_dry_run_result_2026-10-02_final_text.txt)  nothing run  ·8daac5a8
2026-10-02  dress rehearsal of the freeze, the results ledger and the manuscript checks on scratch copies (docs/stage0_build/DRESS_REHEARSAL_2026-10-02.md): nothing committed, frozen, sealed or sent to OSF here; stage commands run on the stored pre-2019 smoke search, the cached exchanges of the 30 pre-2019 development abstracts (no new request) and synthetic registries, with stage 4 claim checks and stage 5 joins on Modal under rehearsal names since removed; no rule changed; fixes to RUNBOOK.md, stage_record.py (freeze record, one-file volume map), modal_biology_joins.py (verify_claims entrypoint), run_extraction.py and apply_eligibility.py (refuse to replace an output), build_registry.py (pinned-file sha256 check), .gitattributes, and the parked census plan renamed; 593 tests pass on Modal (outputs/tests/pytest_all_modal_20261002T192344Z.txt)  nothing run  ·9e16ecb5
2026-10-02  pre-mortem applied (planning/premortem/PREMORTEM_2026-10-02.md; item-by-item in ADJUDICATION_premortem_v17.md), with the author's decisions: H2 unchanged; H2b added, the same three-way rule on identical or overlapping participant sources, read on H2's bootstrap replicates, with a registered reading of the six reachable verdict pairs and both verdicts also at the 1.25th and 98.75th percentiles; the resolvable share registered as the ceiling of H2's lower bound; 20 registered secondary outcomes (scripts/registry_secondaries.py: reporting completeness, dataset usage, edge relations, H2 and H2b by families per pair and over directional families, direction agreement by edge class with identical-release edges as the positive control, significance discordance, contradiction-source comparison, first-claim concordance, periods, yearly series, therapeutic areas, platform pairing, claims per family, top lists, wording by repetition and year, citation of the earlier claim, source overlap, document class and journals, accounting), each an estimate with an interval and no verdict; hub expectation by permutation, alignment expectation from margins, reference screen split by shared pQTL source, pathway naming rule; sensitivities claim_specific_dataset_names_only, tested_count_1000_or_more, protein_cluster_bootstrap, two_verdicts_at_bonferroni_level, and the sensitivity 'H2 on the participant-overlap relation' retired into H2b; record metadata looked up in OpenAlex at stage 5 (reference lists, journal, query sources); country of the first author collected with no planned analysis; reserved words, units and denominators table, reasons for the 0.5 line and the 100-protein floor, the author's check of a manual code defined as a literal match, 'preregistered' removed from the planned paper title with one two-sided sentence registered; outside check of the search registered to run only on a study list pinned before the freeze: the Wu 2024 supplement answered HTTP 403 and the DMRdb file address a 303-byte notice, so no list is pinned and none was read; no search run, no claim extracted, no in-window record read  nothing run  ·ea1735f5
2026-10-02  pre-freeze checks of v17 on synthetic records, fixtures and committed tables only: unit tests on Modal, 651 pass, and the three synthetic dry runs pass with every registered secondary equal to its hand-worked value (outputs/tests/pytest_all_modal_20261002T195518Z.txt, outputs/dry_run/20261002T195526Z, outputs/dry_run_biology/20261002T195518Z, outputs/dry_run_drug/20261002T195518Z); 52 deliberate changes of the new rules each made a test or a dry run fail (docs/stage0_build/mutation_check_v17.json); the OSF dry run accepts the text (docs/stage0_build/osf_dry_run_result_2026-10-02_v17.txt)  nothing run  ·cb4e1972
2026-10-02  wording only, no rule changed: the reason for the 100-protein floor states that the known-item runs changed which stated count the floor applies to and not its value; the alignment-margin sentence no longer asserts what the claims are; reporting completeness has its own denominator row; unit tests and the three synthetic dry runs rerun on Modal on this text, 651 pass (outputs/tests/pytest_all_modal_20261002T195810Z.txt, outputs/dry_run/20261002T195818Z, outputs/dry_run_biology/20261002T195810Z, outputs/dry_run_drug/20261002T195810Z)  nothing run  ·bffc349f
2026-10-02  wording only, no rule changed: the reserved words are reserved for the paper's results, tables and abstract, where they describe pairs, edges, families or data sources; unit tests and the three synthetic dry runs rerun on Modal on this text, 651 pass (outputs/tests/pytest_all_modal_20261002T200046Z.txt)  nothing run  ·2cba2f06
2026-10-02  live smoke run of stages 1 to 6 on records first public before 2019 (label smoke_pre2019_20261002; docs/stage0_build/LIVE_SMOKE_2026-10-02.md, counts in live_smoke_counts_2026-10-02.json): registered queries on 2018-06-01 to 2018-06-30 in the three sources (18 screening records), one smoke citation-chasing round on the one eligible record with cited and citing works limited to an OpenAlex date of 2018-12-31 or earlier (97 screening records), 33 GPT-6.1 Sol requests (29 eligibility, 4 extraction) on records first public before 2019 only, stages 4 to 6 on Modal and locally; both eligible families have the window outside, so no registry claim, pair or table of a registered window exists. One record of the registered window was retrieved and not read: PMID 30239796, which OpenAlex dates in 2018 and PubMed on 2019-01-10, came back in the chase responses; its abstract is in the stored responses and the archived first output of the round, is in no smoke screening set, and went to no model. Gate audit not run (86 eligibility calls needed). Fixes without a rule change: verify_spans.py accepts screening-set abstracts, claim_tags.py and the stage 5 joins take every extraction file and screening set, smoke modes for record_metadata.py fetch and the full-text census, smoke window and label options; 667 tests and the three synthetic dry runs pass on Modal (outputs/tests/pytest_all_modal_20261002T202200Z.txt)  no results seen  ·a9d08231
2026-10-02  live smoke run on records first public before 2019, second pass (docs/stage0_build/LIVE_SMOKE_2026-10-02.md): gate audit of chase round 1 run (86 marked records judged by the eligibility prompt; 3 judged uncertain, each with an empty or three-character abstract), the 3 extracted (no claim), then stages 4b to 6 run with content under a smoke-only switch of assemble_registry.py (--smoke-label: refuses a label not starting smoke_, any record first public in 2019 or later, and an output folder outside outputs/registry/<label>...; later steps refuse to write a smoke registry's results under another name): registry of 5 families and 3 claims, manual-coding queue of 1 row (no row coded), record metadata, funnel of the search and the chase round, biology joins, sensitivity tables and drug joins on Modal against the pinned files, full-text census (no open-access full text). 89 further GPT-6.1 Sol requests (86 eligibility, 3 extraction), all on records first public before 2019; 122 in the smoke run in all. Foreknowledge item 17 added (v17a; no rule changed). An absolute home path was removed from 16 stored tool outputs (docs/stage0_build/HOME_PATHS_STRIPPED_2026-10-02.json); 3 of them are named by ledger manifests and were replaced through stage_record.py replace (outputs/results_manifests/replaced_files.json). Observed and not changed: a record with no abstract is judged uncertain by the eligibility prompt and so enters extraction, the registry's eligible families, the next round's seeds and the gate-audit positives; the plan has no rule for records without an abstract  no results seen  ·7e197829
2026-10-02  no_abstract rule registered (v17b; OPEN_QUESTIONS 101; docs/stage0_build/NO_ABSTRACT_FLOOR_2026-10-02.md): a record for which no source holds an abstract of at least 200 characters (whitespace collapsed) is classed no_abstract by script when a screening set is assembled, before the keyword prefilter and before eligibility; it is not sent to GPT-6.1 Sol, has no decision, is never an eligible family, a chase seed, a marked record or a positive of a gate audit, joins a family only as a linked record (the registry record is chosen among the family's records that have an abstract), and is counted per screening set in the funnel; a negative-control record so classed is counted and not judged; a record's abstract is the first in source order that reaches the floor; the sentence 'A record with no abstract is screened on its title' is removed. The floor was fixed on the abstract lengths of the 313 records first public before 2019 that are held (7 with none, stubs of 3 and 151 characters, 304 with 408 or more); the four shortest non-empty texts, all first public before 2019, were read; of the 24 known-item abstracts only the lengths were computed (shortest 1,014). No sensitivity analysis for the floor; the funnel reports the no_abstract records with no text, with a stub, by document class and with a title holding both prefilter term groups. Foreknowledge item 18 added; item 14 now states the six stored records that PubMed dates in 2019, read by no person and no model; the sentence after the list states what has been run. The smoke round of item 17 was re-assembled under the rule from its stored responses and decisions with no request and no model call (docs/stage0_build/smoke_rerun_no_abstract_rule.py and its counts file): 3 of 115 screening records no_abstract, 112 judged, 2 to extraction (5 before), gate audit 0 positives in 83 sampled (3 in 86), 2 eligible families (5), the same 3 claim records  no results seen  ·1f1ca16e
2026-10-02  pre-freeze checks of v17b on synthetic records, fixtures and committed tables: unit tests on Modal, 711 pass and 1 skipped (the known-item length check reads outputs/known_items, which is outside the test image; it passes locally: 24 abstracts, shortest 1,014 characters), and the three synthetic dry runs pass with tables equal to the previous run apart from timestamps, the no_abstract field of the search records and two zero counts of the registry assembly (outputs/tests/pytest_all_modal_20261002T211127Z.txt, outputs/dry_run/20261002T211138Z, outputs/dry_run_biology/20261002T211127Z, outputs/dry_run_drug/20261002T211127Z); 39 deliberate changes of the no_abstract rule each made a test fail (docs/stage0_build/mutation_check_no_abstract.json; a first run left 1 of 39 standing and the test was strengthened); the OSF dry run accepts the text (docs/stage0_build/osf_dry_run_result_2026-10-02_v17b.txt)  no results seen  ·3f14f789
2026-10-02  correction of a path in the previous line: the registry dry run of that Modal run is outputs/dry_run/20261002T211143Z, not 20261002T211138Z; nothing else changes  no results seen  ·390d7ccc
2026-10-02  wording only, no rule changed: in the table of the no_abstract rule a record 'never dates the family' (it read 'has no date'); unit tests and the three synthetic dry runs rerun on Modal on this text, 711 pass and 1 skipped as before (outputs/tests/pytest_all_modal_20261002T211556Z.txt, outputs/dry_run/20261002T211611Z, outputs/dry_run_biology/20261002T211556Z, outputs/dry_run_drug/20261002T211556Z); results ledger: the rerun of the smoke round under the rule is recorded (runs smoke_pre2019_20261002_no_abstract_rule and ..._paths_removed), and its funnel file is recorded with two hashes because the repository's absolute path was removed from it after the first record (OPEN_QUESTIONS 104)  no results seen  ·f30f3896
2026-10-03  round-8 review applied (planning/perplexity_paper1_final/11_REVIEW_round8.md; item by item in 12_ADJUDICATION_round8.md), v18: H2 and H2b verdicts read on the observed finite-corpus bounds (supported LB > 0.5, contradicted UB <= 0.5); pair bootstrap, family-deletion range and protein-cluster bootstrap reported as resampling-stability displays with no verdict; bootstrap verdicts, the 1.25th/98.75th-percentile verdicts and the sensitivity two_verdicts_at_bonferroni_level removed; H2 primary, H2b a second registered hypothesis nested in H2; release identity undetermined when either family's attribution is unclear, H2b overlap from claim-specific names only, never disjointness, and pair_resolvable false under unclear attribution; contradiction-source dataset fields undetermined under unclear attribution; the (unresolved, unresolved) reading in the reviewer's words; claim dates (scripts/novelty.py) order families on a pair in first_claim_concordance, periods, citation_of_earlier_claim and the pair columns of yearly_series; the outside check of the search removed (scripts/external_lists.py, scripts/modal_external_lists.py and verification/external_study_list*.csv retired to planning/) and stated as a limitation; no country table (record_metadata.py country removed); H2b wording as documented shared participant-source components; every secondary table emitted, six in the main paper, the abstract limited to corpus size, H1, the H2 and H2b verdicts with bounds, the resolvable share and reporting completeness; accounting with pair-level and edge-level denominators; hub and alignment expectations as descriptive baselines; sensitivity family_pair_collapsed_hubs; conventions reworded; foreknowledge item 19; synthetic records, fixtures and committed tables only, no claim extracted and no in-window record read  nothing run  ·e33c5b16
2026-10-03  pre-freeze checks of v18 on synthetic records, fixtures and committed tables: unit tests on Modal, 718 pass and 1 skipped as before (outputs/tests/pytest_all_modal_20261003T172729Z.txt), the three synthetic dry runs pass with the registry dry run's verdicts worked again by hand for the finite-corpus rule (contradicted, contradicted) and the biology dry run's yearly series and accounting worked again for claim dates (outputs/dry_run/20261003T172741Z, outputs/dry_run_biology/20261003T172729Z, outputs/dry_run_drug/20261003T172729Z); 23 deliberate changes of the round-8 rules each made a test fail (docs/stage0_build/mutation_check_round8.json; a first run left 2 of 23 standing and two tests were added); results ledger: the two events of the no-abstract rerun dropped before any commit and the rerun recorded once (docs/stage0_build/LEDGER_RERECORD_2026-10-03.md), results verify --files reports no RESEALED file  nothing run  ·88a40bc6
2026-10-03  v18a: author-supplied lists for the SCALLOP CVD-I and AGES (Emilsson 2018) rows replace the background only when pinned before the pathway enrichment first runs (first s5_biology_ run in the ledger or earliest written confirmatory enrichment output); otherwise read only in the sensitivity author_supplied_lists_after_cutoff (scripts/author_lists.py, verification/author_supplied_lists.csv, empty); foreknowledge item 20 states the requests sent 2026-10-02 and 2026-10-03, no reply; text above the log changes by these only (planning/perplexity_paper1_final/PREREG_v18_to_v18a.diff)  nothing run  ·474314c1
2026-10-03  the author confirmed the 14 platform rows on 2026-10-03 (third check, literal match of quoted value to coded value; docs/stage0_build/PLATFORM_ROWS_CONFIRMATION.md), status coded; the ledger access level planned for the freeze is 'metadata only' (RUNBOOK.md, Results ledger); unit tests on Modal 727 pass, 1 skipped, the three synthetic dry runs pass (outputs/tests/pytest_all_modal_20261003T200129Z.txt); 11 deliberate changes of the new rule each made a test fail (docs/stage0_build/mutation_check_author_lists.json); OSF dry run accepted; synthetic records, fixtures and committed tables only  nothing run  ·e0c4b36a
2026-10-03  v18b: one sentence in the dataset-dictionary paragraph states that a cohort in a release's pinned cohort table stays a component where a footnote limits its role (GIGASTROKE WHI; MAGIC Oxford Biobank, UKHLS, VIKING, Whitehall II), the rule the components table already applied; no table or code changed  nothing run  ·bae5bf42
2026-10-03  frozen at 02bb006f3e55                nothing run  ·b7b0f8af
2026-10-03  osf draft 6ac165699df176be36e148ff of plan 9f06131af9936cc7  nothing run  ·e4b6225c
2026-10-03  osf attached dataset_dictionary.csv sha256 f30dda8e00f8bbc6c43e31e80b38935c7d4f0d3916f33b2e776cabc14fb0d39c  nothing run  ·b06cfa58
2026-10-03  osf attached RELEASES.md sha256 8dd5069d86d85c25e5fd0d84da23b18ab3b6e541e145c463e09d07c353cdd1c6  nothing run  ·1cf23051
2026-10-03  osf attached references.bib sha256 4e85a982b2c62fbbbcf43c9d8794c5aae35ead664ebaab58e28a1adc4ae0148f  nothing run  ·287d69dc
2026-10-03  osf attached modal_inputs_manifest.json sha256 03b054b9d27551d9329d25231974ea5d142be7e9b6c302c6a5918ebb9198e767  nothing run  ·44a643c5
2026-10-03  osf attached eligibility_prompt.md sha256 97073ed7699623d85d7accc0ddc8a7728938d3e2b4292ec3450af2541ddf21d3  nothing run  ·a11d894b
2026-10-03  osf attached extraction_prompt.md sha256 2a2bef3852f822eb64a19cdc6b880f8ba4f4cac7d262976f0016e517177a6049  nothing run  ·10c62984
2026-10-03  osf attached fulltext_extraction_prompt.md sha256 47d6b47bf7d90f1d9927af656db75000bbab6da34bd12a70e5c9bdbb250f9493  nothing run  ·18d0cfb9
2026-10-03  osf attached schema.json sha256 8b74e25a9a48b85cb89a15d9f7632ddaa5d9a2ee792e54c99b5a8f7a6046f7e1  nothing run  ·58de2641
2026-10-03  osf attached queries.md sha256 09c6b37010afaa03e777ebc5a7e451a5617300eca8e4d9d07c69437e1bb07eab  nothing run  ·80ac335f
2026-10-03  osf attached prefilter_terms.json sha256 b3ecc5d2f00b60494e737574c655c239af344b737f154f311853eebecc601496  nothing run  ·d6003ef1
2026-10-03  osf attached known_items.md sha256 c148b311cd4d7de338a55b9235851d3040fe376be990fa4e28faef1f53cc5e44  nothing run  ·8ac8ca17
2026-10-03  osf attached negative_controls.jsonl sha256 6f664f53f41bd4ce383ff69695715fa40ca6d04ce9a843401c8340c56e784de7  nothing run  ·9fb9a40b
2026-10-03  osf attached negative_controls_meta.json sha256 4021030cb3df79d7d92208006b66bedacfc54fd4d6ef5df17e38f2862a70ef71  nothing run  ·cd15a042
2026-10-03  osf attached author_supplied_lists.csv sha256 35a057dcb054872d0f41c2f2c8178cebc20984cbaead3f702d304a08c87e2869  nothing run  ·60044711
2026-10-03  osf attached dataset_components.csv sha256 b82a8ce799626ec054f6e79513f6b6af9af24e3f5de36ea6f9096911de85a591  nothing run  ·02961986
2026-10-03  osf attached direction_lexicon.json sha256 bdd67b7aca7abd0ae5cc0e6cdc241e1d383b56ebf58f54f7d9cafd88d9b09f75  nothing run  ·57ac031f
2026-10-03  osf attached epigraphdb_protein_mapping.csv sha256 e809a3c1771ba142687bfcfd5ab22f17e5fcca9607fde84055de7bac0c6dcd7a  nothing run  ·260d1d74
2026-10-03  osf attached epigraphdb_trait_alias_seed.csv sha256 f4b0bfcfd559479d48691499f356870cebbbe9f5a1c31ad4cbf3287c082cda22  nothing run  ·694a1b3e
2026-10-03  osf attached epigraphdb_trait_aliases.csv sha256 322b98891819c2f0461a86df9e39da2407528aa05f7a579a6b65cef99275f714  nothing run  ·130ba0c3
2026-10-03  osf attached epigraphdb_trait_mapping.csv sha256 097b38acecffe2bd5c3b8009d79ebc2155f80f3feda1546ccfdfdb0bb0c15cf8  nothing run  ·2dfa1789
2026-10-03  osf attached mondo_efo_collision_table.csv sha256 b858b4bd0fba33c1d2138e272b3c753c45f3d3f8b426e25b99a9d97c320fd0e0  nothing run  ·299956c1
2026-10-03  osf attached mondo_efo_collision_table.meta.json sha256 edb203309ed9df178f44cc6ac4e7130e89d5b28c808156a1095d0aef34f74265  nothing run  ·cf3e9e8f
2026-10-03  osf attached obsolete_label_replacements.csv sha256 a9578b07753d7f77606404ced6af5cd5289b9909489760ca05465aedc43db3d7  nothing run  ·169d656c
2026-10-03  osf attached obsolete_label_replacements.meta.json sha256 8b9d0e961e91891f69e96f2c4d015880f093863197c8a259702076b5b242ad25  nothing run  ·62f0daed
2026-10-03  osf attached ontology_edges.csv sha256 5b8f0b3fe17aab4c885c04ad337cec2c980d35c69acc847c8a754f14deff7261  nothing run  ·1f0ee260
2026-10-03  osf attached ontology_edges.meta.json sha256 dd453c702a7611531f9c5a09ce8057f22bd74814c7bd823eb30a0d846c1508d8  nothing run  ·02f6dfef
2026-10-03  osf attached outcome_alias_seed.csv sha256 02783d0b2006f67c4fcd3eadcdafae244e034e96f047f74f47af823c9c3cd598  nothing run  ·c7340a81
2026-10-03  osf attached outcome_aliases.csv sha256 663555898aa3d9fa1892693a8c1bd71dc4f17f81f382f852ac7da33c12a3f240  nothing run  ·e16f68b4
2026-10-03  osf attached phenotype_cross_references.csv sha256 0756154ed75c8c7795ac8928ae914f111a6c7c05c81eff4bc8104ee3ccfd4a67  nothing run  ·aa89489a
2026-10-03  osf attached phenotype_cross_references.meta.json sha256 2c7e38c8764135d79e1a788b69ec1777db3543693aa175c4b0a7b530808a9953  nothing run  ·478da4e9
2026-10-03  osf attached platform_assay_attachments.csv sha256 1c9041e5628fa0422f1be8c562e7c400944381aea39b6cee7bffc64735aa2b12  nothing run  ·d38563de
2026-10-03  osf attached platform_assay_lists.csv sha256 3a01aa3c4ed2fe6c616bc7d767de3d7bee18ec9090509837f10e8c3620c68e96  nothing run  ·9ef75998
2026-10-03  osf attached platform_assay_lists.meta.json sha256 a2def84b1d7e876ea943582a79283ad1df12dc80f7e5aeac3560f8d15b933627  nothing run  ·25b7e037
2026-10-03  osf attached platform_list_sources.csv sha256 5b6b08535c27d58a8b356fe409ac315b0818279c14ca1167f6c103619a173484  nothing run  ·9bac13ee
2026-10-03  osf attached pleiotropic_loci_eldjarn2023_ST36.csv sha256 717050fab7df62dc0ec804bd26561755e0d0ed85bb2a0c206bd178e0356d3cdf  nothing run  ·759c3fd2
2026-10-03  osf attached pleiotropic_loci_eldjarn2023_ST36.meta.json sha256 c34665bdbc66207d1248a6e2e79843dca2e6d3798aaa3ca0c6f4db54f483dcf6  nothing run  ·05126716
2026-10-03  osf attached pqtl_row_attributes.csv sha256 66d71cf132b80d91bf6be4bd03db9c8b57789c5eae042213a4e7729cf5531d0b  nothing run  ·6f0aafb1
2026-10-03  osf attached improve_folkersen2017_S3.csv sha256 808da6fada52f3dea578b974bd4954c9dd30ed2b24de181d4351794c53e1fed3  nothing run  ·ef8e7cc7
2026-10-03  osf attached jhs_katz2022_soma13k_reagents.csv sha256 b339784a8fe6b2f50109dc499a2eae130d439911cd3757e89f4f332f8458565a  nothing run  ·8355c953
2026-10-03  osf attached nsphs_enroth2014_analysed.csv sha256 67d35accfb7900082965b493b3267d8d0ea9b36d8061a3168b3cf3d119e15ebb  nothing run  ·3e39e1fd
2026-10-03  osf attached published_lists_derived.meta.json sha256 6bf469b22ceae8755c8bbd898a5f5432d7ff1096ab5bfcbf4c545b5de68c5f81  nothing run  ·e820fa28
2026-10-03  osf attached scallop_koprulu2026_S5_targets.csv sha256 35addfef914fa8636e64320c22c6c2df74376b2be86a705fed4bb63ae1e3f993  nothing run  ·8b2ecd82
2026-10-03  osf attached published_source_files.csv sha256 b7c94e9062087c4bcc29b208d44923ee18dca2fcbe526bd531cdef831866a1b4  nothing run  ·f12e3de3
2026-10-03  osf attached therapeutic_area_names.csv sha256 87a51779e3e2c4621d04b0df7637cd573f4c40e6ca1ff64676e1a4769564614b  nothing run  ·e4cc6ef2
2026-10-03  osf attached therapeutic_areas.csv sha256 31f61cdac2a185e217cd43e7d0358cb6489c284bff20b9c70ece8efb82540afe  nothing run  ·cd1fb359
2026-10-03  osf attached wording_lexicon.json sha256 8a5dd42f85c5ca9d1e32bca2a24eb0f3eb69e6b9add2ca9c3e55e7cfdce35fcf  nothing run  ·b11f1677
2026-10-03  osf registration https://osf.io/zae8c submitted by the author 2026-10-03T21:04:30Z from draft 6ac165699df176be36e148ff, public immediately; in the OSF approval window when logged  nothing run  ·5404f1b8
2026-10-03  osf registration https://osf.io/zae8c approved by the author and public (checked 2026-10-03T21:32Z)  nothing run  ·7b8af343
2026-10-03  registered search run once on 2026-10-03 (UTC 21:37 to 21:40), all 26 streams complete, no failed request; run_search.py then ended with its count-gap error: six OpenAlex streams retrieved a number of rows different from meta.count (Q1 confirmatory 2486 rows, 2483 distinct works, reported 2484; Q3 confirmatory 1293, 1291, 1291; Q4 confirmatory 2291, 2289, 2289; Q1 update 1156, 1156, 1157; Q3 update 515, 513, 513; Q4 update 1006, 1005, 1005), i.e. ten works returned twice across cursor pages and one work fewer than reported in each Q1 window; PubMed and Europe PMC streams match their reported counts; only counts and work identifiers were read; no screening set assembled and no record sent to GPT-6.1 Sol; the run is stopped here for the author's decision on the gap  results not opened  ·7128f963
2026-10-03  second request of two OpenAlex streams on the search date: the registered runner (run_search.py, 2026-10-03 21:37-21:40 UTC) ended on its count gap, the two OpenAlex Q1 streams each holding one distinct work fewer than OpenAlex reported (2,483 of 2,484 confirmatory; 1,156 of 1,157 update), with works repeated across cursor pages. The runner never requests a completed stream again, so scripts/rerequest_openalex_stream.py requested Q1_confirmatory and Q1_update again at 21:47-21:48 UTC the same day with the runner's query builder, filters, select, page size, headers and paging, into outputs/raw/search/2026-10-03_openalex_q1_rerequest/, beside the first request and not inside it. Second request: 2,483 distinct of 2,484 reported (confirmatory), 1,157 distinct of 1,157 reported (update); one work in each stream is in the second request and not the first, and one confirmatory work is in the first and not the second (comparison.json). Stored separately; not yet used; whether it is used is not decided. Only work identifiers and meta.count were read; no screening set built; no record sent to GPT-6.1 Sol  results not opened  ·cca8222b
2026-10-03  decision by the author 2026-10-03: the screening set takes, for the two OpenAlex Q1 streams, every work present in either request of the search date (first request plus the second request stored in outputs/raw/search/2026-10-03_openalex_q1_rerequest/); all other streams as first retrieved. The union equals the count OpenAlex reported for both streams (2,484 and 1,157 distinct works). Departure from the registered single request, made after reading identifiers and counts only, before any record content was read or screened  results not opened  ·0b91ca44
2026-10-06  Amendment 1 (AMENDMENT_01_extraction_system_comparison.md, sha256 6229a07e97b3d4cf334a3cce689f87db559493c3af055dc0c8a7869185653ce2): extraction-system comparison added (registered Sol extraction against a tuned Luna extraction system: model and prompt both differ, no difference attributed to the model alone); every abstract GPT-6.1 Sol extracts is also extracted in two separate runs by gpt-6-luna with prompts/luna_extraction_prompt.md (sha256 bf02041d287666f6104db8d756cbef3300ab50c8a9640c795b5cac39709b2f40, revision e4e4ee731887) and the verified family-pair registry entries are compared, descriptive, estimates and bounds only for Luna-derived registries with no threshold classification, one fixed supplement table, nothing in the abstract; GPT-6.1 Sol remains the tool of every registered primary and secondary result and none changes; the sentence 'No second model enters any stage' now holds for registered results only; Luna prompt tuned 2026-10-06 on seven pre-2019 development abstracts (records matching Sol: frozen prompt 29 of 66, this prompt 48 of 66, scored on the tuning abstracts); logged after the registered search (2026-10-03), whose responses are stored and of which only work identifiers and counts were read; no record screened, no claim extracted; reviewed in rounds 11 and 12 (planning/perplexity_paper1_final/)  results not opened  ·e1dd9911
2026-10-06  osf registration https://osf.io/zae8c updated for Amendment 1 (OSF schema response 6ac52354c6c5970fb137fdbd, submitted 2026-10-06T16:35:56Z and approved by the author 2026-10-06T16:42:06Z): one answer changed, Data collection procedures, where a bracketed note after the sentence on a second model states the amended sentence and names AMENDMENT_01_extraction_system_comparison.md with sha256 6229a07e97b3d4cf334a3cce689f87db559493c3af055dc0c8a7869185653ce2; the original response 6ac16de1162acfccf0b566f3 remains as the first version; no file attached to the update  results not opened  ·1d68bd65
2026-10-06  screening set built 2026-10-06 from the union of the two requests of the search date, as decided on 2026-10-03: scripts/merge_search_requests.py (new, sha256 0a7bda9b9f5f7e0f1579d19cd301068712a13885929b2037f19bcc15898a668a; no sealed script edited, no stored response altered) wrote outputs/raw/search/2026-10-03_union (first-request files byte for byte, the second request's 37 OpenAlex pages added for Q1_confirmatory and Q1_update; union.json sha256 ae5fd56a95a67a335bf0f29e3dd6fef8221a461e971770f0bd6a32be5b552139 lists the sha256 and origin of every file); the runner's count check, which compared rows and stopped on works returned on two cursor pages, is replaced by an explicit check of distinct works against the count OpenAlex reported, which every OpenAlex stream passes (Q1_confirmatory 2484 of 2484, Q1_update 1157 of 1157, the six other streams equal to their reported counts) and every PubMed and Europe PMC stream passes on its own counts; the sealed assemble_screening_set.py then read that folder (--out outputs/screening/2026-10-03) and keyword_prefilter.py ordered the queue; only identifiers, counts and the funnel counts of funnel.json were read, no title or abstract  results not opened  ·c7a1cc1e
2026-10-06  stage 2 on the search records, 2026-10-06 16:53 to 21:43 UTC: no_abstract classed first (321 of 5,908 screening records), then GPT-6.1 Sol eligibility with the frozen prompt (revision 2811496ef424) on the 5,587 records with an abstract; 5,521 answered and valid (6 after one re-run), 66 recorded extraction_failed because both attempts returned HTTP 429 insufficient_quota (the API account had no credits; 793 such exchanges between 17:46 and 18:16 UTC, every one stored), none for a schema failure; the registered rule covers a response that fails schema validation and does not cover a request that received no response, so apply_eligibility.py, select_eligible.py and the ledger record s2_eligibility_search are not run until the author decides how the 66 are treated; no eligibility decision, title or abstract was read, only run counts and HTTP statuses; all 24 known items are in the screening set and none is among the 66 (docs/run/known_item_retrieval_2026-10-06.json)  results not opened  ·34616c99
2026-10-06  negative controls run once, 2026-10-06: abstracts of the 50 registered control records fetched from PubMed (0 no_abstract), GPT-6.1 Sol eligibility with the frozen prompt (50 answered, 0 failed), registered rule applied; specificity counts of outputs/negative_controls/negative_control_specificity.json read  results seen  ·ed16b055
2026-10-06  rehearsal of scripts/run_extraction_luna.py against the API with --dev on the 30 pre-2019 development abstracts (label dev_rehearsal, run 1; 30 of 30 valid, no retry); outputs outputs/parsed/luna_extraction_dev_rehearsal_run1_e4e4ee731887.* and outputs/raw/luna/extraction/e4e4ee731887/run1; no record of the window used; not a result of the amendment's comparison  results not opened  ·fb3c627c
2026-10-06  stage 2, second request of unanswered records: 66 of the 5,587 search records received no response on 2026-10-06 (HTTP 429 insufficient_quota on every try of both attempts, the API account being out of credit); the author decided that no record is dropped for an operational failure, and on 2026-10-06 (21:55 to 21:56 UTC, after credit was added) the 66 were requested again with the same frozen eligibility prompt, schema and settings (revision 2811496ef424) through the registered runner with its exchanges under outputs/raw/sol_rerequest, so no stored exchange was touched and no stored answer replaced: 66 of 66 valid at the first attempt; scripts/rerequest_unanswered.py (new, no sealed script edited) wrote the queue and writes one eligibility file in which each unanswered row is the row of the second request and every answered row is unchanged; departure from the registered re-run rule, which covers an invalid answer only; no eligibility decision, title or abstract read  results not opened  ·c2acba66
2026-10-06  stage 1b round 1 and its stage 2, 2026-10-06 22:00 to 2026-10-07 UTC: citation_chase.py --round 1 on the 2,093 seeds (2,057 found in OpenAlex; 29 without DOI or PMID); 32,853 new screening records, 1,121 classed no_abstract; keyword gate marked 31,612 and left 120 to screening; GPT-6.1 Sol eligibility with the frozen prompt on the 120 and on five gate-audit batches of 600, no failed call; gate audit stopped at 3,000 sampled with 14 judged eligible or uncertain, one-sided 95% upper bound 0.0073, cap reached without satisfying tolerance (registered outcome, reported as such); the 14 sampled positives enter the workflow with the 24 of the queue (38 records to extraction and seeds of round 2); response bodies on the Modal volume, compared by hash; counts only read, no title, abstract or claim content  results not opened  ·7697ce78
2026-10-06  departure, decided by the author 2026-10-06 after the gate-audit counts of citation-chasing round 1 were seen and before any claim was extracted: GPT-6.1 Sol screens, with the frozen eligibility prompt and settings, every record of round 1 that the keyword gate marked and the audit had not sampled (28,612 records), and in rounds 2 and 3 every chased record with a usable abstract, so the gate orders records and no longer excludes any; reason: the registered audit of round 1 ended at its cap without satisfying the tolerance (14 positives in 3,000 sampled, one-sided 95 percent upper bound 0.0073 against 0.005); unchanged: the audit result of round 1 is reported as registered, the stored audit decisions are reused and not asked again, the sensitivity analysis without citation chasing stands, the no_abstract rule stands, eligibility is decided by the registered rule; no sample audit runs for rounds 2 and 3 because every record is screened, and the gate's marked and passed counts are reported with the eligible records found on each side; the calls run through a separate script with more parallel workers than the registered runner's six, which changes the number of simultaneous requests and nothing else  results seen  ·5d0ccd42
2026-10-06  stage 1b round 1, full screening of the gate-marked records (departure logged 2026-10-06), 2026-10-06 23:21 to 2026-10-07 02:19 UTC: scripts/gated_out_remaining.py listed the 28,612 marked records in no audit batch; scripts/run_extraction_parallel.py sent them to GPT-6.1 Sol with the frozen eligibility prompt (revision 2811496ef424) through the registered runner's own request and cache functions with 48 simultaneous workers, raw exchanges in outputs/raw/sol_chase_full; 28,612 of 28,612 answered and valid at the first attempt, no failed exchange, no rate-limit or billing refusal; registered rule applied: eligible 9, eligible count not stated 27, uncertain 113, ineligible 28,463; the registered audit of round 1 stands as recorded (14 of 3,000; estimate 134, interval 73 to 224, for these 28,612) and the count found among them is 149; records of round 1 to extraction and seeds of round 2: 187 (24 from the gated-in queue, 14 from the audit batches, 149 from the full screening); counts only read  results not opened  ·26d9b8f5
2026-10-07  stage 1b round 2 and its stage 2, 2026-10-07 03:29 to 05:03 UTC: citation_chase.py --round 2 on the 187 seeds of round 1 (187 found in OpenAlex); 4,991 new screening records, 245 classed no_abstract (214 empty, 31 stubs); the keyword gate marked 4,731 and left 15 unmarked; under the departure logged 2026-10-06 GPT-6.1 Sol screened all 4,746 with the frozen eligibility prompt (revision 2811496ef424) through scripts/run_extraction_parallel.py with 48 workers, 4,746 of 4,746 answered and valid at the first attempt, no failed exchange; no sample audit ran because every record was screened; registered rule applied: of the 15 unmarked eligible 0, count not stated 1, uncertain 1, ineligible 13; of the 4,731 marked eligible 5, count not stated 15, uncertain 47, ineligible 4,664; records of round 2 to extraction and seeds of round 3: 69; OpenAlex credits used 144; counts only read  results not opened  ·1b783bd8
2026-10-07  stage 1b round 3 and its stage 2, 2026-10-07 05:08 to 05:14 UTC: citation_chase.py --round 3 on the 69 seeds of round 2 (69 found in OpenAlex); 1,433 new screening records, 36 classed no_abstract (28 empty, 8 stubs); the keyword gate marked all 1,397 and left none unmarked; under the departure logged 2026-10-06 GPT-6.1 Sol screened all 1,397 with the frozen eligibility prompt (revision 2811496ef424) through scripts/run_extraction_parallel.py with 48 workers, raw exchanges in a new folder outputs/raw/sol_chase_round3 (the runner lists the response folder per record, and the folder of rounds 1 and 2 held 33,000 files), 1,397 of 1,397 answered and valid at the first attempt, no failed exchange; no sample audit ran because every record was screened; registered rule applied: eligible 1, count not stated 2, uncertain 11, ineligible 1,383; records of round 3 to extraction: 14; chasing ends here, three rounds being the registered maximum; counts only read  results not opened  ·34e02d28
2026-10-07  stage 3 and stage 3L, how they are run (logged before the first extraction request): one extraction file per screening source, labels search (2,093 abstracts), chase1 (187), chase2 (69) and chase3 (14), each from the eligible_abstracts file select_eligible.py wrote for that source; because under the departure of 2026-10-06 a round's decisions lie in several files (the gated-in queue, the audit batches, the marked records), the round's decisions files are concatenated unchanged into one file per round (sol_eligibility_round<k>_all_2811496ef424.decisions.jsonl) so that sample_repeat_run.py draws the registered ceil(0.10 x n) once over the round's eligible records, seed 20261001; GPT-6.1 Sol requests go through scripts/run_extraction_parallel.py and gpt-6-luna requests through scripts/run_extraction_luna_workers.py, which set the number of simultaneous workers and call the registered runners unchanged; a record left without a response by an operational failure is requested again and never recorded as failed; no rule of extraction, sampling or agreement changes  results not opened  ·246f94c6
2026-10-07  stage 3, 2026-10-07 10:49 to 11:23 UTC: GPT-6.1 Sol extraction with the frozen extraction prompt (revision 0b97103cd7a4) through scripts/run_extraction_parallel.py with 48 workers, raw exchanges in the registered folder outputs/raw/sol/extraction/0b97103cd7a4 (which held 32 files of pre-freeze development runs); labels search 2,093, chase1 187, chase2 69, chase3 14, in all 2,363 of 2,363 answered and valid at the first attempt, no failed exchange, no extraction_failed; repeat-run samples drawn by sample_repeat_run.py (seed 20261001, ceil of 0.10 x n): search 210 of 2,093, round 1 19 of 187, round 2 7 of 69, round 3 2 of 14, in all 238; second run on the samples with --raw-root outputs/raw/sol_repeat, 238 of 238 answered and valid; repeat_run_agreement.py run per source, its output files not opened; no claim content read  results not opened  ·a6dcf050
2026-10-07  stage 3L of Amendment 1, 2026-10-07 11:23 to 12:18 UTC, after stage 3 was complete: gpt-6-luna with prompts/luna_extraction_prompt.md (revision e4e4ee731887) through scripts/run_extraction_luna_workers.py with 32 workers, on the four extraction files of stage 3 (search 2,093, chase1 187, chase2 69, chase3 14); run 1: 2,363 of 2,363 answered and valid at the first attempt, one failed exchange that the runner retried and that was then answered; run 2: 2,363 of 2,363 answered and valid at the first attempt, no failed exchange; no extraction_failed in either run; stages 4L and 5L (verification, registries, usage files and the comparison) wait for stages 4 and 5; no claim content read  results not opened  ·67a0ee44
2026-10-07  stage 4 begun 2026-10-07 and stopped: verify_spans.py ran on the four extraction files (14,053 claim records; both checks pass for 12,601 of 12,664, 980 of 981, 326 of 326 and 82 of 82); claim_tags.py ran; the Modal claim checks completed for chase1, chase2 and chase3; for the search file the registered scripts/verify_claims.py raised (find_estimates, line 546: a P-value exponent written with a thin space, U+2009, which the pattern accepts and the integer conversion does not strip), so no claim check exists for the search file, and the registry assembly and the manual-coding queue have not run; nothing was changed; the correction of the verifier awaits a decision; no claim check, relation or aggregate was opened  results not opened  ·8eba766a
2026-10-07  departure, stage 4 claim verifier: the registered scripts/verify_claims.py (sha256 5f29a69515a3be5ed65f11964f78b8d9c8147a45acd3979cb9d19aea26cf3ff8) raised on the search extraction file (find_estimates, line 546, ValueError) because a P-value exponent was written with a thin space (U+2009) after the minus sign: the patterns admit any white-space character after a sign and the two number conversions removed the ordinary space only; scripts/verify_claims_whitespace.py (sha256 b217f93059d0dd7cb327de0c7df8a0ecc77b5ff6e514e4c1b89659a5f8157c7d) is a copy in which those two conversions, the exponent of a P value and to_float, remove every white-space character, and nothing else differs (no pattern, lexicon, rule, threshold or output changes; tests/test_verify_claims_whitespace.py, sha256 8e6dfb0513da936df97f434747e41bcc8704291693d5f0a33d9cff2615177759, shows the copy differs from the sealed script in those conversions only, 25 cases pass, suite on Modal 829 pass and 1 skipped as before); it runs through scripts/modal_verify_claims_whitespace.py (sha256 82bea23e480478ab62e45e9c4bf6f3b2a46139560e42e89f1b090010de7eb244), which runs the copy with the image, files and command of modal_biology_joins.py::verify_claims, stores its results under /02_claims_meta/stage4_whitespace/ on the volume and leaves the registered script's results under /02_claims_meta/stage4/ untouched; the copy is used for all four extraction files, after a check that on chase1, chase2 and chase3, which the registered script completed, it writes byte-identical claim_checks.jsonl and claim_summary.json (the registered results are kept beside the copy's, and any differing byte stops the stage); seen before this decision: the span-check counts of the four files, and the text of three evidence spans that failed the span check (two records of one paper, one of another), shown once when the span summaries were printed to read their counts; no claim check, dataset relation or aggregate was opened; reviewed in round 13 (planning/perplexity_paper1_final/)  results seen  ·5735c36d
2026-10-07  stage 4 claim verifier, comparison made: scripts/verify_claims_whitespace.py and the registered scripts/verify_claims.py wrote byte-identical claim_checks.jsonl and claim_summary.json from identical inputs for chase1, chase2 and chase3 (3 of 3; outputs/verification/sol_extraction_<label>_0b97103cd7a4/verifier_comparison.json; claim_checks.jsonl sha256 58b199b0102964f490ae73d6daf2d2f0521c148f175958dfc5d90fa4050df14a, a5b527aa290e2a23be6a35767bc6cb06db4588e08a765d70f448243d477d7590 and b3e7da2400f48f4400175dedd9993626d254d0fc91cc52a7c4ba95f7d1103f8d); the copy now runs on the search file; no claim check was opened  results seen  ·05d81dd3
2026-10-07  manual coding of dataset names, how the first check is run (clarifications; logged before any row is coded, before the scripts are sealed): (1) local paper passage: scripts/coding_passages.py (sha256 972d11ea523e413f47c842419ba68283e8dc79592eb42e5557878e8186fa48f5) gives, per queue row, every sentence of the source (the body of the Europe PMC open-access full text as fetch_fulltext.py rendered it, else the abstract; supplementary files never) that holds the name as written or a candidate dictionary row's term from the fields name, aliases, release, source_citation, source_identifier or sample_size, matched case-insensitively after Unicode normalization, with one sentence either side in the same paragraph, one further sentence only after a name-only sentence ending in a citation, overlapping windows merged, a table row line given alone with its caption and headers, and no_local_passage_found when nothing matches, never a wider search; one fixed sentence segmenter; section title, sentence indices and the sha256 of the source kept; (2) citations: where a passage sentence carries a citation linked in the XML, the linked entries of the paper's own reference list are given, and a citation resolves a row only when the local sentence attributes the analysis dataset to it, the reference is one bibliographic record, that record identifies exactly one candidate row, the paper reports no conflicting release, both the sentence and the entry are pinned, and the row is flagged companion_source; (3) a release is identified by a release identifier, accession, uniquely identifying citation or source DOI, or the exact N with platform, panel or analysis year matching one row and conflicting with none; N alone, platform alone, an approximate N or a post-exclusion N is unresolved, and conflict means unresolved; (4) coders: four Claude Code coding agents, one per paper, assigned by scripts/coding_assignment.py (sha256 bc8375a8c0389c80eaf6e62b048ae288761768cdbee569ad7072c3efd5480030, seed 20261007), the same instructions for each (prompts/manual_coding_coder_instructions.md, sha256 ab5d004c69d08d5ea2c04f65d5ead25c7857d40dfa4c59e3494540a828e562fb), each given only the name as written, its passages and the dictionary definitions, the coder recorded on every row, every queue row coded on its own and no code carried between papers; they are not independent human coders and no agreement between them is reported; (5) machine gates added before the second check, replacing none of the three registered checks: scripts/coding_gates.py (sha256 36f52abf2c49f58c5317aab0e519089e106fdb5441baddda9a8a8bb5c340b8ae) checks every pin with citations verify --strict, that the quote is a sentence of a passage given, that the pinned material holds an identifier of the coded row no other candidate has, and for a companion row that the entry's DOI is a DOI of the dictionary row's source; a failed paper returns to its coder and every attempt is kept; tests tests/test_coding_passages.py (sha256 cb4edeaf3db29b0fd68b5a2011df2572f25f27d7f6edaddbaf18e37e5756d5d6) and tests/test_coding_gates.py (sha256 43e8df6b5176896f549b10f5e79dcd8f397e6a23ced495db8e8e84b8f265cb22), suite on Modal 868 pass and 1 skipped; exposure at this point: the span-check counts, the text of three failing evidence spans (logged above), the counts n_claims, span_pass and enters_registry of the four claim summaries, the queue counts (872 rows, 434 papers, 293 distinct names; 528 release_ambiguous and 344 unmatched; 376 pQTL and 496 outcome; 242 papers with open-access full text, 192 abstract only) and the dataset names of the queue with their row counts; the 242 full texts are fetched and unread, no passage has been generated or read, no row is coded, and no claim check, registry record, dataset relation or H1 or H2 aggregate has been opened; reviewed in round 14 (planning/perplexity_paper1_final/)  results seen  ·c292d5ca
2026-10-07  deviation, manual coding of dataset names, a second unresolved value (prospective: logged before any row is coded): Before manual coding began, the queue revealed sources that explicitly named datasets absent from the registered dictionary. Such rows could not truthfully receive not_stated_in_source; a distinct unresolved reason, source_names_dataset_absent_from_dictionary, was therefore added. These rows remain unresolved in every registered analysis, so the change affects provenance and reporting but not dataset-relation assignment. Implementation: scripts/manual_dataset_coding.py and scripts/assemble_registry.py are unchanged; scripts/manual_dataset_coding_reasons.py (sha256 0a3e6ccb7da2b621ee82004f730c2973a9be460167a932217f7af5ea14d1f253) keeps an extended table (the twelve registered columns and, per row, the coder, the attempt, the passage, the unresolved reason, the identification basis, the companion_source flag with its pinned reference entry, and the dataset the source names) and writes the registered table from it, in which a row whose agreed value is the new one carries not_stated_in_source and no other row is altered; tests/test_manual_dataset_coding_reasons.py (sha256 878a6b4307108c649ef0f3bb7118506e39543a0154e6768b857a3589ea7b8ebd) shows that the registered reader then returns exactly the codes it returns for not_stated_in_source rows; the two unresolved values are counted apart; exposure and queue counts as in the preceding entry (872 rows, 344 of them unmatched; the dataset names of the queue seen, no row coded, no passage read); reviewed in round 14 (planning/perplexity_paper1_final/)  results seen  ·00cfa7bc
2026-10-07  departure, manual coding of dataset names, passage generator corrected before any passage was read or any row coded: on its first run scripts/coding_passages.py (sha256 972d11ea523e413f47c842419ba68283e8dc79592eb42e5557878e8186fa48f5) reported 61 of the 242 full-text papers without reference entries; counts of differing lines showed the cause: its strip_marks collapsed white space when removing the citation marks, which altered every table row line holding an empty cell (two spaces in the registered rendering; 1,102 lines in 60 papers, each equal to the stored line but for spaces), so those bodies failed the comparison with the stored body and took the prespecified path without reference entries; scripts/coding_passages_whitespace.py (sha256 b6ed9e3fa2e16d254e7e9a6f4953c6036fe5e99e881e89b7b3aed1916795d675) is a copy in which strip_marks removes the marks and nothing else (and the abbreviation test trims the sentence head), nothing else differs; tests/test_coding_passages_whitespace.py (sha256 31176e6f6c68f9c5618ac8cf3a4b756df8543e83c24e8a498606cc76fc9b8c44) shows the sealed script loses the entries of a body with an empty cell, the copy keeps them, both give the same units and passages for a body without one, and the copy differs in strip_marks only; suite on Modal 877 pass and 1 skipped; the first run's passages and citation folder are kept (superseded_passages_strip_marks, outputs/citations/superseded/) and the copy's replace them; only the counts of the first run's summary were read, no passage; no rule of the preceding entries changes; to be reviewed in round 15 before coding starts (planning/perplexity_paper1_final/)  results seen  ·070db5a4
2026-10-07  deviation, manual coding of dataset names, abstract fallback (prospective: made before any passage was read or any row coded): For a full-text paper yielding no_local_passage_found, apply the identical registered term-matching and passage-window rule to its stored abstract. If an abstract passage is found, supply that passage to the coder with source_read = abstract_fallback_after_fulltext_no_match. If neither source yields a passage, retain no_local_passage_found. No other widening is performed. Reason: the 47 rows concerned (all in full-text papers; of 872 queue rows in 434 papers) carry names extracted from the abstract, so the paper states the dataset where the body does not repeat the string, and without the rule open-access papers would be left unresolved more often than abstract-only ones; the rule applies to every such row, not to a list. In the registered twelve-column table the fallback source is written as abstract (scripts/manual_coding_table.py, sha256 69ac24eed6b864394694278a14b503ec6e8b01983cc2c304608b0353c989d62b, which supersedes scripts/manual_dataset_coding_reasons.py and also counts the unresolved rows by reason: release not identified, conflicting identifiers, no local passage found, dataset named but absent from the dictionary); tests/test_manual_coding_table.py (sha256 b4ec761c63c2ee99a37b5dfa6dd0ebad17fc662be502ddd576c6f099ac328154). Exposure as in the entries above: counts only; no passage read, no row coded, no coder started; reviewed in round 15 (planning/perplexity_paper1_final/)  results seen  ·5c4354fe
2026-10-07  change made on review, manual coding gates, reference identifier: scripts/manual_coding_gates.py (sha256 3aa4bbcd4df6f2a180d5b88e038cafc67e5a7f22d29ba3d78f8fa54cd7ae5e39) supersedes scripts/coding_gates.py, which stays sealed and unused; a companion_source row's reference entry is verified against the coded dictionary row's source_identifier by its DOI, else (no_doi) by its PMID, else by its PMC identifier; an identifier that is not the dictionary row's fails, and an entry with none of the three (no_stable_identifier) fails, so the companion source cannot establish the release and the row is unresolved, with no exception; the gate also checks a quote against the document and claims file of its own passage (body, abstract, or abstract fallback); the coder instructions say the same (prompts/manual_coding_coder_instructions_v2.md, sha256 79f58e4d168fed386cb55192b8e9a98ff23a993cc35e252b481eaff326379cec; the first instruction file stays sealed and unused); tests/test_manual_coding_gates.py (sha256 c3a64db6b8fbb3437b18417f785f65f41371693a2570f483543aaf973c8a6e55); no passage read, no row coded, no coder started; reviewed in round 15 (planning/perplexity_paper1_final/)  results seen  ·9e8b65a5
2026-10-07  change made on review, manual coding, one generator for the run: scripts/manual_coding_passages.py (sha256 bd83efd7c03f0e1d524bbc7ed6e0373c24832d1a82e00ea4a03f95a2d55539d7) is the passage generator of the run; it holds the correction of scripts/coding_passages_whitespace.py (citation marks removed without touching white space), the abstract fallback of the entry above, and the PMC identifier of a reference entry, and it names its document and claims file on every passage; scripts/coding_passages.py and scripts/coding_passages_whitespace.py stay sealed and are superseded; the output of the first run (61 papers without reference entries) and of the second run (before the fallback) are kept under superseded folders, as are the coder inputs made from the second; scripts/manual_coding_manifest.py (sha256 0a4ef1f48df4dd32f32de746f4713424d09c1282efca5a8ee4ecbc894844b279) writes the run manifest (queue, dictionary, scripts, abstract and full-text inputs, passages, assignment and seed, coder instructions, by sha256) before coding starts; the assignment script and seed are unchanged (scripts/coding_assignment.py, seed 20261007); tests/test_manual_coding_passages.py (sha256 49f4e15de803117e252a0394836bf5d585bffcf4378644a5ad168e350bef45cd) and tests/test_manual_coding_manifest.py (sha256 b96fb221d9f8d97bb066431192bfd909477a1201d9b9305f2145224b9a69e16b); suite on Modal 903 pass and 1 skipped; no coder was started and none opened a passage: the coders' folders hold no attempt or gate file and no claims file holds a quotation; reviewed in round 15 (planning/perplexity_paper1_final/)  results seen  ·f8038896
2026-10-07  completion of the round 15 reference-identifier hierarchy: identifiers read from link elements and entry text as well as pub-id tags; decided from counts of entries by identifier source, no passage read, no row coded. The run of scripts/manual_coding_passages.py showed that of 992 reference entries attached to passages 440 had a DOI in a pub-id tag, 1 a PMID only and 551 no tagged identifier, 328 of those printing a DOI in the entry text (in the stored XML 7,057 of 13,317 reference entries have no pub-id tag and hold a link element); the hierarchy of the entry above says a reference entry with a DOI is verified by it, and a DOI in the entry's link or text is the entry having a DOI. scripts/manual_coding_passages_v2.py (sha256 ac87aa18ae153c4d06b8630e182ffe484925b2c21aa4eb7ff3281417aea0eed8) is now the generator of the run and supersedes scripts/manual_coding_passages.py, which stays sealed and unused: an entry's DOI is taken from, in order, its pub-id tag, a link element whose target or text holds a DOI, and a DOI printed in the entry text, with one pattern (10.<registrant>/<suffix>), normalized by lower-casing, dropping a resolver prefix and stripping trailing punctuation and closing brackets; the source of the DOI is recorded on the entry; different DOIs in one entry make it conflicting and it carries no identifier; a PMID is taken the same way from its tag, a PubMed link or PMID: n in the text; nothing else in the generator changes (tests/test_manual_coding_passages_v2.py, sha256 26306c8b68d480b2e7dbaa543ffe24fe4842b3883f04be3085a96244b0ff8ea4; suite on Modal 928 passed, 1 skipped). The error direction is conservative: a wrongly read DOI can only fail the comparison with the dictionary row's DOI and leave a row unresolved. The gate, the table script, the assignment and the coder instructions are unchanged; the output of the superseded generator and the coder inputs made from it are kept under superseded folders; no coder was started (0 attempt files, 0 gate files, no claims file holds a quotation); decided by the coordinator on the round 15 review (planning/perplexity_paper1_final/)  results seen  ·87c8127c
2026-10-07  completion of the round 15 reference-identifier hierarchy, correction of the DOI pattern (decided from counts, no passage read, no row coded): the run of scripts/manual_coding_passages_v2.py gave, of 992 reference entries attached to passages, 440 with a DOI from a pub-id tag, 137 from a link, 2 from the text, 1 with a PMID only, 26 with none and 386 conflicting; counts over the conflicting entries showed that in 385 every DOI read began with the shortest one and went on with an ampersand: the entry holds a look-up link whose address carries the DOI followed by further query fields, and the pattern ran on into them, so one DOI read as two. scripts/manual_coding_passages_v3.py (sha256 1502821b666e49329aa7d7bccaadbb61dc0b71b73058775b372f201471a2510f) is now the generator of the run and supersedes scripts/manual_coding_passages_v2.py, which stays sealed and unused: the suffix of the one DOI pattern ends at white space, a quote, an angle bracket or an ampersand, and nothing else differs (tests/test_manual_coding_passages_v3.py, sha256 bc6f5499f5474e86931b9869aa1618f267eafbe53e7ba1350a7b8a0a897f5c96; suite on Modal 938 passed, 1 skipped). Two different DOIs in one entry are still conflicting. The error direction stays conservative: a DOI read wrongly, or one cut at an ampersand it really holds, can only fail the comparison with the dictionary row's DOI and leave a row unresolved. The gate, the table script, the assignment and the coder instructions are unchanged; the superseded generator's output and the coder inputs made from it are kept under superseded folders; no coder was started (0 attempt files, 0 gate files, no claims file holds a quotation); under the coordinator's decision on the round 15 review (planning/perplexity_paper1_final/)  results seen  ·07a1a21f
2026-10-07  departures from the sealed coder instructions in the first check of the manual dataset coding (four Claude Code coding agents, attempt 1 of 434 papers, 872 rows), logged before any machine gate ran and before any gate result or code was seen by the coordinator: (a) shared scratch folder (a set-up error of the coordinating session: the four coders shared one session scratch folder, though told not to communicate): coder_1 ran another coder's helper by mistake (it failed, wrote nothing, and showed that coder's input path) and then saw six lines of another coder's pin log (claims-file names, claim ids and the opening words of four pinned sentences from three papers not its own); coder_3 saw one such line; coder_2's viewer was overwritten once and failed before reading anything, and the pins and outputs of its first two papers went through a same-named file in the shared folder; no coder reports having seen another coder's coded value; (b) helper scripts: each coder used two small helpers of its own (a viewer of its input files and a pin-then-write helper) though told to run no other script; (c) clipped reading: coders 3 and 4, and coder 2 for result-table rows after the third per table from its 41st paper on, read a condensed view (context sentences that matched no term truncated, repeated table rows collapsed; coder 3 also hid administrative sections and some later passages), so a row left unresolved may have had its identifying sentence in a part not shown; (d) coder_4 named its 108 files <id>.json.attempt1.json, which the gate does not read: they are renamed to <id>.attempt1.json as a recorded mechanical step, bytes unchanged (sha256 of each file before and after in outputs/manual_coding/2026-10-03/coder_4_rename_attempt1.json); (e) four rows were left unresolved because citations pin refused a sentence that occurs twice in its source (coder_1 36864689 outcome_3, coder_2 41165052 outcome_1, coder_3 40269081 outcome_1 and 42677314 pqtl_1). Checked before the gates (outputs/manual_coding/2026-10-03/check1_integrity_attempt1.json): every attempt file matches its input in record, coder, row count, side, name and order; every quote is a sentence of a passage of its row; every coded value is a dictionary row of the row's side; every pin named exists in the claims file of its passage and no claims file holds a pin no row names; no paper is coded by two coders; 0 files with a problem, the first two papers of coder_1 and coder_2 included. Read for this: the counts of rows by value kind (195 coded to a dictionary row, 518 release_not_identified, 9 conflicting_identifiers, 150 source_names_dataset_absent_from_dictionary) and file names; no coded value, quote or passage was read. Answer to (c) and (e): the screen of the next entry; a paper it marks, or that fails a gate, is reread by its own coder with every passage shown in full and written as attempt 2, earlier attempts kept  results seen  ·1ea59348
2026-10-07  added quality-control gate, manual dataset coding, missed-identifier screen (logged and sealed before it runs and before any gate result is seen; it replaces none of the three registered checks): scripts/manual_coding_missed_identifier_screen.py (sha256 5bed003b7cc20c7abecdceb565a591b8f42622b59848221b03342645ccc40d89; tests/test_manual_coding_missed_identifier_screen.py, sha256 ceca10c3619095ea4d2e789e1ce727e0d61d45c01c6035384cba80cd5156df3e; suite on Modal 943 passed, 1 skipped) searches, for every row whose value is not_stated_in_source with the reason release_not_identified, the full text of that row's passages and their attached reference entries with the functions of the sealed gate for what would let a code pass the gate: an identifier of one dictionary row of the row's side that no other candidate has, that row's exact sample size with its platform or a year, or a reference entry verified against that row by DOI, PMID or PMC identifier; a hit codes nothing and only marks the paper for rereading by its own coder; the four refused-pin rows are marked too; the coder is given the marked rows by side and name with the reason and not the dictionary row a hit names; if more than a quarter of the screened rows are hit, the clipping is taken to have mattered broadly and a full unclipped reread of every unresolved row is proposed instead  results seen  ·787a84ad
2026-10-07  manual dataset coding, first check, results of the machine gates and of the missed-identifier screen on attempt 1, and the reread decided from them (logged before any attempt 2 file is read): integrity check, 434 papers and 872 rows, 0 files with a problem; gates (scripts/manual_coding_gates.py; citations verify --strict exit 0): 409 of 434 papers pass and 25 fail, one row each (coder_1 8, coder_2 4, coder_3 8, coder_4 5), all 25 for no identifier of the coded row in the pinned material, none for a pin or a reference identifier; 6 coded rows carry the warning that the value is outside the candidate set; screen (scripts/manual_coding_missed_identifier_screen.py): 240 of the 518 release_not_identified rows hit, in 167 papers (coder_1 59 of 133, coder_2 53 of 120, coder_3 69 of 136, coder_4 59 of 129), 101 of the hits naming a dictionary row within the row's own candidate set (55 one candidate, 46 several) and 139 only a row outside it; the 4 refused-pin rows marked. 240 of 518 is above the quarter of the preceding entry, so every paper with a release_not_identified row or a gate failure is reread by its own coder with every passage shown in full: 339 papers (coder_1 88, coder_2 78, coder_3 85, coder_4 88; outputs/manual_coding/2026-10-03/reread_lists_attempt2/). Caveat: the coder who read unclipped (coder_1) has the same hit rate (44 percent; 17 percent within the candidate set, against 16, 23 and 22 percent for coders 2, 3 and 4), so the rate reflects the breadth of the screen at least as much as the clipping; the full reread was chosen under the logged rule all the same. For the reread each coder has a private scratch folder and uses no script (reading, citations pin and writing only); every row of a reread paper is decided again and written as attempt 2, attempt 1 files and pins kept; attempt 2 pins take claim ids ending in _a2 (a convention added here: the sealed instructions do not name attempt 2 pins). No coded value, quote or passage was read for this entry: counts and file names only  results seen  ·2d3efcd7
2026-10-07  departures in the attempt 2 reread of the first check of the manual dataset coding (339 papers: coder_1 88, coder_2 78, coder_3 85, coder_4 88), logged before the machine gates ran on any attempt 2 file: (a) sessions: coder_1's original session did all its rereads; the original sessions of coder_2, coder_3 and coder_4 ran out of context after 17, 58 and 12 papers, and each was continued by two fresh sessions under the same coder id, the same sealed instructions and fixed non-overlapping shares of the list, so the same coder means the same coder role and instructions, not one session; (b) a standing ruling given to the continuation sessions, consistent with what coders 1 and 4 did in attempt 1: a sample size alone, including exact case and control counts, with no platform, panel, year, citation or accession, is unresolved; (c) slips of blindness and procedure reported: one coder_4 session opened one input file of the other coder_4 session's share (same coder role; no pin made, no file written); a gate file shows a paper's attempt 1 values, so several sessions saw their own role's earlier values for gate-failed papers, and coder_4's first session also opened its own attempt 1 file for one paper; some sessions pinned through a shell loop, ran grep, wc or ls on their own inputs, or worked out of list order; coder_1 typed quotations by hand; coder_1 named reference pins <side>_<k>_ref_a2 and the others <side>_<k>_a2_ref (10 and 32 pins; both forms are accepted, the gate reads the claim id the row names); (d) coder_3 kept its attempt 1 code for the second row of 42323475 though its gate had failed, judging the failure a white-space mismatch between the release identifier in the sentence and the dictionary alias. Checked before the gates (outputs/manual_coding/2026-10-03/check1_integrity_attempt2.json): every paper on a reread list has an attempt 2 file with every row, none off the lists has one; every attempt file matches its input in record, coder, row count, side, name and order; every quote is a sentence of the passage named; every value is a dictionary row of the row's side or an unresolved value; every pin named exists in the claims file of its passage, and no claims file holds a pin no row names; no paper is coded by two coder roles; 0 files with a problem. The final value of a row is that of the paper's highest attempt. No coded value, quote or passage was read for this entry: file names and counts only  results seen  ·69f19e68
2026-10-07  manual dataset coding, first check, results on attempt 2 (339 papers reread in full) and the state of the check: integrity, 0 files with a problem; gates on the 339 attempt 2 files (citations verify --strict exit 0): 328 pass and 11 fail on 12 rows (coder_1 0, coder_2 1 paper and row, coder_3 4, coder_4 6 papers and 7 rows), all for no identifier of the coded row in the pinned material; screen on the last attempt of each paper, for the record only: 242 of 523 release_not_identified rows hit in 173 papers (240 of 518 before the full reread), which shows the hit rate to be the breadth of the screen and not a sign of missed reading; no further reread follows from it. State from the highest attempt per paper (872 rows): 185 coded to a dictionary row (70 by release identifier, 69 by reference entry with every entry verified by DOI, 33 by exact N with platform or year, 7 by unique citation, 6 by source identifier; 167 from full text, 16 from the abstract, 2 from the abstract fallback; 6 outside the candidate set), 523 release_not_identified, 9 conflicting_identifiers, 155 source_names_dataset_absent_from_dictionary. Between attempts, in the reread papers: 16 rows went from coded to release_not_identified, 6 from release_not_identified to coded, 6 from release_not_identified to absent from the dictionary, 1 the other way, 707 kept their value. 12 coded rows in 11 papers still fail a gate; under the sealed instructions a row that cannot pass is unresolved, and how that is applied is not yet decided. Read for this entry: counts, file names, and the coder notes of the 50 rows that mention adjudication, a flag or a judgment, to group the recurring questions (outputs/manual_coding/2026-10-03/check1_question_types_attempt2.json); no quote or passage was read  results seen  ·ae9499b1
2026-10-07  manual dataset coding, clarifications of the identification rule of the entry of 2026-10-07 (round 14), settled on review of the questions the first check raised and adopted before any attempt 3 file is written: A, a release written with other spacing, case, hyphen or underscore, as an ordinal for a cardinal, or with one of the words R, round, release, version, freeze or data freeze and the same number, modifying the dataset name and with no conflicting identifier, is that release; latest release and the like are not identifiers; B, a valid repository accession with no dictionary row is source_names_dataset_absent_from_dictionary; C, the authors' own GWAS of individual-level biobank data is absent from the dictionary when the passage defines the analysis (source with phenotype definition, application, analytic sample or described procedure), and biobank data with only a post-exclusion N is release_not_identified; D, a cohort or consortium name alone never identifies a release, even with one dictionary row for it; E, a citation verified by DOI, PMID or PMC identifier whose source has several dictionary rows, with an attribute of the same analysis dataset (ancestry, subcohort, panel, platform, exact release-specific N) matching exactly one of them and no conflict, is coded, companion_source; F, attribution may cross adjacent sentences that form one dataset description, and a grouped citation after several cohorts maps to none unless order or wording makes the mapping explicit; G, an accession absent from the dictionary stays absent even when its counts equal a listed row's; H, a second N is a conflict only when it purports to be the release-defining N of the source GWAS and exactly identifies another release (post-QC, complete-case, ancestry-subset, effective, protein-specific, variant-specific, maximum and post-exclusion N are not conflicts); I1, exact counts with a cohort name alone are release_not_identified (unchanged); I2, a sentence given under another row of the same paper may be used when it explicitly refers to this row's dataset, the passage used being recorded, and not because two rows share a generic name; I3, an accession inside a row's registered range with incompatible ancestry or counts is conflicting_identifiers, after classifying the discrepant number under H; I4, a sentence occurring twice does not make the release unidentified. For the second check: candidate rows are retrieval suggestions, not an exhaustive allowed set, and a reviewer may select any exact row of the dictionary that the supplied source evidence identifies. Coder instructions: prompts/manual_coding_coder_instructions_v3.md (sha256 39133ec515105ec0c2d805ab55d777f3291499b27350c422f1b5dac0746a2ec4; the second version stays sealed and superseded). Gate: scripts/manual_coding_gates_v2.py (sha256 8d13ed86dcede9579624bdac513abd817c3b93cb48c383037b8bb7665d992026; tests/test_manual_coding_gates_v2.py, sha256 29c56cf23a73713a9178cbfa4a71b27ebf6237a31431a3c92f48fe37fb7f7e9f; suite on Modal 971 passed, 1 skipped) accepts everything scripts/manual_coding_gates.py accepts and, where that finds no identifier, a numbered release written in another form attached to the dataset name (rule A; a different number, a number attached to another name and latest release are refused), and for a companion row whose verified source has several dictionary rows a separating attribute in the pinned sentence (rule E); it accepts a sentence of a passage given for another row of the same paper when the coder names it (rule I2), and writes for the coder a gate file without coded values. Read for this entry: counts, file names and the 50 coder notes of the preceding entry; no registry, relation or aggregate was opened; reviewed (planning/perplexity_paper1_final/25_REVIEW_check2_rules.md)  results seen  ·2b9a8527
2026-10-07  manual dataset coding, proposals of the same review that are declined, each with its reason: a reported dataset family, a reported participant source and new resolution states are not added, because the registered set-valued mapping already keeps this: a row left not_stated_in_source or absent from the dictionary has no manual code, the registered code replaces a name only when a code exists (scripts/build_registry.py lines 241 to 245; scripts/manual_dataset_coding.py lines 158 to 165 skip an unresolved row), so the name as written keeps its automatic mapping state and candidate set and a release_ambiguous name keeps the components shared by every candidate; a side correction or a row-in-scope field is not added, because item 4 limits the manual coding to dataset and platform identity and the side comes from the registered extraction; no dictionary column or row is added, because the dictionary is frozen for this study and rows naming a dataset absent from it are reported as their own category; conflicts and absences are not adjudicated by hand one by one, because item 5 already fixes what follows a disagreement. Also recorded: all 23 batch files of the second-check packet were uploaded with the rules request, not the request alone; the batches hold no coded value; the review returned ten sample adjudications, which are filed with it and are not second-check answers; the second check runs on every one of the 872 rows under the settled rules  results seen  ·f9c748c7
2026-10-07  manual dataset coding, how the first check is run, rule I4 of the settled rules (a sentence occurring twice does not make the release unidentified), logged before any attempt 3 file is written: citations pin refuses a sentence that occurs several times in its source and takes no option naming the occurrence, though its record format has prefix and suffix fields for it; scripts/pin_passage_occurrence.py (sha256 43f01bddf5a4f500744d6a1ce74888063b0d9712a76b81ee4bc87903dcc719dd; tests/test_pin_passage_occurrence.py, sha256 b1fd24130792dbbc7f31db2a24ff6f7e72ac75f0a8a7a8f6e429abd12530c9bc; suite on Modal 978 passed, 1 skipped; tried end to end with the tool on a synthetic source) pins a sentence named by input file, row, passage and sentence number with citations pin, and when the tool refuses it as ambiguous writes the quotation into the passage's claims file with the whole sentence before and the whole sentence after it in the passage as prefix and suffix, after citations verify --strict has confirmed on a copy that they single out one occurrence; otherwise it raises and writes nothing; no coder edits a claims file by hand and no unresolved reason is added; the gate scripts/manual_coding_gates_v2.py reads such a pin unchanged; coder instructions prompts/manual_coding_coder_instructions_v4.md (sha256 e3ccd838b2fe579ea8fc943fbf3286e9de6936a1bc5d9954d5aadf3ee810c572) are the third version with the helper call in place of the interim note marker, and the third version stays sealed and superseded. Attempt 3 covers the 281 papers flagged by a settled rule or a failing gate (coder_1 79, coder_2 68, coder_3 61, coder_4 73; outputs/manual_coding/2026-10-03/reread_lists_attempt3/), not narrowed, in fixed shares of at most 12 papers, each share one fresh session under its coder role. No coded value, quote or passage was read for this entry  results seen  ·e518be64
2026-10-07  manual dataset coding, first check, the attempt 3 run, logged before the machine gates ran on any of its files: 281 papers in 26 fixed shares of at most 12 papers (coder_1 7 shares and 79 papers, coder_2 6 and 68, coder_3 6 and 61, coder_4 7 and 73), each share one fresh session under its coder role with the fourth coder instructions and the settled rules; 269 papers written as attempt 3 and 12, not reread before, as attempt 2. Departures the sessions declared: every pin command run after a change of directory into the pins folder; several pins chained in one command; a sentence held in a shell variable to pin it under several claim ids (coder_1 share 03, coder_3 shares 02 and 04); the helper's error output cut with tail (coder_3 shares 02 and 03); the helper run again on another passage after it raised. Misnamed files: coder_2 share 04 wrote its 12 papers only as <id>.json.attempt3.json, which the gate does not read; each was copied to <id>.attempt3.json with bytes unchanged; coder_3 share 03 wrote its 12 papers under both names with identical bytes; the 24 misnamed files are moved to codes_misnamed and nothing is deleted (sha256 before and after in outputs/manual_coding/2026-10-03/attempt3_misnamed_files.json). The occurrence helper raised for sentences duplicated together with their neighbours or standing alone in their passage, by the sessions' reports in seven rows (coder_1 36864689 outcome_3 and 39333727 outcome_1; coder_2 40328427 outcome_1; coder_3 40269081 outcome_1, 42677314 pqtl_1, 39119976 outcome_1 and 41249132 outcome_2); no pin in the new attempt files carries a prefix or suffix, and two reference pins that no row names were left (36864689 outcome_3_a3_ref, 42677314 pqtl_1_a3_ref). Checked before the gates (outputs/manual_coding/2026-10-03/check1_integrity_attempt3.json): each of the 281 papers has exactly one new attempt file with the attempt number its share gave and every row; every attempt file matches its input in record, coder, row count, side, name and order; every quote is a sentence of the passage named (8 rows name a passage given for another row of the paper, rule I2); every pin named exists in the claims file of its passage; no paper is coded by two coder roles; 0 files with a problem. No coded value, quote or passage was read for this entry  results seen  ·ddf59cfa
2026-10-07  manual dataset coding, first check, results of attempt 3 and the correction of the occurrence helper: gate (scripts/manual_coding_gates_v2.py; citations verify --strict exit 0) on the 281 new attempt files: 267 pass and 14 fail, one coded row each (coder_1 7, coder_2 3, coder_4 4), all for no identifier of the coded row in the pinned material. State from the highest attempt per paper (872 rows): 207 coded to a dictionary row (98 by reference entry, every entry verified by DOI; 66 by release identifier; 26 by exact N with platform or year; 10 by source identifier; 7 by unique citation; 187 from full text, 18 from the abstract, 2 from the abstract fallback; 7 outside the candidate set; 6 from a passage given for another row of the paper), 471 release_not_identified, 12 conflicting_identifiers, 182 source_names_dataset_absent_from_dictionary, 0 without a passage. In the 281 papers against the attempt before: 536 rows unchanged; 29 from release_not_identified and 2 from conflicting to coded; 4 from coded to release_not_identified, 4 to absent and 1 to conflicting; 38 from release_not_identified to absent and 15 the other way; 4 from release_not_identified to conflicting. Helper: scripts/pin_passage_occurrence.py raised wherever the sentences either side were duplicated too or the sentence stood alone; scripts/pin_passage_occurrence_v2.py (sha256 dc39e5bce7579b172b0b94ea322c213340227eaf50fcee97316317e77ba0ee01; tests/test_pin_passage_occurrence_v2.py, sha256 eea65f5e0b730acdc4f9d133e9e498e2d777fbdb6ec24eb330a86c57bb1eb60c; suite on Modal 984 passed, 1 skipped) writes the same record where the first helper pins and otherwise takes as prefix and suffix the source text before and after the passage's own occurrence, 80 characters each way and doubling, until citations verify --strict confirms one occurrence on a copy; tried with the tool on copies only, it pinned every duplicated sentence of the passages concerned (36864689 outcome_3, 39333727 outcome_1, 40269081 outcome_1 and 42677314 pqtl_1: 22 sentences; and the 11 duplicated sentences in the passages of the other row of 39119976 and of 41249132), where the first helper raised on each; no pin was written into a real claims file. The tool has no way to name an occurrence by number; the text before an occurrence back to the start of the document always names it, which is what the helper falls back on. Coder instructions prompts/manual_coding_coder_instructions_v5.md (sha256 0397b5bcc834f837b356a2f2ed0cd03acf78726c1314e0fdf36cc23a9407b94a) are the fourth version with the second helper named; the fourth stays sealed and superseded. Read for this entry: counts, file names, identifier strings matched by pattern in notes and quotes for a consistency listing; no registry, relation or aggregate was opened  results seen  ·5ce8ff25
2026-10-07  manual dataset coding, how rules B, C, D, G and I3 of the settled rules are applied (five clarifications decided by the coordinating session and the author from the round 14 ruling and the review of the rule questions; they are a reading of those rulings, not a new ruling of the reviewer), logged before any attempt 4 file is written: C1 (rule C), the authors' own analysis of a cohort's or biobank's individual-level data, a GWAS or any other analysis, is absent from the dictionary when the passage defines it by more than a number of participants (a phenotype definition, an application number, or a described measurement or analysis procedure), and a cohort or biobank name with only a number of participants (analytic, post-exclusion or replication N) is release_not_identified; this corrects the narrower wording of the entry above, which spoke of the authors' own GWAS only; C2 (round 14, question 3), a named cohort, consortium or study for which the row's side of the dictionary has no row under any release, including a dataset whose only rows are on the other side, is absent from the dictionary, and a repository or portal name alone is not a dataset and is release_not_identified unless an accession or citation follows; C3 (rule B), an identifier of a whole deposit that covers several dictionary rows of the named dataset picks none of them and is release_not_identified, never grounds for a code and never absent; C4 (rules B and I3), an accession whose prefix or range a dictionary row lists is that row when nothing conflicts, is conflicting_identifiers with an ancestry or counts the row does not allow, and is absent when no row lists it by prefix, range or identifier; C5 (rules E and G), a sentence that attributes the dataset to a citation verified by identifier as the source of exactly one dictionary row (or one row after a separating attribute) is coded as companion_source even if it also gives an accession no row lists, and an unlisted accession with matching counts and no such citation stays absent. Order of decision for a row: conflict, then a code, then absent, then release_not_identified. Why now: after attempt 3 the same identifier was treated differently in different papers (a whole-deposit identifier coded, absent and unresolved in three papers; accessions of two listed ranges and of five prefixes coded, absent or conflicting), 14 coded rows fail the gate, and 6 papers hold a sentence the first occurrence helper could not pin. Coder instructions prompts/manual_coding_coder_instructions_v6.md (sha256 7990a8b8611a189d8c340bbc2b07cec1c32bea12479fce44e0e6e77e21a802f2; the fifth version with C1 to C5 and the order; the fifth stays sealed and superseded); the gate scripts/manual_coding_gates_v2.py is unchanged and passes a companion row whose sentence also holds an unlisted accession. Attempt 4 rereads whole 203 papers (coder_1 56, coder_2 41, coder_3 52, coder_4 54) in 19 fixed shares of at most 12, each flagged mechanically by one of: a refused pin (6 papers), a gate-failing coded row (14), the whole-deposit identifier or a listed accession class or range, a note citing rule C or an application number or own analysis, a release_not_identified row that is unmatched or whose name matches only the other side's rows, or an absent row whose passages carry a reference entry verified as a dictionary source (outputs/manual_coding/2026-10-03/reread_lists_attempt4/). No coded value was changed or read for this entry beyond the consistency listing of the preceding entry  results seen  ·177ba314
2026-10-07  manual dataset coding, first check, the attempt 4 run, logged before the machine gates ran on any of its files: 203 papers in 19 fixed shares of at most 12 (coder_1 5 shares and 56 papers, coder_2 4 and 41, coder_3 5 and 52, coder_4 5 and 54), each share one fresh session under its coder role with the sixth coder instructions; 163 papers written as attempt 4, 30 as attempt 3 and 10 as attempt 2, each under the file name its list gave, none misnamed. Departures the sessions declared: a shell loop around the pin command (coder_2 shares 01 and 03, coder_1 share 02); the next input opened before the previous paper's file was written, nothing decided before the write (coder_2 share 02, coder_1 share 02); pins chained in one command; a change of directory before the pin command; an echo of the exit status; two sentences pinned with the helper without first trying citations pin (coder_3 share 03). The second occurrence helper pinned the duplicated sentences of 36864689, 39333727, 40269081, 42677314 and 41249132 (6 pins of the new attempt files carry a prefix or suffix); 39119976 needed no helper. Checked before the gates (outputs/manual_coding/2026-10-03/check1_integrity_attempt4.json): each of the 203 papers has exactly one new attempt file under its listed name with every row; every attempt file matches its input in record, coder, row count, side, name and order; every quote is a sentence of the passage named (7 rows name a passage given for another row of the paper); every pin named exists in the claims file of its passage; the two reference pins no row names are those left by attempt 3; no paper is coded by two coder roles; 0 files with a problem. No coded value, quote or passage was read for this entry  results seen  ·0926074a
2026-10-07  manual dataset coding, first check, results of attempt 4 and the state in which the first check closes: gate (scripts/manual_coding_gates_v2.py; citations verify --strict exit 0) on the 203 new attempt files: 196 pass and 7 fail, one coded row each (coder_1 39333727 pqtl_1, 40052860 outcome_2, 40564116 outcome_1, 41222800 pqtl_1 and 42365225 outcome_3; coder_3 40877285 pqtl_1; coder_4 40462010 pqtl_2), all for no identifier of the coded row in the pinned material; under the sealed instructions a row that cannot pass is unresolved, they are not sent back again, and how the table step applies that is not yet decided (the sealed scripts/manual_coding_table.py takes the last attempt's value whatever its gate result, lines 128 to 176). State from the highest attempt per paper (872 rows): 204 coded to a dictionary row (103 by reference entry, every entry verified by DOI; 64 by release identifier; 22 by exact N with platform or year; 11 by source identifier; 4 by unique citation; 187 from full text, 15 from the abstract, 2 from the abstract fallback; 7 outside the candidate set; 7 from a passage given for another row), 441 release_not_identified, 15 conflicting_identifiers, 212 source_names_dataset_absent_from_dictionary, 0 without a passage. In the 203 papers against the attempt before: 404 rows unchanged; 41 from release_not_identified to absent and 6 the other way; 11 from coded to release_not_identified; 4 from release_not_identified and 4 from absent to coded; 2 from release_not_identified and 1 from absent to conflicting. Identifier strings still given different values in different papers after this pass (listing by pattern over notes and quotes, outputs/manual_coding/2026-10-03/check1_final_state_attempt4.json): the whole-deposit identifier syn51364943 (unresolved in five papers, coded in one, conflicting in one), accessions of the range GCST90018563 to GCST90019002 that one dictionary row lists (absent, conflicting or coded), and of the range GCST90274758 to GCST90274848 that no row lists (absent in one paper, coded in another); these are left as coded and go to the second check. Read for this entry: counts, file names and the pattern listing; no registry, relation or aggregate was opened  results seen  ·5e4a092e
2026-10-07  manual dataset coding, the second check (item 5): pilot, checker and how it is run, logged before any second-check answer is compared with a code. Pilot: the ten rows of batch 23 were run in the Perplexity web interface under four configurations the author selected (Deep Research, Fable 5.1 Thinking, Astra GPT-6 Thinking, Kimi K3 Thinking) with the first check-2 prompt, which allowed reading the paper; Astra retrieved full texts and Kimi tried to and failed; Kimi and Astra were rerun with a closed-packet prompt and stayed in the packet, and Fable was rerun with it; none of these answers is a second-check answer. Checker: the author chose Fable 5.1 Thinking, a model of the same family as the first-check coders, which the paper states; the outputs give the model as Perplexity, so the model is recorded on the author's statement. The second check is closed-packet: the checker is given the prompt, the dictionary definitions and one batch and is told to use nothing else; the interface has no switch that turns web search off, so compliance is checked on every answer file (the closing line external sources used: none, and footnotes naming the attached files only), and a batch showing any other source is rerun. This departs from item 5, which gives the checker the paper reference, only in that the checker is told not to fetch the paper: the registered source is the Europe PMC open-access full text, else the abstract, and a publisher copy fetched by the checker lies outside it, as the pilot showed. Prompt planning/perplexity_paper1_check2_upload/01_PROMPT_check2_v4_closed_packet.md (sha256 a70c9fd62884a967ad511cb6a9fb8a50617c977d0d93126943d58ded21762c68; settled rules A to I4, C2 to C5 and the decision order in the coders' words); the 23 batches are unchanged and cover all 872 rows. The first answer under this prompt is batch 23 (planning/perplexity_paper1_check2_answers/batch_23_fable_prompt_v4.md, 10 rows), which counts. Answers are read by scripts/manual_coding_check2_ingest.py (sha256 c0933479e02892a931c5af88f46f8902620242d97ec331b2a07ee041d3e3d75e; tests/test_manual_coding_check2_ingest.py, sha256 8d97de39af1044108ff632f3d8647e6bd0f3df97299811bca755d62b789ae2b6; suite on Modal 1006 passed, 1 skipped): per file, every row of the batch once and in order, an allowed answer of the row's side, a quotation that is a whole supplied sentence of the row or of another row of the paper, the closing line and the footnotes; a failing batch is rerun, never repaired by hand; the answers are then classed against the first check's final value (same dictionary row; unresolved with the same or another category; both unresolved with different values; disagree) and agreement is reported as a count; a disagreement is resolved by rereading the source with both original answers kept. Files under planning/ are not committed  results seen  ·04d37d2f
2026-10-07  manual dataset coding, how the sealed instruction that a row which cannot pass the machine gates is unresolved, not forced, is carried out, logged before the table of codes is built: scripts/manual_coding_table_v2.py (sha256 7b92b6f95621d8d4976264c036ad9d1f792a87a8c7b3b2cab438196a8cbca754; tests/test_manual_coding_table_v2.py, sha256 bed61362ca3ab04a09d7fe3dc9032f42ac9054186ce073594c4cfe010c33057a; suite on Modal 1011 passed, 1 skipped) supersedes scripts/manual_coding_table.py, which took the last attempt's value whatever its gate result; when it collects the coders' last attempts it reads the gate result of that attempt (scripts/manual_coding_gates_v2.py) and writes a row coded to a dictionary row that fails a gate as not_stated_in_source with the reason release_not_identified, keeping the coder's value and the gate's failures in two further columns of the extended table (coder_value_before_gate, gate_failures); every other row is written exactly as the superseded script writes it, and a paper whose last attempt has no gate file is refused. The rows concerned after attempt 4, none of which is sent back to a coder: coder_1 39333727 pqtl_1, 40052860 outcome_2, 40564116 outcome_1, 41222800 pqtl_1 and 42365225 outcome_3; coder_3 40877285 pqtl_1; coder_4 40462010 pqtl_2 (7 rows, each failing for no identifier of the coded row in the pinned material), so the first check stands at 197 rows coded, 448 release_not_identified, 15 conflicting_identifiers and 212 absent from the dictionary. The script also fills the checker's value into the table from the counted second-check answers. No further coder pass is made; identifier strings treated differently in different papers stay as coded and are left to the second check and the reread of disagreements. No coded value was read or changed for this entry  results seen  ·9e561037
2026-10-07  manual dataset coding, second check, correction of the answer ingest before any agreement is reported: run on the 23 answer files, scripts/manual_coding_check2_ingest.py passed 4 batches and failed 19, every failure being a quotation not found among the supplied sentences (121 rows) and none a missing row, a disallowed answer, a missing closing line or a foreign footnote; character counts over the failing quotations showed the cause for 111 of them: the interface's export rewrites a bracketed citation number inside a quoted sentence as a footnote mark ([14] becomes [^1_14]), and a few more carry a backslash escape or an HTML entity, so sentences quoted whole were refused. scripts/manual_coding_check2_ingest_v2.py (sha256 7b208509455f6bef70ed4b39ccfe8f322504bf987068ea57a53e217e34af76bd; tests/test_manual_coding_check2_ingest_v2.py, sha256 b19b5bc9b5a84f2376f96eb18a6499458e71f300c06c266b3f1526f64b091a20; suite on Modal 1037 passed, 1 skipped) compares a quotation as written and, where that finds no supplied sentence, with those export marks undone, and records which was needed; a fragment, an altered sentence or a changed citation number still fails; nothing else in the checks differs and files the first version passes are read the same. It also classes each row a second time under the gate rule of scripts/manual_coding_table_v2.py, splits disagreements by kind, and writes the rows whose two values differ for the reread. Seen before this entry, from the first version's run: the pass or fail of each batch, the counts of failing checks, and the agreement classes of the 130 rows of the four passing batches (5 on the same dictionary row, 114 unresolved with the same category, 7 unresolved with different values, 4 disagreements); no row value was read  results seen  ·2fa73b37
2026-10-07  manual dataset coding, the second check has run (logged before agreement over all rows is reported): 23 batches covering the 872 queue rows, one answer file per batch (planning/perplexity_paper1_check2_answers/batch_NN_fable_prompt_v4.md), each produced in the Perplexity web interface with the model Fable 5.1 Thinking on the author's statement (13 files give the model as Perplexity and 10 give no model line), closed-packet, with the prompt of sha256 a70c9fd62884a967ad511cb6a9fb8a50617c977d0d93126943d58ded21762c68, the dictionary definitions and one batch. Compliance, read by scripts/manual_coding_check2_ingest_v3.py (sha256 f99bad219b030194db3cccc8219ab922375c606eaece9c402d03da29dfed770b; tests/test_manual_coding_check2_ingest_v3.py, sha256 c2412e1402f706d66cd5cd4192b1ddd5ffc8c2bf32bab70724a018d71d3b218b; suite on Modal 1041 passed, 1 skipped; the third version also undoes an address the export writes as a markdown link, found in three quotations of one batch, and otherwise reads as the second): in all 23 files every row of the batch is answered once and in order, every answer is a dictionary row of the row's side or one of the two unresolved values, the closing line external sources used: none is present, and every footnote names an attached file; addresses occur only inside quoted sentences. 20 batches pass every check (722 rows); in 114 rows the quotation matched after the export's marks were undone and in 16 it is a sentence supplied under another row of the same paper. 3 batches fail and are rerun, not repaired: batch 08 (1 row), batch 11 (4 rows) and batch 13 (2 rows), each for a quotation that is a fragment of a sentence or an altered sentence and not a whole supplied sentence; their 117 rows have no counted answer yet. Seen before this entry: the agreement classes of four batches under the first ingest (logged above); no row value was read  results seen  ·21701f8f
2026-10-07  manual dataset coding, second check, correction of three counts in the preceding entry, which were written before the third ingest's output was read: the 20 batches that pass every check hold 755 rows, not 722; among them the quotation matched after the export's marks were undone in 92 rows and is a sentence supplied under another row of the same paper in 14 (over all 23 files the figures are 114 and 18); the three batches to rerun (08, 11 and 13; 1, 4 and 2 failing rows) hold 117 rows. Everything else in that entry stands. The counts are those of planning/perplexity_paper1_check2_ingest/run_04, the run of scripts/manual_coding_check2_ingest_v3.py  results seen  ·9d597d62
2026-10-07  manual dataset coding, how the reread of item 5 is carried out (a disagreement is resolved by rereading the source; the resolution and the two original answers are kept; a row that cannot be resolved stays unresolved), logged before any reread file is written: rows reread are those whose two values differ, the first check's value taken under the gate rule, including rows the two checks leave unresolved with different values; each paper is reread whole by its own coder role in a fresh session, in fixed shares of at most 12 papers, under the sixth coder instructions and prompts/manual_coding_reread_instructions.md (sha256 e02a6976866d49ff5db8a1e76fe42531696f4007db80d4e159646e56f3df07f5); the rereader is given the paper's passages as before and, for each row in disagreement, the two answers with their unresolved categories and quoted sentences, unlabeled: which check gave which is not said, and the order of the two is drawn per row with a seeded draw (seed 20261008) recorded in a manifest no rereader is given; the rereader reads every passage in full, decides the row under the rules (either answer or neither), pins the sentence under a claim id ending in _r, and writes one resolution file per paper; scripts/manual_coding_reread.py (sha256 78797b051199843bbc37ce5ac812894775c6832c0cce7c38e52713e3e2369aea; tests/test_manual_coding_reread.py, sha256 bfebcde3f4f19157956a18209ffc550dafc567b8e7de3f16e76eb51819a24271; suite on Modal 1046 passed, 1 skipped) writes the disagreement files and shares, reads the resolution files, runs the machine gates of scripts/manual_coding_gates_v2.py on every resolved row, and writes a resolved row that fails a gate as unresolved, never sending it back; it then fills resolved_value and resolution_note of the extended table, leaving the two original answers untouched, and keeps both answers with their quotations beside the resolution in one file. Rule for several answer files of one batch in the second check: a file that fails a check is never counted and stays in the folder as failed and superseded; among files that pass, only the latest rerun counts (batches 08, 11 and 13 are being rerun with the same prompt and files). Model of the second check, restated: 13 answer files give the model as Perplexity and 10 give no model line, so for all 23 the model, Fable 5.1 Thinking, is recorded on the author's statement. The list of rows to reread is final only after the reruns are counted; no reread session has been started  results seen  ·193a2aee
2026-10-07  descriptive addition, stage 4 span check, classes of the failing evidence spans (logged before the script runs; no rule changes, the registered treatment of a failed span stands and no record's status changes): 64 of the 14,053 evidence spans fail the span check (63 of the search file and 1 of chase1); of these 27 hold under the registered quote check and were refused by citations pin as ambiguous, and 37 fail both. scripts/classify_failed_spans.py (sha256 0c1c6defb58ecab20835174e5519adc46b804c195c6a9d837e48ffbd04bc5899; tests/test_classify_failed_spans.py, sha256 163bbd1fcfe8078e373a72a5c1309999c9c8d2833b52cd694e38675acba86247; suite on Modal 1 failed, 1058 passed, 1 skipped) compares each failing span with the stored abstract, the title and the text sent to the model, and assigns the first class that applies: in the abstract more than once; in the abstract once with the pin refused; found after Unicode normalisation (NFKC, dashes, quotes, soft hyphen, zero-width characters, white space); found after also removing tags, entities and sub or superscript marks; pieces of the abstract joined by an ellipsis; two to four pieces of the abstract joined; in the title only; in the text sent to the model but not in the stored abstract; a near match within 3 tokens or a tenth of the span, with a changed digit marked; abstract empty or under 200 characters; no close counterpart. The script reads the 64 spans and their abstracts; no person or agent reads them; it writes a class per record and its counts (outputs/span_failure_classes/span_failure_classes_2026-10-08.json), and only the counts per class are reported  results seen  ·ec013d76
2026-10-07  descriptive addition, stage 4 span check, result and a disclosure about its test: the script of the preceding entry ran once and classed the 64 failing spans (outputs/span_failure_classes/span_failure_classes_2026-10-08.json): 27 are in the abstract more than once (all in the search file; each occurs twice; the registered quote check holds and citations pin refused the span as ambiguous, having no single occurrence to name) and 37 are two pieces of the abstract joined (36 in the search file and 1 in chase1; each is two runs of the abstract in the abstract's order with the text between them left out and no ellipsis written); no span fell in any other class: none needed Unicode or markup normalisation, none is a near match, none is found only in the title or the request, none lacks a close counterpart. So no failing span holds text that is not in its abstract; 27 failures are the pin step's and 37 are spans the extraction model assembled from two parts. No rule, status or registry input changes. Disclosure: the preceding entry gives the suite as 1 failed, 1058 passed; the failing case is one fixture of tests/test_classify_failed_spans.py in which a soft hyphen was put in place of a space, which joins two words, so the script rightly classes it a near match and the test's expectation was wrong; the script and that test were sealed and the script run before this was noticed, which is a breach of testing before use; the script is unchanged, tests/test_classify_failed_spans_fixture.py (sha256 18272ef6717d7e7f27d71748402e30b704ce04452ced77311b070d2bb4326f75) holds the fixture as intended (a soft hyphen inside a word and a zero-width space, classed as found after Unicode normalisation) and shows why the other fails, and the sealed test file is left as it is until its handling is decided. Only the counts per class were read  results seen  ·ea0ff0ec
2026-10-07  correction of a sealed test file, logged before it is resealed: tests/test_classify_failed_spans.py (sealed with sha256 163bbd1fcfe8078e373a72a5c1309999c9c8d2833b52cd694e38675acba86247) held one wrong fixture, a soft hyphen put in place of the space between two words, which joins the words, so the case expected the class found after Unicode normalisation where the script rightly gives a near match, and the suite failed on it at every run; the one line is changed so that the soft hyphen stands inside a word, as intended (new sha256 f1974937eb7183bb6486b93a9996b072abdb0b238a2157721845842b34dac672); nothing else in the file and nothing in scripts/classify_failed_spans.py changes, and the classification of the 64 spans stands as logged. Suite on Modal after the change: 1061 passed, 1 skipped, return code 0 (outputs/tests/pytest_all_modal_20261008T020217Z.txt). The ledger will show the file as sealed twice. From here on a seal or a run is a separate command made after the suite result has been read, never chained to it  results seen  ·a0a9b7ab
2026-10-07  manual dataset coding, second check, the reruns and the pinning of the checker's quotations (logged before any quotation is pinned): the reruns of batches 08, 11 and 13 with the same prompt and files were read by scripts/manual_coding_check2_ingest_v3.py (planning/perplexity_paper1_check2_ingest/run_05): the reruns of 08 and 11 pass every check and are counted, and their first answers stay in the folder as failed and superseded; the rerun of 13 fails again, on one quotation that is a fragment of a supplied sentence, in a row other than the two that failed first, so batch 13 (38 rows) is rerun once more and has no counted answer; 22 batches and 834 rows are counted. Pinning: scripts/pin_check2_quotations.py (sha256 53af941a62e69a8381c2c4040b3d3e3fd26bcab5d6abc24a293bfba298b2c5cf; tests/test_pin_check2_quotations.py, sha256 688af235a5a0d56cc4396341d708b90e1223a7f4d8d9d242a7328b3d8a167259; suite on Modal 1065 passed, 1 skipped, return code 0) pins, for every counted answer that quotes a sentence, the sentence the batch supplied (the export's marks undone as the ingest does) in the claims file of the passage that holds it, against the stored source the coders' pins use, under the claim id <side>_<k>_c2 of the answer's row, with citations pin and, for a sentence occurring more than once, the second occurrence helper; a quotation that will not pin is recorded and its batch fails that check and is rerun; the script may be run again after a rerun and leaves an existing pin as it is; citations verify --strict then runs over the folder. No row value was read for this entry  results seen  ·c8a18f6c
2026-10-07  manual dataset coding, second check complete (logged before the last batch's quotations are pinned and before any reread file is written): batch 13 passed every check on its third answer (planning/perplexity_paper1_check2_answers/batch_13_fable_prompt_v4_rerun2.md); its first answer failed on two quotations and its first rerun on one, each a fragment of a supplied sentence, and both stay in the folder as failed and superseded; for the second rerun the three attached files were the same and the chat message carried one added sentence asking for whole sentences. With it all 23 batches have exactly one passing file and all 872 rows a counted answer (planning/perplexity_paper1_check2_ingest/run_06, read by scripts/manual_coding_check2_ingest_v3.py; four failed files in all, of batches 08, 11 and 13). Compliance over the 23 counted files: every row answered once and in order, every answer allowed, every quotation a whole supplied sentence (115 after the export's marks were undone; 19 supplied under another row of the same paper), the closing line present, every footnote an attached file. Agreement at the second check, a count as item 5 requires, first on the coder's value and then with the first check taken under the gate rule: the same dictionary row 199 and 193; unresolved with the same category 627 and 627; unresolved with another category 1 and 1; both unresolved with different values 22 and 23; the first check coded and the second unresolved 5 and 4; the first unresolved and the second coded 18 and 24; both coded to different rows 0 and 0. Of the seven rows whose code failed the gate, the second check names the coder's dictionary row in six and gives an unresolved value in one. 51 rows in 47 papers differ under the gate rule and go to the reread (coder_1 14 papers, coder_2 9, coder_3 14, coder_4 10). No row value was read for this entry  results seen  ·2a53567e
2026-10-07  preparation for a correction of the stage 4 span check reviewed in round 16 (planning/perplexity_paper1_final/26_REVIEW_round16.md); nothing in this entry has been run on study data, the build of the citations tool the correction needs is not yet fixed, and the amendment naming it is logged separately before any run. Fixed and committed now, before any run: the rule (pin the first occurrence, when and only when the registered quote check holds and the plain pin is refused as ambiguous; the pass condition stays the registered quote check and a pin that is found, both) and the permitted-difference set, verification/span_step_permitted_differences.json (sha256 be73648257dab63299de2655f4c77f2594c84020c642d5197e2184c048cc6e1a): by record id, the 63 failing records of the search file (27 to pass, 36 still failing) and the 1 of the first citation-chasing file (still failing); the 37 records whose span is two verbatim pieces joined stay failed in the primary analysis as registered. Scripts sealed with this entry: scripts/verify_spans_occurrence.py (sha256 bd99dda3e18fa9747731d9ec2f09479267a62cbf86ea111df640bf470f15a8d3), a copy of scripts/verify_spans.py that applies the rule, writes to folders of its own, refuses to run unless the installed citations was installed from the commit it is given, and records the installed build, the occurrence count of each record pinned at an occurrence and the abstracts holding a duplicated passage; scripts/span_step_comparison.py (sha256 c6c9d0aabb8fa17e95be2845058c3d0b84e3abc67be9913923976e95644bd292), which asserts that the records differing between the two runs are a subset of the permitted set, that every passing record is identical, that a file with no permitted record is byte-identical, that the 27 pass and the 37 fail, that the occurrence option was used for the 27 and no other record, and that the two builds' folding functions give identical output on every stored abstract and span, with the sha256 of every input and output; scripts/citations_fold_digest.py (sha256 f7e2e631569a96c9a5d57a0032cc2573f41c6f4637e4e0bfec6f5b6a8b7bea80), run under each build for that last assertion; scripts/span_failure_followup_counts.py (sha256 c04a37f9b1fb9023d6b91203e4ef409149c81a1a5283e9e10f6ca7226a882994), two count-only reports: repeated claims among the 27, and negation or contrast tokens in the text left out of the 37 (tokens fixed: no, not, without, however, but, whereas, in contrast; whole words, case folded); tests tests/test_verify_spans_occurrence.py (sha256 4a092f1970faa71a5cac446a1eeb1e8d272a50f42d8ee29ab6e8316f9f3e4303) and tests/test_span_step_amendment.py (sha256 df284eb6f4057ef72170df9b473dde1dfe3c2d52da344be1e84c75ede29d49d3); suite on Modal 1087 passed, 1 skipped, return code 0 (outputs/tests/pytest_all_modal_20261008T024853Z.txt). A fact recorded here because the amendment will rest on it: the citations tool of the registered run is an editable install of the author's tools repository, whose checkout has stood at commit 5519baf5ef9a7b120ee6984ad179dc91a43fa79d, unmodified, since 6 October 22:17 UTC, before the span check ran; its installed metadata reads 0.4.2 and the source at that commit declares 0.5.0. No span, abstract, registry content, relation or aggregate was read for this entry  results seen  ·8fba918f
2026-10-07  descriptive addition, stage 4 span check, results of the follow-up counts and the classes of a further count fixed before it runs (no rule changes and no record's status changes). Results of scripts/span_failure_followup_counts.py (outputs/span_failure_classes/span_failure_followup_counts_2026-10-08.json): the 27 records whose span stands in the abstract twice are 25 distinct claims as written and after mapping (18 distinct of 18 in one paper, 4 of 6 in a second, 3 of 3 in a third), and the 14 that pass the other claim-level criteria are 14 distinct claims after mapping, so the duplicated passage gave no repeated claim among the records that could enter; of the 37 records whose span is two pieces of the abstract joined, all are two pieces in order, none of the omitted segments holds a negation or contrast token (no, not, without, however, but, whereas, in contrast), and the tokens left out number 37 in all. Next, scripts/span_omitted_token_kinds.py (sha256 6bcedb3b29e2a520ff3a1994426d7954950f8611b496cdda2530001d7749fb29; tests/test_span_omitted_token_kinds.py, sha256 e3b6c5c4b78eb101e5ef49e898494a3fd902c91fb121aaca0fceb88d65ec70ed; suite on Modal 1104 passed, 1 skipped, return code 0) classes the token left out of each of the 37, first class that applies: holds a digit, as a citation-style marker (digits only, directly inside square brackets or parentheses), as a number with a sign before it, a percent sign after it or a letter in it, or as a bare number; punctuation or symbol only (cannot occur: a token is a run of letters and digits); a single letter; a word of letters only, as article or determiner (a, an, the, this, these, that, those), conjunction or preposition (and, or, of, in, on, with, for, to, by, as, at, from), intensifier or hedge (significantly, strongly, potentially, possibly, likely, may, might, could), or other; anything else; a record with none or several tokens left out is counted apart; per class also the records passing the other claim-level criteria, where the gap falls in the span (first tenth, middle, last tenth) and whether a neighbouring token of the abstract holds a digit. A superscript citation number written straight after a word cannot be told apart by this tokeniser. The script reads the 37 spans and their abstracts; no person or agent reads them; it writes classes and counts and no token text  results seen  ·760824e3
2026-10-07  manual dataset coding, the reread of disagreements has run (item 5), logged before its resolution files are read and gated: 51 rows in 47 papers, in 6 fixed shares (coder_1 2 shares and 14 papers, coder_2 1 and 9, coder_3 2 and 14, coder_4 1 and 10), each share one fresh session under its coder role with the sixth coder instructions and the reread instructions; each session was also told not to open reread/source_rows.json, reread/draw_manifest.json or reread/summary.json, which lie beside the shares and hold which check gave which answer. Declared by the sessions: every pin command run after a change of directory into the pins folder; the dictionary and two large input files read in two pages; the pin tool's notice that a claims file records no url or doi printed for several pins; no pin refused, the occurrence helper not needed, nothing opened outside the brief. Checked before reading (file names and row ids only): each of the 47 papers has its resolution file under the listed name, holding exactly the rows of its disagreement file in order, with the record and coder of that file; no other file is in the resolution folders  results seen  ·1f309466
2026-10-07  manual dataset coding, result of the reread of disagreements (outputs/manual_coding/2026-10-03/reread/resolutions.json, read by scripts/manual_coding_reread.py with the gates of scripts/manual_coding_gates_v2.py): of the 51 rows the rereaders resolved 16 to a dictionary row, 19 to a dataset absent from the dictionary and 16 to not stated (13 release not identified, 3 conflicting identifiers); in every row the resolution equals one of the two original answers (the second check's in 35, the first check's in 16), never a third value. Gate: 13 of the 16 rows resolved to a dictionary row fail it, each for no identifier of the coded row in the pinned material, and are unresolved, not sent back (coder_1 39333727 pqtl_1, 40052860 outcome_2, 40564116 outcome_1, 41222800 pqtl_1, 41711838 pqtl_1 and 42365225 outcome_3; coder_2 40765733 outcome_1, 41200820 pqtl_1 and 41319014 pqtl_1; coder_4 40462010 outcome_1 and pqtl_2, 41220142 pqtl_2 and 41487707 outcome_1); in all 13 the rereader's dictionary row is the one the second check named, and in 6 of them it is also the row the first check had coded before its own gate failure, so three readings name a row the gate does not accept; 5 of the 13 rest on a reference entry verified by DOI whose source has several dictionary rows, with no separating attribute in the pinned sentence. Values that stand for the 51 rows: 3 a dictionary row, 19 absent from the dictionary, 26 release not identified, 3 conflicting identifiers; the value that stands equals the first check's value (under the gate rule) in 29 rows and the second check's in 22. Both original answers and their quotations are kept with each resolution. Read for this entry: counts and row ids; no value, quotation or passage  results seen  ·c4b5a4ef
2026-10-07  manual dataset coding, the table after two checks and the reread, and the table for the third check (logged before the author's table is written): the extended table was built in three steps, each file kept: the first check's final values under the gate rule (scripts/manual_coding_table_v2.py collect; 197 coded, 463 not stated, 212 absent; 7 coded rows written unresolved for a failing gate), the checker's values filled in (second-check; all 872 rows), and the reread's resolutions applied (scripts/manual_coding_reread.py apply; 51 rows), as outputs/manual_coding/2026-10-03/manual_dataset_codes_extended_1_first_check.csv, _2_second_check.csv and _3_reread.csv. State of the 872 rows before the third check: the two checks give the same value in 821 rows and different values in 51; standing value a dictionary row in 196 rows (193 agreed, 3 resolved by the reread), release not identified in 435, conflicting identifiers in 15, dataset absent from the dictionary in 226. Of the 196: 98 rest on a reference entry and 98 do not; basis release identifier 62, reference entry 98, exact N with platform or year 23, source identifier 9, unique citation 4; 179 from full text, 15 from the abstract, 2 from the abstract fallback; every one has its quotation and pin. Third check: scripts/manual_coding_check3_table.py (sha256 08cfc5231bb3934b0a7ce6d77b30646974e1e2975501ad5be35455efbf214d2c; tests/test_manual_coding_check3_table.py, sha256 108a2e9090c064cc213902ccf8f4bce0437c098cc0d24942c5b2141dd2b34f9d; suite on Modal 1110 passed, 1 skipped, return code 0, four of the tests being those of a script not yet sealed) writes one line per group of rows standing coded whose pinned sentence, coded row and reference entry are identical, with the rows counted, the basis, the identifier the gate found, and empty columns for the author's yes or no and note; the author confirms each line against the pinned sentence as item 5 says; a row standing unresolved is not in it. No value, quotation or passage was read for this entry  results seen  ·c34fd470
2026-10-07  preparation for the treatment of the 37 evidence spans that leave out one token, as decided by the author after two further review rounds (planning/perplexity_paper1_final/27_REVIEW_round16b.md and 28_REVIEW_round16c.md); nothing in this entry has been run on study data, and the amendment that carries it is logged separately before any run. Decided, with the labels fixed now and kept whatever the results: amended primary analysis, the span is restored from the stored abstract and the record goes through the registered checks (source-restored and checked under the registered verifier); originally registered analysis, the 37 excluded; both are reported together. Not done and not to be done: the re-request of the 15 abstracts put to the reviewer in round 16b (proposal C), which the reviewer accepted only as a sensitivity analysis and the author has dropped; that request was uploaded at about the time the fact that each of the 37 spans omits exactly one token was being added to it, the reviewer's answer does not mention the fact, and no further round was sought on that, the ruling resting on the re-request being conditional on an observed output; no re-request was sent. Counts read since the preceding entries, by sealed scripts, no text: each of the 37 omits one abstract token; in all 37 that token is a word of letters only outside the fixed lists of articles, conjunctions or prepositions and hedges; none holds a digit; in 7 a neighbouring token holds a digit; the gap is in the middle of the span in all; 20 of the 37 pass the other claim-level criteria. Prepared and sealed with this entry: scripts/span_restoration.py (sha256 2eb57c737f712b93414afeebf0a88021df652ffdbb02c8e26d541d3f21d73452; tests/test_span_restoration.py, sha256 f6091a120d1d93bd368c0870ede66d9bb930c93b1aa825164f1ae2ed1a8abe9a; suite on Modal 1121 passed, 1 skipped, return code 0), which applies one predicate to every claim record: the registered quote check fails, and the span's white-space tokens, case folded, are two runs standing in the abstract in order with exactly one whole abstract token between them, the tokens at the junction whole, the alignment unique; a changed sign, a truncated number, a substitution, a cut compound, several tokens left out or an alignment possible in two ways is not eligible; eligibility does not look at verification; the restored passage is the stored abstract's own text from the start of the first run to the end of the second; the script stops unless the eligible records are exactly those of verification/span_restoration_expected_records.json (sha256 a0166e9c8464d5a5f7bec009b01772bdbc3d476dbbf29cfc0782da0235ea7409: the 36 records of the search file and the 1 of the first citation-chasing file classed on 8 October), never overwrites the model's output, and writes a repair map of hashes, offsets and the rule and a derived extraction file; it also compares its passages by hash with another source, and counts the verifier's transitions for the restored records and any difference in every other record. Note on the predicate: the classes of 8 October were found with a tokeniser of letter and digit runs, and the predicate uses white-space tokens as the registered check does, so the two may not select the same records; if they do not, the script stops and that is reported. The registered verifier is unchanged: a direction disagreement keeps a record out of direction-based results and not out of the registry (scripts/verify_claims_whitespace.py, lines 777 and 812), and claims sharing a span are read together for mixed directions (lines 762 to 764), which is why every other record is compared before and after  results seen  ·bf50a4b7
2026-10-07  three records made before the third check of the manual dataset coding and before the amendment of the span check is logged. (1) The restoration predicate of scripts/span_restoration.py was evaluated over all 14,053 claim records as a count-only dry run (outputs/span_failure_classes/span_restoration_predicate_dry_evaluation_2026-10-08.json; nothing restored, no text written): it selects 37 records, the same 37 the classifier found, none outside them and none missed, so the expected-records file stands as sealed. (2) The rows the machine gates refused, for the record (outputs/manual_coding/2026-10-03/gate_refused_rows.json; row ids and classes, no values): 14 rows, the 13 whose reread value failed the gate and one whose first-check code failed it and which the reread left unresolved; in 6 the first check before its gate, the second check and the reread all named a dictionary row, in 7 the second check and the reread did, in 1 the first check alone, and wherever several readings named a row they named the same one; by cause, mechanically: 5 rest on a reference entry verified by DOI whose source has several dictionary rows with no separating attribute in the pinned sentence, 2 write the release in a form outside the list of rule A, 3 hold no term of the coded row in the pinned material, and 4 hold only terms the coded row shares with another candidate; all 14 stand unresolved under the rule as logged. (3) How the third check is read back: scripts/manual_coding_check3_marks.py (sha256 cf9f6258e40a687e804b3a25af2a1c3eadb6d0d03b3616d1b30a752d9615f7f0; tests/test_manual_coding_check3_marks.py, sha256 d35f90e89062bb47e76ef3345423d54bc4b096285e63b1c6344859da08516f51; suite on Modal 1125 passed, 1 skipped, return code 0) writes a reading view of the author's table, the same 196 lines in the same order, and reads the marked table: every line must be marked yes or no and nothing else in the file may differ from the table as written; a row marked yes is coded; a row marked no is unresolved with the reason author_did_not_confirm and the author's note kept, both original answers untouched; a line left blank blocks the step; the sha256 of the marked file is recorded. No value, quotation or passage was read for this entry  results seen  ·347bdcd7
2026-10-07  deviation, manual coding of dataset names, the third check (item 5), logged before any mark of the author exists (the marking spreadsheet holds 0 marks of 20) and decided after the counts of the first and second checks were known, with no registry content, dataset relation or H1 or H2 quantity opened. Item 5 has the author confirm each coded row against its pinned sentence, a literal match and not a judgment of the paper. Instead: the literal match is made for all 196 rows standing coded by the machine gate already applied (scripts/manual_coding_gates_v2.py: the pinned sentence, or its reference entry verified by identifier, holds an identifier of the coded row that no other candidate has) together with citations verify --strict on the pins; and the author reads a random sample of 20 of the 196 and marks each yes or no. This removes the per-row human check of the plan: the author declined to read 196 sentences. No row is recorded as confirmed by the author unless he marked it; the paper says the third check was made by machine on all coded rows and audited by the author on a random sample of 20, with the result. The draw was made by the coordinating session at 03:15 UTC on 8 October, about five minutes before this entry and before the author read any row: seed 20261008, random.Random(seed).sample(range(196), 20) over the lines of outputs/manual_coding/2026-10-03/check3_author_table.csv in file order (sha256 0959c23eb9a7740a41967643b0b1c1366555dfc4d99289081ad16c94d0005634), sorted, giving table lines 8, 12, 23, 32, 40, 55, 56, 62, 72, 75, 80, 103, 105, 113, 120, 146, 173, 182, 184 and 192 (manifest check3_sample/check3_sample_20_seed20261008_v2_manifest.json, sha256 cb1b6294ee08864a0fe74ba5e4b683d087083c45b34a28631650f25508f87ee7; an earlier manifest without _v2 holds the same draw, its spreadsheet was never written because of a script error, and the second view changes only how the matched part of a sentence is highlighted); the author marks check3_sample/check3_sample_20_seed20261008_v2.xlsx (sha256 before marking 6292a8b1a802435a217cf97ec334ac7488697479605367c351eeed01847a8795), a view built ad hoc by an unsealed script of the coordinating session; scripts/manual_coding_check3_sample.py reproduces the draw and gives the same 20 lines as both manifests. Fixed now, before any mark: a sampled row marked no is unresolved with the reason author_did_not_confirm and the note kept; if exactly 1 of the 20 is marked no, the result is reported as 19 of 20 and a second seeded sample of 20 from the remaining 176 (seed 20261009) is read, no further no closing the check; if 2 or more of the 20 are marked no, or any of the second sample, the sample has failed as an audit and every remaining row is read by a person before any is used, or, if the author declines, every coded row not confirmed by him whose identification basis is that of a row marked no is set unresolved; the paper reports the number sampled, the number confirmed, and the one-sided 95 percent upper bound on the share of coded rows that would not be confirmed (exact binomial; for 0 of 20, 1 - 0.05^(1/20), which is 0.139). Reader: scripts/manual_coding_check3_sample.py (sha256 b221ae38162fd6434cf8e08d539e44ff3f9ef4737f60929af9574105d5a8f7e1; tests/test_manual_coding_check3_sample.py, sha256 1b5e3df5b9ff1b2083929ee5950964d1ac269ec87e090ea8e54075e7d3b61b5f) refuses a blank or foreign line, records the marked file's sha256 and applies the rules above. Table: scripts/manual_coding_table_v3.py (sha256 7b94a03c744574844267c5ca6aec43a5b40d5a2d04957bf1ac2f3d2df1ff2546) supersedes the second table script; its extended table has a column third_check (author_confirmed, author_did_not_confirm, machine_gate_only, or empty for a row standing unresolved) and writes author_confirms as yes or no only for a row the author marked and not_read otherwise; the registered reader takes a row as coded only when author_confirms is yes (scripts/manual_dataset_coding.py, lines 125 to 128), so in the registered twelve-column table, and only there, the column is written yes for a row whose third check is author_confirmed or machine_gate_only: in that file it means that the third check as carried out here was passed, not that the author read the row; the extended table is the record. Suite on Modal 1132 passed, 1 skipped, return code 0. The reader is not run on real marks until the reviewer's answer to a question on this deviation is in  results seen  ·09356387
2026-10-07  manual dataset coding, the third check: how the author's sample was marked, logged before the marks are read into the table. The marks: outputs/manual_coding/2026-10-03/check3_sample/check3_sample_20_marks_author.json (sha256 33491574276a467080c377973c8372d9a246b48459fa207b90ae80850795dacc; saved by the author's browser at 2026-10-08T03:22:56Z; the coordinating session's copy of the file he downloaded): 20 rows, the 20 table lines of the draw, all marked yes, no notes. How it was marked: the machine has no spreadsheet program, so the author did not mark the spreadsheet named in the entry above; the coordinating session built a web page from the same 20 rows (check3_sample/check3_sample_20_seed20261008_v2.html, sha256 35396c7a9080adadfce93c3147ac338b5afe22448bddbaa5e87cd3218417901d, written at 03:16:51Z; ad hoc, unsealed; the coded row, the side, a trimmed sentence with the matched terms highlighted, the full sentence and reference entry behind a link, yes or no and a note box, and a button that downloads the marks as JSON), and the marks file is that download. Before marking, the author asked the coordinating session about six of the 20 cards (by card number 3, the card with the UKB-B accession, 14, the card whose pinned sentence begins with the words These pQTLs establish connections, 19 and 20); for each the coordinating session explained what the sentence and the settled rule say and stated which answer was consistent with the rules, leaving the answer to him, and for the These pQTLs card it said that the attribution in the pinned sentence was thin and that either answer could be defended; so for those six the author's mark was made after hearing the coordinating session's reading and is not independent of it. Asked afterwards whether he had read each card or clicked yes on those he had not asked about, the author answered, verbatim: yeah tahts fine jsut say yes. This entry records the question and that answer and makes no further claim about how the other fourteen were read. On the order of events, corrected here: the entry above says it was logged before any mark of the author existed and gives as its ground that the spreadsheet held 0 marks; that entry was written between 03:19:55Z and 03:20:20Z and committed at 03:20:30Z, the marks file was saved at 03:22:56Z, and the web page had been available since 03:16:51Z, so the author's reading of the cards and his questions may have begun before that entry was written; the rules for what the marks mean were therefore fixed and committed about two and a half minutes before the marks were saved, and not provably before the author had begun. The entry above also says the reader is not run on real marks until the reviewer's answer to a question on this deviation is in: the reader is run now on the coordinating session's instruction, and no answer of the reviewer has been given to the session writing this entry. Result under the rules fixed above: 20 of 20 marked yes; no second sample; the check closes; one-sided 95 percent upper bound on the share of coded rows that would not be confirmed, 0.139. Reader: scripts/manual_coding_check3_sample_json.py (sha256 c50a862322353d168fdaeac3c3d7b67183b38edba85c43277db662a44959aa56; tests/test_manual_coding_check3_sample_json.py, sha256 f8028639d4de802fed30b84cb361346e08b472949019702679a3e9d79c83fb80; suite on Modal 1140 passed, 1 skipped, return code 0), the sealed sample reader with the marks read from the JSON file and nothing else changed; the spreadsheet is not edited  results seen  ·bf6070cd
2026-10-07  manual dataset coding, the three checks are complete and the codes are committed before any registry is assembled with them (item 7). The author's marks were read by scripts/manual_coding_check3_sample_json.py: 20 sampled rows recorded as author_confirmed, 176 coded rows as machine_gate_only, 676 rows standing unresolved with no third check; no row is recorded as confirmed by the author that he did not mark. Final state of the 872 queue rows: 196 coded to a dictionary row (98 resting on a reference entry verified by DOI; 179 from full text, 15 from the abstract, 2 from the abstract fallback; 3 coded after the reread), 435 release not identified, 15 conflicting identifiers, 226 dataset named in the source and absent from the dictionary, 0 with no local passage; agreement at the second check 821 rows of 872, and 51 disagreements resolved by the reread to 3 coded, 19 absent and 29 not stated. Tables, in outputs/manual_coding/2026-10-03: manual_dataset_codes_extended_4_third_check.csv, the record (with _1_first_check, _2_second_check and _3_reread, the same table after each step, and the third-check record beside it); manual_dataset_codes.csv, the registered twelve-column table written from it by scripts/manual_coding_table_v3.py, and manual_dataset_coding_report.json; the registered reader (scripts/manual_dataset_coding.py) and the extended reader both take the table and return the same 196 codes, and the table covers the queue exactly. In the registered table author_confirms reads yes for the 196 coded rows, which there means that the third check as carried out was passed, as logged above; in the extended table it reads yes for the 20 rows the author marked. Committed with this entry: those tables; the author's table, its reading view, the draw's manifests, the page and spreadsheet of the sample and the author's marks; the coders' inputs, attempt files, gate files and screen files, the misnamed files set aside, and the reread's files and resolutions; the claims files and source texts the pins rest on (outputs/citations/manual_coding_2026-10-03); the run's small records in the same folder. Not committed with it: the superseded passages, coder inputs and citation folders of earlier generator runs and the fetched full texts, which are kept on disk for the stage record. The manual-coding stage is not yet recorded in the results ledger as a run  results seen  ·2e78d8f3
2026-10-07  manual dataset coding, a further voluntary read by the author after the seeded spot-check of 20 had closed, logged at 2026-10-08 about 03:45 UTC: the author has chosen to read a further seeded random sample of 30 of the 176 coded rows he has not marked, which would bring the rows he has marked to 50 of 196. The draw, made by the coordinating session at 03:43:44 UTC: seed 20261010, random.Random(20261010).sample(range(176), 30) over the 176 lines of outputs/manual_coding/2026-10-03/check3_author_table.csv that are not in the first sample, in file order, sorted, giving table lines 1, 13, 18, 27, 31, 48, 49, 50, 57, 68, 74, 76, 86, 87, 88, 95, 96, 100, 101, 104, 115, 117, 128, 132, 148, 161, 171, 178, 188 and 189; the sealed scripts/manual_coding_check3_sample.py reproduces the draw and gives the same 30 lines as the manifest (check3_extra_30/check3_extra_30_seed20261010_manifest.json, sha256 a9debc40e860f185b7e5f71e0e790a7e98cd5b6cc200b3e903c8a0ea4b5fdbc2); the reading page (check3_extra_30/check3_extra_30_seed20261010.html) was built ad hoc by an unsealed script of the coordinating session. Rule for these marks, the one for a voluntary read: yes makes the row author_confirmed; no makes that row unresolved (author_did_not_confirm) with the note kept; unsure or blank leaves it machine_gate_only and is counted; a no has no consequence beyond its own row; the counts of yes, no and unsure are reported; a row the author discussed with the coordinating session before marking is flagged as such. The page opened at about the time of this entry and the author was to start reading within a minute or two, so this rule is logged at about the same time as the reading began and not provably before it. No row value was read for this entry  results seen  ·c0e3866e
```
