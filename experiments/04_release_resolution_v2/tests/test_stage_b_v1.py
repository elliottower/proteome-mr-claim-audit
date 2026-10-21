import random

import pytest

import audit_pricing as apr
import coding_packets_v2 as cp2
import stage_b_v1 as sb


def acc(ok, reasons=()):
    return {"accepted": ok, "unresolved_reasons": list(reasons)}


def test_records_split_by_unresolved_rows_and_the_audit_draws_its_seed():
    rows = {f"r{i:02d}": [f"r{i:02d}a", f"r{i:02d}b"] for i in range(100)}
    accepted = {}
    for i in range(100):
        accepted[f"r{i:02d}a"] = acc(True)
        accepted[f"r{i:02d}b"] = acc(i % 3 != 0, ["release_not_identified"] if i % 5 == 0 else [])
    supp = {f"r{i:02d}" for i in range(100) if i != 1}
    got = sb.records(rows, accepted, supp)
    unres = {f"r{i:02d}" for i in range(100) if (i % 3 == 0 or i % 5 == 0) and i != 1}
    assert set(got["unresolved_records"]) == unres
    resolved = sorted(set(supp) - unres)
    assert got["resolved_records_with_a_supplement"] == resolved
    assert got["audit_records"] == sorted(random.Random(20261042).sample(resolved, 30))


def test_the_cost_adds_output_above_the_base_and_reads_the_prompt_from_the_cache():
    rec = {"record_id": "r", "carried": 1000, "packets": [50_000, 30_000]}
    base = apr.record_cost(rec, 80_000)["6000"]
    got = sb.record_cost(rec, 80_000, {"claude-sonnet-5-5": 6000, "gpt-6.1-sol": 6000})
    assert got == pytest.approx(base, abs=0.02)
    more = sb.record_cost(rec, 80_000, {"claude-sonnet-5-5": 7000, "gpt-6.1-sol": 6000})
    assert more - got == pytest.approx(2 * 1000 * cp2.PRICE["claude-sonnet-5-5"]["output"] / 1e6)


def test_the_output_floor_and_the_decision_rule():
    assert sb.output_tokens({"a": 2499.5, "b": 7100.2}) == {"a": 6000, "b": 7100}
    assert sb.decide(470.0, 90.0)["stage_b_runs"] is True
    assert sb.decide(470.01, 0.0)["stage_b_runs"] is False
    assert sb.decide(400.0, 160.01)["stage_b_runs"] is False
    assert sb.decide(400.0, 160.0)["stage_b_runs"] is True
