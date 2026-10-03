# Known-item set for the Paper 1 search (2026-09-30)

Assembled for PREREG.md §Data collection procedures, "Search validation". Each item was
identified from a title and PubMed or Europe PMC metadata only. No abstract was read, and no
protein, outcome, direction, dataset or platform was extracted from any item. "Why
eligible-looking" rests on the title and on facts already recorded in the project's
foreknowledge (items 1–3 only); for the other items eligibility is unverified.

Recall was tested by adding `AND <PMID>[uid]` to each registered PubMed query (Q1–Q4 as written
in PREREG.md, Q3 with its GEN block, DATE `"2019/01/01"[dp] : "2025/12/31"[dp]`), counts only.
Script: `known_item_recall.py`. Raw counts: `known_item_recall_2026-09-30.json`. Control:
`32895551[uid]` alone returned 1.

First-public year is the earlier of a preprint found by a Europe PMC title search (SRC:PPR,
metadata only) and the PubMed electronic or print date. eLife reviewed-preprint dates and
preprints with changed titles were not checked.

| # | PMID | DOI | first public | title | why eligible-looking (title and metadata only) | "proteome" in title | retrieved by | source |
|---|---|---|---|---|---|---|---|---|
| 1 | 32895551 | 10.1038/s41588-020-0682-6 | 2019 (bioRxiv 10.1101/627398, 2019-05-05) | Phenome-wide Mendelian randomization mapping the influence of the plasma proteome on complex diseases | foreknowledge item 7: 1,002 proteins, plasma pQTLs | yes | Q1, Q3, Q4 | Chen L 2022 and Yoshikawa 2024 reference lists |
| 2 | 36253349 | 10.1038/s41467-022-33675-1 | 2022 | Systematic Mendelian randomization using the human plasma proteome to discover potential therapeutic targets for stroke | foreknowledge item 7: 308 proteins in MR, Olink, INTERVAL | yes | Q1, Q3, Q4 | project foreknowledge |
| 3 | 39702585 | 10.1038/s42003-024-07403-y | 2024 | Systematic proteome-wide Mendelian randomization to prioritize causal plasma proteins for skin cancers | foreknowledge item 7: 735 instrumented proteins | yes | Q1, Q2, Q4 | project foreknowledge |
| 4 | 31208196 | 10.1161/CIRCULATIONAHA.119.040180 | 2019 | Novel Drug Targets for Ischemic Stroke Identified Through Mendelian Randomization Analysis of the Blood Proteome | MR of the blood proteome | yes | Q1, Q3 | Zheng 2020 reference list |
| 5 | 36864689 | 10.1093/brain/awad070 | 2023 | Potential drug targets for multiple sclerosis identified through Mendelian randomization analysis | drug-target MR screen; protein basis not stated in title | no | **none** | Yoshikawa 2024 reference list; Zheng 2020 citing papers |
| 6 | 38576019 | 10.1186/s12967-024-04919-z | 2024 | Systematic proteome-wide Mendelian randomization using the human plasma proteome to identify therapeutic targets for lung adenocarcinoma | proteome-wide MR, plasma proteome | yes | Q1, Q3, Q4 | Yoshikawa 2024 reference list |
| 7 | 38049731 | 10.1186/s12885-023-11669-6 | 2023 | Proteome-wide analysis reveals potential therapeutic targets for Colorectal cancer: a two-sample mendelian randomization study | proteome-wide two-sample MR | yes | Q1, Q3 | Yoshikawa 2024 reference list |
| 9 | 36388766 | 10.1016/j.xgen.2022.100195 | 2022 (medRxiv, 2022-01-11) | Proteome-wide Mendelian randomization in global biobank meta-analysis reveals multi-ancestry drug targets for common diseases | proteome-wide MR, multi-ancestry | yes | Q1, Q3, Q4 | OpenAlex scoop query D, title |
| 10 | 36510323 | 10.1186/s13073-022-01140-9 | 2022 | Mendelian randomization and genetic colocalization infer the effects of the multi-tissue proteome on 211 complex disease-related phenotypes | proteome MR; multi-tissue, so plasma component uncertain | yes | Q1, Q3, Q4 | PubMed scoop query, title |
| 11 | 36736436 | 10.1053/j.gastro.2023.01.028 | 2021 (medRxiv, 2021-03-11) | Proteome-Wide Mendelian Randomization Identifies Causal Links Between Blood Proteins and Acute Pancreatitis | proteome-wide MR of blood proteins | yes | Q1, Q2, Q3, Q4 | PubMed scoop query, title |
| 12 | 37652020 | 10.1016/j.xcrm.2023.101174 | 2023 | Plasma proteins and onset of type 2 diabetes and diabetic complications: Proteome-wide Mendelian randomization and colocalization analyses | proteome-wide MR of plasma proteins | yes | Q1, Q4 | PubMed scoop query, title |
| 13 | 37726845 | 10.1186/s13073-023-01229-9 | 2022 (Research Square, 2022-12-21) | Identification of novel protein biomarkers and drug targets for colorectal cancer by integrating human plasma proteome with genome | plasma proteome with genome | yes | Q1, Q3, Q4 | PubMed scoop query, title |
| 14 | 37429843 | 10.1038/s41467-023-39253-3 | 2022 (medRxiv, 2022-04-18) | Genome-wide association analysis and Mendelian randomization proteomics identify drug targets for heart failure | MR proteomics for drug targets | no ("proteomics") | Q1, Q3, Q4 | PubMed scoop query, title |
| 15 | 39068416 | 10.1186/s12885-024-12659-y | 2024 | Associations between genetically predicted concentrations of plasma proteins and the risk of prostate cancer | genetically predicted plasma proteins | no | Q1, Q3 | PubMed scoop query, title |
| 16 | 41247789 | 10.7554/eLife.101584 | 2025 (eLife reviewed preprint not checked) | Causal associations between human plasma proteins and prostate cancer identified by proteome-wide Mendelian randomization | proteome-wide MR of plasma proteins | yes | Q1, Q2, Q3, Q4 | PubMed scoop query, title |
| 17 | 41286868 | 10.1186/s12890-025-04006-z | 2025 | Potential drug targets for chronic obstructive pulmonary disease in the plasma proteome identified through Mendelian randomization | plasma proteome MR | yes | Q1, Q2, Q3, Q4 | PubMed scoop query, title |
| 18 | 37996402 | 10.1038/s41467-023-43485-8 | 2023 | Evaluation of circulating plasma proteins in breast cancer using Mendelian randomisation | MR of circulating plasma proteins | no | Q1, Q3 | web search, title |
| 19 | 36280454 | 10.1016/j.biopsych.2022.08.015 | 2022 | Circulating Proteins Influencing Psychiatric Disease: A Mendelian Randomization Study | MR of circulating proteins | no | Q1, Q3, Q4 | Zheng 2020 citing papers |
| 20 | 34758976 | 10.2337/dc21-1049 | 2022 (issue date; online date not in PubMed record) | Clinically Relevant Circulating Protein Biomarkers for Type 1 Diabetes: Evidence From a Two-Sample Mendelian Randomization Study | two-sample MR of circulating proteins | no | Q1 | Zheng 2020 citing papers |
| 21 | 38184718 | 10.1038/s42003-023-05737-7 | 2024 | Mendelian randomization identifies circulating proteins as biomarkers for age at menarche and age at natural menopause | MR of circulating proteins | no | Q1, Q4 | Zheng 2020 citing papers |
| 22 | 40037332 | 10.1093/brain/awaf018 | 2025 | Mendelian randomization identifies proteins involved in neurodegenerative diseases | MR of proteins; tissue not stated in title | no | Q1, Q2, Q4 | Zheng 2020 citing papers |
| 23 | 39806440 | 10.1186/s12931-024-03086-5 | 2024 (Research Square, 2024-10-14) | Potential drug targets for asthma identified through mendelian randomization analysis | drug-target MR screen; protein basis not stated in title | no | Q1, Q3, Q4 | Zheng 2020 citing papers |
| 24 | 39541108 | 10.1167/tvst.13.11.17 | 2024 | Potential Drug Targets for Diabetic Retinopathy Identified Through Mendelian Randomization Analysis | drug-target MR screen; protein basis not stated in title | no | Q1, Q2, Q3, Q4 | Zheng 2020 citing papers |
| 25 | 38762700 | 10.1038/s41598-024-62178-w | 2024 | Potential drug targets for tumors identified through Mendelian randomization analysis | drug-target MR screen; protein basis not stated in title | no | Q1, Q3, Q4 | Zheng 2020 citing papers |

Coverage: 24 items (item 8 removed, below); first public 2019 (2), 2021 (1), 2022 (7), 2023 (4),
2024 (7), 2025 (3). Item numbers are kept as first assigned.
Eleven titles lack "proteome" (items 5, 14, 15, 18–25), ten of them lack the stem "proteom"
altogether, which meets the prereg's quarter. Journals include Nat Genet, Nat Commun, Commun Biol,
Circulation, Brain, Gastroenterology, Cell Genomics, Cell Rep Med, Genome Med, Biol Psychiatry,
Diabetes Care, eLife and several BMC and Scientific Reports titles. Platform coverage cannot be
established without reading abstracts, except for item 2 (Olink) and items 1 and 3 (Zheng 2020
resource); it is left to the eligibility stage.

## Recall result

24 of 25 items are retrieved by at least one query; Q1 alone retrieves 24. Q2 retrieves 6, Q3 19
and Q4 18.

**Recall failure: item 5, PMID 36864689** (Lin J et al. 2023, Brain). Retrieved by no query.
Term-presence counts on the record (`36864689[uid] AND <term>`, counts only, no text read):
"Mendelian randomization" 1, "drug target*" 1, colocali* 1, plasma 1, protein* 1, proteins 1;
"plasma protein*" 0, proteom* 0, pQTL* 0, "quantitative trait loci" 0, deCODE 0. The record uses
"plasma" and "protein(s)" but never adjacently as "plasma protein", and names no pQTL or platform
term, so PROT, PLAT and PQTLB all miss it.

**Proposed minimal change, not applied:** add `(plasma[tiab] AND protein*[tiab])` to the PROT block
of Q1, i.e. Q1 = `(MR) AND (PROT OR (plasma[tiab] AND protein*[tiab])) AND DATE`. It retrieves item
5 and adds 163 PubMed records for 2019–2025 not already in Q1 (count only;
`known_item_recall_fix_options_2026-09-30.json`). It translates to Europe PMC and OpenAlex as plain
Boolean. The alternative, proximity terms such as `"plasma proteins"[tiab:~3]` (with circulating,
blood and serum variants), also retrieves item 5 and adds 172 records, but PubMed proximity syntax
has no exact Europe PMC or OpenAlex equivalent, so the block-for-block translation would diverge.

## Removed

| # | PMID | DOI | title | reason | date |
|---|---|---|---|---|---|
| 8 | 35300523 | 10.1161/CIRCULATIONAHA.121.056663 | Therapeutic Targets for Heart Failure Identified Using Proteomics and Mendelian Randomization | The abstract states 90 proteins tested, below the registered 100-protein floor; genuine ineligibility found by the eligibility-only known-item check (r5, 2026-09-30), not a prompt error | 2026-09-30 |
