# Feature request for `citations`: pin the original file and name the extraction

2026-10-02. From the `proteome-mr-claim-audit` repository, for the session that maintains
`reproducible-science`. Nothing in the tool was changed from this repository.

## The need

A claims file pins one file by sha256, and `citations fetch` installs a download only when its
bytes match that pin. 199 claims files here pin a text that a script extracted from a paper or
a supplement. A reader's download is the publisher's file, so the bytes never match: on an
empty checkout `citations fetch` gave 2 fetched, 156 differ, 41 unavailable.

The fix is to pin the original file and let a named, recorded extraction produce the text the
quotations resolve in. `citations` already does this for a PDF, because it reads a PDF itself.
It cannot do it for the other formats our sources come in.

## What the tool does today (build `b078cb2`)

- A PDF is read by `pdftotext -layout`, then `pdftotext`, `pypdf` and `pdfplumber` where the
  first does not find a passage (`verify.py`, `_chain`, `_second_opinion`).
- A file with a suffix in `TEXT_SUFFIXES` (`.txt .md .tei .xml .html .htm .rst .py`) is read
  straight off disk. An `.xml` or `.html` file is matched with its markup in place.
- `extract_cmd` runs one program from an allowlist (`pdftotext`, `detex`); any other program
  needs `--allow-extractor` from whoever runs the check.
- A claims file has one `local` and one `sha256`. There is no place to record a raw file and a
  derived text side by side.
- A spreadsheet or a `.docx` reaches the PDF readers and is `unchecked`.

## What we did with the tool as it is

Script and plan: `docs/source_verification/repin_originals.py`, `originals_plan.json`. Per
source: `repin_originals_summary_2026-10-02.json`. Status: `REFETCH_STATUS_2026-10-02.md`.

| how the pinned text was made | sources | quotations | original pinned | quotations that resolve in the original | reader can fetch |
|---|---|---|---|---|---|
| PDF, `pdftotext` | 47 | 1,021 | 47 | 761 | 41 sources, 730 quotations |
| Europe PMC `fullTextXML`, tags stripped | 58 | 243 | 53 | 147 | 53 sources, 147 quotations |
| NCBI efetch `db=pmc` XML, tags stripped | 21 | 85 | 19 | 47 | 19 sources, 47 quotations |
| PMC open-data bucket `.txt` | 15 | 69 | 6 (9 needed only a `url:`) | 69 | 15 sources, 69 quotations |
| spreadsheet (`.xlsx`), rows joined with ` \| ` | 40 | 2,688 | 0 | 0 | none |
| `.docx`, paragraphs and table rows | 8 | 298 | 0 | 0 | none |
| web page (2 markdown, 1 HTML) | 3 | 22 | 0 | n/a | 2 sources, 19 quotations (the markdown pages, whose pinned text is the served file) |
| other (excerpt of another pinned text, hand-transcribed PDF table, bioRxiv JATS, PubMed abstract, 2 documentation pages) | 7 | 73 | 0 | n/a | none |
| total | 199 | 4,499 | 125 | 971 in the originals | 130 sources, 1,012 quotations |

Two measurements bear on the XML request:

- Europe PMC `fullTextXML` and NCBI efetch return the same bytes on repeated requests; for six
  articles the Europe PMC bytes equal a copy held since 30 September.
- Read as plain text with markup, the raw XML resolves 194 of 328 quotations. Of the 120
  refused quotations whose XML is still held, 115 resolve once the tags are stripped
  (`"".join(root.itertext())`), so inline markup (`<italic>`, `<sup>`, `<xref>`) and character
  entities account for nearly all refusals.

## Requests

1. **A source block that separates the raw file from the text.** For example:

       source:
         local: sources/original/aragam2022cad_main.xml
         sha256: <raw bytes>
         url: https://www.ebi.ac.uk/europepmc/webservices/rest/PMC9729111/fullTextXML
         extractor: jats-text
         extractor_version: 1
         derived_sha256: <text the extractor produced when the quotations were pinned>

   `fetch` verifies the raw bytes. `verify` checks the raw pin, runs the named extractor and
   resolves the quotations in its output; where `derived_sha256` is present and differs it says
   so, because the extractor then no longer produces the text that was quoted.

2. **`jats-text`, a built-in extractor for JATS XML** (Europe PMC `fullTextXML`, NCBI efetch
   `db=pmc`, bioRxiv source XML): the text of each block element (`title`, `p`, `caption`,
   `label`, table rows) on its own line, inline markup dropped, entities decoded, table cells
   joined with ` | `. It would cover 80 sources and 332 quotations here. Reference behaviour:
   `experiments/02_claims_meta/scripts/fetch_fulltext.py`, functions `text_of`, `render` and
   `render_table`.

3. **`sheet-rows`, a built-in extractor for `.xlsx`, `.xls` and `.csv`**: one row per line,
   cached cell values, cells joined with ` | `, with an option naming the sheet and an option
   for keeping or dropping empty cells. 40 sources and 2,688 quotations, 60% of all quotations
   here, are rows of supplementary cohort tables.

4. **`docx-text`, a built-in extractor for `.docx`**: paragraphs in order, then each table one
   row per line with cells joined with ` | `. 8 sources, 298 quotations.

5. **A member of an archive as the pinned file.** 21 of the 48 spreadsheet and `.docx`
   sources came out of a Europe PMC `supplementaryFiles` zip. A `url:` for the zip plus a
   `member:` path, with the sha256 taken over the member, would let `fetch` install them.

6. **`html-text`** for a web page pinned as tag-stripped text (3 sources, 5 quotations).

Built-in extractors are named in the claims file and run in-process, so they need no
`--allow-extractor`: the file names a reader the tool ships, not a program on the machine.

## Three smaller things found on the way

- **`fetch` asks arXiv for the latest version.** A source with `doi: 10.48550/arXiv.2501.11840`
  and `url: https://arxiv.org/pdf/2501.11840v1` pins version 1. `arxiv_of` takes the id from
  the DOI, which has no version, and `locate` then skips the `url:` because it is an arXiv
  link, so the download is the latest version and the outcome is `differs`. Adding
  `arxiv: 2501.11840v1` to the source block works; preferring a versioned id found in `url:`
  would make it work unasked.
- **`pin` has no `--prefix` or `--suffix`.** A passage that occurs twice is refused as
  ambiguous and the command line offers no way to anchor it (5 quotations here).
- **A table row quoted with separators cannot resolve in a PDF.** 255 quotations of four
  supplementary PDFs were pinned as rows rewritten with ` | ` between cells. This is a property
  of how those texts were made, not a request; it is listed so the count is not mistaken for
  an extraction fault.

## How to tell it worked

On an empty checkout of this repository, `citations fetch --claims claims/` followed by
`citations verify --claims claims/` should verify the 2,688 spreadsheet quotations, the 298
`.docx` quotations and the remaining XML quotations against files the reader downloaded.

## A limit of the reference

The scripts that produced the 199 pinned texts were written per source and were not kept. Each
claims file's `note:` says how its text was made (library, sheet, separator, whether wrapped
lines were joined). A standard extractor will not reproduce those texts byte for byte, so
adopting one means re-pinning the quotations against its output, which `citations pin` checks
quotation by quotation.
