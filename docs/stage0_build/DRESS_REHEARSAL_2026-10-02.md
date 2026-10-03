# Dress rehearsal of the freeze, the ledger and the manuscript checks

2 October 2026. The whole lifecycle of `prereg`, `results`, `citations` and `repro` was run on
two scratch copies of this repository, built from the path list of the first commit, before
anything was committed or frozen here. The real repository was not committed, frozen, sealed,
pushed or sent to OSF. No in-window record, claim or pair was read: the stage commands ran on
the stored pre-2019 smoke search, the cached exchanges of the 30 pre-2019 development
abstracts, and the synthetic registries of the dry runs. No GPT-6.1 Sol request and no search
request was made (the runner reported 0 new requests on both tasks).

The numbers in this file are counts of files, tests and tool events of the rehearsal; none is
a result of the study, and the phrases quoted are tool output.

Tools: `prereg`, `results`, `citations`, `repro` as on PATH; the reproducible-science main
worktree at `b078cb2` where named; Modal client 1.4.3. Commits in the scratch copies were
signed with the configured key (`%G?` = `G`).

## What the rehearsal found, and what was done

| # | found | where | done |
|---|---|---|---|
| 1 | 22 CSV tables end their lines with CRLF, and the machine's git setting `core.autocrlf=input` stores them with LF. A clone would hold bytes whose sha256 differs from RELEASES.md and from every seal (`therapeutic_areas.csv`: working file `31f61cda…`, stored blob `4662c706…`). | first `git add` | `.gitattributes` with `* -text` at the repository root. In a clone of the second scratch copy, `results verify --files` passed on all 117 sealed and recorded files. |
| 2 | The runbook sealed `PREREG.md`. `prereg log` appends to it, so after one log line `results verify --files` reported `CHANGED … PREREG.md` and exited 1, for good. | seal step | `scripts/stage_record.py plan` writes the header's commit, plan sha256 and date to `outputs/results_manifests/prereg_freeze.plan.json` after `prereg check` passes; that file is sealed and `stage_record.py verify` checks it against the header. In the second rehearsal a log line after the seals left both checks passing. |
| 3 | `--frozen-at` was given the commit holding the freeze header. `results claim` accepted it; `repro check` listed five "claims naming a freeze that no frozen plan records". The commit to cite is the one the `**Status:**` line names (the commit before the header commit). A claim citing it was not listed. | claim step | Runbook: `--frozen-at` takes `frozen_at_commit` of the plan record. |
| 4 | The parked census plan `experiments/01_census/PREREG.md` made `prereg check` at the root report `1 not frozen` and exit 1, and `repro check` report `prereg FAILED`. | `repro check` | Renamed to `PARKED_PLAN_v6_never_frozen.md`; `PARKED.md` says why. Root `prereg check` then exits 0 in the scratch copy. In the working copy the tool also read a packet copy of the parked plan under the ignored `planning/` folder; that copy was renamed too, and the root check now reads the one plan. |
| 5 | Stage 4 as written ran `verify_claims.py` locally with no command for the pinned files, although the runbook's first paragraph sends every reader of a pinned file to Modal. | stage 4 | New entrypoint `modal_biology_joins.py::verify_claims`: runs the script against the volume's HGNC, UniProt, MONDO and EFO files, stores the verification folder and the two results under `/02_claims_meta/stage4/<extraction stem>/`, copies the results back. Run once on the development extraction: 141 claim records, local folder equal to the volume folder (5 files). |
| 6 | `assemble_registry.py` failed in the scratch copy: it reads the HGNC and UniProt files, which a clone does not hold, and it did not check their sha256. | stage 4 | `build_registry.pinned_file` refuses a missing file or one whose sha256 differs from `reference/MANIFEST.json`; the runbook gives the two `modal volume get` lines (20 MB). |
| 7 | The ledger table named `outputs/citations/<run>` and `outputs/verification/<run>`; the folders are `…/sol_extraction_<label>_<rev>`. | record step | Table corrected; a stage-4 record line added. |
| 8 | `run_extraction.py` and `apply_eligibility.py` replaced an existing parsed file without a word; the runbook says every script refuses. Six other scripts refused when rerun (`assemble_screening_set`, `keyword_prefilter`, `claim_tags`, `assemble_registry`, `verify_spans`, `sample_repeat_run`); the rest carry an existence check that was read, not run. | reruns | Both refuse now. |
| 9 | `sensitivity_tables.json` is written on Modal and was recorded without being compared with the volume file (the two maps cover folders only). | stage 5 record | `--volume-map` takes one file; the runbook line maps it. |
| 10 | The runbook had no freeze procedure, no retry for a failed OSF upload, and no way to fetch a Modal result when the local copy step is lost. | reading | Section "At the freeze"; recovery lines under stage 5. |
| 11 | `results coverage --strict` passed a manuscript whose numbers were `5, 0.2, 0.4, 2, 0.5`, and still passed after `0.2` became `0.3`: values with one significant digit owe no claim. In Markdown it drops everything after a `%` on the line. | coverage step | Runbook: print proportions to two decimals; run coverage on the `.tex`. Reported to the tools session (`FEATURE_REQUEST_plan_hash_and_coverage.md`). |
| 12 | A `repro.yaml` pinning the plan by whole-file sha256 passed `--policy strict`, then failed after one `prereg log` line (`registered_plan_changed`). | repro step | Runbook note; same request. |

Fixes carry tests: 593 pass on Modal with the three synthetic dry runs
(`outputs/tests/pytest_all_modal_20261002T192344Z.txt`), and 12 deliberate removals of the new
guards each made a test fail (`mutation_check_dress_rehearsal.json`).

## Rehearsal 1, step by step

Scratch copy: 2,231 paths, 51 MB.

**1. Commits.** `git init`; `git add --pathspec-from-file` of the list; commit of everything
but the plan; commit of `PREREG.md` alone. Both signed. Finding 1 arose here.

**2. Freeze.** `prereg check` before: `not frozen`, exit 2. `prereg freeze` (no `--osf`):
header written, `commit eeb885645205`, plan sha256 `3b56787175c1a239…`, `Log: 41 entries`.
Header committed. `prereg check`: `unchanged`, exit 0.

`prereg log` at each level (`nothing run`, `no results seen`, `results not opened`,
`results seen`): each logged; the last adds "Recorded as a deviation". An invalid level exits
1. A line with no `--access` is logged as `no results seen`.

| edit after the freeze | `prereg check` |
|---|---|
| one character in a hypothesis | `CHANGED`, exit 1 |
| one character in the paragraph under the title | `CHANGED` |
| the plan sha256 in the header | `CHANGED` |
| an earlier log line's access level | `LOG ALTERED`, exit 1 |
| a log line removed | `LOG ALTERED` |
| the commit in `**Status:**` | `unchanged` (not read) |
| the date in `**Frozen:**` | `unchanged` (not read) |

A second `prereg freeze` is refused ("already frozen"). The second rehearsal's freeze of the
same text at another commit gave the same plan sha256.

**3. Ledger.** The four seal lines of the runbook ran as written (finding 2 on the first).
`results access` with a placeholder level was recorded; an invalid level is refused.

Stage commands run, each recorded with `stage_record.py record`:

| stage | commands run | data | ledger run |
|---|---|---|---|
| 1 | `assemble_screening_set.py`, `keyword_prefilter.py` | stored pre-2019 smoke search (43 source records, 23 screening records) | `s1_search_2026-10-01`, 25 files |
| 2 | `run_extraction.py --task eligibility`, `apply_eligibility.py` | 30 development abstracts, cached exchanges, 0 requests | — |
| 3 | `run_extraction.py --task extraction`, `sample_repeat_run.py` | same, 0 requests | — |
| 4 | `verify_spans.py` (129 spans pinned, 67 s), `verify_claims` on Modal, `claim_tags.py`, `assemble_registry.py` | development extraction | `s4_verification_zzrehearsal`, 86 files, 5 compared with the volume |
| local dry run | `dry_run_synthetic.py` | invented records | `zzrehearsal_synthetic_registry`, 6 files |
| 5 | `modal_biology_joins.py::joins` (confirmatory, update), `::sensitivity`, `modal_drug_joins.py::joins` | synthetic registry of the biology dry run; synthetic claims | `s5_biology_zz_rehearsal_20261002` (34 files, 16 + 16 compared), `s5_drug_zz_rehearsal_20261002` (4 files, 3 compared) |

`results verify --files` and `stage_record.py verify` after tampering:

| edit | `results verify --files` | `stage_record.py verify` |
|---|---|---|
| a table recorded with `--file` | `CHANGED`, exit 1 | raises |
| a file named only in a manifest | not reported | raises |
| a manifest-named file deleted | not reported | raises |
| a sealed input (`dataset_dictionary.csv`) | `CHANGED`, exit 1 | — |
| a sealed script (the wrapper edited for finding 5) | `CHANGED` | — |
| a manifest | `CHANGED` | — |
| a ledger line's access level | `CHAIN EDITED`, exit 1 | — |
| the last ledger line removed | `CHAIN TRUNCATED`, exit 1 | — |

No edit passed both. The two commands cover different files, so both are run.

**4. Manuscript.** Two-sentence manuscript with numbers of the synthetic run.

- `results claim … --confirmatory --frozen-at <commit>`: recorded. Unknown run id: refused.
  A `--frozen-at` that is not a commit: refused.
- After `results access --level "outcomes seen"`, a confirmatory claim on a run recorded later
  is refused without `--frozen-at`, and with it is recorded as "confirmatory, exposure logged".
- `results coverage --strict`: finding 11 on the first manuscript. With `11`, `0.25`, `0.75`:
  exit 1 before binding, exit 0 after three claims, exit 1 after `0.25` became `0.35`.
- `repro verify`: three metric assertions verified. A reported value changed: `MISS`, exit 1.
  A pointer that does not resolve: `GONE`, exit 1. The artifact edited: `broken_pin`, exit 1.
  With a run record and the plan pinned: `--policy strict` passed; finding 12 after a log line.
- `repro check`: findings 3 and 4, and `citations FAILED` in a copy without `sources/`.

**5. Quotations.** `citations verify --claims claims/` without `sources/`: 5,470 unchecked,
exit 1 ("nothing was measured"). With the source texts linked in: 5,470 found, 0 not found.
`citations coverage` on a `.tex` quoting one pinned sentence: covered, exit 0; with one digit
of the quotation changed: `UNCOVERED`, exit 1 under `--strict`.

**6. OSF dry run** on the frozen scratch plan (`osf_dry_run.py`, sends nothing): accepted, 23
answers, 105,557 bytes; no header line, log line or rehearsal text is in the draft. The longest
answer (Measured variables) is 43,174 characters.

## Rehearsal 2 (the corrected runbook)

Fresh scratch copy of 2,289 paths with `.gitattributes`. Three commits, `prereg freeze`,
`stage_record.py plan`, the four seal lines, the access line, one `prereg log` line, then:
`results verify --files` exit 0; `stage_record.py verify` prints `plan: ok`; `prereg check` at
the root: `1 plans: 1 unchanged`, exit 0. A `git clone` of that copy: `results verify --files`
exit 0 with 117 files `ok`, `prereg check` unchanged, plan ok, the 22 CRLF tables stored as
CRLF.

## What the frozen layout forbids afterwards

Everything above the `---` before `## Log`: the title, the paragraph under it, every section.
Log lines are added only with `prereg log --access`. The text under the title and the log are
not sent to OSF; the 23 answers are. The header lines are the tool's.

## Not rehearsed

- **The OSF upload.** The dry run builds the draft and sends nothing. Whether OSF accepts a
  43,174-character answer is known only from the upload; if it fails after the header is
  written, the runbook's retry applies.
- **Live search and model calls.** `run_search.py`, `citation_chase.py`,
  `fetch_known_item_abstracts.py --controls`, `fetch_fulltext.py`, and `run_extraction.py` on
  records with no cached exchange were not run. Their option parsing and guards were. A live
  `--smoke` pass (pre-2019 months, about 23 eligibility requests) would run stages 1 to 4 on one
  consistent set of records; it needs the author's word, since it calls the model on records
  not yet read.
- **Stage 4 from `select_eligible.py` on, on one consistent set.** The stored smoke search and
  the development abstracts are different papers, so `select_eligible.py` refused the pair
  (as it should), `assemble_registry.py` reported 141 claim records of other records and an
  empty registry, and `manual_dataset_coding.py`, `funnel.py`, `gate_audit.py`,
  `repeat_run_agreement.py`, `negative_control_specificity.py` and stage 6 were not run from
  the command line. Their tests and the three dry runs cover the logic.

## Left behind

- Modal volume: the two rehearsal folders (`/02_claims_meta/stage5/zz_rehearsal_20261002`,
  `/02_claims_meta/stage4/sol_extraction_zzrehearsal_0b97103cd7a4`) were removed.
  `/02_claims_meta/stage5/drug_index_c74d774497a1.json`, the drug index named by the hash of the
  code that builds it, stays; stage 5 reuses it.
- The scratch copies are in the session scratchpad and hold no real record.
