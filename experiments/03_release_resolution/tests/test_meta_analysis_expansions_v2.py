import datetime
import hashlib
import json
import os

import pytest

import meta_analysis_expansions_v2 as mx

DICTIONARY = [{"name": n} for n in ("A R1", "B 2020", "A R1 + B meta-analysis", "C and D", "E")]
DICT_SHA = "d" * 64
URL = "https://example.org/doc"
TODAY = datetime.date(2026, 10, 10)


def sha(body):
    return hashlib.sha256(body).hexdigest()


def store(tmp_path, docs):
    raw = tmp_path / "raw"
    raw.mkdir()
    manifest = {}
    for key, body in docs.items():
        (raw / key).write_bytes(body)
        manifest[key] = {"url": URL, "access_date": "2026-10-09", "sha256": sha(body)}
    (raw / "manifest_v2.json").write_text(json.dumps(manifest))
    return raw


def decisions(**over):
    rows = [{"name": "A R1 + B meta-analysis", "decision": "expand", "documents": ["doc"],
             "basis": "external_documentation",
             "components": [{"component": "A R1", "endpoint": "X", "ancestry": "EUR",
                             "version": "1", "role": "meta_analysis_component"},
                            {"component": "B 2020", "endpoint": "X", "ancestry": "EUR",
                             "version": "1", "role": "meta_analysis_component"}]},
            {"name": "C and D", "decision": "omit", "reason_category": "single_study_release",
             "reason": "one study", "documents": [], "basis": "frozen_dictionary"}]
    return {"dictionary": {"version": "v1", "sha256": DICT_SHA}, "documents": {"doc": URL},
            "rows": over.get("rows", rows)}


def test_rows_carry_provenance_or_the_dictionary_by_basis_in_the_registered_columns(tmp_path):
    raw = store(tmp_path, {"doc": b"documentation"})
    expanded, omitted = mx.build(decisions(), DICTIONARY, DICT_SHA, raw)
    assert [list(e) for e in expanded] == [mx.EXPANDED] * 2
    assert [e["component_dictionary_row"] for e in expanded] == ["A R1", "B 2020"]
    assert expanded[0] == {"meta_analysis_row": "A R1 + B meta-analysis",
                                "component_dictionary_row": "A R1", "endpoint": "X",
                                "ancestry": "EUR", "analysis_version": "1",
                                "component_role": "meta_analysis_component",
                                "provenance_url": URL, "access_date": "2026-10-09",
                                "documents_sha256": sha(b"documentation")}
    assert omitted == [{"meta_analysis_row": "C and D", "reason_category": "single_study_release",
                        "reason": "one study", "basis": "frozen_dictionary",
                        "provenance_url": "", "access_date": "", "documents_sha256": "",
                        "dictionary_version": "v1", "dictionary_sha256": DICT_SHA}]
    assert mx.EXPANDED == ["meta_analysis_row", "component_dictionary_row", "endpoint",
                           "ancestry", "analysis_version", "component_role", "provenance_url",
                           "access_date", "documents_sha256"]


def test_an_omission_on_two_documents_lists_each_in_the_same_order(tmp_path):
    raw = store(tmp_path, {"doc": b"one", "doc2": b"two"})
    d = decisions()
    d["documents"]["doc2"] = URL
    d["rows"][1] |= {"basis": "external_documentation", "documents": ["doc2", "doc"]}
    _, omitted = mx.build(d, DICTIONARY, DICT_SHA, raw)
    assert omitted[0]["documents_sha256"] == f"{sha(b'two')}|{sha(b'one')}"
    assert omitted[0]["access_date"] == "2026-10-09|2026-10-09"


@pytest.mark.parametrize("change", ["missing_row", "unknown_component", "blank_field",
                                    "changed_document", "no_reason", "self_component",
                                    "dictionary_basis_with_document",
                                    "external_basis_without_document", "no_basis",
                                    "other_dictionary", "url_differs"])
def test_a_decision_that_does_not_fit_stops_the_build(tmp_path, change):
    raw = store(tmp_path, {"doc": b"documentation"})
    d = decisions()
    rows = d["rows"]
    dict_sha = DICT_SHA
    if change == "missing_row":
        d = decisions(rows=rows[:1])
    elif change == "unknown_component":
        rows[0]["components"][1]["component"] = "Z 1999"
    elif change == "blank_field":
        rows[0]["components"][0]["ancestry"] = " "
    elif change == "changed_document":
        (raw / "doc").write_bytes(b"other")
    elif change == "no_reason":
        rows[1]["reason"] = ""
    elif change == "self_component":
        rows[0]["components"][0]["component"] = "A R1 + B meta-analysis"
    elif change == "dictionary_basis_with_document":
        rows[1]["documents"] = ["doc"]
    elif change == "external_basis_without_document":
        rows[1]["basis"] = "external_documentation"
    elif change == "no_basis":
        del rows[1]["basis"]
    elif change == "other_dictionary":
        dict_sha = "e" * 64
    elif change == "url_differs":
        d["documents"]["doc"] = "https://example.org/other"
    with pytest.raises(mx.ExpansionError):
        mx.build(d, DICTIONARY, dict_sha, raw)


class Client:
    def __init__(self):
        self.urls = []

    def get(self, url):
        self.urls.append(url)

        class Response:
            content = b"page"

            def raise_for_status(self):
                return None
        return Response()


def test_fetch_stores_each_document_once_with_url_date_and_hash(tmp_path):
    client = Client()
    manifest = mx.fetch(client, decisions(), tmp_path / "raw", TODAY)
    assert manifest == {"doc": {"url": URL, "access_date": "2026-10-10", "sha256": sha(b"page")}}
    again = Client()
    mx.fetch(again, decisions(), tmp_path / "raw", datetime.date(2026, 10, 11))
    assert client.urls == [URL] and again.urls == []
    assert mx.stored(tmp_path / "raw")["doc"]["access_date"] == "2026-10-10"


def test_fetch_adopts_a_matching_first_version_document_with_its_file_date(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "doc").write_bytes(b"old")
    stamp = datetime.datetime(2026, 10, 1, 12, tzinfo=datetime.UTC).timestamp()
    os.utime(raw / "doc", (stamp, stamp))
    (raw / "manifest.json").write_text(json.dumps({"doc": sha(b"old")}))
    client = Client()
    manifest = mx.fetch(client, decisions(), raw, TODAY)
    assert client.urls == []
    assert manifest["doc"] == {"url": URL, "access_date": "2026-10-01", "sha256": sha(b"old")}


def test_fetch_refetches_a_first_version_document_whose_hash_does_not_match(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "doc").write_bytes(b"changed")
    (raw / "manifest.json").write_text(json.dumps({"doc": sha(b"old")}))
    client = Client()
    manifest = mx.fetch(client, decisions(), raw, TODAY)
    assert client.urls == [URL]
    assert manifest["doc"] == {"url": URL, "access_date": "2026-10-10", "sha256": sha(b"page")}
