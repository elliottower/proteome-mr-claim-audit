import csv
import json

import pytest

import manual_dataset_coding as registered
import manual_coding_table as reasons
from dataset_relations import load_rows

ROWS = load_rows()


def row(record, value, second=None, **more):
    coded = value not in reasons.UNRESOLVED_VALUES
    base = {**dict.fromkeys(reasons.EXTENDED_FIELDS, ""), "record_id": record, "side": "outcome",
            "name_as_written": "FinnGen", "claude_code_value": value,
            "perplexity_value": value if second is None else second, "author_confirms": "yes",
            "status": "coded" if coded else "unresolved", "coder_id": "coder_1", "attempt": "1",
            "companion_source": "no"}
    if coded:
        base |= {"source_read": "full_text", "quote": "We used FinnGen R9.",
                 "citations_claim": "claims/x.yaml#outcome_1"}
    return base | more


def write(path, fields, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return path


TABLE = [row("p1", "FinnGen R9"), row("p2", reasons.ABSENT), row("p3", registered.NOT_STATED),
         row("p4", "FinnGen R5", companion_source="yes"),
         row("p5", reasons.ABSENT, registered.NOT_STATED, status="unresolved"),
         row("p6", reasons.ABSENT, registered.NOT_STATED, resolved_value="FinnGen R8",
             resolution_note="reread: release 8", status="coded", source_read="abstract",
             quote="FinnGen release 8.", citations_claim="claims/y.yaml#outcome_1")]


def test_the_registered_reader_refuses_the_new_value(tmp_path):
    path = write(tmp_path / "c.csv", registered.CODE_FIELDS,
                 [{f: r[f] for f in registered.CODE_FIELDS} for r in TABLE[:2]])
    with pytest.raises(registered.ManualCodingError):
        registered.load_codes(path, ROWS)


def test_absent_rows_give_the_codes_that_not_stated_rows_give(tmp_path):
    codes, report = reasons.load_extended(write(tmp_path / "e.csv", reasons.EXTENDED_FIELDS,
                                                TABLE), ROWS)
    literal = [{f: (registered.NOT_STATED if r[f] == reasons.ABSENT
                    and registered.final_value(r) == reasons.ABSENT else r[f])
                for f in registered.CODE_FIELDS} for r in TABLE]
    as_not_stated, _ = registered.load_codes(
        write(tmp_path / "n.csv", registered.CODE_FIELDS, literal), ROWS)
    assert codes == as_not_stated == {("p1", "outcome", "FinnGen"): "FinnGen R9",
                                      ("p4", "outcome", "FinnGen"): "FinnGen R5",
                                      ("p6", "outcome", "FinnGen"): "FinnGen R8"}
    assert report["rows"] == 6 and report["coded"] == 3 and report["unresolved"] == 3
    assert report[f"unresolved_{reasons.ABSENT}"] == 1
    assert report[f"unresolved_{registered.NOT_STATED}"] == 1
    assert report["unresolved_no_agreement"] == 1
    assert report["step2_agree"] == 4 and report["step2_disagree"] == 2
    assert report["coded_resting_on_a_reference_entry"] == 1
    assert report["coded_after_resolution"] == 1


def test_the_registered_table_alters_only_rows_whose_agreed_value_is_absent():
    view = reasons.registered_rows(TABLE)
    assert [set(r) for r in view] == [set(registered.CODE_FIELDS)] * 6
    assert view[1]["claude_code_value"] == view[1]["perplexity_value"] == registered.NOT_STATED
    for i in (0, 2, 3, 4, 5):
        assert view[i] == {f: TABLE[i][f] for f in registered.CODE_FIELDS}
    assert view[4]["claude_code_value"] == reasons.ABSENT


def test_the_assembly_reads_the_registered_table_as_it_reads_not_stated_rows(tmp_path):
    with_absent = write(tmp_path / "a.csv", registered.CODE_FIELDS,
                        reasons.registered_rows(TABLE[:4]))
    literal = [dict(r) for r in TABLE[:4]]
    literal[1] = row("p2", registered.NOT_STATED)
    not_stated = write(tmp_path / "b.csv", registered.CODE_FIELDS,
                       [{f: r[f] for f in registered.CODE_FIELDS} for r in literal])
    assert with_absent.read_bytes() == not_stated.read_bytes()
    assert registered.load_codes(with_absent, ROWS) == registered.load_codes(not_stated, ROWS)


def test_a_dictionary_row_of_the_other_side_is_still_refused(tmp_path):
    bad = [row("p1", "deCODE SomaScan v4 (Ferkingstad 2021)")]
    with pytest.raises(registered.ManualCodingError):
        reasons.load_extended(write(tmp_path / "e.csv", reasons.EXTENDED_FIELDS, bad), ROWS)


def attempt(folder, coder, name, n, record, value):
    path = folder / coder / "codes" / f"{name}.attempt{n}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"record_id": record, "coder_id": coder, "attempt": n, "rows": [
        {"side": "outcome", "name_as_written": "FinnGen", "value": value,
         "companion_source": value == "FinnGen R5", "coder_note": f"attempt {n}"}]}))


def test_collect_takes_the_last_attempt_and_keeps_every_queue_row(tmp_path):
    attempt(tmp_path, "coder_1", "p1", 1, "p1", "FinnGen R9")
    attempt(tmp_path, "coder_1", "p1", 2, "p1", "FinnGen R5")
    attempt(tmp_path, "coder_2", "p2", 1, "p2", reasons.ABSENT)
    queue = [{"record_id": r, "side": "outcome", "name_as_written": "FinnGen"}
             for r in ("p2", "p1")]
    table = reasons.collect(tmp_path, queue)
    assert [(r["record_id"], r["claude_code_value"], r["coder_id"], r["attempt"],
             r["companion_source"]) for r in table] == [
        ("p2", reasons.ABSENT, "coder_2", "1", "no"), ("p1", "FinnGen R5", "coder_1", "2", "yes")]
    assert all(list(r) == reasons.EXTENDED_FIELDS for r in table)
    with pytest.raises(registered.ManualCodingError):
        reasons.collect(tmp_path, queue + [{"record_id": "p3", "side": "outcome",
                                            "name_as_written": "FinnGen"}])
    attempt(tmp_path, "coder_3", "p1", 1, "p1", "FinnGen R9")
    with pytest.raises(registered.ManualCodingError):
        reasons.collect(tmp_path, queue)


def test_the_fallback_source_is_written_as_abstract_and_gives_the_same_codes(tmp_path):
    table = [row("p1", "FinnGen R9", source_read=reasons.FALLBACK),
             row("p2", registered.NOT_STATED, unresolved_reason="no_local_passage_found"),
             row("p3", registered.NOT_STATED, unresolved_reason="release_not_identified"),
             row("p4", reasons.ABSENT, unresolved_reason="dataset_absent_from_dictionary"),
             row("p5", registered.NOT_STATED, unresolved_reason="conflicting_identifiers")]
    refused = write(tmp_path / "r.csv", registered.CODE_FIELDS,
                    [{f: r[f] for f in registered.CODE_FIELDS} for r in table[:1]])
    with pytest.raises(registered.ManualCodingError):
        registered.load_codes(refused, ROWS)
    view = reasons.registered_rows(table)
    assert view[0] == {**{f: table[0][f] for f in registered.CODE_FIELDS},
                       "source_read": "abstract"}
    codes, report = reasons.load_extended(write(tmp_path / "e.csv", reasons.EXTENDED_FIELDS,
                                                table), ROWS)
    as_abstract = [dict(table[0], source_read="abstract"), *table[1:]]
    same, _ = reasons.load_extended(write(tmp_path / "a.csv", reasons.EXTENDED_FIELDS,
                                          as_abstract), ROWS)
    assert codes == same == {("p1", "outcome", "FinnGen"): "FinnGen R9"}
    assert report[f"coded_from_{reasons.FALLBACK}"] == 1 and report["coded_from_abstract"] == 1
    assert {k: v for k, v in report.items() if k.startswith("unresolved_reason_")} == {
        "unresolved_reason_release_not_identified": 1,
        "unresolved_reason_conflicting_identifiers": 1,
        "unresolved_reason_no_local_passage_found": 1,
        "unresolved_reason_dataset_absent_from_dictionary": 1}
