# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml==6.0.3"]
# ///
"""Check of the mapping software on the manifest accessions (DEVIATION_02_c1_controls.md, item
3). No model is called. The gate's own mapping functions (scripts/coding_gate.py, sealed, imported
unchanged) are run on each of the 31 manifest accessions, which must return the expected
dictionary row. Run locally on the volume's manifest packets, copied by `modal volume get` from
/03_release_resolution/coding/packets/manifest/:

    PYTHONPATH=scripts:../02_claims_meta/scripts uv run --no-project --with pyyaml==6.0.3 \\
        python scripts/manifest_mapping_check_v1.py --packets <copy> --out <json>

For each accession of outputs/c1_manifest_controls_2026-10-13.json:

1. `identifier`: coding_gate.identifiers_mapping on the accession alone returns exactly the
   expected row;
2. `packet_file`: coding_gate.identifiers_mapping on the text of the packet's one file (the
   accession table's line for the accession, under its header) returns exactly the expected row;
3. `gate_row`: coding_gate.gate_row passes an answer that identifies the expected row with one D1
   passage quoting that line: the expected row is a dictionary row of the packet row's side, the
   quote stands in the packet file and the frozen file, and the identifier in it maps to exactly
   the coded row.

An accession passes when all three hold.
"""

import argparse
import csv
import hashlib
import json
import pathlib

import coding_gate as gate
import source_scanner_v2 as scanner

REPO_INPUTS = {"patterns": "reference/c1_scanner_patterns_v2.json",
               "accessions": "reference/accession_releases.csv",
               "dictionary": "../02_claims_meta/dataset_dictionary.csv",
               "listing": "outputs/c1_manifest_controls_2026-10-13.json",
               "gate": "scripts/coding_gate.py",
               "scanner": "scripts/source_scanner_v2.py"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
    return {"row_id": entry["row_id"], "identifier": entry["identifier"],
            "side": row["side"], "expected_row": expected,
            "returned_row_identifier": by_identifier, "returned_row_packet_file": by_file,
            "gate_row_passes": verdict["passes"],
            "gate_row_failures": verdict["releases"][expected]["failures"],
            "identifier_in_packet_line": entry["identifier"] in line,
            "checks": checks, "pass": all(checks.values())}


def write_once(path: pathlib.Path, data) -> None:
    if path.exists():
        raise FileExistsError(f"{path} exists; it is written once")
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--packets", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise FileExistsError(f"{a.out} exists; it is written once")
    used = {p: sha256_bytes(pathlib.Path(p).read_bytes()) for p in REPO_INPUTS.values()}
    patterns = json.loads(pathlib.Path(REPO_INPUTS["patterns"]).read_text())
    with open(REPO_INPUTS["accessions"], newline="") as fh:
        table = list(csv.DictReader(fh))
    dictionary = gate.dictionary_rows(REPO_INPUTS["dictionary"])
    mapper = scanner.Mapper(patterns, table, list(dictionary.values()))
    listing = json.loads(pathlib.Path(REPO_INPUTS["listing"]).read_text())["listing"]
    volume_listing = a.packets / "manifest.json"
    used["volume:coding/packets/manifest/manifest.json"] = sha256_bytes(volume_listing.read_bytes())
    if json.loads(volume_listing.read_text()) != listing:
        raise ValueError("the volume's manifest listing differs from the committed one")
    results = []
    for entry in listing:
        path = a.packets / f"{entry['name']}.json"
        used[f"volume:coding/packets/manifest/{entry['name']}.json"] = sha256_bytes(
            path.read_bytes())
        results.append(check(entry, json.loads(path.read_text()), patterns, mapper, dictionary))
    out = {"script": "scripts/manifest_mapping_check_v1.py",
           "rule": "DEVIATION_02_c1_controls.md, item 3; no model request",
           "accessions": len(results), "pass": sum(r["pass"] for r in results),
           "fail": sum(not r["pass"] for r in results),
           "failures": [r["row_id"] for r in results if not r["pass"]],
           "inputs_sha256": dict(sorted(used.items())), "results": results}
    write_once(a.out, out)
    print(json.dumps({k: v for k, v in out.items() if k not in ("results", "inputs_sha256")},
                     indent=1))


if __name__ == "__main__":
    main()
