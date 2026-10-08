import json

import pytest

import release_resolution_availability as av
from test_h2_unresolved_diagnostic import CLAIMS


def test_the_two_sets_are_the_blocking_records_and_every_record_of_a_repeated_pair():
    sets = av.record_sets(CLAIMS)
    # r6 reports a pair one family reports; r4, r5 and r7 name one release on both sides
    assert sets["multi"] == {"r1", "r2", "r3", "r4", "r5", "r7"}
    assert sets["blocking"] == {"r1", "r2", "r3"}


def rec(rid, pmid=None, doi=None, kind="journal"):
    return {"record_id": rid, "pmid": pmid, "doi": doi, "kind": kind, "member_ids": []}


EPMC = {"1": {"pmid": "1", "isOpenAccess": "Y", "pmcid": "PMC1", "inEPMC": "Y", "hasSuppl": "Y"},
        "2": {"pmid": "2", "isOpenAccess": "N", "pmcid": "PMC2", "inEPMC": "Y", "hasSuppl": "N"},
        "3": {"pmid": "3", "isOpenAccess": "N", "inEPMC": "N", "hasSuppl": "N"},
        "4": {"pmid": "4", "isOpenAccess": "N", "inEPMC": "N"},
        "9": {"pmid": "9", "isOpenAccess": "Y", "pmcid": "PMC9", "hasSuppl": "Y"}}
OPENALEX = {"doi:10.1/three": {"is_oa": True, "oa_status": "hybrid"},
            "pmid:4": {"is_oa": False, "oa_status": "closed"},
            "doi:10.1/w": {"is_oa": True, "oa_status": "green"}}


@pytest.mark.parametrize("record,category,suppl", [
    (rec("d", "9"), "full_text_on_disk", "Y"),
    (rec("a", "1"), "open_access_full_text_in_europe_pmc", "Y"),
    (rec("b", "2"), "full_text_in_europe_pmc_not_flagged_open_access", "N"),
    (rec("c", "3", "https://doi.org/10.1/THREE"), "open_access_by_openalex_only", "N"),
    (rec("e", "4"), "closed", None),
    (rec("w", None, "10.1/w", "preprint"), "open_access_by_openalex_only", None),
    (rec("x", "77"), "no_status_found", None),
    (rec("y"), "no_status_found", None)])
def test_a_record_takes_the_first_category_that_fits(record, category, suppl):
    got = av.status_of(record, {"d"}, EPMC, OPENALEX)
    assert got["category"] == category
    assert got["europe_pmc_lists_supplementary_files"] == suppl


def test_the_tally_counts_categories_supplements_and_what_is_readable():
    records = [rec("d", "9"), rec("a", "1"), rec("b", "2"), rec("e", "4"), rec("x", "77")]
    status = {r["record_id"]: av.status_of(r, {"d"}, EPMC, OPENALEX) for r in records}
    made = av.tally({"d", "a", "b", "e", "x"}, status)
    assert made["records"] == 5
    assert made["by_category"] == {
        "full_text_on_disk": 1, "open_access_full_text_in_europe_pmc": 1,
        "full_text_in_europe_pmc_not_flagged_open_access": 1,
        "open_access_by_openalex_only": 0, "closed": 1, "no_status_found": 1}
    assert (made["with_a_full_text_on_disk_or_reachable"], made["closed_or_no_status"]) == (3, 2)
    assert made["europe_pmc_lists_supplementary_files"] == {
        "yes": 2, "no": 1, "no_europe_pmc_record_or_field": 2}
    assert made["supplementary_files_listed_by_category"] == {
        "full_text_on_disk": 1, "open_access_full_text_in_europe_pmc": 1}
    assert av.tally({"a"}, status)["records"] == 1


class Client:
    def __init__(self):
        self.calls = []

    def get(self, url, params=None, headers=None):
        self.calls.append((url, params, headers))
        body = ({"resultList": {"result": [{"pmid": "1", "isOpenAccess": "Y", "pmcid": "PMC1"}]}}
                if url == av.EPMC else
                {"results": [{"id": "https://openalex.org/W5", "doi": "https://doi.org/10.1/A",
                              "ids": {"pmid": "https://pubmed.ncbi.nlm.nih.gov/1"},
                              "open_access": {"is_oa": True, "oa_status": "gold"}}]})

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return body
        return Response()


def test_fetch_asks_for_status_fields_only_stores_each_response_and_asks_once(
        tmp_path, monkeypatch):
    monkeypatch.delenv("OPEN_ALEX_API_KEY", raising=False)
    records = [rec("a", "1", "10.1/a"), rec("b", "2"), rec("w", None, "10.1/w")]
    client = Client()
    made = av.fetch(client, tmp_path / "raw", records)
    assert made["with_a_pmid"] == 2 and made["responses_stored"] == 3
    epmc_call = next(c for c in client.calls if c[0] == av.EPMC)
    assert epmc_call[1]["resultType"] == "lite" and "EXT_ID:1 OR EXT_ID:2" in epmc_call[1]["query"]
    for url, params, headers in client.calls:
        assert "mailto" not in json.dumps(params) and "@" not in json.dumps(params)
        assert headers in (None, {})
        if url == av.OPENALEX:
            assert params["select"] == "id,doi,ids,open_access"
    again = Client()
    av.fetch(again, tmp_path / "raw", records)
    assert again.calls == []
    epmc, openalex = av.read_status(tmp_path / "raw")
    assert epmc["1"]["pmcid"] == "PMC1"
    assert openalex["doi:10.1/a"] == openalex["pmid:1"] == openalex["openalex:W5"] == {
        "is_oa": True, "oa_status": "gold"}
    monkeypatch.setenv("OPEN_ALEX_API_KEY", "k")
    keyed = Client()
    av.fetch(keyed, tmp_path / "raw2", records[:1])
    assert [c[2] for c in keyed.calls if c[0] == av.OPENALEX] == [{"Authorization": "Bearer k"}]
    assert not any("k" == p for p in map(str, (tmp_path / "raw2").iterdir()))
