# Citation chasing: every gate-marked record screened. Run note, 6–7 October 2026 (UTC)

## Departure (logged in PREREG.md on 2026-10-06, before the first call)

The registered gate audit of round 1 ended at its cap without satisfying the tolerance (14
positives in 3,000 sampled; one-sided 95% upper bound 0.0073 against 0.005). The author decided,
after those audit counts were seen and before any claim was extracted, that GPT-6.1 Sol screens
with the frozen eligibility prompt every record of round 1 the keyword gate marked and the audit
had not sampled, and in rounds 2 and 3 every chased record with a usable abstract. The gate
orders records and excludes none.

Unchanged: the audit result of round 1 is reported as registered; stored audit decisions are
reused; the sensitivity analysis without citation chasing; the `no_abstract` rule; the
registered eligibility rule. No sample audit runs for rounds 2 and 3, because every record is
screened.

## Parallelism

`scripts/run_extraction_parallel.py` (new, tested, sealed) sends the registered runner's own
requests through its own `run_one` and cache, with the number of simultaneous workers set by
`SOL_WORKERS`, then calls the runner's `main` to write the parsed file. It halves the worker
limit on a rate-limit refusal and stops without writing a parsed file on a billing refusal or
when a record has no response. The registered runner's constant is 6. This run used 48 workers
throughout (no refusal of either kind, limit never lowered). The number of simultaneous
requests is the only difference from the registered runner.

## Round 1, the 28,612 marked records not sampled by the audit

`scripts/gated_out_remaining.py` (new, tested, sealed): 31,612 marked, 3,000 in the five audit
batches, 28,612 remaining. Sent 2026-10-06 23:21 to 2026-10-07 02:19 UTC.

| count | value |
|---|---|
| records sent | 28,612 |
| answered and valid at the first attempt | 28,612 |
| failed exchanges (any HTTP failure) | 0 |
| eligible | 9 |
| eligible, count not stated | 27 |
| uncertain | 113 |
| ineligible | 28,463 |
| eligible, count not stated or uncertain together | 149 |
| registered audit estimate for these 28,612 (two-sided 95% interval) | 134 (73 to 224) |

Round 1 in all, records to extraction and seeds of round 2: 187 (24 from the gated-in queue,
14 from the audit batches, 149 from the full screening).

## Calls and cost

28,612 requests: 48,467,703 input tokens (37,654,633 cached, 10,727,234 cache writes),
3,791,152 output (943,948 reasoning). Cost at list prices USD 68.67
(`usage_s1b_chase1_full_screening_2026-10-07.json`, written by `scripts/sol_usage.py`).

## Records

Ledger run `s2_eligibility_gateall1_2811496ef424` (28,622 files); `results access` at
`structure seen`; raw exchanges in `outputs/raw/sol_chase_full` (608 MB, 28,612 files of about
21 KB). Modal suite with the three new scripts: 797 pass, 1 skipped as before, the three dry
runs return 0 (`outputs/tests/pytest_all_modal_20261006T232255Z.txt`).
