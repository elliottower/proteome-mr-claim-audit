# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.13.5"]
# ///
"""Dry run of the drug-development joins on synthetic records: the 13 registry claims of
scripts/dry_run_synthetic.py (five pairs, P00001–P00005 × MONDO:1–MONDO:5) against an invented
drug index.

Every record is invented here; no ChEMBL or Open Targets file, no in-window record and no model
is read. The scenario covers an approved single-protein drug whose indication is written with an
EFO identifier the collision table merges into the pair's Mondo identifier, with a terminated
`Negative` trial (PAIR1); an active trial, a suspended trial with a safety label and an approval
at another indication (PAIR2); a drug on a protein complex with a withdrawn trial, visible only
at the component level (PAIR3); a drug whose only ChEMBL indication is one ontology step broader and whose
only matching record is a report that is not a trial (PAIR4); and an outcome absent from both
resources, which leaves the join (PAIR5). PAIR2 also has a stopped trial carrying a
quality-control flag, which the primary rule does not read, and a stopped two-drug trial, so
that each sensitivity rule but `completed_trials_as_completed` and `null_result_claims_counted`
changes a table value. The run raises if any table value differs from EXPECTED.

Usage: uv run scripts/dry_run_drug_synthetic.py --out <dir>
"""

import argparse
import datetime
import json
import pathlib

from drug_joins import (OUTSIDE, STATUS_ORDER, DrugClaim, DrugIndex, Indication, Lookup,
                        Mechanism, Trial, tables, write_outputs)

# (claim_record_id, family, protein, outcome, direction, direction_verified): the registry
# claims written by dry_run_synthetic.py.
CLAIMS = [
    ("J1:000", "J1", "P00001", "MONDO:1", "raises", True),
    ("J1:001", "J1", "P00001", "MONDO:1", "raises", True),
    ("J2:000", "J2", "P00001", "MONDO:1", "raises", True),
    ("J1:002", "J1", "P00002", "MONDO:2", "raises", True),
    ("J3:000", "J3", "P00002", "MONDO:2", "lowers", True),
    ("J1:003", "J1", "P00003", "MONDO:3", "raises", True),
    ("J4:000", "J4", "P00003", "MONDO:3", "raises", True),
    ("J2:001", "J2", "P00004", "MONDO:4", "raises", True),
    ("J3:001", "J3", "P00004", "MONDO:4", "raises", True),
    ("J4:001", "J4", "P00005", "MONDO:5", "raises", True),
    ("J4:002", "J4", "P00005", "MONDO:5", "lowers", True),
    ("J5:000", "J5", "P00005", "MONDO:5", "raises", False),
    ("J1:004", "J1", "P00005", "MONDO:5", "raises", True),
]
WORDING = {"J1": "target", "J2": "causal", "J3": "association", "J4": "causal", "J5": "target"}
COLLISION = {"EFO:1": frozenset({"MONDO:1"}), "MONDO:1": frozenset({"MONDO:1"})}
PARENTS = {"MONDO:4": frozenset({"MONDO:40"})}


def zero_status() -> dict[str, int]:
    return {k: 0 for k in (*STATUS_ORDER, OUTSIDE)}


def margins(n: int, claims_decrease: int, drugs_decrease: int, concordant: int) -> dict:
    """The alignment expectation from hand-counted margins: of `n` claims classed concordant or
    discordant, `claims_decrease` indicate a decrease and `drugs_decrease` have drugs that
    decrease the protein."""
    c, d = claims_decrease / n, drugs_decrease / n
    return {"claims_concordant_or_discordant": n, "share_of_claims_indicating_a_decrease": c,
            "share_of_claims_whose_drugs_decrease": d, "observed_concordant_share": concordant / n,
            "expected_concordant_share": c * d + (1 - c) * (1 - d)}


# Primary: three `raises` claims on PAIR1 against an inhibitor (concordant); on PAIR2 a `raises`
# claim against an agonist (discordant) and a `lowers` claim against it (concordant). Four of
# the five claims indicate a decrease and three have drugs that decrease the protein.
FIVE = margins(5, 4, 3, 4)
# Component level adds two `raises` claims on PAIR3 against a blocker (concordant).
SEVEN = margins(7, 6, 5, 6)


PRIMARY = {
    "pairs": 5, "pairs_matched": 4, "pairs_outcome_not_in_resource": 1,
    "pairs_by_highest_status": {**zero_status(), "approved": 1, "in_clinical_trials": 1,
                                OUTSIDE: 1, "no_matching_trial_or_indication_record": 1},
    "pairs_with_any_drug": 3,
    "stopped_trial_events": 2,
    "stopped_trial_events_by_label": {"Insufficient_Enrollment": 1, "Negative": 1},
    "pairs_with_stopped_trial_event": 2,
    "suspended_trials": 1, "suspended_trials_by_label": {"Safety_Sideeffects": 1},
    "target_drugged_elsewhere": 1,
    "related_indication_records": {"chembl_indication:indication_broader": 1},
    "pairs_with_related_indication": 1,
    "claims": 13, "claims_on_matched_pairs": 9,
    "claims_causal_or_target_with_stopped_trial_event": 4,
    "claims_with_directionally_relevant_stopped_trial": 3,
    "claims_without_verified_direction": 0,
    "alignment_matching_indication": {"ambiguous_only": 2, "concordant": 4, "discordant": 1,
                                      "no_drug": 2},
    "alignment_any_indication": {"ambiguous_only": 2, "concordant": 4, "discordant": 1,
                                 "no_drug": 2},
    "alignment_expected_from_margins": {"matching_indication": FIVE, "any_indication": FIVE},
    "ambiguous_identifier_records": 0,
    "matching_reports": 5, "matching_non_trial_reports": 1,
    "matching_reports_by_source": {"synthetic": 5},
    "flagged_matching_reports_not_read": 1,
    "flagged_matching_reports_by_flag": {"UNVALIDATED_INDICATION": 1},
    "flagged_matching_reports_by_source": {"synthetic": 1},
    "pairs_whose_highest_status_differs_from_primary": 0,
    "highest_status_changes_from_primary": {},
}
# Each sensitivity rule as the primary table with the values it changes.
EXPECTED = {
    "primary": PRIMARY,
    "with_component_level": {
        **PRIMARY,
        "pairs_by_highest_status": {**zero_status(), "approved": 1, "in_clinical_trials": 1,
                                    "stopped_other": 1, OUTSIDE: 1},
        "pairs_with_any_drug": 4,
        "stopped_trial_events": 3,
        "stopped_trial_events_by_label": {"Business_Administrative": 1,
                                          "Insufficient_Enrollment": 1, "Negative": 1},
        "pairs_with_stopped_trial_event": 3,
        "claims_causal_or_target_with_stopped_trial_event": 6,
        "alignment_matching_indication": {"ambiguous_only": 2, "concordant": 6,
                                          "discordant": 1},
        "alignment_any_indication": {"ambiguous_only": 2, "concordant": 6, "discordant": 1},
        "alignment_expected_from_margins": {"matching_indication": SEVEN,
                                            "any_indication": SEVEN},
        "matching_reports": 6, "matching_reports_by_source": {"synthetic": 6},
        "pairs_whose_highest_status_differs_from_primary": 1,
        "highest_status_changes_from_primary": {
            "no_matching_trial_or_indication_record -> stopped_other": 1},
    },
    "clinical_trial_reports_only": {
        **PRIMARY,
        "pairs_by_highest_status": {**zero_status(), "approved": 1, "in_clinical_trials": 1,
                                    "no_matching_trial_or_indication_record": 2},
        "alignment_matching_indication": {"concordant": 4, "discordant": 1, "no_drug": 4},
        "matching_reports": 4, "matching_non_trial_reports": 0,
        "matching_reports_by_source": {"synthetic": 4},
        "pairs_whose_highest_status_differs_from_primary": 1,
        "highest_status_changes_from_primary": {
            f"{OUTSIDE} -> no_matching_trial_or_indication_record": 1},
    },
    "quality_flagged_reports_included": {
        **PRIMARY,
        "stopped_trial_events": 3,
        "stopped_trial_events_by_label": {"Insufficient_Enrollment": 1, "Negative": 1,
                                          "Safety_Sideeffects": 1},
        "matching_reports": 6, "matching_reports_by_source": {"synthetic": 6},
        "flagged_matching_reports_not_read": 0, "flagged_matching_reports_by_flag": {},
        "flagged_matching_reports_by_source": {},
    },
    "single_drug_single_disease_reports": {
        **PRIMARY,
        "stopped_trial_events": 1,
        "stopped_trial_events_by_label": {"Negative": 1},
        "pairs_with_stopped_trial_event": 1,
        "claims_causal_or_target_with_stopped_trial_event": 3,
        "matching_reports": 4, "matching_reports_by_source": {"synthetic": 4},
    },
    "completed_trials_as_completed": PRIMARY,
    "null_result_claims_counted": PRIMARY,
}


def synthetic_index() -> DrugIndex:
    def mech(parent, accession, action, level="single_protein"):
        return Mechanism(mec_id=parent, molregno=parent, parent_molregno=parent,
                         accession=accession, tid=parent,
                         target_type="SINGLE PROTEIN" if level == "single_protein"
                         else "PROTEIN COMPLEX", level=level, action_type=action,
                         direct_interaction=1, molecular_mechanism=1, homologue=0)

    def trial(rid, parent, disease, status, labels=(), n_drugs=1, flags=()):
        return Trial(report_id=rid, n_drugs=n_drugs, parent_molregnos=(parent,),
                     disease_ids=(disease,), status=status, stop_labels=tuple(labels),
                     quality_controls=tuple(flags), source="synthetic",
                     report_type="INDICATION")

    return DrugIndex(
        mechanisms=[mech(100, "P00001", "INHIBITOR"), mech(200, "P00002", "AGONIST"),
                    mech(300, "P00003", "BLOCKER", "component_level_mapping"),
                    mech(400, "P00004", "BINDING AGENT")],
        indications=[
            Indication(parent_molregno=100, indication_id="EFO:1", max_phase=4.0),
            Indication(parent_molregno=200, indication_id="MONDO:20", max_phase=4.0),
            Indication(parent_molregno=400, indication_id="MONDO:40", max_phase=2.0)],
        trials=[trial("T1", 100, "MONDO:1", "TERMINATED", ["Negative"]),
                trial("T2", 200, "MONDO:2", "RECRUITING"),
                trial("T3", 200, "MONDO:2", "SUSPENDED", ["Safety_Sideeffects"]),
                trial("T4", 300, "MONDO:3", "WITHDRAWN", ["Business_Administrative"]),
                trial("T5", 400, "MONDO:4", None),
                trial("T6", 200, "MONDO:2", "TERMINATED", ["Safety_Sideeffects"],
                      flags=["UNVALIDATED_INDICATION"]),
                trial("T7", 200, "MONDO:2", "WITHDRAWN", ["Insufficient_Enrollment"],
                      n_drugs=2)],
        resource_disease_ids=["EFO:1", "MONDO:2", "MONDO:20", "MONDO:3", "MONDO:4", "MONDO:40"],
        provenance={"synthetic": True})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, required=True)
    out = ap.parse_args().out
    claims = [DrugClaim(claim_record_id=rid, family_id=fam, protein_id=p, outcome_id=o,
                        direction=d, direction_verified=v, wording_class=WORDING[fam])
              for rid, fam, p, o, d, v in CLAIMS]
    index = synthetic_index()
    result, pairs, claim_records = tables(claims, Lookup(index, COLLISION, PARENTS))
    header = {"synthetic": True,
              "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")}
    write_outputs(out, header, result, pairs, claim_records)
    (out / "synthetic_drug_index.json").write_text(index.model_dump_json(indent=1))
    if set(result) != set(EXPECTED):
        raise AssertionError("drug dry run: the rules run differ from EXPECTED")
    for level, want in EXPECTED.items():
        for key, value in want.items():
            if result[level][key] != value:
                raise AssertionError(f"drug dry run: {level}.{key} is {result[level][key]!r}, "
                                     f"expected {value!r}")
        if set(result[level]) != set(want):
            raise AssertionError(f"drug dry run: {level} keys differ from EXPECTED")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
