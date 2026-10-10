import hashlib
import json

import pytest

import meta_analysis_expansions as mx

DICTIONARY = [{"name": n} for n in ("A R1", "B 2020", "A R1 + B meta-analysis", "C and D", "E")]


def store(tmp_path, docs):
    raw = tmp_path / "raw"
    raw.mkdir()
    manifest = {}
    for key, body in docs.items():
        (raw / key).write_bytes(body)
        manifest[key] = hashlib.sha256(body).hexdigest()
    (raw / "manifest.json").write_text(json.dumps(manifest))
    return raw


def decisions(**over):
    rows = [{"name": "A R1 + B meta-analysis", "decision": "expand", "documents": ["doc"],
             "components": [{"component": "A R1", "endpoint": "X", "ancestry": "EUR",
                             "version": "1", "role": "meta_analysis_component"},
                            {"component": "B 2020", "endpoint": "X", "ancestry": "EUR",
                             "version": "1", "role": "meta_analysis_component"}]},
            {"name": "C and D", "decision": "omit", "reason_category": "single_study_release",
             "reason": "one study", "documents": []}]
    return {"documents": {"doc": "https://example.org/doc"}, "rows": over.get("rows", rows)}


def test_an_expanded_row_gives_one_line_per_component_and_an_omitted_row_its_reason(tmp_path):
    raw = store(tmp_path, {"doc": b"documentation"})
    expanded, omitted = mx.build(decisions(), DICTIONARY, raw)
    assert [e["component"] for e in expanded] == ["A R1", "B 2020"]
    assert expanded[0]["documents_sha256"] == hashlib.sha256(b"documentation").hexdigest()
    assert omitted == [{"meta_analysis_row": "C and D", "reason_category": "single_study_release",
                        "reason": "one study", "documents_sha256": ""}]
    assert mx.meta_rows(DICTIONARY) == ["A R1 + B meta-analysis", "C and D"]


@pytest.mark.parametrize("change", ["missing_row", "unknown_component", "blank_field",
                                    "changed_document", "no_reason", "self_component"])
def test_a_decision_that_does_not_fit_stops_the_build(tmp_path, change):
    raw = store(tmp_path, {"doc": b"documentation"})
    d = decisions()
    rows = d["rows"]
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
    with pytest.raises(mx.ExpansionError):
        mx.build(d, DICTIONARY, raw)


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


def test_fetch_stores_each_document_once_with_its_hash(tmp_path):
    client = Client()
    manifest = mx.fetch(client, decisions(), tmp_path / "raw")
    assert manifest == {"doc": hashlib.sha256(b"page").hexdigest()}
    again = Client()
    mx.fetch(again, decisions(), tmp_path / "raw")
    assert client.urls == ["https://example.org/doc"] and again.urls == []
