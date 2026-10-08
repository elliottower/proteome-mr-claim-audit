# Draft text for the deviations table: third check of the manual dataset coding (every coded row marked)

Draft, not polished, written after the author had marked every coded row. It replaces
`DEVIATIONS_TABLE_DRAFT_check3_2026-10-08.md`, which is kept as it stood when 124 of 196 rows
were marked. The third check is the author's own reading of every coded row, in several
sittings on one day. It is not independent human validation, and no error rate is estimated
from it.

> The registered procedure required the author to confirm every accepted dataset mapping against
> its pinned sentence. Every one of the 197 accepted mappings was checked by automated
> quotation-provenance and release-identifier checks, and the author marked every one as
> confirmed, in several sittings: first a seeded random sample of 20; then, voluntarily, a
> further seeded sample of 30 (27 marked, 3 left blank), the first 50 rows of a page listing
> the rows he had not yet marked, the 55 rows of a page of reference-based rows that put those
> flagged mechanically as harder first (27 first marks and 28 second marks), and the last 72
> unmarked rows; and the one mapping coded later for a row the rebuilt queue added. Seven first
> marks followed discussion of the row with the coordinating AI session (six in the sample of
> 20, one on the page of unmarked rows), and one second mark did. The rules for what a mark
> would mean were committed before the marks of the sample of 20 were saved, but not
> demonstrably before the author began to inspect the rows. The record holds when each page
> was written and when each set of marks was saved, the author's description of his earlier
> passes in his own words, and no measure of the depth of review. The author is not an
> independent reader, and his marks are not treated as an independent reference standard.

## What the paper must also state

- **Unit.** A row is one entry of the dataset-coding queue (one paper, side, and dataset name
  as written). It is not a paper, a dataset or a claim.
- **What 196 of 872 means** (197 of 876 in the queue rebuilt for the amended primary
  analysis). It concerns the queue of names the automatic mapping left unresolved, not the
  mapping coverage of the census. For scale, on all 14,053 claim records
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
- Second look, completed: a second save at 11:55:27Z (sha256 84dd61df…1740db9d) holds 55 of
  55 yes, the 24 of the first save unchanged and 31 added; no no, no note. Read whole from
  the table as it stood before the second look: 27 first marks (7 flagged rows, 20 unflagged)
  and 28 second marks; all 35 flagged rows have a yes on this page.
- Last 72 rows: a page of the 72 lines with no yes in any saved marks file (44 resting on a
  release number, 20 on an exact sample size with platform or year, 5 on an accession or
  source address, 3 on a citation in the sentence), written at 12:14:56Z; marks saved at
  12:19:23Z (sha256 62aeade9…f84d3709): 72 of 72 yes, no no, no note.
- The new coded row (table line 197): put to the author on its own page; yes, no note, saved
  12:12:02Z.
- Rows the author has marked: 196 of the 196 coded rows of the first run and the 1 coded row
  added by the rebuilt queue, 197 of 197, all yes. No row was marked no in any sitting. Of the
  197 first marks, 7 followed discussion of the row with the coordinating session (6 in the
  spot-check, 1 on the page of unmarked rows); one second mark did.
- The author's description of his earlier fast passes is recorded verbatim in the plan log; no
  further claim is made about how he read.
- A second further draw (seed 20261011, 30 reference-based rows) was made and not used.
- The author's answer about how he read the fourteen is recorded verbatim in the plan log; no
  further claim is made.
- Three versions of the manual mappings were fixed for the analysis before any assembly with
  codes: all mappings, the author-marked mappings only, and none (the registered sensitivity
  analysis). With every coded row marked, the table of the author-marked mappings is byte for
  byte the table of all mappings; it is built under its label and reported as identical.
