# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml==6.0.3"]
# ///
"""Diagnostic of the C1 controls of stage A (outputs/stage_a_counts_2026-10-14.json), after
counting and before any judge request on stage A; it changes no count and no verdict. No model is
called. Run locally on the volume's files, copied by `modal volume get` from
/03_release_resolution/coding/ (packets/stage_a, packets/manifest, answers/stage_a,
answers/manifest, gate/<stage>/<model>/rows.json, c1a/control_set.json):

    PYTHONPATH=scripts:../02_claims_meta/scripts uv run --no-project --with pyyaml==6.0.3 \\
        python scripts/stage_a_control_diagnostic_v1.py --data <copy> --out <json> \\
        --contexts outputs/raw/<json>

For every C1-A control row and every manifest control:

1. Presence. Whether the identifier as the source writes it (the control's `name_as_written`;
   for a manifest control, its identifier) stands in a file of the packet the coder was given,
   after the normalization of Amendment 1 (manual_coding_passages.normalize: NFKC, dashes unified,
   case folded, whitespace collapsed); per file, the count and the first offset in the normalized
   text. Also, per file, the number of the frozen scanner's matches (source_scanner_v2.
   unit_matches, every line, no context term) that map to the expected row. A locating context of
   at most 200 normalized characters around each first occurrence goes to `--contexts` only, a
   path under the ignored outputs/raw/.
2. Source. Whether the source the control was drawn from (its `control_source_key`, whose last
   part is the first 16 hex digits of the sha256 of the source's text) is a file of the packet,
   and whether the identifier stands in the control's line of that file.
3. Per model, from the stored accepted answer and the stored gate verdict: the outcome as
   stage_a_counts_v1.outcome scores it; the identified releases, attribution state and unresolved
   reasons; the gate errors, recomputed by coding_gate.gate_row (sealed, unchanged) and checked
   against the stored verdict; for each decisive passage of the expected row, whether its quote
   stands in its file verbatim and after normalization, whether it holds the identifier, and for
   a reference entry whether it holds a DOI, PMID or PMC id (`gate_causes` names the mechanical
   cause of a class c failure); and whether another row of the same packet and side holds the
   expected row among its identified releases.
4. Class of each control a model does not recover:
     a  identifier absent from the packet (neither the identifier as written nor any scanner
        match to the expected row in any file): the control cannot be passed from stage A inputs;
     b  identifier present, the coder identified no release;
     c  identifier present, the coder coded exactly the expected row and the gate failed;
     d  anything else (another row, or a missing answer).
"""

import argparse
import collections
import csv
import hashlib
import json
import pathlib

import coding_gate as gate
import manual_coding_passages as mp
import source_scanner_v2 as scanner
import stage_a_counts_v1 as sc

MODELS = ("claude-sonnet-5-5", "gpt-6.1-sol")
CONTEXT = 200
CLASSES = {
    "a": "identifier absent from the packet: the control cannot be passed from stage A inputs",
    "b": "identifier present in the packet, the coder identified no release",
    "c": "identifier present, the coder coded exactly the expected row and the gate failed",
    "d": "other: another row, or no accepted answer"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def occurrences(identifier: str, files: list[dict]) -> list[dict]:
    """Each packet file holding the normalized identifier: its count and first offset in the
    normalized text, and a context of at most CONTEXT normalized characters."""
    needle = mp.normalize(identifier)
    out = []
    for f in files:
        hay = mp.normalize(f["text"])
        first = hay.find(needle)
        if first < 0:
            continue
        lo = max(0, first - (CONTEXT - len(needle)) // 2)
        out.append({"file_id": f["file_id"], "kind": f["kind"], "count": hay.count(needle),
                    "first_offset_normalized": first,
                    "context": hay[lo:lo + max(CONTEXT, len(needle))][:CONTEXT]})
    return out


def scanner_hits(expected: str, files: list[dict], patterns: dict,
                 mapper: scanner.Mapper) -> dict[str, int]:
    out = {}
    for f in files:
        n = 0
        for i, line in enumerate(f["text"].split("\n")):
            unit = {"record_id": "", "source_key": "", "unit_id": str(i), "text": line}
            n += sum(m["expected_row"] == expected
                     for m in scanner.unit_matches(unit, patterns, mapper))
        if n:
            out[f["file_id"]] = n
    return out


def source_in_packet(source_key: str, unit_id: str, identifier: str,
                     files: list[dict]) -> dict:
    digest = source_key.split(":")[2]
    for f in files:
        if sha256_bytes(f["text"].encode())[:16] == digest:
            line = f["text"].split("\n")[int(unit_id.split(":")[3])]
            return {"in_packet": True, "file_id": f["file_id"],
                    "identifier_in_control_line": mp.normalize(identifier) in mp.normalize(line)}
    return {"in_packet": False, "file_id": None, "identifier_in_control_line": None}


def classify(present: bool, outcome: str) -> str | None:
    if outcome == "recovered":
        return None
    if not present:
        return "a"
    if outcome == "empty":
        return "b"
    if outcome == "expected_gate_failed":
        return "c"
    return "d"


def gate_errors(verdict: dict) -> list[str]:
    errors = []
    for rel in verdict["releases"].values():
        for fl in rel["failures"]:
            errors += fl["errors"] if isinstance(fl, dict) else [fl]
    return sorted(set(errors))


def passage_checks(row: dict, expected: str, identifier: str, files: list[dict],
                   terminal: str) -> list[dict]:
    """For each decisive passage of the expected row: whether its quote stands verbatim in the
    file it names, whether it stands there after normalization, whether it holds the control's
    identifier (normalized), and, for a reference entry, whether it holds a DOI, PMID or PMC id."""
    texts = {f["file_id"]: f["text"] for f in files}
    out = []
    for e in row["decisive_evidence"]:
        if e["release"] != expected:
            continue
        text = texts.get(e["file_id"], "")
        check = {"rule": e["rule"], "file_id": e["file_id"],
                 "verbatim_in_file": e["quote"] in text,
                 "in_file_after_normalization": mp.normalize(e["quote"]) in mp.normalize(text),
                 "holds_the_identifier": mp.normalize(identifier) in mp.normalize(e["quote"])}
        if e["rule"] == "D2_reference_entry":
            check["holds_a_stable_identifier"] = bool(gate.reference_identifiers(e["quote"],
                                                                                 terminal))
        out.append(check)
    return out


def model_view(row: dict | None, expected: str, stored_pass: bool | None, packet: dict,
               side: str, answers: dict[str, dict], refs: tuple, identifier: str) -> dict:
    outcome = sc.outcome(expected, row, stored_pass)
    if row is None:
        return {"outcome": outcome}
    frozen = {f["file_id"]: {"key": f["file_id"], "sha256": "", "text": f["text"]}
              for f in packet["files"]}
    sides = {r["row_id"]: r["side"] for r in packet["rows"]}
    verdict = gate.gate_row(row, sides[row["row_id"]], packet, frozen, *refs)
    others = [r["row_id"] for r in packet["rows"]
              if r["row_id"] != row["row_id"] and r["side"] == side
              and expected in answers.get(r["row_id"], {}).get("identified_releases", [])]
    return {"outcome": outcome, "identified_releases": row["identified_releases"],
            "attribution_state": row["attribution_state"],
            "unresolved_reasons": row["unresolved_reasons"],
            "decisive_evidence_rules": [e["rule"] for e in row["decisive_evidence"]],
            "gate_passes_stored": stored_pass, "gate_passes_recomputed": verdict["passes"],
            "gate_errors": gate_errors(verdict),
            "passages_of_the_expected_row": passage_checks(
                row, expected, identifier, packet["files"], refs[0]["doi_terminal_characters"]),
            "expected_row_on_another_row_of_the_packet": others}


def load_stage(data: pathlib.Path, stage: str, used: dict) -> tuple[dict, dict, dict]:
    """Packets by row id; per model, accepted answer rows by row id and stored gate verdicts."""
    folder = data / "packets" / stage
    manifest = folder / "manifest.json"
    used[f"volume:coding/packets/{stage}/manifest.json"] = sha256_bytes(manifest.read_bytes())
    by_row = {}
    for m in json.loads(manifest.read_text()):
        path = folder / f"{m['name']}.json"
        packet = json.loads(path.read_text())
        packet["_path"] = f"volume:coding/packets/{stage}/{m['name']}.json"
        packet["_sha256"] = sha256_bytes(path.read_bytes())
        for r in packet["rows"]:
            by_row[r["row_id"]] = packet
    answers, verdicts = {}, {}
    for model in MODELS:
        answers[model] = {}
        for p in sorted((data / "answers" / stage / model).glob("*.json")):
            if ".attempt" in p.name:
                continue
            final = json.loads(p.read_text())
            if final["state"] != "accepted":
                continue
            for row in final["answer"]["rows"]:
                answers[model][row["row_id"]] = row | {"_file": p.name,
                                                       "_sha256": sha256_bytes(p.read_bytes())}
        rows = data / "gate" / stage / model / "rows.json"
        used[f"volume:coding/gate/{stage}/{model}/rows.json"] = sha256_bytes(rows.read_bytes())
        verdicts[model] = json.loads(rows.read_text())
    return by_row, answers, verdicts


def diagnose(controls: list[dict], by_row: dict, answers: dict, verdicts: dict, refs: tuple,
             stage: str, used: dict, contexts: dict) -> list[dict]:
    patterns, mapper = refs[0], refs[1]
    out = []
    for c in controls:
        packet = by_row[c["row_id"]]
        used[packet["_path"]] = packet["_sha256"]
        files = packet["files"]
        occ = occurrences(c["identifier"], files)
        hits = scanner_hits(c["expected_row"], files, patterns, mapper)
        present = bool(occ) or bool(hits)
        entry = {k: c[k] for k in ("row_id", "record_id", "side", "identifier", "expected_row")}
        entry |= {"kind": c.get("kind"), "type": c.get("type"),
                  "packet": packet["_path"].removeprefix(f"volume:coding/packets/{stage}/"),
                  "packet_files": [{"file_id": f["file_id"], "kind": f["kind"],
                                    "sha256_16": sha256_bytes(f["text"].encode())[:16]}
                                   for f in files],
                  "identifier_as_written_present": bool(occ),
                  "identifier_occurrences": [{k: o[k] for k in o if k != "context"} for o in occ],
                  "scanner_matches_to_expected_row": hits,
                  "identifier_present": present}
        if "control_source_key" in c:
            entry["control_source_key"] = c["control_source_key"]
            entry["control_unit_id"] = c["control_unit_id"]
            entry["control_source"] = source_in_packet(c["control_source_key"],
                                                       c["control_unit_id"], c["identifier"], files)
        contexts[c["row_id"]] = [{"file_id": o["file_id"], "context": o["context"]} for o in occ]
        entry["models"] = {}
        for model in MODELS:
            row = answers[model].get(c["row_id"])
            if row is not None:
                used[f"volume:coding/answers/{stage}/{model}/{row['_file']}"] = row["_sha256"]
            view = model_view(row, c["expected_row"], verdicts[model].get(c["row_id"]), packet,
                              c["side"], answers[model], refs, c["identifier"])
            view["class"] = classify(present, view["outcome"])
            view["gate_causes"] = gate_causes(view) if view["class"] == "c" else []
            entry["models"][model] = view
        entry["recovered_by_both"] = all(entry["models"][m]["outcome"] == "recovered"
                                         for m in MODELS)
        out.append(entry)
    return out


def gate_causes(view: dict) -> list[str]:
    """The mechanical causes of a class c failure, from the passages of the expected row:
    `quote_differs_only_after_normalization` (a quote that is not verbatim in its file but stands
    there after normalization), `quote_not_in_file_even_after_normalization`,
    `d2_identifier_inline_not_in_a_reference_entry` (a D2 passage
    holds the control's identifier and no reference entry holds a DOI, PMID or PMC id)."""
    checks = view.get("passages_of_the_expected_row", [])
    out = []
    if any(not c["verbatim_in_file"] and c["in_file_after_normalization"] for c in checks):
        out.append("quote_differs_only_after_normalization")
    if any(not c["in_file_after_normalization"] for c in checks):
        out.append("quote_not_in_file_even_after_normalization")
    if (any(c["rule"] == "D2" and c["holds_the_identifier"] for c in checks)
            and not any(c.get("holds_a_stable_identifier") for c in checks)):
        out.append("d2_identifier_inline_not_in_a_reference_entry")
    return out


def summarize(entries: list[dict]) -> dict:
    per_model = {}
    for m in MODELS:
        classes = collections.Counter(e["models"][m]["class"] for e in entries
                                      if e["models"][m]["class"])
        errors = collections.Counter(err for e in entries if e["models"][m]["class"] == "c"
                                     for err in e["models"][m]["gate_errors"])
        reasons = collections.Counter(
            "+".join(sorted(e["models"][m]["unresolved_reasons"])) or "none"
            for e in entries if e["models"][m]["class"] == "b")
        states = collections.Counter(e["models"][m]["attribution_state"] for e in entries
                                     if e["models"][m]["class"] == "b")
        per_model[m] = {
            "recovered": sorted(e["row_id"] for e in entries
                                if e["models"][m]["outcome"] == "recovered"),
            "not_recovered": sum(1 for e in entries if e["models"][m]["class"]),
            "recovered_by_side": {s: f"{sum(e['models'][m]['outcome'] == 'recovered' for e in entries if e['side'] == s)}"
                                     f" of {sum(e['side'] == s for e in entries)}"
                                  for s in sorted({e["side"] for e in entries})},
            "class_counts": {k: classes.get(k, 0) for k in CLASSES},
            "class_c_gate_errors": dict(errors),
            "class_c_causes": dict(collections.Counter(
                cause for e in entries if e["models"][m]["class"] == "c"
                for cause in e["models"][m]["gate_causes"])),
            "class_b_unresolved_reasons": dict(reasons),
            "class_b_attribution_state": dict(states),
            "gate_stored_and_recomputed_disagree": sorted(
                e["row_id"] for e in entries
                if "gate_passes_recomputed" in e["models"][m]
                and e["models"][m]["identified_releases"]
                and e["models"][m]["gate_passes_stored"] != e["models"][m]["gate_passes_recomputed"]),
            "misses_with_expected_row_on_another_row_of_the_packet": sorted(
                e["row_id"] for e in entries if e["models"][m]["class"]
                and e["models"][m].get("expected_row_on_another_row_of_the_packet"))}
    a, b = MODELS
    rec = {m: set(per_model[m]["recovered"]) for m in MODELS}
    joint = [e for e in entries if not e["recovered_by_both"]]
    pair = collections.Counter(f"{e['models'][a]['class'] or 'recovered'}|"
                               f"{e['models'][b]['class'] or 'recovered'}" for e in joint)
    return {"controls": len(entries), "per_model": per_model,
            "recovered_by_both": sorted(rec[a] & rec[b]),
            "recovered_by_one_only": {a: sorted(rec[a] - rec[b]), b: sorted(rec[b] - rec[a])},
            "not_recovered_by_both": len(joint),
            "not_recovered_by_both_class_pairs": dict(pair),
            "not_recovered_by_both_identifier_absent": sorted(
                e["row_id"] for e in joint if not e["identifier_present"]),
            "not_recovered_by_both_rows": [
                {"row_id": e["row_id"], "identifier": e["identifier"],
                 "expected_row": e["expected_row"],
                 "classes": {m: e["models"][m]["class"] or "recovered" for m in MODELS}}
                for e in joint]}


def write_once(path: pathlib.Path, data) -> None:
    if path.exists():
        raise FileExistsError(f"{path} exists; it is written once")
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--contexts", type=pathlib.Path, required=True)
    a = ap.parse_args()
    for path in (a.out, a.contexts):
        if path.exists():
            raise FileExistsError(f"{path} exists; it is written once")
    repo = {"patterns": "reference/c1_scanner_patterns_v2.json",
            "accessions": "reference/accession_releases.csv",
            "dictionary": "../02_claims_meta/dataset_dictionary.csv",
            "manifest_listing": "outputs/c1_manifest_controls_2026-10-13.json",
            "counts": "outputs/stage_a_counts_2026-10-14.json"}
    used = {p: sha256_bytes(pathlib.Path(p).read_bytes()) for p in repo.values()}
    patterns = json.loads(pathlib.Path(repo["patterns"]).read_text())
    with open(repo["accessions"], newline="") as fh:
        table = list(csv.DictReader(fh))
    dictionary = gate.dictionary_rows(repo["dictionary"])
    refs = (patterns, scanner.Mapper(patterns, table, list(dictionary.values())), dictionary)

    control_set = a.data / "c1a" / "control_set.json"
    used["volume:coding/c1a/control_set.json"] = sha256_bytes(control_set.read_bytes())
    cs = json.loads(control_set.read_text())
    drawn = {(d["record_id"], d["unit_id"], d["identifier"]): d for d in cs["drawn_controls"]}
    c1a = [r | {"identifier": r["name_as_written"],
                "kind": drawn[(r["record_id"], r["control_unit_id"], r["name_as_written"])]["kind"],
                "type": drawn[(r["record_id"], r["control_unit_id"], r["name_as_written"])]["type"]}
           for r in cs["control_rows"]]
    listing = json.loads(pathlib.Path(repo["manifest_listing"]).read_text())["listing"]
    manifest = [{"row_id": m["row_id"], "record_id": m["record_id"], "identifier": m["identifier"],
                 "expected_row": m["expected_row"], "side": dictionary[m["expected_row"]]["side"],
                 "type": "opengwas" if m["identifier"].startswith("ieu-") else "gwas_catalog"}
                for m in listing]

    contexts = {}
    sections = {}
    for stage, controls in (("stage_a", c1a), ("manifest", manifest)):
        by_row, answers, verdicts = load_stage(a.data, stage, used)
        entries = diagnose(controls, by_row, answers, verdicts, refs, stage, used, contexts)
        sections[stage] = {"summary": summarize(entries), "controls": entries}

    counts = json.loads(pathlib.Path(repo["counts"]).read_text())
    check = {}
    for stage, key in (("stage_a", "c1a_source_scanned"), ("manifest", "c1_manifest")):
        s = sections[stage]["summary"]
        check[stage] = {m: len(s["per_model"][m]["recovered"]) == counts[key][m]["counts"]["recovered"]
                        for m in MODELS}
        check[stage]["both"] = len(s["recovered_by_both"]) == counts[key]["both_models"]["counts"]["recovered"]
    out = {"script": "scripts/stage_a_control_diagnostic_v1.py",
           "diagnostic_only": "changes no count or verdict of outputs/stage_a_counts_2026-10-14.json; "
                              "no model request; run before any judge request on stage A",
           "normalization": "manual_coding_passages.normalize (NFKC, dashes unified, case folded, "
                            "whitespace collapsed)",
           "classes": CLASSES,
           "recovered_counts_match_the_counts_file": check,
           "inputs_sha256": dict(sorted(used.items())),
           "c1a": sections["stage_a"], "manifest": sections["manifest"]}
    a.contexts.parent.mkdir(parents=True, exist_ok=True)
    write_once(a.out, out)
    write_once(a.contexts, {"note": "third-party text; ignored location, never committed",
                            "contexts": contexts})
    print(json.dumps({s: {"class_counts": {m: v["summary"]["per_model"][m]["class_counts"]
                                           for m in MODELS},
                          "recovered_by_both": len(v["summary"]["recovered_by_both"])}
                      for s, v in sections.items()} | {"check": check}, indent=1))


if __name__ == "__main__":
    main()
