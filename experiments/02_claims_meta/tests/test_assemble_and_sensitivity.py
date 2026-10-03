import datetime

import pytest

from assemble_registry import assemble, window_of
from build_registry import SEED, PublicDate, RegistryClaim, build
from canonical_ids import PHENOTYPE_XREF_KEY, without_phenotype_xrefs
from dataset_relations import load_rows
from link_families import SearchRecord
from sensitivity_analyses import (checks_entering, direction_unverified_included,
                                  h1_unclear_as_independent, overall_scope_only)

HGNC = {f"HGNC:{i}": frozenset({f"P{i}"}) for i in range(1, 6)}
TITLE = "Proteome-wide Mendelian randomization of plasma proteins and {}"


@pytest.fixture(scope="module")
def rows():
    return load_rows()


def day(text, resolution="day"):
    return PublicDate(value=datetime.date.fromisoformat(text), resolution=resolution)


def record(rid, kind, topic, author, date, doi=None, pub=None):
    return SearchRecord(record_id=rid, kind=kind, doi=doi, pmid=None, pmcid=None,
                        published_as_doi=pub, title=TITLE.format(topic),
                        first_author_surname=author, first_public=day(date))


def check(rid, i, protein, outcome="MONDO:1", direction="raises", first_failure=None, **extra):
    base = {"pmid": rid, "claim_index": i, "claim_record_id": f"{rid}:{i:03d}",
            "direction": direction, "claim_scope": "overall",
            "analysis_context_as_written": "not_stated", "subgroup_as_written": "not_stated",
            "relation_ambiguous": False, "dataset_attribution": "whole_study",
            "pqtl_datasets": ["Sun 2018"], "outcome_datasets": ["FinnGen R10"],
            "protein_ids": [protein], "outcome_ids": [outcome],
            "direction_verification_state": "agrees", "span_passes": True,
            "evidence_type": "mr_estimate", "protein_check": "pass", "outcome_check": "pass",
            "enters_registry": first_failure is None, "first_failure": first_failure}
    return {**base, **extra}


RECORDS = [
    record("J1", "journal", "stroke", "Alpha", "2022-01-10", "10.1/j1"),
    record("P1", "preprint", "stroke", "Alpha", "2021-03-01", "10.9/p1", pub="10.1/j1"),
    record("P2", "preprint", "gout", "Beta", "2023-02-02", "10.9/p2"),
    record("J3", "journal", "asthma", "Gamma", "2024-04-04", "10.1/j3"),
    record("P3", "preprint", "asthma", "Gamma", "2023-12-01", "10.9/p3"),
    record("J4", "journal", "sepsis", "Delta", "2026-02-02", "10.1/j4"),
    record("J5", "journal", "eczema", "Eps", "2020-05-05", "10.1/j5"),
    record("P5", "preprint", "eczema", "Eps", "2018-11-11", "10.9/p5", pub="10.1/j5"),
    record("J6", "journal", "migraine", "Zeta", "2021-06-06", "10.1/j6"),
    record("P6", "preprint", "migraine", "Zeta", "2021-01-01", "10.9/p6", pub="10.1/j6"),
]
DECISIONS = {
    "J1": {"decision": "eligible", "flags": []}, "P1": {"decision": "eligible", "flags": []},
    "P2": {"decision": "uncertain", "flags": ["also_tissue_or_csf"]},
    "J3": {"decision": "eligible_count_not_stated", "flags": []},
    "P3": {"decision": "eligible", "flags": []},
    "J4": {"decision": "eligible", "flags": []},
    "J5": {"decision": "eligible", "flags": []}, "P5": {"decision": "eligible", "flags": []},
    "J6": {"decision": "ineligible", "flags": []}, "P6": {"decision": "eligible", "flags": []},
}
STATUS = {"J1": "ok", "P1": "ok", "P2": "extraction_failed", "J3": "ok", "P3": "ok", "J4": "ok",
          "J5": "ok", "P5": "ok", "P6": "ok"}
CHECKS = [check("J1", 0, "HGNC:1"), check("P1", 0, "HGNC:1"), check("P1", 1, "HGNC:2"),
          check("J3", 0, "HGNC:1"), check("P3", 0, "HGNC:3"), check("J4", 0, "HGNC:4"),
          check("J5", 0, "HGNC:5"), check("P6", 0, "HGNC:5"),
          check("J1", 1, "HGNC:2", first_failure="span_not_verified", span_passes=False)]


def test_windows():
    assert [window_of(day(d)) for d in ("2018-12-31", "2019-01-01", "2025-12-31",
                                        "2026-01-01")] == ["outside", "confirmatory",
                                                           "confirmatory", "update"]


def test_registry_records_dating_records_and_windows():
    a = assemble(RECORDS, DECISIONS, STATUS, CHECKS, HGNC, {})
    assert a.family_of["P1"] == "J1" and a.family_of["P3"] == "J3"
    meta = a.meta
    assert set(meta) == {"J1", "P2", "J3", "J4", "J5"}          # J6's journal abstract is ineligible
    assert (meta["J1"].registry_records, meta["J1"].dating_records) == (["J1"], ["P1"])
    assert meta["J1"].first_public == day("2021-03-01") and meta["J1"].window == "confirmatory"
    assert (meta["P2"].registry_records, meta["P2"].eligibility, meta["P2"].also_tissue_or_csf,
            meta["P2"].extraction) == (["P2"], "uncertain", True, "extraction_failed")
    assert (meta["J3"].eligibility, meta["J3"].fuzzy_linked) == ("eligible_count_not_stated", True)
    assert meta["J4"].window == "update" and meta["J5"].window == "outside"
    confirmatory = {(c.family_id, c.protein_id) for c in a.claims["confirmatory"]}
    assert confirmatory == {("J1", "P1"), ("J3", "P1")}
    assert {(c.family_id, c.protein_id) for c in a.dating_claims["confirmatory"]} == {
        ("J1", "P1"), ("J1", "P2"), ("J3", "P3")}
    assert [c.family_id for c in a.claims["update"]] == ["J4"]
    assert [c.family_id for c in a.claims["outside"]] == ["J5"]
    assert a.report["registry"]["left_out_by_reason"] == {"span_not_verified": 1}
    assert a.report["claim_records_of_other_records"] == 1       # P6's record
    assert (meta["J1"].n_registry_claims, meta["J1"].n_pairs) == (1, 1)
    assert set(a.record_dates) == {"J1", "P1", "P2", "J3", "P3", "J4", "J5", "P5"}


def test_dropping_fuzzy_links_splits_the_fuzzy_family_only():
    a = assemble(RECORDS, DECISIONS, STATUS, CHECKS, HGNC, {}, drop_fuzzy_links=True)
    assert a.family_of["P3"] == "P3" and a.family_of["P1"] == "J1"
    assert a.meta["J3"].dating_records == [] and not a.meta["J3"].fuzzy_linked
    assert a.meta["P3"].registry_records == ["P3"]
    assert {(c.family_id, c.protein_id) for c in a.claims["confirmatory"]} == {
        ("J1", "P1"), ("J3", "P1"), ("P3", "P3")}


OTHER_RECORDS = RECORDS + [
    # A repository copy of J1's abstract, and a conference abstract of a study with no article.
    record("C1", "other", "stroke", "Alpha", "2020-07-07", "10.5/figshare.1"),
    record("C2", "other", "psoriasis", "Eta", "2022-08-08", "10.5/abstract.2"),
]
OTHER_DECISIONS = {**DECISIONS, "C1": {"decision": "eligible", "flags": []},
                   "C2": {"decision": "eligible", "flags": []}}
OTHER_STATUS = {**STATUS, "C1": "ok", "C2": "ok"}
OTHER_CHECKS = CHECKS + [check("C1", 0, "HGNC:1"), check("C1", 1, "HGNC:3"),
                         check("C2", 0, "HGNC:2")]


def test_other_document_types_enter_no_primary_result():
    a = assemble(OTHER_RECORDS, OTHER_DECISIONS, OTHER_STATUS, OTHER_CHECKS, HGNC, {})
    base = assemble(RECORDS, DECISIONS, STATUS, CHECKS, HGNC, {})
    assert a.report["records_other_document_type"] == 2 and a.report["records"] == 10
    assert set(a.meta) == set(base.meta) and "C1" not in a.family_of
    assert a.claims == base.claims and a.record_dates == base.record_dates
    assert a.report["claim_records_of_other_records"] == 1 + 3


def test_all_document_types_links_a_copy_to_its_family_and_keeps_an_unlinked_record():
    a = assemble(OTHER_RECORDS, OTHER_DECISIONS, OTHER_STATUS, OTHER_CHECKS, HGNC, {},
                 include_other_types=True)
    assert a.family_of["C1"] == "J1" and a.family_of["C2"] == "C2"
    assert [l.rule for l in a.links if "C1" in (l.a, l.b)] == ["fuzzy_title_author_copy"]
    # The copy adds no registry record, no dating record and no earlier date to its family.
    assert (a.meta["J1"].registry_records, a.meta["J1"].dating_records) == (["J1"], ["P1"])
    assert a.meta["J1"].first_public == day("2021-03-01")
    assert a.meta["C2"].registry_records == ["C2"] and a.meta["C2"].window == "confirmatory"
    confirmatory = {(c.family_id, c.protein_id) for c in a.claims["confirmatory"]}
    assert confirmatory == {("J1", "P1"), ("J3", "P1"), ("C2", "P2")}


def test_copy_matching_two_families_is_linked_to_neither():
    records = [record("J1", "journal", "stroke", "Alpha", "2022-01-10", "10.1/j1"),
               record("J2", "journal", "stroke", "Alpha", "2023-01-10", "10.1/j2"),
               record("C1", "other", "stroke", "Alpha", "2020-07-07", "10.5/c1")]
    decisions = {r.record_id: {"decision": "eligible", "flags": []} for r in records}
    a = assemble(records, decisions, {r.record_id: "ok" for r in records}, [], HGNC, {},
                 include_other_types=True)
    assert a.family_of == {"J1": "J1", "J2": "J2", "C1": "C1"}


def test_shared_name_gives_a_pair_only_under_mondo_first():
    checks = CHECKS + [check("J3", 1, "HGNC:4", outcome="EFO:0005288",
                             outcome_ids=["EFO:0005288", "MONDO:0005061"])]
    primary = assemble(RECORDS, DECISIONS, STATUS, checks, HGNC, {})
    assert ("J3", "P4") not in {(c.family_id, c.protein_id)
                                for c in primary.claims["confirmatory"]}
    assert primary.report["registry"]["pair_ambiguous_by_reason"] == {
        "outcome_multiple_canonical": 1}
    first = assemble(RECORDS, DECISIONS, STATUS, checks, HGNC, {}, mondo_first=True)
    assert [(c.protein_id, c.outcome_id) for c in first.claims["confirmatory"]
            if c.family_id == "J3"] == [("P1", "MONDO:1"), ("P4", "MONDO:0005061")]


def test_phenotype_only_outcome_joins_the_disease_pair_through_the_cross_reference():
    xrefs = {PHENOTYPE_XREF_KEY + "HP:0000822": frozenset({"MONDO:1"})}
    checks = CHECKS + [check("J3", 1, "HGNC:1", outcome="HP:0000822"),
                       check("J3", 2, "HGNC:4", outcome="HP:0009999")]
    primary = assemble(RECORDS, DECISIONS, STATUS, checks, HGNC, xrefs)
    pairs = [(c.protein_id, c.outcome_id) for c in primary.claims["confirmatory"]
             if c.family_id == "J3"]
    assert pairs == [("P1", "MONDO:1"), ("P1", "MONDO:1"), ("P4", "HP:0009999")]
    assert primary.report["registry"]["pair_ambiguous_by_reason"] == {
        "outcome_phenotype_cross_reference_applied": 1}
    plain = assemble(RECORDS, DECISIONS, STATUS, checks, HGNC, without_phenotype_xrefs(xrefs))
    assert [(c.protein_id, c.outcome_id) for c in plain.claims["confirmatory"]
            if c.family_id == "J3"] == [("P1", "MONDO:1"), ("P1", "HP:0000822"),
                                        ("P4", "HP:0009999")]
    assert plain.claims["confirmatory"][-2].outcome_source_ids == ("HP:0000822",)


def test_checks_entering_admits_only_records_failing_the_named_check_alone():
    checks = [
        check("A", 0, "HGNC:1", first_failure="outcome_not_in_span",
              outcome_check="outcome_not_in_span"),
        check("A", 1, "HGNC:1", first_failure="protein_not_in_span",
              protein_check="protein_not_in_span", relation_ambiguous=True),
        check("A", 2, "HGNC:1", first_failure="span_not_verified", span_passes=False,
              outcome_check="outcome_not_in_span"),
        check("A", 3, "HGNC:1", first_failure="relation_ambiguous", relation_ambiguous=True),
        check("A", 4, "HGNC:1", first_failure="protein_unmapped", protein_check="protein_unmapped"),
        check("A", 5, "HGNC:1"),
    ]
    span = checks_entering(checks, ("protein_not_in_span", "outcome_not_in_span"))
    assert [c["enters_registry"] for c in span] == [True, False, False, False, False, True]
    relation = checks_entering(checks, ("relation_ambiguous",))
    assert [c["enters_registry"] for c in relation] == [False, False, False, True, False, True]
    assert checks[0]["enters_registry"] is False


def claim(family, pair=("P1", "O1"), direction="raises", verified=True, scope="overall",
          context="", pqtl=("Sun 2018",), outcome=("FinnGen R10",)):
    return RegistryClaim(
        claim_record_id=f"{family}-{pair}-{context}-{direction}", family_id=family,
        protein_id=pair[0], outcome_id=pair[1], direction=direction,
        direction_verified=verified, claim_scope=scope, context_key=context,
        pqtl_datasets=pqtl, outcome_datasets=outcome, dataset_attribution="whole_study")


def test_overall_scope_only_applies_where_a_family_has_an_overall_record():
    claims = [claim("A"), claim("A", direction="lowers", scope="sensitivity", context="s"),
              claim("B", direction="lowers", scope="subgroup_specific", context="women")]
    kept = overall_scope_only(claims)
    assert [(c.family_id, c.claim_scope) for c in kept] == [("A", "overall"),
                                                           ("B", "subgroup_specific")]


def test_direction_unverified_included_restores_sols_direction(rows):
    claims = [claim("A", verified=False), claim("B", direction="not_stated", verified=False)]
    reg = build(direction_unverified_included(claims), rows)
    assert reg[("P1", "O1")]["A"].direction == "raises"
    assert reg[("P1", "O1")]["B"].direction == "unresolved"


def test_unclear_edges_counted_as_independent(rows):
    claims = [claim("A", pair=("P1", "O1")),
              claim("B", pair=("P1", "O1"), pqtl=("not_stated",), outcome=("not_stated",)),
              claim("A", pair=("P2", "O1")),
              claim("B", pair=("P2", "O1"), direction="lowers", pqtl=("not_stated",),
                    outcome=("not_stated",)),
              claim("A", pair=("P3", "O1")), claim("B", pair=("P3", "O1"))]
    out = h1_unclear_as_independent(build(claims, rows), n_boot=200, seed=SEED)
    assert (out["h1_pairs"], out["h1_pairs_agreeing"]) == (2, 1)
    assert out["h1_pair_concordance"] == pytest.approx(0.5)
    assert out["h1_edge_concordance"] == pytest.approx(0.5)
