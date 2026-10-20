import copy
import hashlib
import json
import pathlib

import pytest

import coding_runner as cr
import coding_runner_v3 as cr3
import recode_v1 as rc

HERE = pathlib.Path(__file__).resolve().parents[1]
V3 = (HERE / "prompts" / "coding_prompt_v3.md").read_text()
V2 = (HERE.parent / "03_release_resolution" / "prompts" / "coding_prompt_v2.md").read_text()
SCHEMA = json.loads((HERE.parent / "03_release_resolution" / "prompts" / "output_schema.json")
                    .read_text())
DEFS = "name,definition\nFinnGen R10,release 10\n"
STUDY = {"row_id": "000a", "side": "outcome", "name": "not stated",
         "outcomes_as_written": ["gout"], "candidates": ["FinnGen R10"]}
CONTROL = {"row_id": "000b", "side": "outcome", "name": "FinnGen R10",
           "outcomes_as_written": ["gout"], "candidates": ["FinnGen R10"]}
OLD = {"row_id": "000c", "side": "outcome", "name": "FinnGen R9",
       "outcomes_as_written": ["gout"], "candidates": ["FinnGen R9"]}


def packet(rid, rows):
    return {"record_id": rid, "title": "t", "rows": rows,
            "files": [{"file_id": "abstract", "kind": "abstract", "text": "x"}],
            "accession_table_rows": []}


PACKETS = {"r1.1": packet("r1", [STUDY, CONTROL]), "r2.1": packet("r2", [{**STUDY,
                                                                           "row_id": "000d"}])}


def sha(p):
    return hashlib.sha256(json.dumps(p, ensure_ascii=False).encode()).hexdigest()


def bodies(packets=PACKETS, prompt_text=V3, schema=SCHEMA):
    prompt = rc.fixed_prompt(prompt_text, DEFS)
    out = {}
    for m in cr.MODELS:
        runner = cr3.Runner(m, prompt, schema, pathlib.Path("/tmp/test_recode") / m, None)
        out[m] = [(n, runner.body(p)) for n, p in packets.items()]
    return out


def run(b, hashes=None, old=frozenset({"000c"}), drawn=frozenset({"000b"})):
    return rc.preflight(b, V3, DEFS, SCHEMA, hashes or {n: sha(p) for n, p in PACKETS.items()},
                        set(old), set(drawn))


def test_a_correct_set_of_bodies_passes_and_reports_from_the_bodies():
    got = run(bodies())
    assert got["requests_per_coder"] == {m: 2 for m in cr.MODELS}
    assert got["requests_total"] == 4
    assert set(got["embedded_coding_prompt_sha256"].values()) == {rc.V3_SHA256}
    assert got["rows"] == {"study": 2, "drawn_control": 1, "old_control": 0,
                           "packets_with_a_control_row": 1}
    assert got["gate"] == "coding_gate_v2.gate_row"


def test_the_v2_prompt_in_a_body_fails():
    with pytest.raises(rc.PreflightError, match="not v3"):
        run(bodies(prompt_text=V2))


def test_a_missing_body_fails():
    b = bodies()
    b[cr.SOL] = b[cr.SOL][:1]
    with pytest.raises(rc.PreflightError):
        run(b)


def test_a_packet_that_differs_from_its_listed_hash_fails():
    changed = copy.deepcopy(PACKETS)
    changed["r2.1"]["files"][0]["text"] = "y"
    with pytest.raises(rc.PreflightError, match="sha256"):
        run(bodies(changed))


def test_an_old_control_row_present_fails():
    changed = copy.deepcopy(PACKETS)
    changed["r2.1"]["rows"].append(OLD)
    with pytest.raises(rc.PreflightError, match="old control"):
        run(bodies(changed), {n: sha(p) for n, p in changed.items()})


def test_a_missing_drawn_control_fails():
    with pytest.raises(rc.PreflightError, match="drawn control"):
        run(bodies(), drawn={"000b", "0zzz"})


def test_a_packet_of_control_rows_only_or_a_marked_row_fails():
    alone = {"r1.1": packet("r1", [CONTROL]), "r2.1": PACKETS["r2.1"]}
    with pytest.raises(rc.PreflightError, match="without study rows"):
        run(bodies(alone), {n: sha(p) for n, p in alone.items()})
    marked = {"r1.1": packet("r1", [STUDY, {**CONTROL, "kind": "control"}]),
              "r2.1": PACKETS["r2.1"]}
    with pytest.raises(rc.PreflightError, match="marks it"):
        run(bodies(marked), {n: sha(p) for n, p in marked.items()})


def test_a_different_schema_fails():
    other = copy.deepcopy(SCHEMA)
    other["required"] = list(other["required"])[:-1]
    with pytest.raises(rc.PreflightError, match="schema"):
        run(bodies(schema=other))


def test_full_text_files_carry_the_route_of_their_source():
    p = {"record_id": "r", "files": [
        {"file_id": "abstract", "kind": "abstract", "text": "a"},
        {"file_id": "full_text_1", "kind": "full_text", "text": "R3 text"}]}
    sources = [{"route": "R1", "text": None}, {"route": "R3", "type": "PDF", "text": "R3 text"}]
    got = rc.frozen_files(p, sources)
    assert got["full_text_1"]["route"] == "R3" and "route" not in got["abstract"]
    with pytest.raises(rc.PreflightError):
        rc.frozen_files(p, [{"route": "R1", "text": "other"}])


def test_c1_by_type_splits_the_controls_and_counts_the_inline_rule():
    expected = {"c1": "A", "c2": "B", "c3": "C"}
    kinds = {"c1": "release", "c2": "accession", "c3": "source_identifier"}
    answers = {m: {"c1": {"identified_releases": ["A"]}, "c2": {"identified_releases": []},
                   "c3": {"identified_releases": ["C"]}} for m in cr.MODELS}
    verdicts = {m: {"c1": True, "c2": True, "c3": True} for m in cr.MODELS}
    bases = {m: {"c1": {"A": "D1:identifier"}, "c3": {"C": "D2:inline:pmid"}} for m in cr.MODELS}
    got = rc.c1_by_type(expected, kinds, answers, verdicts, bases)
    assert got["overall"]["both_models"]["counts"] == {"not_recovered_by_both": 1,
                                                       "recovered": 2}
    assert got["release"]["both_models"]["controls"] == 1
    assert got["recovered_through_the_inline_d2_rule"] == {m: 1 for m in cr.MODELS}
