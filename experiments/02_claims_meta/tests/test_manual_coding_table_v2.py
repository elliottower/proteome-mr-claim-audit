import json

import pytest

import manual_coding_table as sealed
import manual_coding_table_v2 as table
from manual_dataset_coding import CODE_FIELDS, NOT_STATED, ManualCodingError, load_codes
from dataset_relations import load_rows
from test_manual_dataset_coding_reasons import write

ROWS = load_rows()


def paper(folder, coder, name, n, values, passes):
    codes = folder / coder / "codes"
    gates = folder / coder / table.GATES
    codes.mkdir(parents=True, exist_ok=True)
    gates.mkdir(parents=True, exist_ok=True)
    rows = [{"side": "outcome", "name_as_written": f"FinnGen {i}", "value": v,
             "unresolved_reason": None if v.startswith("FinnGen") else "release_not_identified",
             "identification_basis": "release_identifier" if v.startswith("FinnGen") else None,
             "source_read": "full_text", "quote": "We used FinnGen R9.", "passage_id": "p001",
             "citations_claim": f"claims/{name}.yaml#outcome_{i}", "companion_source": False,
             "coder_note": "note"} for i, v in enumerate(values, 1)]
    (codes / f"{name}.attempt{n}.json").write_text(json.dumps(
        {"record_id": name, "coder_id": coder, "attempt": n, "rows": rows}))
    if passes is not None:
        (gates / f"{name}.attempt{n}.gate.json").write_text(json.dumps({"rows": [
            {"side": "outcome", "name_as_written": r["name_as_written"], "passes": ok,
             "failures": [] if ok else ["no_identifier_of_the_coded_row_in_the_pinned_material"]}
            for r, ok in zip(rows, passes)]}))


def queue(*pairs):
    return [{"record_id": r, "side": "outcome", "name_as_written": f"FinnGen {i}"}
            for r, i in pairs]


def test_a_coded_row_failing_its_gate_is_written_unresolved_with_the_coders_value_kept(
        tmp_path):
    paper(tmp_path, "coder_1", "p1", 1, ["FinnGen R9", "FinnGen R5", NOT_STATED],
          [True, False, False])
    out = table.collect(tmp_path, queue(("p1", 1), ("p1", 2), ("p1", 3)))
    kept, changed, unresolved = out
    assert (kept["claude_code_value"], kept["coder_value_before_gate"]) == ("FinnGen R9", "")
    assert changed["claude_code_value"] == NOT_STATED
    assert changed["unresolved_reason"] == "release_not_identified"
    assert changed["coder_value_before_gate"] == "FinnGen R5"
    assert changed["gate_failures"] == "no_identifier_of_the_coded_row_in_the_pinned_material"
    assert changed["identification_basis"] == "" and changed["quote"] == "We used FinnGen R9."
    assert (unresolved["claude_code_value"], unresolved["coder_value_before_gate"]) == (
        NOT_STATED, "")
    assert all(list(r) == table.EXTENDED_FIELDS for r in out)


def test_every_other_row_is_what_the_sealed_script_writes(tmp_path):
    paper(tmp_path, "coder_1", "p1", 1, ["FinnGen R9", "FinnGen R5", NOT_STATED],
          [True, False, False])
    paper(tmp_path, "coder_2", "p2", 1, ["FinnGen R8"], [False])
    paper(tmp_path, "coder_2", "p2", 2, ["FinnGen R8", ], [True])
    q = queue(("p1", 1), ("p1", 2), ("p1", 3), ("p2", 1))
    new, old = table.collect(tmp_path, q), sealed.collect(tmp_path, q)
    for a, b in zip(new, old, strict=True):
        if a["coder_value_before_gate"]:
            continue
        assert {f: a[f] for f in sealed.EXTENDED_FIELDS} == b
        assert a["gate_failures"] == ""
    assert [bool(r["coder_value_before_gate"]) for r in new] == [False, True, False, False]
    assert new[3]["attempt"] == "2" and new[3]["claude_code_value"] == "FinnGen R8"
    assert table.EXTENDED_FIELDS == sealed.EXTENDED_FIELDS + ["coder_value_before_gate",
                                                              "gate_failures"]


def test_a_last_attempt_without_a_gate_file_is_refused(tmp_path):
    paper(tmp_path, "coder_1", "p1", 1, ["FinnGen R9"], None)
    with pytest.raises(ManualCodingError):
        table.collect(tmp_path, queue(("p1", 1)))


def test_the_registered_table_and_the_codes_follow_the_row_as_written(tmp_path):
    (tmp_path / "c").mkdir()
    paper(tmp_path / "c", "coder_1", "p1", 1, ["FinnGen R9", "FinnGen R5"], [True, False])
    rows = table.collect(tmp_path / "c", queue(("p1", 1), ("p1", 2)))
    done = [dict(r, perplexity_value=r["claude_code_value"], author_confirms="yes",
                 status="coded" if r["claude_code_value"] != NOT_STATED else "unresolved")
            for r in rows]
    codes, report = table.load_extended(write(tmp_path / "e.csv", table.EXTENDED_FIELDS, done),
                                        ROWS)
    assert codes == {("p1", "outcome", "FinnGen 1"): "FinnGen R9"}
    assert report["unresolved_reason_release_not_identified"] == 1
    view = write(tmp_path / "v.csv", CODE_FIELDS, table.registered_rows(done))
    assert load_codes(view, ROWS)[0] == codes


def test_second_check_fills_the_checkers_value_and_refuses_a_row_without_one(tmp_path):
    (tmp_path / "c").mkdir()
    paper(tmp_path / "c", "coder_1", "p1", 1, ["FinnGen R9", NOT_STATED], [True, True])
    rows = table.collect(tmp_path / "c", queue(("p1", 1), ("p1", 2)))
    (tmp_path / "comparison_with_first_check.json").write_text(json.dumps({"rows": [
        {"row": "p1#outcome_1", "second_check": "FinnGen R9"},
        {"row": "p1#outcome_2", "second_check": NOT_STATED}]}))
    filled = table.second_check(tmp_path, rows)
    assert [r["perplexity_value"] for r in filled] == ["FinnGen R9", NOT_STATED]
    assert [{k: v for k, v in r.items() if k != "perplexity_value"} for r in filled] == [
        {k: v for k, v in r.items() if k != "perplexity_value"} for r in rows]
    with pytest.raises(ManualCodingError):
        table.second_check(tmp_path, rows + [dict(rows[0], record_id="p9")])
