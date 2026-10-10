# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""The two mechanical scanners of the release-resolution plan, run on retrieved sources only after
retrieval, with no model and no reading by hand (PREREG.md, §Study design, C1; Other planned
analysis, SA7).

Input: the rendered units of the retrieved sources, one JSON object per line: `record_id`,
`source_key`, `unit_id` (a sentence or a table row with its header), `section_title`,
`sec_type`, `in_reference_list` and `text`.

C1. `controls` finds, in every unit outside a reference list, the explicit accessions, numbered
releases and source identifiers of `reference/c1_scanner_patterns.json`, and keeps a match only
when it lies within no longer match of its unit (the GCST inside an
OpenGWAS `ebi-a-` identifier), (1) it maps to exactly one dictionary row, through `reference/accession_releases.csv` (an
accession, or an OpenGWAS identifier under a batch prefix the table lists), through a dictionary
row whose own fields name the accession, through the dictionary row the release pattern names,
or through the dictionary row whose source identifier the DOI or PMID is; and (2) its unit holds a
context term. `draw` keeps one control per record, identifier and expected row, and draws up to
the frozen maximum by the frozen seed.

SA7. `links` records, per record, whether any unit holds a link to a host of
`reference/repository_link_hosts.json`, whether a unit inside an availability section does, and
which hosts.

Usage:
    uv run scripts/source_scanner.py controls --units <jsonl> --patterns <json> \\
        --accessions <csv> --dictionary <csv> --out <json>
    uv run scripts/source_scanner.py links --units <jsonl> --hosts <json> --out <json>
"""

import argparse
import collections
import csv
import json
import pathlib
import random
import re

TRAILING = ".,;:)]}'\""


class ScannerError(Exception):
    """An output exists already, or a pattern names a field the inputs lack."""


def norm_doi(doi: str) -> str:
    return doi.rstrip(TRAILING).lower()


class Mapper:
    """Identifier to the set of dictionary rows it names."""

    def __init__(self, patterns: dict, accessions: list[dict], dictionary: list[dict]):
        self.rows = {r["name"]: r["side"] for r in dictionary}
        self.exact: dict[str, set[str]] = collections.defaultdict(set)
        self.prefix: dict[str, set[str]] = collections.defaultdict(set)
        for a in accessions:
            target = self.prefix if a["identifier_type"] == "opengwas_batch" else self.exact
            target[a["release_identifier"]].add(a["dictionary_row"])
        acc = [re.compile(p["pattern"]) for p in patterns["accessions"]]
        doi = re.compile(next(p["pattern"] for p in patterns["source_identifiers"]
                              if p["type"] == "doi"))
        for r in dictionary:
            own = " ".join(r[f] for f in ("aliases", "release", "source_identifier"))
            for rx in acc:
                for m in rx.finditer(own):
                    self.exact[m.group(0)].add(r["name"])
            for m in doi.finditer(r["source_identifier"]):
                self.exact[f"doi:{norm_doi(m.group(0))}"].add(r["name"])
            for p in re.findall(r"PMID:\s*(\d+)", r["source_identifier"], re.I):
                self.exact[f"pmid:{p}"].add(r["name"])

    def accession(self, identifier: str) -> set[str]:
        found = set(self.exact.get(identifier, set()))
        if identifier.startswith("ebi-a-"):
            found |= self.exact.get(identifier.removeprefix("ebi-a-"), set())
        for prefix, rows in self.prefix.items():
            if identifier.startswith(prefix + "-"):
                found |= rows
        return found

    def release(self, row: str) -> set[str]:
        return {row} if row in self.rows else set()


def inside(span: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    """Whether a match lies within a longer match of the same unit (GCST in ebi-a-GCST)."""
    return any(s[0] <= span[0] and span[1] <= s[1] and s != span for s in spans)


def unit_matches(unit: dict, patterns: dict, mapper: Mapper) -> list[dict]:
    text = unit["text"]
    found = []
    for p in patterns["accessions"]:
        for m in re.finditer(p["pattern"], text):
            found.append((m.span(), "accession", p["type"], m.group(0), mapper.accession(m.group(0))))
    for p in patterns["releases"]:
        for m in re.finditer(p["pattern"], text):
            row = p["row"].format(n=int(m.group(1)))
            found.append((m.span(), "release", p["resource"], m.group(0), mapper.release(row)))
    for p in patterns["source_identifiers"]:
        for m in re.finditer(p["pattern"], text):
            key = (f"doi:{norm_doi(m.group(0))}" if p["type"] == "doi"
                   else f"pmid:{m.group(1)}")
            found.append((m.span(), "source_identifier", p["type"], m.group(0).rstrip(TRAILING),
                          set(mapper.exact.get(key, set()))))
    return [{"record_id": unit["record_id"], "source_key": unit["source_key"],
             "unit_id": unit["unit_id"], "kind": kind, "type": typ, "identifier": ident,
             "expected_row": next(iter(rows)), "side": mapper.rows[next(iter(rows))]}
            for span, kind, typ, ident, rows in found
            if len(rows) == 1 and not inside(span, [f[0] for f in found])]


def controls(units: list[dict], patterns: dict, mapper: Mapper) -> list[dict]:
    context = re.compile(patterns["context"])
    out = []
    for u in units:
        if u["in_reference_list"] or not context.search(u["text"]):
            continue
        out.extend(unit_matches(u, patterns, mapper))
    return out


def draw(found: list[dict], patterns: dict) -> list[dict]:
    seen, unique = set(), []
    for c in sorted(found, key=lambda c: (c["record_id"], c["identifier"], c["expected_row"],
                                          c["source_key"], c["unit_id"])):
        key = (c["record_id"], c["identifier"], c["expected_row"])
        if key not in seen:
            seen.add(key)
            unique.append(c)
    random.Random(patterns["draw"]["seed"]).shuffle(unique)
    return unique[:patterns["draw"]["maximum"]]


def links(units: list[dict], hosts: dict) -> dict[str, dict]:
    title = re.compile(hosts["availability_section"]["title"])
    out: dict[str, dict] = {}
    for u in units:
        rec = out.setdefault(u["record_id"], {"any_link": False, "availability_section_link": False,
                                              "hosts": [], "hosts_in_availability_section": []})
        in_avail = bool(title.search(u.get("section_title") or "")) or \
            u.get("sec_type") == hosts["availability_section"]["sec_type"]
        for h in hosts["hosts"]:
            if re.search(h["pattern"], u["text"]):
                rec["any_link"] = True
                if h["host"] not in rec["hosts"]:
                    rec["hosts"].append(h["host"])
                if in_avail:
                    rec["availability_section_link"] = True
                    if h["host"] not in rec["hosts_in_availability_section"]:
                        rec["hosts_in_availability_section"].append(h["host"])
    for rec in out.values():
        rec["hosts"].sort()
        rec["hosts_in_availability_section"].sort()
    return out


def read_csv(path: pathlib.Path) -> list[dict]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def write_once(path: pathlib.Path, data) -> None:
    if path.exists():
        raise ScannerError(f"{path} exists; it is written once")
    path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    c = sub.add_parser("controls")
    k = sub.add_parser("links")
    for s in (c, k):
        s.add_argument("--units", type=pathlib.Path, required=True)
        s.add_argument("--out", type=pathlib.Path, required=True)
    c.add_argument("--patterns", type=pathlib.Path, required=True)
    c.add_argument("--accessions", type=pathlib.Path, required=True)
    c.add_argument("--dictionary", type=pathlib.Path, required=True)
    k.add_argument("--hosts", type=pathlib.Path, required=True)
    a = ap.parse_args()
    units = [json.loads(line) for line in a.units.read_text().splitlines() if line.strip()]
    if a.command == "links":
        write_once(a.out, links(units, json.loads(a.hosts.read_text())))
        return
    patterns = json.loads(a.patterns.read_text())
    mapper = Mapper(patterns, read_csv(a.accessions), read_csv(a.dictionary))
    found = controls(units, patterns, mapper)
    write_once(a.out, {"found": found, "drawn": draw(found, patterns)})


if __name__ == "__main__":
    main()
