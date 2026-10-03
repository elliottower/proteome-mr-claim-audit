# For the reproducible-science session: gaps found making this repository an exemplar

2026-10-03, from an audit of how `proteome-mr-claim-audit` uses the four tools
(`docs/REPRO_TOOLS_AUDIT_2026-10-03.md`). Tools at reproducible-science `7bace1c`. Each item is
something a project cannot fix from its own side.

## `citations add` and `citations audit` disagree with each other

1. **Keys with spaces.** `citations add --doi` derives a key from the first family name and
   keeps its spaces: `lango allen2010hundreds` (10.1038/nature09410),
   `alzheimer disease genetics consortium adgc2019genetic` (10.1038/s41588-019-0358-2). The
   write is then refused by its own read-back ("did not read back as its N entries plus …") and
   the file is restored, so the entry cannot be added without `--key`. Strip or join the words
   of a multi-word family name before the year.
2. **Group authors written bare.** Where Crossref lists a consortium as an author
   (`{"name": "FinnGen"}`), `add` writes it unbraced among the people, and `citations lint` on
   the file `add` just wrote flags it as an author with no given name (19 entries of 120 here,
   54 names). `add` should brace a name Crossref gives as `name` rather than `family`/`given`.
3. **`audit` against the file `add` wrote.** On 120 entries all written by `add` from
   Crossref, `audit` reports 47 disagreeing with Crossref, 14,970 surname differences: every
   entry whose Crossref record carries a group author is offset by one position from the
   person-only list `audit` compares against
   (`docs/source_verification/citations_audit_2026-10-03.txt`). A bibliography written by the
   tool and checked by the tool should agree.

## Coverage of a Markdown registration

4. `citations coverage` reads `` ``…'' `` in a `.tex` file only. A preregistration is
   Markdown, and its quotations of other papers (here, six passages of Liu et al. 2025) can only
   be checked by converting `"…"` to `` ``…'' `` first. One of the six was pinned in a shorter
   form than the plan quotes and was found this way. A Markdown mode (`"…"`, `“…”`) would let
   the plan be checked like a manuscript.

## Hooks

5. The `results` hook reports registered parameters in `README.md` and `CLAUDE.md` (the years
   of the study window) as unbound numbers; it treats every Markdown file as a manuscript. A
   project setting naming the manuscript files, or reading only `paper/` and `.tex`, would keep
   the warning for the files it is about.
6. In this session each hook message arrived twice per write. The installed plugin is
   `reproducible-science@reproducible-science` 0.4.2 alone; the cause was not found.

## `prereg freeze --attach`

7. The OSF dry run (`osf.build_draft`) does not exercise attachments, so a name collision, an
   oversize file or a missing path is found only at the real push, after the freeze header is
   written. A dry run that checks the `--attach` list without uploading would close that.

## `citations fetch`

8. Fetching the 105 new extractor pins into an empty folder took more than 20 minutes. Where the
   recorded `url:` served other bytes, `fetch` went on to ask OpenAlex for further copies (six
   attempts for one source in `citations_fetch_extractor_pins_2026-10-03.txt`). Accepting an
   OpenAlex key from the environment, and stopping after the recorded `url:` when the claims file
   says that address is the publisher's own, would shorten a reader's first fetch.

## Release

9. The claims files name the `sheet-rows`, `docx-text` and `jats-text` extractors, which are on
   main and not in a PyPI release. A released build (the `citations` on PATH here) does not
   refuse a source whose `extractor:` it does not know: it reads the article XML as plain text
   and reports 114 of its quotations `not found`, and tries to read each workbook as a PDF
   ("EOF marker not found"), so `citations verify` exits 1 on a repository whose every quotation
   resolves under main (7,783 found, 0 not found). An unknown `extractor:` should make the
   source `unchecked`, naming the field, in every build; and a release that ships the extractors
   would let readers install from PyPI. The README and CI here install from `7bace1c` until then.
