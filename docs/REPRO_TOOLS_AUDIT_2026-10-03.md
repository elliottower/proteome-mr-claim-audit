# How this repository uses the reproducible-science tools

2026-10-03, before the freeze. Capabilities read from the tools themselves: the README of each
package, `--help` of every subcommand, the plugin manifests and hooks, and the docs site, at
reproducible-science `7bace1c` (main). Installed Claude Code plugin:
`reproducible-science@reproducible-science` 0.4.2, installed 2026-08-30 from `7c94c38`. No
registered rule changed and nothing above the log of `PREREG.md` was edited.

## Capabilities and use

| capability | what it gives a project | before | evidence | action | after |
|---|---|---|---|---|---|
| `prereg new` (OSF headings) | a plan that maps onto OSF without rewriting | used | 27 headings verbatim; OSF dry run accepted | none | used |
| `prereg freeze` / `check` | the plan hash and its commit; any later edit caught | planned | `prereg check`: not frozen (expected) | none | at the freeze |
| `prereg log --access` | amendments and deviations told apart by what had been seen | used | log lines carry an access status; RUNBOOK requires `--access` | none | used |
| `prereg freeze --osf` + metadata | the draft on OSF with subjects, tags, licence | planned | freeze command in the freeze notes | none | at the freeze |
| `prereg freeze --attach` | side files uploaded into the draft, OSF's hash checked, sha256 logged in the plan | **not used** | the side files (tables, prompts, search files) were covered by RELEASES only | `osf_attachments.txt` (45 files); RUNBOOK step 3 and the freeze command attach them | at the freeze |
| `prereg register` | submits the draft | not used by choice | Elliot submits on OSF himself | none | n/a |
| `prereg link` | view-only link for double-blind review | not applicable | registration is public | none | n/a |
| `results init`, ledger tracked | the chain committed with the project | used | `.results/` tracked; `results verify --files` all passed | none | used |
| `results seal` / `access` / `run` | inputs hashed before, outputs after, access timeline | used (smoke runs); seals at the freeze | ledger 17 events; RUNBOOK §Results ledger | none | used |
| `results claim` / `coverage` | each manuscript number bound to its run | planned | RUNBOOK §Checks; no manuscript yet | none | when the manuscript is written |
| `results reanchor` | record a ledger length as authoritative | not needed | chain intact | none | n/a |
| `citations verify` | each quotation found in its pinned source | used | 7,783 found, 0 not found | quotations added (below) | used |
| `citations pin` | a quotation written only if it resolves | used | every claims file written through `pin` since 2026-10-02 | full Liu 2025 passage pinned | used |
| built-in extractors (`sheet-rows`, `docx-text`, `jats-text`) | the publisher's workbook, `.docx` or article XML pinned, with the reading recorded | **not used** (shipped after the last re-pin) | 46 workbook and `.docx` sources pinned only as extracted text; 134 XML quotations refused on raw XML | 105 sources pinned again through the extractors: 1,972 of 2,283 workbook quotations, 32 of 32 `.docx`, 308 of 314 XML | used |
| `citations fetch` | a reader downloads the sources and gets exactly the pinned bytes | partly | 130 of 199 sources fetchable before | the 105 extractor pins tested from an empty folder: 101 fetched and their 2,300 quotations verified, 12 quotations unchecked; all 33 workbook and `.docx` originals fetched; 3 XML sources differ (the server now sends other bytes) and 1 is unavailable (`source_verification/citations_fetch_extractor_pins_2026-10-03.txt`) | partly; the 33 workbook and `.docx` sources added |
| `.bib` + `citations add` | references in one file, every listed author | **not used** | no `.bib`; claims files carried DOIs only | `experiments/02_claims_meta/references.bib`, 120 entries; `claims_to_bibkey.csv` | used |
| `citations lint` | repeated keys and bare author names caught offline | not used | no `.bib` | run: 0 repeated keys, 0 bare names after bracing 56 consortium names | used |
| `citations audit` | stored authors and year checked against the registry | not used | no `.bib` | run: 73 agree, 47 disagree, every disagreement a group-author offset between `add` and `audit` (tool gap 3); cache committed so it re-runs offline | run, findings with the tools |
| `citations coverage` | every quotation in a document pinned | not applicable to Markdown | reads `.tex` only | the plan's quotations checked by converting quotes: six Liu 2025 passages all resolve; one was pinned shorter than quoted and is now pinned in full | done by hand; tool gap 4 |
| `citations resolve` / `build` / `projects` / `tags` / `link` / `import-paperclip` | library maintenance | not applicable | claims files are self-contained; the shared library holds the records | none | n/a |
| `repro.yaml` + `repro verify` | stated numbers checked against the files they came from | **not used** | no manifest | `repro.yaml`: the five feasibility counts of foreknowledge item 8; strict policy passes; a changed number and a changed file each fail it | used |
| `repro check` | one pass over every tool the project uses | not used | — | run: citations ok, results ok, prereg not frozen | used |
| pre-commit `repro-verify` | the manifest checked on every commit | not used | — | `.pre-commit-config.yaml` (v0.4.2) | used once the remote exists |
| CI | the same checks on every push | not used | no workflow | `.github/workflows/verify.yml`: records job on push; sources job weekly or by hand; tools pinned to `7bace1c`; the install resolved in a scratch environment and its record checks passed locally | active once pushed |
| plugin hooks (frozen plan, unbound number, unverified quotation, unfrozen plan before a run) | warnings at the moment of writing | used | hooks fired on every write in this session | warnings on registered parameters in Markdown documented (tool gap 5) | used |
| plugin skills and `/…-check` commands | the tools offered when the situation calls for them | used | skills loaded this session | none | used |
| `repro-gates` mod (refuses edits to a frozen plan, status line, `/repro-status`) | the hold the hooks cannot give | **not installed** | `installed_plugins.json` lists the bundle only | Elliot installs it (below) | pending |
| `CLAUDE.md` (written by `repro init`) | the project's rules for Claude Code | **missing** | — | `CLAUDE.md` at the root | used |
| README for readers | what the study is and how to check it | **missing** | — | `README.md` at the root | used |

## Left for others

- **Elliot, in Claude Code:** `/plugin marketplace update reproducible-science`, then
  `/plugin install repro-gates@reproducible-science` (the mod) and reinstall
  `reproducible-science@reproducible-science` so the hooks match main.
- **Elliot, at the freeze:** the private remote; then `pre-commit install` once, and the
  workflow runs on the first push.
- **Elliot, now:** the `citations` on PATH (the PyPI release) fails this repository: it reports
  114 quotations of extractor-pinned sources as not found and cannot read the workbooks, where
  the main build finds all 7,783. Until a release ships the extractors, check this repository
  with the build the README names; the end-of-session `citations verify` of other sessions will
  report this repository as failing if run with the PATH build.
- **The tools session:** the nine items in
  `source_verification/FEATURE_REQUEST_exemplar_gaps_2026-10-03.md`, and a release that ships the
  extractors, so a reader on the PyPI build does not get `unchecked` for 2,312 quotations.
- **Not fixable here:** 13 workbook and `.docx` supplements served only through PubMed Central,
  which refuses scripts, stay pinned as extracted text; 311 workbook quotations refused under
  `sheet-rows` (rows repeated across sheets, or cells pandas kept and `sheet-rows` drops) stay
  pinned to the extracted text.

## Effect on the freeze plan

One addition: the freeze command attaches the 45 files in `osf_attachments.txt`, so the
tables and prompts the plan relies on are registered with it and their sha256 is in its log.
The OSF dry run does not exercise attachments; the first real upload is at the freeze. Nothing
else changes.
