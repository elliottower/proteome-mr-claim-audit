# API framing of the coding prompt

Both models receive the same fixed prompt and the same packet. Only the API framing differs.

The fixed prompt is, in this order: `prompts/coding_prompt.md`; a line `## Dictionary
definitions`; the file
`experiments/02_claims_meta/outputs/manual_coding/2026-10-03/coders/dictionary_definitions.csv`
as CSV. The packet is one JSON object (`record_id`, `title`, `rows`, `files`,
`accession_table_rows`); `accession_table_rows` holds, with the columns `release_identifier`,
`identifier_type` and `dictionary_row`, the rows of `reference/accession_releases.csv` for every
match of the accession patterns of `reference/c1_scanner_patterns.json` in the packet's files
(an `ebi-a-` identifier also under the GWAS Catalog accession it carries), and every row of type
`opengwas_batch`. The output must fit `prompts/output_schema.json`.

| | Claude Sonnet 5.5 (`claude-sonnet-5-5`), Messages API | GPT-6.1 Sol (`gpt-6.1-sol`), Responses API |
|---|---|---|
| fixed prompt | `system`, one text block with `cache_control` of type `ephemeral` | `instructions` |
| packet | one `user` message, the packet as JSON text | `input`, the packet as JSON text |
| output | structured output with the schema | `text.format` of type `json_schema`, strict, with the schema |
| tools | none | none |
| sampling | the API's default | the API's default |
| maximum output | 32,000 tokens | 32,000 tokens |

The model string each API returns is recorded with every response. An answer that does not
parse, or does not fit the schema, is requested once more under the same framing; a second
failure leaves the paper's rows unresolved and is counted.
