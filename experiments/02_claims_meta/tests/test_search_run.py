import datetime
import gzip
import json
import pathlib

import httpx
import pytest

import assemble_screening_set as ass
import run_search as rs
import search_queries as sq
from link_families import SearchRecord, link

FIX = pathlib.Path(__file__).resolve().parent / "fixtures" / "search"
DAY = datetime.date(2026, 10, 20)
PMIDS = ["29875488", "30111768"]


class Sources:
    """A stand-in for the three services. Europe PMC serves its fixture records two per page."""

    def __init__(self, fail_epmc_page_2: bool = False):
        self.calls: list[tuple[str, dict]] = []
        self.fail_epmc_page_2 = fail_epmc_page_2
        self.epmc = json.loads((FIX / "epmc_page.json").read_text())
        self.openalex = json.loads((FIX / "openalex_page.json").read_text())

    def __call__(self, request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        self.calls.append((request.url.host, params))
        confirmatory = "2019" in (params.get("term") or params.get("query")
                                  or params.get("filter") or "")
        if request.url.path.endswith("esearch.fcgi"):
            ids = PMIDS if confirmatory and "SomaScan" in params["term"] else []
            return httpx.Response(200, json={"esearchresult": {"count": str(len(ids)),
                                                               "idlist": ids}})
        if request.url.path.endswith("efetch.fcgi"):
            assert params["id"] == ",".join(PMIDS)
            return httpx.Response(200, content=(FIX / "pubmed_efetch.xml").read_bytes())
        if request.url.host == "www.ebi.ac.uk":
            assert params["synonym"] == "false" and params["resultType"] == "core"
            records = self.epmc["resultList"]["result"]
            if not (confirmatory and "SomaScan" in params["query"]):
                return httpx.Response(200, json={"hitCount": 0, "request": {
                    "cursorMark": "*"}, "resultList": {"result": []}})
            if params["cursorMark"] == "*":
                page, nxt = records[:2], "second"
            elif self.fail_epmc_page_2:
                return httpx.Response(503, text="unavailable")
            elif params["cursorMark"] == "second":
                page, nxt = records[2:], "third"
            else:
                assert params["cursorMark"] == "third"
                page, nxt = [], "third"
            return httpx.Response(200, json={
                "hitCount": len(records), "nextCursorMark": nxt,
                "request": {"cursorMark": params["cursorMark"]},
                "resultList": {"result": page}})
        assert request.url.host == "api.openalex.org" and "mailto" not in params
        if confirmatory and "SomaScan" in params["filter"] and params["cursor"] == "*":
            return httpx.Response(200, json=self.openalex)
        return httpx.Response(200, json={"meta": {"count": 0, "next_cursor": None},
                                         "results": []})


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(rs.time, "sleep", lambda seconds: None)
    monkeypatch.delenv("OPEN_ALEX_API_KEY", raising=False)


def run(tmp_path, sources, day=DAY):
    with httpx.Client(transport=httpx.MockTransport(sources)) as client:
        return rs.run(client, tmp_path / "run", day)


def test_run_stores_every_response_with_its_hash_and_counts(tmp_path):
    counts = run(tmp_path, Sources())
    manifest = rs.read_manifest(tmp_path / "run")
    pages = [l for l in manifest if l.get("status") == 200]
    for l in pages:
        body = gzip.decompress((tmp_path / "run" / l["file"]).read_bytes())
        assert rs.hashlib.sha256(body).hexdigest() == l["sha256"] and len(body) == l["bytes"]
    assert counts["streams"]["pubmed/esearch_Q2_confirmatory"] == {
        "reported": 2, "retrieved": 2, "pages": 1}
    assert counts["streams"]["pubmed/efetch"] == {"reported": 2, "retrieved": 2, "pages": 1}
    assert counts["streams"]["epmc/Q2_confirmatory"] == {"reported": 4, "retrieved": 4,
                                                          "pages": 3}
    assert counts["streams"]["openalex/Q2_confirmatory"]["retrieved"] == 4
    assert counts["windows"]["update"] == ["2026-01-01", DAY.isoformat()]
    assert len(counts["streams"]) == 2 * 4 * 3 + 2
    assert counts["streams_with_count_gap"] == []


def test_interrupted_run_resumes_from_the_stored_cursor_without_repeating_requests(tmp_path):
    broken = Sources(fail_epmc_page_2=True)
    with pytest.raises(rs.SearchRunError):
        run(tmp_path, broken)
    failed = [l for l in rs.read_manifest(tmp_path / "run") if l.get("status") == 503]
    assert len(failed) == rs.MAX_TRIES
    resumed = Sources()
    counts = run(tmp_path, resumed)
    epmc_q2 = [p for host, p in resumed.calls if host == "www.ebi.ac.uk"
               and "SomaScan" in p["query"] and "2019" in p["query"]]
    assert [p["cursorMark"] for p in epmc_q2] == ["second", "third"]
    assert not [p for host, p in resumed.calls if host == "eutils.ncbi.nlm.nih.gov"]
    fresh = run(tmp_path / "fresh", Sources())
    assert counts["streams"] == fresh["streams"]


def test_completed_run_makes_no_request_when_started_again(tmp_path):
    run(tmp_path, Sources())
    again = Sources()
    run(tmp_path, again)
    assert again.calls == []


def test_resume_on_another_day_raises(tmp_path):
    with pytest.raises(rs.SearchRunError):
        run(tmp_path, Sources(fail_epmc_page_2=True))
    with pytest.raises(rs.SearchRunError, match="one day"):
        run(tmp_path, Sources(), DAY + datetime.timedelta(days=1))


def test_changed_stored_response_is_detected_on_resume(tmp_path):
    with pytest.raises(rs.SearchRunError):
        run(tmp_path, Sources(fail_epmc_page_2=True))
    page = tmp_path / "run" / "epmc" / "Q2_confirmatory" / "page_0001.json.gz"
    page.write_bytes(gzip.compress(gzip.decompress(page.read_bytes()).replace(b"Sun", b"Moon")))
    with pytest.raises(rs.SearchRunError, match="manifest hash"):
        run(tmp_path, Sources())


def test_retrieved_fewer_than_reported_raises_after_counts_are_written(tmp_path):
    sources = Sources()
    sources.openalex["meta"]["count"] = 5
    with pytest.raises(rs.SearchRunError, match="openalex/Q2_confirmatory"):
        run(tmp_path, sources)
    counts = json.loads((tmp_path / "run" / "counts.json").read_text())
    assert counts["streams_with_count_gap"] == ["openalex/Q2_confirmatory"]


def test_openalex_key_goes_in_the_header_and_is_never_stored(tmp_path, monkeypatch):
    monkeypatch.setenv("OPEN_ALEX_API_KEY", "secret-key-value")
    seen = []

    def handler(request):
        if request.url.host == "api.openalex.org":
            seen.append(request.headers.get("Authorization"))
            assert "secret-key-value" not in str(request.url)
        return Sources()(request)

    run(tmp_path, handler)
    assert seen and set(seen) == {"Bearer secret-key-value"}
    stored = b"".join(gzip.decompress(p.read_bytes()) if p.suffix == ".gz" else p.read_bytes()
                      for p in (tmp_path / "run").rglob("*") if p.is_file())
    assert b"secret-key-value" not in stored


def test_search_refuses_to_start_before_the_freeze(tmp_path, monkeypatch):
    draft = tmp_path / "PREREG.md"
    draft.write_text("# Title\n\n**Status:** DRAFT — not frozen.\n")
    monkeypatch.setattr(rs, "PREREG", draft)
    with pytest.raises(rs.SearchRunError, match="not frozen"):
        rs.check_frozen()
    draft.write_text("# Title\n\n**Status:** FROZEN at `b946087070e4`\n")
    rs.check_frozen()


def test_stored_run_assembles_into_two_papers_and_their_preprints(tmp_path):
    run(tmp_path, Sources())
    records = ass.load_run(tmp_path / "run")
    screening = {s.record_id: s for s in ass.deduplicate(records)}
    assert set(screening) == {"29875488", "30111768", "PPR28578", "PPR28491"}
    sun = screening["29875488"]
    assert sun.sources == ["pubmed", "epmc", "openalex"] and sun.abstract_source == "pubmed"
    assert sun.streams == ["epmc/Q2_confirmatory", "openalex/Q2_confirmatory",
                           "pubmed/Q2_confirmatory"]
    assert (sun.kind, sun.doi, sun.first_author_surname) == (
        "journal", "10.1038/s41586-018-0175-2", "Sun")
    preprint = screening["PPR28578"]
    assert (preprint.kind, preprint.doi, preprint.published_as_doi) == (
        "preprint", "10.1101/134551", "10.1038/s41586-018-0175-2")
    assert preprint.first_public.value == datetime.date(2017, 5, 5)
    assert preprint.sources == ["epmc", "openalex"] and preprint.abstract_source == "epmc"
    family_of, links = link([SearchRecord(
        record_id=s.record_id, kind=s.kind, doi=s.doi, pmid=s.pmid, pmcid=s.pmcid,
        published_as_doi=s.published_as_doi, title=s.title,
        first_author_surname=s.first_author_surname, first_public=s.first_public)
        for s in screening.values()])
    assert family_of["PPR28578"] == family_of["29875488"]
    assert family_of["PPR28491"] == family_of["30111768"]
    assert family_of["29875488"] != family_of["30111768"]
    assert {l.rule for l in links} == {"published_as"}


def test_registered_queries_are_the_ones_sent(tmp_path):
    sources = Sources()
    run(tmp_path, sources)
    terms = {p["term"] for host, p in sources.calls if "term" in p}
    assert terms == {sq.pubmed_query(q, a, b) for q in sq.QUERIES
                     for a, b in sq.windows(DAY).values()}
    epmc = {p["query"] for host, p in sources.calls if host == "www.ebi.ac.uk"}
    assert epmc == {sq.epmc_query(q, a, b) for q in sq.QUERIES
                    for a, b in sq.windows(DAY).values()}
    filters = {p["filter"] for host, p in sources.calls if host == "api.openalex.org"}
    assert filters == {sq.openalex_filter(q, a, b) for q in sq.QUERIES
                       for a, b in sq.windows(DAY).values()}


@pytest.mark.parametrize("start, end", [
    ("2013-12-31", "2014-01-31"), ("2018-12-01", "2019-01-01"), ("2018-07-01", "2018-06-30")])
def test_smoke_window_outside_2014_to_2018_or_reversed_raises(start, end):
    with pytest.raises(rs.SearchRunError, match="smoke window lies between"):
        rs.smoke_window(datetime.date.fromisoformat(start), datetime.date.fromisoformat(end))


def test_smoke_window_defaults_and_needs_both_dates():
    assert rs.smoke_window(None, None) == rs.SMOKE_WINDOW
    assert rs.smoke_window(datetime.date(2018, 6, 1), datetime.date(2018, 6, 30)) == (
        datetime.date(2018, 6, 1), datetime.date(2018, 6, 30))
    with pytest.raises(rs.SearchRunError, match="both"):
        rs.smoke_window(datetime.date(2018, 6, 1), None)
    assert rs.SMOKE_LATEST < datetime.date(2019, 1, 1)


def test_smoke_run_sends_only_its_window_and_refuses_a_resume_with_another(tmp_path):
    sent: list[str] = []

    def source(request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        sent.append(params.get("term") or params.get("query") or params.get("filter") or "")
        if request.url.host == "eutils.ncbi.nlm.nih.gov":
            if request.url.path.endswith("esearch.fcgi"):
                return httpx.Response(200, json={"esearchresult": {"count": "0", "idlist": []}})
            return httpx.Response(200, content=b"<PubmedArticleSet/>")
        if request.url.host == "www.ebi.ac.uk":
            return httpx.Response(200, json={"hitCount": 0, "resultList": {"result": []}})
        return httpx.Response(200, json={"meta": {"count": 0, "next_cursor": None},
                                         "results": []})

    window = (datetime.date(2018, 6, 1), datetime.date(2018, 6, 30))
    with httpx.Client(transport=httpx.MockTransport(source)) as client:
        counts = rs.run(client, tmp_path / "run", DAY, True, window)
        assert counts["windows"] == {"smoke": ["2018-06-01", "2018-06-30"]}
        dated = [s for s in sent if "201" in s or "202" in s]
        assert dated and all("2018" in s and "2019" not in s and "202" not in s for s in dated)
        with pytest.raises(rs.SearchRunError, match="smoke window"):
            rs.run(client, tmp_path / "run", DAY, True, rs.SMOKE_WINDOW)
        with pytest.raises(rs.SearchRunError, match="smoke run only"):
            rs.run(client, tmp_path / "other", DAY, False, window)
