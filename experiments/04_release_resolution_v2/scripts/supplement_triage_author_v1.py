# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml==6.0.3", "pydantic==2.13.5"]
# ///
"""Unregistered supplement triage: apply the author's review decisions to the v1 decisions. No
model is called.

Inputs: the v1 decisions (outputs/supplement_triage_decisions_2026-10-22.json), the author's
rules file (outputs/supplement_triage_author_rules_2026-10-23.json: rule ids and texts, choices,
card calls, the audit draw) and the applications file
(outputs/supplement_triage_author_applications_2026-10-23.json: for each row a rule changes, the
rule, the new decision and, for a split row, one entry per claim record).

A row the applications file does not name keeps its v1 decision, pins and evidence (every
practical rule P1 to P7 accepted; every reversal of a stage A code accepted). A named row takes
the new decision. `split` (rule R2 or R3, or a card call) codes the row per claim record: each
claim gets the releases its own protein or outcome used, `absent` labels for a source with no
dictionary row (dataset_absent_from_dictionary), or stays unresolved; a claim of the row the
file does not list stays unresolved. The row keeps its v1 evidence and pins and adds the new.

Checks (each failure stops the script): every v1 `review` row is named; every rule an
application cites is in the rules file; every release is a dictionary row; every listed claim
record holds the row (estimands_v1.row_key over Paper 1's claims); every pin names a claims file
holding the id with a quotation over the evidence's text sha256; the audit draw reproduces from
its seed.

    PYTHONPATH=scripts:../03_release_resolution/scripts:../02_claims_meta/scripts \\
        uv run python scripts/supplement_triage_author_v1.py \\
        --out outputs/supplement_triage_decisions_v2_2026-10-23.json
"""

import argparse
import collections
import csv
import hashlib
import json
import pathlib
import random

import estimands_v1 as es
from modal_coding_v2 import CHECKS, REG
from supplement_triage_decisions_v1 import check_pin

HERE = pathlib.Path(__file__).resolve().parent
E4 = HERE.parent
E2 = E4.parent / "02_claims_meta"
ROOT = E4.parent.parent
V1 = E4 / "outputs" / "supplement_triage_decisions_2026-10-22.json"
RULES = E4 / "outputs" / "supplement_triage_author_rules_2026-10-23.json"
APPS = E4 / "outputs" / "supplement_triage_author_applications_2026-10-23.json"
DICTIONARY = E2 / "dataset_dictionary.csv"
REVERSAL_REASONS = {"dataset_absent_from_dictionary", "conflicting_identifiers"}


class AuthorRuleError(Exception):
    """An application breaks a check, or the output exists."""


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def claims_of_rows(rows: set[str]) -> dict[str, set[str]]:
    """Row id -> the Paper 1 claim records holding it."""
    written = {}
    for c in CHECKS:
        for r in jsonl(E2 / c):
            if "claim_record_id" in r:
                written.setdefault(r["claim_record_id"], r["outcome_as_written"])
    out = collections.defaultdict(set)
    for c in jsonl(E2 / REG / "registry_claims_without_manual_coding.jsonl"):
        cid = c["claim_record_id"]
        for side, field in (("pqtl", "pqtl_datasets"), ("outcome", "outcome_datasets")):
            for name in c[field]:
                rid = es.row_key(cid, side, name, written[cid])
                if rid in rows:
                    out[rid].add(cid)
    return out


def rule_ids(rule: str) -> list[str]:
    return rule.split("+")


def is_reversal(r: dict) -> bool:
    return (r["decision"] == "resolved" and r["stage_a"] != "not_accepted"
            and bool(REVERSAL_REASONS & set(r["stage_a"])))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise AuthorRuleError(f"{a.out} exists; it is written once")
    v1 = json.loads(V1.read_text())
    rules = json.loads(RULES.read_text())
    apps = json.loads(APPS.read_text())["rows"]
    names = {r["name"] for r in csv.DictReader(DICTIONARY.open(newline=""))}
    known = set(rules["practical_layer"]["rules"]) | set(rules["review_rules"]) | {"card"}

    rows = {r["row_id"]: r for r in v1["rows"]}
    missing = sorted(rid for rid, r in rows.items() if r["decision"] == "review" and rid not in apps)
    if missing:
        raise AuthorRuleError(f"review rows with no application: {missing}")
    reversals = sorted(rid for rid, r in rows.items() if is_reversal(r))
    if reversals != rules["card_calls"]["reversals_of_stage_a_codes"]["rows"]:
        raise AuthorRuleError("the reversal rows differ from the rules file")
    pool = sorted(rid for rid, r in rows.items() if r["decision"] == "resolved" and not is_reversal(r))
    audit = rules["audit"]
    if random.Random(audit["seed"]).sample(pool, len(audit["rows"])) != audit["rows"]:
        raise AuthorRuleError("the audit draw does not reproduce from its seed")

    holders = claims_of_rows(set(apps))
    cache: dict = {}
    out_rows = []
    claim_counts = collections.Counter()
    for rid, r in sorted(rows.items(), key=lambda kv: (kv[1]["record_id"], kv[1]["side"], kv[0])):
        new = dict(r) | {"author_rule": None, "claims": {}}
        if rid in apps:
            x = apps[rid]
            for rule in rule_ids(x["rule"]):
                if rule not in known:
                    raise AuthorRuleError(f"{rid}: rule {rule} is not in the rules file")
            for rel in x["releases"] + [rl for c in x["claims"].values()
                                        for rl in c.get("releases", [])]:
                if rel["release"] not in names:
                    raise AuthorRuleError(f"{rid}: {rel['release']!r} is not a dictionary row")
            extra = set(x["claims"]) - holders[rid]
            if extra:
                raise AuthorRuleError(f"{rid}: claim records not holding the row: {sorted(extra)}")
            for e in x["evidence"]:
                check_pin(e["pin"], e["text_sha256"], cache)
            claims = {}
            if x["decision"] == "split":
                for cid in sorted(holders[rid]):
                    c = x["claims"].get(cid, {"unresolved": True})
                    state = ("unresolved" if c.get("unresolved") else
                             "absent" if c.get("absent") and not c.get("releases") else
                             "resolved_with_absent_component" if c.get("absent") else "resolved")
                    claims[cid] = {"state": state, "releases": c.get("releases", []),
                                   "absent": c.get("absent", [])}
                    claim_counts[state] += 1
            new |= {"decision": x["decision"], "layer": x["layer"],
                    "releases": x["releases"] if x["decision"] == "resolved" else [],
                    "author_rule": x["rule"], "author_reading": x["reading"],
                    "unresolved_reason": x.get("reason"), "claims": claims,
                    "evidence": r["evidence"] + x["evidence"]}
        out_rows.append(new)

    by = collections.Counter(f"{r['decision']}|{r['layer'] or ''}" for r in out_rows)
    files = [V1, RULES, APPS, DICTIONARY, E2 / REG / "registry_claims_without_manual_coding.jsonl",
             HERE / "supplement_triage_author_v1.py"]
    out = {"script": "scripts/supplement_triage_author_v1.py",
           "what": "unregistered supplement triage decisions after the author's review: v1 "
                   "decisions with the author's rules and card calls applied; ids, releases, "
                   "claim-level codes, evidence pointers and pins only",
           "inputs_sha256": {str(f.relative_to(ROOT)): sha256(f) for f in files},
           "counts": {"rows": len(out_rows),
                      "by_decision_and_layer": dict(sorted(by.items())),
                      "rows_changed_by_the_author": len(apps),
                      "rows_changed_by_rule": dict(sorted(collections.Counter(
                          x["rule"] for x in apps.values()).items())),
                      "split_rows": sum(r["decision"] == "split" for r in out_rows),
                      "claims_in_split_rows_by_state": dict(sorted(claim_counts.items())),
                      "unresolved_rows_with_stage_a_absent_reason": sum(
                          1 for r in out_rows if r["decision"] == "unresolved"
                          and r["stage_a"] != "not_accepted"
                          and "dataset_absent_from_dictionary" in r["stage_a"]),
                      "reversals_accepted": len(reversals),
                      "audit_rows_accepted": audit["accepted"]},
           "rows": out_rows}
    a.out.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(out["counts"], indent=1))


if __name__ == "__main__":
    main()
