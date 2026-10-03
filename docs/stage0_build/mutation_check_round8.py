"""The round-8 rules (3 October 2026): H2 and H2b verdicts on the observed finite-corpus bounds,
release identity undetermined under unclear attribution, overlap from claim-specific names,
the resolvable share, claim dates for the date-ordered secondaries, the accounting table and
the family–pair-collapsed hub sensitivity. Each deliberate change must make a test fail. Runs
on Modal on copies of scripts/ and tests/; fixtures and committed tables only.

    modal run docs/stage0_build/mutation_check_round8.py
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
R, S, H, I = ("test_registry.py", "test_registry_secondaries.py", "test_hub_proteins.py",
              "test_registry_indices.py")
M = [
 ("build_registry.py", "    if not (a.attribution_clear and b.attribution_clear):\n        return \"undetermined\"",
  "    if not (a.attribution_clear or b.attribution_clear):\n        return \"undetermined\"", R),
 ("build_registry.py", "    if not (a.attribution_clear and b.attribution_clear):\n        return \"undetermined\"",
  "    if False:\n        return \"undetermined\"", R),
 ("build_registry.py", "    return all(fp.attribution_clear and names and all(m.state == \"unique\" for m in names)",
  "    return all(names and all(m.state == \"unique\" for m in names)", R),
 ("build_registry.py", "    if lower > 0.5:", "    if lower >= 0.5:", R),
 ("build_registry.py", "    if upper <= 0.5:", "    if upper < 0.5:", R),
 ("build_registry.py", "        if sa and sb and compare_side(sa, sb) in OVERLAP:", "        if sa and sb:", R),
 ("build_registry.py", "    if not (fa.attribution_clear and fb.attribution_clear):\n        sa =",
  "    if False:\n        sa =", R),
 ("build_registry.py", "    if relation == \"disjoint\":\n        return \"disjoint\"",
  "    if relation in (\"disjoint\", \"unclear\"):\n        return \"disjoint\"", R),
 ("build_registry.py", "\"neither_share_placed_on_one_side_of_one_half\"",
  "\"abstracts_do_not_identify_sources_for_enough_pairs\"", R),
 ("build_registry.py", "        \"h2_verdict\": h2_verdict(est),", "        \"h2_verdict\": h2_verdict({}),", R),
 ("registry_secondaries.py", "        years = [dates[(f, pair)].value.year for f in fams]",
  "        years = [year_of(meta, f) for f in fams]", S),
 ("registry_secondaries.py", "        years = sorted(dates[(f, pair)].value.year for f in fams)",
  "        years = sorted(min(d.value.year for (g, _), d in dates.items() if g == f) for f in fams)", S),
 ("registry_secondaries.py", "                dates[(f, pair)], dates[(later, pair)]) == \"earlier\"]",
  "                dates[(later, pair)], dates[(f, pair)]) == \"earlier\"]", S),
 ("registry_secondaries.py", "            date_order(dates[(f.family_id, pair)], dates[(g.family_id, pair)])\n            == \"earlier\"",
  "            date_order(dates[(f.family_id, pair)], dates[(g.family_id, pair)])\n            != \"later\"", S),
 ("registry_secondaries.py", "        if record is None:\n            raise", "        if False:\n            raise", S),
 ("registry_secondaries.py", "    if novelty is None:\n        raise", "    if False:\n        raise", S),
 ("registry_secondaries.py", "                     * sum(b.direction == \"nonsignificant_only\" for b in f.values())",
  "                     + sum(b.direction == \"nonsignificant_only\" for b in f.values())", S),
 ("registry_secondaries.py", "    multi_edges = sum(len(edges(f)) for f in multi.values())",
  "    multi_edges = len(multi)", S),
 ("registry_secondaries.py", "            clear = a.attribution_clear and b.attribution_clear\n",
  "            clear = True\n", S),
 ("registry_indices.py", "    if not attribution_clear:\n        return \"undetermined\"",
  "    if False:\n        return \"undetermined\"", I),
 ("registry_indices.py", "            \"h2b_verdict\": h2_verdict(est, \"h2b\"),",
  "            \"h2b_verdict\": h2_verdict(est),", I),
 ("hub_proteins.py", "        if key not in seen:", "        if True:", H),
 ("hub_proteins.py", "    counted = counted_claims(claims, tags, count_null, collapse)",
  "    counted = counted_claims(claims, tags, count_null)", H),
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
app = modal.App("proteome-mr-mutation-check-round8", image=image)


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
    out = HERE.parent / "mutation_check_round8.json"
    if out.exists():
        shutil.move(out, out.with_name("mutation_check_round8_previous.json"))
    out.write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))
