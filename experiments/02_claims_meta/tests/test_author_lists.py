import datetime
import json

import pytest

from author_lists import (DECISIONS, ELIGIBLE_ROWS, AuthorListError, cutoff, decide,
                          load_decisions, load_table, overrides)
from pathway_enrichment import load_attachments
from test_platform_lists import attachment_table

HEADER = "dictionary_row,list_id,background_level,source_claims,sha256,pinned_utc\n"
SCALLOP, AGES = ELIGIBLE_ROWS
SHA = "a" * 64


def utc(text):
    return datetime.datetime.fromisoformat(text)


def table(tmp_path, rows):
    path = tmp_path / "author_supplied_lists.csv"
    path.write_text(HEADER + "".join(",".join(r) + "\n" for r in rows))
    return path


def ledger(tmp_path, events):
    path = tmp_path / "ledger.jsonl"
    path.write_text("".join(json.dumps(e) + "\n" for e in events))
    return path


def test_first_stage5_biology_run_in_the_ledger_is_the_cutoff(tmp_path):
    led = ledger(tmp_path, [
        {"event": "init", "timestamp": "2026-11-01T00:00:00+00:00"},
        {"event": "run", "run_id": "s5_drug_x", "timestamp": "2026-11-02T00:00:00+00:00"},
        {"event": "run", "run_id": "s5_biology_b", "timestamp": "2026-11-05T00:00:00+00:00"},
        {"event": "run", "run_id": "s5_biology_a", "timestamp": "2026-11-04T00:00:00+00:00"}])
    assert cutoff(led, tmp_path / "none") == (utc("2026-11-04T00:00:00+00:00"), "ledger")


def test_written_enrichment_output_earlier_than_the_ledger_record_sets_the_cutoff(tmp_path):
    led = ledger(tmp_path, [
        {"event": "run", "run_id": "s5_biology_a", "timestamp": "2026-11-04T12:00:00+00:00"}])
    stage5 = tmp_path / "stage5"
    (stage5 / "a").mkdir(parents=True)
    (stage5 / "a" / "pathway_enrichment.json").write_text(json.dumps(
        {"window": "confirmatory", "written_utc": "2026-11-04T09:00:00+00:00"}))
    (stage5 / "u").mkdir()
    (stage5 / "u" / "pathway_enrichment.json").write_text(json.dumps(
        {"window": "update", "written_utc": "2026-10-01T00:00:00+00:00"}))
    assert cutoff(led, stage5) == (utc("2026-11-04T09:00:00+00:00"), "outputs")


def test_no_enrichment_yet_means_no_cutoff(tmp_path):
    led = ledger(tmp_path, [{"event": "run", "run_id": "smoke_pre2019_x",
                             "timestamp": "2026-10-02T00:00:00+00:00"}])
    assert cutoff(led, tmp_path / "none") == (None, "enrichment_not_yet_run")


def test_list_pinned_before_the_cutoff_replaces_and_a_later_one_is_sensitivity_only(tmp_path):
    rows = load_table(table(tmp_path, [
        (SCALLOP, "cvd1_analysed_90", "analysed", "folkersen2020_reply", SHA,
         "2026-11-03T00:00:00+00:00"),
        (AGES, "ages_table_s1", "assayed", "emilsson2018_reply", SHA,
         "2026-11-04T00:00:00+00:00")]))
    d = decide(rows, utc("2026-11-04T00:00:00+00:00"))
    assert set(d["primary"]) == {SCALLOP}
    assert set(d["after_cutoff"]) == {AGES}
    assert overrides(d, "primary") == {SCALLOP: ("cvd1_analysed_90", "analysed")}
    everything_before = decide(rows, None)
    assert set(everything_before["primary"]) == {SCALLOP, AGES}
    assert everything_before["after_cutoff"] == {}


def test_override_changes_the_attached_list_only_for_its_row(tmp_path):
    path, dictionary = attachment_table(tmp_path, [
        (SCALLOP, "Olink CVD I", "panel92", "", "assayed", "", "92"),
        ("Other", "Olink", "panel92", "", "assayed", "", "92")])
    lists = {"panel92": frozenset(f"P{i:03d}" for i in range(92)),
             "cvd1_analysed_90": frozenset(f"P{i:03d}" for i in range(90))}
    assert load_attachments(path, lists, dictionary) == {SCALLOP: "panel92", "Other": "panel92"}
    assert load_attachments(path, lists, dictionary,
                            overrides={SCALLOP: ("cvd1_analysed_90", "analysed")}) == {
        SCALLOP: "cvd1_analysed_90", "Other": "panel92"}


def test_supplied_assayed_list_below_90_percent_coverage_is_refused(tmp_path):
    path, dictionary = attachment_table(tmp_path, [
        (SCALLOP, "Olink CVD I", "panel92", "", "assayed", "", "92")])
    lists = {"panel92": frozenset(f"P{i:03d}" for i in range(92)),
             "short": frozenset(f"P{i:03d}" for i in range(80))}
    with pytest.raises(Exception, match="below 90%"):
        load_attachments(path, lists, dictionary, overrides={SCALLOP: ("short", "assayed")})


def test_rows_outside_the_registered_two_and_missing_hashes_are_refused(tmp_path):
    with pytest.raises(AuthorListError, match="covers only"):
        load_table(table(tmp_path, [("KORA (Suhre 2017)", "x", "analysed", "c", SHA,
                                     "2026-11-03T00:00:00+00:00")]))
    with pytest.raises(AuthorListError, match="sha256"):
        load_table(table(tmp_path, [(SCALLOP, "x", "analysed", "c", "abc",
                                     "2026-11-03T00:00:00+00:00")]))
    with pytest.raises(AuthorListError, match="time zone"):
        load_table(table(tmp_path, [(SCALLOP, "x", "analysed", "c", SHA,
                                     "2026-11-03T00:00:00")]))


def test_joins_refuse_a_supplied_list_without_a_decisions_file(tmp_path):
    t = table(tmp_path, [(SCALLOP, "x", "analysed", "c", SHA, "2026-11-03T00:00:00+00:00")])
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    with pytest.raises(AuthorListError, match="decide"):
        load_decisions(inputs, t)
    (inputs / DECISIONS).write_text(json.dumps(decide(load_table(t), None)))
    assert set(load_decisions(inputs, t)["primary"]) == {SCALLOP}
    empty = table(tmp_path, [])
    assert load_decisions(tmp_path / "nowhere", empty) == {"primary": {}, "after_cutoff": {}}


def test_committed_table_is_empty_at_the_freeze():
    assert load_table() == []
