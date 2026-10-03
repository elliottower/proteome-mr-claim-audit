# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""Hierarchy relations between registry pairs, and the registry recomputed over pair families.

Hierarchy relation. Two registry pairs of one protein whose canonical outcome terms stand in an
ancestor–descendant relation in the pinned ontology graph (scripts/ontology_graph.py) are
recorded once, with the narrower outcome, the broader outcome and the ontology distance (the
shortest is_a path). Seen from the pair on the narrower term the other pair is `claim_broader`;
seen from the pair on the broader term it is `claim_narrower`. Hierarchy relations are reported
apart and never set a primary result.

Pair family. An anchor pair with the registry pairs of the same protein whose outcome is a
one-step parent or a one-step child of the anchor's outcome; no transitive chains. Every
registry pair is an anchor, so a pair is a member of its own family and of each one-step
relative's family.

Recomputed registry. For each anchor, the claim records of every member pair are read as
records on the anchor pair, and the registered family–pair direction, contradicting-pair, H1 and
H2 rules of scripts/build_registry.py are applied unchanged. The counts are over anchors.

Usage: uv run scripts/hierarchy_relations.py --claims <registry_claims.jsonl>
           --ontology-edges <ontology_edges.csv> --out <dir>
"""

import argparse
import collections
import datetime
import json
import pathlib

from pydantic import BaseModel

from build_registry import N_BOOT, SEED, RegistryClaim, build, tables
from dataset_relations import Row, load_rows
from ontology_graph import OntologyGraph, load_graph

Pair = tuple[str, str]


class HierarchyRelation(BaseModel):
    protein_id: str
    narrower_outcome_id: str
    broader_outcome_id: str
    distance: int


def relations(pairs: set[Pair], graph: OntologyGraph) -> list[HierarchyRelation]:
    by_protein: dict[str, set[str]] = collections.defaultdict(set)
    for protein, outcome in pairs:
        by_protein[protein].add(outcome)
    out = []
    for protein, outcomes in sorted(by_protein.items()):
        for narrow in sorted(outcomes):
            ancestors = graph.ancestors(narrow)
            out += [HierarchyRelation(protein_id=protein, narrower_outcome_id=narrow,
                                      broader_outcome_id=broad, distance=ancestors[broad])
                    for broad in sorted(outcomes) if broad in ancestors]
    return out


def pair_families(pairs: set[Pair], graph: OntologyGraph) -> dict[Pair, list[Pair]]:
    """Anchor pair -> its members (the anchor first, then its one-step relatives)."""
    return {(protein, outcome): [(protein, outcome)] + sorted(
        (protein, o) for o in graph.one_step(outcome) if (protein, o) in pairs)
        for protein, outcome in sorted(pairs)}


def pair_family_claims(claims: list[RegistryClaim], graph: OntologyGraph
                       ) -> tuple[list[RegistryClaim], dict[Pair, list[Pair]]]:
    """Every claim record once per anchor whose pair family holds its pair, re-keyed to the
    anchor's outcome."""
    by_pair: dict[Pair, list[RegistryClaim]] = collections.defaultdict(list)
    for c in claims:
        by_pair[(c.protein_id, c.outcome_id)].append(c)
    families = pair_families(set(by_pair), graph)
    out = [c.model_copy(update={"outcome_id": anchor[1]})
           for anchor, members in families.items() for m in members for c in by_pair[m]]
    return out, families


def recomputed(claims: list[RegistryClaim], graph: OntologyGraph, rows: list[Row],
               n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    rekeyed, families = pair_family_claims(claims, graph)
    sizes = collections.Counter(len(m) for m in families.values())
    return {"anchors": len(families),
            "anchors_with_a_one_step_relative": sum(len(m) > 1 for m in families.values()),
            "pair_family_sizes": {str(k): v for k, v in sorted(sizes.items())},
            **tables(build(rekeyed, rows), n_boot, seed)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims", type=pathlib.Path, required=True)
    ap.add_argument("--ontology-edges", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    claims = [RegistryClaim.model_validate_json(l) for l in a.claims.read_text().splitlines()
              if l.strip()]
    graph = load_graph(a.ontology_edges)
    rels = relations({(c.protein_id, c.outcome_id) for c in claims}, graph)
    result = {"claims_file": str(a.claims), "ontology_edges_file": str(a.ontology_edges),
              "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
              "hierarchy_relations": len(rels),
              "hierarchy_relations_by_distance": {
                  str(k): v for k, v in sorted(collections.Counter(
                      r.distance for r in rels).items())},
              "pair_families": recomputed(claims, graph, load_rows())}
    a.out.mkdir(parents=True, exist_ok=True)
    target = a.out / "hierarchy_tables.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; archive it before rerunning")
    (a.out / "hierarchy_relations.jsonl").write_text(
        "".join(r.model_dump_json() + "\n" for r in rels))
    target.write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
