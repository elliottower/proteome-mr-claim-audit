import json
import os
import pathlib
import shutil
import subprocess

import pytest

import dry_run_biology_synthetic as dry
import sensitivity_analyses as sa
import sensitivity_checkpoints as ck
from dataset_relations import load_rows
from ontology_graph import load_graph

N_BOOT = 60


@pytest.fixture(scope="module")
def study(tmp_path_factory):
    records = dry.search_records()
    decisions = {rid: {"decision": d, "flags": flags, "n_proteins_tested": dry.TESTED[rid]}
                 for rid, (d, flags) in dry.DECISIONS.items()}
    rows, checks = dry.extraction_and_checks()
    status = {r["pmid"]: r["status"] for r in rows}
    resources = dry.write_resources(tmp_path_factory.mktemp("study") / "resources")
    return (records, decisions, status, checks, dry.HGNC_UNIPROT, {},
            load_graph(resources.ontology_edges), load_rows())


def run(study):
    return sa.run(*study, n_boot=N_BOOT, chased=dry.CHASED)


def test_a_checkpointed_run_gives_the_json_of_the_registered_run_and_restores_the_module(
        study, tmp_path):
    plain = json.dumps(run(study))
    originals = [getattr(sa, n) for n in ck.NAMES]
    with ck.checkpointed(tmp_path / "s") as calls:
        made = run(study)
    assert json.dumps(made) == plain
    assert [getattr(sa, n) for n in ck.NAMES] == originals
    assert len(calls) > 15 and {c[2] for c in calls} == {"computed"}
    assert {c[1] for c in calls} == set(ck.NAMES)
    assert len(list((tmp_path / "s").glob("call_*.json"))) == len(calls)
    assert not list((tmp_path / "s").glob("*.partial"))


def test_a_run_stopped_part_way_resumes_from_the_stored_calls_and_gives_the_same_json(
        study, tmp_path):
    plain = json.dumps(run(study))
    commits = []

    def stop_after_five():
        commits.append(1)
        if len(commits) == 5:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt), ck.checkpointed(tmp_path / "s", stop_after_five):
        run(study)
    assert len(list((tmp_path / "s").glob("call_*.json"))) == 5
    assert getattr(sa, "tables").__module__ == "build_registry"
    with ck.checkpointed(tmp_path / "s") as calls:
        resumed = run(study)
    assert json.dumps(resumed) == plain
    assert [c[2] for c in calls[:5]] == ["stored"] * 5
    assert {c[2] for c in calls[5:]} == {"computed"}
    with ck.checkpointed(tmp_path / "s") as again:
        assert json.dumps(run(study)) == plain
    assert {c[2] for c in again} == {"stored"}


def test_a_stored_call_for_another_input_or_another_function_stops_the_run(study, tmp_path):
    with ck.checkpointed(tmp_path / "s"):
        run(study)
    with pytest.raises(ck.CheckpointError), ck.checkpointed(tmp_path / "s"):
        sa.run(*study, n_boot=N_BOOT + 1, chased=dry.CHASED)
    first = sorted((tmp_path / "s").glob("call_000_*.json"))[0]
    first.rename(first.with_name("call_000_recomputed.json"))
    with pytest.raises(ck.CheckpointError), ck.checkpointed(tmp_path / "s"):
        run(study)


PROBE = """
import datetime, json
sys_path = {path!r}
import importlib.util
spec = importlib.util.spec_from_file_location("ck", sys_path)
ck = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ck)
from pydantic import BaseModel
class M(BaseModel):
    names: frozenset[str]
    when: datetime.date
value = {{("P1", "EFO:1"): {{"f1": M(names=frozenset("abcdefghij"), when=datetime.date(2024, 1, 2))}},
         ("P2", "EFO:2"): {{"f2": M(names=frozenset({{"x", "y", "z"}}), when=datetime.date(2023, 5, 6))}}}}
print(ck.fingerprint("tables", (value, 100, 7), {{"seed": 1, "extra": {{"k", "l", "m", "n"}}}}))
"""


def test_the_fingerprint_does_not_depend_on_how_a_process_orders_its_sets(tmp_path):
    script = tmp_path / "probe.py"
    script.write_text(PROBE.format(path=str(pathlib.Path(ck.__file__))))
    seen = set()
    for seed in ("1", "2", "3", "77"):
        done = subprocess.run([shutil.which("python"), str(script)], capture_output=True, text=True,
                              env={**os.environ, "PYTHONHASHSEED": seed,
                                   "PYTHONPATH": str(pathlib.Path(ck.__file__).parent)})
        assert done.returncode == 0, done.stderr
        seen.add(done.stdout.strip())
    assert len(seen) == 1 and len(seen.pop()) == 64
    assert ck.fingerprint("a", ({"x", "y"},), {}) != ck.fingerprint("a", ({"x", "z"},), {})
    assert ck.fingerprint("a", ([1, 2],), {}) != ck.fingerprint("a", ([2, 1],), {})
