# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""Abstract–full-text concordance (secondary, descriptive). No model is called.

Inputs are verify_claims.py records for the abstracts and for the full texts of the same study
families (full texts extracted with the separate full-text prompt from the Europe PMC
open-access XML of the PubMed record whose abstract was extracted). Only records that entered the registry with one canonical
pair (one UniProt accession and one canonical outcome identifier, `canonical_ids.py`) take part.

Per abstract record, against the same family's full-text records on the same canonical pair:

    unmatched           no full-text record on the pair
    matched             full-text records on the pair with a compatible context, all sharing
                        one context key
    context_ambiguous   full-text records on the pair, but none with a compatible context, or
                        compatible records with more than one context key

A context is compatible when the two records have the same `claim_scope` and either the scope is
`overall` or one record's folded context key contains the other's. Direction agreement is
computed only over matched records whose abstract direction and every matched full-text
direction were verified by the verifier and are all equal (`agree`) or not (`disagree`).

Family status: `no_open_access_full_text`, `version_unmatched` (the open-access version is not
the version whose abstract was extracted), `extraction_failed`, or `extracted`. Outputs over
extracted families: the share of abstract claims matched to extracted body records;
context-ambiguous and unmatched counts; direction agreement among matched records; additional
extracted body claims (full-text canonical pairs with no abstract record in the family); dataset
names found only in full-text records; colocalization and replication reported in full-text
records; and the H2 (identical-release) and H2b (identical-or-overlapping) classifications
recomputed with each family's datasets taken from its abstract and full-text records together,
beside the abstract-only classifications in the same subset; they are descriptive and carry no
verdict. Span pinning shows that each full-text span occurs in the text; it does not show that
the extraction found every result.

Usage: uv run scripts/fulltext_concordance.py --abstract-checks <claim_checks.jsonl> [...]
           --fulltext-checks <claim_checks.jsonl of the full-text extraction>
           --fulltext-extraction <sol_fulltext_extraction_....jsonl>
           --status <fulltext_status.json> --families <families.json> --out <dir>
"""

import argparse
import collections
import datetime
import json
import pathlib

from build_registry import (build, canonical_inputs, pair_h2, pair_overlap,
                            registry_claims_from_checks)
from canonical_ids import canonical_pair
from dataset_relations import Row, load_rows

Status = str


def context_key(c: dict) -> str:
    return " ".join(f"{c['analysis_context_as_written']} | {c['subgroup_as_written']}"
                    .lower().split())


def compatible(a: dict, b: dict) -> bool:
    if a["claim_scope"] != b["claim_scope"]:
        return False
    if a["claim_scope"] == "overall":
        return True
    ka, kb = context_key(a), context_key(b)
    return ka in kb or kb in ka


Maps = tuple[dict[str, frozenset[str]], dict[str, frozenset[str]]]


def pair_of(c: dict, maps: Maps) -> tuple[str, str] | None:
    """The record's canonical pair, or None when it did not enter the registry or has no single
    pair."""
    if not c["enters_registry"]:
        return None
    return canonical_pair(c["protein_ids"], c["outcome_ids"], *maps)


def verified(c: dict) -> bool:
    return c["direction_verification_state"] == "agrees" and c["direction"] in (
        "raises", "lowers", "reported_nonsignificant_or_null")


def match_family(abstract: list[dict], fulltext: list[dict], maps: Maps) -> dict:
    ab = [(c, p) for c in abstract if (p := pair_of(c, maps))]
    ft = [(c, p) for c in fulltext if (p := pair_of(c, maps))]
    ft_by_pair = collections.defaultdict(list)
    for c, p in ft:
        ft_by_pair[p].append(c)
    rows = []
    for c, p in ab:
        same = ft_by_pair.get(p, [])
        comp = [f for f in same if compatible(c, f)]
        if not same:
            status = "unmatched"
        elif comp and len({context_key(f) for f in comp}) == 1:
            status = "matched"
        else:
            status = "context_ambiguous"
        direction = None
        if status == "matched" and verified(c) and all(verified(f) for f in comp):
            direction = "agree" if {f["direction"] for f in comp} == {c["direction"]} else (
                "disagree")
        rows.append({"claim_record_id": c["claim_record_id"], "pair": list(p),
                     "status": status, "direction": direction})
    ab_pairs = {p for _, p in ab}
    ab_names = {n for c in abstract for n in c["pqtl_datasets"] + c["outcome_datasets"]
                if n != "not_stated"}
    return {
        "records": rows,
        "additional_body_pairs": sorted(list(p) for p in {p for _, p in ft} - ab_pairs),
        "datasets_only_in_full_text": sorted(
            {n for c in fulltext for n in c["pqtl_datasets"] + c["outcome_datasets"]
             if n != "not_stated"} - ab_names),
        "colocalization_reported": sum(c.get("colocalization", "not_reported") != "not_reported"
                                       for c, _ in ft),
        "replication_reported": sum(c.get("replication", "not_reported") != "not_reported"
                                    for c, _ in ft),
    }


def concordance(abstract_checks: list[dict], fulltext_checks: list[dict],
                family_of_pmid: dict[str, str], family_status: dict[str, Status],
                rows: list[Row], maps: Maps) -> dict:
    """Population counts, per-family matches and the pooled descriptive outputs."""
    by_fam_ab = collections.defaultdict(list)
    by_fam_ft = collections.defaultdict(list)
    for c in abstract_checks:
        by_fam_ab[family_of_pmid[c["pmid"]]].append(c)
    for c in fulltext_checks:
        by_fam_ft[family_of_pmid[c["pmid"]]].append(c)
    extracted = sorted(f for f, s in family_status.items() if s == "extracted")
    per_family = {f: match_family(by_fam_ab[f], by_fam_ft[f], maps) for f in extracted}
    recs = [r for f in extracted for r in per_family[f]["records"]]
    status = collections.Counter(r["status"] for r in recs)
    direction = collections.Counter(r["direction"] for r in recs if r["direction"])

    # H2 in the extracted subset: abstract datasets only, then abstract and full-text together.
    sub_ab = [c for f in extracted for c in by_fam_ab[f]]
    sub_both = sub_ab + [c for f in extracted for c in by_fam_ft[f]]
    h2, h2b = {}, {}
    for label, checks in (("abstract_only", sub_ab), ("abstract_and_full_text", sub_both)):
        claims = registry_claims_from_checks(checks, family_of_pmid, *maps)[0]
        ab_pairs = {(c.protein_id, c.outcome_id) for c in registry_claims_from_checks(
            sub_ab, family_of_pmid, *maps)[0]}
        reg = {p: f for p, f in build(claims, rows).items() if p in ab_pairs}
        h2[label] = dict(collections.Counter(
            c for c in (pair_h2(f) for f in reg.values()) if c is not None))
        h2b[label] = dict(collections.Counter(
            c for c in (pair_overlap(f) for f in reg.values()) if c is not None))
    return {
        "population": dict(collections.Counter(family_status.values())),
        "abstract_records_in_extracted_families": len(recs),
        "record_status": dict(status),
        "share_of_abstract_claims_matched_to_extracted_body_records": (
            status["matched"] / len(recs) if recs else None),
        "direction_among_matched_verified": dict(direction),
        "additional_extracted_body_claims": sum(len(v["additional_body_pairs"])
                                                for v in per_family.values()),
        "families_with_datasets_only_in_full_text": sum(
            bool(v["datasets_only_in_full_text"]) for v in per_family.values()),
        "full_text_records_reporting_colocalization": sum(
            v["colocalization_reported"] for v in per_family.values()),
        "full_text_records_reporting_replication": sum(
            v["replication_reported"] for v in per_family.values()),
        "h2_within_extracted_subset": h2,
        "h2b_within_extracted_subset": h2b,
        "per_family": per_family,
    }


def family_statuses(fetch_status: dict[str, dict], extraction_status: dict[str, str],
                    window: str) -> dict[str, Status]:
    """The status of each eligible family of the window: a family whose full text was fetched is
    `extracted` when the full-text extraction of that record succeeded, else
    `extraction_failed`; every other family keeps its fetch status."""
    out = {}
    for fam, f in fetch_status.items():
        if f["window"] != window:
            continue
        if f["status"] != "fetched":
            out[fam] = f["status"]
        else:
            out[fam] = ("extracted" if extraction_status.get(f["full_text_record"]) == "ok"
                        else "extraction_failed")
    return out


def read_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--abstract-checks", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--fulltext-checks", type=pathlib.Path, required=True)
    ap.add_argument("--fulltext-extraction", type=pathlib.Path, required=True)
    ap.add_argument("--status", type=pathlib.Path, required=True)
    ap.add_argument("--families", type=pathlib.Path, required=True)
    ap.add_argument("--window", default="confirmatory", choices=["confirmatory", "update"])
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    family_of = {rid: fam for fam, rids in json.loads(a.families.read_text())["families"].items()
                 for rid in rids}
    statuses = family_statuses(
        json.loads(a.status.read_text())["families"],
        {r["pmid"]: r["status"] for r in read_jsonl(a.fulltext_extraction)}, a.window)
    abstract = [c for p in a.abstract_checks for c in read_jsonl(p)
                if family_of[c["pmid"]] in statuses]
    result = concordance(abstract, read_jsonl(a.fulltext_checks), family_of, statuses,
                         load_rows(), canonical_inputs())
    n = len(statuses)
    result = {"window": a.window, "eligible_families": n,
              "europe_pmc_open_access_rate": sum(
                  s in ("extracted", "extraction_failed") for s in statuses.values()) / n
              if n else None,
              "extraction_coverage": sum(s == "extracted" for s in statuses.values()) / n
              if n else None,
              "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
              **result}
    a.out.mkdir(parents=True, exist_ok=True)
    target = a.out / f"fulltext_concordance_{a.window}.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; archive it before rerunning")
    target.write_text(json.dumps(result, indent=1))
    print(json.dumps({k: v for k, v in result.items() if k != "per_family"}, indent=1))


if __name__ == "__main__":
    main()
