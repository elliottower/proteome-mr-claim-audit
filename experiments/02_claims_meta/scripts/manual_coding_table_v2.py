# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""The table of manual dataset codes with a second unresolved value and the abstract fallback
(PREREG.md log, 2026-10-07, deviations). scripts/manual_dataset_coding.py is unchanged and is
still what scripts/assemble_registry.py reads. This is the table script of the run; it
supersedes scripts/manual_coding_table.py, which stays sealed and is not used.

A row that cannot pass is unresolved (PREREG.md log, 2026-10-08). `collect` reads, for the last
attempt of each paper, the result of the machine gates (scripts/manual_coding_gates_v2.py,
`coders/<coder>/gates_v2/<file name>.attempt<n>.gate.json`). A row the coder coded to a
dictionary row and that fails a gate is written `not_stated_in_source` with the reason
`release_not_identified`; the coder's value goes to the column `coder_value_before_gate` and
the gate's failures to `gate_failures`. Every other row is written exactly as
scripts/manual_coding_table.py writes it, with those two columns empty. A paper whose last
attempt has no gate file is refused.

`second-check` writes a copy of the extended table with `perplexity_value` filled from the
counted answers of scripts/manual_coding_check2_ingest.py (its `comparison_with_first_check.json`);
it refuses unless every row has an answer.

scripts/manual_dataset_coding.py accepts, for a row that is not coded to a dictionary row, the
value `not_stated_in_source` only. A source that names a dataset the dictionary has no row for
does state its dataset, so such a row takes `source_names_dataset_absent_from_dictionary`
here. It is unresolved like a `not_stated_in_source` row: the automatic mapping stands, no
dataset relation is changed, and the row is counted under its own reason.

Two tables. The extended table (`manual_dataset_codes_extended.csv`) is the record: the twelve
columns of the registered table and, per row, the coder, the attempt, the passage, the reason a
row is unresolved, the basis of the identification, whether the code rests on an entry of the
paper's reference list (`companion_source`), that entry as pinned, the dataset the source names
when the dictionary has no row for it, and the coder's note. The registered table
(`manual_dataset_codes.csv`) is written from it by `check`: the twelve registered columns, with
`source_names_dataset_absent_from_dictionary` written as `not_stated_in_source` in the value
columns of every row whose agreed value it is, and `source_read`
`abstract_fallback_after_fulltext_no_match` written as `abstract` (the abstract is what was
read), so the registered reader takes it; nothing else is altered. `load_extended` returns exactly the codes
scripts/manual_dataset_coding.py::load_codes returns for that registered table.

The report of `check` counts the unresolved rows by reason, apart: release not identified,
conflicting identifiers, no local passage found, and dataset named in the source but absent
from the dictionary (which is not a source that states no dataset). A report of the manual
coding gives these four counts separately.

`collect` builds the extended table after the first check from the coders' files (the last
attempt of each paper), one row per queue row, in queue order; the Perplexity answer, the
resolution, the author's confirmation and the status are empty until the later checks fill
them.

Usage:
    uv run scripts/manual_coding_table_v2.py collect --coders <coders dir> \\
        --queue <manual_coding_queue.csv> --out <manual_dataset_codes_extended.csv>
    uv run scripts/manual_coding_table_v2.py check \\
        --codes <manual_dataset_codes_extended.csv> --queue <manual_coding_queue.csv> --out <dir>
    uv run scripts/manual_coding_table_v2.py second-check --ingested <ingest dir> \\
        --codes <manual_dataset_codes_extended.csv> --out <new extended csv>
"""

import argparse
import collections
import csv
import datetime
import hashlib
import json
import pathlib
import re
import tempfile

from dataset_relations import Row, load_rows
from manual_dataset_coding import (CODE_FIELDS, NOT_STATED, ManualCodingError, check_cover,
                                   final_value, load_codes, write_csv)

ABSENT = "source_names_dataset_absent_from_dictionary"
FALLBACK = "abstract_fallback_after_fulltext_no_match"
UNRESOLVED_VALUES = (NOT_STATED, ABSENT)
VALUE_FIELDS = ("claude_code_value", "perplexity_value", "resolved_value")
EXTRA_FIELDS = ["coder_id", "attempt", "passage_id", "unresolved_reason",
                "identification_basis", "companion_source", "reference_label",
                "reference_quote", "reference_citations_claim", "dataset_named_in_source",
                "coder_note", "coder_value_before_gate", "gate_failures"]
EXTENDED_FIELDS = CODE_FIELDS + EXTRA_FIELDS
REASONS = ("release_not_identified", "conflicting_identifiers", "no_local_passage_found",
           "dataset_absent_from_dictionary")
BASES = ("release_identifier", "source_identifier", "unique_citation",
         "exact_n_with_platform_or_year", "reference_entry")
GATES = "gates_v2"
ATTEMPT = re.compile(r"^(?P<name>.+)\.attempt(?P<n>\d+)\.json$")
Key = tuple[str, str, str]


def registered_rows(extended: list[dict]) -> list[dict]:
    """The registered table of an extended table: a row whose agreed value is
    `source_names_dataset_absent_from_dictionary` has that value written as
    `not_stated_in_source`, and the fallback source is written as `abstract`; everything else
    is as recorded."""
    return [{f: (NOT_STATED if f in VALUE_FIELDS and r[f] == ABSENT and final_value(r) == ABSENT
                 else "abstract" if f == "source_read" and r[f] == FALLBACK else r[f])
             for f in CODE_FIELDS} for r in extended]


def read_extended(path: pathlib.Path) -> list[dict]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != EXTENDED_FIELDS:
            raise ManualCodingError(f"{path.name}: columns must be {EXTENDED_FIELDS}")
        return list(reader)


def load_extended(path: pathlib.Path, rows: list[Row]) -> tuple[dict[Key, str], dict]:
    """(key -> dictionary row for the coded rows, report). The codes are those the registered
    reader returns for the registered table; the report counts the two unresolved values, and
    agreement at the second check, on the values as recorded."""
    table = read_extended(path)
    with tempfile.TemporaryDirectory() as folder:
        view = pathlib.Path(folder) / "manual_dataset_codes.csv"
        write_csv(view, CODE_FIELDS, registered_rows(table))
        codes, registered = load_codes(view, rows)
    counts: collections.Counter = collections.Counter()
    for r in table:
        key = (r["record_id"], r["side"], r["name_as_written"])
        counts["step2_agree" if r["claude_code_value"] == r["perplexity_value"]
               else "step2_disagree"] += 1
        value = final_value(r)
        if key in codes:
            counts["coded_resting_on_a_reference_entry"] += r["companion_source"] == "yes"
        elif value == ABSENT:
            counts[f"unresolved_{ABSENT}"] += 1
        elif value == NOT_STATED:
            counts[f"unresolved_{NOT_STATED}"] += 1
        else:
            counts["unresolved_no_agreement"] += 1
        if key in codes:
            counts[f"coded_from_{FALLBACK}"] += r["source_read"] == FALLBACK
        else:
            counts[f"unresolved_reason_{r['unresolved_reason'] or 'none_recorded'}"] += 1
    kept = {k: v for k, v in registered.items()
            if not k.startswith(("step2_", "unresolved_"))}
    return codes, {**kept, "unresolved": registered.get("unresolved", 0),
                   **{f"unresolved_reason_{reason}": 0 for reason in REASONS},
                   **{k: counts[k] for k in sorted(counts)}}


def latest_attempts(coders: pathlib.Path) -> dict[str, dict]:
    """record id -> the last attempt file of that paper, over every coder's folder."""
    best: dict[str, tuple[int, dict]] = {}
    for path in sorted(coders.glob("coder_*/codes/*.json")):
        m = ATTEMPT.match(path.name)
        if not m:
            raise ManualCodingError(f"{path}: not an attempt file")
        made = json.loads(path.read_text())
        n = int(m["n"])
        if made["attempt"] != n or made["coder_id"] != path.parent.parent.name:
            raise ManualCodingError(f"{path}: attempt or coder differs from the file's place")
        held = best.get(made["record_id"])
        if held and held[1]["coder_id"] != made["coder_id"]:
            raise ManualCodingError(f"{made['record_id']}: coded by two coders")
        if not held or n > held[0]:
            gate = path.parent.parent / GATES / f"{m['name']}.attempt{n}.gate.json"
            best[made["record_id"]] = (n, {**made, "gate_file": gate})
    return {rid: made for rid, (_, made) in best.items()}


def collect(coders: pathlib.Path, queue_rows: list[dict]) -> list[dict]:
    """One extended row per queue row from the coders' last attempts. Raises when a queue row
    has no code or a coder's file holds a row the queue does not."""
    attempts = latest_attempts(coders)
    coded: dict[Key, dict] = {}
    names = {(row.side, row.name) for row in load_rows()}
    for rid, made in attempts.items():
        if not made["gate_file"].is_file():
            raise ManualCodingError(f"{rid}: no gate file {made['gate_file'].name}")
        gate = json.loads(made["gate_file"].read_text())["rows"]
        if len(gate) != len(made["rows"]):
            raise ManualCodingError(f"{rid}: the gate file does not hold the attempt's rows")
        for r, g in zip(made["rows"], gate):
            key = (rid, r["side"], r["name_as_written"])
            if key in coded:
                raise ManualCodingError(f"{key} is coded twice")
            if (g["side"], g["name_as_written"]) != key[1:]:
                raise ManualCodingError(f"{key}: the gate file's row differs")
            before, failures = "", ""
            if not g["passes"] and (r["side"], r["value"]) in names:
                before, failures = r["value"], "|".join(g["failures"])
                r = {**r, "value": NOT_STATED, "unresolved_reason": REASONS[0],
                     "identification_basis": None}
            coded[key] = {**r, "coder_id": made["coder_id"], "attempt": made["attempt"],
                          "coder_value_before_gate": before, "gate_failures": failures}
    queued = [(q["record_id"], q["side"], q["name_as_written"]) for q in queue_rows]
    if set(queued) != set(coded):
        raise ManualCodingError(
            f"queue rows without a code: {sorted(set(queued) - set(coded))[:5]}; "
            f"codes outside the queue: {sorted(set(coded) - set(queued))[:5]}")
    out = []
    for key in queued:
        r = coded[key]
        out.append({**dict.fromkeys(EXTENDED_FIELDS, ""), "record_id": key[0], "side": key[1],
                    "name_as_written": key[2], "source_read": r.get("source_read") or "",
                    "quote": r.get("quote") or "",
                    "citations_claim": r.get("citations_claim") or "",
                    "claude_code_value": r["value"], "coder_id": r["coder_id"],
                    "attempt": str(r["attempt"]), "passage_id": r.get("passage_id") or "",
                    "unresolved_reason": r.get("unresolved_reason") or "",
                    "identification_basis": r.get("identification_basis") or "",
                    "companion_source": "yes" if r.get("companion_source") else "no",
                    "reference_label": r.get("reference_label") or "",
                    "reference_quote": r.get("reference_quote") or "",
                    "reference_citations_claim": r.get("reference_citations_claim") or "",
                    "dataset_named_in_source": r.get("dataset_named_in_source") or "",
                    "coder_note": r.get("coder_note") or "",
                    "coder_value_before_gate": r["coder_value_before_gate"],
                    "gate_failures": r["gate_failures"]})
    return out


def second_check(ingested: pathlib.Path, table: list[dict]) -> list[dict]:
    """The extended table with `perplexity_value` filled from the counted answers."""
    rows = json.loads((ingested / "comparison_with_first_check.json").read_text())["rows"]
    second = {r["row"]: r["second_check"] for r in rows}
    out, nth = [], collections.Counter()
    for r in table:
        nth[(r["record_id"], r["side"])] += 1
        key = f"{r['record_id']}#{r['side']}_{nth[(r['record_id'], r['side'])]}"
        if key not in second:
            raise ManualCodingError(f"{key} has no counted second-check answer")
        out.append({**r, "perplexity_value": second[key]})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--coders", type=pathlib.Path, required=True)
    c.add_argument("--queue", type=pathlib.Path, required=True)
    c.add_argument("--out", type=pathlib.Path, required=True)
    k = sub.add_parser("check")
    k.add_argument("--codes", type=pathlib.Path, required=True)
    k.add_argument("--queue", type=pathlib.Path, required=True)
    k.add_argument("--out", type=pathlib.Path, required=True)
    s2 = sub.add_parser("second-check")
    s2.add_argument("--ingested", type=pathlib.Path, required=True)
    s2.add_argument("--codes", type=pathlib.Path, required=True)
    s2.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.command == "second-check":
        write_csv(a.out, EXTENDED_FIELDS, second_check(a.ingested, read_extended(a.codes)))
        print(a.out)
        return
    with a.queue.open(newline="") as f:
        queued = list(csv.DictReader(f))
    if a.command == "collect":
        table = collect(a.coders, queued)
        write_csv(a.out, EXTENDED_FIELDS, table)
        print(json.dumps({"rows": len(table), "by_value_kind": dict(collections.Counter(
            v if v in UNRESOLVED_VALUES else "dictionary_row"
            for v in (r["claude_code_value"] for r in table))),
            "coded_rows_written_unresolved_for_a_failing_gate": sum(
                bool(r["coder_value_before_gate"]) for r in table)}))
        return
    check_cover(a.codes, queued)
    codes, report = load_extended(a.codes, load_rows())
    target = a.out / "manual_dataset_coding_report.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; archive it before rerunning")
    registered = a.out / "manual_dataset_codes.csv"
    write_csv(registered, CODE_FIELDS, registered_rows(read_extended(a.codes)))
    target.write_text(json.dumps({
        "codes": str(a.codes), "codes_sha256": hashlib.sha256(a.codes.read_bytes()).hexdigest(),
        "registered_table": str(registered),
        "registered_table_sha256": hashlib.sha256(registered.read_bytes()).hexdigest(),
        "queue": str(a.queue), "queue_rows": len(queued),
        "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        **report}, indent=1))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
