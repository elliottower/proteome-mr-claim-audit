# Amendment 3: verification rule for the extraction-system comparison

Amendment to `PREREG.md` (frozen at `02bb006f3e55`, which is `82fb024ef0ac` after the history
rewrite of 8 October 2026; plan sha256
`9f06131af9936cc7c3556e87d77dcec65d034e4665be023eedf39948082d417b`; registered at
https://osf.io/zae8c). Date: 11 October 2026. Access level at the time: results seen. It takes
effect when the log of `PREREG.md` names the sha256 of this file. Nothing of stage 4L or 5L runs
before that, and before the OSF update for this amendment is filed and approved.

It concerns stages 4L and 5L of Amendment 1 only. It changes no registered result of Paper 1 and
no result of Amendment 2.

## What is not settled without it

Amendment 1 (6 October) has each Luna extraction file and the second Sol run on the stability
sample pass `verify_spans.py` and `verify_claims.py` unchanged. Amendment 2 (8 October) changed
the Sol span step: a corrected build of the quotation tool; the 27 spans that stand twice in the
stored abstract pinned at their first occurrence; the 37 spans that leave out one token restored
from the stored abstract as the amended primary analysis, with the originally registered
analysis (the 37 excluded) beside it. Amendment 2 concerns the 14,053 Sol claim records. Its
restoration script stops unless the eligible records are the 37 Sol record ids. Neither
amendment says whether the Luna files take Amendment 2's span rules, or which of the two Sol
analyses is the comparator of stage 5L.

## The rule

Stages 4L and 5L use one downstream rule for every compared extraction source: Luna run 1, Luna
run 2, the second Sol run on the stability sample, and the Sol comparator.

- A verbatim span that stands more than once in its stored abstract is pinned at its first
  occurrence under the occurrence-aware build of the quotation tool (`citations` 0.5.1 at
  commit `fb89bb6104be091585f87c8d1a35aa2fd2c44b74`), as in Part 1 of Amendment 2. The pass
  condition is the registered one: the quote check and a pin that is found.
- A span that fails the registered verbatim quotation check is excluded.
- The one-token restoration of Amendment 2 (Part 2) is not applied in the comparison.

Luna run 1, Luna run 2 and the second Sol run are compared with the Sol originally registered
analysis. That analysis includes the 27 spans that stand twice and excludes the 37 spans that
leave out one token. The amended primary analysis remains the primary analysis of Paper 1. It is
not the comparator of Amendment 1.

The reason for one rule is that the comparison varies the extraction system and holds the
downstream inclusion rule fixed. The restoration rule of Amendment 2 was written after the
classes of the Sol failures were seen. Applying a generalized version of it to Luna would apply,
to one side of the comparison, a rule developed on the other side's failures. Pinning the first
of two identical occurrences repairs the pinning of a span that is already verbatim, and does
not change what counts as verbatim.

## Implementation

| step | what runs | file |
|---|---|---|
| span step, every compared file | the occurrence-aware span checker, unchanged, on Modal in parts of 40 rows | `scripts/modal_verify_spans_occurrence.py` running `scripts/verify_spans_occurrence.py` |
| restoration | not run; `scripts/span_restoration_v2.py` is not called | — |
| claim verifier, Luna and second Sol run | the whitespace-safe copy of the registered verifier (the departure of 7 October), unchanged | `scripts/modal_verify_claims_amended.py` running `scripts/verify_claims_whitespace.py`, label `amendment03` |
| assemblies | the registered assembly script, unchanged, with the records, eligibility decisions and code table (version a) of the originally registered analysis | `scripts/modal_amendment03_comparison.py::assemble` running `scripts/assemble_registry.py` |
| comparator check | the comparator is reassembled from the inputs named in the wrapper and must equal `outputs/registry/2026-10-03_registered_with_27_coded_a` byte for byte (`registry_assembly.json` apart from its time stamp) before any other source is assembled | `scripts/modal_amendment03_comparison.py::assemble --source comparator_check` |
| comparison | the registered comparison script, unchanged, inside checkpoints that store each agreement block and each H1/H2 table on the volume as it is computed | `scripts/modal_amendment03_comparison.py::compare` with `scripts/extraction_system_comparison_checkpoints.py` |

**Comparator assertion.** Before anything is computed, the comparison fails unless the rule label
is `originally_registered` and the Sol registry and the Sol table passed are these files, each by
path and sha256, whatever is passed as `--sol` or `--sol-tables`:

| role | path | sha256 |
|---|---|---|
| Sol registry | `outputs/registry/2026-10-03_registered_with_27_coded_a/registry_claims.jsonl` | `faba35bd4cbe135f56761d2eec7d6ff92d446d1c6bef149615afda7f1f5de381` |
| Sol table | `outputs/stage5_biology/2026-10-03_registered_with_27_a/sensitivity_tables.json` | `42758a3ca1ef0993b6559762990f32bd0c1e39aa8892fe7595d036b43092908c` |

Both are recorded in the results ledger (seal of the registry, ledger sequence 250; run
`s5_biology_2026-10-03_registered_with_27_a`, sequence 253). The code table of the assemblies is
`outputs/manual_coding/2026-10-03_registered_with_27/final_codes_every_coded_row_marked/manual_dataset_codes.csv`
(sha256 `d8332c0a9c88a577de35203c58edd7728450d19289b3e4f48430550e47a94430`, sequence 251).

**Primary table first.** The comparison then computes the Sol H1, H2 and H2b tables from the Sol
registry and stops unless they equal the `primary` entry of that Sol table, key for key. Only then
does it compute the comparison.

**Runbook.** `RUNBOOK_amendment03.md` gives the commands. The 4L and 5L steps of `RUNBOOK.md` are
not followed and that file is not edited.

## Reporting

As in Amendment 1: one supplement table headed "Extraction-system comparison", nothing in the
abstract, no threshold classification for the Luna-derived registries, and no difference
attributed to the model alone. The table names its Sol comparator as the originally registered
analysis. The main text and the limitation state that the comparison used the strict registered
quotation rule for every extraction source, with duplicated verbatim spans pinned at their first
occurrence and source-restored spans excluded. They also state that the Sol comparator differs
from the paper's amended primary registry by the source-restored claim records, and when the
rule was fixed.

## Foreknowledge

The rule was fixed after the Sol results were known, but before any Luna claim content,
span-verification result, registry entry or comparison quantity was inspected.

- Known: the H1, H2 and H2b results of the amended primary and of the originally registered Sol
  analyses (stage 5, 8 October), which give the same registered verdicts.
- Known: that stage 3L ran on 7 October, with its completion and failure counts: in each of runs 1
  and 2, 2,363 of 2,363 abstracts answered and valid at the first attempt, one failed exchange in
  run 1 that the runner retried, and no `extraction_failed`.
- Not known: any Luna claim record, any span-check or claim-check result of a Luna file or of
  the second Sol run, any Luna-derived registry entry, and any quantity of the comparison.

## Files

| file | sha256 |
|---|---|
| `scripts/extraction_system_comparison_checkpoints.py` | `844bf14ef5665a4790730dfc1439224bf51a4f914f6db970a37ad219014623a6` |
| `tests/test_extraction_system_comparison_checkpoints.py` | `e160445ff04bd0666d8134007029a31f737d72e4052d5afaef77dd862cba29d8` |
| `scripts/modal_amendment03_comparison.py` | `b8fc2c7aed8d904c3e92248d236368e392c713322cf83821e424bc2c57c10f23` |
| `RUNBOOK_amendment03.md` | `236d0347af52c01df95d884942a673ffd09afd7519b9a7a352359c55c166a4db` |
| `scripts/modal_verify_spans_occurrence.py` (sealed under Amendment 2, unchanged) | `c3f1b8808cdc6f4d4a1ab5cc47d76f88a99913bd737b0ab7925a3966e391087b` |
| `scripts/verify_spans_occurrence.py` (sealed, unchanged) | `bd99dda3e18fa9747731d9ec2f09479267a62cbf86ea111df640bf470f15a8d3` |
| `scripts/span_shards.py` (sealed, unchanged) | `cc010308136078f54977121fdcea530f7d1c4dd1baac37fded8ff5d1bddbac56` |
| `scripts/modal_verify_claims_amended.py` (sealed, unchanged) | `ba4514c919940fa7b58aea3ffddf432ca60a17e8ac15ee08bc43d10d1ea9037f` |
| `scripts/verify_claims_whitespace.py` (sealed, unchanged) | `b217f93059d0dd7cb327de0c7df8a0ecc77b5ff6e514e4c1b89659a5f8157c7d` |
| `scripts/assemble_registry.py` (registered, unchanged) | `c1f95f08e34a9c2c011f761a85b37ef39109692d6e1e77148345a6513ca3f485` |
| `scripts/extraction_system_comparison.py` (sealed under Amendment 1, unchanged) | `1f7ec3e8f6e37380c9b43be4ea9a4307997cd612d0c46a3b15e595b827a9624f` |
| `scripts/sensitivity_checkpoints.py` (sealed, unchanged; its fingerprint is reused) | `5cca7af8aba8bf52692f0970ac7fa4c672a589779eea7c7fde08de5d6d25e735` |

Tests on Modal (`modal run scripts/modal_amendment03_comparison.py::tests`, 20261011T171104Z):
46 passed. They comprise the 14 tests of the checkpoints and the comparator assertion and the 32
existing tests of the comparison script. The cases include a checkpointed run equal to the plain
run, a resumed run, a failed call that stores nothing, and eight failure cases of the comparator
assertion: the amended registry, the amended table, a changed registry, a changed table, swapped
roles, another rule label, a missing rule label, and the registry passed as the table.

Reviewed externally in one round (`planning/perplexity_paper1_luna_span_rules_round1/`, outside
the repository).
