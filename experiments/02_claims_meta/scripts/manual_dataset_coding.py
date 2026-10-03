# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""Manual coding of the dataset names that the automatic mapping leaves unresolved. No model is
called here; this script writes the queue and checks the table of codes.

Trigger. A dataset name on a registry claim record whose mapping state
(scripts/dataset_relations.py) is `release_ambiguous` or `unmatched`. A name that is
`not_stated` is not queued. The queue has one row per record, side and name as written.

Coding. For each queued row the paper is read (its methods or data passage in the Europe PMC
open-access full text where there is one, else its abstract) and the name is coded to one row
of the dataset dictionary, or to `not_stated_in_source` when the passage does not state which
release or platform was used. The coding concerns dataset and platform identity only: never
direction, significance, eligibility, protein or outcome. Each row goes through three checks,
all recorded:

    1. Claude Code reads the paper, codes the value and quotes the sentence, which is pinned
       with the `citations` CLI (`claude_code_value`, `quote`, `citations_claim`).
    2. Perplexity is given the paper reference and the question without the coded value; its
       answer is recorded (`perplexity_value`).
    3. The author confirms the row against the pinned sentence (`author_confirms`).

A row is `coded` only when the three agree: the two values are equal, name a dictionary row of
that side, and the author confirms. When the first two answers differ the source is reread; the
value all three then agree on goes in `resolved_value` with a `resolution_note`, and the two
original answers stay in the table. A row with no agreed value, or whose agreed value is
`not_stated_in_source`, is `unresolved`: the automatic mapping stands and the row is counted.
The `status` column must equal the status these rules give, or the table is refused.

What the coder and the checker see. Manual coders and checkers receive only the unresolved
dataset string, its local paper passage and candidate dictionary definitions; they do not
receive the canonical protein–outcome pair, other families' dataset assignments, the resulting
relation class, or any H1/H2 aggregate. The packet written with the queue
(`manual_coding_packet.csv`) holds, per row, the record, the side, the name as written and the
candidate rows with their dictionary definitions (release, participant sources, platform), and
nothing else.

Further rules. Every code is committed before the registry is assembled with the codes (the
queue comes from an assembly made without them). The source must identify the release: a name
is never coded to the closest available release, and when the passage does not identify one the
answer is `not_stated_in_source` and the row is `unresolved`. Both original answers, and so
every disagreement, stay in the committed table.

Use. scripts/assemble_registry.py replaces a coded name by its dictionary row and lists the
replacement on the claim (`manual_dataset_codes`); the family–pair record is flagged
`manually_coded`. The number of manually coded claim records, family–pair records, H1 pairs,
multi-family pairs and enrichment claims is reported, and the sensitivity analysis
`without_manual_dataset_coding` reruns H1, H2 and the pathway enrichment without the codes.

Usage:
    uv run scripts/manual_dataset_coding.py queue --claims <registry_claims.jsonl> [...] \\
        --out <dir>
    uv run scripts/manual_dataset_coding.py check --codes <manual_dataset_codes.csv> \\
        --queue <manual_coding_queue.csv> --out <dir>
"""

import argparse
import collections
import csv
import datetime
import hashlib
import json
import pathlib

from build_registry import RegistryClaim
from dataset_relations import DICTIONARY, Row, load_rows, map_name
from smoke_guard import check_smoke_output

QUEUE_STATES = ("release_ambiguous", "unmatched")
NOT_STATED = "not_stated_in_source"
SOURCES = ("full_text", "abstract")
QUEUE_FIELDS = ["record_id", "side", "name_as_written", "family_id", "mapping_state",
                "candidates", "claim_records"]
PACKET_FIELDS = ["record_id", "side", "name_as_written", "candidate_rows"]
DEFINITION_FIELDS = ("release", "cohort_components", "platform")
CODE_FIELDS = ["record_id", "side", "name_as_written", "source_read", "quote",
               "citations_claim", "claude_code_value", "perplexity_value", "resolved_value",
               "resolution_note", "author_confirms", "status"]
Key = tuple[str, str, str]


class ManualCodingError(Exception):
    """The table of codes is malformed, disagrees with its own status, or misses a queue row."""


def record_of(claim: RegistryClaim) -> str:
    return claim.claim_record_id.rsplit(":", 1)[0]


def queue(claims: list[RegistryClaim], rows: list[Row]) -> list[dict]:
    """One row per record, side and name whose automatic mapping is not resolved."""
    found: dict[Key, dict] = {}
    for c in claims:
        for side, names in (("pqtl", c.pqtl_datasets), ("outcome", c.outcome_datasets)):
            for name in names:
                m = map_name(name, side, rows)
                if m.state not in QUEUE_STATES:
                    continue
                key = (record_of(c), side, name)
                row = found.setdefault(key, {
                    "record_id": key[0], "side": side, "name_as_written": name,
                    "family_id": c.family_id, "mapping_state": m.state,
                    "candidates": "|".join(m.candidates), "claim_records": 0})
                row["claim_records"] += 1
    return [found[k] for k in sorted(found)]


def packet(queue_rows: list[dict], dictionary: pathlib.Path = DICTIONARY) -> list[dict]:
    """What the coder and the checker receive for each queue row: the record, the side, the
    name as written, and each candidate row of the dictionary with its definition. A candidate
    that is not a dictionary row (an unlisted release or combination) is listed by name."""
    with dictionary.open(newline="") as f:
        definitions = {(r["side"], r["name"]): {k: r[k] for k in DEFINITION_FIELDS}
                       for r in csv.DictReader(f)}
    return [{"record_id": q["record_id"], "side": q["side"],
             "name_as_written": q["name_as_written"],
             "candidate_rows": json.dumps([
                 {"row": c, **definitions.get((q["side"], c), {})}
                 for c in q["candidates"].split("|") if c], ensure_ascii=False)}
            for q in queue_rows]


def final_value(row: dict) -> str | None:
    """The value the three checks agree on, or None."""
    if row["author_confirms"] != "yes":
        return None
    first, second = row["claude_code_value"], row["perplexity_value"]
    if first and first == second:
        return first
    return row["resolved_value"] if row["resolved_value"] and row["resolution_note"] else None


def load_codes(path: pathlib.Path, rows: list[Row]) -> tuple[dict[Key, str], dict]:
    """(key -> dictionary row for the coded rows, report). Raises on a malformed table."""
    names = {(r.side, r.name) for r in rows}
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != CODE_FIELDS:
            raise ManualCodingError(f"{path.name}: columns must be {CODE_FIELDS}")
        table = list(reader)
    codes: dict[Key, str] = {}
    seen: set[Key] = set()
    counts: collections.Counter = collections.Counter()
    for r in table:
        key = (r["record_id"], r["side"], r["name_as_written"])
        if not all(key) or r["side"] not in ("pqtl", "outcome"):
            raise ManualCodingError(f"{key}: record, side or name missing or malformed")
        if key in seen:
            raise ManualCodingError(f"{key} is listed twice")
        seen.add(key)
        if not r["claude_code_value"] or not r["perplexity_value"]:
            raise ManualCodingError(f"{key}: both recorded answers are required")
        agree = r["claude_code_value"] == r["perplexity_value"]
        counts["step2_agree" if agree else "step2_disagree"] += 1
        value = final_value(r)
        status = "coded" if value not in (None, NOT_STATED) else "unresolved"
        if r["status"] != status:
            raise ManualCodingError(f"{key}: status {r['status']!r}, the checks give {status!r}")
        counts[status] += 1
        if status == "unresolved":
            counts["unresolved_not_stated_in_source" if value == NOT_STATED
                   else "unresolved_no_agreement"] += 1
            continue
        if (r["side"], value) not in names:
            raise ManualCodingError(f"{key}: {value!r} is not a {r['side']} dictionary row")
        if r["source_read"] not in SOURCES or not r["quote"].strip() or not r["citations_claim"]:
            raise ManualCodingError(f"{key}: a coded row needs its source, quote and "
                                    "citations claim")
        counts[f"coded_from_{r['source_read']}"] += 1
        counts["coded_after_resolution"] += not agree
        codes[key] = value
    return codes, {"rows": len(table), **{k: counts[k] for k in sorted(counts)}}


def check_cover(codes_path: pathlib.Path, queue_rows: list[dict]) -> None:
    """Every queue row must be in the table of codes once, and nothing else."""
    with codes_path.open(newline="") as f:
        coded = {(r["record_id"], r["side"], r["name_as_written"]) for r in csv.DictReader(f)}
    queued = {(r["record_id"], r["side"], r["name_as_written"]) for r in queue_rows}
    if coded != queued:
        raise ManualCodingError(f"queue rows without a code: {sorted(queued - coded)[:5]}; "
                                f"codes outside the queue: {sorted(coded - queued)[:5]}")


def read_claims(paths: list[pathlib.Path]) -> list[RegistryClaim]:
    return [RegistryClaim.model_validate_json(l) for p in paths
            for l in p.read_text().splitlines() if l.strip()]


def write_csv(path: pathlib.Path, fields: list[str], rows: list[dict]) -> None:
    if path.exists():
        raise FileExistsError(f"{path} exists; archive it before rerunning")
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    q = sub.add_parser("queue")
    q.add_argument("--claims", type=pathlib.Path, nargs="+", required=True,
                   help="registry_claims.jsonl assembled without manual codes")
    q.add_argument("--out", type=pathlib.Path, required=True)
    c = sub.add_parser("check")
    c.add_argument("--codes", type=pathlib.Path, required=True)
    c.add_argument("--queue", type=pathlib.Path, required=True)
    c.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.command == "queue":
        # The queue of a smoke registry goes under its smoke label, and no other queue does.
        for path in a.claims:
            check_smoke_output(path.parent, a.out.resolve().name)
    a.out.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    if a.command == "queue":
        queued = queue(read_claims(a.claims), rows)
        write_csv(a.out / "manual_coding_queue.csv", QUEUE_FIELDS, queued)
        write_csv(a.out / "manual_coding_packet.csv", PACKET_FIELDS, packet(queued))
        write_csv(a.out / "manual_dataset_codes.template.csv", CODE_FIELDS, [
            {**dict.fromkeys(CODE_FIELDS, ""), "record_id": r["record_id"], "side": r["side"],
             "name_as_written": r["name_as_written"]} for r in queued])
        print(json.dumps({"queue_rows": len(queued), "by_state": dict(collections.Counter(
            r["mapping_state"] for r in queued))}))
        return
    with a.queue.open(newline="") as f:
        queued = list(csv.DictReader(f))
    check_cover(a.codes, queued)
    codes, report = load_codes(a.codes, rows)
    target = a.out / "manual_dataset_coding_report.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; archive it before rerunning")
    target.write_text(json.dumps({
        "codes": str(a.codes), "codes_sha256": hashlib.sha256(a.codes.read_bytes()).hexdigest(),
        "queue": str(a.queue), "queue_rows": len(queued),
        "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        **report}, indent=1))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
