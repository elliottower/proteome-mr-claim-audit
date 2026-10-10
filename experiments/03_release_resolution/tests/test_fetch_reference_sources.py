import datetime
import hashlib
import json

import httpx
import pytest

import fetch_reference_sources as fr

TODAY = datetime.date(2026, 10, 10)
DICTIONARY = [{"source_identifier": "doi:10.1/a; PMID:111"},
              {"source_identifier": "PMID:222; PMC9"},
              {"source_identifier": "doi:10.1/b; PMID:222"},
              {"source_identifier": "https://example.org/docs"}]


class Response:
    def __init__(self, content, status=200):
        self.content, self.status = content, status

    def raise_for_status(self):
        if self.status >= 400:
            raise httpx.HTTPStatusError("bad", request=None, response=None)


class Client:
    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def get(self, url, headers):
        self.calls.append((url, headers))
        body = self.pages[url]
        return body if isinstance(body, Response) else Response(body)


def sources():
    return {"documents": [{"key": "doc", "url": "https://r.org/download"},
                          {"key": "api", "url": "https://api.org/b", "auth": "TOKEN_NAME"}],
            "linked": [{"key": "man", "from": "doc", "pattern": r"https://r\.org/[a-z]+_manifest\.tsv",
                        "query": "dl=1"}],
            "gwas_catalog": {"url": "https://gc.org/s?pubmed_id={pmid}&page={page}"}}


def test_a_pmid_with_one_dictionary_row_is_queried_and_one_with_two_is_not():
    assert fr.single_row_pmids(DICTIONARY) == ["111"]


def test_fetch_follows_the_documented_link_pages_the_catalog_and_records_provenance(tmp_path,
                                                                                    monkeypatch):
    monkeypatch.setenv("TOKEN_NAME", "secret")
    page0 = json.dumps({"page": {"totalPages": 2}}).encode()
    pages = {"https://r.org/download": b"see https://r.org/fg_manifest.tsv) and again "
                                       b"https://r.org/fg_manifest.tsv",
             "https://api.org/b": b"[]",
             "https://r.org/fg_manifest.tsv?dl=1": b"a\tb\n",
             "https://gc.org/s?pubmed_id=111&page=0": page0,
             "https://gc.org/s?pubmed_id=111&page=1": b"{}"}
    client = Client(pages)
    manifest = fr.fetch_all(fr.Store(tmp_path, client, TODAY), sources(), DICTIONARY)
    assert ("https://api.org/b", {"Authorization": "Bearer secret"}) in client.calls
    assert manifest["man"] == {"url": "https://r.org/fg_manifest.tsv?dl=1",
                               "url_as_documented": "https://r.org/fg_manifest.tsv",
                               "found_in": "doc", "access_date": "2026-10-10", "bytes": 4,
                               "sha256": hashlib.sha256(b"a\tb\n").hexdigest()}
    assert {"gwas_catalog_pmid111_page0", "gwas_catalog_pmid111_page1"} <= set(manifest)
    assert "secret" not in (tmp_path / "manifest.json").read_text()
    again = Client(pages)
    fr.fetch_all(fr.Store(tmp_path, again, TODAY), sources(), DICTIONARY)
    assert again.calls == []


def test_an_ambiguous_documented_link_stops_the_fetch(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_NAME", "x")
    pages = {"https://r.org/download": b"https://r.org/aa_manifest.tsv https://r.org/bb_manifest.tsv",
             "https://api.org/b": b"[]"}
    with pytest.raises(fr.FetchError):
        fr.fetch_all(fr.Store(tmp_path, Client(pages), TODAY), sources(), DICTIONARY)


def test_a_request_is_tried_three_times_sixty_seconds_apart(tmp_path):
    waits = []
    client = Client({"https://x.org": Response(b"", 500)})
    store = fr.Store(tmp_path, client, TODAY, sleep=waits.append)
    with pytest.raises(fr.FetchError):
        store.get("k", "https://x.org")
    assert len(client.calls) == 3 and waits == [60, 60]
    assert "k" not in store.manifest
