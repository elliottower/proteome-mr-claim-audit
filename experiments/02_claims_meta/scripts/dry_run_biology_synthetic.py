# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5", "rapidfuzz==3.14.6"]
# ///
"""Dry run of the registry assembly, claim tags, stage 5 biology joins and sensitivity analyses
on synthetic records, through the same files the census will write.

Every record and every resource is invented here: no in-window record, abstract or aggregate is
read, no pinned resource file is opened, and no model is called. Five study families (A–E; A
with a preprint that dates one of its pairs, E with a failed extraction) make 15 claim records on
five proteins and seven outcomes. The scenario covers a contradicted pair on disjoint sources, a
`_with_nonsignificant` family–pair, an unverified direction, a `context_unclear` record, a
relation-ambiguous record and an outcome that is not in its span (both outside the registry), a
hub protein whose abstract names a pleiotropic locus, an outcome in two therapeutic areas, an
outcome that takes its area from its nearest ancestor, a one-step ontology relation, novelty
language with and without an earlier registry claim, an outcome name holding a wording keyword
(which does not make the claim a `target` claim), a claim with no stated platform (which
enters the enrichment through its dataset row), families whose datasets give no assay list, a
pathway dropped by size on one platform's analysed list and kept on its whole panel (two
proteins that failed quality control), EpiGraphDB records of each class, a snapshot trait mapped
through a proxy alias (read only in its sensitivity analysis), and two records of document
class `other` (a repository copy of study B
and a conference abstract of a study with no article, XB and XF), which enter the
`all_document_types` sensitivity analysis only. Family D stands for a family added by citation
chasing. The record metadata (RECORD_META: query sources, journals, OpenAlex reference lists)
is invented too: B cites A's preprint, C cites neither earlier family, D has no reference list.
The run raises if any value differs from EXPECTED, which was worked by hand from the scenario;
the registered secondaries are in SECONDARY.

Usage: uv run scripts/dry_run_biology_synthetic.py --out <dir>
"""

import argparse
import csv
import datetime
import json
import pathlib

from assemble_registry import assemble, write
from biology_joins import Resources, run_all
from build_registry import PublicDate
from claim_tags import load_lexicon, tags_from_extraction
from dataset_relations import DICTIONARY, load_rows
from link_families import SearchRecord
from ontology_graph import load_graph
from registry_secondaries import RecordMeta
from sensitivity_analyses import run as sensitivity_run

N_BOOT = 2000
ACC = {i: f"Q0000{i}" for i in range(1, 6)}
HGNC_UNIPROT = {f"HGNC:{i}": frozenset({ACC[i]}) for i in range(1, 6)}
UKB = (["UKB-PPP discovery"], ["FinnGen R10"])
DECODE = (["deCODE 2023"], ["Pan-UKB"])
SUN = (["Sun 2018"], ["FinnGen R12"])
NONE = (["not_stated"], ["not_stated"])
NS = "reported_nonsignificant_or_null"

# record -> ordered claims: (protein, outcome, direction, span, options)
SCENARIO = {
    "A": (UKB, ["Olink"], "European", [
        (1, "MONDO:cad", "raises", "Genetically predicted P1 was causally associated with higher "
                                   "CAD risk.", {}),
        (1, "MONDO:lungca", "raises", "P1 is a novel therapeutic target for lung cancer.", {}),
        (1, "MONDO:asthma", "raises", "P1 showed a causal effect on asthma.", {}),
        (2, "MONDO:cad", "raises", "Higher P2 was associated with CAD.", {}),
        (3, "EFO:crp", "raises", "P3 causally raised C-reactive protein.", {}),
        (4, "EFO:bmi", "lowers", "P4 and BMI were examined.",
         {"first_failure": "relation_ambiguous", "relation_ambiguous": True}),
    ]),
    "PA": (UKB, ["Olink"], "European", [
        (1, "MONDO:cad", "raises", "P1 raised CAD risk.", {}),
    ]),
    "B": (DECODE, ["SomaScan"], "not_stated", [
        (1, "MONDO:cad", "lowers", "For the first time, we show a causal effect of P1 on CAD.",
         {}),
        (2, "MONDO:heart", "raises", "P2 had a causal effect on heart disease.", {}),
        (4, "EFO:bmi", "raises", "P4 is a drug target for BMI.", {"platform": ["not_stated"]}),
        (1, "MONDO:cad", NS, "In sensitivity analyses the estimate for P1 and CAD was not "
                             "significant.",
         {"claim_scope": "sensitivity", "analysis_context_as_written": "in sensitivity analyses"}),
    ]),
    "C": (SUN, ["SomaScan"], "European", [
        (1, "MONDO:cad", "raises", "Higher P1 was associated with treatment-resistant CAD.",
         {"outcome_as_written": "treatment-resistant CAD"}),
        (5, "MONDO:asthma", "lowers", "P5 had a causal protective role in asthma.",
         {"direction_verification_state": "direction_unverified"}),
        (5, "MONDO:asthma", "raises", "In women, higher P5 was associated with asthma.",
         {"claim_scope": "subgroup_specific", "subgroup_as_written": "women"}),
    ]),
    "D": (NONE, ["Olink"], "not_stated", [
        (2, "MONDO:cad", "raises", "We report a novel causal link from P2 to CAD.",
         {"claim_scope": "unclear"}),
        (1, "MONDO:cad", "raises", "P1 raised the risk of coronary disease.",
         {"first_failure": "outcome_not_in_span", "outcome_check": "outcome_not_in_span"}),
    ]),
    "XF": (NONE, ["Olink"], "not_stated", [
        (3, "MONDO:lungca", "raises", "P3 had a causal effect on lung cancer.", {}),
    ]),
}
RECORDS = [("A", "journal", "2020-03-01", "10.1/a", None),
           ("PA", "preprint", "2019-11-01", "10.9/pa", "10.1/a"),
           ("B", "journal", "2021-06-01", "10.1/b", None),
           ("C", "journal", "2022-09-01", "10.1/c", None),
           ("D", "journal", "2023-02-01", "10.1/d", None),
           ("E", "journal", "2024-07-01", "10.1/e", None),
           ("XB", "other", "2021-01-01", "10.5/xb", None),
           ("XF", "other", "2022-03-01", "10.5/xf", None)]
OUTCOME_NAMES = {"MONDO:cad": "CAD", "MONDO:lungca": "lung cancer", "MONDO:asthma": "asthma",
                 "MONDO:heart": "heart disease", "EFO:crp": "C-reactive protein",
                 "EFO:bmi": "BMI"}
CHASED = frozenset({"D"})
DECISIONS = {"XB": ("eligible", []), "XF": ("eligible", []),
             "A": ("eligible", []), "PA": ("eligible", []),
             "B": ("eligible_count_not_stated", []), "C": ("eligible", ["also_tissue_or_csf"]),
             "D": ("uncertain", ["uncertain_proteome_or_panel_wide_screen"]),
             "E": ("eligible", [])}
# Proteins stated as tested: B states none; C states fewer than 1,000.
TESTED = {"A": 1500, "PA": 1500, "B": None, "C": 800, "D": 1200, "E": 2000, "XB": 1500,
          "XF": 1500}
# record -> (query sources, chase round, journal, OpenAlex work, cited works or None)
RECORD_META = {
    "A": (("pubmed", "epmc", "openalex"), None, "Journal One", "W_A", ["W_OLD"]),
    "PA": (("epmc",), None, None, "W_PA", ["W_OLD"]),
    "B": (("pubmed",), None, "Journal Two", "W_B", ["W_PA", "W_OLD"]),
    "C": (("pubmed", "openalex"), None, "Journal One", "W_C", ["W_X"]),
    "D": ((), 1, "Journal Three", "W_D", []),
    "E": (("epmc", "openalex"), None, "Journal Two", "W_E", ["W_A"]),
}
ABSTRACTS = {"A": "Instruments near ABO were excluded. P1 was causally associated with CAD.",
             "PA": "P1 raised CAD risk.", "B": "For the first time, a causal effect of P1.",
             "C": "Higher P1 was associated with CAD.", "D": "A novel causal link.", "E": "x",
             "XF": "P3 had a causal effect on lung cancer."}

EDGES = [("MONDO:cad", "MONDO:heart"), ("MONDO:heart", "MONDO:cardio"),
         ("MONDO:lungca", "MONDO:cancer"), ("MONDO:asthma", "MONDO:resp"),
         ("EFO:bmi", "EFO:measurement"), ("EFO:crp", "EFO:protein"),
         ("EFO:protein", "EFO:measurement")]
# Therapeutic areas: coronary disease lies in two areas, asthma is absent from the table and
# takes the area of its nearest ancestor, and the two traits lie in `measurement` only.
MEASUREMENT = "EFO:0001444"
AREAS = {"MONDO:cad": ["AREA:cardio", "AREA:genetic"], "MONDO:heart": ["AREA:cardio"],
         "MONDO:lungca": ["AREA:cancer"], "MONDO:resp": ["AREA:resp"],
         "EFO:bmi": [MEASUREMENT], "EFO:crp": [MEASUREMENT]}
AREA_NAMES = {"AREA:cardio": "cardiovascular", "AREA:genetic": "genetic", "AREA:cancer": "cancer",
              "AREA:resp": "respiratory", MEASUREMENT: "measurement"}
FILLER = [f"F{i:02d}" for i in range(1, 18)]
# The SomaScan-like study analysed 20 proteins of a 22-protein panel: W01 and W02 failed quality
# control, are on the whole panel only, and W01 lies in pathway X.
LISTS = {"syn_olink": [*ACC.values(), *FILLER[:15]],
         "syn_soma": [ACC[1], ACC[2], ACC[4], *FILLER],
         "syn_soma_panel": [ACC[1], ACC[2], ACC[4], *FILLER, "W01", "W02"]}
# dictionary row -> (assay list, background level, whole-panel list)
ATTACHED = {"UKB-PPP discovery": ("syn_olink", "assayed", ""),
            "deCODE SomaScan v4 (Eldjarn 2023 update)": ("syn_soma", "analysed",
                                                         "syn_soma_panel")}
PATHWAYS = {"R-HSA-X": [ACC[1], ACC[3], *FILLER[:8], "W01"],
            "R-HSA-Y": [ACC[2], ACC[4], ACC[5], *FILLER[8:16]]}
SNAPSHOT_PROTEINS = {"G1": ACC[1], "G2": ACC[2], "G9": None}
SNAPSHOT_TRAITS = {"Coronary heart disease": "MONDO:cad", "Asthma": "MONDO:asthma",
                   "Lung cancer (any stage)": "MONDO:lungca", "Weird trait": None}
# trait -> (name rule, alias relation)
TRAIT_RULES = {"Coronary heart disease": ("as_written", ""),
               "Asthma": ("alias_table", "normalized_equivalent"),
               "Lung cancer (any stage)": ("alias_table", "broader_proxy")}
SNAPSHOT_ESTIMATES = [("G1", "Coronary heart disease", 0.2), ("G2", "Asthma", 0.1),
                      ("G9", "Asthma", -0.4), ("G1", "Weird trait", 0.3),
                      ("G1", "Lung cancer (any stage)", 0.5)]

MAPPING_FAILED = "mapping_failed"
EXPECTED = {
    "assembly": {"eligible_families": 5, "registry_claims": 13, "dating_claims": 1,
                 "left_out": {"relation_ambiguous": 1, "outcome_not_in_span": 1}},
    "wording": {"association": 4, "causal": 7, "target": 2},
    "novelty": {"novelty_language_claims": 3, "novelty_language_earlier_in_registry": 2,
                "novelty_language_related_prior_claim": 1, "related_prior_claim_all_claims": 2,
                "claim_records_by_class": {"earlier_in_registry": 4,
                                           "no_earlier_in_registry": 9}},
    "reference_pairs": {"present_same": 0, "present_opposite": 0,
                        "present_nondirectional_or_ambiguous": 1, "no_returned_record": 2,
                        MAPPING_FAILED: 5},
    # Without the alias table the asthma trait is unmapped, so P1 × asthma fails to map.
    "reference_pairs_as_written": {"present_same": 0, "present_opposite": 0,
                                   "present_nondirectional_or_ambiguous": 1,
                                   "no_returned_record": 1, MAPPING_FAILED: 6},
    # With the proxy alias the lung-cancer trait maps, and P1 x lung cancer has a record in the
    # claim's direction.
    "reference_pairs_with_proxy_aliases": {"present_same": 1, "present_opposite": 0,
                                           "present_nondirectional_or_ambiguous": 1,
                                           "no_returned_record": 2, MAPPING_FAILED: 4},
    "reference_claims": {"present_same": 2, "present_opposite": 1,
                         "present_nondirectional_or_ambiguous": 1, "no_returned_record": 3,
                         MAPPING_FAILED: 6},
    "reference_novelty_language": {"present_same": 0, "present_opposite": 1,
                                   "present_nondirectional_or_ambiguous": 0,
                                   "no_returned_record": 1, MAPPING_FAILED: 1},
    "hubs": [{"protein_id": "Q00001",
              "areas": ["AREA:cancer", "AREA:cardio", "AREA:genetic", "AREA:resp"],
              "minimum_areas": 3, "n_distinct_areas": 4, "n_counted_outcomes": 3,
              "n_causal_or_target_claims": 4, "n_registry_claims": 6, "n_families": 3,
              "pleiotropic_locus_named": True, "pleiotropic_genes_named": ["ABO"]}],
    "enrichment_states": {"enters_enrichment": 7, "not_causal_or_target": 4,
                          "no_pinned_assay_list": 2},
    # (assay list, pathway): (claimed in pathway, claimed, background in pathway, background, p, q)
    "enrichment_rows": {
        ("syn_olink", "R-HSA-X"): (2, 2, 10, 20, 45 / 190, 90 / 190),
        ("syn_olink", "R-HSA-Y"): (0, 2, 10, 20, 1.0, 1.0),
        ("syn_soma", "R-HSA-Y"): (2, 3, 10, 20, 570 / 1140, 570 / 1140),
        ("pooled", "R-HSA-X"): (2, 4, 10, 22, 4620 / 7315, 5170 / 7315),
        ("pooled", "R-HSA-Y"): (2, 4, 11, 22, 5170 / 7315, 5170 / 7315),
    },
    # Whole panel: the SomaScan-like background gains W01 and W02, pathway X reaches 10
    # background proteins on it, and the pooled background has 24 proteins.
    "enrichment_rows_whole_panel": {
        ("syn_olink", "R-HSA-X"): (2, 2, 10, 20, 45 / 190, 90 / 190),
        ("syn_olink", "R-HSA-Y"): (0, 2, 10, 20, 1.0, 1.0),
        ("syn_soma_panel", "R-HSA-X"): (1, 3, 10, 22, 1320 / 1540, 1320 / 1540),
        ("syn_soma_panel", "R-HSA-Y"): (2, 3, 10, 22, 660 / 1540, 1320 / 1540),
        ("pooled", "R-HSA-X"): (2, 4, 11, 24, 6765 / 10626, 6765 / 10626),
        ("pooled", "R-HSA-Y"): (2, 4, 11, 24, 6765 / 10626, 6765 / 10626),
    },
    "background_levels": {"analysed": 1, "assayed": 1, "unavailable": 26},
    "density": {("R-HSA-X", "MONDO:cad"): (3, 1), ("R-HSA-X", "MONDO:lungca"): (1, 1),
                ("R-HSA-X", "MONDO:asthma"): (1, 1), ("R-HSA-X", "EFO:crp"): (1, 1),
                ("R-HSA-Y", "MONDO:cad"): (2, 1), ("R-HSA-Y", "MONDO:heart"): (1, 1),
                ("R-HSA-Y", "EFO:bmi"): (1, 1), ("R-HSA-Y", "MONDO:asthma"): (1, 1)},
    "hierarchy": {"hierarchy_relations": 1, "anchors": 8, "anchors_with_a_one_step_relative": 2,
                  "h1_pairs": 3, "h1_pairs_agreeing": 2, "h1_independent_edges": 4,
                  "h2_multi_family_pairs": 3, "h2_known_not_identical": 3},
    "papers_per_pair": {"1": 6, "2": 1, "3": 1},
    "participant_overlap": {"multi_family_pairs": 2, "known_overlapping": 0,
                            "known_not_overlapping": 1, "unresolved": 1},
    "within_family_discordance": {"mixed_family_pair_records": 0, "scopes_differ": 0,
                                  "scope_shared": 0},
    "contradiction_fields": {"pqtl": "differ", "outcome": "differ", "platform": "differ",
                             "ancestry": "not_stated", "any": "differ"},
    "families_per_year": {"2019": 1, "2021": 1, "2022": 1, "2023": 1, "2024": 1},
    "most_claimed": [("Q00001", 3, 3, 6), ("Q00002", 3, 2, 3), ("Q00003", 1, 1, 1),
                     ("Q00004", 1, 1, 1), ("Q00005", 1, 1, 2)],
    "pairs_per_area": {"AREA:cardio": 3, "AREA:genetic": 2, "AREA:cancer": 1, "AREA:resp": 2,
                       MEASUREMENT: 2},
    "pairs_by_area_rule": {"direct": 6, "nearest_ancestor": 2},
    "outcomes_by_area_assignment": {"direct": 5, "inherited": 1},
    "asthma_area_assignment": {
        "areas": ["AREA:resp"], "disease_areas": ["AREA:resp"], "assignment": "inherited",
        "ancestor_distance": 1, "nearest_ancestors": ["MONDO:resp"],
        "several_equally_near_ancestors": False},
    "distinct_pair_bounds": (8, 10.5),
    # variant -> (h1 pairs, h1 pairs agreeing, H2 multi-family pairs, claim records)
    "sensitivity": {
        "primary": (1, 0, 2, 13),
        "without_eligibility_uncertain": (1, 0, 1, 12),
        "without_also_tissue_or_csf": (1, 0, 2, 10),
        "direction_unverified_included": (1, 0, 2, 13),
        "dictionary_match_failures_included": (1, 0, 2, 14),
        "relation_ambiguous_included": (2, 0, 3, 14),
        "overall_scope_only": (1, 0, 2, 11),
        "h1_without_with_nonsignificant": (0, 0, 2, 11),
        "without_context_unclear": (1, 0, 1, 12),
        "without_fuzzy_family_links": (1, 0, 2, 13),
        "first_public_2020_2025": (1, 0, 1, 8),
        "without_count_not_stated": (0, 0, 2, 9),
        "all_document_types": (1, 0, 2, 14),
        "without_citation_chasing": (1, 0, 1, 12),
        "shared_names_mondo_first": (1, 0, 2, 13),
        "without_phenotype_cross_references": (1, 0, 2, 13),
    },
    "all_document_types": {"records_other_document_type": 2, "eligible_families": 6},

    "sensitivity_by_direction": {
        "primary": {"raises": 10, "lowers_with_nonsignificant": 1},
        "direction_unverified_included": {"raises": 9, "lowers_with_nonsignificant": 1,
                                          "mixed": 1},
        "overall_scope_only": {"raises": 9, "lowers": 1, "unresolved": 1},
    },
    "unclear_as_independent": {"h1_pairs": 2, "h1_pairs_agreeing": 1,
                               "h1_independent_or_unclear_edges": 3},
    # Every dataset name is `whole_study`, so no name is claim-specific and no edge is
    # independent; families A, D and E state at least 1,000 proteins tested.
    "sensitivity_added": {"claim_specific_dataset_names_only": (0, 0, 2, 13),
                          "tested_count_1000_or_more": (0, 0, 1, 6)},
    # Claim records by reference class for families whose pQTL source is a source of the
    # snapshot (C, INTERVAL), another source (A, B) or not stated (D).
    "reference_by_source": {
        "shared_pqtl_source": {"present_same": 1, "present_opposite": 0,
                               "present_nondirectional_or_ambiguous": 0,
                               "no_returned_record": 0, MAPPING_FAILED: 2},
        "other_pqtl_source": {"present_same": 1, "present_opposite": 1,
                              "present_nondirectional_or_ambiguous": 1,
                              "no_returned_record": 2, MAPPING_FAILED: 4},
        "pqtl_not_stated_or_unmatched": {"present_same": 0, "present_opposite": 0,
                                         "present_nondirectional_or_ambiguous": 0,
                                         "no_returned_record": 1, MAPPING_FAILED: 0}},
    # Seven counted claim records with a disease area: P1 holds four, P2 two, P5 one. Only a
    # protein with four records can need three areas (lung cancer, asthma and a cardiovascular
    # outcome): 16 of the 35 ways to give P1 four of the seven outcomes.
    "hub_expectation": {"observed_hubs": 1, "counted_claim_records_with_a_disease_area": 7,
                        "expected_hubs_exact": 16 / 35},
}
# The registered secondaries, each value worked by hand from the scenario (families A 2019,
# B 2021, C 2022, D 2023, E 2024; pair P1 x CAD has A, B and C, pair P2 x CAD has A and D).
# Claim dates: A's preprint PA (2019-11-01) holds P1 x CAD only, so A's claim date is 2019 on
# that pair and 2020 (its journal abstract) on its four other pairs.
SECONDARY = {
    "reporting_completeness": {
        "families_with_a_registry_claim": 4, "eligible_families_without_a_registry_claim": 1,
        "pqtl_dataset_named": 3, "outcome_dataset_named": 3, "pqtl_release_unique": 3,
        "outcome_release_unique": 2, "both_releases_unique": 2, "platform_stated": 4,
        "ancestry_stated": 2},
    "pqtl_labels": {"INTERVAL SomaScan (Sun 2018)": 1, "UKB-PPP discovery": 1,
                    "deCODE SomaScan v4 (Eldjarn 2023 update)": 1, "not_stated": 1},
    "pqtl_components": {"DECODE_COHORT": 1, "INTERVAL": 1, "UKB": 1},
    "edges": 4,
    "edge_pqtl": {"identical_release": 0, "overlapping_participant_source": 0, "disjoint": 3,
                  "unclear": 1},
    "edge_outcome": {"identical_release": 0, "overlapping_participant_source": 1, "disjoint": 2,
                     "unclear": 1},
    "edge_class": {"identical_release": 0, "overlapping": 1, "unclear": 1, "independent": 2},
    # stratum -> (pairs, H2 lower, H2 upper, H2b lower, H2b upper, resolvable pairs)
    "h2_by_k": {"2": (1, 0.0, 1.0, 0.0, 1.0, 0), "3": (1, 0.0, 0.0, 0.0, 0.0, 0),
                "4_or_more": (0, None, None, None, None, 0)},
    "h2_directional": (2, 0.0, 0.5, 0.0, 0.5, 0),
    # edge class -> (edges, edges agreeing)
    "agreement": {"identical_release": (0, 0), "overlapping": (1, 1), "unclear": (1, 1),
                  "independent": (2, 0)},
    "independent_minus_overlapping": -1.0,
    "significance_discordant_pairs": 0,
    # field -> (differ among the 2 discordant edges, differ among the 2 concordant edges)
    "contradiction_comparison": {"pqtl": (2, 1), "outcome": (2, 1), "platform": (1, 1),
                                 "ancestry": (0, 0), "any": (2, 1)},
    "first_claim": {"pairs_with_a_first_family": 2, "pairs_tied_first": 0, "later_families": 3,
                    "later_families_same_direction": 2},
    "first_claim_by_class": {"identical_release": (0, 0), "overlapping": (1, 1),
                             "unclear": (1, 1), "independent": (1, 0)},
    # period -> index -> (pairs, share)
    "periods": {
        "2019-2022": {"h2_upper": (1, 0.0), "h2b_upper": (1, 0.0), "resolvable_share": (1, 0.0),
                      "contradicting_share": (1, 1.0), "h1_pair_concordance": (1, 0.0)},
        "2023-2025": {"h2_upper": (1, 1.0), "h2b_upper": (1, 1.0), "resolvable_share": (1, 0.0),
                      "contradicting_share": (1, 0.0), "h1_pair_concordance": (0, None)}},
    "period_counts": {"2019-2022": (8, 1), "2023-2025": (0, 1)},
    # year -> (families and claim records by family first-public year; pairs claimed, new and
    # already claimed by claim-date year)
    "years": {"2019": (1, 5, 1, 1, 0), "2020": (0, 0, 4, 4, 0), "2021": (1, 4, 3, 2, 1),
              "2022": (1, 3, 2, 1, 1), "2023": (1, 1, 1, 0, 1), "2024": (1, 0, 0, 0, 0)},
    # area -> (pairs, multi-family pairs, pairs with two directional families, contradicting)
    "areas": {"AREA:cardio": (3, 2, 2, 1), "AREA:genetic": (2, 2, 2, 1),
              "AREA:cancer": (1, 0, 0, 0), "AREA:resp": (2, 0, 0, 0), MEASUREMENT: (2, 0, 0, 0)},
    # label -> (edges, edges agreeing): A is on Olink, B and C on SomaScan, D states nothing
    "platforms": {"same_platform": (1, 0), "cross_platform": (2, 1),
                  "platform_unknown": (1, 1)},
    "claims_per_family": {"eligible_families": 5, "claim_records": 13,
                          "families_with_zero_claims": 1, "min": 0, "q25": 1.0, "median": 3,
                          "q75": 4.0, "q90": 5.0, "max": 5, "top_decile_families": 1,
                          "share_of_claim_records_from_top_decile": 5 / 13},
    "top_pairs": [("Q00001", "MONDO:cad", 3, 4), ("Q00002", "MONDO:cad", 2, 2),
                  ("Q00005", "MONDO:asthma", 1, 2)],
    "top_proteins": ["Q00001", "Q00002", "Q00003", "Q00004", "Q00005"],
    "top_outcomes": [("MONDO:cad", 4, 2), ("MONDO:asthma", 2, 2), ("EFO:bmi", 1, 1),
                     ("EFO:crp", 1, 1), ("MONDO:heart", 1, 1), ("MONDO:lungca", 1, 1)],
    # families per pair -> (association, causal, target)
    "wording_by_k": {"1": (1, 4, 2), "2": (1, 1, 0), "3_or_more": (2, 2, 0)},
    # year -> (claim records, with novelty language)
    "novelty_by_year": {"2019": (5, 1), "2021": (4, 1), "2022": (3, 0), "2023": (1, 1)},
    # (later family–pair records, without a reference list, with one, citing an earlier family)
    "citation": (3, 1, 2, 1),
    "citation_novelty": (2, 1, 1, 1),
    "families_with_a_reference_list": 4,
    "by_search_sources": {"epmc+openalex": 1, "pubmed": 1, "pubmed+epmc+openalex": 1,
                          "pubmed+openalex": 1},
    "found_only_by_citation_chasing": 1,
    "document_classes": {"journal": 5},
    "journals": [("Journal One", 2), ("Journal Two", 2), ("Journal Three", 1)],
    # index -> (n, edge_n): pair-level and edge-level counts. P1 x CAD has three directional
    # families (three edges, two independent), P2 x CAD two (one edge); no family is
    # nonsignificant_only; later families by claim date: B and C on P1 x CAD, D on P2 x CAD.
    "accounting": {"registry claim records": (13, None),
                   "distinct pairs; papers per pair": (8, None),
                   "H2; H2b; resolvable share": (2, None),
                   "family–pair direction counts": (11, None),
                   "contradicting pairs; Liu-analogue": (2, None), "H1": (1, 2),
                   "direction-based results": (11, None),
                   "reporting_completeness; dataset_usage": (4, None),
                   "edge_relations": (2, 4), "h2_by_families_per_pair": (2, None),
                   "h2_directional_pairs": (2, None),
                   "direction_agreement_by_edge_class; contradiction_source_comparison; "
                   "platform_pairing": (2, 4),
                   "significance_discordance": (2, 0), "first_claim_concordance": (2, 3),
                   "periods; therapeutic_areas: distinct pairs": (8, None),
                   "periods; therapeutic_areas: repeated-pair indices": (2, None),
                   "yearly_series; claims_per_family; source_overlap; "
                   "document_class_and_journals": (5, None),
                   "top_lists": (8, None), "wording_by_repetition_and_year": (13, None),
                   "citation_of_earlier_claim": (3, None)},
}


def day(text: str) -> PublicDate:
    return PublicDate(value=datetime.date.fromisoformat(text), resolution="day")


def search_records() -> list[SearchRecord]:
    return [SearchRecord(record_id=rid, kind=kind, doi=doi, pmid=None, pmcid=None,
                         published_as_doi=pub, title=f"Proteome-wide MR, study {rid[-1]}",
                         first_author_surname=f"Author{rid[-1]}", first_public=day(date))
            for rid, kind, date, doi, pub in RECORDS]


def extraction_and_checks() -> tuple[list[dict], list[dict]]:
    """Extraction rows (run_extraction.py) and claim checks (verify_claims.py) of the scenario,
    written from one specification so the record ids agree."""
    rows, checks = [], []
    for rid, ((pqtl, outcome), platform, ancestry, claims) in SCENARIO.items():
        out_claims = []
        for i, (protein, outcome_id, direction, span, opts) in enumerate(claims):
            failure = opts.get("first_failure")
            out_claims.append({"evidence_span": span, "platform": opts.get("platform", platform),
                               "ancestry": ancestry, "protein_as_written": f"P{protein}",
                               "outcome_as_written": opts.get("outcome_as_written",
                                                              OUTCOME_NAMES[outcome_id])})
            checks.append({
                "pmid": rid, "claim_index": i, "claim_record_id": f"{rid}:{i:03d}",
                "direction": direction, "evidence_type": "mr_estimate", "span_passes": True,
                "claim_scope": opts.get("claim_scope", "overall"),
                "analysis_context_as_written": opts.get("analysis_context_as_written",
                                                        "not_stated"),
                "subgroup_as_written": opts.get("subgroup_as_written", "not_stated"),
                "relation_ambiguous": opts.get("relation_ambiguous", False),
                "dataset_attribution": "whole_study", "pqtl_datasets": pqtl,
                "outcome_datasets": outcome, "protein_ids": [f"HGNC:{protein}"],
                "outcome_ids": [outcome_id], "protein_check": "pass",
                "outcome_check": opts.get("outcome_check", "pass"),
                "direction_verification_state": opts.get("direction_verification_state",
                                                         "agrees"),
                "enters_registry": failure is None, "first_failure": failure})
        rows.append({"pmid": rid, "status": "ok", "output": {"claims": out_claims}})
    rows.append({"pmid": "E", "status": "extraction_failed", "output": None})
    return rows, checks


def write_resources(folder: pathlib.Path) -> Resources:
    folder.mkdir(parents=True)

    def table(name: str, header: list[str], rows: list) -> pathlib.Path:
        path = folder / name
        with path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
        return path

    with DICTIONARY.open(newline="") as f:
        pqtl_rows = [(r["name"], r["platform"]) for r in csv.DictReader(f) if r["side"] == "pqtl"]
    reactome = folder / "UniProt2Reactome.txt"
    reactome.write_text("".join(f"{acc}\t{p}\turl\tPathway {p[-1]}\tTAS\tHomo sapiens\n"
                                for p, accs in PATHWAYS.items() for acc in accs)
                        + f"{ACC[1]}\tR-MMU-1\turl\tMouse pathway\tIEA\tMus musculus\n")
    snapshot = folder / "mrres_estimates.jsonl"
    snapshot.write_text("".join(json.dumps({"expID": e, "outID": o, "beta": b}) + "\n"
                                for e, o, b in SNAPSHOT_ESTIMATES))
    return Resources(
        ontology_edges=table("ontology_edges.csv", ["child", "parent"], EDGES),
        therapeutic_areas=table("therapeutic_areas.csv", ["canonical_id", "therapeutic_areas"],
                                [(k, "|".join(v)) for k, v in AREAS.items()]),
        therapeutic_area_names=table("therapeutic_area_names.csv",
                                     ["area_id", "name", "disease_area"],
                                     [(k, v, int(k != MEASUREMENT))
                                      for k, v in AREA_NAMES.items()]),
        assay_lists=table("assay_lists.csv", ["list_id", "accession"],
                          [(k, a) for k, v in LISTS.items() for a in v]),
        attachments=table("attachments.csv",
                          ["dictionary_row", "platform_string", "assay_list",
                           "background_level", "whole_panel_assay_list",
                           "alternative_assay_list", "assay_reagents", "reported_targets",
                           "analysed_targets", "status", "basis"],
                          [(n, p, *ATTACHED.get(n, ("", "unavailable", "")), "", "", "", "",
                            "synthetic", "") for n, p in pqtl_rows]),
        reactome=reactome, snapshot_estimates=snapshot,
        protein_mapping=table("protein_mapping.csv", ["name", "state", "accession"],
                              [(n, "mapped" if a else "no_hgnc", a or "")
                               for n, a in SNAPSHOT_PROTEINS.items()]),
        trait_mapping=table("trait_mapping.csv",
                            ["name", "state", "name_rule", "alias_relation", "canonical_id"],
                            [(n, "mapped" if o else "unmapped", *TRAIT_RULES.get(n, ("", "")),
                              o or "") for n, o in SNAPSHOT_TRAITS.items()]),
        locus_list=table("loci.csv", ["gene", "variant_rows"], [("ABO", 1), ("APOE", 1)]))


def expect(name: str, got, want) -> None:
    if got != want:
        raise AssertionError(f"dry run: {name} is {got!r}, expected {want!r}")


def close(name: str, got: float, want: float) -> None:
    if abs(got - want) > 1e-12:
        raise AssertionError(f"dry run: {name} is {got!r}, expected {want!r}")


def read_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def check_secondaries(sec: dict) -> None:
    """Every registered secondary against SECONDARY."""
    want = SECONDARY
    rc = sec["reporting_completeness"]
    for k, v in want["reporting_completeness"].items():
        expect(f"reporting completeness {k}", rc[k]["families"] if isinstance(rc[k], dict)
               else rc[k], v)
    usage = sec["dataset_usage"]
    expect("pQTL labels", usage["families_per_pqtl_label"], want["pqtl_labels"])
    expect("pQTL components", usage["families_per_pqtl_component"], want["pqtl_components"])
    expect("dataset combinations", [c["families"] for c in
                                    usage["commonest_pqtl_outcome_combinations"]], [1, 1, 1, 1])
    er = sec["edge_relations"]
    expect("edges", er["edges"], want["edges"])
    for key, table in (("edge_pqtl", "pqtl_side"), ("edge_outcome", "outcome_side"),
                       ("edge_class", "edge_class")):
        expect(key, {k: v["edges"] for k, v in er[table].items()}, want[key])

    def h2_row(tables: dict) -> tuple:
        a, b = tables["h2_identical_release"], tables["h2b_identical_or_overlapping"]
        return (a["pairs"], a["lower"], a["upper"], b["lower"], b["upper"],
                tables["resolvable_pairs"])

    expect("H2 by families per pair", {k: h2_row(v) for k, v in
                                       sec["h2_by_families_per_pair"].items()}, want["h2_by_k"])
    expect("H2 on directional pairs", h2_row(sec["h2_directional_pairs"]),
           want["h2_directional"])
    agreement = sec["direction_agreement_by_edge_class"]
    expect("agreement by edge class", {c: (agreement[c]["edges"], agreement[c]["edges_agreeing"])
                                       for c in want["agreement"]}, want["agreement"])
    expect("positive control", agreement["identical_release"]["role"], "positive_control")
    close("independent minus overlapping",
          agreement["independent_minus_overlapping"]["difference"],
          want["independent_minus_overlapping"])
    expect("significance-discordant pairs",
           sec["significance_discordance"]["significance_discordant_pairs"],
           want["significance_discordant_pairs"])
    comparison = sec["contradiction_source_comparison"]
    expect("discordant and concordant edges",
           (comparison["discordant_edges"], comparison["concordant_edges"]), (2, 2))
    expect("contradiction-source comparison",
           {f: (comparison[f]["discordant_differ"], comparison[f]["concordant_differ"])
            for f in want["contradiction_comparison"]}, want["contradiction_comparison"])
    first = sec["first_claim_concordance"]
    for k, v in want["first_claim"].items():
        expect(f"first claim {k}", first[k], v)
    expect("first claim by edge class",
           {c: (v["later_families"], v["same_direction"])
            for c, v in first["by_edge_class"].items()}, want["first_claim_by_class"])
    periods = sec["periods"]
    for period, rows in want["periods"].items():
        expect(f"period counts {period}", (periods[period]["distinct_pairs"],
                                           periods[period]["multi_family_pairs"]),
               want["period_counts"][period])
        for index, row in rows.items():
            expect(f"period {period} {index}", (periods[period][index]["pairs"],
                                                periods[period][index]["share"]), row)
    close("H2 upper bound, later minus earlier",
          periods["later_minus_earlier"]["h2_upper"]["difference"], 1.0)
    expect("H1 difference between periods",
           periods["later_minus_earlier"]["h1_pair_concordance"]["difference"], None)
    expect("yearly series",
           {y: (v["families"], v["claim_records"], v["pairs_claimed"], v["new_pairs"],
                v["pairs_already_claimed_in_an_earlier_year"])
            for y, v in sec["yearly_series"].items()}, want["years"])
    expect("therapeutic areas",
           {a: (v["pairs"], v["multi_family_pairs"], v["pairs_with_two_directional_families"],
                v["contradicting_pairs"]) for a, v in sec["therapeutic_areas"].items()},
           want["areas"])
    cardio = sec["therapeutic_areas"]["AREA:cardio"]
    expect("H2 bounds in the cardiovascular area", h2_row(cardio), (2, 0.0, 0.5, 0.0, 0.5, 0))
    platforms = sec["platform_pairing"]
    expect("platform pairing", {k: (platforms[k]["edges"], platforms[k]["edges_agreeing"])
                                for k in want["platforms"]}, want["platforms"])
    close("cross minus same platform", platforms["cross_minus_same"]["difference"], 0.5)
    expect("claims per family", sec["claims_per_family"], want["claims_per_family"])
    top = sec["top_lists"]
    expect("top pairs", [(p["protein_id"], p["outcome_id"], p["families"], p["claim_records"])
                         for p in top["pairs"][:3]], want["top_pairs"])
    expect("top proteins", [p["id"] for p in top["proteins"]], want["top_proteins"])
    expect("top outcomes", [(o["id"], o["families"], o["pairs"]) for o in top["outcomes"]],
           want["top_outcomes"])
    wording = sec["wording_by_repetition_and_year"]
    expect("wording by families per pair",
           {k: tuple(v[w]["claim_records"] for w in ("association", "causal", "target"))
            for k, v in wording["by_families_per_pair"].items()}, want["wording_by_k"])
    expect("novelty language by year",
           {y: (v["claim_records"], v["novelty_language"])
            for y, v in wording["novelty_language_by_year"].items()}, want["novelty_by_year"])
    citation = sec["citation_of_earlier_claim"]

    def cite_row(table: dict) -> tuple:
        return (table["later_family_pair_records"], table["without_a_reference_list"],
                table["with_a_reference_list"], table["citing_an_earlier_family_of_the_pair"])

    expect("citation of the earlier claim", cite_row(citation["later_families"]),
           want["citation"])
    expect("citation, novelty-language claims", cite_row(citation[
        "later_families_with_novelty_language_and_an_earlier_registry_claim"]),
        want["citation_novelty"])
    expect("families with a reference list",
           citation["eligible_families_with_a_reference_list"],
           want["families_with_a_reference_list"])
    overlap = sec["source_overlap"]
    expect("families by search sources", overlap["by_search_sources"],
           want["by_search_sources"])
    expect("found only by chasing", overlap["found_only_by_citation_chasing"],
           want["found_only_by_citation_chasing"])
    documents = sec["document_class_and_journals"]
    expect("document classes", documents["families_by_document_class"],
           want["document_classes"])
    expect("journals", [(j["journal"], j["families"])
                        for j in documents["journals_with_most_families"]], want["journals"])
    expect("accounting", {r["index"]: (r["n"], r["edge_n"]) for r in sec["accounting"]},
           want["accounting"])
    expect("claim records left out", sec["accounting"][0]["left"],
           EXPECTED["assembly"]["left_out"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    out: pathlib.Path = a.out
    inputs, joins = out / "inputs", out / "joins"
    records = search_records()
    decisions = {rid: {"decision": d, "flags": flags, "n_proteins_tested": TESTED[rid]}
                 for rid, (d, flags) in DECISIONS.items()}
    rows, checks = extraction_and_checks()
    status = {r["pmid"]: r["status"] for r in rows}

    assembly = assemble(records, decisions, status, checks, HGNC_UNIPROT, {})
    write(assembly, inputs)
    tags = tags_from_extraction(rows, load_lexicon())
    (inputs / "claim_tags.jsonl").write_text("".join(t.model_dump_json() + "\n" for t in tags))
    abstracts = inputs / "abstracts.jsonl"
    abstracts.write_text("".join(json.dumps({"pmid": k, "abstract": v}) + "\n"
                                 for k, v in ABSTRACTS.items()))
    resources = write_resources(out / "resources")
    kinds = {r.record_id: r.kind for r in records}
    (inputs / "record_metadata.jsonl").write_text("".join(RecordMeta(
        record_id=rid, kind=kinds[rid], search_sources=sources, chase_round=chase,
        journal=journal, openalex_ids=(work,), has_reference_list=bool(cited),
        referenced_works=tuple(cited), first_author_country=None).model_dump_json() + "\n"
        for rid, (sources, chase, journal, work, cited) in RECORD_META.items()))

    claims = assembly.claims["confirmatory"]
    in_registry = {c.claim_record_id for c in claims}
    wording: dict[str, int] = {}
    for t in tags:
        if t.claim_record_id in in_registry:
            wording[t.wording_class] = wording.get(t.wording_class, 0) + 1
    e = EXPECTED["assembly"]
    expect("eligible families", len(assembly.meta), e["eligible_families"])
    expect("registry claims", len(claims), e["registry_claims"])
    expect("dating claims", len(assembly.dating_claims["confirmatory"]), e["dating_claims"])
    expect("left out", assembly.report["registry"]["left_out_by_reason"], e["left_out"])
    expect("wording classes", wording, EXPECTED["wording"])

    s = run_all(inputs, abstracts, joins, resources, n_boot=N_BOOT)
    for k, v in EXPECTED["novelty"].items():
        expect(f"novelty {k}", s["novelty_index"][k], v)
    ref = s["reference_screen"]
    expect("reference pairs", ref["pairs_by_class"], EXPECTED["reference_pairs"])
    expect("reference claims", ref["claim_records_by_class"], EXPECTED["reference_claims"])
    expect("reference by novelty language", ref["claim_records_by_novelty_language"]["true"],
           EXPECTED["reference_novelty_language"])
    expect("reference by shared pQTL source", ref["claim_records_by_shared_pqtl_source"],
           EXPECTED["reference_by_source"])
    for k, v in EXPECTED["novelty"].items():
        expect(f"novelty from registry abstracts only {k}",
               s["novelty_index"]["sensitivity_claim_dates_from_registry_abstracts_only"][k], v)
    expect("reference pairs, names as written",
           ref["sensitivity_names_as_written_only"]["pairs_by_class"],
           EXPECTED["reference_pairs_as_written"])
    expect("reference pairs, proxy aliases included",
           ref["sensitivity_proxy_trait_aliases_included"]["pairs_by_class"],
           EXPECTED["reference_pairs_with_proxy_aliases"])
    expect("hubs", s["hub_proteins"]["hub_proteins"], EXPECTED["hubs"])
    volume, eh = s["hub_proteins"]["expected_from_claim_volume"], EXPECTED["hub_expectation"]
    for k in ("observed_hubs", "counted_claim_records_with_a_disease_area"):
        expect(f"hub expectation {k}", volume[k], eh[k])
    if abs(volume["expected_hubs"] - eh["expected_hubs_exact"]) > 0.06:
        raise AssertionError(f"dry run: expected hubs {volume['expected_hubs']!r} is not "
                             f"within 0.06 of the exact {eh['expected_hubs_exact']!r}")
    for variant in ("null_result_claims_counted", "distinct_therapeutic_areas",
                    "family_pair_collapsed"):
        expect(f"hubs, {variant}", s["hub_proteins"][f"sensitivity_{variant}"]["hub_proteins"],
               EXPECTED["hubs"])
    # No two counted records share a family, protein and outcome, so the collapse keeps all 7.
    collapsed = s["hub_proteins"]["sensitivity_family_pair_collapsed"][
        "expected_from_claim_volume"]
    expect("hub expectation, family–pair units",
           (collapsed["counted_unit"], collapsed["observed_hubs"],
            collapsed["counted_claim_records_with_a_disease_area"]), ("family_pair", 1, 7))
    expect("enrichment states", s["pathway_enrichment"]["claims_by_enrichment_state"],
           EXPECTED["enrichment_states"])
    expect("enrichment states, any candidate row",
           s["pathway_enrichment"]["sensitivity_any_candidate_row_attachment"][
               "claims_by_enrichment_state"], EXPECTED["enrichment_states"])
    expect("enrichment states, null-result claims counted",
           s["pathway_enrichment"]["sensitivity_null_result_claims_counted"][
               "claims_by_enrichment_state"], EXPECTED["enrichment_states"])
    got_rows = {(r["assay_list"], r["pathway_id"]): r
                for r in read_jsonl(joins / "pathway_enrichment_rows.jsonl")}
    expect("pathways named in the text", [k for k, r in got_rows.items() if r["named_in_text"]],
           [])
    expect("enrichment rows", sorted(got_rows), sorted(EXPECTED["enrichment_rows"]))
    for key, (k, n, big_k, big_n, p, q) in EXPECTED["enrichment_rows"].items():
        r = got_rows[key]
        expect(f"enrichment counts {key}", (r["claimed_in_pathway"], r["claimed"],
                                            r["background_in_pathway"], r["background"]),
               (k, n, big_k, big_n))
        close(f"enrichment p {key}", r["p_one_sided_fisher"], p)
        close(f"enrichment q {key}", r["q_benjamini_hochberg"], q)
    whole = {(r["assay_list"], r["pathway_id"]): r for r in read_jsonl(
        joins / "pathway_enrichment_rows_whole_panel_backgrounds.jsonl")}
    expect("enrichment rows, whole panel", sorted(whole),
           sorted(EXPECTED["enrichment_rows_whole_panel"]))
    for key, (k, n, big_k, big_n, p, q) in EXPECTED["enrichment_rows_whole_panel"].items():
        r = whole[key]
        expect(f"whole-panel enrichment counts {key}",
               (r["claimed_in_pathway"], r["claimed"], r["background_in_pathway"],
                r["background"]), (k, n, big_k, big_n))
        close(f"whole-panel enrichment p {key}", r["p_one_sided_fisher"], p)
        close(f"whole-panel enrichment q {key}", r["q_benjamini_hochberg"], q)
    expect("enrichment states, whole panel",
           s["pathway_enrichment"]["sensitivity_whole_panel_backgrounds"][
               "claims_by_enrichment_state"], EXPECTED["enrichment_states"])
    levels: dict[str, int] = {}
    for level in s["pathway_enrichment"]["background_level_by_dictionary_row"].values():
        levels[level] = levels.get(level, 0) + 1
    expect("background levels", levels, EXPECTED["background_levels"])
    expect("density", {(d["pathway_id"], d["outcome_id"]): (d["families"], d["proteins"])
                       for d in read_jsonl(joins / "pathway_claim_density.jsonl")},
           EXPECTED["density"])
    h, eh = s["hierarchy_tables"], EXPECTED["hierarchy"]
    expect("hierarchy relations", h["hierarchy_relations"], eh["hierarchy_relations"])
    for k in ("anchors", "anchors_with_a_one_step_relative"):
        expect(f"pair families {k}", h["pair_families"][k], eh[k])
    for k in ("h1_pairs", "h1_pairs_agreeing", "h1_independent_edges", "h2_multi_family_pairs",
              "h2_known_not_identical"):
        expect(f"pair families {k}", h["pair_families"]["estimates"][k], eh[k])
    ind = s["registry_indices"]
    expect("papers per pair", ind["papers_per_pair"], EXPECTED["papers_per_pair"])
    for k, v in EXPECTED["participant_overlap"].items():
        expect(f"participant overlap {k}", ind["participant_overlap_share"][k], v)
    expect("within-family discordance", ind["within_family_discordance"],
           EXPECTED["within_family_discordance"])
    expect("contradicting pairs", ind["contradiction_sources"]["contradicting_pairs"], 1)
    for field, state in EXPECTED["contradiction_fields"].items():
        expect(f"contradiction source {field}", ind["contradiction_sources"][field].get(state), 1)
    land = ind["landscape"]
    expect("families per year", land["families_per_year"], EXPECTED["families_per_year"])
    expect("most claimed proteins",
           [(p["protein_id"], p["families"], p["pairs"], p["claim_records"])
            for p in land["most_claimed_proteins"]], EXPECTED["most_claimed"])
    expect("pairs per therapeutic area", land["pairs_per_therapeutic_area"],
           dict(sorted(EXPECTED["pairs_per_area"].items())))
    expect("pairs by area rule", land["pairs_by_area_rule"], EXPECTED["pairs_by_area_rule"])
    expect("outcomes by area assignment", land["outcomes_by_area_assignment"],
           EXPECTED["outcomes_by_area_assignment"])
    expect("area assignment of asthma", land["outcome_area_assignments"]["MONDO:asthma"],
           EXPECTED["asthma_area_assignment"])
    expect("inherited outcomes by distance", land["inherited_outcomes_by_ancestor_distance"],
           {"1": 1})
    expect("inherited outcomes with ties",
           land["inherited_outcomes_with_several_equally_near_ancestors"], 0)
    bounds = ind["distinct_pair_bounds"]
    expect("distinct pair bounds", (bounds["distinct_pairs_lower"],
                                    bounds["distinct_pairs_upper"]),
           EXPECTED["distinct_pair_bounds"])

    sens = sensitivity_run(records, decisions, status, checks, HGNC_UNIPROT, {},
                           load_graph(resources.ontology_edges), load_rows(), n_boot=N_BOOT,
                           chased=CHASED)
    (out / "sensitivity_tables.json").write_text(json.dumps(sens, indent=1))
    for variant, (h1, agree, multi, n_claims) in EXPECTED["sensitivity"].items():
        est = sens[variant]["estimates"]
        expect(f"sensitivity {variant}", (est["h1_pairs"], est["h1_pairs_agreeing"],
                                          est["h2_multi_family_pairs"],
                                          sens[variant]["claim_records"]),
               (h1, agree, multi, n_claims))
    for k, v in EXPECTED["all_document_types"].items():
        expect(f"all document types {k}", sens["all_document_types"][k], v)
    for variant, by_direction in EXPECTED["sensitivity_by_direction"].items():
        expect(f"sensitivity directions {variant}",
               sens[variant]["denominators"]["by_direction"], by_direction)
    pf = sens["pair_families"]["estimates"]
    expect("sensitivity pair_families", (pf["h1_pairs"], pf["h1_pairs_agreeing"]),
           (eh["h1_pairs"], eh["h1_pairs_agreeing"]))
    for variant, (h1, agree, multi, n_claims) in EXPECTED["sensitivity_added"].items():
        est = sens[variant]["estimates"]
        expect(f"sensitivity {variant}", (est["h1_pairs"], est["h1_pairs_agreeing"],
                                          est["h2_multi_family_pairs"],
                                          sens[variant]["claim_records"]),
               (h1, agree, multi, n_claims))
    check_secondaries(s["registry_secondaries"])
    for k, v in EXPECTED["unclear_as_independent"].items():
        expect(f"unclear edges as independent {k}", sens["h1_unclear_edges_as_independent"][k], v)
    primary = sens["primary"]["estimates"]
    for k, v in EXPECTED["participant_overlap"].items():
        if k != "multi_family_pairs":
            expect(f"H2b in the sensitivity tables {k}",
                   primary[{"unresolved": "h2b_unresolved"}.get(k, f"h2b_{k}")], v)
    print(json.dumps({"out": str(out), "checked": sorted(EXPECTED)}, indent=1))


if __name__ == "__main__":
    main()
