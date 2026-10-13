# Amendment 1: the supplement cut and C2

Amendment to `experiments/03_release_resolution/PREREG.md` (frozen 10 October 2026, registered at
https://osf.io/2s479). It takes effect when the plan's log names the sha256 of this file. Access
level: results seen (the results of Paper 1). Nothing of this stage has been coded and no model
request has been made.

## Why

After retrieval the registered cost-approval step was run (Data collection procedures, Cost
approval). With the registered cut, the estimate was 568 US dollars with the expected C2 and
929 more if C2 failed, against an approval line of 100. Six mechanical calibrations, counts
only, located the cost:

- The cut threshold is not the lever. At 10,000 characters instead of 200,000 the total falls by
  57 dollars.
- The rule "keep every row that holds a dictionary term" keeps most rows of very large tables. In
  these tables a dictionary name or a release-specific sample size repeats in row after row. The
  registered cut also repeats the header before every kept row that does not follow it. As a
  result, the cut text of two of the three largest papers is longer than the whole supplement.
- C2 reads each sampled paper's cut supplements whole: 131 dollars expected and up to 328
  dollars.

## What changes

**1. The cut of a supplement the registered threshold cuts** (§Study design, What the models read).
The threshold is unchanged: under 200,000 characters and at most 20 sheets, a supplement is given
whole. A larger supplement is cut as follows, every other rule of the registered cut standing.

- (a) **Keep list.** A line is always kept when it matches the frozen file
  `reference/release_language_patterns_v2.json` (sha256
  a5e77442ec701e2cd75f22210b0017e567dc8473e387aa2a1e47ac40169ef31f) or a C1 identifier pattern
  (accession, numbered release, DOI, PMID). The file covers:
  - release, version, freeze, data freeze, round, build;
  - R or round with a number, v with a number;
  - summary statistics, GWAS catalog, accession, downloaded, obtained from, data availability.

  Every row holding an identifier is therefore kept, mapped or not. No identifier row is set
  aside because another row maps to the same release. Dictionary names and aliases are not on the
  keep list.
- (b) **Table rule** for the other rows the registered rule keeps (rows holding a dictionary term).
  Within each table, kept are:
  - the sheet and table names and the header rows;
  - the first row per evidence unit, the unit being the table, a hash of its header or name, and
    the whole row, every cell numeric and non-numeric, each cell normalized (Unicode NFKC, dashes
    unified, case folded, whitespace collapsed).

  A row is dropped only when it equals a kept row of the same table in every normalized cell.

  A table is the rows under one header: a sheet, a CSV or TSV file, or a run of tab-separated
  lines. Failing that, it is the lines after one table name; failing that, the file.
- (c) **Headers.** A table's header is shown before the table's first kept row. It is repeated at
  the head of every model-input request (at most 400,000 characters) that holds rows of that
  table. Repeated headers are counted in cost and never as retained evidence.
- (d) **Containment.** Every evidence unit (as in (b)) that the registered cut retains in a paper
  is retained by this cut. The test is run on the frozen sources before the cut is applied; if
  any registered unit is absent in any paper, the stage stops.

**2. The removed-chunk miss-rate diagnostic** (replaces C2: §Research questions, C2; §Study design,
C2; §Indices; §Inference criteria; the C2 failure rule). C2 as registered asked whether the cut loses
any decisive release statement that a whole supplement holds. That paper-level question is not
answered here. The diagnostic estimates instead how common such statements are in the text the cut
removes. It cannot establish that no paper contains a miss.

- **Population.** The removed text of every cut supplement, cut into chunks of at most 10,000
  characters:
  - in file order;
  - a row never split, so a single longer row is one chunk;
  - the table's header carried at the head of each chunk.

  The calibration counts 49,280 chunks. The population is frozen with the cut before the sample
  is drawn.
- **Sample.** n = 400 chunks, drawn without replacement and uniformly across all papers by
  `random.Random(seed).sample` over the chunks in paper and file order. The first sample uses
  seed 20261012.
- **Reading.** The checker (GPT-6.1 Sol) reads each sampled chunk with the paper's rows. It
  reports any decisive release statement or identifier (D1 or D2) for a row. A report counts as a
  miss only when the provenance and identifier gate verifies it and the paper's cut text does not
  hold it.
- **Reported.** The number of chunks with a verified miss, and the exact hypergeometric one-sided
  95% upper bound on the number and share of affected chunks in the population. For 400 of
  49,280 chunks the bound is at most 366 chunks (0.74%) with 0 misses and 579 (1.17%) with 1
  miss.
- **Failure path.** Each verified miss is generalized to its wording class (the release phrase or
  identifier form that carried it) and added to the keep list as a new frozen version, logged
  before it is applied. The cut is then rerun mechanically and the containment test rerun. Both
  models re-code the papers whose cut text changed. A new sample of 400 chunks is drawn from the
  new removed text with the next registered seed (20261013, then 20261014).
- **Decision flow.**
  - A round with zero verified misses ends the diagnostic after that round.
  - A round with one or more verified misses triggers the refinement above (keep-list update,
    mechanical rerun of the cut and the containment test, re-coding of the changed papers) and
    the next seeded round.
  - Rounds are limited to three, with seeds 20261012, 20261013 and 20261014, and every round
    stays within the ceiling of 350 US dollars.
  - If the third round holds a verified miss, or the next round would cross the ceiling, the
    pipeline stops and reports, and the estimates carry the diagnostic's result.
  - No round reads whole supplements.

The registered rule "if C2 fails, both models code every cut supplement again under the
exhaustive whole-supplement pass" is withdrawn with C2. The exhaustive whole-supplement pass
remains the way a supplement given whole is read when it exceeds the input limit.

**3. The Maximum claim** is narrowed by one sentence: "It cannot state that the cut of a
supplement lost no decisive release statement in any paper; the removed-chunk miss-rate
diagnostic bounds only the share of removed chunks that hold one." The plan's statement of C2 (§Research
questions) becomes: "C2. The removed-chunk miss-rate diagnostic: the share of chunks of the text
the cut removes that hold a decisive release statement, with its exact upper bound."

**4. The cost ceiling** (Data collection procedures, Cost approval). The author approved full
containment on 13 October 2026, with a ceiling of 350 US dollars for this stage. It covers coding,
SA1, controls, the diagnostic and its failure path. If the estimate written after retrieval, or
the spending during the run, would exceed 350, the run stops before the request that would cross
it and waits for him. This replaces the registered approval line of 100 for this stage.

## Retention, as calibrated

`outputs/cut_containment_fullrow_calibration_2026-10-13.json` (ledger run
`rr_containment_fullrow_calibration_2026-10-13`):

| measure | registered cut | this cut |
|---|---|---|
| evidence units, whole row | 763,366 | 768,365; registered minus this cut = empty in every paper |
| characters read | 191.6M | 192.8M |

Every row the registered cut keeps is kept, except a row equal in every normalized cell to a kept
row of the same table. Identifiers and dictionary term sets are therefore all retained.

## Cost, as calibrated, against the ceiling of 350

US dollars, list prices and measured characters per token as in the plan. Headers are repeated per
request.

| line | Claude Sonnet 5.5 | GPT-6.1 Sol |
|---|---|---|
| coding (full texts and supplements as cut; 715 requests per model) | 166.60 | 106.14 |
| SA1 abstract-only pass | 5.14 | 4.69 |
| control-only papers (16 assumed) | 3.73 | 2.37 |
| removed-chunk diagnostic, 400 chunks | — | 9.03 |

The total is 297.70, which leaves 52.30 under the ceiling. Each further diagnostic round costs
about 9 dollars plus the re-coding of the papers whose cut text changed. The run stops before a
request that would cross 350.

**Variants calibrated, not adopted:**
- **Row-text unit** (the whole row without its numeric cells). Total 290.90. Rows differing from a
  kept row only in a numeric cell other than a count could be dropped.
- **Table rule without row text** (one row per set of dictionary terms, identifier values and
  count values). Total 147.73. It retains every such combination the registered cut retains, and
  loses 453,162 registered evidence units in 68 papers (494,417 rows, 112.5M characters), rows
  that differ from a kept row in their phenotype, analysis stage, protein or other text.
- **Full keep list with dictionary names, without row text.** Total 278.21.

## Foreknowledge

Seen before this amendment:

- the retrieval counts (204 records retrieved, 61 no source, 1 unreadable; sources by route;
  supplement files by type);
- the two cost estimates;
- the counts of seven mechanical calibrations of the cut: thresholds, the table rule, the keep
  list with the chunk population, the narrow keep list with the characters each pattern group
  adds, containment with the identifier signature rule, containment with the row text in the
  unit, and containment with the whole row in the unit.
  These cover retention counts, characters and identifier strings of public registries.

Four external review rounds of earlier drafts were read and their points are applied here; the
fourth confirmed this text. No supplement or full text was read for content. No row was coded and no model request was made.
The rule was chosen on cost and on these retention counts. Its effect on the resolution estimates
is not known.
