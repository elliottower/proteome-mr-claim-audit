# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "numpy==2.5.3", "pydantic==2.13.5", "pyyaml==6.0.3"]
# ///
"""The reread of the rows on which the two checks of the manual dataset coding disagree
(PREREG.md, §Manual coding of dataset names, item 5: a disagreement is resolved by rereading
the source, and the resolution and the two original answers are kept; a row that cannot be
resolved stays unresolved; log of 2026-10-08).

`write` reads the rows to reread that scripts/manual_coding_check2_ingest_v3.py lists
(`disagreements_for_reread.json`: every row whose two values differ, the first check's value
taken under the gate rule) and writes, per coder role and paper,
`<out>/<coder>/input/<file name>.disagreement.json`: for each row its id, side and name as
written, and the two answers as `answer_1` and `answer_2`, each with its value, its
unresolved category and its quoted sentence. Which check gave which answer is not written
there: the order of the two is drawn per row with `random.Random(seed)` over the sorted row
ids, and the draw is recorded in `<out>/draw_manifest.json`, which no rereader is given. It
also writes each coder's papers in shares of at most 12
(`<out>/<coder>_share_<nn>.json`, each paper with its input file, its disagreement file and the
exact name of the resolution file to write).

`read` reads the rereaders' files, `<out>/<coder>/resolutions/<file name>.resolution.json`
(the paper's rows in disagreement, each with the resolved value, the reason when unresolved, a
one-line note, and for a dictionary row or an absent dataset the pinned sentence), checks that
every row in disagreement is resolved once and no other, and runs the machine gates
(scripts/manual_coding_gates_v2.py, `gate_row`) on every resolved row. A resolved row that
fails a gate is unresolved (`not_stated_in_source`, `release_not_identified`), with the
rereader's value and the failures in the note: a row that cannot be resolved stays unresolved.
The result is one file, `resolutions.json`, holding per row both original answers with their
quotations, the rereader's answer, the gate result and the value that stands.

`apply` writes a copy of the extended table (scripts/manual_coding_table_v2.py, after the
checker's values are filled) with `resolved_value` and `resolution_note` filled for those rows.
`claude_code_value` and `perplexity_value`, the two original answers, are not touched. Where
the value that stands is a dictionary row or an absent dataset, the row's evidence columns
(`source_read`, `quote`, `citations_claim`, `passage_id`, `identification_basis`,
`companion_source`, the reference entry, `dataset_named_in_source`) take the reread's pinned
evidence, and the note ends with the first check's own pin, which `resolutions.json` keeps in
full. It refuses when a row whose two answers differ has no resolution.

Usage:
    uv run scripts/manual_coding_reread.py write --ingested <ingest dir> --coders <coders dir> \\
        --out <reread dir> [--seed 20261008]
    uv run scripts/manual_coding_reread.py read --reread <reread dir> --coders <coders dir> \\
        --citations <citations dir>
    uv run scripts/manual_coding_reread.py apply --reread <reread dir> \\
        --codes <extended csv with the checker's values> --out <new extended csv>
"""

import argparse
import collections
import csv
import json
import pathlib
import random

from dataset_relations import DICTIONARY
from manual_coding_gates_v2 import gate_row
from manual_coding_table_v2 import ABSENT, EXTENDED_FIELDS, read_extended
from manual_dataset_coding import NOT_STATED, write_csv

SHARE = 12
EVIDENCE = ("source_read", "quote", "citations_claim", "passage_id", "identification_basis",
            "reference_label", "reference_quote", "reference_citations_claim",
            "dataset_named_in_source")
UNRESOLVED = (NOT_STATED, ABSENT)


class RereadError(Exception):
    """An output exists, or a resolution file does not match its disagreement file."""


def draw(row_ids: list[str], seed: int) -> dict[str, str]:
    """row id -> which check is shown as `answer_1` (`first_check` or `second_check`)."""
    rng = random.Random(seed)
    return {row: rng.choice(("first_check", "second_check")) for row in sorted(row_ids)}


def shown(answer: dict) -> dict:
    return {"value": answer["value"], "unresolved_category": answer["category"],
            "quoted_sentence": answer["quote"]}


def disagreement_file(record_id: str, coder: str, rows: list[dict], given: dict,
                      first_shown: dict[str, str]) -> dict:
    """What the rereader is given for one paper."""
    by_id = {}
    nth: collections.Counter = collections.Counter()
    for g in given["rows"]:
        nth[g["side"]] += 1
        by_id[f"{record_id}#{g['side']}_{nth[g['side']]}"] = g
    out = []
    for r in rows:
        order = (("first_check", "second_check") if first_shown[r["row"]] == "first_check"
                 else ("second_check", "first_check"))
        g = by_id[r["row"]]
        out.append({"row": r["row"].split("#", 1)[1], "side": g["side"],
                    "name_as_written": g["name_as_written"],
                    "answer_1": shown(r[order[0]]), "answer_2": shown(r[order[1]])})
    return {"record_id": record_id, "coder_id": coder, "rows_in_disagreement": out}


def write(ingested: pathlib.Path, coders: pathlib.Path, out: pathlib.Path, seed: int) -> dict:
    if out.exists():
        raise RereadError(f"{out} exists; the reread files are written once")
    listed = json.loads((ingested / "disagreements_for_reread.json").read_text())
    first_shown = draw([r["row"] for p in listed.values() for rows in p.values()
                        for r in rows], seed)
    out.mkdir(parents=True)
    summary = {"seed": seed, "coders": {}}
    for coder, papers in sorted(listed.items()):
        (out / coder / "input").mkdir(parents=True)
        (out / coder / "resolutions").mkdir()
        entries = []
        for input_file, rows in sorted(papers.items()):
            given = json.loads((coders / coder / "input" / input_file).read_text())
            name = input_file.removesuffix(".json")
            made = disagreement_file(given["record_id"], coder, rows, given, first_shown)
            target = out / coder / "input" / f"{name}.disagreement.json"
            target.write_text(json.dumps(made, indent=1, ensure_ascii=False) + "\n")
            entries.append({"input_file": input_file,
                            "disagreement_file": f"{coder}/input/{target.name}",
                            "rows_in_disagreement": len(rows),
                            "write_as": f"{coder}/resolutions/{name}.resolution.json"})
        shares = [entries[i:i + SHARE] for i in range(0, len(entries), SHARE)]
        for k, share in enumerate(shares, 1):
            (out / f"{coder}_share_{k:02d}.json").write_text(json.dumps(share, indent=1) + "\n")
        summary["coders"][coder] = {"papers": len(entries), "shares": len(shares),
                                    "rows": sum(e["rows_in_disagreement"] for e in entries)}
    (out / "draw_manifest.json").write_text(json.dumps(
        {"seed": seed, "note": "not for rereaders", "shown_as_answer_1": first_shown},
        indent=1) + "\n")
    (out / "source_rows.json").write_text(json.dumps(listed, indent=1, ensure_ascii=False)
                                          + "\n")
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    return summary


def resolve_paper(source_rows: list[dict], resolution: dict, given: dict,
                  dictionary: dict[tuple[str, str], dict], citations: pathlib.Path) -> list[dict]:
    """The value that stands for each row in disagreement of one paper."""
    record = given["record_id"]
    wanted = [r["row"] for r in source_rows]
    got = [f"{record}#{r['row']}" for r in resolution.get("rows", [])]
    if got != wanted or resolution.get("record_id") != record:
        raise RereadError(f"{record}: resolved rows {got}, rows in disagreement {wanted}")
    nth: collections.Counter = collections.Counter()
    paper_rows = {}
    for g in given["rows"]:
        nth[g["side"]] += 1
        paper_rows[f"{g['side']}_{nth[g['side']]}"] = g
    documents = {p["document"] for g in given["rows"] for p in g["passages"]}
    texts = {d: (citations / d).read_text() for d in sorted(documents)}
    refs = given["source"]["references"]
    reference_text = (citations / refs["document"]).read_text() if refs else ""
    out = []
    for src, res in zip(source_rows, resolution["rows"], strict=True):
        g = paper_rows[res["row"]]
        coded = {**res, "value": res.get("resolved_value")}
        gate = gate_row(coded, g, dictionary, texts, reference_text, citations, paper_rows)
        value, reason = res.get("resolved_value"), res.get("unresolved_reason")
        note = " ".join((res.get("resolution_note") or "").split())
        if not note:
            raise RereadError(f"{src['row']}: a resolution needs its note")
        if not gate["passes"]:
            note += (f" [the reread's value {value!r} failed the gate: "
                     f"{', '.join(gate['failures'])}; the row is unresolved]")
            value, reason = NOT_STATED, "release_not_identified"
        out.append({"row": src["row"], "class": src["class"],
                    "first_check": src["first_check"], "second_check": src["second_check"],
                    "reread": res, "gate": gate, "value_that_stands": value,
                    "unresolved_reason": None if value not in UNRESOLVED else reason,
                    "resolution_note": note})
    return out


def read(reread: pathlib.Path, coders: pathlib.Path, citations: pathlib.Path) -> dict:
    target = reread / "resolutions.json"
    if target.exists():
        raise RereadError(f"{target} exists; the resolutions are read once")
    with DICTIONARY.open(newline="") as f:
        dictionary = {(r["side"], r["name"]): r for r in csv.DictReader(f)}
    listed = json.loads((reread / "source_rows.json").read_text())
    rows, missing = [], []
    for coder, papers in sorted(listed.items()):
        for input_file, source_rows in sorted(papers.items()):
            name = input_file.removesuffix(".json")
            path = reread / coder / "resolutions" / f"{name}.resolution.json"
            if not path.is_file():
                missing.append(f"{coder}/resolutions/{path.name}")
                continue
            given = json.loads((coders / coder / "input" / input_file).read_text())
            resolution = json.loads(path.read_text())
            if resolution.get("coder_id") != coder:
                raise RereadError(f"{path}: coder_id differs from the folder")
            rows += resolve_paper(source_rows, resolution, given, dictionary, citations)
    if missing:
        raise RereadError(f"no resolution file for: {missing[:10]} ({len(missing)} in all)")
    counts = collections.Counter(
        "resolved_to_a_dictionary_row" if r["value_that_stands"] not in UNRESOLVED
        else f"unresolved_{r['unresolved_reason']}" for r in rows)
    counts["reread_value_failed_the_gate"] = sum(not r["gate"]["passes"] for r in rows)
    result = {"rows": len(rows), "counts": dict(sorted(counts.items())), "resolutions": rows}
    target.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    return result


def apply(table: list[dict], resolutions: list[dict]) -> list[dict]:
    """The extended table with the resolutions written in."""
    by_row = {r["row"]: r for r in resolutions}
    out, used = [], set()
    nth: collections.Counter = collections.Counter()
    for t in table:
        nth[(t["record_id"], t["side"])] += 1
        key = f"{t['record_id']}#{t['side']}_{nth[(t['record_id'], t['side'])]}"
        res = by_row.get(key)
        if res is None:
            if t["claude_code_value"] != t["perplexity_value"]:
                raise RereadError(f"{key}: the two answers differ and no resolution is given")
            out.append(dict(t))
            continue
        used.add(key)
        value = res["value_that_stands"]
        new = {**t, "resolved_value": value,
               "resolution_note": f"{res['resolution_note']} [first-check pin: "
                                  f"{t['citations_claim'] or 'none'}]"}
        if res["gate"]["passes"] and (value not in UNRESOLVED or value == ABSENT):
            reread = res["reread"]
            for field in EVIDENCE:
                new[field] = reread.get(field) or ""
            new["companion_source"] = "yes" if reread.get("companion_source") else "no"
            new["unresolved_reason"] = res["unresolved_reason"] or ""
        elif value in UNRESOLVED:
            new["unresolved_reason"] = res["unresolved_reason"] or ""
        out.append(new)
    if used != set(by_row):
        raise RereadError(f"resolutions of rows not in the table: {sorted(set(by_row) - used)}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    w = sub.add_parser("write")
    for name in ("ingested", "coders", "out"):
        w.add_argument(f"--{name}", type=pathlib.Path, required=True)
    w.add_argument("--seed", type=int, default=20261008)
    r = sub.add_parser("read")
    for name in ("reread", "coders", "citations"):
        r.add_argument(f"--{name}", type=pathlib.Path, required=True)
    a = sub.add_parser("apply")
    for name in ("reread", "codes", "out"):
        a.add_argument(f"--{name}", type=pathlib.Path, required=True)
    args = ap.parse_args()
    if args.command == "write":
        print(json.dumps(write(args.ingested, args.coders, args.out, args.seed), indent=1))
    elif args.command == "read":
        print(json.dumps(read(args.reread, args.coders, args.citations)["counts"], indent=1))
    else:
        resolutions = json.loads((args.reread / "resolutions.json").read_text())["resolutions"]
        write_csv(args.out, EXTENDED_FIELDS, apply(read_extended(args.codes), resolutions))
        print(args.out)


if __name__ == "__main__":
    main()
