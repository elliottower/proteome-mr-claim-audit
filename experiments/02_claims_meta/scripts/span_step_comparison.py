# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Compare the registered span step with the corrected one, run under the corrected build of
`citations` (PREREG.md, Amendment 2). The corrected step may change the records listed in
verification/span_step_permitted_differences.json and no other; this script checks that and
writes every hash and every assertion to one file. It exits non-zero when an assertion fails:
nothing downstream is rebuilt then.

Assertions:
    same_records            both runs hold the same claim records in the same order, per file
    diff_within_permitted   the records whose line differs are a subset of the permitted set
    unaffected_files_equal  a file with an empty permitted set is byte-identical
    passing_unchanged       every record that passed the registered step has an identical line
    duplicated_now_pass     every record listed as pinned at its first occurrence passes, with
                            the registered quote check holding as before
    joined_still_fail       every record listed as still failing fails
    occurrence_only_there   `--occurrence` was used for exactly the records listed as pinned at
                            their first occurrence, each with an occurrence count of two or more
    fold_parity             the two builds' folding functions give identical output on every
                            stored abstract and evidence span (scripts/citations_fold_digest.py,
                            run under each build)

Usage: uv run scripts/span_step_comparison.py --files <label>=<extraction stem> [...] \\
           --registered outputs/verification --corrected outputs/verification_occurrence \\
           --permitted verification/span_step_permitted_differences.json \\
           --inputs <extraction and abstract files> --fold-registered <digest.json> \\
           --fold-corrected <digest.json> --out <json>
"""

import argparse
import datetime
import hashlib
import json
import pathlib


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record_id(line: str) -> str:
    r = json.loads(line)
    return f"{r['pmid']}:{r['claim_index']:03d}"


def compare_file(registered: list[str], corrected: list[str], permitted: dict,
                 occurrences: dict) -> dict:
    """The assertions on one extraction file's two span files (their lines)."""
    now_pass = set(permitted["pinned_at_first_occurrence_and_passing"])
    still_fail = set(permitted["still_failing"])
    ids = [record_id(line) for line in registered]
    same = ids == [record_id(line) for line in corrected]
    out = {"records": len(ids), "same_records": same}
    if not same:
        return out | {"holds": False}
    old = dict(zip(ids, map(json.loads, registered)))
    new = dict(zip(ids, map(json.loads, corrected)))
    differing = {i for i, a, b in zip(ids, registered, corrected) if a != b}
    used = occurrences["records_pinned_at_an_occurrence"]
    out |= {
        "differing_records": sorted(differing),
        "diff_within_permitted": differing <= now_pass | still_fail,
        "unaffected_files_equal": bool(now_pass | still_fail) or registered == corrected,
        "passing_unchanged": all(old[i] == new[i] for i in ids if old[i]["passes"]),
        "duplicated_now_pass": all(
            new[i]["passes"] and new[i]["registered_check"] and old[i]["registered_check"]
            and new[i]["citations_pin"] == "found" for i in now_pass),
        "joined_still_fail": all(not new[i]["passes"] for i in still_fail),
        "occurrence_only_there": set(used) == now_pass and all(
            v["occurrence_count"] >= 2 and v["pin_method"] == "occurrence_1"
            for v in used.values()),
        "passing_registered": sum(r["passes"] for r in old.values()),
        "passing_corrected": sum(r["passes"] for r in new.values()),
        "occurrence_counts": sorted({v["occurrence_count"] for v in used.values()}),
        "stored_abstract_has_duplicated_passage": sorted(
            occurrences["stored_abstract_has_duplicated_passage"])}
    checks = ("same_records", "diff_within_permitted", "unaffected_files_equal",
              "passing_unchanged", "duplicated_now_pass", "joined_still_fail",
              "occurrence_only_there")
    return out | {"holds": all(out[c] for c in checks)}


def fold_parity(registered: dict, corrected: dict) -> dict:
    same = registered["items"] == corrected["items"]
    differing = sorted(k for k in registered["items"]
                       if registered["items"][k] != corrected["items"].get(k))
    return {"texts": registered["texts"], "identical": same, "differing_texts": len(differing),
            "registered_build": registered["citations"],
            "corrected_build": corrected["citations"], "holds": same and not differing
            and registered["texts"] == corrected["texts"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="+", required=True, help="<label>=<extraction stem>")
    for name in ("registered", "corrected", "permitted", "fold-registered", "fold-corrected",
                 "out"):
        ap.add_argument(f"--{name}", type=pathlib.Path, required=True)
    ap.add_argument("--inputs", type=pathlib.Path, nargs="+", required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise FileExistsError(f"{a.out} exists; a comparison is written once")
    permitted = json.loads(a.permitted.read_text())["files"]
    result: dict = {
        "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "permitted": {"path": str(a.permitted), "sha256": sha256(a.permitted)},
        "inputs": {str(p): sha256(p) for p in sorted(a.inputs)}, "files": {}}
    for item in a.files:
        label, stem = item.split("=", 1)
        old, new = a.registered / stem / "spans.jsonl", a.corrected / stem / "spans.jsonl"
        occurrences = json.loads((a.corrected / stem / "span_occurrences.json").read_text())
        made = compare_file(old.read_text().splitlines(), new.read_text().splitlines(),
                            permitted[label], occurrences)
        made["outputs"] = {"registered": {"path": str(old), "sha256": sha256(old)},
                           "corrected": {"path": str(new), "sha256": sha256(new)}}
        made["citations_installed"] = occurrences["citations_installed"]
        result["files"][label] = made
    result["fold_parity"] = fold_parity(json.loads(a.fold_registered.read_text()),
                                        json.loads(a.fold_corrected.read_text()))
    result["all_assertions_hold"] = (result["fold_parity"]["holds"]
                                     and all(f["holds"] for f in result["files"].values()))
    a.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({"all_assertions_hold": result["all_assertions_hold"],
                      "fold_parity": result["fold_parity"]["holds"],
                      "files": {k: {c: v.get(c) for c in ("holds", "records",
                                                         "passing_registered",
                                                         "passing_corrected")}
                                for k, v in result["files"].items()}}, indent=1))
    if not result["all_assertions_hold"]:
        raise SystemExit("an assertion fails: stop, nothing downstream is rebuilt")


if __name__ == "__main__":
    main()
