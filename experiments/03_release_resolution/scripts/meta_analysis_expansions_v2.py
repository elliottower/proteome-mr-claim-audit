# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1"]
# ///
"""The release-level expansion table of the release-resolution plan, built before its freeze
(experiments/03_release_resolution/PREREG.md, §Study design, meta-analysis canonicalization).
Second version: it adds provenance to every row of both tables and changes no decision.

Every meta-analysis or combination row of Paper 1's dictionary is decided in the decisions
file: expanded, with its component dictionary releases, endpoint, ancestry, version and roles,
only when every one is explicitly documented and every component is a dictionary row;
otherwise omitted, with the reason. Nothing is inferred from cohort names, dates or counts.

Each decision states its basis. `external_documentation`: the decision rests on documents the
decisions file lists, and the row carries their URL, access date and sha256, besides the
dictionary's version and sha256. `frozen_dictionary`: the decision rests on the frozen
dictionary alone, cites no document, and carries the dictionary's version and sha256.

`fetch` stores the cited documents under an ignored folder (they are third-party text) and
records, in `manifest_v2.json`, each one's URL, access date (UTC) and sha256, without an e-mail
address in any request and without imitating a browser. A document already stored by the first
version (listed in `manifest.json` with a matching sha256) is adopted with the date of its file
instead of being fetched again; a document in `manifest_v2.json` is not fetched again.

`build` checks the decisions against the dictionary and the stored documents and writes the two
frozen tables, `meta_analysis_expansions_v2.csv` (the expanded rows, one line per component, in
the registered columns) and `meta_analysis_expansions_omitted_v2.csv` (the omitted rows with
their reason, basis and provenance). It stops when a meta-analysis or combination row of the
dictionary has no decision or two, when a decision names a row the dictionary does not hold,
when an expanded row names a component that is not a dictionary row or lacks a field, when a
basis does not agree with the cited documents, when the dictionary's sha256 is not the one the
decisions file states, or when a cited document is missing or changed.

Usage:
    uv run scripts/meta_analysis_expansions_v2.py fetch --decisions <json> --raw <dir>
    uv run scripts/meta_analysis_expansions_v2.py build --decisions <json> --dictionary <csv> \\
        --raw <dir> --out <dir>
"""

import argparse
import csv
import datetime
import hashlib
import io
import json
import pathlib
import re

import httpx

META = re.compile(r"meta|\+| and |combined|joint", re.I)
COMPONENT_FIELDS = {"component_dictionary_row": "component", "endpoint": "endpoint",
                    "ancestry": "ancestry", "analysis_version": "version",
                    "component_role": "role"}
PROVENANCE = ["provenance_url", "access_date", "documents_sha256"]
DICTIONARY = ["dictionary_version", "dictionary_sha256"]
EXPANDED = ["meta_analysis_row", *COMPONENT_FIELDS, *PROVENANCE]
OMITTED = ["meta_analysis_row", "reason_category", "reason", "basis", *PROVENANCE, *DICTIONARY]
BASES = ("external_documentation", "frozen_dictionary")


class ExpansionError(Exception):
    """A decision does not fit the dictionary or the stored documents."""


def meta_rows(dictionary: list[dict]) -> list[str]:
    return [r["name"] for r in dictionary if META.search(r["name"])]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stored(raw: pathlib.Path) -> dict[str, dict]:
    path = raw / "manifest_v2.json"
    return json.loads(path.read_text()) if path.exists() else {}


def fetch(client: httpx.Client, decisions: dict, raw: pathlib.Path,
          today: datetime.date) -> dict[str, dict]:
    raw.mkdir(parents=True, exist_ok=True)
    manifest = stored(raw)
    first = raw / "manifest.json"
    adopted = json.loads(first.read_text()) if first.exists() else {}
    for key, url in sorted(decisions["documents"].items()):
        if key in manifest:
            continue
        path = raw / key
        if key in adopted and path.exists() and sha256(path.read_bytes()) == adopted[key]:
            date = datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.UTC).date()
        else:
            r = client.get(url)
            r.raise_for_status()
            path.write_bytes(r.content)
            date = today
        manifest[key] = {"url": url, "access_date": date.isoformat(),
                         "sha256": sha256(path.read_bytes())}
        (raw / "manifest_v2.json").write_text(json.dumps(manifest, indent=1, sort_keys=True)
                                              + "\n")
    return manifest


def build(decisions: dict, dictionary: list[dict], dictionary_sha256: str, raw: pathlib.Path
          ) -> tuple[list[dict], list[dict]]:
    if dictionary_sha256 != decisions["dictionary"]["sha256"]:
        raise ExpansionError("the dictionary is not the one the decisions name")
    names = {r["name"] for r in dictionary}
    wanted = meta_rows(dictionary)
    decided = [d["name"] for d in decisions["rows"]]
    if sorted(decided) != sorted(wanted):
        raise ExpansionError(f"rows without a decision: {sorted(set(wanted) - set(decided))}; "
                             f"decisions for other rows or twice: "
                             f"{sorted(n for n in decided if decided.count(n) > 1 or n not in wanted)}")
    manifest = stored(raw)
    dictionary_fields = {"dictionary_version": decisions["dictionary"]["version"],
                         "dictionary_sha256": dictionary_sha256}
    expanded, omitted = [], []
    for d in decisions["rows"]:
        docs = []
        for key in d["documents"]:
            path = raw / key
            if key not in manifest or not path.exists() or \
                    sha256(path.read_bytes()) != manifest[key]["sha256"] or \
                    manifest[key]["url"] != decisions["documents"][key]:
                raise ExpansionError(f"{d['name']}: document {key} is missing or changed")
            docs.append(manifest[key])
        if d.get("basis") not in BASES or \
                (d["basis"] == "external_documentation") != bool(docs):
            raise ExpansionError(f"{d['name']}: basis {d.get('basis')!r} does not agree with "
                                 f"{len(docs)} cited documents")
        provenance = {"provenance_url": "|".join(m["url"] for m in docs),
                      "access_date": "|".join(m["access_date"] for m in docs),
                      "documents_sha256": "|".join(m["sha256"] for m in docs)}
        if d["decision"] == "omit":
            if not d.get("reason") or not d.get("reason_category"):
                raise ExpansionError(f"{d['name']}: an omission needs a reason")
            omitted.append({"meta_analysis_row": d["name"], "reason_category": d["reason_category"],
                            "reason": d["reason"], "basis": d["basis"], **provenance,
                            **dictionary_fields})
        elif d["decision"] == "expand":
            if d["basis"] != "external_documentation" or not d.get("components"):
                raise ExpansionError(f"{d['name']}: an expansion needs documents and components")
            for c in d["components"]:
                if any(not str(c.get(f, "")).strip() for f in COMPONENT_FIELDS.values()):
                    raise ExpansionError(f"{d['name']}: a component lacks a field")
                if c["component"] not in names or c["component"] == d["name"]:
                    raise ExpansionError(f"{d['name']}: {c['component']!r} is not another "
                                         "dictionary row")
                expanded.append({"meta_analysis_row": d["name"],
                                 **{col: c[f] for col, f in COMPONENT_FIELDS.items()},
                                 **provenance})
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
        today = datetime.datetime.now(datetime.UTC).date()
        with httpx.Client(timeout=120, follow_redirects=True) as client:
            print(json.dumps(fetch(client, decisions, a.raw, today), indent=1))
        return
    data = a.dictionary.read_bytes()
    dictionary = list(csv.DictReader(io.StringIO(data.decode(), newline="")))
    expanded, omitted = build(decisions, dictionary, sha256(data), a.raw)
    write(a.out / "meta_analysis_expansions_v2.csv", EXPANDED, expanded)
    write(a.out / "meta_analysis_expansions_omitted_v2.csv", OMITTED, omitted)
    print(json.dumps({"meta_analysis_rows": len(meta_rows(dictionary)),
                      "expanded_rows": len({r["meta_analysis_row"] for r in expanded}),
                      "omitted_rows": len(omitted),
                      "omitted_by_basis": {k: sum(o["basis"] == k for o in omitted)
                                           for k in BASES},
                      "omitted_by_reason": {k: sum(o["reason_category"] == k for o in omitted)
                                            for k in sorted({o["reason_category"]
                                                             for o in omitted})}}, indent=1))


if __name__ == "__main__":
    main()
