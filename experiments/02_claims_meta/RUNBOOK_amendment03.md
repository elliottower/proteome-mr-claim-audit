# RUNBOOK for stages 4L and 5L under Amendment 3

This file replaces the stage 4L and 5L steps of `RUNBOOK.md` (Amendment 1 section), which stays as it
was. Commands run from `experiments/02_claims_meta`. `<lrev>` is `e4e4ee731887`; `<rev>` is
`0b97103cd7a4`; `<label>` is each of `search`, `chase1`, `chase2`, `chase3`.

Nothing below runs before the log of `PREREG.md` names the sha256 of
`AMENDMENT_03_extraction_comparison_verification.md` and before the OSF update for Amendment 3
is filed and approved.

## Abstracts files

| extraction label | abstracts file of Sol's and Luna's span step | abstracts file of the second Sol run |
|---|---|---|
| search | `outputs/parsed/sol_eligibility_search_complete_2811496ef424.decisions.eligible_abstracts.jsonl` | `outputs/parsed/sol_eligibility_search_complete_2811496ef424.decisions.repeat_sample.jsonl` |
| chase1 | `outputs/parsed/sol_eligibility_gateall1_2811496ef424.decisions.eligible_abstracts.jsonl` | `outputs/parsed/sol_eligibility_round1_all_2811496ef424.decisions.repeat_sample.jsonl` |
| chase2 | `outputs/parsed/sol_eligibility_chase2_2811496ef424.decisions.eligible_abstracts.jsonl` | `outputs/parsed/sol_eligibility_round2_all_2811496ef424.decisions.repeat_sample.jsonl` |
| chase3 | `outputs/parsed/sol_eligibility_gateall3_2811496ef424.decisions.eligible_abstracts.jsonl` | `outputs/parsed/sol_eligibility_round3_all_2811496ef424.decisions.repeat_sample.jsonl` |

The first column holds the abstracts the registered Sol span step used (same sha256 as recorded
in `outputs/verification_occurrence/sol_extraction_<label>_<rev>/span_step_run.json`).

## Stage 4L, span step (occurrence-aware, every compared file)

For each Luna run `<k>` in 1, 2 and each label, and for each second-Sol-run file:

    modal run --detach scripts/modal_verify_spans_occurrence.py::span_step \
        --extraction outputs/parsed/luna_extraction_<label>_run<k>_<lrev>.jsonl \
        --abstracts <first column>
    modal run --detach scripts/modal_verify_spans_occurrence.py::span_step \
        --extraction outputs/parsed/sol_extraction_<label>_repeat_<rev>.jsonl \
        --abstracts <second column>

Results in `outputs/verification_occurrence/<stem>/`. `scripts/span_restoration_v2.py` is not run.

## Stage 4L, claim verifier (whitespace-safe copy)

    modal run --detach scripts/modal_verify_claims_amended.py::verify_claims --label amendment03 \
        --extraction outputs/parsed/<stem>.jsonl --spans-folder outputs/verification_occurrence/<stem>

for the eight Luna files and the four second-Sol-run files. Results in
`outputs/verification_amendment02/amendment03/<stem>/` (the wrapper's own folder name).

## Stage 4L, assemblies

    modal run --detach scripts/modal_amendment03_comparison.py::assemble --source comparator_check
    modal run --detach scripts/modal_amendment03_comparison.py::assemble --source luna_run1
    modal run --detach scripts/modal_amendment03_comparison.py::assemble --source luna_run2
    modal run --detach scripts/modal_amendment03_comparison.py::assemble --source sol_repeat

The first reassembles the Sol comparator from the inputs the wrapper names and stops unless it
equals `outputs/registry/2026-10-03_registered_with_27_coded_a` byte for byte; the others refuse
to run until it has passed. Results in
`outputs/extraction_system_comparison/amendment03_originally_registered/<source>_registry/`.

## Stage 5L, usage

With `<out>` = `outputs/extraction_system_comparison/amendment03_originally_registered`:

    uv run scripts/extraction_system_comparison.py usage --role sol \
        --raw outputs/raw/sol/extraction/<rev> \
        --parsed <the four outputs/parsed/sol_extraction_<label>_<rev>.jsonl> --out <out>/usage_sol.json
    uv run scripts/extraction_system_comparison.py usage --role luna_run<k> \
        --raw outputs/raw/luna/extraction/<lrev>/run<k> \
        --parsed <the four outputs/parsed/luna_extraction_<label>_run<k>_<lrev>.jsonl> \
        --out <out>/usage_luna_run<k>.json

## Stage 5L, comparison

    modal run --detach scripts/modal_amendment03_comparison.py::compare \
        --rule-label originally_registered \
        --sol outputs/registry/2026-10-03_registered_with_27_coded_a/registry_claims.jsonl \
        --sol-tables outputs/stage5_biology/2026-10-03_registered_with_27_a/sensitivity_tables.json

It fails unless the rule label, the Sol registry and the Sol tables are the originally
registered analysis's, by path and sha256; then reproduces the Sol primary table and fails
unless it equals the `primary` entry; then runs the comparison with checkpoints on the volume.
Result: `<out>/extraction_system_comparison.json` and `<out>/comparison_run.json`.

## Results ledger

| stage | run id | folders |
|---|---|---|
| 4L | `a3_verification_2026-10` | `outputs/verification_occurrence/luna_extraction_*`, `outputs/verification_occurrence/sol_extraction_*_repeat_*`, `outputs/verification_amendment02/amendment03/` |
| 4L, 5L | `a3_extraction_system_comparison_2026-10` | `outputs/extraction_system_comparison/amendment03_originally_registered/` |

## Tests

    modal run scripts/modal_amendment03_comparison.py::tests

runs `tests/test_extraction_system_comparison_checkpoints.py` and
`tests/test_extraction_system_comparison.py` on Modal and saves the output under `outputs/tests/`.
