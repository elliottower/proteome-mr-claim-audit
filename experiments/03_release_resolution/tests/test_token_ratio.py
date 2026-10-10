import pytest

import token_ratio as tr


def test_the_draw_is_seeded_sorted_and_the_same_for_the_same_seed():
    ids = [f"r{i}" for i in range(30)]
    one, two = tr.draw(ids, 5, 7), tr.draw(list(reversed(ids)), 5, 7)
    assert one == two == sorted(one) and len(one) == 5 and tr.draw(ids, 5, 8) != one


def test_ratios_pool_characters_over_tokens_and_give_the_smallest():
    rows = [{"characters": 1000, "openai_tokens": 250}, {"characters": 300, "openai_tokens": 150}]
    got = tr.ratios(rows, "openai")
    assert got["characters_per_token_pooled"] == pytest.approx(1300 / 400)
    assert got["characters_per_token_smallest"] == pytest.approx(2.0)
