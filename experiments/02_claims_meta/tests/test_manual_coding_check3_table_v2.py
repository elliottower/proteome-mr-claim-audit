import json

import manual_coding_check3_table as first
import manual_coding_check3_table_v2 as t
from manual_coding_table_v6 import EXTENDED_FIELDS
from test_manual_coding_check3_table import ROWS

BASES = {"p1#outcome_1": ["aliases:FinnGen release 9"], "p1#outcome_2": ["aliases:FinnGen release 9"]}


def test_lines_continue_from_the_given_number_and_are_otherwise_the_first_copys():
    wide = [{**dict.fromkeys(EXTENDED_FIELDS, ""), **r} for r in ROWS]
    old, new = first.table(ROWS, BASES), t.table(wide, BASES, 197)
    assert [x["line"] for x in new] == [197, 198, 199]
    assert [{**x, "line": 0} for x in new] == [{**x, "line": 0} for x in old]
    assert t.table(wide, BASES) == old and set(new[0]) == set(t.FIELDS)


def test_without_a_reread_folder_the_gate_files_alone_give_the_identifiers(tmp_path):
    coder = tmp_path / "coder_1"
    (coder / "codes").mkdir(parents=True)
    (coder / "gates_v2").mkdir()
    (coder / "codes" / "p1.attempt1.json").write_text(json.dumps({"record_id": "p1"}))
    (coder / "codes" / "p1.attempt2.json").write_text(json.dumps({"record_id": "p1"}))
    for n, basis in ((1, "old"), (2, "name:FinnGen R9")):
        (coder / "gates_v2" / f"p1.attempt{n}.gate.json").write_text(json.dumps(
            {"rows": [{"side": "outcome", "machine_basis": [basis]},
                      {"side": "pqtl", "machine_basis": []},
                      {"side": "outcome", "machine_basis": ["x"]}]}))
    assert t.gate_bases(tmp_path, None) == {
        "p1#outcome_1": ["name:FinnGen R9"], "p1#pqtl_1": [], "p1#outcome_2": ["x"]}
    reread = tmp_path / "reread"
    reread.mkdir()
    (reread / "resolutions.json").write_text(json.dumps(
        {"resolutions": [{"row": "p1#outcome_2", "gate": {"machine_basis": ["y"]}}]}))
    assert t.gate_bases(tmp_path, reread)["p1#outcome_2"] == ["y"]
