import io
import json
import zipfile

import openpyxl
import pytest

import abstract_characters as ac
import estimate_cost as ec
import retrieve_sources as rs

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


def xlsx(rows):
    book = openpyxl.Workbook()
    for row in rows:
        book.active.append(row)
    buf = io.BytesIO()
    book.save(buf)
    return buf.getvalue()


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


def test_r1_renders_the_body_without_the_abstract_and_r2_converts_each_supplement():
    supp = zipped({"Table S1.xlsx": xlsx([["cohort", "release"], ["FinnGen", "R10"]]),
                   "notes.txt": b"plain notes", "movie.mp4": b"\x00\x01"})
    routes = {**search("EXT_ID:1 AND SRC:MED", {"pmcid": "PMC9", "hasSuppl": "Y"}),
              f"{rs.EPMC}/PMC9/fullTextXML": Response(200, XML),
              f"{rs.EPMC}/PMC9/supplementaryFiles": Response(200, supp)}
    held = {}
    out = rs.retrieve_record(Client(routes), {"record_id": "1", "pmid": "1", "kind": "journal"},
                             [], store_into(held), sleep=lambda s: None)
    assert out["status"] == "retrieved"
    r1 = [s for s in out["sources"] if s["route"] == "R1"][0]
    assert r1["text"] == "## Methods\nWe used FinnGen R10." and "Abstract" not in r1["text"]
    assert r1["characters"] == len(r1["text"])
    r2 = {s["name"]: s for s in out["sources"] if s["route"] == "R2"}
    assert r2["supplementaryFiles.zip/Table S1.xlsx"]["text"] == (
        "## sheet Sheet\ncohort\trelease\nFinnGen\tR10")
    assert r2["supplementaryFiles.zip/notes.txt"]["text"] == "plain notes"
    assert r2["supplementaryFiles.zip/movie.mp4"]["text"] is None
    assert r2["supplementaryFiles.zip/movie.mp4"]["reason"] == "type_not_accepted"


def test_no_supplement_request_when_europe_pmc_lists_none():
    routes = {**search("EXT_ID:1 AND SRC:MED", {"pmcid": "PMC9", "hasSuppl": "N"}),
              f"{rs.EPMC}/PMC9/fullTextXML": Response(200, XML)}
    client = Client(routes)
    rs.retrieve_record(client, {"record_id": "1", "pmid": "1", "kind": "journal"}, [],
                       store_into({}), sleep=lambda s: None)
    assert not any("supplementaryFiles" in c for c in client.calls)


def test_a_failed_request_is_tried_three_times_sixty_seconds_apart_then_no_source():
    waits = []
    client = Client({})
    out = rs.retrieve_record(client, {"record_id": "2", "pmid": "2", "doi": "10.1/x",
                                      "kind": "journal"}, [], store_into({}), sleep=waits.append)
    assert out["status"] == "no_source"
    assert client.calls.count(f"{rs.EPMC}/search?EXT_ID:2 AND SRC:MED") == 3
    assert waits and set(waits) == {60}


def test_r3_only_without_a_europe_pmc_full_text_and_a_journal_record_falls_back_to_a_preprint():
    pdfless = {**search("EXT_ID:3 AND SRC:MED", {"hasSuppl": "N"}),
               rs.OPENALEX + "doi:10.1/three": Response(200, data={"best_oa_location": None}),
               **search("EXT_ID:PPR7 AND SRC:PPR", {"hasSuppl": "N"}),
               f"{rs.EPMC}/PPR7/fullTextXML": Response(200, XML)}
    out = rs.retrieve_record(Client(pdfless), {"record_id": "3", "pmid": "3", "doi": "10.1/three",
                                               "kind": "journal"},
                             [{"record_id": "PPR7", "kind": "preprint"}], store_into({}),
                             sleep=lambda s: None)
    assert [(s["route"], s["version"]) for s in out["sources"]] == [("R1", "preprint")]
    assert {"route": "R3", "version": "journal", "url": None,
            "reason": "no_open_access_location"} in out["failures"]
    assert out["status"] == "retrieved"


def test_a_linked_correction_is_retrieved_as_its_own_version():
    routes = {**search("EXT_ID:4 AND SRC:MED", {"pmcid": "PMC4", "hasSuppl": "N",
                                               "commentCorrectionList": {"commentCorrection": [
                                                   {"id": "5", "source": "MED",
                                                    "type": "Erratum in"},
                                                   {"id": "6", "source": "MED",
                                                    "type": "Comment in"}]}}),
              f"{rs.EPMC}/PMC4/fullTextXML": Response(200, XML),
              **search("EXT_ID:5 AND SRC:MED", {"pmcid": "PMC5", "hasSuppl": "N"}),
              f"{rs.EPMC}/PMC5/fullTextXML": Response(200, XML)}
    out = rs.retrieve_record(Client(routes), {"record_id": "4", "pmid": "4", "kind": "journal"},
                             [], store_into({}), sleep=lambda s: None)
    assert [(s["route"], s["version"]) for s in out["sources"]] == [("R1", "journal"),
                                                                     ("R1", "correction")]


@pytest.mark.parametrize("name,data,reason", [
    ("scan.pdf", b"%PDF-1.4 no text layer", "pdf_without_text_layer"),
    ("big.csv", b"a" * (rs.TABLE_LIMIT + 1), "table_over_50_mb"),
    ("slides.pptx", b"PK\x03\x04", "type_not_accepted"),
    ("broken.xlsx", b"PK\x03\x04 not a workbook", "unreadable_BadZipFile")])
def test_unreadable_files_are_counted_with_their_reason(name, data, reason):
    [entry] = rs.convert(name, data)
    assert entry["text"] is None and entry["reason"] == reason


def test_html_text_drops_scripts_and_keeps_lines():
    assert rs.html_text(b"<html><script>x=1</script><p>One</p><p>Two  words</p></html>") == (
        "One\nTwo words")


def result(rid, status, full, supps):
    sources = ([{"route": "R1", "text": "x" * full, "characters": full}] if full else []) + [
        {"route": "R2", "text": "y" * n, "characters": n} for n in supps]
    return {"record_id": rid, "status": status, "sources": sources}


def test_the_estimate_counts_requests_by_the_input_limit_and_prices_each_model():
    results = [result("a", "retrieved", 100_000, [350_000]), result("b", "retrieved", 50_000, []),
               result("c", "no_source", 0, [])]
    out = ec.estimate(results, {"a": 2_000, "b": 1_000, "c": 1_500}, 75_000)
    rows = {r["record_id"]: r for r in out["per_record"]}
    assert rows["a"]["requests"] == 2 and rows["b"]["requests"] == 1 and rows["c"]["requests"] == 1
    assert out["requests_per_model_for_coding"] == 4
    sol = out["by_model"]["gpt-6.1-sol"]["coding"]
    assert sol["new_input_tokens"] == round((500_000 + 75_000) / 4.28)
    assert sol["cached_input_tokens"] == round(3 * 75_000 / 4.28)
    assert sol["output_tokens"] == 4 * 1_500
    assert "c2_exhaustive_pass" in out["by_model"]["gpt-6.1-sol"]
    assert "c2_exhaustive_pass" not in out["by_model"]["claude-sonnet-5-5"]
    assert out["total_usd"] == pytest.approx(sum(
        p["usd"] for m in out["by_model"].values() for p in m.values()), abs=0.011)
    assert out["by_status"] == {"no_source": 1, "retrieved": 2}


def test_abstract_characters_counts_each_scope_record_and_refuses_a_missing_one():

    rows = [{"pmid": "1", "abstract": "abc"}, {"pmid": "2", "abstract": None},
            {"pmid": "3", "abstract": "zz"}]
    assert ac.characters(["1", "2"], rows) == {"1": 3, "2": 0}
    with pytest.raises(ac.AbstractError):
        ac.characters(["1", "9"], rows)
