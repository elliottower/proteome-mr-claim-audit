# Amendment 2: staged reading of full texts and supplements

Amendment to `experiments/03_release_resolution/PREREG.md` (frozen 10 October 2026, registered at
https://osf.io/2s479), after Amendment 1. It takes effect when the plan's log names the sha256 of
this file. Access level: results seen (the results of Paper 1). Nothing
of this stage has been coded and no model request has been made.

## Why

With the amended cut, the full-text pass is priced from the packets themselves at 318.36 to
429.15 US dollars for coding alone (`outputs/fulltext_layouts_2026-10-13.json`), with 1,500
output tokens a request and no thinking or reasoning output, against a ceiling of 350. Most of
that is supplements: 136 records hold a readable supplement, and their requests carry 255.0M of
the 265.7M packet characters (`outputs/staged_design_pricing_2026-10-13.json`). The frozen C1
draw gives 147 of its 150 controls from one supplement of one record, with 3 distinct expected
rows (`outputs/c1_controls_2026-10-13.json`).

## What changes

**1. Two stages of coding** (§Study design, What the models read; Order).

- **Stage A.** Every queue row is coded from the record's abstract and full texts (routes R1 and
  R3), with no supplement, by both models under the registered checks: the gate, the author's
  adjudication of every disagreement and the audit of a seeded 10% of agreements. A record with
  no full text is coded from its abstract alone.
- **Stage B.** After every stage A code is committed, a row is still unresolved when its
  accepted code holds any unresolved reason. Stage B reads the supplements, under the cut of
  Amendment 1, of the records named below, and only those records. Every row of such a record is
  coded again from the abstract, the full texts and the supplements, under the same checks.
  - **Unresolved records:** every record that holds an unresolved row and a readable supplement.
  - **Resolved-record audit:** a sample of 30 records whose rows are all resolved and that hold a
    readable supplement, drawn by `random.Random(20261015).sample` over those records in sorted
    order of record identifier; all of them if fewer than 30.
  - **Escalation:** if 2 or more audited records change, in any row, the identified release, a
    role, the attribution state or the presence of `conflicting_identifiers` between stage A and
    stage B, stage B extends to every record with a readable supplement.
- **Final code.** For a record that enters stage B, its checked and adjudicated stage B code is
  the final code; stage A and stage B release assignments are not merged. The stage A code is
  kept as an intermediate code, and each row's transition from it is classed `confirmed`,
  `refined`, `contradicted` or `unresolved`, as the plan classes the transition from abstract to
  full text. Passages are merged by union only within one stage B packet's parts.
- **Stage B decision.** Stage B is decided by a frozen rule on cost alone, with no approval by
  the author after stage A. When stage A is committed, the pipeline writes the reserved upper
  bound of stage B for the unresolved records and the audit, with the diagnostic. The bound prices
  every packet at the preflight's characters per token, with output per request set to the larger
  of 6,000 tokens and the mean output (thinking and reasoning included) that each model billed per
  request in stage A. Stage B runs if that bound is at most 470 US dollars and the spend of stage
  A and SA1 plus that bound stays at most 560 US dollars; otherwise stage B does not run.
- **Escalation cost.** The escalation is incremental: a record already read in stage B is not
  requested again, and the escalation's bound covers only the records with a readable supplement
  not yet read. If the audit triggers the escalation, the pipeline writes that bound, priced as
  above. The escalation runs if the bound of stage B and the escalation together, which is the
  cost of reading every record with a readable supplement once, with the diagnostic, is at most
  470 US dollars, and the spend of stage A and SA1 plus that total stays at most 560 US dollars;
  otherwise it does not run.
- **Estimands.** H2-R, H2b-R, H1-R and the secondary analyses are computed once, after the last
  stage that runs. The paper states whether stage B ran, whether the escalation was triggered and
  whether it ran, with the number of records each read. The primary analysis is:
  - the staged estimate, when stage B ran and the audit did not trigger the escalation, or when
    the escalation ran;
  - stage A, when stage B did not run, or when the audit triggered the escalation and the cost
    rule prevented it from running. Results from the records read in stage B are then reported
    only as a labeled sensitivity analysis, and no staged estimate is presented as field-wide.

**2. Every request carries the full text** (§Study design, Input limit). When a record's sources
exceed one request, every request of the record holds the abstract and every full text, and the
supplement parts are sized to the room that leaves. The fixed prompt and the carried abstract and
full texts are cached after the first request.

**3. C1 becomes C1-A** (§Research questions, C1; §Study design, C1, step 5). The control tests
the stage A reading only: abstracts and full texts. Supplement reading has no positive control;
the resolved-record audit of stage B is its safeguard. The frozen scanner and its patterns are
unchanged, and so are the thresholds of C1 and their gate on the estimands; the draw becomes:

- candidates: the scanner's matches in the text stage A reads (routes R1 and R3);
- one candidate per record and identifier, the first in sorted order of source and unit;
- shuffled by the frozen seed (20261011), then taken in that order, at most 5 per record, at most
  150 in all, with the frozen minimum of 50.

Applied to the frozen scan, the rule gives 70 controls in 51 records, at most 4 from one record:
64 outcome-side and 6 pQTL-side; 40 numbered releases, 25 accessions and 5 source identifiers;
18 distinct expected rows. These counts are computed consequences of the frozen rule and the
retrieved sources, not expected results. A drawn control is a row of its record in stage A:
- its side is the expected row's side;
- its name as written is the identifier as the source writes it;
- its candidates are every dictionary row of the side;
- for an outcome-side control, its outcomes as written are those of the record's outcome-side
  rows.

The packet orders all rows by row identifier. The manifest controls (31 packets) run with stage
A and are reported apart.

**4. C2.** The removed-chunk miss-rate diagnostic of Amendment 1 applies to stage B. Its
population is the frozen population of Amendment 1 restricted to the records stage B reads; its
sample is 400 chunks of that population, or all of them if fewer, with the seeds of Amendment 1.
Without stage B there is no cut text, and the paper reports that no supplement was read.

**5. The cost ceiling** (Data collection procedures, Cost approval). The ceiling for stage A
and SA1 is 100 US dollars. Stage B runs under the rule of item 1, with 470 and 560. The spend of
every stage counts against one ledger. As priced at the preflight's characters per token, stage
A and SA1 together cost:

| output tokens a request | stage A and SA1 (US dollars) |
|---|---|
| 1,500 | 42.07 |
| 3,000 | 58.03 |
| 6,000 | 89.95 |

Thinking and reasoning output is billed as output tokens. The 6,000 line is the one the ceiling
is set against. The run stops before a request whose reserved bound would cross the ceiling.

Stage B, priced from the same packets (`outputs/audit_escalation_pricing_2026-10-13.json`), in
US dollars for both models at 1,500 / 3,000 / 6,000 output tokens a request:

| part | cost |
|---|---|
| the audit, upper bound (the 30 most expensive of the 136 records) | 366.37 / 384.27 / 419.85 |
| the audit, expected (mean per record times 30) | 86.80 / 91.69 / 100.94 |
| the escalation (all 136 records) | 393.51 / 415.65 / 457.59 |
| the removed-chunk diagnostic, 400 chunks | 9.03 |

**6. The Maximum claim** gains one sentence: "Supplements were read only for the records the
staged rule named and only when the frozen cost rule let stage B run; the paper states whether
they were read, whether the resolved-record audit triggered the escalation, and C1-A tests the
reading of abstracts and full texts only."

## Foreknowledge

Seen before this amendment: the counts of Amendment 1 and of its run (the cut, containment, the
removed-chunk population); the queue's counts; the frozen C1 draw and the stratified draw above,
by record, side, identifier type and expected row; the token counts of the free preflight; the
prices of both full-text layouts, of the staged design, of the audit and of the escalation; three
external review rounds of earlier drafts, whose points are applied here; the third confirmed
this text. No source was read for content, no row was coded and no model request was made.
