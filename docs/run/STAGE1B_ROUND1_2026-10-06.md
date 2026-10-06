# Citation chasing round 1 and its eligibility: run note, 6 October 2026 (UTC)

Round 1 ran to its end with the registered commands. Counts only were read; no title, abstract
or claim content.

## Chase (22:00 to 22:23)

`citation_chase.py --round 1`, seeds the 2,093 search records judged eligible, eligible with
count not stated, or uncertain; known records the search screening set.

| count | value |
|---|---|
| seeds | 2,093 (29 without DOI or PMID; 2,057 found in OpenAlex) |
| works referenced by the seeds | 49,605 |
| referenced works retrieved (published 2019 or later) | 25,282 |
| works citing the seeds | 9,350 |
| works already in the screening set | 621 |
| new works | 32,874 |
| new screening records | 32,853 |
| `no_abstract` (empty 948, stub 173) | 1,121 |
| stored requests | 1,584 manifest lines; OpenAlex credits used 836 of the day's 10,000 |

## Gate and eligibility

| count | value |
|---|---|
| records with an abstract | 31,732 |
| marked by the keyword gate (not screened) | 31,612 |
| left to screening | 120 |
| of the 120: eligible / count not stated / uncertain / ineligible | 7 / 13 / 4 / 96 |

## Gate audit

| batch | sampled so far | positives so far | one-sided 95% upper bound |
|---|---|---|---|
| 1 | 600 | 1 | 0.0079 |
| 2 | 1,200 | 3 | 0.0064 |
| 3 | 1,800 | 7 | 0.0073 |
| 4 | 2,400 | 11 | 0.0076 |
| 5 | 3,000 | 14 | 0.0073 |

Stopping reason: maximum sample reached; **cap reached without satisfying tolerance**. Share
14 of 3,000 (0.0047; two-sided 95% interval 0.0026 to 0.0078). Marked records not judged:
28,612; estimated eligible among them 134 (two-sided 95% interval 73 to 224). No eligibility
call failed. The 14 sampled positives enter the workflow.

Records to extraction and seeds of round 2: 38 (24 of the queue, 14 of the audit).

## Calls and cost

GPT-6.1 Sol eligibility, 3,120 requests, 0 failed: 5,268,665 input tokens (4,105,920 cached,
1,153,385 cache writes), 420,183 output. Cost at list prices USD 7.51
(`usage_s1b_chase1_eligibility_2026-10-06.json`).

## Records

Response bodies (349 MB) on the Modal volume, 991 files compared by hash; ledger runs
`s1b_chase_1` and `s2_eligibility_chase1_2811496ef424`; `results access` at `structure seen`;
one `prereg log` line at `results not opened`.

## Parallelism

Every GPT-6.1 Sol call of stage 2 and of this round ran with 6 workers, the constant `WORKERS`
of `scripts/run_extraction.py` (line 59), a sealed script with no command-line or environment
setting for it. A request for more workers arrived after the last batch of this round had
finished, so no batch ran with another count.
