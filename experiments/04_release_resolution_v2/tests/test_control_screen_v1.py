import csv
import hashlib
import json
import pathlib
import random

import pytest

import coding_queue as q
import control_screen_v1 as cs
import source_scanner_v2 as scanner

EXPERIMENTS = pathlib.Path(__file__).resolve().parents[2]
PATTERNS = json.loads((EXPERIMENTS / "03_release_resolution/reference/"
                       "c1_scanner_patterns_v2.json").read_text())
with (EXPERIMENTS / "03_release_resolution/reference/accession_releases.csv").open(newline="") as f:
    TABLE = list(csv.DictReader(f))
with (EXPERIMENTS / "02_claims_meta/dataset_dictionary.csv").open(newline="") as f:
    DICTIONARY = list(csv.DictReader(f))
MAPPER = scanner.Mapper(PATTERNS, TABLE, DICTIONARY)
SIDE_ROWS = {s: sorted(r["name"] for r in DICTIONARY if r["side"] == s) for s in ("pqtl", "outcome")}

PROSE = ("Introduction text. Outcome summary statistics came from FinnGen R10 for gout. "
         "The GWAS of gout in FinnGen release 10 was used again.\nOther line.")


def key(route, n, text):
    return f"{route}:{n}:{hashlib.sha256(text.encode()).hexdigest()[:16]}"


def match(rec, ident, source_key, unit_id, side="outcome", row="FinnGen R10"):
    return {"record_id": rec, "source_key": source_key, "unit_id": unit_id, "kind": "release",
            "type": "FinnGen", "identifier": ident, "expected_row": row, "side": side}


def test_the_frozen_scanner_finds_each_identifier_as_written_on_a_retrieved_text():
    out = cs.scan_record("r1", [{"route": "R1", "type": "JATS XML", "text": PROSE}], PATTERNS,
                         MAPPER)
    found = {(m["identifier"], m["expected_row"], m["side"]) for m in out["found"]}
    assert found == {("FinnGen R10", "FinnGen R10", "outcome"),
                     ("FinnGen release 10", "FinnGen R10", "outcome")}


def test_one_candidate_per_record_and_identifier_the_first_by_source_and_unit():
    k1, k2 = key("R1", 1, "a"), key("R3", 2, "b")
    found = [match("r1", "FinnGen R10", k2, f"{k2}:0:0"),
             match("r1", "FinnGen R10", k1, f"{k1}:5:1"),
             match("r1", "FinnGen R10", k1, f"{k1}:3:0"),
             match("r1", "FinnGen release 10", k1, f"{k1}:9:0"),
             match("r2", "FinnGen R10", k1, f"{k1}:1:0"),
             match("r3", "FinnGen R10", key("R2", 1, "c"), "x")]
    got = cs.candidates(found, SIDE_ROWS)
    assert len(got) == 3
    by = {(r["record_id"], r["name_as_written"]): r for r in got}
    assert by[("r1", "FinnGen R10")]["control_unit_id"] == f"{k1}:3:0"
    assert ("r3", "FinnGen R10") not in by
    assert by[("r2", "FinnGen R10")]["row_id"] == q.row_id("r2", "outcome", "FinnGen R10", "control")
    assert [r["row_id"] for r in got] == sorted(r["row_id"] for r in got)
    assert all(r["identifier_kind"] == "release" and r["kind"] == "control" for r in got)
    assert all(r["candidates"] == SIDE_ROWS["outcome"] for r in got)


def test_every_candidate_of_a_record_is_kept_whatever_their_number():
    k = key("R1", 1, "a")
    found = [match("r1", f"ebi-a-GCST9{i:05d}", k, f"{k}:{i}:0") for i in range(8)]
    assert len(cs.candidates(found, SIDE_ROWS)) == 8


def test_claims_are_every_claim_record_of_the_record():
    got = cs.claim_queue(["111:001", "111:000", "222:000", "333:000"], ["111", "333", "444"])
    assert got == [{"record_id": "111", "claim_record_ids": ["111:000", "111:001"]},
                   {"record_id": "333", "claim_record_ids": ["333:000"]}]


def test_the_send_order_is_the_sorted_ids_shuffled_by_its_own_seed():
    ids = [f"{i:012x}" for i in range(60)]
    expected = sorted(ids)
    random.Random(20261034).shuffle(expected)
    assert cs.SEND_SEED == 20261034 and cs.order(list(reversed(ids))) == expected


def judged(mark):
    if mark == "FAILED":
        return {"state": "failed", "decision": None}
    return {"state": "accepted", "decision": {"mark": mark}}


@pytest.mark.parametrize("a,b,label", [
    ("valid", "valid", "eligible"), ("invalid", "invalid", "invalid"),
    ("valid", "invalid", "disputed"), ("invalid", "valid", "disputed"),
    ("valid", "cannot_mark", "cannot_mark"), ("cannot_mark", "invalid", "cannot_mark"),
    ("cannot_mark", "cannot_mark", "cannot_mark"), ("valid", "FAILED", "failed_twice"),
    ("FAILED", "FAILED", "failed_twice")])
def test_only_two_valid_marks_make_a_candidate_eligible(a, b, label):
    assert cs.classify(judged(a), judged(b)) == label


def test_a_pending_or_missing_answer_is_refused():
    with pytest.raises(cs.ScreenError):
        cs.classify({"state": "pending"}, judged("valid"))
    with pytest.raises(cs.ScreenError):
        cs.classify(None, judged("valid"))


def test_the_draw_shuffles_sorted_ids_by_its_seed_and_caps_per_record_and_overall():
    rows = [{"row_id": f"{i:012x}", "record_id": f"rec{i % 40}"} for i in range(400)]
    got = cs.draw(list(reversed(rows)))
    pool = sorted(rows, key=lambda r: r["row_id"])
    random.Random(20261033).shuffle(pool)
    expected, per = [], {}
    for r in pool:
        if len(expected) < 150 and per.get(r["record_id"], 0) < 5:
            expected.append(r)
            per[r["record_id"]] = per.get(r["record_id"], 0) + 1
    assert got == expected and len(got) == 150
    assert max(sum(r["record_id"] == x["record_id"] for r in got) for x in got) == 5
    few = [{"row_id": f"{i:012x}", "record_id": "only"} for i in range(9)]
    assert len(cs.draw(few)) == 5
