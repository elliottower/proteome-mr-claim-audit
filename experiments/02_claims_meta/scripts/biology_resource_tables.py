"""Build the resource tables of the stage 5 biology joins from the pinned files, and count what
the registered rules can reach in them. Resource files only: no claim, pair or registry record
is read. Run on Modal (scripts/modal_biology_joins.py::resource_tables).

Written to the output directory:

    ontology_edges.csv, ontology_edges.meta.json     scripts/ontology_graph.py
    outcome_aliases.csv                              scripts/build_outcome_aliases.py
    phenotype_cross_references.csv, .meta.json       scripts/outcome_alias_completion.py
    obsolete_label_replacements.csv, .meta.json      scripts/outcome_alias_completion.py
    platform_assay_lists.csv, .meta.json             scripts/assay_backgrounds.py
    epigraphdb_protein_mapping.csv                   scripts/reference_screen.py `map_exposure`
    epigraphdb_trait_mapping.csv                     scripts/reference_screen.py `map_trait`
    mrres_estimates.jsonl                            one `mrres` estimate per line (expID,
                                                     outID, beta, se, pvalue), from the frozen
                                                     API responses
    resource_tables.json                             the counts below

    therapeutic_areas.csv, therapeutic_area_names.csv  scripts/therapeutic_areas.py

Counts: therapeutic areas (the `disease` rows, the areas and the terms in each, and the share of
the live outcome terms of the pinned ontology files that have an area, in all, by ontology, and
under MONDO `human disease` and EFO `measurement`); Reactome (human rows, pathways, accessions); assay lists (sizes; background
proteins with a pathway; pathways kept by the 10–500 rule, per attached list and pooled);
EpiGraphDB (exposures and traits by mapping state, estimates, estimates on mapped pairs);
outcome names (how many labels and exact synonyms of the pinned ontologies give more than one
canonical identifier, before and after the rule that drops identifiers from other ontologies
beside a MONDO or EFO identifier, by the ontologies involved; how many give phenotype
identifiers only, and how many of those the phenotype cross-references complete); assay
backgrounds (per dictionary row: the level, the three counts its source states and the reviewed
accessions on its list).
"""

import collections
import csv
import hashlib
import json
import pathlib
import urllib.parse

from assay_backgrounds import build_lists, build_published, write_lists
from canonical_ids import (canonical_outcomes, load_collision_table, load_hgnc_uniprot,
                           outcome_candidates, phenotype_term, without_phenotype_xrefs)
from ontology_graph import (ONTOLOGIES, OntologyGraph, build_from_pinned, load_graph, parse_is_a,
                            write_edges)
from pathway_enrichment import (MAX_BACKGROUND, MIN_BACKGROUND, attachment_records,
                                load_attachments, load_reactome, proxy_coverage)
from build_outcome_aliases import EQUIVALENT_RELATIONS
from build_outcome_aliases import build as build_aliases
from build_outcome_aliases import pinned_terms
from outcome_alias_completion import (OBSOLETE_FIELDS, PHENOTYPE_FIELDS, icd10_terms,
                                      obsolete_label_replacements, phenotype_cross_references,
                                      stanzas, write_rows)
from platform_list_sources import load_sources
from reference_screen import (TRAIT_FIELDS, first_tier, load_trait_aliases, map_exposure,
                              map_trait, write_mapping)
from therapeutic_areas import (NOT_DISEASE_AREAS, all_areas_of, areas_of, build_table,
                               write_table)
from verify_claims import (build_outcome_index, build_protein_index, compact, label_index,
                           load_manifest)

HUMAN_DISEASE = "MONDO:0700096"
MEASUREMENT = "EFO:0001444"


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def descendants(graph: OntologyGraph, root: str) -> set[str]:
    seen: set[str] = set()
    stack = [root]
    while stack:
        for child in graph.children.get(stack.pop(), ()):
            if child not in seen:
                seen.add(child)
                stack.append(child)
    return seen


def ontology_tables(exp: pathlib.Path, out: pathlib.Path) -> dict:
    edges, meta = build_from_pinned(exp, exp / "verification" / "mondo_efo_collision_table.csv")
    write_edges(edges, out / "ontology_edges.csv")
    meta["ontology_edges_sha256"] = sha256(out / "ontology_edges.csv")
    (out / "ontology_edges.meta.json").write_text(json.dumps(meta, indent=1))
    return meta


def collision_with_xrefs(exp: pathlib.Path, out: pathlib.Path) -> dict[str, frozenset[str]]:
    """The committed collision table with the phenotype cross-references this job built."""
    return load_collision_table(exp / "verification" / "mondo_efo_collision_table.csv",
                                out / "phenotype_cross_references.csv")


def outcome_index(manifest: dict, out: pathlib.Path):
    """The verifier's outcome tiers with the alias and obsolete-label tables this job built."""
    return build_outcome_index(manifest, out / "outcome_aliases.csv",
                               out / "obsolete_label_replacements.csv")


def outcome_alias_tables(exp: pathlib.Path, out: pathlib.Path, manifest: dict) -> dict:
    """The outcome alias table from its seed, and the two tables of equivalences the pinned
    files assert (phenotype cross-references, obsolete-label replacements)."""
    resolved = build_aliases(exp / "verification" / "outcome_alias_seed.csv",
                             out / "outcome_aliases.csv", pinned_terms(exp))
    exact, _, names = label_index(manifest)
    collision = without_phenotype_xrefs(load_collision_table(
        exp / "verification" / "mondo_efo_collision_table.csv"))
    mondo = list(stanzas(exp / manifest["mondo"]["file"]))
    efo = list(stanzas(exp / manifest["efo"]["file"]))
    by_id: dict[str, dict] = {}
    for t in mondo + efo:
        by_id.setdefault(t["id"], t)
    labels = {tid: by_id[tid]["name"] for tid in names if tid in by_id}
    phenotype_rows, phenotype_counts = phenotype_cross_references(mondo, labels, collision)
    write_rows(out / "phenotype_cross_references.csv", PHENOTYPE_FIELDS, phenotype_rows)
    obsolete_rows, obsolete_counts = obsolete_label_replacements(efo, by_id, exact, set(names),
                                                                 compact)
    write_rows(out / "obsolete_label_replacements.csv", OBSOLETE_FIELDS, obsolete_rows)
    shas = {n: sha256(out / n) for n in ("outcome_aliases.csv", "phenotype_cross_references.csv",
                                         "obsolete_label_replacements.csv")}
    inputs = {k: manifest[k]["sha256"] for k in ("mondo", "efo")}
    (out / "phenotype_cross_references.meta.json").write_text(json.dumps(
        {"inputs_sha256": inputs, **phenotype_counts,
         "table_sha256": shas["phenotype_cross_references.csv"]}, indent=1))
    (out / "obsolete_label_replacements.meta.json").write_text(json.dumps(
        {"inputs_sha256": inputs, **obsolete_counts,
         "table_sha256": shas["obsolete_label_replacements.csv"]}, indent=1))
    return {"outcome_alias_rows": len(resolved),
            "outcome_aliases_by_relation": dict(sorted(collections.Counter(
                r["alias_relation"] for r in resolved).items())),
            "phenotype_cross_references": phenotype_counts,
            "obsolete_label_replacements": obsolete_counts, "sha256": shas}


def therapeutic_area_tables(exp: pathlib.Path, out: pathlib.Path, manifest: dict,
                            disease_rows, disease_file_sha256: str) -> dict:
    """The therapeutic-area table from the pinned Open Targets `disease` file, and its coverage
    of the live outcome terms of the pinned ontology files."""
    collision = load_collision_table(exp / "verification" / "mondo_efo_collision_table.csv")
    areas, names, counts = build_table(disease_rows, collision)
    write_table(areas, names, out / "therapeutic_areas.csv", out / "therapeutic_area_names.csv")
    live: set[str] = set()
    for name in ONTOLOGIES:
        terms, _ = parse_is_a(exp / manifest[name]["file"])
        live |= {c for t in terms for c in collision.get(t, frozenset({t}))}
    graph = load_graph(out / "ontology_edges.csv")

    def coverage(terms: set[str]) -> dict:
        direct = [areas.get(t, frozenset()) for t in terms]
        disease = [a - NOT_DISEASE_AREAS for a in direct]
        rules = collections.Counter(all_areas_of(t, areas, graph)[1] for t in terms)
        with_disease_area = sum(bool(areas_of(t, areas, graph)[0]) for t in terms)
        return {"terms": len(terms), "in_table": sum(t in areas for t in terms),
                "with_an_area": sum(bool(a) for a in direct),
                "with_a_disease_area": sum(bool(a) for a in disease),
                "share_with_an_area": sum(bool(a) for a in direct) / len(terms) if terms
                else None,
                "by_area_rule": dict(sorted(rules.items())),
                "with_a_disease_area_under_the_registered_rule": with_disease_area,
                "by_number_of_disease_areas": {str(k): v for k, v in sorted(
                    collections.Counter(len(a) for a in disease).items())}}

    under = {name: descendants(graph, root) & live
             for name, root in (("human_disease", HUMAN_DISEASE), ("measurement", MEASUREMENT))}
    by_prefix = collections.defaultdict(set)
    for t in live:
        by_prefix[t.split(":", 1)[0]].add(t)
    per_area = collections.Counter(a for v in areas.values() for a in v)
    return {**counts, "disease_file_sha256": disease_file_sha256,
            "areas_by_terms": [{"area_id": a, "name": names[a], "terms": per_area[a],
                                "disease_area": a not in NOT_DISEASE_AREAS}
                               for a in sorted(names, key=lambda a: -per_area[a])],
            "not_disease_areas_present": sorted(NOT_DISEASE_AREAS & set(names)),
            "not_disease_areas_missing": sorted(NOT_DISEASE_AREAS - set(names)),
            "coverage_live_outcome_terms": coverage(live),
            "coverage_by_prefix": {k: coverage(v) for k, v in sorted(by_prefix.items())},
            "coverage_under": {k: coverage(v) for k, v in under.items()},
            "therapeutic_areas_sha256": sha256(out / "therapeutic_areas.csv"),
            "therapeutic_area_names_sha256": sha256(out / "therapeutic_area_names.csv")}


def assay_and_pathway_tables(exp: pathlib.Path, out: pathlib.Path, reviewed: frozenset[str],
                             manifest: dict, hgnc_uniprot: dict[str, frozenset[str]]) -> dict:
    lists, meta = build_lists(exp / "inputs" / "platform_assays", reviewed)
    protein_tiers, _ = build_protein_index(manifest)

    def symbol_accessions(symbol: str) -> frozenset[str]:
        hgnc, _ = first_tier({compact(symbol)}, protein_tiers)
        return frozenset().union(*(hgnc_uniprot.get(h, frozenset()) for h in hgnc))

    published, published_meta = build_published(
        exp / "inputs" / "platform_assays_published",
        load_sources(exp / "verification" / "platform_list_sources.csv"), reviewed,
        symbol_accessions)
    clash = sorted(set(lists) & set(published))
    if clash:
        raise ValueError(f"published list ids already pinned: {clash}")
    lists, meta = {**lists, **published}, {**meta, **published_meta}
    write_lists(lists, out / "platform_assay_lists.csv")
    meta_out = {"platform_assay_lists_sha256": sha256(out / "platform_assay_lists.csv"),
                "lists": meta}
    (out / "platform_assay_lists.meta.json").write_text(json.dumps(meta_out, indent=1))
    reactome = exp / "inputs" / "reactome" / "UniProt2Reactome.txt"
    pathways, _ = load_reactome(reactome)
    annotated = frozenset().union(*pathways.values())
    table = exp / "verification" / "platform_assay_attachments.csv"
    attachments = load_attachments(table, lists, exp / "dataset_dictionary.csv")
    attached = sorted({a for a in attachments.values() if a})
    backgrounds = {a: lists[a] for a in attached}
    backgrounds["pooled"] = frozenset().union(*(lists[a] for a in attached))
    alternative = load_attachments(table, lists, exp / "dataset_dictionary.csv",
                                   alternative=True)
    whole_panel = load_attachments(table, lists, exp / "dataset_dictionary.csv",
                                   whole_panel=True)
    for label, variant in (("alternative", alternative), ("whole panel", whole_panel)):
        for row, cell in variant.items():
            if cell and cell != attachments[row]:
                backgrounds[f"{label}: {row}"] = lists[cell]
    backgrounds["pooled, whole panel"] = frozenset().union(
        *(lists[a] for a in whole_panel.values() if a))
    rows_out = {}
    for r in attachment_records(table):
        name, cell = r["dictionary_row"], attachments[r["dictionary_row"]]
        size = len(lists[cell]) if cell else 0
        rows_out[name] = {
            "background_level": r["background_level"], "assay_list": cell,
            "assay_reagents": r["assay_reagents"], "reported_targets": r["reported_targets"],
            "analysed_targets": r["analysed_targets"], "reviewed_accessions": size,
            "proxy_coverage_of_reported_targets": proxy_coverage(
                r["background_level"], size, r["reported_targets"]),
            "whole_panel_assay_list": whole_panel[name] if whole_panel[name] != cell else None,
            "whole_panel_reviewed_accessions": len(lists[whole_panel[name]])
            if whole_panel[name] and whole_panel[name] != cell else None}

    def kept(background: frozenset[str]) -> int:
        return sum(MIN_BACKGROUND <= len(m & background) <= MAX_BACKGROUND
                   for m in pathways.values())

    return {
        "reactome": {"file_sha256": sha256(reactome),
                     "human_rows_distinct_accession_pathway": sum(
                         len(m) for m in pathways.values()),
                     "pathways": len(pathways), "accessions": len(annotated),
                     "accessions_in_reviewed_uniprot": len(annotated & reviewed)},
        "assay_lists": {k: {"accessions": len(v), "with_a_pathway": len(v & annotated)}
                        for k, v in sorted(lists.items())},
        "attached_lists": {k: {"dictionary_rows": sorted(r for r, a in attachments.items()
                                                         if a == k),
                               "background": len(v), "with_a_pathway": len(v & annotated),
                               "pathways_kept_10_to_500": kept(v)}
                           for k, v in backgrounds.items()},
        "dictionary_rows_without_a_list": sorted(r for r, a in attachments.items() if not a),
        "backgrounds_by_dictionary_row": rows_out,
        "dictionary_rows_by_background_level": dict(sorted(collections.Counter(
            r["background_level"] for r in rows_out.values()).items())),
        "platform_assay_lists_sha256": meta_out["platform_assay_lists_sha256"],
    }


def epigraphdb_tables(exp: pathlib.Path, out: pathlib.Path, manifest: dict,
                      hgnc_uniprot: dict[str, frozenset[str]]) -> dict:
    snapshot = exp / "inputs" / "epigraphdb_pqtl"
    protein_tiers, _ = build_protein_index(manifest)
    outcome_tiers, _ = outcome_index(manifest, out)
    collision = collision_with_xrefs(exp, out)
    icd10 = icd10_terms(list(stanzas(exp / manifest["mondo"]["file"])),
                        without_phenotype_xrefs(collision))
    exposures = [r["expID"] for r in json.loads(
        (snapshot / "list_exposures.json").read_text())["results"]]
    traits = [r["outID"] for r in json.loads(
        (snapshot / "list_outcomes.json").read_text())["results"]]
    proteins = [map_exposure(n, protein_tiers, hgnc_uniprot) for n in exposures]
    resolved = build_aliases(exp / "verification" / "epigraphdb_trait_alias_seed.csv",
                             out / "epigraphdb_trait_aliases.csv", pinned_terms(exp))
    aliases = load_trait_aliases(out / "epigraphdb_trait_aliases.csv")
    not_traits = sorted(set(aliases) - set(traits))
    if not_traits:
        raise ValueError(f"alias seed rows that are not snapshot traits: {not_traits[:5]}")
    outcomes = [map_trait(n, outcome_tiers, collision, aliases, icd10) for n in traits]
    write_mapping(proteins, out / "epigraphdb_protein_mapping.csv", ("hgnc_ids", "accession"))
    write_mapping(outcomes, out / "epigraphdb_trait_mapping.csv", TRAIT_FIELDS)
    protein_of = {p["name"]: p["accession"] for p in proteins if p["state"] == "mapped"}
    mapped_with_proxies = {o["name"]: o["canonical_id"] for o in outcomes
                           if o["state"] == "mapped"}
    outcome_of = {n: c for n, c in mapped_with_proxies.items() if not any(
        o["name"] == n and o["name_rule"] == "alias_table"
        and o["alias_relation"] not in EQUIVALENT_RELATIONS for o in outcomes)}
    icd_coded = [o for o in outcomes if "ICD10: " in o["name"]]
    n = on_mapped = on_mapped_with_proxies = missing = 0
    pairs: set[tuple[str, str]] = set()
    mapped_pairs: set[tuple[str, str]] = set()
    signs: collections.Counter = collections.Counter()
    with (out / "mrres_estimates.jsonl").open("w") as f:
        for name in exposures:
            path = snapshot / "responses" / f"mrres__{urllib.parse.quote(name, safe='')}.json"
            if not path.exists():
                missing += 1
                continue
            for r in json.loads(path.read_text())["results"]:
                n += 1
                pairs.add((r["expID"], r["outID"]))
                beta = r.get("beta")
                signs["none" if beta is None or beta == 0 else "raises" if beta > 0
                      else "lowers"] += 1
                if r["expID"] in protein_of and r["outID"] in mapped_with_proxies:
                    on_mapped_with_proxies += 1
                if r["expID"] in protein_of and r["outID"] in outcome_of:
                    on_mapped += 1
                    mapped_pairs.add((protein_of[r["expID"]], outcome_of[r["outID"]]))
                f.write(json.dumps({k: r.get(k) for k in ("expID", "outID", "beta", "se",
                                                          "pvalue")}) + "\n")
    tier_names = {None: "none", 0: "tier_1", 1: "tier_2", 2: "tier_3", 3: "tier_4"}
    return {
        "exposures": len(exposures), "traits": len(traits),
        "exposures_by_state": dict(sorted(collections.Counter(
            p["state"] for p in proteins).items())),
        "exposures_mapped_by_tier": dict(sorted(collections.Counter(
            tier_names[p["tier"]] for p in proteins if p["state"] == "mapped").items())),
        "distinct_accessions": len(set(protein_of.values())),
        "traits_by_state": dict(sorted(collections.Counter(o["state"] for o in outcomes).items())),
        "traits_mapped_by_name_rule": dict(sorted(collections.Counter(
            o["name_rule"] for o in outcomes if o["state"] == "mapped").items())),
        "traits_mapped_by_tier": dict(sorted(collections.Counter(
            tier_names[o["tier"]] for o in outcomes if o["state"] == "mapped").items())),
        "distinct_canonical_outcomes": len(set(outcome_of.values())),
        "response_files_missing": missing, "estimates": n,
        "distinct_exposure_trait_pairs": len(pairs), "estimates_by_sign_of_beta": dict(signs),
        "estimates_on_mapped_pairs": on_mapped, "distinct_canonical_pairs": len(mapped_pairs),
        "traits_read_in_the_primary_join": len(outcome_of),
        "traits_mapped_through_a_proxy_alias": len(mapped_with_proxies) - len(outcome_of),
        "estimates_on_mapped_pairs_with_proxy_aliases": on_mapped_with_proxies,
        "traits_mapped_by_alias_relation": dict(sorted(collections.Counter(
            o["alias_relation"] for o in outcomes
            if o["state"] == "mapped" and o["name_rule"] == "alias_table").items())),
        "alias_rows_not_used_an_earlier_rule_maps_the_trait": sorted(
            o["name"] for o in outcomes if o["name"] in aliases
            and o["name_rule"] != "alias_table"),
        "icd10_coded_traits": len(icd_coded),
        "icd10_coded_traits_by_name_rule": dict(sorted(collections.Counter(
            str(o["name_rule"]) for o in icd_coded).items())),
        "mrres_estimates_sha256": sha256(out / "mrres_estimates.jsonl"),
        "trait_alias_rows": len(resolved),
        "traits_unmapped": sorted(o["name"] for o in outcomes if o["state"] == "unmapped"),
        "traits_ambiguous": sorted(o["name"] for o in outcomes if o["state"] == "ambiguous"),
        "trait_aliases_sha256": sha256(out / "epigraphdb_trait_aliases.csv"),
        "protein_mapping_sha256": sha256(out / "epigraphdb_protein_mapping.csv"),
        "trait_mapping_sha256": sha256(out / "epigraphdb_trait_mapping.csv"),
    }


def outcome_name_tables(exp: pathlib.Path, out: pathlib.Path, manifest: dict) -> dict:
    """Labels and exact synonyms (the verifier's second outcome tier, folded) by the number of
    canonical identifiers they give, and the names that give phenotype identifiers only."""
    exact = outcome_index(manifest, out)[0][1]
    collision = collision_with_xrefs(exp, out)
    plain = without_phenotype_xrefs(collision)
    phenotype_only = completed = 0
    completed_examples: list[str] = []
    for name in sorted(exact):
        candidates = outcome_candidates(sorted(exact[name]), plain)
        if candidates and not any(c.startswith(("MONDO:", "EFO:")) for c in candidates):
            phenotype_only += 1
            term = phenotype_term(candidates, collision)
            if term is not None:
                completed += 1
                if len(completed_examples) < 40:
                    completed_examples.append(f"{name}: {'|'.join(candidates)} -> {term}")

    def pattern(ids: list[str]) -> str:
        return "+".join(f"{p}x{n}" for p, n in sorted(collections.Counter(
            i.split(":", 1)[0] for i in ids).items()))

    before: collections.Counter = collections.Counter()
    after: collections.Counter = collections.Counter()
    examples: dict[str, list[str]] = collections.defaultdict(list)
    resolved = 0
    for name in sorted(exact):
        ids = sorted(exact[name])
        candidates, final = outcome_candidates(ids, collision), canonical_outcomes(ids, collision)
        if len(candidates) < 2:
            continue
        before[pattern(candidates)] += 1
        if len(final) == 1:
            resolved += 1
        else:
            after[pattern(final)] += 1
            if len(examples[pattern(final)]) < 25:
                examples[pattern(final)].append(f"{name}: {'|'.join(final)}")
    return {"names_with_no_mondo_or_efo_identifier": phenotype_only,
            "of_those_completed_by_a_phenotype_cross_reference": completed,
            "completed_examples": completed_examples,
            "names": len(exact), "names_with_several_candidates": sum(before.values()),
            "by_ontologies_before_the_rule": dict(sorted(before.items())),
            "resolved_to_one_mondo_or_efo_identifier": resolved,
            "still_ambiguous": sum(after.values()),
            "still_ambiguous_by_ontologies": dict(sorted(after.items())),
            "still_ambiguous_examples": dict(sorted(examples.items()))}


def run(exp: pathlib.Path, out: pathlib.Path, commit, disease_rows, disease_file: pathlib.Path
        ) -> dict:
    """Each table is written and committed before the next begins; a table whose summary is
    already in `out` is not rebuilt. `disease_rows` yields the rows of the pinned Open Targets
    `disease` file (`disease_file`) as dictionaries."""
    out.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    hgnc_uniprot = load_hgnc_uniprot(exp / manifest["hgnc"]["file"],
                                     exp / manifest["uniprot"]["file"])
    with (exp / manifest["uniprot"]["file"]).open(newline="") as f:
        reviewed = frozenset(r["Entry"] for r in csv.DictReader(f, delimiter="\t"))
    steps = {"ontology": lambda: ontology_tables(exp, out),
             "outcome_aliases": lambda: outcome_alias_tables(exp, out, manifest),
             "therapeutic_areas": lambda: therapeutic_area_tables(
                 exp, out, manifest, disease_rows(), sha256(disease_file)),
             "assay_lists_and_pathways": lambda: assay_and_pathway_tables(
                 exp, out, reviewed, manifest, hgnc_uniprot),
             "epigraphdb": lambda: epigraphdb_tables(exp, out, manifest, hgnc_uniprot),
             "outcome_names": lambda: outcome_name_tables(exp, out, manifest)}
    result = {"inputs": "resource files only; no claim, pair or registry record read",
              "reference_sha256": {k: v["sha256"] for k, v in manifest.items()}}
    for name, compute in steps.items():
        part = out / f"resource_tables.{name}.json"
        if not part.exists():
            part.write_text(json.dumps(compute(), indent=1))
            commit()
        result[name] = json.loads(part.read_text())
    (out / "resource_tables.json").write_text(json.dumps(result, indent=1))
    commit()
    return result
