# Verification of the Perplexity report (2026-09-30)

Subject: a Perplexity report on auditing proteome-wide MR claims, dated 2026-09-30 (read in full,
1,923 lines). The report is one of the author's working files and is not in this repository.
Performed 2026-09-30. Pinned quotations are in `claims/*.yaml` at the repository root
(`citations` CLI); the full texts they resolve against are in `sources/`, which is not
redistributed. `citations verify --claims claims` on the day: 58 quotes, 58 found, 0 not found,
0 unchecked. Quoted strings attributed to "the report" are quotations of the Perplexity report
itself, not of a source, and are not pinned. The `scoop/` folder named below (full texts and raw
query outputs) is also a working folder outside the repository; the four texts in it that carry
pins are in `sources/`.

Sources were retrieved through the Europe PMC REST full-text endpoint, OpenAlex, the bioRxiv API
and institutional repositories. No email address was sent in any request.

## 1. Scoop search

**Verdict: open, with one partial precedent outside proteomics.** No paper from 2019 to
30 Sep 2026 was found that samples other groups' published proteome-wide pQTL–disease MR claims and
re-runs them through a uniform pipeline. Full texts are in `scoop/`; raw query outputs are in
`scoop/search_logs/`.

Coverage caveat: OpenAlex anonymous keyword search was paused for the whole session, and no
OpenAlex key was available. The search used Europe PMC (including preprints), PubMed E-utilities and
Semantic Scholar. OpenAlex was used only for DOI lookups and for the citing papers of Gibson 2023
(19), Stender 2024 (48) and Burgess 2024 (99). **Rerun the OpenAlex keyword search before the
freeze.**

### Closest papers (full text read unless stated)

| Paper | What it does | How it differs from the planned audit |
|---|---|---|
| Nguyen TN, Terry L, Guggenheim JA. Mendelian Randomization Studies of Myopia: Choosing the Right Summary Statistics. IOVS 2025;66(13):57. doi 10.1167/iovs.66.13.57; PMID 41171040; PMC12582192 | Re-analyzes other groups' published MR claims | Single disease, no proteins. 8 of 35 papers, selected by criteria in Suppl. Note S6 (not read), not a probability sample. One factor varied (outcome GWAS). No colocalization, platform or cohort replication, or overlap check |
| Liu Y, Burton J, Gatua W, Hemani G, Gaunt TR. MR-KG: a knowledge graph of Mendelian randomization evidence powered by large language models. medRxiv 2025, doi 10.64898/2025.12.14.25342218 | Direction agreement between published abstracts on the same trait pair | Nothing re-run. LLM extraction from abstracts; the unit is a trait pair |
| Yang J, Han C, Zhang Y, et al. Mendelian randomization studies on ischemic stroke: a field synopsis and systematic review. J Transl Med 2025. doi 10.1186/s12967-025-06992-4; PMC12374473 | Grades 1,199 published MR associations from 207 studies on reported methods | No re-analysis. Not proteomic |
| Sobczyk MK, Zheng J, Davey Smith G, Gaunt TR. Systematic comparison of Mendelian randomisation studies and randomised controlled trials using electronic databases. BMJ Open 2023. doi 10.1136/bmjopen-2023-072087; PMC10533809 | Compares published MR directions with RCT directions. Its pQTL arm covers only Zheng 2020 targets | No MR re-run |
| Liu Y, Gaunt TR. Triangulating evidence in health sciences with Annotated Semantic Queries. Bioinformatics 2024. doi 10.1093/bioinformatics/btae519; PMC11377847 | Checks 412 claim triples from medRxiv abstracts against precomputed MR-EvE evidence | Generic claims. No reconstruction, colocalization or platform replication |
| Chen J, Zhao J, Fu S. Addressing sample overlap … a critical appraisal of protein targets for myocardial infarction. Eur Heart J 2025. doi 10.1093/eurheartj/ehaf186 | Single-paper critique of a proteome-MR claim set (overlap) | **Not read** (closed access). Only proteome-specific re-appraisal found. Obtain before the freeze |

Quotations, all pinned in `claims/nguyen2025.yaml`, `claims/liu2025mrkg.yaml` and `claims/sobczyk2023.yaml`:

- Nguyen, Methods, Part 2: "we re-analyzed selected published MR studies using our newly derived
  myopia GWAS summary statistics" and "we adhered to the analysis plan outlined in the original
  articles".
- Nguyen, Results: "From 35 published MR studies that used GWAS summary statistics of myopia
  case-control status, we selected eight studies that met our criteria for re-analysis
  (Supplementary Note S6)."
- Nguyen, Discussion: "Only one out of eight re-analyses generated findings that were consistent
  with the original study."
- MR-KG, Results: "2,075 unique exposure" (the trait-pair count) and "20.2 percent (n=419)
  demonstrate discordant results".
- Sobczyk, Abstract: "a series of 26 manual literature comparisons among 54 MR and 77 RCT
  publications".
- Yang, Abstract: "a total of 207 published studies with 1199 MR associations were included". This
  quotation did not pin through the CLI. It was read in `scoop/yang2025_stroke_synopsis.txt`
  line 22 and is unverified by the tool.

Other hits:

- Single-paper re-analyses of other groups' MR, not systematic:
  - Xiang et al. 2024, J Transl Med, PMC10964565 (read).
  - Zhang B 2024, Eye, PMC11461607 (not read; body blocked).
  - Yang Q / Borges / Lawlor letters, PMIDs 38818841 and 37957108 (abstracts only).
- Commentary and bibliometric papers (read; nothing re-run):
  - Hemani et al. 2025, Eur J Epidemiol, PMC12660478.
  - Burgess et al. 2024, BMC Med, PMC11389083.
  - Spick et al. 2026, J Clin Epidemiol, PMC13178217.
- Not relevant after reading:
  - Khunsriraksakul 2025 (pQTL atlas).
  - Lee 2025 (dementia MR meta-analysis of reported estimates).
  - Liu 2025 (vitiligo umbrella review).
  - Sud & Houlston 2026.
  - Wen 2026.
- Not read: Wu T 2024, Heart (a systematic review pooling published protein-MR estimates; blocked).
  It needs reading, because pooling published estimates is adjacent.

Consequence for the novelty statement: cite Nguyen 2025 as the precedent for re-analyzing other
groups' MR claims (1 of 8 consistent), and scope the claim to "a probability sample of published
proteome-wide pQTL–MR claims, evaluated under multiple prespecified checks". The Perplexity report
missed Nguyen 2025, MR-KG, ASQ, the stroke field synopsis and Chen 2025.

## 2. Report citations

### Summary

| Report item | Paper (authors; identifier) | Status |
|---|---|---|
| (a) 116-paper MR audit, "attempt direct replications" | Gibson MJ, Spiga F, Campbell A, Khouja JN, Richmond RC, Munafò MR. Reporting and methodological quality of studies that use Mendelian randomisation in UK Biobank: a meta-epidemiological study. BMJ Evid Based Med 2023;28(2):103. doi 10.1136/bmjebm-2022-112006; PMID 36600446; PMC10086297 | Verified. Scope misdescribed (see below) |
| (b) Stender 2024 | Stender S, Gellert-Kristensen H, Davey Smith G. Reclaiming mendelian randomization from the deluge of papers and misleading findings. Lipids Health Dis 2024;23:286. doi 10.1186/s12944-024-02284-w; PMID 39244551; PMC11380209 | Verified (punctuation differs) |
| (c) Munafò 2024 | Munafò MR, Brown J, Hefler M, Davey Smith G. Managing the exponential growth of mendelian randomization studies. Tob Control 2024;33(5):559–560. doi 10.1136/tc-2024-058987; PMID 39313311. Co-published Addiction doi 10.1111/add.16627 (PMID 39311417) and Nicotine Tob Res | Verified quote; the "Recommendations" section does not exist |
| (d) Burgess 2016 | Burgess S, Davies NM, Thompson SG. Bias due to participant overlap in two-sample Mendelian randomization. Genet Epidemiol 2016;40(7):597–608. doi 10.1002/gepi.21998; PMID 27625185; PMC5082560 | Verified (quote is from the Abstract, trimmed); the report omits the paper's rule on the overlap denominator |
| (e) Pietzner 2021: 61%, 81.2%, 44.2% | Pietzner M, Wheeler E, Carrasco-Zanini J, Cortes A, Koprulu M, Wörheide MA, Oerton E, Cook J, Stewart ID, Kerrison ND, Luan J, Raffler J, Arnold M, Arlt W, O'Rahilly S, Kastenmüller G, Gamazon ER, Hingorani AD, Scott RA, Wareham NJ, Langenberg C. Mapping the proteo-genomic convergence of human diseases. Science 2021;374:eabj1541. doi 10.1126/science.abj1541; PMID 34648354; PMC9904207 | Numbers verified. Design misdescribed; the "earlier matched-sample, 64%" row is wrong |
| (f) Eldjarn 2023: 616/1,097 and 248/616 | Numbers are in Hjörleifsson Eldjárn G, Ferkingstad E, et al. bioRxiv doi 10.1101/2022.02.18.481034, v1 (20 Feb 2022), which the authors **withdrew** on 15 Mar 2022. The published paper (Eldjarn GH, Ferkingstad E, Lund SH, et al. Large-scale plasma proteomics comparisons through genetics and disease associations. Nature 2023;622:348–358. doi 10.1038/s41586-023-06563-x; PMID 37794188; PMC10567571) does not contain them | **Wrong source**: numbers exist only in a withdrawn preprint; cohort misdescribed as "deCODE Olink" |
| (g) Katz 2022: 64% shared pQTLs, 871 proteins | Katz DH, Robbins JM, Deng S, Tahir UA, Bick AG, Pampana A, Yu Z, Ngo D, Benson MD, Chen ZZ, Cruz DE, Shen D, Gao Y, Bouchard C, Sarzynski MA, Correa A, Natarajan P, Wilson JG, Gerszten RE. Proteomic profiling platforms head to head: leveraging genetics and clinical traits to compare aptamer- and antibody-based methods. Sci Adv 2022;8(33):eabm5164. doi 10.1126/sciadv.abm5164; PMID 35984888; PMC9390994 | **Wrong**. Neither 64% nor 871 appears in Katz |
| (extra) Sun 2023: 95.6%/64.1%, 934/1,116, 1,877/4,978, 54,219 | Sun BB, Chiou J, Traylor M, et al. Plasma proteomic associations with genetics and health in the UK Biobank. Nature 2023;622:329–338. doi 10.1038/s41586-023-06592-6; PMID 37794186; PMC10567551 | Verified |

### (a) Gibson et al. 2023, BMJ Evidence-Based Medicine

Full text: Europe PMC fullTextXML, `sources/gibson2023.txt`. Pins: `claims/gibson2023.yaml`.

- Abstract, Conclusions: "Future research should focus on the quality of code and analyses, attempt
  direct replications and investigate the impact of the STROBE-MR specifically."
  The report's "Future research should…attempt direct replications" is a faithful elision.
- Abstract, Results: "116 articles were included in this review. The proportion of articles which
  reported complete information/adequate methodology ranged from 3% to 100% across the different
  items." The report drops "across the different items"; otherwise verbatim.
- Abstract, Methods: "Data were extracted using a 25-item checklist relating to reporting and
  methodological quality".
- Results: "Overall, the mean article completeness was 55% (SD = 9%)."
- Protocol identifier OSF.IO/NWRDJ is in the article (verified).

Scope correction. The report calls this the closest precedent for a re-analysis audit and describes
the sample as MR "in UK Biobank". The article's own aim: "The aim of our study is to assess whether
published articles that conduct MR analyses using individual-level data from the UKB cohort use
appropriate analyses and report enough details to allow accurate interpretation and replication"
(Introduction). The sample is individual-level UKB MR, not two-sample summary-data MR, and no
estimate was recomputed. The reporting-frequency table the report copies (13%, 53%, 65%, 86%, ...)
describes that population, not pQTL-MR. The spot-checked values (13% assumptions, 53% one- vs
two-sample, 65% variants and weights, 86% estimator) match the article.

### (b) Stender, Gellert-Kristensen, Davey Smith 2024, Lipids in Health and Disease

Full text: Europe PMC (PMC11380209), `sources/stender2024.txt`. Pins: `claims/stender2024.yaml`.
Article type: Comment.

- Abstract: "These studies add minimal – if any – value and overwhelm reviewers and journals."
  The report prints em-dashes without spaces; the source has spaced en-dashes. Wording identical.
- Final paragraph: "Sadly, MR has run off the rails." Verbatim.
- Main text: "A decade ago, there were about 100 MR papers published annually. In 2023, this number
  exceeded 3,000, and it will reach almost 5,000 in 2024 (Fig. 1)."
- Fig. 1 caption: "Number of papers identified using the search term ‘Mendelian randomization’ in
  PubMed, stratified by year." The counts are PubMed hits for the phrase, and 2024 is a projection.

### (c) Munafò, Brown, Hefler, Davey Smith 2024

Full text: publisher PDF of the Tobacco Control version (Flinders University repository),
`sources/munafo2024_flinders.pdf` and `.txt`. Pins: `claims/munafo2024.yaml`.

- p. 560, col. 1: "We therefore suggest that MR studies that simply use summary GWAS data to estimate
  the causal effect of X on Y should be given a low priority for publication unless they genuinely
  advance knowledge."
- p. 560, col. 1: "incorporating negative controls and/or evidence from other study designs such as
  natural experiments, and collaborating with biologists to advance plausible biological mechanisms."

The report's quote is a faithful elision. The report's location "Section: Recommendations" is
wrong: the editorial has no section headings. The article states it is co-published in Addiction,
Tobacco Control and Nicotine & Tobacco Research, and that "The articles are identical except for
minor stylistic and spelling differences in keeping with each journal’s style."

### (d) Burgess, Davies, Thompson 2016, Genetic Epidemiology

Full text: Europe PMC (PMC5082560), `sources/burgess2016.txt`. Pins: `claims/burgess2016.yaml`.

- Abstract: "For a continuous outcome, bias due to sample overlap is a linear function of the
  proportion of overlap between the samples." The report prints a shortened, re-capitalized
  version and places it in "Results/Discussion".
- Abstract: "is less biased and any bias is in the direction of the null".
- Abstract: "if the relative bias of the one‐sample instrumental variable estimate is 10%
  (corresponding to an F parameter of 10), then the relative bias with 50% sample overlap is 5%,
  and with 30% sample overlap is 3%." The report's paraphrase is correct.
- Section 6.1: "If the datasets are of different size, then the percentage overlap in these
  formulae should be taken with respect to the larger dataset". The report omits this.
- Section 6: "With a binary outcome, provided that the IV–risk factor associations are estimated in
  the control participants only, bias due to sample overlap is negligible and Type 1 error rates are
  at nominal levels."

### (e) Pietzner et al. 2021, Science

Full text: Science First Release PDF (Helmholtz Munich repository),
`sources/pietzner2021_science_firstrelease.txt`; accepted manuscript with Methods (University of
Birmingham copy), `sources/pietzner2021_birmingham_aam.txt`. Europe PMC fullTextXML returned HTTP 500
for PMC9904207. Pins: `claims/pietzner2021.yaml`, `claims/pietzner2021aam.yaml`.

- Results, "Genetic associations for protein targets": "Further, 61% (488 out of 797, table S2) of
  pQTLs replicated using the complementary Olink technique (see supplementary materials), with a
  higher proportion of replication for variants in cis (81.2%) compared to trans (44.2%)."
  Numbers verified. The report's second quote, "81.2%…in cis…compared to trans (44.2%)", reorders
  the source ("in cis (81.2%)"); it is not verbatim.
- Methods (AAM), "Replication using the Olink PEA technology": "we used in-house GWAS results for
  1,069 proteins measured using Proximity Extension Assays provided by Olink in a subset of 485
  individuals of the Fenland study" and "We identified 797 pQTLs that a) mapped to proteins covered
  on the Olink platform (N=543) and b) were significant at p-value<0.01" in that subset.

Two errors in the report:

1. The 61% is a same-individual comparison in 485 Fenland participants, restricted to SNP–protein
   pairs already nominally significant (p < 0.01) on SomaScan in those 485. It is not an
   independent-cohort replication. The report's table ("Fenland SomaScan, compared with Olink data")
   does not say so.
2. The row "Pietzner et al., earlier matched-sample comparison | 871 proteins in 485 people | 64% of
   pQTLs consistent across platforms" merges two different sentences. The source says "We have
   previously provided a detailed comparison of 871 overlapping proteins measured in 485 individuals
   (10)" (ref. 10 = Pietzner et al., bioRxiv 435919, "Cross-platform proteomics to advance genetic
   prioritisation strategies"), and separately "64% (867 out of 1,356 pQTLs) available in (4)
   replicated (p < 0.05, directionally consistent)", where ref. 4 is Sun et al. 2018 (INTERVAL,
   SomaScan). The 64% is **same-platform, different-cohort** replication of newly reported regions,
   not cross-platform concordance.

Data availability sentence verified: "Summary statistics can be obtained from
www.omicscience.org/apps/pgwas."

### (f) Eldjarn et al.

Published paper: Nature 2023, Europe PMC (PMC10567571), `sources/eldjarn2023.txt`.
Preprint: bioRxiv 10.1101/2022.02.18.481034 v1 JATS XML, `sources/eldjarn2022_biorxiv_v1.txt`;
v2 PDF is a one-page withdrawal notice, `sources/eldjarn2022_biorxiv_v2_withdrawal_notice.pdf`.
Pins: `claims/eldjarn2023.yaml`, `claims/eldjarn2022preprint.yaml`, `claims/eldjarn2022withdrawal.yaml`.

The report's two quotes resolve in the **withdrawn preprint v1** only:

- "Of the 1,097 proteins targeted with both SomaScan v4 and Olink Explore, 616 (56%) had a cis pQTL
  detected using the two platforms. For 248 of these 616 proteins (40%), the sentinel cis pQTLs
  detected using SomaScan v4 and Olink Explore were in high LD (r2>0.80)".
- "this is based on 541 replicating and 85 non-replicating pQTLs, while for cis pQTLs detected using
  the Olink Explore platform and replicated using the SomaScan v4 platform, this is based on 519
  replicating and 238 non-replicating pQTLs." (also v1 only)

Withdrawal notice (v2, 15 Mar 2022): "The authors have withdrawn this manuscript because this paper
was posted prematurely in advance of a UK Biobank Pharma Proteomics Project consortium effort.
Therefore, the authors do not wish this work to be cited as reference for the project."

Cohort error. The preprint's Olink data are UK Biobank, not deCODE: "Olink Explore 1536 (1,459
immunoassays) in 47,151 European participants from the UK Biobank" (Summary). The report's table
labels the study "deCODE Olink and SomaScan" and its cohort table lists "deCODE Olink | Olink Explore
| Icelandic; 47,151 in the large comparison | 1,459 assays".

Published Nature 2023 equivalents (use these):

- Introduction: "Here we compare two affinity-based platforms, Olink Explore 3072 using data from the
  UK Biobank (UKB) generated by the UKB Pharma Proteomics Project (UKB-PPP) and SomaScan v4 generated
  in Iceland" and "We analysed SomaScan v4 data for plasma samples from 35,892 Icelanders, where 1,514
  of the samples were also measured using the Olink Explore 3072 platform."
- Results, "Relationship of pQTLs between platforms": "In the UKB-BI Olink data, 581 (40%) out of
  1,468 sentinel cis pQTL signals had a corresponding pQTL in the Icelandic SomaScan data, and in 434
  cases (30%) the pQTL was the sentinel signal at the locus." and "In the SomaScan data, 559 (48%)
  out of 1,164 sentinel cis pQTL signals had a corresponding pQTL in the UKB-BI Olink data, and in
  449 cases (39%) the pQTL was the sentinel signal at the locus." Then: "Thus, even when pQTLs for a
  protein are detected on both platforms, they are not necessarily the same."
- Discussion: "Even where cis pQTLs provide evidence that both platforms are measuring the targeted
  protein, in more than half of the cases, the top associated variants were in low LD."
- Results, protein–phenotype associations: "Of note, NFL levels measured with both the Olink and
  SomaScan platforms correlate strongly with Alzheimer’s disease, but with opposite directions of
  effect." (a direct example of platform-dependent direction for the audit's direction check).

### (g) Katz et al. 2022, Science Advances

Full text: Europe PMC (PMC9390994), `sources/katz2022.txt`, read in full through the Discussion.
Pins: `claims/katz2022.yaml`.

The report's row ("Same participants, 871 overlapping proteins | 64% of pQTLs shared") is wrong.
Katz profiled "a subset of JHS participants (N = 568) using both aptamer-based and antibody-based
methods" on SomaScan 1.3K and Olink Explore 1536, "revealing 591 overlapping proteins mapping to 602
Soma1.3K aptamers and 597 Olink probes". The pQTL result is "At this threshold, 164 of the reagent
pairs show a cis pQTL for both reagents" (of 616 pairs, P < 1e-5) and "At this threshold, 98 reagent
pairs have cis pQTLs for both reagents" (P < 5e-8). No 64% and no 871 appear. The "N = 485
overlapping samples" in Katz is a citation of Pietzner et al.'s cross-platform paper (ref. 18).
The 871/485 figures belong to Pietzner et al.'s own cross-platform comparison (bioRxiv 435919,
ref. 10 of Pietzner 2021); Katz cites a Nat Commun paper by Pietzner et al., "Synergistic insights
into human health from aptamer- and antibody-based proteomic profiling", for N = 485. Neither was
downloaded here, so whether that comparison reports a 64% figure is not read.

### Sun et al. 2023 (checked because the report's table uses it)

`sources/sun2023.txt`, `claims/sun2023.yaml`. All verified verbatim: "characterizing the plasma
proteomic profiles of 54,219 UK Biobank participants"; "A total of 95.6% (1,869 out of 1,955) of cis
and 64.1% (7,906 out of 12,332) of trans associations remained significant"; "84% (934 out of 1116)
of the previous associations were replicated in our discovery study"; "38% of previous associations
replicated in our discovery study (1,877 out of 4,978 associations, across 1,982 proteins)".

## 3. Errors in the report that change the design

1. **No large deCODE Olink resource.** The report's replication hierarchy puts "deCODE Olink:
   independent cohort, same broad assay technology" first for UKB-PPP claims, on the strength of a
   "deCODE Olink, Icelandic, 47,151" row. The 47,151 were UK Biobank participants. The published
   Eldjarn paper has 1,514 Icelanders on Olink Explore 3072, a subset of the SomaScan cohort. The
   same-platform, independent-cohort check for UKB-PPP (Olink) claims needs a different Olink cohort,
   and its power at N ≈ 1,500 is limited. Cross-platform replication (UKB-PPP Olink vs deCODE or
   Fenland SomaScan) remains feasible.
2. **Cross-platform benchmark numbers must come from the published Nature paper.** 616/1,097 and
   248/616 are from a withdrawn preprint the authors ask not be cited. The published figures are
   581/1,468 (40%) and 559/1,164 (48%) sentinel cis pQTLs with a corresponding pQTL on the other
   platform, over 1,848 shared proteins.
3. **Katz and "Pietzner earlier" rows are wrong**; the 64% is same-platform (INTERVAL) replication,
   and Pietzner's 61% Olink figure is same-individual (n = 485) with a p < 0.01 pre-filter. None of
   these is an independent-cohort cross-platform rate. Any prior-expectation or power calculation
   built on "64% cross-platform concordance" is built on a misattribution.
4. **Overlap denominator.** Burgess et al. take the overlap fraction "with respect to the larger
   dataset". The report's claim that "from the exposure-GWAS perspective the overlap can be nearly
   complete", and its proposed "overlap divided by the exposure sample" field, run against this.
   For UKB-PPP pQTLs against a full-UKB disease GWAS, the relevant fraction is the UKB-PPP N over
   the outcome GWAS N; where the cis-pQTL F-statistic is large the expected bias is small (our
   inference from the Burgess formula, not a number in any source read here).
   The overlap check should record overlap relative to the larger sample and the F-statistic,
   and report expected bias from the Burgess formula rather than a binary overlap flag.
5. **Closest precedent is narrower than stated.** Gibson et al. audited individual-level UKB MR
   reporting and recomputed nothing. It supports the "attempt direct replications" framing, but it
   is not a two-sample or pQTL-MR precedent.
