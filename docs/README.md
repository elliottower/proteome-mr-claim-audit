# Records behind the preregistration

Files that `experiments/02_claims_meta/PREREG.md` and `RELEASES.md` cite as evidence. What had
been read in the 2019–2025 window before the freeze is listed in PREREG.md, §Explanation of
foreknowledge.

| folder | holds |
|---|---|
| `source_verification/` | the check of the source report's citations against the papers (`VERIFICATION.md`), the search for earlier studies of the same kind (`SCOOP_RERUN_2026-09-30.md`), the cohort lists read from each consortium's cohort tables (`compositions/`), and the reading of the quotations `citations verify` warns about (`QUOTE_WARNINGS_2026-10-02.md`) |
| `feasibility/` | PubMed result counts for the four queries, counts only |
| `stage0_build/` | checks made while the scripts were written, on resource files and on records published before 2019: query-translation counts, the platform lookups for 14 pQTL datasets, the rule table of the build, the deliberate rule changes that each make a test fail, and the probes of published list files |

The quotations are in `claims/` at the repository root, one file per source, each with the
sha256 of the text it was taken from. The texts are full texts of papers and supplements and are
not redistributed; `citations verify --claims claims/` checks the quotations where the texts are
present in `sources/`.

Two probe outputs of `stage0_build/` (`probe_backgrounds_round6.json`,
`probe_backgrounds2_round6.json`) are not here: they reproduce a supplementary sheet that lists
investigators' e-mail addresses. The scripts that wrote them are.
