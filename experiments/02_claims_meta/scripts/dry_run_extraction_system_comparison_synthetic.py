# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5", "rapidfuzz==3.14.6"]
# ///
"""Dry run of the extraction-system comparison (AMENDMENT_01_extraction_system_comparison.md)
on synthetic records: registry claim files of GPT-6.1 Sol, of two Luna runs and of a second Sol
run on a repeat sample, and stored exchanges with usage blocks and parsed extraction files for
the three extraction runs, through scripts/extraction_system_comparison.py to every quantity the
amendment reports.

Every record is invented here; no in-window record is read and no model is called. The dataset
names are rows of the committed dictionary. The run raises if a reported quantity differs from
the value worked by hand in EXPECTED.

Scenario. Four families (F1 to F4, one record each, R1 to R4), six pairs. Sol holds eight
family–pair records. Luna run 1 lacks two of them (F2 on pair 1, F2's null result on pair 4),
gives the opposite direction for F3 on pair 2, lacks F1's null record on pair 3, names no pQTL
dataset for F4 on pair 3, and holds one record Sol lacks (F4 on pair 6). Luna run 2 lacks only
F2 on pair 4. The repeat sample is the abstracts R1 and R3; the second Sol run lacks F1's null
record on pair 3 and F3's record on pair 5.

Cost scenario. Each run attempted five abstracts (R1 to R5; R5 yields no claim). Luna run 1 has
only failed HTTP exchanges for R5, which it records `extraction_failed`: R5 is in the
denominator of its cost per abstract and adds no billable request.

Usage: uv run scripts/dry_run_extraction_system_comparison_synthetic.py --out <dir>
"""

import argparse
import json
import pathlib

import extraction_system_comparison as mc
from build_registry import N_BOOT, RegistryClaim

UKB = (("UKB-PPP discovery",), ("FinnGen R10",))
DEC = (("deCODE 2023",), ("Biobank Japan",))
NULL = "reported_nonsignificant_or_null"
SAMPLE = ("R1", "R3")

# (a_in_b, b_in_a, shared, direction_class_equal, both_directional, same_direction,
#  opposite_direction, null_flag_equal, pQTL release identity, outcome release identity)
EXPECTED_COMPARISONS = {
    "sol_vs_luna_run1": ((6, 8), (6, 7), 6, (4, 6), 6, (5, 6), 1, (5, 6),
                         {"identical": 5, "undetermined": 1}, {"identical": 6}),
    "sol_vs_luna_run1_completed": ((7, 8), (7, 8), 7, (5, 7), 7, (6, 7), 1, (6, 7),
                          {"identical": 6, "undetermined": 1}, {"identical": 7}),
    "luna_run1_vs_luna_run2": ((6, 7), (6, 7), 6, (4, 6), 6, (5, 6), 1, (5, 6),
                               {"identical": 5, "undetermined": 1}, {"identical": 6}),
}
EXPECTED_SAMPLE = {
    "sol_vs_sol_repeat": ((4, 5), (4, 4), 4, (3, 4), 4, (4, 4), 0, (3, 4),
                          {"identical": 4}, {"identical": 4}),
    "sol_vs_luna_run1": ((5, 5), (5, 5), 5, (3, 5), 5, (4, 5), 1, (4, 5),
                         {"identical": 5}, {"identical": 5}),
    "luna_run1_vs_luna_run2": ((5, 5), (5, 5), 5, (3, 5), 5, (4, 5), 1, (4, 5),
                               {"identical": 5}, {"identical": 5}),
}
EXPECTED_RECORDS = {"sol": 8, "luna_run1": 7, "luna_run2": 7, "luna_run1_completed": 8}
# Sol: pairs 1 and 2 each join two families on disjoint sources (pair 2 in opposite
# directions); pair 3 joins two families on the identical releases. Luna run 1: pair 1 has one
# family; on pair 3 one family names no pQTL dataset, so the pair is unresolved and not
# resolvable. Run 1 completed by run 2 regains pair 1.
EXPECTED_TABLES = {
    "sol": {"h1_pairs": 2, "h1_pairs_agreeing": 1, "h1_independent_edges": 2,
            "h1_independent_edges_agreeing": 1, "h2_multi_family_pairs": 3,
            "h2_known_identical": 1, "h2_known_not_identical": 2, "h2_unresolved": 0,
            "h2b_known_overlapping": 1, "h2b_known_not_overlapping": 2, "h2b_unresolved": 0,
            "h2_resolvable_pairs": 3},
    "luna_run1": {"h1_pairs": 1, "h1_pairs_agreeing": 1, "h1_independent_edges": 1,
                  "h1_independent_edges_agreeing": 1, "h2_multi_family_pairs": 2,
                  "h2_known_identical": 0, "h2_known_not_identical": 1, "h2_unresolved": 1,
                  "h2b_known_overlapping": 0, "h2b_known_not_overlapping": 1,
                  "h2b_unresolved": 1, "h2_resolvable_pairs": 1},
    "luna_run1_completed": {"h1_pairs": 2, "h1_pairs_agreeing": 2, "h1_independent_edges": 2,
                   "h1_independent_edges_agreeing": 2, "h2_multi_family_pairs": 3,
                   "h2_known_identical": 0, "h2_known_not_identical": 2, "h2_unresolved": 1,
                   "h2b_known_overlapping": 0, "h2b_known_not_overlapping": 2,
                   "h2b_unresolved": 1, "h2_resolvable_pairs": 2},
}
# Threshold classifications are reported for Sol only. Sol: LB = UB = 1/3, both contradicted.
EXPECTED_SOL_VERDICTS = ("contradicted", "contradicted", True)
EXPECTED_CONTRADICTING = {"sol": 1, "luna_run1": 0, "luna_run1_completed": 0}
# Each Luna-derived estimate minus Sol's. Sol: H1 1/2 and 1/2; LB = UB = 1/3; resolvable 1;
# LB_b = UB_b = 1/3. Luna run 1: H1 1 and 1; LB 0, UB 1/2; resolvable 1/2; LB_b 0, UB_b 1/2.
# Run 1 completed: H1 1 and 1; LB 0, UB 1/3; resolvable 2/3; LB_b 0, UB_b 1/3.
EXPECTED_DIFFERENCES = {
    "luna_run1": {"h1_pair_concordance": 1 / 2, "h1_edge_concordance": 1 / 2,
                  "h2_lower": -1 / 3, "h2_upper": 1 / 2 - 1 / 3, "h2_resolvable_share": -1 / 2,
                  "h2b_lower": -1 / 3, "h2b_upper": 1 / 2 - 1 / 3},
    "luna_run1_completed": {"h1_pair_concordance": 1 / 2, "h1_edge_concordance": 1 / 2,
                            "h2_lower": -1 / 3, "h2_upper": 0.0,
                            "h2_resolvable_share": 2 / 3 - 1, "h2b_lower": -1 / 3,
                            "h2b_upper": 0.0},
}
# Sol: five exchanges of 1,000 input tokens (600 cached, 300 cache writes) and 200 output
# tokens, one per attempted abstract; one failed HTTP try is not priced. USD 0.001 + 0.0003 +
# 0.00375 + 0.01 = 0.01505, over 5 attempted abstracts.
# Luna run 1: R1 (1,000 input, 900 cache writes, 400 output); R2 twice, R3 and R4 once each
# (1,000 input, 900 cached, 300 output); R5 two failed HTTP exchanges and no response. Tokens
# 5,000 input, 3,600 cached, 900 cache writes, 1,600 output: USD 0.00005 + 0.000036 + 0.0001125
# + 0.0008 = 0.0009985, over 5 attempted abstracts (not the 4 with a response).
# Luna run 2: five exchanges of 1,000 input (900 cached) and 300 output: USD 0.00005 + 0.000045
# + 0.00075 = 0.000845, over 5.
EXPECTED_COST = {
    "sol": {"abstracts_attempted": 5, "billable_requests": 5,
            "abstracts_with_a_billable_response": 5, "abstracts_without_a_billable_response": 0,
            "extraction_failed_abstracts": 0, "failed_http_exchanges": 1,
            "records_outside_the_parsed_files_not_priced": 1, "uncached_input_tokens": 500,
            "usd": 0.01505, "usd_per_attempted_abstract": 0.00301},
    "luna_run1": {"abstracts_attempted": 5, "billable_requests": 5,
                  "abstracts_with_a_billable_response": 4,
                  "abstracts_without_a_billable_response": 1, "extraction_failed_abstracts": 1,
                  "failed_http_exchanges": 2, "records_outside_the_parsed_files_not_priced": 0,
                  "uncached_input_tokens": 500, "usd": 0.0009985,
                  "usd_per_attempted_abstract": 0.0001997},
    "luna_run2": {"abstracts_attempted": 5, "billable_requests": 5,
                  "abstracts_with_a_billable_response": 5,
                  "abstracts_without_a_billable_response": 0, "extraction_failed_abstracts": 0,
                  "failed_http_exchanges": 0, "records_outside_the_parsed_files_not_priced": 0,
                  "uncached_input_tokens": 500, "usd": 0.000845,
                  "usd_per_attempted_abstract": 0.000169},
}
EXPECTED_RATIOS = {"luna_run1": 0.00301 / 0.0001997, "luna_run2": 0.00301 / 0.000169,
                   "luna_two_runs": 0.00301 / (0.0001997 + 0.000169)}
ATTEMPTED = ("R1", "R2", "R3", "R4", "R5")


def claim(rec: str, i: int, family: str, n: int, direction: str,
          datasets: tuple[tuple[str, ...], tuple[str, ...]], context: str = "not_stated"
          ) -> RegistryClaim:
    """A verified registry claim of `family` on pair `n` (protein P<n>, outcome O<n>)."""
    return RegistryClaim(claim_record_id=f"{rec}:{i:03d}", family_id=family,
                         protein_id=f"P{n}", outcome_id=f"O{n}", direction=direction,
                         direction_verified=True, claim_scope="overall", context_key=context,
                         pqtl_datasets=datasets[0], outcome_datasets=datasets[1],
                         dataset_attribution="whole_study")


def sol_claims() -> list[RegistryClaim]:
    return [claim("R1", 0, "F1", 1, "raises", UKB), claim("R2", 0, "F2", 1, "raises", DEC),
            claim("R1", 1, "F1", 2, "raises", UKB), claim("R3", 0, "F3", 2, "lowers", DEC),
            claim("R1", 2, "F1", 3, "raises", UKB),
            claim("R1", 3, "F1", 3, NULL, UKB, "in women"),
            claim("R4", 0, "F4", 3, "raises", UKB), claim("R2", 1, "F2", 4, NULL, DEC),
            claim("R3", 1, "F3", 5, "raises", DEC)]


def luna_run1_claims() -> list[RegistryClaim]:
    return [claim("R1", 0, "F1", 1, "raises", UKB), claim("R1", 1, "F1", 2, "raises", UKB),
            claim("R3", 0, "F3", 2, "raises", DEC), claim("R1", 2, "F1", 3, "raises", UKB),
            claim("R4", 0, "F4", 3, "raises", (("not_stated",), ("FinnGen R10",))),
            claim("R3", 1, "F3", 5, "raises", DEC), claim("R4", 1, "F4", 6, "raises", UKB)]


def luna_run2_claims() -> list[RegistryClaim]:
    return [claim("R1", 0, "F1", 1, "raises", UKB), claim("R2", 0, "F2", 1, "raises", DEC),
            claim("R1", 1, "F1", 2, "raises", UKB), claim("R3", 0, "F3", 2, "lowers", DEC),
            claim("R1", 2, "F1", 3, "raises", UKB),
            claim("R1", 3, "F1", 3, NULL, UKB, "in women"),
            claim("R4", 0, "F4", 3, "raises", UKB), claim("R3", 1, "F3", 5, "raises", DEC)]


def sol_repeat_claims() -> list[RegistryClaim]:
    return [claim("R1", 0, "F1", 1, "raises", UKB), claim("R1", 1, "F1", 2, "raises", UKB),
            claim("R3", 0, "F3", 2, "lowers", DEC), claim("R1", 2, "F1", 3, "raises", UKB)]


def exchange(status: int, input_tokens: int, cached: int, cache_write: int, output: int) -> dict:
    usage = {"input_tokens": input_tokens,
             "input_tokens_details": {"cached_tokens": cached, "cache_write_tokens": cache_write},
             "output_tokens": output, "output_tokens_details": {"reasoning_tokens": 0}}
    return {"status": status, "response_text": json.dumps({"usage": usage})}


def write_exchanges(root: pathlib.Path) -> dict[str, pathlib.Path]:
    """The stored exchanges of the three extraction runs. The Sol folder also holds an exchange
    of a record of another run (DEV1), which no parsed file of this run names."""
    sol, run1, run2 = root / "raw_sol", root / "raw_luna" / "run1", root / "raw_luna" / "run2"
    for folder in (sol, run1, run2):
        folder.mkdir(parents=True)
    failed = json.dumps({"status": 500, "response_text": "upstream error"})
    for rec in ATTEMPTED:
        (sol / f"{rec}_attempt1.json").write_text(json.dumps(exchange(200, 1000, 600, 300, 200)))
        (run2 / f"{rec}_attempt1.json").write_text(json.dumps(exchange(200, 1000, 900, 0, 300)))
    (sol / "R2_attempt1.http1.json").write_text(failed)
    (sol / "DEV1_attempt1.json").write_text(json.dumps(exchange(200, 9000, 0, 0, 9000)))
    (run1 / "R1_attempt1.json").write_text(json.dumps(exchange(200, 1000, 0, 900, 400)))
    for name in ("R2_attempt1.json", "R2_attempt2.json", "R3_attempt1.json", "R4_attempt1.json"):
        (run1 / name).write_text(json.dumps(exchange(200, 1000, 900, 0, 300)))
    for name in ("R5_attempt1.http1.json", "R5_attempt2.http1.json"):
        (run1 / name).write_text(failed)
    return {"sol": sol, "luna_run1": run1, "luna_run2": run2}


def write_parsed(root: pathlib.Path) -> dict[str, list[pathlib.Path]]:
    """The parsed extraction files of the three runs: one row per attempted abstract, in two
    files per run. Luna run 1 records R5 `extraction_failed`."""
    out = {}
    for role in ("sol", "luna_run1", "luna_run2"):
        rows = [{"pmid": rec, "status": "extraction_failed"
                 if (role, rec) == ("luna_run1", "R5") else "ok"} for rec in ATTEMPTED]
        files = [root / f"parsed_{role}_search.jsonl", root / f"parsed_{role}_chase1.jsonl"]
        files[0].write_text("".join(json.dumps(r) + "\n" for r in rows[:3]))
        files[1].write_text("".join(json.dumps(r) + "\n" for r in rows[3:]))
        out[role] = files
    return out


def write_inputs(root: pathlib.Path) -> dict[str, pathlib.Path]:
    files = {}
    for name, claims in (("sol", sol_claims()), ("luna_run1", luna_run1_claims()),
                         ("luna_run2", luna_run2_claims()), ("sol_repeat", sol_repeat_claims())):
        files[name] = root / f"{name}_registry_claims.jsonl"
        files[name].write_text("".join(c.model_dump_json() + "\n" for c in claims))
    files["sample"] = root / "repeat_sample.json"
    files["sample"].write_text(json.dumps({"seed": 20261001, "sampled_ids": list(SAMPLE)}))
    return files


def expect(name: str, got, want) -> None:
    if got != want:
        raise AssertionError(f"dry run: {name} is {got!r}, expected {want!r}")


def close(name: str, got: float, want: float) -> None:
    if abs(got - want) > 1e-12 * max(1.0, abs(want)):
        raise AssertionError(f"dry run: {name} is {got!r}, expected {want!r}")


def expect_comparison(name: str, block: dict, want: tuple) -> None:
    a_in_b, b_in_a, shared, classes, both, same, opposite, null, pqtl, outcome = want
    among = block["among_shared"]
    for label, got, pair in (("a_in_b", block["a_in_b"], a_in_b),
                             ("b_in_a", block["b_in_a"], b_in_a),
                             ("direction_class_equal", among["direction_class_equal"], classes),
                             ("same_direction", among["same_direction"], same),
                             ("null_flag_equal", among["null_flag_equal"], null)):
        expect(f"{name} {label}", (got["count"], got["of"]), pair)
        close(f"{name} {label} share", got["share"], pair[0] / pair[1])
    expect(f"{name} shared", block["shared_records"], shared)
    expect(f"{name} both directional", among["both_directional"], both)
    expect(f"{name} opposite direction", among["opposite_direction"], opposite)
    expect(f"{name} pQTL release identity", among["release_identity"]["pqtl"], pqtl)
    expect(f"{name} outcome release identity", among["release_identity"]["outcome"], outcome)


def run(out: pathlib.Path, n_boot: int = N_BOOT) -> dict:
    """Write the synthetic inputs, run the two commands of extraction_system_comparison.py and
    return the comparison as read back from the file it wrote."""
    out.mkdir(parents=True, exist_ok=True)
    files, raw, parsed = write_inputs(out), write_exchanges(out), write_parsed(out)
    usage = {}
    for role in ("sol", "luna_run1", "luna_run2"):
        usage[role] = out / f"usage_{role}.json"
        mc.main_usage(argparse.Namespace(role=role, raw=[raw[role]], parsed=parsed[role],
                                         out=usage[role]))
    # The registered primary table, as the stage-5 sensitivity run stores it.
    primary = out / "sensitivity_tables.json"
    primary.write_text(json.dumps({"primary": mc.h1_h2(
        sol_claims(), mc.load_rows(), n_boot, mc.SEED)}))
    mc.main_compare(argparse.Namespace(
        sol=files["sol"], luna_run1=files["luna_run1"], luna_run2=files["luna_run2"],
        sol_repeat=files["sol_repeat"], repeat_sample=[files["sample"]], sol_tables=primary,
        usage_sol=usage["sol"], usage_luna_run1=usage["luna_run1"],
        usage_luna_run2=usage["luna_run2"], n_boot=n_boot, out=out))
    return json.loads((out / "extraction_system_comparison.json").read_text())


def check(result: dict) -> None:
    expect("family–pair records", result["family_pair_records"], EXPECTED_RECORDS)
    for name, want in EXPECTED_COMPARISONS.items():
        expect_comparison(name, result["comparisons"][name], want)
    expect("sampled abstracts", result["repeat_sample"]["sampled_abstracts"], len(SAMPLE))
    for name, want in EXPECTED_SAMPLE.items():
        expect_comparison(f"repeat sample {name}", result["repeat_sample"][name], want)
    for source, want in EXPECTED_TABLES.items():
        table = result["h1_h2"][source]
        for key, value in want.items():
            expect(f"{source} {key}", table["estimates"][key], value)
        expect(f"{source} contradicting pairs", table["denominators"]["contradicting_pairs"],
               EXPECTED_CONTRADICTING[source])
    sol = result["h1_h2"]["sol"]
    expect("Sol verdicts", (sol["h2_verdict"], sol["h2b_verdict"],
                            sol["h2_supported_attainable"]), EXPECTED_SOL_VERDICTS)
    for source, want in EXPECTED_DIFFERENCES.items():
        table = result["h1_h2"][source]
        expect(f"{source} threshold classifications reported",
               sorted(k for k in mc.VERDICT_KEYS if k in table), [])
        expect(f"{source} differences reported", sorted(table["difference_from_sol"]),
               sorted(want))
        for key, value in want.items():
            close(f"{source} {key} minus Sol", table["difference_from_sol"][key], value)
    expect("heading", result["heading"], "Extraction-system comparison")
    expect("display label", result["display"]["luna_run1_completed"],
           "Luna run 1, completed by run 2 for missing family–pairs")
    expect("Sol table checked against the primary",
           result["sol_table_checked_against_registered_primary"], True)
    expect("usage roles", sorted(result["cost"]["usage"]), sorted(EXPECTED_COST))
    for role, want in EXPECTED_COST.items():
        got = result["cost"]["usage"][role]
        for key, value in want.items():
            if isinstance(value, float):
                close(f"{role} {key}", got[key], value)
            else:
                expect(f"{role} {key}", got[key], value)
    for name, want in EXPECTED_RATIOS.items():
        close(f"cost ratio {name}",
              result["cost"]["sol_cost_per_attempted_abstract_over_luna"][name], want)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    result = run(a.out)
    check(result)
    print(json.dumps({"out": str(a.out), "synthetic": True,
                      "family_pair_records": result["family_pair_records"],
                      "checked": "every quantity equals its hand-worked value"}, indent=1))


if __name__ == "__main__":
    main()
