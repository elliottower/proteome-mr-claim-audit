# Manual coding of dataset names, reference identifiers: run note, 7 October 2026 (UTC)

Continues `MANUAL_CODING_SETUP_2026-10-07.md`, whose generator and counts this note replaces.
No row is coded; no coder was started (0 attempt files, 0 gate files, no claims file holds a
quotation, before each regeneration and in the run manifest). Counts only were read.

## Generator of the run

`scripts/manual_coding_passages_v3.py`, sha256
`1502821b666e49329aa7d7bccaadbb61dc0b71b73058775b372f201471a2510f`. A reference entry's DOI is
read from its `pub-id` tag, then a link element, then the entry text; a PMID from its tag, a
PubMed link, or "PMID: n" in the text; different DOIs in one entry make it conflicting, with no
identifier.

Superseded, sealed and not used: `scripts/manual_coding_passages.py` (identifiers from `pub-id`
tags only) and `scripts/manual_coding_passages_v2.py` (its DOI pattern ran on into the query
string of a look-up link, so 385 entries read as two DOIs), besides the two earlier generators.
Their outputs are kept: `superseded_passages_pub_id_only/`, `superseded_coders_pub_id_only/`,
`superseded_passages_doi_query_string/`, `superseded_coders_doi_query_string/`, the two
superseded run manifests, and the matching folders under `outputs/citations/superseded/`.

The gate (`scripts/manual_coding_gates.py`), the table script (`scripts/manual_coding_table.py`),
the assignment (`scripts/coding_assignment.py`, seed 20261007; `assignment.json` byte-identical
to every earlier one) and the coder instructions (`prompts/manual_coding_coder_instructions_v2.md`)
are unchanged.

## Counts (`passages/passages_summary.json`)

| | |
|---|---|
| queue rows / papers | 872 / 434 |
| rows with at least one passage | 872 (47 through the abstract fallback) |
| passages | 3,878 |
| passages with a reference entry | 813 (388 rows) |
| distinct reference entries attached | 992 |
| DOI from a `pub-id` tag | 440 |
| DOI from a link element | 520 |
| DOI from the entry text | 2 |
| PMID only | 1 |
| PMC identifier only | 0 |
| conflicting | 3 |
| no identifier | 26 |

Run manifest: `outputs/manual_coding/2026-10-03/run_manifest.json`, sha256
`b1c6d9d3575437cc6ced5cc33d6609627e63a1618768ee2de4787d4651e7770b`.

Whole suite on Modal: 938 passed, 1 skipped
(`outputs/tests/pytest_all_modal_20261007T180201Z.txt`).
