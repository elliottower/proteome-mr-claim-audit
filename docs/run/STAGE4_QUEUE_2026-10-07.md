# Stage 4 up to the manual-coding queue: run note, 7 October 2026 (UTC)

Continues `STAGE4_2026-10-07.md`. Stopped at the manual-coding queue: no row is coded, the
assembly with codes and stage 5 have not run. Count fields only were read; the printed summary
of the registry assembly was discarded and `registry_assembly.json`, `claim_checks.jsonl`,
`registry_claims*.jsonl` and `wording_summary.json` are not opened.

## Corrected copy of the claim verifier

The registered `scripts/verify_claims.py` raised on the search file (`find_estimates`, line 546,
`ValueError`): a P-value exponent written with a thin space (U+2009) after the minus sign. The
patterns admit any white-space character after a sign; the two number conversions removed the
ordinary space only. `scripts/verify_claims_whitespace.py` is a copy that differs in those two
conversions (PREREG.md log, 2026-10-07, access "results seen"; review round 13). Unified diff:

```diff
--- scripts/verify_claims.py	2026-10-02 09:56:42
+++ scripts/verify_claims_whitespace.py	2026-10-07 11:46:53
@@ -512,8 +512,15 @@
                      r"snps?|IV|per-allele|MR)\b", re.IGNORECASE)
 
 
+# Corrected copy of verify_claims.py (PREREG.md log, 2026-10-07). NUM and the exponent of P_VALUE
+# admit any white-space character (`\s`) after a sign; the two number conversions below strip
+# every such character, where verify_claims.py strips the ordinary space only and raises on a
+# thin or no-break space. Nothing else differs.
+WHITE_SPACE = re.compile(r"\s")
+
+
 def to_float(num: str) -> float:
-    return float(num.replace("·", ".").replace("−", "-").replace(" ", ""))
+    return float(WHITE_SPACE.sub("", num.replace("·", ".").replace("−", "-")))
 
 
 class Estimate(BaseModel):
@@ -543,7 +550,7 @@
                 p = to_float(pm.group("v"))
                 exp = pm.group("e1") or pm.group("e2")
                 if exp:
-                    p *= 10 ** int(exp.replace("−", "-").replace(" ", ""))
+                    p *= 10 ** int(WHITE_SPACE.sub("", exp.replace("−", "-")))
                 op = pm.group("op")
             lo = to_float(m.group("lo")) if "lo" in m.groupdict() and m.group("lo") else None
             hi = to_float(m.group("hi")) if "hi" in m.groupdict() and m.group("hi") else None
```

| file | sha256 |
|---|---|
| `scripts/verify_claims.py` (registered) | `5f29a69515a3be5ed65f11964f78b8d9c8147a45acd3979cb9d19aea26cf3ff8` |
| `scripts/verify_claims_whitespace.py` | `b217f93059d0dd7cb327de0c7df8a0ecc77b5ff6e514e4c1b89659a5f8157c7d` |
| `scripts/modal_verify_claims_whitespace.py` | `82bea23e480478ab62e45e9c4bf6f3b2a46139560e42e89f1b090010de7eb244` |
| `tests/test_verify_claims_whitespace.py` | `8e6dfb0513da936df97f434747e41bcc8704291693d5f0a33d9cff2615177759` |

Tests, on Modal: the suite, 829 passed and 1 skipped
(`outputs/tests/pytest_all_modal_20261007T160241Z.txt`); the wrapper's synthetic check, 7 of 7
(`outputs/tests/verify_claims_whitespace_modal_20261007T160040Z.json`: the registered script
raises on a thin space, the copy completes, both write the same bytes without one, the
comparison reports a differing byte).

Order: log line, `results access` note for the three shown spans ("outcomes seen"), seal,
`prereg check`, commit; registered results of chase1 to chase3 moved to
`outputs/verification/<stem>/registered_verifier_5f29a695/`; the copy run on the three files.

| file | `claim_checks.jsonl` | `claim_summary.json` | inputs | sha256 of `claim_checks.jsonl` (both scripts) |
|---|---|---|---|---|
| chase1 | byte-identical | byte-identical | identical | `58b199b0102964f490ae73d6daf2d2f0521c148f175958dfc5d90fa4050df14a` |
| chase2 | byte-identical | byte-identical | identical | `a5b527aa290e2a23be6a35767bc6cb06db4588e08a765d70f448243d477d7590` |
| chase3 | byte-identical | byte-identical | identical | `b3e7da2400f48f4400175dedd9993626d254d0fc91cc52a7c4ba95f7d1103f8d` |

Each comparison is in `outputs/verification/<stem>/verifier_comparison.json` (hashes of the
inputs and outputs of both runs, the command, the environment, the time), made on the volume
and confirmed locally with `cmp`. A second log line records the three comparisons; the copy
then ran on the search file. Volume: the copy's results under
`/02_claims_meta/stage4_whitespace/`; the registered script's under `/02_claims_meta/stage4/`,
unchanged.

## Verification counts

| file | claim records | both span checks pass | enter the registry |
|---|---|---|---|
| search | 12,664 | 12,601 | 5,140 |
| chase1 | 981 | 980 | 339 |
| chase2 | 326 | 326 | 167 |
| chase3 | 82 | 82 | 19 |
| all | 14,053 | 13,989 | 5,665 |

Read from `n_claims`, `span_pass` and `enters_registry` of each `claim_summary.json`; no other
field was read.

## First assembly and queue

`assemble_registry.py` without codes, to `outputs/registry/2026-10-03` (records of the search
and three rounds; decisions of the search, chase1, gate1b1 to gate1b5, gateall1, chase2,
gateall2, gateall3; the four extraction files and their claim checks); its printed summary went
to `/dev/null`. `manual_dataset_coding.py queue` to `outputs/manual_coding/2026-10-03`.

Queue size (`docs/run/manual_coding_queue_size_2026-10-07.json`; a queue row is one record,
side and name as written):

| | rows | papers | distinct names |
|---|---|---|---|
| all | 872 | 434 | 293 |
| release_ambiguous | 528 | 333 | 76 |
| unmatched | 344 | 233 | 224 |
| pQTL side | 376 | 255 | 134 |
| outcome side | 496 | 329 | 194 |

Rows by state and side: release_ambiguous 273 pQTL and 255 outcome; unmatched 103 pQTL and 241
outcome. Distinct (paper, name) pairs: 824. The rows cover 3,882 claim records (summed over
rows).

Source to read, by paper (Europe PMC metadata looked up on 7 October with the flag test of
`fetch_fulltext.py::fetch_one`, a journal record with a PMID whose Europe PMC record has
`isOpenAccess` Y and a PMCID; the XML was not fetched, so a paper whose XML is missing or has no
body would move to abstract only):

| | papers | rows |
|---|---|---|
| open-access full text flagged | 242 | 496 |
| abstract only: no open-access flag | 113 | 227 |
| abstract only: not a journal record with a PMID | 78 | 148 |
| abstract only: no Europe PMC record for the PMID | 1 | 1 |

The 15 most frequent names as written (queue rows):

| | name as written | rows |
|---|---|---|
| 1 | UK Biobank | 155 |
| 2 | FinnGen | 100 |
| 3 | deCODE | 57 |
| 4 | UKB-PPP | 32 |
| 5 | UK Biobank Pharma Proteomics Project | 29 |
| 6 | FinnGen study | 15 |
| 7 | UK Biobank Pharma Proteomics Project (UKB-PPP) | 14 |
| 8 | FinnGen consortium | 11 |
| 9 | deCODE Genetics | 11 |
| 10 | INTERVAL | 9 |
| 11 | Million Veteran Program | 9 |
| 12 | deCODE genetics | 9 |
| 13 | Decode | 8 |
| 14 | Fenland | 8 |
| 15 | FinnGen cohort | 7 |

## Ledger

Run id `s4_verification_queue_2026-10-03` (6,719 files; the four verification folders compared
with the volume, no file on the volume only). The run id `s4_registry_2026-10-03` of the
RUNBOOK is left for the completed stage, with the codes, the coded registry, the record
metadata and the funnel.

No model was called in stage 4; the cost at list prices stays USD 158.73.
