# The 14 platform rows: three checks

Each of the 14 pQTL rows of the dataset dictionary whose platform string names no pinned list
was coded by reading the dataset's own source paper (§Manual coding of dataset names in
PREREG.md), with three checks:

1. Claude Code read the source paper and coded the platform and protein list, with the
   sentence pinned with `citations` (2026-10-01; `PLATFORM_LOOKUPS.md`, `platform_lookups.csv`).
2. Perplexity read the source papers blind to the coded value (round 6, 2026-10-02) and agreed
   with the platform on all 14 rows; it asked for the analysed rather than the whole-panel list
   on 7 rows, which was done, and round 7 confirmed every final background.
3. The author confirmed each row on 2026-10-03 (rows 4 and 10 on 2026-10-02): the confirmation
   is a literal match of the value the quoted sentence states to the coded value, as PREREG.md
   defines it. On ten rows the quoted count equals the coded count. Row 2 is confirmed as 92
   proteins measured, the 90 analysed not being identifiable; row 4 as the annotation-linked
   proxy; row 10 as the 257 analysed rows of Supplementary Data 7; row 11 as the 184 proteins of
   Supplementary Data 8.

In `verification/platform_assay_attachments.csv` the 14 rows have status `coded`.

On six rows (2, 4, 6, 10, 11, 13) the quoted sentence supports the platform and the headline
count, and the final protein list is derived from the supplementary table or companion paper
named under "List derived from", not from the sentence itself. For rows 2 and 4 the authors
were asked for the missing list (2026-10-02 and 2026-10-03); PREREG.md registers when a list
they supply can replace the background.

"Level" is where the protein list comes from: **analysed** = the study's own list of proteins
that entered its analysis; **assayed** = the study's list of proteins measured, with the
analysed ones not marked.

---

**1. Fenland, Pietzner 2020 (COVID-19 host proteins)**
- Sentence: "Of the 409 proteins prioritized, 179 were detectable by the currently
  most-comprehensive proteomic assay using an aptamer-based technology (SomaScan©), including 28
  recognized by more than one aptamer (i.e., 179 proteins recognized by 190 aptamers)."
- Our value: SomaScan v4; the 179 proteins the study reports.
- Perplexity: agrees.
- Final background: the 179-protein study list (175 reviewed accessions). Level: analysed.

**2. SCALLOP CVD-I, Folkersen 2020**
- Sentence: "Ninety proteins in up to 21,758 participants from 13 cohorts passed quality
  control (QC) criteria and were available for GWAS meta-analysis [Supplementary Table 1]."
- Our value: Olink CVD-I panel, 92 proteins measured, 90 analysed.
- Perplexity: platform correct; wants the 90 analysed proteins as background.
- Final background: the 92 measured proteins. Level: assayed. **Not done as asked:** the
  paper's table lists all 92 and does not mark the 2 that failed quality control, and the text
  does not name them, so the list of 90 cannot be formed.
- List derived from: the paper's Supplementary Table 1 (the 92 proteins measured). The quoted
  sentence supports the 90 analysed, not the 92-protein list.
- Perplexity, round 7: qualified yes; keep `assayed`.

**3. SCALLOP meta-analysis, Koprulu 2026**
- Sentence: "Finally, we performed an inverse-variance fixed-effects meta-analyses (with
  METAL) for 1,161 protein targets (with overlapping UniProt ID across different antibody-based
  platforms offered by Olink) using summary level data from SCALLOP meta-analyses and UKB".
- Our value: 13 Olink Target 96 panels, meta-analysed with UK Biobank Olink Explore 1536.
- Perplexity: agrees on platform; wants the proteins in the reported meta-analysis if they
  differ from the 13-panel union.
- Final background: the 1,161 targets of the paper's Table S5 (1,034 reviewed accessions; the
  13-panel union has 1,071). Level: analysed.

**4. AGES, Emilsson 2018**
- Sentence: "This resulted in an updated array of 5034 SOMAmers, 4783 of which recognize 4137
  individual human proteins (table S1)".
- Our value: custom SomaScan array; list taken from Gudjonsson 2022 (same array and samples),
  because this paper's own table is in a supplementary PDF that cannot be fetched.
- Perplexity: qualified agreement; call the list an annotation-linked proxy (4,118 targets
  against 4,137 proteins).
- Final background: the Gudjonsson 2022 list (4,146 reviewed accessions), labelled an
  annotation-linked proxy. Level: assayed.
- List derived from: Gudjonsson et al. 2022, Supplementary Data 6 (a later paper on the same
  array and samples). The quoted sentence supports the 4,137 proteins of the original array, not
  that list.
- Perplexity, round 7: qualified yes; "annotation-linked proxy" is the permanent label.

**5. AGES, Gudjonsson 2022**
- Sentence: "thus the 4782 SOMAmers are annotated to a total of 4118 unique targets (annotated
  as one or more Entrez gene symbols)".
- Our value: the same custom SomaScan array; the 4,118 targets of Supplementary Data 6.
- Perplexity: agrees.
- Final background: that list (4,146 reviewed accessions). Level: analysed.

**6. KORA, Suhre 2017**
- Sentence: "Five of the probes failed SOMAscan QC, leaving a total of 1,124 probes for analysis
  (Supplementary Table 1)."
- Our value: SOMAscan V3.2; the 1,124 analysed probes.
- Perplexity: agrees; asked that the file name be reconciled.
- Final background: the 1,124 probes (1,124 reviewed accessions). The paper cites
  Supplementary Table 1; the file read is Supplementary Dataset 2, the annotation of the same
  1,124 probes. Level: analysed.
- List derived from: Supplementary Dataset 2 (the annotation dataset corresponding to the
  supplementary table the sentence cites). The quoted sentence supports the count of 1,124.
- Perplexity, round 7: qualified yes.

**7. Framingham Heart Study, Yao 2018**
- Sentence: "A list of the 71 proteins and their coefficients of variation and selection
  criteria were shown in Supplementary Data 1."
- Our value: Luminex immunoassays; 85 assayed, 71 analysed.
- Perplexity: agrees; background should be 71.
- Final background: the 71 analysed proteins (70 reviewed accessions). Level: analysed.

**8. IMPROVE, Folkersen 2017**
- Sentence: "After QC, a total number of 83 proteins out of the 92 remained for analysis (full
  overview in supplementary S3 Table)."
- Our value: Olink ProSeek CVD array I; 92 on the panel, 83 analysed.
- Perplexity: agrees on platform; use 83.
- Final background: the 83 proteins marked "Included: yes" in S3 Table (82 reviewed
  accessions). Level: analysed. The 9 left out: CASP8, IL1RN, IL4, ITGB1BP2, PTX3, S100A12,
  SELPLG, SIRT2, TNFRSF1A.

**9. Zheng 2020 instrument set**
- Sentence: "we retained 2,113 pQTLs for 1,699 proteins as instruments for the MR analysis
  (Supplementary Table 1)".
- Our value: no assay of its own; the 1,699 proteins that have an instrument.
- Perplexity: agrees; the union of the five source studies' assays is the sensitivity analysis.
- Final background: the 1,699 instrumented proteins (1,725 reviewed accessions). Level:
  analysed.

**10. MANOLIS, Gilly 2020**
- Sentence: "The serum levels of 275 unique proteins in 1407 MANOLIS samples from three Olink
  panels—CVDII, CVDIII and Metabolism—were measured using Olink's proximity extension assay
  (PEA) technology".
- Our value: Olink CVD II, CVD III and Metabolism; 275 measured, 257 after quality control.
- Perplexity: agrees on platform; use 257.
- Final background: the 257 rows of Supplementary Data 7 marked "not excluded" (258 reviewed
  accessions). Level: analysed.
- List derived from: Supplementary Data 7. The quoted sentence supports the 275 proteins
  measured; the 257 analysed rows come from the supplementary table.
- Perplexity, round 7: qualified yes.

**11. MANOLIS and Pomak, Png 2021**
- Sentence: "We included all proteins and all below-LOD NPX values in our analysis."
- Our value: Olink Neurology and Neuro-exploratory; 184 proteins, all analysed.
- Perplexity: agrees; asked why 184 proteins gave 185 accessions.
- Final background: the study's own Supplementary Data 8 (184 reviewed accessions). The 185
  came from the commercial panel file, where one protein carries two accessions; the study's
  list has 184. Level: analysed.
- List derived from: Supplementary Data 8. The quoted sentence ("all proteins") does not state
  184; the supplementary table does.
- Perplexity, round 7: qualified yes; the 184-against-185 difference is resolved.

**12. NSPHS, Enroth 2014**
- Sentence: "After individual and protein quality control, 77 proteins measured in 970
  individuals remained."
- Our value: Olink Proseek Multiplex Oncology I; 92 on the panel, 77 analysed.
- Perplexity: agrees on platform; use 77.
- Final background: the 77 analytes named by the phenotypes of Supplementary Data 2 (77
  reviewed accessions). Level: analysed.

**13. Jackson Heart Study, Katz 2022**
- Sentence (same authors, Sci Adv 2022): "Proteomic measurements were performed using
  Soma1.3K, a single-stranded DNA aptamer-based proteomic platform, which contained 1305
  aptamers (43). Nonhuman proteins were excluded from analysis (N = 4) for a final count of
  1301."
- Our value: SomaScan 1.3k; 1,301 protein measures.
- Perplexity: **disagreed with the list**: the generic 1,063-accession list is too incomplete;
  recover the study's own list or mark the row unavailable.
- Final background: a companion-paper, study-specific analysis-eligible background: the 1,301
  reagents of Table S2 of the same authors' Jackson Heart Study paper in Sci Adv (1,297 UniProt
  identifiers, 1,296 reviewed accessions). The supplement of the Circulation paper itself is not
  open access, so each reagent's final quality-control status in the pQTL analysis is not
  confirmed from it. Level: analysed. The 1,063-accession list is kept only for a sensitivity
  analysis.
- List derived from: Katz et al. 2022 (Sci Adv) Table S2, the companion paper, not the
  Circulation supplement.
- Perplexity, round 7: qualified yes, with that label.

**14. Guangzhou Nutrition and Health Study, Xu 2023**
- Sentence: the GWAS covers "levels of 304 proteins in four sub-cohorts of GNHS".
- Our value: SWATH/DIA mass spectrometry; 304 proteins.
- Perplexity: agrees.
- Final background: the 304 protein-level rows of Supplementary Data 2 (304 reviewed
  accessions). Level: analysed.
