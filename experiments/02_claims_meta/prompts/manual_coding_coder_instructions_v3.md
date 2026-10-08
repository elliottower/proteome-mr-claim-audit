# Manual coding of dataset names: instructions for a coder

You are one of four coders. Each paper has one coder; you code every row of every paper in your
folder and no row of any other paper. You do not communicate with the other coders.

## What you receive, and nothing else

Your folder is `outputs/manual_coding/2026-10-03/coders/<your coder id>/` (paths are relative to
`experiments/02_claims_meta`).

- `input/<file name>.json`, one per paper. For each row: the side (`pqtl` or `outcome`), the
  dataset name as written, its mapping state, its candidate dictionary rows by name, and its
  passages. A passage holds its sentences (or one table row line with its caption and column
  headers), its section title, the document it is from (`source_read`, and the `claims_file`
  its sentences are pinned in), and, where one of its sentences carries a linked citation, the
  linked entries of the paper's own reference list (`references`: label, entry, DOI, PMID, PMC
  identifier).
  A passage's `source_read` is `full_text`, `abstract`, or
  `abstract_fallback_after_fulltext_no_match`: for a full-text paper whose body gave no passage
  for a row, the same rule was applied to the paper's abstract, and the passage found there is
  what you are given. A row with no passage in either has the status `no_local_passage_found`.
- `../dictionary_definitions.csv`: the definition of every dictionary row (side, name, aliases,
  release, participant sources, ancestry, sample size, platform, source citation, source
  identifier).
- This file.

You open no other file of the study: no abstract or full text beyond the passages given, no
claim, registry, queue, summary or result file, no other coder's folder. You fetch nothing: no
supplementary file, no cited paper, no web page. You are not given, and must not look for, the
protein–outcome pair a row belongs to, any other paper's dataset assignment, any dataset
relation class, or any count or aggregate.

## The registered rules (PREREG.md, §Manual coding of dataset names)

> 2. *Source read:* the paper's methods or data passage, in the Europe PMC open-access full
> text where there is one, else the abstract. When neither states the release or platform the
> row stays unresolved and is counted.
>
> 3. *Record:* the quoted sentence pinned with `citations`, the dictionary row coded [...].
>
> 4. *Scope:* dataset and platform identity only; never direction, significance, eligibility,
> protein or outcome.
>
> 6. *What the coder and the checker see:* Manual coders and checkers receive only the
> unresolved dataset string, its local paper passage and candidate dictionary definitions; they
> do not receive the canonical protein–outcome pair, other families' dataset assignments, the
> resulting relation class, or any H1/H2 aggregate.
>
> 7. *Rules for a code:* [...] The source must identify the release: a name is never coded to
> the closest available release, and a row whose source does not identify one is `unresolved`.

A row where the coded value is taken from a companion source and not from the pinned sentence is
recorded as such (item 5).

## When the source identifies a release

> The source identifies a release when its local passage or explicitly attributed companion
> source reports a release identifier, accession, uniquely identifying citation, or a
> conjunction of release-specific attributes that matches exactly one candidate row and
> conflicts with none. Sample size or platform alone is insufficient unless the registered
> dictionary establishes that the value is release-specific and the passage clearly states that
> it describes the analysis dataset.

- Unique release, version or accession: code it.
- Unique source DOI tied to one candidate release: code it.
- Exact N plus platform, panel or analysis year, uniquely matching one row: code it.
- N alone: unresolved.
- Platform alone: unresolved.
- Approximate N: unresolved.
- Post-exclusion analytic N differing from the release N: unresolved unless another identifier
  settles it.
- Conflicting identifiers: unresolved and flagged for adjudication.

## When a citation identifies a release (`companion_source`)

A citation resolves a row only when all six hold:

1. The local sentence explicitly attributes the analysis dataset to that citation.
2. The numbered reference resolves unambiguously to one bibliographic record.
3. That record identifies exactly one candidate dictionary row.
4. The local paper does not report conflicting release information elsewhere.
5. Both the attribution sentence and reference entry are pinned.
6. The row is flagged `companion_source`.

If the cited paper supports several candidate releases, the row remains unresolved. A citation
to a general cohort description does not identify a particular GWAS or pQTL release merely
because that cohort produced it. The only companion source is an entry listed under
`references` in the passage that holds your quoted sentence.

The entry must be verifiable against the dictionary row's `source_identifier`: by its DOI; if it
has no DOI, by its PMID; if it has neither, by its PMC identifier. An entry whose identifier is
not one of the dictionary row's, or that has none of the three, cannot carry a code: the row is
unresolved (`release_not_identified`) unless the sentence itself identifies the release. There
is no exception to this.

## Rules settled on review (they refine the rules above; where they differ, these govern)

A. A release written in another form is that release: other spacing, case, hyphen or
   underscore; an ordinal for a cardinal ("the 12th release", "the twelfth release"); or one of
   the words R, round, release, version, freeze, data freeze with the same number ("DF 11",
   "Data Freeze 11", "release 11", "R11"), when it modifies the dataset name and no other
   identifier conflicts. "Latest release" and the like are not identifiers.
B. A valid repository accession (for example a GWAS Catalog or OpenGWAS identifier) that no
   dictionary row lists is `source_names_dataset_absent_from_dictionary`.
C. The authors' own GWAS of a biobank's individual-level data is
   `source_names_dataset_absent_from_dictionary` when the passage defines the analysis (the
   source with a phenotype definition, an application number, an analytic sample or a described
   procedure). "UK Biobank data" with only a post-exclusion N is `release_not_identified`.
D. A cohort or consortium name alone never identifies a release, even when the dictionary has
   exactly one row for that name.
E. A citation verified by DOI, PMID or PMC identifier whose source has several dictionary rows,
   together with an attribute of the same analysis dataset that matches exactly one of them
   (ancestry, subcohort, panel, platform, exact release-specific N), with no conflict, is coded,
   `companion_source`. The attribute must be in the pinned sentence.
F. Attribution may cross adjacent sentences when they form one description of the dataset. One
   grouped citation after several cohorts maps to none of them unless order or wording makes
   the mapping explicit.
G. An accession absent from the dictionary stays absent
   (`source_names_dataset_absent_from_dictionary`) even when its counts equal those of a listed
   row.
H. A second sample size is a conflict only when it purports to be the release-defining N of the
   source GWAS and exactly identifies another release. A post-QC, complete-case,
   ancestry-subset, effective, protein-specific, variant-specific, maximum or post-exclusion N
   is not a conflict.
I1. Exact counts with a cohort name alone are `release_not_identified`.
I2. A sentence given under another row of the same paper may be used when it explicitly refers
    to this row's dataset, and never only because two rows share a generic name. Record the
    passage actually used: write `passage_id` as `<side>_<k>:<passage id>` (the other row and
    its passage) and pin the sentence in that passage's claims file under this row's claim id.
I3. An accession inside a dictionary row's registered range, with an ancestry or counts that
    row does not allow, is `conflicting_identifiers`, after first deciding what the discrepant
    number is (rule H).
I4. A sentence that occurs twice in its source does not make the release unidentified, but
    `citations pin` refuses it. Use another sentence that identifies the release if there is
    one. If there is none, write the row `not_stated_in_source` with `release_not_identified`
    and begin `coder_note` with `PIN REFUSED, SENTENCE OCCURS TWICE:`; these rows are counted
    apart.

## Further rules

- Conflict means unresolved: when the local sentence, a reference entry or two passages of the
  paper disagree, the row is unresolved with the reason `conflicting_identifiers`.
- Never the closest release. Never a guess from the paper's year or from what such papers
  usually use.
- Never carry a code from one paper to another because the dataset string is the same. Each
  paper is coded from its own passages.
- Every row is coded on its own. Two rows of one paper may rest on the same sentence; each
  still gets its own row and its own pin.
- A coded value is the exact `name` of a dictionary row of the row's side. It is normally one
  of the row's candidates; a dictionary row outside them is allowed when the passage
  identifies it, and is flagged by the gates for the later checks.
- A candidate written `unlisted release of ...` or `unlisted combination of ...` is not a
  dictionary row and cannot be coded.

## The three values

| value | when | `unresolved_reason` |
|---|---|---|
| the dictionary row's `name` | the passages identify exactly that row under the rules above | none |
| `not_stated_in_source` | the passages do not identify one row | `release_not_identified`, `conflicting_identifiers`, or `no_local_passage_found` (only for a row whose `status` is `no_local_passage_found`) |
| `source_names_dataset_absent_from_dictionary` | the passages name the dataset used and the dictionary has no row for it | `dataset_absent_from_dictionary` |

For `source_names_dataset_absent_from_dictionary`, pin the sentence that names the dataset and
give the dataset as that sentence writes it (`dataset_named_in_source`, a string that occurs in
the quoted sentence).

## Pin before you write the code

Pins are made from `outputs/citations/manual_coding_2026-10-03/`. A sentence is pinned in the
claims file its passage names (`claims_file`); a reference entry in the paper's reference-list
claims file (`source.references.claims_file` in the input file).

    env -u CITATIONS_HOME citations pin <the passage's claims_file> --id <claim id> --quote "<the sentence>"
    env -u CITATIONS_HOME citations pin <source.references.claims_file> --id <claim id> --quote "<the entry>"

- The quote is one whole sentence exactly as it stands in the passage's `sentences` (or the
  whole table row line); a reference entry is the whole `entry` text.
- Claim ids: `<side>_<k>` for the k-th row of that side in the paper's file, and
  `<side>_<k>_ref` for its reference entry.
- A pin that `citations` refuses is not written and the row is not coded from it. Do not edit a
  claims file by hand. A sentence already pinned for another row is pinned again under the new
  row's id.
- Only after the pin is written do you write the row's value.

## Output, one file per paper, written when the paper is finished

`codes/<file name>.attempt1.json` (the same file name as the input file):

    {"record_id": "<as in the input>", "coder_id": "<your coder id>", "attempt": 1,
     "rows": [
      {"side": "pqtl", "name_as_written": "<as in the input>",
       "value": "<dictionary row name | not_stated_in_source | source_names_dataset_absent_from_dictionary>",
       "unresolved_reason": null,
       "identification_basis": "<release_identifier | source_identifier | unique_citation | exact_n_with_platform_or_year | reference_entry>",
       "source_read": "<the source_read of the passage holding the quoted sentence>",
       "passage_id": "<the passage holding the quoted sentence>",
       "quote": "<the pinned sentence>",
       "citations_claim": "<the passage's claims_file>#<claim id>",
       "companion_source": false,
       "reference_label": null, "reference_quote": null, "reference_citations_claim": null,
       "dataset_named_in_source": null,
       "coder_note": "<one line: what in the sentence identifies the row, or why it is unresolved>"}]}

- One entry per row of the input file, every row, in the input's order.
- An unresolved row has `identification_basis` null; a `not_stated_in_source` row needs no
  quote, passage or pin (leave them and `source_read` null).
- A `companion_source` row gives `reference_label`, `reference_quote` (the entry) and
  `reference_citations_claim` (`<source.references.claims_file>#<claim id>`), with
  `identification_basis` `reference_entry`.
- Write the file once per paper, when all its rows are done, before opening the next paper. A
  stop then loses at most the paper in hand. Never overwrite an attempt file.

## Machine gates

After your files are written, `scripts/manual_coding_gates_v2.py` checks each attempt: the
value and reason, that the quote is a sentence of a passage given for that row (or of the
passage of another row that you named under rule I2) and is the pinned quotation in that
passage's claims file, that the pinned material holds an identifier of the coded row that no
other candidate has (or its numbered release in another written form, or its exact sample size
with its platform or year), and for a companion row that the entry's DOI, else its PMID, else
its PMC identifier, is one of the dictionary row's source; an entry with none of them fails. For
a companion row whose source has several dictionary rows, the pinned sentence must hold the
attribute that separates them (rule E). A paper that fails comes back to you with
its gate file (the one under `gates_v2_for_coder/`, which names the failing rows and not their
values); you reread its passages and write `codes/<file name>.attempt2.json` (then 3, and
so on) with every row of the paper. Earlier attempts and gate files stay. A row that cannot
pass is unresolved, not forced.
