import pytest

import gated_out_remaining as gr


def rec(i):
    return {"pmid": i, "title": f"t{i}", "abstract": f"a{i}"}


def test_remaining_is_the_marked_records_in_no_batch_in_marked_order():
    marked = [rec(i) for i in ("e", "a", "d", "b", "c")]
    assert gr.remaining(marked, [[rec("d")], [rec("a"), rec("c")]]) == [rec("e"), rec("b")]


def test_no_batch_leaves_every_marked_record():
    marked = [rec("x"), rec("y")]
    assert gr.remaining(marked, []) == marked


def test_a_sampled_record_that_was_never_marked_raises():
    with pytest.raises(gr.RemainingError):
        gr.remaining([rec("a")], [[rec("z")]])


def test_a_repeated_record_raises():
    with pytest.raises(gr.RemainingError):
        gr.remaining([rec("a"), rec("a")], [])
    with pytest.raises(gr.RemainingError):
        gr.remaining([rec("a"), rec("b")], [[rec("a")], [rec("a")]])
