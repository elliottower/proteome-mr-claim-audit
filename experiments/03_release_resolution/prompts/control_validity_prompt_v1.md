# Marking whether a dataset identifier is attributed to the dataset of a claim

You receive one item at a time. Each item is a dataset identifier found in a published
Mendelian-randomization paper, the passage of the paper where it stands, and the paper's claims.
You work only from what the item holds and these instructions. You have no web access and no
tools.

## What an item holds

One JSON object:
- `row_id`: the item's identifier; return it unchanged;
- `side`: `outcome` or `pqtl`;
- `identifier`: the dataset identifier as the paper writes it (an accession, a numbered release,
  or a DOI or PMID of the dataset's source publication);
- `passage`: where the identifier stands: `text`, the sentence or table row that holds it;
  `before` and `after`, the sentence or table row immediately before and after it in the same
  file (`null` at the start or end of the file); `table_header`, the header line of the table when
  `text` is a table row (otherwise `null`);
- `claims`: the paper's claims, one or more, each with `protein`, `outcome` and `direction` as
  the paper's abstract states them.

## Rubric

A control is valid when its source sentence or table row attributes its identifier to the dataset
of the control's own side for the record's claim: for an outcome-side control, the dataset of the
claim's outcome; for a pQTL-side control, the pQTL dataset of the claim's exposure protein. It is
invalid when the identifier belongs to another role on that side (an exposure or covariate for an
outcome-side control, another outcome, a replication or secondary analysis), or when it names one
component of a meta-analysis or combined dataset while the claim's dataset for that side is the
combined one. An identifier of a component the claim analysed alone is valid.

Here the item is the control, `side` is the control's side, and `claims` are the record's claims.
When the item lists several claims, apply the rubric to each; the control is valid when it is valid
for at least one of them.

## What you decide

- `mark`: `valid` or `invalid` by the rubric; `cannot_mark` when the passage does not let you
  decide.
- `reason`: one or two sentences: what in the passage decides the mark.
- `quotation`: the words of the passage, copied exactly as they stand, that support the mark; the
  empty string when the mark is `cannot_mark` and no words bear on it.

## Output

Return one JSON object that fits the schema given with these instructions. Write nothing outside
the JSON.
