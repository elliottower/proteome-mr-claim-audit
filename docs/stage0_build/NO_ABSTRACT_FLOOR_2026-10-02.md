# The `no_abstract` rule and its floor, 2 October 2026

Before the freeze. Records first public before 2019 only; for the 24 known items, which lie in
the window, lengths only. Counts are in `no_abstract_floor_evidence_2026-10-02.json` and
`smoke_rerun_no_abstract_rule_counts_2026-10-02.json`.

## Why a rule

The live smoke run (`LIVE_SMOKE_2026-10-02.md`) sent three chased records with no abstract
(two empty, one holding "n/a") to the eligibility prompt. Each was answered `uncertain` on all
three criteria. Under the registered rules an `uncertain` record goes to extraction, is an
eligible family, seeds the next citation-chasing round and is a positive of the gate audit. At
3 positives in 86 the audit of every round would draw batches to its 3,000-record cap.

## The rule

A record is `no_abstract` when no source holds an abstract of at least 200 characters for it
(`scripts/abstract_floor.py`; the length is counted after runs of whitespace are collapsed).
It is classed when the screening set is assembled, before the keyword prefilter:

| stage | what happens to a `no_abstract` record |
|---|---|
| screening set | listed in `no_abstract.jsonl`, left out of `screening_set.jsonl` |
| keyword prefilter, gate, gate audit | not read; never marked, sampled or a positive |
| eligibility, extraction | not sent to GPT-6.1 Sol; the runner refuses a file that holds one |
| chase seeds | never a seed |
| families | linked like any record; adds nothing; never a registry record |
| funnel | counted per screening set: empty, stub, by document class, title with both term groups |
| negative controls | counted, not judged, outside the specificity denominator |

The abstract of a record is the first one in the order PubMed, Europe PMC, OpenAlex that
reaches the floor, so a stub in one source does not hide an abstract in another.

## Evidence for 200

313 distinct records first public before 2019 are held (30 development abstracts, two smoke
searches, two smoke chase rounds). Six further records in those sets are dated in 2019 by
PubMed; they are left out here and their abstracts were not read.

| abstract length (characters) | records |
|---|---|
| none in any source | 7 |
| 1 to 199 | 2 (3 and 151) |
| 200 to 399 | 0 |
| 400 to 599 | 8 (shortest 408) |
| 600 or more | 296 |

The four shortest non-empty texts were read. The 3-character text is "n/a" (an editorial). The
151-character text is a truncated opening sentence of a software manual. The 408-character
text is a complete preprint abstract. The 430-character text is a journal's citation line for
a 1951 paper, not an abstract.

200 lies above both stubs and at about half the shortest abstract. It does not separate every
non-abstract from every abstract: the 430-character citation line passes it and is judged by
the eligibility prompt like any record. The 24 known items have abstracts of 1,014 to 3,045
characters.

## No sensitivity analysis

In the pre-2019 evidence every record below the floor that was judged (the three of the smoke
run) was `uncertain` and gave no claim record. A record below the floor that an eligibility
prompt would have passed adds a family with no named claim, or in the rare case of a stub
that states a result, a handful of claim records. The funnel reports the stub records and the
`no_abstract` records whose title alone holds a genetic term and a protein term of the keyword
prefilter, listed by id, so the reach of the rule is visible in the counts. Screening those
records would mean judging titles, which criterion 2 of the eligibility rule (a stated result
of the protein analysis) cannot be answered from.

## The smoke round under the rule

Re-assembled from the stored responses and decisions by `smoke_rerun_no_abstract_rule.py`; no
request was made and no model was called.

| count | before | after |
|---|---|---|
| screening records | 115 | 115 |
| `no_abstract` records | not classed | 3 (2 empty, 1 stub; all in the chase round) |
| records sent to GPT-6.1 Sol | 115 | 112 |
| decisions `uncertain` | 4 | 1 |
| records to extraction | 5 | 2 |
| chase round 1, marked by the gate | 86 | 83 |
| gate-audit positives | 3 | 0 |
| gate-audit upper bound (one-sided 95%) | 0.088 | 0.035 |
| eligible families | 5 | 2 |
| eligible families with no named claim | 4 | 1 |
| seeds of round 2 | 4 | 1 |
| claim records, and claims entering the registry | 3 and 3 | 3 and 3 |

No `no_abstract` record of the round has a title holding both term groups.
