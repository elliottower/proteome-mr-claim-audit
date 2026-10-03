import datetime
import json

import httpx
import pytest

import fetch_fulltext as ff

XML = (b"<article><front><abstract><p>abstract text</p></abstract></front>"
       b"<body><sec><title>Results</title><p>IL6R  lowered CAD risk.</p></sec></body></article>")
META = {"11": {"isOpenAccess": "Y", "pmcid": "PMC11"}, "12": {"isOpenAccess": "N"},
        "13": {"isOpenAccess": "Y", "pmcid": "PMC13"}, "14": {"isOpenAccess": "Y", "pmcid": "PMC14"}}
BODIES = {"PMC11": (200, XML), "PMC13": (404, b""), "PMC14": (200, b"<article><front/></article>")}


class EuropePMC:
    def __init__(self):
        self.requests: list[str] = []
        self.asked: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(str(request.url))
        assert "email" not in str(request.url) and "mailto" not in str(request.url)
        if request.url.path.endswith("/search"):
            pmid = request.url.params["query"].split()[0].removeprefix("EXT_ID:")
            self.asked.append(pmid)
            return httpx.Response(200, json={"resultList": {"result": [{
                "title": f"Paper {pmid}", "firstPublicationDate": "2021-05-05", **META[pmid]}]}})
        status, body = BODIES[request.url.path.split("/")[-2]]
        return httpx.Response(status, content=body)


def record(rid, kind="journal", pmid=None, source="pubmed"):
    return {"record_id": rid, "kind": kind, "pmid": pmid, "abstract_source": source}


RECORDS = {r["record_id"]: r for r in [
    record("11", pmid="11"), record("12", pmid="12"), record("13", pmid="13"),
    record("14", pmid="14"), record("PPR9", kind="preprint"), record("W5"),
    record("15", pmid="15", source="epmc"), record("16", pmid="16", source="openalex")]}
META_FAMILIES = {
    "A": {"registry_records": ["11"], "window": "confirmatory"},
    "B": {"registry_records": ["12"], "window": "confirmatory"},
    "C": {"registry_records": ["13"], "window": "confirmatory"},
    "D": {"registry_records": ["14"], "window": "update"},
    "E": {"registry_records": ["PPR9"], "window": "confirmatory"},
    "F": {"registry_records": ["W5"], "window": "confirmatory"},
    "G": {"registry_records": ["15"], "window": "confirmatory"},
    "H": {"registry_records": ["16", "11"], "window": "confirmatory"},
}


@pytest.fixture()
def raw(tmp_path, monkeypatch):
    monkeypatch.setattr(ff, "RAW", tmp_path / "raw")


def run(tmp_path, source):
    with httpx.Client(transport=httpx.MockTransport(source)) as client:
        return ff.census(client, META_FAMILIES, RECORDS, tmp_path / "out")


def test_each_family_takes_the_registered_status(tmp_path, raw):
    status = run(tmp_path, EuropePMC())
    assert {f: v["status"] for f, v in status["families"].items()} == {
        "A": "fetched", "B": "no_open_access_full_text", "C": "no_open_access_full_text",
        "D": "no_open_access_full_text", "E": "no_open_access_full_text",
        "F": "no_open_access_full_text", "G": "version_unmatched", "H": "fetched"}
    assert status["families_by_window_and_status"] == {
        "confirmatory": {"fetched": 2, "no_open_access_full_text": 4, "version_unmatched": 1},
        "update": {"no_open_access_full_text": 1}}
    assert status["families"]["H"]["full_text_record"] == "11"
    assert [r["status"] for r in status["families"]["H"]["records"]] == [
        "version_unmatched", "fetched"]


def test_bodies_drop_the_abstract_and_carry_the_record_id(tmp_path, raw):
    run(tmp_path, EuropePMC())
    bodies = [json.loads(l) for l in (tmp_path / "out" / "fulltext_bodies.jsonl").read_text()
              .splitlines()]
    assert [b["pmid"] for b in bodies] == ["11", "11"]
    assert bodies[0]["body"] == "## Results\nIL6R lowered CAD risk."
    assert "abstract text" not in bodies[0]["body"]


def test_no_request_is_made_for_a_record_without_a_pubmed_abstract(tmp_path, raw):
    source = EuropePMC()
    run(tmp_path, source)
    assert sorted(source.asked) == ["11", "12", "13", "14"]


def test_stopped_census_resumes_without_repeating_a_request(tmp_path, raw):
    first = run(tmp_path, EuropePMC())

    def refuse(request):
        raise AssertionError("no request expected")

    second = run(tmp_path, refuse)
    assert second["families"] == first["families"]


@pytest.mark.parametrize("statuses, expected", [
    (["fetched", "version_unmatched"], "fetched"),
    (["version_unmatched", "no_open_access_full_text"], "version_unmatched"),
    (["no_open_access_full_text"], "no_open_access_full_text")])
def test_family_status_precedence(statuses, expected):
    assert ff.family_status(statuses) == expected


def test_census_before_a_date_refuses_a_later_record_ahead_of_any_request(tmp_path, raw):
    def dated(day):
        return {rid: {**r, "first_public": {"value": day, "resolution": "day"}}
                for rid, r in RECORDS.items()}

    source = EuropePMC()
    with httpx.Client(transport=httpx.MockTransport(source)) as client:
        with pytest.raises(ff.FullTextError, match="first public on or after"):
            ff.census(client, META_FAMILIES, dated("2019-01-01"), tmp_path / "late",
                      datetime.date(2019, 1, 1))
    assert source.requests == []


def test_refetched_full_text_with_other_bytes_is_refused(tmp_path, raw):
    (ff.RAW).mkdir(parents=True, exist_ok=True)
    (ff.RAW / "PMC11.xml").write_bytes(b"<article>other bytes</article>")
    with httpx.Client(transport=httpx.MockTransport(EuropePMC())) as client:
        with pytest.raises(ff.FullTextError, match="other bytes"):
            ff.fetch_one(client, "11")
