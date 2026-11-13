# History rewrite of 8 October 2026

The commit history of this repository was rewritten on 8 October 2026, before the repository
was made public, to remove third-party text: abstracts and full texts of the papers the study
reads, API responses that carry them, and metadata holding authors' e-mail addresses. A few
files that recorded a local path, and two working-notes files, were removed with them.

## What changed and what did not

- Every commit hash changed, because a commit hash covers every file in the commit. The 85
  commits keep their order, messages, author dates and committer dates, and are signed with the
  same key.
- Every file that remains is byte-identical to the same file in the original commit. For each
  of the 85 commits, the file list of the rewritten commit equals the original list minus the
  removed paths.
- `COMMIT_MAP.tsv` gives the original and the rewritten hash of each commit.
- `WITHHELD_FILES.tsv` lists the 64,936 removed files with their size and sha256.

## Reading the records

The plan was frozen at original commit `02bb006f3e55`, which is `82fb024ef0ac` here. The plan
header, its log, both amendments and the results ledger name the original hash and are not
edited: the plan is frozen and the ledger is a hash chain. The registration does not depend on
the commit hash. `prereg check` compares the sha256 of the plan file
(`9f06131af9936cc7c3556e87d77dcec65d034e4665be023eedf39948082d417b`), which is unchanged, and the
OpenTimestamps proofs bind file bytes and ledger heads.

The tag `prereg-paper1-freeze-2026-10-03` points at the rewritten commit that corresponds to the
original tagged commit `c009e46f6257`.

The original signed history is kept by the author as a git bundle (sha256
`55473a4ed5bf1a910f361ecd39cad5040454530ab6bbd1cc1622e2fff6fa6e4c`).

## Checks that need the withheld files

The stage manifests under `experiments/02_claims_meta/outputs/results_manifests/` and the ledger
record a sha256 for each withheld file, and `WITHHELD_FILES.tsv` repeats them. In a clone of
this repository:

| check | result without the withheld files |
|---|---|
| `prereg check` | passes |
| `results verify` (the chain) | passes |
| `results verify --files` | reports the withheld inputs as missing |
| `uv run scripts/stage_record.py verify` | reports the withheld files as missing |
| `citations verify` over `outputs/citations*/` | reports quotations as unchecked, source not found |
| tests that read stored search pages or development abstracts | fail |

The abstracts and open-access full texts can be fetched again with the study's scripts
(`scripts/run_search.py`, `scripts/fetch_fulltext.py`); a fetched file can be compared with the
recorded sha256.

# History rewrite of 12 November 2026

The history was rewritten a second time on 12 November 2026, before the repository was made
public, to remove 68 files that commit `75ef799c2e64` (`9da805dc1c0e` before this rewrite)
stopped tracking but that the commits before it still held:

- 17 abstracts pinned as quotation sources under
  `experiments/02_claims_meta/outputs/span_restoration/` and
  `experiments/02_claims_meta/outputs/superseded/`. Each has the sha256 of a file listed in
  `WITHHELD_FILES.tsv`.
- 47 coder input files of the manual-coding reread (`*.disagreement.json`), which quote
  sentences from the papers.
- 4 briefs written for the coding sessions.

The ignore rules added in that commit cover all 68 paths. The rewrite followed the procedure of
8 October:

- Every commit hash changed again, because the first commit holds removed files. The 231
  commits keep their order, messages, author dates and committer dates, and are signed with the
  same key.
- Every file that remains is byte-identical to the same file in the commit before this rewrite.
  For each of the 231 commits, the file list of the rewritten commit equals the earlier
  list minus the removed paths.
- `COMMIT_MAP_2026-11-12.tsv` gives the hash of each commit before and after this rewrite. A
  hash of the original history maps through `COMMIT_MAP.tsv` first.
- `WITHHELD_FILES_2026-11-12_second_rewrite.tsv` lists the 68 removed files with their size and
  sha256.

The freeze commit, `02bb006f3e55` in the original history and `82fb024ef0ac` after the first
rewrite, is `7f99685c9db7` here. The tag `prereg-paper1-freeze-2026-10-03` points at
`61b37d30a390`, the counterpart of the original tagged commit `c009e46f6257`. The records still
name hashes of the original history and are not edited.

The history before this rewrite is kept by the author as a git bundle (sha256
`8ce625f2797fb3b5be0b44e08edb222e918f304e89ac825ca8ef55810c2b19f3`).
