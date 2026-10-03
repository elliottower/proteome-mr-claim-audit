# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Build the MONDO–EFO canonical-identifier collision table from the pinned releases.

A concept is in the table when the pinned files assert that a MONDO term and a term of the EFO
file (an `EFO:` term, or an `Orphanet:`/`HP:` term the EFO file carries) are the same concept,
by any of three cross-references:

    mondo_xref      a `xref:` line of the MONDO term to an `EFO:` term, or to an `Orphanet:` or
                    `HP:` term the EFO file carries, with source `MONDO:equivalentTo` (or
                    `MONDO:obsoleteEquivalent`, recorded and flagged)
    mondo_sssom     a `skos:exactMatch` row of MONDO's `mondo_exactmatch_efo.sssom.tsv`
    efo_xref        a `xref: MONDO:...` line of the term in the EFO file

MONDO terms that EFO imports under their own MONDO identifier are one identifier in both files
and are counted, not listed.

Canonical choice (registered rule: a Mondo term for diseases, an EFO term for non-disease
traits). The concept is a disease when its MONDO term descends, in the pinned MONDO, from
`disease` (MONDO:0000001) or `injury` (MONDO:0021178); the canonical identifier is then the MONDO
term. Otherwise (MONDO's `disease characteristic` and `disease susceptibility` branches) it is a
non-disease trait and the canonical identifier is the EFO-file term.

Conflicts, listed per row (pipe-separated); none changes the `canonical_id` column, which
records the rule. The registry (`canonical_ids.load_collision_table`) leaves rows flagged
`branch_disagreement` unmerged, each identifier its own key:

    efo_term_maps_to_multiple_mondo   the EFO-file term is equivalent to more than one live MONDO
                                      term; a record mapped to it gets several canonical IDs and
                                      is counted pair_ambiguous
    mondo_term_maps_to_multiple_efo   the MONDO term is equivalent to more than one live EFO-file
                                      term (only matters for non-disease rows)
    branch_disagreement               MONDO places the concept under disease or injury and EFO
                                      places its term only under measurement or phenotype, or
                                      MONDO places it outside disease and EFO under disease

A cross-reference whose MONDO or EFO-file term is obsolete in, or absent from, its pinned file
is not a collision: the verifier never returns an obsolete term, so only one identifier is live.
Such cross-references (most of MONDO's EFO exact matches, whose EFO terms EFO has obsoleted in
favor of the imported MONDO term) are counted by reason in the metadata and not listed.

Outputs: verification/mondo_efo_collision_table.csv and its metadata
verification/mondo_efo_collision_table.meta.json (input releases and sha256, counts).

Usage: uv run scripts/build_collision_table.py --sssom <path to mondo_exactmatch_efo.sssom.tsv>
(fetched from the Modal volume; inputs/README_MOVED_TO_MODAL.md)
"""

import argparse
import collections
import csv
import hashlib
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
OUT = EXP / "verification" / "mondo_efo_collision_table.csv"
META = EXP / "verification" / "mondo_efo_collision_table.meta.json"
SSSOM_SHA256 = "7f4e2c0e27e3657885b7032a97aaab0186365b62922308434ff88c8c308defb9"
MONDO_DISEASE_ROOTS = ("MONDO:0000001", "MONDO:0021178")
EFO_DISEASE = "EFO:0000408"
EFO_NON_DISEASE = ("EFO:0001444", "EFO:0000651", "HP:0000118")  # measurement, phenotype,
#                                                                 phenotypic abnormality
EFO_SIDE_PREFIXES = ("EFO:", "Orphanet:", "HP:")
FIELDS = ["mondo_id", "mondo_label", "efo_id", "efo_label", "sources", "mondo_branch",
          "efo_branch", "concept_class", "canonical_id", "conflicts"]


class CollisionError(Exception):
    """An input does not match its pinned checksum or cannot be read."""


def canonical_id(raw: str) -> str:
    raw = raw.strip()
    for pat in (r"http://purl\.obolibrary\.org/obo/([A-Za-z]+)_(\w+)",
                r"http://www\.ebi\.ac\.uk/efo/([A-Za-z]+)_(\w+)",
                r"http://www\.orpha\.net/ORDO/([A-Za-z]+)_(\w+)",
                r"[A-Za-z]+:([A-Za-z]+)_(\w+)"):
        m = re.fullmatch(pat, raw)
        if m:
            return f"{m.group(1)}:{m.group(2)}"
    return raw


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_obo(path: pathlib.Path) -> dict[str, dict]:
    """term ID -> {name, obsolete, is_a, xrefs: [(target, source annotation)]}."""
    terms: dict[str, dict] = {}
    cur: dict | None = None
    with path.open() as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("["):
                cur = {"name": "", "obsolete": False, "is_a": [], "xrefs": []} \
                    if line == "[Term]" else None
            elif cur is None:
                continue
            elif line.startswith("id: "):
                terms.setdefault(canonical_id(line[4:]), cur)
            elif line.startswith("name: "):
                cur["name"] = line[6:].strip()
            elif line.startswith("is_obsolete: true"):
                cur["obsolete"] = True
            elif line.startswith("is_a: "):
                cur["is_a"].append(canonical_id(line[6:].split()[0]))
            elif line.startswith("xref: "):
                body = line[6:]
                target = canonical_id(body.split()[0])
                src = re.search(r'\{(.*)\}', body)
                cur["xrefs"].append((target, src.group(1) if src else ""))
    return terms


def ancestors(tid: str, terms: dict[str, dict], memo: dict[str, frozenset[str]]
              ) -> frozenset[str]:
    if tid in memo:
        return memo[tid]
    memo[tid] = frozenset()  # cycle guard
    out: set[str] = set()
    for p in terms.get(tid, {}).get("is_a", ()):
        out.add(p)
        out |= ancestors(p, terms, memo)
    memo[tid] = frozenset(out)
    return memo[tid]


def mondo_branch(tid: str, mondo: dict[str, dict], memo: dict) -> str:
    if tid not in mondo:
        return "absent"
    if mondo[tid]["obsolete"]:
        return "obsolete"
    anc = ancestors(tid, mondo, memo) | {tid}
    if "MONDO:0000001" in anc:
        return "disease"
    if "MONDO:0021178" in anc:
        return "injury"
    if "MONDO:0021125" in anc:
        return "disease_characteristic"
    if "MONDO:0042489" in anc:
        return "disease_susceptibility"
    return "other"


def efo_branch(tid: str, efo: dict[str, dict], memo: dict) -> str:
    if tid not in efo:
        return "absent"
    if efo[tid]["obsolete"]:
        return "obsolete"
    anc = ancestors(tid, efo, memo) | {tid}
    if EFO_DISEASE in anc or "MONDO:0000001" in anc:
        return "disease"
    if "EFO:0001444" in anc:
        return "measurement"
    if anc & {"EFO:0000651", "HP:0000118"}:
        return "phenotype"
    return "other"


def collect_pairs(mondo: dict[str, dict], efo: dict[str, dict],
                  sssom_rows: list[dict]) -> dict[tuple[str, str], set[str]]:
    pairs: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for mid, t in mondo.items():
        if not mid.startswith("MONDO:"):
            continue
        for target, src in t["xrefs"]:
            # EFO: targets always; Orphanet:/HP: targets only when the EFO file carries them.
            if not (target.startswith("EFO:") or (target.startswith(EFO_SIDE_PREFIXES)
                                                  and target in efo)):
                continue
            if "MONDO:equivalentTo" in src:
                pairs[(mid, target)].add("mondo_xref")
            elif "MONDO:obsoleteEquivalent" in src:
                pairs[(mid, target)].add("mondo_xref_obsolete_equivalent")
    for r in sssom_rows:
        if r["predicate_id"] == "skos:exactMatch":
            pairs[(r["subject_id"], r["object_id"])].add("mondo_sssom")
    for eid, t in efo.items():
        if not eid.startswith(EFO_SIDE_PREFIXES):
            continue
        for target, _ in t["xrefs"]:
            if target.startswith("MONDO:"):
                pairs[(target, eid)].add("efo_xref")
    return pairs


def build_rows(mondo: dict[str, dict], efo: dict[str, dict],
               sssom_rows: list[dict]) -> tuple[list[dict], dict[str, int], int]:
    """Rows for cross-references with both terms live; counts of the others by reason; the
    number of distinct cross-referenced pairs."""
    pairs = collect_pairs(mondo, efo, sssom_rows)
    mm, em = {}, {}
    mb = {m: mondo_branch(m, mondo, mm) for m, _ in pairs}
    eb = {e: efo_branch(e, efo, em) for _, e in pairs}
    live = {(m, e) for m, e in pairs if mb[m] not in ("obsolete", "absent")
            and eb[e] not in ("obsolete", "absent")}
    mondo_per_efo: dict[str, set[str]] = collections.defaultdict(set)
    efo_per_mondo: dict[str, set[str]] = collections.defaultdict(set)
    for m, e in live:
        mondo_per_efo[e].add(m)
        efo_per_mondo[m].add(e)
    rows, excluded = [], collections.Counter()
    for (m, e), sources in sorted(pairs.items()):
        if (m, e) not in live:
            excluded[f"mondo_{mb[m]}" if mb[m] in ("obsolete", "absent")
                     else f"efo_{eb[e]}"] += 1
            continue
        disease = mb[m] in ("disease", "injury")
        conflicts = []
        if len(mondo_per_efo[e]) > 1:
            conflicts.append("efo_term_maps_to_multiple_mondo")
        if len(efo_per_mondo[m]) > 1:
            conflicts.append("mondo_term_maps_to_multiple_efo")
        if ((disease and eb[e] in ("measurement", "phenotype"))
                or (not disease and eb[e] == "disease")):
            conflicts.append("branch_disagreement")
        if "mondo_xref_obsolete_equivalent" in sources:
            conflicts.append("mondo_obsolete_equivalent")
        rows.append({"mondo_id": m, "mondo_label": mondo[m]["name"], "efo_id": e,
                     "efo_label": efo[e]["name"], "sources": "|".join(sorted(sources)),
                     "mondo_branch": mb[m], "efo_branch": eb[e],
                     "concept_class": "disease" if disease else "non_disease_trait",
                     "canonical_id": m if disease else e, "conflicts": "|".join(conflicts)})
    return rows, dict(excluded), len(pairs)


def read_sssom(path: pathlib.Path) -> list[dict]:
    with path.open() as f:
        lines = [l for l in f if not l.startswith("#")]
    return list(csv.DictReader(lines, delimiter="\t"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sssom", type=pathlib.Path, required=True)
    a = ap.parse_args()
    manifest = json.loads((EXP / "reference" / "MANIFEST.json").read_text())
    inputs = {k: EXP / manifest[k]["file"] for k in ("mondo", "efo")}
    for k, p in inputs.items():
        if sha256(p) != manifest[k]["sha256"]:
            raise CollisionError(f"{p}: sha256 differs from reference/MANIFEST.json")
    if sha256(a.sssom) != SSSOM_SHA256:
        raise CollisionError(f"{a.sssom}: sha256 differs from the pinned SSSOM (RELEASES.md)")
    mondo, efo = parse_obo(inputs["mondo"]), parse_obo(inputs["efo"])
    rows, excluded, n_pairs = build_rows(mondo, efo, read_sssom(a.sssom))
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    conflict_counts = collections.Counter(c for r in rows for c in r["conflicts"].split("|")
                                          if c)
    meta = {
        "inputs": {
            "mondo": {"file": manifest["mondo"]["file"], "release": manifest["mondo"]["release"],
                      "sha256": manifest["mondo"]["sha256"]},
            "efo": {"file": manifest["efo"]["file"], "release": manifest["efo"]["release"],
                    "sha256": manifest["efo"]["sha256"]},
            "mondo_exactmatch_efo_sssom": {
                "modal_volume_path":
                    "/02_claims_meta/inputs/mondo_v2026-09-01/mondo_exactmatch_efo.sssom.tsv",
                "sha256": SSSOM_SHA256}},
        "table": str(OUT.relative_to(EXP)),
        "table_sha256": sha256(OUT),
        "cross_referenced_pairs": n_pairs,
        "pairs_not_listed_one_side_not_live": excluded,
        "rows": len(rows),
        "distinct_mondo_ids": len({r["mondo_id"] for r in rows}),
        "distinct_efo_side_ids": len({r["efo_id"] for r in rows}),
        "by_concept_class": dict(collections.Counter(r["concept_class"] for r in rows)),
        "by_canonical_prefix": dict(collections.Counter(r["canonical_id"].split(":")[0]
                                                        for r in rows)),
        "by_sources": dict(collections.Counter(r["sources"] for r in rows)),
        "by_mondo_branch": dict(collections.Counter(r["mondo_branch"] for r in rows)),
        "by_efo_branch": dict(collections.Counter(r["efo_branch"] for r in rows)),
        "rows_with_any_conflict": sum(bool(r["conflicts"]) for r in rows),
        "conflicts": dict(conflict_counts),
        "mondo_terms_imported_by_efo_under_mondo_id": sum(
            1 for t in efo if t.startswith("MONDO:")),
    }
    META.write_text(json.dumps(meta, indent=1) + "\n")
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
