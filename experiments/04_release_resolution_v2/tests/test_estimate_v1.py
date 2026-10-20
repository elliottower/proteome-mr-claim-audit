import pytest

import coding_packets_v2 as cp2
import estimate_v1 as est
import judge_v2 as j2


def packet(rec, rows, text="x" * 1000):
    return {"record_id": rec, "title": "t", "files": [{"file_id": "abstract", "kind": "abstract",
                                                      "text": text}],
            "accession_table_rows": [], "rows": [{"row_id": r} for r in rows]}


def test_rows_judged_use_the_first_stage_a_shares_and_the_audit_minimum():
    packets = [packet("a", [f"s{i}" for i in range(657)]), packet("b", [f"c{i}" for i in range(70)])]
    got = est.rows_judged(packets, {f"c{i}" for i in range(70)})
    assert got["expected_disagreements"] == pytest.approx(172.0)
    assert got["expected_audit_rows"] == 56
    assert got["upper_rows_judged"] == 727
    small = est.rows_judged([packet("a", ["s1", "s2"])], set())
    assert small["expected_audit_rows"] == 30


def test_a_judge_row_prices_cached_system_new_body_and_output():
    m = j2.FABLE
    p = j2.PRICE[m]
    r = j2.MIN_RATIO[m]
    got = est.judge_row_usd(m, 19_800, 4_000, 1_500)
    assert got == pytest.approx((19_800 / r * p["cached"] + 10_000 / r * p["new"]
                                 + 1_500 * p["output"]) / 1e6)


def test_the_coder_estimate_is_the_first_registrations_layout_cost():
    packets = [packet("a", ["s1"]), packet("b", ["s2"], "y" * 50_000)]
    got = est.coders(packets, 80_000)
    recs = [{"record_id": p["record_id"], "carried": 0, "packets": [est.packet_chars(p)]}
            for p in packets]
    base = cp2.layout_cost(recs, 80_000, est.RATIOS["preflight_ratios"], True)
    assert got["preflight_ratios"]["1500"]["claude-sonnet-5-5"] == pytest.approx(
        base["claude-sonnet-5-5"]["usd"], abs=0.006)
    assert (got["preflight_ratios"]["measured_output_of_the_first_stage_a"]["claude-sonnet-5-5"]
            > got["preflight_ratios"]["1500"]["claude-sonnet-5-5"])
