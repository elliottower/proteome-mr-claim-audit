import pytest

import sol_usage as su


def test_cost_prices_each_token_class_once():
    tokens = dict(input=1_000_000, cached=600_000, cache_write=300_000, output=200_000)
    assert su.cost(tokens) == pytest.approx(0.1 * 2.0 + 0.6 * 0.1 + 0.3 * 2.5 + 0.2 * 10.0)


def test_add_reads_cached_and_cache_write_from_the_input_details():
    tokens = dict(requests=0, input=0, cached=0, cache_write=0, output=0, reasoning=0)
    su.add(tokens, {"input_tokens": 1166, "output_tokens": 84,
                    "input_tokens_details": {"cache_write_tokens": 1163, "cached_tokens": 0},
                    "output_tokens_details": {"reasoning_tokens": 16}})
    su.add(tokens, {"input_tokens": 1200, "output_tokens": 100,
                    "input_tokens_details": {"cached_tokens": 1163}})
    assert tokens == dict(requests=2, input=2366, cached=1163, cache_write=1163, output=184,
                          reasoning=16)
