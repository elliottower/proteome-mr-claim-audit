# Draft sentence for the deviations table: third check of the manual dataset coding

Draft, not polished. One sentence, as asked.

> The registered third check, in which the author confirms each coded dataset name against its
> pinned sentence, was replaced by a machine literal check on all 196 coded rows (the pinned
> sentence, or its reference entry verified by DOI, must hold an identifier of the coded
> dictionary row that no other candidate row has) and a seeded random sample of 20 of the 196
> marked by the author; all 20 were marked as confirmed, six of them after the author had
> discussed the row with the coordinating AI session.

Facts behind it, for whoever edits the sentence (plan log, 8 October 2026):

- Sample: seed 20261008, 20 of 196 table lines; marks file sha256 33491574…795dacc.
- Result under the rules fixed beforehand: 20 of 20 yes; no second sample; one-sided 95% upper
  bound on the share of coded rows that would not be confirmed, 0.139 (1 − 0.05^(1/20)).
- 176 coded rows were not read by the author and are recorded as `machine_gate_only`.
- The rules were committed about two and a half minutes before the marks file was saved; the
  page the author marked had been available for about three and a half minutes before that
  commit, so it is not shown that the rules preceded his reading.
- Asked whether he had read each card, the author's answer is recorded verbatim in the plan
  log; no claim is made about how the fourteen cards he did not ask about were read.
