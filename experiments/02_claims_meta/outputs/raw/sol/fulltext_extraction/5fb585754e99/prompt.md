You extract protein–outcome claim records from the full text of one scientific paper. You
receive the title and the text of the paper's body and main tables. The text has been
removed, and supplementary files are not included. Use nothing you may know about the paper from
elsewhere.

The text is laid out as follows. A line starting `## ` is a section title. Every other line is
one paragraph, or one row of a table. A table row line starts with the table's label and caption
in square brackets, followed by the row's cells, each as `column header: value`, separated by
` | `. A line starting `[Table N footnote]` is that table's footnote.

Return JSON that follows the schema exactly: an object with a `claims` list. Return an empty
list when the text states no protein–outcome result.

## What is a claim record

A claim record is one explicitly stated protein–outcome result for one analysis context: one
named protein, one outcome (a disease, a trait, a clinical measurement or another biomarker),
and the analysis that produced the result. It can say the protein raises, lowers, causes, is
associated with or is a target for the outcome, or that it has no effect on it.

- Statements that repeat a result without a distinct direction, dataset, ancestry, subgroup or
  analysis context give one record, quoted from the sentence or table row that states it most
  completely. A result stated in the Results and restated in the Discussion gives one record.
- Distinct results for the same protein and outcome give separate records when the text
  distinguishes their direction or their analysis context: for example a result in a discovery
  dataset and a result in a replication dataset, a result in Europeans and a result in East
  Asians, a result in women and a result in men, or a main result and a sensitivity analysis.
  Never merge two such results into one record, and never choose one of them over the other.
- Only proteins the text names. "Thirty proteins were associated with stroke" gives no
  record.
- A sentence naming several proteins and several outcomes gives one record per protein–outcome
  combination only when its wording applies every protein to every outcome ("X, Y and Z were
  each associated with A and B") or pairs them explicitly ("X and Y were associated with A and
  B, respectively" gives X–A and Y–B only). When the wording does not make clear whether a
  listed protein is linked to a listed outcome, give the record and set `relation_ambiguous`
  to true. Otherwise `relation_ambiguous` is false.
- Only results of this paper's own analyses, as reported in the Results, the tables, or the
  Discussion's statements of this paper's findings. A sentence reporting earlier studies,
  background knowledge, a hypothesis or a motivation ("A high concentration of X is associated
  with Y", "Previous studies observed ...") gives no record, and neither does a Methods
  description of an analysis without its result.
- The title is context only. Every record must be stated in the text.
- Tables. Each table row that states a result for a named protein and a named outcome gives a
  record; a row stating results for several outcomes (for example in different columns) gives
  one record per outcome. The outcome may be named in the row, the column header or the caption.
  The analysis context of a row comes from the table's caption and headers (for example a
  replication table, or a column for one MR method) as well as the row.
- Extract every protein–outcome result the text states, and label each with its
  `evidence_type` (below). Only genetically proxied estimates enter the study, but the other
  results are still extracted and labelled.

## Fields

- `protein_as_written`: the protein as the evidence span names it, copied exactly (for example
  `IL-6R`, `interleukin-6 receptor`, `soluble ST2`). Do not expand abbreviations, translate to a
  gene symbol or add words that are not in the span.
- `outcome_as_written`: the outcome as the evidence span names it, copied exactly (for example
  `coronary heart disease`, `CHD`, `type 2 diabetes`). Leave out words such as "risk of" or
  "increased".
- `direction`: the direction of the protein's effect or association on the outcome.
  - `raises`: higher protein level goes with higher risk of the disease or a higher value of the
    trait. This includes a lower protein level going with lower risk.
  - `lowers`: higher protein level goes with lower risk or a lower value. This includes a lower
    protein level going with higher risk, and a protein described as protective.
  - `reported_nonsignificant_or_null`: the text states no association, no causal effect, or
    no evidence of one, for this record; or the estimate printed for it is not statistically
    significant. An estimate is not significant when its printed confidence interval includes
    the null value (1 for an odds, hazard or risk ratio; 0 for a difference, beta or change),
    or, when no interval is printed, when its printed P value is 0.05 or larger, or when the
    text calls it non-significant. A non-significant estimate takes this value whatever the
    side of the null its point estimate lies.
  - `not_stated`: the text states a result for the record but not its direction.
  Read the direction from the words of the evidence span and any effect estimate printed there.
  An odds ratio or hazard ratio above 1 per higher protein level is `raises`; below 1 is
  `lowers`. The direction refers to the measured level of the named protein. When the text
  gives the effect of a variant, or of blocking the protein's signaling, without saying whether
  the protein's level is higher or lower, use `not_stated`.
- `evidence_type`: what kind of estimate the record reports.
  - `mr_estimate`: a genetically proxied estimate of the effect of the protein's level on the
    outcome, from Mendelian randomization, summary-data-based MR (SMR) or another analysis that
    uses genetic variants (for example cis variants, pQTLs or a genetic score for the protein)
    as instruments for the protein.
  - `observational`: an association between measured protein levels and the outcome, without
    genetic instruments.
  - `experimental`: a result from cells, animals, knockdown or an intervention.
  - `variant_association`: the association of a genetic variant with the outcome, reported
    without stating it as the effect of the protein's level (for example "the rs7529229 allele
    was associated with lower odds of coronary heart disease").
  - `other`: anything else.
- `claim_scope`: which analysis the record comes from.
  - `overall`: the paper's main analysis, with no narrower context stated.
  - `dataset_specific`: a result the text ties to one named dataset or to one stage (for
    example discovery or replication) among several.
  - `ancestry_specific`: a result the text ties to one ancestry or population.
  - `subgroup_specific`: a result in a subgroup defined otherwise (sex, age, disease subtype,
    medication use).
  - `sensitivity`: a result the text presents as a sensitivity, secondary or alternative
    analysis (for example another MR method or another instrument set).
  - `unclear`: the text states the result but not enough to tell which of the above.
- `analysis_context_as_written`: the words of the text that set this record's analysis
  apart from the paper's other records on the same protein and outcome (for example `in the
  replication cohort`, `using FinnGen`, `cis-MR`), copied exactly, or `not_stated` when the
  record has no such words.
- `subgroup_as_written`: the subgroup or ancestry the result is restricted to, copied exactly
  (for example `in women`, `East Asian`), or `not_stated`.
- `pqtl_datasets`: the named studies, cohorts, consortia or data releases from which the protein
  genetic associations (pQTLs) for this record come, each as written in the text, for
  example `INTERVAL`, `deCODE`, `UK Biobank Pharma Proteomics Project`. Each name once.
  `["not_stated"]` when the text names none.
- `outcome_datasets`: the named studies, cohorts, consortia or data releases for the outcome of
  this record, each as written and each once, for example `CARDIoGRAMplusC4D`, `FinnGen R10`.
  `["not_stated"]` when the text names none.
- `dataset_attribution`: how the text ties the named datasets to this record.
  - `claim_specific`: the text names the datasets for this result or its stage.
  - `whole_study`: the text names the datasets for the paper's analysis as a whole, and
    nothing in it restricts this result to some of them.
  - `unclear`: the text names datasets but does not say which of them produced this result
    (for example discovery and replication datasets named, with the result not tied to either).
    List every name that could apply.
  When both dataset lists are `["not_stated"]`, use `whole_study`.
- `platform`: the protein measurement platform, one entry per platform named, each once. Write
  `Olink` for Olink or proximity extension assay panels, `SomaScan` for SomaScan, SomaLogic or
  aptamer-based assays, `mass_spectrometry` for mass spectrometry. For any other platform, write
  its name as the text gives it. `["not_stated"]` when the text names none.
- `ancestry`: the ancestry, ethnicity or national population of the participants as written in
  the text (for example `European`, `East Asian`, `Icelandic`, `Danish`), or `not_stated`.
  Clinical or demographic descriptions such as "patients with CVD risk factors" or "healthy
  blood donors" are not ancestry.
- `relation_ambiguous`: as defined above.
- `evidence_span`: one sentence, or two adjacent sentences, of one paragraph line that together
  state the record; or, for a result from a table, the whole table row line, from its opening
  square bracket to its end. Copy it character for character: the same words, spelling,
  capitalization, punctuation, symbols, numbers and brackets, with nothing added, removed,
  corrected, reordered or abbreviated, and no ellipsis. Never include a `## ` section title.
  Two sentences must be consecutive in the same line. The span must itself name the protein and
  the outcome, in the words given in `protein_as_written` and `outcome_as_written`; take a second
  sentence only when one sentence does not contain both. Use the shortest span that states the
  record, and quote from the text, never from the title.
- `source_location`: the title of the section the span is in (the nearest `## ` line above it),
  or the table label (for example `Table 2`) for a table row, copied exactly.
- `colocalization`: what the text reports about colocalization (for example coloc, SMR-HEIDI or
  another shared-causal-variant test) for this protein and outcome. `supports` when it reports
  that the test supports a shared causal variant; `does_not_support` when it reports that the
  test was run and does not; `not_reported` otherwise.
- `replication`: what the text reports about testing this record's result in a dataset other
  than the one that produced it. `replicated` when it reports that the result was repeated in
  the same direction in another dataset; `not_replicated` when it reports that a test in another
  dataset did not repeat it; `not_reported` otherwise. A record that is itself the replication
  result is `not_reported`.

The dataset, platform and ancestry fields may be taken from anywhere in the text, including the
Methods, not only from the evidence span, under the attribution rule above. Use `not_stated`
rather than a guess. In a list field, `not_stated` stands alone.
