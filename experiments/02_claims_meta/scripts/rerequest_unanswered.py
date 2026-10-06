# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Second request of records whose first request received no response.

On 2026-10-06 the API account ran out of credit during stage 2 and 66 search records received
HTTP 429 on every try of both attempts, so they hold no answer. The registered re-run rule covers
an invalid answer, not an unanswered request; the second request is a departure logged in
PREREG.md. This script calls no model. It writes the queue of the unanswered records for the
registered runner (run with another `--raw-root`, so no stored exchange is touched), and
afterwards one eligibility file in which each unanswered row is replaced by the row of the second
request. A row that holds an answer is never replaced.

    uv run scripts/rerequest_unanswered.py queue --first outputs/parsed/sol_eligibility_<label>_<rev>.jsonl \
        --queue outputs/screening/<run>/screening_queue.jsonl --raw outputs/raw/sol/eligibility/<rev> \
        --out outputs/screening/<run>_rerequest
    uv run scripts/run_extraction.py --task eligibility --label <label>_rerequest \
        --raw-root outputs/raw/sol_rerequest --abstracts outputs/screening/<run>_rerequest/unanswered_queue.jsonl
    uv run scripts/rerequest_unanswered.py merge --first <first file> --second <second file> \
        --out outputs/parsed/sol_eligibility_<label>_complete_<rev>.jsonl
"""

import argparse
import hashlib
import json
import pathlib
import re

NO_RESPONSE = re.compile(r"attempt \d+: HTTP (429|None|5\d\d)")


class RerequestError(Exception):
    """The second request cannot be prepared or merged as stated."""


def read_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unanswered(rows: list[dict]) -> list[str]:
    """Ids of the rows with no answer: failed, and every attempt an HTTP refusal or error.

    A row that failed because an answer did not pass the schema holds an answer and is not
    requested again.
    """
    ids = []
    for row in rows:
        if row["status"] == "ok":
            continue
        if not row["errors"] or not all(NO_RESPONSE.fullmatch(e) for e in row["errors"]):
            continue
        ids.append(row["pmid"])
    return ids


def stored_answers(raw: pathlib.Path, ids: list[str]) -> list[str]:
    """Ids among `ids` for which the first request's folder holds an HTTP-200 exchange."""
    return sorted(i for i in ids if any(raw.glob(f"{i}_attempt[0-9].json")))


def merge(first: list[dict], second: list[dict]) -> tuple[list[dict], list[str]]:
    """The first file's rows, each unanswered row replaced by the second request's row."""
    targets = set(unanswered(first))
    by_id = {r["pmid"]: r for r in second}
    if len(by_id) != len(second):
        raise RerequestError("the second request holds a record twice")
    if set(by_id) != targets:
        raise RerequestError(
            f"the second request must hold exactly the unanswered records: "
            f"{len(set(by_id) - targets)} not unanswered, {len(targets - set(by_id))} missing")
    out = [by_id[r["pmid"]] if r["pmid"] in targets else r for r in first]
    if [r["pmid"] for r in out] != [r["pmid"] for r in first]:
        raise RerequestError("row order changed")
    return out, sorted(targets)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("queue")
    q.add_argument("--first", type=pathlib.Path, required=True)
    q.add_argument("--queue", type=pathlib.Path, required=True)
    q.add_argument("--raw", type=pathlib.Path, required=True)
    q.add_argument("--out", type=pathlib.Path, required=True)
    m = sub.add_parser("merge")
    m.add_argument("--first", type=pathlib.Path, required=True)
    m.add_argument("--second", type=pathlib.Path, required=True)
    m.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()

    first = read_jsonl(a.first)
    if a.cmd == "queue":
        ids = unanswered(first)
        answered = stored_answers(a.raw, ids)
        if answered:
            raise RerequestError(f"records recorded as unanswered hold a stored answer: {answered[:5]}")
        by_id = {r["pmid"]: r for r in read_jsonl(a.queue)}
        missing = [i for i in ids if i not in by_id]
        if missing:
            raise RerequestError(f"unanswered records absent from the screening queue: {missing[:5]}")
        target = a.out / "unanswered_queue.jsonl"
        if target.exists():
            raise RerequestError(f"{target} exists")
        a.out.mkdir(parents=True, exist_ok=True)
        target.write_text("".join(json.dumps(by_id[i], ensure_ascii=False) + "\n" for i in ids))
        meta = {"first": str(a.first), "first_sha256": sha256(a.first),
                "queue": str(a.queue), "queue_sha256": sha256(a.queue),
                "n_rows_first": len(first), "n_unanswered": len(ids), "record_ids": ids}
        (a.out / "unanswered_queue.meta.json").write_text(json.dumps(meta, indent=1))
        print(json.dumps({k: v for k, v in meta.items() if k != "record_ids"}, indent=1))
        return

    if a.out.exists():
        raise RerequestError(f"{a.out} exists")
    rows, replaced = merge(first, read_jsonl(a.second))
    a.out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    meta = {"first": str(a.first), "first_sha256": sha256(a.first),
            "second": str(a.second), "second_sha256": sha256(a.second),
            "n_rows": len(rows), "n_replaced": len(replaced),
            "n_ok": sum(r["status"] == "ok" for r in rows),
            "n_extraction_failed": sum(r["status"] != "ok" for r in rows),
            "replaced_record_ids": replaced}
    a.out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps({k: v for k, v in meta.items() if k != "replaced_record_ids"}, indent=1))


if __name__ == "__main__":
    main()
