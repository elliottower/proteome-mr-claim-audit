import hashlib
import json

import pytest

import stage_record


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


@pytest.fixture
def stage(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "outputs" / "stage"
    (out / "raw").mkdir(parents=True)
    (out / "tables.json").write_bytes(b'{"n": 3}\n')
    (out / "raw" / "a.gz").write_bytes(b"\x1f\x8b raw a")
    (out / "raw" / "b.gz").write_bytes(b"\x1f\x8b raw b")
    return out


def volume_listing(pairs: dict[str, bytes]) -> dict[str, dict]:
    return {remote: {"bytes": len(content), "sha256": digest(content)}
            for remote, content in pairs.items()}


def test_manifest_lists_every_file_under_a_folder_with_its_own_hash(stage):
    calls = []
    target = stage_record.record(
        "run_1", "synthetic", [stage_record.pathlib.Path("outputs/stage")],
        [stage_record.pathlib.Path("outputs/stage/tables.json")], {}, [],
        run=lambda argv, check: calls.append(argv))
    manifest = json.loads(target.read_text())
    assert {f["path"]: (f["bytes"], f["sha256"]) for f in manifest["files"]} == {
        "outputs/stage/raw/a.gz": (8, digest(b"\x1f\x8b raw a")),
        "outputs/stage/raw/b.gz": (8, digest(b"\x1f\x8b raw b")),
        "outputs/stage/tables.json": (9, digest(b'{"n": 3}\n')),
    }
    assert calls == [["results", "run", "--run-id", "run_1", "--note", "synthetic",
                      "outputs/results_manifests/run_1.json", "outputs/stage/tables.json"]]


def test_a_run_id_is_recorded_once(stage):
    args = ("run_1", "synthetic", [stage_record.pathlib.Path("outputs/stage")], [], {}, [])
    stage_record.record(*args, run=lambda argv, check: None)
    with pytest.raises(stage_record.StageRecordError, match="recorded once"):
        stage_record.record(*args, run=lambda argv, check: None)


def test_nothing_reaches_the_ledger_when_a_local_copy_differs_from_the_volume(stage):
    volume = volume_listing({"/vol/run/tables.json": b'{"n": 4}\n',
                             "/vol/run/raw/a.gz": b"\x1f\x8b raw a",
                             "/vol/run/raw/b.gz": b"\x1f\x8b raw b"})
    calls = []
    with pytest.raises(stage_record.StageRecordError, match="outputs/stage/tables.json"):
        stage_record.record("run_1", "synthetic", [stage_record.pathlib.Path("outputs/stage")],
                            [], volume, [("/vol/run", "outputs/stage")],
                            run=lambda argv, check: calls.append(argv))
    assert calls == []
    assert not (stage / ".." / "results_manifests" / "run_1.json").exists()


def test_a_local_file_the_volume_does_not_hold_is_refused(stage):
    volume = volume_listing({"/vol/run/tables.json": b'{"n": 3}\n',
                             "/vol/run/raw/a.gz": b"\x1f\x8b raw a"})
    with pytest.raises(stage_record.StageRecordError, match="raw/b.gz: not on the volume"):
        stage_record.record("run_1", "synthetic", [stage_record.pathlib.Path("outputs/stage")],
                            [], volume, [("/vol/run", "outputs/stage")],
                            run=lambda argv, check: None)


def test_matching_copies_are_counted_and_volume_only_files_are_named(stage):
    volume = volume_listing({"/vol/run/tables.json": b'{"n": 3}\n',
                             "/vol/run/raw/a.gz": b"\x1f\x8b raw a",
                             "/vol/run/raw/b.gz": b"\x1f\x8b raw b",
                             "/vol/run/inputs/claims.jsonl": b"{}\n",
                             "/vol/other/tables.json": b"elsewhere"})
    target = stage_record.record("run_1", "synthetic",
                                 [stage_record.pathlib.Path("outputs/stage")], [], volume,
                                 [("/vol/run/", "outputs/stage")], run=lambda argv, check: None)
    check = json.loads(target.read_text())["volume_checks"]
    assert check == [{"volume_folder": "/vol/run", "local_folder": "outputs/stage",
                      "n_compared": 3, "volume_only": ["/vol/run/inputs/claims.jsonl"]}]


def test_a_volume_map_that_covers_no_recorded_file_is_refused(stage):
    with pytest.raises(stage_record.StageRecordError, match="no recorded file lies under"):
        stage_record.record("run_1", "synthetic", [stage_record.pathlib.Path("outputs/stage")],
                            [], {}, [("/vol/run", "outputs/elsewhere")],
                            run=lambda argv, check: None)


def test_verify_names_a_changed_and_a_missing_file_and_passes_untouched_runs(stage):
    stage_record.record("run_1", "synthetic", [stage_record.pathlib.Path("outputs/stage")], [],
                        {}, [], run=lambda argv, check: None)
    assert stage_record.verify() == {"run_1": []}
    (stage / "tables.json").write_bytes(b'{"n": 4}\n')
    (stage / "raw" / "b.gz").unlink()
    assert stage_record.verify() == {"run_1": ["MISSING  outputs/stage/raw/b.gz",
                                               "CHANGED  outputs/stage/tables.json"]}


def test_a_path_that_does_not_exist_is_refused(stage):
    with pytest.raises(stage_record.StageRecordError, match="neither a file nor a folder"):
        stage_record.record("run_1", "synthetic", [stage_record.pathlib.Path("outputs/absent")],
                            [], {}, [], run=lambda argv, check: None)


def test_a_volume_listing_beside_the_manifests_is_not_read_as_a_manifest(stage):
    stage_record.record("run_1", "synthetic", [stage_record.pathlib.Path("outputs/stage")], [],
                        {}, [], run=lambda argv, check: None)
    listing = stage_record.MANIFESTS / "run_1.volume.json"
    listing.write_text(json.dumps(volume_listing({"/vol/run/tables.json": b"x"})))
    assert stage_record.verify() == {"run_1": []}
    with pytest.raises(stage_record.StageRecordError, match="cannot end in .volume"):
        stage_record.record("run_2.volume", "synthetic",
                            [stage_record.pathlib.Path("outputs/stage")], [], {}, [],
                            run=lambda argv, check: None)


def test_one_local_file_is_compared_with_the_volume_file_it_is_mapped_to(stage):
    tables = stage_record.pathlib.Path("outputs/stage/tables.json")
    same = volume_listing({"/vol/run/sensitivity.json": b'{"n": 3}\n'})
    target = stage_record.record("run_1", "synthetic", [tables], [], same,
                                 [("/vol/run/sensitivity.json", "outputs/stage/tables.json")],
                                 run=lambda argv, check: None)
    assert json.loads(target.read_text())["volume_checks"] == [
        {"volume_folder": "/vol/run/sensitivity.json",
         "local_folder": "outputs/stage/tables.json", "n_compared": 1, "volume_only": []}]
    other = volume_listing({"/vol/run/sensitivity.json": b'{"n": 4}\n'})
    with pytest.raises(stage_record.StageRecordError, match="outputs/stage/tables.json: local"):
        stage_record.record("run_2", "synthetic", [tables], [], other,
                            [("/vol/run/sensitivity.json", "outputs/stage/tables.json")],
                            run=lambda argv, check: None)


PLAN_HASH = "ab" * 32


def frozen_plan(digest: str = PLAN_HASH) -> str:
    return ("# A question?\n\n**Status:** FROZEN at `eeb885645205`\n"
            f"**Plan sha256:** `{digest}`\n**Log:** 3 entries, head `f7f40cdb`\n"
            "**Frozen:** 2026-10-02\n\nThe plan.\n\n---\n\n## Log\n")


class Checked:
    def __init__(self, returncode: int, stdout: str = ""):
        self.returncode = returncode
        self.stdout = stdout


def prereg_check(returncode: int, stdout: str = ""):
    return lambda argv, capture_output, text: Checked(returncode, stdout)


def test_plan_record_holds_the_commit_hash_and_date_of_the_freeze_header(stage):
    stage_record.PLAN.write_text(frozen_plan())
    target = stage_record.record_plan(run=prereg_check(0))
    assert target == stage_record.PLAN_RECORD
    assert json.loads(target.read_text()) == {
        "plan": "PREREG.md", "frozen_at_commit": "eeb885645205", "plan_sha256": PLAN_HASH,
        "frozen": "2026-10-02"}
    with pytest.raises(stage_record.StageRecordError, match="recorded once"):
        stage_record.record_plan(run=prereg_check(0))


def test_no_plan_record_is_written_for_a_draft_or_for_a_plan_prereg_reports_changed(stage):
    stage_record.PLAN.write_text("# A question?\n\n**Status:** DRAFT — not frozen.\n\nThe plan.\n")
    with pytest.raises(stage_record.StageRecordError, match="no freeze header"):
        stage_record.record_plan(run=prereg_check(0))
    stage_record.PLAN.write_text(frozen_plan())
    with pytest.raises(stage_record.StageRecordError, match="CHANGED      PREREG.md"):
        stage_record.record_plan(run=prereg_check(1, "CHANGED      PREREG.md"))
    assert not stage_record.PLAN_RECORD.exists()


def test_verify_plan_names_the_header_field_that_no_longer_matches_its_record(stage):
    stage_record.PLAN.write_text(frozen_plan())
    stage_record.record_plan(run=prereg_check(0))
    assert stage_record.verify_plan(run=prereg_check(0)) == []
    stage_record.PLAN.write_text(frozen_plan("cd" * 32))
    assert stage_record.verify_plan(run=prereg_check(0)) == [
        f"plan_sha256: recorded {PLAN_HASH}, plan header {'cd' * 32}"]
    with pytest.raises(stage_record.StageRecordError, match="did not pass"):
        stage_record.verify_plan(run=prereg_check(1, "LOG ALTERED  PREREG.md"))


def test_the_plan_record_is_not_read_as_a_stage_manifest(stage):
    stage_record.PLAN.write_text(frozen_plan())
    stage_record.record_plan(run=prereg_check(0))
    stage_record.record("run_1", "synthetic", [stage_record.pathlib.Path("outputs/stage")], [],
                        {}, [], run=lambda argv, check: None)
    assert stage_record.verify() == {"run_1": []}
    with pytest.raises(stage_record.StageRecordError, match="cannot end in .plan"):
        stage_record.record("freeze.plan", "synthetic",
                            [stage_record.pathlib.Path("outputs/stage")], [], {}, [],
                            run=lambda argv, check: None)


def recorded(stage):
    stage_record.record("run_1", "synthetic", [stage_record.pathlib.Path("outputs/stage")], [],
                        {}, [], run=lambda argv, check: None)
    stage_record.record("run_2", "synthetic", [stage_record.pathlib.Path("outputs/stage/raw")],
                        [], {}, [], run=lambda argv, check: None)
    return stage_record.pathlib.Path("outputs/stage/raw/a.gz")


def test_a_documented_replacement_verifies_only_with_exactly_the_replaced_bytes(stage, tmp_path):
    path = recorded(stage)
    archive = stage_record.pathlib.Path("archive")
    rows = stage_record.replace(path, b"stripped", archive, "absolute path removed")
    assert [(r.run_id, r.path) for r in rows] == [("run_1", str(path)), ("run_2", str(path))]
    assert {r.recorded_sha256 for r in rows} == {digest(b"\x1f\x8b raw a")}
    assert {r.replaced_sha256 for r in rows} == {digest(b"stripped")}
    assert (archive / path).read_bytes() == b"\x1f\x8b raw a" and path.read_bytes() == b"stripped"
    assert stage_record.verify() == {"run_1": [], "run_2": []}
    path.write_bytes(b"stripped and then edited")
    assert stage_record.verify() == {"run_1": [f"CHANGED  {path}"], "run_2": [f"CHANGED  {path}"]}
    path.write_bytes(b"\x1f\x8b raw a")
    assert stage_record.verify() == {"run_1": [], "run_2": []}


def test_a_replacement_row_covers_only_its_own_run_path_and_recorded_hash(stage):
    path = recorded(stage)
    stage_record.replace(path, b"stripped", stage_record.pathlib.Path("archive"), "reason")
    table = stage_record.MANIFESTS / stage_record.REPLACED_NAME
    rows = json.loads(table.read_text())
    other = stage_record.pathlib.Path("outputs/stage/raw/b.gz")
    other.write_bytes(b"stripped")
    assert stage_record.verify() == {"run_1": [f"CHANGED  {other}"],
                                     "run_2": [f"CHANGED  {other}"]}
    other.write_bytes(b"\x1f\x8b raw b")
    table.write_text(json.dumps([r for r in rows if r["run_id"] == "run_1"]))
    assert stage_record.verify() == {"run_1": [], "run_2": [f"CHANGED  {path}"]}
    table.write_text(json.dumps([{**r, "recorded_sha256": "0" * 64} for r in rows]))
    assert stage_record.verify() == {"run_1": [f"CHANGED  {path}"], "run_2": [f"CHANGED  {path}"]}


def test_replace_refuses_an_edited_file_an_unrecorded_file_and_a_second_archive(stage):
    path = recorded(stage)
    archive = stage_record.pathlib.Path("archive")
    with pytest.raises(stage_record.StageRecordError, match="the recorded bytes"):
        stage_record.replace(path, b"\x1f\x8b raw a", archive, "reason")
    with pytest.raises(stage_record.StageRecordError, match="needs its reason"):
        stage_record.replace(path, b"stripped", archive, " ")
    loose = stage_record.pathlib.Path("outputs/loose.txt")
    loose.write_bytes(b"x")
    with pytest.raises(stage_record.StageRecordError, match="no manifest names"):
        stage_record.replace(loose, b"y", archive, "reason")
    path.write_bytes(b"edited by hand")
    with pytest.raises(stage_record.StageRecordError, match="no longer has the bytes"):
        stage_record.replace(path, b"stripped", archive, "reason")
    path.write_bytes(b"\x1f\x8b raw a")
    (archive / path).parent.mkdir(parents=True)
    (archive / path).write_bytes(b"an earlier original")
    with pytest.raises(stage_record.StageRecordError, match="archived once"):
        stage_record.replace(path, b"stripped", archive, "reason")
    assert path.read_bytes() == b"\x1f\x8b raw a"
    (archive / path).unlink()
    stage_record.replace(path, b"stripped", archive, "reason")
    with pytest.raises(stage_record.StageRecordError, match="no longer has the bytes"):
        stage_record.replace(path, b"again", archive, "reason")
    assert len(json.loads((stage_record.MANIFESTS / stage_record.REPLACED_NAME).read_text())) == 2


def test_the_replacement_table_is_not_read_as_a_manifest_and_is_no_run_id(stage):
    path = recorded(stage)
    stage_record.replace(path, b"stripped", stage_record.pathlib.Path("archive"), "reason")
    assert set(stage_record.verify()) == {"run_1", "run_2"}
    with pytest.raises(stage_record.StageRecordError, match="cannot be replaced_files"):
        stage_record.record("replaced_files", "synthetic",
                            [stage_record.pathlib.Path("outputs/stage")], [], {}, [],
                            run=lambda argv, check: None)
