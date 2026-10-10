# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1"]
# ///
"""The release-level expansion table of the release-resolution plan, built before its freeze
(experiments/03_release_resolution/PREREG.md, §Study design, meta-analysis canonicalization).

Every meta-analysis or combination row of Paper 1's dictionary is decided in
`reference/meta_analysis_expansion_decisions.json`: expanded, with its component dictionary
releases, endpoint, ancestry, version and roles, only when every one is explicitly documented
and every component is a dictionary row; otherwise omitted, with the reason. Nothing is
inferred from cohort names, dates or counts.

`fetch` stores the documents the decisions cite, from the URLs listed there, under an ignored
folder (they are third-party text), each with its sha256, without an e-mail address in any
request and without imitating a browser. A stored document is not fetched again.

`build` checks the decisions against the dictionary and the stored documents and writes the
two frozen tables: `meta_analysis_expansions.csv` (the expanded rows, one line per component)
and `meta_analysis_expansions_omitted.csv` (the omitted rows with their reason). It stops when
a meta-analysis or combination row of the dictionary has no decision or two, when a decision
names a row the dictionary does not hold, when an expanded row names a component that is not a
dictionary row or lacks a field, or when a cited document is missing or changed.

Usage:
    uv run scripts/meta_analysis_expansions.py fetch --decisions <json> --raw <dir>
    uv run scripts/meta_analysis_expansions.py build --decisions <json> --dictionary <csv> \\
        --raw <dir> --out <dir>
"""

import argparse
import csv
import hashlib
import json
import pathlib
import re

import httpx

META = re.compile(r"meta|\+| and |combined|joint", re.I)
COMPONENT_FIELDS = ("component", "endpoint", "ancestry", "version", "role")
EXPANDED = ["meta_analysis_row", "component", "endpoint", "ancestry", "version", "role",
            "documents_sha256"]
OMITTED = ["meta_analysis_row", "reason_category", "reason", "documents_sha256"]


class ExpansionError(Exception):
    """A decision does not fit the dictionary or the stored documents."""


def meta_rows(dictionary: list[dict]) -> list[str]:
    return [r["name"] for r in dictionary if META.search(r["name"])]


def stored(raw: pathlib.Path) -> dict[str, str]:
    path = raw / "manifest.json"
    return json.loads(path.read_text()) if path.exists() else {}


def fetch(client: httpx.Client, decisions: dict, raw: pathlib.Path) -> dict[str, str]:
    raw.mkdir(parents=True, exist_ok=True)
    manifest = stored(raw)
    for key, url in sorted(decisions["documents"].items()):
        if key in manifest:
            continue
        r = client.get(url)
        r.raise_for_status()
        (raw / key).write_bytes(r.content)
        manifest[key] = hashlib.sha256(r.content).hexdigest()
        (raw / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return manifest


def build(decisions: dict, dictionary: list[dict], raw: pathlib.Path
          ) -> tuple[list[dict], list[dict]]:
    names = {r["name"] for r in dictionary}
    wanted = meta_rows(dictionary)
    decided = [d["name"] for d in decisions["rows"]]
    if sorted(decided) != sorted(wanted):
        raise ExpansionError(f"rows without a decision: {sorted(set(wanted) - set(decided))}; "
                             f"decisions for other rows or twice: "
                             f"{sorted(n for n in decided if decided.count(n) > 1 or n not in wanted)}")
    manifest = stored(raw)
    expanded, omitted = [], []
    for d in decisions["rows"]:
        docs = []
        for key in d["documents"]:
            path = raw / key
            if key not in manifest or not path.exists() or \
                    hashlib.sha256(path.read_bytes()).hexdigest() != manifest[key]:
                raise ExpansionError(f"{d['name']}: document {key} is missing or changed")
            docs.append(manifest[key])
        shas = "|".join(docs)
        if d["decision"] == "omit":
            if not d.get("reason") or not d.get("reason_category"):
                raise ExpansionError(f"{d['name']}: an omission needs a reason")
            omitted.append({"meta_analysis_row": d["name"], "reason_category": d["reason_category"],
                            "reason": d["reason"], "documents_sha256": shas})
        elif d["decision"] == "expand":
            if not docs or not d.get("components"):
                raise ExpansionError(f"{d['name']}: an expansion needs documents and components")
            for c in d["components"]:
                if any(not str(c.get(f, "")).strip() for f in COMPONENT_FIELDS):
                    raise ExpansionError(f"{d['name']}: a component lacks a field")
                if c["component"] not in names or c["component"] == d["name"]:
                    raise ExpansionError(f"{d['name']}: {c['component']!r} is not another "
                                         "dictionary row")
                expanded.append({"meta_analysis_row": d["name"],
                                 **{f: c[f] for f in COMPONENT_FIELDS}, "documents_sha256": shas})
        else:
            raise ExpansionError(f"{d['name']}: decision {d['decision']!r}")
    return expanded, omitted


def write(path: pathlib.Path, fields: list[str], rows: list[dict]) -> None:
    if path.exists():
        raise FileExistsError(f"{path} exists; it is written once")
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    f = sub.add_parser("fetch")
    b = sub.add_parser("build")
    for s in (f, b):
        s.add_argument("--decisions", type=pathlib.Path, required=True)
        s.add_argument("--raw", type=pathlib.Path, required=True)
    b.add_argument("--dictionary", type=pathlib.Path, required=True)
    b.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    decisions = json.loads(a.decisions.read_text())
    if a.command == "fetch":
        with httpx.Client(timeout=120, follow_redirects=True) as client:
            print(json.dumps(fetch(client, decisions, a.raw), indent=1))
        return
    with a.dictionary.open(newline="") as fh:
        dictionary = list(csv.DictReader(fh))
    expanded, omitted = build(decisions, dictionary, a.raw)
    write(a.out / "meta_analysis_expansions.csv", EXPANDED, expanded)
    write(a.out / "meta_analysis_expansions_omitted.csv", OMITTED, omitted)
    print(json.dumps({"meta_analysis_rows": len(meta_rows(dictionary)),
                      "expanded_rows": len({r["meta_analysis_row"] for r in expanded}),
                      "omitted_rows": len(omitted),
                      "omitted_by_reason": {k: sum(o["reason_category"] == k for o in omitted)
                                            for k in sorted({o["reason_category"]
                                                             for o in omitted})}}, indent=1))


if __name__ == "__main__":
    main()
