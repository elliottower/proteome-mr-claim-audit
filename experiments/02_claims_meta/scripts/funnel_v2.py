# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""The funnel across stages: records per source and query, citation-chasing additions,
duplicates, document types, prefilter marks, eligibility decisions, family links, extraction
failures, quotation-check and verification failures by reason, and eligible families by window.
No model is called.

This copy supersedes scripts/funnel.py, which stays sealed (PREREG.md log, 2026-10-08). It
differs in one thing. The registered script takes a gated chase round to have been screened as
planned: the records the prefilter left unmarked and the marked records the gate audit
sampled, with the audit at its stopping rule. In the run, the marked records of the chase
rounds were all sent to the screening model instead (logged departures of 6 and 7 October), and
the registered script stops on such a round. Here a gated round is `screened in full` when
every record the prefilter marked in it has an eligibility decision; that is read from the
screening records, the prefilter marks and the decisions given, and from nothing else. For such
a round every record with an abstract counts as sent to screening, the audit need not have
reached its stopping rule, the audit of the batches that were sampled is still reported where
there are any, and the round's entry says `screened_in_full` with the number of marked records
judged and judged eligible or uncertain. A gated round in which some marked record has no
decision is read exactly as the registered script reads it, and stops the funnel when its
audit has not finished or its decisions are not those of whole batches.

Each stage's count is checked against the stage before it, and a mismatch raises:

    screening     a record id occurs once across the search and the chase rounds; the prefilter
                  marks hold every screening record with an abstract once
    no abstract   a record classed `no_abstract` (scripts/abstract_floor.py) has no prefilter
                  mark, no eligibility decision and no extraction row, and is not in a gate
                  sample
    eligibility   the decisions hold exactly the records sent to GPT-6.1 Sol: every record of
                  the search that has an abstract, and of a chase round the records with an
                  abstract that the prefilter left unmarked and the marked records sampled by
                  the gate audit
    gate audit    the sampled records of a chase round are whole batches of the registered
                  order, and the audit has reached its stopping rule (scripts/gate_audit.py)
    extraction    the extraction rows hold exactly the records judged `eligible`,
                  `eligible_count_not_stated` or `uncertain`
    quotation     one span check per extracted claim record
    verification  one claim check per extracted claim record

A screening directory is the output of assemble_screening_set.py (the search) or of
citation_chase.py (a chase round) after keyword_prefilter.py has run on it.

Gate audit, per chase round: the marked records sampled and judged, the share judged `eligible`,
`eligible_count_not_stated` or `uncertain` with its one-sided 95% upper bound, and the estimated
number of eligible records among the marked records not judged. A round whose audit stopped at
the 3,000-record cap with the bound not below the tolerance is listed under
`gate_audit_rounds_cap_reached_without_satisfying_tolerance`. The sampled records judged
eligible are in the eligibility, extraction and family counts like any other record; the
decisions files passed here include those of the gate batches.

No abstract, per screening set (the search and each chase round): the `no_abstract` records,
those with no text at all and those with a stub below the floor, by document class, and those
whose title alone holds a genetic term and a protein term of the keyword prefilter
(`title_holds_both_term_groups`, listed by id). The last count bounds the eligible papers the
rule can leave out: a record whose title names neither kind of term would have been marked by
the prefilter on its title.

Usage: uv run scripts/funnel_v2.py --screening-dir <dir> [--screening-dir <dir> ...]
           --decisions <f> [<f> ...] --extraction <f> [<f> ...] --spans <f> [<f> ...]
           --checks <f> [<f> ...] --assembly <dir written by assemble_registry.py> --out <dir>
"""

import argparse
import collections
import datetime
import json
import pathlib

from pydantic import BaseModel

import gate_audit
import keyword_prefilter
from abstract_floor import ABSTRACT_FLOOR
from smoke_guard import check_smoke_output

ELIGIBLE = ("eligible", "eligible_count_not_stated", "uncertain")


class FunnelError(Exception):
    """Two stages disagree on which records or claim records they hold."""


class ScreeningRun(BaseModel):
    name: str
    chase_round: int | None
    counts: dict
    records: list[dict]
    marks: list[dict]
    gated: bool
    gate_sampled: list[str] = []

    def without_abstract(self) -> list[dict]:
        return [r for r in self.records if r.get("no_abstract")]


def same_ids(stage: str, expected: list[str], found: list[str]) -> None:
    if len(set(found)) != len(found):
        dup = [i for i, n in collections.Counter(found).items() if n > 1]
        raise FunnelError(f"{stage}: ids listed twice: {sorted(dup)[:5]}")
    if set(expected) != set(found):
        raise FunnelError(f"{stage}: missing {sorted(set(expected) - set(found))[:5]}, "
                          f"unexpected {sorted(set(found) - set(expected))[:5]}")


def claim_ids(extraction: list[dict]) -> list[str]:
    return [f"{r['pmid']}:{i:03d}" for r in extraction if r["status"] == "ok"
            for i in range(len(r["output"]["claims"]))]


def funnel(runs: list[ScreeningRun], decisions: list[dict], extraction: list[dict],
           spans: list[dict], checks: list[dict], links: list[dict], meta: dict[str, dict],
           assembly_report: dict) -> dict:
    record_ids = [r["record_id"] for run in runs for r in run.records]
    same_ids("screening records", sorted(set(record_ids)), record_ids)
    sent: list[str] = []
    prefilter: dict[str, dict] = {}
    audits: dict[str, dict] = {}
    decision_of = {d["pmid"]: d["decision"] for d in decisions}
    terms = keyword_prefilter.load_terms() if any(run.without_abstract() for run in runs) else {}
    no_abstract: dict[str, dict] = {}
    for run in runs:
        without = run.without_abstract()
        without_ids = {r["record_id"] for r in without}
        ids = [r["record_id"] for r in run.records if r["record_id"] not in without_ids]
        titled = sorted(r["record_id"] for r in without if not keyword_prefilter.mark(
            r["record_id"], r.get("title") or "", "", terms).marked)
        no_abstract[run.name] = {
            "records": len(without),
            "empty": sum(not (r.get("abstract") or "").strip() for r in without),
            "stub_below_floor": sum(bool((r.get("abstract") or "").strip()) for r in without),
            "by_document_class": dict(sorted(collections.Counter(
                r["kind"] for r in without).items())),
            "title_holds_both_term_groups": len(titled),
            "title_holds_both_term_groups_record_ids": titled}
        judged_without = sorted(without_ids & set(decision_of))
        if judged_without:
            raise FunnelError(f"no abstract, {run.name}: records classed no_abstract have an "
                              f"eligibility decision: {judged_without[:5]}")
        same_ids(f"prefilter marks of {run.name}", ids, [m["record_id"] for m in run.marks])
        marked = [m["record_id"] for m in run.marks if m["marked"]]
        sampled = run.gate_sampled if run.gated else []
        if set(sampled) - set(marked):
            raise FunnelError(f"gate sample of {run.name}: sampled records that are not "
                              f"marked: {sorted(set(sampled) - set(marked))[:5]}")
        in_full = screened_in_full(run.gated, marked, decision_of)
        not_screened = len(marked) - len(sampled) if run.gated and not in_full else 0
        if in_full:
            sent += ids
        else:
            sent += [i for i in ids if not (run.gated and i in set(marked))] + sampled
        prefilter[run.name] = {
            "records": len(ids), "no_abstract_records_not_screened": len(without),
            "marked": len(marked),
            "no_genetic_term": sum(not m["has_genetic_term"] for m in run.marks),
            "no_protein_term": sum(not m["has_protein_term"] for m in run.marks),
            "marked_records_sampled_by_the_gate_audit": len(sampled),
            "marked_records_not_screened": not_screened,
            "sent_to_screening": len(ids) - not_screened,
            "screened_in_full": in_full}
        if run.gated:
            if in_full and not sampled:
                audits[run.name] = {"sampled": 0}
            else:
                try:
                    audits[run.name] = gate_audit.audit(
                        marked, {i: decision_of[i] for i in sampled if i in decision_of})
                except gate_audit.GateAuditError as e:
                    raise FunnelError(f"gate audit of {run.name}: {e}") from e
            if not in_full and not audits[run.name]["finished"]:
                raise FunnelError(f"gate audit of {run.name}: batch "
                                  f"{audits[run.name]['next_batch']} has not been judged")
            audits[run.name]["no_abstract_records_of_the_round"] = len(without)
            audits[run.name]["screened_in_full"] = in_full
            if in_full:
                audits[run.name]["marked_records_judged_in_full_screening"] = sum(
                    decision_of[i] != gate_audit.FAILED for i in marked)
                audits[run.name]["marked_records_judged_eligible_or_uncertain"] = sum(
                    decision_of[i] in ELIGIBLE for i in marked)
    same_ids("eligibility decisions", sent, [d["pmid"] for d in decisions])
    by_decision = collections.Counter(d["decision"] for d in decisions)
    to_extraction = [d["pmid"] for d in decisions if d["decision"] in ELIGIBLE]
    same_ids("extraction rows", to_extraction, [r["pmid"] for r in extraction])
    extracted = claim_ids(extraction)
    same_ids("span checks", extracted, [f"{s['pmid']}:{s['claim_index']:03d}" for s in spans])
    same_ids("claim checks", extracted, [c["claim_record_id"] for c in checks])

    claims_of = {r["pmid"]: (len(r["output"]["claims"]) if r["status"] == "ok" else None)
                 for r in extraction}
    no_named = sorted(f for f, m in meta.items() if m["extraction"] == "ok"
                      and sum(claims_of.get(i) or 0 for i in m["registry_records"]) == 0)
    kind = collections.Counter(r["kind"] for run in runs for r in run.records)
    return {
        "search": {run.name: run.counts for run in runs if run.chase_round is None},
        "citation_chasing": {f"round_{run.chase_round}": run.counts for run in runs
                             if run.chase_round is not None},
        "screening": {"records": len(record_ids),
                      "records_from_citation_chasing": sum(
                          len(run.records) for run in runs if run.chase_round is not None),
                      "by_document_class": dict(sorted(kind.items())),
                      "no_abstract": sum(n["records"] for n in no_abstract.values()),
                      "with_an_abstract": len(record_ids) - sum(
                          n["records"] for n in no_abstract.values())},
        "no_abstract": {"floor_characters": ABSTRACT_FLOOR, **no_abstract},
        "prefilter": prefilter,
        "eligibility": {
            "records_sent_to_screening": len(sent),
            "decisions": dict(sorted(by_decision.items())),
            "to_extraction": len(to_extraction),
            "eligibility_uncertain": by_decision["uncertain"],
            "also_tissue_or_csf": sum("also_tissue_or_csf" in d["flags"] for d in decisions
                                      if d["decision"] in ELIGIBLE),
            "ineligible_by_reason": dict(sorted(collections.Counter(
                r for d in decisions for r in d["reasons"]).items()))},
        "extraction": {
            "records": len(extraction),
            "ok": sum(r["status"] == "ok" for r in extraction),
            "extraction_failed": sum(r["status"] != "ok" for r in extraction),
            "needed_retry": sum(r["status"] == "ok" and r["attempts"] > 1 for r in extraction),
            "claim_records": len(extracted)},
        "quotation_check": {"spans": len(spans), "pass": sum(bool(s["passes"]) for s in spans),
                            "fail": sum(not s["passes"] for s in spans)},
        "verification": {
            "claim_records": len(checks),
            "enters_registry": sum(bool(c["enters_registry"]) for c in checks),
            "left_out_by_first_failure": dict(sorted(collections.Counter(
                c["first_failure"] for c in checks if c["first_failure"]).items())),
            "direction_verification_state": dict(sorted(collections.Counter(
                c["direction_verification_state"] for c in checks).items()))},
        "families": {
            "links_by_rule": dict(sorted(collections.Counter(l["rule"] for l in links).items())),
            "eligible_families": len(meta),
            "eligible_families_by_window": dict(sorted(collections.Counter(
                m["window"] for m in meta.values()).items())),
            "eligible_families_extraction_failed": sum(
                m["extraction"] == "extraction_failed" for m in meta.values()),
            "eligible_no_named_claims": len(no_named),
            "eligible_no_named_claims_families": no_named},
        "registry_assembly": assembly_report,
        "prefiltered_citation_chasing_gate_audit": audits,
        "gate_audit_rounds_cap_reached_without_satisfying_tolerance": rounds_at_cap(audits),
    }


def screened_in_full(gated: bool, marked: list[str], decision_of: dict[str, str]) -> bool:
    """Whether a gated round was screened in full: it has marked records and every one of
    them has an eligibility decision."""
    return gated and bool(marked) and all(i in decision_of for i in marked)


def rounds_at_cap(audits: dict[str, dict]) -> list[str]:
    """The chase rounds whose gate audit stopped at the 3,000-record cap with the bound not
    below the tolerance, and that were not then screened in full."""
    return sorted(name for name, a in audits.items()
                  if a.get("cap_reached_without_satisfying_tolerance")
                  and not a.get("screened_in_full"))


def read_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def load_run(folder: pathlib.Path) -> ScreeningRun:
    chase = folder / "chase_counts.json"
    counts = json.loads((chase if chase.exists() else folder / "funnel.json").read_text())
    return ScreeningRun(
        name=folder.name, chase_round=counts["round"] if chase.exists() else None,
        counts=counts, records=read_jsonl(folder / "screening_records.jsonl"),
        marks=read_jsonl(folder / "prefilter_marks.jsonl"),
        gated=json.loads((folder / "prefilter_counts.json").read_text())["gated"],
        gate_sampled=[r["pmid"] for p in sorted(folder.glob("gate_sample_batch_*.jsonl"))
                      for r in read_jsonl(p)])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--screening-dir", type=pathlib.Path, action="append", required=True)
    ap.add_argument("--decisions", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--extraction", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--spans", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--checks", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--assembly", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    # The funnel of a smoke registry goes under its smoke label, and no other funnel does.
    check_smoke_output(a.assembly, a.out.resolve().name)

    def many(paths: list[pathlib.Path]) -> list[dict]:
        return [row for p in paths for row in read_jsonl(p)]

    result = {
        "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "inputs": {"screening_dirs": [str(p) for p in a.screening_dir],
                   "decisions": [str(p) for p in a.decisions],
                   "extraction": [str(p) for p in a.extraction],
                   "spans": [str(p) for p in a.spans], "checks": [str(p) for p in a.checks],
                   "assembly": str(a.assembly)},
        **funnel([load_run(d) for d in a.screening_dir], many(a.decisions), many(a.extraction),
                 many(a.spans), many(a.checks),
                 json.loads((a.assembly / "families.json").read_text())["links"],
                 json.loads((a.assembly / "families_meta.json").read_text()),
                 json.loads((a.assembly / "registry_assembly.json").read_text()))}
    a.out.mkdir(parents=True, exist_ok=True)
    target = a.out / "funnel.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; archive it before rerunning")
    target.write_text(json.dumps(result, indent=1))
    print(json.dumps({k: v for k, v in result.items() if k not in ("search", "inputs")},
                     indent=1))


if __name__ == "__main__":
    main()
