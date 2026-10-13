import json
import pathlib
import subprocess

import coding_queue_v2 as q2

HERE = pathlib.Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
P1 = "experiments/02_claims_meta"
INPUTS = [f"{P1}/outputs/verification_amendment02/amended_primary/"
          "sol_extraction_search_0b97103cd7a4_restored/claim_checks.jsonl",
          f"{P1}/outputs/verification_amendment02/amended_primary/"
          "sol_extraction_chase1_0b97103cd7a4_restored/claim_checks.jsonl",
          f"{P1}/outputs/verification/sol_extraction_chase2_0b97103cd7a4/claim_checks.jsonl",
          f"{P1}/outputs/verification/sol_extraction_chase3_0b97103cd7a4/claim_checks.jsonl"]
REG = f"{P1}/outputs/registry/2026-10-03_amended_primary_coded_a"


def test_paths_are_relative_to_the_repository():
    assert q2.REPO == REPO
    assert q2.relative(REPO / P1 / "dataset_dictionary.csv") == f"{P1}/dataset_dictionary.csv"


def test_the_second_version_rebuilds_the_committed_queue_with_no_local_path(tmp_path):
    out = tmp_path / "queue.json"
    run = subprocess.run(["python", str(HERE / "scripts" / "coding_queue_v2.py"),
                          "--coded", f"{REG}/registry_claims.jsonl",
                          "--plain", f"{REG}/registry_claims_without_manual_coding.jsonl",
                          "--checks", *INPUTS, "--out", str(out)],
                         capture_output=True, text=True, cwd=REPO)
    assert run.returncode == 0, run.stderr[-2000:]
    got = json.loads(out.read_text())
    committed = json.loads((HERE / "outputs" / "coding_queue_2026-10-13.json").read_text())
    for d in (got, committed):
        d.pop("written_utc")
    assert got == committed
    assert all(not k.startswith("/") for k in got["inputs_sha256"])
