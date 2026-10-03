# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""Stage 5 joins of the committed registry to the pinned ontology, Reactome, assay-list,
EpiGraphDB and pleiotropic-locus resources, one after another: novelty, reference screen, hub
proteins, pathway enrichment and density, hierarchy relations, registry indices, registered
secondaries. No model is called.

Each analysis writes its result files and then calls `commit`; an analysis whose result file
already exists in the output directory is not rerun, so a stopped run resumes at the next
analysis. Result files are never overwritten.

Inputs (files of scripts/assemble_registry.py and scripts/claim_tags.py): registry_claims.jsonl,
dating_claims.jsonl, claim_tags.jsonl, record_dates.json, families_meta.json,
registry_claims_without_manual_coding.jsonl when manual dataset codes were applied,
families.json, registry_assembly.json, record_metadata.jsonl (scripts/record_metadata.py), and
the abstracts
(`pmid`, `abstract` per line; `pmid` holds the record id). Resources: `Resources` below, by
default the committed tables under verification/, the pinned Reactome file under inputs/ and
the `mrres` estimates of the frozen EpiGraphDB responses under derived/ (on the Modal volume;
scripts/biology_resource_tables.py).

Usage: uv run scripts/biology_joins.py --inputs <dir> --abstracts <abstracts.jsonl> --out <dir>
"""

import argparse
import collections
import datetime
import json
import pathlib
from collections.abc import Callable

from pydantic import BaseModel

from assay_backgrounds import load_lists
from author_lists import load_decisions
from author_lists import overrides as author_overrides
from build_registry import N_BOOT, SEED, build
from claim_tags import load_tags
from dataset_relations import load_rows
from eldjarn_pleiotropic_loci import load_list
from hierarchy_relations import recomputed, relations
from hub_proteins import hub_expectation, hubs
from novelty import claim_dates, classify, index, load_dates, read_claims
from ontology_graph import load_graph
from pathway_enrichment import attachment_records, load_attachments, load_reactome
from pathway_enrichment import run as pathway_run
from reference_screen import Snapshot, load_mapping, screen
from registry_indices import indices
from registry_secondaries import load_record_meta, secondaries
from therapeutic_areas import (all_areas_of, area_assignment, areas_of, load_areas,
                               load_names)

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
VERIFICATION = EXP / "verification"


class Resources(BaseModel):
    ontology_edges: pathlib.Path = VERIFICATION / "ontology_edges.csv"
    therapeutic_areas: pathlib.Path = VERIFICATION / "therapeutic_areas.csv"
    therapeutic_area_names: pathlib.Path = VERIFICATION / "therapeutic_area_names.csv"
    assay_lists: pathlib.Path = VERIFICATION / "platform_assay_lists.csv"
    attachments: pathlib.Path = VERIFICATION / "platform_assay_attachments.csv"
    author_lists: pathlib.Path = VERIFICATION / "author_supplied_lists.csv"
    reactome: pathlib.Path = EXP / "inputs" / "reactome" / "UniProt2Reactome.txt"
    snapshot_estimates: pathlib.Path = EXP / "derived" / "epigraphdb_mrres_estimates.jsonl"
    protein_mapping: pathlib.Path = VERIFICATION / "epigraphdb_protein_mapping.csv"
    trait_mapping: pathlib.Path = VERIFICATION / "epigraphdb_trait_mapping.csv"
    locus_list: pathlib.Path = VERIFICATION / "pleiotropic_loci_eldjarn2023_ST36.csv"


def jsonl(records: list[BaseModel]) -> str:
    return "".join(r.model_dump_json() + "\n" for r in records)


def run_all(inputs: pathlib.Path, abstracts: pathlib.Path, out: pathlib.Path,
            resources: Resources, commit: Callable[[], None] = lambda: None,
            window: str = "confirmatory", n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Run every analysis not yet written to `out`; return each analysis's summary."""
    suffix = "" if window == "confirmatory" else f"_{window}"
    claims = read_claims(inputs / f"registry_claims{suffix}.jsonl")
    dating = read_claims(inputs / f"dating_claims{suffix}.jsonl")
    tags = load_tags(inputs / "claim_tags.jsonl")
    meta = {f: m for f, m in json.loads((inputs / "families_meta.json").read_text()).items()
            if m["window"] == window}
    rows = load_rows()
    graph = load_graph(resources.ontology_edges)
    areas = load_areas(resources.therapeutic_areas)
    area_names = load_names(resources.therapeutic_area_names)
    out.mkdir(parents=True, exist_ok=True)
    header = {"inputs": str(inputs), "window": window, "claim_records": len(claims),
              "resources": {k: str(v) for k, v in resources.model_dump().items()}}
    summaries: dict[str, dict] = {}

    def disease_areas(outcome: str) -> frozenset[str]:
        return areas_of(outcome, areas, graph)[0]

    def step(name: str, compute: Callable[[], tuple[dict, dict[str, str]]]) -> None:
        target = out / f"{name}.json"
        if target.exists():
            summaries[name] = json.loads(target.read_text())
            return
        summary, files = compute()
        for file_name, text in files.items():
            (out / file_name).write_text(text)
        result = {**header, "written_utc": datetime.datetime.now(datetime.UTC).isoformat(
            timespec="seconds"), **summary}
        target.write_text(json.dumps(result, indent=1))
        commit()
        summaries[name] = result

    def novelty_step() -> tuple[dict, dict[str, str]]:
        dates = load_dates(inputs / "record_dates.json")
        records = classify(claims, tags, claim_dates(claims, dating, dates), graph)
        journal_only = classify(claims, tags, claim_dates(claims, [], dates), graph)
        return ({**index(records),
                 "sensitivity_claim_dates_from_registry_abstracts_only": index(journal_only)},
                {"novelty_claims.jsonl": jsonl(records)})

    def reference_step() -> tuple[dict, dict[str, str]]:
        novelty = {n["claim_record_id"]: n for n in map(json.loads, (
            l for l in (out / "novelty_claims.jsonl").read_text().splitlines() if l.strip()))}
        proteins = load_mapping(resources.protein_mapping, "accession")
        with resources.snapshot_estimates.open() as f:
            estimates = [json.loads(l) for l in f if l.strip()]
        snapshot = Snapshot(proteins, load_mapping(resources.trait_mapping, "canonical_id"),
                            estimates)
        summary, records, pairs = screen(claims, snapshot, novelty, rows)
        as_written = screen(claims, Snapshot(proteins, load_mapping(
            resources.trait_mapping, "canonical_id", as_written_only=True), estimates),
            novelty, rows)[0]
        with_proxies = screen(claims, Snapshot(proteins, load_mapping(
            resources.trait_mapping, "canonical_id", proxy_aliases=True), estimates),
            novelty, rows)[0]
        return {**summary, "sensitivity_names_as_written_only": as_written,
                "sensitivity_proxy_trait_aliases_included": with_proxies}, {
            "reference_screen_claims.jsonl": jsonl(records),
            "reference_screen_pairs.json": json.dumps(pairs, indent=1)}

    def hub_step() -> tuple[dict, dict[str, str]]:
        texts = {r["pmid"]: r["abstract"] for r in map(json.loads, (
            l for l in abstracts.read_text().splitlines() if l.strip()))}
        genes = load_list(resources.locus_list)
        records, summary = hubs(claims, tags, disease_areas, texts, genes)

        def variant(**kw) -> dict:
            recs, s = hubs(claims, tags, disease_areas, texts, genes, **kw)
            return {**s, "hub_proteins": [h.model_dump() for h in recs]}

        return {**summary, "area_names": area_names,
                "hub_proteins": [h.model_dump() for h in records],
                "expected_from_claim_volume": hub_expectation(claims, tags, disease_areas,
                                                              seed=seed),
                "sensitivity_null_result_claims_counted": variant(count_null=True),
                "sensitivity_distinct_therapeutic_areas": variant(distinct_areas=True),
                "sensitivity_family_pair_collapsed": {
                    **variant(collapse=True),
                    "expected_from_claim_volume": hub_expectation(
                        claims, tags, disease_areas, seed=seed, collapse=True)}}, {}

    def pathway_step() -> tuple[dict, dict[str, str]]:
        lists = load_lists(resources.assay_lists)
        pathways, names = load_reactome(resources.reactome)
        decisions = load_decisions(inputs, resources.author_lists)
        primary = author_overrides(decisions, "primary")
        attachments = load_attachments(resources.attachments, lists, overrides=primary)
        summary, table, density = pathway_run(claims, tags, rows, lists, attachments, pathways,
                                              names)
        summary["author_supplied_lists"] = decisions
        files = {"pathway_enrichment_rows.jsonl": jsonl(table),
                 "pathway_claim_density.jsonl": jsonl(density)}
        summary["background_level_by_dictionary_row"] = {
            r["dictionary_row"]: primary.get(r["dictionary_row"], (None, r["background_level"]))[1]
            for r in attachment_records(resources.attachments)}
        alternative = load_attachments(resources.attachments, lists, alternative=True,
                                       overrides=primary)
        whole_panel = load_attachments(resources.attachments, lists, whole_panel=True)
        variants = []
        if decisions["after_cutoff"]:
            variants.append(("author_supplied_lists_after_cutoff", load_attachments(
                resources.attachments, lists,
                overrides={**primary, **author_overrides(decisions, "after_cutoff")}), {}))
        for name, attached, kw in (*variants,
                ("any_candidate_row_attachment", attachments, {"any_row": True}),
                ("null_result_claims_counted", attachments, {"count_null": True}),
                ("alternative_assay_lists", alternative, {}),
                ("whole_panel_backgrounds", whole_panel, {})):
            s, t, _ = pathway_run(claims, tags, rows, lists, attached, pathways, names, **kw)
            summary[f"sensitivity_{name}"] = s
            files[f"pathway_enrichment_rows_{name}.jsonl"] = jsonl(t)
        plain = inputs / f"registry_claims_without_manual_coding{suffix}.jsonl"
        if plain.exists():
            s, t, _ = pathway_run(read_claims(plain), tags, rows, lists, attachments, pathways,
                                  names)
            summary["sensitivity_without_manual_dataset_coding"] = s
            files["pathway_enrichment_rows_without_manual_dataset_coding.jsonl"] = jsonl(t)
        return summary, files

    def hierarchy_step() -> tuple[dict, dict[str, str]]:
        rels = relations({(c.protein_id, c.outcome_id) for c in claims}, graph)
        summary = {"hierarchy_relations": len(rels),
                   "hierarchy_relations_by_distance": {
                       str(k): v for k, v in sorted(collections.Counter(
                           r.distance for r in rels).items())},
                   "pair_families": recomputed(claims, graph, rows, n_boot, seed)}
        return summary, {"hierarchy_relations.jsonl": jsonl(rels)}

    def indices_step() -> tuple[dict, dict[str, str]]:
        result = indices(claims, tags, rows, meta, lambda o: all_areas_of(o, areas, graph),
                         n_boot, seed)
        result["landscape"]["area_names"] = area_names
        assignments = {o: area_assignment(o, areas, graph)
                       for o in sorted({c.outcome_id for c in claims})}
        result["landscape"]["outcome_area_assignments"] = assignments
        inherited = [a for a in assignments.values() if a["assignment"] == "inherited"]
        result["landscape"]["outcomes_by_area_assignment"] = dict(sorted(collections.Counter(
            a["assignment"] for a in assignments.values()).items()))
        result["landscape"]["inherited_outcomes_by_ancestor_distance"] = {
            str(k): v for k, v in sorted(collections.Counter(
                a["ancestor_distance"] for a in inherited).items())}
        result["landscape"]["inherited_outcomes_with_several_equally_near_ancestors"] = sum(
            a["several_equally_near_ancestors"] for a in inherited)
        return result, {}

    def secondaries_step() -> tuple[dict, dict[str, str]]:
        missing = [n for n in ("families.json", "registry_assembly.json", "record_metadata.jsonl")
                   if not (inputs / n).exists()]
        if missing:
            raise FileNotFoundError(
                f"{inputs}: {missing} missing; scripts/assemble_registry.py writes the first "
                "two and scripts/record_metadata.py build the third")
        novelty = {n["claim_record_id"]: n for n in map(json.loads, (
            l for l in (out / "novelty_claims.jsonl").read_text().splitlines() if l.strip()))}
        families = json.loads((inputs / "families.json").read_text())["families"]
        report = json.loads((inputs / "registry_assembly.json").read_text())
        return secondaries(
            claims, tags, build(claims, rows), meta, lambda o: all_areas_of(o, areas, graph),
            families, load_record_meta(inputs / "record_metadata.jsonl"), novelty, report,
            n_boot=n_boot, seed=seed), {}

    step("novelty_index", novelty_step)
    step("reference_screen", reference_step)
    step("hub_proteins", hub_step)
    step("pathway_enrichment", pathway_step)
    step("hierarchy_tables", hierarchy_step)
    step("registry_indices", indices_step)
    step("registry_secondaries", secondaries_step)
    return summaries


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", type=pathlib.Path, required=True)
    ap.add_argument("--abstracts", type=pathlib.Path, required=True)
    ap.add_argument("--window", default="confirmatory", choices=["confirmatory", "update"])
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    summaries = run_all(a.inputs, a.abstracts, a.out, Resources(), window=a.window)
    print(json.dumps({k: {x: y for x, y in v.items() if not isinstance(y, (list, dict))}
                      for k, v in summaries.items()}, indent=1))


if __name__ == "__main__":
    main()
