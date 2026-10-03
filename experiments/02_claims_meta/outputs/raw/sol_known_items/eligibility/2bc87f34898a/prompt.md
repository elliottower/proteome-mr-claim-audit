You screen one scientific paper for a study of proteome-wide Mendelian randomization (MR)
papers. You receive only the paper's title and abstract. Judge from them alone; do not use
anything you may know about the paper from elsewhere.

Answer each question below about what the title and abstract state. Return JSON that follows
the schema exactly.

1. `genetic_instruments_for_circulating_proteins`: true if the paper uses genetic variants as
   instruments for the levels of proteins measured in plasma or serum (blood) in a Mendelian
   randomization or summary-data-based Mendelian randomization (SMR) analysis, or in an
   analysis the abstract describes as causal inference from protein quantitative trait loci
   (pQTLs) to an outcome. Protein levels described as circulating, blood, plasma or serum
   levels, or measured in study participants with no tissue named, count as plasma or serum
   levels. False if the instruments are for gene expression (eQTLs) or for something other than
   circulating protein levels, if the proteins are measured in tissue, cerebrospinal fluid or
   cells rather than blood, or if no MR-type analysis is described.
2. `states_protein_outcome_result`: true if the abstract states at least one result linking a
   named protein to a disease, trait or other outcome (including a null result). False if it
   reports only genetic associations with protein levels, or only methods.
3. `proteome_or_panel_wide_screen`: true if the abstract describes testing many proteins
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
   - `tissue_or_csf_proteomics`: the proteins analysed are measured in tissue, cerebrospinal
     fluid or cells rather than plasma or serum.

Answer from the text. When the abstract does not say, answer false or null as the field
allows.
