import io
import json
import zipfile

import retrieve_sources as rs
import retrieve_sources_v2 as rs2

XML = (b"<article><front><abstract><p>Abstract text.</p></abstract></front><body>"
       b"<sec><title>Methods</title><p>We used FinnGen R10.</p></sec></body></article>")


class Response:
    def __init__(self, status, content=b"", data=None):
        self.status_code, self.content, self._data = status, content, data

    def json(self):
        return self._data


class Client:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get(self, url, params=None):
        key = url + ("?" + params["query"] if params else "")
        self.calls.append(key)
        return self.routes.get(key, Response(404))


def search(query, hit):
    return {f"{rs.EPMC}/search?{query}": Response(200, data={"resultList": {"result": [hit]}})}


def zipped(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


def store_into(held):
    def store(data):
        key = rs.sha256(data)
        held[key] = data
        return key
    return store


def test_r1_is_rendered_as_in_the_first_registration_and_no_supplement_is_requested():
    routes = {**search("EXT_ID:1 AND SRC:MED", {"pmcid": "PMC9", "hasSuppl": "Y"}),
              f"{rs.EPMC}/PMC9/fullTextXML": Response(200, XML),
              f"{rs.EPMC}/PMC9/supplementaryFiles": Response(200, zipped({"notes.txt": b"x"}))}
    client = Client(routes)
    rec = {"record_id": "1", "pmid": "1", "kind": "journal"}
    out = rs2.retrieve_record(client, rec, [], store_into({}), sleep=lambda s: None)
    assert not any("supplementaryFiles" in c for c in client.calls)
    assert [s["route"] for s in out["sources"]] == ["R1"]
    first = rs.retrieve_record(Client(routes), rec, [], store_into({}), sleep=lambda s: None)
    r1 = [s for s in first["sources"] if s["route"] == "R1"]
    assert out["sources"][0]["text"] == r1[0]["text"]
    assert out["sources"][0]["text_sha256"] == r1[0]["text_sha256"]
    assert out["versions"][0]["europe_pmc_has_supplements"] == "Y"
    assert out["status"] == "retrieved"


def test_without_r2_the_first_registration_differs_only_by_its_r2_sources_and_failures():
    routes = {**search("EXT_ID:4 AND SRC:MED", {"pmcid": "PMC4", "hasSuppl": "Y",
                                               "commentCorrectionList": {"commentCorrection": [
                                                   {"id": "5", "source": "MED",
                                                    "type": "Erratum in"}]}}),
              **search("EXT_ID:5 AND SRC:MED", {"pmcid": "PMC5", "hasSuppl": "N"}),
              f"{rs.EPMC}/PMC5/fullTextXML": Response(200, XML)}
    rec = {"record_id": "4", "pmid": "4", "doi": "10.1/four", "kind": "journal"}
    oa = {rs.OPENALEX + "doi:10.1/four": Response(200, data={"best_oa_location": {
        "pdf_url": "https://example.org/a.html"}}),
          "https://example.org/a.html": Response(200, b"<html><p>Open text</p></html>")}
    new = rs2.retrieve_record(Client(routes | oa), rec, [], store_into({}), sleep=lambda s: None)
    old = rs.retrieve_record(Client(routes | oa), rec, [], store_into({}), sleep=lambda s: None)

    def strip(out):
        return ([{k: v for k, v in s.items() if k != "retrieved_utc"} for s in out["sources"]
                 if s["route"] != "R2"], [f for f in out["failures"] if f["route"] != "R2"])

    assert strip(new) == strip(old)
    assert [(s["route"], s["version"]) for s in new["sources"]] == [("R3", "journal"),
                                                                     ("R1", "correction")]
    assert not any(f["route"] == "R2" for f in new["failures"])


def test_a_failed_request_is_tried_three_times_sixty_seconds_apart_then_no_source():
    waits = []
    client = Client({})
    out = rs2.retrieve_record(client, {"record_id": "2", "pmid": "2", "doi": "10.1/x",
                                       "kind": "journal"}, [], store_into({}), sleep=waits.append)
    assert out["status"] == "no_source"
    assert client.calls.count(f"{rs.EPMC}/search?EXT_ID:2 AND SRC:MED") == 3
    assert set(waits) == {60}


def test_a_journal_record_without_full_text_falls_back_to_its_family_preprint():
    routes = {**search("EXT_ID:3 AND SRC:MED", {"hasSuppl": "N"}),
              rs.OPENALEX + "doi:10.1/three": Response(200, data={"best_oa_location": None}),
              **search("EXT_ID:PPR7 AND SRC:PPR", {"hasSuppl": "Y"}),
              f"{rs.EPMC}/PPR7/fullTextXML": Response(200, XML)}
    out = rs2.retrieve_record(Client(routes), {"record_id": "3", "pmid": "3",
                                               "doi": "10.1/three", "kind": "journal"},
                              [{"record_id": "PPR7", "kind": "preprint"}], store_into({}),
                              sleep=lambda s: None)
    assert [(s["route"], s["version"]) for s in out["sources"]] == [("R1", "preprint")]


def test_outside_scope_is_the_corpus_minus_the_scope_with_family_preprints():
    claims = ["111:000", "111:001", "222:000", "PPR9:000", "333:000"]
    search_records = {r: {"record_id": r, "kind": "preprint" if r.startswith("PPR") else "journal"}
                      for r in ("111", "222", "333", "PPR9")}
    families = {"families": {"f1": ["111", "PPR9"], "f2": ["222"], "f3": ["333"]}}
    out = rs2.outside_scope(claims, ["222"], search_records, families)
    assert [u["record"]["record_id"] for u in out] == ["111", "333", "PPR9"]
    assert [p["record_id"] for p in out[0]["family_preprints"]] == ["PPR9"]
    assert out[1]["family_preprints"] == []


def test_the_listing_carries_no_text_and_no_url():
    routes = {**search("EXT_ID:1 AND SRC:MED", {"pmcid": "PMC9", "hasSuppl": "N"}),
              f"{rs.EPMC}/PMC9/fullTextXML": Response(200, XML)}
    out = rs2.retrieve_record(Client(routes), {"record_id": "1", "pmid": "1", "kind": "journal"},
                              [], store_into({}), sleep=lambda s: None)
    blob = json.dumps(rs2.listing(out))
    assert "FinnGen" not in blob and "http" not in blob
    assert rs2.listing(out)["sources"][0]["text_sha256"] == out["sources"][0]["text_sha256"]
