# Development results before the freeze (GPT-6.1 Sol only)

Prompt development used 30 abstracts first public before 2019 (none can enter the census) and,
for the full-text prompt, one pre-2019 open-access paper. The known-item check used the
eligibility prompt only on the known items; no claim fields were requested or read for any
in-window abstract. Every figure below is an internal consistency check on unlabeled
development records; none estimates extraction recall or precision.

All extraction metrics are scored with the final verifier and the registered reference files
(HGNC 2026-09-04, UniProt 2026_03 `620d646a96c0`, MONDO v2026-09-01, EFO v3.93.0) and the
dataset dictionary (`reference/MANIFEST.json`; RELEASES.md).

## Extraction, development set (r4 → r8; full metrics in outputs/dev_metrics/r4.json, r8.json)

| metric | r4 | r8 |
|---|---|---|
| schema-valid extraction, first attempt | 30/30 | 30/30 |
| claim records extracted | 76 | 141 |
| evidence type (mr / observational / variant / experimental / other) | 43 / 9 / 19 / 2 / 3 | 77 / 20 / 41 / 2 / 1 |
| claim scope (overall / dataset / ancestry / subgroup / sensitivity) | — | 95 / 13 / 2 / 3 / 28 |
| spans verified (normalized check and `citations verify`) | 75/76 | 129/141 |
| protein mapper acceptance (mapped / ambiguous / unmapped) | 69 / 3 / 4 | 128 / 9 / 4 |
| outcome mapper acceptance (mapped / ambiguous / unmapped / not in span) | 60 / 10 / 5 / 1 | 110 / 14 / 14 / 3 |
| dataset names (not stated / unmatched / release-ambiguous) | 125 / 26 / 2 | 240 / 43 / 4 |
| directional records: agrees / unverified / disagrees | 52 / 5 / 2 | 64 / 23 / 20 |
| MR-estimate directional records: agrees / unverified / disagrees | 36 / 4 / 0 | 45 / 13 / 9 |
| records entering the registry | 37 | 63 |
| of which enter direction-based results | 33 | 43 |
| cost of the extraction run (upper bound, USD) | 0.37 | 0.66 |

r8 keeps distinct analysis contexts apart (the round-4 claim-record definition), which is most of
the rise from 76 to 141 records. The nine r8 MR disagreements all come from one abstract (PMID
27327646): heterogeneity-adjusted sensitivity records whose spans quote the main-analysis
sentence, so the verifier reads the main estimate and keeps them out of direction results. The
twelve failing r8 spans join two sentences of the abstract that are not adjacent. The r4 outputs
give the same per-claim results under the registered files as under the EFO v3.94.0 run.

## Full-text prompt, one pre-2019 open-access paper (outputs/dev_metrics/ft1.json)

| metric | PMID 30111768 |
|---|---|
| body words (abstract and supplements excluded) | 8,514 |
| claim records (text / Table 1 / Table 2) | 45 (9 / 10 / 26) |
| spans verified | 45/45 |
| evidence type (observational / variant / mr / other) | 26 / 10 / 6 / 3 |
| records entering the registry | 6 |
| directional records: agrees / unverified / disagrees | 27 / 1 / 1 |
| colocalization or replication reported | 0 |
| cost (upper bound, USD) | 0.17 |

## Eligibility on the known-item calibration set (r4 → r7)

The eligibility prompt was revised until every retained known item passed, so the final row is
calibration, not an estimate of sensitivity.

| revision | change | known items passing |
|---|---|---|
| r4 | — | 17 of 25 |
| r5 | criterion 2 accepts count-level results; tissue/CSF exclusion only when no plasma/serum proteins; `uncertain` added | 24 of 25 |
| r6 | protein count recorded only when stated as tested in MR; other counts to `count_other`; PMID 35300523 removed from the set (abstract states 90 proteins tested, below the floor) | 24 of 24, but two small pre-2019 panels passed via `count_other` |
| r6 + floor rule | 100-protein floor applied to `count_other` when no tested count is stated (deterministic script) | 23 of 24 (one association count misread as a protein count) |
| r7 | association/significance counts excluded from both count fields | **24 of 24** (12 eligible, 11 `count_not_stated`, 1 `uncertain`) |

Development set under r7: 1 of 30 eligible (Sun 2018, pre-2019, removed by the date rule).

## Registry, statistics and dry run

- `tests/` (run with `uv run --no-project --with pytest==8.4.2 --with pydantic==2.13.5 --with
  numpy==2.5.3 --with rapidfuzz==3.14.6 pytest tests/`): 35 pass: 19 dataset-relation tests on
  the committed dictionary, 12 registry and statistics tests, 4 full-text concordance tests.
- Dry run on synthetic records (`scripts/dry_run_synthetic.py`, `outputs/dry_run/`): 13 search
  records → 10 families (one identifier link, one fuzzy link, one shared-PMID link; two
  look-alike journal articles, a later preprint and a preprint published as another article
  left unlinked) → eligibility decisions → 17 verifier-format records (4 dropped by reason) → 5
  pairs → H1 and H2 tables with the pair bootstrap, family jackknife and H2 verdict. Every stage
  matches its stated expectation.

Total Sol cost across development: about $3.
