# Pinned external releases

Retrieved 2026-09-30. Files live on the Modal volume `proteome-mr-claim-audit-inputs` (see Input storage below);
the gitignored `inputs/` beside this file keeps the folder structure. The sha256 is of the file
as downloaded. No claim data was read and no join was run.

## Table

| resource | version | release date | URL | sha256 | fields used |
|---|---|---|---|---|---|
| Open Targets Platform: `clinical_report` | 26.09 | 2026-09-18 | https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/26.09/output/clinical_report/00000000.parquet | `ba0ea48b129182de119f5d676bb1483e6225ba65857a31b7319b65c0e6b8fa25` | `id`, `drugs.drugId`, `diseases.diseaseId`, `clinicalStage`, `trialPhase`, `trialOverallStatus`, `trialWhyStopped`, `trialStopReasonCategories`, `trialStartDate`, `source`, `type`, `qualityControls` |
| Open Targets Platform: `clinical_indication` | 26.09 | 2026-09-18 | …/26.09/output/clinical_indication/00000000.parquet | `e10ced7ce09495cd3fa6e7cb94e81e083aed78ee399424730d567243b49a38d8` | `drugId`, `diseaseId`, `maxClinicalStage`, `clinicalReportIds` |
| Open Targets Platform: `clinical_target` | 26.09 | 2026-09-18 | …/26.09/output/clinical_target/00000000.parquet | `33feae900b97a0935c3e30a5c745d3074a2ca46c5e50456b334482c0da113735` | `drugId`, `targetId`, `diseases.diseaseId`, `maxClinicalStage`, `clinicalReportIds` |
| Open Targets Platform: `evidence_clinical_precedence` | 26.09 | 2026-09-18 | …/26.09/output/evidence_clinical_precedence/part-00000-c18648ed-1b6a-4490-aecf-bfadcf459516-c000.zstd.parquet | `df235108bff0a9db4a313ae7c6997c6edeb30f9e74bf719c47753757bf6e1f47` | `targetId`, `diseaseId`, `drugId`, `clinicalReportId`, `clinicalStage`, `trialStopReasonCategories`, `directionOnTarget` |
| Open Targets Platform: `drug_mechanism_of_action` | 26.09 (from ChEMBL 37) | 2026-09-18 | …/26.09/output/drug_mechanism_of_action/00000000.parquet | `8484accd3383837e0eaac2164eed89991daf58dc93f0a599072fb7e5ef4f6c28` | `chemblIds`, `targets`, `actionType`, `mechanismOfAction` (cross-check of ChEMBL only) |
| Open Targets Platform: `drug_molecule` | 26.09 | 2026-09-18 | …/26.09/output/drug_molecule/00000000.parquet | `be65749aa1dbcc68d0930f8ac18126cec5c2bc2c0f232f11e8530dad4ba0585c` | `id`, `parentId`, `childChemblIds`, `name` (parent–salt collapse) |
| Open Targets Platform: `disease` | 26.09 (EFO v3.93.0 slim) | 2026-09-18 | …/26.09/output/disease/00000000.parquet | `a89b8b8b89bad168016e6ff8302d2bcc8d9b7f9cbb35c459ef847c36a4f17aed` | `id`, `name`, `therapeuticAreas`, `ontology.isTherapeuticArea` (therapeutic areas); `id` (drug-join disease index); `dbXRefs`, `parents`, `children`, `obsoleteTerms` (checked, not read by a script) |
| Open Targets Platform: dataset schema | 26.09 | 2026-09-18 | https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/26.09/croissant.json | `6015a040b88715208eb68ab45db962f03b8474014bfed7265d21f25a8334634f` | field descriptions |
| ChEMBL | chembl_37 | 2026-05-01 (README); files 2026-05-29 | …/releases/chembl_37/chembl_37_sqlite.tar.gz (5,764,252,857 bytes; on Modal volume `proteome-mr-claim-audit-inputs` at `/chembl_37/`) | publisher `33c203740555f96067710cdfc1c3c55d890660e5908ec5cbf5817492c290d281`; computed on Modal `33c203740555f96067710cdfc1c3c55d890660e5908ec5cbf5817492c290d281` (match, 2026-09-30T22:14:25Z); extracted `chembl_37.db` `4be13df3b68e25dcd0bff44bf094033b5aebe98f415acdc8c1cdf380e0c15142` (30,480,314,368 bytes); record in `/chembl_37/VERIFIED.json` | `drug_mechanism` (`molregno`, `tid`, `action_type`, `direct_interaction`, `molecular_mechanism`); `target_dictionary` (`target_type`, `organism`); `drug_indication` (`molregno`, `max_phase_for_ind`, `efo_id`, `mesh_id`); `action_type` (`action_type`, `parent_type`); `target_components` → `component_sequences.accession` (UniProt); `molecule_hierarchy` |
| ChEMBL: published checksums | chembl_37 | 2026-05-29 | https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/checksums.txt | `e949808982cc9f0d08fa16b42ebe75b4e04b511d8b96693c973890e6e024e62a` | publisher's sha256 of the dump: `d5fb08a6c9bf6cf7319dbdf74bdb5a7d4ce767aace670250ba1435cab4d58c58` |
| ChEMBL: target–UniProt map | chembl_37 | 2026-05-29 | …/releases/chembl_37/chembl_uniprot_mapping.txt | `5b21436984a41e31bfe178d807544c7ece4649303c397d461c14a61f27f6d082` | UniProt accession → ChEMBL target ID |
| ChEMBL: schema documentation | chembl_37 | 2026-05-29 | …/releases/chembl_37/schema_documentation.txt | `170021a58a6d8c09ca088eae5ee75c9b9d0b3b457c6428adf63986b9d765f9fb` | definitions quoted below |
| Reactome: UniProt → lowest-level pathway | 97 | 2026-06-19 | https://reactome.org/download/97/UniProt2Reactome.txt | `e34fe56a5129d88d8cd67300c279d7e81fa1d3bf86fa0577cf91032c326eaecc` | columns 1 (UniProt), 2 (pathway stable ID), 6 (species; `Homo sapiens` only: 54,699 rows) |
| Reactome: pathway names | 97 | 2026-06-19 | https://reactome.org/download/97/ReactomePathways.txt | `f6d7a2bf89b5bcfe0250a0bc7f51bff94641447911712b8ff129f5b55e52df3a` | stable ID, name, species |
| Reactome: pathway hierarchy | 97 | 2026-06-19 | https://reactome.org/download/97/ReactomePathwaysRelation.txt | `fd49a624d80c14eb37ae57a02e141d574d5ede3f60022bb99edbd909448a3f1e` | parent → child (not used by the registered analysis; kept for the record) |
| MONDO | v2026-09-01 | 2026-09-01 | https://github.com/monarch-initiative/mondo/releases/download/v2026-09-01/mondo.obo | `50c8367f9bd9978321eedf84d4e2e79cb757efbed514c81effb00b9ad2e49994` | `id`, `name`, `synonym`, `is_a`, `xref` (2,400 `xref: EFO:` lines), `is_obsolete`, `replaced_by` |
| MONDO: all mappings (SSSOM) | v2026-09-01 | 2026-09-01 | https://raw.githubusercontent.com/monarch-initiative/mondo/v2026-09-01/src/ontology/mappings/mondo.sssom.tsv | `317ac4bf93be1deff4406b4d7d18bb730ead3c4f5c7c814f75d24be7f6ef302f` | `subject_id`, `predicate_id`, `object_id` |
| MONDO: exact matches to EFO (SSSOM) | v2026-09-01 | 2026-09-01 | https://raw.githubusercontent.com/monarch-initiative/mondo/v2026-09-01/src/ontology/mappings/mondo_exactmatch_efo.sssom.tsv | `7f4e2c0e27e3657885b7032a97aaab0186365b62922308434ff88c8c308defb9` | `subject_id` (MONDO), `object_id` (EFO), `predicate_id` = `skos:exactMatch`; 2,400 rows |
| MONDO: imported source versions | v2026-09-01 | 2026-09-01 | https://github.com/monarch-initiative/mondo/releases/download/v2026-09-01/source-versions.tsv | `c98ed57fbd7f915b5fa213f44d7c092c85fba571687420dc521bf2f78c4193b5` | record only |
| EFO | v3.94.0 | 2026-09-15 | https://github.com/EBISPOT/efo/releases/download/v3.94.0/efo.obo | `1f7bdc48b91c17cd98742d8c0fca77d576d4d74998efd643e51b1b49602ca49c` | `id`, `name`, `synonym`, `is_a`, `xref`; EFO imports 16,600 MONDO terms directly and carries 198 `xref: MONDO:` lines |
| EFO (release used by Open Targets 26.09) | v3.93.0 | 2026-08-17 | https://github.com/EBISPOT/efo/releases/download/v3.93.0/efo.obo | `66e87fc65a6254c6d69281ed3d286784ee5f8265b1e57691efddd29b20570c46` | as above; see Decision 1 |
| HGNC complete set | monthly 2026-09-04 | 2026-09-04 | https://storage.googleapis.com/public-download-files/hgnc/archive/archive/monthly/tsv/hgnc_complete_set_2026-09-04.tsv | `6f43d6ff43aa9fdfa5fb2f20a20a7cace66e6e02e2a0dcf19d9b726e2e248d20` | `hgnc_id`, `symbol`, `alias_symbol`, `prev_symbol`, `uniprot_ids`, `status` |
| UniProtKB human reviewed (pinned query) | 2026_03 (`X-UniProt-Release`) | 2026-09-02 | https://rest.uniprot.org/uniprotkb/stream?query=(organism_id:9606) AND (reviewed:true)&format=tsv&fields=accession,id,gene_primary,gene_synonym,xref_hgnc,protein_name | `620d646a96c07ab3c6c71306518bbf28ee61c0d5e91cab26e4c5417e91e19f83` | all six columns; 20,431 entries (equals `X-Total-Results`) |
| Olink Explore 3072: UKB-PPP protein map | Synapse syn52364558 v1 | 2023-08-30 (modified 2023-11-26) | https://www.synapse.org/Synapse:syn52364558 | `2bc9668e56f43818e2a61558fcdd0b5384b4919602bc61c9faaed2622aefe6aa` | `UniProt`, `HGNC.symbol`, `Assay`, `Panel`, `OlinkID`; 2,958 assays, 2,923 UniProt, 8 panels |
| Olink Explore 1536: UKB-PPP protein map | Synapse syn51396732 v1 | 2023-04-27 (modified 2023-11-26) | https://www.synapse.org/Synapse:syn51396732 | `431187e35d15c39b3861b75e6c10ab634b1506fe3e02f90f6c753c8d78fe91d6` | as above; 1,480 assays |
| Olink Explore 3072: Olink assay list | Olink xlsx as shipped in pQTLdata 0.6 | 2026-03-09 (package) | https://cran.r-project.org/src/contrib/pQTLdata_0.6.tar.gz → `inst/Olink/assay-list-olink-explore-3072.xlsx` | xlsx `61d85f8f31272276c4f5da2e731744fb68b9fda21b30a09799f4304106a15476`; tarball `aede30b7c4e3ca2a8513ccc6f0b31b1df79b309d05ea6df052ac15bb225db409` | `UniProt.ID`, `Gene.name`, `Explore.384.panel`; 2,943 rows, 2,925 UniProt; 2,922 shared with the UKB-PPP map |
| Olink Target 96 panels (earlier Olink) | Olink xlsx as shipped in pQTLdata 0.6 | 2026-03-09 (package) | same tarball → `inst/Olink/Olink-Target-96-Assay-List.xlsx`; exported `pQTLdata_0.6_Olink_Target_96.tsv` | xlsx `9b7039afed79aa2472d79c79251658efff3c12965f2a1080b2cf60303400682d`; tsv `99d540b85780f6e04ddb94d9efc0339b5852a1dc8804ed0bb1c76bf3e279a56d` | `UniProt`, `Panel` (CVD II, CVD III, INF, NEU, ONC II/III, MET, …); 1,161 rows |
| Olink Explore HT vs 3072 (Olink document, third-party mirror) | v1.4 | unknown | https://bioxpedia.com/wp-content/uploads/uploads/Olink-Explore-HT-vs-Explore-3072_v1.4.pdf | `d4ca8976a8be561788b92134b8e95c62e821f5393e9133a5f32ef7da84a4c9c5` | cross-check only |
| SomaScan v4 (5k): Eldjarn et al. 2023 ST2 | Nature 10.1038/s41586-023-06563-x, Supplementary Table 2 (`ST2_soma_assays`) | 2023 | local `pqtl-mr-domain-of-validity/planning/perplexity_v8_design/F_data_readmes/eldjarn2023/eldjarn2023_MOESM3.xlsx` (sha256 `cb93f441ad64a8c28a659f12c8101cf84cd9b0e7a09ca3c8bcca44d90a084284`), exported as `eldjarn2023_ST2_soma_assays.tsv` | `d274b6466f59384457d27f398f97de09b8bf059236e8f56d11725587bd48f82c` | `seqid`, `uniprot`, `gene_name`, `on_1.2k`; 5,029 aptamers, 4,718 distinct `uniprot` strings (96 multi-protein) |
| SomaScan 1.3k (earlier SomaScan) | subset of ST2 with `on_1.2k` = True | 2023 | as above | as above | 1,158 aptamers |
| SomaScan 160410 (INTERVAL, Sun et al. 2018; earlier SomaScan) | pQTLdata 0.6 `SomaScan160410` | 2026-03-09 (package) | tarball above; exported `pQTLdata_0.6_SomaScan160410.tsv` | `30c311410c04940ae1728a060d22e02d55240d38942b6846733bbad20b698d41` | `SOMAMER_ID`, `UniProt`; 5,178 rows, 3,601 UniProt strings |
| SomaScan v4.1 (7k) | pQTLdata 0.6 `SomaScanV4.1` ("obtained directly from SomaLogic") | 2026-03-09 (package) | tarball above; exported `pQTLdata_0.6_SomaScanV4.1.tsv` | `9442ebd9964c0cf344b71753d67409b2ec1850cd2325d2ae8519f48549b9a9a4` | `SeqID`, `UniProt.ID`, `GeneID`; 7,288 rows |
| EpiGraphDB pQTL MR (Zheng et al. 2020) | EpiGraphDB API 1.0, pQTL database 3.0 | retrieved 2026-09-30 | https://api.epigraphdb.org/pqtl/?query={protein}&rtype={mrres,simple}&searchflag=proteins&pvalue=1, for every protein in /pqtl/list/?flag=exposures | `manifest.json` `2c5c03cef914aa9fbd83a8617858152e24484794e9831f5392bf0623e114964d` (1,980 files: 2 lists, 989 × 2 responses) | `expID`, `outID`, `outID_mrbase`, `nsnp`, `method`, `beta`, `se`, `pvalue`; `simple` adds `rsID`, `trans_cis`, `coloc_prob`, `direction` (Steiger), `steiger_pvalue` |

`…` abbreviates `https://ftp.ebi.ac.uk/pub/databases/opentargets/platform` or the ChEMBL release
directory in the row above.

**ChEMBL 37 packaging.** The registered ChEMBL release is chembl_37. It is read from the
publisher's SQLite package (`chembl_37_sqlite.tar.gz`) in place of the PostgreSQL dump
(`chembl_37_postgresql.tar.gz`, publisher sha256 `d5fb08a6c9bf6cf7319dbdf74bdb5a7d4ce767aace670250ba1435cab4d58c58`); both packages are the
same release, and the choice of package is a packaging choice only. The tarball was downloaded,
verified against the publisher's `checksums.txt` and extracted on Modal by
`scripts/modal_chembl_extract.py` (logic in `scripts/chembl_extract.py`). The tables used were
exported to CSV on the volume at `/chembl_37/tables/` (`SHA256SUMS` beside them) and copied to
`inputs/chembl_37/tables/`, where the sha256 were rechecked locally:

| table CSV | columns | rows | sha256 |
|---|---|---|---|
| `drug_indication.csv` | all | 60,055 | `95838754c10fe7a0f0e71dcc55f363554870782172d15fb6dc11e1457b899097` |
| `drug_mechanism.csv` | all | 7,561 | `6ac645e99656c332e971d8e9be69000656d2dd21cce9469595634ec934278d3e` |
| `action_type.csv` | all | 35 | `b805791159791f48a6ea5ddbb6a633f1c0a56b50be13897eafbeb51e9d1bd624` |
| `molecule_dictionary.csv` | `molregno`, `chembl_id`, `pref_name`, `max_phase`, `molecule_type` | 2,921,148 | `d83cbb0fd0d5dc5537638054c4a970e7555b9ae1beb866f2f9c3d0a66b3a44e8` |
| `molecule_hierarchy.csv` | `molregno`, `parent_molregno`, `active_molregno` | 2,828,129 | `2cc876c6e4fd94344d51787314e7ff5c2dcf8ec63ca3c63f03a30fbb56720ccc` |
| `target_dictionary.csv` | all | 18,552 | `b8acb67f76221eff0b1a69350b84dda0c41617789da1c97da5a4ed02dc021eea` |
| `target_components.csv` | all | 17,284 | `efc71b567ad6b030db3ac60d84e026a9cfe979cebe0c52e48ad327fdb351d2e8` |
| `component_sequences.csv` | all except `sequence` | 12,986 | `636d52fb0958f03374cb4d6d1e3d33ccc3db7fccb41e13d7ceaed87321dece07` |

`compound_records.csv` (sha256 `0dafab0af7587c7eb1cba8b7043170643a7c7563fb239eb08a1e5fe1b992cb13`) and `docs.csv` (sha256 `994b1650fdc300005a7989f11c7a08cb55e63c8d1f5e1bea32d2cba7240b68c5`) are
also on the volume for other uses and are not used by this registration.

## What the documentation and data confirm

**Open Targets 26.09 has no `known_drug` or `evidence_chembl` dataset.** Clinical records now
come from the Open Targets Mira pipeline as `clinical_report`, with aggregated
`clinical_indication` (drug × disease) and `clinical_target` (drug × target) views
(documentation: https://platform-docs.opentargets.org/drug/clinical-report.md, read
2026-09-30). The six source families are ClinicalTrials.gov via AACT, ChEMBL curated
indications, ChEMBL drug warnings, TTD, EMA and PMDA. From 26.06, drugs and diseases of AACT
trials are extracted by a large language model and mapped to ChEMBL and EFO.

- **Stop-reason class** is `clinical_report.trialStopReasonCategories` (array of strings), also
  carried on `evidence_clinical_precedence`. The documentation lists 17 classes; the 26.09 data
  carry 13 labels, written with underscores: `Insufficient_Enrollment` (8,047),
  `Business_Administrative` (7,905), `Negative` (2,456), `Study_Design` (1,672),
  `Logistics_Resources` (1,614), `Invalid_Reason` (1,309), `Another_Study` (1,026),
  `Safety_Sideeffects` (935), `Study_Staff_Moved` (847), `Covid19` (812), `Regulatory` (611),
  `Uncategorised` (540), `No_Context` (241). `Uncategorised` is not in the documented list.
  Labels occur only on trials whose `trialOverallStatus` is `TERMINATED`, `WITHDRAWN` or
  `SUSPENDED`.
- **Active status** is `clinical_report.trialOverallStatus`: `RECRUITING` (21,288),
  `ACTIVE_NOT_RECRUITING` (9,254), `NOT_YET_RECRUITING` (7,155), `ENROLLING_BY_INVITATION` (870);
  also `COMPLETED`, `TERMINATED`, `WITHDRAWN`, `SUSPENDED`, `UNKNOWN`, null (58,965, non-trial
  sources) and expanded-access values.
- **Phase** is `clinical_report.clinicalStage` (harmonized: `PHASE_1` … `PHASE_4`,
  `PHASE_1_2`, `PHASE_2_3`, `EARLY_PHASE_1`, `IND`, `PRECLINICAL`, `PREAPPROVAL`, `APPROVAL`,
  `WITHDRAWAL`, `UNKNOWN`) and `clinical_indication.maxClinicalStage`.
- **Quality filters**: reports flagged in `qualityControls` (Phase IV without an approval for the
  indication; trials whose primary purpose does not measure the effect on the condition) are
  excluded from `clinical_indication`, `clinical_target` and the evidence, but stay in
  `clinical_report`.
- Open Targets 26.09 was built from ChEMBL 37 (`chembl_37_postgresql.tar.gz` in its
  `manifest.json`) and EFO v3.93.0.

**ChEMBL 37** (`schema_documentation.txt`): `DRUG_INDICATION.MAX_PHASE_FOR_IND` is "Maximum
phase of development that the drug is known to have reached for this particular indication (4 =
Approved, 3 = Phase 3 Clinical Trials, 2 = Phase 2 Clinical Trials, 1 = Phase 1 Clinical Trials,
0.5 = Early Phase 1 Clinical Trials, -1 = Clinical Phase unknown …)", with `EFO_ID` and
`MESH_ID` per indication. `DRUG_MECHANISM` carries `ACTION_TYPE` (foreign key to `ACTION_TYPE`),
`TID`, `DIRECT_INTERACTION` and `MOLECULAR_MECHANISM`. `ACTION_TYPE` has `ACTION_TYPE`,
`DESCRIPTION` and `PARENT_TYPE` (positive modulator / negative modulator / other).

**EpiGraphDB pQTL MR.** No bulk file exists: the browser page is JavaScript only, the
`MRCIEU/epigraphdb-pqtl` repository holds instruments and outcome IDs but no results, and the
paper's data-availability statement ("All our analysis results for 989 proteins against 225
human phenotypes are freely available to browse, query and download in EpiGraphDB") points to
the API. The frozen copy is therefore the API response for every one of the 989 exposures, by
`scripts/pin_epigraphdb_pqtl.py`, with a per-file sha256 in `inputs/epigraphdb_pqtl/manifest.json`;
the table gives the sha256 of that manifest.

- **Nonsignificant pairs are included.** With `pvalue=1`, ADAM19 returns 208 records up to
  P = 0.972; with the default 0.5, 121; with 0.05, 16.
- **Completeness is not confirmable.** The API's Cypher (returned in `metadata.query`) keeps an
  MR record only when the exposure–outcome pair also has a sensitivity-analysis node
  (`SENS_EXP`/`SENS_OUT`), and filters `r.pvalue < 1.0` strictly. ADAM19 has 208 of 225
  outcomes. Absence can mean untested, missing sensitivity node, or P = 1. Under the
  registration's own rule, `tested_nonsignificant` is therefore not used and absence stays
  `no_returned_record`.
- The frozen copy holds 179,928 distinct protein–trait records (one estimate per pair in
  `mrres`; 198,239 rows in `simple`, which splits by instrument) out of 989 × 225 = 222,525
  possible pairs. No protein has all 225 traits (range 2–224). Maximum P is 0.99999.
- Zheng et al. 2020 report 1,002 proteins with tier 1–2 instruments; the browser lists 989.

## Decisions for Elliot before the freeze

1. **EFO release.** Open Targets 26.09 mapped diseases with EFO v3.93.0; v3.94.0 is the latest.
   Mapping outcomes with v3.93.0 keeps identifiers identical to the Open Targets join; v3.94.0
   is newer. Both files are pinned.
2. **Stop-reason collapse table.** `stopped_negative_or_safety` = {`Negative`,
   `Safety_Sideeffects`}; `stopped_other` = the other 11 labels, `Uncategorised` included. The
   prereg's wording "Safety and Side Effects" should read the data label `Safety_Sideeffects`.
3. **Active status set.** `in_clinical_trials` = `trialOverallStatus` in {`RECRUITING`,
   `ACTIVE_NOT_RECRUITING`, `NOT_YET_RECRUITING`, `ENROLLING_BY_INVITATION`}, matching the prereg.
   `SUSPENDED` trials carry stop-reason labels; the prereg does not yet say whether a suspended
   trial is `stopped_*`.
4. **ChEMBL vs Open Targets phase.** Open Targets `clinical_indication` pools ChEMBL indications
   with AACT, TTD, EMA and PMDA, so its stage will exceed ChEMBL's `max_phase_for_ind` for some
   pairs by construction. The prereg uses ChEMBL for `approved` and Open Targets for trial
   status; a precedence rule is still needed where both speak to approval.
5. **Direction token rule vs ChEMBL 37 action types.** Counted in Open Targets
   `drug_mechanism_of_action`, the copied rule classes these as AMBIGUOUS: `BINDING AGENT` (253
   mechanisms), `MODULATOR` (107), `POSITIVE MODULATOR` (37), `NEGATIVE MODULATOR` (5),
   `GENE EDITING NEGATIVE MODULATOR` (1), and the non-directional types (`EXOGENOUS PROTEIN`,
   `VACCINE ANTIGEN`, `OTHER`, …). `POSITIVE MODULATOR` and `NEGATIVE MODULATOR` have a stated
   direction that the rule drops. Recorded only; the rule is copied verbatim and not changed.

## Resolved 2026-09-30 (registered in PREREG.md)

1. **EFO release:** EFO v3.93.0 is the registered ontology release, matching the Open Targets
   26.09 build. v3.94.0 stays pinned as a recorded file only and is not used.
2. **Stop-reason collapse table:** as in Decision 2; the prereg now names the 13 data labels
   verbatim and the negative-or-safety subset as `Negative` and `Safety_Sideeffects`.
3. **Suspended trials:** `trialOverallStatus` SUSPENDED is its own class (`suspended`) and is never
   counted as stopped, whatever stop-reason label it carries.
4. **Phase precedence:** development phase comes from ChEMBL `max_phase_for_ind` only; Open
   Targets 26.09 `clinical_report` supplies trial events, `trialOverallStatus` and stop reasons
   only. Where they differ on phase, ChEMBL is used.
5. **Direction rule:** unchanged; `POSITIVE MODULATOR` and `NEGATIVE MODULATOR` stay AMBIGUOUS,
   stated in the prereg.

**Pre-freeze item:** the local ChEMBL 37 dump must be verified against the publisher's sha256
`d5fb08a6c9bf6cf7319dbdf74bdb5a7d4ce767aace670250ba1435cab4d58c58` before the freeze.

**Pre-freeze item closed 2026-09-30:** ChEMBL 37 is read from the SQLite package, whose sha256
matched the publisher's `33c203740555f96067710cdfc1c3c55d890660e5908ec5cbf5817492c290d281` on
Modal; the incomplete local PostgreSQL download was deleted.

**Input storage.** Every other file under `inputs/` and `reference/raw/` now lives on the Modal
volume `proteome-mr-claim-audit-inputs` under `/02_claims_meta/`, with the local sha256 of each
file in `modal_inputs_manifest.json` and the sha256 recomputed on Modal in
`modal_inputs_verification.json` (2,051 of 2,051 match). `inputs/README_MOVED_TO_MODAL.md` says
how to fetch a file.

## Reference files used by the verifier (round 4, 2026-09-30)

`reference/MANIFEST.json` now names the registered files of the table above, fetched from the
Modal volume (`/02_claims_meta/inputs/...`) and checked against `modal_inputs_manifest.json`;
`scripts/verify_claims.py` re-hashes each file before use and raises on a mismatch.

| resource | file | sha256 |
|---|---|---|
| HGNC complete set 2026-09-04 | `inputs/hgnc/hgnc_complete_set_2026-09-04.tsv` | `6f43d6ff43aa9fdfa5fb2f20a20a7cace66e6e02e2a0dcf19d9b726e2e248d20` |
| UniProtKB human reviewed 2026_03 | `inputs/uniprot/uniprot_human_reviewed.tsv` | `620d646a96c07ab3c6c71306518bbf28ee61c0d5e91cab26e4c5417e91e19f83` |
| MONDO v2026-09-01 | `inputs/mondo_v2026-09-01/mondo.obo` | `50c8367f9bd9978321eedf84d4e2e79cb757efbed514c81effb00b9ad2e49994` |
| EFO v3.93.0 | `inputs/efo_v3.93.0/efo.obo` | `66e87fc65a6254c6d69281ed3d286784ee5f8265b1e57691efddd29b20570c46` |

**UniProt checksum.** The development runs r1–r4 used `reference/raw/uniprot_human_reviewed_2026_03.tsv`
(sha256 `8a9fda6847b0e8995f9f47626e6f829bf8640aabcd8ff746b95da1951130f29a`), downloaded by the
earlier `scripts/fetch_reference_files.py` from the same UniProt release (2026_03) with a
three-column query (`fields=accession,gene_names,protein_name`). The registered file (`620d…`)
is the six-column query in the table (`accession,id,gene_primary,gene_synonym,xref_hgnc,
protein_name`), 20,431 entries, with its response headers in `inputs/uniprot/hdr.txt`
(`x-uniprot-release: 2026_03`). The two files differ in columns, not in release. The verifier
reads the `Entry` and `Protein names` columns, which both files carry; the 8a9f file is out of
the analysis path (its manifest is kept at `reference/superseded/`), and
`fetch_reference_files.py` now names the registered query and paths. HGNC: the development
manifest named the `.txt` download of the same file; the sha256 is identical.

**EFO.** The development runs r1–r4 used EFO v3.94.0. The verifier rerun on the r4 outputs with
v3.93.0 gave the same per-claim protein and outcome identifiers, checks and registry entries;
`verification/outcome_aliases.csv` rebuilt against v3.93.0 is byte-identical.

**ChEMBL 37 checksum (round-4 checklist item 8): closed.** Verified on Modal as recorded above
(`/chembl_37/VERIFIED.json`: publisher and computed sha256
`33c203740555f96067710cdfc1c3c55d890660e5908ec5cbf5817492c290d281`).

**ChEMBL target types.** Counts of human drug-mechanism records by `target_type` are in
`outputs/resource_counts/chembl37_mechanism_target_types.json` (4,477 meet the primary
single-protein, direct, molecular rule; 1,248 have a component-level target).

## Canonical identifiers and dataset compositions (pre-freeze, 2026-09-30)

No claim data was read. The MONDO SSSOM file was fetched from the Modal volume
(`/02_claims_meta/inputs/mondo_v2026-09-01/mondo_exactmatch_efo.sssom.tsv`) into a temporary
location and checked against its sha256 in the table above; the MONDO and EFO obo files are the
registered ones in `reference/MANIFEST.json`.

| file | what | sha256 |
|---|---|---|
| `verification/mondo_efo_collision_table.csv` | 1,427 MONDO–EFO-file concepts with both terms live, canonical choice and conflicts (`scripts/build_collision_table.py`) | `b858b4bd0fba33c1d2138e272b3c753c45f3d3f8b426e25b99a9d97c320fd0e0` |
| `verification/mondo_efo_collision_table.meta.json` | inputs, sha256 and counts of the table | `edb203309ed9df178f44cc6ac4e7130e89d5b28c808156a1095d0aef34f74265` |
| `dataset_dictionary.csv` | 121 rows (28 pQTL, 93 outcome), cohort compositions from the papers' cohort tables | `f8a8bcb24534058c374673edd55a17968ff8ac6de8501ab1ed2bd0bb3f5d9a64` |
| `verification/dataset_components.csv` | component identifiers per row, completeness, and the claims files pinning each composition (`composition_claims`) | `2a4e155c4c5765c9ab9f9e9e6029c5add6e265de200344acc3d61149ae806d54` |
| `outputs/resource_counts/dataset_pairings_before_compositions_2026-09-30.json` | relation counts over every two dictionary rows, previous dictionary (`ce4075…`/`a5bae9…`) | `f9dab39c076e920abbb1d6bcc0892466431462b23e7ef5435e4da38f38f474e5` |
| `outputs/resource_counts/dataset_pairings_after_compositions_2026-09-30.json` | the same, this dictionary | `c0c620c0a6c1d1aca59d34fe26f7ba45781a4af14c93d48c4aa0250aeb579664` |
| `scripts/build_collision_table.py` | collision-table builder | `fa294e62272c3b6a1069ba2a66f3cc9841a0154f75c2789bc88adfec9f1ea160` |
| `scripts/canonical_ids.py` | HGNC → UniProt and collision-table application for the registry | `d011ba25e56b289ca776a440c70b78507fb5887d4b9addc1b2649b15594cca9e` |
| `scripts/dataset_pairings_report.py` | the pairing counts | `9250265550473dbf519f52ddb9d96e91944692224362b9bc3c61e20a9b1e9736` |

**Collision table.** 8,141 MONDO–EFO cross-referenced pairs in the pinned files; 5,978 have an
obsolete EFO term (EFO replaced its own term with the imported MONDO term) and 736 an obsolete
MONDO term, so only one identifier is live and they are not listed. Listed: 1,427 (1,411 MONDO →
Orphanet terms the EFO file carries, 16 EFO → MONDO cross-references); 1,423 diseases (canonical
MONDO), 4 MONDO `disease susceptibility` terms (canonical EFO-file term). Conflicts: 8 rows where a
MONDO term has two live Orphanet equivalents (canonical MONDO; no ambiguity) and 6 branch
disagreements (for example EFO:0803536 "multiple sclerosis symptom measurement", which EFO
cross-references to MONDO:0005301 "multiple sclerosis"). 16,596 MONDO terms are imported by EFO
under their MONDO identifier and need no table.

**Compositions.** Every composition fact is a pinned quotation of a paper's methods or
supplementary cohort table under `claims/` (reader outputs in
`docs/source_verification/compositions/*.json`; `citations verify --claims claims`:
4,424 quotes, 4,424 found). Harmonization applied to every row: synonymous IDs merged
(FINNTWIN, CROATIA_KORCULA, CROATIA_SPLIT, HEALTH2000_GENMETS, FINRISK_DILGOM, LIFELINES_DEEP,
MPP_RES, ROTTERDAM); any EPIC centre or sub-study also carries `EPIC`; any list with FINNGEN also
carries the 13 FinnGen legacy cohorts of Kurki et al. 2023 Supplementary Table 2 (FINRISK, Health
2000/2011, Botnia, Corogene, GeneRISK, Helsinki Heart Study, Migraine, FinHealth 2017, SUPER, THL
Diabetes, Finnish Twin Cohort, Finnish IPF, FiNNAKI). An incomplete row's `no` flag for UK Biobank or
Iceland is written `unknown`.

## Pre-freeze defaults, OPEN_QUESTIONS 41–45 (2026-09-30)

No claim data was read. `dataset_components.csv` and the collision table are unchanged.

| file | what | sha256 |
|---|---|---|
| `dataset_dictionary.csv` | notes only: FinnGen R6–R12 completeness basis; SWEBIC/STANLEY on Koprulu 2026 | `aad14e0c9e3aca427bd887ddfebd3407acc74e20c662082aee561d8b8f1cd3dc` |
| `scripts/dataset_relations.py` | combination rule (a release plus another dataset never maps to the release alone) | `f6b0645df1e43ee68b6c3a7534d8ebbc74c649f67b2b906e58529efaf559b5c7` |
| `scripts/canonical_ids.py` | branch-disagreement rows left unmerged | `b938ea7528a69fae9c525ef3f6c44a22a2fcffece73874f469104e4e36c7f2a7` |
| `scripts/build_collision_table.py` | docstring only | `b4302ac590ae48867a933bba786d52aa44db7adb4c90403c2f31822d88e1453a` |
| `tests/test_dataset_relations.py` | pinning test replaced; combination cases | `23b1b31e1b2d5ce0644b49b467ee6ac7ccf452b9d346c702e8a05e281bc02039` |
| `tests/test_canonical_ids.py` | unmerged branch-disagreement case | `7a97f9734e7643795b9cf5ad320b811f7915a3001b1a0db85502da08583fa08a` |
| `outputs/tests/pytest_round5_2026-09-30.txt` | 53 passed | `31e1c7bbb1ad88587ec45a1f3824f760088412de02fbd505022250964d538893` |
| `outputs/resource_counts/dataset_pairings_round5_before_name_mapping_fix.json` | row-pair relations before the fix | `21d54e13538818f30663e4ea602bf77c69513f2331836ae969e44cf6cf6935b9` |
| `outputs/resource_counts/dataset_pairings_round5_after_name_mapping_fix.json` | the same after; counts identical | `352fe933690f5edc79fc55a3ccf146299c071dcde7829c2e42d5b6ec9b5b3df7` |
| `outputs/dry_run/20261001T005219Z/h1_h2_tables.json` | synthetic dry run; identical to 20261001T004513Z except the timestamp | `ce86c00d5224de434f9d7ef72254d63cbbe4fd88cdf275b9b2c45a043d5c12fd` |

The pairing report names every row by its own row name, which the exact rule matches, so the
combination rule leaves its counts unchanged; FinnGen R6–R12 were already complete. The rule
changes the mapping of written names such as "FinnGen R12 and UK Biobank meta-analysis" (before:
`unique` FinnGen R12, composition FinnGen only; after: `unique` FinnGen R12 + UK Biobank
meta-analysis) and "FinnGen R10 + UKB" (before: `unique` FinnGen R10, `disjoint` from Pan-UKB;
after: `release_ambiguous`, `overlapping_participant_source` with Pan-UKB).

## Round-5 fixes (pre-freeze, 2026-10-01)

No claim data was read. Review: `planning/perplexity_paper1_final/03_REVIEW_round5.md`;
adjudication: `planning/perplexity_paper1_final/04_ADJUDICATION_round5.md`.

| file | what | sha256 |
|---|---|---|
| `verification/dataset_components.csv` | component identifiers `AGES` → `AGES_REYKJAVIK` (26 rows), `DECODE` → `DECODE_COHORT` (38 rows); nothing else changed | `b82a8ce799626ec054f6e79513f6b6af9af24e3f5de36ea6f9096911de85a591` |
| `dataset_dictionary.csv` | notes only: "Icelandic sources" → "Icelandic cohorts" on the seven FinnGen R6–R12 rows | `f30dda8e00f8bbc6c43e31e80b38935c7d4f0d3916f33b2e776cabc14fb0d39c` |
| `scripts/dataset_relations.py` | no `ICELAND` component; Icelandic cohorts separate; `includes_iceland` yes without an Icelandic cohort component is incomplete, no with one is an error; AGES_REYKJAVIK against DECODE_COHORT with no shared component is `unclear`, never `disjoint`; attribution condition written out per side | `3da13c726236bd9186e5fb7f81a52f6658032b484a895a9d60da80b6f5820980` |
| `scripts/dataset_pairings_report.py` | pQTL × outcome cross-tab applies the same possible-overlap rule | `2c1971765a0b492aafbe0500f5df85f24f7511305578b2fc0b89c619a3ce7bab` |
| `scripts/fetch_fulltext.py` | docstring only: Europe PMC open-access XML is the only full-text source | `61ea9def5ccaed7c71d071e63a4dfceff1664bee0d92cdb64672128fb7e0d0a3` |
| `scripts/fulltext_concordance.py` | docstring only, as above | `4af8944d29c7d13268596aba09bd30d1dfe03782a56b94c2b0b63ba5480bfb39` |
| `tests/test_dataset_relations.py` | AGES/deCODE test now requires `unclear`; Icelandic-flag completeness; attribution unclear on either side; symmetry over every same-side dictionary row pair and all four attribution flag settings | `7566cfa05c4fa63b0048edd9916c92ce635fd27e98d3b332c652505932ec933d` |
| `outputs/tests/pytest_round5_fixes_2026-10-01.txt` | 56 passed | `ffd37d0eb9ca7ee0326c2fb7daa82b007e82e02783ea4f4834862caf9c05a57b` |
| `outputs/resource_counts/dataset_pairings_round5_before_iceland_split.json` | row-pair relations before the split | `00720f3f1afb986575f11de4448eb6d0469c2cc965a8ad5f3a3a11fb34ad1412` |
| `outputs/resource_counts/dataset_pairings_round5_after_iceland_split.json` | the same after (written before the notes-only dictionary edit, so it records the previous dictionary hash) | `cdd7aad940fad6e4fe46d7b5af36c0b5643d4c870a6d8efe9b0510873dc9b6f0` |
| `outputs/dry_run/20261001T152922Z/h1_h2_tables.json` | synthetic dry run; identical to 20261001T005219Z except the timestamp | `b79b07320479ba5775582221af39015ad3ad3e05e4d29c4bf879cd5e1d4264d4` |

Row-pair relations, before → after the split. pQTL (378 pairs): overlapping 59 → 53, disjoint
319 → 319, unclear 0 → 6 (deCODE Ferkingstad 2021 and Eldjarn 2023 each against AGES Emilsson
2018, AGES Gudjonsson 2022 and the Zheng 2020 instrument set). Outcome (4,278 pairs): overlapping
2,813 → 2,785, disjoint 402 → 402, unclear 1,063 → 1,091 (13 of the 28 are AGES-only against
deCODE-only rows with resolved compositions; 15 involve incomplete rows that shared only the
former `ICELAND` component). pQTL × outcome rows: shared component 847 → 786, disjoint 917 → 917,
unclear 840 → 901. No pair became `disjoint`, and complete-row counts are unchanged (pQTL 28 of
28, outcome 44 of 93).

## Stage-0 build and round-6 rules (pre-freeze, 2026-10-01)

No claim, pair, registry record or in-window record was read. Rules:
`docs/stage0_build/PROPOSED_RULES.md` (90 points); builders' lists `AMBIGUITIES_search.md`,
`AMBIGUITIES_drug.md`, `AMBIGUITIES_biology.md`; platform lookups `PLATFORM_LOOKUPS.md`. Packet:
`planning/perplexity_paper1_round6_upload/`. Every file of the build is hashed in
`outputs/tests/stage0_file_sha256_2026-10-01_final.txt` (139 files; sha256 `78d000ec444a33d09334f3ac5a9d2206238fec7910fefc2364333292b794ad69`).

### Inputs added to the Modal volume

| file on the volume (`/02_claims_meta/inputs/…`) | source | bytes | sha256 |
|---|---|---|---|
| `eldjarn2023/eldjarn2023_MOESM3.xlsx` | Eldjarn et al. 2023 (Nature) supplementary tables workbook; ST36 is the pleiotropic-locus list | 144,187,917 | `cb93f441ad64a8c28a659f12c8101cf84cd9b0e7a09ca3c8bcca44d90a084284` |
| `platform_assays_published/pietzner2020_SD1.xlsx` | Pietzner et al. 2020 (Nat Commun) Supplementary Data 1; https://static-content.springer.com/esm/art%3A10.1038%2Fs41467-020-19996-z/MediaObjects/41467_2020_19996_MOESM4_ESM.xlsx | 433,440 | `bb9e011a1d82adb9e40227877483403f5142a3629b928eff57c6c0edd2812e78` |
| `platform_assays_published/folkersen2020_ST1.xlsx` | Folkersen et al. 2020 (Nat Metab) Supplementary Table 1; https://static-content.springer.com/esm/art%3A10.1038%2Fs42255-020-00287-2/MediaObjects/42255_2020_287_MOESM3_ESM.xlsx | 8,811,666 | `928e2526e972469f52cfea931e1bcec1be9d699f3305db4a197aad0ffeb64d4d` |
| `platform_assays_published/gudjonsson2022_SD6.xlsx` | Gudjonsson et al. 2022 (Nat Commun) Supplementary Data 6; https://static-content.springer.com/esm/art%3A10.1038%2Fs41467-021-27850-z/MediaObjects/41467_2021_27850_MOESM8_ESM.xlsx | 424,746 | `c6364dede2887c75c0429a31ec8320a7465d61fdb6379d11264087f8f383a88a` |
| `platform_assays_published/suhre2017_dataset2.xlsx` | Suhre et al. 2017 (Nat Commun) Supplementary Dataset 2; https://www.ebi.ac.uk/europepmc/webservices/rest/PMC5333359/supplementaryFiles (member `ncomms14357-s3.xlsx`) | 152,599 | `d945d90433bcc6ac6ff3eb82ae19d0589681effa894720a24d97aaba494609b4` |
| `platform_assays_published/yao2018_SD1.xlsx` | Yao et al. 2018 (Nat Commun) Supplementary Data 1; https://static-content.springer.com/esm/art%3A10.1038%2Fs41467-018-05512-x/MediaObjects/41467_2018_5512_MOESM1_ESM.xlsx | 18,489 | `3369290df4595d7dea1a953294215df0d119c8a8736c3e5b6676548653eda658` |
| `platform_assays_published/zheng2020_ST1.xlsx` | Zheng et al. 2020 (Nat Genet) Supplementary Table 1; https://static-content.springer.com/esm/art%3A10.1038%2Fs41588-020-0682-6/MediaObjects/41588_2020_682_MOESM3_ESM.xlsx | 2,990,385 | `0812c04ca38150e67d6eae1bde3863331ffd61fc0f7634e1120780edd8328a14` |
| `platform_assays_published/enroth2014_SD1.xlsx` | Enroth et al. 2014 (Nat Commun) Supplementary Data 1; https://www.ebi.ac.uk/europepmc/webservices/rest/PMC4143927/supplementaryFiles (member `ncomms5684-s2.xlsx`) | 46,947 | `25a61c2f2fb24d7471404900c26ed8df0da6af1d37a6d5c4b589474b748e6e30` |
| `platform_assays_published/xu2023_SD2.xlsx` | Xu et al. 2023 (Nat Commun) Supplementary Data 2; https://static-content.springer.com/esm/art%3A10.1038%2Fs41467-023-36491-3/MediaObjects/41467_2023_36491_MOESM3_ESM.xlsx | 111,821 | `cf5488da38892896ff371f09d377ac55f0709755a5d9a91e5360f9befc02a847` |

The eight published list files were fetched straight to the volume (no local copy) by
`scripts/modal_biology_joins.py::fetch_platform_lists`; a file whose sha256 differed from
`verification/platform_list_sources.csv` would not have been kept
(`outputs/resource_counts/platform_list_files_20261001T174611Z.json`). The Eldjarn workbook's
sha256 and size were computed on the volume
(`outputs/resource_counts/eldjarn2023_workbook_heads_20261001T171804Z.json`). All nine are in
`modal_inputs_manifest.json` (2,060 files).

### Committed tables built from the pinned files (Modal, label `2026-10-01_round6b`)

| file | what | sha256 |
|---|---|---|
| `verification/ontology_edges.csv` | 96,473 unconditional `is_a` edges of the pinned MONDO and EFO files on canonical identifiers; unchanged from the first build apart from line endings | `5b8f0b3fe17aab4c885c04ad337cec2c980d35c69acc847c8a754f14deff7261` |
| `verification/therapeutic_areas.csv` | Open Targets 26.09 therapeutic areas per canonical outcome identifier (45,867 terms, 26 areas) | `31f61cdac2a185e217cd43e7d0358cb6489c284bff20b9c70ece8efb82540afe` |
| `verification/therapeutic_area_names.csv` | the 26 areas, with the three that are not disease areas marked | `646d346c6b333bc8967f149c7d29fc314acfc65c8898959017417b9aa7be7503` |
| `verification/platform_list_sources.csv` | the eight published assay lists: URL, sha256, sheet, identifier column, row filter | `c36f168dcdafcce93d6dfcd7122140dbb829822785d6a2600ad1563e071f6c04` |
| `verification/platform_assay_lists.csv` | accessions of every assay list, pinned packages and published lists | `978e0be7f5a3d4a950b928de6127180f6f919b5bd435a0b8db277018dd59be51` |
| `verification/platform_assay_lists.meta.json` | provenance of each list (rows, accessions, unmapped cells or symbols) | `2abd8a25bb3a2abc24848d188af57f321f332b2124fccbe731864df0197e3cf1` |
| `verification/platform_assay_attachments.csv` | all 28 pQTL dictionary rows attached; 14 by platform string, 14 read from the dataset's source paper (`coded_checks_pending`) | `2e562ea57d3cad7f39cde79f2cd792d10bd2a88e901c5a1e690a00e463a49013` |
| `verification/epigraphdb_trait_alias_seed.csv` | 65 snapshot trait names with the label of the term each stands for | `d73591f3d48df66e673a7e99e870fb4cfcea945833a9ab6703e6f99ba67d5903` |
| `verification/epigraphdb_trait_aliases.csv` | the seed resolved against the pinned MONDO and EFO files | `c08d4f8bb69e342b0b6f1918494bb46f5adf01a989eb78b13e8df709cb917119` |
| `verification/epigraphdb_trait_mapping.csv` | 225 traits: 187 mapped (79 as written, 43 after the colon, 65 by alias), 38 unmapped | `dba5241513da2506e0b9867f2b74a1442c222a2ce1d2a6254b5c73cf39894030` |
| `verification/epigraphdb_protein_mapping.csv` | 989 exposures: 973 mapped | `e809a3c1771ba142687bfcfd5ab22f17e5fcca9607fde84055de7bac0c6dcd7a` |
| `verification/pleiotropic_loci_eldjarn2023_ST36.csv` | 386 genes of 69 variant rows; byte-exact copy of the volume file | `717050fab7df62dc0ec804bd26561755e0d0ed85bb2a0c206bd178e0356d3cdf` |

The committed copies are byte-exact copies of the files the build jobs wrote on the volume, so
each has the sha256 its job recorded; the copies of the first build, which differed in line
endings, are in `verification/superseded/`. The drafted 18-category anchor table is not in the
repository (`docs/stage0_build/superseded_project_category_anchors.csv`).

### Resource-only counts and checks

| file | what | sha256 |
|---|---|---|
| `outputs/resource_counts/biology_resource_tables_2026-10-01_round6b.json` | ontology edges; therapeutic-area coverage; assay lists and pathways kept; EpiGraphDB mapping; ontology names giving several identifiers | `2b245d41a3052712da2d30816e57363c75b588d2fb708b184197917530e2e71d` |
| `outputs/resource_counts/drug_schema_check_20261001T172000Z.json` | ChEMBL 37 and Open Targets 26.09 columns and value counts; every registered value check ok | `2c86f9ac1adc2cdfb85a85c958fe80583216a6b6a98921880aa2b223c768329f` |
| `outputs/resource_counts/drug_index_counts_20261001T171911Z.json` | drug index built by the final code: 11,968 mechanism–component records, 36,131 indications, 173,850 reports | `102b88627a16e5397b9297b1141d9c9b55fb6e0047d853cf5ba8d096de7a8e69` |
| `outputs/resource_counts/platform_list_files_20261001T174611Z.json` | the eight published list files: sha256, sheets, header, row counts | `51b1f76bf4fa476e5064dbe3fbc347aac1497553555ae709ef34b06b6f1bf22c` |
| `outputs/resource_counts/eldjarn2023_workbook_heads_20261001T171804Z.json` | workbook sha256, size and sheet heads | `fdd1b07cad00c58bbcc25d32fdadfdf99136d5f72fa0d5a1268690e6aecdd603` |
| `outputs/tests/pytest_all_modal_20261001T180435Z.txt` | 464 passed (whole suite, on Modal) | `406897802624190ea2d3bb77ef161cc7157406a6a24ab98c3180b252d12149a7` |
| `outputs/dry_run_biology/20261001T180435Z/stdout.txt` | synthetic dry run of the registry assembly, biology joins and sensitivity analyses: every value equals its hand-worked expectation | `aff3635e2f46481fa7ad26822e9ba86d1973844fb87674e31bbd52934d961525` |
| `outputs/dry_run_drug/20261001T180435Z/drug_tables.json` | synthetic dry run of the drug joins under the primary rule and the six sensitivity rules | `3f5dec2e4e41eb48fcdb20e4becea4583d09279d2ae4b5a89eaa57881559f130` |
| `outputs/dry_run_drug/modal_wiring_synthetic_round6/drug_tables.json` | drug joins end to end on Modal: real index, synthetic claims, claim-tag file, committed edges; every synthetic pair leaves the join | `d0c63b88e644beac2d8838a37b2edb529fd9d699be48aa325ca090a3b0914ace` |
| `outputs/dry_run/20261001T180442Z/h1_h2_tables.json` | synthetic dry run from search records to the H1 and H2 tables | `5eac4f56159c2dc9b5a3d275f0618804737facee1b8747249c33f98e53b34edc` |

Earlier runs of the same checks are kept beside these: the first whole-suite run (400 tests,
`…171322Z`), a run in which the biology dry run failed on a fixture column added for the trait
alias rule (`…175355Z`; fixed), and runs `…175656Z` and `…180113Z`. 48 deliberate rule changes
each made a test fail (`docs/stage0_build/mutation_check_round6.py`).

### Counts that set a rule

- Ontology names: 156,053 labels and exact synonyms; 1,965 give several canonical identifiers;
  921 are resolved by dropping HP, OBA or Orphanet identifiers beside a MONDO or EFO identifier;
  1,044 stay ambiguous (704 one MONDO and one EFO identifier; 238 several MONDO; 93 several EFO;
  9 other).
- Therapeutic areas: 45,896 `disease` rows, 26 areas; MONDO human-disease terms
  24,954, of which 17,108 in the file and 24,601 with an area through nearest ancestors; EFO
  measurement terms 25,404, of which 25,398 in the file.
- Assay lists: accessions and pathways kept by the 10–500 rule per attached list are in the
  `attached_lists` block of the biology resource table; pooled, 6,119 accessions and 718
  pathways; the Zheng 2020 alternative background, 4,172 accessions and 517 pathways.
- EpiGraphDB: 145,037 of 179,928 estimates on mapped pairs (136,942 distinct canonical pairs).
- Drug resources: as in the round-6 foreknowledge item of PREREG.md.

### Dependencies

`pyproject.toml` and `uv.lock` at the repository root: Python 3.12; httpx 0.28.1, modal 1.4.3,
numpy 2.5.3, openpyxl 3.1.5, pyarrow 21.0.0, pydantic 2.13.5, pyyaml 6.0.3, rapidfuzz 3.14.6;
pytest 8.4.2. The Modal images pin the same versions.

## Round-6 fixes (pre-freeze, 2026-10-02)

Review `planning/perplexity_paper1_final/05_REVIEW_round6.md`; item-by-item in
`06_ADJUDICATION_round6.md`. No claim, pair, registry record or in-window record was read: the
files below are supplementary tables of pQTL source papers, the pinned ontology and resource
files, and synthetic records.

### Inputs added to the Modal volume

| file on the volume (`/02_claims_meta/inputs/platform_assays_published/…`) | source | bytes | sha256 |
|---|---|---|---|
| `folkersen2017_S3.pdf` | Folkersen et al. 2017 (PLoS Genet) S3 Table; https://www.ebi.ac.uk/europepmc/webservices/rest/PMC5393901/supplementaryFiles (member `pgen.1006706.s005.pdf`) | 190,683 | `9fe8bed8ca5acbba1ea828611fa0d3ee33eafe55d5aac586a8f7c2252c88451a` |
| `enroth2014_SD2.xlsx` | Enroth et al. 2014 (Nat Commun) Supplementary Data 2; https://www.ebi.ac.uk/europepmc/webservices/rest/PMC4143927/supplementaryFiles (member `ncomms5684-s3.xlsx`) | 95,591 | `7ae9d42fc270e785bfe4de9cb2ec6c36725d19460004256e8c202dc01f7a20d9` |
| `koprulu2026_S5.xlsx` | Koprulu et al. 2026 (Cell) Table S5; https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13343581/supplementaryFiles (member `NIHMS2173841-supplement-MMC5.xlsx`) | 94,076 | `b8c18cb41d7680b19f0461bd621b94b3ce5dfe9ea3ed3e128d465c671f1c9eed` |
| `katz2022sciadv_tables_S1_S6.xlsx` | Katz et al. 2022 (Sci Adv) Tables S1 to S6; https://www.ebi.ac.uk/europepmc/webservices/rest/PMC9390994/supplementaryFiles (member `sciadv.abm5164_tables_s1_to_s6.zip`, its member `sciadv.abm5164_tables_s1_to_s6.xlsx`) | 830,921 | `bd8ba000d37fb2d56bcb68a6eb19e68c71caeee726c40251e2d9976efdca34d6` |
| `gilly2020_SD7.xlsx` | Gilly et al. 2020 (Nat Commun) Supplementary Data 7; https://static-content.springer.com/esm/art%3A10.1038%2Fs41467-020-20079-2/MediaObjects/41467_2020_20079_MOESM10_ESM.xlsx | 29,270 | `078dc5395da72d66546081625d1c804a7a576a8c65203f794ff2be9cce001670` |
| `png2021_SD8.xlsx` | Png et al. 2021 (Nat Commun) Supplementary Data 8; https://static-content.springer.com/esm/art%3A10.1038%2Fs41467-021-27387-1/MediaObjects/41467_2021_27387_MOESM11_ESM.xlsx | 27,269 | `1b872d9843835fe5c30c69bf75b7948a274766964cc6ec29b4141462399c62ae` |

The files were fetched on the volume from these URLs on 2026-10-02 by a probe job
(`docs/stage0_build/probe_backgrounds_round6.py`) and moved into the registered folder
with their sha256 checked (`docs/stage0_build/copy_probe_files_round6.json`); two of them
were fetched there directly by `scripts/modal_biology_joins.py::fetch_platform_lists`, whose
Europe PMC download of the Koprulu archive then broke off, so the job did not complete. The job
re-checks every file's sha256 when it is run again. Not obtained: the supplement of Katz et al.
2022 (Circulation; PMC9158509), which Europe PMC reports as not open access.

### Committed tables (Modal, label `2026-10-02_round6_fixes_b`)

| file | what | sha256 |
|---|---|---|
| `verification/platform_assay_attachments.csv` | all 28 pQTL rows with their background level (12 analysed, 11 assayed, 5 platform), whole-panel list and the counts the source states; the 14 rows read from source papers are `coded_author_confirmation_pending` | `d67f70c9b5cf28d10c0c2b2a523940b5076221d85cce788d6dcdf5ca67353454` |
| `verification/platform_list_sources.csv` | 14 list sources: 10 published files (URL, sha256, sheet, column, filter) and 4 derived tables | `5b6b08535c27d58a8b356fe409ac315b0818279c14ca1167f6c103619a173484` |
| `verification/published_source_files.csv` | the 4 published files the derived tables are built from: URL, zip member, sha256 | `b7c94e9062087c4bcc29b208d44923ee18dca2fcbe526bd531cdef831866a1b4` |
| `verification/published_lists_derived/improve_folkersen2017_S3.csv` | Folkersen 2017 S3 Table read from its PDF: 92 genes, 83 included | `808da6fada52f3dea578b974bd4954c9dd30ed2b24de181d4351794c53e1fed3` |
| `verification/published_lists_derived/nsphs_enroth2014_analysed.csv` | Enroth 2014: 92 analytes, 77 analysed | `67d35accfb7900082965b493b3267d8d0ea9b36d8061a3168b3cf3d119e15ebb` |
| `verification/published_lists_derived/scallop_koprulu2026_S5_targets.csv` | Koprulu 2026 Table S5: 1,161 targets with their UniProt cell (1,032 distinct cells) | `35addfef914fa8636e64320c22c6c2df74376b2be86a705fed4bb63ae1e3f993` |
| `verification/published_lists_derived/jhs_katz2022_soma13k_reagents.csv` | Katz 2022 (Sci Adv) Table S2: 1,301 SomaScan 1.3k reagents, 1,297 UniProt cells (1,360 rows) | `b339784a8fe6b2f50109dc499a2eae130d439911cd3757e89f4f332f8458565a` |
| `verification/published_lists_derived/published_lists_derived.meta.json` | source checksums and counts of the four derived tables | `6bf469b22ceae8755c8bbd898a5f5432d7ff1096ab5bfcbf4c545b5de68c5f81` |
| `verification/platform_assay_lists.csv` | accessions of every assay list, the analysed lists included | `3a01aa3c4ed2fe6c616bc7d767de3d7bee18ec9090509837f10e8c3620c68e96` |
| `verification/platform_assay_lists.meta.json` | provenance of each list | `a2def84b1d7e876ea943582a79283ad1df12dc80f7e5aeac3560f8d15b933627` |
| `verification/outcome_alias_seed.csv` | 58 hand-written outcome aliases, each with relation, source and rationale | `02783d0b2006f67c4fcd3eadcdafae244e034e96f047f74f47af823c9c3cd598` |
| `verification/outcome_aliases.csv` | the seed resolved against the pinned files | `663555898aa3d9fa1892693a8c1bd71dc4f17f81f382f852ac7da33c12a3f240` |
| `verification/phenotype_cross_references.csv` | 247 HP terms that exactly one canonical disease term cross-references in the pinned MONDO file | `0756154ed75c8c7795ac8928ae914f111a6c7c05c81eff4bc8104ee3ccfd4a67` |
| `verification/phenotype_cross_references.meta.json` | its inputs and counts | `2c7e38c8764135d79e1a788b69ec1777db3543693aa175c4b0a7b530808a9953` |
| `verification/obsolete_label_replacements.csv` | 901 labels of obsolete EFO terms with their single live replacement | `a9578b07753d7f77606404ced6af5cd5289b9909489760ca05465aedc43db3d7` |
| `verification/obsolete_label_replacements.meta.json` | its inputs and counts | `8b9d0e961e91891f69e96f2c4d015880f093863197c8a259702076b5b242ad25` |
| `verification/epigraphdb_trait_alias_seed.csv` | 66 snapshot trait aliases, each with relation, source and rationale | `f4b0bfcfd559479d48691499f356870cebbbe9f5a1c31ad4cbf3287c082cda22` |
| `verification/epigraphdb_trait_aliases.csv` | the seed resolved against the pinned files | `322b98891819c2f0461a86df9e39da2407528aa05f7a579a6b65cef99275f714` |
| `verification/epigraphdb_trait_mapping.csv` | 225 traits: 191 mapped (11 by ICD-10 cross-reference, 66 by alias, 79 as written, 35 after the colon), 34 unmapped; 16 through a proxy alias | `097b38acecffe2bd5c3b8009d79ebc2155f80f3feda1546ccfdfdb0bb0c15cf8` |
| `verification/therapeutic_area_names.csv` | the 26 areas, with the six that do not count toward hubs marked | `87a51779e3e2c4621d04b0df7637cd573f4c40e6ca1ff64676e1a4769564614b` |
| `modal_inputs_manifest.json` | 2,066 files (six published supplementary files added) | `a23940d79e1b4cb0d5817edce0efe90246606b8235dcd3805e2c188032a74ffc` |
| `PREREG.md` | v15 in OSF layout (layout only; foreknowledge option placeholder pending the author's choice), with the three log lines of 2026-10-02; v15 before the layout change was `8f37aa327903f3afea22fef7cf19afabc4d5f9442e61b7670964b27a5fc087b9` | `cf3482d100dc9e76247e157152e6e72e99186f389a1e93300bea1950bad63bad` |
| `RUNBOOK.md` | gate-audit steps added | `74efa50e0d20cb6c6a9091a57ec4947bd51b85a8dff1c1bcfb3d7884d06698fc` |
| `outputs/tests/stage0_file_sha256_2026-10-02_round6_fixes.txt` | sha256 of every script, test, fixture, prompt and search file (113 files) | `96d4ca17b163a8e0ac06da56e7c79b99bd0a5b1b51e72b8e05428a0aa4af9fe5` |

`verification/ontology_edges.csv`, `therapeutic_areas.csv`, `epigraphdb_protein_mapping.csv`,
`mondo_efo_collision_table.csv` and `pleiotropic_loci_eldjarn2023_ST36.csv` are unchanged. The
tables these replace are in `verification/superseded/2026-10-02_before_round6_fixes/`; the trait
tables of the first build of the day are in `…/2026-10-02_round6_fixes_first_build/`.

### Checks

| file | what | sha256 |
|---|---|---|
| `outputs/resource_counts/biology_resource_tables_2026-10-02_round6_fixes_b.json` | resource tables of the final build: backgrounds by dictionary row, alias completion, trait mapping | `caacd9ec63bc134bb4ae99013309e804167b121aa1cb4a2f1867b3d5d2707c7d` |
| `outputs/resource_counts/biology_resource_tables_2026-10-02_round6_fixes.json` | the first build of the day, with the trait rules in the order labels before aliases (superseded) | `82599d24e1f56359282d81d2a79c9569771b449ab751a2f4e66b4d8d12da34f8` |
| `outputs/tests/pytest_all_modal_20261002T143504Z.txt` | 564 passed (whole suite, on Modal) | `2acc26cfa41f66e06d67e786681b1b223b2f144da18d52ea09a01b28f0106310` |
| `outputs/dry_run_biology/20261002T143504Z/stdout.txt` | synthetic biology dry run: every value equals its hand-worked expectation | `1b4392799ebaf7b04436deb95c1cb373c37eb6e795d99751dd47468aa21bb3ba` |
| `outputs/dry_run_drug/20261002T143504Z/drug_tables.json` | synthetic drug dry run under the primary rule and the six sensitivity rules | `9e960aa6cbe00ba23d1d9a42accece063bf2290a779a8ba983a9fd8fb4b596c1` |
| `outputs/dry_run/20261002T143512Z/h1_h2_tables.json` | synthetic dry run from search records to the H1 and H2 tables | `abfc0b863e07f45e271e40a8600cc2b2aa79820ef1bd0797ac4cabdb2e84fc09` |

The earlier runs of the day are kept: `…143102Z` (3 of 564 tests failed, each a test that still
expected a rule this round changed; the tests were corrected) and `…143224Z` (564 pass, before a
redundant condition was removed from `canonical_ids.phenotype_term`). 55 deliberate changes of
the round-6 rules each made a test fail (`docs/stage0_build/mutation_check_round6_fixes.py`,
run on Modal without bytecode caching).

### Counts that set a rule

- Backgrounds: reviewed accessions and pathways kept per list are in the `attached_lists` and
  `backgrounds_by_dictionary_row` blocks of the resource table; pooled, 6,117 accessions and
  717 pathways (6,119 and 718 with whole panels). The commercial SomaScan 1.3k list has 1,063
  accessions against the 1,297 UniProt identifiers of the Jackson Heart Study reagents (82%).
- Outcome names: 47,734 labels and exact synonyms give no MONDO or EFO identifier; the
  phenotype cross-references complete 282 of them (247 HP terms). 4,931 obsolete EFO terms, of
  which 901 give an obsolete-label replacement.
- EpiGraphDB: 135,001 of 179,928 estimates on the pairs the primary join reads; 147,819 with
  the proxy aliases.

### Dependencies

`pypdf` 5.9.0 added (it reads the S3 Table of Folkersen et al. 2017); `uv.lock` has 49
packages. The Modal images of `modal_biology_joins.py` and `modal_all_tests.py` pin it.

## Round-7 fixes (pre-freeze, 2026-10-02)

Review `planning/perplexity_paper1_final/07_REVIEW_round7.md`; item-by-item in
`08_ADJUDICATION_round7.md`. One rule changed (novelty terms inside a protein or outcome name);
the rest is wording. No claim, pair, registry record or in-window record was read; tests and dry
runs use synthetic records, fixtures and committed tables.

### Files changed

| file | what | sha256 |
|---|---|---|
| `scripts/tag_wording.py` | the name rule applies to novelty terms; raw matches and the flag without the rule kept | `94f11e8c17d6caef3da05ec2b392b0d5ed93c47b4857e66a23c79aac187c96d9` |
| `scripts/claim_tags.py` | docstring only | `d73ada65508dfd9bec2a751381cc2115a5844c28e98b9b553d678c36ed47e5a6` |
| `scripts/gate_audit.py` | the audit state carries `cap_reached_without_satisfying_tolerance` | `9fd360f1f1f91534532396d98f0f04f26d18217f2755c40adf3fb8912201997d` |
| `scripts/funnel.py` | lists the chase rounds whose audit stopped at the cap above the tolerance | `c7aaad8ba6da6c6eaccc6cb3cad2bd6a0deecac9c12b1bef78c7fa20f59c8b6f` |
| `tests/test_prefilter_wording_sample.py` | hand-worked novelty-name cases | `28018bd80cdd2861ff725b6c73a025a4a9d06217fb8ceadfda0daeaefc91b9a7` |
| `tests/test_claim_tags.py` | novelty flag in the claim tags | `21525ac4930336a37d7cff42144dc29997bca20656f99a0782604d92ad28fdc7` |
| `tests/test_gate_audit.py` | cap state | `cc2478fabe6cd4996d67bd0776f75a8f3b18fd2edbd842cc64880c6a55a80ef5` |
| `tests/test_stage_reports.py` | capped rounds in the funnel | `4902c6b807959db22f5834140fa96b66cadfdf39220e3fa36b65792185fdd494` |
| `verification/platform_assay_attachments.csv` | Jackson Heart Study row labelled a companion-paper, study-specific analysis-eligible background; no other cell changed; the 14 rows read from source papers stay `coded_author_confirmation_pending` (confirmed by the checker at round 7; the author has not yet answered) | `037473d326d555a40bfcfd575e1e67985f21ae4c27665a874f5b5918e193c0d0` |
| `OPEN_QUESTIONS.md` | round-7 outcomes | `29f605f78d78b03833c9b5cc1bd4c6a96d54a981f7558341340e6684267e2e56` |
| `outputs/tests/stage0_file_sha256_2026-10-02_round7_fixes.txt` | sha256 of every script, test, fixture, prompt and search file (114 files; `tests/pytest.ini` added to the listing) | `ebacc3343ceffa01f6019a1beb789b102442b8b6733c04058b60d8e75592dee7` |

| file | what | sha256 |
|---|---|---|
| `PREREG.md` | v16: the novelty name rule, the round-7 wording, the OSF foreknowledge option, foreknowledge items 12 and 13, and the log to the round-7 line; identical to `planning/perplexity_paper1_final/PREREG_paper1_v16.md`; diff from v15 in `PREREG_v15_to_v16.diff` | `64ac53cd1b1f8bd34c0c9a7ee41115bd190cf37ac81699e97c68af7023a36c2b` |

A log line appended later changes this hash; the hash of the registered text is the one
`prereg freeze` records.

### Checks

| file | what | sha256 |
|---|---|---|
| `outputs/tests/pytest_all_modal_20261002T150722Z.txt` | whole suite on Modal on the v16 text: 576 pass | `0d28b85981e9f96937df9ccc1a962d8d6b527385222a579a2f694fec5402001e` |
| `outputs/dry_run/20261002T150729Z/h1_h2_tables.json` | synthetic dry run from search records to the H1 and H2 tables | `fb7b49f0110b5fb0be680f9ae0af08aed97842769feb2abe1640b46c45120676` |
| `outputs/dry_run_biology/20261002T150722Z/sensitivity_tables.json` | synthetic biology dry run | `b57acb71ef23a26bc8230b8c52359adeecbcd8b434cda8c0166bd3295cdb7831` |
| `outputs/dry_run_drug/20261002T150722Z/drug_tables.json` | synthetic drug dry run | `61b2878e98e49e5fb1afa0c4d6f6ec8b683d8c65fceb7eb62fd03b690a8cf359` |

13 deliberate changes of the round-7 rules each made a test fail
(`docs/stage0_build/mutation_check_round7_fixes.py`, run on Modal). The OSF dry run
(`docs/stage0_build/osf_dry_run.py`, sends nothing) accepted the text before the round-7
edits; the edits change no heading and no multiple-choice answer.

Four rows of the round-5 section above (`scripts/canonical_ids.py`, `tests/test_canonical_ids.py`,
`scripts/fetch_fulltext.py`, `scripts/fulltext_concordance.py`) give the sha256 those files had
on 2026-10-01; the files changed in the stage-0 build and the round-6 fixes, and their current
sha256 is in `outputs/tests/stage0_file_sha256_2026-10-02_round7_fixes.txt`. For every other
file in the repository, the last row of this file that names it gave its sha256 on disk when
this section was written; earlier rows give the sha256 at their date.

## Three-gates pass (pre-freeze, 2026-10-02)

Records for the three tools, made before the first commit. No rule changed. No claim, pair,
registry record or in-window record was read; the one Modal run reads synthetic claims. Paths
under `planning/` anywhere in this file name the author's working files, which are not in the
public repository.

**Results ledger.** `.results/` at the repository root (`ledger.jsonl`, `ledger.head`; lock files
ignored), started with the `results` build of reproducible-science `b078cb2`, which tracks the
ledger in git. It holds the `init` event and one `run` event,
`prefreeze_ledger_proof_20261002`. Nothing is sealed yet: the inputs are sealed at the freeze
(RUNBOOK.md, §Results ledger), because a file sealed and then edited is reported as `RESEALED`
from then on.

**Quotations.** The claims files moved from `planning/source_reports/verification/claims/` to
`claims/` at the repository root: 199 files, 4,499 quotations, all found
(`citations verify --claims claims/`). The 199 source texts are in `sources/` at the repository
root, which is ignored; 27 claims files that pointed at texts in other working folders now
point there, the sha256 of each text unchanged. Three files gained a `url:` (Cochrane Handbook
chapter 4, the Mondo documentation, the Open Targets documentation), so every source records a
`doi:` or `url:`. Two source notes lost a sentence about a working review document. 29 claims
were added and none edited (`docs/source_verification/QUOTE_WARNINGS_2026-10-02.md`). The one
uncommitted record of the shared citations library (arXiv 2405.14860, another project's) was
committed there (`806a4ab`).

**Evidence in `docs/`.** Moved from `planning/`, with the notes addressed to co-workers removed
and paths updated: `docs/source_verification/` (`VERIFICATION.md`,
`SCOOP_RERUN_2026-09-30.md`, `compositions/`), `docs/feasibility/`, `docs/stage0_build/`
(platform lookups, rule table, mutation checks, probes, query-translation checks, OSF dry run).
The builders' open-point lists, the review documents, the source report, the confirmation list
of the 14 platform rows and two probe outputs that reproduce investigators' e-mail addresses
stay outside the repository.

### Files changed

| file | what | sha256 |
|---|---|---|
| `scripts/stage_record.py` | records a stage in the results ledger through one manifest; compares local copies of Modal results with the volume files; `verify` rehashes every file a manifest names | `f27996994be5d002e5303aec5e0e5b21fc15ec09db8ab8e2fa7c1cc30952d6cb` |
| `scripts/modal_hash_volume.py` | entrypoint `tree`: bytes and sha256 of every file under one volume folder; `main` unchanged | `7476ccd17fabdb9ddad8ce3b6d3a2953c8c4119bd1c5a67cbf425ed118b5de36` |
| `tests/test_stage_record.py` | 9 hand-worked cases | `fad5c8c542bc5bc0c54538cf22977c45544cac79f84dd4e7294b0d917bf031b3` |
| `RUNBOOK.md` | §Results ledger: the seal and access lines at the freeze, the record line of every stage, the checks | `88e3e76419d170e780f26aa12ffbe288882f95f6add1d8b0a440552ca890a9a6` |
| `OPEN_QUESTIONS.md` | items 81 to 86 | `0e472d470daece14fb6c5906a92cd9ab6ddf80a03a8b67b8fbe23585734777df` |
| `modal_inputs_manifest.json` | six `note` strings name `docs/stage0_build/copy_probe_files_round6.json`; no file entry changed (2,066 files) | `03b054b9d27551d9329d25231974ea5d142be7e9b6c302c6a5918ebb9198e767` |
| `outputs/tests/stage0_file_sha256_2026-10-02_three_gates.txt` | sha256 of every script, test, fixture, prompt and search file (116 files) | `34bd3339823f9083cda122879e6e15eebef30164e741ed55e03984af0824c8f1` |
| `outputs/tests/claims_docs_sha256_2026-10-02_three_gates.txt` | sha256 of every file of `claims/` and `docs/` (257 files) | `4dcd2493805c645b39ff0e1cef08d799e48f170934d24d285c84d88e2f2060c7` |

| file | what | sha256 |
|---|---|---|
| `PREREG.md` | v16 with the moved paths in the body, one sentence in §Explanation of foreknowledge on paths under `planning/`, and the log to the two lines of this pass; diff of the body in `planning/perplexity_paper1_final/PREREG_v16_to_v16_paths.diff` | `3d703b6eb2a6969882f04e921edf6be1d0c9b0894405a4707c8a99bfa33a55cc` |

A log line appended later changes this hash; the hash of the registered text is the one
`prereg freeze` records.

### Checks

| file | what | sha256 |
|---|---|---|
| `outputs/tests/pytest_all_modal_20261002T160140Z.txt` | whole suite on Modal on this text: 585 pass | `2e62b20f5da48f7357598dbfe056f8b5207023af2f5dcd3ca8984f0c8befa939` |
| `outputs/dry_run/20261002T160157Z/h1_h2_tables.json` | synthetic dry run; equal to the round-7 run apart from `written_utc` | `cc0df6fc39faa957ed23f10a53070c2cf2b416ddbc38386a239fc4cabc96c57f` |
| `outputs/dry_run_biology/20261002T160140Z/sensitivity_tables.json` | synthetic biology dry run; same sha256 as the round-7 run | `b57acb71ef23a26bc8230b8c52359adeecbcd8b434cda8c0166bd3295cdb7831` |
| `outputs/dry_run_drug/20261002T160140Z/drug_tables.json` | synthetic drug dry run; equal to the round-7 run apart from `written_utc` | `0f32c73fa53fd78d1fe3bd52500b9d484b2af007df2845a7c263f81d9588c896` |
| `outputs/results_manifests/prefreeze_ledger_proof_20261002.json` | manifest of the wrapper's one pre-freeze run: stage-5 drug joins on Modal on synthetic claims; 3 local copies equal to the volume files | `46565c42d6c36b76316d293d069229c9c77cfdc09dbd278aa95bf1bae1e5f405` |
| `outputs/results_manifests/ledger_proof_20261002.volume.json` | bytes and sha256 of the 6 files of that run's volume folder | `c30b03948440eb800b2c7b5ecf95d63dcd59bf1e9fdf70e12eabb2326d727bd1` |
| `docs/stage0_build/osf_dry_run_result_2026-10-02_final_text.txt` | OSF dry run (sends nothing): the text is accepted | `2b6b3fa6965d56f728e21aa2df45a55a8f982fbdbc77acb7da03eece7277d6fb` |
| `docs/stage0_build/mutation_check_stage_record.json` | 7 deliberate changes of the wrapper's rules each made a test fail | `868c5ea70153a4c07937594618d1aff38802ace01dcdd9d90cdf83d98edff68c` |
| `docs/source_verification/QUOTE_WARNINGS_2026-10-02.md` | reading of the 1,572 quotations `citations verify` warns about | `54850bb930f8ac6e1e1cbb68c4e8c1b683c4ea600ae8a7e967d9528d85d2fe2d` |
| `docs/source_verification/citations_fetch_2026-10-02.txt` | `citations fetch` on an empty copy of `claims/`: 2 fetched, 156 differ, 41 unavailable | `a798606177a5670b21dbaf3087b23421fad2e918fedb850a1590bb4346f75a6d` |

`prereg check`: not frozen. `results verify --files`: chain intact, the three recorded files
match. `uv run scripts/stage_record.py verify`: the manifest's files match.
`citations verify --claims claims/`: 4,499 found, 0 not found; warnings 1,544 short, 26
truncated, 6 normalized, each read.

## Original-file pins (pre-freeze, 2026-10-02)

No registered rule, table, script of the pipeline or test changed. `PREREG.md` was not edited.

**Why.** A text pin names a text extracted from a paper, so a reader's download of the paper
never matches its sha256 (`citations fetch` on an empty checkout: 2 fetched of 199). Where
`citations` reads the original format itself, the original file is now pinned beside the text.

**What changed in `claims/`.** 125 files `claims/<stem>_original.yaml` were added, each pinning
an original PDF, XML or text file by sha256 with its `url:` and `doi:`, and holding the
quotations of `claims/<stem>.yaml` that `citations pin` resolved in that file: 971 quotations.
Nine text pins whose text is byte for byte a file in the PMC open-data bucket gained one line,
`url:`, in their `source:` block (`demontis2019adhd_main`, `demontis2023adhd_main`,
`grove2019asd_main`, `howard2019dep_main`, `mullins2021bip_main`, `nievergelt2019ptsd_main`,
`ripke2014scz2_main`, `trubetskoy2022scz3_main`, `wray2018mdd_main`). No quotation was edited
or removed. The originals are in `sources/original/` (125 files, 257 MB), which is ignored.

**Result.** A reader can fetch and match 130 of 199 sources and check 1,012 of 4,499
quotations against files they downloaded (before: 2 sources, 19 quotations). Spreadsheets and
`.docx` supplements (48 sources, 2,986 quotations) have no reader in `citations`;
`docs/source_verification/FEATURE_REQUEST_citations_extractors.md` asks for one.

### Files added or changed

| file | what | sha256 |
|---|---|---|
| `outputs/tests/claims_docs_sha256_2026-10-02_original_file_pins.txt` | sha256 of every file of `claims/` and `docs/` (391 files); against the three-gates listing, 9 files changed (the nine `url:` lines) and 134 were added | `60e5db1270460c5fc57f7b8ad0152fcb1c2b5a50007a0b07e7b783ad3af384a5` |
| `docs/source_verification/REFETCH_STATUS_2026-10-02.md` | counts before and after, by how each text was made, and what a reader still cannot fetch | `7e2543b58d0d4a091bb27f224ff4ba3fff3bd95cd0c7d4d3b2e81234583768ec` |
| `docs/source_verification/FEATURE_REQUEST_citations_extractors.md` | request to the tool's maintainers: raw file plus named extractor, readers for JATS XML, spreadsheets and `.docx` | `71dff6efeba9e639369df01ece2b8c3092baf50e465fa0ec7171e31329410349` |
| `docs/source_verification/repin_originals.py` | obtains each original, writes its claims file, passes each quotation to `citations pin` | `55afa9535892ebf44fcbe6ff41ff17a75d5d81a80e6651a4934dcaabf5dcb880` |
| `docs/source_verification/originals_plan.json` | the 125 originals: address, `doi`, and the held copy where a plain download is refused | `bdacc0b1ef75f7809689f71de55a1cfdb12bf8f08564b5e072f8509e62925056` |
| `docs/source_verification/repin_originals_summary_2026-10-02.json` | one row per source: class, quotations, original pinned, quotations in it, refusals, whether a reader can fetch it | `83de66b8da93be62c3a71d4a18415aef0440babc452f8a08a8102a51b6c8b6e2` |
| `docs/source_verification/repin_originals_result_2026-10-02.json` | run record, PDFs and bucket text: 777 pinned, 260 refused | `cc70a129fc2095b196de5d7f4bfbd03c8faedf0698bb50ad4cac8e0305a2f122` |
| `docs/source_verification/repin_originals_xml_result_2026-10-02.json` | run record, XML: 194 pinned, 134 refused | `7c655257303711118446bcdda12403ce4988df101f47ad18dfd7f9480b480412` |
| `docs/source_verification/repin_originals_served_copies_result_2026-10-02.json` | run record, five PDFs pinned again from the copy their address serves | `d75f386bc45bdb566aff2937e76df78ac5ea2a5ff200b734034c598d1c9089b9` |
| `docs/source_verification/citations_fetch_after_repin_2026-10-02.txt` | `citations fetch` then `verify` in an empty folder on the 136 new or changed claims files: 130 fetched, 1 differs, 5 unavailable; 1,012 found, 31 unchecked | `3cd6b21be76dd04a2d0cbdeeab9b9ecd8e68ec8c984929aa3c3cff2f93fb899e` |

`citations verify --claims claims/` with the sources present: 5,470 found, 0 not found
(4,499 text-pinned quotations and 971 pinned again in an original); warnings 1,775 short, 44
truncated, 14 normalized. The 18 new truncation warnings sit on quotations whose text pin
carries the same warning, each read in `docs/source_verification/QUOTE_WARNINGS_2026-10-02.md`.

## Dress rehearsal (pre-freeze, 2026-10-02)

The freeze, the ledger and the manuscript checks were run end to end on two scratch copies
built from the path list of the first commit (`docs/stage0_build/DRESS_REHEARSAL_2026-10-02.md`).
Nothing was committed, frozen, sealed or sent to OSF in this repository, and its ledger still
holds its two events. No registered rule, table or estimate changed; `PREREG.md` gained one log
line and nothing above its log changed. No in-window record, claim or pair was read; no search request and no GPT-6.1 Sol
request was made (the stage commands ran on the stored pre-2019 smoke search, the cached
exchanges of the 30 development abstracts and the synthetic registries). The two rehearsal
folders on the Modal volume were removed afterwards.

Twelve findings, each with what was done, are in the rehearsal file. Those that changed a file
here: a clone would have held 22 CSV tables under other bytes than their recorded sha256; a seal
of `PREREG.md` breaks at the first log line; the parked census plan failed `prereg check` at the
repository root; stage 4 had no command for the claim checks on the pinned files; two scripts
replaced an existing output.

### Files changed

| file | what | sha256 |
|---|---|---|
| `.gitattributes` (repository root) | `* -text`: every file is stored byte for byte, so a clone holds the bytes whose sha256 this file and the ledger record (22 CSV tables end their lines with CRLF) | `46ce136d18e1eca2afc96f33bb553c2a1ea6f2894b12644aae0a3704fddcfe0e` |
| `RUNBOOK.md` | section "At the freeze"; stage 4 claim checks on Modal and the two reference files fetched; stage 5 recovery lines; the freeze record sealed in place of `PREREG.md`; corrected stage-4 folders; `--frozen-at` names the commit of the `**Status:**` line; manuscript checks | `4e84b03bb02dd46dff1f1210147028d0a9729b7e0f77c5967a1edb6fbfb39b0f` |
| `scripts/stage_record.py` | `plan` writes the freeze record (commit, plan sha256, date of the header, after `prereg check`); `verify` checks it; `--volume-map` takes one file | `d7b6bdb1867d2896b4f70415619a0ac3120c305b22515ff7bd11e0d6aa59ee3c` |
| `scripts/modal_biology_joins.py` | entrypoint `verify_claims` (stage 4): `verify_claims.py` against the volume's pinned files, results under `/02_claims_meta/stage4/`; nothing else changed | `4d0ce2f478cbd244a341bea25d26aa571d31ebd72f5925ae80abec79b346aa85` |
| `scripts/run_extraction.py` | refuses a label whose parsed file exists, before any request; requests, prompts and parsing unchanged | `1c5890a32438e52965690c2df55268fad0b432c838d1f2d13f75235df0d6da5a` |
| `scripts/apply_eligibility.py` | refuses to replace its decisions file; the rule (`decide`) unchanged | `3513ddd6d689e74b565b7c40cf322711b1b2c551f72f907f64b635ae65f9295a` |
| `scripts/build_registry.py` | `pinned_file`: the HGNC and UniProt files must be present with the sha256 of `reference/MANIFEST.json`; no table or estimate changed | `99a80aacbc9cae3aa1deac95ac4d17e0b4ba2477accd2e5f4982eb73427b3104` |
| `tests/test_stage_record.py` | 14 hand-worked cases (5 added) | `f197984d50e02fb20e912a89ce382d033caa879e21339e24c393e72969d34d5b` |
| `tests/test_rerun_and_pinned_file_guards.py` | 3 cases: the two overwrite refusals and the pinned-file check | `a4599159ebbcab639f7fa7b99e552036d3525251ecc9e29e500860bec33e4af2` |
| `../01_census/PARKED_PLAN_v6_never_frozen.md` | the parked census plan, renamed from `PREREG.md` (content unchanged) so that `prereg check` at the repository root does not count a plan that will never be frozen | `0f6dc56e96954bec2901cb3bdc018da6cd097b7e97aabd81dd0a08fa134ef6b8` |
| `../01_census/PARKED.md` | names the renamed file and why | `b5083d28f7229624d079dcfbb42f2cf9019fceeff657eef75f981c1401b45e8f` |
| `outputs/tests/stage0_file_sha256_2026-10-02_dress_rehearsal.txt` | sha256 of every script, test, fixture, prompt and search file (119 files) | `5ff9f4451047b18de98ce2245865feed616db7e29f3f8b01584863cb1af19e9c` |

`scripts/external_lists.py` and `scripts/modal_external_lists.py` appear in the listing and are
not part of this pass.

| file | what | sha256 |
|---|---|---|
| `PREREG.md` | v16 with the log to the line of this pass; body unchanged | `7ffac5ce3f68111f3acb1b5ad992f0d25e89a16efdb349acc31a5302036fff27` |

A log line appended later changes this hash; the hash of the registered text is the one
`prereg freeze` records (in both scratch copies, `3b56787175c1a2391ff54f55180e107c331a51f511b53985820f4b392393f241`
for the text above the log as it stands).

### Checks

| file | what | sha256 |
|---|---|---|
| `docs/stage0_build/DRESS_REHEARSAL_2026-10-02.md` | the rehearsal: commands, outcomes, findings, what was not rehearsed | `fa2f7f651c19ab5cc9cbf9b8548e29e636047e9e183d9f2f2e518664b0d332b9` |
| `docs/stage0_build/dress_rehearsal_outcomes_2026-10-02.json` | the same outcomes as data | `14a3ec7806661bdfe0e795539716cd96387fcd8ff100e0171032dd15e4c7ef89` |
| `docs/stage0_build/FEATURE_REQUEST_plan_hash_and_coverage.md` | what the rehearsal found in `prereg`, `results` and `repro`, for their maintainers | `29be336a7a7797d0e5947ea5c99211ebb40f0e0340781c62de4e0721cb4f0a90` |
| `docs/stage0_build/mutation_check_dress_rehearsal.json` | 12 deliberate removals of the new guards each made a test fail (driver: `mutation_check_dress_rehearsal.py`) | `92de3830a075a638aff8e83d875d0b7d7ad8fc0ea1990c3c4fd8a5f10e8c32ac` |
| `outputs/tests/pytest_all_modal_20261002T192344Z.txt` | whole suite on Modal after the fixes: 593 pass | `bb583cbdc5b345e505d0cab100c39a0433864d80a9bb9be54dff7805c5a05f01` |
| `outputs/dry_run/20261002T192352Z/h1_h2_tables.json` | synthetic dry run | `f480c6063272e10bfca73f9cd24f1c4594d659321d0a6620a11a0f4276c3fd85` |
| `outputs/dry_run_biology/20261002T192344Z/sensitivity_tables.json` | synthetic biology dry run; same sha256 as the three-gates run | `b57acb71ef23a26bc8230b8c52359adeecbcd8b434cda8c0166bd3295cdb7831` |
| `outputs/dry_run_drug/20261002T192344Z/drug_tables.json` | synthetic drug dry run | `61c745d0e4e5b2dac0bec06b70f42389594c12c986f080e5ce71ec6c316ab4e7` |

`prereg check`: not frozen. `results verify --files` and `uv run scripts/stage_record.py
verify`: unchanged from the three-gates pass. `citations verify --claims claims/`: 5,470 found,
0 not found.

## PREREG v17: pre-mortem applied (pre-freeze, 2026-10-02)

Nothing was searched, extracted, joined, committed or frozen. No in-window record was read.

**Why.** A pre-mortem of v16 (`planning/premortem/PREMORTEM_2026-10-02.md`) found that H2's
"supported" verdict has a ceiling set by how often abstracts name a release, that the verdict
was on identical release sets while the paper will speak of the same or overlapping data, and
that sentences the paper will write had no registered quantity.

**What changed in the plan.** H2 is unchanged. H2b carries a second verdict, by the same rule,
on identical or overlapping participant sources; the resolvable share is the ceiling of H2's
lower bound; twenty secondary outcomes are registered as estimates with intervals and no
verdict; the hub and alignment expectations, the reference-screen split and the pathway naming
rule are registered; four sensitivity analyses were added and one became H2b; the record
metadata (OpenAlex reference lists, journal, query sources, the first author's country) is
collected at stage 5, country with no planned analysis; the planned paper title no longer says
"preregistered". Item by item: `planning/premortem/ADJUDICATION_premortem_v17.md`.

**Not done as asked.** No external study list is pinned: the supplement of Wu et al. 2024
answered HTTP 403 to a plain client and the DMRdb file address answered with a notice that its
files are moving. The check is registered to run only on a list pinned before the freeze.

### Files added or changed

| file | what | sha256 |
|---|---|---|
| `scripts/build_registry.py` | H2b (`pair_overlap`), the resolvable share, H2b and the resolvable share read on H2's bootstrap replicates, the 1.25th/98.75th percentiles, `two_verdict_reading`, `h2_supported_attainable`, the protein-cluster bootstrap; H1 and H2 estimates and their bootstrap unchanged | `59cd3fefde53e72306251bb60a8e10dbd6ec6cd27f5d46e47b105c483670968c` |
| `scripts/registry_secondaries.py` | new: the 20 registered secondary outcomes and `RecordMeta` | `efaedf3e68ee2ccffbffb45e49bc7ee7cb5892bfbb6b87f4f8e3688e28be07ff` |
| `scripts/registry_indices.py` | the participant-overlap row reads the H2b table of `build_registry.py` | `0614bb1800961b13237f11fa32cb649450f6db06cf063ef53a58a710991f2c8b` |
| `scripts/sensitivity_analyses.py` | `claim_specific_dataset_names_only`, `tested_count_1000_or_more`; `h2_on_participant_overlap` removed (it is H2b) | `c32e1c4ed60e23f046528b31b355b102412f90938b21e55d8d9292b6847af1fc` |
| `scripts/hub_proteins.py` | `hub_expectation` (1,000 permutations, generator `[20261001, 2]`) | `c68ea95c94cb0f1f51d951109a2c145222d6531acf36bcc4a3faa017a01f5ea6` |
| `scripts/drug_joins.py` | `alignment_expectation`, written as `alignment_expected_from_margins` under every rule | `fb840d39bb8f3b0073344f7d6db85e35843a715ac1af39210c16625c8aa05acd` |
| `scripts/reference_screen.py` | claim records split by `shared_pqtl_source` / `other_pqtl_source` / `pqtl_not_stated_or_unmatched` | `0c9450926b7ef3cb908efd695d349548433efe03780317a7a3387087d25de458` |
| `scripts/pathway_enrichment.py` | `named_in_text` on every pathway row (q below 0.05 and at least 3 claimed proteins) | `1f000d4361e2561d4d84e6dc69e15e2d19114d450fa1b5da200d0253c49f6806` |
| `scripts/fulltext_concordance.py` | `h2b_within_extracted_subset` beside the H2 classes | `db1666da07e7a333812d0d46ed2072a264bc540afcf4501f9edc05a667303fb4` |
| `scripts/biology_joins.py` | step `registry_secondaries`; hub expectation in the hub step | `58936613fb84bc49e728bc8f65ed7fdbfe57af127e09ee4e880133189237235d` |
| `scripts/assemble_screening_set.py` | `journal` on retrieved and screening records; nothing else changed | `5695fc615b64a9f0c40c2a5978f430941134b98ca9b48ba290dca9339c38e8bb` |
| `scripts/record_metadata.py` | new: OpenAlex look-up of the eligible families' records (`fetch`, refused before the freeze), the record metadata table (`build`), the requested country tabulation (`country`) | `706c826d1c34fb0c025d0962bde01f00ad745a7f87e2742fa629c24b35c64732` |
| `scripts/external_lists.py` | new: identifiers of a published study list and the share the queries returned | `ad8179b3d99bdd7dfb56e31294093ca78c3c85aeb1094b08ab6f6ed031798f23` |
| `scripts/modal_external_lists.py` | new: Modal wrapper that reads the header and the identifier and year columns of a list file on the volume | `a9ba80e0aa1c779639f2c17e17dd1149cc7a61fed9fa38a128dc6ebdbc36d4c6` |
| `scripts/dry_run_synthetic.py` | expected H2b classes, resolvable pairs and the two verdicts | `f4f224308a945a9c2f361a5c51b821e0f35524afdfb9c8203a667a9b5a833260` |
| `scripts/dry_run_biology_synthetic.py` | synthetic record metadata; hand-worked values of every secondary (`SECONDARY`), of the two new sensitivities, of the hub expectation and of the reference-screen split | `8df5b6fff1e11c9dc576c560c1bed865be31010b2099e269877ea1d31434889a` |
| `scripts/dry_run_drug_synthetic.py` | hand-worked alignment expectation under every rule | `cc62cd5e03d2d328c9e8d5f8e945a71366a3e8ff782cd75f00ae14ba4e0c36c4` |
| `tests/test_registry_secondaries.py` | new: 26 cases | `32ae1cc2c25f55294b5790b346b5dc3d57bd38c76ab1cab64cfd9c27cd8a8a0a` |
| `tests/test_secondary_joins.py` | new: 11 cases (hub expectation, alignment expectation, naming rule, reference split, the two sensitivities, journal) | `98eee005b5cc4db17aa9616c0552fdefc3554e08b3c591c0693285b3e2145917` |
| `tests/test_record_metadata.py` | new: 12 cases (look-up, record metadata, country, external lists) | `07d4c689ecc607e2ba236f05f5cc16f7c8c6e378dd38587fd71439fc197048ee` |
| `tests/test_registry.py` | 9 cases added (H2b, nesting on random registries, readings, Bonferroni level, protein-cluster bootstrap) | `e67ce7c2116724367d4fbbad94e9fcb401b81dc7735d31cec2ea33ae855040f8` |
| `tests/test_fulltext_concordance.py` | H2b classes in the full-text subset | `8154ccfc468bda3ac1eecab721462de728ead7e706ab07083a198e126eb613fc` |
| `verification/pqtl_row_attributes.csv` | new: assay family and Zheng 2020 source flag of the 28 pQTL dictionary rows | `66d71cf132b80d91bf6be4bd03db9c8b57789c5eae042213a4e7729cf5531d0b` |
| `verification/external_study_lists.csv` | new: header row only; no list is pinned | `dbe9b9a486c87b0e7ae8dcb042eec8ead7c45a016aaf89311aa0775a4560194f` |
| `verification/external_study_list_ids.csv` | new: header row only | `e374a38e2f4edf6d640e02bec89e19664ee3f34a3424864ad16a07edccdadca6` |
| `OPEN_QUESTIONS.md` | items 90 to 100 | `3b331822a4ab2a03726cd56a056320af091ec714da6e76c15fe95f9a2f569a30` |
| `docs/stage0_build/RUNBOOK_additions_v17.md` | run order of the record-metadata step, the new result files and the external-list check, to merge into RUNBOOK.md | `02c909aa481d92fe17f0cd4a3bb4adefb9d4870683ef4695d979af031a4b222c` |
| `docs/stage0_build/mutation_check_v17.py` | driver of the mutation check | `77afec16a35d77456493e6b6ea3b5b5202cdb33aed3149ede0b83783e6672852` |

| file | what | sha256 |
|---|---|---|
| `PREREG.md` | v17 with the log to the fourth line of this pass | `c17170b19c3e78b106dc2c27aa2c7c4ff50c3cbb5798cd05e2eea4b9857d8250` |

The text above the log has sha256 `97acf76616338fac39fab9e73cfc712f6dee3bbd51779a98e91fbcc9f0fb57a2` as this file
computes it (the bytes before the `---` line that precedes the log); `prereg freeze` records
its own hash of the registered text. The copy at this point is
`planning/perplexity_paper1_final/PREREG_paper1_v17.md`; the copy before this pass is
`PREREG_paper1_v16b_before_premortem.md`, and the difference `PREREG_v16b_to_v17.diff`.

### Checks

| file | what | sha256 |
|---|---|---|
| `outputs/tests/pytest_all_modal_20261002T195518Z.txt` | whole suite on Modal on the v17 text before three wording edits: 651 pass | `7d6bc62245b28d273dc61bca7097eda79cb7fbcfd08351bece701af35b9c5826` |
| `outputs/tests/stage0_file_sha256_2026-10-02_v17.txt` | sha256 of every script, test, fixture, prompt and search file (124 files); against the dress-rehearsal listing, 5 added and 15 changed, each named above | `affb8c6c60224712c5e61ab33ed1aa71d4b6be9f847db0685b1fe31258f7b97a` |
| `outputs/dry_run/20261002T195526Z/h1_h2_tables.json` | synthetic dry run, with the H2b table and the two verdicts | `b0c626a68865e87356927a380f96aa41f46a6d137b6a6e3ac1bdf8364ee85cb0` |
| `outputs/dry_run_biology/20261002T195518Z/joins/registry_secondaries.json` | the 20 secondaries on the synthetic registry | `f387d432bfdd8d00406d3aecd7a5b84a0fc49c69a5a779a8b235ce18d0e5c7ec` |
| `outputs/dry_run_biology/20261002T195518Z/sensitivity_tables.json` | synthetic sensitivity tables | `7ce2092a0ebb47fae5643ec60fa651ddaa829fb650374d014c538cc1472a0f3b` |
| `outputs/dry_run_drug/20261002T195518Z/drug_tables.json` | synthetic drug dry run | `e2ce155593ba484a6e194169ceee01b34d66ebbd8fc2b7fb328f14335a1189e8` |
| `outputs/tests/pytest_all_modal_20261002T195810Z.txt` | whole suite on Modal on the v17 text before the reserved-words wording: 651 pass | `f8107a48dd13d9e2016dfdb8a432b03d92ba4e762151d0f26669d0e81d2375db` |
| `outputs/dry_run/20261002T195818Z/h1_h2_tables.json` | synthetic dry run on the final text | `05e470a53781c1139e1929d5f05ebe07cc7298f14c5eff6fd9029bd7a270b7af` |
| `outputs/dry_run_biology/20261002T195810Z/joins/registry_secondaries.json` | the 20 secondaries on the synthetic registry, final text | `ffb189fe7cb7ff08d9385aa1880c33da3744873cd1b7bf546e7c848b31f46747` |
| `outputs/dry_run_biology/20261002T195810Z/sensitivity_tables.json` | synthetic sensitivity tables, final text | `7ce2092a0ebb47fae5643ec60fa651ddaa829fb650374d014c538cc1472a0f3b` |
| `outputs/dry_run_drug/20261002T195810Z/drug_tables.json` | synthetic drug dry run, final text | `4cccbc20f039ac019270f9a1d64ba05fa8a4288bd368aa7e3d0ac5bb0fb3df30` |
| `outputs/tests/pytest_all_modal_20261002T200046Z.txt` | whole suite on Modal after the last wording edit (reserved words): 651 pass, and the three dry runs pass | `7ed8ed4cf01f5bdb51a98efcb63c1eb27e01c77e508f82fe9aeb77626a73f2e1` |
| `docs/stage0_build/mutation_check_v17.json` | 52 deliberate changes of the new rules, 52 made a test or a dry run fail | `c9a072ef5c371ffa732e10e55e70b123a580436fbd1ae74903329b37536d3df5` |
| `docs/stage0_build/osf_dry_run_result_2026-10-02_v17_final_text.txt` | OSF dry run on the final v17 text: accepted; nothing sent | `3a71d1a1fa090fc3474bb194549a9fa75f4ca5ca64eabc95958b1cc25ea97a04` |
| `docs/stage0_build/osf_dry_run_result_2026-10-02_v17.txt` | OSF dry run on the v17 text before three wording edits: accepted; nothing sent | `3a71d1a1fa090fc3474bb194549a9fa75f4ca5ca64eabc95958b1cc25ea97a04` |

`prereg check`: not frozen. `results verify --files`: all checks passed (1 run, 3 recorded
files), and `uv run scripts/stage_record.py verify`: ok; no stage was run or recorded in this
pass. `citations verify --claims claims/`: 5,470 found, 0 not found; warnings unchanged (1,775
short, 44 truncated, 14 normalized). No quotation was added: the pass quotes no source.

## Live smoke run on records first public before 2019 (pre-freeze, 2026-10-02)
One pass of stages 1 to 6 from the command line on one live set, label
`smoke_pre2019_20261002` (`docs/stage0_build/LIVE_SMOKE_2026-10-02.md`). Registered queries on
2018-06-01 to 2018-06-30, one smoke citation-chasing round, 33 GPT-6.1 Sol requests, all on
records first public before 2019. Both eligible families have the window `outside`, so no
registry claim, pair or table of a registered window exists. One record of the registered
window (PMID 30239796, dated 2018 by OpenAlex and 2019-01-10 by PubMed) came back in the chase
responses; its abstract is in the stored responses and in the archived first output of the
round (`outputs/superseded/smoke_pre2019_20261002/`), was not read, is in no smoke screening
set and went to no model. No rule of PREREG.md changed; nothing above its log changed.

Outputs of the run, each folder named in a ledger manifest below: `outputs/raw/search_smoke/`,
`outputs/screening_smoke/`, `outputs/raw/citation_chase_smoke/`, `outputs/raw/sol_` and
`outputs/raw/sol_..._repeat` with the label, the `outputs/parsed/` files with the label,
`outputs/repeat_run/`, `outputs/citations/`, `outputs/verification/`, `outputs/registry/`,
`outputs/manual_coding/`, `outputs/raw/openalex_metadata/`, `outputs/funnel/`,
`outputs/stage5_biology/`, `outputs/stage5_drug/` and `outputs/fulltext/` with the label. On the
volume: `/02_claims_meta/raw/citation_chase_smoke/smoke_pre2019_20261002/`, two folders under
`/02_claims_meta/stage4/` and `/02_claims_meta/stage5/smoke_pre2019_20261002/`.

### Files changed

| file | change | sha256 |
|---|---|---|
| `scripts/run_search.py` | smoke window options `--smoke-start`, `--smoke-end` (2014-01-01 to 2018-12-31) and `--smoke-label`; a resume with another smoke window raises; the registered path is unchanged | `a3ef0bcdb9ab31b303631751e3089b6fba2dae49e3e2a1cef7b75067e32684e3` |
| `scripts/citation_chase.py` | smoke mode only: the OpenAlex date limit is on cited works as well as citing works, records first public after 2018 are left out of the smoke screening set and counted, `--smoke-label`; the registered filters are unchanged | `ef9feb749bc7aa5bf810581118b613151b824a7f71819722435d80b306d9e60d` |
| `scripts/record_metadata.py` | `fetch --smoke`: runs before the freeze and refuses a record first public in 2019 or later | `e952f00d3f9edf6c8158a2449681cf89fc68a69039fd241a0cba6f1da1d0e021` |
| `scripts/fetch_fulltext.py` | `--census --before 2019-01-01` runs before the freeze and refuses a later record ahead of any request; a stored full-text XML with other bytes is not overwritten | `9f1ce89ffa868dc46d385a54db11f17687850aeb614124197c422bd8b5569b89` |
| `scripts/verify_spans.py` | the artifact digest is compared when the input record carries one (screening-set abstracts carry none; the script raised `KeyError` on them); the claims-file URL follows the record id | `f6a3a41984e6cba578f4e34d23ddfb623940e073a1dd27ef9bb53bf544c9f248` |
| `scripts/claim_tags.py` | `--extraction` takes the extraction files of the search and of each round in one call; a record id in two files raises | `c8f1064b38f212988f111e276c4a6aad6bba17ac1d5c518f1c3270ed543215fa` |
| `scripts/modal_biology_joins.py` | `joins --abstracts` takes the screening sets comma-separated | `9e3b83da49f30d1ee20ed90aa4916d1a72e6844d072e7e47a317ba041f7bca9a` |
| `tests/test_search_run.py` | 5 cases added (smoke window bounds, default, both dates, window sent, resume with another window) | `7c790b0f41bd8deaf278bbb2bb6e0eb985fd373cda740976e1bf7e45ae1c1b6a` |
| `tests/test_citation_chase.py` | smoke limit on both directions; smoke screening set keeps no record first public after 2018 | `bf8ef102f3df365ee7e64c71a77fcb5158138f83965076a27b2615ad81443efc` |
| `tests/test_record_metadata.py` | 1 case added (smoke fetch refuses a window record) | `be6be80e04555858f045da692d1138915f3aa80ad6c770c31f83363ee8a97903` |
| `tests/test_fetch_fulltext.py` | 2 cases added (census before a date; refetch with other bytes) | `1d6e6c22675d00f0f8e8034c213270f91fa18f7f9319e008afffda38857db781` |
| `tests/test_claim_tags.py` | 1 case added (several extraction files) | `e9e7b29697d2736cc7ff346196d14d723cfce6064f51d5c78b774436889b2cb6` |
| `tests/test_verify_spans.py` | new: 6 cases (recorded digest, landing page by record id, the registered quote check) | `e727dd6a939b0841e2b5a424f55a9e5c57e0a0ac034f792b626fe1b46b2fa827` |
| `RUNBOOK.md` | the v17 additions merged; `claim_tags.py` and the joins with several files; the copy of `claim_tags.jsonl`; stage 6 written out with the census; a section for the smoke run before the freeze | `250a5d43dc6014eb3041d5a2f71731179215b7cb62c0a1794f30187bc7429845` |
| `docs/stage0_build/LIVE_SMOKE_2026-10-02.md` | new: the live smoke run: commands, counts per stage, what broke and the fix, what was not exercised | `bb16e68a23921468e1f936c805acde421bcf5a842bfc601716437fde944309e6` |
| `docs/stage0_build/live_smoke_counts_2026-10-02.json` | new: the counts of the run, per stage | `98378cf194ef36efecc5146e15629f26c264313acf6f6b1df7242791832a9e59` |
| `docs/stage0_build/mutation_check_live_smoke.py` | new: driver of the mutation check | `c8281b6d64adba469e7fb53fc0b52f161ae7b88383ed78f66751932b9c10b98b` |

| file | what | sha256 |
|---|---|---|
| `PREREG.md` | v17 with one further log line (this run); nothing above the log changed | `e552015e0ad9e3e2cc4e734f0bcd0fa61c94a3dca72b987e02dce2585cad249b` |

### Checks

| file | what | sha256 |
|---|---|---|
| `outputs/tests/pytest_all_modal_20261002T202200Z.txt` | whole suite on Modal after the fixes: 667 pass, and the three synthetic dry runs pass | `322803bb6988baadc01e2eb981f79237008ecca36d4a82b5a8203aa52f283a71` |
| `outputs/tests/stage0_file_sha256_2026-10-02_live_smoke.txt` | sha256 of every script, test, fixture, prompt and search file (125 files); against the v17 listing, 1 added and 12 changed, each named above | `1b927d087eae5e431fe6f1b56f216d7b1d06185ea1e23743022c6a86f4e3bd69` |
| `docs/stage0_build/mutation_check_live_smoke.json` | 16 deliberate changes of the new guards, 16 made a test fail | `1c845d56999ef8ffa5853f34248dcd9eb6c43dc2d568c4c7d7dbd8fb96be4e14` |
| `outputs/results_manifests/smoke_pre2019_20261002_s1_search.json` | ledger manifest: search responses, screening set, prefilter | `9627324099292ad1a4756447dd3ec7f388724230c50ac44a4a8fee95482c96d4` |
| `outputs/results_manifests/smoke_pre2019_20261002_s2_eligibility_2811496ef424.json` | ledger manifest: eligibility exchanges and decisions | `6c0fa3926feea690bd6a8c268e9681bffaefd8f07c79762f9b61dc606f59c840` |
| `outputs/results_manifests/smoke_pre2019_20261002_s1b_chase_1.json` | ledger manifest: chase round 1 (response bodies equal to the volume copies) | `2a51ebb0cb6b9dd09680dd815c781ebe065318d4998874ab5d84ccb642d0a2fd` |
| `outputs/results_manifests/smoke_pre2019_20261002_s3_extraction_0b97103cd7a4.json` | ledger manifest: extraction, repeat run, agreement | `bb1c942e02c1a52b080a9bc50522885730825baf30f66dcc0ef7344428252e29` |
| `outputs/results_manifests/smoke_pre2019_20261002_s4_registry.json` | ledger manifest: span and claim checks (equal to the volume copies), registry, manual-coding queue, record metadata, funnel of the search | `e9b4dacf627b71fc61e0cef060ca86ba8fdb7cff7f282ed6f0f9cecf33cbeb52` |
| `outputs/results_manifests/smoke_pre2019_20261002_s5_biology.json` | ledger manifest: stage 5 biology joins and sensitivity tables (equal to the volume copies) | `0af671b084f06b5906f8888e2836ced0328ac9d5b2f6769dc9ced0c5ad56e686` |
| `outputs/results_manifests/smoke_pre2019_20261002_s5_drug.json` | ledger manifest: stage 5 drug joins (equal to the volume copies) | `289cc97c1ec4717ad255d5dfd6deaf034cf26bc539d293cc459190f310ad1e6e` |
| `outputs/results_manifests/smoke_pre2019_20261002_s6_fulltext.json` | ledger manifest: full-text census | `419dc1e98f5d70e02ab0468193737e64d9e045894dec575a09a9e2061bc86945` |
| `.results/ledger.jsonl` | the ledger after the eight smoke runs (10 events) | `31ff7d0e910b49003faacddd01aa5015cff8ac8c7a6765b41ad8739c8d7e541a` |

`prereg check`: not frozen. `results verify --files`: all checks passed, and
`uv run scripts/stage_record.py verify`: ok for the eight smoke runs. No quotation of a source
was added.

## Live smoke run, second pass: gate audit and stages 4b to 6 with content (pre-freeze, 2026-10-02)

The gate audit of chase round 1 (approved by the author) and stages 4b to 6 on live content,
same label and screening sets (`docs/stage0_build/LIVE_SMOKE_2026-10-02.md`, last section). 89
further GPT-6.1 Sol requests (86 eligibility, 3 extraction), all on records first public before
2019; 122 in the two passes. A smoke-only switch (`assemble_registry.py --smoke-label`,
`scripts/smoke_guard.py`) treats families first public before 2019 as inside the window, so the
registry (5 families, 3 claims), the manual-coding queue (1 row, none coded), the record
metadata, the funnel, the biology joins, the sensitivity tables, the drug joins and the
full-text census ran with content, the Modal steps against the pinned files. No record first
public in 2019 or later was fetched, read or sent to a model. No registered rule changed;
PREREG.md gained foreknowledge item 17 (v17a) and one log line.

Outputs, each named in a ledger manifest below: the `outputs/parsed/` files with
`_gate1b1_` and `_chase1gate_`, `outputs/citations/` and `outputs/verification/` for
`sol_extraction_smoke_pre2019_20261002_chase1gate_0b97103cd7a4`, and `outputs/registry/`,
`outputs/manual_coding/`, `outputs/raw/openalex_metadata/`, `outputs/funnel/`,
`outputs/stage5_biology/`, `outputs/stage5_drug/` and `outputs/fulltext/` with
`smoke_pre2019_20261002_window`. On the volume: one further folder under `/02_claims_meta/stage4/`
and `/02_claims_meta/stage5/smoke_pre2019_20261002_window/`.

### Files added or changed

| file | change | sha256 |
|---|---|---|
| `scripts/smoke_guard.py` | new: the guards of the smoke window (label, registry folder, result names); standard library only | `91e0511db60bdb691270b245ea476e242dc482d3b9fe9bb02e4bf96376025182` |
| `scripts/assemble_registry.py` | `--smoke-label` and `smoke_window`: pre-2019 families take the window `confirmatory`; refuses a 2019-or-later record, a non-smoke label and a folder outside `outputs/registry/<label>...`; `registry_assembly.json` carries the label | `b0eee246dafd55e02c9e268ec98d76f03fdc599ce229b5559c2c7b4b5ac520a7` |
| `scripts/sensitivity_analyses.py` | `smoke_window` passed to every assembly; `--smoke-label` | `a6c51956c7ec79a27d8729314589ae53bbecf4b32884199401b26525fca187f9` |
| `scripts/modal_biology_joins.py` | `joins` refuses a smoke registry under another run name; `sensitivity --smoke-label` | `396297834adeb1356e78552db0c8b088b396bcede0ffaab5e402be8553a19b8d` |
| `scripts/modal_drug_joins.py` | `joins` refuses a smoke registry under another run name | `fd7b8733d3f665472ca08449209fb38d53c96987130de782cf2b435f6c9d3430` |
| `scripts/funnel.py` | refuses a smoke registry's funnel under another folder name | `420324bc5a84b2dae258188685eb8fa165c111d2775bbbb60e0d14d5c4ed95bd` |
| `scripts/manual_dataset_coding.py` | `queue` refuses a smoke registry's queue under another folder name | `0f87dc25da92ece3ced67a8f28392a05fb0cf7765224b665a9817c7039c44f0a` |
| `scripts/fetch_fulltext.py` | the census refuses a smoke registry's output under another folder name | `575f969745997c5a3ee870252772ef20bdfe75c618ab05a1a46d1ba8d5849341` |
| `scripts/stage_record.py` | `replace`: documented replacement of a recorded file; `verify` accepts it only with exactly the replaced bytes | `1f70f435107b1d61589e270832c8cc7d9fad3c9ea5c6296d0566c5efd38d2c73` |
| `scripts/verify_spans.py` | the stored output of `citations verify` names paths relative to the experiment folder | `6cf52a34a7054c551cf8a416b4473df94ae32a543e7ef1bb5a9208071c5fa2f7` |
| `tests/test_smoke_window.py` | new: 21 cases (the switch, the label, the folder, the result names, the later steps run as commands, the sensitivity tables) | `d55b42cf1c2d0e2c276303fe13086d7d62758af24f52ae2c44a78ff0c0989938` |
| `tests/test_stage_record.py` | 4 cases added (replacement accepted only with the replaced bytes; a row covers its own run, path and hash; refusals; the table is no manifest) | `1fb36e599ebebc59850be44df74bf3418b362d0313359bf6c04c0766d2ec2080` |
| `tests/test_verify_spans.py` | 1 case added (relative paths in the stored output) | `91f26acba744f8febcdedf02cd7bd67729af58e96e6d22e8c89cc1ca869d9379` |
| `RUNBOOK.md` | the smoke section rewritten for the switch, the gate audit and the uncoded queue; the replacement procedure under §Results ledger | `4e95b279cdf60972fbb33fd8f0e52a6b2b000469ec90f64acaaa9c9c8b473191` |
| `docs/stage0_build/LIVE_SMOKE_2026-10-02.md` | second-pass section added: gate audit, stages 4b to 6 with content, what was added, what was seen | `accd498583fafd8577fb611b9186a7c49d8694a02322ab614317c6e8c9daf3b2` |
| `docs/stage0_build/live_smoke_second_pass_counts_2026-10-02.json` | new: the counts of the second pass | `3c20ca38cfbf209089afde9a9a0c57275e6e807f22088049d6751ce41752dc02` |
| `docs/stage0_build/HOME_PATHS_STRIPPED_2026-10-02.json` | new: the 16 stored outputs from which the absolute repository path was removed, each with its sha256 before and after | `a6ebd3fdb2c494dcef2506768c7c5a911d48600513b14b0c73b4ad07429ae0aa` |
| `docs/stage0_build/mutation_check_smoke_window.py` | new: driver of the mutation check | `9c93b51045cbfab66c5d53779d3a12457e156cbdb5ee5c11054e2bd4ec94c654` |
| `docs/stage0_build/osf_dry_run_result_2026-10-02_v17a.txt` | new: OSF dry run on the v17a text, accepted | `b2b7138dcba816fcf1a07aeaa6ab170fd5af67bf24f0124809cb9857c623d583` |
| `.gitignore` (repository root) | the local archive of the stripped originals is ignored | `3db2a836e486646b18a6b7d0b89b04592ffb4a46e939ef1cc6a584e813a31c74` |

| `OPEN_QUESTIONS.md` | items 101 (a record with no abstract has no rule) and 102 (the smoke run; the one stored window abstract) added; item 93 marked done | `97bc0946fa7712372337c73e8df6d1d1357e5b823c2b27c4a94ef69f4f69a99a` |
| file | what | sha256 |
|---|---|---|
| `PREREG.md` | v17a: foreknowledge item 17 (the live smoke run) and one further log line; the copy before the item is `planning/perplexity_paper1_final/PREREG_paper1_v17_before_smoke_item.md` | `7ef2fc520a90229a65c433d49edcccf5c0ea1f4a876cdf8ccf7bfdde23386ac4` |

### Stored outputs with the repository path removed

Sixteen stored tool outputs named the repository's absolute path on the author's machine. The
path was removed and no other byte changed (`docs/stage0_build/HOME_PATHS_STRIPPED_2026-10-02.json`
lists each file with both hashes). The rows below replace the hashes recorded above for the
files this document names; the earlier rows stand as history.

| file | sha256 before | sha256 now |
|---|---|---|
| `outputs/resource_counts/dataset_pairings_after_compositions_2026-09-30.json` | `c0c620c0a6c1d1aca59d34fe26f7ba45781a4af14c93d48c4aa0250aeb579664` | `8ba1165349aa36e96d69780fe5e4ffa348d16519387fb9b9b35708f7a9b96d09` |
| `outputs/resource_counts/dataset_pairings_round5_after_iceland_split.json` | `cdd7aad940fad6e4fe46d7b5af36c0b5643d4c870a6d8efe9b0510873dc9b6f0` | `e1c48d32fe2892ffb06e23f1840b3b0197093e31c265438a53c49ac60924e242` |
| `outputs/resource_counts/dataset_pairings_round5_after_name_mapping_fix.json` | `352fe933690f5edc79fc55a3ccf146299c071dcde7829c2e42d5b6ec9b5b3df7` | `4e72856d5b5aeb55368beba987cf17e19dfad56c5aeef7feaf44c0ef4bd88c45` |
| `outputs/resource_counts/dataset_pairings_round5_before_iceland_split.json` | `00720f3f1afb986575f11de4448eb6d0469c2cc965a8ad5f3a3a11fb34ad1412` | `6fa4b738faaabd1858ee655e808aacd7cbc5c9da9f5add8c306021cfe71928d0` |
| `outputs/resource_counts/dataset_pairings_round5_before_name_mapping_fix.json` | `21d54e13538818f30663e4ea602bf77c69513f2331836ae969e44cf6cf6935b9` | `63278ddd13fa6447642f3b2ad57eb68389e35a493357809a9e1aa28d35b60385` |
| `outputs/tests/pytest_round5_fixes_2026-10-01.txt` | `ffd37d0eb9ca7ee0326c2fb7daa82b007e82e02783ea4f4834862caf9c05a57b` | `083db13ca46863f39d4809890d333017ba30e37521a9e677eb2586a852caa314` |

### Checks

| file | what | sha256 |
|---|---|---|
| `outputs/tests/pytest_all_modal_20261002T204747Z.txt` | whole suite on Modal on the v17a text and the final code: 693 pass, and the three synthetic dry runs pass | `135e260a119c307d52bd5ef8cd6a2be4c8777955b5f8fe65b245d70be65eafff` |
| `outputs/tests/stage0_file_sha256_2026-10-02_smoke_second_pass.txt` | sha256 of every script, test, fixture, prompt and search file (127 files); against the live-smoke listing, 2 added and 11 changed, each named above | `8e3e2ff6facbbca027ab19507e679f64c2ccbef464812e78d54aba593d2f59af` |
| `docs/stage0_build/mutation_check_smoke_window.json` | 35 deliberate changes of the new guards, 35 made a test fail | `20a576ba884ab56112e433314dd98686bed78e758820df18ef29a67df22cd928` |
| `outputs/results_manifests/smoke_pre2019_20261002_s1b_gate_audit_1.json` | ledger manifest: gate audit of chase round 1 (86 eligibility exchanges, decisions, audit, round selection) | `4d6a877ca30dc1596ed4c4954dcc8d50c5ec3fe23595828898af0460a2f8739d` |
| `outputs/results_manifests/smoke_pre2019_20261002_s3_extraction_chase1gate_0b97103cd7a4.json` | ledger manifest: extraction of the round's four eligible or uncertain records | `50c4a688ebdf449aaa6613f3c271cc86772f2829dcf973588350e22326e9a0cf` |
| `outputs/results_manifests/smoke_pre2019_20261002_window_s4_registry.json` | ledger manifest: span and claim checks (equal to the volume copies when recorded), smoke-window registry, manual-coding queue, record metadata, funnel | `677c93e104167c6972734f6edc04177d494fc42542d3b7f0a0b42bea82b668bd` |
| `outputs/results_manifests/smoke_pre2019_20261002_window_s5_biology.json` | ledger manifest: stage 5 biology joins and sensitivity tables on 3 claims (equal to the volume copies) | `ec6872c60d5c54d99227987c35e2f3a56990af6fd87b6f60ca7eebe8c45bfc05` |
| `outputs/results_manifests/smoke_pre2019_20261002_window_s5_drug.json` | ledger manifest: stage 5 drug joins on 3 claims (equal to the volume copies) | `9145084409c59670ee0214dc316dc8bc0fe6351e809455f921ba12cb047bf78b` |
| `outputs/results_manifests/smoke_pre2019_20261002_window_s6_fulltext.json` | ledger manifest: full-text census of the 5 families | `b481f0f74363ef873a02391e327bf04a146199ab4ded157aff867a1cb7ed6554` |
| `outputs/results_manifests/replaced_files.json` | the 3 documented replacements (stored `citations verify` outputs with the repository path removed) | `8431ebe8cf5a5a039eb6827a01a5dd4697237d284511ba47b110b1e9909c13d5` |
| `.results/ledger.jsonl` | the ledger after the six further smoke runs (16 events) | `ac895c2cf5fe945ef8fcc6e9c7b18109381a62fd340868baf3b70ae128963eb1` |

`prereg check`: not frozen. `results verify --files`: all checks passed.
`uv run scripts/stage_record.py verify`: ok for the fourteen smoke runs and the wiring check,
with 3 documented replacements. `citations verify --claims claims/`: 5,470 found, 0 not found.
OSF dry run on the v17a text: accepted (`docs/stage0_build/osf_dry_run_result_2026-10-02_v17a.txt`).
No quotation of a source was added.

## The `no_abstract` rule and PREREG v17b (pre-freeze, 2026-10-02)

A record for which no source holds an abstract of at least 200 characters is classed
`no_abstract` before the keyword prefilter and is not sent to GPT-6.1 Sol (OPEN_QUESTIONS 101;
`docs/stage0_build/NO_ABSTRACT_FLOOR_2026-10-02.md`). The floor rests on the abstract lengths of
the 313 records first public before 2019 that are held; of the 24 known-item abstracts only the
lengths were computed. No in-window abstract was read and no request to GPT-6.1 Sol was made.

### Files added or changed

| file | what | sha256 |
|---|---|---|
| `PREREG.md` | v17b: the `no_abstract` rule in §Data collection procedures (paragraph and table), with its sentences in Study design, the chase and gate audit, the negative controls, the prefilter, Sample size, the funnel, the units table, the consistency checks and the Maximum claim; foreknowledge item 18, the six 2019-dated stored records in item 14, and the sentence after the list restated; four log lines. The copy before this is `planning/perplexity_paper1_final/PREREG_paper1_v17a.md` | `31cad25c572352046a96e7df74fe04e04fc827b86cd16779cb76461698035a8b` |
| `OPEN_QUESTIONS.md` | item 101 registered as a rule; items 103 (six stored records dated 2019 by PubMed) and 104 (one ledger file recorded with two hashes) added | `31c947d3c42f1ac6690443aa81c6b6c7cb5e3f7feb56133199cb4c0b7ad6437f` |
| `RUNBOOK.md` | the `no_abstract` rule at stage 1; the negative-control command takes `--no-abstract`; the rerun of the smoke round noted | `3b3850209ac43da579603a8b47a76df4f2560309d1ea61777135199dbeebc35e` |
| `scripts/abstract_floor.py` | new: the floor (200 characters after whitespace is collapsed), `is_no_abstract`, `refuse_no_abstract` | `d1431cc8d5d0a09043888de27ff16ca3a74f782d0c934552a3e0d9ca46fee555` |
| `scripts/assemble_screening_set.py` | abstract = the first in source order that reaches the floor; `no_abstract` on every screening record; `no_abstract.jsonl`; `screening_set.jsonl` holds the records with an abstract; counts in `funnel.json`; one writer for the search and a chase round | `60fe24664912ab1f2f750b055088070770764aacb40c526561c65bc6aae23d74` |
| `scripts/link_families.py` | `SearchRecord.no_abstract` | `47cd0e6c8bb08be87ff3762026f28656e15d6f91f634b71cee3538887a666426` |
| `scripts/citation_chase.py` | writes through the same writer; refuses a `no_abstract` seed; counts | `bb3ab27c80ffcd1b7b49c9dbefee7f11bddcb2e865312c6e839f5b2202dada16` |
| `scripts/keyword_prefilter.py` | refuses an input holding a record below the floor | `2cebad6b3122ed3d4e83542b9e633b7fea3c30082a4a43cb2c57af5240f8181b` |
| `scripts/gate_audit.py` | refuses a marked record below the floor; writes `no_abstract_records_of_the_round` | `35163661cb520604114c1436641c40075e451bae02e5c9afbd1099fc8249edd9` |
| `scripts/run_extraction.py` | the eligibility and extraction tasks refuse an input holding a record below the floor, before any request | `7307332c83b22a5a3c1fe1ad10c5a00d669b50761b09a7f75f940f2f3f25e3fb` |
| `scripts/select_eligible.py` | a decision on a `no_abstract` record raises | `e06ae60ae72720c5fb7228d802db56260bb13d3234a143260a48b85c75935008` |
| `scripts/funnel.py` | counts the `no_abstract` records per screening set (empty, stub, document class, title holding both term groups); they have no mark, decision or gate sample; the audit block carries their count | `0b4d94570c1528cbf1d22e851bb0c7b6f0ed6b3b46b72b062af3399c11ad385c` |
| `scripts/assemble_registry.py` | a `no_abstract` record adds nothing to its family (the registry record is chosen among the records with an abstract); a decision on one raises; two counts | `c1f95f08e34a9c2c011f761a85b37ef39109692d6e1e77148345a6513ca3f485` |
| `scripts/fetch_known_item_abstracts.py` | `--controls` writes the `no_abstract` controls to their own file; a known item below the floor raises | `26d04583f161689f7fccbf35b6efde96a0ab71b40d6f7b209d7db5f838e90ad8` |
| `scripts/negative_control_specificity.py` | `--no-abstract`: such controls are counted, not judged, outside the denominator | `e2d496e398f471c03126c14419966b7b26af7941dfc3ee98f8af6388903459c3` |
| `tests/test_no_abstract.py` | new: 18 tests with hand-worked values | `3c2ffe0f3188c6f3ebe9ff42004d70e22376f73f41f6a08f23a386f99d9d27ec` |
| `tests/test_citation_chase.py` | the round's `no_abstract` counts; the seed guard | `99c47f2be5ba0a4cc9f762897d2a7f8118630adba0e8c28fad22952772f3b4f0` |
| `tests/test_gate_audit.py` | the round's `no_abstract` count beside the audit | `381c9c15bd689f1d61a07cf2f6ed2d7936f18dc8c167953c083c34e9f2819692` |
| `tests/test_stage_reports.py` | the funnel's new count rows | `d6243a4c1e5ea9598ff2109292ef4a0d296cc145392f4de451ade4c344674e7e` |
| `tests/test_screening_set.py` | a record with no abstract is `no_abstract` | `0d2f2c49915d45ddf2535497c3198c72ba38153ff97708cc76415a841264ec0a` |
| `docs/stage0_build/NO_ABSTRACT_FLOOR_2026-10-02.md` | new: the rule, the evidence for the floor, why no sensitivity analysis, the smoke round before and after | `4a88e71cbb1894568ad2f0ce96e1090c0978a3c214da1559b25edd5d342b4419` |
| `docs/stage0_build/no_abstract_floor_evidence.py` | new: abstract lengths of the held pre-2019 records; lengths only for the known items | `66ec64fe34a21f0219c9de4ba98b59234de338e93615b15617aa96381e1c4502` |
| `docs/stage0_build/no_abstract_floor_evidence_2026-10-02.json` | new: its output (313 records; 9 below the floor; six records dated 2019 by PubMed left out) | `d90b7b94f45258f1e8a94ca235d21484be569e5ce4c6fc17e62ed0c0d41c5f3a` |
| `docs/stage0_build/smoke_rerun_no_abstract_rule.py` | new: re-assembly of the smoke round under the rule from stored responses and decisions; no request can be made | `1fcae035814ae0f827de957aa2ac6f7bc13f629c3bd8f2b5909552ba0ef2c6df` |
| `docs/stage0_build/smoke_rerun_no_abstract_rule_counts_2026-10-02.json` | new: before and after counts | `09070481a122e8c921e19cf47a3ebffa9180ee7b2980055cd9a6820fb894cc23` |
| `docs/stage0_build/mutation_check_no_abstract.py` | new: 39 deliberate changes of the rule | `5df47b59f184e034cf2d50efd9867b4c9e409d4491cf58aa0c572a5a38de2cac` |
| `docs/stage0_build/mutation_check_no_abstract.json` | 39 of 39 made a test fail | `9fcc4fd8e8c0dad861d845ce4d7274408c0de49d086bbceffe7007c96906c6cd` |
| `docs/stage0_build/mutation_check_no_abstract_previous.json` | the first run: 38 of 39 (the `empty` count; the test was strengthened) | `953cb3b0b2de77c6b85c6249fec817d209e7e2f89beb0d3120f63744c30c60bd` |
| `docs/stage0_build/osf_dry_run_result_2026-10-02_v17b.txt` | new: OSF dry run on the v17b text, accepted | `b2b7138dcba816fcf1a07aeaa6ab170fd5af67bf24f0124809cb9857c623d583` |
| `docs/stage0_build/LIVE_SMOKE_2026-10-02.md` | a closing section on the rule and the rerun | `b3bbec74d8f68371c18f3b44e4f70e75fc1ff09a9a1744061cb983b8abe0413b` |

### Checks

| file | what | sha256 |
|---|---|---|
| `outputs/tests/pytest_all_modal_20261002T211556Z.txt` | whole suite on Modal on the v17b text and the final code: 711 pass, 1 skipped (the known-item length check, which reads a file outside the image and passes locally); the three synthetic dry runs pass | `e343e43d2c1d1f93c0b90cd367cf346cbf341e935334edf23a7b707683142bf9` |
| `outputs/tests/pytest_all_modal_20261002T211127Z.txt` | the same suite before the one-cell wording change of the rule's table: 711 pass, 1 skipped | `5d5c6e4bb7e42a34fef625a371f5675bc84e7e73c40ceba17b0899fac13d11ce` |
| `outputs/tests/pytest_all_modal_20261002T210933Z.txt` | the same suite before the test of the `empty` count was strengthened: 711 pass, 1 skipped | `b68a372c3a0ccaafe35f90264423c13554c587eaa1f52e84a55044cef8c2c060` |
| `outputs/tests/stage0_file_sha256_2026-10-02_no_abstract_rule.txt` | sha256 of every script, test, fixture, prompt and search file (129 files); against the second-pass listing, 2 added and 15 changed, each named above | `8fdc02778cd9a732f5cd238c245a67cd6be3450753f572f21eda892176923ffa` |
| `outputs/results_manifests/smoke_pre2019_20261002_no_abstract_rule.json` | ledger manifest: the smoke round re-assembled under the rule (42 files) | `c16cf3ac3f1bd071881c41d7d04b6b5e54ead88c0df2c1958e129d2dc4a00a20` |
| `outputs/results_manifests/smoke_pre2019_20261002_no_abstract_rule_paths_removed.json` | ledger manifest: the funnel of the rerun after the repository path was removed from it | `fcd77a8cd11073396b74dd763969470e1371dc9365804ef91d3909016127fde3` |
| `outputs/results_manifests/replaced_files.json` | 6 documented replacements (3 added: the rerun's two funnel files and its gate-audit file, repository path removed) | `59ea61b7ec43d77e2fd43d2c0ad793a7b22ce0d840e9811e3582c958a1d51ee2` |
| `outputs/funnel/smoke_pre2019_20261002_no_abstract_rule/funnel.json` | the funnel of the rerun | `2fe3e7da624952f70cb5d73750189890b95ce769d42e2635c3ba38afa16501fb` |
| `.results/ledger.jsonl` | the ledger after the two runs of the rerun (18 events) | `4bdea5552475e3915f64b843fe8dec23e77bedf49d944f1b5a617c975b6f3497` |

`prereg check`: not frozen. `citations verify --claims claims/`: 5,470 found, 0 not found.
`uv run scripts/stage_record.py verify`: ok for the 17 manifests, with 6 documented replacements.
`results verify --files`: the chain is intact and every file matches except one, reported
`RESEALED`: `outputs/funnel/smoke_pre2019_20261002_no_abstract_rule/funnel.json` is recorded
with two hashes, because the repository's absolute path was removed from it after the rerun was
first recorded (OPEN_QUESTIONS 104). No count in the file changed. The ledger before the two
events had sha256 `ac895c2cf5fe945ef8fcc6e9c7b18109381a62fd340868baf3b70ae128963eb1`, the value
recorded in the section above.
OSF dry run on the v17b text: accepted (`docs/stage0_build/osf_dry_run_result_2026-10-02_v17b.txt`).
Dry-run tables: equal to the run before the rule apart from timestamps, the `no_abstract` field
of the synthetic search records and two zero counts in `registry_assembly.json`.
No quotation of a source was added.

## PREREG v18: round-8 review applied (pre-freeze, 2026-10-03)

Review `planning/perplexity_paper1_final/11_REVIEW_round8.md`; item by item in
`12_ADJUDICATION_round8.md`. Retired to `planning/build_stage0/retired_external_lists/`
(not committed): `scripts/external_lists.py`, `scripts/modal_external_lists.py`,
`verification/external_study_lists.csv`, `verification/external_study_list_ids.csv`.
Archived, not deleted: the ledger with the two dropped events, the two dropped manifests and
the replacement table before the change, in `outputs/superseded/ledger_rerecord_2026-10-03/`.

| file | what | sha256 |
|---|---|---|
| `PREREG.md` | v18 (round-8 review applied; two log lines of 2026-10-03) | `3d351130162fb9a28f8540f9755e64cd36c9d388aad535ab5c304afc4beda2e4` |
| `scripts/build_registry.py` | verdicts on the finite-corpus bounds; `family_release_identity` and `side_overlap` (attribution); `pair_resolvable` needs clear attribution; bootstrap verdicts removed; resampling-stability list | `6537c6e55a89c7c263653bd7dccacfc0731d4840073306868c1154743c96bb63` |
| `scripts/registry_secondaries.py` | claim dates (`pair_claim_dates`) for the first claim, periods, citation and yearly pairs; attribution-aware dataset fields; accounting with pair-level and edge-level counts | `3fcf1d92d072017cee7e359f288d7e2b18379c80faf1355d377398f3e21e51fd` |
| `scripts/registry_indices.py` | H2b verdict on the bounds; contradiction-source dataset fields undetermined under unclear attribution | `1ef08b16e89e390a7b5dc1a05cb0588e87ec41ea006291e3b0487d8a72dc6535` |
| `scripts/hub_proteins.py` | `counted_claims` with family–pair collapse; baseline wording | `21225022ca53e7ac5e6123bc01c4dd068cb7a0cb39caa3571876e4849727ae53` |
| `scripts/biology_joins.py` | hub sensitivity `family_pair_collapsed` | `cb4e84819843f5d7366a02ab41d20eca30443e951ab73a8a98ae24bae7cd3a97` |
| `scripts/record_metadata.py` | `country` command and `country_counts` removed; the variable is still collected | `a246c69c4826e59178181f866f25f37a8965f6597db80324dcc87f28a7ca56b1` |
| `scripts/dry_run_synthetic.py` | expected verdicts worked again for the finite-corpus rule | `5a1ff8f430a0a9a7999179970dc46c97ab7f79811ad02ca6186b2d4861a6c147` |
| `scripts/dry_run_biology_synthetic.py` | yearly series and accounting worked again for claim dates; collapsed-hub check | `fe21ff3299c32769bd3d3c064f00f8446798f169196b1227630a8b2d8699b003` |
| `tests/test_registry.py` | verdict on bounds; attribution rule; claim-specific overlap | `71a0520f2481999c00f0fa1ed97e06aaa73bd5c9014d9434921f690b49fd876c` |
| `tests/test_registry_secondaries.py` | claim dates; attribution in the comparison; accounting edge counts | `650ad6782d36df5fb00a27f7497ac93197b56fde3cbefa17bb0991e47039336f` |
| `tests/test_registry_indices.py` | attribution in contradiction sources; H2b verdict on bounds | `a7407d8e60fd2b367a1bfd2b1f2a0f8426080306958cea68988ba2150a66e8a4` |
| `tests/test_hub_proteins.py` | family–pair collapse | `a3c71b62efde7e87ea48f72d7528889d4fd0dffd1db81eced886dd4e930b1460` |
| `tests/test_record_metadata.py` | external-list and country-table tests removed; no country table | `f8c1ea6c8836740b283be7e5dba3eb48f611baa5ce9b8b8c4f81d6e59253ce9d` |
| `RUNBOOK.md` | external-list and country-table steps removed | `4b45cd155eda8679d6869dfe1b3b5d4b12450d96bc3c6fb2c8f4c5989960528c` |
| `OPEN_QUESTIONS.md` | round-8 items settled; 101 for round 9; 105, 106 | `4a0422e888064d0635fc662d2a0228280b165fcc32ebb503b3a92c7cc7296dff` |
| `outputs/results_manifests/smoke_pre2019_20261002_no_abstract_rule.json` | ledger manifest of the no-abstract rerun, recorded once (42 files) | `14d199aa1d6b8a94421ea8d4705139257267c580dcb8af2fa9e1e63079fd3758` |
| `outputs/results_manifests/replaced_files.json` | 3 documented replacements (the rerun's 3 rows removed) | `8431ebe8cf5a5a039eb6827a01a5dd4697237d284511ba47b110b1e9909c13d5` |
| `.results/ledger.jsonl` | the ledger after the rerun recorded once (17 events) | `f632771a68bf2005b6d08ea451823884e2dc495ea5e7ab51fcf0f33a8d2f7a12` |
| `docs/stage0_build/LEDGER_RERECORD_2026-10-03.md` | new: what was done to the ledger and why | `58b77903b59fc3585606c759807dd083bfaa928e65541cbfd772165d554cfc78` |
| `docs/stage0_build/mutation_check_round8.py` | new: 23 deliberate changes of the round-8 rules | `c746df2394e21105bf9713c9bbecea6d0412df50d4ad5403f8c469fac304449f` |
| `docs/stage0_build/mutation_check_round8.json` | 23 of 23 made a test fail | `76f79132d7d3670206e5f133178892a69b680a5cc4630cc255ee6625357bcf82` |
| `docs/stage0_build/mutation_check_round8_previous.json` | the first run: 21 of 23 (two tests added) | `a2deb9d2251d3f9ac261ddef5d0d69d26297602155efa1a4c55837a0da39e695` |
| `docs/stage0_build/osf_dry_run_result_2026-10-03_v18.txt` | OSF dry run on v18, accepted | `76f79e033d0aa75459f8225a945a4be0d5856d22011a6d2d8caf0bb624c05599` |
| `outputs/tests/pytest_all_modal_20261003T172729Z.txt` | whole suite on Modal on v18 and the final code: 718 pass, 1 skipped | `435519883fd94e7e82cf7e3a0d89bf8775f1ace16bc5d8f299368969c415db3d` |
| `outputs/tests/pytest_all_modal_20261003T172531Z.txt` | the same suite before the two tests that kill the surviving mutations: 716 pass, 1 skipped | `ba3475dbfd6e67b9b41f25da2911b1abc60f760ccd9ec0ff693125c8ce93390a` |

`prereg check`: not frozen. `citations verify --claims claims/`: 5,470 found, 0 not found.
`results verify --files`: all checks passed; chain intact, 17 events; no `RESEALED`,
`CHANGED` or `MISSING` file. `uv run scripts/stage_record.py verify`: ok for every manifest.
OSF dry run on the v18 text: accepted; 23 answers, the longest 49,211 characters.
Dry runs: `outputs/dry_run/20261003T172741Z`, `outputs/dry_run_biology/20261003T172729Z`,
`outputs/dry_run_drug/20261003T172729Z`. No quotation of a source was added.

## Reproducible-science audit, 2026-10-03

No rule changed and nothing above the log of PREREG.md was edited. Files added or changed by the audit of how the repository uses prereg, results, citations and repro (`../../docs/REPRO_TOOLS_AUDIT_2026-10-03.md`).

| file | what | sha256 |
|---|---|---|
| `../../README.md` | new: what the study is, how its record is kept, how to check it, which tools build to install | `5c644d24897e6650ea082dd90b53f9a8db4bb34715626c77786cc4ca26b88b38` |
| `../../CLAUDE.md` | new: the tools and the rules of this repository for Claude Code | `2fedc525aa4323eee8b54fef0905981979f801031ee6ade2e17a39592cda79e1` |
| `../../repro.yaml` | new: the five feasibility counts of foreknowledge item 8 bound to the counts files | `46585593dc3a604d359f9b95fab9c7fdf6984af7eb26bec22637e7dc122076d6` |
| `../../.pre-commit-config.yaml` | new: `repro-verify` on every commit | `a07245e708f90d8646b6ea6b03613fc293442237387f3ac3764f96eb25fa74f1` |
| `../../.github/workflows/verify.yml` | new: records checked on push; sources fetched and quotations verified weekly or by hand; tools pinned to `7bace1c` | `9008f7d55bc3c103305397e3914db20425906c3f43f4f1186731de182c8d8980` |
| `references.bib` | new: 120 entries, every DOI the claims files name and the six works the plan cites without one; `citations lint` clean | `4e85a982b2c62fbbbcf43c9d8794c5aae35ead664ebaab58e28a1adc4ae0148f` |
| `osf_attachments.txt` | new: the 45 files attached to the OSF draft at the freeze | `656f56ff24d2668385fac4ad3d81bd0142e7c103412f82afbfe933dc6dbe265b` |
| `RUNBOOK.md` | the freeze step attaches `osf_attachments.txt` | `bc65be8724553cc2d37886bc3d73ff1eb4a14956543b39fe90c21d9348a6b5c9` |
| `../../claims/liu2025mrkg_original.yaml` | one quotation added: the full passage the plan quotes | `1a817ca52e2ec663da08eb8bf69132e9333ad3ace22e57236e80c85420e95bc5` |
| `../../docs/REPRO_TOOLS_AUDIT_2026-10-03.md` | new: the audit | `281a031e1968a9b669741b6f73982f936c219755b3556d789037e815a3421410` |
| `../../docs/source_verification/FEATURE_REQUEST_exemplar_gaps_2026-10-03.md` | new: tool gaps for the tools session | `6c3fa71445591a829d3e93aa09e5c8d2f7d3a0871b4b4cd94706236aeb300ee5` |
| `../../docs/source_verification/repin_with_extractors.py` | new: pins workbooks, .docx and article XML through the named extractors | `d2767b3abd6481965eb33cb8c9ff981a59e7e0b794e77de7e6bbd692d447bbde` |
| `../../docs/source_verification/extractors_plan.json` | new: the 105 sources it pins | `979ce5f1702ce381452900efa5fbc848d73ec2124576ee002a5ae0ae71fb64c2` |
| `../../docs/source_verification/repin_with_extractors_result_2026-10-03.json` | new: one row per source, pinned and refused quotations | `33f2d30205a6f6e0cb4e94faea67da3fbc55e8f8aa8e971e132d88a697c98a22` |
| `../../docs/source_verification/citations_fetch_extractor_pins_2026-10-03.txt` | new: fetch and verify of the 105 extractor pins from an empty folder | `282380bf82ffce54d7b699b34911b46d1ccd2311b3a3f15c6f8fcc9528a392b0` |
| `../../docs/source_verification/build_references_bib.py` | new: builds references.bib and the claims-to-key map | `97fd7953e9985ef638d2f8929c60fe1be6338c43d88d978b250d9abf6b422cd5` |
| `../../docs/source_verification/claims_to_bibkey.csv` | new: each claims file and its bibliography key | `2509a19277ff7efa1e7ea5ca33385c0f7b1190639bfd31b135be8ff7d62f3630` |
| `../../docs/source_verification/citations_audit_2026-10-03.txt` | new: `citations audit` of references.bib, home path removed | `c54066d550773b1e6a960e8fab1872d35fb95e6fa0a58e69b02bc0e89b1c8c81` |

The 105 claims files that name a built-in extractor, hashed file by file in name order and that list hashed: `4543592a3eb1ac3dd16d0ff79598dfb9e395d4bca928c6e5f405e57338bf7a04`. `.audit-cache/` (120 files) holds the registry records `citations audit` read, so the audit re-runs offline. Checks with reproducible-science `7bace1c`: `citations verify --claims claims/` 7,783 found, 0 not found; `results verify --files` all passed; `repro verify --policy strict` 5 verified; `citations lint` 120 entries, no repeated key, no bare name; `prereg check` not frozen; OSF dry run accepted. The released `citations` on PATH reports 114 quotations of extractor-pinned sources as not found (`../../docs/source_verification/FEATURE_REQUEST_exemplar_gaps_2026-10-03.md`, item 9).

## PREREG v18a: author-reply rule, platform rows confirmed (pre-freeze, 2026-10-03)

Round 9 (`planning/perplexity_paper1_final/13_REVIEW_round9.md`) confirmed v18. v18a adds the rule for lists the authors of the SCALLOP CVD-I and AGES (Emilsson 2018) papers may supply, and foreknowledge item 20; the 14 platform rows are confirmed. Synthetic records, fixtures and committed tables only.

| file | what | sha256 |
|---|---|---|
| `PREREG.md` | v18a: the author-supplied-list rule (background section, sensitivity table) and foreknowledge item 20; two log lines | `abfbc841c17aac0778671be383a22b4cdb7072bc6c99aa52bc96f38862671540` |
| `scripts/author_lists.py` | new: the stage-tied cutoff for author-supplied lists and the decisions file | `a477ea61453e707ba448ca15dfa9439cf7d338cdc022173bb47b4770b4081e70` |
| `scripts/pathway_enrichment.py` | `load_attachments` takes the author-list overrides | `2f8521475d949972fec4e83f50623fb7bfe41991b3ef4c7fd7ce6b9facff6591` |
| `scripts/biology_joins.py` | the pathway step reads the decisions file and runs `author_supplied_lists_after_cutoff` when it has rows | `176805f85431f24a20310a0bd517c533c0e39d1b990bdf9327f543cd7a7c74eb` |
| `tests/test_author_lists.py` | new: both branches of the cutoff, the override, refusals | `025362dc833208a7482fb191397f3a23b5848d165e75895354b59b7295f70cc7` |
| `verification/author_supplied_lists.csv` | new: empty table (header only) | `35a057dcb054872d0f41c2f2c8178cebc20984cbaead3f702d304a08c87e2869` |
| `verification/platform_assay_attachments.csv` | the 14 manually coded rows: status `coded` (author confirmation 2026-10-03) | `1c9041e5628fa0422f1be8c562e7c400944381aea39b6cee7bffc64735aa2b12` |
| `osf_attachments.txt` | adds verification/author_supplied_lists.csv (46 files) | `2a79770208f132f4684130ce585a6dc0db130ceb7f0ccf0602334bb4afb5d47f` |
| `RUNBOOK.md` | stage 5 runs `author_lists.py decide` first; the freeze access line is `metadata only`, with the reason it differs from the OSF option | `727ad3194d79807b0d49537d123e903b46ce0958b74df6f5e560af19e5a57a06` |
| `OPEN_QUESTIONS.md` | 71 and 105 resolved; 107 added | `170aee85282d1b5781a2740d22542f306fe31dcf39b6f4836e34ed6cba176dbb` |
| `../../docs/stage0_build/PLATFORM_ROWS_CONFIRMATION.md` | new location of the platform-row record, with the three checks and the author's confirmation | `72d48071648001661a2612312835b492dcc3ff765d69ab23444d1817d963c4d6` |
| `../../docs/stage0_build/platform_lookups.csv` | column `author_confirmation` added | `8a4c6b96efa8f039a06303d79ea3e557331258e9866b9d9fe8b84dc0df1d00ab` |
| `../../docs/stage0_build/mutation_check_author_lists.py` | new: 11 mutations of the new rule | `8c9a7a6cf14b1b75c16185ec286fce977d575edc08a771d38a95de8a6778a1a3` |
| `../../docs/stage0_build/mutation_check_author_lists.json` | new: 11 of 11 killed | `ccf1fecd76e1604ff76a66bc540e4276b757ee337a3bceb50bf11fcb02283a36` |
| `../../docs/stage0_build/osf_dry_run_result_2026-10-03_v18a.txt` | new: OSF dry run on v18a, accepted | `76f79e033d0aa75459f8225a945a4be0d5856d22011a6d2d8caf0bb624c05599` |
| `../../docs/stage0_build/checks_v18a/verify_commands_2026-10-03.txt` | new: prereg check, results verify, citations verify, repro check with the 7bace1c build | `9de97d32abcfb2ac21fcc204b35a9b9c0192a0391b83a5aee69c5a8c840a99d6` |
| `outputs/tests/pytest_all_modal_20261003T200129Z.txt` | new: 727 pass, 1 skipped; three dry runs pass | `14ead445fd9a819500201b52cab2ad17b578bdeaca19ec330c9319fd80f84c9a` |

## v18b, 2026-10-03

One sentence in §Dataset dictionary (footnote-limited cohorts stay components); OSF dry run accepted; no table or code changed.

| file | change | sha256 |
|---|---|---|
| `PREREG.md` | v18b: the footnote-limited cohort sentence; one `prereg log` line | `736b5b7f5d7df23ca63ba1354599cffcc4abc99f5ac0e543ab06989bb210cc60` |
| `OPEN_QUESTIONS.md` | 82 resolved | `a7697abd4914b9807e2485d6f26c2f434c5f66606ce1e54854d85f69fc37e1ca` |

## Before the first commit, 2026-10-03

| file | change | sha256 |
|---|---|---|
| `../01_census/PARKED_PLAN_v6_never_frozen.md` | one parenthesis naming another manuscript removed from a log line of the parked, never-frozen plan; supersedes the row above for this file | `49a33442284a75cb12edd952795744bf32c6e4c7e5d7faf2aab859a05914fcaf` |
