"""Live smoke run fixes (2 October 2026): each deliberate change of a new guard must make a test
fail. Runs on Modal on copies of scripts/ and tests/; fixtures and committed tables only.

    modal run docs/stage0_build/mutation_check_live_smoke.py
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
 ("run_search.py", "    if not SMOKE_EARLIEST <= start <= end <= SMOKE_LATEST:", "    if not SMOKE_EARLIEST <= start <= end:", "test_search_run.py"),
 ("run_search.py", "    if not SMOKE_EARLIEST <= start <= end <= SMOKE_LATEST:", "    if not start <= end <= SMOKE_LATEST:", "test_search_run.py"),
 ("run_search.py", "SMOKE_EARLIEST, SMOKE_LATEST = datetime.date(2014, 1, 1), datetime.date(2018, 12, 31)", "SMOKE_EARLIEST, SMOKE_LATEST = datetime.date(2014, 1, 1), datetime.date(2019, 12, 31)", "test_search_run.py"),
 ("run_search.py", "        if stored.get(\"smoke_window\") != smoke_dates:", "        if False:", "test_search_run.py"),
 ("run_search.py", "    if window is not None and not smoke:\n        raise SearchRunError(\"a window is given to a smoke run only\")\n", "", "test_search_run.py"),
 ("run_search.py", "    chosen = (window or SMOKE_WINDOW) if smoke else None", "    chosen = SMOKE_WINDOW if smoke else None", "test_search_run.py"),
 ("citation_chase.py", "f\"openalex:{'|'.join(batch)}{limit}\"", "f\"openalex:{'|'.join(batch)}{floor}\"", "test_citation_chase.py"),
 ("citation_chase.py", "    return [s for s in screening if s.first_public.value <= end]", "    return list(screening)", "test_citation_chase.py"),
 ("record_metadata.py", "                  >= cc.PUBLISHED_FROM)", "                  > cc.PUBLISHED_FROM)", "test_record_metadata.py"),
 ("record_metadata.py", "    if late:\n        raise RecordMetadataError(f\"--smoke: records first public in the registered window: \"", "    if False:\n        raise RecordMetadataError(f\"--smoke: records first public in the registered window: \"", "test_record_metadata.py"),
 ("fetch_fulltext.py", "        if late:\n            raise FullTextError(f\"records first public on or after {before}: {late[:5]}\")\n", "", "test_fetch_fulltext.py"),
 ("fetch_fulltext.py", "    if target.exists() and target.read_bytes() != x.content:\n        raise FullTextError(f\"{target} exists with other bytes; archive it before refetching\")\n", "", "test_fetch_fulltext.py"),
 ("verify_spans.py", "    if recorded is not None and digest != recorded:", "    if False:", "test_verify_spans.py"),
 ("verify_spans.py", "    recorded = rec.get(f\"{text_field}_sha256\")", "    recorded = rec[f\"{text_field}_sha256\"]", "test_verify_spans.py"),
 ("verify_spans.py", "    if re.fullmatch(r\"W\\d+\", record_id):\n        return f\"https://openalex.org/{record_id}\"\n", "", "test_verify_spans.py"),
 ("claim_tags.py", "    if len(set(ids)) != len(ids):\n        raise ValueError(f\"{[str(p) for p in paths]}: a record id occurs twice\")\n", "", "test_claim_tags.py"),
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
    out = HERE.parent / "mutation_check_live_smoke.json"
    if out.exists():
        shutil.move(out, out.with_name("mutation_check_live_smoke_previous.json"))
    out.write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))
