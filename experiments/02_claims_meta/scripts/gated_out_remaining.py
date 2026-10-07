# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""List the gate-marked records of a citation-chasing round that no audit batch sampled.

`keyword_prefilter.py --gate` writes the marked records to `gated_out.jsonl`, and
`gate_audit.py` draws its batches from them (`gate_sample_batch_<b>.jsonl`). When every marked
record is to be screened (PREREG.md log, 2026-10-06), the records the audit already judged are
not asked again: this script writes the marked records that are in no batch, in the order of
`gated_out.jsonl`, with the same fields, to a new folder. No model is called and no input file
is changed.

It raises when a sampled record is not a marked record, when a record id occurs twice, or when
the output exists.

Usage:
    uv run scripts/gated_out_remaining.py --round-dir outputs/screening/chase_round_1 \
        --out-dir outputs/screening/chase_round_1_full_screening
"""

import argparse
import json
import pathlib


class RemainingError(Exception):
    """The round's files are inconsistent, or the output exists."""


def read_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def remaining(marked: list[dict], batches: list[list[dict]]) -> list[dict]:
    """The marked records in no batch, in the order of `marked`."""
    marked_ids = [r["pmid"] for r in marked]
    if len(set(marked_ids)) != len(marked_ids):
        raise RemainingError("a marked record occurs twice")
    sampled = [r["pmid"] for batch in batches for r in batch]
    if len(set(sampled)) != len(sampled):
        raise RemainingError("a record is in two audit batches")
    strangers = sorted(set(sampled) - set(marked_ids))
    if strangers:
        raise RemainingError(f"sampled records that are not marked records: {strangers[:5]}")
    taken = set(sampled)
    return [r for r in marked if r["pmid"] not in taken]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round-dir", type=pathlib.Path, required=True)
    ap.add_argument("--out-dir", type=pathlib.Path, required=True)
    a = ap.parse_args()
    out = a.out_dir / "gated_out_remaining.jsonl"
    if out.exists():
        raise RemainingError(f"{out} exists; archive it before rerunning")
    marked = read_jsonl(a.round_dir / "gated_out.jsonl")
    batch_files = sorted(a.round_dir.glob("gate_sample_batch_*.jsonl"))
    batches = [read_jsonl(p) for p in batch_files]
    rows = remaining(marked, batches)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    counts = {"round_dir": str(a.round_dir), "marked": len(marked),
              "audit_batches": [p.name for p in batch_files],
              "sampled_by_the_audit": sum(len(b) for b in batches), "remaining": len(rows)}
    (a.out_dir / "gated_out_remaining_counts.json").write_text(json.dumps(counts, indent=1))
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
