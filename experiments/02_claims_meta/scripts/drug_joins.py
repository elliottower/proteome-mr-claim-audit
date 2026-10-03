# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.13.5"]
# ///
"""Drug-development records of each registry pair, and the nominal abundance–action alignment
of each claim (stage 5 joins to ChEMBL 37 and Open Targets 26.09 `clinical_report`).

Inputs. A `DrugIndex` built from the pinned files by `drug_tables.py`; the registry's claim
records (`build_registry.RegistryClaim` lines) with each claim's wording class; the committed
collision table; and the one-step parent edges of the pinned ontology. No model is called.

Drugs acting on a protein. Every molecule is its parent (`molecule_hierarchy.parent_molregno`)
before anything is read from it. Primary rule: `drug_mechanism` rows with `direct_interaction`
= 1 and `molecular_mechanism` = 1 on a `SINGLE PROTEIN` target of Homo sapiens whose component
is the protein's UniProt accession. Rows on a `PROTEIN COMPLEX`, `PROTEIN COMPLEX GROUP`,
`PROTEIN FAMILY`, `SELECTIVITY GROUP`, `CHIMERIC PROTEIN` or `PROTEIN-PROTEIN INTERACTION`
target holding the accession are `component_level_mapping` and enter only the sensitivity
level (`with_component_level`). Other target types are not used.

Matching indication. An indication or trial disease matches a pair when its canonical
identifier (collision table; an identifier outside the table is its own) equals the pair's
outcome identifier. An identifier with more than one canonical identifier matches nothing and
is counted. An identifier one ontology step broader or narrower than the pair's outcome is
recorded as `related_indication` and never sets a class.

Phase comes from ChEMBL `max_phase_for_ind` only (a parent takes the highest value among its
forms for each indication); trial events come from `clinical_report` only.

Highest development status, first that applies:

    approved                      a drug has max_phase_for_ind = 4 for a matching indication
    in_clinical_trials            a matching trial is RECRUITING, ACTIVE_NOT_RECRUITING,
                                  NOT_YET_RECRUITING or ENROLLING_BY_INVITATION
    stopped_negative_or_safety    a matching trial that is not SUSPENDED carries `Negative` or
                                  `Safety_Sideeffects`
    stopped_other                 a matching trial that is not SUSPENDED carries any other label
    suspended                     a matching trial is SUSPENDED
    completed_no_later_record     a drug has max_phase_for_ind 1–3 for a matching indication
    no_matching_trial_or_indication_record
                                  no drug acting on the protein has any record for a matching
                                  indication

    other_matching_record         a drug acting on the protein has a record for a matching
                                  indication and none of the first six conditions holds: a
                                  ChEMBL phase of 0.5, -1 or none; a matching trial that is
                                  COMPLETED, of UNKNOWN status, an expanded-access record, or
                                  TERMINATED or WITHDRAWN with no stop label; or a matching
                                  report that is not a trial (a regulator, label or
                                  nomenclature source). The reason is stored

(`no_matching_trial_or_indication_record` is the last class in the registered order; it and
`other_matching_record` exclude each other.) A `clinical_report` row is a trial when it has a
`trialOverallStatus` (in the pinned file, every ClinicalTrials.gov row and no other). A report
that is not a trial (a regulator, label or nomenclature source) is a record for a matching
indication and never sets a trial class; every pair record lists its matching reports by source
and how many of them are not trials.

Quality-control flags. A report carrying any `qualityControls` flag is not read in the primary
analysis (Open Targets leaves such reports out of its own aggregates). Each pair record counts
the flagged reports that would have matched, by flag, and the tables give them by flag and by
source.

Sensitivity rules, each a full rerun of the tables beside the primary, with the number of pairs
whose highest status differs from the primary and the changes by class:

    with_component_level                  `component_level_mapping` drugs included
    clinical_trial_reports_only           reports that are not trials are not records
    quality_flagged_reports_included      reports carrying a `qualityControls` flag are read
    single_drug_single_disease_reports    only reports naming one drug and one disease are read
    completed_trials_as_completed         a matching COMPLETED trial sets
                                          `completed_no_later_record` as a ChEMBL phase 1–3 does
    null_result_claims_counted            claims reporting no significant estimate count as
                                          `causal` or `target` claims in the co-occurrence

Claim–trial-history co-occurrence counts claims of wording class `causal` or `target` whose
direction is not `reported_nonsignificant_or_null`: a record stating that no significant
estimate was found asserts no effect, whatever keyword its span holds.

Stopped-trial events: every matching trial with at least one stop-reason label whose status is
not SUSPENDED, labels verbatim, one event per report. Suspended trials are listed apart. A label
outside the 13 registered values raises.

Direction rule (pqtl-mr-domain-of-validity PREREG_direction_concordance.md §3.2–3.4, unchanged):
`token_class`, `drug_direction`. A claim with verified direction `raises` indicates decreasing
the protein; `lowers` indicates increasing it. Alignment per claim, over the drugs with a record
for a matching indication and over every drug acting on the protein: `concordant`,
`discordant`, `mixed`, `ambiguous_only`, `no_drug`. Claims without a verified `raises` or
`lowers` direction leave the alignment and are counted.

Usage: uv run scripts/drug_joins.py --claims <registry_claims.jsonl> --wording <wording.jsonl>
           --index <drug_index.json> --ontology-edges <edges.csv> --out <dir>
"""

import argparse
import collections
import csv
import datetime
import json
import pathlib
from collections.abc import Iterable, Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict

from canonical_ids import load_collision_table

ACTIVE_STATUSES = ("RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING",
                   "ENROLLING_BY_INVITATION")
SUSPENDED = "SUSPENDED"
# The committed table of source stop-reason labels (the 13 values of
# `trialStopReasonCategories` in the pinned 26.09 file) to collapsed classes.
STOP_REASON_CLASS = {
    "Another_Study": "stopped_other",
    "Business_Administrative": "stopped_other",
    "Covid19": "stopped_other",
    "Insufficient_Enrollment": "stopped_other",
    "Invalid_Reason": "stopped_other",
    "Logistics_Resources": "stopped_other",
    "Negative": "stopped_negative_or_safety",
    "No_Context": "stopped_other",
    "Regulatory": "stopped_other",
    "Safety_Sideeffects": "stopped_negative_or_safety",
    "Study_Design": "stopped_other",
    "Study_Staff_Moved": "stopped_other",
    "Uncategorised": "stopped_other",
}
STOP_LABELS = tuple(STOP_REASON_CLASS)
NEGATIVE_OR_SAFETY = "stopped_negative_or_safety"
STATUS_ORDER = ("approved", "in_clinical_trials", "stopped_negative_or_safety", "stopped_other",
                "suspended", "completed_no_later_record",
                "no_matching_trial_or_indication_record")
OUTSIDE = "other_matching_record"
COMPLETED = "COMPLETED"
NONSIG = "reported_nonsignificant_or_null"


class Rule(BaseModel):
    """What a rerun of the tables reads. The primary rule sets nothing."""
    model_config = ConfigDict(frozen=True)
    component_level: bool = False
    clinical_trials_only: bool = False
    include_flagged: bool = False
    single_drug_single_disease: bool = False
    completed_trial_sets_completed: bool = False
    null_result_claims_count: bool = False


RULES = {
    "primary": Rule(),
    "with_component_level": Rule(component_level=True),
    "clinical_trial_reports_only": Rule(clinical_trials_only=True),
    "quality_flagged_reports_included": Rule(include_flagged=True),
    "single_drug_single_disease_reports": Rule(single_drug_single_disease=True),
    "completed_trials_as_completed": Rule(completed_trial_sets_completed=True),
    "null_result_claims_counted": Rule(null_result_claims_count=True),
}
LEVELS = tuple(RULES)

TIER1 = {"INVERSE AGONIST": "BLOCKING", "NEGATIVE ALLOSTERIC MODULATOR": "BLOCKING",
         "POSITIVE ALLOSTERIC MODULATOR": "ACTIVATING", "PARTIAL AGONIST": "ACTIVATING"}
TIER2 = ("INHIBITOR", "ANTAGONIST", "BLOCKER", "DEGRADER", "DISRUPT", "SUPPRESSOR")
TIER3 = ("AGONIST", "ACTIVATOR", "OPENER", "STABILISER", "STABILIZER", "RELEASING AGENT")
INDICATED_CHANGE = {"raises": "decrease", "lowers": "increase"}

Level = Literal["single_protein", "component_level_mapping"]


class Mechanism(BaseModel):
    """One `drug_mechanism` row on one protein component, its molecule collapsed to the parent."""
    model_config = ConfigDict(frozen=True)
    mec_id: int
    molregno: int
    parent_molregno: int
    accession: str
    tid: int
    target_type: str
    level: Level
    action_type: str | None
    direct_interaction: int | None
    molecular_mechanism: int | None
    homologue: int | None


class Indication(BaseModel):
    """A parent molecule's highest `max_phase_for_ind` among its forms for one indication.
    `indication_id` is None when the ChEMBL rows carry a MeSH identifier only."""
    model_config = ConfigDict(frozen=True)
    parent_molregno: int
    indication_id: str | None
    max_phase: float | None


class Trial(BaseModel):
    """One `clinical_report` row, its drugs collapsed to ChEMBL parents. `n_drugs` is the
    number of drug entries the report lists, mapped or not."""
    model_config = ConfigDict(frozen=True)
    report_id: str
    n_drugs: int
    parent_molregnos: tuple[int, ...]
    disease_ids: tuple[str, ...]
    status: str | None
    stop_labels: tuple[str, ...]
    quality_controls: tuple[str, ...]
    source: str | None
    report_type: str | None


class DrugIndex(BaseModel):
    mechanisms: list[Mechanism]
    indications: list[Indication]
    trials: list[Trial]
    resource_disease_ids: list[str]
    provenance: dict


class Lookup:
    """The index keyed for the joins, with every disease identifier canonicalized."""

    def __init__(self, index: DrugIndex, collision: Mapping[str, frozenset[str]],
                 parents: Mapping[str, frozenset[str]]) -> None:
        for t in index.trials:
            unknown = sorted(set(t.stop_labels) - set(STOP_REASON_CLASS))
            if unknown:
                raise ValueError(f"report {t.report_id}: stop-reason label outside the "
                                 f"registered 13: {unknown}")
        self.collision = collision
        self.parents = parents
        self.children: dict[str, set[str]] = collections.defaultdict(set)
        for child, ps in parents.items():
            for p in ps:
                self.children[p].add(child)
        self.mechanisms: dict[str, list[Mechanism]] = collections.defaultdict(list)
        for m in index.mechanisms:
            self.mechanisms[m.accession].append(m)
        self.indications: dict[int, list[Indication]] = collections.defaultdict(list)
        for i in index.indications:
            self.indications[i.parent_molregno].append(i)
        self.trials: dict[int, list[Trial]] = collections.defaultdict(list)
        for t in index.trials:
            for p in t.parent_molregnos:
                self.trials[p].append(t)
        self.resource_outcomes = {c for i in index.resource_disease_ids
                                  for c in self.canonical_all(i)}

    def canonical_all(self, raw: str) -> frozenset[str]:
        return self.collision.get(raw, frozenset({raw}))

    def canonical(self, raw: str | None) -> str | None:
        """The single canonical identifier, or None for no identifier or more than one."""
        if raw is None:
            return None
        ids = self.canonical_all(raw)
        return next(iter(ids)) if len(ids) == 1 else None

    def relation(self, canonical: str | None, outcome: str) -> str | None:
        """`match`, `indication_broader` (a one-step parent of the pair's outcome),
        `indication_narrower` (a one-step child), or None."""
        if canonical is None:
            return None
        if canonical == outcome:
            return "match"
        if canonical in self.parents.get(outcome, ()):
            return "indication_broader"
        if canonical in self.children.get(outcome, ()):
            return "indication_narrower"
        return None


def parse_tokens(action_types: Iterable[str | None]) -> frozenset[str]:
    """§3.2 on a drug's action types (ChEMBL holds one action type per mechanism row, so the
    field's elements are the rows' values): empty elements give no token; strip, uppercase,
    collapse internal whitespace, deduplicate."""
    return frozenset(" ".join(a.upper().split()) for a in action_types if a and a.strip())


def token_class(token: str) -> Literal["BLOCKING", "ACTIVATING", "AMBIGUOUS"]:
    """§3.3: the first tier that matches."""
    if token in TIER1:
        return TIER1[token]
    if any(s in token for s in TIER2):
        return "BLOCKING"
    if any(s in token for s in TIER3):
        return "ACTIVATING"
    return "AMBIGUOUS"


def drug_direction(action_types: Iterable[str | None]
                   ) -> Literal["decrease", "increase", "ambiguous"]:
    """§3.4: drop AMBIGUOUS tokens; if at least one remains and all agree, BLOCKING is
    `decrease` and ACTIVATING is `increase`; otherwise `ambiguous`."""
    classes = {token_class(t) for t in parse_tokens(action_types)} - {"AMBIGUOUS"}
    if classes == {"BLOCKING"}:
        return "decrease"
    if classes == {"ACTIVATING"}:
        return "increase"
    return "ambiguous"


class DrugOnPair(BaseModel):
    parent_molregno: int
    levels: list[Level]
    action_types: list[str]
    direction: Literal["decrease", "increase", "ambiguous"]
    max_phase_matching: float | None
    has_matching_record: bool
    approved_other_indication: bool


class TrialEvent(BaseModel):
    report_id: str
    status: str | None
    stop_labels: list[str]
    stop_classes: list[str]
    parent_molregnos: list[int]
    quality_controls: list[str]
    source: str | None


class RelatedIndication(BaseModel):
    source: Literal["chembl_indication", "clinical_report"]
    relation: Literal["indication_broader", "indication_narrower"]
    indication_id: str
    parent_molregno: int
    max_phase: float | None = None
    report_id: str | None = None


class PairDrugRecord(BaseModel):
    protein_id: str
    outcome_id: str
    level: str
    join_state: Literal["matched", "outcome_not_in_resource"]
    highest_status: str | None
    outside_reasons: list[str]
    drugs: list[DrugOnPair]
    matching_trial_reports: int
    matching_non_trial_reports: int
    matching_reports_by_source: dict[str, int]
    flagged_matching_reports_not_read: int
    flagged_matching_reports_by_flag: dict[str, int]
    flagged_matching_reports_by_source: dict[str, int]
    stopped_trial_events: list[TrialEvent]
    suspended_trials: list[TrialEvent]
    target_drugged_elsewhere: bool
    related_indications: list[RelatedIndication]
    ambiguous_identifier_records: int
    unmapped_indication_rows: int


def event(t: Trial, drugs: set[int]) -> TrialEvent:
    return TrialEvent(report_id=t.report_id, status=t.status, stop_labels=list(t.stop_labels),
                      stop_classes=sorted({STOP_REASON_CLASS[l] for l in t.stop_labels}),
                      parent_molregnos=sorted(set(t.parent_molregnos) & drugs),
                      quality_controls=list(t.quality_controls), source=t.source)


def admitted(t: Trial, rule: Rule) -> bool:
    """Whether a rule reads the report at all."""
    if rule.clinical_trials_only and t.status is None:
        return False
    if t.quality_controls and not rule.include_flagged:
        return False
    if rule.single_drug_single_disease and (t.n_drugs != 1 or len(t.disease_ids) != 1):
        return False
    return True


def join_pair(look: Lookup, protein_id: str, outcome_id: str, level: str) -> PairDrugRecord:
    rule = RULES[level]
    mechs = [m for m in look.mechanisms.get(protein_id, ())
             if m.level == "single_protein" or rule.component_level]
    by_parent: dict[int, list[Mechanism]] = collections.defaultdict(list)
    for m in mechs:
        by_parent[m.parent_molregno].append(m)
    drug_ids = set(by_parent)
    related: list[RelatedIndication] = []
    ambiguous = unmapped = 0
    phase: dict[int, float | None] = {}
    has_ind_record: set[int] = set()
    approved_elsewhere: set[int] = set()
    for p in sorted(drug_ids):
        for ind in look.indications.get(p, ()):
            if ind.indication_id is None:
                unmapped += 1
                continue
            canon = look.canonical(ind.indication_id)
            if canon is None:
                ambiguous += 1
                continue
            rel = look.relation(canon, outcome_id)
            if rel == "match":
                has_ind_record.add(p)
                if ind.max_phase is not None and (phase.get(p) is None
                                                  or ind.max_phase > phase[p]):
                    phase[p] = ind.max_phase
                phase.setdefault(p, None)
                continue
            if ind.max_phase == 4:
                approved_elsewhere.add(p)
            if rel is not None:
                related.append(RelatedIndication(
                    source="chembl_indication", relation=rel, indication_id=canon,
                    parent_molregno=p, max_phase=ind.max_phase))
    matching: dict[str, Trial] = {}
    flagged_out: dict[str, Trial] = {}
    has_trial_record: set[int] = set()
    with_flagged = rule.model_copy(update={"include_flagged": True})
    for p in sorted(drug_ids):
        for t in look.trials.get(p, ()):
            read = admitted(t, rule)
            if not read and not admitted(t, with_flagged):
                continue
            rels = set()
            for d in t.disease_ids:
                canon = look.canonical(d)
                if canon is None:
                    ambiguous += read
                    continue
                rel = look.relation(canon, outcome_id)
                if read and rel in ("indication_broader", "indication_narrower"):
                    related.append(RelatedIndication(
                        source="clinical_report", relation=rel, indication_id=canon,
                        parent_molregno=p, report_id=t.report_id))
                rels.add(rel)
            if "match" in rels and read:
                matching[t.report_id] = t
                has_trial_record.add(p)
            elif "match" in rels:
                flagged_out[t.report_id] = t
    trials = [matching[k] for k in sorted(matching)]
    stopped = [event(t, drug_ids) for t in trials if t.stop_labels and t.status != SUSPENDED]
    suspended = [event(t, drug_ids) for t in trials if t.status == SUSPENDED]
    phases = [v for v in phase.values() if v is not None]
    status: str | None
    outside: list[str] = []
    if any(v == 4 for v in phases):
        status = "approved"
    elif any(t.status in ACTIVE_STATUSES for t in trials):
        status = "in_clinical_trials"
    elif any(NEGATIVE_OR_SAFETY in e.stop_classes for e in stopped):
        status = "stopped_negative_or_safety"
    elif stopped:
        status = "stopped_other"
    elif suspended:
        status = "suspended"
    elif any(1 <= v <= 3 for v in phases) or (rule.completed_trial_sets_completed and any(
            t.status == COMPLETED for t in trials)):
        status = "completed_no_later_record"
    elif not has_ind_record and not has_trial_record:
        status = "no_matching_trial_or_indication_record"
    else:
        status = OUTSIDE
        if has_ind_record:
            outside.append("chembl_indication_phase_not_1_to_4:"
                           + ",".join(sorted({"none" if v is None else f"{v:g}"
                                              for v in phase.values()})))
        if has_trial_record:
            outside.append("clinical_report_status:"
                           + ",".join(sorted({str(t.status) for t in trials})))
    joined = outcome_id in look.resource_outcomes
    drugs = [DrugOnPair(
        parent_molregno=p, levels=sorted({m.level for m in by_parent[p]}),
        action_types=sorted(parse_tokens(m.action_type for m in by_parent[p])),
        direction=drug_direction(m.action_type for m in by_parent[p]),
        max_phase_matching=phase.get(p),
        has_matching_record=p in has_ind_record or p in has_trial_record,
        approved_other_indication=p in approved_elsewhere) for p in sorted(drug_ids)]
    return PairDrugRecord(
        protein_id=protein_id, outcome_id=outcome_id, level=level,
        join_state="matched" if joined else "outcome_not_in_resource",
        highest_status=status if joined else None, outside_reasons=outside, drugs=drugs,
        matching_trial_reports=len(trials),
        matching_non_trial_reports=sum(t.status is None for t in trials),
        matching_reports_by_source=dict(sorted(collections.Counter(
            str(t.source) for t in trials).items())),
        flagged_matching_reports_not_read=len(flagged_out),
        flagged_matching_reports_by_flag=dict(sorted(collections.Counter(
            q for t in flagged_out.values() for q in t.quality_controls).items())),
        flagged_matching_reports_by_source=dict(sorted(collections.Counter(
            str(t.source) for t in flagged_out.values()).items())),
        stopped_trial_events=stopped,
        suspended_trials=suspended, target_drugged_elsewhere=bool(approved_elsewhere),
        related_indications=sorted(related, key=lambda r: r.model_dump_json()),
        ambiguous_identifier_records=ambiguous, unmapped_indication_rows=unmapped)


def alignment(indicated: str, drugs: list[DrugOnPair]) -> str:
    if not drugs:
        return "no_drug"
    directional = [d.direction for d in drugs if d.direction != "ambiguous"]
    if not directional:
        return "ambiguous_only"
    if all(d == indicated for d in directional):
        return "concordant"
    if all(d != indicated for d in directional):
        return "discordant"
    return "mixed"


def alignment_expectation(claims: list[tuple[str | None, str | None]]) -> dict:
    """The `concordant` share expected from the two margins. Input: per claim, its indicated
    change and its alignment class. Among the claims classed `concordant` or `discordant` (all
    their directional drugs point one way), the drugs' direction is the indicated change when
    concordant and its opposite when discordant; the expected share is
    P(indicated = decrease) x P(drugs = decrease) + P(indicated = increase) x P(drugs = increase),
    both margins taken over those claims."""
    rows = [(i, a) for i, a in claims if a in ("concordant", "discordant")]
    n = len(rows)
    if not n:
        return {"claims_concordant_or_discordant": 0, "observed_concordant_share": None,
                "expected_concordant_share": None}
    opposite = {"decrease": "increase", "increase": "decrease"}
    claim_decrease = sum(i == "decrease" for i, _ in rows) / n
    drug_decrease = sum((i if a == "concordant" else opposite[i]) == "decrease"
                        for i, a in rows) / n
    return {"claims_concordant_or_discordant": n,
            "share_of_claims_indicating_a_decrease": claim_decrease,
            "share_of_claims_whose_drugs_decrease": drug_decrease,
            "observed_concordant_share": sum(a == "concordant" for _, a in rows) / n,
            "expected_concordant_share": claim_decrease * drug_decrease
            + (1 - claim_decrease) * (1 - drug_decrease)}


class DrugClaim(BaseModel):
    """The fields of a registry claim the drug joins read, with its wording class."""
    model_config = ConfigDict(extra="ignore", frozen=True)
    claim_record_id: str
    family_id: str
    protein_id: str
    outcome_id: str
    direction: Literal["raises", "lowers", "reported_nonsignificant_or_null", "not_stated"]
    direction_verified: bool
    wording_class: Literal["target", "causal", "association"]


class ClaimDrugRecord(BaseModel):
    claim_record_id: str
    level: str
    indicated_change: str | None
    alignment_matching_indication: str | None
    alignment_any_indication: str | None
    trial_history_cooccurrence: bool
    directionally_relevant_stopped_trials: list[str]


def join_claim(c: DrugClaim, pair: PairDrugRecord) -> ClaimDrugRecord:
    indicated = INDICATED_CHANGE.get(c.direction) if c.direction_verified else None
    worded = c.wording_class in ("causal", "target") and (
        RULES[pair.level].null_result_claims_count or c.direction != NONSIG)
    relevant: list[str] = []
    if indicated is not None:
        aligned = {d.parent_molregno for d in pair.drugs if d.direction == indicated}
        relevant = [e.report_id for e in pair.stopped_trial_events
                    if NEGATIVE_OR_SAFETY in e.stop_classes and aligned & set(e.parent_molregnos)]
    return ClaimDrugRecord(
        claim_record_id=c.claim_record_id, level=pair.level, indicated_change=indicated,
        alignment_matching_indication=None if indicated is None else alignment(
            indicated, [d for d in pair.drugs if d.has_matching_record]),
        alignment_any_indication=None if indicated is None else alignment(indicated, pair.drugs),
        trial_history_cooccurrence=worded and bool(pair.stopped_trial_events),
        directionally_relevant_stopped_trials=relevant if worded else [])


def tables(claims: list[DrugClaim], look: Lookup) -> tuple[dict, list[PairDrugRecord],
                                                             list[ClaimDrugRecord]]:
    """The §Indices drug outcomes under the primary rule and under each sensitivity rule
    (`RULES`), with the pair and claim records behind them.
    A pair that leaves the join (`outcome_not_in_resource`) enters the match rate only, and so
    do its claims."""
    pairs = sorted({(c.protein_id, c.outcome_id) for c in claims})
    pair_records, claim_records, out = [], [], {}
    primary_status: dict[tuple[str, str], str | None] = {}

    def summed(matched: dict, field: str) -> dict[str, int]:
        total: collections.Counter = collections.Counter()
        for r in matched.values():
            total.update(getattr(r, field))
        return dict(sorted(total.items()))

    for level in LEVELS:
        recs = {p: join_pair(look, p[0], p[1], level) for p in pairs}
        matched = {p: r for p, r in recs.items() if r.join_state == "matched"}
        if level == "primary":
            primary_status = {p: r.highest_status for p, r in recs.items()}
        changes = collections.Counter(
            f"{primary_status[p]} -> {r.highest_status}" for p, r in recs.items()
            if r.highest_status != primary_status[p])
        joined_claims = [join_claim(c, matched[(c.protein_id, c.outcome_id)])
                         for c in claims if (c.protein_id, c.outcome_id) in matched]
        pair_records += recs.values()
        claim_records += joined_claims
        status = collections.Counter(r.highest_status for r in matched.values())
        directional = [j for j in joined_claims if j.indicated_change is not None]
        out[level] = {
            "pairs": len(pairs),
            "pairs_matched": len(matched),
            "pairs_outcome_not_in_resource": len(pairs) - len(matched),
            "pairs_by_highest_status": {k: status.get(k, 0) for k in (*STATUS_ORDER, OUTSIDE)},
            "pairs_with_any_drug": sum(bool(r.drugs) for r in matched.values()),
            "stopped_trial_events": sum(len(r.stopped_trial_events) for r in matched.values()),
            "stopped_trial_events_by_label": dict(sorted(collections.Counter(
                l for r in matched.values() for e in r.stopped_trial_events
                for l in e.stop_labels).items())),
            "pairs_with_stopped_trial_event": sum(
                bool(r.stopped_trial_events) for r in matched.values()),
            "suspended_trials": sum(len(r.suspended_trials) for r in matched.values()),
            "suspended_trials_by_label": dict(sorted(collections.Counter(
                l for r in matched.values() for e in r.suspended_trials
                for l in e.stop_labels).items())),
            "target_drugged_elsewhere": sum(
                r.target_drugged_elsewhere for r in matched.values()),
            "related_indication_records": dict(sorted(collections.Counter(
                f"{x.source}:{x.relation}" for r in matched.values()
                for x in r.related_indications).items())),
            "pairs_with_related_indication": sum(
                bool(r.related_indications) for r in matched.values()),
            "claims": len(claims),
            "claims_on_matched_pairs": len(joined_claims),
            "claims_causal_or_target_with_stopped_trial_event": sum(
                j.trial_history_cooccurrence for j in joined_claims),
            "claims_with_directionally_relevant_stopped_trial": sum(
                bool(j.directionally_relevant_stopped_trials) for j in joined_claims),
            "claims_without_verified_direction": len(joined_claims) - len(directional),
            "alignment_matching_indication": dict(sorted(collections.Counter(
                j.alignment_matching_indication for j in directional).items())),
            "alignment_any_indication": dict(sorted(collections.Counter(
                j.alignment_any_indication for j in directional).items())),
            "alignment_expected_from_margins": {
                "matching_indication": alignment_expectation(
                    [(j.indicated_change, j.alignment_matching_indication)
                     for j in directional]),
                "any_indication": alignment_expectation(
                    [(j.indicated_change, j.alignment_any_indication) for j in directional])},
            "ambiguous_identifier_records": sum(
                r.ambiguous_identifier_records for r in matched.values()),
            "matching_reports": sum(r.matching_trial_reports for r in matched.values()),
            "matching_non_trial_reports": sum(
                r.matching_non_trial_reports for r in matched.values()),
            "matching_reports_by_source": summed(matched, "matching_reports_by_source"),
            "flagged_matching_reports_not_read": sum(
                r.flagged_matching_reports_not_read for r in matched.values()),
            "flagged_matching_reports_by_flag": summed(
                matched, "flagged_matching_reports_by_flag"),
            "flagged_matching_reports_by_source": summed(
                matched, "flagged_matching_reports_by_source"),
            "pairs_whose_highest_status_differs_from_primary": sum(changes.values()),
            "highest_status_changes_from_primary": dict(sorted(changes.items())),
        }
    return out, pair_records, claim_records


def load_edges(path: pathlib.Path) -> dict[str, frozenset[str]]:
    """One-step parent edges of the pinned ontology: CSV with columns `child`, `parent`
    (canonical identifiers)."""
    parents: dict[str, set[str]] = collections.defaultdict(set)
    with path.open(newline="") as f:
        for r in csv.DictReader(f):
            parents[r["child"]].add(r["parent"])
    return {k: frozenset(v) for k, v in parents.items()}


def load_claims(claims: pathlib.Path, wording: pathlib.Path) -> list[DrugClaim]:
    """Registry claim lines joined to their wording class (`claim_record_id`, `wording_class`
    lines). A claim with no wording class raises."""
    cls = {}
    for line in wording.read_text().splitlines():
        if line.strip():
            w = json.loads(line)
            cls[w["claim_record_id"]] = w["wording_class"]
    out = []
    for line in claims.read_text().splitlines():
        if line.strip():
            c = json.loads(line)
            if c["claim_record_id"] not in cls:
                raise KeyError(f"claim {c['claim_record_id']} has no wording class")
            out.append(DrugClaim(**c, wording_class=cls[c["claim_record_id"]]))
    return out


def write_outputs(out: pathlib.Path, header: dict, result: dict, pairs: list[PairDrugRecord],
                  claims: list[ClaimDrugRecord]) -> None:
    """Result files first, then nothing else: the tables, and one JSON line per pair record and
    per claim record."""
    out.mkdir(parents=True, exist_ok=True)
    target = out / "drug_tables.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; archive it before rerunning")
    (out / "drug_pair_records.jsonl").write_text(
        "".join(r.model_dump_json() + "\n" for r in pairs))
    (out / "drug_claim_records.jsonl").write_text(
        "".join(r.model_dump_json() + "\n" for r in claims))
    target.write_text(json.dumps({**header, "levels": result}, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims", type=pathlib.Path, required=True)
    ap.add_argument("--wording", type=pathlib.Path, required=True)
    ap.add_argument("--index", type=pathlib.Path, required=True)
    ap.add_argument("--collision-table", type=pathlib.Path, required=True)
    ap.add_argument("--ontology-edges", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    index = DrugIndex.model_validate_json(a.index.read_text())
    look = Lookup(index, load_collision_table(a.collision_table), load_edges(a.ontology_edges))
    claims = load_claims(a.claims, a.wording)
    result, pairs, claim_records = tables(claims, look)
    header = {"claims_file": str(a.claims), "wording_file": str(a.wording),
              "index_file": str(a.index), "index_provenance": index.provenance,
              "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")}
    write_outputs(a.out, header, result, pairs, claim_records)
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
