# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""The is_a graph of the pinned outcome ontologies, on canonical outcome identifiers.

Edges. Every unconditional `is_a` line of a live `[Term]` in the pinned MONDO and EFO files
(reference/MANIFEST.json), kept when child and parent are both outcome terms (MONDO, EFO, HP,
OBA, Orphanet, the prefixes the verifier maps to). `is_a` lines carrying a `gci_` qualifier are
conditional axioms and are not edges; `relationship:` lines (part_of and others) are not edges.
Each endpoint is replaced by its canonical identifier from the committed collision table (an
identifier outside the table is its own; an identifier with several canonical identifiers gives
one edge per identifier), and an edge whose two ends become the same identifier is dropped. The
graph is the union of the two files' edges.

    one-step parent / child   an edge of this graph
    ancestor / descendant     a path of edges; the ontology distance is the length of the
                              shortest path

The edges are written as CSV with columns `child`, `parent` (the file scripts/drug_joins.py
reads for `related_indication`).

Usage: uv run scripts/ontology_graph.py --out <dir>
"""

import argparse
import collections
import csv
import hashlib
import json
import pathlib
from collections.abc import Iterable, Mapping

from canonical_ids import load_collision_table
from verify_claims import OUTCOME_PREFIXES, canonical_id

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
COLLISION_TABLE = EXP / "verification" / "mondo_efo_collision_table.csv"
ONTOLOGIES = ("mondo", "efo")


class OntologyError(Exception):
    """A pinned file or a committed table is missing or inconsistent."""


def parse_is_a(path: pathlib.Path) -> tuple[set[str], set[tuple[str, str]]]:
    """(live outcome terms, (child, parent) edges between outcome terms) of one obo file."""
    live: set[str] = set()
    edges: set[tuple[str, str]] = set()
    tid: str | None = None
    parents: list[str] = []
    obsolete = in_term = False

    def flush() -> None:
        if in_term and tid and not obsolete and tid.startswith(OUTCOME_PREFIXES):
            live.add(tid)
            edges.update((tid, p) for p in parents if p.startswith(OUTCOME_PREFIXES))

    with path.open() as f:
        for line in f:
            if line.startswith("["):
                flush()
                in_term, tid, parents, obsolete = line.strip() == "[Term]", None, [], False
            elif line.startswith("id: "):
                tid = canonical_id(line[4:].strip())
            elif line.startswith("is_a: ") and "gci_" not in line:
                parents.append(canonical_id(line[6:].split()[0]))
            elif line.startswith("is_obsolete: true"):
                obsolete = True
        flush()
    return live, edges


def canonical_edges(edges: Iterable[tuple[str, str]], collision: Mapping[str, frozenset[str]]
                    ) -> set[tuple[str, str]]:
    out = set()
    for child, parent in edges:
        for c in collision.get(child, frozenset({child})):
            for p in collision.get(parent, frozenset({parent})):
                if c != p:
                    out.add((c, p))
    return out


class OntologyGraph:
    def __init__(self, edges: Iterable[tuple[str, str]]) -> None:
        parents: dict[str, set[str]] = collections.defaultdict(set)
        children: dict[str, set[str]] = collections.defaultdict(set)
        for child, parent in edges:
            parents[child].add(parent)
            children[parent].add(child)
        self.parents = {k: frozenset(v) for k, v in parents.items()}
        self.children = {k: frozenset(v) for k, v in children.items()}
        self._ancestors: dict[str, dict[str, int]] = {}

    def edges(self) -> list[tuple[str, str]]:
        return sorted((c, p) for c, ps in self.parents.items() for p in ps)

    def one_step(self, term: str) -> frozenset[str]:
        """The term's one-step parents and children."""
        return self.parents.get(term, frozenset()) | self.children.get(term, frozenset())

    def ancestors(self, term: str) -> dict[str, int]:
        """Ancestor -> shortest distance in edges."""
        if term not in self._ancestors:
            dist: dict[str, int] = {}
            frontier, d = [term], 0
            while frontier:
                d += 1
                nxt = []
                for t in frontier:
                    for p in self.parents.get(t, ()):
                        if p not in dist and p != term:
                            dist[p] = d
                            nxt.append(p)
                frontier = nxt
            self._ancestors[term] = dist
        return self._ancestors[term]

    def distance(self, descendant: str, ancestor: str) -> int | None:
        return self.ancestors(descendant).get(ancestor)


def write_edges(edges: Iterable[tuple[str, str]], path: pathlib.Path) -> None:
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["child", "parent"])
        w.writerows(sorted(edges))


def load_graph(path: pathlib.Path) -> OntologyGraph:
    with path.open(newline="") as f:
        return OntologyGraph((r["child"], r["parent"]) for r in csv.DictReader(f))


def file_sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_from_pinned(exp: pathlib.Path = EXP, collision_table: pathlib.Path = COLLISION_TABLE
                      ) -> tuple[set[tuple[str, str]], dict]:
    """Edges from the pinned files named in reference/MANIFEST.json, each re-hashed first."""
    manifest = json.loads((exp / "reference" / "MANIFEST.json").read_text())
    collision = load_collision_table(collision_table)
    raw: set[tuple[str, str]] = set()
    meta: dict = {"collision_table_sha256": file_sha256(collision_table), "files": {}}
    live: set[str] = set()
    for name in ONTOLOGIES:
        path = exp / manifest[name]["file"]
        if not path.exists():
            raise OntologyError(f"{manifest[name]['file']} missing; fetch it from the Modal "
                                "volume (inputs/README_MOVED_TO_MODAL.md)")
        if file_sha256(path) != manifest[name]["sha256"]:
            raise OntologyError(f"{manifest[name]['file']}: sha256 differs from the manifest")
        terms, edges = parse_is_a(path)
        live |= terms
        raw |= edges
        meta["files"][name] = {"release": manifest[name]["release"],
                               "sha256": manifest[name]["sha256"],
                               "live_outcome_terms": len(terms), "is_a_edges": len(edges)}
    edges = canonical_edges(raw, collision)
    meta["live_outcome_terms"] = len(live)
    meta["edges_before_canonical"] = len(raw)
    meta["edges"] = len(edges)
    return edges, meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    target = a.out / "ontology_edges.csv"
    if target.exists():
        raise FileExistsError(f"{target} exists; archive it before rerunning")
    edges, meta = build_from_pinned()
    write_edges(edges, target)
    meta["ontology_edges_sha256"] = file_sha256(target)
    (a.out / "ontology_edges.meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
