# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5", "rapidfuzz==3.14.6"]
# ///
"""The registered sensitivity analyses of the registry tables, each reported beside the primary.
No model is called. Every variant re-applies scripts/build_registry.py unchanged to a changed
set of claim records, families or edges:

    primary                              the confirmatory-window registry
    without_eligibility_uncertain        families judged `uncertain` removed
    without_also_tissue_or_csf           families flagged `also_tissue_or_csf` removed
    direction_unverified_included        claims that fail only direction verification enter
                                         with GPT-6.1 Sol's direction
    dictionary_match_failures_included   claims that fail the protein or outcome check enter
                                         when the verifier still returned identifiers for them
                                         (`protein_not_in_span`, `outcome_not_in_span`); a
                                         claim with no identifier cannot form a pair
    relation_ambiguous_included          records flagged `relation_ambiguous` enter
    overall_scope_only                   a family's records on a pair restricted to
                                         `claim_scope` `overall`, where it has any
    h1_without_with_nonsignificant       family–pair records of direction
                                         `raises_with_nonsignificant` or
                                         `lowers_with_nonsignificant` removed; read for H1 only
    without_context_unclear              family–pair records flagged `context_unclear` removed
    pair_families                        pair families in place of pairs
                                         (scripts/hierarchy_relations.py)
    without_fuzzy_family_links           families rebuilt without fuzzy title–author links
    h1_unclear_edges_as_independent      `unclear` edges counted as independent; H1 only
    first_public_2020_2025               families first public before 2020 removed
    without_count_not_stated             families classed `count_not_stated` removed
    all_document_types                   records of kind `other` (conference abstracts,
                                         dissertations, datasets, repository copies) kept; one
                                         linked to a journal or preprint record joins its family
    without_citation_chasing             families whose registry records were all added by
                                         citation chasing removed
    shared_names_mondo_first             an outcome name that gives exactly one MONDO identifier
                                         beside EFO identifiers takes the MONDO identifier
                                         (in the primary analysis it gives no pair)
    without_manual_dataset_coding        the manually coded dataset names are not applied: each
                                         name keeps its automatic mapping (the primary registry
                                         applies the codes; scripts/manual_dataset_coding.py)
    without_phenotype_cross_references   an outcome name that gives phenotype identifiers only
                                         keeps them (in the primary analysis it takes the
                                         disease term that cross-references them;
                                         scripts/canonical_ids.py)
    claim_specific_dataset_names_only    dataset names of records whose attribution is not
                                         `claim_specific` are read as `not_stated`, so a family's
                                         datasets on a pair are the names tied to that result
    tested_count_1000_or_more            families whose registry abstract states at least 1,000
                                         proteins tested (a family with no stated tested count
                                         is removed)

Every table also carries the protein-cluster bootstrap (scripts/build_registry.py), a
sensitivity of the intervals that never sets a verdict.

The drug-development sensitivity (`component_level_mapping` drugs) is in scripts/drug_joins.py
and the pooled-background pathway enrichment in scripts/pathway_enrichment.py.

Usage: uv run scripts/sensitivity_analyses.py --records <search_records.jsonl> [...]
           --decisions <...decisions.jsonl> [...] --extraction <sol_extraction_....jsonl> [...]
           --checks <claim_checks.jsonl> [...] --ontology-edges <ontology_edges.csv>
           [--chase-records <chase round search_records.jsonl> ...]
           [--manual-codes <manual_dataset_codes.csv>] --out <dir>
"""

import argparse
import datetime
import itertools
import json
import pathlib
from collections.abc import Callable

from assemble_registry import Assembly, FamilyMeta, assemble, read_all, read_jsonl
from canonical_ids import without_phenotype_xrefs
from build_registry import (DIRECTIONAL, N_BOOT, SEED, ManualCodes, PairH1, Registry,
                            RegistryClaim, build, canonical_inputs, edge, pair_bootstrap, tables,
                            wilson)
from manual_dataset_coding import load_codes
from dataset_relations import Row, load_rows
from hierarchy_relations import recomputed
from link_families import SearchRecord
from ontology_graph import OntologyGraph, load_graph
from smoke_guard import SmokeWindowError, check_smoke_label

NOT_IN_SPAN = ("protein_not_in_span", "outcome_not_in_span")
HIGH_FLOOR = 1000
WITH_NONSIGNIFICANT = ("raises_with_nonsignificant", "lowers_with_nonsignificant")


def keep_families(claims: list[RegistryClaim], meta: dict[str, FamilyMeta],
                  keep: Callable[[FamilyMeta], bool]) -> list[RegistryClaim]:
    return [c for c in claims if keep(meta[c.family_id])]


def direction_unverified_included(claims: list[RegistryClaim]) -> list[RegistryClaim]:
    return [c.model_copy(update={"direction_verified": True}) for c in claims]


def claim_specific_names_only(claims: list[RegistryClaim]) -> list[RegistryClaim]:
    """Dataset names that are not tied to the record's own result are read as not stated."""
    blank = {"pqtl_datasets": ("not_stated",), "outcome_datasets": ("not_stated",)}
    return [c if c.dataset_attribution == "claim_specific" else c.model_copy(update=blank)
            for c in claims]


def stated_tested_count(m: FamilyMeta, decisions: dict[str, dict]) -> int | None:
    """The largest tested protein count stated by a family's registry abstracts, or None."""
    counts = [decisions[r].get("n_proteins_tested") for r in m.registry_records
              if r in decisions]
    counts = [c for c in counts if c is not None]
    return max(counts) if counts else None


def overall_scope_only(claims: list[RegistryClaim]) -> list[RegistryClaim]:
    has_overall = {(c.family_id, c.protein_id, c.outcome_id) for c in claims
                   if c.claim_scope == "overall"}
    return [c for c in claims if c.claim_scope == "overall"
            or (c.family_id, c.protein_id, c.outcome_id) not in has_overall]


def without_family_pairs(claims: list[RegistryClaim], registry: Registry,
                         drop: Callable) -> list[RegistryClaim]:
    gone = {(pair, fam) for pair, fams in registry.items() for fam, fp in fams.items()
            if drop(fp)}
    return [c for c in claims if ((c.protein_id, c.outcome_id), c.family_id) not in gone]


def checks_entering(checks: list[dict], only_failure: tuple[str, ...]) -> list[dict]:
    """The verifier's records with those whose first failure is one of `only_failure`, and
    that pass every other entry check, marked as entering the registry."""
    out = []
    for c in checks:
        others_pass = (c["span_passes"] and c["evidence_type"] == "mr_estimate"
                       and (c["relation_ambiguous"] is not True
                            or "relation_ambiguous" in only_failure)
                       and all(check == "pass" or check in only_failure
                               for check in (c["protein_check"], c["outcome_check"])))
        if c["first_failure"] in only_failure and others_pass:
            c = {**c, "enters_registry": True, "first_failure": None}
        out.append(c)
    return out


def h1_unclear_as_independent(registry: Registry, n_boot: int, seed: int) -> dict:
    h1_set = []
    for fams in registry.values():
        d = sorted((f for f in fams.values() if f.direction in DIRECTIONAL),
                   key=lambda f: f.family_id)
        ind = agree = 0
        for a, b in itertools.combinations(d, 2):
            if edge(a, b) in ("independent", "unclear"):
                ind += 1
                agree += DIRECTIONAL[a.direction] == DIRECTIONAL[b.direction]
        if ind:
            h1_set.append(PairH1(pair=d[0].pair, families=[f.family_id for f in d],
                                 n_directional_families=len(d), independent_edges=ind,
                                 independent_agreeing=agree, all_edges=0, all_concordant=0,
                                 in_h1=True, agrees=agree == ind, liu_c=None))
    n, k = len(h1_set), sum(bool(p.agrees) for p in h1_set)
    edges = sum(p.independent_edges for p in h1_set)
    return {"h1_pairs": n, "h1_pairs_agreeing": k,
            "h1_pair_concordance": k / n if n else None,
            "h1_independent_or_unclear_edges": edges,
            "h1_edge_concordance": sum(p.independent_agreeing for p in h1_set) / edges
            if edges else None,
            "wilson_descriptive": wilson(k, n),
            "pair_bootstrap": pair_bootstrap({"_h1_set": h1_set, "_h2": []}, n_boot, seed),
            "imprecise_under_20_pairs": n < 20}


def run(records: list[SearchRecord], decisions: dict[str, dict],
        extraction_status: dict[str, str], checks: list[dict],
        hgnc_uniprot: dict[str, frozenset[str]], collision: dict[str, frozenset[str]],
        graph: OntologyGraph, rows: list[Row], n_boot: int = N_BOOT, seed: int = SEED,
        chased: frozenset[str] = frozenset(), manual: ManualCodes | None = None,
        smoke_window: bool = False) -> dict:
    """`chased` holds the ids of the screening records added by citation chasing; `manual`
    the manually coded dataset names, applied in every variant but one. `smoke_window` is the
    pre-freeze smoke switch of scripts/assemble_registry.py, passed to every assembly."""
    def assembled(these_checks: list[dict], **kw) -> Assembly:
        kw.setdefault("manual", manual)
        kw.setdefault("smoke_window", smoke_window)
        return assemble(records, decisions, extraction_status, these_checks, hgnc_uniprot,
                        collision, **kw)

    def table(claims: list[RegistryClaim]) -> dict:
        return {"claim_records": len(claims), **tables(build(claims, rows), n_boot, seed)}

    base = assembled(checks)
    claims, meta = base.claims["confirmatory"], base.meta
    registry = build(claims, rows)
    no_fuzzy = assembled(checks, drop_fuzzy_links=True)
    all_types = assembled(checks, include_other_types=True)
    out = {
        "primary": table(claims),
        "without_eligibility_uncertain": table(keep_families(
            claims, meta, lambda m: m.eligibility != "uncertain")),
        "without_also_tissue_or_csf": table(keep_families(
            claims, meta, lambda m: not m.also_tissue_or_csf)),
        "direction_unverified_included": table(direction_unverified_included(claims)),
        "dictionary_match_failures_included": table(
            assembled(checks_entering(checks, NOT_IN_SPAN)).claims["confirmatory"]),
        "relation_ambiguous_included": table(
            assembled(checks_entering(checks, ("relation_ambiguous",))).claims["confirmatory"]),
        "overall_scope_only": table(overall_scope_only(claims)),
        "h1_without_with_nonsignificant": table(without_family_pairs(
            claims, registry, lambda fp: fp.direction in WITH_NONSIGNIFICANT)),
        "without_context_unclear": table(without_family_pairs(
            claims, registry, lambda fp: fp.context_unclear)),
        "pair_families": recomputed(claims, graph, rows, n_boot, seed),
        "without_fuzzy_family_links": {
            "fuzzy_links_dropped": sum(l.rule == "fuzzy_title_author" for l in base.links),
            **table(no_fuzzy.claims["confirmatory"])},
        "h1_unclear_edges_as_independent": h1_unclear_as_independent(registry, n_boot, seed),
        "first_public_2020_2025": table(keep_families(
            claims, meta, lambda m: m.first_public.value.year >= 2020)),
        "without_count_not_stated": table(keep_families(
            claims, meta, lambda m: m.eligibility != "eligible_count_not_stated")),
        "all_document_types": {
            "records_other_document_type": all_types.report["records_other_document_type"],
            "eligible_families": all_types.report["eligible_families_by_window"].get(
                "confirmatory", 0),
            **table(all_types.claims["confirmatory"])},
        "without_citation_chasing": table(keep_families(
            claims, meta, lambda m: not set(m.registry_records) <= chased)),
        "shared_names_mondo_first": table(
            assembled(checks, mondo_first=True).claims["confirmatory"]),
        "without_manual_dataset_coding": table(
            assembled(checks, manual=None).claims["confirmatory"]),
        "without_phenotype_cross_references": table(assemble(
            records, decisions, extraction_status, checks, hgnc_uniprot,
            without_phenotype_xrefs(collision), manual=manual,
            smoke_window=smoke_window).claims["confirmatory"]),
        "claim_specific_dataset_names_only": table(claim_specific_names_only(claims)),
        "tested_count_1000_or_more": table(keep_families(
            claims, meta, lambda m: (stated_tested_count(m, decisions) or 0) >= HIGH_FLOOR)),
    }
    if smoke_window:
        out["smoke_window"] = True
    out["manual_dataset_coding"] = {
        "codes_given": len(manual or {}),
        "claim_records_with_a_manually_coded_dataset": sum(
            bool(c.manual_dataset_codes) for c in claims)}
    out["families_removed"] = {
        "eligibility_uncertain": sum(m.eligibility == "uncertain" and m.window == "confirmatory"
                                     for m in meta.values()),
        "also_tissue_or_csf": sum(m.also_tissue_or_csf and m.window == "confirmatory"
                                  for m in meta.values()),
        "first_public_before_2020": sum(m.first_public.value.year < 2020
                                        and m.window == "confirmatory" for m in meta.values()),
        "count_not_stated": sum(m.eligibility == "eligible_count_not_stated"
                                and m.window == "confirmatory" for m in meta.values()),
        "citation_chasing_only": sum(set(m.registry_records) <= chased
                                     and m.window == "confirmatory" for m in meta.values()),
        "tested_count_below_1000_or_not_stated": sum(
            (stated_tested_count(m, decisions) or 0) < HIGH_FLOOR and m.window == "confirmatory"
            for m in meta.values()),
    }
    out["claim_records_with_dataset_names_not_claim_specific"] = sum(
        c.dataset_attribution != "claim_specific" for c in claims)
    fps = [fp for fams in registry.values() for fp in fams.values()]
    out["family_pair_records_removed"] = {
        "with_nonsignificant": sum(fp.direction in WITH_NONSIGNIFICANT for fp in fps),
        "context_unclear": sum(fp.context_unclear for fp in fps)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--decisions", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--extraction", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--checks", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--ontology-edges", type=pathlib.Path, required=True)
    ap.add_argument("--chase-records", type=pathlib.Path, nargs="*", default=[],
                    help="search_records.jsonl of each citation-chasing round")
    ap.add_argument("--manual-codes", type=pathlib.Path,
                    help="the manual dataset codes (scripts/manual_dataset_coding.py)")
    ap.add_argument("--smoke-label",
                    help="before the freeze only (scripts/assemble_registry.py); --out must be "
                         "a folder whose name starts with the label")
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.smoke_label is not None:
        check_smoke_label(a.smoke_label)
        if not a.out.resolve().name.startswith(a.smoke_label):
            raise SmokeWindowError(f"smoke tables are written under a folder named "
                                   f"{a.smoke_label}..., not {a.out}")
    records = [SearchRecord.model_validate(r) for r in read_all(a.records, "record_id")]
    decisions = {d["pmid"]: d for d in read_all(a.decisions, "pmid")}
    status = {r["pmid"]: r["status"] for r in read_all(a.extraction, "pmid")}
    chased = frozenset(r["record_id"] for p in a.chase_records for r in read_jsonl(p))
    result = {"written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
              **run(records, decisions, status, read_all(a.checks, "claim_record_id"),
                    *canonical_inputs(),
                    load_graph(a.ontology_edges), load_rows(), chased=chased,
                    manual=load_codes(a.manual_codes, load_rows())[0] if a.manual_codes
                    else None, smoke_window=a.smoke_label is not None)}
    a.out.mkdir(parents=True, exist_ok=True)
    target = a.out / "sensitivity_tables.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; archive it before rerunning")
    target.write_text(json.dumps(result, indent=1))
    print(json.dumps({k: (v.get("estimates") if isinstance(v, dict) else v)
                      for k, v in result.items()}, indent=1, default=str))


if __name__ == "__main__":
    main()
