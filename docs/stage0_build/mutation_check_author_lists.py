"""Mutation check of the author-supplied-list rule (scripts/author_lists.py and the override in
scripts/pathway_enrichment.py): each mutation is applied to a copy of the scripts folder and
tests/test_author_lists.py is run against it; a mutation is killed when the tests fail.

Usage, from experiments/02_claims_meta:
    uv run --with pytest==8.4.2 --with pydantic==2.13.5 --with numpy==2.5.3 \
        python ../../docs/stage0_build/mutation_check_author_lists.py
"""

import datetime
import json
import pathlib
import shutil
import subprocess
import tempfile

EXP = pathlib.Path.cwd()
OUT = pathlib.Path(__file__).resolve().with_name("mutation_check_author_lists.json")

MUTATIONS = [
    ("author_lists.py", "r.pinned_utc < cut", "r.pinned_utc <= cut", "pin at the cutoff counts as before"),
    ("author_lists.py", "if cut is None or r.pinned_utc", "if r.pinned_utc", "no-cutoff branch removed"),
    ("author_lists.py", 'STAGE5_RUN_PREFIX = "s5_biology_"', 'STAGE5_RUN_PREFIX = "s5_"', "any stage-5 run sets the cutoff"),
    ("author_lists.py", "    return min(times, default=None)\n\n\ndef output_cutoff", "    return max(times, default=None)\n\n\ndef output_cutoff", "latest ledger run used"),
    ("author_lists.py", 'if d.get("window", "confirmatory") == "confirmatory":', "if True:", "update-window outputs set the cutoff"),
    ("author_lists.py", "    return min(found)", "    return max(found)", "later of ledger and outputs used"),
    ("author_lists.py", "        if r.dictionary_row not in ELIGIBLE_ROWS:", "        if False:", "any row may be replaced"),
    ("author_lists.py", "        if len(r.sha256) != 64:", "        if False:", "no sha256 required"),
    ("author_lists.py", "        if rows:\n            raise AuthorListError", "        if False:\n            raise AuthorListError", "joins run without a decisions file"),
    ("pathway_enrichment.py", "        if name in overrides:\n", "        if False:\n", "override ignored"),
    ("pathway_enrichment.py", 'if cell and (cell == r["assay_list"] or name in overrides):', 'if cell and cell == r["assay_list"]:', "coverage rule skipped for a supplied list"),
]


def main() -> None:
    results = []
    for target, old, new, label in MUTATIONS:
        with tempfile.TemporaryDirectory() as tmp:
            work = pathlib.Path(tmp)
            shutil.copytree(EXP / "scripts", work / "scripts")
            shutil.copytree(EXP / "tests", work / "tests")
            shutil.copytree(EXP / "verification", work / "verification")
            shutil.copy(EXP / "dataset_dictionary.csv", work / "dataset_dictionary.csv")
            src = work / "scripts" / target
            text = src.read_text()
            if text.count(old) != 1:
                raise SystemExit(f"mutation text not found once: {label}")
            src.write_text(text.replace(old, new))
            proc = subprocess.run(["python", "-m", "pytest", "-q", "-x",
                                   "test_author_lists.py"], cwd=work / "tests",
                                  capture_output=True, text=True)
            results.append({"mutation": label, "file": target, "killed": proc.returncode != 0})
    summary = {"written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
               "mutations": len(results), "killed": sum(r["killed"] for r in results),
               "results": results}
    OUT.write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
