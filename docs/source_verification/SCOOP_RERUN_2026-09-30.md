# Scoop rerun before the Paper 1 freeze (2026-09-30)

Subject: the novelty sentence in `experiments/02_claims_meta/PREREG.md`, §Context and additional
information, and the three pre-freeze checks it names: the OpenAlex keyword search, Chen, Zhao and
Fu 2025 (Eur Heart J), and the blocked systematic review in `VERIFICATION.md` (Wu T 2024, Heart).

Raw query output, request logs and full texts are in `scoop/rerun_2026-09-30/` (`logs/`, `texts/`),
a working folder outside this repository; the four texts that carry pins are in `sources/`,
which is not redistributed. New pins are in `claims/wu2024heart.yaml`,
`claims/zheng2025dmrdb.yaml`, `claims/shi2025triangulator.yaml` and `claims/zhu2025letter.yaml`.
`citations verify --claims claims` on the day, after the pins: 123 quotes, 123 found, 0 not
found. No email address was sent in any request; no browser automation and no user-agent
spoofing were used.

## Verdict

**The novelty sentence needs one precedent added and one component removed.** Wu et al. 2024
(Heart), the review that was blocked in the first session, pooled published protein–disease MR
estimates across 35 studies, graded 1,614 pairs, and looked up indication-specific
drug-development status for the resulting 291 pairs. That is a cross-paper synthesis of published
protein MR claims with a drug-development join, restricted to six cardiometabolic outcomes and
built from full-text estimates rather than abstract claims. It does not count exact-pair
repetition, directional contradiction between MR papers, agreement on independent data, or
dataset reuse; it excludes overlapping cohorts rather than measuring overlap. The
"indication-specific drug-development records" clause of the current sentence therefore has a
precedent and should leave the list of what is new. DMRdb (Zheng et al. 2025) curates causal pairs
from 166 published eQTL/pQTL MR studies but compares none of them, and belongs among the closest
precedents. Nothing found assembles abstract claims across all diseases or quantifies repetition,
contradiction, independent-data agreement or dataset reuse.

Proposed replacement for the sentence:

> Searches of PubMed, Europe PMC (including preprints), Semantic Scholar and OpenAlex, 2019 to
> 2026-09-30 (`docs/source_verification/VERIFICATION.md`,
> `SCOOP_RERUN_2026-09-30.md`), identified no study that assembled protein–outcome claims from the
> abstracts of proteome-wide plasma or serum pQTL-MR papers across diseases and quantified
> exact-pair repetition, directional contradiction, agreement on independent data and reuse of
> identical source datasets under prespecified automated rules. The closest precedents are Wu et
> al. 2024, which pooled published MR estimates for protein–cardiometabolic disease pairs from 35
> studies and looked up their drug-development status; Liu et al. 2025 (MR-KG), which measured
> direction discordance across general MR abstracts; Zheng et al. 2025 (DMRdb), which curates
> causal pairs from 166 published eQTL and pQTL MR studies; and Nguyen, Terry and Guggenheim 2025,
> Sobczyk et al. 2023 and Liu and Gaunt 2024.

Two consequences outside the sentence:

1. **Foreknowledge.** Wu 2024 was read in full on 2026-09-30, including its drug-development
   counts (3 of 291 pairs with an approved matching indication, 288 without a record) and its
   heterogeneity figure for pooled MR pairs (14.2% with I² ≥ 80%). Both bear on descriptive
   outcomes (drug-development records) and on H1's territory (cross-paper agreement), and belong
   in §Foreknowledge before the freeze. Sobczyk and Gaunt 2026 (Sci Rep), read in full as a scoop
   candidate, is a pQTL-MR paper first public in 2026 and could enter the update set; its reading
   should be recorded there too.
2. **The last sentence of the current paragraph** ("Before the freeze, the OpenAlex keyword search
   is rerun, Chen, Zhao and Fu 2025 … is read, and the blocked systematic review … is inspected")
   describes pending work that this rerun completes, except that Chen 2025's full text was not
   read (below).

## Searches run

| source | what | output |
|---|---|---|
| OpenAlex (API key, no email) | 6 keyword searches on `title_and_abstract.search` from 2019-01-01: (A) redundancy, duplication, research waste, meta-research, field synopsis; (B) contradiction, discordance, concordance with published studies; (C) knowledge graph, LLM, text or literature mining; (D) clinical trials, drug development, approved drugs with systematic review; (E) systematic, scoping, umbrella review, evidence map, bibliometric; (F) replicability, reproducibility, sample overlap, credibility | `logs/oa_A.txt` … `oa_F.txt`: 12, 18, 33, 56, 14, 32 hits |
| OpenAlex | 1 DOI lookup (9 works), 1 forward-citation query (citing Wu 2024, Chen 2025, MR-KG, Zhu 2025: 6 works), 2 content-endpoint PDF requests | `logs/oa_G_lookup.json`, `logs/oa_H_citing.json` |
| Europe PMC | 13 queries covering the same concepts, one restricted to preprints | `logs/epmc_1.txt` … `epmc_13_preprints.txt` |
| PubMed | 8 queries, including letters and comments on protein MR | `logs/pm_1.txt` … `pm_8.txt` |
| web | 3 plain web searches | nothing new |

OpenAlex requests used: 10 (8 API, 2 content), logged in `logs/openalex_requests.log`. Semantic
Scholar returned HTTP 429 for both requests and was not used further.

## Candidates, read in full unless stated

### Wu et al. 2024, Heart: the blocked review (closest precedent)

Wu T, Ke Y, Li Y, Wu Z, Lv J, Yu C, Sun D, Yao P, Kartsonaki C, Chen Z, Li L, Pang Y. Associations
between circulating proteins and cardiometabolic diseases: a systematic review and meta-analysis
of observational and Mendelian randomisation studies. Heart 2024;110:1208–1215. doi
10.1136/heartjnl-2024-324050; PMID 39084708; PROSPERO CRD42022350327. Publisher PDF from the
OpenAlex content endpoint (heart.bmj.com returned HTTP 403), `texts/wu2024_heart_plain.txt`.
Supplement not read.

Pinned in `claims/wu2024heart.yaml`:

- Key messages: "We searched PubMed, Web of Science and Embase from database inception to July 2023"
- Abstract: "Results 50 observational, 25 MR and 10 studies performing both analyses were included"
- Methods, Literature search: "When two or more studies reported data from the same cohort or
  consortium, only the study with the largest number of participants was included."
- Methods, Statistical analysis: "Protein-disease pairs with ≥2 non-overlapping reports were
  included."
- Results: "The evaluation of MR evidence included 35 studies assessing circulating proteins as
  possible causal biomarkers for CMDs, with 10 531 protein-disease pairs reported and 1614 pairs
  eligible for meta-analysis."
- Results: "Moderate heterogeneity was observed for MR pooled results, and 14.2% pairs had
  I2≥80%."
- Results: "Of 1731 protein-disease pairs investigated in both of observational and MR pooled
  analyses, only 22 pairs showed directionally consistent associations"
- Results: "we identified 23 tier 1 and 2 proteins associated with risk of two or more CMDs,
  referred to as ‘pleiotropic protein’"
- Results, Quality assessment: "29 studies (82.9%) restricted instrumental variables to cis-pQTLs"
- Abstract, Results: "Of the 245 potentially causal proteins (291 protein-disease pairs), 3 pairs
  were validated by evidence of drug development from existing drug databases, 288 pairs lacked
  evidence of drug development and 66 proteins were drug targets approved for other indications."

(The source text carries soft hyphens after each hyphen; the pins include them.)

| Paper 1 component | Wu 2024 |
|---|---|
| unit | protein–disease pair from full-text estimates, pooled by random-effects meta-analysis; not abstract claims |
| scope | six cardiometabolic outcomes; search to July 2023; 35 MR studies |
| repetition (echo) | not counted; overlapping cohorts removed, largest study kept |
| contradiction between MR papers | not reported; heterogeneity (I²) of pooled MR pairs reported |
| independent-data agreement | no; overlap handled by exclusion |
| dataset reuse (H2) | no |
| drug development | yes, DrugBank lookup: approved matching indication, no record, target approved elsewhere |
| hub or pleiotropic proteins | yes, proteins with tier 1–2 evidence for ≥ 2 diseases |
| pathways | yes, GO and KEGG enrichment |
| observational vs MR direction | yes (22 of 1,731 pairs consistent) |

Three Paper 1 descriptive outcomes (drug-development status, `target_drugged_elsewhere`, hub
proteins) and the pathway enrichment have a disease-restricted precedent here. The echo-chamber
counts, contradiction, H1 and H2 do not.

### Chen, Zhao and Fu 2025, Eur Heart J: full text not read

Chen J, Zhao J, Fu S. Addressing sample overlap and meta-analysis imbalances in Mendelian
randomization: a critical appraisal of protein targets for myocardial infarction. Eur Heart J
2025;46(29):2928–2929. doi 10.1093/eurheartj/ehaf186; PMID 40249360; published online 2025-04-18.

**Full text not read.** The record has no abstract in PubMed, Europe PMC or Crossref. Europe PMC:
not in PMC, "Subscription required". The OUP article page and PDF returned HTTP 403; the OpenAlex
content endpoint returned 404 (no stored copy); OpenAlex lists no open location; no preprint or
author manuscript was found in Europe PMC; Semantic Scholar was rate-limited. No supplement exists
for a two-page letter.

What the metadata show: Crossref lists three references, the first being Titova OE et al., "Plasma
proteome and incident myocardial infarction: sex-specific differences", Eur Heart J 2024 (doi
10.1093/eurheartj/ehae658; PMC11560279), and the others LD Hub and a 2025 J Hepatol letter on MR
data integrity. The same issue carries the authors' reply: Titova OE, Yuan S, Larsson SC. Applying
Mendelian randomization to study the relationship between circulating proteins and myocardial
infarction. Eur Heart J 2025 (doi 10.1093/eurheartj/ehaf187; PMID 40249358; also closed). The
item is a single-paper letter on one proteome-MR study, as `VERIFICATION.md` assumed. It is not a
multi-paper synthesis on any reading of its metadata.

A letter by the same group, read in full as a check on the genre: Zhu X, … Chen J, Li X.
Insights and concerns on proteomic-based Mendelian randomization in ischemic stroke. Ann Med Surg
2025;87:2510–2511 (PMC11981414). Pinned in `claims/zhu2025letter.yaml`: "We have carefully read the
article by Zou et al" (paragraph 1) and "there appears to be a sample overlap between the plasma
protein data (including 4775 proteins from the Fenland study, center 3) and the outcome data"
(paragraph 2). One paper, four methodological points, no data.

### DMRdb (Zheng et al. 2025, Nucleic Acids Res)

Zheng X, Tian Z, Che X, Zhang X, Xiang Y, Ge Z, Zhai Z, Ma Q, Pan J. DMRdb: a disease-centric
Mendelian randomization database. Nucleic Acids Res 2025;53(D1):D1363–D1371 (online 2024-10-01).
doi 10.1093/nar/gkae853; PMC11701675; a correction was published 2026 (gkag011, not read). Pinned in
`claims/zheng2025dmrdb.yaml`:

- Abstract: "over 380 000 causal relationship pairs from 1223 literature sources relevant to MR
  analyses"
- Schematic overview: "including 1057 publications on MR studies on causal relationships between
  diseases and 166 MR studies on eQTL/pQTL relationships between diseases, resulting in >380
  thousand pairs of causal relationships"

A curated registry of published MR conclusions, pQTL MR included, offered for lookup. The paper
reports no count of repeated, contradictory or independent pairs, and its own MR arm uses pQTLs from
Sun 2018, Folkersen and Suhre. A registry precedent, not an analysis precedent; its curation
criteria for the 166 studies are not described in the main text.

### Other candidates

| paper | read | relevance |
|---|---|---|
| Shi X, Zhao W, Chen T, Yang C, Du J. Evidence triangulator. Nat Commun 2025;16:7355. PMC12335490 | full | LLM extraction of exposure, outcome, direction and significance from titles and abstracts, aggregated into a direction-convergence score; case study salt and blood pressure (942 studies). Pinned: "particularly in identifying the direction of effect (F1 = 0.86) and statistical significance (F1 = 0.96)" (Abstract); "our LLM pipeline—despite relying solely on results reported in abstracts—closely aligns with established systematic review processes" (Results, Case 1). A method precedent for abstract-level direction extraction; not proteomic, no repetition or dataset analysis |
| Xu W et al. MRAgent. Brief Bioinform 2025. PMC11975362 | full | LLM agent that extracts exposure–outcome pairs from PubMed, checks whether MR was already done, and runs new MR. A tool; no meta-analysis of published claims |
| Moix S, Sadler MC, Kutalik Z. Integration of genetic evidence to identify approved drug targets. Genome Med 2026. PMC13335195 | full through Conclusions | own GWAS, eQTL, pQTL-MR (UKB-PPP) and burden scores benchmarked against approved targets; no published claims |
| Sobczyk MK, Gaunt TR. Integrative MR approaches for therapeutic target prioritisation in immune-mediated diseases. Sci Rep 2026. PMC13065838 | full through Declarations | own pQTL and intermediate-trait MR for 834 IMD drug targets; sensitivity against approved drugs; no published claims. First public 2026: an update-set candidate, so this reading is foreknowledge |
| Zhang M et al. Optimizing MR for drug prediction. Research Square 2024, doi 10.21203/rs.3.rs-3966011/v1 | full | own MR of approved drug targets (ChEMBL) as positives; no published claims |
| Dillman A et al. The circulating proteome and cancer risk. EBioMedicine 2026. PMC12818075 | Summary, Research in context, Methods and study table; results tables not read | meta-analysis of 26 prospective observational proteomic studies with own MR follow-up; does not synthesize published MR |
| Jonmundsson T et al. Systematic comparison of observational and MR estimates for cardiometabolic proteomic signatures. medRxiv 2025, doi 10.64898/2025.12.02.25341031 | abstract | direction agreement between observational and MR estimates within one cohort (AGES-RS); no published claims |
| Ganguly D. Does drug-target MR track clinical progression of MASH drug programmes? Zenodo 2026 (10.5281/zenodo.22026563) | Zenodo metadata | own MR for 18 MASH programmes against clinical progression; no published claims |
| Tower E. MR predicts drug-target success only for abundance-modulating mechanisms. Zenodo 2026 (10.5281/zenodo.21207254) | Zenodo metadata | the author's own work (foreknowledge item 5); uses the EpiGraphDB catalog, not published papers |
| Yoshiji S. Triangulating evidence in proteome-wide MR for cardiovascular disease. J Am Coll Cardiol 2026, PMID 42524809 | title | editorial comment on one paper |

Titles and hits read and excluded without opening: disease-specific systematic reviews of MR
studies (miscarriage, migraine, periodontitis, alcohol, dementia and others), whose unit is an
exposure's published MR estimates for one disease; LLM benchmarking papers not about MR claims
(CARDBiomedBench, Corpas 2026); knowledge-graph and bibliometric papers on other topics; and
primary proteome-MR papers, whose titles were seen but whose abstracts were not read.

## Earlier conclusions that still stand

From `VERIFICATION.md`: Nguyen, Terry and Guggenheim 2025 remains the only re-analysis of other
groups' MR claims found; MR-KG remains the only cross-abstract direction-discordance study; Yang et
al. 2025 (stroke field synopsis) grades published MR associations without comparing them;
Sobczyk et al. 2023 compares MR with RCT directions. None was superseded by this rerun.
