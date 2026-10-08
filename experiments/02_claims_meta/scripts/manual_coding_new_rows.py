# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Set-up for coding the rows that the rebuilt manual-coding queue adds (PREREG.md, Amendment 2).
The rows are coded by the registered checks with the scripts of the run: the passage generator,
the assignment, the gates and the table script are used unchanged. This script does the three
things around them that the first run did by hand or with one-off code. It reads no coded value
and prints counts only.

`queue` writes the queue of the new rows alone: the rows of the rebuilt queue that
scripts/queue_rebuild_comparison_v2.py listed as new, exactly as the rebuilt queue has them. It
stops when a listed row is not in the rebuilt queue.

`shares` writes one list per coder that was dealt a paper, in the form of the lists of the
earlier passes: per paper the input file, the rules that flagged it (none), a gate file (none),
`next_attempt` 1 and `write_as`, the name of the attempt file.

`batch` writes the second check's batch file for the papers of a coders folder, in the format
of the batches of the run (one `## Paper` block per paper in record order with its reference
line; one `### Row` block per row with its side, name as written, candidate rows and every
passage with its sentences and reference entries), and the dictionary definitions file. No
first-check value is in either. The batch is numbered after the batches that exist.

Usage:
    uv run scripts/manual_coding_new_rows.py queue --rebuilt <manual_coding_queue.csv> \\
        --comparison <queue_rebuild_comparison json> --out <csv>
    uv run scripts/manual_coding_new_rows.py shares --coders <coders dir> --out <dir>
    uv run scripts/manual_coding_new_rows.py batch --coders <coders dir> --records <jsonl> [...] \\
        --number <n> --out <dir>
"""

import argparse
import collections
import csv
import hashlib
import json
import pathlib

DICTIONARY = pathlib.Path(__file__).resolve().parent.parent / "dataset_dictionary.csv"
DEFINITION_FIELDS = ("side", "name", "aliases", "release", "cohort_components", "ancestry",
                     "sample_size", "platform", "source_citation", "source_identifier")
Key = tuple[str, str, str]


class NewRowsError(Exception):
    """A listed row is missing, or an output exists."""


def key(row: dict) -> Key:
    return row["record_id"], row["side"], row["name_as_written"]


def new_queue(rebuilt: list[dict], listed: list[dict]) -> list[dict]:
    """The rows of the rebuilt queue that are listed as new, in the queue's order."""
    wanted = {key(r) for r in listed}
    out = [r for r in rebuilt if key(r) in wanted]
    if len(out) != len(listed) or len(wanted) != len(listed):
        raise NewRowsError("a listed row is not in the rebuilt queue, or is listed twice")
    return out


def share_list(input_files: list[str]) -> list[dict]:
    return [{"input_file": name, "rules": [], "gate_file": None, "next_attempt": 1,
             "write_as": f"{name.removesuffix('.json')}.attempt1.json"}
            for name in sorted(input_files)]


def reference(record: dict) -> str:
    """The reference line of a paper, as the batches of the run give it."""
    date = record.get("first_public")
    date = date.get("value") if isinstance(date, dict) else date
    ids = "; ".join(f"{k.upper()} {record[k]}" for k in ("pmid", "doi", "pmcid")
                    if record.get(k))
    return (f"{record.get('first_author_surname') or 'Author not recorded'} "
            f"({str(date)[:4]}). {record.get('title')}. {ids}")


def block(paper: dict, record: dict) -> str:
    """One paper of a batch file, as the batches of the run give it."""
    out = [f"## Paper {paper['record_id']}", "", f"Reference: {reference(record)}", ""]
    nth: collections.Counter = collections.Counter()
    for row in paper["rows"]:
        nth[row["side"]] += 1
        candidates = ("; ".join(row["candidates"])
                      or "none listed (any row of this side may be named)")
        out += [f"### Row {paper['record_id']}#{row['side']}_{nth[row['side']]}", "",
                f"- Side: {row['side']}", f"- Dataset name as written: {row['name_as_written']}",
                f"- Candidate dictionary rows: {candidates}", ""]
        for p in row["passages"]:
            out.append(f"Passage {p['passage_id']} ({p['source_read']}; "
                       f"section: {p['section'] or 'none'}):")
            out += [f"  {i + 1}. {s}" for i, s in enumerate(p["sentences"])]
            out += [f"  [reference {r['label']}] {r['entry']}"
                    + (f" (DOI {r['doi']})" if r.get("doi") else "") for r in p["references"]]
            out.append("")
    return "\n".join(out) + "\n"


def batch_text(papers: list[dict], records: dict[str, dict], number: int) -> str:
    papers = sorted(papers, key=lambda d: d["record_id"])
    rows = sum(len(d["rows"]) for d in papers)
    return (f"# Check 2, batch {number} of {number}: {rows} rows in {len(papers)} papers\n\n"
            "Answer every row below as the prompt file says.\n\n"
            + "".join(block(d, records[d["record_id"]]) for d in papers))


def coder_papers(coders: pathlib.Path) -> dict[str, list[pathlib.Path]]:
    return {c.name: sorted((c / "input").glob("*.json"))
            for c in sorted(coders.glob("coder_*")) if c.is_dir()}


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    q = sub.add_parser("queue")
    for name in ("rebuilt", "comparison", "out"):
        q.add_argument(f"--{name}", type=pathlib.Path, required=True)
    s = sub.add_parser("shares")
    s.add_argument("--coders", type=pathlib.Path, required=True)
    s.add_argument("--out", type=pathlib.Path, required=True)
    b = sub.add_parser("batch")
    b.add_argument("--coders", type=pathlib.Path, required=True)
    b.add_argument("--records", type=pathlib.Path, nargs="+", required=True)
    b.add_argument("--number", type=int, required=True)
    b.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise NewRowsError(f"{a.out} exists; it is written once")
    if a.command == "queue":
        with a.rebuilt.open(newline="") as f:
            reader = csv.DictReader(f)
            fields, rebuilt = reader.fieldnames, list(reader)
        made = new_queue(rebuilt, json.loads(a.comparison.read_text())["new_rows_list"])
        with a.out.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(made)
        print(json.dumps({"rows": len(made), "papers": len({r["record_id"] for r in made})}))
    elif a.command == "shares":
        a.out.mkdir(parents=True)
        made = {}
        for coder, files in coder_papers(a.coders).items():
            if files:
                path = a.out / f"{coder}_share_01.json"
                path.write_text(json.dumps(share_list([p.name for p in files]), indent=1) + "\n")
                made[coder] = {"file": path.name, "papers": len(files),
                               "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        (a.out / "shares_manifest.json").write_text(json.dumps(made, indent=1) + "\n")
        print(json.dumps({c: v["papers"] for c, v in made.items()}))
    else:
        records: dict[str, dict] = {}
        for path in a.records:
            for line in path.read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    records.setdefault(r["record_id"], r)
        papers = [json.loads(p.read_text()) for files in coder_papers(a.coders).values()
                  for p in files]
        a.out.mkdir(parents=True)
        target = a.out / f"batch_{a.number:02d}.md"
        target.write_text(batch_text(papers, records, a.number))
        with DICTIONARY.open(newline="") as f, \
                (a.out / "02_dictionary_definitions.csv").open("w", newline="") as g:
            w = csv.DictWriter(g, fieldnames=DEFINITION_FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(csv.DictReader(f))
        print(json.dumps({"batch": target.name, "papers": len(papers),
                          "rows": sum(len(d["rows"]) for d in papers),
                          "bytes": target.stat().st_size}))


if __name__ == "__main__":
    main()
