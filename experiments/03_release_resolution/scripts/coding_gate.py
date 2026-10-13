# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml==6.0.3"]
# ///
"""The provenance and identifier gate of the release-resolution follow-up (PREREG.md, §Study
design, Checks: "every accepted mapping: the quotation is pinned with `citations` in a frozen
file of the record; the pinned text holds the decisive identifier; the identifier maps to the
coded row in the table or dictionary; for D2 the reference entry verifies"). Used on the coded
answers of every pass and on the reports of the removed-chunk diagnostic. No model is called.

A row's answer passes when every release it identifies passes; a row that identifies none has
nothing to accept and passes. A release passes when one of its decisive passages passes:

    file        the passage names a file of the packet, and its quote stands verbatim in the
                text of that file as the packet gave it
    frozen      the quote stands verbatim in the frozen file the packet file came from (the
                abstract, the full text, or the whole retrieved supplement of a part or cut)
    pin         the quote is pinned in that frozen file with `citations pin` (first occurrence,
                as Paper 1's Amendment 3 fixed) and `citations verify --strict` resolves it
                (`pin`, run on the passages that pass the other checks)
    identifier  D1: the quote holds an accession, OpenGWAS identifier or numbered release that
                the accession table or the dictionary maps to exactly the coded row
                (source_scanner_v2.unit_matches over the quote), or writes the coded row's
                numbered release in another form (Paper 1's rule A,
                manual_coding_gates_v2.release_number_basis, sealed, imported unchanged).
                D2: a passage of the same row and release with rule `D2_reference_entry` holds
                a DOI, else a PMID, else a PMC identifier, and Paper 1's reference check
                (manual_coding_gates_v2.reference_check) verifies it against the coded row's
                `source_identifier`; the D2 passage itself passes `file` and `frozen`.

The coded release must be a dictionary row of the row's side.

Diagnostic (`diagnostic_miss`). A report from a removed chunk counts as a miss only when its
release passes the gate (with the whole supplement as the frozen file) and its quote does not
stand in the text the amended cut kept from the record's files.
"""

import csv
import hashlib
import json
import pathlib
import re
import subprocess

import yaml

import manual_coding_gates_v2 as g2
import source_scanner_v2 as scanner

DOI = re.compile(r"(?i)\b10\.\d{4,9}/[^\s\"<>]+")
PMID = re.compile(r"(?i)\bPMID:?\s*(\d{7,8})\b")
PMCID = re.compile(r"(?i)\bPMC\s*(\d{5,9})\b")


class GateError(Exception):
    """A passage names a file with no frozen source, or a claims file cannot be written."""


def identifiers_mapping(quote: str, patterns: dict, mapper: scanner.Mapper) -> set[str]:
    """The dictionary rows the quote's identifiers map to one by one (each to exactly one row)."""
    unit = {"record_id": "", "source_key": "", "unit_id": "", "text": quote}
    return {m["expected_row"] for m in scanner.unit_matches(unit, patterns, mapper)}


def reference_identifiers(quote: str, terminal: str) -> dict:
    out = {}
    if m := DOI.search(quote):
        out["doi"] = m.group(0).rstrip(terminal)
    if m := PMID.search(quote):
        out["pmid"] = m.group(1)
    if m := PMCID.search(quote):
        out["pmcid"] = m.group(1)
    return out


def check_passage(e: dict, packet_texts: dict[str, str], frozen: dict[str, dict]) -> list[str]:
    errors = []
    if e["file_id"] not in packet_texts:
        return ["file_not_in_packet"]
    if e["quote"] not in packet_texts[e["file_id"]]:
        errors.append("quote_not_in_packet_file")
    source = frozen.get(e["file_id"])
    if source is None:
        raise GateError(f"{e['file_id']}: no frozen source")
    if e["quote"] not in source["text"]:
        errors.append("quote_not_in_frozen_file")
    return errors


def gate_row(row: dict, side: str, packet: dict, frozen: dict[str, dict], patterns: dict,
             mapper: scanner.Mapper, dictionary: dict[str, dict]) -> dict:
    """The gate of one answered row. `frozen`: packet file id -> {"key", "text"} of the frozen
    file it came from; `dictionary`: row name -> dictionary row."""
    texts = {f["file_id"]: f["text"] for f in packet["files"]}
    releases = {}
    to_pin = []
    for release in row["identified_releases"]:
        own = [e for e in row["decisive_evidence"] if e["release"] == release]
        result = {"passes": False, "basis": None, "failures": []}
        if release not in dictionary or dictionary[release]["side"] != side:
            result["failures"].append("not_a_dictionary_row_of_the_side")
            releases[release] = result
            continue
        drow = dictionary[release]
        refs = [e for e in own if e["rule"] == "D2_reference_entry"]
        for e in own:
            if e["rule"] == "D2_reference_entry":
                continue
            errors = check_passage(e, texts, frozen)
            basis = None
            if e["rule"] == "D1":
                if identifiers_mapping(e["quote"], patterns, mapper) == {release}:
                    basis = "D1:identifier"
                elif g2.release_number_basis(drow, e["quote"]):
                    basis = "D1:release_number"
                else:
                    errors.append("no_identifier_mapping_to_the_coded_row")
            else:
                for r in refs:
                    r_errors = check_passage(r, texts, frozen)
                    found = reference_identifiers(r["quote"], patterns["doi_terminal_characters"])
                    how, failure = g2.reference_check(found, drow["source_identifier"])
                    if not r_errors and failure is None:
                        basis = f"D2:{how}"
                        to_pin.append(r)
                        break
                    errors += [f"reference:{x}" for x in r_errors + [failure] if x]
                if basis is None and not refs:
                    errors.append("no_reference_entry")
            if not errors and basis:
                result.update({"passes": True, "basis": basis})
                to_pin.append(e)
                break
            result["failures"].append({"quote_sha256": hashlib.sha256(e["quote"].encode()).hexdigest()[:16],
                                       "errors": sorted(set(errors))})
        releases[release] = result
    passes = all(r["passes"] for r in releases.values())
    return {"row_id": row["row_id"], "passes": passes, "releases": releases,
            "to_pin": [{"file_id": e["file_id"], "quote": e["quote"]} for e in to_pin]}


def diagnostic_miss(gated: dict, row: dict, kept_text: str) -> bool:
    """A verified report whose quotes the cut does not hold."""
    if not gated["passes"] or not row["identified_releases"]:
        return False
    return any(p["quote"] not in kept_text for p in gated["to_pin"])


def pin(folder: pathlib.Path, source: dict, claim_id: str, quote: str) -> dict:
    """Pin one quote in a frozen source with `citations pin --occurrence 1`; the source's text is
    written under `sources/` of the folder (an ignored location) and its claims file under
    `claims/`."""
    (folder / "sources").mkdir(parents=True, exist_ok=True)
    (folder / "claims").mkdir(parents=True, exist_ok=True)
    local = folder / "sources" / f"{source['key']}.txt"
    if not local.exists():
        local.write_text(source["text"])
    claims = folder / "claims" / f"{source['key']}.yaml"
    if not claims.exists():
        claims.write_text(yaml.safe_dump({"source": {"citation": source["key"],
                                                     "local": f"sources/{source['key']}.txt",
                                                     "sha256": source["sha256"]},
                                          "claims": {}}, sort_keys=False))
    run = subprocess.run(["citations", "pin", str(claims), "--id", claim_id, "--quote", quote,
                          "--occurrence", "1"], capture_output=True, text=True, cwd=folder)
    return {"claim_id": claim_id, "pinned": run.returncode == 0,
            "message": (run.stdout + run.stderr)[-500:]}


def verify(folder: pathlib.Path) -> dict:
    run = subprocess.run(["citations", "verify", "--claims", "claims", "--strict"],
                         capture_output=True, text=True, cwd=folder)
    return {"returncode": run.returncode, "report": (run.stdout + run.stderr)[-4000:]}


def dictionary_rows(path) -> dict[str, dict]:
    with open(path, newline="") as fh:
        return {r["name"]: r for r in csv.DictReader(fh)}


def write_json(path: pathlib.Path, data) -> None:
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
