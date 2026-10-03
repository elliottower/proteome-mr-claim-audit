# Reading of the quotations `citations verify` warns about (2026-10-02)

`citations verify --claims claims/` before this reading: 4,470 quotations, 4,470 found, 0 not
found; warnings 1,541 short, 26 truncated, 5 normalized. A warning is a note about the quotation,
not a failure: the passage is in the source. Each warned quotation was read against its source
text to see whether what follows it changes what it is quoted for. No pinned quotation was
edited; where a fuller passage was needed it was pinned as a new claim beside the old one
(`citations pin`, which refuses a passage that does not resolve). After the reading: 4,499
quotations, 4,499 found, 0 not found.

## Truncated (26)

A quotation is `truncated` when it ends inside a word or a number in the source.

- **24 end at a reference superscript.** The extracted text glues the reference numbers to the
  last word ("participants2,3,7,10,16", "PLINK v1.9116,117", "757,601 individuals20"), so the
  quotation stops at the word and the "number" it cuts is the reference list. No digit of a
  reported number is cut and no qualifier is dropped. In one of them
  (`malik2018megastroke_supp_info#helsinki-controls-finrisk`) the sentence goes on after the
  reference ("participants residing in the same geographic area"), which does not change the
  cohort the controls come from.
- **`howson2017cad_main#denovo-aa`** stops inside a consortium name ("Myocardial Infarctio").
  The full sentence is pinned as `denovo-aa-full`.
- **`schumacher2018practical_supp#st1-trofinn`** is one line of a wrapped table cell and stops
  at a line-break hyphen ("The Nord-"). The cell through "(HUNT 2 and 3)" is pinned as
  `st1-trofinn-hunt`.

Neither re-pinned quotation changes a cohort list.

## Normalized (5)

Matched after ignoring punctuation and spacing: three line-break hyphens ("arterial- wall",
"meta- analyses", "meta- analysis"), one reference title quoted without its last clause, and one
soft hyphen ("cis-­pQTLs"). None changes the meaning.

## Short (1,541)

A quotation is `short` when it has fewer than 40 characters or ends in a connective. 1,529 of
the 1,541 are under 40 characters, and they are the first cells of a table row that name a
cohort in a consortium's study list.

**Sample.** 60 quotations, drawn across claims files in proportion to their number of short
quotations, seed 20261002 (`short_quote_sample_2026-10-02.json`). Read in context: all 60 are
row labels, table cells or list headings, and the text that follows gives counts, design or
genotyping. In 0 of 60 does the following text change what the quotation is quoted for.
Four sampled rows carry a footnote marker.

**Every short quotation.** Because the sample showed footnote markers, all 1,541 were then
scanned: the rest of each quotation's own table row (or, in laid-out tables, the 220 characters
after it) for words of exclusion, replication, follow-up, stage or overlap, and each quotation
for a footnote marker. 124 rows were flagged and read. Quality-control, phenotype-definition and
descriptive-statistics cells account for all but the following.

| source | rows | what the row or legend says | pinned before | now |
|---|---|---|---|---|
| GIGASTROKE Supplementary Table 1 (`mishra2022gigastroke_supp_table1`) | SiGN (WHI); HISAYAMA_ASN | "incident (only, not included in global meta-analysis)" | no | row pinned through that cell (`st1-sign-whi-row`, `st1-hisayama-asn-row`) |
| same | ARIC_AA, CHS_AA, REGARDS_SIGNET_AA, JHS_AA, INTERSTROKE_AA | "(not included for prevalent AS, as in COMPASS)" | no | rows pinned through that cell (`st1-*-aa-row`) |
| MAGIC Supplementary Table 1 (`chen2021magic_supp_table1`) | Oxford Biobank, UKHLS, VIKING, Whitehall II | "VarExp only - as per protocol" in the Data Analyses columns; "Yes" under "Contributed to variance explained analysis?" | no | both cell runs and the two header cells pinned (`c_*_analysis`, `c_*_analysis_options`, `header_*`) |
| PGC-PTSD Supplementary Data 1 (`nievergelt2019ptsd_supp_data1`) | 12 rows marked `*` | "* included in PGC PTSD freeze 1 (#47: GTPC only partially)" | no | legend pinned |
| FinnGen Supplementary Table 2, PGC bipolar Supplementary Table 1, Wightman Supplementary Table 1, Deloukas Supplementary Table 1, Roselli Supplementary Table 17 | rows marked `*` or `**` | legends on consent route, trio design, public availability, descriptive statistics, analysis model | no | legends pinned |
| GIGASTROKE, Demontis 2019, MEGASTROKE | rows marked `*` or `**` | legends | yes | unchanged |

27 claims were added for these rows and legends, and 2 for the truncated quotations.

## Two component lists the readings bear on

The readings above do not change `verification/dataset_components.csv`; they are recorded here
because two of its lists include cohorts whose own table row limits their contribution.

- **GIGASTROKE (Mishra 2022) lists `WHI`.** The SiGN (WHI) European sample is "incident (only,
  not included in global meta-analysis)"; the Supplementary Appendix also describes a WHI
  African-American sample. `HISAYAMA` carries the same note in its incident-only row and has a
  second row without it.
- **MAGIC (Chen 2021) lists `OXFORD_BIOBANK`, `UKHLS`, `VIKING` and `WHITEHALL2`.** Their
  analysis cells read "VarExp only - as per protocol".

A component list names every participant source of a dataset, and a source that is listed joins
the overlap comparison, so keeping these cohorts makes two datasets less likely to be classed
`disjoint`, never more.
