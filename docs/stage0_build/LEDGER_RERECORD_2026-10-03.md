# Results ledger: the no-abstract rerun recorded once (3 October 2026)

Done before the repository's first commit; no commit existed.

On 2 October the rerun of the pre-2019 smoke round under the `no_abstract` rule was recorded in
the ledger (event 17, run `smoke_pre2019_20261002_no_abstract_rule`) while three of its outputs
still named the repository's folder on the author's machine. The path was removed from the
three files with `stage_record.py replace`, and the funnel was recorded a second time (event 18,
run `smoke_pre2019_20261002_no_abstract_rule_paths_removed`). `results verify --files` then
reported that funnel as `RESEALED`: one path recorded with two hashes.

What was done:

1. The ledger with the two events was archived to
   `experiments/02_claims_meta/outputs/superseded/ledger_rerecord_2026-10-03/`
   (`ledger_with_the_two_events.jsonl` and `.head`), with the two run manifests and the
   replacement table as it stood (`replaced_files_before.json`).
2. The ledger after 16 events, saved before the rerun, was restored. Its sha256 is
   `ac895c2cf5fe945ef8fcc6e9c7b18109381a62fd340868baf3b70ae128963eb1`, the value RELEASES.md
   recorded for the ledger after 16 events.
3. The three rows of the rerun were removed from
   `outputs/results_manifests/replaced_files.json`; the rows of the three earlier smoke runs
   stay.
4. The rerun was recorded once, with the files as they now are (relative paths only), under
   its original run id: `stage_record.py record --run-id smoke_pre2019_20261002_no_abstract_rule`
   with `funnel.json` recorded directly and the three folders (`outputs/screening_smoke/…`,
   `outputs/registry/…`, `outputs/funnel/…` of that run) hashed into its manifest (42 files).

Result: `results verify --files` reports "chain intact: 17 events, anchored" and no `RESEALED`,
`CHANGED` or `MISSING` line; `stage_record.py verify` passes for every manifest. No count in any
file changed: the two recorded versions of the funnel differed in 13 path strings only.

Why: the ledger was not yet committed, so restoring its saved state rewrote nothing anyone
could have relied on, and a first commit whose ledger reports a file recorded with two hashes
reads as tampering. The archived copies keep what happened.
