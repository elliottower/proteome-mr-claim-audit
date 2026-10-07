# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "numpy==2.5.3", "pydantic==2.13.5", "pyyaml==6.0.3"]
# ///
"""Machine gates on a coder's file of manual dataset codes, run before the second check
(PREREG.md log, 2026-10-07). The gates are quality-control checks added to the three
registered checks and replace none of them: a literal match does not show that a sentence
describes the dataset an analysis used.

For every row of an attempt file (`coders/<coder>/codes/<file name>.attempt<n>.json`):

    value        the value is a dictionary row of the row's side, `not_stated_in_source` or
                 `source_names_dataset_absent_from_dictionary`; an unresolved row gives one of
                 the four reasons, and the reason fits the value and the row's passage status
    pin          the quoted sentence is a sentence of a passage given for that row, occurs in
                 the pinned source document, and is the quotation the named claim of the
                 paper's claims file holds; for a `companion_source` row the same holds for
                 the reference entry, which must be an entry listed with that passage
    identifier   the pinned material (the sentence, and the reference entry when there is one)
                 holds a term of the coded dictionary row that no other candidate row has
                 (from `name`, `aliases`, `release`, `source_citation` or `source_identifier`),
                 or the row's exact sample size, shared with no other candidate, together with
                 its platform or a year of its release or source citation
    reference    for a `companion_source` row, the DOI the XML gives for the reference entry
                 is a DOI of the coded row's `source_identifier`; an entry without a DOI is
                 reported as `no_stable_identifier` and does not fail

Candidate rows are the row's candidates that are dictionary rows; for a row with none, every
dictionary row of its side. A coded value outside the candidate set is a warning. Terms and
their matching are those of scripts/coding_passages.py.

`citations verify --strict` is run once over the claims folder and its report kept. A gate
file `coders/<coder>/gates/<file name>.attempt<n>.gate.json` is written per attempt and never
overwritten; a failed attempt goes back to the same coder, who writes the next attempt, and
every attempt and gate file is kept.

Usage: uv run scripts/coding_gates.py --coders <coders dir> --citations <citations dir>
"""

import argparse
import collections
import csv
import datetime
import json
import os
import pathlib
import re
import subprocess

import yaml

from coding_passages import NO_PASSAGE, bounded, dictionary_terms, matches, normalize
from dataset_relations import DICTIONARY
from manual_dataset_coding_reasons import ABSENT, ATTEMPT, BASES, REASONS, UNRESOLVED_VALUES

UNIQUE_FIELDS = ("name", "aliases", "release", "source_citation", "source_identifier")
YEAR = re.compile(r"(?:19|20)\d{2}")
DOI = re.compile(r"10\.\d{4,9}/[^\s;]+")


class GateError(Exception):
    """An attempt file has no input file, or a gate file exists."""


def platform_terms(row: dict) -> list[str]:
    head = row["platform"].split("(")[0].strip()
    if not head or head == "NA":
        return []
    return list(dict.fromkeys([head, head.split()[0]]))


def identifier_basis(value_row: dict, pool: list[dict], material: str) -> list[str]:
    """Which identifiers of the coded row the pinned material holds; empty fails the gate."""
    others = {t for r in pool if r["name"] != value_row["name"] for t in dictionary_terms(r)}
    own = [t for t in dictionary_terms(value_row) if t not in others]
    found = [f"{f}:{t}" for f, t in own if f in UNIQUE_FIELDS and matches((f, t), material)]
    sizes = [t for t in own if t[0] == "sample_size" and matches(t, material)]
    norm = normalize(material)
    years = YEAR.findall(value_row["release"] + " " + value_row["source_citation"])
    beside = ([p for p in platform_terms(value_row) if bounded(p).search(norm)]
              + [y for y in years if bounded(y).search(norm)])
    if sizes and beside:
        found.append(f"sample_size:{sizes[0][1]}+{beside[0]}")
    return found


def pinned_quote(claims_root: pathlib.Path, reference: str) -> str | None:
    """The quotation of `claims/<file>.yaml#<id>`, or None when it is not there."""
    if "#" not in reference:
        return None
    name, claim_id = reference.rsplit("#", 1)
    path = claims_root / name
    if not path.is_file():
        return None
    quotes = (yaml.safe_load(path.read_text()).get("claims") or {}).get(claim_id, {}).get(
        "quotes") or []
    return quotes[0].get("exact") if quotes else None


def gate_row(coded: dict, given: dict, dictionary: dict[tuple[str, str], dict],
             source_text: str, reference_text: str, claims_root: pathlib.Path) -> dict:
    """The gate result of one coded row against the row the coder was given."""
    failures, warnings, basis = [], [], []
    side, value = given["side"], coded.get("value")
    row = dictionary.get((side, value))
    reason = coded.get("unresolved_reason")
    if row is None and value not in UNRESOLVED_VALUES:
        failures.append("value_not_allowed")
    if row is not None and reason:
        failures.append("coded_row_gives_an_unresolved_reason")
    if row is None and value in UNRESOLVED_VALUES:
        fits = (reason in REASONS
                and (reason == "dataset_absent_from_dictionary") == (value == ABSENT)
                and (reason == "no_local_passage_found") == (given["status"] == NO_PASSAGE))
        if not fits:
            failures.append("unresolved_reason_does_not_fit")
    needs_pin = row is not None or value == ABSENT
    sentence = coded.get("quote") or ""
    passage = next((p for p in given["passages"] if p["passage_id"] == coded.get("passage_id")),
                   None)
    if needs_pin:
        if passage is None or sentence not in passage["sentences"]:
            failures.append("quote_is_not_a_sentence_of_a_passage_given")
        if not sentence or normalize(sentence) not in normalize(source_text):
            failures.append("quote_not_in_the_source_document")
        if pinned_quote(claims_root, coded.get("citations_claim") or "") != sentence:
            failures.append("quote_is_not_the_pinned_quotation")
    if value == ABSENT and not (coded.get("dataset_named_in_source")
                                and normalize(coded["dataset_named_in_source"])
                                in normalize(sentence)):
        failures.append("named_dataset_not_in_the_quote")
    entry_text = ""
    if row is not None and coded.get("companion_source"):
        entry_text = coded.get("reference_quote") or ""
        entry = next((r for r in (passage or {}).get("references", [])
                      if r["entry"] == entry_text), None)
        if entry is None:
            failures.append("reference_entry_not_listed_with_the_passage")
        if not entry_text or normalize(entry_text) not in normalize(reference_text):
            failures.append("reference_entry_not_in_the_reference_list")
        if pinned_quote(claims_root, coded.get("reference_citations_claim") or "") != entry_text:
            failures.append("reference_entry_is_not_the_pinned_quotation")
        if entry and entry.get("doi"):
            wanted = {d.rstrip(".").casefold() for d in DOI.findall(row["source_identifier"])}
            if entry["doi"].casefold() not in wanted:
                failures.append("reference_doi_differs_from_the_dictionary_source")
        elif entry:
            warnings.append("no_stable_identifier")
    if row is not None:
        if coded.get("identification_basis") not in BASES:
            failures.append("identification_basis_not_allowed")
        named = [dictionary[(side, c)] for c in given["candidates"] if (side, c) in dictionary]
        if named and row not in named:
            warnings.append("value_outside_the_candidate_set")
        pool = named if row in named else [r for (s, _), r in dictionary.items() if s == side]
        basis = identifier_basis(row, pool, f"{sentence} {entry_text}")
        if not basis:
            failures.append("no_identifier_of_the_coded_row_in_the_pinned_material")
    return {"side": side, "name_as_written": given["name_as_written"], "value": value,
            "passes": not failures, "failures": failures, "warnings": warnings,
            "machine_basis": basis}


def gate_attempt(attempt: dict, given: dict, dictionary: dict[tuple[str, str], dict],
                 citations: pathlib.Path) -> dict:
    """The gate result of one attempt file: every row given must be coded once."""
    source_text = (citations / given["source"]["document"]).read_text()
    refs = given["source"]["references"]
    reference_text = (citations / refs["document"]).read_text() if refs else ""
    by_key = collections.defaultdict(list)
    for r in attempt["rows"]:
        by_key[(r["side"], r["name_as_written"])].append(r)
    rows, missing = [], []
    for g in given["rows"]:
        coded = by_key.pop((g["side"], g["name_as_written"]), [])
        if len(coded) != 1:
            missing.append([g["side"], g["name_as_written"]])
            continue
        rows.append(gate_row(coded[0], g, dictionary, source_text, reference_text, citations))
    wrong_coder = attempt["coder_id"] != given["coder_id"]
    return {"record_id": given["record_id"], "coder_id": attempt["coder_id"],
            "attempt": attempt["attempt"], "rows": rows,
            "rows_not_coded_once": missing, "rows_not_given": sorted(map(list, by_key)),
            "wrong_coder": wrong_coder,
            "passes": (not missing and not by_key and not wrong_coder
                       and all(r["passes"] for r in rows))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coders", type=pathlib.Path, required=True)
    ap.add_argument("--citations", type=pathlib.Path, required=True)
    a = ap.parse_args()
    with DICTIONARY.open(newline="") as f:
        dictionary = {(r["side"], r["name"]): r for r in csv.DictReader(f)}
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    env = {k: v for k, v in os.environ.items() if k != "CITATIONS_HOME"}
    verify = subprocess.run(["citations", "verify", "--claims", "claims", "--strict"],
                            capture_output=True, text=True, env=env, cwd=a.citations)
    (a.coders / f"citations_verify_{stamp}.txt").write_text(
        f"exit {verify.returncode}\n{verify.stdout}\n{verify.stderr}".replace(
            f"{a.citations.resolve()}/", ""))
    counts: collections.Counter = collections.Counter()
    for path in sorted(a.coders.glob("coder_*/codes/*.json")):
        m = ATTEMPT.match(path.name)
        if not m:
            raise GateError(f"{path}: not an attempt file")
        coder = path.parent.parent
        target = coder / "gates" / f"{m['name']}.attempt{m['n']}.gate.json"
        if target.exists():
            continue
        given_path = coder / "input" / f"{m['name']}.json"
        if not given_path.is_file():
            raise GateError(f"{path}: no input file {given_path}")
        result = gate_attempt(json.loads(path.read_text()), json.loads(given_path.read_text()),
                              dictionary, a.citations)
        result["gated_utc"] = stamp
        target.parent.mkdir(exist_ok=True)
        target.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
        counts["attempts_gated"] += 1
        counts["attempts_passed" if result["passes"] else "attempts_failed"] += 1
        counts["rows_failed"] += sum(not r["passes"] for r in result["rows"])
    print(json.dumps({"citations_verify_exit": verify.returncode, **counts}, indent=1))


if __name__ == "__main__":
    main()
