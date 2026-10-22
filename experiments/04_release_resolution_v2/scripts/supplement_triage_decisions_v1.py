# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml==6.0.3"]
# ///
"""Unregistered supplement triage: assemble and check the hand decisions, one file per record in
the gitignored work folder (outputs/raw/supplement_triage_work_2026-10-22/decisions/), into the
committed decisions file and a gitignored review file. No model is called; the decisions were
made by reading the scan's hits in the sources (scripts/supplement_triage_v2.py).

Checks (each failure stops the script): every row that is unresolved after stage A in the 135
records appears exactly once and no other row appears; every release is a dictionary row name;
a `resolved` row has a layer (`rules` or `practical`), at least one release with a registered
role, and at least one evidence item whose pin names a claims file holding that claim id with a
quotation; the claims file's source sha256 equals the evidence's text_sha256.

The committed file holds ids, decisions, release names, evidence pointers (file, text sha256,
location, identifier, pin) and each row's reading in the reviewer's own words. Quotations go only
to the review file in the gitignored folder.

    uv run python scripts/supplement_triage_decisions_v1.py \\
        --out outputs/supplement_triage_decisions_2026-10-22.json \\
        --review outputs/raw/supplement_triage_review_2026-10-22.md
"""

import argparse
import collections
import csv
import hashlib
import json
import pathlib

import yaml

HERE = pathlib.Path(__file__).resolve().parent
E4 = HERE.parent
ROOT = E4.parent.parent
WORK = E4 / "outputs" / "raw" / "supplement_triage_work_2026-10-22"
VOL = E4 / "outputs" / "raw" / "volume_copy_2026-10-22"
DECISION = E4 / "outputs" / "stage_b_decision_2026-10-21.json"
DICTIONARY = E4.parent / "02_claims_meta" / "dataset_dictionary.csv"
SCAN = E4 / "outputs" / "supplement_triage_scan_v2_2026-10-22.json"
ROLES = {"primary", "meta_analysis_component", "replication", "sensitivity"}
DECISIONS = {"resolved", "unresolved", "conflict", "review"}
LAYERS = {"rules", "practical"}


class DecisionError(Exception):
    """A decision file breaks a check, or an output exists."""


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unresolved_rows() -> dict[str, dict]:
    records = set(json.loads(DECISION.read_text())["unresolved_record_ids"])
    queue = json.loads((VOL / "queue.json").read_text())["queue"]
    accepted = json.loads((VOL / "accepted_stage_a.json").read_text())
    out = {}
    for r in queue:
        a = accepted[r["row_id"]]
        if r["record_id"] in records and (not a["accepted"] or a["code"]["unresolved_reasons"]):
            out[r["row_id"]] = {"record_id": r["record_id"], "side": r["side"],
                                "name_as_written": r["name_as_written"],
                                "stage_a": ("not_accepted" if not a["accepted"]
                                            else sorted(a["code"]["unresolved_reasons"]))}
    return out


def check_pin(pin: dict, text_sha256: str, cache: dict) -> None:
    path = ROOT / pin["claims_file"]
    if path not in cache:
        cache[path] = yaml.safe_load(path.read_text())
    doc = cache[path]
    claim = (doc.get("claims") or {}).get(pin["id"])
    if not claim or not claim.get("quotes"):
        raise DecisionError(f"{pin} names no pinned quotation")
    if doc["source"]["sha256"] != text_sha256:
        raise DecisionError(f"{pin}: source sha256 differs from the evidence's text_sha256")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--review", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists() or a.review.exists():
        raise DecisionError("an output exists; each is written once")
    names = {r["name"] for r in csv.DictReader(DICTIONARY.open(newline=""))}
    want = unresolved_rows()
    seen, rows, cache = set(), [], {}
    for f in sorted((WORK / "decisions").glob("*.json")):
        doc = json.loads(f.read_text())
        for r in doc["rows"]:
            rid = r["row_id"]
            if rid not in want or rid in seen:
                raise DecisionError(f"{f.name}: row {rid} is not an open row or appears twice")
            if want[rid]["record_id"] != doc["record_id"]:
                raise DecisionError(f"{f.name}: row {rid} belongs to another record")
            seen.add(rid)
            if r["decision"] not in DECISIONS:
                raise DecisionError(f"{rid}: decision {r['decision']!r}")
            for rel in r.get("releases", []):
                if rel["release"] not in names or rel["role"] not in ROLES:
                    raise DecisionError(f"{rid}: release or role {rel}")
            if r["decision"] == "resolved":
                if r["layer"] not in LAYERS or not r["releases"]:
                    raise DecisionError(f"{rid}: resolved without a layer or a release")
                if not any(e.get("pin") for e in r["evidence"]):
                    raise DecisionError(f"{rid}: resolved without a pinned quotation")
            for e in r.get("evidence", []):
                if e.get("pin"):
                    check_pin(e["pin"], e["text_sha256"], cache)
            rows.append(r | {"record_id": doc["record_id"], "stage_a": want[rid]["stage_a"]})
    missing = sorted(set(want) - seen)
    if missing:
        raise DecisionError(f"{len(missing)} open rows have no decision: {missing[:10]}")
    rows.sort(key=lambda r: (r["record_id"], r["side"], r["row_id"]))

    committed = [{k: r.get(k) for k in ("row_id", "record_id", "side", "name_as_written",
                                        "stage_a", "decision", "layer", "releases", "reading")}
                 | {"evidence": [{k: e.get(k) for k in ("kind", "file", "text_sha256",
                                                        "location", "identifier", "pin")}
                                 for e in r.get("evidence", [])]} for r in rows]
    by = collections.Counter(f"{r['decision']}|{r['layer'] or ''}" for r in rows)
    kinds = collections.Counter(e["kind"] for r in rows if r["decision"] == "resolved"
                                for e in r["evidence"])
    roles = collections.Counter(f"{r['layer']}|{x['role']}" for r in rows
                                if r["decision"] == "resolved" for x in r["releases"])
    entering = sum(1 for r in rows if r["decision"] == "resolved" and any(
        x["role"] in ("primary", "meta_analysis_component") for x in r["releases"]))
    files = [DECISION, VOL / "queue.json", VOL / "accepted_stage_a.json", DICTIONARY, SCAN,
             HERE / "supplement_triage_decisions_v1.py"]
    out = {"script": "scripts/supplement_triage_decisions_v1.py",
           "what": "unregistered supplement triage: one hand decision per row left unresolved "
                   "by stage A in the 135 records; ids, release names, evidence pointers and "
                   "pins only (quotations in the gitignored review file)",
           "rule_reading": {
               "rules": "decisive under the stage A rules: D1 release number or an accession "
                        "the frozen table maps; D2 DOI or PMID (prefixed, bare in a table cell, "
                        "or a cited reference) mapping to one dictionary row, or several rows "
                        "narrowed to one by an attribute of the same dataset",
               "practical": "established outside those tables: OpenGWAS metadata PMID, file "
                            "naming with a sample size, exact counts or a size signature; each "
                            "with a pinned quotation"},
           "inputs_sha256": {str(f.relative_to(ROOT)): sha256(f) for f in files},
           "decision_files_sha256": hashlib.sha256("".join(
               sha256(p) for p in sorted((WORK / "decisions").glob("*.json"))).encode())
           .hexdigest(),
           "counts": {"open_rows": len(want), "records": len({r["record_id"] for r in rows}),
                      "by_decision_and_layer": dict(sorted(by.items())),
                      "resolved_rows_entering_estimates": entering,
                      "resolved_release_roles": dict(sorted(roles.items())),
                      "evidence_kinds_of_resolved_rows": dict(sorted(kinds.items())),
                      "claims_files": len(cache), "pins": sum(
                          1 for r in rows for e in r.get("evidence", []) if e.get("pin"))},
           "rows": committed}
    a.out.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")

    lines = ["# Supplement triage review, 22 October 2026 (unregistered)", "",
             "One block per row left unresolved by stage A in the 135 records. Quotations are "
             "verbatim from the stored texts (tab = table cell); pins resolve with "
             "`citations verify --claims claims/`.", ""]
    for rec in sorted({r["record_id"] for r in rows}):
        lines += [f"## {rec}", ""]
        for r in [x for x in rows if x["record_id"] == rec]:
            rel = ", ".join(f"{x['release']} ({x['role']})" for x in r["releases"]) or "none"
            lines += [f"### {r['row_id']} {r['side']}: {r['name_as_written']}", "",
                      f"- stage A: {r['stage_a']}",
                      f"- decision: **{r['decision']}**"
                      + (f" ({r['layer']})" if r.get("layer") else "") + f"; releases: {rel}",
                      f"- reading: {r['reading']}"]
            for e in r.get("evidence", []):
                pin = e.get("pin") or {}
                lines.append(f"- evidence {e['kind']}: {e['identifier']} in `{e['file'][-90:]}` "
                             f"{e.get('location')} pin `{pin.get('claims_file', '-')}#"
                             f"{pin.get('id', '-')}`")
            for q in r.get("quotes_for_review", []):
                lines.append("  > " + q.replace("\t", " | ").replace("\n", " "))
            lines.append("")
    a.review.write_text("\n".join(lines) + "\n")
    print(json.dumps(out["counts"], indent=1))


if __name__ == "__main__":
    main()
