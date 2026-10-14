# Amendment 4: two judges, one of each coding family, in place of the third-family judge

Amendment to `experiments/03_release_resolution/PREREG.md` (frozen 10 October 2026, registered at
https://osf.io/2s479), after Amendments 1 to 3. It takes effect when the plan's log names the
sha256 of this file. Access level: as for Amendment 3; in addition, the judge
prompt and schema of Amendment 3 were frozen and all 212 judge requests of the abstract-only pass
were refused by the provider (HTTP 402, prepaid credit depleted), so no judge answer exists. No
row has been adjudicated and no estimand has been computed.

## Why

The judge of Amendment 3 was chosen for being of a third family, so that it could not favor
either coder's family. A judge of a third family is not necessarily as strong as the strongest
models of the two coding families. Two judges, the strongest model of each coding family, each
blinded, with a decision standing alone only when they agree, mitigate a family-aligned
preference while using stronger judges: a pick biased toward one family stands only if the judge
of the other family makes it too. Agreement does not establish correctness or remove errors the
two judges share through the same prompt, dictionary, sources or training material, so their
joint decisions remain subject to the author's blinded calibration.

## What changes

**1. The judges** (Amendment 3, item 1). In place of Gemini 3.1 Pro, two judges:
- Claude Fable 5.1 (Anthropic, `claude-fable-5-1`);
- GPT-6 Astra (OpenAI, `gpt-6-astra`).

Neither coded a row. Each receives, as its own request, every row Amendment 3 gives the judge:
every disagreement, every audit row and, when the registered escalation is triggered, every
agreed row of the escalated review. Each request carries the inputs, prompt and schema of
Amendment 3 (`prompts/judge_prompt.md` and `prompts/judge_schema.json`, sha256 as logged on 13
October 2026), with the same system instruction (the judge prompt, the coders' prompt and the
dictionary definitions), the two answers blinded in the order of seed 20261017, and no access to
the other judge's answer. Both are called through their APIs with no tools and no web access,
sampling and reasoning at the vendor's defaults, structured output with the frozen schema and at
most 8,192 output tokens, reasoning included; the model string returned is recorded with every
response.

**Attempts.** Each judge's request for a row has at most two attempts. An attempt that returns no
valid answer (an error, a refusal, a truncated or malformed response) counts as one attempt.
The one exception is a refusal on the account's side (HTTP 402 for want of credit, or 429 for
rate): it is not an attempt and is sent again once the account is restored, but only until the
stage the request serves closes, that is, before the coding of the next stage or the computation
of the estimands; a request still refused then counts as failed twice.

**2. When a decision stands alone** (Amendment 3, item 2). A row is decided without the author only
when both judges give the same choice and, for each judge, none of the routing conditions of
Amendment 3, item 2 holds (needs-human, confidence below 0.80, neither, substantive error, other
issue, gate failure of the chosen answer, an unverifiable quotation, a request failed twice). Every
other row goes to the author, and in particular every row on which the two judges differ and
every row for which either judge's request was not sent because of the ceiling. The author
decides these rows blind to both judges' answers, as in Amendment 3.

**3. Calibration and consequences** (Amendment 3, items 3 and 4) are unchanged. They apply to the
rows decided alone under item 2, the judges' shared choice being compared with the author's
mark, with the seeds of Amendment 3 and the page order of seed 20261027.

**4. Cost.** Each judge's spend is counted at its vendor's list prices, recorded in the plan's log
before its first request, with reasoning billed as output, against the ceiling of the stage the
requests serve, as in Amendment 3. Before the first request, the pipeline writes to the log the
reserved bound of every planned request of the pass at those prices (input at the preflight's
characters per token, output at 8,192 tokens). Rows are sent in an order shuffled by
`random.Random(20261028).shuffle` over the rows in order of row identifier, both judges' requests
for a row together, so that the ceiling, if it binds, cuts a seeded sample rather than a
selected one. The run stops before a request whose reserved bound would cross the ceiling, and
every row not then judged by both goes to the author without a further request.

**5. The Maximum claim** sentence of Amendment 3, item 6, becomes: "two judges, one of each coding
family and each blind to the other, adjudicated every disagreement and a seeded 10% of agreements;
a row was decided without the author only when both judges made the same choice and neither
flagged it; the author decided every other row and a seeded sample of the judges' joint decisions
in each task and pass, and the agreement with the author on those samples is reported". It cannot
state that the author read every disagreement.

## Foreknowledge

Seen before this amendment: the counts of Amendment 3, and that every one of the 212 judge
requests of Amendment 3 was refused without an answer (`outputs/sa1_judge_run_2026-10-13.json`:
212 pending, 0 accepted, 0 failed, nothing billed). The author opened the superseded SA1 pages
and marked no row. No judge answer exists, no row has been adjudicated and no estimand has been
computed. Two external review rounds of earlier drafts were read and their points are applied
here; the second confirmed this text.
