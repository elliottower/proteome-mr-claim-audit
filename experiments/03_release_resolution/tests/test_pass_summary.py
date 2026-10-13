import pytest

import pass_summary as ps


def row(rels=(), roles=(), state="unresolved", reasons=("attribution_unresolved",)):
    return {"identified_releases": list(rels), "roles": [{"release": r, "role": x} for r, x in roles],
            "attribution_state": state, "unresolved_reasons": list(reasons)}


def test_usage_counts_thinking_as_billed_output_and_re_requests():
    entries = [
        {"model": "claude-sonnet-5-5", "attempt": 1, "usd": 0.1,
         "usage": {"input_tokens": 100, "cache_creation_input_tokens": 50,
                   "cache_read_input_tokens": 1000, "output_tokens": 4000}},
        {"model": "claude-sonnet-5-5", "attempt": 2, "usd": 0.2,
         "usage": {"input_tokens": 100, "cache_read_input_tokens": 1000, "output_tokens": 2000}},
        {"model": "gpt-6.1-sol", "attempt": 1, "usd": 0.3,
         "usage": {"input_tokens": 1100, "input_tokens_details": {"cached_tokens": 1000},
                   "output_tokens": 3000, "output_tokens_details": {"reasoning_tokens": 2500}}}]
    got = ps.usage_summary(entries)
    c, s = got["claude-sonnet-5-5"], got["gpt-6.1-sol"]
    assert c["requests_billed"] == 2 and c["re_requests"] == 1
    assert c["mean_output_tokens_per_request"] == 3000 and c["cache_write_tokens"] == 50
    assert s["new_input_tokens"] == 100 and s["cache_read_tokens"] == 1000
    assert s["reasoning_tokens"] == 2500 and got["total_usd"] == pytest.approx(0.6)


def test_rows_differ_on_releases_roles_attribution_or_reasons_and_not_on_notes():
    a = row(["X"], [("X", "primary")], "explicit", ())
    assert not ps.differs(a, {**a, "note": "other"})
    assert ps.differs(a, row(["Y"], [("Y", "primary")], "explicit", ()))
    assert ps.differs(a, row(["X"], [("X", "replication")], "explicit", ()))
    assert ps.differs(a, row(["X"], [("X", "primary")], "paper_wide", ()))
    assert ps.differs(row(), row(reasons=("release_not_identified",)))


def test_rows_to_adjudicate_are_disagreements_and_rows_one_model_did_not_answer():
    first = {"a": row(), "b": row(["X"]), "c": row()}
    second = {"a": row(), "b": row(["Y"])}
    got = ps.adjudication_rows(["a", "b", "c"], first, second)
    assert got["rows_where_the_models_differ"] == 1
    assert got["rows_without_an_accepted_answer_from_a_model"] == 1
    assert got["row_ids_to_adjudicate"] == ["b", "c"]
