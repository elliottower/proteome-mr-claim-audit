# Deviation 2: C1 controls that do not test the coding as built

Deviation from `experiments/03_release_resolution/PREREG.md` (§Study design, C1 and manifest controls; §Inference criteria, C1) as amended by Amendment 2, item 3 (C1-A). It takes effect when the plan's log names the sha256 of this file. Access level: stage A is coded and gated by both models; the raw C1-A and manifest recovery counts and a diagnostic of the missed controls (`outputs/stage_a_control_diagnostic_2026-10-14.json`) have been read. No judge has run on stage A, no stage A row has been adjudicated, and no estimand has been computed.

## Counts seen

On the coders' raw answers, before adjudication: C1-A recovery 49 of 70 (Claude) and 53 of 70 (GPT), 47 of 70 by both; manifest recovery 10 of 31 for each model, 3 of 31 by both; contradiction 0 everywhere. The diagnostic found every expected identifier in the packet the coder was given. Of the 23 C1-A controls not recovered by both models, 9 match an identifier the source attributes to something other than the claim's dataset (an exposure, one component of a meta-analysis, a combined FinnGen and UK Biobank meta-analysis, a secondary analysis); 5 are source identifiers that both models coded to the expected row but the gate rejected, because the DOI or PMID stands in a table cell or a data-availability sentence and the paper's reference entry carries none; the other 9 are coder misses, quotation failures or sources that give two identifiers for one outcome. The 31 manifest packets carry no title, abstract or claim, so no identifier in them is attributed to an analysed dataset, as D1 requires.

## What changes

1. **The registered C1 is computed and reported as registered**, on accepted codes after adjudication, with its thresholds and its void condition. Nothing in this deviation removes a control from it. If it fails, the paper says so, and item 5 decides what is reported.

2. **Valid-control C1-A** (a deviation analysis).
   - **Rubric.** A control is valid when its source sentence or table row attributes its identifier to the dataset of the control's own side for the record's claim: for an outcome-side control, the dataset of the claim's outcome; for a pQTL-side control, the pQTL dataset of the claim's exposure protein. It is invalid when the identifier belongs to another role on that side (an exposure or covariate for an outcome-side control, another outcome, a replication or secondary analysis), or when it names one component of a meta-analysis or combined dataset while the claim's dataset for that side is the combined one. An identifier of a component the claim analysed alone is valid.
   - **Packets and judges.** Each of the 70 C1-A controls, recovered or not, gets a packet holding only the control's side, its identifier, its source sentence or table row with the adjacent sentences, and the record's claim. The rubric, the judge prompt and the packets are frozen, with their sha256 logged, before any judge request. The two blinded judges of Amendment 4 mark each control valid or invalid independently; neither sees coder answers, recovery status, the diagnostic, or the other judge's mark.
   - **Disagreement.** A control the judges mark differently, or either judge cannot mark, is retained as valid. The author, who has seen the diagnostic, marks no control.
   - **Scoring.** Valid-control C1-A is computed on accepted codes under the unchanged primary rules and gate, with the registered thresholds (recovery at least 0.90, contradiction at most 0.02) and the minimum of 50 controls. A valid control missed because the gate rejects an identifier is a miss here.

3. **The manifest check becomes a check of the mapping software.** The registered manifest result is reported as registered, with the reason codes of every miss. Beside it, the gate's mapping functions are run by script on each manifest accession, with no model, and must return the expected dictionary row for all 31. This tests what the plan calls the manifest check's purpose, "a separate implementation check of the mapping and the software"; the coded packets test whether a coder codes an identifier no claim is attached to. The script check tests the software, not the coding, and never substitutes for item 2.

4. **Inline source identifiers** (a sensitivity analysis). The primary gate is unchanged. A sensitivity analysis also accepts, under D2, a DOI or PMID that stands in the paper's own text (a table cell, a data-availability or key-resources statement) and is attributed there to the analysed dataset, with no reference entry. It is applied to study rows and to valid-control C1-A, and the rows and controls it changes are counted apart. It never decides whether the gate of item 5 passes.

5. **Decision rule.**
   - **Both registered checks pass** (source-scanned C1-A and the manifest check): the estimates stand under the registered plan, subject to its other safeguards; items 2 to 4 are reported as additional checks.
   - **Either registered check fails:** the estimates are computed and reported only as post hoc, deviation-based analyses, never as validated under the registered plan, and beside the registered failure, and only if valid-control C1-A passes on at least 50 valid controls and the mapping script returns the expected row for all 31 manifest accessions.
   - **Otherwise** (valid-control C1-A fails, rests on fewer than 50 valid controls, or the mapping script fails on any accession): every estimate the registered checks gate is void, as registered.

## Reason

The C1 scanner's context condition (a dataset or GWAS term in the same sentence or table row) does not establish that an identifier is the dataset of the claim's outcome, and each drawn control is given the record's claim outcomes (Amendment 2, item 3). The gate's citation rule asks for a reference entry and so cannot credit an identifier written inline. The manifest packets cannot meet D1's attribution requirement. Each is a property of how the checks were built, found before any judge or estimand.

## Review

Three external review rounds of earlier drafts were read and their points are applied here; the third confirmed this text.
