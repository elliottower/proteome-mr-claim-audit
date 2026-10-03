import pytest

from assay_backgrounds import load_lists
from build_registry import RegistryClaim
from claim_tags import ClaimTags
from dataset_relations import load_rows, map_name
from pathway_enrichment import (ASSAY_LISTS, ATTACHMENTS, PathwayInputError, benjamini_hochberg,
                                claim_density, claimed_sets, enrich, enrichment, fisher_greater,
                                lists_of_names, load_attachments, load_reactome)


@pytest.fixture(scope="module")
def rows():
    return load_rows()


@pytest.fixture(scope="module")
def attachments():
    return load_attachments(ATTACHMENTS, load_lists(ASSAY_LISTS))


def claim(rid, family, protein, pqtl, outcome="O1", direction="raises"):
    return RegistryClaim(
        claim_record_id=rid, family_id=family, protein_id=protein, outcome_id=outcome,
        direction=direction, direction_verified=True, claim_scope="overall", context_key=rid,
        pqtl_datasets=tuple(pqtl), outcome_datasets=("not_stated",),
        dataset_attribution="whole_study")


def tag(rid, wording="causal", platform=("Olink",)):
    return ClaimTags(claim_record_id=rid, pmid="1", wording_class=wording,
                     novelty_language=False, platform=platform, ancestry="not_stated")


def test_fisher_one_sided_matches_hand_worked_hypergeometric_tails():
    assert fisher_greater(2, 4, 3, 10) == pytest.approx(40 / 120)
    assert fisher_greater(3, 4, 3, 10) == pytest.approx(4 / 120)
    assert fisher_greater(1, 4, 3, 10) == pytest.approx(1 - 20 / 120)
    assert fisher_greater(0, 4, 3, 10) == 1.0
    assert fisher_greater(3, 10, 3, 20) == pytest.approx(120 / 1140)


def test_benjamini_hochberg_is_monotone_step_up():
    q = benjamini_hochberg([0.01, 0.04, 0.03, 0.5])
    assert q == pytest.approx([0.04, 0.16 / 3, 0.16 / 3, 0.5])
    assert benjamini_hochberg([]) == []
    assert benjamini_hochberg([0.9, 0.8]) == pytest.approx([0.9, 0.9])


def test_pathways_outside_ten_to_five_hundred_background_proteins_are_dropped():
    background = frozenset(f"B{i}" for i in range(600))
    pathways = {"p9": frozenset(f"B{i}" for i in range(9)),
                "p10": frozenset(f"B{i}" for i in range(10)) | {"OUTSIDE"},
                "p500": frozenset(f"B{i}" for i in range(500)),
                "p501": frozenset(f"B{i}" for i in range(501)),
                "elsewhere": frozenset(f"X{i}" for i in range(50))}
    names = {p: p for p in pathways}
    table, summary = enrich("L", {"B0", "B1"}, background, pathways, names)
    assert [r.pathway_id for r in table] == ["p10", "p500"]
    assert summary["pathways_tested"] == 2 and summary["pathways_dropped_by_size"] == 2


def test_enrichment_restricts_the_claimed_set_to_the_background():
    background = frozenset(f"B{i}" for i in range(20))
    pathways = {"pw": frozenset(f"B{i}" for i in range(10)) | {"X"},
                "rest": frozenset(f"B{i}" for i in range(10, 20))}
    table, summary = enrich("L", {"B0", "B1", "B2", "Z"}, background, pathways,
                            {"pw": "a pathway", "rest": "the rest"})
    row = {r.pathway_id: r for r in table}
    assert (row["pw"].claimed_in_pathway, row["pw"].claimed, row["pw"].background_in_pathway,
            row["pw"].background) == (3, 3, 10, 20)
    assert row["pw"].p_one_sided_fisher == pytest.approx(120 / 1140)
    assert row["rest"].p_one_sided_fisher == 1.0
    assert row["pw"].q_benjamini_hochberg == pytest.approx(2 * 120 / 1140)
    assert summary["claimed_outside_background"] == 1


def test_a_dataset_name_gives_a_list_only_when_all_its_dictionary_rows_share_it(rows, attachments):
    def lists(*names):
        return lists_of_names([map_name(n, "pqtl", rows) for n in names], attachments)

    assert lists("UKB-PPP discovery") == {"olink_explore_3072"}
    assert lists("UKB-PPP") == {"olink_explore_3072"}
    assert lists("deCODE") == {"somascan_v4"}
    assert lists("INTERVAL") == {"somascan_160410"}
    assert lists("SCALLOP") == frozenset()
    assert lists("Fenland") == frozenset()
    assert lists("not_stated") == frozenset()
    assert lists("UKB-PPP", "deCODE 2023", "SCALLOP") == {"olink_explore_3072", "somascan_v4"}
    # Rows read from the dataset's source paper: a custom array, a discontinued panel, a union.
    assert lists("AGES") == {"somascan_ages_custom"}
    assert lists("KORA") == {"somascan_v3.2_kora"}
    assert lists("SCALLOP CVD-I (Folkersen 2020)") == {"olink_target_96:CVD I"}
    assert lists("MANOLIS (Gilly 2020)") == {"olink_manolis_gilly2020_analysed"}


def test_claimed_sets_follow_wording_platform_and_family_datasets(rows, attachments):
    claims = [claim("1:000", "F1", "PA", ["UKB-PPP discovery"]),
              claim("1:001", "F1", "PA", ["deCODE 2023"]),
              claim("1:002", "F1", "PB", ["UKB-PPP discovery"]),
              claim("1:003", "F1", "PC", ["UKB-PPP discovery"]),
              claim("1:004", "F2", "PD", ["SCALLOP"]),
              claim("1:005", "F2", "PE", ["UKB-PPP discovery"])]
    tags = {"1:000": tag("1:000"), "1:001": tag("1:001", wording="association"),
            "1:002": tag("1:002", wording="association"),
            "1:003": tag("1:003", platform=("not_stated",)), "1:004": tag("1:004"),
            "1:005": tag("1:005", wording="target")}
    claimed, counts = claimed_sets(claims, tags, rows, attachments)
    # PA: the family's datasets on the pair are the union over its two records. PC: the dataset
    # row decides, so a claim whose `platform` field is `not_stated` still enters.
    assert claimed == {"olink_explore_3072": {"PA", "PC", "PE"}, "somascan_v4": {"PA"}}
    assert counts == {"enters_enrichment": 3, "not_causal_or_target": 2,
                      "no_pinned_assay_list": 1}


def test_any_candidate_row_attachment_gives_every_list_of_a_generic_name(rows, attachments):
    def lists(*names):
        return lists_of_names([map_name(n, "pqtl", rows) for n in names], attachments,
                              any_row=True)

    assert lists("Fenland") == {"somascan_v4", "fenland_covid_179"}
    scallop = lists("SCALLOP")
    assert {"olink_target_96:INF", "olink_target_96:CVD I"} < scallop and len(scallop) == 3
    assert lists("not_stated") == frozenset()
    claims = [claim("1:000", "F1", "PA", ["Fenland"]),
              claim("1:001", "F2", "PB", ["UKB-PPP discovery"])]
    tags = {"1:000": tag("1:000"), "1:001": tag("1:001", platform=("not_stated",))}
    primary, counts = claimed_sets(claims, tags, rows, attachments)
    assert primary == {"olink_explore_3072": {"PB"}}
    assert counts == {"no_pinned_assay_list": 1, "enters_enrichment": 1}
    any_row, counts = claimed_sets(claims, tags, rows, attachments, any_row=True)
    assert any_row == {"somascan_v4": {"PA"}, "fenland_covid_179": {"PA"},
                       "olink_explore_3072": {"PB"}}
    assert counts == {"enters_enrichment": 2}


def test_claim_reporting_no_significant_estimate_enters_no_claimed_set(rows, attachments):
    claims = [claim("1:000", "F1", "PA", ["UKB-PPP discovery"],
                    direction="reported_nonsignificant_or_null"),
              claim("1:001", "F1", "PB", ["UKB-PPP discovery"])]
    tags = {c.claim_record_id: tag(c.claim_record_id) for c in claims}
    claimed, counts = claimed_sets(claims, tags, rows, attachments)
    assert claimed == {"olink_explore_3072": {"PB"}}
    assert counts == {"enters_enrichment": 1, "reports_no_significant_estimate": 1}
    counted, _ = claimed_sets(claims, tags, rows, attachments, count_null=True)
    assert counted == {"olink_explore_3072": {"PA", "PB"}}


def test_pooled_background_is_the_union_of_attached_lists():
    lists = {"a": frozenset(f"A{i}" for i in range(12)), "b": frozenset(f"B{i}" for i in range(12)),
             "unattached": frozenset(f"U{i}" for i in range(12))}
    attachments = {"row a": "a", "row b": "b", "row c": None}
    pathways = {"pw": frozenset(f"A{i}" for i in range(6)) | frozenset(f"B{i}" for i in range(6))}
    table, summary = enrichment({"a": {"A0", "B0"}, "b": {"B1"}}, lists, attachments, pathways,
                                {"pw": "pw"})
    pooled = [r for r in table if r.assay_list == "pooled"]
    assert [(r.claimed_in_pathway, r.claimed, r.background_in_pathway, r.background)
            for r in pooled] == [(2, 2, 12, 24)]
    assert [r.assay_list for r in table] == ["pooled"]
    assert set(summary["primary"]) == {"a", "b"}


def test_density_counts_families_and_proteins_per_pathway_and_outcome():
    pathways = {"pw1": frozenset({"PA", "PB"}), "pw2": frozenset({"PA"})}
    claims = [claim("1", "F1", "PA", ["not_stated"]), claim("2", "F2", "PB", ["not_stated"]),
              claim("3", "F1", "PA", ["not_stated"], outcome="O2"),
              claim("4", "F3", "PZ", ["not_stated"])]
    got = {(d.pathway_id, d.outcome_id): (d.families, d.proteins)
           for d in claim_density(claims, pathways)}
    assert got == {("pw1", "O1"): (2, 2), ("pw1", "O2"): (1, 1), ("pw2", "O1"): (1, 1),
                   ("pw2", "O2"): (1, 1)}


def test_reactome_reader_keeps_human_rows(tmp_path):
    path = tmp_path / "UniProt2Reactome.txt"
    path.write_text("P1\tR-HSA-1\turl\tPathway one\tTAS\tHomo sapiens\n"
                    "P2\tR-HSA-1\turl\tPathway one\tIEA\tHomo sapiens\n"
                    "P3\tR-MMU-1\turl\tMouse pathway\tIEA\tMus musculus\n")
    members, names = load_reactome(path)
    assert members == {"R-HSA-1": frozenset({"P1", "P2"})} and names == {"R-HSA-1": "Pathway one"}


def test_attachment_table_must_match_the_dictionary(tmp_path, attachments):
    assert attachments["UKB-PPP discovery"] == "olink_explore_3072"
    assert attachments["SCALLOP CVD-I (Folkersen 2020)"] == "olink_target_96:CVD I"
    bad = tmp_path / "attachments.csv"
    bad.write_text("dictionary_row,platform_string,assay_list,background_level,status,basis\n"
                   "UKB-PPP replication,Olink Explore 3072,olink_explore_3072,assayed,proposed,"
                   "x\n")
    with pytest.raises(PathwayInputError):
        load_attachments(bad, load_lists(ASSAY_LISTS))
