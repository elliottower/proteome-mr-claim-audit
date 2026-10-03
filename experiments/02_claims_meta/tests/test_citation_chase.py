import datetime
import json
import pathlib

import httpx
import pytest

import citation_chase as cc
import run_search as rs

FIX = pathlib.Path(__file__).resolve().parent / "fixtures" / "search"


def work(wid, doi=None, pmid=None, refs=(), title="t", abstract=("word",), date="2021-02-03"):
    return {"id": f"https://openalex.org/{wid}",
            "doi": f"https://doi.org/{doi}" if doi else None,
            "ids": {"openalex": f"https://openalex.org/{wid}",
                    **({"pmid": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}"} if pmid else {})},
            "display_name": title, "publication_date": date, "type": "article",
            "authorships": [{"author_position": "first",
                             "author": {"display_name": "Ada Lovelace"}}],
            "abstract_inverted_index": {w: [i] for i, w in enumerate(abstract)},
            "referenced_works": [f"https://openalex.org/{r}" for r in refs]}


WORKS = {
    "W1": work("W1", doi="10.1/seed1", refs=["W10", "W11", "W2"]),
    "W2": work("W2", pmid="222", refs=["W10", "W12", "W13", "W14"]),
    "W10": work("W10", doi="10.1/cited-by-both"),
    "W11": work("W11", doi="10.1/known"),
    "W12": work("W12", pmid="29875488", abstract=("openalex", "text")),
    "W13": work("W13", pmid="30111768", doi="10.1038/S41467-018-05512-X"),
    "W14": work("W14", doi="10.1/cited-and-published-in-2018", date="2018-12-31"),
    "W20": work("W20", doi="10.1/citing"),
    "W21": work("W21", pmid="999"),
}
CITING = {"W1": ["W20", "W10"], "W2": ["W21", "W20"]}


class OpenAlex:
    def __init__(self):
        self.filters: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        if request.url.host == "eutils.ncbi.nlm.nih.gov":
            assert params["id"] == "29875488,30111768"
            return httpx.Response(200, content=(FIX / "pubmed_efetch.xml").read_bytes())
        assert "mailto" not in params
        if params["cursor"] != "*":
            return httpx.Response(200, json={"meta": {"count": 0, "next_cursor": None},
                                             "results": []})
        self.filters.append(params["filter"])
        first, *limits = params["filter"].split(",")
        field, _, value = first.partition(":")
        values = value.split("|")
        if field == "doi":
            found = [w for w in WORKS.values() if w["doi"] and w["doi"].removeprefix(
                "https://doi.org/") in values]
        elif field == "pmid":
            found = [w for w in WORKS.values() if w["ids"].get("pmid", "").rsplit("/", 1)[-1]
                     in values]
        elif field == "openalex":
            found = [WORKS[v] for v in values]
        else:
            assert field == "cites"
            found = [WORKS[c] for c in dict.fromkeys(c for v in values for c in CITING[v])]
        for limit in limits:
            name, _, day = limit.partition(":")
            found = [w for w in found if (w["publication_date"] >= day
                                          if name == "from_publication_date"
                                          else w["publication_date"] <= day)]
        return httpx.Response(200, json={"meta": {"count": len(found), "next_cursor": "end"},
                                         "results": found})


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(rs.time, "sleep", lambda seconds: None)
    monkeypatch.delenv("OPEN_ALEX_API_KEY", raising=False)


def run_chase(tmp_path, source, **kwargs):
    seeds = [{"record_id": "S1", "doi": "10.1/seed1", "pmid": None},
             {"record_id": "222", "doi": None, "pmid": "222"},
             {"record_id": "S3", "doi": None, "pmid": None}]
    known = [{"record_id": "K", "doi": "10.1/known", "pmid": None, "pmcid": None,
              "member_ids": ["epmc:PPR1"]},
             {"record_id": "999", "doi": None, "pmid": "999", "pmcid": None,
              "member_ids": ["pubmed:999"]}]
    with httpx.Client(transport=httpx.MockTransport(source)) as client:
        return cc.chase(client, tmp_path / "round", seeds, known, **kwargs)


def test_round_returns_new_cited_and_citing_works_only(tmp_path):
    source = OpenAlex()
    screening, counts = run_chase(tmp_path, source)
    by_id = {s.record_id: s for s in screening}
    assert set(by_id) == {"W10", "29875488", "30111768", "W20"}
    assert by_id["W10"].streams == ["openalex/backward", "openalex/forward"]
    assert by_id["W20"].streams == ["openalex/forward"]
    assert by_id["29875488"].abstract_source == "pubmed"
    assert by_id["29875488"].sources == ["pubmed", "openalex"]
    assert by_id["29875488"].abstract != "openalex text"
    assert by_id["30111768"].member_ids == ["pubmed:30111768", "openalex:W13"]
    assert counts == {
        "seeds": 3, "seeds_without_doi_or_pmid": 1, "seed_works_found": 2,
        "published_from": "2019-01-01", "backward_works_referenced": 5,
        "backward_works_retrieved": 3, "forward_works": 3,
        "works_already_in_screening_sets": 2,
        "new_works": 4, "new_works_with_pmid": 2, "new_screening_records": 4,
        "new_screening_records_no_abstract": {
            "records": 2, "empty": 0, "stub_below_floor": 2,
            "by_document_class": {"journal": 2}, "floor_characters": 200}}
    # W10 and W20 carry the one-word OpenAlex stub; the two PubMed records have abstracts.
    assert [s.record_id for s in screening if s.no_abstract] == ["W10", "W20"]
    assert source.filters[:2] == ["doi:10.1/seed1", "pmid:222"]
    assert "cites:W1|W2,from_publication_date:2019-01-01" in source.filters
    assert "openalex:W11|W12|W13|W14,from_publication_date:2019-01-01" in source.filters
    assert len(source.filters) == 4


def test_work_published_before_2019_is_not_chased(tmp_path):
    screening, _ = run_chase(tmp_path, OpenAlex())
    assert "10.1/cited-and-published-in-2018" not in {s.doi for s in screening}
    unlimited, _ = run_chase(tmp_path / "no_floor", OpenAlex(), published_from=None)
    assert "10.1/cited-and-published-in-2018" in {s.doi for s in unlimited}


def test_finished_round_makes_no_request_when_started_again(tmp_path):
    first, _ = run_chase(tmp_path, OpenAlex())
    again = OpenAlex()

    def counting(request):
        again.filters.append(str(request.url))
        raise AssertionError("no request expected")

    second, _ = run_chase(tmp_path, counting)
    assert [s.record_id for s in second] == [s.record_id for s in first]
    assert again.filters == []


def test_smoke_run_retrieves_no_cited_or_citing_work_dated_after_2018(tmp_path):
    source = OpenAlex()
    with httpx.Client(transport=httpx.MockTransport(source)) as client:
        screening, _ = cc.chase(client, tmp_path / "round",
                                [{"doi": None, "pmid": "222"}], [],
                                datetime.date(2018, 12, 31), None)
    assert source.filters == ["pmid:222", "cites:W2,to_publication_date:2018-12-31",
                              "openalex:W10|W12|W13|W14,to_publication_date:2018-12-31"]
    assert [s.doi for s in screening] == ["10.1/cited-and-published-in-2018"]


def test_smoke_screening_set_keeps_no_record_first_public_after_2018(tmp_path):
    screening, _ = run_chase(tmp_path, OpenAlex(), published_from=None)
    days = {s.record_id: s.first_public.value for s in screening}
    assert days["W10"] == datetime.date(2021, 2, 3)
    kept = cc.dated_until(screening, datetime.date(2018, 12, 31))
    assert kept and all(s.first_public.value <= datetime.date(2018, 12, 31) for s in kept)
    assert "W10" not in {s.record_id for s in kept}
    assert {s.doi for s in kept} >= {"10.1/cited-and-published-in-2018"}


def test_seed_without_an_abstract_is_refused_before_any_request(tmp_path):
    def no_request(request):
        raise AssertionError("no request expected")

    with httpx.Client(transport=httpx.MockTransport(no_request)) as client:
        with pytest.raises(cc.ChaseError, match="no_abstract"):
            cc.chase(client, tmp_path / "round",
                     [{"record_id": "S9", "doi": "10.1/x", "pmid": None, "no_abstract": True}],
                     [])
    assert not (tmp_path / "round").exists()


@pytest.mark.parametrize("round_number, newly_eligible, expected", [
    (1, 5, True), (2, 1, True), (3, 9, False), (1, 0, False), (2, 0, False)])
def test_chasing_stops_after_an_empty_round_or_three_rounds(round_number, newly_eligible,
                                                           expected):
    assert cc.another_round(round_number, newly_eligible) is expected


def test_stop_rule_is_the_registered_one():
    prereg = (pathlib.Path(cc.__file__).resolve().parent.parent / "PREREG.md").read_text()
    assert "repeating until a round adds no eligible paper, to a maximum of three rounds" in (
        " ".join(prereg.split()))
    assert "publication date of 2019-01-01 or later" in " ".join(prereg.split())
    assert cc.PUBLISHED_FROM == datetime.date(2019, 1, 1)
    assert cc.MAX_ROUNDS == 3
