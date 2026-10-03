"""Version 17 rules (H2b, the resolvable share, the registered secondaries, the record
metadata and the external-list check): each deliberate change of a rule must make a test or a
synthetic dry run fail. Runs on Modal on copies of scripts/ and tests/; fixtures and committed
tables only.

    modal run docs/stage0_build/mutation_check_v17.py
"""
import json
import pathlib
import subprocess

import modal

VOLUME = "proteome-mr-claim-audit-inputs"
MOUNT = pathlib.Path("/vol")
REMOTE = MOUNT / "02_claims_meta"
EXP = pathlib.Path("/exp")
HERE = pathlib.Path(__file__).resolve()
LOCAL_EXP = HERE.parents[2] / "experiments" / "02_claims_meta" if modal.is_local() else EXP
IGNORE = ["__pycache__", "*.pyc", ".pytest_cache"]
REG, SEC, JOIN, META = ("test_registry.py", "test_registry_secondaries.py",
                        "test_secondary_joins.py", "test_record_metadata.py")
BIO = "dry_run_biology_synthetic.py"
# (script, text, replacement, test file or dry-run script that must fail)
M = [
 ("build_registry.py", 'if relation in OVERLAP or release_identity(na, nb) == "identical":', "if relation in OVERLAP:", REG),
 ("build_registry.py", 'states.append("disjoint" if relation == "disjoint" else "unclear")', 'states.append("unclear")', REG),
 ("build_registry.py", 'return "known_not_overlapping" if "disjoint" in states else "unresolved"', 'return "unresolved"', REG),
 ("build_registry.py", 'return all(names and all(m.state == "unique" for m in names)', 'return all(names and all(m.state != "not_stated" for m in names)', REG),
 ("build_registry.py", 'over = np.array([c == "known_overlapping" for c in h2b], dtype=float)', 'over = np.array([c != "known_not_overlapping" for c in h2b], dtype=float)', REG),
 ("build_registry.py", '"h2b_verdict": h2_verdict(boot, "h2b"),', '"h2b_verdict": h2_verdict(boot),', REG),
 ("build_registry.py", 'two_verdict_reading(h2_verdict(boot), h2_verdict(boot, "h2b")),', "two_verdict_reading(h2_verdict(boot), h2_verdict(boot)),", REG),
 ("build_registry.py", "BONFERRONI_LEVELS = (0.0125, 0.9875)", "BONFERRONI_LEVELS = (0.025, 0.975)", REG),
 ("build_registry.py", "            den[at[p]] += denominator[j]", "            den[at[p]] = denominator[j]", REG),
 ("build_registry.py", 'and est["h2_resolvable_share"] > 0.5),', 'and est["h2_resolvable_share"] >= 0.5),', REG),
 ("build_registry.py", '("unresolved", "unresolved"): "abstracts_do_not_identify_sources_for_enough_pairs",', '("unresolved", "unresolved"): "majority_on_identical_releases",', REG),
 ("build_registry.py", '    return READINGS.get((h2, h2b), "not_nested")', '    return READINGS.get((h2, h2b), "majority_on_identical_releases")', REG),
 ("registry_secondaries.py", 'if pq == oc == "identical_release":', 'if pq == "identical_release":', SEC),
 ("registry_secondaries.py", "flags.append(float(bool(up) and bool(null)))", "flags.append(float(bool(null)))", SEC),
 ("registry_secondaries.py", 'return ([float(sum(a == agree and f[field] == "differ" for a, f in rows))', 'return ([float(sum(f[field] == "differ" for a, f in rows))', SEC),
 ("registry_secondaries.py", '            == "earlier" for g in d if g is not f)]', '            != "later" for g in d if g is not f)]', SEC),
 ("registry_secondaries.py", "        if len(fams) < 2 or period_of(years[1]) is None:\n            continue\n        rows = out[period_of(years[1])]", "        if len(fams) < 2 or period_of(years[0]) is None:\n            continue\n        rows = out[period_of(years[0])]", SEC),
 ("registry_secondaries.py", "already = sum(first[p] < y for p in claimed[y])", "already = sum(first[p] <= y for p in claimed[y])", SEC),
 ("registry_secondaries.py", 'unique = {s: bool(sides[s]) and all(m.state == "unique" for m in sides[s].values())', 'unique = {s: bool(sides[s]) and any(m.state == "unique" for m in sides[s].values())', SEC),
 ("registry_secondaries.py", "pairs = [{f: fp for f, fp in fams.items() if directional(fp)} for fams in registry.values()]", "pairs = [{f: fp for f, fp in fams.items()} for fams in registry.values()]", SEC),
 ("registry_secondaries.py", '        if (len(of_rows) != 1 or "mixed" in of_rows', "        if (len(of_rows) != 1", SEC),
 ("registry_secondaries.py", "top = sorted(counts, reverse=True)[:math.ceil(0.10 * len(counts))]", "top = sorted(counts, reverse=True)[:math.floor(0.10 * len(counts))]", SEC),
 ("registry_secondaries.py", "TOP_N = 20", "TOP_N = 10", SEC),
 ("registry_secondaries.py", '                public_date(meta, f), public_date(meta, later)) == "earlier"]', '                public_date(meta, f), public_date(meta, later)) != "later"]', SEC),
 ("registry_secondaries.py", '    ids = [*meta[family]["registry_records"], *meta[family]["dating_records"]]', '    ids = [*meta[family]["registry_records"]]', SEC),
 ("registry_secondaries.py", "    defined = total > 0\n    return {\"interval\": quantiles(n[idx].sum(axis=1)[defined] / total[defined]),", "    defined = total >= 0\n    return {\"interval\": quantiles(n[idx].sum(axis=1)[defined] / total[defined]),", SEC),
 ("registry_secondaries.py", 'by_k["3_or_more" if k >= 3 else str(k)][t.wording_class] += 1', 'by_k["3_or_more" if k >= 2 else str(k)][t.wording_class] += 1', SEC),
 ("registry_secondaries.py", "        with_list = [r for r in rows if r[2]]", "        with_list = list(rows)", SEC),
 ("registry_secondaries.py", '"agree": DIRECTIONAL[a.direction] == DIRECTIONAL[b.direction]}', '"agree": True}', SEC),
 ("registry_secondaries.py", "        multi = [f for f in pairs if len(f) >= 2]\n        with_two", "        multi = [f for f in pairs if len(f) >= 1]\n        with_two", BIO),
 ("registry_secondaries.py", '        rows["contradicting_share"].append(float(contradicting(fams)))', '        rows["contradicting_share"].append(float(significance_discordant(fams)))', SEC),
 ("hub_proteins.py", "            n += minimum_cover(list(sets)) >= HUB_MIN_AREAS", "            n += 1", JOIN),
 ("hub_proteins.py", "    counted = [c for c in counted if area_of[c.outcome_id]]", "    counted = list(counted)", JOIN),
 ("hub_proteins.py", "[areas[i] for i in rng.permutation(len(areas))]", "[areas[i] for i in range(len(areas))]", JOIN),
 ("drug_joins.py", '    rows = [(i, a) for i, a in claims if a in ("concordant", "discordant")]', "    rows = [(i, a) for i, a in claims if a is not None]", JOIN),
 ("drug_joins.py", '    drug_decrease = sum((i if a == "concordant" else opposite[i]) == "decrease"', '    drug_decrease = sum(i == "decrease"', JOIN),
 ("pathway_enrichment.py", "NAMING_Q, NAMING_MIN_CLAIMED = 0.05, 3", "NAMING_Q, NAMING_MIN_CLAIMED = 0.05, 2", JOIN),
 ("pathway_enrichment.py", "named_in_text=qv < NAMING_Q and len(inside & kept[p]) >= NAMING_MIN_CLAIMED)", "named_in_text=len(inside & kept[p]) >= NAMING_MIN_CLAIMED)", JOIN),
 ("reference_screen.py", '    if fp.pqtl and all(m.state in ("unique", "release_ambiguous") for m in fp.pqtl):', '    if fp.pqtl and all(m.state == "unique" for m in fp.pqtl):', JOIN),
 ("reference_screen.py", "    if any(c in zheng_rows for m in fp.pqtl for c in m.candidates):", "    if all(c in zheng_rows for m in fp.pqtl for c in m.candidates):", JOIN),
 ("sensitivity_analyses.py", '    return [c if c.dataset_attribution == "claim_specific" else c.model_copy(update=blank)', '    return [c if c.dataset_attribution != "unclear" else c.model_copy(update=blank)', JOIN),
 ("sensitivity_analyses.py", "    return max(counts) if counts else None", "    return min(counts) if counts else None", JOIN),
 ("sensitivity_analyses.py", "HIGH_FLOOR = 1000", "HIGH_FLOOR = 100", BIO),
 ("assemble_screening_set.py", "            journal=next((r.journal for r in members if r.journal), None)))", "            journal=members[-1].journal))", JOIN),
 ("record_metadata.py", '                  if a.get("author_position") == "first"), None)', '                  if a.get("author_position") == "last"), None)', META),
 ("record_metadata.py", '        return institutions[0].get("country_code") or None', '        return institutions[-1].get("country_code") or None', META),
 ("record_metadata.py", '            s for s in SOURCES if any(st.startswith(f"{s}/") for st in record["streams"]))', "            s for s in SOURCES)", META),
 ("record_metadata.py", "            has_reference_list=None if work is None else bool(refs),", "            has_reference_list=bool(refs),", META),
 ("record_metadata.py", '    if record.get("doi"):\n        return "doi", norm_doi(record["doi"])\n    if record.get("pmid"):\n        return "pmid", norm_pmid(record["pmid"])', '    if record.get("pmid"):\n        return "pmid", norm_pmid(record["pmid"])\n    if record.get("doi"):\n        return "doi", norm_doi(record["doi"])', META),
 ("external_lists.py", "        dated = [s for s in listed if s.year is not None and WINDOW[0] <= s.year <= WINDOW[1]]", "        dated = list(listed)", META),
 ("external_lists.py", "        found = [s for s in dated if (s.id_kind, s.identifier) in by_search]", "        found = [s for s in dated if (s.id_kind, s.identifier) in by_any]", META),
 ("external_lists.py", "        years[ident] = year if known is None else known if year is None else min(known, year)", "        years[ident] = year if known is None else known if year is None else max(known, year)", META),
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
app = modal.App("proteome-mr-mutation-check-v17", image=image)


@app.function(volumes={str(MOUNT): vol}, timeout=7200, cpu=4.0, memory=8192)
def check() -> dict:
    env = {"PYTHONPATH": str(EXP / "scripts"), "PATH": "/usr/local/bin:/usr/bin:/bin",
           "PYTHONDONTWRITEBYTECODE": "1"}

    def run(test: str, n: int) -> subprocess.CompletedProcess:
        if test.startswith("dry_run"):
            return subprocess.run(["python", f"scripts/{test}", "--out", f"/tmp/mutation_{n}"],
                                  cwd=EXP, capture_output=True, text=True, env=env)
        return subprocess.run(["python", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
                               test], cwd=EXP / "tests", capture_output=True, text=True, env=env)

    results = []
    for n, (name, old, new, test) in enumerate(M):
        target = EXP / "scripts" / name
        text = target.read_text()
        if text.count(old) != 1:
            results.append({"file": name, "old": old, "state": f"not_applied ({text.count(old)})"})
            continue
        target.write_text(text.replace(old, new, 1))
        r = run(test, n)
        target.write_text(text)
        results.append({"file": name, "old": old, "new": new, "test": test,
                        "state": "killed" if r.returncode == 1 else
                        "survived" if r.returncode == 0 else f"error {r.returncode}",
                        "tail": (r.stdout + r.stderr)[-300:] if r.returncode not in (0, 1) else ""})
    base = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                          cwd=EXP / "tests", capture_output=True, text=True, env=env)
    dry = run(BIO, 9999)
    return {"mutations": len(M), "killed": sum(r["state"] == "killed" for r in results),
            "not_killed": [r for r in results if r["state"] != "killed"],
            "unmutated_suite_returncode": base.returncode, "unmutated_tail": base.stdout[-600:],
            "unmutated_biology_dry_run_returncode": dry.returncode}


@app.local_entrypoint()
def main() -> None:
    result = check.remote()
    out = HERE.parent / "mutation_check_v17.json"
    if out.exists():
        raise FileExistsError(f"{out} exists; archive it before rerunning")
    out.write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))
