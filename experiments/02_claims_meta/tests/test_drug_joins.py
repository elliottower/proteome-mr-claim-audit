import pytest

from drug_joins import (OUTSIDE, RULES, STOP_LABELS, STOP_REASON_CLASS, DrugClaim, DrugIndex,
                        Indication, Lookup, Mechanism, Rule, Trial, alignment, drug_direction,
                        join_claim, join_pair, parse_tokens, tables, token_class)

OUTCOME = "MONDO:1"
COLLISION = {"EFO:1": frozenset({"MONDO:1"}), "MONDO:1": frozenset({"MONDO:1"}),
             "EFO:9": frozenset({"MONDO:1", "MONDO:9"})}
PARENTS = {"MONDO:1": frozenset({"MONDO:100"}), "MONDO:11": frozenset({"MONDO:1"})}


def mech(parent, action="INHIBITOR", accession="P1", level="single_protein", molregno=None):
    return Mechanism(mec_id=parent, molregno=molregno or parent, parent_molregno=parent,
                     accession=accession, tid=1,
                     target_type="SINGLE PROTEIN" if level == "single_protein"
                     else "PROTEIN COMPLEX",
                     level=level, action_type=action, direct_interaction=1,
                     molecular_mechanism=1, homologue=0)


def ind(parent, phase, indication=OUTCOME):
    return Indication(parent_molregno=parent, indication_id=indication, max_phase=phase)


def trial(rid, parents, status, labels=(), diseases=(OUTCOME,), n_drugs=None, flags=(),
          source="ClinicalTrials.gov"):
    return Trial(report_id=rid, n_drugs=len(parents) if n_drugs is None else n_drugs,
                 parent_molregnos=tuple(parents), disease_ids=tuple(diseases),
                 status=status, stop_labels=tuple(labels), quality_controls=tuple(flags),
                 source=source, report_type="INDICATION")


def look(mechanisms=(), indications=(), trials=(), resource=(OUTCOME,)):
    index = DrugIndex(mechanisms=list(mechanisms), indications=list(indications),
                      trials=list(trials), resource_disease_ids=list(resource), provenance={})
    return Lookup(index, COLLISION, PARENTS)


def pair(lk, level="primary", protein="P1", outcome=OUTCOME):
    return join_pair(lk, protein, outcome, level)


def claim(direction="raises", verified=True, wording="causal", rid="c1"):
    return DrugClaim(claim_record_id=rid, family_id="F", protein_id="P1", outcome_id=OUTCOME,
                     direction=direction, direction_verified=verified, wording_class=wording)


@pytest.mark.parametrize("token,expected", [
    ("INVERSE AGONIST", "BLOCKING"),
    ("NEGATIVE ALLOSTERIC MODULATOR", "BLOCKING"),
    ("POSITIVE ALLOSTERIC MODULATOR", "ACTIVATING"),
    ("PARTIAL AGONIST", "ACTIVATING"),
    ("INHIBITOR", "BLOCKING"),
    ("ANTAGONIST", "BLOCKING"),
    ("BLOCKER", "BLOCKING"),
    ("DEGRADER", "BLOCKING"),
    ("DISRUPTING AGENT", "BLOCKING"),
    ("ANTISENSE INHIBITOR", "BLOCKING"),
    ("AGONIST", "ACTIVATING"),
    ("ACTIVATOR", "ACTIVATING"),
    ("OPENER", "ACTIVATING"),
    ("STABILISER", "ACTIVATING"),
    ("STABILIZER", "ACTIVATING"),
    ("RELEASING AGENT", "ACTIVATING"),
    ("POSITIVE MODULATOR", "AMBIGUOUS"),
    ("NEGATIVE MODULATOR", "AMBIGUOUS"),
    ("MODULATOR", "AMBIGUOUS"),
    ("BINDING AGENT", "AMBIGUOUS"),
    ("CROSS-LINKING AGENT", "AMBIGUOUS"),
    ("OTHER", "AMBIGUOUS"),
])
def test_token_class_tiers(token, expected):
    assert token_class(token) == expected


def test_parse_tokens_normalizes_and_deduplicates():
    assert parse_tokens([" inhibitor ", "Inhibitor", None, "", "  ", "releasing   agent"]) == {
        "INHIBITOR", "RELEASING AGENT"}


@pytest.mark.parametrize("actions,expected", [
    (["INHIBITOR"], "decrease"),
    (["INHIBITOR", "BINDING AGENT"], "decrease"),
    (["INHIBITOR", "ANTAGONIST", "INVERSE AGONIST"], "decrease"),
    (["AGONIST", "partial agonist"], "increase"),
    (["INHIBITOR", "AGONIST"], "ambiguous"),
    (["BINDING AGENT"], "ambiguous"),
    (["POSITIVE MODULATOR"], "ambiguous"),
    ([], "ambiguous"),
    ([None], "ambiguous"),
])
def test_drug_direction(actions, expected):
    assert drug_direction(actions) == expected


def test_stop_reason_table_is_the_registered_13():
    assert sorted(STOP_LABELS) == [
        "Another_Study", "Business_Administrative", "Covid19", "Insufficient_Enrollment",
        "Invalid_Reason", "Logistics_Resources", "Negative", "No_Context", "Regulatory",
        "Safety_Sideeffects", "Study_Design", "Study_Staff_Moved", "Uncategorised"]
    assert sorted(l for l, c in STOP_REASON_CLASS.items()
                  if c == "stopped_negative_or_safety") == ["Negative", "Safety_Sideeffects"]
    assert set(STOP_REASON_CLASS.values()) == {"stopped_negative_or_safety", "stopped_other"}


STATUS_CASES = [
    ("approved_beats_active_and_stopped",
     [ind(1, 4.0)], [trial("t1", [1], "RECRUITING"), trial("t2", [1], "TERMINATED", ["Negative"])],
     "approved"),
    ("active_beats_stopped_and_phase",
     [ind(1, 3.0)], [trial("t1", [1], "ENROLLING_BY_INVITATION"),
                     trial("t2", [1], "TERMINATED", ["Safety_Sideeffects"])],
     "in_clinical_trials"),
    ("not_yet_recruiting_is_active", [], [trial("t1", [1], "NOT_YET_RECRUITING")],
     "in_clinical_trials"),
    ("active_not_recruiting_is_active", [], [trial("t1", [1], "ACTIVE_NOT_RECRUITING")],
     "in_clinical_trials"),
    ("negative_beats_other_label",
     [], [trial("t1", [1], "WITHDRAWN", ["Business_Administrative"]),
          trial("t2", [1], "TERMINATED", ["Study_Design", "Negative"])],
     "stopped_negative_or_safety"),
    ("safety_label", [], [trial("t1", [1], "TERMINATED", ["Safety_Sideeffects"])],
     "stopped_negative_or_safety"),
    ("other_label", [ind(1, 3.0)], [trial("t1", [1], "TERMINATED", ["Covid19"])],
     "stopped_other"),
    ("suspended_negative_is_not_stopped",
     [ind(1, 2.0)], [trial("t1", [1], "SUSPENDED", ["Negative"])], "suspended"),
    ("stopped_other_beats_suspended_negative",
     [], [trial("t1", [1], "SUSPENDED", ["Negative"]),
          trial("t2", [1], "TERMINATED", ["Regulatory"])], "stopped_other"),
    ("phase_2_with_completed_trial",
     [ind(1, 2.0)], [trial("t1", [1], "COMPLETED")], "completed_no_later_record"),
    ("phase_1", [ind(1, 1.0)], [], "completed_no_later_record"),
    ("phase_3", [ind(1, 3.0)], [], "completed_no_later_record"),
    ("terminated_without_label_then_phase",
     [ind(1, 1.0)], [trial("t1", [1], "TERMINATED")], "completed_no_later_record"),
    ("no_record", [], [], "no_matching_trial_or_indication_record"),
    ("records_at_another_indication_only",
     [ind(1, 4.0, "MONDO:77")], [trial("t1", [1], "RECRUITING", diseases=["MONDO:77"])],
     "no_matching_trial_or_indication_record"),
    ("early_phase_1_only", [ind(1, 0.5)], [], OUTSIDE),
    ("phase_unknown_only", [ind(1, -1.0)], [], OUTSIDE),
    ("phase_missing_only", [ind(1, None)], [], OUTSIDE),
    ("completed_trial_without_chembl_indication", [], [trial("t1", [1], "COMPLETED")], OUTSIDE),
    ("non_trial_report_without_chembl_indication", [], [trial("t1", [1], None)], OUTSIDE),
]


@pytest.mark.parametrize("name,indications,trials,expected", STATUS_CASES,
                         ids=[c[0] for c in STATUS_CASES])
def test_highest_status_first_that_applies(name, indications, trials, expected):
    rec = pair(look([mech(1)], indications, trials, resource=[OUTCOME, "MONDO:77"]))
    assert rec.highest_status == expected
    assert bool(rec.outside_reasons) == (expected == OUTSIDE)


def test_protein_without_drug_has_no_matching_record():
    rec = pair(look())
    assert rec.highest_status == "no_matching_trial_or_indication_record"
    assert rec.drugs == []


def test_stopped_events_exclude_suspended_and_unlabelled_trials():
    rec = pair(look([mech(1)], [ind(1, 4.0)], [
        trial("t1", [1], "TERMINATED", ["Negative", "Study_Design"]),
        trial("t2", [1], "SUSPENDED", ["Safety_Sideeffects"]),
        trial("t3", [1], "TERMINATED"),
        trial("t4", [1], "WITHDRAWN", ["Covid19"]),
        trial("t5", [1], "TERMINATED", ["Negative"], diseases=["MONDO:77"])]))
    assert rec.highest_status == "approved"
    assert [e.report_id for e in rec.stopped_trial_events] == ["t1", "t4"]
    assert rec.stopped_trial_events[0].stop_labels == ["Negative", "Study_Design"]
    assert rec.stopped_trial_events[0].stop_classes == ["stopped_negative_or_safety",
                                                        "stopped_other"]
    assert [e.report_id for e in rec.suspended_trials] == ["t2"]
    assert rec.suspended_trials[0].stop_labels == ["Safety_Sideeffects"]
    assert rec.matching_trial_reports == 4


def test_trial_with_two_drugs_of_the_protein_is_one_event():
    rec = pair(look([mech(1), mech(2)], [], [trial("t1", [1, 2], "TERMINATED", ["Negative"])]))
    assert len(rec.stopped_trial_events) == 1
    assert rec.stopped_trial_events[0].parent_molregnos == [1, 2]


def test_trial_of_a_drug_not_acting_on_the_protein_is_not_used():
    rec = pair(look([mech(1), mech(2, accession="P2")], [ind(2, 4.0)],
                    [trial("t1", [2], "TERMINATED", ["Negative"])]))
    assert rec.highest_status == "no_matching_trial_or_indication_record"
    assert rec.stopped_trial_events == []


def test_unregistered_stop_label_raises():
    with pytest.raises(ValueError, match="Lack_Of_Efficacy"):
        look([mech(1)], [], [trial("t1", [1], "TERMINATED", ["Lack_Of_Efficacy"])])


def test_indication_matches_through_the_collision_table():
    rec = pair(look([mech(1)], [ind(1, 4.0, "EFO:1")]))
    assert rec.highest_status == "approved"


def test_identifier_with_two_canonical_identifiers_matches_nothing_and_is_counted():
    rec = pair(look([mech(1)], [ind(1, 4.0, "EFO:9")],
                    [trial("t1", [1], "RECRUITING", diseases=["EFO:9"])]))
    assert rec.highest_status == "no_matching_trial_or_indication_record"
    assert rec.ambiguous_identifier_records == 2
    assert rec.target_drugged_elsewhere is False


def test_indication_without_identifier_is_counted_and_matches_nothing():
    rec = pair(look([mech(1)], [ind(1, 4.0, None)]))
    assert rec.highest_status == "no_matching_trial_or_indication_record"
    assert rec.unmapped_indication_rows == 1
    assert rec.target_drugged_elsewhere is False


def test_related_indication_never_sets_a_class():
    rec = pair(look([mech(1)], [ind(1, 4.0, "MONDO:100"), ind(1, 3.0, "MONDO:11")],
                    [trial("t1", [1], "TERMINATED", ["Negative"], diseases=["MONDO:100"]),
                     trial("t2", [1], "RECRUITING", diseases=["MONDO:11"])]))
    assert rec.highest_status == "no_matching_trial_or_indication_record"
    assert rec.stopped_trial_events == []
    assert sorted((r.source, r.relation, r.indication_id) for r in rec.related_indications) == [
        ("chembl_indication", "indication_broader", "MONDO:100"),
        ("chembl_indication", "indication_narrower", "MONDO:11"),
        ("clinical_report", "indication_broader", "MONDO:100"),
        ("clinical_report", "indication_narrower", "MONDO:11")]
    assert rec.target_drugged_elsewhere is True


def test_two_steps_away_is_not_related():
    lk = look([mech(1)], [ind(1, 4.0, "MONDO:100")])
    rec = join_pair(lk, "P1", "MONDO:11", "primary")
    assert rec.related_indications == []


def test_target_drugged_elsewhere_needs_phase_4_at_another_indication():
    assert pair(look([mech(1)], [ind(1, 3.0, "MONDO:77")])).target_drugged_elsewhere is False
    assert pair(look([mech(1)], [ind(1, 4.0, "MONDO:77")])).target_drugged_elsewhere is True
    assert pair(look([mech(1)], [ind(1, 4.0)])).target_drugged_elsewhere is False


def test_component_level_drugs_enter_only_the_sensitivity_level():
    lk = look([mech(1, level="component_level_mapping")], [ind(1, 4.0)],
              [trial("t1", [1], "TERMINATED", ["Negative"])])
    primary, sens = pair(lk), pair(lk, "with_component_level")
    assert primary.highest_status == "no_matching_trial_or_indication_record"
    assert primary.drugs == [] and primary.stopped_trial_events == []
    assert sens.highest_status == "approved"
    assert [d.levels for d in sens.drugs] == [["component_level_mapping"]]
    assert len(sens.stopped_trial_events) == 1


def test_report_that_is_not_a_trial_is_a_record_only_outside_the_trials_only_rule():
    lk = look([mech(1)], [], [trial("label", [1], None)])
    assert pair(lk).highest_status == OUTSIDE
    assert pair(lk).outside_reasons == ["clinical_report_status:None"]
    only = pair(lk, "clinical_trial_reports_only")
    assert only.highest_status == "no_matching_trial_or_indication_record"
    assert only.matching_trial_reports == 0 and only.drugs[0].has_matching_record is False


def test_flagged_report_is_read_only_under_the_flagged_included_rule():
    lk = look([mech(1)], [], [trial("t1", [1], "TERMINATED", ["Negative"],
                                    flags=["UNVALIDATED_INDICATION"])])
    primary = pair(lk)
    assert primary.highest_status == "no_matching_trial_or_indication_record"
    assert primary.stopped_trial_events == [] and primary.matching_trial_reports == 0
    assert primary.drugs[0].has_matching_record is False
    included = pair(lk, "quality_flagged_reports_included")
    assert included.highest_status == "stopped_negative_or_safety"
    assert included.stopped_trial_events[0].quality_controls == ["UNVALIDATED_INDICATION"]
    assert included.flagged_matching_reports_not_read == 0


def test_flagged_reports_left_out_are_counted_by_flag_and_source_when_they_match():
    lk = look([mech(1)], [], [
        trial("t1", [1], "RECRUITING"),
        trial("t2", [1], "TERMINATED", ["Negative"], flags=["A_FLAG", "B_FLAG"]),
        trial("t3", [1], None, flags=["A_FLAG"], source="EMA"),
        trial("t4", [1], "TERMINATED", ["Negative"], flags=["A_FLAG"], diseases=["MONDO:77"]),
        trial("t5", [1], "RECRUITING", flags=["B_FLAG"], diseases=["MONDO:100"])],
        resource=[OUTCOME, "MONDO:77"])
    rec = pair(lk)
    assert rec.highest_status == "in_clinical_trials"
    assert rec.flagged_matching_reports_not_read == 2
    assert rec.flagged_matching_reports_by_flag == {"A_FLAG": 2, "B_FLAG": 1}
    assert rec.flagged_matching_reports_by_source == {"ClinicalTrials.gov": 1, "EMA": 1}
    assert rec.related_indications == []
    included = pair(lk, "quality_flagged_reports_included")
    assert included.matching_trial_reports == 3
    assert [r.report_id for r in included.related_indications] == ["t5"]


def test_flagged_non_trial_report_under_the_trials_only_rule_is_not_counted_as_left_out():
    lk = look([mech(1)], [], [trial("t1", [1], None, flags=["A_FLAG"], source="EMA")])
    assert pair(lk).flagged_matching_reports_not_read == 1
    assert pair(lk, "clinical_trial_reports_only").flagged_matching_reports_not_read == 0


def test_matching_reports_are_listed_by_source_and_non_trial_reports_set_no_trial_class():
    lk = look([mech(1)], [], [trial("label", [1], None, source="DailyMed"),
                              trial("ema", [1], None, source="EMA"),
                              trial("t1", [1], "COMPLETED")])
    rec = pair(lk)
    assert rec.matching_reports_by_source == {"ClinicalTrials.gov": 1, "DailyMed": 1, "EMA": 1}
    assert rec.matching_non_trial_reports == 2 and rec.matching_trial_reports == 3
    assert rec.highest_status == OUTSIDE
    assert rec.stopped_trial_events == [] and rec.suspended_trials == []


def test_tables_count_the_pairs_each_sensitivity_rule_reclassifies():
    lk = look([mech(1)], [], [trial("t1", [1], "TERMINATED", ["Negative"], flags=["A_FLAG"]),
                              trial("t2", [1], None, source="EMA")])
    result, _, _ = tables([claim()], lk)
    assert result["primary"]["pairs_by_highest_status"][OUTSIDE] == 1
    assert result["primary"]["pairs_whose_highest_status_differs_from_primary"] == 0
    assert result["primary"]["flagged_matching_reports_by_flag"] == {"A_FLAG": 1}
    assert result["primary"]["flagged_matching_reports_by_source"] == {"ClinicalTrials.gov": 1}
    assert result["primary"]["matching_reports_by_source"] == {"EMA": 1}
    assert result["primary"]["matching_non_trial_reports"] == 1
    flagged = result["quality_flagged_reports_included"]
    assert flagged["pairs_whose_highest_status_differs_from_primary"] == 1
    assert flagged["highest_status_changes_from_primary"] == {
        f"{OUTSIDE} -> stopped_negative_or_safety": 1}
    trials_only = result["clinical_trial_reports_only"]
    assert trials_only["highest_status_changes_from_primary"] == {
        f"{OUTSIDE} -> no_matching_trial_or_indication_record": 1}
    assert result["completed_trials_as_completed"][
        "pairs_whose_highest_status_differs_from_primary"] == 0


@pytest.mark.parametrize("n_drugs, diseases, read", [
    (1, (OUTCOME,), True), (2, (OUTCOME,), False), (1, (OUTCOME, "MONDO:77"), False),
    (3, (OUTCOME, "MONDO:77"), False)])
def test_single_drug_single_disease_rule_reads_only_such_reports(n_drugs, diseases, read):
    lk = look([mech(1)], [], [trial("t1", [1], "RECRUITING", diseases=diseases,
                                    n_drugs=n_drugs)], resource=[OUTCOME, "MONDO:77"])
    assert pair(lk).highest_status == "in_clinical_trials"
    assert pair(lk, "single_drug_single_disease_reports").highest_status == (
        "in_clinical_trials" if read else "no_matching_trial_or_indication_record")


def test_completed_trial_sets_the_completed_class_only_under_its_rule():
    lk = look([mech(1)], [], [trial("t1", [1], "COMPLETED")])
    assert pair(lk).highest_status == OUTSIDE
    assert pair(lk, "completed_trials_as_completed").highest_status == (
        "completed_no_later_record")
    unknown = look([mech(1)], [], [trial("t1", [1], "UNKNOWN")])
    assert pair(unknown, "completed_trials_as_completed").highest_status == OUTSIDE


def test_null_result_claim_is_no_cooccurrence_except_under_its_rule():
    lk = look([mech(1)], [], [trial("t1", [1], "TERMINATED", ["Negative"])])
    null = claim("reported_nonsignificant_or_null")
    assert join_claim(null, pair(lk)).trial_history_cooccurrence is False
    assert join_claim(claim("raises"), pair(lk)).trial_history_cooccurrence is True
    counted = join_claim(null, pair(lk, "null_result_claims_counted"))
    assert counted.trial_history_cooccurrence is True
    assert counted.directionally_relevant_stopped_trials == []


def test_every_registered_rule_is_run_and_the_primary_rule_sets_nothing():
    assert list(RULES) == [
        "primary", "with_component_level", "clinical_trial_reports_only",
        "quality_flagged_reports_included", "single_drug_single_disease_reports",
        "completed_trials_as_completed", "null_result_claims_counted"]
    assert RULES["primary"] == Rule()
    assert sum(sum(r.model_dump().values()) for r in RULES.values()) == len(RULES) - 1
    result, _, _ = tables([claim()], look([mech(1)], [ind(1, 4.0)]))
    assert list(result) == list(RULES)


def test_other_matching_record_is_the_registered_eighth_class():
    assert OUTSIDE == "other_matching_record"
    result, _, _ = tables([claim()], look([mech(1)], [ind(1, 0.5)]))
    assert result["primary"]["pairs_by_highest_status"][OUTSIDE] == 1
    assert sum(result["primary"]["pairs_by_highest_status"].values()) == 1


def test_component_level_action_types_do_not_set_the_primary_direction():
    lk = look([mech(1, "INHIBITOR"), mech(1, "AGONIST", level="component_level_mapping")])
    assert pair(lk).drugs[0].direction == "decrease"
    assert pair(lk, "with_component_level").drugs[0].direction == "ambiguous"


def test_outcome_absent_from_the_resources_leaves_the_join():
    rec = pair(look([mech(1)], resource=["MONDO:77"]))
    assert rec.join_state == "outcome_not_in_resource"
    assert rec.highest_status is None


def test_resource_identifiers_are_canonicalized():
    assert pair(look([mech(1)], resource=["EFO:1"])).join_state == "matched"


@pytest.mark.parametrize("indicated,directions,expected", [
    ("decrease", [], "no_drug"),
    ("decrease", ["ambiguous"], "ambiguous_only"),
    ("decrease", ["decrease", "decrease", "ambiguous"], "concordant"),
    ("decrease", ["increase"], "discordant"),
    ("increase", ["increase"], "concordant"),
    ("increase", ["decrease", "ambiguous"], "discordant"),
    ("decrease", ["decrease", "increase"], "mixed"),
])
def test_alignment_classes(indicated, directions, expected):
    actions = {"decrease": "INHIBITOR", "increase": "AGONIST", "ambiguous": "BINDING AGENT"}
    lk = look([mech(i + 1, actions[d]) for i, d in enumerate(directions)])
    assert alignment(indicated, pair(lk).drugs) == expected


def test_alignment_over_matching_indication_and_over_any_indication():
    lk = look([mech(1, "INHIBITOR"), mech(2, "AGONIST"), mech(3, "INHIBITOR")],
              [ind(1, 2.0, "MONDO:77"), ind(2, 1.0)],
              [trial("t1", [3], "COMPLETED", diseases=["MONDO:77"])],
              resource=[OUTCOME, "MONDO:77"])
    rec = pair(lk)
    raises = join_claim(claim("raises"), rec)
    assert raises.indicated_change == "decrease"
    assert raises.alignment_matching_indication == "discordant"
    assert raises.alignment_any_indication == "mixed"
    lowers = join_claim(claim("lowers"), rec)
    assert lowers.indicated_change == "increase"
    assert lowers.alignment_matching_indication == "concordant"
    assert lowers.alignment_any_indication == "mixed"


def test_drug_with_only_a_matching_trial_record_is_a_drug_for_the_matching_indication():
    rec = pair(look([mech(1, "INHIBITOR")], [], [trial("t1", [1], "COMPLETED")]))
    assert join_claim(claim("raises"), rec).alignment_matching_indication == "concordant"


@pytest.mark.parametrize("direction,verified", [
    ("raises", False), ("lowers", False), ("reported_nonsignificant_or_null", True),
    ("not_stated", True)])
def test_claims_without_a_verified_direction_leave_the_alignment(direction, verified):
    rec = pair(look([mech(1)], [ind(1, 4.0)], [trial("t1", [1], "TERMINATED", ["Negative"])]))
    j = join_claim(claim(direction, verified), rec)
    assert j.indicated_change is None
    assert j.alignment_matching_indication is None and j.alignment_any_indication is None
    assert j.trial_history_cooccurrence is (direction != "reported_nonsignificant_or_null")
    assert j.directionally_relevant_stopped_trials == []


def test_cooccurrence_and_directionally_relevant_stopped_trial():
    lk = look([mech(1, "INHIBITOR"), mech(2, "AGONIST")], [], [
        trial("neg_inhibitor", [1], "TERMINATED", ["Negative"]),
        trial("safety_agonist", [2], "WITHDRAWN", ["Safety_Sideeffects"]),
        trial("business_inhibitor", [1], "TERMINATED", ["Business_Administrative"]),
        trial("suspended_inhibitor", [1], "SUSPENDED", ["Negative"])])
    rec = pair(lk)
    raises = join_claim(claim("raises"), rec)
    assert raises.trial_history_cooccurrence is True
    assert raises.directionally_relevant_stopped_trials == ["neg_inhibitor"]
    lowers = join_claim(claim("lowers", wording="target"), rec)
    assert lowers.directionally_relevant_stopped_trials == ["safety_agonist"]
    assoc = join_claim(claim("raises", wording="association"), rec)
    assert assoc.trial_history_cooccurrence is False
    assert assoc.directionally_relevant_stopped_trials == []


def test_stopped_trial_of_an_ambiguous_drug_is_cooccurrence_but_not_directionally_relevant():
    rec = pair(look([mech(1, "BINDING AGENT")], [],
                    [trial("t1", [1], "TERMINATED", ["Negative"])]))
    j = join_claim(claim("raises"), rec)
    assert j.trial_history_cooccurrence is True
    assert j.directionally_relevant_stopped_trials == []


def test_tables_counts_pairs_once_and_keeps_unmatched_pairs_out_of_every_class():
    lk = look([mech(1, "INHIBITOR")], [ind(1, 4.0)],
              [trial("t1", [1], "TERMINATED", ["Negative"])])
    claims = [claim(rid="a"), claim(rid="b", wording="association"),
              DrugClaim(claim_record_id="c", family_id="G", protein_id="P1",
                        outcome_id="MONDO:555", direction="raises", direction_verified=True,
                        wording_class="causal")]
    result, pairs, joined = tables(claims, lk)
    primary = result["primary"]
    assert primary["pairs"] == 2 and primary["pairs_matched"] == 1
    assert primary["pairs_outcome_not_in_resource"] == 1
    assert primary["pairs_by_highest_status"]["approved"] == 1
    assert sum(primary["pairs_by_highest_status"].values()) == 1
    assert primary["stopped_trial_events_by_label"] == {"Negative": 1}
    assert primary["claims_on_matched_pairs"] == 2
    assert primary["claims_causal_or_target_with_stopped_trial_event"] == 1
    assert primary["claims_with_directionally_relevant_stopped_trial"] == 1
    assert primary["alignment_matching_indication"] == {"concordant": 2}
    assert len(pairs) == 2 * len(RULES) and len(joined) == 2 * len(RULES)
