# proteome-mr-claim-audit

A preregistered census of the protein–outcome claims made in the abstracts of proteome-wide
Mendelian-randomization studies first public 2019–2025: how often a claim is repeated, how often
studies contradict one another, and how often repeated claims rest on the same source data.

The plan is `experiments/02_claims_meta/PREREG.md`. Its hypotheses, decision rules, data
sources and every analysis are fixed there; the scripts that carry them out are in the same
folder and were written and tested before the plan was frozen. A later rerun of the claims
against the source data is a separate registration.

## Status

The plan was frozen on 3 October 2026 and registered at https://osf.io/zae8c. `prereg check`
reports whether the plan still says what it said; every later change is in the `## Log` of
`PREREG.md` and in the two amendment files beside it. As of 8 October 2026 the search,
screening, extraction, span and claim checks and the manual dataset coding have run, and the
registered joins (stage 5) have not. What had been read before the freeze is listed in
PREREG.md, §Explanation of foreknowledge.

## How the record is kept

Four tools from [reproducible-science](https://github.com/elliottower/reproducible-science)
keep each step of the study checkable after the fact.

| step | tool | record in this repository |
|---|---|---|
| freeze the plan before running it, then log every change with what had been seen | `prereg` | the header and the `## Log` of `PREREG.md` |
| hash the inputs before a run and the outputs after it | `results` | `.results/ledger.jsonl`, `outputs/results_manifests/` |
| bind each number in the manuscript to the run that produced it | `results claim` | the ledger |
| pin each quotation to the bytes of the source it comes from | `citations` | `claims/`, one file per source |
| check declared numbers against the files they come from | `repro verify` | `repro.yaml` |

The run order, with the exact command for each stage and its ledger record, is
`experiments/02_claims_meta/RUNBOOK.md`.

## Checking it

Install the tools at the commit the claims files need. Several sources are pinned as the
publisher's workbook, `.docx` or article XML and read through the `sheet-rows`, `docx-text` and
`jats-text` extractors, which are not yet in a PyPI release; a released build reads those
sources without the extractor and reports their quotations as not found. Until a release ships
them, install from the commit `.github/workflows/verify.yml` names:

```bash
T=git+https://github.com/elliottower/reproducible-science@7bace1c
uv tool install "reproducible-science @ $T#subdirectory=packages/repro" \
  --with "provenance-core @ $T#subdirectory=packages/provenance-core" \
  --with "prereg @ $T#subdirectory=packages/prereg" \
  --with "results-cli @ $T#subdirectory=packages/results" \
  --with "citations[sheets,docx] @ $T#subdirectory=packages/citations" \
  --with-executables-from prereg,results-cli,citations
```

From the repository root:

```bash
repro check .                               # prereg, results and citations in one pass
results verify --files                      # the ledger chain and every hash it names
citations fetch --claims claims/            # download the pinned sources where they are open
citations verify --claims claims/           # every quotation against its source
citations lint --bib experiments/02_claims_meta/references.bib
repro verify                                # the numbers declared in repro.yaml
```

and, from `experiments/02_claims_meta/`:

```bash
prereg check                                # has the plan changed since the freeze?
uv run scripts/stage_record.py verify       # every file each stage manifest names
```

The abstracts and full texts the study reads, and the model requests that embed them, are not
redistributed. `docs/history_rewrite/WITHHELD_FILES.tsv` lists each such file with its sha256,
and `docs/history_rewrite/README.md` says which checks need them and how the commit hashes in
the records map to the hashes in this repository.

The pinned sources are full texts of papers and supplements and are not redistributed.
`citations fetch` downloads each one where it is openly available and installs it only when its
sha256 matches the pin; a source that is paywalled or refuses a script stays `unchecked`, which
is reported as such and never as found. Several sources are pinned twice, once as the text that
was quoted and once as the publisher's file read through a named extractor, so that a reader
can check the quotation against a file they fetched themselves
(`docs/source_verification/REFETCH_STATUS_2026-10-02.md`).

The resource files the analyses read (ChEMBL, Open Targets, Reactome, the ontologies, the
EpiGraphDB snapshot) are pinned by sha256 in `experiments/02_claims_meta/RELEASES.md` and
`modal_inputs_manifest.json`, and the heavy stages run on [Modal](https://modal.com).

## Layout

| path | holds |
|---|---|
| `experiments/02_claims_meta/` | the plan, prompts, scripts, tests, verification tables, search files and outputs |
| `experiments/01_census/` | an earlier reporting-quality census, not frozen and not run |
| `claims/` | the pinned quotations behind the dataset, cohort and platform decisions |
| `docs/` | the checks made before the freeze, the records the plan cites, run notes, and `history_rewrite/` |
| `.results/` | the results ledger |

## Licence and citation

Code is MIT-licensed (`LICENSE`). Cite the registration: https://osf.io/zae8c.
