# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml==6.0.3"]
# ///
"""Second version of the provenance and identifier gate (the first registration's
scripts/coding_gate.py, sealed, imported unchanged), for the second release-resolution
registration (PREREG.md, §Study design, item 2: inline source identifiers under D2, primary
rule). No model is called.

Every condition of the first gate holds. One addition: D2 also passes a passage, of rule `D2`,
that writes a DOI or PMID in the paper's own text with no reference entry, when (1) the quote
stands verbatim in the packet file and in its frozen file (`coding_gate.check_passage`); (2) the
quote holds a DOI, else a PMID (`coding_gate.reference_identifiers`, the PMC identifier not used);
(3) the quote stands outside a reference list as c1_controls.units marks it (`outside_reference_
list`: the lines c1_controls.units puts in a reference list are removed from the frozen file's
text, and the quote must stand in what is left; units mark a reference list only in files of
routes R2 and R3, so a frozen file with no `route`, such as the abstract or a rendered R1 body,
holds none); and (4) Paper 1's reference check (manual_coding_gates_v2.reference_check, sealed)
verifies the identifier against the coded row's `source_identifier`. Its basis is
`D2:inline:<doi|pmid>`. Attribution is not checked here.

`gate_row` runs the first gate and, for each release the first gate does not pass, tries the
inline rule on that release's D2 passages; D1 and reference-entry results are those of the first
gate, unchanged. `identifiers_mapping` is the first gate's.
"""

import hashlib

import c1_controls as c1
import coding_gate as gate
import manual_coding_gates_v2 as g2
import source_scanner_v2 as scanner

identifiers_mapping = gate.identifiers_mapping
dictionary_rows = gate.dictionary_rows


def outside_reference_list(quote: str, source: dict) -> bool:
    route = source.get("route")
    text = source["text"]
    if route not in ("R2", "R3"):
        return quote in text
    units = c1.units("", [{"route": route, "text": text, "type": source.get("type", "")}])
    in_refs = {int(u["unit_id"].split(":")[3]) for u in units if u["in_reference_list"]}
    kept = "\n".join(line for i, line in enumerate(text.split("\n")) if i not in in_refs)
    return quote in kept


def inline_d2(e: dict, release_row: dict, packet_texts: dict[str, str], frozen: dict[str, dict],
              terminal: str) -> tuple[str | None, list[str]]:
    errors = gate.check_passage(e, packet_texts, frozen)
    found = {k: v for k, v in gate.reference_identifiers(e["quote"], terminal).items()
             if k in ("doi", "pmid")}
    if not found:
        errors.append("inline:no_doi_or_pmid_in_quote")
    elif not outside_reference_list(e["quote"], frozen[e["file_id"]]):
        errors.append("inline:quote_in_a_reference_list")
    else:
        how, failure = g2.reference_check(found, release_row["source_identifier"])
        if failure:
            errors.append(f"inline:{failure}")
        elif not errors:
            return f"D2:inline:{how}", []
    return None, errors


def gate_row(row: dict, side: str, packet: dict, frozen: dict[str, dict], patterns: dict,
             mapper: scanner.Mapper, dictionary: dict[str, dict]) -> dict:
    out = gate.gate_row(row, side, packet, frozen, patterns, mapper, dictionary)
    texts = {f["file_id"]: f["text"] for f in packet["files"]}
    for release, result in out["releases"].items():
        if result["passes"] or release not in dictionary or dictionary[release]["side"] != side:
            continue
        for e in row["decisive_evidence"]:
            if e["release"] != release or e["rule"] != "D2":
                continue
            basis, errors = inline_d2(e, dictionary[release], texts, frozen,
                                      patterns["doi_terminal_characters"])
            if basis:
                result.update({"passes": True, "basis": basis})
                out["to_pin"].append({"file_id": e["file_id"], "quote": e["quote"]})
                break
            result["failures"].append({
                "quote_sha256": hashlib.sha256(e["quote"].encode()).hexdigest()[:16],
                "errors": sorted(set(errors))})
    out["passes"] = all(r["passes"] for r in out["releases"].values())
    return out
