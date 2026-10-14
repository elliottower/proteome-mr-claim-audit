# Deviation 1: the routed SA1 disagreements not adjudicated, treated as missing

Deviation from `experiments/03_release_resolution/PREREG.md` (§Secondary analyses, SA1: "the author's adjudication of every row on which the two models differ") as amended by Amendments 3 and 4. It takes effect when the plan's log names the sha256 of this file. Access level: SA1 (result B, abstract only) is coded, gated and judged; only routing counts are known (`outputs/`, commit a2c5d1f59). No judge choice, judge reason or estimand has been read, and no row has been adjudicated.

## Counts seen

Of 162 SA1 disagreements, the two judges decided 33 alone and routed 129 to the author (all 129 with a judge confidence below 0.80; 56 flagged needs-human; 22 on which the judges chose differently). Of 50 audit rows, 48 were decided alone and 2 routed. With the 40 calibration rows, the author's page holds 171 rows.

## What changes

1. **The 129 routed disagreements of SA1 are not adjudicated.** Each is coded `not_adjudicated_due_to_deviation` and treated as a missing B outcome, not as unresolved: the judges' low confidence shows that this workflow did not settle the row, not that the abstract cannot settle it. These rows never count as resolved or unresolved in B, and never enter SA3 as an unresolved reason.
2. **The author marks 42 rows**, blind to both judges, on one page in the order of seed 20261027: the 2 routed audit rows, the 20 calibration rows of disagreement adjudication (seed 20261018) and the 20 of agreement audit (seed 20261019). Calibration and its consequences (Amendment 3, items 3 and 4) are unchanged: a failed adjudication task makes the 33 lone decisions unaccepted and unresolved, as Amendment 3 states; a failed audit task returns the whole audit sample of 50 to the author.
3. **Reporting.** B and its contrasts are reported as follows:
   - the number and share of SA1 rows coded `not_adjudicated_due_to_deviation`, with their routing reasons;
   - complete-case results: B, and the contrasts A to B and B to C, on the rows with an accepted B outcome;
   - bounds over all rows: each registered count of B and of its contrasts (rows resolved, rows that change state, cells of the 3 by 3 tables of pair classes) is reported with its range over every assignment of each missing row to unresolved or to either coder's answer, the two ends computed separately for each count; the bounds assume an adjudicated row would take one of these three codes, and say so;
   - no statement that the complete-case results are free of bias: the missing rows were selected because the coders disagreed and the judges did not settle them.
4. **Scope.** This applies to SA1 (B) only. Stage A and stage B of Amendment 2, the primary analysis, keep the full routing of Amendments 3 and 4: every routed row there is decided by the author.

## Reason

SA1 is a secondary, source-restricted analysis. The author cannot read 129 rows with the care the check requires for a secondary analysis, and every one of these rows is read again from the full text in stage A, under the full checks. The decision was made on routing counts only.

## Review

Two external review rounds of earlier drafts were read and their points are applied here; the second confirmed this text.
