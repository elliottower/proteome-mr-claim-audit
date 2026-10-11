import pytest

import estimate_cost as base
import estimate_cost_v2 as ev


def result(rid, full, page=False):
    sources = [{"route": "R3" if page else "R1", "text": "x", "characters": full}] if full else []
    return {"record_id": rid, "status": "retrieved" if full else "no_source", "sources": sources}


def cut(*files):
    return {"files": [{"cut": c, "characters_before": b, "characters_after": a}
                      for c, b, a in files]}


def build(n_cut_papers=3):
    results = [result("a", 50_000), result("b", 300), result("c", 0)]
    cuts = {"a": cut((True, 900_000, 100_000), (False, 10_000, 10_000)), "b": cut(), "c": cut()}
    for i in range(n_cut_papers - 1):
        results.append(result(f"p{i}", 20_000))
        cuts[f"p{i}"] = cut((True, 250_000 * (i + 1), 5_000))
    abstracts = {r["record_id"]: 1_000 for r in results}
    return ev.estimate(results, cuts, abstracts, 70_000)


def test_coding_reads_full_texts_and_supplements_as_cut():
    out = build()
    a = next(r for r in out["per_record"] if r["record_id"] == "a")
    assert a["supplement_characters_read"] == 110_000 and a["coding_requests"] == 1
    assert out["supplement_characters_read"] == 110_000 + 5_000 + 5_000
    assert out["supplement_characters_before_cut"] == 910_000 + 250_000 + 500_000
    sol = out["lines"]["coding"]["gpt-6.1-sol"]
    assert sol["requests"] == out["coding_requests_per_model"] == 5
    assert sol["new_input_tokens"] == round((50_000 + 110_000 + 300 + 40_000 + 10_000 + 70_000)
                                            / 4.28)


def test_c2_gives_the_expectation_and_the_range_over_draws_not_the_largest_papers():
    out = ev.estimate(*_many(40))
    c2 = out["lines"]["c2_sampled_pass"]
    assert c2["papers_with_a_cut_supplement"] == 40 and c2["sample_size"] == 30
    assert c2["cheapest_sample_usd"] <= c2["percentile_5_usd"] <= c2["expected_usd"]
    assert c2["expected_usd"] <= c2["percentile_95_usd"] <= c2["dearest_sample_usd"]
    assert c2["cheapest_sample_usd"] < c2["dearest_sample_usd"]


def _many(n):
    results, cuts = [], {}
    for i in range(n):
        results.append(result(f"r{i}", 10_000))
        cuts[f"r{i}"] = cut((True, 200_000 + 100_000 * i, 1_000))
    return results, cuts, {r["record_id"]: 500 for r in results}, 70_000


def test_c2_samples_all_papers_when_fewer_than_30_and_the_failure_path_is_both_models():
    out = build()
    c2 = out["lines"]["c2_sampled_pass"]
    assert c2["sample_size"] == 3 == c2["papers_with_a_cut_supplement"]
    assert c2["expected_usd"] == pytest.approx(c2["dearest_sample_usd"], abs=0.011)
    fail = out["lines"]["c2_failure_path_contingent"]
    assert set(fail) == set(base.RATIO)
    assert fail["gpt-6.1-sol"]["requests"] == 3 + 1 + 2


def test_a_short_page_is_counted_as_retrieved_and_listed_apart():
    results = [result("w", 300, page=True), result("j", 30_000)]
    out = ev.estimate(results, {"w": cut(), "j": cut()}, {"w": 10, "j": 10}, 1_000)
    assert out["records_whose_only_full_text_is_a_page_under_1000_characters"] == ["w"]
    assert out["records_by_status"] == {"retrieved": 2}


def test_a_record_without_a_cut_stops_the_estimate():
    with pytest.raises(ev.EstimateError):
        ev.estimate([result("a", 10)], {}, {"a": 1}, 10)
