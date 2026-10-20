# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml==6.0.3", "pydantic>=2"]
# ///
"""Counts of C1 control candidates for the draft second registration of the release-resolution
follow-up (post-results planning; nothing here is registered or frozen). No model is called.
No candidate text, unit text or coder answer is written or printed: counts, record ids and
identifier types only.

Scope, stage A text: the pool of the stratified draw of Amendment 2 is read from the committed
output outputs/staged_design_pricing_2026-10-13.json (it was computed on the Modal volume).

Outside the scope: the frozen scanner (source_scanner_v2.controls over c1_controls.units, both
sealed, imported unchanged) is run over the full texts stored for Paper 1's manual coding
(experiments/02_claims_meta/outputs/manual_coding/2026-10-03/fulltext/pmid*.jsonl) of records
outside the 266 of the scope, as route R1 text. These are the stored texts only; the rest of
Paper 1's corpus outside the scope has not been retrieved.

Run with PYTHONPATH set to the two scripts folders:
    PYTHONPATH=experiments/03_release_resolution/scripts:experiments/02_claims_meta/scripts \
        uv run planning/release_resolution_v2_registration/candidate_count.py
"""

import collections
import json
import pathlib

import c1_controls as c1
import source_scanner_v2 as scanner

ROOT = pathlib.Path(__file__).resolve().parents[3]
RR = ROOT / "experiments/03_release_resolution"
P1 = ROOT / "experiments/02_claims_meta"
OUT = pathlib.Path(__file__).resolve().parents[1] / "outputs" / "candidate_count_2026-10-19.json"
PER_RECORD = 5


def capped(pool: list[dict], per_record: int) -> int:
    per = collections.Counter(c["record_id"] for c in pool)
    return sum(min(n, per_record) for n in per.values())


def main() -> None:
    patterns = json.loads((RR / "reference/c1_scanner_patterns_v2.json").read_text())
    mapper = scanner.Mapper(patterns, scanner.read_csv(RR / "reference/accession_releases.csv"),
                            scanner.read_csv(P1 / "dataset_dictionary.csv"))
    scope = set(json.loads((P1 / "outputs/release_resolution/availability_2026-10-08.json")
                           .read_text())["records"])
    corpus = set()
    for line in (P1 / "outputs/registry/2026-10-03_amended_primary_coded_a/registry_claims.jsonl"
                 ).read_text().splitlines():
        if line.strip():
            corpus.add(json.loads(line)["claim_record_id"].split(":")[0])
    folder = P1 / "outputs/manual_coding/2026-10-03/fulltext"
    record_of = {}
    for line in (folder / "fetch_status.jsonl").read_text().splitlines():
        if line.strip():
            s = json.loads(line)
            record_of[str(s["pmid"])] = s["record_id"]

    found = []
    texts = {"in_corpus": 0, "not_in_amended_primary_corpus": 0}
    for path in sorted(folder.glob("pmid*.jsonl")):
        rid = record_of[path.stem[4:]]
        if rid in scope:
            continue
        texts["in_corpus" if rid in corpus else "not_in_amended_primary_corpus"] += 1
        body = json.loads(path.read_text().splitlines()[0])["body"]
        units = c1.units(rid, [{"route": "R1", "text": body, "type": "XML"}])
        for m in scanner.controls(units, patterns, mapper):
            m["in_corpus"] = rid in corpus
            found.append(m)

    def summary(ms: list[dict]) -> dict:
        first = {}
        for c in sorted(ms, key=lambda c: (c["record_id"], c["identifier"], c["source_key"],
                                            c["unit_id"])):
            first.setdefault((c["record_id"], c["identifier"]), c)
        pool = list(first.values())
        return {"matches": len(ms), "record_identifier_pairs": len(pool),
                "records": len({c["record_id"] for c in pool}),
                "pairs_after_cap_of_5_per_record": capped(pool, PER_RECORD),
                "by_side": dict(collections.Counter(c["side"] for c in pool)),
                "by_kind": dict(collections.Counter(c["kind"] for c in pool)),
                "by_type": dict(collections.Counter(c["type"] for c in pool)),
                "expected_rows": len({c["expected_row"] for c in pool})}

    staged = json.loads((RR / "outputs/staged_design_pricing_2026-10-13.json").read_text())
    triples = staged["c1_candidate_triples"]
    draw = staged["stratified_draw"]
    result = {
        "note": "post-results planning for a draft second registration; counts only; no text "
                "of a source, unit or answer is written",
        "scope_stage_a_text": {
            "from": "outputs/staged_design_pricing_2026-10-13.json",
            "record_identifier_row_triples_in_stage_a_text": triples["full_text_only"] + triples["both"],
            "triples_supplement_only": triples["supplement_only"],
            "stratified_draw_of_amendment_2": draw["drawn"],
            "max_per_record_in_that_draw": max(draw["per_record"].values()),
            "reading": "the draw took every stage A candidate: the cap of 5 per record and the "
                       "maximum of 150 did not bind, so the pool is the 70 controls already used",
        },
        "outside_scope_stored_full_texts": {
            "texts_scanned": texts,
            "paper1_amended_primary_records": len(corpus),
            "paper1_records_outside_scope": len(corpus - scope),
            "all_stored": summary(found),
            "in_amended_primary_corpus": summary([m for m in found if m["in_corpus"]]),
        },
        "inputs": {"patterns_seed": patterns["draw"]["seed"],
                   "scanner": "experiments/03_release_resolution/scripts/source_scanner_v2.py",
                   "units": "experiments/03_release_resolution/scripts/c1_controls.py"},
    }
    if OUT.exists():
        raise FileExistsError(f"{OUT} exists; it is written once")
    OUT.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
