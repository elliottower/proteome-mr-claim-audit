# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Resolve the committed outcome-alias seed against the pinned ontology files.

`verification/outcome_alias_seed.csv` lists surface strings (clinical abbreviations and the
outcome names the pre-2019 development set failed to map) with the LABEL of the term each
stands for, the relation between the two (`alias_relation`), where the alias comes from
(`source`) and why it holds (`rationale`). The relation is one of:

    exact_equivalent       the same name up to spelling, case or word order
    normalized_equivalent  an abbreviation, a common or older name, a synonym, or the wording
                           of a data field, for the same concept
    broader_proxy          the term is broader or narrower than the name: a qualifier (age,
                           acuity, site, timing, fasting state, "and related conditions") is
                           dropped or added
    derived_measurement    the term is a quantity derived from, or standing for, the one named

Every seed row is a hand-written alias (`rule` `hand_alias` in the output); the equivalences
that the pinned files themselves assert are built by scripts/outcome_alias_completion.py.

This script looks every label up in the pinned Mondo and EFO files (the files and
releases named in reference/MANIFEST.json), follows `replaced_by` from an obsolete term to
its replacement, and writes `verification/outcome_aliases.csv` with the resolved identifier.
When a label names live terms from several ontologies, the first prefix in PRIORITY wins
(Mondo for diseases, then EFO, OBA, HP, Orphanet). A label that resolves to no live term, or to
more than one term of the winning prefix, raises: nothing is guessed.

The alias table is the only curated alias source for the outcome check in verify_claims.py;
beyond it, the check uses only the pinned files' labels and EXACT and RELATED synonyms.

`--traits` resolves a second seed the same way: `verification/epigraphdb_trait_alias_seed.csv`
lists the trait names of the EpiGraphDB snapshot that the label tiers do not map, each with the
label of the term it stands for, and gives `verification/epigraphdb_trait_aliases.csv`
(scripts/reference_screen.py). That table is read for snapshot trait names only, never for an
extracted outcome.

Usage: uv run scripts/build_outcome_aliases.py [--traits]
"""

import argparse
import csv
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
SEED = EXP / "verification" / "outcome_alias_seed.csv"
OUT = EXP / "verification" / "outcome_aliases.csv"
TRAIT_SEED = EXP / "verification" / "epigraphdb_trait_alias_seed.csv"
TRAIT_OUT = EXP / "verification" / "epigraphdb_trait_aliases.csv"
PRIORITY = ("MONDO", "EFO", "OBA", "HP", "Orphanet")
RELATIONS = ("exact_equivalent", "normalized_equivalent", "broader_proxy", "derived_measurement")
EQUIVALENT_RELATIONS = RELATIONS[:2]
SEED_FIELDS = ["surface", "target_label", "alias_relation", "source", "rationale"]
ALIAS_FIELDS = ["surface", "term_id", "term_label", "rule", "alias_relation", "source",
                "rationale"]
HAND_ALIAS = "hand_alias"


class AliasError(Exception):
    """A seed label resolves to no live term or to several."""


def canonical_id(raw: str) -> str:
    raw = raw.strip()
    m = re.fullmatch(r"http://purl\.obolibrary\.org/obo/([A-Za-z]+)_(\w+)", raw)
    if m:
        return f"{m.group(1)}:{m.group(2)}"
    m = re.fullmatch(r"[A-Za-z]+:([A-Za-z]+)_(\w+)", raw)
    return f"{m.group(1)}:{m.group(2)}" if m else raw


def load_terms(paths: list[pathlib.Path]) -> dict[str, dict]:
    terms: dict[str, dict] = {}
    for path in paths:
        cur: dict | None = None
        with path.open() as f:
            for line in f:
                line = line.rstrip("\n")
                if line.startswith("["):
                    cur = {"obsolete": False, "replaced_by": []} if line == "[Term]" else None
                elif cur is None:
                    continue
                elif line.startswith("id: "):
                    cur["id"] = canonical_id(line[4:])
                    terms.setdefault(cur["id"], cur)
                elif line.startswith("name: "):
                    cur["name"] = line[6:].strip()
                elif line.startswith("is_obsolete: true"):
                    cur["obsolete"] = True
                elif line.startswith("replaced_by: "):
                    cur["replaced_by"].append(canonical_id(line[13:]))
    return terms


def resolve(label: str, terms: dict[str, dict], by_name: dict[str, list[str]]) -> tuple[str, str]:
    ids = by_name.get(label.lower(), [])
    live = [i for i in ids if not terms[i]["obsolete"]]
    if not live:
        repl = {r for i in ids for r in terms[i]["replaced_by"]
                if r in terms and not terms[r]["obsolete"]}
        live = sorted(repl)
    for prefix in PRIORITY:
        pref = sorted({i for i in live if i.startswith(prefix + ":")})
        if pref:
            live = pref
            break
    if len(set(live)) != 1:
        raise AliasError(f"label {label!r} resolves to {sorted(set(live))} (ids seen {ids})")
    tid = live[0]
    return tid, terms[tid]["name"]


def search(terms: dict[str, dict], queries: list[str], limit: int = 25) -> dict[str, dict]:
    """For authoring a seed: per query, the live outcome terms whose label equals it (any case)
    and up to `limit` live labels that contain every word of it. Resource files only."""
    live = [(t["name"], tid) for tid, t in terms.items()
            if "name" in t and not t["obsolete"] and tid.startswith(tuple(p + ":" for p in PRIORITY))]
    out = {}
    for q in queries:
        words = q.lower().split()
        out[q] = {"exact": sorted(f"{tid} {name}" for name, tid in live
                                  if name.lower() == q.lower()),
                  "contains": sorted(f"{tid} {name}" for name, tid in live
                                     if all(w in name.lower() for w in words))[:limit]}
    return out


def build(seed: pathlib.Path, out: pathlib.Path, terms: dict[str, dict]) -> list[dict]:
    """Resolve every seed row's label and write the alias table."""
    by_name: dict[str, list[str]] = {}
    for tid, t in terms.items():
        if "name" in t:
            by_name.setdefault(t["name"].lower(), []).append(tid)
    with seed.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != SEED_FIELDS:
            raise AliasError(f"{seed.name}: columns must be {SEED_FIELDS}")
        rows = list(reader)
    if len({r["surface"] for r in rows}) != len(rows):
        raise AliasError(f"{seed.name}: a surface string is listed twice")
    resolved = []
    for r in rows:
        if r["alias_relation"] not in RELATIONS:
            raise AliasError(f"{seed.name}: {r['surface']!r} has relation "
                             f"{r['alias_relation']!r}; it must be one of {RELATIONS}")
        if not r["source"].strip() or not r["rationale"].strip():
            raise AliasError(f"{seed.name}: {r['surface']!r} needs a source and a rationale")
        tid, name = resolve(r["target_label"], terms, by_name)
        resolved.append({"surface": r["surface"], "term_id": tid, "term_label": name,
                         "rule": HAND_ALIAS, "alias_relation": r["alias_relation"],
                         "source": r["source"], "rationale": r["rationale"]})
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ALIAS_FIELDS)
        w.writeheader()
        w.writerows(resolved)
    return resolved


def pinned_terms(exp: pathlib.Path = EXP) -> dict[str, dict]:
    manifest = json.loads((exp / "reference" / "MANIFEST.json").read_text())
    return load_terms([exp / manifest["mondo"]["file"], exp / manifest["efo"]["file"]])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--traits", action="store_true",
                    help="resolve the EpiGraphDB snapshot trait seed instead of the outcome seed")
    a = ap.parse_args()
    seed, out = (TRAIT_SEED, TRAIT_OUT) if a.traits else (SEED, OUT)
    resolved = build(seed, out, pinned_terms())
    print(f"{out}: {len(resolved)} aliases")


if __name__ == "__main__":
    main()
