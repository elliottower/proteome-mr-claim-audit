# /// script
# requires-python = ">=3.12"
# dependencies = ["anthropic==1.13.0", "httpx==0.28.1", "jsonschema==4.26.0", "pyyaml==6.0.3"]
# ///
"""Stage A recode of the second release-resolution registration (PREREG.md, §Study design,
item 4): both coders (claude-sonnet-5-5, gpt-6.1-sol) code every packet of item 1 from scratch
under coding prompt v3 and the gate of item 2. No model is called here; the Modal wrapper
(scripts/modal_recode_v1.py) sends the requests through the first registration's
scripts/coding_runner_v3.py (sealed, unchanged).

Fixed prompt (`fixed_prompt`): coding_packets.fixed_prompt over prompts/coding_prompt_v3.md and
Paper 1's dictionary definitions; schema prompts/output_schema.json; framing
prompts/api_framing_v2.md as the runner implements it (coding_runner.claude_body, sol_body).

Preflight (`preflight`): every request body is built offline with the runner's own `body`, and
the checks are read from the bodies themselves: the count per coder equals the packets; the
coding prompt each body embeds (the text before the dictionary-definitions line) has the v3
sha256 and the definitions after it are the definitions file; the schema each body carries is the
schema file; the packet each body carries, as the JSON text sent, has the sha256 the packets
output lists; the first registration's 70 control rows are in no body and the 69 drawn control
rows each stand in exactly one body, among study rows, with nothing marking them. Any failed
check raises PreflightError.

Gate (`gate_answers`): coding_gate_v2.gate_row on every accepted answer, the frozen file of each
packet file being its own text with, for a full text, the route of the retrieved source it came
from (`frozen_files`), so the inline rule can see a reference list.

C1 (`c1_by_type`): stage_a_counts_v1.c1_scores on the 69 drawn controls, overall (minimum 50)
and by identifier type (numbered release; accession; source identifier, DOI or PMID); and, per
model, the controls recovered through the inline D2 rule.
"""

import hashlib
import json

import coding_gate_v2 as gate2
import coding_packets as cp
import coding_runner as cr
import stage_a_counts_v1 as sc

DEFINITIONS_LINE = "\n\n## Dictionary definitions\n\n"
V3_SHA256 = "08109b4911ffe6dcd425bf09e8164c19b65da537fcf037ff389d5a722e93afb0"
GATE = gate2.gate_row
KINDS = ("release", "accession", "source_identifier")


class PreflightError(Exception):
    """A request body differs from what the registration and its frozen inputs fix."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fixed_prompt(v3: str, definitions: str) -> str:
    return cp.fixed_prompt(v3, definitions)


def embedded(model: str, body: dict) -> tuple[str, dict, str]:
    """(fixed prompt, schema, packet JSON text) as the body carries them."""
    if model == cr.CLAUDE:
        return (body["system"][0]["text"], body["output_config"]["format"]["schema"],
                body["messages"][0]["content"])
    return body["instructions"], body["text"]["format"]["schema"], body["input"]


def preflight(bodies: dict[str, list[tuple[str, dict]]], v3_text: str, definitions: str,
              schema: dict, packet_sha256: dict[str, str], old_controls: set[str],
              drawn_controls: set[str]) -> dict:
    out = {"requests_per_coder": {}, "embedded_coding_prompt_sha256": {},
           "embedded_definitions_sha256": {}, "embedded_schema_sha256": {}}
    schema_hash = sha256(json.dumps(schema, sort_keys=True).encode())
    for model, items in bodies.items():
        if len(items) != len(packet_sha256):
            raise PreflightError(f"{model}: {len(items)} bodies for {len(packet_sha256)} packets")
        prompts, defs, schemas, seen = set(), set(), set(), {}
        for name, body in items:
            prompt, sch, text = embedded(model, body)
            if DEFINITIONS_LINE not in prompt:
                raise PreflightError(f"{model} {name}: no dictionary-definitions line")
            coding, defn = prompt.split(DEFINITIONS_LINE, 1)
            prompts.add(sha256((coding + "\n").encode()))
            defs.add(sha256(defn.encode()))
            schemas.add(sha256(json.dumps(sch, sort_keys=True).encode()))
            if sha256(text.encode()) != packet_sha256.get(name):
                raise PreflightError(f"{model} {name}: packet sha256 differs from the output")
            seen[name] = json.loads(text)
        if prompts != {V3_SHA256} or sha256(v3_text.encode()) != V3_SHA256:
            raise PreflightError(f"{model}: embedded coding prompt is not v3: {sorted(prompts)}")
        if defs != {sha256(definitions.encode())}:
            raise PreflightError(f"{model}: embedded definitions differ from the file")
        if schemas != {schema_hash}:
            raise PreflightError(f"{model}: embedded schema differs from the file")
        if set(seen) != set(packet_sha256):
            raise PreflightError(f"{model}: bodies do not cover the packets")
        rows = [(n, r) for n, p in seen.items() for r in p["rows"]]
        ids = [r["row_id"] for _, r in rows]
        if len(ids) != len(set(ids)):
            raise PreflightError(f"{model}: a row stands in two bodies")
        if old_controls & set(ids):
            raise PreflightError(f"{model}: an old control row is present")
        if not drawn_controls <= set(ids):
            raise PreflightError(f"{model}: a drawn control row is missing")
        for n, p in seen.items():
            pids = [r["row_id"] for r in p["rows"]]
            if pids != sorted(pids):
                raise PreflightError(f"{model} {n}: rows not in order of row id")
            if set(pids) & drawn_controls and not set(pids) - drawn_controls:
                raise PreflightError(f"{model} {n}: control rows without study rows")
            if any(set(r) - {"row_id", "side", "name", "outcomes_as_written", "candidates"}
                   for r in p["rows"]):
                raise PreflightError(f"{model} {n}: a row carries a field that marks it")
        out["requests_per_coder"][model] = len(items)
        out["embedded_coding_prompt_sha256"][model] = sorted(prompts)[0]
        out["embedded_definitions_sha256"][model] = sorted(defs)[0]
        out["embedded_schema_sha256"][model] = sorted(schemas)[0]
        out.setdefault("rows", {"study": len(ids) - len(drawn_controls),
                                "drawn_control": len(drawn_controls & set(ids)),
                                "old_control": len(old_controls & set(ids)),
                                "packets_with_a_control_row": sum(
                                    bool({r["row_id"] for r in p["rows"]} & drawn_controls)
                                    for p in seen.values())})
    out["requests_total"] = sum(out["requests_per_coder"].values())
    out["gate"] = f"{GATE.__module__}.{GATE.__name__}"
    if out["gate"] != "coding_gate_v2.gate_row":
        raise PreflightError("the gate in use is not coding_gate_v2")
    return out


def frozen_files(packet: dict, sources: list[dict]) -> dict[str, dict]:
    full = [s for s in sources if s["route"] in ("R1", "R3") and s.get("text")]
    out = {}
    for f in packet["files"]:
        entry = {"key": f"{packet['record_id']}-{f['file_id']}", "sha256": cp.sha256(f["text"]),
                 "text": f["text"]}
        if f["kind"] == "full_text":
            src = full[int(f["file_id"].rsplit("_", 1)[1]) - 1]
            if src["text"] != f["text"]:
                raise PreflightError(f"{packet['record_id']} {f['file_id']}: not its source")
            entry |= {"route": src["route"], "type": src.get("type", "")}
        out[f["file_id"]] = entry
    return out


def gate_answers(packet: dict, answer_rows: list[dict], frozen: dict, patterns: dict, mapper,
                 dictionary: dict) -> dict[str, dict]:
    sides = {r["row_id"]: r["side"] for r in packet["rows"]}
    return {row["row_id"]: GATE(row, sides[row["row_id"]], packet, frozen, patterns, mapper,
                                dictionary) for row in answer_rows}


def c1_by_type(expected: dict[str, str], kinds: dict[str, str], answers: dict, verdicts: dict,
               bases: dict) -> dict:
    out = {"overall": sc.c1_scores(expected, answers, verdicts, sc.SOURCE_SCANNED_MINIMUM)}
    for k in KINDS:
        sub = {r: e for r, e in expected.items() if kinds[r] == k}
        out[k] = sc.c1_scores(sub, answers, verdicts, 0) if sub else {"controls": 0}
    out["recovered_through_the_inline_d2_rule"] = {
        m: sum(1 for r, e in expected.items()
               if sc.outcome(e, answers[m].get(r), verdicts[m].get(r)) == "recovered"
               and str(bases[m].get(r, {}).get(e, "")).startswith("D2:inline"))
        for m in answers}
    return out
