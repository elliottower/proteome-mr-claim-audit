# Run order after the freeze

Every command runs from `experiments/02_claims_meta/`. Each script refuses to overwrite its
output; a stage is committed before the next begins (PREREG.md §Study design). Light steps
(HTTP requests, GPT-6.1 Sol calls, text checks on abstracts) run locally with `uv run`; anything
that reads a pinned resource file or builds the registry tables runs on Modal.

`<run>` is the search date; `<k>` is a citation-chasing round (1 to 3); `<label>` names a
GPT-6.1 Sol run; `<rev>` is the prompt revision id the runner prints.

Every stage is recorded in the results ledger (`.results/` at the repository root) before it is
committed: the inputs are sealed once at the freeze, and each stage ends with its
`stage_record.py record` line (§Results ledger at the end of this file).

## At the freeze

Rehearsed end to end on a scratch copy on 2026-10-02
(`../../docs/stage0_build/DRESS_REHEARSAL_2026-10-02.md`). In this order:

1. Commit everything except `PREREG.md` (the path list of the first commit, with
   `.gitattributes`, which stores every file byte for byte so that a clone holds the bytes whose
   sha256 RELEASES.md and the ledger record).
2. Commit `PREREG.md` alone.
3. `prereg freeze --osf` with the metadata flags, from this folder, and one `--attach` for each
   file in `osf_attachments.txt` (the tables, prompts, search files and resource manifest the plan
   relies on, which the freeze hash does not cover):

       prereg freeze --osf $(sed 's/^/--attach /' osf_attachments.txt) <metadata flags>

   Each attachment is uploaded into the draft, its sha256 compared with the sha256 OSF reports
   for what it received, and an `osf attached <name> sha256 <digest>` line written to the log, so
   the files are registered with the plan and their digests are in it. The freeze refuses a plan
   with uncommitted changes and names the commit of step 2 in the `**Status:**` line. Every check
   that can refuse (the OSF layout, the token, the subject names) runs before anything is
   written. If the draft upload itself fails after the header is written, the plan is frozen and
   has no draft: retry with `prereg freeze --force --osf --access "nothing run"` and the same
   flags; the plan sha256 does not change.
4. Commit the header and the log lines the freeze wrote.
5. Record and seal the freeze, seal the inputs, write the access line (§Results ledger), and
   commit `.results/` and `outputs/results_manifests/prereg_freeze.plan.json`.

After step 3 nothing above the `---` line that precedes `## Log` may change: the title, the
paragraph under it, every section. `prereg check` reports `CHANGED` for one edited character
and `LOG ALTERED` for an edited, reordered or removed log line. A change of plan is a
`prereg log "<what and why>" --access "<level>"` line, never an edit; `--access` is always
given (without it the tool writes `no results seen`). `prereg check` does not read the commit in
the `**Status:**` line or the `**Frozen:**` date; the commit of step 4 is their record.

The whole-file sha256 of `PREREG.md` changes at the freeze and with every log line. After the
freeze, RELEASES.md cites the plan sha256 of the header, which covers everything above the log.

## Stage 1 — search

    uv run scripts/run_search.py
    uv run scripts/assemble_screening_set.py --run outputs/raw/search/<run>
    uv run scripts/keyword_prefilter.py --screening-set outputs/screening/<run>/screening_set.jsonl

`assemble_screening_set.py` (and `citation_chase.py` for a round) classes the records with no
abstract of at least 200 characters as `no_abstract` (`scripts/abstract_floor.py`): they are
listed in `no_abstract.jsonl`, left out of `screening_set.jsonl`, and so are never marked,
gated, sampled, queued or sent to GPT-6.1 Sol. `keyword_prefilter.py`, `gate_audit.py` and
`run_extraction.py` (eligibility and extraction) raise on an input that holds such a record,
`select_eligible.py` and `assemble_registry.py` raise on a decision for one, and
`citation_chase.py` raises on such a seed. `funnel.py` counts them per screening set.

## Stage 2 — eligibility (search)

    uv run scripts/run_extraction.py --task eligibility --label search \
        --abstracts outputs/screening/<run>/screening_queue.jsonl
    uv run scripts/apply_eligibility.py --eligibility outputs/parsed/sol_eligibility_search_<rev>.jsonl
    uv run scripts/select_eligible.py --decisions <...search_<rev>.decisions.jsonl> \
        --screening-set outputs/screening/<run>/screening_set.jsonl \
        --screening-records outputs/screening/<run>/screening_records.jsonl

## Stage 1b — prefiltered citation chasing, round k (then stage 2 on the round)

    uv run scripts/citation_chase.py --round <k> --seeds <previous ...eligible_records.jsonl> \
        --known outputs/screening/<run>/screening_records.jsonl \
        [--known outputs/screening/chase_round_<j>/screening_records.jsonl ...]
    uv run scripts/keyword_prefilter.py --gate \
        --screening-set outputs/screening/chase_round_<k>/screening_set.jsonl
    uv run scripts/run_extraction.py --task eligibility --label chase<k> \
        --abstracts outputs/screening/chase_round_<k>/screening_queue.jsonl
    uv run scripts/apply_eligibility.py --eligibility outputs/parsed/sol_eligibility_chase<k>_<rev>.jsonl

Gate audit, batch b (from 1), repeated until `gate_audit.py` writes no further batch:

    uv run scripts/run_extraction.py --task eligibility --label gate<k>b<b> \
        --abstracts outputs/screening/chase_round_<k>/gate_sample_batch_<b>.jsonl
    uv run scripts/apply_eligibility.py --eligibility outputs/parsed/sol_eligibility_gate<k>b<b>_<rev>.jsonl
    uv run scripts/gate_audit.py --round-dir outputs/screening/chase_round_<k> \
        --decisions <the decisions files of gate batches 1 to b>

Then the round's eligible records, with the sampled records judged eligible or uncertain:

    uv run scripts/select_eligible.py \
        --decisions <...chase<k>_<rev>.decisions.jsonl> <the gate batch decisions files> \
        --screening-set outputs/screening/chase_round_<k>/screening_set.jsonl \
        --screening-records outputs/screening/chase_round_<k>/screening_records.jsonl

Round k+1 runs when round k's `eligible_records.jsonl` is not empty and k < 3. The chase
response bodies go to the volume and only their manifest is committed:

    modal volume put proteome-mr-claim-audit-inputs outputs/raw/citation_chase \
        /02_claims_meta/raw/citation_chase

## Negative controls (once)

    uv run scripts/fetch_known_item_abstracts.py --controls
    uv run scripts/run_extraction.py --task eligibility --label controls \
        --abstracts outputs/negative_controls/negative_control_abstracts.jsonl
    uv run scripts/apply_eligibility.py --eligibility outputs/parsed/sol_eligibility_controls_<rev>.jsonl
    uv run scripts/negative_control_specificity.py --controls search/negative_controls.jsonl \
        --decisions <...controls_<rev>.decisions.jsonl> \
        --no-abstract outputs/negative_controls/negative_control_no_abstract.jsonl \
        --out outputs/negative_controls

`fetch_known_item_abstracts.py --controls` writes the control records classed `no_abstract` to
`negative_control_no_abstract.jsonl` and leaves them out of the abstracts file; they are counted,
not judged, and outside the specificity denominator.

## Stage 3 — extraction (the search and each round)

    uv run scripts/run_extraction.py --task extraction --label <label> \
        --abstracts <...eligible_abstracts.jsonl>
    uv run scripts/sample_repeat_run.py --decisions <...decisions.jsonl> \
        --abstracts <screening_set.jsonl>
    uv run scripts/run_extraction.py --task extraction --label <label>_repeat \
        --raw-root outputs/raw/sol_repeat --abstracts <...repeat_sample.jsonl>
    uv run scripts/repeat_run_agreement.py --run1 outputs/parsed/sol_extraction_<label>_<rev>.jsonl \
        --run2 outputs/parsed/sol_extraction_<label>_repeat_<rev>.jsonl \
        --sample <...repeat_sample.json> --out outputs/repeat_run/<label>

## Stage 4 — verification and registry

    uv run scripts/verify_spans.py --extraction outputs/parsed/sol_extraction_<label>_<rev>.jsonl \
        --abstracts <...eligible_abstracts.jsonl>
    modal run --detach scripts/modal_biology_joins.py::verify_claims \
        --extraction outputs/parsed/sol_extraction_<label>_<rev>.jsonl
    uv run scripts/claim_tags.py --extraction <the extraction file of the search and of each round> \
        --out outputs/registry/<run>
    modal volume get proteome-mr-claim-audit-inputs \
        /02_claims_meta/inputs/hgnc/hgnc_complete_set_2026-09-04.tsv inputs/hgnc/
    modal volume get proteome-mr-claim-audit-inputs \
        /02_claims_meta/inputs/uniprot/uniprot_human_reviewed.tsv inputs/uniprot/
    uv run scripts/assemble_registry.py --records <search_records.jsonl of the search and each round> \
        --decisions <decisions of each> --extraction <extraction rows of each> \
        --checks <claim_checks.jsonl of each> --out outputs/registry/<run>
    uv run scripts/manual_dataset_coding.py queue \
        --claims outputs/registry/<run>/registry_claims.jsonl \
                 outputs/registry/<run>/registry_claims_update.jsonl \
        --out outputs/manual_coding/<run>
    # the three checks fill outputs/manual_coding/<run>/manual_dataset_codes.csv (PREREG.md
    # §Manual coding of dataset names); then:
    uv run scripts/manual_dataset_coding.py check \
        --codes outputs/manual_coding/<run>/manual_dataset_codes.csv \
        --queue outputs/manual_coding/<run>/manual_coding_queue.csv \
        --out outputs/manual_coding/<run>
    uv run scripts/assemble_registry.py <the same inputs> \
        --manual-codes outputs/manual_coding/<run>/manual_dataset_codes.csv \
        --out outputs/registry/<run>_coded
    uv run scripts/record_metadata.py fetch --inputs outputs/registry/<run>_coded \
        --screening outputs/screening/<run>/screening_records.jsonl \
        [--chase-screening outputs/screening/chase_round_<k>/screening_records.jsonl ...]
    uv run scripts/record_metadata.py build --inputs outputs/registry/<run>_coded \
        --screening outputs/screening/<run>/screening_records.jsonl \
        [--chase-screening outputs/screening/chase_round_1/screening_records.jsonl ...] \
        --openalex outputs/raw/openalex_metadata/<run>_coded
    uv run scripts/funnel.py --screening-dir outputs/screening/<run> \
        [--screening-dir outputs/screening/chase_round_<k> ...] --decisions <...> \
        --extraction <...> --spans <...> --checks <...> --assembly outputs/registry/<run>_coded \
        --out outputs/funnel/<run>

The decisions, extraction, span and check files passed to `assemble_registry.py` and `funnel.py`
include those of the gate batches. `claim_tags.py` also writes the wording audit
(`wording.jsonl`, `wording_summary.json`); `manual_dataset_coding.py queue` also writes
`manual_coding_packet.csv`, the only file the coder and the checker are given.

The first assembly (without codes) feeds the manual-coding queue; the second, with the codes,
is the registry of stage 5 (`outputs/registry/<run>_coded`, which also holds
`registry_claims_without_manual_coding.jsonl` for the sensitivity analysis when at least one
name was coded; with no coded name the file is not written and the joins report no
`sensitivity_without_manual_dataset_coding`, which would equal the primary). `claim_tags.jsonl`
is copied into it:

    cp outputs/registry/<run>/claim_tags.jsonl outputs/registry/<run>_coded/claim_tags.jsonl

`record_metadata.py fetch` looks up the eligible families' records in OpenAlex (HTTP, local). It
refuses to run before the freeze, stores every response under
`outputs/raw/openalex_metadata/<run>_coded/` with a manifest, and resumes from stored pages. The
chase rounds are passed to `build` in round order. `build` writes
`outputs/registry/<run>_coded/record_metadata.jsonl`, which the stage 5 joins read. Both folders
are recorded with the stage 4 `stage_record.py record` line.

The first author's country is collected in `record_metadata.jsonl` and no table of it is made;
a table is made only if a reviewer requests one after submission (PREREG.md, §Measured
variables, record metadata and country).

`verify_claims.py` reads the pinned HGNC, UniProt, MONDO and EFO files (160 MB), so it runs on
Modal: the entrypoint sends the extraction file and the folder
`outputs/verification/sol_extraction_<label>_<rev>/` that `verify_spans.py` wrote, runs the
script against the files of the volume, stores the folder with `claim_checks.jsonl` and
`claim_summary.json` under `/02_claims_meta/stage4/sol_extraction_<label>_<rev>/`, and copies the
two results into the local folder. `assemble_registry.py` and `fulltext_concordance.py` read the
HGNC and UniProt files (20 MB) locally; the two `modal volume get` lines fetch them (skip a file
already present), and the scripts refuse a file that is missing or whose sha256 differs from
`reference/MANIFEST.json`. `verify_spans.py`, `verify_claims` and their ledger folders run once
per extraction file; `claim_tags.py` takes all the extraction files in one call and writes one
`claim_tags.jsonl`. `verify_spans.py`
pins every evidence span with `citations` and takes about half a second per claim record.

## Stage 5 — tables and joins (Modal)

    uv run scripts/author_lists.py decide --inputs outputs/registry/<run>_coded \
        --ledger "$(git rev-parse --show-toplevel)/.results/ledger.jsonl"
    modal run --detach scripts/modal_biology_joins.py::joins --inputs outputs/registry/<run>_coded \
        --abstracts <screening_set.jsonl of the search and of each round, comma-separated> \
        --run-name <run>
    modal run --detach scripts/modal_biology_joins.py::joins --inputs outputs/registry/<run>_coded \
        --abstracts <the same files> --run-name <run> --window update
    modal run --detach scripts/modal_biology_joins.py::sensitivity --records <...> \
        --decisions <...> --extraction <...> --checks <...> --run-name <run> \
        --chase-records <chase search_records.jsonl, comma-separated> \
        --manual-codes outputs/manual_coding/<run>/manual_dataset_codes.csv
    modal run --detach scripts/modal_drug_joins.py::joins \
        --claims outputs/registry/<run>_coded/registry_claims.jsonl \
        --wording outputs/registry/<run>_coded/claim_tags.jsonl --run-name <run>

The H1 and H2 tables are the `primary` entry of the sensitivity run
(`scripts/build_registry.py` applied to the confirmatory-window registry).

`author_lists.py decide` writes `author_list_decisions.json` into the inputs folder before the
joins: a list the authors supplied for the SCALLOP CVD-I or AGES (Emilsson 2018) row
(`verification/author_supplied_lists.csv`, empty at the freeze) replaces that row's background
when it was pinned before the first `s5_biology_` run in the ledger and before any written
confirmatory `pathway_enrichment.json`; otherwise it is read only in
`author_supplied_lists_after_cutoff`. The joins refuse to run when the table has a row and the
decisions file is absent. A supplied list is pinned with `citations`, added to the assay lists
(`platform_list_sources.csv`, rebuilt on Modal), entered in the table with the UTC time of its
pin and logged with `prereg log` before `decide` runs.

`modal_biology_joins.py::joins` sends every file of `outputs/registry/<run>_coded`, which must
hold `families.json`, `registry_assembly.json` (both written by `assemble_registry.py`) and
`record_metadata.jsonl`; the joins write `registry_secondaries.json` after
`registry_indices.json`. The sensitivity run writes the tables
`claim_specific_dataset_names_only` and `tested_count_1000_or_more` with the others, and every
table of `build_registry.py` carries `h2b_verdict`, `two_verdict_reading`,
`two_verdicts_at_bonferroni_level`, `h2_supported_attainable` and `protein_cluster_bootstrap`.
The drug joins write `alignment_expected_from_margins`; the hub and reference-screen results
carry `expected_from_claim_volume` and `claim_records_by_shared_pqtl_source`. The memory of the
joins and sensitivity jobs (32 GB) covers the protein-cluster bootstrap (10,000 replicates times
the number of proteins, the size of the pair bootstrap or smaller).

Each job writes its results on the volume and commits before it returns; the local entrypoint
then copies them under `outputs/`. If the laptop sleeps or the terminal closes before the copy,
the results are still on the volume. Fetch them instead of rerunning (a rerun under the same
run name is refused):

    modal volume get proteome-mr-claim-audit-inputs \
        /02_claims_meta/stage5/<run>/biology_confirmatory outputs/stage5_biology/<run>/confirmatory
    modal volume get proteome-mr-claim-audit-inputs \
        /02_claims_meta/stage5/<run>/sensitivity_tables.json outputs/stage5_biology/<run>/

and likewise `biology_update` to `outputs/stage5_biology/<run>/update`, and the three
`drug_*` files of `/02_claims_meta/stage5/<run>/` to `outputs/stage5_drug/<run>/`. The stage's
`stage_record.py record` line then compares every local copy with the volume file.

## Stage 6 — full-text concordance (secondary)

    uv run scripts/fetch_fulltext.py --census \
        --families-meta outputs/registry/<run>_coded/families_meta.json \
        --screening-records outputs/screening/<run>/screening_records.jsonl \
            [outputs/screening/chase_round_<k>/screening_records.jsonl ...] \
        --out outputs/fulltext/<run>
    uv run scripts/run_extraction.py --task fulltext_extraction --label ft \
        --abstracts outputs/fulltext/<run>/fulltext_bodies.jsonl
    uv run scripts/verify_spans.py --extraction outputs/parsed/sol_fulltext_extraction_ft_<rev>.jsonl \
        --abstracts outputs/fulltext/<run>/fulltext_bodies.jsonl --text-field body
    modal run --detach scripts/modal_biology_joins.py::verify_claims \
        --extraction outputs/parsed/sol_fulltext_extraction_ft_<rev>.jsonl
    uv run scripts/fulltext_concordance.py \
        --abstract-checks <claim_checks.jsonl of the search and of each round> \
        --fulltext-checks outputs/verification/sol_fulltext_extraction_ft_<rev>/claim_checks.jsonl \
        --fulltext-extraction outputs/parsed/sol_fulltext_extraction_ft_<rev>.jsonl \
        --status outputs/fulltext/<run>/fulltext_status.json \
        --families outputs/registry/<run>_coded/families.json --out outputs/fulltext/<run>
    uv run scripts/fulltext_concordance.py <the same inputs> --window update

The census writes `fulltext_status.json` and `fulltext_bodies.jsonl`. When no family has an
open-access full text, `fulltext_bodies.jsonl` is empty and the stage ends with the census:
`run_extraction.py` refuses an empty input, and there is no full-text extraction and no
concordance table (seen in the smoke run of 2026-10-02, where neither eligible family had one).
`fulltext_concordance.py` writes `h2b_within_extracted_subset` beside
`h2_within_extracted_subset`. The full-text claim checks run on Modal like those of stage 4.

## Smoke run before the freeze (records first public before 2019 only)

Run on 2026-10-02 in two passes (`../../docs/stage0_build/LIVE_SMOKE_2026-10-02.md`). The same
commands as stages 1 to 6, with these differences, which exist only for a run made before the
freeze:

    uv run scripts/run_search.py --smoke [--smoke-start <day> --smoke-end <day>] --smoke-label <label>
    uv run scripts/assemble_screening_set.py --run outputs/raw/search_smoke/<label> \
        --out outputs/screening_smoke/<label>
    uv run scripts/citation_chase.py --round 1 --smoke --smoke-label <label> --seeds <...> --known <...>
    uv run scripts/assemble_registry.py <inputs> --smoke-label <label> --out outputs/registry/<label>...
    uv run scripts/record_metadata.py fetch --smoke --inputs <registry dir> --screening <...>
    modal run --detach scripts/modal_biology_joins.py::sensitivity <inputs> \
        --run-name <label>... --smoke-label <label>
    uv run scripts/fetch_fulltext.py --census --before 2019-01-01 --families-meta <...> \
        --screening-records <...> --out outputs/fulltext/<label>...

- The smoke window lies between 2014-01-01 and 2018-12-31; the default is November and December
  2018. The smoke chase limits cited and citing works to an OpenAlex date of 2018-12-31 or
  earlier and leaves out of its screening set any record whose first public date (PubMed's,
  where there is one) is later; `record_metadata.py fetch --smoke` and
  `fetch_fulltext.py --census --before` refuse a record first public in 2019 or later before
  any request.
- GPT-6.1 Sol runs take `--raw-root outputs/raw/sol_<label>` (and `outputs/raw/sol_<label>_repeat`
  for the repeat run), so no exchange is written into the folders of the registered run.
- Every eligible family of such a run is first public before 2019, so without a switch its
  window is `outside` and `registry_claims.jsonl`, the manual-coding queue and every stage 5
  table are empty (the first pass). `assemble_registry.py --smoke-label <label>` gives those
  families the window `confirmatory` so that stages 4b to 6 run with content (the second pass).
  The switch refuses a label that does not start with `smoke_`, any record first public in
  2019 or later, and an output folder other than `outputs/registry/<label>...`;
  `registry_assembly.json` carries `smoke_label`, and the manual-coding queue, the funnel, the
  biology and drug joins and the full-text census refuse to write the results of a smoke
  registry under a folder or run name that does not start with the label, and refuse a smoke
  name for any other registry (`scripts/smoke_guard.py`). The sensitivity run takes the same
  label, since it assembles the registry itself. No registered run passes `--smoke-label`.
- The gate audit of a chase round needs one eligibility call per sampled record (a first batch
  of up to 600), and `funnel.py` refuses a round whose audit is not finished; the funnel of a
  smoke run without the audit takes the search alone. With the audit run (second pass: 86
  calls), `select_eligible.py` takes the gate decisions with the round's decisions, and the
  funnel takes the search and the round.
- The smoke round was re-assembled under the `no_abstract` rule from its stored responses and
  decisions, with no request and no model call
  (`../../docs/stage0_build/smoke_rerun_no_abstract_rule.py`; outputs under
  `<label>_no_abstract_rule`): 3 of 115 screening records are `no_abstract`, and the gate audit
  has 0 positives in 83 sampled records.
- A dataset name queued for manual coding is not coded in a smoke run: `check` refuses a codes
  table that does not cover the queue, and the registry is assembled with a codes table that
  holds the header row only, so the automatic mapping stands.

## Results ledger

`.results/ledger.jsonl` and `.results/ledger.head` are committed with every stage. `results`
finds the ledger from any folder of the repository and writes paths relative to its root. Notes
are public text.

### Once, at the freeze (after `prereg freeze` and its commit, before stage 1)

    uv run scripts/stage_record.py plan
    results seal --role prereg outputs/results_manifests/prereg_freeze.plan.json
    results seal --role script scripts/*.py ../../pyproject.toml ../../uv.lock
    results seal --role input prompts/eligibility_prompt.md prompts/extraction_prompt.md \
        prompts/fulltext_extraction_prompt.md prompts/schema.json search/queries.md \
        search/prefilter_terms.json search/known_items.md search/negative_controls.jsonl \
        search/negative_controls_meta.json
    results seal --role data dataset_dictionary.csv reference/MANIFEST.json \
        modal_inputs_manifest.json modal_inputs_verification.json \
        $(find verification -type f -not -path 'verification/superseded/*' | sort)
    results access "in-window material seen before the freeze: PubMed hit counts (2020-2025) and, for the 24 known items, the eligibility decisions, reason codes and tested protein counts that GPT-6.1 Sol returned as the screening instrument (people read only those outputs); no claim, direction, dataset or outcome from the window was extracted or viewed" --level "metadata only"

`stage_record.py plan` runs `prereg check` and writes the commit, the plan sha256 and the date
of the freeze header to `prereg_freeze.plan.json`; that file is sealed, and `PREREG.md` is not.
`prereg log` appends to `PREREG.md`, so a seal of the whole file reads `CHANGED` from the first
log line on (seen in the rehearsal), while the plan sha256 covers everything above the log and
does not move. `stage_record.py verify` compares the header with the record and runs
`prereg check` again.

`modal_inputs_manifest.json` carries the sha256 of every file on the Modal volume and
`modal_inputs_verification.json` the comparison made on the volume
(`modal run scripts/modal_hash_volume.py::main`), so sealing the two seals the volume inputs by
hash. A sealed file is not edited afterwards: `results verify --files` reports a file sealed
twice as `RESEALED`. The access line is the author's statement of foreknowledge (PREREG.md,
§Explanation of foreknowledge, item 12); a further `results access` line is written when a
stage's outputs are first opened. The level differs from the OSF foreknowledge option ("Authors
have observed the data, but have not performed the proposed analyses") because the two ask
different questions: OSF asks whether what was seen could influence analysis decisions (the
known-item check changed the eligibility prompt), the ledger asks what kind of data was seen
(eligibility metadata of 24 records, no outcome).

### After each stage

`stage_record.py record` hashes every file under the folders given into
`outputs/results_manifests/<run-id>.json` and records that manifest and the `--file` results with
`results run`. A run id is recorded once.

A recorded file is not edited. If one must change (on 2026-10-02 an absolute path was removed
from three stored outputs of the `citations` CLI), `stage_record.py replace --path <file> --new
<file with the new bytes> --archive <folder> --reason "<why>"` archives the original, writes the
new bytes and adds a row to `outputs/results_manifests/replaced_files.json`; `verify` then
accepts that file with exactly the replaced bytes and reports any other change. The table is
committed with the stage.

| stage | run id | recorded |
|---|---|---|
| 1 search | `s1_search_<run>` | `outputs/raw/search/<run>` `outputs/screening/<run>` |
| 2 eligibility | `s2_eligibility_<label>_<rev>` | `outputs/raw/sol/eligibility/<rev>` and the `outputs/parsed/sol_eligibility_<label>_<rev>*` files |
| 1b chase round k | `s1b_chase_<k>` | `outputs/raw/citation_chase/chase_round_<k>` `outputs/screening/chase_round_<k>` (response bodies compared with the volume) |
| negative controls | `controls_<rev>` | `outputs/negative_controls` |
| 3 extraction | `s3_extraction_<label>_<rev>` | `outputs/raw/sol/extraction/<rev>` `outputs/raw/sol_repeat` `outputs/repeat_run/<label>` and the `outputs/parsed/sol_extraction_<label>*_<rev>*` files |
| 4 verification and registry | `s4_registry_<run>` | `outputs/citations/sol_extraction_<label>_<rev>` `outputs/verification/sol_extraction_<label>_<rev>` (compared with the volume) for each extraction file, then `outputs/registry/<run>` `outputs/manual_coding/<run>` `outputs/registry/<run>_coded` `outputs/raw/openalex_metadata/<run>_coded` `outputs/funnel/<run>` |
| 5 biology joins | `s5_biology_<run>` | `outputs/stage5_biology/<run>` (compared with the volume, `sensitivity_tables.json` included) |
| 5 drug joins | `s5_drug_<run>` | `outputs/stage5_drug/<run>` (compared with the volume) |
| 6 full text | `s6_fulltext_<run>` | `outputs/raw/fulltext` `outputs/fulltext/<run>` `outputs/raw/sol/fulltext_extraction/<rev>` |

A stage that ran locally:

    uv run scripts/stage_record.py record --run-id s1_search_<run> \
        --note "registered search <run>: raw responses, screening set, prefilter" \
        --file outputs/screening/<run>/screening_set.jsonl \
        outputs/raw/search/<run> outputs/screening/<run>

A stage that ran on Modal writes its results on the volume and the local entrypoint copies them
under `outputs/`. The volume folder is hashed on the volume, and `record` refuses unless every
local copy has the bytes of the volume file:

    modal run scripts/modal_hash_volume.py::tree --prefix /02_claims_meta/stage5/<run> \
        --out outputs/results_manifests/s5_<run>.volume.json
    uv run scripts/stage_record.py record --run-id s5_biology_<run> \
        --note "stage 5 biology joins and sensitivity tables, run <run>" \
        --volume-hashes outputs/results_manifests/s5_<run>.volume.json \
        --volume-map /02_claims_meta/stage5/<run>/biology_confirmatory=outputs/stage5_biology/<run>/confirmatory \
        --volume-map /02_claims_meta/stage5/<run>/biology_update=outputs/stage5_biology/<run>/update \
        --volume-map /02_claims_meta/stage5/<run>/sensitivity_tables.json=outputs/stage5_biology/<run>/sensitivity_tables.json \
        --file outputs/stage5_biology/<run>/sensitivity_tables.json \
        outputs/stage5_biology/<run>
    uv run scripts/stage_record.py record --run-id s5_drug_<run> \
        --note "stage 5 drug-development joins, run <run>" \
        --volume-hashes outputs/results_manifests/s5_<run>.volume.json \
        --volume-map /02_claims_meta/stage5/<run>=outputs/stage5_drug/<run> \
        --file outputs/stage5_drug/<run>/drug_tables.json outputs/stage5_drug/<run>

Stage 4, with one extraction file (one `--volume-map` and the two folders per further file):

    modal run scripts/modal_hash_volume.py::tree --prefix /02_claims_meta/stage4 \
        --out outputs/results_manifests/s4_<run>.volume.json
    uv run scripts/stage_record.py record --run-id s4_registry_<run> \
        --note "stage 4: span and claim checks, registry, manual dataset codes, funnel, run <run>" \
        --volume-hashes outputs/results_manifests/s4_<run>.volume.json \
        --volume-map /02_claims_meta/stage4/sol_extraction_<label>_<rev>=outputs/verification/sol_extraction_<label>_<rev> \
        --file outputs/registry/<run>_coded/registry_assembly.json \
        outputs/citations/sol_extraction_<label>_<rev> \
        outputs/verification/sol_extraction_<label>_<rev> \
        outputs/registry/<run> outputs/manual_coding/<run> outputs/registry/<run>_coded \
        outputs/raw/openalex_metadata/<run>_coded outputs/funnel/<run>

The chase response bodies of round k, after `modal volume put`:

    modal run scripts/modal_hash_volume.py::tree \
        --prefix /02_claims_meta/raw/citation_chase/chase_round_<k> \
        --out outputs/results_manifests/s1b_chase_<k>.volume.json
    uv run scripts/stage_record.py record --run-id s1b_chase_<k> \
        --note "citation chasing round <k>: responses, screening set, gate audit" \
        --volume-hashes outputs/results_manifests/s1b_chase_<k>.volume.json \
        --volume-map /02_claims_meta/raw/citation_chase/chase_round_<k>=outputs/raw/citation_chase/chase_round_<k> \
        outputs/raw/citation_chase/chase_round_<k> outputs/screening/chase_round_<k>

### Checks

    results verify --files                     # the chain, the sealed inputs, each manifest
    uv run scripts/stage_record.py verify      # the freeze record, and every file each manifest names
    citations verify --claims claims/          # from the repository root
    prereg check

Both of the first two are needed: `results verify --files` rehashes the sealed inputs, the
manifests and the files recorded with `--file`, and does not open a file that only a manifest
names; `stage_record.py verify` rehashes those. In the rehearsal each reported the edits made to
its own files (a recorded table, a file named only in a manifest, a sealed input, a manifest, a
ledger line, a ledger line removed) and neither reported the other's. `citations verify` reads
the texts under `sources/`, which are not committed: in a clone every quotation is `unchecked`
and the command exits non-zero until `citations fetch --claims claims/` has run
(`../../docs/source_verification/REFETCH_STATUS_2026-10-02.md` for what it can fetch).

A number that enters the manuscript is bound to its run when the sentence is written:

    results claim "<the sentence's number, as written>" --run-id <run id> --confirmatory \
        --frozen-at <the commit in PREREG.md's **Status:** line> --location "<table or section>"

`--frozen-at` takes the commit the freeze header names (`frozen_at_commit` in
`prereg_freeze.plan.json`), not the later commit that holds the header: `results` accepts any
commit, and `repro check` lists a claim citing a commit no frozen plan records. After the
`results access` line that records outputs as seen, a confirmatory claim on a later run is
refused without `--frozen-at`.

Before submission, on the manuscript source:

    results coverage <paper.tex> --strict      # every number bound to a run
    citations coverage <paper.tex> --claims claims/ --strict
    repro verify --policy strict               # if a repro.yaml is kept

`results coverage` does not count a value with one significant digit (0.2, 0.8, 80%, 5) or one
of its listed constants (0.5, 0.05, 0.95, 95), so an estimate printed that way is never
reported as unbound: print proportions to two decimals. It reads `%` as the start of a comment
in every format, so it reads a `.tex` source (where a percent sign is `\%`) and not a
Markdown draft. A `repro.yaml` that pins `PREREG.md` by its whole-file sha256 breaks at the next
`prereg log` line; regenerate the pin after the last log line or leave the plan out of the
manifest (`../../docs/stage0_build/FEATURE_REQUEST_plan_hash_and_coverage.md`).

