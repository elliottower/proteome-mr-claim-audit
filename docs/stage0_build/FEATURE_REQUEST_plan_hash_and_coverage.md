# Requests for `prereg`, `results` and `repro`, from the dress rehearsal of 2 October 2026

Found while rehearsing the freeze, the ledger and the manuscript checks of this repository on a
scratch copy (`DRESS_REHEARSAL_2026-10-02.md`, same folder). Tool versions: `prereg`, `results`,
`repro` and `citations` as installed on PATH, and the `reproducible-science` main worktree at
`b078cb2`. Nothing here was patched in this repository; each item states what was done instead.

## 1. A plan pinned by its whole-file hash breaks at the next log line

`prereg log` appends to `PREREG.md`. Two tools pin the plan by the sha256 of the whole file:

- `results seal --role prereg PREREG.md`: after one `prereg log` line, `results verify --files`
  reports `CHANGED experiments/02_claims_meta/PREREG.md` and exits 1, permanently.
- `repro.yaml` with the plan as a pinned artifact and `runs[].registered_plan`: after one log
  line, `repro verify --policy strict` reports `artifact.pin` and
  `claim.ordering_unchecked.registered_plan_changed` for every confirmatory claim.

`prereg check` on the same file reports `unchanged`, correctly: its hash covers everything
above the log.

Wanted: for a file with a freeze header, `results seal --role prereg` and the `repro` artifact
pin use the hash `prereg` uses (the plan sha256 of the header, recomputed), so appending a log
line does not break the pin and editing the plan does.

Done here instead: `scripts/stage_record.py plan` writes the header's commit, plan sha256 and
date to `outputs/results_manifests/prereg_freeze.plan.json` after `prereg check` passes; that
file is sealed, and `stage_record.py verify` compares it with the header and reruns
`prereg check`.

## 2. `results coverage` cannot fail on two kinds of number

- **One significant digit.** `constraining_digits` below 2 is exempt, so `0.2`, `0.8`, `80%`
  and `5` owe no claim. A manuscript whose headline proportion is printed as `0.8` or `80%`
  passes `--strict` with the value unbound, and still passes after the value is changed to
  `0.3`. Seen: a two-sentence manuscript with `5`, `0.2`, `0.4`, `2`, `0.5` reported "no numbers
  in this manuscript owe a run" before and after an edit of `0.2` to `0.3`.
- **`%` in a non-TeX source.** `COMMENT` strips from an unescaped `%` to the end of the line in
  every format. In Markdown a paragraph is one line, so `63 (44.7%) entered the registry and 43
  entered …; share 0.25 … P = 0.031` counts `141, 63, 44.7` and drops every number after the
  percent sign.

Wanted: comment stripping only for `.tex`; a decimal fraction or a percentage never exempt for
its digit count; and a flag that lists the exempted values, so an exemption is visible.

Done here instead: the runbook says to print proportions to two decimals and to run coverage
on the `.tex` source.

## 3. `prereg log` without `--access` records `no results seen`

`prereg log "note"` succeeds and writes `no results seen`. The level is the field that
separates an amendment from a deviation; a default writes one nobody chose. Wanted: `--access`
required, as it is with `freeze --force`.

## 4. `results claim --frozen-at` accepts any commit

`--frozen-at` was given the commit that holds the freeze header rather than the commit the
header names. `results claim` accepted it and printed "plan frozen at … before outcomes were
seen". Only `repro check` reported "claims naming a freeze that no frozen plan records". Wanted:
`results claim` itself checks the commit against the `**Status:** FROZEN at` line of a plan in
the repository, or accepts either of the two commits a freeze produces.

## 5. A plan that will never be frozen fails the repository's `prereg check`

A parked plan named `PREREG.md` (`experiments/01_census/`) made `prereg check` at the root
report `2 plans: 1 unchanged, 0 changed, 1 not frozen` and exit 1, and `repro check` report
`prereg FAILED`. Wanted: a status the tool reads as withdrawn (`**Status:** PARKED`), reported
on its own line and not counted as a failure. Done here instead: the file was renamed.

## 6. `prereg check` does not read two header lines

Editing the commit in `**Status:** FROZEN at` or the date in `**Frozen:**` leaves `prereg check`
at `unchanged`. The skill says those lines are skipped by the hash; the check could still
confirm that the named commit exists and holds a plan with the recorded hash.

## 7. Smaller points

- `results verify --files` does not notice a ledger whose last line and `ledger.head` were both
  rewritten consistently; only the git history of `.results/` does. Worth one sentence in the
  skill.
- `results run` takes files, not folders. A stage here writes thousands of files, or writes on
  a Modal volume, so `scripts/stage_record.py` records one manifest per stage and rehashes the
  files itself. A native folder manifest would remove the second verify command.
