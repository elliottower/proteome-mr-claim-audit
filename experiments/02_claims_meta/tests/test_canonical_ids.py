import csv
import json
import pathlib

import pytest

from build_collision_table import build_rows, parse_obo
from build_registry import build, registry_claims_from_checks
from canonical_ids import (canonical_outcomes, load_collision_table, load_hgnc_uniprot,
                           outcome_candidates,
                           protein_accession)
from dataset_relations import load_rows

EXP = pathlib.Path(__file__).resolve().parent.parent

MONDO_OBO = """format-version: 1.2

[Term]
id: MONDO:0000001
name: disease

[Term]
id: MONDO:0021125
name: disease characteristic

[Term]
id: MONDO:0000010
name: alpha disease
is_a: MONDO:0000001
xref: EFO:0000010 {source="MONDO:equivalentTo"}

[Term]
id: MONDO:0000020
name: beta disease
is_a: MONDO:0000001
xref: EFO:0000030 {source="MONDO:equivalentTo"}

[Term]
id: MONDO:0000021
name: beta disease variant
is_a: MONDO:0000001
xref: EFO:0000030 {source="MONDO:equivalentTo"}

[Term]
id: MONDO:0000040
name: gamma level
is_a: MONDO:0021125

[Term]
id: MONDO:0000050
name: delta disease
is_a: MONDO:0000001
xref: EFO:0000050 {source="MONDO:equivalentTo"}

[Term]
id: MONDO:0000060
name: epsilon disease
is_a: MONDO:0000001
xref: Orphanet:60 {source="MONDO:equivalentTo"}
xref: Orphanet:61 {source="MONDO:equivalentTo"}

[Term]
id: MONDO:0000070
name: zeta disease
is_a: MONDO:0000001
"""

EFO_OBO = """format-version: 1.2

[Term]
id: efo:EFO_0000408
name: disease

[Term]
id: efo:EFO_0001444
name: measurement

[Term]
id: efo:EFO_0000010
name: alpha disease
is_a: efo:EFO_0000408

[Term]
id: efo:EFO_0000030
name: beta disease
is_a: efo:EFO_0000408

[Term]
id: efo:EFO_0000040
name: gamma measurement
is_a: efo:EFO_0001444
xref: MONDO:0000040

[Term]
id: efo:EFO_0000050
name: delta disease
is_obsolete: true

[Term]
id: Orphanet:60
name: epsilon disease
is_a: efo:EFO_0000408

[Term]
id: efo:EFO_0000070
name: zeta measurement
is_a: efo:EFO_0001444
xref: MONDO:0000070
"""


@pytest.fixture
def table_rows(tmp_path):
    (tmp_path / "mondo.obo").write_text(MONDO_OBO)
    (tmp_path / "efo.obo").write_text(EFO_OBO)
    rows, excluded, n_pairs = build_rows(parse_obo(tmp_path / "mondo.obo"),
                                         parse_obo(tmp_path / "efo.obo"), [])
    return {(r["mondo_id"], r["efo_id"]): r for r in rows}, excluded, n_pairs


def as_table(rows: dict, tmp_path: pathlib.Path) -> dict[str, frozenset[str]]:
    path = tmp_path / "table.csv"
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(next(iter(rows.values()))))
        w.writeheader()
        w.writerows(rows.values())
    return load_collision_table(path)


def test_disease_concepts_take_the_mondo_term(table_rows):
    rows, _, _ = table_rows
    r = rows[("MONDO:0000010", "EFO:0000010")]
    assert (r["concept_class"], r["canonical_id"], r["conflicts"]) == (
        "disease", "MONDO:0000010", "")
    assert rows[("MONDO:0000060", "Orphanet:60")]["canonical_id"] == "MONDO:0000060"


def test_non_disease_traits_take_the_efo_term(table_rows):
    rows, _, _ = table_rows
    r = rows[("MONDO:0000040", "EFO:0000040")]
    assert (r["concept_class"], r["canonical_id"], r["sources"]) == (
        "non_disease_trait", "EFO:0000040", "efo_xref")


def test_obsolete_and_absent_sides_are_counted_not_listed(table_rows):
    rows, excluded, n_pairs = table_rows
    # delta: EFO term obsolete; Orphanet:61 is not carried by the EFO file, so never paired.
    assert ("MONDO:0000050", "EFO:0000050") not in rows
    assert excluded == {"efo_obsolete": 1}
    assert n_pairs == len(rows) + 1


def test_conflicts_are_listed(table_rows):
    rows, _, _ = table_rows
    assert rows[("MONDO:0000020", "EFO:0000030")]["conflicts"] == (
        "efo_term_maps_to_multiple_mondo")
    assert rows[("MONDO:0000070", "EFO:0000070")]["conflicts"] == "branch_disagreement"


def test_collision_table_merges_equivalent_ids_and_flags_one_to_many(table_rows, tmp_path):
    table = as_table(table_rows[0], tmp_path)
    assert canonical_outcomes(["EFO:0000010", "MONDO:0000010"], table) == ["MONDO:0000010"]
    assert canonical_outcomes(["Orphanet:60"], table) == ["MONDO:0000060"]
    assert canonical_outcomes(["MONDO:0000040"], table) == ["EFO:0000040"]
    assert canonical_outcomes(["EFO:0000030"], table) == ["MONDO:0000020", "MONDO:0000021"]
    assert canonical_outcomes(["HP:0000001"], table) == ["HP:0000001"]


def test_branch_disagreement_rows_are_left_unmerged(table_rows, tmp_path):
    table = as_table(table_rows[0], tmp_path)
    assert canonical_outcomes(["EFO:0000070"], table) == ["EFO:0000070"]
    assert canonical_outcomes(["MONDO:0000070"], table) == ["MONDO:0000070"]
    assert canonical_outcomes(["EFO:0000070", "MONDO:0000070"], table) == [
        "EFO:0000070", "MONDO:0000070"]


def test_other_ontology_candidates_are_dropped_only_beside_a_mondo_or_efo_term(table_rows,
                                                                              tmp_path):
    table = as_table(table_rows[0], tmp_path)
    assert canonical_outcomes(["HP:0001370", "MONDO:0008383"], table) == ["MONDO:0008383"]
    assert canonical_outcomes(["EFO:0009999", "OBA:0000002"], table) == ["EFO:0009999"]
    assert canonical_outcomes(["HP:0000001", "OBA:0000002"], table) == [
        "HP:0000001", "OBA:0000002"]
    assert canonical_outcomes(["HP:0000001", "MONDO:0008383", "MONDO:0008384"], table) == [
        "MONDO:0008383", "MONDO:0008384"]
    assert canonical_outcomes(["EFO:0009999", "HP:0000001", "MONDO:0008383"], table) == [
        "EFO:0009999", "MONDO:0008383"]
    assert outcome_candidates(["HP:0001370", "MONDO:0008383"], table) == [
        "HP:0001370", "MONDO:0008383"]


def test_mondo_first_takes_the_single_mondo_identifier_beside_efo_identifiers(table_rows,
                                                                             tmp_path):
    table = as_table(table_rows[0], tmp_path)
    shared = ["EFO:0005288", "MONDO:0005061"]
    assert canonical_outcomes(shared, table) == shared
    assert canonical_outcomes(shared, table, mondo_first=True) == ["MONDO:0005061"]
    assert canonical_outcomes(["EFO:1", "EFO:2", "MONDO:0005061"], table, mondo_first=True) == [
        "MONDO:0005061"]
    two_mondo = ["EFO:0005288", "MONDO:0005061", "MONDO:0005062"]
    assert canonical_outcomes(two_mondo, table, mondo_first=True) == two_mondo
    assert canonical_outcomes(["EFO:1", "EFO:2"], table, mondo_first=True) == ["EFO:1", "EFO:2"]
    assert canonical_outcomes(["MONDO:0005061"], table, mondo_first=True) == ["MONDO:0005061"]


def test_protein_accession_states():
    m = {"HGNC:1": frozenset({"P1"}), "HGNC:2": frozenset({"P2"}),
         "HGNC:3": frozenset({"P3a", "P3b"}), "HGNC:4": frozenset({"P1"}),
         "HGNC:5": frozenset()}
    assert protein_accession(["HGNC:1"], m)[:2] == ("P1", "mapped")
    assert protein_accession(["HGNC:1", "HGNC:4"], m)[:2] == ("P1", "mapped")
    assert protein_accession(["HGNC:1", "HGNC:2"], m) == (None, "multiple_uniprot",
                                                         ["P1", "P2"])
    assert protein_accession(["HGNC:3"], m)[1] == "multiple_uniprot"
    assert protein_accession(["HGNC:5"], m)[1] == "no_uniprot"
    assert protein_accession(["HGNC:9"], m)[1] == "no_uniprot"
    assert protein_accession([], m)[1] == "no_hgnc"


def test_load_hgnc_uniprot_keeps_approved_entries_and_reviewed_accessions(tmp_path):
    (tmp_path / "hgnc.tsv").write_text(
        "hgnc_id\tsymbol\tstatus\tuniprot_ids\n"
        "HGNC:1\tA\tApproved\tP00001\n"
        "HGNC:2\tB\tApproved\t\"P00002|Q99999\"\n"
        "HGNC:3\tC\tEntry Withdrawn\tP00003\n")
    (tmp_path / "uniprot.tsv").write_text(
        "Entry\tProtein names\nP00001\tA protein\nP00002\tB protein\nP00003\tC protein\n")
    m = load_hgnc_uniprot(tmp_path / "hgnc.tsv", tmp_path / "uniprot.tsv")
    assert m == {"HGNC:1": frozenset({"P00001"}), "HGNC:2": frozenset({"P00002"})}


def check(pmid, protein_ids, outcome_ids, pqtl=("UKB-PPP discovery",)):
    return {"pmid": pmid, "claim_index": 0, "claim_record_id": f"{pmid}:000",
            "direction": "raises", "claim_scope": "overall",
            "analysis_context_as_written": "not_stated", "subgroup_as_written": "not_stated",
            "relation_ambiguous": False, "dataset_attribution": "whole_study",
            "pqtl_datasets": list(pqtl), "outcome_datasets": ["FinnGen R10"],
            "protein_ids": protein_ids, "outcome_ids": outcome_ids,
            "direction_verification_state": "agrees", "enters_registry": True,
            "first_failure": None}


def test_registry_keys_pairs_on_uniprot_and_canonical_outcome(table_rows, tmp_path):
    table = as_table(table_rows[0], tmp_path)
    hu = {"HGNC:1": frozenset({"P1"}), "HGNC:4": frozenset({"P1"}),
          "HGNC:2": frozenset({"P2"}), "HGNC:5": frozenset()}
    checks = [check("A", ["HGNC:1"], ["EFO:0000010"]),
              check("B", ["HGNC:4"], ["MONDO:0000010"]),
              check("C", ["HGNC:1", "HGNC:2"], ["MONDO:0000010"]),
              check("D", ["HGNC:1"], ["EFO:0000030"]),
              check("E", ["HGNC:5"], ["MONDO:0000010"]),
              check("F", ["HGNC:2"], ["HP:0000001", "MONDO:0000010"]),
              check("G", ["HGNC:2"], ["HP:0000001", "OBA:0000002"])]
    claims, dropped, ambiguous = registry_claims_from_checks(
        checks, {k: k for k in "ABCDEFG"}, hu, table)
    assert [(c.family_id, c.protein_id, c.outcome_id) for c in claims] == [
        ("A", "P1", "MONDO:0000010"), ("B", "P1", "MONDO:0000010"),
        ("F", "P2", "MONDO:0000010")]
    assert claims[0].outcome_source_ids == ("EFO:0000010",)
    assert claims[1].hgnc_ids == ("HGNC:4",)
    assert claims[2].outcome_source_ids == ("HP:0000001", "MONDO:0000010")
    assert dropped == {"pair_ambiguous": 3, "protein_no_uniprot": 1}
    assert ambiguous == {"protein_multiple_uniprot": 1, "outcome_multiple_canonical": 2,
                         "outcome_other_ontology_candidates_dropped": 1}
    registry = build(claims, load_rows())
    assert set(registry[("P1", "MONDO:0000010")]) == {"A", "B"}


PINNED = json.loads((EXP / "reference" / "MANIFEST.json").read_text())


@pytest.mark.skipif(not (EXP / PINNED["hgnc"]["file"]).exists(),
                    reason="pinned HGNC/UniProt files not fetched from the Modal volume")
def test_pinned_hgnc_uniprot_map():
    m = load_hgnc_uniprot(EXP / PINNED["hgnc"]["file"], EXP / PINNED["uniprot"]["file"])
    assert protein_accession(["HGNC:20001"], m)[:2] == ("Q8NBP7", "mapped")  # PCSK9
    assert protein_accession(["HGNC:6019"], m)[:2] == ("P08887", "mapped")  # IL6R
    assert protein_accession(["HGNC:4392"], m)[1] == "multiple_uniprot"  # GNAS
    # IL12A + IL12B named as one analyte (IL-12p70): a complex gives no pair.
    assert protein_accession(["HGNC:5969", "HGNC:5970"], m)[1] == "multiple_uniprot"


def test_committed_collision_table_follows_the_rule():
    with (EXP / "verification" / "mondo_efo_collision_table.csv").open() as f:
        rows = list(csv.DictReader(f))
    assert rows
    for r in rows:
        want = r["mondo_id"] if r["concept_class"] == "disease" else r["efo_id"]
        assert r["canonical_id"] == want
        assert (r["concept_class"] == "disease") == (r["mondo_branch"] in ("disease", "injury"))
