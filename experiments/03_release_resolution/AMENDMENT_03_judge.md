# Amendment 3: a third model as judge of disagreements and of the audit

Amendment to `experiments/03_release_resolution/PREREG.md` (frozen 10 October 2026, registered at
https://osf.io/2s479), after Amendments 1 and 2. It takes effect when the plan's log names
the sha256 of this file. Access level: SA1 is coded and gated; of its
answers only counts are known (`outputs/sa1_gate_2026-10-13.json`): 657 rows, 162 on which the two
models differ, 495 on which they agree, one gate failure per model. No estimand has been computed,
and no row has been adjudicated.

## Why

The plan gives every disagreement and a 10% audit of agreements to the author (§Study design,
Checks). SA1 alone yields 162 disagreements and an audit of 50 rows, each needing the record's
sources to be read. Stage A and stage B will yield comparable numbers on longer sources. A single
author cannot read some 200 records per pass with the care the check requires, so the check as
registered would be done badly or not at all. A third model of a third family takes the first
pass, and the author's reading is kept for the rows it cannot settle and for a seeded test of
its agreement with him.

## What changes

**1. The judge** (§Study design, Checks, rows "adjudication" and "audit of agreements"). Gemini
3.1 Pro (Google, `gemini-3.1-pro-preview`), a family different from both coders, called through
its API with no tools and no web access, the model string returned recorded with every response.
Per row it receives:
- the same sources the coders received for that record in that pass (the abstract in SA1; the
  abstract and full texts in stage A; with the cut supplements in stage B);
- the row's fields as the coders received them;
- for a disagreement: the two answers, labeled Answer 1 and Answer 2 in the page's seeded order,
  without the models' names, each with its gate verdict;
- for an audit row: the agreed answer and its gate verdict.

It answers, in a frozen schema:
- for a disagreement: Answer 1, Answer 2 or neither; for an audit row: correct, substantive
  error (a wrong row, a wrong role or a wrong attribution state) or other issue;
- a confidence between 0 and 1;
- `needs_human`, true or false;
- a reason, and a quotation from the sources supporting its choice.

Its prompt (`prompts/judge_prompt.md`) and schema (`prompts/judge_schema.json`) are frozen, and
their sha256 logged, before the first judge request.

**2. What the author reads.** A judge decision stands alone unless the row goes to the author.
A row goes to the author when any of the following holds:
- `needs_human` is true;
- the confidence is below 0.80;
- the judge answers neither (a disagreement), or substantive error or other issue (an audit row);
- the answer the judge chose fails the gate;
- the judge's quotation does not stand verbatim in the sources it received;
- the judge's request fails twice.

The author decides these rows on the registered pages, with the judge's answer hidden, and his
decision is the final code. On an audit row, a substantive error counts toward the registered
escalation only when the author's blind review finds it; the judge's call alone never counts.

**3. Calibration of the judge, by task.** The judge's two tasks are calibrated apart, in each
pass: disagreement adjudication, over the disagreements it decided alone; and agreement audit,
over the audit rows it decided alone (marked correct). In each task, the rows it decided alone
are put in order of row identifier and shuffled by `random.Random(seed).shuffle`, with the seeds
of the table below, fixed by this amendment before any judge request. The author marks the first
20 of that order (all of them if fewer than 20), blind to the judge's answer, and the two are then
compared:
- 0 or 1 differences: the task passes.
- 3 or more: the task fails.
- exactly 2: the author marks the next 20 of the same order, and the task passes only with at most
  3 differences among the 40.

| pass | disagreement adjudication | agreement audit | escalated review of agreements |
|---|---|---|---|
| SA1 | 20261018 | 20261019 | 20261020 |
| stage A | 20261021 | 20261022 | 20261023 |
| stage B (with the escalation of Amendment 2) | 20261024 | 20261025 | 20261026 |

The agreement in each task and pass is reported with its exact binomial 95% interval.

**4. Consequences of a failed task.**
- **Disagreement adjudication fails:** no lone decision of the judge in that task stands; each
  such row is not accepted and counts as unresolved, as the plan treats any row not accepted,
  unless the author adjudicates it.
- **Agreement audit fails:** the judge's audit decisions of that pass do not stand; the author
  reviews the whole registered audit sample of that pass, blind, and the registered escalation
  rule is applied to his review.
- **Escalated review of agreements:** when the registered escalation is triggered, the judge
  reviews every agreed row of that pass under items 2 and 3, as its own task. If that task fails,
  each row the judge reviewed alone is not accepted and counts as unresolved, unless the author
  adjudicates it.

**5. Order and cost.** The judge runs after a pass is coded and gated, and before the author's
pages for that pass are built. Its requests count against the ceiling of the stage they serve.
SA1's judge requests count against the ceiling of 100 US dollars for stage A and SA1.

**6. The Maximum claim** changes: "the author's adjudication of every disagreement and audit of
a seeded 10% of agreements" becomes "a third model's adjudication of every disagreement and of a
seeded 10% of agreements, with the author deciding every row it flagged or could not settle and
a seeded sample of its lone decisions in each task and pass, and its agreement with the author
on those samples reported". It cannot state that the author read every disagreement.

## Foreknowledge

Seen before this amendment: the SA1 counts above, the SA1 spend, and the counts of the two
adjudication pages (162 and 50 rows). The author opened the pages and marked no row. Two external review rounds of earlier drafts were
read and their points are applied here; the second confirmed this text.
