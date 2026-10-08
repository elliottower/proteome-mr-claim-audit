# Amendment 2: the span check under a corrected build of the quotation tool, and restoration of spans that leave out one token

Amendment to `PREREG.md` (frozen at `02bb006f3e55`, plan sha256
`9f06131af9936cc7c3556e87d77dcec65d034e4665be023eedf39948082d417b`, registered at
https://osf.io/zae8c). Date: 8 October 2026. Access level at the time: results seen. It takes
effect when the log of `PREREG.md` names the sha256 of this file; nothing below is run before
that.

It has three parts: (1) the build of the `citations` tool and one step of the span check, which
concerns 27 claim records; (2) the restoration of an evidence span from its stored abstract,
which concerns 37; (3) what is rebuilt downstream.

64 of 14,053 claim records failed the stage 4 span check. A sealed script classed them by cause
without any person or agent reading them: 27 hold a span that stands in the stored abstract
verbatim, twice; 37 hold a span made of two verbatim pieces of the abstract with one token
between them left out. The study does not drop a record for an operational failure.

## Part 1. The tool and the span step

| | registered run | from this amendment |
|---|---|---|
| tool | `citations`, an editable install of the author's tools repository at commit `5519baf5ef9a7b120ee6984ad179dc91a43fa79d` (the installed metadata reads 0.4.2; the source at that commit declares 0.5.0) | `citations` 0.5.1 installed from commit `fb89bb6104be091585f87c8d1a35aa2fd2c44b74` of the same repository, not editable, with `provenance-core` 0.5.1 from the same commit |
| span step | `scripts/verify_spans.py`, one local run per extraction file | `scripts/verify_spans_occurrence.py`, unchanged, run on Modal in parts by `scripts/modal_verify_spans_occurrence.py` |

**The tool is the author's own.** The repository is `elliottower/reproducible-science`. The
change is pull request 113, written for this purpose by an agent session at the author's
direction and merged to `main` as the squash commit named above (the branch head before the
squash was `15673127f756e50f760e1bc71886c5300e20e178`). This is not a third-party update. A
separate agent session reviewed the code three times; fixes followed the first two passes; the
third found it safe to merge with minor points, filed as issue 114 of that repository.

**The commit is not the one named in the review request.** The request of round 16 named
`d56283315b0ab39b244247c5cd53ce59e86221e8`. The code reviews that followed changed the branch,
so that commit is not the one used. No further round of the external review was sought for the
later commits.

**What the build adds.** `citations pin --occurrence N`, which pins one named occurrence of a
passage that stands more than once in its source. A reason, `omission`, on a quotation that is
not found and whose pieces are whole white-space-delimited tokens of the source, in order, with
source text left out between them. `citations restore`, which writes the bounded source passage
as a separate record in a file beside the claims file (`<name>.restored.yaml`), with its
provenance (rule `bounded-passage`, rule version 2), and never changes the original.

**The rule for the 27.** Pin the first occurrence. In `scripts/verify_spans_occurrence.py` a
span is pinned with `--occurrence 1` when, and only when, the registered quote check holds and
the plain pin is refused as ambiguous. Both occurrences are the same text. This is a mechanical
correction: what counts as verbatim does not change. The pass condition is the registered one,
both checks required: the quote check (white space collapsed, case folded, nothing else) and a
`citations` pin that is found.

**Run in parts.** The step makes one call of the tool per span and writes its results only when
it ends. It is run on Modal and not on the author's laptop: each extraction file is cut into
parts of 40 consecutive rows (a row is one paper), the sealed script runs unchanged on each
part, each part's results are stored and committed as it ends, and a restarted run computes
only the missing parts. The parts are joined by `scripts/span_shards.py`: `spans.jsonl` in
order, the union of `span_occurrences.json`, `span_summary.json` computed from the joined lines
with the sealed script's expressions, and `citations verify --strict` once over the joined
claims tree. A paper's spans are pinned in that paper's own claims file, so a record's result
does not depend on the other papers in the file. On made-up records the wrapper's check
(`outputs/tests/verify_spans_occurrence_modal_20261008T043228Z.json`) found the joined results
and claims tree byte for byte those the sealed script writes for the whole file at once, for
parts of two and of three rows.

**Permitted differences, fixed before the run.**
`verification/span_step_permitted_differences.json` lists by record id the only records whose
span-check line may differ between the two runs: 63 in the search file (27 to pass, 36 still
failing) and 1 in the first citation-chasing file (still failing). The other two files must be
byte-identical. `scripts/span_step_comparison.py` asserts that the differing records are a
subset of that set, that every one of the 13,989 passing records has an identical line, that
the 27 pass and the 37 fail, and that `--occurrence` was used for the 27 and for no other
record. It records the sha256 of every input file and of every span file of both runs.

**Normalization.** The reviewer asked that the corrected build apply the same normalization as
the registered one and nothing more. That cannot be asserted in those words. The registered
pass condition has always joined two checks with different folding: the study's quote check
folds white space and case only; the tool's pin folds more (NFKD with combining marks dropped,
quotes, dashes, de-hyphenation across a line break). That is unchanged. What is shown: the pass
condition is unchanged; the folding functions of the two builds give byte-identical output on
every stored abstract and evidence span (`scripts/citations_fold_digest.py`, run under each
build and compared by the comparison script); and every one of the 13,989 passing records comes
out identical.

Also recorded on the affected records: `occurrence_count` and, for the three abstracts,
`stored_abstract_has_duplicated_passage` (`span_occurrences.json`).

## Part 2. The 37 spans that leave out one token

Labels, fixed now and not changed after H1 and H2 are seen:

- **Amended primary analysis.** The evidence span is restored from the stored abstract and the
  record goes through the registered checks: source-restored and checked under the registered
  verifier.
- **Originally registered analysis.** The 37 are excluded, as registered.

Both main estimates are shown together in the paper. The 27 (a tool correction: the same text,
pinned at its first occurrence) and the 37 (a restoration of the span from its source) are
reported as different operations. Both analyses include the 27; they differ only in the 37. The
registry exactly as first assembled, with all 64 excluded, is reported as a third column of
counts.

**The rule is a predicate applied to every one of the 14,053 claim records, not a list**
(`scripts/span_restoration_v2.py`). A span is eligible when the registered quote check fails
and the span's white-space tokens, case folded, are two runs standing in the abstract in order
with exactly one whole abstract token between them, the junction tokens whole and the alignment
unique within that predicate. A token is stated in the tool's terms: a stretch of the stored
abstract between white space of the abstract's own, a group of digits joined by thin, narrow or
no-break spaces being one token. A changed sign, a truncated number, a substitution, a cut
compound, several tokens left out or an alignment possible in two ways is not eligible and
stays failed. Eligibility does not depend on what verification later gives. The eligible set
must equal the 37 record ids of `verification/span_restoration_expected_records.json`, or the
run stops.

**The restored passage** is the stored abstract's own text from the start of the first run to
the end of the second, nothing wider. The model's output is never overwritten. A repair map
holds, per record, the hashes of the original span and of the restored passage, the stored
source and its hash, the offsets, the position of the omitted token, the rule and the script's
hash. A derived extraction file holds the restored spans.

**Three computations of the passage must agree for all 37, or the run stops**: the study
script's own; `citations restore` under the pinned build, run by
`scripts/span_restoration_tool_side.py` in a claims tree under the study's output folder, the
only place a sidecar is written; and a file of hashes made with the tool in the session that
built the tool change (hashes, offsets and counts, no text).

**The tool's rule and the study's differ in one respect, stated here.** The tool restores the
shortest passage the quotation fits when every other fitting spans a longer passage that
contains it, and records the number of fittings; its documentation states that a containing
fitting can be a different reading of where the quotation came from. Tried on scratch copies
before this amendment, with counts only: of the 37, 34 have exactly one fitting and 3 (records
`42489810:000`, `42489810:001` and `42489810:002`, one paper) have two, the second containing
the first and leaving out more than one token. The amended primary analysis includes all 37
under the rule as ruled: exactly one whole token left out, unique alignment within that
predicate. The transition report states the 34 and 3 separately, and the downstream results are
also reported without those 3.

**Verification.** The restored record goes into the unchanged verifier of the run
(`scripts/verify_claims_whitespace.py`) with its original claim fields. No rule is added that
excludes a record because its result changed. As registered, a direction disagreement keeps a
record out of direction-based results and not out of the registry (lines 777 and 812). Because
the verifier reads claims that share a span together (lines 762 to 764), every other record's
verification output is compared before and after and any difference is explained. Reported, in
counts: the transitions of protein mapping, outcome mapping, parsed direction, verification
method, registry eligibility and direction-result eligibility; and, when the analysis runs, the
H1 and H2 denominators and estimates under both labels.

**What the verifier does not show.** That the omitted token was semantically harmless. The
verifier checks the presence of the protein and outcome names and derives direction from
estimates or lexical cues. The restored records are described as source-restored and checked
under the registered verifier, and not as proven equivalent.

**Not adopted.** A single re-request of the 15 abstracts was put to the reviewer in round 16b,
accepted there only as a sensitivity analysis, and dropped; nothing was sent. Round 16c accepted
restoration as the amended primary analysis with the registered exclusion reported alongside.

## Part 3. Downstream

Two assemblies are built and kept: the amended primary (the 27, and those of the restored 37
that pass the registered checks) and the originally registered one (the 27, the 37 excluded).
The first assembly and the manual-coding queue are rebuilt for the amended primary. Every one of
the 872 existing queue rows must be unchanged by a per-row hash (paper, side, name as written,
candidate rows, passages). Every existing code is kept. New rows from records that enter the
amended primary analysis are primary rows, coded by the same checks. The summary of the first
assembly stays suppressed through the rebuild; no aggregate is printed.

## Exposure statement

Seen by the author or an agent session before this amendment was logged:

- Three failing spans, shown on 7 October 2026 when the claim verifier raised on them (logged
  that day with access "outcomes seen").
- Counts per class of the 64 failing spans (27 in three abstracts, 18 of them one span of one
  paper; 37 in 15 papers), and the positions and lengths of the duplicated passages.
- That each of the 37 leaves out exactly one token, in the middle of the span; that all 37
  tokens are alphabetic words of the class "other"; that none is one of no, not, without,
  however, but, whereas, in contrast; that 7 stand next to a token holding a digit.
- That 14 of the 27 and 20 of the 37 pass every other claim-level criterion as their records
  stand; that the 27 are 25 distinct claims after mapping.
- The dry evaluation of the predicate: it selects the 37 and no other record.
- The trial of the tool on scratch copies: 27 pin at occurrence 1 and verify strictly; 37 are
  reported as omissions and are restorable at the limit of one token; the 34 and 3 split above.
- The estimate that the rebuilt queue gains about 5 rows.

Not opened: registry content, any dataset relation, any H1 or H2 quantity.

The rule was developed after these were seen. It is a data-informed change to the inclusion
procedure, which is why the originally registered analysis is reported beside it.

## Files

| file | sha256 |
|---|---|
| `scripts/verify_spans_occurrence.py` | `bd99dda3e18fa9747731d9ec2f09479267a62cbf86ea111df640bf470f15a8d3` |
| `scripts/span_shards.py` | `cc010308136078f54977121fdcea530f7d1c4dd1baac37fded8ff5d1bddbac56` |
| `scripts/modal_verify_spans_occurrence.py` | `c3f1b8808cdc6f4d4a1ab5cc47d76f88a99913bd737b0ab7925a3966e391087b` |
| `scripts/span_step_comparison.py` | `c6c9d0aabb8fa17e95be2845058c3d0b84e3abc67be9913923976e95644bd292` |
| `scripts/citations_fold_digest.py` | `f7e2e631569a96c9a5d57a0032cc2573f41c6f4637e4e0bfec6f5b6a8b7bea80` |
| `scripts/span_restoration_v2.py` | `6e4f223734e59a0488af839fe090e0e6f57619e339ce896ec46b71f0bbd6adfd` |
| `scripts/span_restoration_tool_side.py` | `d879d60434b9e590d5a45ffd39875290d95145e3f856e14ce8a50f1e303e46e5` |
| `scripts/verify_claims_whitespace.py` | `b217f93059d0dd7cb327de0c7df8a0ecc77b5ff6e514e4c1b89659a5f8157c7d` |
| `scripts/modal_verify_claims_amended.py` | `ba4514c919940fa7b58aea3ffddf432ca60a17e8ac15ee08bc43d10d1ea9037f` |
| `verification/span_step_permitted_differences.json` | `be73648257dab63299de2655f4c77f2594c84020c642d5197e2184c048cc6e1a` |
| `verification/span_restoration_expected_records.json` | `a0166e9c8464d5a5f7bec009b01772bdbc3d476dbbf29cfc0782da0235ea7409` |
| `tests/test_span_restoration_v2.py` | `60a2f07b7ca1de09c08fed632b271c1efe60c7aa1351481e8477e17909f2bfa4` |

`scripts/span_restoration.py` (sha256
`2eb57c737f712b93414afeebf0a88021df652ffdbb02c8e26d541d3f21d73452`), the first copy of the
predicate, stays sealed and is not used: it took a part of a digit group for a token.

Tests on Modal: the suite, 1,182 passed and 1 skipped (20261008T043134Z); the span wrapper's
check on made-up records, all passed (20261008T043228Z).

Reviewed externally in rounds 16, 16b and 16c.
