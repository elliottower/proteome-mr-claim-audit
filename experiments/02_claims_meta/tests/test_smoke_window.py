import datetime
import json
import pathlib
import subprocess

import pytest

import smoke_guard
from assemble_registry import assemble, window_of, write
from build_registry import PublicDate
from dataset_relations import load_rows
from link_families import SearchRecord
from ontology_graph import OntologyGraph
from sensitivity_analyses import run
from smoke_guard import (SmokeWindowError, check_run_name, check_smoke_folder,
                         check_smoke_label, check_smoke_output, smoke_label_of)

HGNC = {f"HGNC:{i}": frozenset({f"P{i}"}) for i in range(1, 4)}
TITLE = "Proteome-wide Mendelian randomization of plasma proteins and {}"


def day(text):
    return PublicDate(value=datetime.date.fromisoformat(text), resolution="day")


def record(rid, topic, author, date):
    return SearchRecord(record_id=rid, kind="journal", doi=f"10.1/{rid}", pmid=None, pmcid=None,
                        published_as_doi=None, title=TITLE.format(topic),
                        first_author_surname=author, first_public=day(date))


def check(rid, i, protein):
    return {"pmid": rid, "claim_index": i, "claim_record_id": f"{rid}:{i:03d}",
            "direction": "raises", "claim_scope": "overall",
            "analysis_context_as_written": "not_stated", "subgroup_as_written": "not_stated",
            "relation_ambiguous": False, "dataset_attribution": "whole_study",
            "pqtl_datasets": ["Sun 2018"], "outcome_datasets": ["FinnGen R10"],
            "protein_ids": [protein], "outcome_ids": ["MONDO:1"],
            "direction_verification_state": "agrees", "span_passes": True,
            "evidence_type": "mr_estimate", "protein_check": "pass", "outcome_check": "pass",
            "enters_registry": True, "first_failure": None}


OLD = [record("A", "stroke", "Alpha", "2018-06-11"), record("B", "gout", "Beta", "2017-02-02")]
DECISIONS = {"A": {"decision": "eligible", "flags": []},
             "B": {"decision": "uncertain", "flags": []},
             "C": {"decision": "eligible", "flags": []}}
STATUS = {"A": "ok", "B": "ok", "C": "ok"}
CHECKS = [check("A", 0, "HGNC:1"), check("A", 1, "HGNC:2"), check("B", 0, "HGNC:1")]


def test_window_of_under_the_smoke_switch():
    assert window_of(day("2018-12-31")) == "outside"
    assert window_of(day("2018-12-31"), smoke_window=True) == "confirmatory"
    assert window_of(day("2014-01-01"), smoke_window=True) == "confirmatory"
    with pytest.raises(SmokeWindowError):
        window_of(day("2019-01-01"), smoke_window=True)


def test_smoke_window_puts_pre_2019_claims_in_the_registry_and_the_plain_run_does_not():
    plain = assemble(OLD, DECISIONS, STATUS, CHECKS, HGNC, {})
    assert {m.window for m in plain.meta.values()} == {"outside"}
    assert plain.claims["confirmatory"] == [] and len(plain.claims["outside"]) == 3
    assert "smoke_window" not in plain.report
    smoke = assemble(OLD, DECISIONS, STATUS, CHECKS, HGNC, {}, smoke_window=True)
    assert {m.window for m in smoke.meta.values()} == {"confirmatory"}
    assert sorted((c.family_id, c.protein_id) for c in smoke.claims["confirmatory"]) == [
        ("A", "P1"), ("A", "P2"), ("B", "P1")]
    assert smoke.claims["outside"] == [] and smoke.claims["update"] == []
    assert smoke.report["smoke_window"] is True
    assert smoke.report["eligible_families_by_window"] == {"confirmatory": 2}
    assert (smoke.meta["A"].n_registry_claims, smoke.meta["A"].n_pairs) == (2, 2)


@pytest.mark.parametrize("date", ["2019-01-01", "2022-05-05", "2026-01-01"])
def test_smoke_window_refuses_any_record_of_2019_or_later(date):
    records = OLD + [record("C", "asthma", "Gamma", date)]
    with pytest.raises(SmokeWindowError):
        assemble(records, DECISIONS, STATUS, CHECKS, HGNC, {}, smoke_window=True)
    # Even an ineligible record of the window stops a smoke assembly.
    decisions = {**DECISIONS, "C": {"decision": "ineligible", "flags": []}}
    with pytest.raises(SmokeWindowError):
        assemble(records, decisions, STATUS, CHECKS, HGNC, {}, smoke_window=True)


@pytest.mark.parametrize("label", ["run_20261002", "", "smoke", "smoke-x", "smoke_../x",
                                   "smoke_a b", "Smoke_a"])
def test_labels_that_are_not_smoke_labels_are_refused(label):
    with pytest.raises(SmokeWindowError):
        check_smoke_label(label)


def test_smoke_labels_are_accepted():
    check_smoke_label("smoke_pre2019_20261002")
    check_smoke_label("smoke_a1")


def test_a_smoke_registry_is_written_only_under_its_label(tmp_path, monkeypatch):
    root = tmp_path / "outputs" / "registry"
    monkeypatch.setattr(smoke_guard, "REGISTRY_ROOT", root)
    check_smoke_folder("smoke_a", root / "smoke_a")
    check_smoke_folder("smoke_a", root / "smoke_a_coded")
    for out in (root / "run_a", root / "smoke_b", tmp_path / "smoke_a",
                root / "smoke_a" / "nested", root.parent / "funnel" / "smoke_a"):
        with pytest.raises(SmokeWindowError):
            check_smoke_folder("smoke_a", out)


def test_write_ties_the_smoke_assembly_to_its_label(tmp_path, monkeypatch):
    root = tmp_path / "outputs" / "registry"
    monkeypatch.setattr(smoke_guard, "REGISTRY_ROOT", root)
    smoke = assemble(OLD, DECISIONS, STATUS, CHECKS, HGNC, {}, smoke_window=True)
    plain = assemble(OLD, DECISIONS, STATUS, CHECKS, HGNC, {})
    with pytest.raises(SmokeWindowError):
        write(smoke, root / "smoke_a")                     # smoke assembly, no label
    with pytest.raises(SmokeWindowError):
        write(plain, root / "smoke_a", "smoke_a")          # label on a plain assembly
    with pytest.raises(SmokeWindowError):
        write(plain, root / "smoke_a")                     # plain assembly into a smoke folder
    with pytest.raises(SmokeWindowError):
        write(smoke, root / "run_a", "smoke_a")            # smoke assembly into a run folder
    assert not root.exists()
    write(smoke, root / "smoke_a_coded", "smoke_a")
    write(plain, root / "run_a")
    report = json.loads((root / "smoke_a_coded" / "registry_assembly.json").read_text())
    assert (report["smoke_label"], report["smoke_window"]) == ("smoke_a", True)
    lines = (root / "smoke_a_coded" / "registry_claims.jsonl").read_text().splitlines()
    assert len(lines) == 3
    assert (root / "run_a" / "registry_claims.jsonl").read_text() == ""
    assert smoke_label_of(root / "smoke_a_coded") == "smoke_a"
    assert smoke_label_of(root / "run_a") is None


def test_results_of_a_smoke_registry_stay_under_its_label(tmp_path):
    smoke_dir, run_dir = tmp_path / "s", tmp_path / "r"
    for folder, extra in ((smoke_dir, {"smoke_label": "smoke_a"}), (run_dir, {})):
        folder.mkdir()
        (folder / "registry_assembly.json").write_text(json.dumps({**extra, "records": 1}))
    check_smoke_output(smoke_dir, "smoke_a")
    check_smoke_output(smoke_dir, "smoke_a_window")
    check_smoke_output(run_dir, "20261101")
    for folder, name in ((smoke_dir, "20261101"), (smoke_dir, "smoke_b"), (smoke_dir, ""),
                         (run_dir, "smoke_a"), (run_dir, "smoke_anything")):
        with pytest.raises(SmokeWindowError):
            check_smoke_output(folder, name)


def test_run_name_and_smoke_label_must_agree():
    check_run_name("smoke_a_window", "smoke_a")
    check_run_name("20261101", "")
    for run_name, label in (("smoke_a", ""), ("20261101", "smoke_a"), ("smoke_b", "smoke_a"),
                            ("smoke_a", "run")):
        with pytest.raises(SmokeWindowError):
            check_run_name(run_name, label)


def test_sensitivity_tables_read_the_smoke_window_only_when_asked():
    rows = load_rows()
    graph = OntologyGraph([])
    args = (OLD, DECISIONS, STATUS, CHECKS, HGNC, {}, graph, rows)
    plain = run(*args, n_boot=50)
    assert plain["primary"]["claim_records"] == 0 and "smoke_window" not in plain
    smoke = run(*args, n_boot=50, smoke_window=True)
    assert smoke["smoke_window"] is True
    assert smoke["primary"]["claim_records"] == 3
    assert smoke["without_eligibility_uncertain"]["claim_records"] == 2
    assert smoke["shared_names_mondo_first"]["claim_records"] == 3
    assert smoke["without_phenotype_cross_references"]["claim_records"] == 3
    assert smoke["first_public_2020_2025"]["claim_records"] == 0
    assert smoke["families_removed"]["eligibility_uncertain"] == 1


SCRIPTS = pathlib.Path(smoke_guard.__file__).parent


def registry_dir(folder, label=None):
    folder.mkdir(parents=True)
    extra = {"smoke_label": label} if label else {}
    (folder / "registry_assembly.json").write_text(json.dumps({**extra, "records": 0}))
    (folder / "registry_claims.jsonl").write_text("")
    (folder / "families_meta.json").write_text("{}")
    (folder / "families.json").write_text(json.dumps({"families": {}, "links": []}))
    return folder


def later_step(script, registry, out):
    commands = {
        "funnel.py": ["--screening-dir", "x", "--decisions", "x", "--extraction", "x", "--spans",
                      "x", "--checks", "x", "--assembly", str(registry), "--out", str(out)],
        "manual_dataset_coding.py": ["queue", "--claims", str(registry / "registry_claims.jsonl"),
                                     "--out", str(out)],
        "fetch_fulltext.py": ["--census", "--before", "2019-01-01", "--families-meta",
                              str(registry / "families_meta.json"), "--out", str(out)],
    }
    return subprocess.run(["python", str(SCRIPTS / script), *commands[script]],
                          capture_output=True, text=True)


@pytest.mark.parametrize("script", ["funnel.py", "manual_dataset_coding.py", "fetch_fulltext.py"])
def test_later_steps_refuse_a_smoke_registry_under_another_name_and_a_smoke_name_otherwise(
        script, tmp_path):
    smoke = registry_dir(tmp_path / "registry" / "smoke_a_coded", "smoke_a")
    plain = registry_dir(tmp_path / "registry" / "run_a")
    for registry, out in ((smoke, tmp_path / "out" / "run_a"), (plain, tmp_path / "out" / "smoke_a")):
        done = later_step(script, registry, out)
        assert done.returncode != 0 and "SmokeWindowError" in done.stderr
        assert not out.exists()
    for registry, out in ((smoke, tmp_path / "ok" / "smoke_a_x"), (plain, tmp_path / "ok" / "run_a")):
        assert "SmokeWindowError" not in later_step(script, registry, out).stderr
