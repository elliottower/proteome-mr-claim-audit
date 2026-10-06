"""Mutation check of the extraction-system comparison
(AMENDMENT_01_extraction_system_comparison.md; scripts/extraction_system_comparison.py and
scripts/run_extraction_luna.py): each mutation is applied to a copy of the scripts folder and
tests/test_extraction_system_comparison.py and tests/test_run_extraction_luna.py are run against
it; a mutation is killed when the tests fail. The unmutated copy is run first and must pass.

Runs on Modal (scripts/modal_extraction_system_comparison.py::tests), from the experiment folder:
    python mutation_check_amendment01.py --out <result json>
"""

import argparse
import datetime
import json
import os
import pathlib
import shutil
import subprocess
import tempfile

EXP = pathlib.Path.cwd()
TESTS = ["test_extraction_system_comparison.py", "test_run_extraction_luna.py"]
MC, LX = "extraction_system_comparison.py", "run_extraction_luna.py"

MUTATIONS = [
    (MC, "null_flag=key in null,", "null_flag=False,", "null flag never set"),
    (MC, "measure([(a[k].pair, k in b) for k in sorted(a)]",
     "measure([(a[k].pair, k in a) for k in sorted(a)]", "A-in-B counts every record of A"),
    (MC, "measure([(b[k].pair, k in a) for k in sorted(b)]",
     "measure([(b[k].pair, k in b) for k in sorted(b)]", "B-in-A counts every record of B"),
    (MC, "[(a[k].pair, a[k].direction == b[k].direction) for k in shared]",
     "[(a[k].pair, DIRECTIONAL.get(a[k].direction) == DIRECTIONAL.get(b[k].direction)) "
     "for k in shared]", "direction class read as direction"),
    (MC, "same = [DIRECTIONAL[a[k].direction] == DIRECTIONAL[b[k].direction] for k in both]",
     "same = [a[k].direction == b[k].direction for k in both]",
     "same direction requires the same class"),
    (MC, "if a[k].direction in DIRECTIONAL and b[k].direction in DIRECTIONAL]",
     "if a[k].direction in DIRECTIONAL or b[k].direction in DIRECTIONAL]",
     "directional in either source"),
    (MC, '"opposite_direction": same.count(False),', '"opposite_direction": same.count(True),',
     "opposite direction counts agreements"),
    (MC, "a[k].null_flag == b[k].null_flag", "a[k].null_flag != b[k].null_flag",
     "null flag agreement inverted"),
    (MC, "for c in second if claim_key(c) not in have])", "for c in second])",
     "run-1-first completion pools the two runs"),
    (MC, "if record_id(c) in record_ids]", "if record_id(c) not in record_ids]",
     "restriction keeps the unsampled abstracts"),
    (MC, "outside = sorted({record_id(c) for c in sol_repeat} - sample_ids)", "outside = []",
     "second Sol run outside the sample accepted"),
    (MC, "if (sol_repeat is None) != (sample_ids is None):", "if False:",
     "second Sol run without a sample accepted"),
    (MC, "family_pair_records(restricted(claims, sample_ids), rows)",
     "family_pair_records(claims, rows)", "repeat-sample comparisons on every abstract"),
    (MC, "differing = [k for k in PRIMARY_KEYS if mine[k] != primary[k]]", "differing = []",
     "Sol table never checked against the primary"),
    (MC, '        if exchange.get("status") != 200:\n            failed_http += 1\n'
         '            continue',
     '        if False:\n            failed_http += 1\n            continue',
     "failed HTTP tries priced"),
    (MC, 'record = path.name.split("_attempt")[0]', "record = path.name",
     "no exchange matched to its abstract"),
    (MC, '        if record not in want:\n            other.add(record)\n            continue',
     '        if False:\n            other.add(record)\n            continue',
     "exchanges of records outside the parsed files priced"),
    (MC, '"usd_per_attempted_abstract": usd / totals["abstracts_attempted"]}',
     '"usd_per_attempted_abstract": usd / totals["abstracts_with_a_billable_response"]}',
     "cost divided by the abstracts with a successful response"),
    (MC, 'return {"abstracts_attempted": len(want),',
     'return {"abstracts_attempted": len(billed),',
     "attempted abstracts counted from successful exchanges"),
    (MC, '"abstracts_without_a_billable_response": len(want - billed),',
     '"abstracts_without_a_billable_response": 0,',
     "abstracts without a response not counted"),
    (MC, 'if r["status"] == "extraction_failed")', 'if r["status"] == "ok")',
     "extraction failures read from the successful rows"),
    (MC, "    if set(usages) != set(ROLES):", "    if not set(usages) <= set(ROLES):",
     "a subset of the three usage files accepted"),
    (MC, 'if u.get("role") != role or u.get("model") != ROLES[role]:', "if False:",
     "a usage file of another run accepted"),
    (MC, 'if len({u["attempted_sha256"] for u in usages.values()}) != 1:', "if False:",
     "usage over different abstracts accepted"),
    (MC, "return {**{k: v for k, v in table.items() if k not in VERDICT_KEYS},",
     "return {**table,", "Luna tables reported with their threshold classifications"),
    (MC, "diff[key] = None if ours is None or theirs is None else ours - theirs",
     "diff[key] = None if ours is None or theirs is None else theirs - ours",
     "difference from Sol with the wrong sign"),
    (MC, '"luna_run1": descriptive(h1_h2(run1, rows, n_boot, seed), sol_table),',
     '"luna_run1": h1_h2(run1, rows, n_boot, seed),',
     "Luna run 1 table reported in full"),
    (MC, 'uncached = t["input_tokens"] - t["cached_input_tokens"] - t["cache_write_tokens"]',
     'uncached = t["input_tokens"] - t["cached_input_tokens"]',
     "cache writes priced twice"),
    (MC, '"cache_write": t["cache_write_tokens"] * price["cache_write"] / 1e6',
     '"cache_write": t["cache_write_tokens"] * price["input"] / 1e6',
     "cache writes at the input price"),
    (MC, "num[pair] += bool(hit)", "num[pair] += 1", "every unit counted as a hit"),
    (MC, "[float(den[p]) for p in pairs], n_boot, seed, stream),",
     "[float(den[p]) for p in pairs], n_boot, seed, 0),", "one stream for every share"),
    (MC, "BASE_STREAMS = {name: 100 + 10 * i for", "BASE_STREAMS = {name: 100 + i for",
     "streams of two comparisons overlap"),
    (MC, '"cache_write": 0.125, "output": 0.50}', '"cache_write": 0.125, "output": 5.0}',
     "Luna output price"),
    (MC, '"luna_run1_completed": descriptive(h1_h2(completed, rows, n_boot, seed),',
     '"luna_run1_completed": descriptive(h1_h2(run1 + run2, rows, n_boot, seed),',
     "completion tables from the pooled runs"),
    (MC, '    if path.exists():\n        raise ComparisonError(f"{path} exists',
     '    if False:\n        raise ComparisonError(f"{path} exists', "outputs overwritten"),
    (LX, "if not luna_prompt.startswith(frozen_prompt) or",
     "if frozen_prompt not in luna_prompt or", "frozen prompt anywhere in the Luna prompt"),
    (LX, " or len(luna_prompt) <= len(frozen_prompt):", ":", "no addendum required"),
    (LX, "log = prereg_text.rsplit(LOG_HEADING, 1)[1]", "log = prereg_text",
     "digests read above the log"),
    (LX, "if digest not in log]", "if digest not in log and False]", "gate never refuses"),
    (LX, "if only_here or only_sol or len(sol_ids) != len(record_ids):", "if only_here:",
     "records missing from the Luna run accepted"),
    (LX, 'body["model"] = LUNA_MODEL', 'body["model"] = rx.MODEL', "request sent to Sol"),
    (LX, 'return RAW / TASK / rev / f"run{run}"', "return RAW / TASK / rev",
     "the two runs share a raw folder"),
    (LX, "for attempt in range(1, rx.MAX_SCHEMA_ATTEMPTS + 1):", "for attempt in range(1, 2):",
     "no second attempt after a schema failure"),
    (LX, 'usage.cache_write_tokens += details.get("cache_write_tokens", 0)',
     "usage.cache_write_tokens += 0", "cache writes not recorded"),
    (LX, '"schema": schema, "model": LUNA_MODEL,', '"schema": schema, "model": rx.MODEL,',
     "revision id of the Sol model"),
    (LX, 'f"luna_extraction_{label}_run{run}_{rev}.jsonl"',
     'f"luna_extraction_{label}_{rev}.jsonl"', "the two runs share a parsed file"),
]


def copy(work: pathlib.Path) -> None:
    for folder in ("scripts", "tests", "verification", "prompts"):
        shutil.copytree(EXP / folder, work / folder,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy(EXP / "dataset_dictionary.csv", work / "dataset_dictionary.csv")


def tests_fail(work: pathlib.Path) -> bool:
    proc = subprocess.run(["python", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
                           *TESTS], cwd=work / "tests", capture_output=True, text=True,
                          env={**os.environ, "PYTHONPATH": str(work / "scripts")})
    return proc.returncode != 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp)
        copy(work)
        if tests_fail(work):
            raise SystemExit("the unmutated tests fail")
    results = []
    for target, old, new, label in MUTATIONS:
        with tempfile.TemporaryDirectory() as tmp:
            work = pathlib.Path(tmp)
            copy(work)
            src = work / "scripts" / target
            text = src.read_text()
            if text.count(old) != 1:
                raise SystemExit(f"mutation text not found once: {label}")
            src.write_text(text.replace(old, new))
            results.append({"mutation": label, "file": target, "killed": tests_fail(work)})
    summary = {"written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
               "tests": TESTS, "unmutated_tests_pass": True, "mutations": len(results),
               "killed": sum(r["killed"] for r in results), "results": results}
    a.out.write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
