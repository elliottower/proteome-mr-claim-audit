import pytest

import audit_pricing as ap
import coding_packets_v2 as cp2


def rec(chars, n=1, carried=100):
    return {"record_id": "r", "carried": carried, "packets": [chars] * n}


def test_a_record_is_priced_with_the_prompt_read_from_the_cache():
    got = ap.record_cost(rec(1000), 500)
    expected = 0.0
    for m, p in cp2.PRICE.items():
        r = ap.PREFLIGHT[m]
        expected += (1000 / r * p["new"] + 500 / r * p["cached"] + 1500 * p["output"]) / 1e6
    assert got["1500"] == pytest.approx(expected, abs=0.01)


def test_the_audit_bounds_order_and_the_escalation_sums_every_record():
    records = [rec(c) for c in (10_000_000, 1_000, 2_000, 3_000)]
    got = ap.price(records, 0, audit=2)
    costs = sorted((ap.record_cost(r, 0)["1500"] for r in records), reverse=True)
    assert got["1500"]["audit_upper_bound_usd"] == pytest.approx(costs[0] + costs[1], abs=0.01)
    assert got["1500"]["escalation_all_records_usd"] == pytest.approx(sum(costs), abs=0.01)
    assert got["1500"]["audit_expected_usd"] == pytest.approx(sum(costs) / 4 * 2, abs=0.01)
    assert got["1500"]["audit_upper_bound_usd"] >= got["1500"]["audit_expected_usd"]
    assert got["6000"]["escalation_all_records_usd"] > got["1500"]["escalation_all_records_usd"]


def test_fewer_records_than_the_audit_size_take_them_all():
    records = [rec(1000), rec(2000)]
    got = ap.price(records, 0, audit=30)
    assert got["1500"]["audit_expected_usd"] == pytest.approx(
        got["1500"]["escalation_all_records_usd"], abs=0.01)
