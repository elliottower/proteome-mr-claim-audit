import copy
import json

import pytest

import funnel as fn
import gate_audit as ga
import keyword_prefilter as kp
import negative_control_specificity as ncs
import repeat_run_agreement as rra
import select_eligible as se


def record(rid, kind="journal"):
    return {"record_id": rid, "kind": kind}


def mark(rid, genetic=True, protein=True):
    return {"record_id": rid, "has_genetic_term": genetic, "has_protein_term": protein,
            "marked": not (genetic and protein)}


def decision(rid, value, reasons=(), flags=()):
    return {"pmid": rid, "decision": value, "reasons": list(reasons), "flags": list(flags)}


def extraction_row(rid, n_claims, attempts=1):
    if n_claims is None:
        return {"pmid": rid, "status": "extraction_failed", "attempts": 2, "output": None}
    return {"pmid": rid, "status": "ok", "attempts": attempts,
            "output": {"claims": [{}] * n_claims}}


@pytest.fixture()
def stages():
    runs = [
        fn.ScreeningRun(name="search", chase_round=None, counts={"screening_records": 4},
                        records=[record("A"), record("B"), record("C", "preprint"),
                                 record("D", "other")],
                        marks=[mark("A"), mark("B", protein=False), mark("C"), mark("D")],
                        gated=False),
        fn.ScreeningRun(name="chase_round_1", chase_round=1, counts={"round": 1, "new_works": 2},
                        records=[record("E"), record("F")],
                        marks=[mark("E"), mark("F", genetic=False, protein=False)], gated=True,
                        gate_sampled=["F"])]
    return {
        "runs": runs,
        "decisions": [decision("A", "eligible"),
                      decision("B", "ineligible", ["no_protein_outcome_result"]),
                      decision("C", "uncertain", flags=["uncertain_x", "also_tissue_or_csf"]),
                      decision("D", "eligible_count_not_stated"),
                      decision("E", "extraction_failed"), decision("F", "ineligible")],
        "extraction": [extraction_row("A", 2), extraction_row("C", 0, attempts=2),
                       extraction_row("D", None)],
        "spans": [{"pmid": "A", "claim_index": 0, "passes": True},
                  {"pmid": "A", "claim_index": 1, "passes": False}],
        "checks": [{"claim_record_id": "A:000", "enters_registry": True, "first_failure": None,
                    "direction_verification_state": "agrees"},
                   {"claim_record_id": "A:001", "enters_registry": False,
                    "first_failure": "span_not_verified",
                    "direction_verification_state": "direction_unverified"}],
        "links": [{"a": "A", "b": "X", "rule": "published_as"}],
        "meta": {"A": {"window": "confirmatory", "extraction": "ok", "registry_records": ["A"]},
                 "C": {"window": "update", "extraction": "ok", "registry_records": ["C"]}},
        "assembly_report": {"records": 5},
    }


def run_funnel(s):
    return fn.funnel(s["runs"], s["decisions"], s["extraction"], s["spans"], s["checks"],
                     s["links"], s["meta"], s["assembly_report"])


def test_funnel_counts_every_stage(stages):
    out = run_funnel(stages)
    assert out["search"] == {"search": {"screening_records": 4}}
    assert out["citation_chasing"] == {"round_1": {"round": 1, "new_works": 2}}
    assert out["screening"] == {"records": 6, "records_from_citation_chasing": 2,
                                "by_document_class": {"journal": 4, "other": 1, "preprint": 1},
                                "no_abstract": 0, "with_an_abstract": 6}
    assert out["no_abstract"]["search"]["records"] == 0
    assert out["prefilter"]["search"] == {
        "records": 4, "no_abstract_records_not_screened": 0, "marked": 1,
        "no_genetic_term": 0, "no_protein_term": 1,
        "marked_records_sampled_by_the_gate_audit": 0,
        "marked_records_not_screened": 0, "sent_to_screening": 4}
    assert out["prefilter"]["chase_round_1"] == {
        "records": 2, "no_abstract_records_not_screened": 0, "marked": 1,
        "no_genetic_term": 1, "no_protein_term": 1,
        "marked_records_sampled_by_the_gate_audit": 1,
        "marked_records_not_screened": 0, "sent_to_screening": 2}
    assert out["eligibility"] == {
        "records_sent_to_screening": 6,
        "decisions": {"eligible": 1, "eligible_count_not_stated": 1, "extraction_failed": 1,
                      "ineligible": 2, "uncertain": 1},
        "to_extraction": 3, "eligibility_uncertain": 1, "also_tissue_or_csf": 1,
        "ineligible_by_reason": {"no_protein_outcome_result": 1}}
    assert out["extraction"] == {"records": 3, "ok": 2, "extraction_failed": 1,
                                 "needed_retry": 1, "claim_records": 2}
    assert out["quotation_check"] == {"spans": 2, "pass": 1, "fail": 1}
    assert out["verification"] == {
        "claim_records": 2, "enters_registry": 1,
        "left_out_by_first_failure": {"span_not_verified": 1},
        "direction_verification_state": {"agrees": 1, "direction_unverified": 1}}
    assert out["families"] == {
        "links_by_rule": {"published_as": 1}, "eligible_families": 2,
        "eligible_families_by_window": {"confirmatory": 1, "update": 1},
        "eligible_families_extraction_failed": 0, "eligible_no_named_claims": 1,
        "eligible_no_named_claims_families": ["C"]}
    assert out["registry_assembly"] == {"records": 5}
    audit = out["prefiltered_citation_chasing_gate_audit"]
    assert list(audit) == ["chase_round_1"]
    assert (audit["chase_round_1"]["marked_records"], audit["chase_round_1"]["sampled"],
            audit["chase_round_1"]["judged_eligible_or_uncertain"],
            audit["chase_round_1"]["stopping_reason"]) == (1, 1, 0, "every_marked_record_sampled")
    assert out["gate_audit_rounds_cap_reached_without_satisfying_tolerance"] == []


def broken(stages, change):
    s = copy.deepcopy(stages)
    change(s)
    return s


@pytest.mark.parametrize("stage, change", [
    ("eligibility decisions", lambda s: s["decisions"].pop(0)),
    ("eligibility decisions", lambda s: s["decisions"].append(decision("G", "ineligible"))),
    ("gate audit of chase_round_1", lambda s: s["decisions"].pop()),
    ("gate audit of chase_round_1", lambda s: setattr(s["runs"][1], "gate_sampled", [])),
    ("gate sample of chase_round_1", lambda s: setattr(s["runs"][1], "gate_sampled",
                                                       ["E", "F"])),
    ("extraction rows", lambda s: s["extraction"].pop(0)),
    ("extraction rows", lambda s: s["extraction"].append(extraction_row("B", 1))),
    ("span checks", lambda s: s["spans"].pop()),
    ("claim checks", lambda s: s["checks"].append(dict(s["checks"][0]))),
    ("screening records", lambda s: s["runs"][1].records.append(record("A"))),
    ("prefilter marks of search", lambda s: s["runs"][0].marks.pop()),
])
def test_funnel_raises_when_two_stages_disagree(stages, stage, change):
    with pytest.raises(fn.FunnelError, match=stage):
        run_funnel(broken(stages, change))


def test_marked_record_of_the_search_is_still_sent_to_screening(stages):
    assert run_funnel(stages)["prefilter"]["search"]["sent_to_screening"] == 4
    gated_search = broken(stages, lambda s: setattr(s["runs"][0], "gated", True))
    with pytest.raises(fn.FunnelError, match="gate audit of search"):
        run_funnel(gated_search)


def test_sampled_record_judged_eligible_goes_to_extraction_like_any_other(stages):
    positive = broken(stages, lambda s: s["decisions"].__setitem__(
        5, decision("F", "eligible")))
    with pytest.raises(fn.FunnelError, match="extraction rows: missing \\['F'\\]"):
        run_funnel(positive)
    positive["extraction"].append(extraction_row("F", 0))
    out = run_funnel(positive)
    assert out["eligibility"]["to_extraction"] == 4
    audit = out["prefiltered_citation_chasing_gate_audit"]["chase_round_1"]
    assert audit["positive_record_ids"] == ["F"] and audit["share"] == pytest.approx(1.0)


def test_funnel_lists_the_rounds_whose_audit_stopped_at_the_cap_above_the_tolerance():
    marked = [f"R{i:05d}" for i in range(10000)]
    order = ga.draw_order(marked)
    at_cap = {i: "eligible" if k % 200 == 0 else "ineligible"
              for k, i in enumerate(order[:3000])}
    clean = {i: "ineligible" for i in order[:600]}
    audits = {"chase_round_2": ga.audit(marked, at_cap), "chase_round_1": ga.audit(marked, clean),
              "chase_round_3": ga.audit(marked, at_cap)}
    assert audits["chase_round_2"]["stopping_reason"] == "maximum_sample_reached"
    assert fn.rounds_at_cap(audits) == ["chase_round_2", "chase_round_3"]


def test_gate_keeps_unmarked_records_and_draws_the_first_audit_batch():
    records = [{"pmid": f"{i:04d}", "title": "t", "abstract": ""} for i in range(2000)]
    marks = [kp.Mark(record_id=r["pmid"], has_genetic_term=i % 5 == 0, has_protein_term=True,
                     marked=i % 5 != 0) for i, r in enumerate(records)]
    sent, out, batch = kp.gate(records, marks)
    assert [r["pmid"] for r in sent] == [f"{i:04d}" for i in range(0, 2000, 5)]
    assert len(out) == 1600 and not {r["pmid"] for r in out} & {r["pmid"] for r in sent}
    order = ga.draw_order([r["pmid"] for r in out])
    assert len(batch) == ga.BATCH == 600
    assert {r["pmid"] for r in batch} == set(order[:600])
    assert [r["pmid"] for r in batch] == sorted(r["pmid"] for r in batch)
    assert [r["pmid"] for r in kp.gate(records, marks, seed=1)[2]] != [r["pmid"] for r in batch]
    few = kp.gate(records[:10], marks[:10])
    assert len(few[1]) == 8 and [r["pmid"] for r in few[2]] == [r["pmid"] for r in few[1]]


def test_select_eligible_keeps_the_three_decisions_that_go_to_extraction():
    decisions = [decision("3", "uncertain"), decision("1", "eligible"),
                 decision("2", "ineligible"), decision("4", "eligible_count_not_stated"),
                 decision("5", "extraction_failed")]
    abstracts = [{"pmid": str(i), "title": f"t{i}", "abstract": ""} for i in range(1, 6)]
    records = [{"record_id": str(i), "doi": f"10.1/{i}"} for i in range(1, 6)]
    kept_abstracts, kept_records = se.select(decisions, abstracts, records)
    assert [r["pmid"] for r in kept_abstracts] == ["1", "3", "4"]
    assert [r["doi"] for r in kept_records] == ["10.1/1", "10.1/3", "10.1/4"]
    with pytest.raises(se.SelectError, match="'4'"):
        se.select(decisions, abstracts, records[:3])
    with pytest.raises(se.SelectError, match="two eligibility decisions"):
        se.select(decisions + [decision("1", "ineligible")], abstracts, records)


def claim(protein, outcome, direction="raises", context="not_stated", subgroup="not_stated",
          pqtl=("UKB-PPP",), span="s"):
    return {"protein_as_written": protein, "outcome_as_written": outcome,
            "direction": direction, "evidence_type": "mr_estimate", "claim_scope": "overall",
            "analysis_context_as_written": context, "subgroup_as_written": subgroup,
            "pqtl_datasets": list(pqtl), "outcome_datasets": ["FinnGen"],
            "dataset_attribution": "whole_study", "platform": ["Olink"],
            "ancestry": "European", "relation_ambiguous": False, "evidence_span": span}


def test_records_pair_on_the_full_key_then_on_protein_and_outcome():
    run1 = [claim("IL-6R", "coronary artery disease"),
            claim("IL6R", "coronary artery disease", context="in women"),
            claim("PCSK9", "stroke"), claim("PCSK9", "stroke"),
            claim("APOB", "asthma")]
    run2 = [claim("il6r", "Coronary Artery Disease", context="women only"),
            claim("IL6R", "coronary artery disease"),
            claim("PCSK9", "stroke"),
            claim("LPA", "asthma")]
    pairing = rra.pair_records(run1, run2)
    # IL-6R/not_stated pairs with run 2's second record on the full key; the "in women" record
    # pairs with "women only" on protein and outcome alone; the second PCSK9 record and APOB
    # have no partner, and neither has LPA.
    assert pairing.pairs == [(0, 1, 1), (1, 0, 2), (2, 2, 1)]
    assert pairing.unpaired_run1 == [3, 4] and pairing.unpaired_run2 == [3]


def test_field_agreement_is_counted_over_paired_records_only():
    rows1 = {"1": {"pmid": "1", "status": "ok", "revision": "r", "output": {"claims": [
        claim("IL6R", "CAD", "raises", pqtl=("UKB-PPP", "deCODE"), span="a  b"),
        claim("PCSK9", "stroke", "lowers"), claim("APOB", "asthma")]}},
        "2": {"pmid": "2", "status": "extraction_failed", "revision": "r", "output": None},
        "3": {"pmid": "3", "status": "ok", "revision": "r", "output": {"claims": []}}}
    rows2 = {"1": {"pmid": "1", "status": "ok", "revision": "r", "output": {"claims": [
        claim("PCSK9", "stroke", "raises"),
        claim("IL6R", "CAD", "raises", pqtl=("deCODE", "UKB-PPP"), span="a b")]}},
        "2": {"pmid": "2", "status": "ok", "revision": "r", "output": {"claims": []}},
        "3": {"pmid": "3", "status": "ok", "revision": "r", "output": {"claims": []}}}
    out = rra.agreement(rows1, rows2, ["1", "2", "3"])
    assert out["sampled_abstracts"] == 3 and out["abstracts_compared"] == 2
    assert out["abstracts_extraction_failed_in_run1"] == 1
    assert out["abstracts_extraction_failed_in_run2"] == 0
    assert out["abstracts_with_equal_record_count"] == 1
    assert (out["run1_records"], out["run2_records"], out["paired_records"]) == (3, 2, 2)
    assert out["run1_share_paired"] == pytest.approx(2 / 3)
    assert out["run2_share_paired"] == pytest.approx(1.0)
    fields = out["field_agreement_among_paired"]
    assert fields["direction"] == {"agree": 1, "share": pytest.approx(0.5)}
    assert fields["pqtl_datasets"]["agree"] == 2 and fields["evidence_span"]["agree"] == 2
    assert fields["protein_as_written"]["agree"] == 2


def test_agreement_refuses_missing_records_and_mixed_revisions():
    row = {"pmid": "1", "status": "ok", "revision": "r", "output": {"claims": []}}
    with pytest.raises(rra.AgreementError, match="missing"):
        rra.agreement({"1": row}, {}, ["1"])
    with pytest.raises(rra.AgreementError, match="revisions"):
        rra.agreement({"1": row}, {"1": {**row, "revision": "other"}}, ["1"])


def controls():
    return [{"pmid": f"{s}{i}", "stratum": s, "title": "t"} for s in ("mr", "review")
            for i in range(5)]


def test_specificity_is_the_share_judged_not_eligible_per_stratum():
    decisions = [decision(c["pmid"], "ineligible", ["excluded_review"]) for c in controls()]
    decisions[0] = decision("mr0", "eligible")
    decisions[1] = decision("mr1", "uncertain", flags=["uncertain_x"])
    decisions[2] = decision("mr2", "extraction_failed")
    out = ncs.specificity(controls(), decisions)
    mr = out["per_stratum"]["mr"]
    assert (mr["records"], mr["extraction_failed"], mr["judged"], mr["not_eligible"]) == (
        5, 1, 4, 2)
    assert mr["specificity"] == pytest.approx(0.5)
    assert [j["pmid"] for j in mr["judged_eligible"]] == ["mr0", "mr1"]
    assert out["per_stratum"]["review"]["specificity"] == pytest.approx(1.0)
    assert out["per_stratum"]["review"]["ineligibility_reasons"] == {"excluded_review": 5}
    assert out["overall"]["judged"] == 9 and out["overall"]["not_eligible"] == 7
    assert out["overall"]["specificity"] == pytest.approx(7 / 9)
    low, high = out["overall"]["wilson_descriptive"]
    assert low < 7 / 9 < high


def test_specificity_refuses_decisions_that_do_not_cover_the_control_set():
    decisions = [decision(c["pmid"], "ineligible") for c in controls()]
    with pytest.raises(ncs.ControlError):
        ncs.specificity(controls(), decisions[:-1])
    with pytest.raises(ncs.ControlError):
        ncs.specificity(controls(), decisions + [decision("other", "ineligible")])
    with pytest.raises(ncs.ControlError):
        ncs.specificity(controls(), decisions + [decisions[0]])


def test_funnel_reads_its_stage_files(tmp_path, stages):
    folder = tmp_path / "search"
    folder.mkdir()
    run = stages["runs"][0]
    (folder / "funnel.json").write_text(json.dumps(run.counts))
    (folder / "screening_records.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in run.records))
    (folder / "prefilter_marks.jsonl").write_text(
        "".join(json.dumps(m) + "\n" for m in run.marks))
    (folder / "prefilter_counts.json").write_text(json.dumps({"gated": False}))
    loaded = fn.load_run(folder)
    assert loaded == run.model_copy(update={"name": "search"})
    chase = tmp_path / "chase_round_2"
    chase.mkdir()
    for name in ("screening_records.jsonl", "prefilter_marks.jsonl"):
        (chase / name).write_text("")
    (chase / "chase_counts.json").write_text(json.dumps({"round": 2}))
    (chase / "prefilter_counts.json").write_text(json.dumps({"gated": True}))
    (chase / "gate_sample_batch_02.jsonl").write_text(json.dumps({"pmid": "Z"}) + "\n")
    (chase / "gate_sample_batch_01.jsonl").write_text(
        json.dumps({"pmid": "X"}) + "\n" + json.dumps({"pmid": "Y"}) + "\n")
    loaded = fn.load_run(chase)
    assert (loaded.chase_round, loaded.gated, loaded.gate_sampled) == (2, True, ["X", "Y", "Z"])
