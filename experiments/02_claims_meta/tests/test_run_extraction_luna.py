import hashlib
import json
import threading

import pytest

import run_extraction as rx
import run_extraction_luna as lx

CLAIM = {"protein_as_written": "IL6R", "outcome_as_written": "coronary artery disease",
         "direction": "lowers", "evidence_type": "mr_estimate", "claim_scope": "overall",
         "analysis_context_as_written": "not_stated", "subgroup_as_written": "not_stated",
         "pqtl_datasets": ["not_stated"], "outcome_datasets": ["not_stated"],
         "dataset_attribution": "whole_study", "platform": ["not_stated"],
         "ancestry": "not_stated", "relation_ambiguous": False,
         "evidence_span": "Genetically predicted IL6R lowered risk of coronary artery disease."}
RECORD = rx.Record(pmid="111", title="A title", abstract="An abstract. " * 30)
SCHEMA = {"type": "object"}


def response(claims, model="gpt-6-luna-2026"):
    return json.dumps({
        "model": model, "temperature": 1.0,
        "output": [{"type": "reasoning"},
                   {"type": "message",
                    "content": [{"type": "output_text", "text": json.dumps({"claims": claims})}]}],
        "usage": {"input_tokens": 1000,
                  "input_tokens_details": {"cached_tokens": 600, "cache_write_tokens": 300},
                  "output_tokens": 200, "output_tokens_details": {"reasoning_tokens": 50}}})


class Reply:
    def __init__(self, status_code, text):
        self.status_code, self.text = status_code, text


class Client:
    def __init__(self, replies):
        self.replies, self.bodies = list(replies), []

    def post(self, url, json, headers):
        self.bodies.append(json)
        return self.replies.pop(0)


def run_one(client, tmp_path, run=1):
    usage = lx.Usage()
    row = lx.run_one(client, "key", "rev", run, "PROMPT", SCHEMA, RECORD, usage,
                     threading.Lock(), tmp_path / f"run{run}")
    return row, usage


@pytest.fixture()
def run_dirs(tmp_path):
    for run in lx.RUNS:
        (tmp_path / f"run{run}").mkdir()
    return tmp_path


def test_committed_luna_prompt_is_the_frozen_prompt_followed_by_the_addendum():
    frozen, luna = lx.FROZEN_PROMPT.read_text(), lx.LUNA_PROMPT.read_text()
    lx.check_prompt(luna, frozen)
    addendum = luna[len(frozen):]
    assert addendum.count("(added for this model)") == 1
    assert "Carried-over results." in addendum
    assert hashlib.sha256(frozen.encode()).hexdigest() == (
        "2a2bef3852f822eb64a19cdc6b880f8ba4f4cac7d262976f0016e517177a6049")
    assert hashlib.sha256(luna.encode()).hexdigest() == (
        "bf02041d287666f6104db8d756cbef3300ab50c8a9640c795b5cac39709b2f40")


def test_prompt_that_alters_or_only_repeats_the_frozen_prompt_is_refused():
    frozen = "Frozen rules.\n"
    lx.check_prompt(frozen + "\nAddendum.\n", frozen)
    with pytest.raises(lx.LunaRunError, match="frozen extraction prompt"):
        lx.check_prompt(frozen, frozen)
    with pytest.raises(lx.LunaRunError, match="frozen extraction prompt"):
        lx.check_prompt("Frozen rule.\n\nAddendum.\n", frozen)
    with pytest.raises(lx.LunaRunError, match="frozen extraction prompt"):
        lx.check_prompt("Preface.\n" + frozen + "Addendum.\n", frozen)


def test_request_is_the_study_request_with_another_model():
    sol = rx.request_body("extraction", "PROMPT", SCHEMA, RECORD)
    luna = lx.luna_body("PROMPT", SCHEMA, RECORD)
    assert luna["model"] == "gpt-6-luna"
    assert sol["model"] == "gpt-6.1-sol"
    assert {k: v for k, v in luna.items() if k != "model"} == {
        k: v for k, v in sol.items() if k != "model"}
    assert luna["reasoning"] == {"effort": "medium"}
    assert (luna["tools"], luna["store"]) == ([], False)


def test_revision_id_is_the_study_formula_with_the_luna_model(monkeypatch):
    luna = lx.luna_revision_id("PROMPT", SCHEMA)
    assert luna != rx.revision_id("extraction", "PROMPT", SCHEMA)
    assert luna != lx.luna_revision_id("PROMPT ", SCHEMA)
    monkeypatch.setattr(lx, "LUNA_MODEL", rx.MODEL)
    assert lx.luna_revision_id("PROMPT", SCHEMA) == rx.revision_id("extraction", "PROMPT", SCHEMA)


def test_revision_id_of_the_committed_prompt():
    schema = json.loads((rx.PROMPTS / "schema.json").read_text())["extraction"]
    assert lx.luna_revision_id(lx.LUNA_PROMPT.read_text(), schema) == "e4e4ee731887"


def test_run_is_refused_until_the_log_names_both_digests():
    a, p = "a" * 64, "b" * 64
    plan = "# Plan\n\nbody\n\n---\n\n## Log\n\n```text\n2026-10-03  frozen  nothing run\n"
    logged = plan + f"2026-10-07  amendment 01 sha256 {a}; Luna prompt sha256 {p}  nothing run\n"
    lx.require_logged(logged, a, p)
    with pytest.raises(lx.LunaRunError, match="the amendment file or of the Luna prompt"):
        lx.require_logged(plan, a, p)
    with pytest.raises(lx.LunaRunError, match="sha256 of the Luna prompt"):
        lx.require_logged(plan + f"2026-10-07  amendment 01 sha256 {a}\n", a, p)
    with pytest.raises(lx.LunaRunError, match="sha256 of the amendment file"):
        lx.require_logged(plan + f"2026-10-07  Luna prompt sha256 {p}\n", a, p)
    above_the_log = f"# Plan\n\n{a} {p}\n\n---\n\n## Log\n\n```text\n2026-10-03  frozen\n"
    with pytest.raises(lx.LunaRunError):
        lx.require_logged(above_the_log, a, p)
    with pytest.raises(lx.LunaRunError, match="no log"):
        lx.require_logged(f"# Plan\n\n{a} {p}\n", a, p)


def test_luna_extracts_exactly_the_records_sol_extracted():
    sol = [{"pmid": "1", "status": "ok"}, {"pmid": "2", "status": "extraction_failed"}]
    lx.check_same_records(["2", "1"], sol)
    with pytest.raises(lx.LunaRunError, match="1 records only here"):
        lx.check_same_records(["1", "2", "3"], sol)
    with pytest.raises(lx.LunaRunError, match="1 only in Sol's"):
        lx.check_same_records(["1"], sol)
    with pytest.raises(lx.LunaRunError, match="occurs twice"):
        lx.check_same_records(["1", "1"], sol)
    with pytest.raises(lx.LunaRunError):
        lx.check_same_records(["1", "2"], sol + [{"pmid": "2", "status": "ok"}])


def test_valid_response_gives_a_row_in_the_study_format(run_dirs):
    client = Client([Reply(200, response([CLAIM]))])
    row, usage = run_one(client, run_dirs)
    assert row["status"] == "ok"
    assert (row["pmid"], row["task"], row["revision"], row["run"]) == ("111", "extraction",
                                                                       "rev", 1)
    assert (row["model"], row["model_returned"]) == ("gpt-6-luna", "gpt-6-luna-2026")
    assert row["output"] == {"claims": [CLAIM]}
    assert rx.ExtractionOutput.model_validate(row["output"]).claims[0].direction == "lowers"
    assert usage.model_dump() == {"requests": 1, "input_tokens": 1000,
                                  "cached_input_tokens": 600, "cache_write_tokens": 300,
                                  "output_tokens": 200, "reasoning_tokens": 50}
    stored = json.loads((run_dirs / "run1" / "111_attempt1.json").read_text())
    assert stored["model_requested"] == "gpt-6-luna"
    assert stored["request"]["model"] == "gpt-6-luna"
    assert stored["request"]["instructions"] == "PROMPT"
    assert "key" not in json.dumps(stored["request"])
    assert client.bodies == [stored["request"]]


def test_cached_exchange_is_reused_within_a_run_and_never_across_runs(run_dirs):
    first = Client([Reply(200, response([CLAIM]))])
    run_one(first, run_dirs, run=1)
    again = Client([])
    row, usage = run_one(again, run_dirs, run=1)
    assert (row["status"], again.bodies, usage.requests) == ("ok", [], 0)
    other = Client([Reply(200, response([]))])
    row2, _ = run_one(other, run_dirs, run=2)
    assert len(other.bodies) == 1
    assert row2["output"] == {"claims": []}
    assert (run_dirs / "run2" / "111_attempt1.json").exists()


def test_schema_failure_is_rerun_once_then_recorded_as_failed(run_dirs):
    bad = dict(CLAIM, direction="up")
    client = Client([Reply(200, response([bad])), Reply(200, response([CLAIM]))])
    row, usage = run_one(client, run_dirs, run=1)
    assert (row["status"], row["attempts"], usage.requests) == ("ok", 2, 2)
    assert len(row["errors"]) == 1
    client = Client([Reply(200, response([bad])), Reply(200, response([bad]))])
    row, _ = run_one(client, run_dirs, run=2)
    assert (row["status"], row["attempts"], row["output"]) == ("extraction_failed", 2, None)
    assert len(row["errors"]) == 2


def test_non_retryable_http_status_is_stored_apart_and_fails_the_record(run_dirs):
    client = Client([Reply(400, "{\"error\": \"bad request\"}")] * 2)
    row, usage = run_one(client, run_dirs, run=1)
    assert (row["status"], usage.requests) == ("extraction_failed", 0)
    assert (run_dirs / "run1" / "111_attempt1.http1.json").exists()
    assert not (run_dirs / "run1" / "111_attempt1.json").exists()


def test_each_run_and_revision_has_its_own_parsed_file():
    one, two = lx.parsed_path("search", 1, "abc"), lx.parsed_path("search", 2, "abc")
    assert one.name == "luna_extraction_search_run1_abc.jsonl"
    assert one != two
    assert one.parent == rx.PARSED
    assert not one.name.startswith("sol_")
    assert lx.RAW == rx.EXP / "outputs" / "raw" / "luna"
    assert lx.RAW != rx.RAW
    assert lx.run_folder("abc", 1) == lx.RAW / "extraction" / "abc" / "run1"
    assert lx.run_folder("abc", 2) == lx.RAW / "extraction" / "abc" / "run2"
