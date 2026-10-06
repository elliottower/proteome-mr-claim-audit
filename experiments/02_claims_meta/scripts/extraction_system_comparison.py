# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5", "rapidfuzz==3.14.6"]
# ///
"""Extraction-system comparison (AMENDMENT_01_extraction_system_comparison.md): agreement
between the registered extraction (GPT-6.1 Sol with the frozen prompt) and the tuned Luna
extraction system (`gpt-6-luna` with prompts/luna_extraction_prompt.md) on the same abstracts.
The two systems differ in model and in prompt, so no difference found here is attributed to the
model alone. No model is called. Nothing here changes or replaces a registered result; the
estimates of H1, H2 and H2b recomputed from Luna's records are comparison columns.

Inputs are registry claim files (`registry_claims.jsonl` of scripts/assemble_registry.py), one
per source: the coded primary registry of GPT-6.1 Sol, the registry assembled from Luna run 1,
the one from Luna run 2 and, for the repeat sample, the one assembled from the second GPT-6.1
Sol run on the 10% stability sample. Every file went through the same span check, claim check,
canonical identifiers and family assignment.

Unit. A family–pair record is study family × UniProt accession × canonical outcome identifier,
as `build_registry.build` forms it from the claim records: its direction is the family–pair
direction, its null flag is whether the family has a verified
`reported_nonsignificant_or_null` record on the pair, and its datasets are the mapped names of
its records, per side.

Comparison of two sources A and B:

    a_in_b                  share of A's family–pair records that B also holds
    b_in_a                  share of B's that A also holds
    direction_class_equal   among shared records, the two family–pair directions are the same
                            class (raises, lowers, either with_nonsignificant form, mixed,
                            nonsignificant_only, unresolved)
    same_direction          among shared records directional in both sources, the two
                            directions agree (a with_nonsignificant form read as its
                            direction); the others are counted `opposite_direction`
    null_flag_equal         among shared records, the two null flags are equal
    release_identity        among shared records, per side, `dataset_relations.release_identity`
                            of the two sources' names: identical, not_identical, undetermined

Each share is count / denominator with a Wilson 95% interval (naive, descriptive) and the
registered pair bootstrap: canonical pairs resampled with replacement, the share recomputed as
the ratio of the summed counts (10,000 replicates, seed 20261001, one generator stream per
share, inverted-CDF 2.5th and 97.5th percentiles; `registry_secondaries.boot_ratio`). None
carries a P value or a verdict; a share on fewer than 20 records is labeled imprecise.

Run-1-first completion (`luna_run1_completed`, "Luna run 1, completed by run 2 for missing
family–pairs"): run 1 as it is, completed by the claim records of run 2 on the family–pair
records run 1 lacks. A family–pair record present in both runs keeps run 1's records: a run-2
context, null result or dataset name never supplements a family–pair already present in run 1.
It is not the pooled records of the two runs.

Repeat sample. With `--sol-repeat` and `--repeat-sample`, three comparisons are made on the
claim records of the sampled abstracts only: Sol run 1 against the second Sol run, Sol run 1
against Luna run 1, and Luna run 1 against Luna run 2.

H1, H2 and H2b. `build_registry.tables` is applied to Sol's claims, to Luna run 1's and to
`luna_run1_completed`'s. With `--sol-tables` (the stage-5 `sensitivity_tables.json`) the script
raises unless Sol's estimates and verdicts here equal the registered `primary` table. Threshold
classifications remain exclusively those of the registered Sol analysis: for the two
Luna-derived registries the report holds the estimates, bounds, denominators and intervals and
each estimate's difference from Sol's, and none of VERDICT_KEYS.

Cost. `usage` prices one extraction run. The denominator is every abstract the run attempted:
the records of its parsed extraction files (`--parsed`), whether or not any request succeeded.
The numerator sums the usage blocks of the stored exchanges with HTTP 200 of those records, at
the list prices in PRICES (USD per million tokens; PRICE_SOURCE says where they come from);
`input_tokens` is read as including the cached and the cache-write tokens. Abstracts with no
billable response and `extraction_failed` abstracts are counted separately, and exchanges of
records outside the parsed files (another run stored in the same folder) are counted and not
priced. `compare` requires the usage of all three runs (Sol, Luna run 1, Luna run 2) over the
same attempted abstracts and refuses anything else.

Usage:
    uv run scripts/extraction_system_comparison.py usage --role sol \
        --raw outputs/raw/sol/extraction/<rev> --parsed <sol_extraction_*.jsonl ...> \
        --out <dir>/usage_sol.json
    uv run scripts/extraction_system_comparison.py compare --sol <registry_claims.jsonl> \
        --luna-run1 <...> --luna-run2 <...> [--sol-repeat <...> --repeat-sample <...json> ...]
        [--sol-tables <sensitivity_tables.json>] --usage-sol <...> --usage-luna-run1 <...>
        --usage-luna-run2 <...> --out <dir>
"""

import argparse
import collections
import datetime
import hashlib
import json
import pathlib

from pydantic import BaseModel, ConfigDict

from build_registry import (DIRECTIONAL, N_BOOT, NONSIG, SEED, RegistryClaim, build, effective,
                            tables, wilson)
from dataset_relations import NameMapping, Row, load_rows, release_identity
from registry_secondaries import boot_ratio

AMENDMENT = "AMENDMENT_01_extraction_system_comparison.md"
IMPRECISE_BELOW = 20
SIDES = ("pqtl", "outcome")
PRICES = {
    "gpt-6.1-sol": {"input": 2.00, "cached_input": 0.10, "cache_write": 2.50, "output": 10.00},
    "gpt-6-luna": {"input": 0.10, "cached_input": 0.01, "cache_write": 0.125, "output": 0.50},
}
PRICE_SOURCE = {"source": "OpenAI's pricing table, short-context column, as given by the author",
                "date_given": "2026-10-05", "unit": "USD per million tokens"}
ROLES = {"sol": "gpt-6.1-sol", "luna_run1": "gpt-6-luna", "luna_run2": "gpt-6-luna"}
LUNA_SOURCES = ("luna_run1", "luna_run1_completed")
DISPLAY = {"luna_run1_completed": "Luna run 1, completed by run 2 for missing family–pairs"}
VERDICT_KEYS = ("verdict_rule", "h2_verdict", "h2b_verdict", "two_verdict_reading",
                "h2_supported_attainable")
DIFFERENCE_KEYS = ("h1_pair_concordance", "h1_edge_concordance", "h2_lower", "h2_upper",
                   "h2_resolvable_share", "h2b_lower", "h2b_upper")
BASE_STREAMS = {name: 100 + 10 * i for i, name in enumerate(
    ("sol_vs_luna_run1", "sol_vs_luna_run1_completed", "luna_run1_vs_luna_run2",
     "sample_sol_vs_sol_repeat", "sample_sol_vs_luna_run1", "sample_luna_run1_vs_luna_run2"))}
PRIMARY_KEYS = ("claim_records", "estimates", "h2_verdict", "h2b_verdict",
                "two_verdict_reading", "h2_supported_attainable")
Key = tuple[str, str, str]


class ComparisonError(Exception):
    """The inputs are inconsistent: a claim outside the repeat sample, a Sol table that differs
    from the registered primary, a usage block that cannot be priced, an incomplete or
    mismatched set of usage files, an existing output."""


class FamilyPairRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    family_id: str
    pair: tuple[str, str]
    direction: str
    null_flag: bool
    pqtl: tuple[NameMapping, ...]
    outcome: tuple[NameMapping, ...]


def claim_key(c: RegistryClaim) -> Key:
    return (c.family_id, c.protein_id, c.outcome_id)


def family_pair_records(claims: list[RegistryClaim], rows: list[Row]
                        ) -> dict[Key, FamilyPairRecord]:
    """The family–pair records of a claim file, as the registry builder forms them."""
    null = {claim_key(c) for c in claims if effective(c) == NONSIG}
    out: dict[Key, FamilyPairRecord] = {}
    for pair, fams in build(claims, rows).items():
        for fam, fp in fams.items():
            key = (fam, *pair)
            out[key] = FamilyPairRecord(family_id=fam, pair=pair, direction=fp.direction,
                                        null_flag=key in null, pqtl=tuple(fp.pqtl),
                                        outcome=tuple(fp.outcome))
    return out


def measure(units: list[tuple[tuple[str, str], bool]], stream: int, n_boot: int, seed: int
            ) -> dict:
    """count / denominator over records, each belonging to one canonical pair, with a Wilson
    interval and the pair bootstrap over the canonical pairs."""
    num: collections.Counter = collections.Counter()
    den: collections.Counter = collections.Counter()
    for pair, hit in units:
        den[pair] += 1
        num[pair] += bool(hit)
    pairs = sorted(den)
    k, n = sum(num.values()), sum(den.values())
    return {"count": k, "of": n, "share": k / n if n else None, "wilson": wilson(k, n),
            "pair_bootstrap": boot_ratio([float(num[p]) for p in pairs],
                                         [float(den[p]) for p in pairs], n_boot, seed, stream),
            "canonical_pairs": len(pairs), "stream": stream,
            "imprecise_under_20": n < IMPRECISE_BELOW}


def compare(a: dict[Key, FamilyPairRecord], b: dict[Key, FamilyPairRecord], base_stream: int,
            n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Agreement of source B with source A over family–pair records."""
    shared = sorted(set(a) & set(b))
    both = [k for k in shared
            if a[k].direction in DIRECTIONAL and b[k].direction in DIRECTIONAL]
    same = [DIRECTIONAL[a[k].direction] == DIRECTIONAL[b[k].direction] for k in both]
    return {
        "a_records": len(a), "b_records": len(b), "shared_records": len(shared),
        "a_in_b": measure([(a[k].pair, k in b) for k in sorted(a)], base_stream, n_boot, seed),
        "b_in_a": measure([(b[k].pair, k in a) for k in sorted(b)], base_stream + 1, n_boot,
                          seed),
        "among_shared": {
            "direction_class_equal": measure(
                [(a[k].pair, a[k].direction == b[k].direction) for k in shared],
                base_stream + 2, n_boot, seed),
            "direction_classes_a_then_b": dict(sorted(collections.Counter(
                f"{a[k].direction}|{b[k].direction}" for k in shared).items())),
            "both_directional": len(both),
            "same_direction": measure([(a[k].pair, s) for k, s in zip(both, same)],
                                      base_stream + 3, n_boot, seed),
            "opposite_direction": same.count(False),
            "null_flag_equal": measure(
                [(a[k].pair, a[k].null_flag == b[k].null_flag) for k in shared],
                base_stream + 4, n_boot, seed),
            "release_identity": {side: dict(sorted(collections.Counter(
                release_identity(list(getattr(a[k], side)), list(getattr(b[k], side)))
                for k in shared).items())) for side in SIDES},
        },
    }


def completed_by(first: list[RegistryClaim], second: list[RegistryClaim]) -> list[RegistryClaim]:
    """Run-1-first completion: every claim record of `first`, and the claim records of `second`
    on the family–pair records `first` lacks; nothing of `second` supplements a family–pair
    `first` holds. Record ids are prefixed with their run."""
    have = {claim_key(c) for c in first}
    return ([c.model_copy(update={"claim_record_id": f"run1/{c.claim_record_id}"})
             for c in first]
            + [c.model_copy(update={"claim_record_id": f"run2/{c.claim_record_id}"})
               for c in second if claim_key(c) not in have])


def record_id(c: RegistryClaim) -> str:
    """The screening record a claim record was extracted from (`<record id>:<index>`)."""
    return c.claim_record_id.rsplit(":", 1)[0]


def restricted(claims: list[RegistryClaim], record_ids: frozenset[str]) -> list[RegistryClaim]:
    return [c for c in claims if record_id(c) in record_ids]


def h1_h2(claims: list[RegistryClaim], rows: list[Row], n_boot: int, seed: int) -> dict:
    return {"claim_records": len(claims), **tables(build(claims, rows), n_boot, seed)}


def descriptive(table: dict, sol: dict) -> dict:
    """A Luna-derived table as reported: estimates, bounds, denominators and intervals, each
    estimate of DIFFERENCE_KEYS also as its difference from Sol's, and no threshold
    classification (none of VERDICT_KEYS)."""
    diff = {}
    for key in DIFFERENCE_KEYS:
        ours, theirs = table["estimates"][key], sol["estimates"][key]
        diff[key] = None if ours is None or theirs is None else ours - theirs
    return {**{k: v for k, v in table.items() if k not in VERDICT_KEYS},
            "difference_from_sol": diff}


def check_primary(ours: dict, primary: dict) -> None:
    """Raise unless Sol's table here equals the registered primary table, key by key."""
    mine = json.loads(json.dumps(ours))
    differing = [k for k in PRIMARY_KEYS if mine[k] != primary[k]]
    if differing:
        raise ComparisonError(f"Sol's table differs from the registered primary in "
                              f"{differing}; the Sol claims file is not the primary registry")


def comparison(sol: list[RegistryClaim], run1: list[RegistryClaim], run2: list[RegistryClaim],
               rows: list[Row], sol_repeat: list[RegistryClaim] | None = None,
               sample_ids: frozenset[str] | None = None, n_boot: int = N_BOOT,
               seed: int = SEED) -> dict:
    completed = completed_by(run1, run2)
    fp = {name: family_pair_records(claims, rows) for name, claims in (
        ("sol", sol), ("luna_run1", run1), ("luna_run2", run2),
        ("luna_run1_completed", completed))}
    sol_table = h1_h2(sol, rows, n_boot, seed)
    out: dict = {
        "heading": "Extraction-system comparison",
        "systems": {"sol": "GPT-6.1 Sol with the frozen extraction prompt (registered)",
                    "luna": "gpt-6-luna with prompts/luna_extraction_prompt.md (tuned)"},
        "attribution": "two model–prompt configurations; no difference is attributed to the "
                       "model alone",
        "unit": "family–pair record: study family × UniProt accession × canonical outcome "
                "identifier",
        "display": DISPLAY,
        "run1_completed_rule": "run 1, completed by run 2's claim records on the family–pair "
                               "records run 1 lacks; a run-2 context, null result or dataset "
                               "name never supplements a family–pair present in run 1",
        "replicates": n_boot, "seed": seed,
        "family_pair_records": {name: len(records) for name, records in fp.items()},
        "comparisons": {
            "sol_vs_luna_run1": compare(fp["sol"], fp["luna_run1"],
                                        BASE_STREAMS["sol_vs_luna_run1"], n_boot, seed),
            "sol_vs_luna_run1_completed": compare(fp["sol"], fp["luna_run1_completed"],
                                         BASE_STREAMS["sol_vs_luna_run1_completed"], n_boot, seed),
            "luna_run1_vs_luna_run2": compare(fp["luna_run1"], fp["luna_run2"],
                                              BASE_STREAMS["luna_run1_vs_luna_run2"], n_boot,
                                              seed),
        },
        "repeat_sample": None,
        "threshold_classifications": "those of the registered Sol analysis only; for "
                                     "Luna-derived registries only descriptive estimates, "
                                     "bounds and denominators are reported",
        "h1_h2": {"sol": sol_table,
                  "luna_run1": descriptive(h1_h2(run1, rows, n_boot, seed), sol_table),
                  "luna_run1_completed": descriptive(h1_h2(completed, rows, n_boot, seed),
                                                     sol_table)},
    }
    if (sol_repeat is None) != (sample_ids is None):
        raise ComparisonError("the second Sol run and the repeat sample are given together")
    if sol_repeat is not None and sample_ids is not None:
        outside = sorted({record_id(c) for c in sol_repeat} - sample_ids)
        if outside:
            raise ComparisonError(f"the second Sol run holds records outside the sample: "
                                  f"{outside[:5]}")
        part = {name: family_pair_records(restricted(claims, sample_ids), rows)
                for name, claims in (("sol", sol), ("luna_run1", run1), ("luna_run2", run2))}
        part["sol_repeat"] = family_pair_records(sol_repeat, rows)
        out["repeat_sample"] = {
            "sampled_abstracts": len(sample_ids),
            "family_pair_records": {name: len(records) for name, records in part.items()},
            "sol_vs_sol_repeat": compare(part["sol"], part["sol_repeat"],
                                         BASE_STREAMS["sample_sol_vs_sol_repeat"], n_boot, seed),
            "sol_vs_luna_run1": compare(part["sol"], part["luna_run1"],
                                        BASE_STREAMS["sample_sol_vs_luna_run1"], n_boot, seed),
            "luna_run1_vs_luna_run2": compare(part["luna_run1"], part["luna_run2"],
                                              BASE_STREAMS["sample_luna_run1_vs_luna_run2"],
                                              n_boot, seed),
        }
    return out


def attempted_abstracts(parsed: list[pathlib.Path]) -> tuple[list[str], list[str]]:
    """The record ids an extraction run attempted and those it recorded `extraction_failed`,
    from its parsed extraction files (one row per abstract submitted)."""
    rows = [json.loads(line) for path in parsed for line in path.read_text().splitlines()
            if line.strip()]
    ids = [str(r["pmid"]) for r in rows]
    if not ids:
        raise ComparisonError("the parsed extraction files hold no record")
    if len(set(ids)) != len(ids):
        raise ComparisonError("a record occurs twice in the parsed extraction files")
    return sorted(ids), sorted(str(r["pmid"]) for r in rows if r["status"] == "extraction_failed")


def usage_totals(folders: list[pathlib.Path], attempted: list[str], failed: list[str]) -> dict:
    """Tokens of the stored exchanges with HTTP 200 of the attempted abstracts (the record id is
    the file name up to `_attempt`). The attempted abstracts are the denominator of the cost per
    abstract, whether or not a request succeeded."""
    want = set(attempted)
    tokens: collections.Counter = collections.Counter()
    billed: set[str] = set()
    other: set[str] = set()
    requests = failed_http = 0
    for path in sorted(p for folder in folders for p in folder.rglob("*_attempt*.json")):
        record = path.name.split("_attempt")[0]
        if record not in want:
            other.add(record)
            continue
        exchange = json.loads(path.read_text())
        if exchange.get("status") != 200:
            failed_http += 1
            continue
        u = json.loads(exchange["response_text"]).get("usage") or {}
        details = u.get("input_tokens_details") or {}
        requests += 1
        billed.add(record)
        tokens["input_tokens"] += u.get("input_tokens", 0)
        tokens["cached_input_tokens"] += details.get("cached_tokens", 0)
        tokens["cache_write_tokens"] += details.get("cache_write_tokens", 0)
        tokens["output_tokens"] += u.get("output_tokens", 0)
        tokens["reasoning_tokens"] += (u.get("output_tokens_details") or {}).get(
            "reasoning_tokens", 0)
    return {"abstracts_attempted": len(want),
            "attempted_sha256": hashlib.sha256("\n".join(sorted(want)).encode()).hexdigest(),
            "billable_requests": requests,
            "abstracts_with_a_billable_response": len(billed),
            "abstracts_without_a_billable_response": len(want - billed),
            "extraction_failed_abstracts": len(failed),
            "failed_http_exchanges": failed_http,
            "records_outside_the_parsed_files_not_priced": len(other),
            "tokens": {k: tokens[k] for k in ("input_tokens", "cached_input_tokens",
                                              "cache_write_tokens", "output_tokens",
                                              "reasoning_tokens")}}


def cost(totals: dict, role: str) -> dict:
    """USD at the list prices; `input_tokens` includes the cached and cache-write tokens. The
    cost per abstract divides by every attempted abstract."""
    if role not in ROLES:
        raise ComparisonError(f"no extraction run is called {role}")
    model = ROLES[role]
    price, t = PRICES[model], totals["tokens"]
    uncached = t["input_tokens"] - t["cached_input_tokens"] - t["cache_write_tokens"]
    if uncached < 0:
        raise ComparisonError("cached and cache-write tokens exceed the input tokens")
    parts = {"input": uncached * price["input"] / 1e6,
             "cached_input": t["cached_input_tokens"] * price["cached_input"] / 1e6,
             "cache_write": t["cache_write_tokens"] * price["cache_write"] / 1e6,
             "output": t["output_tokens"] * price["output"] / 1e6}
    usd = sum(parts.values())
    return {"role": role, "model": model, "prices_usd_per_million": price,
            "price_source": PRICE_SOURCE, **totals, "uncached_input_tokens": uncached,
            "usd_parts": parts, "usd": usd,
            "usd_per_attempted_abstract": usd / totals["abstracts_attempted"]}


def cost_table(usages: dict[str, dict]) -> dict:
    """The usage of the three extraction runs, and Sol's cost per attempted abstract over each
    Luna run's and over the two Luna runs together. Refuses unless the three runs are all
    present, each of its role and model, over the same attempted abstracts."""
    if set(usages) != set(ROLES):
        raise ComparisonError(f"the usage of {sorted(ROLES)} is required; got {sorted(usages)}")
    for role, u in usages.items():
        if u.get("role") != role or u.get("model") != ROLES[role]:
            raise ComparisonError(f"the usage file given for {role} is of {u.get('role')}, "
                                  f"{u.get('model')}")
    if len({u["attempted_sha256"] for u in usages.values()}) != 1:
        raise ComparisonError("the three extraction runs did not attempt the same abstracts: "
                              + ", ".join(f"{r} {u['abstracts_attempted']}"
                                          for r, u in sorted(usages.items())))
    sol = usages["sol"]["usd_per_attempted_abstract"]
    run1 = usages["luna_run1"]["usd_per_attempted_abstract"]
    run2 = usages["luna_run2"]["usd_per_attempted_abstract"]
    ratio = {"luna_run1": sol / run1 if run1 else None,
             "luna_run2": sol / run2 if run2 else None,
             "luna_two_runs": sol / (run1 + run2) if run1 + run2 else None}
    return {"usage": usages, "sol_cost_per_attempted_abstract_over_luna": ratio}


def read_claims(path: pathlib.Path) -> list[RegistryClaim]:
    return [RegistryClaim.model_validate_json(line) for line in path.read_text().splitlines()
            if line.strip()]


def write_new(path: pathlib.Path, result: dict) -> None:
    if path.exists():
        raise ComparisonError(f"{path} exists; archive it before rerunning")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=1, ensure_ascii=False))


def main_usage(a: argparse.Namespace) -> None:
    attempted, failed = attempted_abstracts(a.parsed)
    result = {"folders": [str(f) for f in a.raw], "parsed": [str(f) for f in a.parsed],
              "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
              **cost(usage_totals(a.raw, attempted, failed), a.role)}
    write_new(a.out, result)
    print(json.dumps(result, indent=1))


def main_compare(a: argparse.Namespace) -> None:
    files = {"sol": a.sol, "luna_run1": a.luna_run1, "luna_run2": a.luna_run2}
    if a.sol_repeat is not None:
        files["sol_repeat"] = a.sol_repeat
    claims = {name: read_claims(path) for name, path in files.items()}
    sample = None
    if a.repeat_sample:
        sample = frozenset(i for p in a.repeat_sample
                           for i in json.loads(p.read_text())["sampled_ids"])
    costs = cost_table({"sol": json.loads(a.usage_sol.read_text()),
                        "luna_run1": json.loads(a.usage_luna_run1.read_text()),
                        "luna_run2": json.loads(a.usage_luna_run2.read_text())})
    result = comparison(claims["sol"], claims["luna_run1"], claims["luna_run2"], load_rows(),
                        claims.get("sol_repeat"), sample, a.n_boot, SEED)
    if a.sol_tables is not None:
        check_primary(result["h1_h2"]["sol"], json.loads(a.sol_tables.read_text())["primary"])
    result = {
        "amendment": AMENDMENT,
        "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "inputs": {name: {"path": str(path),
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                          "claim_records": len(claims[name])} for name, path in files.items()},
        "sol_table_checked_against_registered_primary": a.sol_tables is not None,
        **result,
        "cost": costs,
    }
    write_new(a.out / "extraction_system_comparison.json", result)
    summary = {name: {k: block[k]["share"] for k in ("a_in_b", "b_in_a")}
               for name, block in result["comparisons"].items()}
    print(json.dumps({"out": str(a.out), "family_pair_records": result["family_pair_records"],
                      "shares": summary}, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    u = sub.add_parser("usage", help="tokens and list-price cost of one extraction run")
    u.add_argument("--role", choices=sorted(ROLES), required=True)
    u.add_argument("--raw", type=pathlib.Path, nargs="+", required=True)
    u.add_argument("--parsed", type=pathlib.Path, nargs="+", required=True,
                   help="the run's parsed extraction files: the abstracts it attempted")
    u.add_argument("--out", type=pathlib.Path, required=True)
    u.set_defaults(run=main_usage)
    c = sub.add_parser("compare", help="the comparison tables")
    c.add_argument("--sol", type=pathlib.Path, required=True)
    c.add_argument("--luna-run1", type=pathlib.Path, required=True)
    c.add_argument("--luna-run2", type=pathlib.Path, required=True)
    c.add_argument("--sol-repeat", type=pathlib.Path)
    c.add_argument("--repeat-sample", type=pathlib.Path, nargs="+", default=[])
    c.add_argument("--sol-tables", type=pathlib.Path,
                   help="the stage-5 sensitivity_tables.json; Sol's table must equal `primary`")
    c.add_argument("--usage-sol", type=pathlib.Path, required=True)
    c.add_argument("--usage-luna-run1", type=pathlib.Path, required=True)
    c.add_argument("--usage-luna-run2", type=pathlib.Path, required=True)
    c.add_argument("--n-boot", type=int, default=N_BOOT)
    c.add_argument("--out", type=pathlib.Path, required=True)
    c.set_defaults(run=main_compare)
    a = ap.parse_args()
    a.run(a)


if __name__ == "__main__":
    main()
