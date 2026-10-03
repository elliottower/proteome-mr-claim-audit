# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""EpiGraphDB reference screen: each registry pair looked up in the frozen snapshot of
EpiGraphDB's pQTL MR resource (Zheng et al. 2020; scripts/pin_epigraphdb_pqtl.py, `mrres`
responses). The resource shares pQTL data with many of the papers; agreement with it is not
independent confirmation, and absence from it is never read as a null result. No model is
called.

Snapshot mapping. Each snapshot exposure name maps to a UniProt accession through the verifier's
protein tiers (approved symbol; approved name and UniProt protein names; alias and previous
symbols and names; first tier with a hit) and the registered HGNC-to-UniProt step
(scripts/canonical_ids.py); it is mapped when that gives exactly one accession. Each snapshot
outcome trait name is mapped by the first of four rules that gives exactly one canonical
identifier (`name_rule`):

    icd10_cross_reference  the name holds an ICD-10 code ("Diagnoses - main ICD10: K80
                           Cholelithiasis") that exactly one canonical term carries as an
                           equivalent cross-reference in the pinned MONDO file
                           (scripts/outcome_alias_completion.py `icd10_terms`)
    alias_table            the committed alias table of snapshot trait names
                           (verification/epigraphdb_trait_aliases.csv, resolved from a seed of
                           trait name and term label by scripts/build_outcome_aliases.py
                           --traits), each alias with its source, its rationale and its
                           relation to the term
    as_written             the verifier's outcome tiers on the name (the committed outcome
                           alias table; labels and exact synonyms; obsolete-label
                           replacements; related synonyms; first tier with a hit; the same
                           name variants as for an extracted outcome) and the
                           canonical-identifier rules
    after_last_colon       the same tiers on the text after the name's last ": " (the
                           snapshot's UK Biobank field names, such as "Non-cancer illness code
                           self-reported: asthma"), with a leading ICD-10 code removed

The cross-reference the pinned files assert comes first. A hand-written alias comes before the
label rules because it is written only where they give nothing or mislead: the snapshot's
"Serum creatinine (eGFRcrea)" is the glomerular filtration rate estimated from creatinine, and
its words alone would map it to serum creatinine. A name that no rule maps to one identifier is
`ambiguous` when a rule gave several and `unmapped` otherwise; no trait is forced to map. The
two mapping tables are committed
(verification/epigraphdb_protein_mapping.csv, verification/epigraphdb_trait_mapping.csv).

Alias relations. The primary join reads the aliases whose relation is `exact_equivalent` or
`normalized_equivalent`. A trait mapped through a `broader_proxy` or `derived_measurement` alias
is unmapped in the primary join and read in the sensitivity `proxy_trait_aliases_included`.

Sensitivity `names_as_written_only`: the screen with only the trait names that the label tiers
map as written (no ICD-10 rule, no after-colon rule, no alias table).

Direction of a returned estimate: `raises` when its beta is above 0, `lowers` when below 0, none
when beta is 0 or missing. A pair's returned records are the `mrres` estimates of every mapped
exposure–trait combination that maps to the pair; their direction is usable when at least one
record has a direction and all such records agree.

Class of a pair or of a claim record:

    mapping_failed                        the protein or the outcome maps to nothing in the
                                          snapshot
    no_returned_record                    both map, and the snapshot has no record for the pair
    present_same                          a usable returned direction equal to the direction
                                          under comparison
    present_opposite                      a usable returned direction opposite to it
    present_nondirectional_or_ambiguous   a returned record, and either the returned records
                                          have no usable direction or there is no direction to
                                          compare

The direction under comparison is, for a claim record, its verified `raises` or `lowers`
direction; for a pair, the one direction shared by its directional family–pair directions
(`_with_nonsignificant` read as its direction), and none when its families disagree or none is
directional. `tested_nonsignificant` is never used.

Outputs: pairs by class; claim records by class, cross-tabulated with `novelty_language` and
with the novelty class (scripts/novelty.py), and split by whether the claim's family names, for
the pair, a pQTL dataset that is one of the snapshot's own sources: a candidate row of any of
its pQTL names is marked `zheng2020_source` in verification/pqtl_row_attributes.csv (the five
source studies of Zheng et al. 2020 and its instrument set). Groups: `shared_pqtl_source`,
`other_pqtl_source` (every name matched, none of them such a row) and
`pqtl_not_stated_or_unmatched`.

Usage: uv run scripts/reference_screen.py --claims <registry_claims.jsonl>
           --novelty <novelty_claims.jsonl> --snapshot <snapshot_estimates.jsonl> --out <dir>
"""

import argparse
import collections
import csv
import datetime
import json
import pathlib
import re
from collections.abc import Iterable, Mapping

from pydantic import BaseModel

from build_outcome_aliases import EQUIVALENT_RELATIONS
from build_registry import DIRECTIONAL, RegistryClaim, build
from canonical_ids import canonical_outcomes, protein_accession
from dataset_relations import Row, load_rows
from verify_claims import OUTCOME_LEAD, OUTCOME_TAIL, compact, variants

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
PROTEIN_MAPPING = EXP / "verification" / "epigraphdb_protein_mapping.csv"
TRAIT_MAPPING = EXP / "verification" / "epigraphdb_trait_mapping.csv"
ROW_ATTRIBUTES = EXP / "verification" / "pqtl_row_attributes.csv"
SOURCE_GROUPS = ("shared_pqtl_source", "other_pqtl_source", "pqtl_not_stated_or_unmatched")
CLASSES = ("present_same", "present_opposite", "present_nondirectional_or_ambiguous",
           "no_returned_record", "mapping_failed")
Pair = tuple[str, str]
ICD10_CODE = re.compile(r"^[A-Z]\d{2}(?:\.\d+)?\s+")
ICD10_IN_NAME = re.compile(r"ICD10: ([A-Z]\d{2}(?:\.\d+)?)(?![A-Za-z0-9.])")
TRAIT_FIELDS = ("name_rule", "alias_relation", "source_ids", "canonical_ids", "canonical_id")


def first_tier(keys: set[str], tiers: list[dict[str, set[str]]]) -> tuple[list[str], int | None]:
    """Identifiers of the first tier any key hits, with the tier index."""
    for t, tier in enumerate(tiers):
        ids = set().union(*(tier.get(k, set()) for k in keys))
        if ids:
            return sorted(ids), t
    return [], None


def map_exposure(name: str, protein_tiers: list[dict[str, set[str]]],
                 hgnc_uniprot: Mapping[str, frozenset[str]]) -> dict:
    hgnc, tier = first_tier({compact(name)}, protein_tiers)
    acc, state, candidates = protein_accession(hgnc, dict(hgnc_uniprot))
    return {"name": name, "state": state, "tier": tier, "hgnc_ids": hgnc,
            "accession": acc, "candidate_accessions": candidates}


def after_last_colon(name: str) -> str | None:
    """The text after the name's last ": ", without a leading ICD-10 code; None when the name
    has no ": "."""
    if ": " not in name:
        return None
    return ICD10_CODE.sub("", name.rsplit(": ", 1)[1].strip()).strip() or None


def icd10_code(name: str) -> str | None:
    """The ICD-10 code a snapshot trait name states ("... ICD10: K80 Cholelithiasis"), or
    None."""
    m = ICD10_IN_NAME.search(name)
    return m.group(1) if m else None


def map_trait(name: str, outcome_tiers: list[dict[str, set[str]]],
              collision: Mapping[str, frozenset[str]],
              aliases: Mapping[str, Mapping[str, str]] | None = None,
              icd10: Mapping[str, frozenset[str]] | None = None) -> dict:
    """`aliases` maps a snapshot trait name to its row of the committed alias table (`term_id`,
    `alias_relation`); `icd10` an ICD-10 code to the canonical terms that carry it as an
    equivalent cross-reference."""
    def tiers(text: str) -> tuple[list[str], int | None]:
        keys = {compact(v) for v in variants(text, OUTCOME_LEAD, OUTCOME_TAIL)}
        keys |= {k + "measurement" for k in keys}
        return first_tier(keys, outcome_tiers)

    attempts: list[tuple[str, list[str], int | None, list[str]]] = []
    code = icd10_code(name)
    if icd10 and code and icd10.get(code):
        attempts.append(("icd10_cross_reference", [f"ICD10:{code}"], None, sorted(icd10[code])))
    relation = ""
    if aliases and name in aliases:
        ids = [aliases[name]["term_id"]]
        attempts.append(("alias_table", ids, None, canonical_outcomes(ids, dict(collision))))
    ids, tier = tiers(name)
    attempts.append(("as_written", ids, tier, canonical_outcomes(ids, dict(collision))))
    tail = after_last_colon(name)
    if tail:
        ids, tier = tiers(tail)
        attempts.append(("after_last_colon", ids, tier,
                         canonical_outcomes(ids, dict(collision))))
    rule, ids, tier, canon = next(
        (a for a in attempts if len(a[3]) == 1),
        next((a for a in attempts if a[3]), (None, [], None, [])))
    if rule == "alias_table":
        relation = aliases[name]["alias_relation"]
    state = "unmapped" if not canon else "mapped" if len(canon) == 1 else "ambiguous"
    return {"name": name, "state": state, "tier": tier, "name_rule": rule,
            "alias_relation": relation, "source_ids": ids, "canonical_ids": canon,
            "canonical_id": canon[0] if len(canon) == 1 else None}


def write_mapping(rows: list[dict], path: pathlib.Path, id_fields: tuple[str, ...]) -> None:
    fields = ["name", "state", "tier", *id_fields]
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in sorted(rows, key=lambda r: r["name"]):
            w.writerow({k: "|".join(r[k]) if isinstance(r[k], list) else
                        "" if r[k] is None else r[k] for k in fields})


def load_mapping(path: pathlib.Path, id_field: str, as_written_only: bool = False,
                 proxy_aliases: bool = False) -> dict[str, str | None]:
    """Snapshot name -> its single mapped identifier, or None. A trait mapped through a
    `broader_proxy` or `derived_measurement` alias is read only with `proxy_aliases` (the
    sensitivity `proxy_trait_aliases_included`). `as_written_only` keeps only the trait names
    mapped as written."""
    def read(r: dict) -> bool:
        if r["state"] != "mapped":
            return False
        if as_written_only:
            return r.get("name_rule") == "as_written"
        proxy = r.get("name_rule") == "alias_table" and r.get(
            "alias_relation") not in EQUIVALENT_RELATIONS
        return proxy_aliases or not proxy

    with path.open(newline="") as f:
        return {r["name"]: (r[id_field] or None) if read(r) else None
                for r in csv.DictReader(f)}


def load_trait_aliases(path: pathlib.Path) -> dict[str, dict[str, str]]:
    """Snapshot trait name -> its row of the committed alias table."""
    with path.open(newline="") as f:
        return {r["surface"]: r for r in csv.DictReader(f)}


class Snapshot:
    """The frozen snapshot keyed on canonical pairs."""

    def __init__(self, proteins: Mapping[str, str | None], traits: Mapping[str, str | None],
                 estimates: Iterable[dict]) -> None:
        self.proteins = {a for a in proteins.values() if a}
        self.outcomes = {o for o in traits.values() if o}
        directions: dict[Pair, set[str]] = collections.defaultdict(set)
        self.records = self.records_on_mapped_pairs = 0
        for e in estimates:
            self.records += 1
            acc, out = proteins.get(e["expID"]), traits.get(e["outID"])
            if acc and out:
                self.records_on_mapped_pairs += 1
                beta = e.get("beta")
                directions[(acc, out)].add(
                    "none" if beta is None or beta == 0 else "raises" if beta > 0 else "lowers")
        self.directions = dict(directions)

    def returned_direction(self, pair: Pair) -> str | None:
        dirs = self.directions.get(pair, set()) - {"none"}
        return next(iter(dirs)) if len(dirs) == 1 else None

    def classify(self, pair: Pair, direction: str | None) -> str:
        if pair[0] not in self.proteins or pair[1] not in self.outcomes:
            return "mapping_failed"
        if pair not in self.directions:
            return "no_returned_record"
        returned = self.returned_direction(pair)
        if returned is None or direction is None:
            return "present_nondirectional_or_ambiguous"
        return "present_same" if returned == direction else "present_opposite"


def claim_direction(c: RegistryClaim) -> str | None:
    return c.direction if c.direction_verified and c.direction in ("raises", "lowers") else None


class ClaimScreen(BaseModel):
    claim_record_id: str
    protein_id: str
    outcome_id: str
    direction_compared: str | None
    reference_class: str


def load_zheng_source_rows(path: pathlib.Path = ROW_ATTRIBUTES) -> frozenset[str]:
    with path.open(newline="") as f:
        return frozenset(r["dictionary_row"] for r in csv.DictReader(f)
                         if r["zheng2020_source"] == "yes")


def source_group(fp, zheng_rows: frozenset[str]) -> str:
    """Whether a family's pQTL names on a pair include a source of the snapshot."""
    if any(c in zheng_rows for m in fp.pqtl for c in m.candidates):
        return "shared_pqtl_source"
    if fp.pqtl and all(m.state in ("unique", "release_ambiguous") for m in fp.pqtl):
        return "other_pqtl_source"
    return "pqtl_not_stated_or_unmatched"


def screen(claims: list[RegistryClaim], snapshot: Snapshot, novelty: Mapping[str, dict],
           rows: list[Row], zheng_rows: frozenset[str] | None = None
           ) -> tuple[dict, list[ClaimScreen], dict[str, str]]:
    zheng_rows = load_zheng_source_rows() if zheng_rows is None else zheng_rows
    registry = build(claims, rows)
    pair_class = {}
    for pair, fams in registry.items():
        dirs = {DIRECTIONAL[fp.direction] for fp in fams.values() if fp.direction in DIRECTIONAL}
        pair_class[pair] = snapshot.classify(pair, next(iter(dirs)) if len(dirs) == 1 else None)
    records = [ClaimScreen(claim_record_id=c.claim_record_id, protein_id=c.protein_id,
                           outcome_id=c.outcome_id, direction_compared=claim_direction(c),
                           reference_class=snapshot.classify((c.protein_id, c.outcome_id),
                                                             claim_direction(c)))
               for c in claims]
    by_language: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    by_novelty: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    by_source: dict[str, collections.Counter] = {
        g: collections.Counter() for g in SOURCE_GROUPS}
    for c, r in zip(claims, records):
        n = novelty[r.claim_record_id]
        by_language[str(bool(n["novelty_language"])).lower()][r.reference_class] += 1
        by_novelty[n["novelty_class"]][r.reference_class] += 1
        fp = registry[(c.protein_id, c.outcome_id)][c.family_id]
        by_source[source_group(fp, zheng_rows)][r.reference_class] += 1

    def full(counter: Mapping[str, int]) -> dict[str, int]:
        return {k: counter.get(k, 0) for k in CLASSES}

    pairs = collections.Counter(pair_class.values())
    summary = {
        "snapshot_records": snapshot.records,
        "snapshot_records_on_mapped_pairs": snapshot.records_on_mapped_pairs,
        "snapshot_mapped_proteins": len(snapshot.proteins),
        "snapshot_mapped_outcomes": len(snapshot.outcomes),
        "pairs": len(pair_class),
        "pairs_by_class": full(pairs),
        "pairs_matched_to_snapshot": len(pair_class) - pairs["mapping_failed"],
        "claim_records": len(records),
        "claim_records_by_class": full(collections.Counter(r.reference_class for r in records)),
        "claim_records_by_novelty_language": {k: full(v) for k, v in sorted(by_language.items())},
        "claim_records_by_novelty_class": {k: full(v) for k, v in sorted(by_novelty.items())},
        "claim_records_by_shared_pqtl_source": {k: full(v) for k, v in by_source.items()},
    }
    return summary, records, {f"{p[0]}|{p[1]}": c for p, c in sorted(pair_class.items())}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims", type=pathlib.Path, required=True)
    ap.add_argument("--novelty", type=pathlib.Path, required=True)
    ap.add_argument("--snapshot", type=pathlib.Path, required=True,
                    help="one `mrres` estimate per line (expID, outID, beta)")
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    claims = [RegistryClaim.model_validate_json(l) for l in a.claims.read_text().splitlines()
              if l.strip()]
    novelty = {n["claim_record_id"]: n for n in map(json.loads, (
        l for l in a.novelty.read_text().splitlines() if l.strip()))}
    with a.snapshot.open() as f:
        snapshot = Snapshot(load_mapping(PROTEIN_MAPPING, "accession"),
                            load_mapping(TRAIT_MAPPING, "canonical_id"),
                            (json.loads(l) for l in f if l.strip()))
    summary, records, pair_class = screen(claims, snapshot, novelty, load_rows())
    result = {"claims_file": str(a.claims), "novelty_file": str(a.novelty),
              "snapshot_file": str(a.snapshot),
              "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
              **summary}
    a.out.mkdir(parents=True, exist_ok=True)
    target = a.out / "reference_screen.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; archive it before rerunning")
    (a.out / "reference_screen_claims.jsonl").write_text(
        "".join(r.model_dump_json() + "\n" for r in records))
    (a.out / "reference_screen_pairs.json").write_text(json.dumps(pair_class, indent=1))
    target.write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
