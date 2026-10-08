# Stage 5 run plan after Amendment 2 (written 8 October 2026; nothing here has been run)

Stage 5 opens H1, H2 and H2b. This note lists what the frozen plan requires before it, the exact
commands, and what must be decided or logged first. Paths are relative to
`experiments/02_claims_meta`. No registry file, relation or assembly summary was opened to write
it.

## The four assemblies

| label | folder under `outputs/registry/` | claim checks and extraction | manual codes |
|---|---|---|---|
| D+(a), amended primary analysis | `2026-10-03_amended_primary_coded_a` | 27 pinned, 37 restored | all (197) |
| D+(b) | `2026-10-03_amended_primary_coded_b` | as D+(a) | author-marked only (197; the same bytes as version a) |
| D+(c) | `2026-10-03_amended_primary_coded_c` | as D+(a) | none |
| A+(a), originally registered analysis | `2026-10-03_registered_with_27_coded_a` | 27 pinned, 37 excluded | all (196) |

The registry as first assembled (all 64 excluded, no codes) is `2026-10-03`; it is a column of
counts and gets no stage 5 run.

## What the frozen plan requires before stage 5

Read in `PREREG.md` (§Data collection procedures, §Indices, §Inference criteria, §Missing data,
§Other planned analysis) and `RUNBOOK.md` (stages 4 and 5):

- **No gate and no void condition stands before stage 5.** The inference criteria are the H2
  and H2b bounds against one half; H1 has no verdict. An estimate on fewer than 20 pairs is
  labelled imprecise and still reported. Repeat-run stability, negative-control specificity,
  the gate audits and the span verification rate are internal consistency checks that are
  reported; none stops or conditions the analysis.
- **Negative controls:** run once on 6 October (`outputs/negative_controls/`, run
  `controls_2811496ef424`). Nothing further.
- **Repeat-run stability:** the second Sol run on the 10% sample and the agreement files exist
  (`outputs/repeat_run/<label>/`, stage 3). Nothing further before stage 5.
- **Order of the comparison of Amendment 1:** stage 4L follows stage 4 and stage 5L follows the
  committed stage-5 tables of the primary registry. Neither precedes stage 5.
- **Full-text concordance (stage 6):** after the primary results are committed.
- **Before the joins, in the runbook's order:** `claim_tags.jsonl` copied into the coded folder;
  `record_metadata.py fetch` and `build`; `funnel.py`; `author_lists.py decide`
  (`verification/author_supplied_lists.csv` is empty, so no list is supplied).
- **The H1 and H2 tables are the `primary` entry of the sensitivity run**, which also writes
  `without_manual_dataset_coding` and every other registered sensitivity table.

## Commands, per assembly `<R>` (the folder above) with run name `<N>`

With `<records>`, `<decisions>`, `<extraction>`, `<checks>` and `<codes>` the inputs the assembly
was built from, and `<screening sets>` the `screening_set.jsonl` of the search and of each round:

    cp outputs/registry/<first assembly of the analysis>/claim_tags.jsonl outputs/registry/<R>/claim_tags.jsonl
    uv run scripts/record_metadata.py fetch --inputs outputs/registry/<R> \
        --screening outputs/screening/2026-10-03/screening_records.jsonl \
        --chase-screening outputs/screening/chase_round_{1,2,3}/screening_records.jsonl
    uv run scripts/record_metadata.py build --inputs outputs/registry/<R> --screening <...> \
        --chase-screening <...> --openalex outputs/raw/openalex_metadata/<R>
    uv run scripts/funnel.py --screening-dir outputs/screening/2026-10-03 \
        --screening-dir outputs/screening/chase_round_{1,2,3} --decisions <decisions> \
        --extraction <extraction> --spans <spans.jsonl of each file> --checks <checks> \
        --assembly outputs/registry/<R> --out outputs/funnel/<N>
    uv run scripts/author_lists.py decide --inputs outputs/registry/<R> \
        --ledger "$(git rev-parse --show-toplevel)/.results/ledger.jsonl"
    modal run --detach scripts/modal_biology_joins.py::joins --inputs outputs/registry/<R> \
        --abstracts <screening sets> --run-name <N>
    modal run --detach scripts/modal_biology_joins.py::joins --inputs outputs/registry/<R> \
        --abstracts <screening sets> --run-name <N> --window update
    modal run --detach scripts/modal_biology_joins.py::sensitivity --records <records> \
        --decisions <decisions> --extraction <extraction> --checks <checks> --run-name <N> \
        --chase-records <chase search_records.jsonl> --manual-codes <codes>
    modal run --detach scripts/modal_drug_joins.py::joins \
        --claims outputs/registry/<R>/registry_claims.jsonl \
        --wording outputs/registry/<R>/claim_tags.jsonl --run-name <N>

What each writes: `record_metadata.jsonl` into `<R>`; `outputs/funnel/<N>/`; `author_list_decisions.json`
into `<R>`; `outputs/stage5_biology/<N>/confirmatory/` and `/update/` (registry indices, registry
secondaries, pathway enrichment and the other biology joins); `outputs/stage5_biology/<N>/sensitivity_tables.json`
(H1, H2 and H2b in `primary`, and every sensitivity table); `outputs/stage5_drug/<N>/` (three
`drug_*` files). Each Modal job writes on the volume and commits before it returns; a run name
is used once.

Proposed run names: `2026-10-03_amended_primary_a`, `_amended_primary_b`, `_amended_primary_c`,
`2026-10-03_registered_with_27_a`.

Proposed scope: every command for D+(a) and A+(a), the two analyses whose main estimates the
paper shows together; for D+(b) and D+(c) the sensitivity run only (H1, H2, H2b), the joins and
drug joins being secondary outcomes.

## To decide or log before stage 5 runs

1. **The joins print outcome content.** `modal_biology_joins.py::joins` prints the summaries
   of its results, and `sensitivity` writes the H tables locally. Whoever runs stage 5 opens
   the outcomes; the access goes in the ledger at "outcomes seen" and the labels of Amendment 2
   are already fixed.
2. **OSF.** Amendment 1 was filed on OSF before its stage ran. Amendment 2 is logged and
   committed and is not yet filed on OSF.
3. **D+(b) equals D+(a).** With every coded row marked, version b is the same file as version
   a. Decide whether D+(b) gets its own stage-5 run (the same tables twice) or is reported as
   identical by the byte comparison of its inputs and of its assembly.
4. **D+(c) and `without_manual_dataset_coding`.** The sensitivity run of D+(a) already writes
   the table without manual codes. A separate run of D+(c) should reproduce it; decide whether
   to run it as a cross-check or to report the registered table alone.
5. **One metadata fetch for four folders.** `record_metadata.py fetch` stores OpenAlex responses
   per coded folder. The families are the same in all four assemblies, so one fetch could serve
   all four; using one folder of responses for several builds departs from the runbook and
   needs a log line, or the fetch is repeated per folder.
6. **Stages 4L and 5L (Amendment 1) under Amendment 2.** The Luna files and the Sol repeat run
   have not had their span check or assembly. Amendment 2 fixes the tool build, the
   first-occurrence pin and the restoration for the registered Sol extraction only. Whether the
   Luna and repeat-run records get the same span step (corrected build, first occurrence,
   restoration), and which Sol registry the comparison reads (amended primary or originally
   registered), is not written anywhere. Applying Amendment 2's rules to another extraction
   system, or declining to, is a rule and wants a review round before 4L runs. It does not
   block stage 5.
7. **The 14 rows the machine gate refused** stand unresolved; no decision changes them.
8. **`results verify --files`** exits non-zero for one test file recorded as resealed on
   7 October. No stage-5 script reads that result.
9. **Local assembly time.** An assembly with codes took between 9 and 26 minutes of one core on
   the author's laptop while other sessions loaded it (about 5 minutes for the assembly without
   codes). The sensitivity run does its own assemblies on Modal.
