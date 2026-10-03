"""Round-6 fixes: each deliberate change of a registered rule must make a test fail. Runs on
Modal on copies of scripts/ and tests/; fixtures and committed tables only.

    modal run docs/stage0_build/mutation_check_round6_fixes.py
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
M = [
 ("drug_joins.py", "if t.quality_controls and not rule.include_flagged:", "if False:", "test_drug_joins.py"),
 ("drug_joins.py", '"quality_flagged_reports_included": Rule(include_flagged=True),', '"quality_flagged_reports_included": Rule(),', "test_drug_joins.py"),
 ("drug_joins.py", "                flagged_out[t.report_id] = t", "                pass", "test_drug_joins.py"),
 ("drug_joins.py", "matching_non_trial_reports=sum(t.status is None for t in trials),", "matching_non_trial_reports=sum(t.status is not None for t in trials),", "test_drug_joins.py"),
 ("drug_joins.py", "if r.highest_status != primary_status[p])", "if False)", "test_drug_joins.py"),
 ("drug_tables.py", 'flagged_by_source[str(r["source"])] += bool(flags)', 'flagged_by_source[str(r["source"])] += 1', "test_drug_tables.py"),
 ("tag_wording.py", "if m.wording_class == name and not (masked and m.inside):", "if m.wording_class == name:", "test_prefilter_wording_sample.py"),
 ("tag_wording.py", 'NAME_GAP = r"[\\s\\-‐‑‒–—]+"', 'NAME_GAP = r"\\s+"', "test_prefilter_wording_sample.py"),
 ("tag_wording.py", "if s <= m.start() and m.end() <= e})", "if s <= m.start()})", "test_prefilter_wording_sample.py"),
 ("claim_tags.py", "wording_class=w.wording_class, novelty_language=w.novelty_language,", "wording_class=w.wording_class_unmasked, novelty_language=w.novelty_language,", "test_claim_tags.py"),
 ("gate_audit.py", "TOLERANCE = 0.005", "TOLERANCE = 0.01", "test_gate_audit.py"),
 ("gate_audit.py", "BATCH = 600", "BATCH = 200", "test_gate_audit.py"),
 ("gate_audit.py", "MAX_SAMPLED = 3000", "MAX_SAMPLED = 6000", "test_gate_audit.py"),
 ("gate_audit.py", "judged = len(sampled) - failed", "judged = len(sampled)", "test_gate_audit.py"),
 ("gate_audit.py", "    random.Random(seed).shuffle(order)\n", "", "test_gate_audit.py"),
 ("gate_audit.py", "if set(sampled) != set(decisions):", "if False:", "test_gate_audit.py"),
 ("gate_audit.py", "not_judged = len(order) - judged", "not_judged = len(order) - len(sampled)", "test_gate_audit.py"),
 ("funnel.py", "if not (run.gated and i in set(marked))] + sampled", "if not (run.gated and i in set(marked))]", "test_stage_reports.py"),
 ("funnel.py", 'if not audits[run.name]["finished"]:', "if False:", "test_stage_reports.py"),
 ("funnel.py", "if set(sampled) - set(marked):", "if False:", "test_stage_reports.py"),
 ("select_eligible.py", "if len(set(decided)) != len(decided):", "if False:", "test_stage_reports.py"),
 ("keyword_prefilter.py", "gate_audit.draw_order([r[\"pmid\"] for r in out], seed), 1))", "[r[\"pmid\"] for r in out], 1))", "test_stage_reports.py"),
 ("pathway_enrichment.py", 'if whole_panel and r.get("whole_panel_assay_list"):', "if False:", "test_platform_lists.py"),
 ("pathway_enrichment.py", "if coverage is not None and coverage < MIN_PROXY_COVERAGE:", "if False:", "test_platform_lists.py"),
 ("pathway_enrichment.py", "MIN_PROXY_COVERAGE = 0.90", "MIN_PROXY_COVERAGE = 0.80", "test_platform_lists.py"),
 ("pathway_enrichment.py", "if level not in PROXY_LEVELS or not reported_targets:", "if not reported_targets:", "test_platform_lists.py"),
 ("pathway_enrichment.py", 'if (r["background_level"] == "unavailable") != (not r["assay_list"]):', "if False:", "test_platform_lists.py"),
 ("canonical_ids.py", "if not candidates or not all(crossed):", "if not candidates or not any(crossed):", "test_outcome_alias_completion.py"),
 ("canonical_ids.py", "return next(iter(terms)) if len(terms) == 1 else None", "return sorted(terms)[0] if terms else None", "test_outcome_alias_completion.py"),
 ("canonical_ids.py", "return {k: v for k, v in table.items() if not k.startswith(PHENOTYPE_XREF_KEY)}", "return dict(table)", "test_outcome_alias_completion.py"),
 ("outcome_alias_completion.py", 'if not target.startswith("HP:") or not used or target not in live_labels:', 'if not target.startswith("HP:") or target not in live_labels:', "test_outcome_alias_completion.py"),
 ("outcome_alias_completion.py", 'if len(terms) != 1 or not terms[0].startswith(("MONDO:", "EFO:")):', 'if not terms[0].startswith(("MONDO:", "EFO:")):', "test_outcome_alias_completion.py"),
 ("outcome_alias_completion.py", "        if key in names_in_use:", "        if False:", "test_outcome_alias_completion.py"),
 ("outcome_alias_completion.py", "        if len(found[key]) != 1:", "        if False:", "test_outcome_alias_completion.py"),
 ("outcome_alias_completion.py", "if prefix in ICD_PREFIXES and ICD_TAG in sources:", "if prefix in ICD_PREFIXES:", "test_outcome_alias_completion.py"),
 ("outcome_alias_completion.py", "if new is None or new not in live or not new.startswith(OUTCOME_PREFIXES):", "if new is None:", "test_outcome_alias_completion.py"),
 ("reference_screen.py", "(a for a in attempts if len(a[3]) == 1),", "(a for a in attempts if a[3]),", "test_reference_screen.py"),
 ("reference_screen.py", '"alias_relation") not in EQUIVALENT_RELATIONS', '"alias_relation") in EQUIVALENT_RELATIONS', "test_reference_screen.py"),
 ("reference_screen.py", "        return proxy_aliases or not proxy", "        return True", "test_reference_screen.py"),
 ("reference_screen.py", "    if icd10 and code and icd10.get(code):", "    if False:", "test_reference_screen.py"),
 ("reference_screen.py", "    if aliases and name in aliases:", "    if False:", "test_reference_screen.py"),
 ("derive_published_lists.py", "if (len(found), yes, cells) != (rows, included, rows):", "if False:", "test_derive_published_lists.py"),
 ("derive_published_lists.py", "        if len(hits) != 1:", "        if not hits:", "test_derive_published_lists.py"),
 ("derive_published_lists.py", "        if len(by_id[explore]) != 1:", "        if False:", "test_derive_published_lists.py"),
 ("derive_published_lists.py", "if (len(reagents), len(cells)) != (n_reagents, n_uniprot):", "if False:", "test_derive_published_lists.py"),
 ("therapeutic_areas.py", '"MONDO:0005583", "OTAR:0000018"})', '"MONDO:0005583"})', "test_therapeutic_areas.py"),
 ("therapeutic_areas.py", "nearest = min(with_areas.values())", "nearest = max(with_areas.values())", "test_therapeutic_areas.py"),
 ("manual_dataset_coding.py", 'for c in q["candidates"].split("|") if c], ensure_ascii=False)}', 'for c in q["candidates"].split("|")], ensure_ascii=False)}', "test_manual_dataset_coding.py"),
 ("manual_dataset_coding.py", '{"row": c, **definitions.get((q["side"], c), {})}', '{"row": c, "family": q["family_id"]}', "test_manual_dataset_coding.py"),
 ("build_outcome_aliases.py", 'if r["alias_relation"] not in RELATIONS:', "if False:", "test_outcome_aliases.py"),
 ("build_outcome_aliases.py", 'if not r["source"].strip() or not r["rationale"].strip():', "if False:", "test_outcome_aliases.py"),
 ("platform_list_sources.py", 'for member in [m for m in zip_member.split("!") if m]:', "for member in ([zip_member] if zip_member else []):", "test_platform_lists.py"),
 ("platform_list_sources.py", "bad = [s.list_id for s in sources if is_derived(s) == bool(s.url)]", "bad = []", "test_platform_lists.py"),
 ("assay_backgrounds.py", "path = (derived if is_derived(source) else folder) / source.file", "path = folder / source.file", "test_platform_lists.py"),
 ("build_registry.py", "if phenotype_term(candidates, collision) is not None:", "if False:", "test_assemble_and_sensitivity.py"),
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
    out = HERE.parent / "mutation_check_round6_fixes.json"
    if out.exists():
        shutil.move(out, out.with_name("mutation_check_round6_fixes_previous.json"))
    out.write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))
