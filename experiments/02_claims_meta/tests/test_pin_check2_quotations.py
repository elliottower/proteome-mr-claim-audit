import pytest
import yaml

import pin_check2_quotations as pins
from pin_passage_occurrence_v2 import PinError
from test_pin_passage_occurrence_v2 import DUPLICATED, S, fake, folder, held

PASSAGE = {"passage_id": "p001", "sentences": ["Some intro text.", S, "Final words here."],
           "claims_file": "claims/x.yaml", "line": 3, "source_read": "full_text"}
ROWS = {"p1#outcome_1": {"passages": [PASSAGE]},
        "p1#pqtl_1": {"passages": [dict(PASSAGE, sentences=["Lead in two."])]}}


def answer(row, sentence, other=None):
    return {"row": row, "quote": sentence, "sentence_supplied": sentence,
            "quote_from_another_row": other}


def test_a_quotation_is_pinned_under_the_c2_id_of_its_own_row(tmp_path):
    root = folder(tmp_path, DUPLICATED)
    assert pins.pin_answer(answer("p1#pqtl_1", "Lead in two."), ROWS, root,
                           fake(DUPLICATED)) == "pinned"
    how = pins.pin_answer(answer("p1#outcome_1", S), ROWS, root, fake(DUPLICATED))
    assert how == "pinned_with_source_text_either_side"
    assert held(root)["outcome_1_c2"]["quotes"][0]["exact"] == S


def test_a_sentence_supplied_under_another_row_is_pinned_under_the_answers_own_id(tmp_path):
    root = folder(tmp_path, DUPLICATED)
    pins.pin_answer(answer("p1#pqtl_1", S, other="p1#outcome_1"), ROWS, root, fake(DUPLICATED))
    assert list(held(root)) == ["pqtl_1_c2"]


def test_a_second_run_leaves_a_pin_and_refuses_an_id_holding_another_sentence(tmp_path):
    root = folder(tmp_path, DUPLICATED)
    pins.pin_answer(answer("p1#outcome_1", S), ROWS, root, fake(DUPLICATED))
    before = (root / "claims" / "x.yaml").read_text()
    assert pins.pin_answer(answer("p1#outcome_1", S), ROWS, root,
                           fake(DUPLICATED)) == "already_pinned"
    assert (root / "claims" / "x.yaml").read_text() == before
    with pytest.raises(pins.QuotationPinError):
        pins.pin_answer(answer("p1#outcome_1", "Final words here."), ROWS, root,
                        fake(DUPLICATED))


def test_a_sentence_not_in_the_named_rows_passages_will_not_pin(tmp_path):
    root = folder(tmp_path, DUPLICATED)
    with pytest.raises(PinError):
        pins.pin_answer(answer("p1#pqtl_1", S), ROWS, root, fake(DUPLICATED))
    assert held(root) == {}
    assert yaml.safe_load((root / "claims" / "x.yaml").read_text())["claims"] == {}
