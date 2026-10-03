# Platform lookups for the 14 unattached pQTL rows

2026-10-01. Resource-only work: each dataset's own source paper, no proteome-wide MR paper, no
claim. No abstract-based fallback is used: the platform of a dataset is read from the dataset's
source paper and decided here.

These are the lookups as made on 2026-10-01. The backgrounds registered afterwards follow the
analysed, assayed, platform hierarchy of PREREG.md and are recorded per row in
`experiments/02_claims_meta/verification/platform_assay_attachments.csv`; where that table
differs from a decision below, the table holds.

Machine-readable table: `docs/stage0_build/platform_lookups.csv` (one row per dictionary
row, with the list file, URL and sha256 where a new list is needed).

## How each row was read

For each row the open full text was fetched (Europe PMC `fullTextXML`, or NCBI `efetch db=pmc`
for author manuscripts), converted to one paragraph per line, and the section that describes the
protein measurement was read. Sentences are pinned with `citations pin` in
`claims/<key>.yaml` against `sources/<key>.txt`.
`citations verify --claims claims` over every claims file: all found.

Where a study names a supplementary file as its protein list, that file was opened to confirm
its identifier column and row count. The files are small (18 KB to 8.8 MB), are not in the
repository, and are not on the Modal volume; the CSV gives URL and sha256 for each.

## Rule used for the decision

The assay list of a row is the set of proteins that the release reports pQTL results for, as
assayed: the commercial panel where the study ran a whole panel, the study's own list where it
ran a custom array, a non-commercial method, or a stated subset. Proteins dropped at quality
control stay on the list (the pinned commercial lists are whole panels too); the count after
quality control is recorded beside it.

## Decisions

| # | dictionary row | platform as the source states it | decision | status | confidence |
|---|---|---|---|---|---|
| 1 | Fenland SomaScan v4 (Pietzner 2020, COVID-19 host proteins) | SomaScan v4, 4,979 aptamers; analysis restricted to 179 candidate proteins (190 aptamers) | study list of 179 proteins (`fenland_covid_179`), a subset of SomaScan v4 | new list needed | high |
| 2 | SCALLOP CVD-I (Folkersen 2020) | Olink CVD-I panel; 90 proteins passed QC | `olink_target_96:CVD I`, 92 proteins, from Folkersen 2020 Supplementary Table 1 | new list needed | high |
| 3 | SCALLOP multi-cohort meta-analysis (Koprulu 2026) | 13 named Olink Target 96 panels (1,194 targets), meta-analysed with UK Biobank Olink Explore 1536 (1,161 overlapping) | union of the 13 pinned Target 96 panels | attach now (pinned union) | high |
| 4 | AGES Reykjavik (Emilsson 2018) | custom SomaScan array, 5,034 SOMAmers, 4,783 human, 4,137 proteins | AGES custom list (`somascan_ages_custom`) from Gudjonsson 2022 Supplementary Data 6 | new list needed | high for platform; medium for list |
| 5 | AGES Reykjavik (Gudjonsson 2022) | the Emilsson 2018 array; 4,782 SOMAmers, 4,135 proteins, 4,118 unique targets | the same AGES custom list | new list needed | high |
| 6 | KORA (Suhre 2017) | SOMAscan assay V3.2, 1,129 SOMAmers, 1,124 analysed; KORA F4 | study list of 1,124 probes (`somascan_v3.2_kora`) from Supplementary Dataset 2 | new list needed | high |
| 7 | Framingham Heart Study (Yao 2018) | Luminex xMAP multiplex immunoassays; 85 assayed, 71 analysed | study list of 71 proteins (`fhs_luminex_71`) from Supplementary Data 1 | new list needed | high |
| 8 | IMPROVE (Folkersen 2017) | Olink ProSeek CVD array I; 92 on panel, 83 analysed | `olink_target_96:CVD I` (the list of row 2) | new list needed | high |
| 9 | Zheng 2020 proteome-wide MR instrument set | no platform: instruments curated from five pQTL studies | the 1,699 instrumented proteins of Supplementary Table 1 (`zheng2020_instrumented_1699`) | new list needed | medium |
| 10 | MANOLIS (Gilly 2020) | Olink CVD II, CVD III and Metabolism; 275 unique proteins, 257 after QC | union of the three pinned Target 96 panels | attach now (pinned union) | high |
| 11 | MANOLIS and Pomak neurology (Png 2021) | Olink Neurology and Neuro-exploratory; 184 proteins, all analysed | union of the two pinned Target 96 panels | attach now (pinned union) | high |
| 12 | NSPHS (Enroth 2014) | Olink Proseek Multiplex Oncology I; 92 on panel, 77 analysed | study list of 92 proteins (`olink_proseek_oncology_I`) from Supplementary Data 1 | new list needed | high |
| 13 | Jackson Heart Study (Katz 2022) | SomaScan 1.3k; 1,305 aptamers, 1,301 after removing 4 non-human | pinned `somascan_1.3k` | attach now (approximate) | high for platform; medium for list |
| 14 | Guangzhou Nutrition and Health Study (Xu 2023) | SWATH/DIA mass spectrometry; 304 proteins | study list (`gnhs_swath_ms_304`) from Supplementary Data 2 | new list needed | high |

Every row is decided from its source. Four rows can be attached from lists already pinned; ten
need eight new list files (rows 2 and 8 share a list, rows 4 and 5 share a list).

## Entries

### 1. Fenland SomaScan v4 (Pietzner 2020, COVID-19 host proteins)

- Source: Pietzner et al. 2020, Nat Commun, PMC7744536. Claims file `pietzner2020covid.yaml`.
- Quote (`platform-v4`, Methods: Proteomic profiling): "Relative protein abundances of 4775 human
  protein targets were evaluated by 4979 aptamers (SomaLogic V4), and a detailed description can
  be found elsehwere43."
- Quote (`subset-179`, Results): "Of the 409 proteins prioritized, 179 were detectable by the
  currently most-comprehensive proteomic assay using an aptamer-based technology (SomaScan©),
  including 28 recognized by more than one aptamer (i.e., 179 proteins recognized by 190
  aptamers)."
- The Olink data cover 32 of the 179 proteins in 485 participants and serve the cross-platform
  comparison (`olink-subset`, `olink-12-panels`); the pQTL discovery is SomaScan.
- Decision: platform SomaScan v4. The release holds pQTL results for the 179 proteins only, so
  the list is those 179 (Supplementary Data 1, sheet SD1, `SOMAmer target` = 1: 179 rows,
  `UniProtID` column), not the full v4 list.
- Confidence: high.

### 2. SCALLOP CVD-I (Folkersen 2020)

- Source: Folkersen et al. 2020, Nat Metab, PMC7611474. Claims files `folkersen2020scallop.yaml`,
  `folkersen2020scallop_supp_table1.yaml`.
- Quote (`platform-cvd1`, Online Methods: Cohorts and data collection): "Summary statistics from
  GWAS of Olink CVD-I proteins were obtained from 13 cohorts of European ancestry."
- Quote (`proteins-90`, Results): "Ninety proteins in up to 21,758 participants from 13 cohorts
  passed quality control (QC) criteria and were available for GWAS meta-analysis [Supplementary
  Table 1]."
- Supplementary Table 1 (sheet `1 Protein_info`, "Information about all measured proteins") has
  116 protein rows with a `UniProt ID` column and panel flags; 92 rows carry `CVDI` = Y.
- Decision: Olink Target 96 CVD I, 92 proteins. The pinned pQTLdata Target 96 file has no CVD I
  panel, and neither has its `Olink_qPCR` table (12 panels: Cardiometabolic, Cell Regulation,
  CVD II, CVD III, Development, Immune Response, Immuno-Oncology, Inflammation, Metabolism,
  Neurology, Oncology II, Organ Damage), so this table is the list.
- Confidence: high.

### 3. SCALLOP multi-cohort meta-analysis (Koprulu 2026)

- Source: Koprulu et al. 2026, Cell, PMC13343581. Claims file `koprulu2026scallop_fulltext.yaml`
  (existing; four claims added).
- Quote (`panels-13`, STAR Methods): "For the 37 cohorts included in this study, antibody-based
  proteomic measurements were generated through at least one of the 13 Target-96 panels offered
  by Olink measuring 92 protein targets (Cardiometabolic, Cardiovascular II, Cardiovascular III,
  Cell Regulation, Development, Immuno-oncology, Inflammation, Immune Response, Metabolism,
  Neurology, Neuro Exploratory, Organ Damage, Oncology II)."
- Quote (`ukb-explore-1536`): "In UKBB, the proteomic measurements used in this study were
  generated through Olink Explore 1536 platform utilizing the same antibody-based technology but
  measuring a broader coverage of 1,463 protein targets."
- Quote (`overlap-1161`): the overall meta-analysis covers "1,161 protein targets (with
  overlapping UniProt ID across different antibody-based platforms offered by Olink)".
- Decision: the union of the 13 named panels, all 13 of which are pinned (`CAM`, `CVD II`,
  `CVD III`, `CRE`, `DEV`, `IMO`, `INF`, `IRE`, `MET`, `NEU`, `NEX`, `ODA`, `ONC II`; the pinned
  `ONC III` is not among them). The union is the 1,194-target SCALLOP set; the 1,161 targets of
  the overall meta-analysis are its intersection with `olink_explore_1536` and lie inside it.
- Confidence: high. The paper is dated 2026, so the row can only be cited by update-set papers.

### 4. AGES Reykjavik (Emilsson 2018)

- Source: Emilsson et al. 2018, Science, PMC6190714 (author manuscript; main text only, methods
  in a supplementary PDF). Claims file `emilsson2018ages.yaml`.
- Quote (`platform-custom`): "We designed an expanded custom version of this platform to include
  proteins known or predicted to be found in the extracellular milieu".
- Quote (`somamers-5034`): "This resulted in an updated array of 5034 SOMAmers, 4783 of which
  recognize 4137 individual human proteins (table S1)".
- Decision: a custom SomaScan array that is neither the 1.3k assay nor commercial v4, so neither
  pinned list is substituted. List: the AGES list of row 5. Table S1 of this paper is inside the
  PMC supplementary PDF, which Europe PMC's supplement service does not return; Gudjonsson 2022 measures the same
  samples on the same array "as previously described" and its list is open.
- Confidence: high for the platform; medium for the list, which differs from Table S1 by one
  SOMAmer and two proteins on the papers' own counts (4,783 against 4,782; 4,137 against 4,135).

### 5. AGES Reykjavik (Gudjonsson 2022)

- Source: Gudjonsson et al. 2022, Nat Commun, PMC8789779. Claims file `gudjonsson2022ages.yaml`.
- Quote (`platform`, Methods: Protein measurements): "Serum levels of 4135 human proteins,
  targeted by 4782 SOMAmers50, were determined at SomaLogic Inc. (Boulder, US) in samples from
  5457 AGES-Reykjavik participants as previously described8."
- Quote (`targets-4118`): "thus the 4782 SOMAmers are annotated to a total of 4118 unique targets
  (annotated as one or more Entrez gene symbols)".
- Decision: the AGES custom array. List: Supplementary Data 6 ("Protein annotations used for
  enrichment analysis"), 4,118 rows keyed by Entrez gene symbol, so it enters through the
  registered HGNC to UniProt step.
- Confidence: high.

### 6. KORA (Suhre 2017)

- Source: Suhre et al. 2017, Nat Commun, PMC5333359. Claims file `suhre2017kora.yaml`.
- Quote (`platform-v3-2`, Methods: Proteomics measurements): "Data for 1,129 SOMAmer probes
  (SOMAscan assay V3.2) was obtained for these samples."
- Quote (`probes-1124`): "Five of the probes failed SOMAscan QC, leaving a total of 1,124 probes
  for analysis (Supplementary Table 1)."
- Quote (`kora-f4`): the sample is 1,000 participants of KORA F4, which answers the dictionary
  note "KORA survey wave not stated in the passages read".
- Decision: SOMAscan V3.2, the 1.1k assay. The pinned `somascan_1.3k` is a later, larger assay
  and is not substituted. List: Supplementary Dataset 2 ("Annotation of the SOMAmer probes"),
  1,124 probe rows with a `UniProt` column (multi-protein targets are space-separated).
- Confidence: high.

### 7. Framingham Heart Study (Yao 2018)

- Source: Yao et al. 2018, Nat Commun, PMC6093935. Claims file `yao2018fhs.yaml`.
- Quote (`platform-luminex`, Methods: Protein quantification): "A total of 85 plasma protein
  biomarkers were assayed using a modified enzyme-linked immunosorbent assay sandwich method,
  multiplexed on a Luminex xMAP platform (Luminex, Inc., Austin, TX)."
- Quote (`list-71`): "A list of the 71 proteins and their coefficients of variation and selection
  criteria were shown in Supplementary Data 1."
- Decision: a custom Luminex immunoassay set with no commercial panel. List: the 71 proteins of
  Supplementary Data 1 (gene symbols only; the 14 excluded proteins are not listed there, so the
  list is the analysed set).
- Confidence: high.

### 8. IMPROVE (Folkersen 2017)

- Source: Folkersen et al. 2017, PLoS Genet, PMC5393901. Claims file `folkersen2017improve.yaml`.
- Quote (`platform-cvd1`): "Plasma concentrations were measured in baseline EDTA plasma samples
  using the ProSeek CVD array I (Olink Biosciences, Uppsala, Sweden), according to the standard
  protocol."
- Quote (`proteins-83-of-92`): "After QC, a total number of 83 proteins out of the 92 remained for
  analysis (full overview in supplementary S3 Table)."
- Decision: the Olink CVD I panel of row 2 (`olink_target_96:CVD I`, 92 proteins). S3 Table is a
  PDF keyed by gene symbol with an `Included` column, usable if the analysed 83 are wanted.
- Confidence: high.

### 9. Zheng 2020 proteome-wide MR instrument set

- Source: Zheng et al. 2020, Nat Genet, PMC7610464. Claims file `zheng2020pwmr.yaml`.
- Quote (`five-gwas`): "pQTLs from five GWAS9,13-16 were used for the instrument selection
  (Fig. 1)."
- Quote (`instruments-1699`): "we retained 2,113 pQTLs for 1,699 proteins as instruments for the
  MR analysis (Supplementary Table 1)".
- Two candidate lists:
  - **Instrumented proteins.** Supplementary Table 1 (`TableS1.Instruments`), 1,699 proteins
    with `UNIPROT` and `Study` columns.
  - **Assayed proteins.** The union of the five component lists (INTERVAL `somascan_160410`,
    KORA row 6, AGES row 4, IMPROVE row 8, FHS row 7).
- Decision: the instrumented proteins. A paper that takes its instruments from this set can test
  only the proteins in Supplementary Table 1, which is what the row releases; the five studies'
  full assays are not what a user of this row has.
- Confidence: medium. The platform reading is certain (there is none); the choice of universe is
  a judgment, and the assayed-proteins union is the alternative.

### 10. MANOLIS (Gilly 2020)

- Source: Gilly et al. 2020, Nat Commun, PMC7729872. Claims file `gilly2020manolis.yaml`.
- Quote (`platform-three-panels`, Methods: Proteomics): "The serum levels of 275 unique proteins
  in 1407 MANOLIS samples from three Olink panels—CVDII, CVDIII and Metabolism—were measured
  using Olink’s proximity extension assay (PEA) technology9."
- Decision: union of pinned `olink_target_96:CVD II`, `olink_target_96:CVD III`,
  `olink_target_96:MET`. The study's own table (Supplementary Data 7: 275 rows, 257 "not
  excluded", `Uniprot ID` column) is available if the analysed set is preferred.
- Confidence: high.

### 11. MANOLIS and Pomak neurology (Png 2021)

- Source: Png et al. 2021, Nat Commun, PMC8640022. Claims file `png2021helic.yaml`.
- Quote (`platform-two-panels`, Methods: Proteomics and QC): "Proteins from Olink’s
  (https://www.olink.com) Neurology and Neuro-exploratory panels were measured in the serum of
  1457 MANOLIS and 1611 Pomak samples."
- Quote (`all-included`): "We included all proteins and all below-LOD NPX values in our analysis."
- Decision: union of pinned `olink_target_96:NEU` and `olink_target_96:NEX`. Supplementary
  Data 8 lists the same 184 proteins (92 `NEU`, 92 `NEX`) with `uniprot_ID`.
- Confidence: high.

### 12. NSPHS (Enroth 2014)

- Source: Enroth et al. 2014, Nat Commun, PMC4143927. Claims file `enroth2014nsphs.yaml`.
- Quote (`platform-onc1`, Methods: Multiplexed PEA): "Protein levels in plasma were analysed
  using the Olink Proseek Multiplex Oncology I 96 × 96 kit and quantified by real-time PCR using
  the Fluidigm BioMark HD real-time PCR platform as described earlier10."
- Quote (`remained-77`): "After individual and protein quality control, 77 proteins measured in
  970 individuals remained."
- Decision: Olink Proseek Oncology I, 92 proteins. No pinned file holds this panel (pQTLdata has
  Oncology II and III only). List: Supplementary Data 1, sheet `Analytes`, `UniprotID` column.
- Confidence: high.

### 13. Jackson Heart Study (Katz 2022)

- Source: Katz et al. 2022, Circulation, PMC9158509 (author manuscript). Claims file
  `katz2022jhs.yaml`. The main text sends the platform description to the Supplemental Methods
  (`profiling`), a PDF the default client cannot fetch from PMC or Europe PMC.
- Quote (`measures-1301`, Results): "We performed whole genome association analysis between 28.1
  million variants with an allele count in JHS of at least 5 and 1,301 plasma protein measures in
  1852 self-identified Black individuals (61% women)."
- The version is stated by the same authors in Katz et al. 2022, Sci Adv (`katz2022.yaml`,
  existing; two claims added), whose reference 21 is the Circulation paper:
  - (`jhs-soma13k-discovery`) "Our group has previously described the genetic architecture of
    the circulating plasma proteome from JHS, leveraging the SomaScan1.3K (1301 aptamers, herein
    “Soma1.3K”) platform for discovery and the Olink Explore (1472 probes, herein “Olink”)
    platform for validation (21)"
  - (`soma13k-1305`) "Proteomic measurements were performed using Soma1.3K, a single-stranded DNA
    aptamer-based proteomic platform, which contained 1305 aptamers (43). Nonhuman proteins were
    excluded from analysis (N = 4) for a final count of 1301."
- Decision: SomaScan 1.3k; attach pinned `somascan_1.3k`. That list is the 1,158 aptamers of
  Eldjarn 2023 ST2 flagged `on_1.2k` (1,063 accessions), against 1,301 aptamers mapping to 1,297
  UniProt identifiers on the assay as run, so it is an approximation of the assay list. The exact
  list is a table of the Circulation supplement.
- Confidence: high for the platform; medium for the list.

### 14. Guangzhou Nutrition and Health Study (Xu 2023)

- Source: Xu et al. 2023, Nat Commun, PMC9935862. Claims file `xu2023gnhs.yaml`.
- Quote (`platform-swath`, Methods: Circulating proteomics profiling): "Peptide samples were then
  analyzed by SWATH-MS over a 20 min linear LC gradient on a TripleTOF 5600 system (SCIEX, CA,
  USA) coupled to Eksigent NanoLC 400 System (Eksigent, Dublin, CA, USA)."
- Quote (`proteins-304`, Results): the GWAS covers "levels of 304 proteins in four sub-cohorts of
  GNHS".
- Decision: untargeted mass spectrometry, no panel. List: Supplementary Data 2, protein-level
  rows (`Sequence of peptide` = NULL), `UniProtKB ID` column. The file has 305 such rows against
  304 in the text; the difference of one row is not explained in the passages read.
- Confidence: high.

## Names that cover several rows

Before these lookups the bare names "Fenland", "SCALLOP", "AGES" and "KORA" gave no list. With
the decisions above:

| bare name | candidate rows | reading |
|---|---|---|
| Fenland | Pietzner 2021 (SomaScan v4, 4,775 targets); Pietzner 2020 (the 179-protein subset of the same assay and participants) | One platform, SomaScan v4. The 2020 row is a subset of the 2021 row, so the bare name takes `somascan_v4`. The Olink measurements (485 participants) are a comparison set in both papers, with no pQTL release of their own. |
| AGES | Emilsson 2018; Gudjonsson 2022 | One array and one list (`somascan_ages_custom`). |
| KORA | Suhre 2017 | One row, one list (`somascan_v3.2_kora`). |
| SCALLOP | Folkersen 2020 (CVD I); Zhao 2023 (Inflammation); Koprulu 2026 (13 panels) | One platform, Olink Target 96, but three different panel sets, and the name alone does not say which. The sources cannot settle this for a given claim paper; it is a registry rule (whether a release-ambiguous name takes the union of its candidates' lists or none), and not a platform fact. |

## Notes

- These lookups added 14 claims files and 14 source texts (13 papers and the Folkersen 2020
  Supplementary Table 1); `katz2022.yaml` and `koprulu2026scallop_fulltext.yaml` gained claims.
- One quotation would not pin because it occurs twice in its source ("Annotation of the SOMAmer
  probes.", the caption of Suhre 2017 Supplementary Dataset 2); the file itself was opened.
- Eight list files would need to go on the Modal volume and into `platform_assay_lists.csv`:
  Pietzner 2020 SD1, Folkersen 2020 ST1, Gudjonsson 2022 SD6, Suhre 2017 Dataset 2, Yao 2018 SD1,
  Zheng 2020 ST1, Enroth 2014 SD1, Xu 2023 SD2. The copies examined on 2026-10-01 were not
  kept; the files were fetched to the volume afterwards (RELEASES.md).
- Gudjonsson SD6 and Yao SD1 carry gene symbols, not UniProt accessions.
- The dictionary's platform strings for rows 4 to 6 and 13 name no version; the sources give
  "custom array" (AGES), "SOMAscan assay V3.2" (KORA) and "SomaScan 1.3k" (JHS).
- Small lists and the 10–500 pathway-size rule: rows 1, 2, 7, 8 and 12 have 71 to 179 proteins,
  so few or no pathways will pass on their own backgrounds (the build reported 5 for `INF` and 0
  for `NEU`). Their lists mainly affect the pooled background.
- Not checked: whether the sha256 of the pinned Target 96 panels on the volume matches the
  mirror copy for every file. `Olink_qPCR.rda` was compared and matches
  (`fd149ab5…f999ba`).
