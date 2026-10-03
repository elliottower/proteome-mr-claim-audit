You screen one scientific paper for a study of proteome-wide Mendelian randomization (MR)
papers. You receive only the paper's title and abstract. Judge from them alone; do not use
anything you may know about the paper from elsewhere.

Answer each question below about what the title and abstract state. Return JSON that follows
the schema exactly. Questions 1 to 3 take `yes`, `no` or `uncertain`: answer `uncertain` only
when the title and abstract leave the question genuinely open, not as a default.

1. `genetic_instruments_for_circulating_proteins`: yes if the paper uses genetic variants as
   instruments for the levels of proteins measured in plasma or serum (blood) in a Mendelian
   randomization or summary-data-based Mendelian randomization (SMR) analysis, or in an
   analysis the abstract describes as causal inference from protein quantitative trait loci
   (pQTLs) to an outcome. Protein levels described as circulating, blood, plasma or serum
   levels, or measured in study participants with no tissue named, count as plasma or serum
   levels. Yes when at least some of the instrumented proteins are measured in plasma or serum,
   even if the paper also analyses proteins measured in tissue, cerebrospinal fluid or cells.
   No if the instruments are for gene expression (eQTLs) or for something other than circulating
   protein levels, if every protein analysed is measured in tissue, cerebrospinal fluid or cells
   rather than blood, or if no MR-type analysis is described.
2. `states_protein_outcome_result`: yes if the abstract states at least one result of the
   protein analysis on a disease, trait or other outcome. The protein need not be named: a count
   of significant protein–outcome pairs (for example "111 causal effects of 65 proteins on 52
   phenotypes") counts, and so does a null result. No if the abstract reports only genetic
   associations with protein levels, or only methods.
3. `proteome_or_panel_wide_screen`: yes if the abstract describes testing many proteins
   together, from a proteomic platform, an assay panel or a proteome-wide screen, rather than one
   or a few proteins chosen in advance.
4. `n_proteins_tested`: the number of proteins the abstract states were measured or tested, as
   an integer, or null if the abstract states no such number. If the abstract gives several
   numbers (for example proteins measured and proteins with instruments), give the number of
   proteins tested as exposures in the MR analysis when it is stated, otherwise the number
   measured.
5. `n_proteins_tested_span`: the sentence of the abstract that states that number, copied
   exactly, or null when `n_proteins_tested` is null.
6. `exclusion`: every category below that applies, or an empty list when none applies.
   - `review`: a review, commentary, editorial or tutorial rather than an original analysis.
   - `protocol`: a study protocol or analysis plan without results.
   - `non_human`: the analysis is not in humans.
   - `tissue_or_csf_proteomics`: none of the proteins analysed are measured in plasma or serum;
     every protein analysed is measured in tissue, cerebrospinal fluid or cells. Do not apply it
     when the paper analyses plasma or serum proteins as well as tissue or cerebrospinal fluid
     proteins; answer `also_tissue_or_csf` instead.
7. `also_tissue_or_csf`: true if the paper analyses proteins measured in tissue, cerebrospinal
   fluid or cells in addition to plasma or serum proteins; false otherwise.

Answer from the text. When the abstract does not settle questions 1 to 3, answer `uncertain`;
for the other fields, answer false, null or an empty list as the field allows.
