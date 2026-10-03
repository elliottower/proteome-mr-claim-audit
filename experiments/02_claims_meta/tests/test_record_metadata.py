import inspect

import httpx
import pytest

import record_metadata as rm
import registry_secondaries as rsec
import run_search as rs


def work(wid, doi=None, pmid=None, refs=(), authorships=None):
    return {"id": f"https://openalex.org/{wid}",
            "doi": f"https://doi.org/{doi}" if doi else None,
            "ids": {"openalex": f"https://openalex.org/{wid}",
                    **({"pmid": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}"} if pmid else {})},
            "referenced_works": [f"https://openalex.org/{r}" for r in refs],
            "authorships": authorships if authorships is not None else []}


def author(position, institutions=(), countries=()):
    return {"author_position": position,
            "institutions": [{"country_code": c} for c in institutions],
            "countries": list(countries)}


def screening(rid, doi=None, pmid=None, kind="journal", streams=(), members=(), journal=None):
    return {"record_id": rid, "doi": doi, "pmid": pmid, "kind": kind, "streams": list(streams),
            "member_ids": list(members), "journal": journal}


WORKS = {
    "W1": work("W1", doi="10.1/A", refs=["W9", "W8"],
               authorships=[author("middle", ["FR"]), author("first", ["GB", "US"]),
                            author("last", ["DE"])]),
    "W2": work("W2", pmid="222", authorships=[author("first", [], ["CN", "SE"])]),
    "W3": work("W3", refs=["W1"], authorships=[author("first")]),
}


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(rs.time, "sleep", lambda seconds: None)
    monkeypatch.delenv("OPEN_ALEX_API_KEY", raising=False)


class OpenAlex:
    def __init__(self):
        self.requests: list[dict] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        assert "mailto" not in params
        if params["cursor"] != "*":
            return httpx.Response(200, json={"meta": {"count": 0, "next_cursor": None},
                                             "results": []})
        self.requests.append(params)
        field, _, value = params["filter"].partition(":")
        values = value.split("|")
        found = [w for w in WORKS.values() if
                 (field == "doi" and w["doi"] and w["doi"].removeprefix(
                     "https://doi.org/").lower() in values)
                 or (field == "pmid" and w["ids"].get("pmid", "").rsplit("/", 1)[-1] in values)
                 or (field == "openalex" and w["id"].rsplit("/", 1)[-1] in values)]
        return httpx.Response(200, json={"meta": {"count": len(found), "next_cursor": "end"},
                                         "results": found})


RECORDS = [
    screening("101", doi="10.1/A", pmid="101", streams=["pubmed/Q1_confirmatory",
                                                        "openalex/Q2_confirmatory"],
              members=["pubmed:101", "openalex:W1"], journal="Journal A"),
    screening("222", pmid="222", streams=["epmc/Q1_confirmatory"], members=["pubmed:222",
                                                                           "epmc:222"]),
    screening("W3", kind="preprint", streams=["openalex/Q4_confirmatory"],
              members=["openalex:W3"]),
    screening("999", pmid="999", streams=["epmc/Q1_confirmatory"]),
]
CHASED = [screening("W7", doi="10.1/chased", streams=["openalex/forward"],
                    members=["openalex:W7"])]


def test_fetch_looks_each_record_up_by_doi_then_pmid_then_openalex_id(tmp_path):
    transport = OpenAlex()
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        counts = rm.fetch(client, tmp_path, RECORDS)
    filters = sorted(r["filter"] for r in transport.requests)
    assert filters == ["doi:10.1/a", "openalex:W3", "pmid:222|999"]
    assert all(r["select"] == "id,doi,ids,referenced_works,authorships"
               for r in transport.requests)
    assert counts == {"records": 4, "records_without_an_identifier": 0, "looked_up_by_doi": 1,
                      "looked_up_by_openalex": 1, "looked_up_by_pmid": 2}
    assert sorted(w["id"].rsplit("/", 1)[-1] for w in rm.stored_works(tmp_path)) == [
        "W1", "W2", "W3"]


def test_fetch_resumes_from_stored_responses_without_new_requests(tmp_path):
    first, second = OpenAlex(), OpenAlex()
    with httpx.Client(transport=httpx.MockTransport(first)) as client:
        rm.fetch(client, tmp_path, RECORDS)
    with httpx.Client(transport=httpx.MockTransport(second)) as client:
        rm.fetch(client, tmp_path, RECORDS)
    assert len(first.requests) == 3 and second.requests == []


def test_build_reads_sources_references_and_the_first_authors_first_institution():
    families = {"101": ["101", "W3"], "222": ["222"], "999": ["999"], "W7": ["W7"]}
    rows = {r.record_id: r for r in rm.build(families, RECORDS, [CHASED], list(WORKS.values()))}
    a = rows["101"]
    assert (a.search_sources, a.chase_round, a.journal) == (("pubmed", "openalex"), None,
                                                            "Journal A")
    assert (a.openalex_ids, a.referenced_works, a.has_reference_list) == (
        ("W1",), ("W8", "W9"), True)
    assert a.first_author_country == "GB"
    b = rows["222"]
    assert (b.search_sources, b.openalex_ids, b.has_reference_list, b.first_author_country) == (
        ("epmc",), ("W2",), False, "CN")
    c = rows["W3"]
    assert (c.kind, c.referenced_works, c.first_author_country) == ("preprint", ("W1",), None)
    missing = rows["999"]
    assert (missing.openalex_ids, missing.has_reference_list, missing.referenced_works,
            missing.first_author_country) == ((), None, (), None)
    chased = rows["W7"]
    assert (chased.search_sources, chased.chase_round, chased.openalex_ids) == ((), 1, ("W7",))


def test_build_refuses_a_family_record_that_is_in_no_screening_set():
    with pytest.raises(rm.RecordMetadataError):
        rm.build({"F": ["absent"]}, RECORDS, [], [])


def test_a_pubmed_record_fetched_for_another_source_has_no_pubmed_query_source():
    linked = screening("5", pmid="5", streams=["epmc/Q1_confirmatory"],
                       members=["pubmed:5", "epmc:5"])
    row, = rm.build({"5": ["5"]}, [linked], [], [])
    assert row.search_sources == ("epmc",)


def test_no_country_table_is_planned():
    assert not hasattr(rm, "country_counts")
    assert '"country"' not in inspect.getsource(rm.main)


def test_the_metadata_file_written_by_build_is_the_one_the_secondaries_read(tmp_path):
    families = {"101": ["101", "W3"], "222": ["222"]}
    rows = rm.build(families, RECORDS, [], list(WORKS.values()))
    path = tmp_path / "record_metadata.jsonl"
    path.write_text("".join(r.model_dump_json() + "\n" for r in rows))
    loaded = rsec.load_record_meta(path)
    assert loaded == {r.record_id: r for r in rows}
    meta = {f: {"registry_records": [f], "dating_records": [],
                "first_public": {"value": "2020-01-01", "resolution": "day"}}
            for f in families}
    overlap = rsec.source_overlap(meta, families, loaded)
    assert overlap["by_search_sources"] == {"epmc": 1, "pubmed+openalex": 1}


def test_smoke_fetch_refuses_a_record_first_public_in_the_window():
    early = {"record_id": "1", "first_public": {"value": "2018-12-31", "resolution": "day"}}
    late = {"record_id": "2", "first_public": {"value": "2019-01-01", "resolution": "day"}}
    rm.refuse_window_records([early])
    with pytest.raises(rm.RecordMetadataError, match="registered window"):
        rm.refuse_window_records([early, late])
