import pytest

import coding_packets_v2 as cp2
import stage_pricing as sp


def match(rec, ident, route="R1", unit="u"):
    return {"record_id": rec, "identifier": ident, "source_key": f"{route}:1:x",
            "unit_id": unit, "side": "outcome", "expected_row": "X", "type": "gwas_catalog"}


def test_one_candidate_per_record_and_identifier_from_stage_a_text_only():
    found = [match("r1", "A", unit="u2"), match("r1", "A", unit="u1"), match("r1", "B", "R2")]
    got = sp.stratified_draw(found, 1, 150)
    assert [(c["identifier"], c["unit_id"]) for c in got] == [("A", "u1")]


def test_at_most_five_per_record_and_the_maximum_overall():
    found = [match(f"r{i}", f"I{j}") for i in range(40) for j in range(9)]
    got = sp.stratified_draw(found, 20261011, 150)
    per = {}
    for c in got:
        per[c["record_id"]] = per.get(c["record_id"], 0) + 1
    assert max(per.values()) == 5 and len(got) == 150
    assert got == sp.stratified_draw(list(reversed(found)), 20261011, 150)
    assert got != sp.stratified_draw(found, 7, 150)


def test_output_sensitivity_adds_the_extra_output_at_the_output_price():
    cost = {"claude-sonnet-5-5": {"requests": 100, "usd": 10.0},
            "gpt-6.1-sol": {"requests": 100, "usd": 5.0}, "total_usd": 15.0}
    got = sp.with_outputs(cost)
    assert got["1500"]["total_usd"] == pytest.approx(15.0)
    assert got["3000"]["claude-sonnet-5-5"] == pytest.approx(10.0 + 100 * 1500 * 10 / 1e6)
    assert got["6000"]["total_usd"] == pytest.approx(15.0 + 2 * 100 * 4500 * 10 / 1e6)
    assert set(got["3000"]) == set(cp2.PRICE) | {"total_usd"}
