"""Second pass of the live smoke run (2 October 2026): the smoke-window switch and its guards,
the documented replacement of a recorded file, and the relative paths of a stored tool output.
Each deliberate change must make a test fail. Runs on Modal on copies of scripts/ and tests/;
fixtures and committed tables only.

    modal run docs/stage0_build/mutation_check_smoke_window.py
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
 ("smoke_guard.py", "    if not label.startswith(SMOKE_PREFIX) or not label.replace(\"_\", \"\").isalnum():", "    if not label.replace(\"_\", \"\").isalnum():", "test_smoke_window.py"),
 ("smoke_guard.py", "    if not label.startswith(SMOKE_PREFIX) or not label.replace(\"_\", \"\").isalnum():", "    if not label.startswith(SMOKE_PREFIX):", "test_smoke_window.py"),
 ("smoke_guard.py", "    if out.parent != REGISTRY_ROOT or not out.name.startswith(label):", "    if not out.name.startswith(label):", "test_smoke_window.py"),
 ("smoke_guard.py", "    if out.parent != REGISTRY_ROOT or not out.name.startswith(label):", "    if out.parent != REGISTRY_ROOT:", "test_smoke_window.py"),
 ("smoke_guard.py", "    if label is not None and not name.startswith(label):", "    if False:", "test_smoke_window.py"),
 ("smoke_guard.py", "    if label is None and name.startswith(SMOKE_PREFIX):", "    if False:", "test_smoke_window.py"),
 ("smoke_guard.py", "    if bool(smoke_label) != run_name.startswith(SMOKE_PREFIX) or not run_name.startswith(", "    if not run_name.startswith(", "test_smoke_window.py"),
 ("smoke_guard.py", " or not run_name.startswith(\n            smoke_label):", ":", "test_smoke_window.py"),
 ("assemble_registry.py", "        if year >= WINDOW_START:\n            raise SmokeWindowError(f\"smoke window: a family first public {date.value}\")\n", "", "test_smoke_window.py"),
 ("assemble_registry.py", "            raise SmokeWindowError(f\"smoke window: a family first public {date.value}\")\n        return \"confirmatory\"", "            raise SmokeWindowError(f\"smoke window: a family first public {date.value}\")\n        return \"outside\"", "test_smoke_window.py"),
 ("assemble_registry.py", "        if late:\n            raise SmokeWindowError(f\"smoke window: records first public in 2019 or later: \"", "        if False:\n            raise SmokeWindowError(f\"smoke window: records first public in 2019 or later: \"", "test_smoke_window.py"),
 ("assemble_registry.py", "late = sorted(r.record_id for r in records if r.first_public.value.year >= WINDOW_START)", "late = sorted(r.record_id for r in records if r.first_public.value.year > WINDOW_START)", "test_smoke_window.py"),
 ("assemble_registry.py", "            window=window_of(dates[fam], smoke_window),", "            window=window_of(dates[fam]),", "test_smoke_window.py"),
 ("assemble_registry.py", "    report: dict = {**({\"smoke_window\": True} if smoke_window else {}),", "    report: dict = {**{},", "test_smoke_window.py"),
 ("assemble_registry.py", "    if bool(assembly.report.get(\"smoke_window\")) != (smoke_label is not None):", "    if False:", "test_smoke_window.py"),
 ("assemble_registry.py", "    if smoke_label is not None:\n        check_smoke_folder(smoke_label, out)\n    elif", "    if False:\n        check_smoke_folder(smoke_label, out)\n    elif", "test_smoke_window.py"),
 ("assemble_registry.py", "    elif out.resolve().name.startswith(SMOKE_PREFIX):\n        raise SmokeWindowError(f\"{out} is a smoke folder; give --smoke-label\")\n", "", "test_smoke_window.py"),
 ("assemble_registry.py", "         **({\"smoke_label\": smoke_label} if smoke_label is not None else {}),", "         **{},", "test_smoke_window.py"),
 ("sensitivity_analyses.py", "        kw.setdefault(\"smoke_window\", smoke_window)\n", "", "test_smoke_window.py"),
 ("sensitivity_analyses.py", "            without_phenotype_xrefs(collision), manual=manual,\n            smoke_window=smoke_window).claims[\"confirmatory\"]),", "            without_phenotype_xrefs(collision), manual=manual).claims[\"confirmatory\"]),", "test_smoke_window.py"),
 ("sensitivity_analyses.py", "    if smoke_window:\n        out[\"smoke_window\"] = True\n", "", "test_smoke_window.py"),
 ("funnel.py", "    check_smoke_output(a.assembly, a.out.resolve().name)\n", "", "test_smoke_window.py"),
 ("manual_dataset_coding.py", "            check_smoke_output(path.parent, a.out.resolve().name)\n", "            pass\n", "test_smoke_window.py"),
 ("fetch_fulltext.py", "        check_smoke_output(a.families_meta.parent, a.out.resolve().name)\n", "", "test_smoke_window.py"),
 ("stage_record.py", "now != replaced.get(\n                    (manifest.run_id, entry.path, entry.sha256)):", "(\n                    (manifest.run_id, entry.path, entry.sha256)) not in replaced:", "test_stage_record.py"),
 ("stage_record.py", "    replaced = {(r.run_id, r.path, r.recorded_sha256): r.replaced_sha256", "    replaced = {(manifest_run, r.path, r.recorded_sha256): r.replaced_sha256\n                for manifest_run in (\"run_1\", \"run_2\")", "test_stage_record.py"),
 ("stage_record.py", "                if entry.sha256 != current:\n                    raise StageRecordError(f\"{path} no longer has the bytes {manifest.run_id} \"", "                if False:\n                    raise StageRecordError(f\"{path} no longer has the bytes {manifest.run_id} \"", "test_stage_record.py"),
 ("stage_record.py", "    if not naming:\n        raise StageRecordError(f\"no manifest names {path}; edit it without `replace`\")\n", "", "test_stage_record.py"),
 ("stage_record.py", "    if kept.exists():\n        raise StageRecordError(f\"{kept} exists; an original is archived once\")\n", "", "test_stage_record.py"),
 ("stage_record.py", "    if new_sha == current:\n        raise StageRecordError(f\"{path}: the new bytes are the recorded bytes\")\n", "", "test_stage_record.py"),
 ("stage_record.py", "    if not reason.strip():\n        raise StageRecordError(\"a replacement needs its reason\")\n", "", "test_stage_record.py"),
 ("stage_record.py", "    kept.write_bytes(path.read_bytes())\n", "    kept.write_bytes(new_bytes)\n", "test_stage_record.py"),
 ("stage_record.py", "                  and p.name != REPLACED_NAME)", "                  )", "test_stage_record.py"),
 ("stage_record.py", "    if target.name == REPLACED_NAME:\n        raise StageRecordError(f\"a run id cannot be {REPLACED_NAME.removesuffix('.json')}\")\n", "", "test_stage_record.py"),
 ("verify_spans.py", "    return text.replace(f\"{root}/\", \"\")", "    return text", "test_verify_spans.py"),
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
    out = HERE.parent / "mutation_check_smoke_window.json"
    if out.exists():
        shutil.move(out, out.with_name("mutation_check_smoke_window_previous.json"))
    out.write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))
