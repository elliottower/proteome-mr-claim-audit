You extract protein–outcome claims from the abstract of one scientific paper. You receive only
the title and the abstract. Use nothing you may know about the paper from elsewhere.

Return JSON that follows the schema exactly: an object with a `claims` list. Return an empty
list when the abstract states no protein–outcome result.

## What is a claim

A claim is one result, stated in the abstract, linking one named protein to one outcome: a
disease, a trait, a clinical measurement or another biomarker. It can say the protein raises,
lowers, causes, is associated with or is a target for the outcome, or that it has no effect on
it.

- One claim per protein–outcome pair. A sentence naming three proteins and two outcomes gives
  six claims, each with the same evidence span, if the sentence links each protein to each
  outcome.
- Only proteins the abstract names. "Thirty proteins were associated with stroke" gives no claim.
- A result that the abstract repeats gives one claim, quoted from the sentence that states it
  most completely.
- Only results of this paper's own analyses. A sentence reporting earlier studies, background
  knowledge, a hypothesis or a motivation ("A high concentration of X is associated with Y",
  "Previous studies observed ...") gives no claim.
- The title is context only. Every claim must be stated in the abstract.
- Extract every protein–outcome result the abstract states, and label each with its
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
  - `null`: the abstract states no association, no causal effect, or no evidence of one, for this
    pair; or the estimate printed for the pair is not statistically significant. An estimate is
    not significant when its printed confidence interval includes the null value (1 for an odds,
    hazard or risk ratio; 0 for a difference, beta or change), or, when no interval is printed,
    when its printed P value is 0.05 or larger, or when the abstract calls it non-significant.
    A non-significant estimate is `null` whatever the side of the null its point estimate lies.
  - `not_stated`: the abstract states a result for the pair but not its direction.
  Read the direction from the words of the evidence span and any effect estimate printed there.
  An odds ratio or hazard ratio above 1 per higher protein level is `raises`; below 1 is
  `lowers`. The direction refers to the measured level of the named protein. When the abstract
  gives the effect of a variant, or of blocking the protein's signaling, without saying whether
  the protein's level is higher or lower, use `not_stated`.
- `evidence_type`: what kind of estimate the claim reports.
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
- `pqtl_datasets`: the named studies, cohorts, consortia or data releases from which the protein
  genetic associations (pQTLs) come, each as written in the abstract, for example
  `INTERVAL`, `deCODE`, `UK Biobank Pharma Proteomics Project`. `["not_stated"]` when the
  abstract names none.
- `outcome_datasets`: the named studies, cohorts, consortia or data releases for the outcome,
  each as written, for example `CARDIoGRAMplusC4D`, `FinnGen R10`. `["not_stated"]` when the
  abstract names none.
- `platform`: the protein measurement platform, one entry per platform named. Write `Olink` for
  Olink or proximity extension assay panels, `SomaScan` for SomaScan, SomaLogic or aptamer-based
  assays, `mass_spectrometry` for mass spectrometry. For any other platform, write its name as
  the abstract gives it. `["not_stated"]` when the abstract names none.
- `ancestry`: the ancestry, ethnicity or national population of the participants as written in
  the abstract (for example `European`, `East Asian`, `Icelandic`, `Danish`), or `not_stated`.
  Clinical or demographic descriptions such as "patients with CVD risk factors" or "healthy
  blood donors" are not ancestry.
- `evidence_span`: one sentence, or two adjacent sentences, of the abstract that together state
  the claim. Copy them character for character: the same words, spelling, capitalization,
  punctuation, symbols, numbers and brackets, with nothing added, removed, corrected, reordered
  or abbreviated, and no ellipsis. Do not include a section label such as "RESULTS:" that
  precedes the sentence. Two sentences must be consecutive in the abstract. The span must
  itself name the protein and the outcome, in the words given in `protein_as_written` and
  `outcome_as_written`; take a second sentence only when one sentence does not contain both.
  Use the shortest span that states the claim, and quote from the abstract, never from the
  title.

The dataset, platform and ancestry fields describe the analysis that produced the claim and may
be taken from anywhere in the abstract, not only from the evidence span. Use `not_stated` rather
than a guess.
