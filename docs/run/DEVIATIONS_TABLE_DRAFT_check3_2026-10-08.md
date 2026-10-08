# Draft text for the deviations table: third check of the manual dataset coding

Draft, not polished. It follows the wording the reviewer of round 17 asked for, adjusted to
the facts on record. The third check is a seeded author spot-check. It is not independent human
validation and not completion of the registered procedure.

> The registered procedure required the author to confirm every accepted dataset mapping against
> its pinned sentence. This was replaced by automated quotation-provenance and
> release-identifier checks for all 196 accepted mappings, supplemented by a seeded random
> sample of 20 that the author marked as confirmed. Six of those confirmations followed
> discussion of the row with the coordinating AI session. For the other fourteen the record
> holds the author's marks and his answer when asked how he had gone through them, and no
> measure of the depth of review. The rules for what a mark would mean were committed before
> the marks were saved, but not demonstrably before the author began to inspect the rows. After
> the spot-check had closed the author voluntarily marked further rows as confirmed: 27 of a
> seeded sample of 30, the first 50 rows of a page listing every row he had not yet marked,
> and 2 rows on a page of reference-based rows flagged mechanically as harder; neither page
> was a random sample. In all he marked 99 of the 196 mappings, each as confirmed, and 22 of
> those a second time on the page of flagged rows. Neither the spot-check nor the voluntary marks are treated as an independent
> reference standard, and no error-rate bound is reported from them.

## What the paper must also state

- **Unit.** A row is one entry of the dataset-coding queue (one paper, side, and dataset name
  as written). It is not a paper, a dataset or a claim.
- **What 196 of 872 means.** It concerns the queue of names the automatic mapping left
  unresolved, not the mapping coverage of the census. For scale, on all 14,053 claim records
  the automatic mapping gave: unique 503 names, release ambiguous 6,494, unmatched 5,049, not
  stated 19,543 (the unit there is a name on a claim record). The count of names mapped
  automatically among the claims of the registry waits for the assembly.
- **The unresolved categories.** 435 release not identified, 15 conflicting identifiers and 226
  dataset named but absent from the study's dictionary describe this coding process. They are
  not all reporting defects of the papers: a name absent from the dictionary is a limit of the
  dictionary.
- **Agreement.** The two model checks gave the same value for 821 of 872 rows; the 51
  disagreements were then adjudicated by rereading (3 coded, 19 absent, 29 not stated).
- **The two model checks are not independent.** Both are of one model family, and the model of
  the second check is recorded on the author's statement (the interface's output does not name
  it).
- **What the machine check tests.** That the pinned sentence, or a reference entry verified by
  DOI, holds an identifier of the coded dictionary row that no other candidate row has. For 144
  of the 196 rows "candidate" means the row's own retrieved shortlist; for 52 it means every
  dictionary row of that side. Of the 144, 136 hold an identifier unique among all rows of the
  side, 7 pass by a numbered release written in another form or by a citation with a separating
  attribute, and 1 holds an identifier that a dictionary row outside its shortlist also has. The
  check cannot establish that the sentence attributes the analysed data to that source.
- **Software tests.** A passing test suite supports the behaviour of the software, not the
  semantic correctness of the mappings.

## Facts behind the text (plan log, 8 October 2026)

- Spot-check: seed 20261008, 20 of 196 table lines; 20 of 20 marked yes; marks file sha256
  33491574…795dacc. The six discussed rows are table lines 23, 103, 113, 182, 184 and 192.
- Further voluntary sample: seed 20261010, 30 of the 176 remaining lines; 27 yes, 3 blank, no
  no; marks file sha256 4e9ee553…dad719c. One card of it was asked about and explained after
  the file was saved; it was one of the 3 blanks.
- Marks on the page of rows not yet marked: the page listed the 149 unmarked rows, the 3 left
  blank in the sample of 30 first, then the reference-based rows, then the others, by table
  line. The author worked from the top and marked the first 50 yes (49 reference-based, 1
  other); 99 unmarked; no no. The page was written at 03:51:26Z; a first save at 03:54:14Z
  held 30 marks and a second at 03:56:10Z held 50 (sha256 636244e4…2d127b04). Two of the three
  earlier blanks he decided before the coordinating session said anything about them; the
  third had been explained to him before he marked it. He stopped at 50.
- Second look: a page of 55 reference-based rows, first the 35 flagged by fixed mechanical
  rules as harder (family word of the coded dataset absent from the pinned sentence; no
  citation mark or first-author name in the sentence; several references cited together; the
  sentence begins with a back-reference word; the dictionary source shared by several rows of
  the side), then the 20 unflagged rows he had not marked. He marked the first 24 cards yes,
  all flagged, and stopped: 22 were rows he had already marked yes and 2 were new; 31 cards
  unmarked; no no. Page rewritten 04:00:44Z, marks saved 04:04:31Z (sha256
  930129ab…97ef9913). One of the 24, a second mark, followed discussion of the card with the
  coordinating session. Of the 35 flagged rows: 24 marked yes on this page, 6 marked once
  only (elsewhere), 5 unmarked.
- Rows the author has marked: 99 of 196, all yes; 73 of the 98 rows that rest on a reference
  entry and 26 of the 98 others. The remaining 97 are recorded as machine-checked only. Of the
  99 first marks, 7 followed discussion of the row with the coordinating session (6 in the
  spot-check, 1 on the page of unmarked rows).
- The author's description of his earlier fast passes is recorded verbatim in the plan log; no
  further claim is made about how he read.
- A second further draw (seed 20261011, 30 reference-based rows) was made and not used.
- The author's answer about how he read the fourteen is recorded verbatim in the plan log; no
  further claim is made.
- Three versions of the manual mappings are registered for the analysis: all 196 (amended
  primary), the author-marked rows only (a transparent restriction, not a gold standard), and
  none (the registered sensitivity analysis).
