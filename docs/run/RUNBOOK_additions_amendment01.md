# RUNBOOK additions for Amendment 1 (extraction-system comparison: registered Sol extraction, tuned Luna extraction system)

To be merged into `experiments/02_claims_meta/RUNBOOK.md` when the amendment is logged. Commands
run from `experiments/02_claims_meta`. `<lrev>` is the Luna revision (`e4e4ee731887` for the
committed prompt and schema); `<rev>` is the Sol extraction revision (`0b97103cd7a4`).

Nothing below runs before the log of `PREREG.md` names the sha256 of
`AMENDMENT_01_extraction_system_comparison.md` and of `prompts/luna_extraction_prompt.md`;
`run_extraction_luna.py` refuses otherwise. No step changes a file of the primary run.

## Stage 3L: Luna extraction (after stage 3, once per extraction file: the search, each chase round, each gate batch)

    uv run scripts/run_extraction_luna.py --abstracts <...eligible_abstracts.jsonl> \
        --sol-extraction outputs/parsed/sol_extraction_<label>_<rev>.jsonl --label <label> --run 1
    uv run scripts/run_extraction_luna.py --abstracts <...eligible_abstracts.jsonl> \
        --sol-extraction outputs/parsed/sol_extraction_<label>_<rev>.jsonl --label <label> --run 2

Each run stores every exchange under `outputs/raw/luna/extraction/<lrev>/run<k>/` before it is
parsed and resumes from the stored exchanges if stopped. The parsed file
`outputs/parsed/luna_extraction_<label>_run<k>_<lrev>.jsonl` and its `.meta.json` are written
once; an existing one is refused.

## Stage 4L: verification and registry claims (after stage 4)

For each Luna file, and for the second Sol run on the stability sample
(`sol_extraction_<label>_repeat_<rev>.jsonl`, with `--abstracts <...repeat_sample.jsonl>`):

    uv run scripts/verify_spans.py --extraction outputs/parsed/luna_extraction_<label>_run<k>_<lrev>.jsonl \
        --abstracts <...eligible_abstracts.jsonl>
    modal run --detach scripts/modal_biology_joins.py::verify_claims \
        --extraction outputs/parsed/luna_extraction_<label>_run<k>_<lrev>.jsonl

Then one assembly per source, with the records, decisions and manual codes of the primary
registry and that source's extraction rows and claim checks:

    uv run scripts/assemble_registry.py --records <as in stage 4> --decisions <as in stage 4> \
        --extraction <the source's extraction files> --checks <the source's claim_checks.jsonl files> \
        --manual-codes outputs/manual_coding/<run>/manual_dataset_codes.csv \
        --out outputs/extraction_system_comparison/<run>/<source>_registry

with `<source>` one of `luna_run1`, `luna_run2`, `sol_repeat`. The manual-coding queue is not
rebuilt and no name is coded for these assemblies.

## Stage 5L: the comparison (after the stage-5 tables of the primary registry are committed)

With `<out>` = `outputs/extraction_system_comparison/<run>`:

    uv run scripts/extraction_system_comparison.py usage --role sol \
        --raw outputs/raw/sol/extraction/<rev> \
        --parsed <every outputs/parsed/sol_extraction_<label>_<rev>.jsonl of the run, not the repeat> \
        --out <out>/usage_sol.json
    uv run scripts/extraction_system_comparison.py usage --role luna_run1 \
        --raw outputs/raw/luna/extraction/<lrev>/run1 \
        --parsed <every outputs/parsed/luna_extraction_<label>_run1_<lrev>.jsonl> \
        --out <out>/usage_luna_run1.json
    uv run scripts/extraction_system_comparison.py usage --role luna_run2 \
        --raw outputs/raw/luna/extraction/<lrev>/run2 \
        --parsed <every outputs/parsed/luna_extraction_<label>_run2_<lrev>.jsonl> \
        --out <out>/usage_luna_run2.json
    modal run --detach scripts/modal_extraction_system_comparison.py::compare --run-name <run> \
        --sol outputs/registry/<run>_coded/registry_claims.jsonl \
        --luna-run1 <out>/luna_run1_registry/registry_claims.jsonl \
        --luna-run2 <out>/luna_run2_registry/registry_claims.jsonl \
        --sol-repeat <out>/sol_repeat_registry/registry_claims.jsonl \
        --repeat-sample <each ...repeat_sample.json, comma-separated> \
        --sol-tables outputs/stage5_biology/<run>/sensitivity_tables.json \
        --usage-sol <out>/usage_sol.json --usage-luna-run1 <out>/usage_luna_run1.json \
        --usage-luna-run2 <out>/usage_luna_run2.json

`usage` reads stored exchanges and the run's parsed extraction files only and prices the tokens
(no bootstrap; local). Its denominator is every abstract the run attempted, read from `--parsed`
(one row per abstract submitted), not the abstracts with a successful response; abstracts with
no billable response and `extraction_failed` abstracts are counted separately. Exchanges in the
raw folder of records no parsed file names (the pre-freeze development and smoke runs share
`outputs/raw/sol/extraction/<rev>`) are counted and not priced. The three usage files are
required: `compare` refuses a missing one, a file of another run, or runs that did not attempt
the same abstracts.

`compare` runs on Modal, stores `extraction_system_comparison.json` on the volume under
`/02_claims_meta/extraction_system_comparison/<run>/`, commits, and the entrypoint copies it to
`<out>/extraction_system_comparison.json`. It raises if the tables it computes from the Sol
claims differ from the `primary` entry of `sensitivity_tables.json`, and never overwrites a
result. For the two Luna-derived registries the file holds estimates, bounds, denominators,
intervals and each estimate's difference from Sol's, and no threshold classification. If the
terminal closes before the copy:

    modal volume get proteome-mr-claim-audit-inputs \
        /02_claims_meta/extraction_system_comparison/<run>/extraction_system_comparison.json <out>/

The "verification by source" rows of the supplement table are read from
`outputs/verification/<extraction stem>/span_summary.json` and `claim_summary.json` and from
each extraction file's `.meta.json`.

## Results ledger

| stage | run id | folders |
|---|---|---|
| 3L Luna extraction | `a1_luna_extraction_<label>_<lrev>` | `outputs/raw/luna/extraction/<lrev>` and the `outputs/parsed/luna_extraction_<label>_run*_<lrev>*` files |
| 4L, 5L | `a1_extraction_system_comparison_<run>` | `outputs/verification/luna_extraction_*`, `outputs/verification/sol_extraction_<label>_repeat_<rev>`, `outputs/extraction_system_comparison/<run>` |

Recorded with `scripts/stage_record.py record --run-id <run id>` and the folders, as for the
other stages. The Luna prompt and the four new scripts are sealed when the amendment is logged
(`planning/build_stage0/AMENDMENT_01_logging_steps.md`).

## Tests

    modal run scripts/modal_extraction_system_comparison.py::tests

runs `tests/test_extraction_system_comparison.py` and `tests/test_run_extraction_luna.py`, the synthetic
dry run (`scripts/dry_run_extraction_system_comparison_synthetic.py`) and the mutation check
(`docs/run/mutation_check_amendment01.py`), and saves the three results under `outputs/tests/`,
`outputs/dry_run_extraction_system_comparison/<stamp>/` and `docs/run/`. `modal_all_tests.py` picks the two
test files up with the rest of the suite.
