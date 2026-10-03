# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Draw the repeat-run stability sample: a random 10% of eligible abstracts, seed 20261001.

The eligible records are those whose decision (apply_eligibility.py) is `eligible`,
`eligible_count_not_stated` or `uncertain`. Their record ids are sorted, and
`random.Random(20261001).sample` draws ceil(0.10 × n) of them. The drawn abstracts are written
in the input format of run_extraction.py; the second run uses the same prompt with
`--raw-root outputs/raw/sol_repeat`, so no first-run exchange is reused. The first run stays
the registered extraction.

Output, next to the decisions file: <decisions stem>.repeat_sample.jsonl (records) and
<decisions stem>.repeat_sample.json (seed, fraction, counts, ids, input checksums).

Usage: uv run scripts/sample_repeat_run.py --decisions <...decisions.jsonl> --abstracts <screening_set.jsonl>
"""

import argparse
import hashlib
import json
import math
import pathlib
import random

SEED = 20261001
FRACTION = 0.10
ELIGIBLE = ("eligible", "eligible_count_not_stated", "uncertain")


class SampleError(Exception):
    """An eligible record has no abstract in the input, or the output exists."""


def draw(eligible_ids: list[str], seed: int = SEED, fraction: float = FRACTION) -> list[str]:
    """The sampled ids, in sorted order."""
    ids = sorted(set(eligible_ids))
    if len(ids) != len(eligible_ids):
        raise SampleError("an eligible record id occurs twice")
    k = math.ceil(fraction * len(ids))
    return sorted(random.Random(seed).sample(ids, k))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--decisions", type=pathlib.Path, required=True)
    ap.add_argument("--abstracts", type=pathlib.Path, required=True)
    a = ap.parse_args()
    stem = a.decisions.name.removesuffix(".jsonl")
    out = a.decisions.with_name(stem + ".repeat_sample.jsonl")
    if out.exists():
        raise SampleError(f"{out} exists; the sample is drawn once")
    decisions = [json.loads(l) for l in a.decisions.read_text().splitlines() if l.strip()]
    eligible = [d["pmid"] for d in decisions if d["decision"] in ELIGIBLE]
    records = {r["pmid"]: r for r in (json.loads(l) for l in
                                      a.abstracts.read_text().splitlines() if l.strip())}
    missing = sorted(set(eligible) - set(records))
    if missing:
        raise SampleError(f"eligible records without an abstract record: {missing[:5]}")
    sample = draw(eligible)
    meta = {"seed": SEED, "fraction": FRACTION, "rounding": "ceil",
            "n_eligible": len(eligible), "n_sampled": len(sample), "sampled_ids": sample,
            "decisions": str(a.decisions),
            "decisions_sha256": hashlib.sha256(a.decisions.read_bytes()).hexdigest(),
            "abstracts": str(a.abstracts),
            "abstracts_sha256": hashlib.sha256(a.abstracts.read_bytes()).hexdigest()}
    out.with_suffix(".json").write_text(json.dumps(meta, indent=1))
    out.write_text("".join(json.dumps(records[i], ensure_ascii=False) + "\n" for i in sample))
    print(json.dumps({k: v for k, v in meta.items() if k != "sampled_ids"}, indent=1))


if __name__ == "__main__":
    main()
