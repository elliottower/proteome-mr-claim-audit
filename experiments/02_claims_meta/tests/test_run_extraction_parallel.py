import collections
import json
import threading

import httpx
import pytest

import run_extraction as rx
import run_extraction_parallel as rp

ANSWER = {
    "genetic_instruments_for_circulating_proteins": "yes",
    "states_protein_outcome_result": "yes",
    "proteome_or_panel_wide_screen": "no",
    "n_proteins_tested": None, "n_proteins_tested_span": None,
    "count_other": None, "count_other_span": None,
    "exclusion": [], "also_tissue_or_csf": False,
}
ABSTRACT = "Genetically predicted protein levels and an outcome were studied. " * 5


def ok_response(pmid):
    answer = dict(ANSWER, count_other=len(pmid))
    return httpx.Response(200, json={
        "model": "gpt-6.1-sol", "temperature": 1.0,
        "usage": {"input_tokens": 10, "output_tokens": 2},
        "output": [{"type": "message",
                    "content": [{"type": "output_text", "text": json.dumps(answer)}]}]})


def refusal(code):
    return httpx.Response(429, json={"error": {"code": code, "type": code}})


def pmid_of(request):
    text = json.loads(request.content)["input"]
    return text.split("Title: ", 1)[1].split("\n", 1)[0]


class Server:
    """A fake endpoint: `policy(pmid, nth call for that pmid)` returns the response."""

    def __init__(self, policy):
        self.policy = policy
        self.calls = collections.Counter()
        self.active = 0
        self.max_active = 0
        self.lock = threading.Lock()

    def handle(self, request):
        pmid = pmid_of(request)
        with self.lock:
            self.calls[pmid] += 1
            nth = self.calls[pmid]
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        threading.Event().wait(0.02)
        with self.lock:
            self.active -= 1
        return self.policy(pmid, nth)


@pytest.fixture
def run(tmp_path, monkeypatch):
    """Run the wrapper's main on records p0..p(n-1) against a fake server."""
    monkeypatch.setattr(rx, "PARSED", tmp_path / "parsed")
    monkeypatch.setattr(rx.time, "sleep", lambda seconds: None)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def go(server, n, workers, label="lab"):
        abstracts = tmp_path / f"{label}.jsonl"
        abstracts.write_text("".join(
            json.dumps({"pmid": f"p{i}", "title": f"p{i}", "abstract": ABSTRACT}) + "\n"
            for i in range(n)))
        monkeypatch.setattr(rp, "make_client", lambda: httpx.Client(
            transport=httpx.MockTransport(server.handle)))
        monkeypatch.setenv("SOL_WORKERS", str(workers))
        monkeypatch.setattr("sys.argv", ["x", "--task", "eligibility", "--label", label,
                                         "--abstracts", str(abstracts),
                                         "--raw-root", str(tmp_path / "raw")])
        rp.main()
        return [json.loads(line) for line in next(
            (tmp_path / "parsed").glob(f"sol_eligibility_{label}_*[0-9a-f].jsonl")
        ).read_text().splitlines()]

    go.tmp = tmp_path
    return go


def test_parsed_rows_carry_each_records_own_answer_in_input_order(run):
    server = Server(lambda pmid, nth: ok_response(pmid))
    rows = run(server, 23, 8)
    assert [r["pmid"] for r in rows] == [f"p{i}" for i in range(23)]
    assert all(r["status"] == "ok" and r["attempts"] == 1 for r in rows)
    assert [r["output"]["count_other"] for r in rows] == [len(f"p{i}") for i in range(23)]
    assert set(server.calls.values()) == {1}


def test_requests_in_flight_never_exceed_the_worker_count(run):
    server = Server(lambda pmid, nth: ok_response(pmid))
    run(server, 60, 5)
    assert 1 < server.max_active <= 5


def test_rate_limit_refusal_halves_the_limit_and_the_record_is_still_answered(run):
    server = Server(lambda pmid, nth: refusal("rate_limit_exceeded")
                    if pmid == "p3" and nth == 1 else ok_response(pmid))
    rows = run(server, 12, 8)
    assert all(r["status"] == "ok" for r in rows)
    summary = json.loads(next((run.tmp / "parsed").glob("*.parallel_run.json")).read_text())
    assert summary["worker_limit_history"] == [8, 4]
    assert server.calls["p3"] == 2


def test_billing_refusal_stops_without_a_parsed_file_and_the_same_command_resumes(run):
    paid = {"p0", "p1", "p2"}
    server = Server(lambda pmid, nth: ok_response(pmid) if pmid in paid
                    else refusal("insufficient_quota"))
    with pytest.raises(rp.BillingStop) as stopped:
        run(server, 40, 2)
    summary = json.loads(str(stopped.value))
    assert summary["answered"] == 3 and summary["unanswered"] == 37
    assert not list((run.tmp / "parsed").glob("*.jsonl"))
    raw = next((run.tmp / "raw" / "eligibility").iterdir())
    assert sorted(p.name for p in raw.glob("*_attempt[12].json")) == [
        "p0_attempt1.json", "p1_attempt1.json", "p2_attempt1.json"]
    refused = [p for p in server.calls if p not in paid]
    assert len(refused) < 37

    funded = Server(lambda pmid, nth: ok_response(pmid))
    rows = run(funded, 40, 2)
    assert all(r["status"] == "ok" for r in rows) and len(rows) == 40
    assert not paid & set(funded.calls)
    assert set(funded.calls.values()) == {1}


def test_a_record_with_no_response_is_never_written_as_failed(run):
    server = Server(lambda pmid, nth: httpx.Response(503, text="down")
                    if pmid == "p4" else ok_response(pmid))
    with pytest.raises(rp.Unanswered) as stopped:
        run(server, 9, 4)
    assert json.loads(str(stopped.value))["unanswered"] == 1
    assert not list((run.tmp / "parsed").glob("*.jsonl"))


def test_a_schema_failure_keeps_the_runners_own_rule(run):
    bad = httpx.Response(200, json={
        "model": "gpt-6.1-sol", "usage": {},
        "output": [{"type": "message",
                    "content": [{"type": "output_text", "text": "{\"x\": 1}"}]}]})
    server = Server(lambda pmid, nth: bad if pmid == "p1" else ok_response(pmid))
    rows = run(server, 4, 4)
    assert [r["status"] for r in rows] == ["ok", "extraction_failed", "ok", "ok"]
    assert server.calls["p1"] == rx.MAX_SCHEMA_ATTEMPTS


def test_a_lowered_limit_holds_new_requests_until_enough_have_finished():
    limiter = rp.Limiter(4)
    for _ in range(4):
        limiter.acquire()
    limiter.halve()
    assert limiter.limit == 2
    entered = threading.Event()

    def waiter():
        limiter.acquire()
        entered.set()

    thread = threading.Thread(target=waiter, daemon=True)
    thread.start()
    limiter.release()
    assert not entered.wait(0.3)
    limiter.release()
    assert not entered.wait(0.3)
    limiter.release()
    assert entered.wait(5)
    assert limiter.active == 2


def test_the_limit_is_never_lowered_below_the_minimum_or_twice_within_the_cooldown():
    limiter = rp.Limiter(16)
    limiter.halve()
    limiter.halve()
    assert limiter.history == [16, 8]
    low = rp.Limiter(rp.MIN_WORKERS)
    low.halve()
    assert low.history == [rp.MIN_WORKERS]
