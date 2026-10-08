import pytest

import h2_unresolved_diagnostic as d
from build_registry import RegistryClaim


def claim(record, family, pair=("P1", "O1"), pqtl=("deCODE",), outcome=("FinnGen R9",),
          attribution="whole_study"):
    return RegistryClaim(
        claim_record_id=f"{record}:000", family_id=family, protein_id=pair[0],
        outcome_id=pair[1], direction="raises", direction_verified=True, claim_scope="overall",
        context_key="", pqtl_datasets=pqtl, outcome_datasets=outcome,
        dataset_attribution=attribution)


CLAIMS = [
    # pair 1: both families name the release on the outcome side; the pQTL name is ambiguous
    claim("r1", "F1"), claim("r2", "F2"),
    # pair 2: one family names nothing on the outcome side, the other an ambiguous name
    claim("r1", "F1", ("P2", "O1"), outcome=("not_stated",)),
    claim("r3", "F3", ("P2", "O1"), outcome=("FinnGen",)),
    # pair 3: every name maps to one row and the rows are the same: identical, not unresolved
    claim("r4", "F4", ("P3", "O1"), pqtl=("deCODE SomaScan v4 (Ferkingstad 2021)",)),
    claim("r5", "F5", ("P3", "O1"), pqtl=("deCODE SomaScan v4 (Ferkingstad 2021)",)),
    # pair 4: one family only
    claim("r6", "F6", ("P4", "O1")),
    # pair 5: unique names on both sides, one family's attribution unclear
    claim("r4", "F4", ("P5", "O1"), pqtl=("deCODE SomaScan v4 (Ferkingstad 2021)",)),
    claim("r7", "F7", ("P5", "O1"), pqtl=("deCODE SomaScan v4 (Ferkingstad 2021)",),
          attribution="unclear")]
CATEGORY = {("r1", "pqtl", "deCODE"): "release_not_identified",
            ("r2", "pqtl", "deCODE"): "conflicting_identifiers",
            ("r3", "outcome", "FinnGen"): "dataset_absent_from_dictionary"}
PASSAGES = {("r1", "pqtl", "deCODE"): "We used GCST90012345 (n = 35,559).",
            ("r3", "outcome", "FinnGen"): "See Supplementary Table 2 and github.com/x/y."}
TEXT = {"r1": ("full_text", "Data: ebi-a-GCST90012345; 4,907 cases were studied."),
        "r2": ("abstract", "Nothing of the kind."), "r3": ("abstract", "supplementary data")}


@pytest.fixture(scope="module")
def made():
    return d.diagnose(CLAIMS, CATEGORY, PASSAGES, TEXT)


def test_only_multi_family_pairs_that_the_registered_functions_leave_unresolved_are_read(made):
    assert made["multi_family_pairs"] == 4
    assert made["h2"]["unresolved_pairs"] == 3


def test_blocking_mentions_are_the_names_that_do_not_map_to_one_row(made):
    h2 = made["h2"]
    # r1 and r2 pQTL (pair 1); r1 and r3 pQTL, r1 and r3 outcome (pair 2); pair 5 has none
    assert h2["blocking_mentions"] == 5 and h2["blocking_papers"] == 3
    assert h2["blocking_mentions_by_side"] == {"pqtl": 3, "outcome": 2}
    assert h2["blocking_mentions_by_manual_coding_category"] == {
        "conflicting_identifiers": 1, "dataset_absent_from_dictionary": 1,
        "never queued: named, not in the queue": 1, "never queued: no dataset named": 1,
        "release_not_identified": 1}
    assert h2["blocking_mentions_by_mapping_state"] == {"release_ambiguous": 4, "not_stated": 1}
    assert h2["pairs_blocked_per_mention"]["max"] == 2      # r1's pQTL name blocks pairs 1 and 2
    assert h2["pairs_blocked_per_mention"]["distribution"] == {1: 4, 2: 1}


def test_a_pair_is_resolved_only_by_all_its_mentions_and_never_past_an_attribution_block(made):
    h2 = made["h2"]
    assert h2["pairs_with_an_attribution_block"] == 1
    assert h2["pairs_resolved_by_every_blocking_mention"] == 2
    assert h2["pairs_resolved_by_the_top_mentions"]["10"] == 2
    assert h2["mentions_needed_to_resolve_every_pair_that_mentions_can_resolve"] == 5
    blocked = {"a": {("x", "pqtl", "1"), ("y", "pqtl", "2")}, "b": {("x", "pqtl", "1")},
               "c": {("z", "pqtl", "3")}, "e": set()}
    cover = d.coverage(blocked, barred={"c"})
    assert cover["order"][0] == ("x", "pqtl", "1")
    assert cover["pairs_resolved_by_every_blocking_mention"] == 3
    assert d.coverage({"a": blocked["a"], "b": blocked["b"]}, set())[
        "pairs_resolved_by_the_top_mentions"]["10"] == 2
    assert cover["pairs_with_no_blocking_mention_and_no_attribution_block"] == 1


def test_pairs_are_counted_by_the_side_on_which_a_comparison_is_undetermined(made):
    assert made["h2"]["unresolved_pairs_by_undetermined_side"] == {
        "both sides": 2, "pqtl side only": 1}


def test_stored_material_is_counted_by_pattern_in_passages_and_in_the_papers_text(made):
    s = made["h2"]["stored_material_for_the_blocking_mentions"]
    assert s["mentions"] == 5 and s["mentions_with_passages_given_to_the_coders"] == 2
    assert s["in_the_mention_s_passages"] == {
        "sample_size_or_case_control_count": 1, "gwas_accession": 1, "code_repository_link": 1,
        "supplementary_material_mention": 1}
    assert s["anywhere_in_the_paper_s_stored_text"]["gwas_accession"] == 2     # two r1 mentions
    assert s["anywhere_in_the_paper_s_stored_text"]["supplementary_material_mention"] == 2
    assert s["stored_text_of_the_paper"] == {"abstract": 3, "full_text": 2}
    named = made["h2"]["stored_material_for_the_blocking_mentions_that_name_a_dataset"]
    assert named["mentions"] == 4


def test_patterns_find_accessions_counts_links_and_supplements_and_nothing_in_plain_text():
    assert all(d.found("ukb-b-19953, finn-b-I9_CHD, ieu-a-7 and GCST004988; n = 12,345; "
                       "https://github.com/a/b; Supplementary Data 3").values())
    assert not any(d.found("Protein X was associated with outcome Y in 2021.").values())
    assert d.found("we studied 60,801 cases and 123,504 controls")[
        "sample_size_or_case_control_count"]


def test_the_resource_of_a_name_is_what_its_candidate_rows_have_in_common():
    assert d.common_prefix(("FinnGen R9", "FinnGen R10", "unlisted release of finngen")) == "FinnGen"
    assert d.common_prefix(("UK Biobank a", "UK Biobank b")) == "UK Biobank"
    assert d.common_prefix(("A x", "B y")) == "candidate rows of several resources"
    assert d.common_prefix(("unlisted release of x",)) == "unlisted release only"
