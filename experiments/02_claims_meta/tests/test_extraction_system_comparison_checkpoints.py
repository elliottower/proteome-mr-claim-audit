import hashlib
import json

import pytest

import dry_run_extraction_system_comparison_synthetic as dry
import extraction_system_comparison as mc
import extraction_system_comparison_checkpoints as ck
from build_registry import SEED
from dataset_relations import load_rows

N = 300


@pytest.fixture(scope="module")
def rows():
    return load_rows()


def run(rows):
    return mc.comparison(dry.sol_claims(), dry.luna_run1_claims(), dry.luna_run2_claims(), rows,
                         dry.sol_repeat_claims(), frozenset(dry.SAMPLE), N, SEED)


def as_json(result):
    return json.loads(json.dumps(result))


def test_a_checkpointed_comparison_gives_the_registered_result(rows, tmp_path):
    plain = as_json(run(rows))
    with ck.checkpointed(tmp_path / "store") as calls:
        stored = as_json(run(rows))
    assert stored == plain
    assert {c[2] for c in calls} == {"computed"}
    assert {c[0] for c in calls} == {"compare", "h1_h2"}
    assert mc.compare.__name__ == "compare" and mc.h1_h2.__name__ == "h1_h2"


def test_a_resumed_comparison_takes_the_stored_calls_and_computes_the_rest(rows, tmp_path):
    plain = as_json(run(rows))
    store = tmp_path / "store"
    with ck.checkpointed(store):
        run(rows)
    files = sorted(store.glob("*.json"))
    for path in files[::2]:
        path.unlink()
    with ck.checkpointed(store) as calls:
        resumed = as_json(run(rows))
    assert resumed == plain
    states = [c[2] for c in calls]
    assert "stored" in states and "computed" in states
    with ck.checkpointed(store) as calls:
        again = as_json(run(rows))
    assert again == plain and {c[2] for c in calls} == {"stored"}


def test_a_call_that_fails_stores_nothing_and_the_rerun_completes(rows, tmp_path, monkeypatch):
    plain = as_json(run(rows))
    store = tmp_path / "store"
    original = mc.h1_h2

    def failing(*args, **kwargs):
        raise RuntimeError("stopped")

    monkeypatch.setattr(mc, "h1_h2", failing)
    with pytest.raises(RuntimeError), ck.checkpointed(store):
        run(rows)
    assert not list(store.glob("h1_h2_*")) and not list(store.glob("*.partial"))
    assert mc.h1_h2 is failing
    monkeypatch.setattr(mc, "h1_h2", original)
    with ck.checkpointed(store) as calls:
        assert as_json(run(rows)) == plain
    assert {c[0] for c in calls if c[2] == "stored"} <= {"compare"}


def fake_comparator(monkeypatch):
    sol, tables = b"sol registry", b"sol tables"
    monkeypatch.setattr(ck, "COMPARATOR", {
        "rule_label": "originally_registered", "analysis": "test",
        "sol": {"path": "outputs/registry/x_registered/registry_claims.jsonl",
                "sha256": hashlib.sha256(sol).hexdigest()},
        "sol_tables": {"path": "outputs/stage5_biology/x_registered/sensitivity_tables.json",
                       "sha256": hashlib.sha256(tables).hexdigest()}})
    return sol, tables


def test_the_comparator_check_passes_only_the_named_files_of_one_analysis(monkeypatch):
    sol, tables = fake_comparator(monkeypatch)
    sol_path = "outputs/registry/x_registered/registry_claims.jsonl"
    tables_path = "outputs/stage5_biology/x_registered/sensitivity_tables.json"
    rule = "originally_registered"
    got = ck.comparator_check(rule, sol_path, sol, "./" + tables_path, tables)
    assert got["sol"]["sha256"] == hashlib.sha256(sol).hexdigest()
    assert got["rule_label"] == rule


@pytest.mark.parametrize("case", ["amended_registry", "amended_tables", "changed_registry",
                                  "changed_tables", "swapped_roles", "amended_rule_label",
                                  "missing_rule_label", "registry_as_tables"])
def test_the_comparator_check_fails_on_any_other_combination(monkeypatch, case):
    sol, tables = fake_comparator(monkeypatch)
    rule = "originally_registered"
    sol_path = "outputs/registry/x_registered/registry_claims.jsonl"
    tables_path = "outputs/stage5_biology/x_registered/sensitivity_tables.json"
    args = {"amended_registry": (rule, "outputs/registry/x_amended/registry_claims.jsonl", sol,
                                 tables_path, tables),
            "amended_tables": (rule, sol_path, sol,
                               "outputs/stage5_biology/x_amended/sensitivity_tables.json",
                               tables),
            "changed_registry": (rule, sol_path, sol + b" ", tables_path, tables),
            "changed_tables": (rule, sol_path, sol, tables_path, tables + b" "),
            "swapped_roles": (rule, tables_path, tables, sol_path, sol),
            "amended_rule_label": ("amended_primary", sol_path, sol, tables_path, tables),
            "missing_rule_label": ("", sol_path, sol, tables_path, tables),
            "registry_as_tables": (rule, sol_path, sol, tables_path, sol)}[case]
    with pytest.raises(ck.ComparatorError):
        ck.comparator_check(*args)


def test_the_named_comparator_is_the_originally_registered_analysis():
    assert ck.COMPARATOR["rule_label"] == "originally_registered"
    assert "registered_with_27" in ck.COMPARATOR["sol"]["path"]
    assert "registered_with_27" in ck.COMPARATOR["sol_tables"]["path"]
    assert "amended" not in json.dumps(ck.COMPARATOR["sol"]) + json.dumps(ck.COMPARATOR["sol_tables"])


def test_the_named_files_have_the_named_hashes():
    root = ck.pathlib.Path(__file__).resolve().parents[1]
    for role in ("sol", "sol_tables"):
        want = ck.COMPARATOR[role]
        assert ck.sha256((root / want["path"]).read_bytes()) == want["sha256"]
