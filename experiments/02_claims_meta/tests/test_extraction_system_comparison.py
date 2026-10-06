import argparse
import json

import pytest

import dry_run_extraction_system_comparison_synthetic as dry
import extraction_system_comparison as mc
from build_registry import N_BOOT, SEED
from dataset_relations import load_rows
from registry_secondaries import boot_ratio

N = 400


@pytest.fixture(scope="module")
def rows():
    return load_rows()


@pytest.fixture(scope="module")
def records(rows):
    return {"sol": mc.family_pair_records(dry.sol_claims(), rows),
            "run1": mc.family_pair_records(dry.luna_run1_claims(), rows),
            "run2": mc.family_pair_records(dry.luna_run2_claims(), rows)}


def counts(block):
    return block["count"], block["of"]


def test_family_pair_record_takes_direction_and_null_flag_from_all_its_records(records):
    with_null = records["sol"][("F1", "P3", "O3")]
    assert with_null.direction == "raises_with_nonsignificant"
    assert with_null.null_flag is True
    assert records["run1"][("F1", "P3", "O3")].direction == "raises"
    assert records["run1"][("F1", "P3", "O3")].null_flag is False
    only_null = records["sol"][("F2", "P4", "O4")]
    assert (only_null.direction, only_null.null_flag) == ("nonsignificant_only", True)
    assert len(records["sol"]) == 8


def test_presence_is_counted_in_each_direction_over_family_pair_records(records):
    block = mc.compare(records["sol"], records["run1"], 100, N, SEED)
    assert counts(block["a_in_b"]) == (6, 8)
    assert counts(block["b_in_a"]) == (6, 7)
    assert block["a_in_b"]["share"] == pytest.approx(0.75)
    assert block["b_in_a"]["share"] == pytest.approx(6 / 7)
    assert block["shared_records"] == 6
    swapped = mc.compare(records["run1"], records["sol"], 100, N, SEED)
    assert counts(swapped["a_in_b"]) == (6, 7)
    assert counts(swapped["b_in_a"]) == (6, 8)


def test_agreement_among_shared_records(records):
    among = mc.compare(records["sol"], records["run1"], 100, N, SEED)["among_shared"]
    assert counts(among["direction_class_equal"]) == (4, 6)
    assert among["both_directional"] == 6
    assert counts(among["same_direction"]) == (5, 6)
    assert among["opposite_direction"] == 1
    assert counts(among["null_flag_equal"]) == (5, 6)
    assert among["direction_classes_a_then_b"] == {
        "lowers|raises": 1, "raises_with_nonsignificant|raises": 1, "raises|raises": 4}
    assert among["release_identity"] == {"pqtl": {"identical": 5, "undetermined": 1},
                                         "outcome": {"identical": 6}}


def test_with_nonsignificant_form_is_read_as_its_direction_and_not_as_the_same_class(records):
    a = {k: v for k, v in records["sol"].items() if k == ("F1", "P3", "O3")}
    b = {k: v for k, v in records["run1"].items() if k == ("F1", "P3", "O3")}
    among = mc.compare(a, b, 100, N, SEED)["among_shared"]
    assert counts(among["direction_class_equal"]) == (0, 1)
    assert counts(among["same_direction"]) == (1, 1)
    assert counts(among["null_flag_equal"]) == (0, 1)


def test_nonsignificant_only_record_is_shared_but_not_directional(rows):
    a = mc.family_pair_records([dry.claim("R2", 1, "F2", 4, dry.NULL, dry.DEC)], rows)
    b = mc.family_pair_records([dry.claim("R2", 0, "F2", 4, "raises", dry.DEC)], rows)
    among = mc.compare(a, b, 100, N, SEED)["among_shared"]
    assert among["both_directional"] == 0
    assert among["same_direction"]["share"] is None
    assert among["opposite_direction"] == 0
    assert counts(among["null_flag_equal"]) == (0, 1)


def test_completion_keeps_run1_on_shared_family_pairs_and_adds_only_the_missing_ones(rows):
    completed = mc.completed_by(dry.luna_run1_claims(), dry.luna_run2_claims())
    assert sorted(c.claim_record_id for c in completed
                  if c.claim_record_id.startswith("run2/")) \
        == ["run2/R2:000"]
    assert len(completed) == len(dry.luna_run1_claims()) + 1
    fp = mc.family_pair_records(completed, rows)
    assert len(fp) == 8
    assert fp[("F3", "P2", "O2")].direction == "raises"
    assert fp[("F1", "P3", "O3")].null_flag is False
    assert [m.state for m in fp[("F4", "P3", "O3")].pqtl] == ["not_stated"]
    assert fp[("F2", "P1", "O1")].direction == "raises"


def test_completion_is_not_the_pooled_claims_of_the_two_runs(rows):
    pooled = mc.family_pair_records(dry.luna_run1_claims() + dry.luna_run2_claims(), rows)
    assert pooled[("F3", "P2", "O2")].direction == "mixed"
    completed = mc.family_pair_records(
        mc.completed_by(dry.luna_run1_claims(), dry.luna_run2_claims()), rows)
    assert completed[("F3", "P2", "O2")].direction != "mixed"


def test_run2_never_supplements_a_family_pair_run1_holds(rows):
    run1 = [dry.claim("R1", 0, "F1", 3, "raises", (("not_stated",), ("FinnGen R10",)))]
    run2 = [dry.claim("R1", 0, "F1", 3, "raises", dry.UKB),
            dry.claim("R1", 1, "F1", 3, dry.NULL, dry.UKB, "in women")]
    completed = mc.completed_by(run1, run2)
    assert [c.claim_record_id for c in completed] == ["run1/R1:000"]
    record = mc.family_pair_records(completed, rows)[("F1", "P3", "O3")]
    assert record.null_flag is False
    assert [m.state for m in record.pqtl] == ["not_stated"]


def test_record_id_and_restriction_to_sampled_abstracts():
    claims = dry.sol_claims()
    assert {mc.record_id(c) for c in claims} == {"R1", "R2", "R3", "R4"}
    kept = mc.restricted(claims, frozenset({"R1", "R3"}))
    assert sorted(c.claim_record_id for c in kept) == ["R1:000", "R1:001", "R1:002", "R1:003",
                                                       "R3:000", "R3:001"]
    relabeled = mc.completed_by(claims, [])
    assert {mc.record_id(c) for c in relabeled} == {"run1/R1", "run1/R2", "run1/R3", "run1/R4"}


def test_repeat_sample_comparisons_use_only_the_sampled_abstracts(rows):
    out = mc.comparison(dry.sol_claims(), dry.luna_run1_claims(), dry.luna_run2_claims(), rows,
                        dry.sol_repeat_claims(), frozenset(dry.SAMPLE), N, SEED)
    sample = out["repeat_sample"]
    assert sample["family_pair_records"] == {"sol": 5, "luna_run1": 5, "luna_run2": 5,
                                             "sol_repeat": 4}
    assert counts(sample["sol_vs_sol_repeat"]["a_in_b"]) == (4, 5)
    assert counts(sample["sol_vs_sol_repeat"]["b_in_a"]) == (4, 4)
    assert counts(sample["sol_vs_sol_repeat"]["among_shared"]["null_flag_equal"]) == (3, 4)
    assert counts(sample["sol_vs_luna_run1"]["a_in_b"]) == (5, 5)
    assert sample["sol_vs_luna_run1"]["among_shared"]["opposite_direction"] == 1
    assert counts(out["comparisons"]["sol_vs_luna_run1"]["a_in_b"]) == (6, 8)


def test_second_sol_run_outside_the_sample_raises(rows):
    with pytest.raises(mc.ComparisonError, match="outside the sample"):
        mc.comparison(dry.sol_claims(), dry.luna_run1_claims(), dry.luna_run2_claims(), rows,
                      dry.sol_repeat_claims(), frozenset({"R1"}), N, SEED)


def test_second_sol_run_and_sample_are_given_together(rows):
    with pytest.raises(mc.ComparisonError, match="together"):
        mc.comparison(dry.sol_claims(), dry.luna_run1_claims(), dry.luna_run2_claims(), rows,
                      dry.sol_repeat_claims(), None, N, SEED)
    with pytest.raises(mc.ComparisonError, match="together"):
        mc.comparison(dry.sol_claims(), dry.luna_run1_claims(), dry.luna_run2_claims(), rows,
                      None, frozenset(dry.SAMPLE), N, SEED)


def test_tables_recomputed_from_each_source(rows):
    out = mc.comparison(dry.sol_claims(), dry.luna_run1_claims(), dry.luna_run2_claims(), rows,
                        n_boot=N)
    for source, want in dry.EXPECTED_TABLES.items():
        estimates = out["h1_h2"][source]["estimates"]
        assert {k: estimates[k] for k in want} == want
    assert out["h1_h2"]["sol"]["estimates"]["h2_lower"] == pytest.approx(1 / 3)
    assert out["h1_h2"]["luna_run1"]["estimates"]["h2_upper"] == pytest.approx(0.5)
    assert out["h1_h2"]["luna_run1_completed"]["estimates"]["h1_pair_concordance"] \
        == pytest.approx(1.0)
    assert out["h1_h2"]["sol"]["estimates"]["h1_pair_concordance"] == pytest.approx(0.5)
    assert out["repeat_sample"] is None


def test_threshold_classifications_are_reported_for_sol_only(rows):
    out = mc.comparison(dry.sol_claims(), dry.luna_run1_claims(), dry.luna_run2_claims(), rows,
                        n_boot=N)
    assert (out["h1_h2"]["sol"]["h2_verdict"], out["h1_h2"]["sol"]["h2b_verdict"]) \
        == ("contradicted", "contradicted")
    assert set(mc.LUNA_SOURCES) == set(out["h1_h2"]) - {"sol"}
    for source in mc.LUNA_SOURCES:
        table = out["h1_h2"][source]
        assert [k for k in mc.VERDICT_KEYS if k in table] == []
        assert not [k for k in table if "verdict" in k or "attainable" in k]
        for kept in ("estimates", "denominators", "wilson_descriptive", "pair_bootstrap",
                     "protein_cluster_bootstrap", "family_jackknife", "difference_from_sol"):
            assert kept in table
    text = json.dumps({s: out["h1_h2"][s] for s in mc.LUNA_SOURCES})
    for word in ("supported", "contradicted", "verdict"):
        assert word not in text
    assert mc.VERDICT_KEYS == ("verdict_rule", "h2_verdict", "h2b_verdict",
                               "two_verdict_reading", "h2_supported_attainable")


def test_luna_estimates_are_also_given_as_differences_from_sol(rows):
    out = mc.comparison(dry.sol_claims(), dry.luna_run1_claims(), dry.luna_run2_claims(), rows,
                        n_boot=N)
    for source, want in dry.EXPECTED_DIFFERENCES.items():
        assert out["h1_h2"][source]["difference_from_sol"] == pytest.approx(want)
    sol = mc.h1_h2(dry.sol_claims(), rows, N, SEED)
    undefined = json.loads(json.dumps(sol))
    undefined["estimates"]["h1_pair_concordance"] = None
    assert mc.descriptive(undefined, sol)["difference_from_sol"]["h1_pair_concordance"] is None
    assert mc.descriptive(sol, sol)["difference_from_sol"] == pytest.approx(
        dict.fromkeys(mc.DIFFERENCE_KEYS, 0.0))


def test_luna_classifications_are_computed_only_outside_the_report(rows):
    internal = mc.h1_h2(dry.luna_run1_claims(), rows, N, SEED)
    assert internal["h2_verdict"] == "contradicted"
    assert internal["h2_supported_attainable"] is False


def test_sol_table_must_equal_the_registered_primary(rows):
    ours = mc.h1_h2(dry.sol_claims(), rows, N, SEED)
    mc.check_primary(ours, json.loads(json.dumps(ours)))
    other = json.loads(json.dumps(mc.h1_h2(dry.luna_run1_claims(), rows, N, SEED)))
    with pytest.raises(mc.ComparisonError, match="registered primary"):
        mc.check_primary(ours, other)
    altered = json.loads(json.dumps(ours))
    altered["h2_verdict"] = "supported"
    with pytest.raises(mc.ComparisonError, match="h2_verdict"):
        mc.check_primary(ours, altered)


def test_share_interval_is_the_pair_bootstrap_of_its_stream():
    units = [(("P1", "O1"), True), (("P1", "O1"), False), (("P2", "O2"), True),
             (("P3", "O3"), False), (("P3", "O3"), False), (("P3", "O3"), True)]
    block = mc.measure(units, 123, 2000, SEED)
    assert counts(block) == (3, 6)
    assert block["canonical_pairs"] == 3
    assert block["pair_bootstrap"] == boot_ratio([1.0, 1.0, 1.0], [2.0, 1.0, 3.0], 2000, SEED,
                                                 123)
    low, high = block["pair_bootstrap"]["interval"]
    assert 1 / 3 <= low <= 0.5 <= high <= 1.0
    assert block["imprecise_under_20"] is True


def test_share_interval_differs_between_streams():
    den = [i % 7 + 1 for i in range(200)]
    num = [min(i % 4, d) for i, d in enumerate(den)]
    units = [((f"P{i:03d}", "O"), j < num[i]) for i in range(200) for j in range(den[i])]
    block = mc.measure(units, 123, 2000, SEED)
    assert counts(block) == (sum(num), sum(den))
    assert block["canonical_pairs"] == 200
    assert block["imprecise_under_20"] is False
    floats = [float(n) for n in num], [float(d) for d in den]
    assert block["pair_bootstrap"] == boot_ratio(*floats, 2000, SEED, 123)
    assert block["pair_bootstrap"] != boot_ratio(*floats, 2000, SEED, 124)
    assert block["pair_bootstrap"] != boot_ratio(*floats, 2000, SEED, 0)


def test_share_with_no_units_is_undefined():
    block = mc.measure([], 100, N, SEED)
    assert (block["count"], block["of"], block["share"], block["wilson"]) == (0, 0, None, None)
    assert block["pair_bootstrap"]["interval"] is None


def test_constant_share_has_a_degenerate_interval():
    units = [((f"P{i}", "O"), True) for i in range(25)]
    block = mc.measure(units, 100, N, SEED)
    assert block["pair_bootstrap"]["interval"] == [1.0, 1.0]
    assert block["imprecise_under_20"] is False


def test_every_share_has_its_own_stream(rows):
    out = mc.comparison(dry.sol_claims(), dry.luna_run1_claims(), dry.luna_run2_claims(), rows,
                        dry.sol_repeat_claims(), frozenset(dry.SAMPLE), N, SEED)
    blocks = [*out["comparisons"].values(), out["repeat_sample"]["sol_vs_sol_repeat"],
              out["repeat_sample"]["sol_vs_luna_run1"],
              out["repeat_sample"]["luna_run1_vs_luna_run2"]]
    streams = [m["stream"] for b in blocks for m in (
        b["a_in_b"], b["b_in_a"], b["among_shared"]["direction_class_equal"],
        b["among_shared"]["same_direction"], b["among_shared"]["null_flag_equal"])]
    assert len(streams) == 30
    assert len(set(streams)) == 30
    assert min(streams) >= 100
    assert (out["replicates"], out["seed"]) == (N, SEED)
    assert N_BOOT == 10_000


def usage_of(tmp_path, role):
    raw, parsed = dry.write_exchanges(tmp_path), dry.write_parsed(tmp_path)
    attempted, failed = mc.attempted_abstracts(parsed[role])
    return mc.usage_totals([raw[role]], attempted, failed)


def test_cost_denominator_is_every_attempted_abstract(tmp_path):
    luna = usage_of(tmp_path, "luna_run1")
    assert luna["abstracts_attempted"] == 5
    assert luna["abstracts_with_a_billable_response"] == 4
    assert luna["abstracts_without_a_billable_response"] == 1
    assert luna["extraction_failed_abstracts"] == 1
    assert luna["failed_http_exchanges"] == 2
    assert luna["billable_requests"] == 5
    priced = mc.cost(luna, "luna_run1")
    assert priced["usd"] == pytest.approx(0.0009985)
    assert priced["usd_per_attempted_abstract"] == pytest.approx(0.0009985 / 5)
    assert priced["usd_per_attempted_abstract"] != pytest.approx(0.0009985 / 4)


def test_abstract_with_only_failed_http_exchanges_is_attempted_and_not_billed(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    for name in ("X1_attempt1.http1.json", "X1_attempt2.http1.json"):
        (raw / name).write_text(json.dumps({"status": 500, "response_text": "upstream error"}))
    (raw / "X2_attempt1.json").write_text(json.dumps(dry.exchange(200, 1000, 0, 0, 100)))
    parsed = tmp_path / "parsed.jsonl"
    parsed.write_text(json.dumps({"pmid": "X1", "status": "extraction_failed"}) + "\n"
                      + json.dumps({"pmid": "X2", "status": "ok"}) + "\n")
    attempted, failed = mc.attempted_abstracts([parsed])
    assert (attempted, failed) == (["X1", "X2"], ["X1"])
    totals = mc.usage_totals([raw], attempted, failed)
    assert totals["abstracts_attempted"] == 2
    assert totals["billable_requests"] == 1
    assert totals["abstracts_without_a_billable_response"] == 1
    assert totals["extraction_failed_abstracts"] == 1
    assert totals["failed_http_exchanges"] == 2
    priced = mc.cost(totals, "luna_run1")
    assert priced["usd"] == pytest.approx(0.00015)
    assert priced["usd_per_attempted_abstract"] == pytest.approx(0.000075)
    only_failed = mc.usage_totals([raw], ["X1"], ["X1"])
    assert (only_failed["billable_requests"], only_failed["tokens"]["input_tokens"]) == (0, 0)
    assert mc.cost(only_failed, "luna_run1")["usd_per_attempted_abstract"] == 0.0


def test_usage_skips_failed_tries_and_exchanges_of_other_records(tmp_path):
    sol = usage_of(tmp_path, "sol")
    assert (sol["billable_requests"], sol["abstracts_attempted"]) == (5, 5)
    assert sol["failed_http_exchanges"] == 1
    assert sol["records_outside_the_parsed_files_not_priced"] == 1
    assert sol["tokens"] == {"input_tokens": 5000, "cached_input_tokens": 3000,
                             "cache_write_tokens": 1500, "output_tokens": 1000,
                             "reasoning_tokens": 0}
    luna = usage_of(tmp_path / "again", "luna_run1")
    assert luna["tokens"]["output_tokens"] == 1600


def test_attempted_abstracts_come_from_the_parsed_files(tmp_path):
    parsed = dry.write_parsed(tmp_path)
    attempted, failed = mc.attempted_abstracts(parsed["luna_run1"])
    assert (attempted, failed) == (list(dry.ATTEMPTED), ["R5"])
    assert mc.attempted_abstracts(parsed["sol"]) == (list(dry.ATTEMPTED), [])
    with pytest.raises(mc.ComparisonError, match="twice"):
        mc.attempted_abstracts([parsed["sol"][0], parsed["sol"][0]])
    empty = tmp_path / "empty.jsonl"
    empty.write_text("")
    with pytest.raises(mc.ComparisonError, match="no record"):
        mc.attempted_abstracts([empty])


def three_usages(tmp_path):
    raw, parsed = dry.write_exchanges(tmp_path), dry.write_parsed(tmp_path)
    return {role: mc.cost(mc.usage_totals([raw[role]], *mc.attempted_abstracts(parsed[role])),
                          role) for role in mc.ROLES}


def test_cost_at_list_prices(tmp_path):
    usages = three_usages(tmp_path)
    sol = usages["sol"]
    assert sol["uncached_input_tokens"] == 500
    assert sol["usd_parts"] == pytest.approx({"input": 0.001, "cached_input": 0.0003,
                                              "cache_write": 0.00375, "output": 0.01})
    assert sol["usd"] == pytest.approx(0.01505)
    assert sol["usd_per_attempted_abstract"] == pytest.approx(0.00301)
    assert usages["luna_run2"]["usd"] == pytest.approx(0.000845)
    table = mc.cost_table(usages)
    assert table["sol_cost_per_attempted_abstract_over_luna"] == pytest.approx(
        dry.EXPECTED_RATIOS)
    assert mc.PRICES == {
        "gpt-6.1-sol": {"input": 2.0, "cached_input": 0.1, "cache_write": 2.5, "output": 10.0},
        "gpt-6-luna": {"input": 0.1, "cached_input": 0.01, "cache_write": 0.125, "output": 0.5}}
    assert sol["price_source"] == {
        "source": "OpenAI's pricing table, short-context column, as given by the author",
        "date_given": "2026-10-05", "unit": "USD per million tokens"}
    assert (sol["model"], usages["luna_run1"]["model"]) == ("gpt-6.1-sol", "gpt-6-luna")


def test_cost_table_requires_the_three_runs_over_the_same_abstracts(tmp_path):
    usages = three_usages(tmp_path)
    for missing in mc.ROLES:
        with pytest.raises(mc.ComparisonError, match="is required"):
            mc.cost_table({r: u for r, u in usages.items() if r != missing})
    swapped = {**usages, "luna_run2": usages["luna_run1"]}
    with pytest.raises(mc.ComparisonError, match="given for luna_run2"):
        mc.cost_table(swapped)
    wrong_model = {**usages, "sol": {**usages["sol"], "model": "gpt-6-luna"}}
    with pytest.raises(mc.ComparisonError, match="given for sol"):
        mc.cost_table(wrong_model)
    fewer = {**usages, "luna_run2": {**usages["luna_run2"], "attempted_sha256": "0" * 64,
                                     "abstracts_attempted": 4}}
    with pytest.raises(mc.ComparisonError, match="same abstracts"):
        mc.cost_table(fewer)


def test_compare_command_refuses_a_missing_usage_file(tmp_path, monkeypatch):
    files = dry.write_inputs(tmp_path)
    argv = ["extraction_system_comparison.py", "compare", "--sol", str(files["sol"]),
            "--luna-run1", str(files["luna_run1"]), "--luna-run2", str(files["luna_run2"]),
            "--usage-sol", "a.json", "--usage-luna-run1", "b.json", "--out",
            str(tmp_path / "out")]
    monkeypatch.setattr("sys.argv", argv)
    with pytest.raises(SystemExit):
        mc.main()
    assert not (tmp_path / "out").exists()


def test_cost_refuses_an_unknown_run_and_impossible_tokens():
    totals = {"abstracts_attempted": 1,
              "tokens": {"input_tokens": 10, "cached_input_tokens": 8, "cache_write_tokens": 5,
                         "output_tokens": 1, "reasoning_tokens": 0}}
    with pytest.raises(mc.ComparisonError, match="exceed"):
        mc.cost(totals, "luna_run1")
    with pytest.raises(mc.ComparisonError, match="no extraction run"):
        mc.cost(totals, "another-model")


def test_commands_write_once_and_the_file_equals_the_hand_worked_scenario(tmp_path):
    result = dry.run(tmp_path / "out", N)
    dry.check(result)
    assert result["amendment"] == "AMENDMENT_01_extraction_system_comparison.md"
    assert result["heading"] == "Extraction-system comparison"
    assert "model comparison" not in json.dumps(result).lower()
    assert set(result["inputs"]) == {"sol", "luna_run1", "luna_run2", "sol_repeat"}
    assert result["inputs"]["sol"]["claim_records"] == 9
    with pytest.raises(mc.ComparisonError, match="exists"):
        mc.main_usage(argparse.Namespace(
            role="sol", raw=[tmp_path / "out" / "raw_sol"],
            parsed=[tmp_path / "out" / "parsed_sol_search.jsonl",
                    tmp_path / "out" / "parsed_sol_chase1.jsonl"],
            out=tmp_path / "out" / "usage_sol.json"))
    with pytest.raises(mc.ComparisonError, match="exists"):
        mc.write_new(tmp_path / "out" / "extraction_system_comparison.json", {})


def test_compare_command_raises_when_the_sol_file_is_not_the_primary(tmp_path):
    files = dry.write_inputs(tmp_path)
    usage = {}
    for role, u in three_usages(tmp_path).items():
        usage[role] = tmp_path / f"usage_{role}.json"
        usage[role].write_text(json.dumps(u))
    primary = tmp_path / "sensitivity_tables.json"
    primary.write_text(json.dumps({"primary": mc.h1_h2(dry.luna_run2_claims(), load_rows(), N,
                                                       SEED)}))
    with pytest.raises(mc.ComparisonError, match="registered primary"):
        mc.main_compare(argparse.Namespace(
            sol=files["sol"], luna_run1=files["luna_run1"], luna_run2=files["luna_run2"],
            sol_repeat=None, repeat_sample=[], sol_tables=primary, usage_sol=usage["sol"],
            usage_luna_run1=usage["luna_run1"], usage_luna_run2=usage["luna_run2"], n_boot=N,
            out=tmp_path / "out"))
    assert not (tmp_path / "out" / "extraction_system_comparison.json").exists()
