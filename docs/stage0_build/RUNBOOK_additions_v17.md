# Run-order additions for PREREG v17

To merge into `experiments/02_claims_meta/RUNBOOK.md` (not edited here: another session was
working on that file). Every command runs from `experiments/02_claims_meta/`.

## Before the freeze — external study lists (only if a list file is obtained)

Neither list could be fetched by a plain client on 2026-10-02 (PREREG foreknowledge item 16), so
`verification/external_study_lists.csv` and `verification/external_study_list_ids.csv` hold a
header row only, and the outside check of the search is not run. To add a list before the
freeze, with a list file whose identifier column holds PMIDs or DOIs:

    modal volume put proteome-mr-claim-audit-inputs <file> /02_claims_meta/inputs/external_lists/<file>
    # add one row to verification/external_study_lists.csv: list id, file, url, sha256,
    # identifier column, identifier kind (pmid or doi), year column, source
    PYTHONPATH=scripts modal run scripts/modal_external_lists.py::ids

`ids` checks the sha256, reads the header and the identifier and year columns only, and writes
`verification/external_study_list_ids.csv`. Log the list and its sha256 with `prereg log`, add
the file to `modal_inputs_manifest.json` and RELEASES.md, and rerun the suite. A list file that
is a PDF or a document with a reference list has no reader here.

## Stage 1 — after `assemble_screening_set.py` (only with a pinned list)

After stage 2 has written the eligibility decisions of the search:

    uv run scripts/external_lists.py \
        --screening outputs/screening/<run>/screening_records.jsonl \
        [--chase-screening outputs/screening/chase_round_<k>/screening_records.jsonl ...] \
        --decisions <...search_<rev>.decisions.jsonl> [<chase and gate decisions> ...] \
        --out outputs/external_lists/<run>

Record: `stage_record.py record` with `outputs/external_lists/<run>` among the folders of the
stage in which it runs.

## Stage 4 — after the second `assemble_registry.py` (the registry with the manual codes)

Record metadata of the eligible families: OpenAlex look-ups (HTTP, local), then the table.

    uv run scripts/record_metadata.py fetch --inputs outputs/registry/<run>_coded \
        --screening outputs/screening/<run>/screening_records.jsonl \
        [--chase-screening outputs/screening/chase_round_<k>/screening_records.jsonl ...]
    uv run scripts/record_metadata.py build --inputs outputs/registry/<run>_coded \
        --screening outputs/screening/<run>/screening_records.jsonl \
        [--chase-screening outputs/screening/chase_round_1/screening_records.jsonl ...] \
        --openalex outputs/raw/openalex_metadata/<run>_coded

`fetch` refuses to run before the freeze, stores every response under
`outputs/raw/openalex_metadata/<run>_coded/` with a manifest, and resumes from stored pages.
The chase rounds are passed to `build` in round order. `build` writes
`outputs/registry/<run>_coded/record_metadata.jsonl`, which the stage 5 joins read. Record both
folders with the stage 4 `stage_record.py record` line.

`country` is not part of any stage. It runs only if a reviewer asks for the tabulation:

    uv run scripts/record_metadata.py country --inputs outputs/registry/<run>_coded --window confirmatory

and its output is labelled "requested, not planned".

## Stage 5 — tables and joins

No new command. `modal_biology_joins.py::joins` sends every file of
`outputs/registry/<run>_coded`, which now must hold `families.json`, `registry_assembly.json`
(both written by `assemble_registry.py`) and `record_metadata.jsonl`; the joins write one more
result file, `registry_secondaries.json`, after `registry_indices.json`. The sensitivity run
writes two more tables (`claim_specific_dataset_names_only`, `tested_count_1000_or_more`), and
every table of `build_registry.py` now carries `h2b_verdict`, `two_verdict_reading`,
`two_verdicts_at_bonferroni_level`, `h2_supported_attainable` and `protein_cluster_bootstrap`.
The drug joins write `alignment_expected_from_margins`; the hub and reference-screen results
carry `expected_from_claim_volume` and `claim_records_by_shared_pqtl_source`.

The memory of the joins and sensitivity jobs (32 GB) covers the protein-cluster bootstrap
(10,000 replicates times the number of proteins, the size of the pair bootstrap or smaller).

## Stage 6

No new command. `fulltext_concordance.py` now writes `h2b_within_extracted_subset` beside
`h2_within_extracted_subset`.
