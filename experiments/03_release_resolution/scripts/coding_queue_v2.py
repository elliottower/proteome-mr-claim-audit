# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""Second version of scripts/coding_queue.py (sealed, unchanged and imported): the same queue,
with every input named by its path relative to the repository root, so the output records no
local path. Usage as in the first version.
"""

import argparse
import collections
import datetime
import hashlib
import json
import pathlib

import coding_queue as q
from build_registry import RegistryClaim
from dataset_relations import DICTIONARY

REPO = pathlib.Path(__file__).resolve().parents[3]


def relative(path: pathlib.Path) -> str:
    return str(path.resolve().relative_to(REPO))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coded", type=pathlib.Path, required=True)
    ap.add_argument("--plain", type=pathlib.Path, required=True)
    ap.add_argument("--checks", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise q.QueueError(f"{a.out} exists; it is written once")
    coded = [RegistryClaim.model_validate_json(l) for l in a.coded.read_text().splitlines()
             if l.strip()]
    plain = {r["claim_record_id"]: r for r in q.read_jsonl([a.plain])}
    written: dict[str, str] = {}
    for r in q.read_jsonl(a.checks):
        if "claim_record_id" in r:
            written.setdefault(r["claim_record_id"], r["outcome_as_written"])
    rows = q.queue(coded, plain, written)
    files = [a.coded, a.plain, *a.checks, DICTIONARY]
    out = {"written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
           "inputs_sha256": {relative(p): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in files},
           "rows": len(rows),
           "rows_by_side": dict(sorted(collections.Counter(r["side"] for r in rows).items())),
           "rows_not_stated_by_side": dict(sorted(collections.Counter(
               r["side"] for r in rows if r["name_as_written"] == q.SHOWN_NOT_STATED).items())),
           "records": len({r["record_id"] for r in rows}),
           "claim_records": len({c for r in rows for c in r["claim_record_ids"]}),
           "queue": rows}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "queue"}, indent=1))


if __name__ == "__main__":
    main()
