# Live smoke run on records first public before 2019, 2 October 2026

One pass of stages 1 to 6 from the command line on one live set, before the freeze. Label
`smoke_pre2019_20261002`. Counts are in `live_smoke_counts_2026-10-02.json`; the run is
recorded in the results ledger as eight runs named `smoke_pre2019_20261002_s<stage>...`. A
second pass the same day (last section) ran the gate audit and stages 4b to 6 with content;
its counts are in `live_smoke_second_pass_counts_2026-10-02.json` and its six ledger runs are
named there.

No record first public in 2019 or later was sent to GPT-6.1 Sol or read. One such record came
back in a chase response (PMID 30239796: OpenAlex dates it in 2018, PubMed on 2019-01-10). Its
abstract is in the stored OpenAlex and PubMed responses of the chase round and in the archived
first output of that round; it was not opened, is in no smoke screening set, and went to no
model.

## Window and set

The smoke window was 2018-06-01 to 2018-06-30, not the default November and December 2018: the
June window holds a paper known from prompt development to pass the eligibility prompt
(PMID 29875488), so one eligible family was certain at 18 eligibility calls.

| stage | count |
|---|---|
| search | 37 source records (PubMed 16, Europe PMC 8, OpenAlex 13), 18 screening records, all first public before 2019 |
| prefilter (search) | 0 of 18 marked |
| eligibility (search) | 17 ineligible, 1 `eligible_count_not_stated` |
| chase round 1 | 1 seed; 72 works referenced, 70 retrieved; 28 citing works; 98 new works; 1 left out (dated 2019 by PubMed); 97 screening records |
| keyword gate | 86 marked, 11 sent to screening |
| eligibility (chase) | 10 ineligible, 1 `uncertain` |
| extraction | 0 claim records (search record), 3 (chase record) |
| repeat run | 1 abstract sampled per label; 0 and 0 records; 3 and 3 records, 3 paired, every field equal |
| span check | 3 of 3 pass; `citations verify` exit 2 on the file with no claim ("nothing to check") |
| claim check (Modal) | 3 enter the registry, 0 enter direction results (direction `not_stated`) |
| registry | 114 records after 1 of kind `other`; 112 families; 2 fuzzy links (each a preprint and its article); 2 eligible families, both window `outside`; 3 claims with a pair, none in a registered window |
| manual coding | queue of 0 rows; an empty codes table passes `check` |
| record metadata | 2 records looked up, both found, both with a reference list |
| stage 5 | every table written on an empty confirmatory and update registry; H2 and H2b `no_multi_family_pairs`; 24 sensitivity tables |
| stage 6 | census: 2 families, both `no_open_access_full_text`; nothing to extract |

Requests: GPT-6.1 Sol 33 (29 eligibility, 2 extraction, 2 repeat extraction; 63,619 input
tokens, 7,113 output tokens); OpenAlex 8, with the key in the header; PubMed 7; Europe PMC 5.
No email address in any request; no key in any stored file (searched for both values).

## Commands, in order

From `experiments/02_claims_meta`, with `L=smoke_pre2019_20261002`, `R=2811496ef424`
(eligibility revision), `X=0b97103cd7a4` (extraction revision), `S=outputs/screening_smoke/$L`.

    uv run scripts/run_search.py --smoke --smoke-start 2018-06-01 --smoke-end 2018-06-30 --smoke-label $L
    uv run scripts/assemble_screening_set.py --run outputs/raw/search_smoke/$L --out $S
    uv run scripts/keyword_prefilter.py --screening-set $S/screening_set.jsonl
    uv run scripts/run_extraction.py --task eligibility --label $L --raw-root outputs/raw/sol_$L \
        --abstracts $S/screening_queue.jsonl
    uv run scripts/apply_eligibility.py --eligibility outputs/parsed/sol_eligibility_${L}_$R.jsonl
    uv run scripts/select_eligible.py --decisions outputs/parsed/sol_eligibility_${L}_$R.decisions.jsonl \
        --screening-set $S/screening_set.jsonl --screening-records $S/screening_records.jsonl
    uv run scripts/citation_chase.py --round 1 --smoke --smoke-label $L \
        --seeds outputs/parsed/sol_eligibility_${L}_$R.decisions.eligible_records.jsonl \
        --known $S/screening_records.jsonl
    uv run scripts/keyword_prefilter.py --gate --screening-set $S/chase_round_1/screening_set.jsonl
    uv run scripts/run_extraction.py --task eligibility --label ${L}_chase1 --raw-root outputs/raw/sol_$L \
        --abstracts $S/chase_round_1/screening_queue.jsonl
    uv run scripts/apply_eligibility.py ...chase1...; uv run scripts/select_eligible.py ...chase1...
    uv run scripts/run_extraction.py --task extraction --label $L|${L}_chase1 --raw-root outputs/raw/sol_$L ...
    uv run scripts/sample_repeat_run.py ...; uv run scripts/run_extraction.py --task extraction \
        --label <label>_repeat --raw-root outputs/raw/sol_${L}_repeat ...; uv run scripts/repeat_run_agreement.py ...
    uv run scripts/verify_spans.py --extraction ... --abstracts ...eligible_abstracts.jsonl      (twice)
    modal run --detach scripts/modal_biology_joins.py::verify_claims --extraction ...             (twice)
    uv run scripts/claim_tags.py --extraction <both extraction files> --out outputs/registry/$L
    uv run scripts/assemble_registry.py --records ... --decisions ... --extraction ... --checks ... \
        --out outputs/registry/$L
    uv run scripts/manual_dataset_coding.py queue ...; check ...   (empty codes table)
    uv run scripts/assemble_registry.py ... --manual-codes ... --out outputs/registry/${L}_coded
    cp outputs/registry/$L/claim_tags.jsonl outputs/registry/${L}_coded/claim_tags.jsonl
    uv run scripts/record_metadata.py fetch --smoke ...; uv run scripts/record_metadata.py build ...
    uv run scripts/funnel.py ... (search and chase: refused; search alone: written)
    modal run --detach scripts/modal_biology_joins.py::joins ...            (confirmatory, update)
    modal run --detach scripts/modal_biology_joins.py::sensitivity ...
    modal run --detach scripts/modal_drug_joins.py::joins ...
    uv run scripts/fetch_fulltext.py --census --before 2019-01-01 ...
    modal volume put ...; modal run scripts/modal_hash_volume.py::tree ...  (three listings)
    uv run scripts/stage_record.py record ...                              (eight runs)
    results verify --files; uv run scripts/stage_record.py verify          (all ok)

## What broke, and the fix

1. **`verify_spans.py` crashed on every screening-set abstract file** (`KeyError:
   'abstract_sha256'`). It required a recorded digest that only the development abstracts and
   the rendered full texts carry, so stage 4 of the registered run would have stopped at its
   first command. Fix: the digest is compared when the record carries one. The claims file's
   `url` now follows the record id (PubMed, OpenAlex or Europe PMC preprint) instead of a PubMed
   address for every id. New `tests/test_verify_spans.py`.
2. **`claim_tags.py` could not be run as RUNBOOK said with more than one extraction file**: it
   takes one file and refuses an existing output, and no command concatenated the outputs. Fix:
   `--extraction` takes every file in one call; a record id in two files raises.
3. **The stage 5 joins took one abstracts file**, so the abstracts of chase-round records would
   not have reached the hub analysis. Fix: `--abstracts` takes the screening sets
   comma-separated, as the sensitivity entry point already does.
4. **RUNBOOK gaps**: no command copied `claim_tags.jsonl` into the coded registry; stage 6
   listed the development form of `fetch_fulltext.py` (`--pmid`) and placeholder arguments, not
   the census; the full-text claim check was shown as a local command although it reads the
   pinned files on the volume. All written out.
5. **The smoke chase retrieved a record of the registered window.** OpenAlex's date limit was
   on citing works only, and OpenAlex and PubMed can disagree on a date. Fix (smoke mode only):
   the limit is on cited works too, and a record whose first public date is after 2018 is left
   out of the smoke screening set and counted. The first output of the round is archived under
   `outputs/superseded/smoke_pre2019_20261002/`.
6. **Two scripts refused to run before the freeze with no smoke mode** (`record_metadata.py
   fetch`, `fetch_fulltext.py --census`). Added `--smoke` and `--before 2019-01-01`; each
   refuses a record first public in 2019 or later before any request.
   `fetch_fulltext.py` no longer overwrites a stored full-text XML that has other bytes.
7. **The smoke search window and folder were fixed constants**, so a second smoke run on one
   day would have resumed the first. Added `--smoke-start`, `--smoke-end` (between 2014-01-01
   and 2018-12-31) and `--smoke-label`; a resume with another window raises.

No registered rule changed. The suite on Modal: 667 pass, three synthetic dry runs pass
(`outputs/tests/pytest_all_modal_20261002T202200Z.txt`). Sixteen deliberate changes of the new
guards each made a test fail (`mutation_check_live_smoke.json`).

## What the first pass did not exercise

The gate audit and stages 4b to 6 with content were run in the second pass (below).

- **Gate audit.** Batch 1 of chase round 1 is the 86 marked records, so it needs 86
  eligibility calls; the run was capped at 60 calls in all and no script scales the batch. The
  audit, `select_eligible.py` with gate decisions, and the funnel of a chase round were not
  run. `funnel.py` refused the unfinished round as designed
  ("batch 1 has not been judged"), and ran on the search alone.
- **Stages 4b to 6 with content.** `assemble_registry.py` gives every family first public
  before 2019 the window `outside`, so the confirmatory registry, the manual-coding queue and
  every stage 5 table were empty. The commands, the Modal jobs, the volume comparison and the
  empty-input paths ran; the contents are covered by the synthetic dry runs only. Running them
  on live pre-2019 claims would need the window rule changed for a smoke run, which was not
  done.
- **Full-text extraction and concordance.** Neither eligible family has an open-access full
  text in Europe PMC, so stage 6 ended with the census. The full-text claim check on Modal has
  not been run on a full-text extraction file.
- **Chase rounds 2 and 3, negative controls, the external-list check, the update window with
  records, and `record_metadata.py country`.**

## Seen in passing

- With no coded dataset name, `registry_claims_without_manual_coding.jsonl` is not written and
  the joins report no `sensitivity_without_manual_dataset_coding` (it would equal the primary).
  RUNBOOK now says so.
- `citations verify --strict` exits 2 for an extraction file with no claim; `verify_spans.py`
  records the exit code and goes on.
- The hub analysis counts pleiotropic-locus names over every abstract passed with `--abstracts`
  (115 here, the whole of both screening sets), not over the eligible abstracts only.
- The fuzzy family link joined a preprint and its article twice and nothing else among 114
  records.

## Second pass: gate audit, and stages 4b to 6 with content

Same day, same label and screening sets. The author approved the gate audit (about 86
eligibility calls). No record first public in 2019 or later was fetched, read or sent to a
model: every one of the 86 gate-sample records has a first public date of 2018-12-19 or
earlier in the round's screening records, checked before the first request.

| step | count |
|---|---|
| gate audit, batch 1 | 86 marked records, all 86 judged: 83 ineligible, 3 `uncertain`; share 3 of 86, one-sided 95% upper bound 0.088; stopped at `every_marked_record_sampled` |
| the 3 positives | PMID 16325682 (no abstract), PMID 29966350 (an abstract of three characters), OpenAlex W4406537262 (no abstract); each answered `uncertain` on all three criteria |
| round selection | 4 records judged eligible or uncertain (1 from the screening queue, 3 from the gate sample) |
| extraction | 4 records, 3 new requests; 3 claim records, all from W2901567682; the 3 gate records give none |
| span and claim checks | 3 of 3 spans pass; 3 enter the registry, direction `not_stated` |
| registry (smoke window) | 114 records, 112 families, 5 eligible families, 3 claims with a pair (proteins P46531, P55103, P05121; outcome EFO:0003907); 4 eligible families with no named claim |
| manual coding | queue of 1 row (outcome dataset "UK Biobank", `release_ambiguous`, 5 candidate rows); `check` refuses a header-only codes table and the blank template; no row was coded, and the coded registry was assembled with a header-only table |
| record metadata | 5 records looked up in one OpenAlex request, all found, all with a reference list |
| funnel | search and chase round 1 together: 115 records sent to screening, 110 ineligible, 4 uncertain, 1 `eligible_count_not_stated`; gate audit finished |
| biology joins (Modal) | 3 claim records against the pinned files: reference screen 0 of 3 pairs matched; 3 proteins, 0 hubs; 3 of 3 proteins with a Reactome pathway, 30 density cells; 0 hierarchy relations; every secondary written |
| sensitivity tables (Modal) | 28 entries; `primary` 3 claim records; H2 and H2b `no_multi_family_pairs` (one family holds every pair) |
| drug joins (Modal) | 3 pairs, all matched to the index, 2 with a drug on the target, 3 `no_matching_trial_or_indication_record` |
| full-text census | 5 families: 3 `no_open_access_full_text`, 2 `version_unmatched`; nothing to extract |

Requests in this pass: GPT-6.1 Sol 89 (86 eligibility, 3 extraction; 146,044 input tokens,
10,571 output tokens); OpenAlex 1, with the key in the header; Europe PMC one record looked up
by the census. In the two passes together: 122 GPT-6.1 Sol requests on 115 records.

### Commands

With `L`, `R`, `X`, `S` as above and `W=${L}_window`:

    uv run scripts/run_extraction.py --task eligibility --label ${L}_gate1b1 --raw-root outputs/raw/sol_$L \
        --abstracts $S/chase_round_1/gate_sample_batch_01.jsonl                     # 86 calls
    uv run scripts/apply_eligibility.py --eligibility outputs/parsed/sol_eligibility_${L}_gate1b1_$R.jsonl
    uv run scripts/gate_audit.py --round-dir $S/chase_round_1 \
        --decisions outputs/parsed/sol_eligibility_${L}_gate1b1_$R.decisions.jsonl
    uv run scripts/select_eligible.py --decisions <gate decisions> <chase decisions> \
        --screening-set $S/chase_round_1/screening_set.jsonl \
        --screening-records $S/chase_round_1/screening_records.jsonl
    uv run scripts/run_extraction.py --task extraction --label ${L}_chase1gate --raw-root outputs/raw/sol_$L \
        --abstracts <...gate1b1...decisions.eligible_abstracts.jsonl>               # 3 new calls
    uv run scripts/verify_spans.py ...; modal run --detach scripts/modal_biology_joins.py::verify_claims ...
    uv run scripts/claim_tags.py --extraction <search file> <chase1gate file> --out outputs/registry/$W
    uv run scripts/assemble_registry.py <records, decisions (search, chase, gate), extraction, checks> \
        --smoke-label $L --out outputs/registry/$W
    uv run scripts/manual_dataset_coding.py queue ... --out outputs/manual_coding/$W
    uv run scripts/manual_dataset_coding.py check ...                (refused twice, as it should)
    uv run scripts/assemble_registry.py <the same> --manual-codes <header-only table> \
        --smoke-label $L --out outputs/registry/${W}_coded
    uv run scripts/record_metadata.py fetch --smoke ...; uv run scripts/record_metadata.py build ...
    uv run scripts/funnel.py --screening-dir $S --screening-dir $S/chase_round_1 ... --out outputs/funnel/$W
    modal run --detach scripts/modal_biology_joins.py::joins --inputs outputs/registry/${W}_coded \
        --abstracts <both screening sets> --run-name $W            (and --window update)
    modal run --detach scripts/modal_biology_joins.py::sensitivity ... --run-name $W --smoke-label $L
    modal run --detach scripts/modal_drug_joins.py::joins --claims ... --wording ... --run-name $W
    uv run scripts/fetch_fulltext.py --census --before 2019-01-01 ... --out outputs/fulltext/$W
    modal run scripts/modal_hash_volume.py::tree ...  (two listings); uv run scripts/stage_record.py record ...  (six runs)

In the round selection the gate decisions file was given first, so the selection was written
next to it and the first pass's selection of the round (recorded in the ledger) was not
replaced; RUNBOOK gives the round's file first. The repeat-run sample was not redrawn for the
second extraction file.

### What was added, and what broke

1. **Smoke-window switch** (`assemble_registry.py --smoke-label`, `scripts/smoke_guard.py`).
   Families first public before 2019 take the window `confirmatory`. It refuses a label that
   does not start with `smoke_`, any record first public in 2019 or later (eligible or not),
   and an output folder other than `outputs/registry/<label>...`; `registry_assembly.json`
   carries the label. The manual-coding queue, the funnel, the biology and drug joins and the
   full-text census refuse to write the results of a smoke registry under a name that does not
   start with the label, and refuse a smoke name for any other registry; the sensitivity run
   takes the label with a run name that starts with it. Each refusal was seen on the command
   line (a run name `run_x`, a label `run_x`, a folder `outputs/registry/run_x`, a sensitivity
   run without the label). No registered rule changed.
2. **Nothing in stages 4b to 6 broke on live content.** Every command of RUNBOOK ran as
   written once the switch existed.
3. **Stored tool outputs named the home folder.** `verify_spans.py` now writes the output of
   `citations verify` with paths relative to the experiment folder. Sixteen existing files
   were stripped (`HOME_PATHS_STRIPPED_2026-10-02.json`); the originals are kept locally and
   not committed. Three of them are named by ledger manifests and went through the new
   `stage_record.py replace`, which archives the original, writes the new bytes and records
   the replacement (`outputs/results_manifests/replaced_files.json`); `verify` accepts such a
   file only with exactly the replaced bytes. The volume copies of those three files keep the
   original bytes.

Tests on Modal: see RELEASES.md for the run. `mutation_check_smoke_window.json` holds the
mutation check of the new guards.

### Seen in this pass, for the author (no rule was changed)

- **A record with no abstract is judged `uncertain`, and the plan has no rule for it.** All
  three gate positives are records with an empty or three-character abstract. Under the
  registered rules an `uncertain` record goes to extraction (no claim comes back), becomes an
  eligible family (4 of the 5 families here have no named claim), seeds the next
  citation-chasing round (PMID 16325682 is a 2005 Lancet commentary, "Nature's randomised
  trials", whose cited and citing works round 2 would then retrieve), and counts as a positive
  of the gate audit. A first batch of 600 with one positive has a bound of 0.0079, so abstract-less
  records at this rate (3 of 86) would keep the audit drawing batches to the 3,000 cap in
  every round. In the main search they would also enter as `eligibility_uncertain` families.
  The sensitivity `without_eligibility_uncertain` removes them from the tables; nothing
  removes them from the chase seeds or the audit.
- **The one claim-bearing family is itself `uncertain`** (a 2018 preprint), so
  `without_eligibility_uncertain` and `without_citation_chasing` both give 0 claim records
  here.
- **Not exercised with live content:** a coded dataset name, a full-text extraction and its
  concordance (no open-access full text among the five families), chase rounds 2 and 3, the
  negative controls, the external-list check, the update window, `record_metadata.py country`,
  and any multi-family pair (H1, H2 and H2b need two families on one pair).

## Afterwards: the `no_abstract` rule (same day)

The first item of the list above is now a registered rule (PREREG v17b;
`NO_ABSTRACT_FLOOR_2026-10-02.md`): a record with no abstract of at least 200 characters is
classed `no_abstract` before the keyword prefilter and is not sent to the eligibility prompt.
The round was re-assembled under the rule from the stored responses and decisions, with no
request and no model call (`smoke_rerun_no_abstract_rule.py`; counts in
`smoke_rerun_no_abstract_rule_counts_2026-10-02.json`; outputs under
`smoke_pre2019_20261002_no_abstract_rule`): 3 of 115 screening records are `no_abstract`, 112
are judged, the gate audit has 0 positives in 83 sampled records, 2 records go to extraction
and 2 families are eligible, with the same 3 claim records. The three files of that rerun that
named the repository's folder on the author's machine were corrected through
`stage_record.py replace`; the funnel file is therefore recorded twice in the results ledger.
