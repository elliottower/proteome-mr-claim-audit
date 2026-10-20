# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml==6.0.3"]
# ///
"""Manifest check of the second release-resolution registration (PREREG.md, §Study design, item
3; H5): the mapping script of Deviation 2, item 3 (the first registration's
scripts/manifest_mapping_check_v1.py, sealed, imported unchanged) run with the functions of the
gate of item 2 (scripts/coding_gate_v2.py) on the 31 manifest accessions. No model is called; the
coded manifest packets are not run. H5 holds when all 31 return the expected dictionary row.

Run from experiments/04_release_resolution_v2 on a copy of the volume's manifest packets
(/03_release_resolution/coding/packets/manifest/, which hold the accession table's lines only):

    PYTHONPATH=scripts:../03_release_resolution/scripts:../02_claims_meta/scripts \\
        uv run --no-project --with pyyaml==6.0.3 python scripts/manifest_mapping_check_v2.py \\
        --packets <copy> --out <json>

Per accession, as in the first version: the gate's identifiers_mapping on the accession alone and
on the packet file's text return exactly the expected row, and the gate's gate_row passes a D1
answer quoting the packet's table line.
"""

import argparse
import csv
import hashlib
import json
import pathlib

import coding_gate_v2 as gate
import manifest_mapping_check_v1 as first
import source_scanner_v2 as scanner

FIRST = pathlib.Path("../03_release_resolution")
INPUTS = {"patterns": FIRST / "reference/c1_scanner_patterns_v2.json",
          "accessions": FIRST / "reference/accession_releases.csv",
          "dictionary": pathlib.Path("../02_claims_meta/dataset_dictionary.csv"),
          "listing": FIRST / "outputs/c1_manifest_controls_2026-10-13.json",
          "gate_v2": pathlib.Path("scripts/coding_gate_v2.py"),
          "gate": FIRST / "scripts/coding_gate.py",
          "mapping_check_v1": FIRST / "scripts/manifest_mapping_check_v1.py",
          "scanner": FIRST / "scripts/source_scanner_v2.py"}


def check(entry: dict, packet: dict, patterns: dict, mapper: scanner.Mapper,
          dictionary: dict[str, dict]) -> dict:
    expected = entry["expected_row"]
    (row,) = packet["rows"]
    (file,) = packet["files"]
    line = file["text"].split("\n")[-1]
    by_identifier = sorted(gate.identifiers_mapping(entry["identifier"], patterns, mapper))
    by_file = sorted(gate.identifiers_mapping(file["text"], patterns, mapper))
    answer = {"row_id": row["row_id"], "identified_releases": [expected],
              "decisive_evidence": [{"release": expected, "rule": "D1",
                                     "file_id": file["file_id"], "quote": line}]}
    frozen = {file["file_id"]: {"key": file["file_id"], "sha256": "", "text": file["text"]}}
    verdict = gate.gate_row(answer, row["side"], packet, frozen, patterns, mapper, dictionary)
    checks = {"identifier": by_identifier == [expected], "packet_file": by_file == [expected],
              "gate_row": verdict["passes"]}
    return {"row_id": entry["row_id"], "identifier": entry["identifier"], "side": row["side"],
            "expected_row": expected, "returned_row_identifier": by_identifier,
            "returned_row_packet_file": by_file, "gate_row_passes": verdict["passes"],
            "gate_row_basis": verdict["releases"][expected]["basis"],
            "gate_row_failures": verdict["releases"][expected]["failures"],
            "checks": checks, "pass": all(checks.values())}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--packets", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise FileExistsError(f"{a.out} exists; it is written once")
    used = {str(p): first.sha256_bytes(p.read_bytes()) for p in INPUTS.values()}
    patterns = json.loads(INPUTS["patterns"].read_text())
    with INPUTS["accessions"].open(newline="") as fh:
        table = list(csv.DictReader(fh))
    dictionary = gate.dictionary_rows(INPUTS["dictionary"])
    mapper = scanner.Mapper(patterns, table, list(dictionary.values()))
    listing = json.loads(INPUTS["listing"].read_text())["listing"]
    volume_listing = a.packets / "manifest.json"
    used["volume:03_release_resolution/coding/packets/manifest/manifest.json"] = \
        first.sha256_bytes(volume_listing.read_bytes())
    if json.loads(volume_listing.read_text()) != listing:
        raise ValueError("the volume's manifest listing differs from the committed one")
    results = []
    for entry in listing:
        path = a.packets / f"{entry['name']}.json"
        used[f"volume:03_release_resolution/coding/packets/manifest/{entry['name']}.json"] = \
            hashlib.sha256(path.read_bytes()).hexdigest()
        results.append(check(entry, json.loads(path.read_text()), patterns, mapper, dictionary))
    out = {"script": "scripts/manifest_mapping_check_v2.py",
           "rule": "PREREG.md, §Study design, item 3 (H5); no model request",
           "accessions": len(results), "pass": sum(r["pass"] for r in results),
           "fail": sum(not r["pass"] for r in results), "h5_holds": all(r["pass"] for r in results),
           "failures": [r["row_id"] for r in results if not r["pass"]],
           "inputs_sha256": dict(sorted(used.items())), "results": results}
    first.write_once(a.out, out)
    print(json.dumps({k: v for k, v in out.items() if k not in ("results", "inputs_sha256")},
                     indent=1))


if __name__ == "__main__":
    main()
