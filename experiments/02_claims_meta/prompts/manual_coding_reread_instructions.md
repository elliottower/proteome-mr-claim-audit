# Manual coding of dataset names: instructions for rereading a disagreement

Two checks of a row gave different answers. You reread the paper's passages and settle the row.
You work under `prompts/manual_coding_coder_instructions_v6.md`: read it first, in full. Its
rules decide every row here, the settled rules (A to I4, C2 to C5) and the order of decision
included. This file only says what is different for a reread.

## What you receive

For each paper of your share:

- its input file, as before: every row of the paper with its passages and reference entries;
- its disagreement file, `<file name>.disagreement.json`: the rows of the paper on which the two
  checks differ, each with `answer_1` and `answer_2` (a value, its unresolved category when it
  has one, and the sentence that answer quoted). You are not told which check gave which
  answer, and the order carries no meaning. Do not try to find out;
- `dictionary_definitions.csv`, and these two instruction files.

You open nothing else: no attempt file, no gate file, no answer file of the second check, no
other coder's folder, no queue, registry, summary or result file. You fetch nothing.

## What you do, one paper at a time

1. Read every passage of every row of the paper in full, not only the rows in disagreement and
   not only the two quoted sentences: every sentence, every table row line, every reference
   entry.
2. For each row in disagreement, decide the row from the passages under the rules. The two
   answers are two readings to weigh, not two options to choose between: the value that the
   passages support may be either of them or neither.
3. A row you cannot settle stays unresolved: `not_stated_in_source` with the reason the rules
   give (`release_not_identified` or `conflicting_identifiers`). Never the closest release,
   never a split of the difference.
4. Pin before you write a value that is a dictionary row or
   `source_names_dataset_absent_from_dictionary`. Claim ids end in `_r`: `<side>_<k>_r` for the
   sentence and `<side>_<k>_r_ref` for a reference entry.

       env -u CITATIONS_HOME citations pin <the passage's claims_file> --id <claim id> --quote "<the sentence>"

   If the tool refuses the sentence as ambiguous, from `experiments/02_claims_meta`:

       uv run scripts/pin_passage_occurrence_v2.py --input <the input file> --row <side>_<k> \
           --passage <passage id> --sentence <n> --id <claim id>

   A sentence already pinned for an earlier attempt is pinned again under the `_r` id. Leave
   every earlier pin as it is.
5. Write the paper's resolution file before you open the next paper.

## Output, one file per paper

The share list gives its exact name (`write_as`). For the input file `12345678.json` it is
`resolutions/12345678.resolution.json`, never `12345678.json.resolution.json`.

    {"record_id": "<as in the input>", "coder_id": "<your coder id>",
     "rows": [
      {"row": "<side>_<k>, as in the disagreement file",
       "resolved_value": "<dictionary row name | not_stated_in_source | source_names_dataset_absent_from_dictionary>",
       "unresolved_reason": null,
       "resolution_note": "<one line: what in which sentence settles the row, or why it cannot be settled>",
       "identification_basis": "<as in the coder instructions, null when unresolved>",
       "source_read": "<the source_read of the passage holding the quoted sentence>",
       "passage_id": "<the passage; <side>_<k>:<passage id> for a passage of another row, rule I2>",
       "quote": "<the pinned sentence>",
       "citations_claim": "<the passage's claims_file>#<claim id>",
       "companion_source": false,
       "reference_label": null, "reference_quote": null, "reference_citations_claim": null,
       "dataset_named_in_source": null}]}

- One entry for each row of the disagreement file, in its order, and no other row.
- An unresolved row gives `unresolved_reason` (`release_not_identified`,
  `conflicting_identifiers`, or `dataset_absent_from_dictionary` for the absent value) and, for
  `not_stated_in_source`, needs no quote or pin (leave those fields null).
- Every row has a `resolution_note`.

## After you

The machine gates of the coder instructions run on every resolved row. A resolved value that
fails a gate is unresolved: it is not sent back. Both original answers stay in the table beside
your resolution.
