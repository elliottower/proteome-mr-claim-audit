# Manual coding of dataset names, set-up before the first check: run note, 7 October 2026 (UTC)

No row is coded. No coder was started and none opened a passage: before the regeneration the
coders' folders held 0 attempt files and 0 gate files and no claims file held a quotation; the
run manifest records 0 attempt files. Only counts were read from every output.

## Scripts of the run

| role | script | sha256 |
|---|---|---|
| passage generator | `scripts/manual_coding_passages.py` | `bd83efd7c03f0e1d524bbc7ed6e0373c24832d1a82e00ea4a03f95a2d55539d7` |
| assignment (seed 20261007, 4 coders) | `scripts/coding_assignment.py` | `bc8375a8c0389c80eaf6e62b048ae288761768cdbee569ad7072c3efd5480030` |
| machine gates | `scripts/manual_coding_gates.py` | `3aa4bbcd4df6f2a180d5b88e038cafc67e5a7f22d29ba3d78f8fa54cd7ae5e39` |
| extended and registered table | `scripts/manual_coding_table.py` | `69ac24eed6b864394694278a14b503ec6e8b01983cc2c304608b0353c989d62b` |
| run manifest | `scripts/manual_coding_manifest.py` | `0a4ef1f48df4dd32f32de746f4713424d09c1282efca5a8ee4ecbc894844b279` |
| coder instructions | `prompts/manual_coding_coder_instructions_v2.md` | `79f58e4d168fed386cb55192b8e9a98ff23a993cc35e252b481eaff326379cec` |

Superseded, sealed and not used: `scripts/coding_passages.py` (first generator; its
mark-stripping collapsed white space), `scripts/coding_passages_whitespace.py` (corrected copy,
before the abstract fallback), `scripts/coding_gates.py`,
`scripts/manual_dataset_coding_reasons.py`, `prompts/manual_coding_coder_instructions.md`.

Superseded outputs, kept: `superseded_passages_strip_marks/` (first run, 61 papers without
reference entries), `superseded_passages_before_abstract_fallback/` and
`superseded_coders_before_abstract_fallback/` (second run), and the two folders under
`outputs/citations/superseded/`.

## Counts of the run's passages (`passages/passages_summary.json`)

| | |
|---|---|
| queue rows / papers | 872 / 434 |
| rows with at least one passage | 872 |
| rows given the abstract fallback | 47 |
| rows still `no_local_passage_found` | 0 |
| passages | 3,878 |
| passages with a reference entry | 813 (388 rows) |
| distinct reference entries attached | 992 |
| with a DOI tagged in the XML | 440 |
| with a PMID only | 1 |
| with a PMC identifier only | 0 |
| with no tagged identifier | 551 |
| full-text papers without reference entries | 1 |

Of the 551 entries with no tagged identifier, 328 print a DOI in the entry text. In the stored
XML files 6,164 of 13,317 reference entries carry a `pub-id` and 7,057 carry none and hold an
`ext-link`. The generator reads identifiers from `pub-id` only.

Assignment: 109, 109, 108 and 108 papers; `assignment.json` is byte-identical to the earlier
one. Run manifest: `outputs/manual_coding/2026-10-03/run_manifest.json` (sha256 `eb1670e58a33e29c0b6af3d6098c7685b8e82093d337f3ee48b73ebaf4381afe`).

## Requirement on the report of the table check

The report of the manual coding gives the unresolved rows in four categories, apart: release not
identified; conflicting identifiers; no local passage found; dataset named in the source but
absent from the dictionary. The last is not described as a source that does not report its
dataset. `manual_coding_table.py check` writes the four counts
(`unresolved_reason_<reason>`), and the extended table is the provenance record.

## Tests

Whole suite on Modal: 903 passed, 1 skipped
(`outputs/tests/pytest_all_modal_20261007T175221Z.txt`).
