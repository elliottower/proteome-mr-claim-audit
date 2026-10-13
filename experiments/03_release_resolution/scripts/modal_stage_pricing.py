"""Modal wrapper for the pricing of the staged design and the stratified C1 draw
(scripts/stage_pricing.py); it reuses the image and volume of scripts/modal_coding_v2.py (sealed,
unchanged). No model is called; the output holds counts, public registry identifiers and unit
ids, never source text.

Run from experiments/03_release_resolution:

    modal run scripts/modal_stage_pricing.py::tests
    modal run scripts/modal_stage_pricing.py::price --out outputs/staged_design_pricing_2026-10-13.json
"""

import json
import pathlib

import modal

from modal_coding_v2 import CODING, E2, E3, LOCAL, MOUNT, PAPER1, ROOT, image, vol

app = modal.App("release-resolution-stage-pricing", image=image)

with image.imports():
    import collections
    import subprocess

    import c1_controls as c1
    import coding_packets as cp
    import coding_packets_v2 as cp2
    import coding_queue as q
    import stage_pricing as sp

RATIOS = {"pooled_full_text_ratios_of_the_plan": {"claude-sonnet-5-5": 2.62, "gpt-6.1-sol": 4.28},
          "preflight_ratios": {"claude-sonnet-5-5": 1.98, "gpt-6.1-sol": 3.11}}


@app.function(timeout=1800, cpu=2.0)
def tests_job() -> dict:
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                          "test_stage_pricing.py", "test_coding_packets_v2.py",
                          "test_c1_controls.py"], capture_output=True, text=True,
                         cwd=f"{E3}/tests")
    return {"returncode": run.returncode, "output": run.stdout + run.stderr}


def priced(recs: list[dict], prompt: int, carrying: bool) -> dict:
    out = {}
    for name, ratio in RATIOS.items():
        cost = cp2.layout_cost(recs, prompt, ratio, carrying)
        out[name] = {"at_1500_output_tokens": cost, "output_sensitivity": sp.with_outputs(cost)}
    return out


@app.function(volumes={str(MOUNT): vol}, timeout=6 * 3600, memory=32768)
def price_job(records: list[str], queue: dict) -> dict:
    vol.reload()
    patterns = json.loads(open(f"{E3}/reference/c1_scanner_patterns_v2.json").read())
    held = json.loads((CODING / "inputs" / "abstracts.json").read_text())
    acc = cp.read_accessions(f"{E3}/reference/c1_scanner_patterns_v2.json",
                             f"{E3}/reference/accession_releases.csv")
    prompt = len(cp.fixed_prompt(open(f"{E3}/prompts/coding_prompt_v2.md").read(),
                                 open(f"{E2}/outputs/manual_coding/2026-10-03/coders/"
                                      "dictionary_definitions.csv").read()))
    found = [c for r in records
             for c in json.loads((CODING / "c1" / f"{r}.json").read_text())["found"]]
    triples = {(c["record_id"], c["identifier"], c["expected_row"]): set() for c in found}
    for c in found:
        triples[(c["record_id"], c["identifier"], c["expected_row"])].add(sp.route(c))
    where = collections.Counter(
        "full_text_only" if r <= {"R1", "R3"} else "supplement_only" if r == {"R2"} else "both"
        for r in triples.values())
    drawn = sp.stratified_draw(found, patterns["draw"]["seed"], patterns["draw"]["maximum"])
    controls = c1.control_rows(drawn, queue["queue"],
                               q.side_rows(pathlib.Path(f"{E2}/dataset_dictionary.csv")))
    by_record: dict[str, list[dict]] = {}
    for r in queue["queue"]:
        by_record.setdefault(r["record_id"], []).append(r)
    ctrl: dict[str, list[dict]] = {}
    for r in controls:
        ctrl.setdefault(r["record_id"], []).append(r)
    stage_a, stage_b, sa1 = [], [], []
    a_full = 0
    for rec, rows in sorted(by_record.items()):
        result = json.loads((ROOT / "retrieval" / rec / "result.json").read_text())
        full = [s for s in result["sources"] if s["route"] in ("R1", "R3") and s.get("text")]
        a_full += bool(full)
        rows_a = c1.merge(rows, ctrl.get(rec, []))
        carried = len(held[rec]["abstract"]) + sum(len(s["text"]) for s in full)
        pa, _ = cp.fulltext_packets(rec, held[rec]["title"], rows_a, held[rec]["abstract"],
                                    full, [], acc)
        stage_a.append({"record_id": rec, "carried": carried,
                        "packets": [len(json.dumps(p, ensure_ascii=False)) for p in pa]})
        n = len([s for s in result["sources"] if s["route"] == "R2"
                 and s.get("text") is not None])
        if n:
            supps = [json.loads((ROOT / "cut_v2" / rec / "files" / f"{k}.json").read_text())
                     for k in range(n)]
            pb, _ = cp2.fulltext_packets_carrying(rec, held[rec]["title"], rows,
                                                  held[rec]["abstract"], full, supps, acc)
            stage_b.append({"record_id": rec, "carried": carried,
                            "packets": [len(json.dumps(p, ensure_ascii=False)) for p in pb]})
    manifest = json.loads((CODING / "packets" / "sa1" / "manifest.json").read_text())
    sa1 = [{"record_id": m["record_id"], "carried": 0, "packets": [m["packet_characters"]]}
           for m in manifest]

    def block(recs, carrying):
        return {"records": len(recs), "requests_per_model": sum(len(r["packets"]) for r in recs),
                "records_with_several_requests": sum(len(r["packets"]) > 1 for r in recs),
                "packet_characters": sum(sum(r["packets"]) for r in recs),
                "cost": priced(recs, prompt, carrying)}

    return {
        "fixed_prompt_characters": prompt,
        "c1_candidate_triples": {"total": len(triples), **dict(where)},
        "c1_matches_by_route": dict(collections.Counter(sp.route(c) for c in found)),
        "stratified_draw": {
            "rule": "one per (record, identifier) in stage A text (R1, R3), seeded shuffle "
                    f"(seed {patterns['draw']['seed']}), at most {sp.PER_RECORD} per record, at "
                    f"most {patterns['draw']['maximum']}",
            "drawn": len(drawn), "minimum": patterns["draw"]["minimum"],
            "records": len({c["record_id"] for c in drawn}),
            "by_side": dict(collections.Counter(c["side"] for c in drawn)),
            "by_identifier_type": dict(collections.Counter(c["type"] for c in drawn)),
            "by_kind": dict(collections.Counter(c["kind"] for c in drawn)),
            "expected_rows": len({c["expected_row"] for c in drawn}),
            "per_record": dict(collections.Counter(c["record_id"] for c in drawn)),
            "drawn_controls": drawn},
        "stage_a": block(stage_a, True) | {"records_with_a_full_text": a_full,
                                           "records_abstract_only": len(stage_a) - a_full,
                                           "control_rows_merged": len(controls)},
        "sa1": block(sa1, False),
        "stage_b_upper_bound": block(stage_b, True) | {
            "note": "every record with a readable supplement, as if each still held an "
                    "unresolved row; no control rows"},
        "assumptions": {"output_tokens_per_request_base": cp2.OUTPUT_TOKENS,
                        "prices": cp2.PRICE,
                        "excluded": "thinking and reasoning tokens (billed as output) beyond "
                                    "the stated output lengths; the diagnostic (about 9 US "
                                    "dollars at 400 chunks, with stage B); control-only "
                                    "papers; the 31 manifest packets; any re-request"},
        "per_record": {"stage_a": stage_a, "stage_b_upper_bound": stage_b}}


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-2500:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def price(out: str) -> None:
    target = LOCAL / out
    if target.exists():
        raise FileExistsError(f"{target} exists; it is written once")
    records = sorted(json.loads((PAPER1 / "outputs/release_resolution/"
                                          "availability_2026-10-08.json").read_text())["records"])
    queue = json.loads((LOCAL / "outputs" / "coding_queue_2026-10-13.json").read_text())
    result = price_job.remote(records, queue)
    target.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("per_record",)} | {"stratified_draw": {
                          k: v for k, v in result["stratified_draw"].items()
                          if k != "drawn_controls"}}, indent=1)[:6000])
