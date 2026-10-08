import json

import pytest

import manual_coding_check3_sample as xlsx
import manual_coding_check3_sample_json as js
from test_manual_coding_check3_sample import sheet


def marks_file(path, items):
    path.write_text(json.dumps({"sample": "s", "saved_at": "t", "marks": [
        {"n": i, "table_line": str(line), "author_confirms": mark, "author_note": note}
        for i, (line, (mark, note)) in enumerate(items.items(), 1)]}))
    return path


def test_json_marks_are_read_as_the_spreadsheet_reader_reads_the_same_marks(tmp_path):
    items = {3: (" Yes", ""), 5: ("NO", "release  6 in the sentence")}
    from_json = js.read_marks_json(marks_file(tmp_path / "m.json", items), [3, 5])
    assert from_json == xlsx.read_marks(sheet(tmp_path / "m.xlsx", items), [3, 5])
    assert from_json == {3: ("yes", ""), 5: ("no", "release 6 in the sentence")}


@pytest.mark.parametrize("items,sampled", [
    ({3: ("yes", ""), 5: ("", "")}, [3, 5]),
    ({3: ("yes", ""), 5: ("maybe", "")}, [3, 5]),
    ({3: ("yes", ""), 6: ("yes", "")}, [3, 5]),
    ({3: ("yes", "")}, [3, 5]),
    ({3: ("yes", ""), 5: ("yes", ""), 7: ("yes", "")}, [3, 5]),
])
def test_a_blank_or_other_mark_or_lines_that_are_not_the_sample_block(tmp_path, items, sampled):
    with pytest.raises(js.SampleError):
        js.read_marks_json(marks_file(tmp_path / "m.json", items), sampled)


def test_a_line_given_twice_blocks(tmp_path):
    path = tmp_path / "m.json"
    path.write_text(json.dumps({"marks": [
        {"table_line": "3", "author_confirms": "yes", "author_note": ""},
        {"table_line": "3", "author_confirms": "yes", "author_note": ""}]}))
    with pytest.raises(js.SampleError):
        js.read_marks_json(path, [3])


def test_the_rules_and_the_table_are_the_sealed_readers():
    assert js.decide is xlsx.decide and js.apply is xlsx.apply and js.draw is xlsx.draw
    assert (js.SEED, js.N) == (20261008, 20)
