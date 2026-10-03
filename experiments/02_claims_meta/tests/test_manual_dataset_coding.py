import csv
import json

import pytest

from assemble_registry import assemble
from build_registry import RegistryClaim, build, pair_h2, registry_claims_from_checks, tables
from dataset_relations import load_rows, map_name
from link_families import SearchRecord
from manual_dataset_coding import (CODE_FIELDS, NOT_STATED, PACKET_FIELDS, ManualCodingError,
                                   check_cover, final_value, load_codes, packet, queue)
from pathway_enrichment import claimed_sets, load_attachments, ASSAY_LISTS, ATTACHMENTS
from assay_backgrounds import load_lists
from claim_tags import ClaimTags
import datetime
from build_registry import PublicDate

R10 = "FinnGen R10"
PPP = "UKB-PPP discovery"
DECODE_2023 = "deCODE SomaScan v4 (Eldjarn 2023 update)"


@pytest.fixture(scope="module")
def rows():
    return load_rows()


def claim(rid, family, pqtl, outcome=(R10,), protein="P1"):
    return RegistryClaim(
        claim_record_id=rid, family_id=family, protein_id=protein, outcome_id="MONDO:1",
        direction="raises", direction_verified=True, claim_scope="overall", context_key="",
        pqtl_datasets=tuple(pqtl), outcome_datasets=tuple(outcome),
        dataset_attribution="whole_study")


def code(record, name, first, second, side="pqtl", resolved="", note="", author="yes",
         status="coded", source="full_text", quote="We used the 2023 release.",
         citation="claims/x.yaml#1"):
    return dict(zip(CODE_FIELDS, [record, side, name, source, quote, citation, first, second,
                                  resolved, note, author, status]))


def write(tmp_path, table):
    path = tmp_path / "manual_dataset_codes.csv"
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CODE_FIELDS)
        w.writeheader()
        w.writerows(table)
    return path


def test_every_dictionary_row_name_maps_to_itself_alone(rows):
    for r in rows:
        m = map_name(r.name, r.side, rows)
        assert (m.state, m.candidates) == ("unique", (r.name,))


def test_queue_lists_ambiguous_and_unmatched_names_once_per_record(rows):
    claims = [claim("11:000", "F1", ["deCODE"]), claim("11:001", "F1", ["deCODE", PPP]),
              claim("12:000", "F2", ["not_stated"], outcome=["some unknown biobank"]),
              claim("13:000", "F3", [PPP])]
    q = queue(claims, rows)
    assert [(r["record_id"], r["side"], r["name_as_written"], r["mapping_state"],
             r["claim_records"]) for r in q] == [
        ("11", "pqtl", "deCODE", "release_ambiguous", 2),
        ("12", "outcome", "some unknown biobank", "unmatched", 1)]
    assert DECODE_2023 in q[0]["candidates"].split("|")


@pytest.mark.parametrize("row, expected", [
    (code("1", "deCODE", DECODE_2023, DECODE_2023), DECODE_2023),
    (code("1", "deCODE", DECODE_2023, DECODE_2023, author="no"), None),
    (code("1", "deCODE", DECODE_2023, "other"), None),
    (code("1", "deCODE", DECODE_2023, "other", resolved=DECODE_2023, note="reread methods"),
     DECODE_2023),
    (code("1", "deCODE", DECODE_2023, "other", resolved=DECODE_2023), None),
    (code("1", "deCODE", NOT_STATED, NOT_STATED), NOT_STATED),
])
def test_a_row_is_coded_only_when_the_three_checks_agree(row, expected):
    assert final_value(row) == expected


def test_codes_table_gives_the_coded_rows_and_the_agreement_counts(rows, tmp_path):
    table = [
        code("1", "deCODE", DECODE_2023, DECODE_2023),
        code("2", "deCODE", DECODE_2023, "deCODE SomaScan v4 (Ferkingstad 2021)",
             resolved=DECODE_2023, note="methods name the 2023 update", source="abstract"),
        code("3", "deCODE", DECODE_2023, "deCODE SomaScan v4 (Ferkingstad 2021)",
             status="unresolved"),
        code("4", "deCODE", NOT_STATED, NOT_STATED, status="unresolved"),
        code("5", "deCODE", DECODE_2023, DECODE_2023, author="no", status="unresolved"),
    ]
    codes, report = load_codes(write(tmp_path, table), rows)
    assert codes == {("1", "pqtl", "deCODE"): DECODE_2023, ("2", "pqtl", "deCODE"): DECODE_2023}
    assert report == {"rows": 5, "coded": 2, "coded_after_resolution": 1,
                      "coded_from_abstract": 1, "coded_from_full_text": 1, "step2_agree": 3,
                      "step2_disagree": 2, "unresolved": 3, "unresolved_no_agreement": 2,
                      "unresolved_not_stated_in_source": 1}


@pytest.mark.parametrize("bad", [
    code("1", "deCODE", DECODE_2023, DECODE_2023, status="unresolved"),
    code("1", "deCODE", DECODE_2023, "other", status="coded"),
    code("1", "deCODE", "not a dictionary row", "not a dictionary row"),
    code("1", "deCODE", R10, R10),
    code("1", "deCODE", DECODE_2023, DECODE_2023, quote=" "),
    code("1", "deCODE", DECODE_2023, DECODE_2023, citation=""),
    code("1", "deCODE", DECODE_2023, DECODE_2023, source="supplement"),
    code("1", "deCODE", DECODE_2023, ""),
    code("1", "deCODE", DECODE_2023, DECODE_2023, side="exposure"),
])
def test_malformed_code_rows_are_refused(rows, tmp_path, bad):
    with pytest.raises(ManualCodingError):
        load_codes(write(tmp_path, [bad]), rows)


def test_codes_must_cover_the_queue_exactly(rows, tmp_path):
    table = [code("1", "deCODE", DECODE_2023, DECODE_2023)]
    path = write(tmp_path, table)
    check_cover(path, [{"record_id": "1", "side": "pqtl", "name_as_written": "deCODE"}])
    with pytest.raises(ManualCodingError, match="without a code"):
        check_cover(path, [{"record_id": "1", "side": "pqtl", "name_as_written": "deCODE"},
                           {"record_id": "2", "side": "pqtl", "name_as_written": "deCODE"}])
    with pytest.raises(ManualCodingError, match="outside the queue"):
        check_cover(path, [])
    with pytest.raises(ManualCodingError, match="twice"):
        load_codes(write(tmp_path, table * 2), rows)


def check(pmid, i, pqtl):
    return {"pmid": pmid, "claim_index": i, "claim_record_id": f"{pmid}:{i:03d}",
            "direction": "raises", "claim_scope": "overall",
            "analysis_context_as_written": "not_stated", "subgroup_as_written": "not_stated",
            "relation_ambiguous": False, "dataset_attribution": "whole_study",
            "pqtl_datasets": list(pqtl), "outcome_datasets": [R10], "protein_ids": ["HGNC:1"],
            "outcome_ids": ["MONDO:1"], "direction_verification_state": "agrees",
            "enters_registry": True, "first_failure": None}


def test_coded_name_is_replaced_by_its_row_and_changes_the_h2_class(rows):
    checks = [check("1", 0, ["deCODE"]), check("2", 0, [DECODE_2023]),
              check("1", 1, ["deCODE", DECODE_2023])]
    hgnc = {"HGNC:1": frozenset({"P1"})}
    family = {"1": "A", "2": "B"}
    plain, _, _ = registry_claims_from_checks(checks, family, hgnc, {})
    assert [c.pqtl_datasets for c in plain] == [("deCODE",), (DECODE_2023,),
                                                ("deCODE", DECODE_2023)]
    assert all(c.manual_dataset_codes == () for c in plain)
    registry = build(plain, rows)
    assert pair_h2(registry[("P1", "MONDO:1")]) == "unresolved"
    assert tables(registry, n_boot=50)["denominators"][
        "family_pair_records_with_a_manually_coded_dataset"] == 0

    manual = {("1", "pqtl", "deCODE"): DECODE_2023}
    coded, _, _ = registry_claims_from_checks(checks, family, hgnc, {}, manual=manual)
    assert [c.pqtl_datasets for c in coded] == [(DECODE_2023,), (DECODE_2023,), (DECODE_2023,)]
    assert coded[0].manual_dataset_codes == (f"pqtl|deCODE|{DECODE_2023}",)
    assert coded[1].manual_dataset_codes == ()
    registry = build(coded, rows)
    fams = registry[("P1", "MONDO:1")]
    assert (fams["A"].manually_coded, fams["B"].manually_coded) == (True, False)
    assert pair_h2(fams) == "known_identical"
    den = tables(registry, n_boot=50)["denominators"]
    assert den["family_pair_records_with_a_manually_coded_dataset"] == 1
    assert den["multi_family_pairs_with_a_manually_coded_dataset"] == 1
    assert den["h1_pairs_with_a_manually_coded_dataset"] == 0


def test_code_of_another_record_or_side_is_not_applied(rows):
    checks = [check("1", 0, ["deCODE"])]
    hgnc = {"HGNC:1": frozenset({"P1"})}
    for key in (("2", "pqtl", "deCODE"), ("1", "outcome", "deCODE"), ("1", "pqtl", "decode")):
        claims, _, _ = registry_claims_from_checks(checks, {"1": "A"}, hgnc, {},
                                                   manual={key: DECODE_2023})
        assert claims[0].pqtl_datasets == ("deCODE",)


def test_outcome_side_code_replaces_the_outcome_name_only(rows):
    row = check("1", 0, ["FinnGen"])
    row["outcome_datasets"] = ["FinnGen"]
    claims, _, _ = registry_claims_from_checks(
        [row], {"1": "A"}, {"HGNC:1": frozenset({"P1"})}, {},
        manual={("1", "outcome", "FinnGen"): R10})
    assert claims[0].outcome_datasets == (R10,)
    assert claims[0].pqtl_datasets == ("FinnGen",)
    assert claims[0].manual_dataset_codes == (f"outcome|FinnGen|{R10}",)


def test_assembly_applies_the_codes_and_counts_the_claims(rows):
    day = PublicDate(value=datetime.date(2021, 1, 1), resolution="day")
    records = [SearchRecord(record_id=r, kind="journal", doi=f"10.1/{r}", pmid=None, pmcid=None,
                            published_as_doi=None, title=f"Study {r} of plasma proteins",
                            first_author_surname=f"Author{r}", first_public=day)
               for r in ("1", "2")]
    decisions = {r: {"decision": "eligible", "flags": []} for r in ("1", "2")}
    checks = [check("1", 0, ["deCODE"]), check("2", 0, [DECODE_2023])]
    hgnc = {"HGNC:1": frozenset({"P1"})}
    plain = assemble(records, decisions, {"1": "ok", "2": "ok"}, checks, hgnc, {})
    assert plain.report["registry"]["claims_with_a_manually_coded_dataset"] == 0
    coded = assemble(records, decisions, {"1": "ok", "2": "ok"}, checks, hgnc, {},
                     manual={("1", "pqtl", "deCODE"): DECODE_2023})
    assert coded.report["registry"]["claims_with_a_manually_coded_dataset"] == 1
    assert {c.pqtl_datasets for c in coded.claims["confirmatory"]} == {(DECODE_2023,)}


def test_manually_coded_claim_enters_the_enrichment_and_is_counted(rows):
    attachments = load_attachments(ATTACHMENTS, load_lists(ASSAY_LISTS))
    tag = ClaimTags(claim_record_id="1:000", pmid="1", wording_class="causal",
                    novelty_language=False, platform=("not_stated",), ancestry="not_stated")
    plain = [claim("1:000", "A", ["deCODE", "AGES"])]
    claimed, counts = claimed_sets(plain, {"1:000": tag}, rows, attachments)
    coded = [plain[0].model_copy(update={
        "pqtl_datasets": (DECODE_2023,),
        "manual_dataset_codes": (f"pqtl|deCODE|{DECODE_2023}", f"pqtl|AGES|{DECODE_2023}")})]
    claimed_coded, counts_coded = claimed_sets(coded, {"1:000": tag}, rows, attachments)
    assert claimed_coded == {"somascan_v4": {"P1"}}
    assert counts_coded == {"enters_enrichment": 1,
                            "enters_enrichment_with_a_manually_coded_dataset": 1}
    assert "enters_enrichment_with_a_manually_coded_dataset" not in counts


def test_coding_packet_shows_the_name_and_candidate_definitions_and_nothing_else(rows):
    claims = [claim("11:000", "F1", ["deCODE"], protein="P9"),
              claim("12:000", "F2", ["not_stated"], outcome=["some unknown biobank"])]
    queued = queue(claims, rows)
    rows_out = packet(queued)
    assert [list(r) for r in rows_out] == [PACKET_FIELDS] * len(queued)
    assert PACKET_FIELDS == ["record_id", "side", "name_as_written", "candidate_rows"]
    by_name = {r["name_as_written"]: r for r in rows_out}
    candidates = json.loads(by_name["deCODE"]["candidate_rows"])
    listed = [c for c in candidates if c["row"] == DECODE_2023]
    assert listed and set(listed[0]) == {"row", "release", "cohort_components", "platform"}
    assert "SomaScan v4" in listed[0]["platform"]
    unlisted = [c for c in candidates if c["row"].startswith("unlisted release of")]
    assert unlisted == [{"row": unlisted[0]["row"]}]
    assert json.loads(by_name["some unknown biobank"]["candidate_rows"]) == []
    text = json.dumps(rows_out)
    for hidden in ("F1", "F2", "P9", "MONDO:1", "raises", "claim_records", "family"):
        assert hidden not in text
