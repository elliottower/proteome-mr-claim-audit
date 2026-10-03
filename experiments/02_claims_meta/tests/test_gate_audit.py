import json
import math
import pathlib
import random
import re

import pytest

import gate_audit as ga

PREREG = (pathlib.Path(ga.__file__).resolve().parent.parent / "PREREG.md").read_text()


def ids(n):
    return [f"R{i:05d}" for i in range(n)]


def decided(order, n, positives=(), failed=()):
    out = {i: "ineligible" for i in order[:n]}
    out.update({order[k]: "eligible" for k in positives})
    out.update({order[k]: "extraction_failed" for k in failed})
    return out


def exact_cdf(x, n, p):
    return sum(math.comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(x + 1))


def test_order_is_a_seeded_shuffle_of_the_sorted_ids():
    marked = ids(1000)
    order = ga.draw_order(marked)
    assert sorted(order) == marked and order != marked
    shuffled = marked[:]
    random.Random().shuffle(shuffled)
    assert ga.draw_order(shuffled) == order
    assert ga.draw_order(marked, seed=ga.SEED + 1) != order
    with pytest.raises(ga.GateAuditError):
        ga.draw_order(["a", "a"])


def test_order_gives_every_record_the_same_chance_of_the_first_batch():
    marked = ids(40)
    hits = {i: 0 for i in marked}
    for seed in range(3000):
        for i in ga.draw_order(marked, seed=seed)[:10]:
            hits[i] += 1
    for i in marked:
        assert hits[i] / 3000 == pytest.approx(0.25, abs=0.04)


def test_batches_are_consecutive_600s_up_to_3000():
    order = ga.draw_order(ids(3500))
    batches = [ga.batch_ids(order, j) for j in range(1, 8)]
    assert [len(b) for b in batches] == [600, 600, 600, 600, 600, 0, 0]
    assert [i for b in batches for i in b] == order[:3000]
    assert [len(ga.batch_ids(order[:1000], j)) for j in (1, 2, 3)] == [600, 400, 0]


@pytest.mark.parametrize("x, n", [(0, 20), (1, 50), (3, 50), (7, 200), (15, 400)])
def test_upper_bound_solves_the_binomial_tail_exactly(x, n):
    p = ga.upper_bound(x, n)
    assert exact_cdf(x, n, p) == pytest.approx(0.05, abs=1e-9)
    assert exact_cdf(x, n, ga.upper_bound(x, n, 0.025)) == pytest.approx(0.025, abs=1e-9)
    assert ga.upper_bound(x, n) > x / n


@pytest.mark.parametrize("x, n", [(1, 50), (3, 50), (7, 200)])
def test_lower_bound_solves_the_other_tail(x, n):
    p = ga.lower_bound(x, n, 0.025)
    assert 1 - exact_cdf(x - 1, n, p) == pytest.approx(0.025, abs=1e-9)
    assert p < x / n


def test_bounds_at_the_edges():
    assert ga.upper_bound(0, 600) == pytest.approx(1 - 0.05 ** (1 / 600), rel=1e-9)
    assert ga.upper_bound(0, 598) < ga.TOLERANCE < ga.upper_bound(0, 597)
    assert ga.upper_bound(1, 600) == pytest.approx(0.0078815, abs=2e-6)
    assert ga.upper_bound(1, 1200) < ga.TOLERANCE < ga.upper_bound(2, 1200)
    assert ga.lower_bound(0, 50) == 0.0 and ga.upper_bound(50, 50) == 1.0
    assert ga.upper_bound(0, 0) is None and ga.lower_bound(0, 0) is None


def test_a_clean_first_batch_stops_the_audit():
    marked = ids(1500)
    order = ga.draw_order(marked)
    state = ga.audit(marked, decided(order, 600))
    assert (state["sampled"], state["judged"], state["judged_eligible_or_uncertain"]) == (
        600, 600, 0)
    assert state["finished"] and state["stopping_reason"] == "upper_bound_below_tolerance"
    assert state["cap_reached_without_satisfying_tolerance"] is False
    assert state["next_batch"] is None and state["share"] == 0
    assert state["marked_records_not_judged"] == 900
    assert state["estimated_eligible_records_not_judged"] == 0
    assert state["estimated_eligible_records_not_judged_upper_one_sided_95"] == pytest.approx(
        900 * (1 - 0.05 ** (1 / 600)))


def test_a_positive_in_the_first_batch_draws_a_second_batch():
    marked = ids(10000)
    order = ga.draw_order(marked)
    first = ga.audit(marked, decided(order, 600, positives=[17]))
    assert not first["finished"] and first["next_batch"] == 2
    assert first["stopping_reason"] is None
    assert first["positive_record_ids"] == [order[17]]
    second = ga.audit(marked, decided(order, 1200, positives=[17]))
    assert second["finished"] and second["stopping_reason"] == "upper_bound_below_tolerance"
    assert second["share"] == pytest.approx(1 / 1200)
    assert second["marked_records_not_judged"] == 8800
    assert second["estimated_eligible_records_not_judged"] == pytest.approx(8800 / 1200)
    low, high = second["estimated_eligible_records_not_judged_interval_two_sided_95"]
    assert low < 8800 / 1200 < second[
        "estimated_eligible_records_not_judged_upper_one_sided_95"] < high


def test_two_positives_in_1200_draw_a_third_batch():
    marked = ids(10000)
    order = ga.draw_order(marked)
    state = ga.audit(marked, decided(order, 1200, positives=[17, 900]))
    assert not state["finished"] and state["next_batch"] == 3
    assert ga.audit(marked, decided(order, 1800, positives=[17, 900]))["finished"]


def test_audit_stops_at_3000_sampled_whatever_the_bound():
    marked = ids(10000)
    order = ga.draw_order(marked)
    positives = [k for j in range(5) for k in (600 * j, 600 * j + 1, 600 * j + 2)]
    for n in (600, 1200, 1800, 2400):
        state = ga.audit(marked, decided(order, n, positives=[k for k in positives if k < n]))
        assert not state["finished"] and state["next_batch"] == n // 600 + 1
    last = ga.audit(marked, decided(order, 3000, positives=positives))
    assert last["finished"] and last["stopping_reason"] == "maximum_sample_reached"
    assert last["cap_reached_without_satisfying_tolerance"] is True
    assert last["upper_bound_one_sided_95"] > ga.TOLERANCE
    met_at_cap = ga.audit(marked, decided(order, 3000, positives=positives[:7]))
    assert ga.upper_bound(7, 2400) > ga.TOLERANCE > ga.upper_bound(7, 3000)
    assert met_at_cap["stopping_reason"] == "upper_bound_below_tolerance"
    assert met_at_cap["cap_reached_without_satisfying_tolerance"] is False
    assert last["estimated_eligible_records_not_judged"] == pytest.approx(7000 * 15 / 3000)


def test_audit_of_fewer_marked_records_than_a_batch_judges_them_all():
    marked = ids(400)
    order = ga.draw_order(marked)
    state = ga.audit(marked, decided(order, 400, positives=[0, 1, 2]))
    assert state["finished"] and state["stopping_reason"] == "every_marked_record_sampled"
    assert state["cap_reached_without_satisfying_tolerance"] is False
    assert state["marked_records_not_judged"] == 0
    assert state["estimated_eligible_records_not_judged"] == 0
    assert len(state["positive_record_ids"]) == 3


def test_failed_eligibility_calls_are_sampled_but_not_judged():
    marked = ids(5000)
    order = ga.draw_order(marked)
    two = ga.audit(marked, decided(order, 600, failed=[3, 4]))
    assert (two["judged"], two["eligibility_call_failed"], two["finished"]) == (598, 2, True)
    assert two["marked_records_not_judged"] == 4402
    four = ga.audit(marked, decided(order, 600, failed=[3, 4, 5, 6]))
    assert four["judged"] == 596 and not four["finished"] and four["next_batch"] == 2


def test_audit_before_any_decision_asks_for_the_first_batch():
    state = ga.audit(ids(900), {})
    assert not state["finished"] and state["next_batch"] == 1 and state["sampled"] == 0
    assert ga.audit([], {})["finished"]


def test_decisions_must_hold_whole_batches_of_the_order():
    marked = ids(2000)
    order = ga.draw_order(marked)
    with pytest.raises(ga.GateAuditError):
        ga.audit(marked, decided(order, 599))
    with pytest.raises(ga.GateAuditError):
        ga.audit(marked, decided(order, 700))
    swapped = decided(order, 600)
    del swapped[order[0]]
    swapped[order[1999]] = "ineligible"
    with pytest.raises(ga.GateAuditError):
        ga.audit(marked, swapped)


def test_script_draws_the_next_batch_and_then_closes_the_audit(tmp_path, monkeypatch):
    marked = ids(700)
    order = ga.draw_order(marked)
    (tmp_path / "gated_out.jsonl").write_text("".join(
        json.dumps({"pmid": i, "title": "t", "abstract": "word " * 60}) + "\n" for i in marked))
    (tmp_path / "no_abstract.jsonl").write_text("".join(
        json.dumps({"pmid": f"N{i}", "title": "t"}) + "\n" for i in range(3)))
    first = tmp_path / "gate1.decisions.jsonl"
    first.write_text("".join(json.dumps({"pmid": i, "decision": d}) + "\n"
                             for i, d in decided(order, 600, positives=[5]).items()))
    monkeypatch.setattr("sys.argv", ["gate_audit.py", "--round-dir", str(tmp_path),
                                     "--decisions", str(first)])
    ga.main()
    batch = [json.loads(l)["pmid"] for l in
             (tmp_path / "gate_sample_batch_02.jsonl").read_text().splitlines()]
    assert sorted(batch) == sorted(order[600:]) and len(batch) == 100
    state = json.loads((tmp_path / "gate_audit_after_batch_01.json").read_text())
    assert not state["finished"] and state["next_batch"] == 2
    assert state["marked_records"] == 700 and state["no_abstract_records_of_the_round"] == 3
    with pytest.raises(ga.GateAuditError):
        ga.main()
    second = tmp_path / "gate2.decisions.jsonl"
    second.write_text("".join(json.dumps({"pmid": i, "decision": "ineligible"}) + "\n"
                              for i in order[600:]))
    monkeypatch.setattr("sys.argv", ["gate_audit.py", "--round-dir", str(tmp_path),
                                     "--decisions", str(first), str(second)])
    ga.main()
    final = json.loads((tmp_path / "gate_audit_after_batch_02.json").read_text())
    assert final["finished"] and final["stopping_reason"] == "every_marked_record_sampled"
    assert final["positive_record_ids"] == [order[5]] and final["seed"] == 20261001
    assert not (tmp_path / "gate_sample_batch_03.jsonl").exists()


def test_registered_numbers_are_the_ones_in_the_preregistration():
    text = " ".join(PREREG.split())
    m = re.search(r"batches of (\d+) .*?`random\.Random\((\d+)\)`.*?is below ([\d.]+)%"
                  r".*?or ([\d,]+) records have been sampled", text)
    assert (int(m.group(1)), int(m.group(2))) == (ga.BATCH, ga.SEED)
    assert float(m.group(3)) / 100 == pytest.approx(ga.TOLERANCE)
    assert int(m.group(4).replace(",", "")) == ga.MAX_SAMPLED
