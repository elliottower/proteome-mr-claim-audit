import hashlib
import json

import pytest

import process_counts as pc


def test_an_address_is_followed_through_nested_objects_and_a_missing_one_raises():
    data = {"a": {"b": {"c": 7}}, "n": 3}
    assert pc.at(data, "a.b.c") == 7 and pc.at(data, "n") == 3
    for wrong in ("a.x", "n.c", "z"):
        with pytest.raises(pc.CountError):
            pc.at(data, wrong)


PLAN = """# Plan

2026-01-01  a dated line above the log is not a log line          nothing run

## Log

Append only.

```
2026-09-30  created                              nothing run
2026-10-01  a rule, logged before anything was seen: no results seen
2026-10-02  files fetched; results not opened
2026-10-07  a deviation, counts read                     results seen
2026-10-08  another, which mentions nothing run in its text       results seen
2026-10-08  a line with the chain mark after its level  results not opened  ·0a1b2c3d
continuation text that is not dated  results seen
2026-10-08  a line with no level at its end.
```
"""


def test_log_lines_are_the_dated_lines_of_the_log_section_by_the_level_they_end_with():
    assert pc.log_lines(PLAN) == {"all": 7, "nothing run": 1, "no results seen": 1,
                                  "results not opened": 2, "results seen": 2,
                                  "no level read": 1}


def test_ledger_events_are_counted_by_kind_with_distinct_sealed_files():
    events = [{"event": "init", "seq": 0},
              {"event": "seal", "seq": 1, "files": [{"path": "a"}, {"path": "b"}]},
              {"event": "seal", "seq": 2, "files": [{"path": "a"}]},
              {"event": "access", "seq": 3, "level": "structure seen"},
              {"event": "access", "seq": 4, "level": "outcomes seen"},
              {"event": "access", "seq": 5, "level": "structure seen"},
              {"event": "run", "seq": 6}]
    made = pc.ledger_events("".join(json.dumps(e) + "\n" for e in events) + "\n")
    assert made == {"events": 7, "last_seq": 6,
                    "by_kind": {"init": 1, "seal": 2, "access": 3, "run": 1},
                    "distinct_files_sealed": 2,
                    "access_by_level": {"outcomes seen": 1, "structure seen": 2}}


def test_quotations_are_counted_over_every_claim_of_every_claims_file(tmp_path):
    (tmp_path / "a.yaml").write_text(
        "source: {citation: a}\nclaims:\n  c1:\n    quotes:\n    - exact: one\n    - exact: two\n"
        "  c2:\n    quotes:\n    - exact: three\n      prefix: x\n  c3: {}\n")
    (tmp_path / "b.yaml").write_text("source: {citation: b}\nclaims: {}\n")
    (tmp_path / "c.yaml").write_text("source: {citation: c}\n")
    (tmp_path / "d.yaml.provenance-lock").write_text("")
    assert pc.quotations(tmp_path) == {"claims_files": 3, "claims_files_with_a_quotation": 1,
                                       "quotations": 3}


def test_the_suite_counts_are_those_of_the_last_summary_line():
    text = ("test_x.py: 3 passed in the docstring\n1 failed, 10 passed, 2 skipped in 3.10s\n"
            "======\n1199 passed, 1 skipped in 19.18s\n")
    assert pc.suite(text) == {"passed": 1199, "skipped": 1, "failed": 0}
    assert pc.suite("=== 5 passed in 0.1s ===\n") == {"passed": 5, "skipped": 0, "failed": 0}
    assert pc.suite("2 failed, 7 passed in 1s") == {"passed": 7, "skipped": 0, "failed": 2}
    with pytest.raises(pc.CountError):
        pc.suite("nothing here")


def test_a_count_and_its_sources_are_read_from_files_and_every_file_is_hashed(tmp_path):
    (tmp_path / "x.json").write_text(json.dumps({"n": 4, "deep": {"m": 6}}))
    (tmp_path / "y.json").write_text(json.dumps({"n": 10}))
    (tmp_path / "rows.jsonl").write_text('{"a": 1}\n\n{"a": 2}\n')
    (tmp_path / "t.csv").write_text('id,text\n1,"two\nlines"\n2,plain\n')
    c = pc.Counts(tmp_path)
    assert c.direct("one", "m", "x.json", "deep.m") == 6
    assert c.total("both", "m", [("x.json", "n"), ("y.json", "n")]) == 14
    assert c.lines("records", "m", ["rows.jsonl", "rows.jsonl"]) == 4
    assert c.lines("table", "m", ["t.csv"], header=True) == 2
    assert c.counts["both"]["sources"] == [{"file": "x.json", "address": "n", "value": 4},
                                           {"file": "y.json", "address": "n", "value": 10}]
    assert c.digests["x.json"] == hashlib.sha256((tmp_path / "x.json").read_bytes()).hexdigest()
    assert set(c.digests) == {"x.json", "y.json", "rows.jsonl", "t.csv"}
    with pytest.raises(pc.CountError):
        c.direct("one", "again", "x.json", "n")


def test_a_run_holds_a_count_only_when_it_names_every_source_with_the_bytes_it_has_now():
    manifests = {"run_a": {"x": "1", "y": "2"}, "run_b": {"x": "1"}, "run_c": {"x": "9", "y": "2"}}
    digests = {"x": "1", "y": "2"}
    assert pc.runs_holding(["x"], manifests, digests) == ["run_a", "run_b"]
    assert pc.runs_holding(["x", "y"], manifests, digests) == ["run_a"]
    assert pc.runs_holding([], manifests, digests) == []


def test_manifests_are_read_by_run_id_and_other_json_files_are_passed_over(tmp_path):
    (tmp_path / "r1.json").write_text(json.dumps(
        {"run_id": "r1", "files": [{"path": "a", "sha256": "1", "bytes": 3}]}))
    (tmp_path / "r1.volume.json").write_text(json.dumps({"files": {"a": "1"}}))
    (tmp_path / "replaced_files.json").write_text(json.dumps([]))
    assert pc.load_manifests(tmp_path) == {"r1": {"a": "1"}}
