# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""Novelty language against earlier claims of the same pair in the registry. No model is called.

Claim date. A family's date for a canonical pair is the public date of its earliest abstract in
which the pair appears: the family's registry abstract, or a dating-only abstract of the same
family (its preprint version 1), whose claim records passed the same verification and mapping.
A family with one abstract dates its claims by that abstract.

Per registry claim record, against the claim dates of the other families with a registry claim
of the exact canonical pair (scripts/build_registry.py `novelty_class`): `earlier_in_registry`
when one is strictly earlier at the least precise resolution the two dates share;
`tied_or_unknown_order` when none is earlier and at least one ties; else
`no_earlier_in_registry`. `related_prior_claim` is set, apart, when another family has a
strictly earlier claim date on a pair of the same protein whose outcome is an ancestor or a
descendant of this outcome in the pinned ontology graph; it never sets `earlier_in_registry`.

Index: among claim records with `novelty_language` (scripts/claim_tags.py), the number and
proportion that are `earlier_in_registry`, with `tied_or_unknown_order` and `related_prior_claim`
beside it. The registry holds eligible 2019–2025 abstracts only, so the index says nothing about
novelty in the literature.

Usage: uv run scripts/novelty.py --claims <registry_claims.jsonl> --tags <claim_tags.jsonl>
           --dates <record_dates.json> --ontology-edges <ontology_edges.csv> --out <dir>
           [--dating-claims <dating_claims.jsonl>]
"""

import argparse
import collections
import datetime
import json
import pathlib
from collections.abc import Mapping

from pydantic import BaseModel

from build_registry import PublicDate, RegistryClaim, date_order, novelty_class, wilson
from claim_tags import ClaimTags, load_tags
from ontology_graph import OntologyGraph, load_graph

Pair = tuple[str, str]
RESOLUTION_ORDER = ("year", "month", "day")


class ClaimNovelty(BaseModel):
    claim_record_id: str
    family_id: str
    protein_id: str
    outcome_id: str
    claim_date: PublicDate
    novelty_language: bool
    novelty_class: str
    related_prior_claim: bool


def record_of(claim: RegistryClaim) -> str:
    return claim.claim_record_id.rsplit(":", 1)[0]


def claim_dates(claims: list[RegistryClaim], dating_claims: list[RegistryClaim],
                dates: Mapping[str, PublicDate]) -> dict[tuple[str, Pair], PublicDate]:
    """(family, pair) -> the earliest public date among the family's abstracts holding the
    pair, for the pairs the family claims in the registry."""
    in_registry = {(c.family_id, (c.protein_id, c.outcome_id)) for c in claims}
    held: dict[tuple[str, Pair], set[str]] = collections.defaultdict(set)
    for c in [*claims, *dating_claims]:
        key = (c.family_id, (c.protein_id, c.outcome_id))
        if key in in_registry:
            held[key].add(record_of(c))
    out = {}
    for key, records in held.items():
        ordered = sorted((dates[r] for r in records),
                         key=lambda d: (d.value, RESOLUTION_ORDER.index(d.resolution)))
        best = ordered[0]
        for d in ordered[1:]:
            if date_order(d, best) == "earlier":
                best = d
        out[key] = best
    return out


def classify(claims: list[RegistryClaim], tags: Mapping[str, ClaimTags],
             dated: Mapping[tuple[str, Pair], PublicDate], graph: OntologyGraph
             ) -> list[ClaimNovelty]:
    by_pair: dict[Pair, dict[str, PublicDate]] = collections.defaultdict(dict)
    by_protein: dict[str, set[str]] = collections.defaultdict(set)
    for (family, pair), d in dated.items():
        by_pair[pair][family] = d
        by_protein[pair[0]].add(pair[1])
    out = []
    for c in claims:
        pair = (c.protein_id, c.outcome_id)
        own = dated[(c.family_id, pair)]
        others = [d for f, d in by_pair[pair].items() if f != c.family_id]
        ancestors = graph.ancestors(c.outcome_id)
        related = [o for o in by_protein[c.protein_id]
                   if o in ancestors or c.outcome_id in graph.ancestors(o)]
        related_prior = any(date_order(d, own) == "earlier"
                            for o in related for f, d in by_pair[(c.protein_id, o)].items()
                            if f != c.family_id)
        out.append(ClaimNovelty(
            claim_record_id=c.claim_record_id, family_id=c.family_id, protein_id=c.protein_id,
            outcome_id=c.outcome_id, claim_date=own,
            novelty_language=tags[c.claim_record_id].novelty_language,
            novelty_class=novelty_class(own, others), related_prior_claim=related_prior))
    return out


def index(records: list[ClaimNovelty]) -> dict:
    worded = [r for r in records if r.novelty_language]
    by_class = collections.Counter(r.novelty_class for r in worded)
    n, k = len(worded), by_class["earlier_in_registry"]
    return {"claim_records": len(records),
            "claim_records_by_class": dict(sorted(collections.Counter(
                r.novelty_class for r in records).items())),
            "novelty_language_claims": n,
            "novelty_language_by_class": dict(sorted(by_class.items())),
            "novelty_language_earlier_in_registry": k,
            "novelty_language_earlier_in_registry_share": k / n if n else None,
            "wilson_descriptive": wilson(k, n),
            "novelty_language_tied_or_unknown_order": by_class["tied_or_unknown_order"],
            "novelty_language_related_prior_claim": sum(r.related_prior_claim for r in worded),
            "related_prior_claim_all_claims": sum(r.related_prior_claim for r in records),
            "imprecise_under_20": n < 20}


def load_dates(path: pathlib.Path) -> dict[str, PublicDate]:
    return {k: PublicDate.model_validate(v) for k, v in json.loads(path.read_text()).items()}


def read_claims(path: pathlib.Path) -> list[RegistryClaim]:
    return [RegistryClaim.model_validate_json(l) for l in path.read_text().splitlines()
            if l.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims", type=pathlib.Path, required=True)
    ap.add_argument("--dating-claims", type=pathlib.Path)
    ap.add_argument("--tags", type=pathlib.Path, required=True)
    ap.add_argument("--dates", type=pathlib.Path, required=True)
    ap.add_argument("--ontology-edges", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    claims = read_claims(a.claims)
    dating = read_claims(a.dating_claims) if a.dating_claims else []
    dated = claim_dates(claims, dating, load_dates(a.dates))
    records = classify(claims, load_tags(a.tags), dated, load_graph(a.ontology_edges))
    result = {"claims_file": str(a.claims),
              "dating_claims_file": str(a.dating_claims) if a.dating_claims else None,
              "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
              **index(records)}
    a.out.mkdir(parents=True, exist_ok=True)
    target = a.out / "novelty_index.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; archive it before rerunning")
    (a.out / "novelty_claims.jsonl").write_text(
        "".join(r.model_dump_json() + "\n" for r in records))
    target.write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
