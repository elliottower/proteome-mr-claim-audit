# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5", "rapidfuzz==3.14.6"]
# ///
"""Assemble the claim registry's input files from the verified claim records. No model is called.

Inputs: the search records (scripts/assemble_screening_set.py `search_records.jsonl`), the
eligibility decisions (scripts/apply_eligibility.py), the extraction rows
(scripts/run_extraction.py, for `extraction_failed`) and the verifier's claim records
(scripts/verify_claims.py `claim_checks.jsonl`). The `pmid` field of the last three holds the
record id.

Families and dates: scripts/link_families.py, unchanged.

Document class. Records of kind `other` (scripts/assemble_screening_set.py: conference
abstracts, dissertations, datasets, repository copies and the like) are left out before the
families are built and counted (`records_other_document_type`). The sensitivity analysis
`all_document_types` keeps them (`include_other_types`): such a record joins the family of the
journal or preprint record it is linked to and adds nothing to it, and forms a family of its
own only when it is linked to none.

No abstract. A record classed `no_abstract` (scripts/abstract_floor.py) has no eligibility
decision; one that has a decision raises. It joins a family only as a linked record: the
family's registry record is chosen among its records that have an abstract, so a family whose
journal record has no abstract and whose preprint abstract is eligible takes the preprint. A
family with no eligible record that has an abstract is not an eligible family. Counted
(`records_no_abstract`, `eligible_families_with_a_no_abstract_record`).

Registry record of a family: its journal records judged eligible or uncertain; a family with no
journal record takes its eligible or uncertain preprint records; a family with neither takes its
eligible or uncertain records of kind `other`. A family with a registry record is an eligible
family. The eligible or uncertain preprint records of a family whose registry
record is a journal record are dating-only: their verified claims date the family's pairs
(scripts/novelty.py) and never enter the registry.

Window, from the family date: `confirmatory` (first public 2019-01-01 to 2025-12-31), `update`
(from 2026-01-01), `outside` (before 2019).

Outputs in --out: families.json (families, links with their rule);
families_meta.json (per eligible family: first public date, window, eligibility decision,
`also_tissue_or_csf`, extraction status, whether a fuzzy link joins it, registry claim and pair
counts); record_dates.json; registry_claims.jsonl and dating_claims.jsonl (confirmatory
window); registry_claims_update.jsonl and dating_claims_update.jsonl (update set);
registry_assembly.json (records left out by reason, `pair_ambiguous` by reason, counts); and,
when manual codes are given, registry_claims_without_manual_coding.jsonl (and `_update`), the
same claims with every dataset name as written.

Each input takes one file per screening set (the search and each citation-chasing round); the
files of one kind are read as one.

Manual dataset codes (`--manual-codes`): a dataset name the automatic mapping left
`release_ambiguous` or `unmatched` and that was coded by reading the paper
(scripts/manual_dataset_coding.py) is replaced by the dictionary row it was coded to; the claim
lists the replacement. The registry is assembled once without codes, to write the coding queue,
and once with them.

Smoke window (`--smoke-label`, for a run made before the freeze on records first public before
2019; no registered run uses it). The families of such a run all have the window `outside`, so
the registry and every table built from it would be empty. With a smoke label, a family first
public before 2019 takes the window `confirmatory`, so stages 4b to 6 run with content. The
switch refuses a label that does not start with `smoke_`, a record first public in 2019 or
later, and an output folder that is not `outputs/registry/<label>...`; `registry_assembly.json`
carries the label, and scripts/smoke_guard.py makes the later steps refuse to write the results
of a smoke registry under a name that does not start with it.

Usage: uv run scripts/assemble_registry.py --records <search_records.jsonl> [...]
           --decisions <...decisions.jsonl> [...] --extraction <sol_extraction_....jsonl> [...]
           --checks <claim_checks.jsonl> [...] [--manual-codes <manual_dataset_codes.csv>]
           [--smoke-label <label>] --out <dir>
"""

import argparse
import collections
import datetime
import json
import pathlib
from typing import Literal

from pydantic import BaseModel

from build_registry import (ManualCodes, PublicDate, RegistryClaim, canonical_inputs,
                            registry_claims_from_checks)
from dataset_relations import load_rows
from manual_dataset_coding import load_codes
from link_families import ELIGIBLE, Link, SearchRecord, family_dates, link
from smoke_guard import SMOKE_PREFIX, SmokeWindowError, check_smoke_folder

DECISION_ORDER = ("uncertain", "eligible_count_not_stated", "eligible")
WINDOW_START, WINDOW_END = 2019, 2025
Window = Literal["confirmatory", "update", "outside"]


class FamilyMeta(BaseModel):
    family_id: str
    first_public: PublicDate
    window: Window
    eligibility: str
    also_tissue_or_csf: bool
    extraction: Literal["ok", "extraction_failed"]
    fuzzy_linked: bool
    registry_records: list[str]
    dating_records: list[str]
    n_registry_claims: int = 0
    n_pairs: int = 0


class AssemblyError(Exception):
    """The inputs disagree: a record without an abstract has an eligibility decision."""


class Assembly(BaseModel):
    family_of: dict[str, str]
    links: list[Link]
    meta: dict[str, FamilyMeta]
    record_dates: dict[str, PublicDate]
    claims: dict[str, list[RegistryClaim]]
    dating_claims: dict[str, list[RegistryClaim]]
    report: dict


def window_of(date: PublicDate, smoke_window: bool = False) -> Window:
    """`smoke_window`: a date before 2019 takes `confirmatory` (a pre-freeze smoke run only);
    a date in 2019 or later raises."""
    year = date.value.year
    if smoke_window:
        if year >= WINDOW_START:
            raise SmokeWindowError(f"smoke window: a family first public {date.value}")
        return "confirmatory"
    if year < WINDOW_START:
        return "outside"
    return "confirmatory" if year <= WINDOW_END else "update"


def assemble(records: list[SearchRecord], decisions: dict[str, dict],
             extraction_status: dict[str, str], checks: list[dict],
             hgnc_uniprot: dict[str, frozenset[str]], collision: dict[str, frozenset[str]],
             drop_fuzzy_links: bool = False, include_other_types: bool = False,
             mondo_first: bool = False, manual: ManualCodes | None = None,
             smoke_window: bool = False) -> Assembly:
    """`drop_fuzzy_links` rebuilds the families without the fuzzy title–author links,
    `include_other_types` keeps records of kind `other`, and `mondo_first` takes the MONDO
    identifier of an outcome name shared by one MONDO term and EFO terms (three registered
    sensitivity analyses). `manual` holds the manually coded dataset names; the primary registry
    applies them and the sensitivity `without_manual_dataset_coding` does not. `smoke_window`
    (a pre-freeze smoke run only) refuses any record first public in 2019 or later and gives
    every family the window `confirmatory`."""
    if smoke_window:
        late = sorted(r.record_id for r in records if r.first_public.value.year >= WINDOW_START)
        if late:
            raise SmokeWindowError(f"smoke window: records first public in 2019 or later: "
                                   f"{late[:5]}")
    n_other = sum(r.kind == "other" for r in records)
    if not include_other_types:
        records = [r for r in records if r.kind != "other"]
    judged_without = sorted(r.record_id for r in records
                            if r.no_abstract and r.record_id in decisions)
    if judged_without:
        raise AssemblyError(f"records classed no_abstract have an eligibility decision: "
                            f"{judged_without[:5]}")
    n_no_abstract = sum(r.no_abstract for r in records)
    family_of, links = link(records)
    if drop_fuzzy_links:
        kept = [l for l in links if l.rule != "fuzzy_title_author"]
        parent = {r.record_id: r.record_id for r in records}

        def find(x: str) -> str:
            while parent[x] != x:
                x = parent[x]
            return x

        for l in kept:
            ra, rb = find(l.a), find(l.b)
            parent[max(ra, rb)] = min(ra, rb)
        family_of, links = {r.record_id: find(r.record_id) for r in records}, kept
    decision = {rid: d["decision"] for rid, d in decisions.items()}
    members: dict[str, list[SearchRecord]] = collections.defaultdict(list)
    for r in records:
        members[family_of[r.record_id]].append(r)
    # A record of kind `other` never dates a family that has a journal or preprint record.
    copies = {r.record_id for rs in members.values() if any(x.kind != "other" for x in rs)
              for r in rs if r.kind == "other"}
    dates = family_dates(records, family_of,
                         {rid: d for rid, d in decision.items() if rid not in copies})
    fuzzy = {family_of[l.a] for l in links if l.rule == "fuzzy_title_author"}
    meta: dict[str, FamilyMeta] = {}
    for fam, rs in sorted(members.items()):
        ok = [r for r in rs if decision.get(r.record_id) in ELIGIBLE]
        journals = [r for r in ok if r.kind == "journal"]
        # A record without an abstract adds nothing to its family: the registry record is
        # chosen among the records that have one.
        has_journal = any(r.kind == "journal" and not r.no_abstract for r in rs)
        has_preprint = any(r.kind == "preprint" and not r.no_abstract for r in rs)
        registry = journals if has_journal else [
            r for r in ok if r.kind == "preprint"] if has_preprint else ok
        if not registry:
            continue
        ids = sorted(r.record_id for r in registry)
        meta[fam] = FamilyMeta(
            family_id=fam, first_public=dates[fam],
            window=window_of(dates[fam], smoke_window),
            eligibility=min((decision[i] for i in ids), key=DECISION_ORDER.index),
            also_tissue_or_csf=any("also_tissue_or_csf" in decisions[i].get("flags", [])
                                   for i in ids),
            extraction="extraction_failed" if all(
                extraction_status.get(i) != "ok" for i in ids) else "ok",
            fuzzy_linked=fam in fuzzy, registry_records=ids,
            dating_records=sorted(r.record_id for r in ok if r.kind == "preprint")
            if has_journal else [])
    registry_of = {i: f for f, m in meta.items() for i in m.registry_records}
    dating_of = {i: f for f, m in meta.items() for i in m.dating_records}
    claims: dict[str, list[RegistryClaim]] = {"confirmatory": [], "update": [], "outside": []}
    dating: dict[str, list[RegistryClaim]] = {"confirmatory": [], "update": [], "outside": []}
    report: dict = {**({"smoke_window": True} if smoke_window else {}),
                    "records": len(records), "records_other_document_type": n_other,
                    "records_no_abstract": n_no_abstract,
                    "eligible_families_with_a_no_abstract_record": sum(
                        any(r.no_abstract for r in members[f]) for f in meta),
                    "other_document_types_included": include_other_types,
                    "families": len(members),
                    "eligible_families": len(meta),
                    "eligible_families_by_window": dict(collections.Counter(
                        m.window for m in meta.values())),
                    "claim_records_of_other_records": sum(
                        c["pmid"] not in registry_of and c["pmid"] not in dating_of
                        for c in checks)}
    for name, owner, target in (("registry", registry_of, claims), ("dating", dating_of, dating)):
        made, dropped, ambiguous = registry_claims_from_checks(
            [c for c in checks if c["pmid"] in owner], owner, hgnc_uniprot, collision,
            mondo_first, manual)
        for c in made:
            target[meta[c.family_id].window].append(c)
        report[name] = {"claim_records": sum(c["pmid"] in owner for c in checks),
                        "claims_with_a_pair": len(made), "left_out_by_reason": dropped,
                        "pair_ambiguous_by_reason": ambiguous,
                        "claims_with_a_manually_coded_dataset": sum(
                            bool(c.manual_dataset_codes) for c in made)}
    for window, cs in claims.items():
        per_family = collections.Counter(c.family_id for c in cs)
        pairs: dict[str, set] = collections.defaultdict(set)
        for c in cs:
            pairs[c.family_id].add((c.protein_id, c.outcome_id))
        for fam, m in meta.items():
            if m.window == window:
                m.n_registry_claims, m.n_pairs = per_family[fam], len(pairs[fam])
    record_dates = {r.record_id: r.first_public for r in records
                    if r.record_id in registry_of or r.record_id in dating_of}
    return Assembly(family_of=family_of, links=links, meta=meta, record_dates=record_dates,
                    claims=claims, dating_claims=dating, report=report)


def read_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def read_all(paths: list[pathlib.Path], key: str) -> list[dict]:
    """The rows of several files as one list; a `key` value in two rows raises."""
    rows = [r for p in paths for r in read_jsonl(p)]
    if len({r[key] for r in rows}) != len(rows):
        raise ValueError(f"{[str(p) for p in paths]}: a {key} occurs twice")
    return rows


def write(assembly: Assembly, out: pathlib.Path, smoke_label: str | None = None) -> None:
    if bool(assembly.report.get("smoke_window")) != (smoke_label is not None):
        raise SmokeWindowError("a smoke-window assembly is written with its smoke label, and "
                               "no other assembly is")
    if smoke_label is not None:
        check_smoke_folder(smoke_label, out)
    elif out.resolve().name.startswith(SMOKE_PREFIX):
        raise SmokeWindowError(f"{out} is a smoke folder; give --smoke-label")
    out.mkdir(parents=True, exist_ok=True)
    target = out / "registry_assembly.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; archive it before rerunning")
    families: dict[str, list[str]] = collections.defaultdict(list)
    for rid, fam in sorted(assembly.family_of.items()):
        families[fam].append(rid)
    (out / "families.json").write_text(json.dumps({
        "families": families, "links": [l.model_dump() for l in assembly.links]}, indent=1))
    (out / "families_meta.json").write_text(json.dumps(
        {f: m.model_dump(mode="json") for f, m in assembly.meta.items()}, indent=1))
    (out / "record_dates.json").write_text(json.dumps(
        {r: d.model_dump(mode="json") for r, d in assembly.record_dates.items()}, indent=1))
    for stem, source in (("registry_claims", assembly.claims),
                         ("dating_claims", assembly.dating_claims)):
        for window, suffix in (("confirmatory", ""), ("update", "_update")):
            (out / f"{stem}{suffix}.jsonl").write_text(
                "".join(c.model_dump_json() + "\n" for c in source[window]))
    target.write_text(json.dumps(
        {"written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
         **({"smoke_label": smoke_label} if smoke_label is not None else {}),
         **assembly.report}, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--decisions", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--extraction", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--checks", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--manual-codes", type=pathlib.Path,
                    help="the manual dataset codes (scripts/manual_dataset_coding.py)")
    ap.add_argument("--smoke-label",
                    help="before the freeze only: records first public before 2019 take the "
                         "window `confirmatory`; --out must be outputs/registry/<label>...")
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    smoke = a.smoke_label is not None
    if smoke:
        check_smoke_folder(a.smoke_label, a.out)
    records = [SearchRecord.model_validate(r) for r in read_all(a.records, "record_id")]
    decisions = {d["pmid"]: d for d in read_all(a.decisions, "pmid")}
    status = {r["pmid"]: r["status"] for r in read_all(a.extraction, "pmid")}
    manual = load_codes(a.manual_codes, load_rows())[0] if a.manual_codes else None
    assembly = assemble(records, decisions, status, read_all(a.checks, "claim_record_id"),
                        *canonical_inputs(), manual=manual, smoke_window=smoke)
    write(assembly, a.out, a.smoke_label)
    if manual:
        # The same registry without the codes, for the sensitivity analysis of the joins.
        plain = assemble(records, decisions, status, read_all(a.checks, "claim_record_id"),
                         *canonical_inputs(), smoke_window=smoke)
        for window, suffix in (("confirmatory", ""), ("update", "_update")):
            (a.out / f"registry_claims_without_manual_coding{suffix}.jsonl").write_text(
                "".join(c.model_dump_json() + "\n" for c in plain.claims[window]))
    print(json.dumps(assembly.report, indent=1))


if __name__ == "__main__":
    main()
