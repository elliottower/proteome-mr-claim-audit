# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""The character count of each scope record's abstract as Paper 1 stored it (the screening
sets), for the abstract-only requests of SA1 in the cost estimate. Counts only; no text is
written.

Usage: uv run scripts/abstract_characters.py --availability <json> --screening <jsonl> [...]
           --out <json>
"""

import argparse
import json
import pathlib


class AbstractError(Exception):
    """A scope record has no stored abstract, or the output exists."""


def characters(scope: list[str], screening: list[dict]) -> dict[str, int]:
    held = {r["pmid"]: r.get("abstract") or "" for r in screening}
    missing = sorted(r for r in scope if r not in held)
    if missing:
        raise AbstractError(f"no stored abstract for {missing[:5]}")
    return {r: len(held[r]) for r in sorted(scope)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--availability", type=pathlib.Path, required=True)
    ap.add_argument("--screening", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise AbstractError(f"{a.out} exists; it is written once")
    rows = [json.loads(line) for p in a.screening for line in p.read_text().splitlines()
            if line.strip()]
    counts = characters(sorted(json.loads(a.availability.read_text())["records"]), rows)
    a.out.write_text(json.dumps(counts, indent=1) + "\n")
    print(json.dumps({"records": len(counts), "characters": sum(counts.values())}))


if __name__ == "__main__":
    main()
