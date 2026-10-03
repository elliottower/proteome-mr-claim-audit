"""The `no_abstract` rule (2 October 2026; scripts/abstract_floor.py and its guards in the
screening-set assembly, the prefilter, the gate audit, the extraction runner, the selection,
citation chasing, the funnel, the registry assembly and the negative controls). Each deliberate
change must make a test fail. Runs on Modal on copies of scripts/ and tests/; fixtures and
committed tables only.

    modal run docs/stage0_build/mutation_check_no_abstract.py
"""
import json
import pathlib
import shutil
import subprocess

import modal

VOLUME = "proteome-mr-claim-audit-inputs"
MOUNT = pathlib.Path("/vol")
REMOTE = MOUNT / "02_claims_meta"
EXP = pathlib.Path("/exp")
HERE = pathlib.Path(__file__).resolve()
LOCAL_EXP = HERE.parents[2] / "experiments" / "02_claims_meta" if modal.is_local() else EXP
IGNORE = ["__pycache__", "*.pyc", ".pytest_cache"]
T = "test_no_abstract.py"
M = [
 ("abstract_floor.py", "ABSTRACT_FLOOR = 200", "ABSTRACT_FLOOR = 100", T),
 ("abstract_floor.py", "ABSTRACT_FLOOR = 200", "ABSTRACT_FLOOR = 199", T),
 ("abstract_floor.py", "ABSTRACT_FLOOR = 200", "ABSTRACT_FLOOR = 201", T),
 ("abstract_floor.py", "    return len(\" \".join((text or \"\").split()))", "    return len(text or \"\")", T),
 ("abstract_floor.py", "    return abstract_length(text) < ABSTRACT_FLOOR", "    return abstract_length(text) <= ABSTRACT_FLOOR", T),
 ("abstract_floor.py", "    if short:\n        raise NoAbstractError(", "    if False:\n        raise NoAbstractError(", T),
 ("assemble_screening_set.py", "        with_abstract = (next((r for r in members if not is_no_abstract(r.abstract)), None)\n                         or next((r for r in members if r.abstract.strip()), None))", "        with_abstract = next((r for r in members if r.abstract.strip()), None)", T),
 ("assemble_screening_set.py", "        return is_no_abstract(self.abstract)", "        return False", T),
 ("assemble_screening_set.py", "        ensure_ascii=False) + \"\\n\" for s in screening if not s.no_abstract))", "        ensure_ascii=False) + \"\\n\" for s in screening))", T),
 ("assemble_screening_set.py", "        ensure_ascii=False) + \"\\n\" for s in screening if s.no_abstract))", "        ensure_ascii=False) + \"\\n\" for s in screening))", T),
 ("assemble_screening_set.py", "        first_author_surname=s.first_author_surname, first_public=s.first_public,\n        no_abstract=s.no_abstract).model_dump_json()", "        first_author_surname=s.first_author_surname, first_public=s.first_public,\n        ).model_dump_json()", T),
 ("assemble_screening_set.py", "        \"screening_records_with_an_abstract\": sum(not s.no_abstract for s in screening),", "        \"screening_records_with_an_abstract\": sum(s.no_abstract for s in screening),", T),
 ("assemble_screening_set.py", "    return {\"records\": len(rows), \"empty\": sum(not s.abstract.strip() for s in rows),", "    return {\"records\": len(rows), \"empty\": sum(bool(s.abstract.strip()) for s in rows),", T),
 ("keyword_prefilter.py", "    refuse_no_abstract(records, \"keyword prefilter\")\n", "", T),
 ("run_extraction.py", "    if a.task != \"fulltext_extraction\":\n        refuse_no_abstract(", "    if False:\n        refuse_no_abstract(", T),
 ("select_eligible.py", "    if judged_without:", "    if False:", T),
 ("select_eligible.py", "judged_without = sorted(i for i in decided if by_record.get(i, {}).get(\"no_abstract\"))", "judged_without = sorted(i for i in decided if not by_record.get(i, {}).get(\"no_abstract\", True))", T),
 ("citation_chase.py", "    if without:\n        raise ChaseError(f\"seeds classed no_abstract", "    if False:\n        raise ChaseError(f\"seeds classed no_abstract", "test_citation_chase.py"),
 ("citation_chase.py", "        \"new_screening_records_no_abstract\": ass.no_abstract_counts(screening),\n    }", "        \"new_screening_records_no_abstract\": ass.no_abstract_counts([]),\n    }", "test_citation_chase.py"),
 ("gate_audit.py", "    refuse_no_abstract(gated, f\"gate audit of {a.round_dir}\")\n", "", T),
 ("gate_audit.py", "len(read_jsonl(without)) if without.exists()", "0 if without.exists()", "test_gate_audit.py"),
 ("funnel.py", "        ids = [r[\"record_id\"] for r in run.records if r[\"record_id\"] not in without_ids]", "        ids = [r[\"record_id\"] for r in run.records]", T),
 ("funnel.py", "        if judged_without:", "        if False:", T),
 ("funnel.py", "            audits[run.name][\"no_abstract_records_of_the_round\"] = len(without)", "            audits[run.name][\"no_abstract_records_of_the_round\"] = 0", T),
 ("funnel.py", "        titled = sorted(r[\"record_id\"] for r in without if not keyword_prefilter.mark(", "        titled = sorted(r[\"record_id\"] for r in without if keyword_prefilter.mark(", T),
 ("funnel.py", "            \"empty\": sum(not (r.get(\"abstract\") or \"\").strip() for r in without),", "            \"empty\": 0,", T),
 ("funnel.py", "            \"stub_below_floor\": sum(bool((r.get(\"abstract\") or \"\").strip()) for r in without),", "            \"stub_below_floor\": 0,", T),
 ("funnel.py", "            \"records\": len(ids), \"no_abstract_records_not_screened\": len(without),", "            \"records\": len(ids), \"no_abstract_records_not_screened\": 0,", T),
 ("funnel.py", "                      \"no_abstract\": sum(n[\"records\"] for n in no_abstract.values()),", "                      \"no_abstract\": 0,", T),
 ("assemble_registry.py", "        has_journal = any(r.kind == \"journal\" and not r.no_abstract for r in rs)", "        has_journal = any(r.kind == \"journal\" for r in rs)", T),
 ("assemble_registry.py", "    if judged_without:", "    if False:", T),
 ("assemble_registry.py", "                    \"records_no_abstract\": n_no_abstract,", "                    \"records_no_abstract\": 0,", T),
 ("assemble_registry.py", "                        any(r.no_abstract for r in members[f]) for f in meta),", "                        False for f in meta),", T),
 ("negative_control_specificity.py", "        ids = [i for i in all_ids if i not in no_abstract]", "        ids = list(all_ids)", T),
 ("negative_control_specificity.py", "    expected = set(stratum) - no_abstract", "    expected = set(stratum)", T),
 ("negative_control_specificity.py", "    if no_abstract - set(stratum):", "    if False:", T),
 ("negative_control_specificity.py", "        return {\"records\": len(all_ids), \"no_abstract\": len(all_ids) - len(ids),", "        return {\"records\": len(all_ids), \"no_abstract\": 0,", T),
 ("fetch_known_item_abstracts.py", "            if p not in short:\n", "            if True:\n", T),
 ("fetch_known_item_abstracts.py", "    short = [p for p in pmids if is_no_abstract(items[p].abstract)]", "    short = [p for p in pmids if not items[p].abstract]", T),
]

image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("httpx==0.28.1", "numpy==2.5.3", "openpyxl==3.1.5", "pyarrow==21.0.0",
                      "pydantic==2.13.5", "pypdf==5.9.0", "pytest==8.4.2", "pyyaml==6.0.3",
                      "rapidfuzz==3.14.6")
         .add_local_dir(LOCAL_EXP / "scripts", str(EXP / "scripts"), copy=True, ignore=IGNORE)
         .add_local_dir(LOCAL_EXP / "tests", str(EXP / "tests"), copy=True, ignore=IGNORE)
         .add_local_dir(LOCAL_EXP / "verification", str(EXP / "verification"), copy=True)
         .add_local_dir(LOCAL_EXP / "search", str(EXP / "search"), copy=True, ignore=IGNORE)
         .add_local_dir(LOCAL_EXP / "prompts", str(EXP / "prompts"), copy=True)
         .add_local_file(LOCAL_EXP / "PREREG.md", str(EXP / "PREREG.md"), copy=True)
         .add_local_file(LOCAL_EXP / "dataset_dictionary.csv",
                         str(EXP / "dataset_dictionary.csv"), copy=True)
         .add_local_file(LOCAL_EXP / "reference" / "MANIFEST.json",
                         str(EXP / "reference" / "MANIFEST.json"), copy=True)
         .run_commands(f"ln -s {REMOTE / 'inputs'} {EXP / 'inputs'}",
                       f"ln -s {REMOTE / 'derived'} {EXP / 'derived'}"))
vol = modal.Volume.from_name(VOLUME)
app = modal.App("proteome-mr-mutation-check", image=image)


@app.function(volumes={str(MOUNT): vol}, timeout=3600, cpu=4.0, memory=8192)
def check() -> dict:
    env = {"PYTHONPATH": str(EXP / "scripts"), "PATH": "/usr/local/bin:/usr/bin:/bin",
           "PYTHONDONTWRITEBYTECODE": "1"}
    results = []
    for name, old, new, test in M:
        target = EXP / "scripts" / name
        text = target.read_text()
        if text.count(old) != 1:
            results.append({"file": name, "old": old, "state": f"not_applied ({text.count(old)})"})
            continue
        target.write_text(text.replace(old, new, 1))
        r = subprocess.run(["python", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", test],
                           cwd=EXP / "tests", capture_output=True, text=True, env=env)
        target.write_text(text)
        results.append({"file": name, "old": old, "new": new, "test": test,
                        "state": "killed" if r.returncode == 1 else
                        "survived" if r.returncode == 0 else f"error {r.returncode}",
                        "tail": r.stdout[-300:] if r.returncode not in (0, 1) else ""})
    base = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                          cwd=EXP / "tests", capture_output=True, text=True, env=env)
    return {"mutations": len(M), "killed": sum(r["state"] == "killed" for r in results),
            "not_killed": [r for r in results if r["state"] != "killed"],
            "unmutated_suite_returncode": base.returncode, "unmutated_tail": base.stdout[-600:]}


@app.local_entrypoint()
def main() -> None:
    result = check.remote()
    out = HERE.parent / "mutation_check_no_abstract.json"
    if out.exists():
        shutil.move(out, out.with_name("mutation_check_no_abstract_previous.json"))
    out.write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))
