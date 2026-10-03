"""Dress-rehearsal fixes (2 October 2026): each deliberate change of a new guard must make a test fail. Runs on
Modal on copies of scripts/ and tests/; fixtures and committed tables only.

    modal run docs/stage0_build/mutation_check_dress_rehearsal.py
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
 ("stage_record.py", "        if path == local_root:\n            remote = remote_root  # one local file mapped to one volume file\n        elif path.is_relative_to(local_root):", "        if path.is_relative_to(local_root):", "test_stage_record.py"),
 ("stage_record.py", "    if done.returncode != 0:\n        raise StageRecordError(f\"`prereg check` did not pass for {path}:\\n{done.stdout}\")\n", "", "test_stage_record.py"),
 ("stage_record.py", "    if not all(found):\n        raise StageRecordError(f\"{path} carries no freeze header; run `prereg freeze` first\")\n", "    if not all(found):\n        return PlanRecord(plan=str(path), frozen_at_commit=\"\", plan_sha256=\"\", frozen=\"\")\n", "test_stage_record.py"),
 ("stage_record.py", "            if getattr(recorded, field) != getattr(now, field)]", "            if False]", "test_stage_record.py"),
 ("stage_record.py", "    if target.exists():\n        raise StageRecordError(f\"{target} exists; the freeze is recorded once\")\n", "", "test_stage_record.py"),
 ("stage_record.py", "if not p.name.endswith((VOLUME_LISTING, PLAN_SUFFIX)))", "if not p.name.endswith(VOLUME_LISTING))", "test_stage_record.py"),
 ("stage_record.py", "    for suffix in (VOLUME_LISTING, PLAN_SUFFIX):", "    for suffix in (VOLUME_LISTING,):", "test_stage_record.py"),
 ("stage_record.py", "commit, digest, date = (m.group(1) for m in found)", "digest, commit, date = (m.group(1) for m in found)", "test_stage_record.py"),
 ("run_extraction.py", "    if out.exists():\n        raise ExtractionRunError(f\"{out} exists; archive it or choose another label\")\n", "", "test_rerun_and_pinned_file_guards.py"),
 ("apply_eligibility.py", "    if out.exists():\n        raise FileExistsError(f\"{out} exists; archive it before rerunning\")\n", "", "test_rerun_and_pinned_file_guards.py"),
 ("build_registry.py", "    if digest != spec[\"sha256\"]:", "    if False:", "test_rerun_and_pinned_file_guards.py"),
 ("build_registry.py", "    if not path.is_file():\n        raise PinnedFileError(f\"{spec['file']} missing; fetch it from the Modal volume \"\n                              \"(inputs/README_MOVED_TO_MODAL.md)\")\n", "", "test_rerun_and_pinned_file_guards.py"),
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
    out = HERE.parent / "mutation_check_dress_rehearsal.json"
    if out.exists():
        shutil.move(out, out.with_name("mutation_check_dress_rehearsal_previous.json"))
    out.write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))
