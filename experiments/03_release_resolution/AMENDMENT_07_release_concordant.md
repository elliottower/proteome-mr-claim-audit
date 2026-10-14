# Amendment 7: rows on which the models agree on the release, settled by rule

Amendment to `experiments/03_release_resolution/PREREG.md` (frozen 10 October 2026, registered at https://osf.io/2s479), after Amendments 1 to 6 and Deviations 1 and 2. It takes effect when the plan's log names the sha256 of this file. Access level: SA1 is coded, judged and calibrated (`outputs/sa1_calibration_2026-10-14.json`, `outputs/sa1_calibration_diagnostic_2026-10-14.json`); stage A is coded and gated by both models, and its agreement counts (`outputs/stage_a_counts_2026-10-14.json`) and the diagnostic of its C1 controls (`outputs/stage_a_control_diagnostic_2026-10-14.json`) have been read. No stage A study-row answer has been read, the number of release-concordant stage A rows is not known, no judge has run on stage A, and no estimand has been computed.

## Why

In the SA1 disagreement calibration the author and the two judges chose differently on 16 of 20 rows. In all 16, both models' answers identified no release; the answers differed only in the attribution state or the unresolved reasons. The author coded such rows by one principle, the more conservative attribution, while the judges applied the rubric's separate attribution field. A disagreement confined to attribution and reasons does not change which release a row has, and sending it to the judges and the author spends their reading on the field the release estimands do not turn on.

## What changes

**1. Release-concordant rows.** In stage A and stage B, after the gate, a row is release-concordant when both models' answers pass the gate and give the same identified release set (empty included), the same role and ancestry for each release, and the same presence or absence of `conflicting_identifiers`, and differ in nothing else than `attribution_state`, `unresolved_reasons`, notes and passages.

**2. Settled by rule.** A release-concordant row is not sent to the judges or the author and does not enter the disagreement calibration. Its accepted code is set by script:
- the release set, roles and ancestry the two answers share;
- the attribution state the more conservative of the two, in the order `unresolved`, then `paper_wide`, then `explicit`;
- the unresolved reasons the union of both answers' reasons, with `attribution_unresolved` added when the attribution state is `unresolved`;
- the passages the union of both answers' verified passages.

**3. Every other disagreement** goes to the judges and the author as in Amendments 3 and 4.

**4. Reported.** The number of release-concordant rows per stage, by the pair of attribution states. Every result that depends on attribution (added rule 1, and the attribution column of the levels of Amendment 6) is also reported with these rows given the less conservative of the two attribution states, so the effect of the rule is shown.

**5. SA1** is not recoded: its calibration stands as scored. The number of SA1 disagreements that were release-concordant is reported, as a count.

## Foreknowledge

Seen before this amendment: the SA1 calibration and its diagnostic (16 of 20 differences, all between answers identifying no release); the author's reasons on his 42 marks; the attribution states and reasons of the two answers on the 16 differing rows. In stage A: the counts of rows on which the two models agree and differ (657 study rows: 510 agree, 147 differ; 70 controls: 45 agree, 25 differ), the C1 counts, and, for the C1 controls only, the diagnostic's classes, the models' reason codes and quotations, and the source context of each control. No stage A study-row answer, judge reason or estimand was read.
