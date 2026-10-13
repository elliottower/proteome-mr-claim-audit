import json
import pathlib

import jsonschema
import pytest

import coding_packets as cp

HERE = pathlib.Path(__file__).resolve().parents[1]
ACC = cp.read_accessions(HERE / "reference" / "c1_scanner_patterns_v2.json",
                         HERE / "reference" / "accession_releases.csv")
ROWS = [{"row_id": "a1", "record_id": "r1", "side": "pqtl", "name_as_written": "not stated",
         "outcomes_as_written": [], "candidates": ["UKB-PPP discovery"]},
        {"row_id": "b2", "record_id": "r1", "side": "outcome", "name_as_written": "FinnGen",
         "outcomes_as_written": ["asthma"], "candidates": ["FinnGen R10"]}]


def cut_file(rows, cut=True, text=None, kind="XLSX"):
    return {"cut": cut, "type": kind, "sha256": "e" * 64, "text": text,
            "rows": [{"table": 0, "line": l, "header": "h1\th2", "structural": False}
                     for l in rows] if cut else None}


def test_the_fixed_prompt_is_prompt_then_definitions():
    got = cp.fixed_prompt("Instructions.\n", "side,name\npqtl,X\n")
    assert got == "Instructions.\n\n## Dictionary definitions\n\nside,name\npqtl,X\n"


def test_a_packet_shows_what_the_framing_lists_and_nothing_else():
    p = cp.sa1_packets("r1", "T", ROWS, "We used FinnGen R10.", ACC)[0]
    assert set(p) == {"record_id", "title", "rows", "files", "accession_table_rows"}
    assert p["files"] == [{"file_id": "abstract", "kind": "abstract",
                           "text": "We used FinnGen R10."}]
    assert set(p["rows"][0]) == {"row_id", "side", "name", "candidates"}
    assert set(p["rows"][1]) == {"row_id", "side", "name", "outcomes_as_written", "candidates"}
    assert "record_id" not in p["rows"][0] and "family_id" not in json.dumps(p["rows"])


def test_accession_rows_are_the_matches_and_every_batch_row():
    batches = [r for r in ACC.batches]
    p = cp.sa1_packets("r1", "T", ROWS, "no accession here", ACC)[0]
    assert p["accession_table_rows"] == batches
    some = next(iter(ACC.by_id))
    q = cp.sa1_packets("r1", "T", ROWS, f"data from {some.lower()} were used", ACC)[0]
    assert ACC.by_id[some][0] in q["accession_table_rows"]
    if some.startswith("GCST"):
        r = cp.sa1_packets("r1", "T", ROWS, f"ebi-a-{some}", ACC)[0]
        assert ACC.by_id[some][0] in r["accession_table_rows"]


def test_full_text_packets_keep_every_source_line_within_the_limit(monkeypatch):
    monkeypatch.setattr(cp, "LIMIT", 300)
    abstract = "A" * 50
    full = [{"text": "F" * 120}]
    supps = [cut_file([f"r{i}\tx" * 3 for i in range(30)]),
             cut_file(None, cut=False, text="small supplement"),
             cut_file(None, cut=False, text="Sentence one. Sentence two. Sentence three. " * 20,
                      kind="PDF")]
    packets, log = cp.fulltext_packets("r1", "T", ROWS, abstract, full, supps, ACC)
    assert len(packets) > 1
    for p in packets:
        assert sum(len(f["text"]) for f in p["files"]) <= 300
        assert p["files"][0]["kind"] == "abstract"
    assert [f["kind"] for f in packets[0]["files"][:2]] == ["abstract", "full_text"]
    assert all(f["kind"] != "full_text" for p in packets[1:] for f in p["files"])
    text = "\n".join(f["text"] for p in packets for f in p["files"])
    for line in supps[0]["rows"]:
        assert line["line"] in text
    assert "small supplement" in text
    assert log and log[0]["file_id"] == "supplement_3"


def test_exhaustive_chunks_cover_every_line_repeat_headers_and_overlap_prose():
    table = "## sheet S\nh1\th2\n" + "\n".join(f"v{i}\tw{i}" for i in range(40))
    chunks = cp.exhaustive_chunks(table, "XLSX", 60)
    assert len(chunks) > 1
    for c in chunks[1:]:
        assert c["text"].split("\n")[0] == "h1\th2"
    joined = "\n".join(c["text"] for c in chunks)
    for i in range(40):
        assert f"v{i}\tw{i}" in joined
    prose = " ".join(f"Sentence {i} ends here." for i in range(30))
    pc = cp.exhaustive_chunks(prose, "PDF", 120)
    for a, b in zip(pc, pc[1:]):
        last_two = a["text"].split("\n")[-2:]
        assert b["text"].split("\n")[:2] == last_two
    assert all(c["sha256"] == cp.sha256(c["text"]) for c in pc)


def test_abstract_and_full_text_over_the_limit_stop(monkeypatch):
    monkeypatch.setattr(cp, "LIMIT", 100)
    with pytest.raises(cp.PacketError):
        cp.fulltext_packets("r1", "T", ROWS, "A" * 50, [{"text": "F" * 60}], [], ACC)


def test_a_diagnostic_packet_holds_the_chunk_alone():
    p = cp.diagnostic_packet("r1", "T", ROWS, {"text": "h\tx\nrow\t1\n"}, 7, ACC)
    assert p["files"] == [{"file_id": "removed_chunk_7", "kind": "supplement_chunk",
                           "text": "h\tx\nrow\t1\n"}]


def test_a_packet_answer_shape_fits_the_frozen_schema():
    schema = json.loads((HERE / "prompts" / "output_schema.json").read_text())
    p = cp.sa1_packets("r1", "T", ROWS, "x", ACC)[0]
    answer = {"record_id": p["record_id"], "rows": [{
        "row_id": r["row_id"], "identified_releases": [], "roles": [], "ancestry": [],
        "attribution_state": "unresolved", "unresolved_reasons": ["release_not_identified",
                                                                  "attribution_unresolved"],
        "decisive_evidence": [], "count_evidence": [], "abstract_transition": "none",
        "attribution_passage": None, "note": "n"} for r in p["rows"]]}
    jsonschema.validate(answer, schema)
