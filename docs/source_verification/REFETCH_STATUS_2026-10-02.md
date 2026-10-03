# Can a reader re-fetch the pinned sources? Status on 2026-10-02

`sources/` is not committed: it holds full texts of papers and supplements. A reader has the
claims files, each with a sha256 and a `doi:` or `url:`, and runs `citations fetch` to obtain
the files and `citations verify` to check the quotations in them.

## Counts

On an empty checkout, with the `citations` build of reproducible-science `b078cb2`:

| | before | after |
|---|---|---|
| claims files | 199 | 324 (199 text pins, 125 original-file pins) |
| quotations (`citations verify --claims claims/`, sources present) | 4,499 found, 0 not found | 5,470 found, 0 not found |
| sources a reader can fetch and match to a pin | 2 of 199 | 130 of 199 |
| quotations a reader can check against a file they fetched | 19 of 4,499 | 1,012 of 4,499 |
| `citations fetch`, text pins (199) | 2 fetched, 156 differ, 41 unavailable | 11 fetched, 148 differ, 40 unavailable |
| `citations fetch`, original-file pins (125) | none existed | 119 fetched, 1 differs, 5 unavailable |

The 5,470 quotations are the 4,499 of the text pins plus 971 of them pinned a second time
against an original file. No text pin was edited and no quotation was reworded.

Records: `citations_fetch_2026-10-02.txt` (before), `citations_fetch_after_repin_2026-10-02.txt`
(after: the 136 new or changed claims files, fetched and verified in an empty folder; the other
188 text pins were not asked again and keep their earlier outcome),
`repin_originals_summary_2026-10-02.json` (one row per source).

## What was done

`repin_originals.py` reads `originals_plan.json`. For each source it obtains the original
file, writes `claims/<stem>_original.yaml` pinning that file with its `url:` and `doi:`, and
passes each quotation of `claims/<stem>.yaml` to `citations pin`, which writes a quotation only
when it resolves in the original. The run records are `repin_originals_result_2026-10-02.json`
(PDF and bucket text), `repin_originals_xml_result_2026-10-02.json` (XML) and
`repin_originals_served_copies_result_2026-10-02.json` (five sources pinned a second time, see
below). The originals are in `sources/original/` (125 files, 257 MB, ignored).

| how the pinned text was made | sources | quotations | originals pinned | quotations in the originals | refused by `citations pin` |
|---|---|---|---|---|---|
| PDF, `pdftotext` | 47 | 1,021 | 47 | 761 | 260 |
| Europe PMC `fullTextXML` | 58 | 243 | 53 | 147 | 96 |
| NCBI efetch `db=pmc` XML | 21 | 85 | 19 | 47 | 38 |
| PMC open-data bucket `.txt` with one header line added | 6 | 16 | 6 | 16 | 0 |
| PMC open-data bucket `.txt`, unchanged | 9 | 53 | none needed | | |
| spreadsheet | 40 | 2,688 | 0 | | |
| `.docx` | 8 | 298 | 0 | | |
| web page | 3 | 22 | 0 | | |
| other | 7 | 73 | 0 | | |

- **PDF.** The original is read by `pdftotext -layout`, and by `pdftotext`, `pypdf` or
  `pdfplumber` where the first does not find a passage. Of the 260 refusals, 255 are table rows
  that the text pin rewrote with ` | ` between cells (`lambert2013_supp` 29,
  `michailidou2017bcac_ref20_michailidou2015_supp_table1` 78, `schumacher2018practical_supp`
  59, `trubetskoy2022scz3_supp_cohorts` 89), and 5 are short passages that occur twice in the
  whole PDF and once in the excerpt the text pin holds (`bellenguez2022_supp_note` 1,
  `lambert2013_supp` 2, `nalls2019_supp` 2).
- **XML.** The original is the XML as served, read as plain text with its markup. A quotation
  that crosses an inline tag or a character entity does not resolve there; 115 of the 120
  refused quotations whose XML is held resolve once the tags are stripped. Six XML sources had
  no quotation that resolved and got no original-file pin.
- **Bucket text, unchanged.** Nine text pins are byte for byte the file in the PMC open-data
  bucket. Each gained one line, `url:`, in its `source:` block; nothing else in those nine
  claims files changed.
- **Five PDFs pinned from the served copy.** For `chen2025lung`, `gartlehner2025swar`,
  `gibson2022preprint`, `liu2025mrkg` and `skrivankova2021jama` the copy the text pin was
  extracted from is not the copy a plain download now gets. The original-file pin is the
  served copy, in which every quotation of the source resolves.

## What a reader still cannot fetch

- **Six original-file pins.** `eldjarn2022withdrawal` (bioRxiv serves a PDF whose bytes change
  between downloads), `pietzner2021`, `pietzner2021aam` (the repository refuses a plain
  client), `konet2024`, `nibali2026`, `wu2024heart` (publisher PDFs obtained through the
  OpenAlex content endpoint, which needs a key). 31 quotations.
- **Spreadsheets and `.docx`: 48 sources, 2,986 quotations.** `citations` has no reader for
  them. `FEATURE_REQUEST_citations_extractors.md` asks for one.
- **Quotations refused above: 394**, which stay pinned to the extracted text only. The XML
  ones need a tag-stripping reader (same request); the PDF table rows would need re-pinning in
  the form the PDF prints them.
- **Fifteen other sources**: seven XML sources with no original-file pin (six in which no
  quotation resolved in the raw XML, one with no quotation), two excerpts of another pinned
  text, one hand-transcribed PDF table, one bioRxiv JATS file, one PubMed abstract, and three
  web or documentation pages pinned as tag-stripped HTML.

## Provenance of the numbers here

Every count is in `repin_originals_summary_2026-10-02.json`, the three run records or the two
fetch records named above. They are counts about source files, not results a paper reports,
and are not bound in the results ledger.
