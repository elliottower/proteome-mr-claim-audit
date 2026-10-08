# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""The table the author marks in the third check of the manual dataset coding (PREREG.md,
§Manual coding of dataset names, item 5: the author confirms each row against the pinned
sentence; a literal match: the pinned sentence, or the table it names, states the coded dataset
name, release or count).

One line per group of rows whose standing value is a dictionary row and whose pinned sentence,
coded row and reference entry are identical; the group's rows are listed and counted. The
standing value of a row is the value the two checks agree on or, where they differ, the
reread's resolution (scripts/manual_coding_reread.py). A row standing unresolved is not in the
table. Each line carries the coded dictionary row, the side, the pinned sentence, the reference
entry when the code rests on one (`companion_source`), the basis the coder gave, the identifier
the machine gate found in the pinned material, and two empty columns for the author:
`author_confirms` (yes or no) and `author_note`. Lines are sorted by coded row, then sentence,
so like lines stand together.

Usage: uv run scripts/manual_coding_check3_table.py --codes <extended csv after the reread> \\
           --coders <coders dir> --reread <reread dir> --out <csv>
"""

import argparse
import collections
import csv
import json
import pathlib

from manual_coding_table_v2 import ABSENT, ATTEMPT, GATES, read_extended
from manual_dataset_coding import NOT_STATED, write_csv

FIELDS = ["line", "n_rows", "dictionary_row", "side", "pinned_sentence", "reference_entry",
          "companion_source", "identification_basis", "gate_identifier", "source_read",
          "rows", "author_confirms", "author_note"]
UNRESOLVED = (NOT_STATED, ABSENT, "")


def standing(row: dict) -> str:
    """The value that stands for a row of the extended table."""
    if row["claude_code_value"] == row["perplexity_value"]:
        return row["claude_code_value"]
    return row["resolved_value"]


def gate_bases(coders: pathlib.Path, reread: pathlib.Path) -> dict[str, list[str]]:
    """row id -> the identifiers the gate found, from the last attempt's gate file, replaced
    by the reread's gate where the row was reread."""
    out = {}
    for coder in sorted(p for p in coders.glob("coder_*") if p.is_dir()):
        best: dict[str, int] = {}
        for path in (coder / "codes").glob("*.json"):
            m = ATTEMPT.match(path.name)
            if m:
                best[m["name"]] = max(best.get(m["name"], 0), int(m["n"]))
        for name, n in best.items():
            made = json.loads((coder / "codes" / f"{name}.attempt{n}.json").read_text())
            gate = json.loads((coder / GATES / f"{name}.attempt{n}.gate.json").read_text())
            nth: collections.Counter = collections.Counter()
            for g in gate["rows"]:
                nth[g["side"]] += 1
                out[f"{made['record_id']}#{g['side']}_{nth[g['side']]}"] = g["machine_basis"]
    for r in json.loads((reread / "resolutions.json").read_text())["resolutions"]:
        out[r["row"]] = r["gate"]["machine_basis"]
    return out


def table(rows: list[dict], bases: dict[str, list[str]]) -> list[dict]:
    """The grouped lines of the table."""
    groups: dict = collections.defaultdict(list)
    nth: collections.Counter = collections.Counter()
    for r in rows:
        nth[(r["record_id"], r["side"])] += 1
        value = standing(r)
        if value in UNRESOLVED:
            continue
        row_id = f"{r['record_id']}#{r['side']}_{nth[(r['record_id'], r['side'])]}"
        key = (value, r["side"], r["quote"], r["reference_quote"])
        groups[key].append((row_id, r))
    out = []
    for (value, side, quote, reference), members in sorted(groups.items()):
        first = members[0][1]
        found = sorted({b for row_id, _ in members for b in bases.get(row_id, [])})
        out.append({
            "n_rows": len(members), "dictionary_row": value, "side": side,
            "pinned_sentence": quote, "reference_entry": reference,
            "companion_source": first["companion_source"],
            "identification_basis": " | ".join(sorted({m["identification_basis"]
                                                       for _, m in members})),
            "gate_identifier": " | ".join(found),
            "source_read": " | ".join(sorted({m["source_read"] for _, m in members})),
            "rows": " ; ".join(f"{row_id} [{m['name_as_written']}]" for row_id, m in members),
            "author_confirms": "", "author_note": ""})
    for i, line in enumerate(out, 1):
        line["line"] = i
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    for name in ("codes", "coders", "reread", "out"):
        ap.add_argument(f"--{name}", type=pathlib.Path, required=True)
    a = ap.parse_args()
    lines = table(read_extended(a.codes), gate_bases(a.coders, a.reread))
    write_csv(a.out, FIELDS, lines)
    print(json.dumps({"lines": len(lines), "rows": sum(line["n_rows"] for line in lines),
                      "lines_with_a_reference_entry": sum(bool(line["reference_entry"])
                                                          for line in lines)}))


if __name__ == "__main__":
    main()
