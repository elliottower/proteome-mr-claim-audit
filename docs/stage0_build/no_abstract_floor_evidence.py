"""Abstract lengths of the records first public before 2019 that are held, for the floor of the
`no_abstract` rule (scripts/abstract_floor.py). Lengths only; no abstract is printed. A record
that PubMed dates in 2019 or later is left out and counted. For the 24 known items, which lie
in the window, only the lengths of the stored abstracts are computed.

Run from experiments/02_claims_meta:

    PYTHONPATH=scripts uv run --project ../.. python \
        ../../docs/stage0_build/no_abstract_floor_evidence.py
"""

import json
import pathlib
import statistics

from abstract_floor import ABSTRACT_FLOOR, abstract_length

EXP = pathlib.Path.cwd()
OUT = EXP.parent.parent / "docs" / "stage0_build" / "no_abstract_floor_evidence_2026-10-02.json"
SETS = {
    "development abstracts (prompts/dev_abstracts.jsonl)": "prompts/dev_abstracts.jsonl",
    "smoke search 2018-06": "outputs/screening_smoke/smoke_pre2019_20261002/screening_records.jsonl",
    "smoke chase round 1 (2018-06 seed)":
        "outputs/screening_smoke/smoke_pre2019_20261002/chase_round_1/screening_records.jsonl",
    "stage-0 smoke search 2018-11 to 2018-12":
        "outputs/screening_smoke/2026-10-01/screening_records.jsonl",
    "stage-0 chase round on two development papers":
        "outputs/screening_smoke/chase_round_1/screening_records.jsonl",
}
KNOWN = "outputs/known_items/known_items_abstracts_24.jsonl"


def rows(path: str) -> list[dict]:
    return [json.loads(l) for l in (EXP / path).read_text().splitlines() if l.strip()]


def bands(lengths: list[int]) -> dict:
    return {"empty": sum(n == 0 for n in lengths), "1-99": sum(0 < n < 100 for n in lengths),
            "100-199": sum(100 <= n < 200 for n in lengths),
            "200-399": sum(200 <= n < 400 for n in lengths),
            "400-599": sum(400 <= n < 600 for n in lengths),
            "600 or more": sum(n >= 600 for n in lengths)}


def main() -> None:
    if OUT.exists():
        raise FileExistsError(OUT)
    per_set, pooled, dated_2019 = {}, {}, []
    for name, path in SETS.items():
        lengths = []
        for r in rows(path):
            rid = r.get("record_id") or r["pmid"]
            if "first_public" in r and r["first_public"]["value"] >= "2019":
                dated_2019.append({"set": name, "record_id": rid,
                                   "first_public": r["first_public"]["value"]})
                continue
            lengths.append(abstract_length(r.get("abstract")))
            pooled[rid] = lengths[-1]
        nonzero = sorted(n for n in lengths if n)
        per_set[name] = {"records": len(lengths), **bands(lengths),
                         "shortest_nonempty": nonzero[:5],
                         "median_nonempty": statistics.median(nonzero) if nonzero else None}
    values = sorted(pooled.values())
    nonzero = [n for n in values if n]
    known = sorted(abstract_length(r["abstract"]) for r in rows(KNOWN))
    result = {
        "floor_characters": ABSTRACT_FLOOR,
        "length": "characters after runs of whitespace are collapsed and the ends stripped",
        "pooled_distinct_records_first_public_before_2019": {
            "records": len(values), **bands(values), "below_floor": sum(n < ABSTRACT_FLOOR
                                                                        for n in values),
            "shortest_nonempty": nonzero[:8], "median_nonempty": statistics.median(nonzero),
            "shortest_at_or_above_floor": min(n for n in values if n >= ABSTRACT_FLOOR)},
        "per_set": per_set,
        "records_dated_2019_by_pubmed_left_out": dated_2019,
        "known_items_lengths_only": {"records": len(known), "shortest": known[0],
                                     "longest": known[-1],
                                     "below_floor": sum(n < ABSTRACT_FLOOR for n in known)},
    }
    OUT.write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
