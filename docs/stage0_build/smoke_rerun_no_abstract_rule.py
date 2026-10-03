"""Rerun of the pre-2019 smoke round (label smoke_pre2019_20261002) under the `no_abstract`
rule, from the stored responses and decisions only. No request is made: the chase round is
re-assembled through an HTTP transport that raises on any request, and no model is called (a
record already judged keeps its stored decision; a `no_abstract` record leaves the sets).

Run from experiments/02_claims_meta:

    PYTHONPATH=scripts uv run --project ../.. python \
        ../../docs/stage0_build/smoke_rerun_no_abstract_rule.py

Writes outputs/screening_smoke/<label>_no_abstract_rule/ (the search set, chase_round_1/ and
decisions/), outputs/registry/<label>_no_abstract_rule/, outputs/funnel/<label>_no_abstract_rule/
and docs/stage0_build/smoke_rerun_no_abstract_rule_counts_2026-10-02.json. Every output folder
is new; an existing one raises.

The run of 2026-10-02 used absolute paths, and three of its outputs named the repository's
folder on the author's machine; the path was removed through `stage_record.py replace`
(outputs/results_manifests/replaced_files.json). The script now passes relative paths.
"""

import json
import pathlib
import subprocess

import httpx

import assemble_screening_set as ass
import citation_chase as cc

EXP = pathlib.Path(".")       # relative, so no stored output names the machine's folders
LABEL = "smoke_pre2019_20261002"
NEW = f"{LABEL}_no_abstract_rule"
ELIG = "2811496ef424"
EXTR = "0b97103cd7a4"
PARSED = EXP / "outputs" / "parsed"
VERIF = EXP / "outputs" / "verification"
OLD = EXP / "outputs" / "screening_smoke" / LABEL
OUT = EXP / "outputs" / "screening_smoke" / NEW
ROUND = OUT / "chase_round_1"
DEC = OUT / "decisions"
COUNTS = EXP / ".." / ".." / "docs" / "stage0_build" / (
    "smoke_rerun_no_abstract_rule_counts_2026-10-02.json")


def rows(path: pathlib.Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def write(path: pathlib.Path, items: list[dict]) -> pathlib.Path:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in items))
    return path


def script(name: str, *args: str) -> None:
    subprocess.run(["python", f"scripts/{name}", *map(str, args)], check=True, cwd=EXP)


def kept(source: pathlib.Path, target: pathlib.Path, ids: set[str], key: str = "pmid"
         ) -> pathlib.Path:
    """The stored rows of `source` whose record is in `ids`."""
    return write(target, [r for r in rows(source) if r[key] in ids])


def no_request(request: httpx.Request) -> httpx.Response:
    raise AssertionError(f"a request was attempted: {request.url}")


def main() -> None:
    if COUNTS.exists():
        raise FileExistsError(COUNTS)
    # Search: the stored responses, re-assembled; then the prefilter, as RUNBOOK stage 1.
    ass.write_outputs(EXP / "outputs" / "raw" / "search_smoke" / LABEL, OUT)
    script("keyword_prefilter.py", "--screening-set", OUT / "screening_set.jsonl")
    search_ids = {r["pmid"] for r in rows(OUT / "screening_queue.jsonl")}
    search_dec = kept(PARSED / f"sol_eligibility_{LABEL}_{ELIG}.decisions.jsonl",
                      DEC / f"sol_eligibility_{NEW}_{ELIG}.decisions.jsonl", search_ids)
    script("select_eligible.py", "--decisions", search_dec, "--screening-set",
           OUT / "screening_set.jsonl", "--screening-records", OUT / "screening_records.jsonl")
    seeds_path = search_dec.with_name(search_dec.name.removesuffix(".jsonl")
                                      + ".eligible_records.jsonl")

    # Chase round 1: the stored pages of the same seed, with no request possible.
    seeds = rows(seeds_path)
    with httpx.Client(transport=httpx.MockTransport(no_request)) as client:
        screening, counts = cc.chase(
            client, EXP / "outputs" / "raw" / "citation_chase_smoke" / LABEL / "chase_round_1",
            seeds, rows(OUT / "screening_records.jsonl"), cc.SMOKE_END, None)
    in_window_left_out = len(screening) - len(cc.dated_until(screening, cc.SMOKE_END))
    screening = cc.dated_until(screening, cc.SMOKE_END)
    counts["smoke_records_first_public_after_2018_left_out"] = in_window_left_out
    counts["new_screening_records"] = len(screening)
    counts["new_screening_records_no_abstract"] = ass.no_abstract_counts(screening)
    ROUND.mkdir(parents=True)
    ass.write_screening_files(ROUND, screening)
    (ROUND / "chase_counts.json").write_text(json.dumps(
        {"round": 1, "seeds_file": str(seeds_path.relative_to(EXP)),
         "rerun_of": f"outputs/screening_smoke/{LABEL}/chase_round_1", **counts}, indent=1))
    script("keyword_prefilter.py", "--gate", "--screening-set", ROUND / "screening_set.jsonl")
    queue_ids = {r["pmid"] for r in rows(ROUND / "screening_queue.jsonl")}
    batch_ids = {r["pmid"] for r in rows(ROUND / "gate_sample_batch_01.jsonl")}
    chase_dec = kept(PARSED / f"sol_eligibility_{LABEL}_chase1_{ELIG}.decisions.jsonl",
                     DEC / f"sol_eligibility_{NEW}_chase1_{ELIG}.decisions.jsonl", queue_ids)
    gate_dec = kept(PARSED / f"sol_eligibility_{LABEL}_gate1b1_{ELIG}.decisions.jsonl",
                    DEC / f"sol_eligibility_{NEW}_gate1b1_{ELIG}.decisions.jsonl", batch_ids)
    undecided = (queue_ids | batch_ids) - {r["pmid"] for r in rows(chase_dec) + rows(gate_dec)}
    if undecided:
        raise RuntimeError(f"records with no stored decision (a model call would be needed): "
                           f"{sorted(undecided)}")
    script("gate_audit.py", "--round-dir", ROUND, "--decisions", gate_dec)
    script("select_eligible.py", "--decisions", chase_dec, gate_dec, "--screening-set",
           ROUND / "screening_set.jsonl", "--screening-records",
           ROUND / "screening_records.jsonl")

    # Extraction rows, span checks and claim checks of the records still judged eligible.
    eligible = {r["pmid"] for path in (search_dec, chase_dec, gate_dec) for r in rows(path)
                if r["decision"] in ("eligible", "eligible_count_not_stated", "uncertain")}
    extraction, spans, checks = [], [], []
    for stem in (f"sol_extraction_{LABEL}_{EXTR}", f"sol_extraction_{LABEL}_chase1gate_{EXTR}"):
        tag = stem.replace(LABEL, NEW)
        extraction.append(kept(PARSED / f"{stem}.jsonl", DEC / f"{tag}.jsonl", eligible))
        spans.append(kept(VERIF / stem / "spans.jsonl", DEC / f"{tag}.spans.jsonl", eligible))
        checks.append(kept(VERIF / stem / "claim_checks.jsonl",
                           DEC / f"{tag}.claim_checks.jsonl", eligible))
    registry = EXP / "outputs" / "registry" / NEW
    script("assemble_registry.py", "--records", OUT / "search_records.jsonl",
           ROUND / "search_records.jsonl", "--decisions", search_dec, chase_dec, gate_dec,
           "--extraction", *extraction, "--checks", *checks, "--smoke-label", LABEL,
           "--out", registry)
    funnel_dir = EXP / "outputs" / "funnel" / NEW
    script("funnel.py", "--screening-dir", OUT, "--screening-dir", ROUND, "--decisions",
           search_dec, chase_dec, gate_dec, "--extraction", *extraction, "--spans", *spans,
           "--checks", *checks, "--assembly", registry, "--out", funnel_dir)

    before = json.loads((EXP / "outputs" / "funnel" / f"{LABEL}_window" / "funnel.json")
                        .read_text())
    after = json.loads((funnel_dir / "funnel.json").read_text())

    def summary(f: dict) -> dict:
        audit = f["prefiltered_citation_chasing_gate_audit"]["chase_round_1"]
        chase = f["prefilter"]["chase_round_1"]
        return {
            "screening_records": f["screening"]["records"],
            "no_abstract_records": f["screening"].get("no_abstract", 0),
            "records_sent_to_gpt_6_1_sol": f["eligibility"]["records_sent_to_screening"],
            "eligibility_decisions": f["eligibility"]["decisions"],
            "records_to_extraction": f["eligibility"]["to_extraction"],
            "chase_round_1_marked": chase["marked"],
            "chase_round_1_gate_sampled": audit["sampled"],
            "chase_round_1_gate_positives": audit["judged_eligible_or_uncertain"],
            "chase_round_1_gate_positive_ids": audit["positive_record_ids"],
            "chase_round_1_gate_upper_bound_one_sided_95": audit["upper_bound_one_sided_95"],
            "chase_round_1_gate_stopping_reason": audit["stopping_reason"],
            "eligible_families": f["families"]["eligible_families"],
            "eligible_no_named_claims": f["families"]["eligible_no_named_claims"],
            "claim_records": f["extraction"]["claim_records"],
            "claims_entering_the_registry": f["verification"]["enters_registry"]}

    round_two_seeds = len(rows(chase_dec.with_name(
        chase_dec.name.removesuffix(".jsonl") + ".eligible_records.jsonl")))
    result = {
        "label": LABEL, "rerun_label": NEW, "requests_made": 0, "model_calls": 0,
        "floor_characters": after["no_abstract"]["floor_characters"],
        "before": {**summary(before), "round_2_seeds": len(rows(
            PARSED / f"sol_eligibility_{LABEL}_gate1b1_{ELIG}.decisions.eligible_records.jsonl"))},
        "after": {**summary(after), "round_2_seeds": round_two_seeds},
        "no_abstract_after": after["no_abstract"],
        "records_first_public_after_2018_left_out_of_the_round": in_window_left_out}
    COUNTS.write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
