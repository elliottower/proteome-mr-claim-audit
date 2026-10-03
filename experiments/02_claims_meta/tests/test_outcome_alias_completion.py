import pytest

from canonical_ids import (PHENOTYPE_XREF_KEY, canonical_outcomes, load_collision_table,
                           phenotype_term, without_phenotype_xrefs)
from outcome_alias_completion import (icd10_terms, obsolete_label_replacements,
                                      phenotype_cross_references, replacement, stanzas, term_id,
                                      write_rows, PHENOTYPE_FIELDS)
from verify_claims import compact

MONDO = """format-version: 1.2

[Term]
id: MONDO:1
name: hypertensive disorder
xref: HP:1 {source="MONDO:otherHierarchy"}
xref: ICD10CM:I10 {source="MONDO:equivalentTo", source="DOID:1"}
xref: ICD10CM:I15 {source="MONDO:relatedTo"}
xref: UMLS:C1 {source="MONDO:equivalentTo"}

[Term]
id: MONDO:2
name: heart failure
xref: HP:2 {source="MONDO:otherHierarchy"}
xref: ICD10WHO:I50 {source="MONDO:equivalentTo"}

[Term]
id: MONDO:3
name: congestive heart failure
xref: HP:2 {source="MONDO:equivalentTo"}
xref: ICD10CM:I50 {source="MONDO:equivalentTo"}

[Term]
id: MONDO:4
name: asthma
xref: HP:4
xref: HP:5 {source="MONDO:relatedTo"}

[Term]
id: MONDO:6
name: obsolete old disease
is_obsolete: true
xref: HP:6 {source="MONDO:otherHierarchy"}

[Term]
id: MONDO:7
name: merged disease
xref: HP:7 {source="MONDO:otherHierarchy"}

[Term]
id: MONDO:8
name: phenotype not carried by the EFO file
xref: HP:99 {source="MONDO:otherHierarchy"}

[Typedef]
id: part_of
xref: HP:1 {source="MONDO:otherHierarchy"}
"""
EFO = """[Term]
id: efo:EFO_0000010
name: obsolete_mean corpuscular volume
is_obsolete: true
replaced_by: http://purl.obolibrary.org/obo/OBA_10

[Term]
id: OBA:10
name: erythrocyte volume

[Term]
id: efo:EFO_0000020
name: obsolete_asthma
is_obsolete: true
replaced_by: http://purl.obolibrary.org/obo/MONDO_4

[Term]
id: efo:EFO_0000030
name: obsolete_chained
is_obsolete: true
replaced_by: efo:EFO_0000031

[Term]
id: efo:EFO_0000031
name: obsolete_chained, the middle step
is_obsolete: true
replaced_by: http://purl.obolibrary.org/obo/MONDO_1

[Term]
id: efo:EFO_0000040
name: obsolete_two successors
is_obsolete: true
replaced_by: http://purl.obolibrary.org/obo/MONDO_1
replaced_by: http://purl.obolibrary.org/obo/MONDO_2

[Term]
id: efo:EFO_0000050
name: obsolete_dead end
is_obsolete: true
replaced_by: efo:EFO_0000051

[Term]
id: efo:EFO_0000060
name: obsolete_no successor
is_obsolete: true

[Term]
id: efo:EFO_0000070
name: obsolete_shared label
is_obsolete: true
replaced_by: http://purl.obolibrary.org/obo/MONDO_1

[Term]
id: efo:EFO_0000071
name: obsolete_Shared Label
is_obsolete: true
replaced_by: http://purl.obolibrary.org/obo/MONDO_2

[Term]
id: efo:EFO_0000080
name: obsolete_replaced by an anatomy term
is_obsolete: true
replaced_by: http://purl.obolibrary.org/obo/UBERON_5

[Term]
id: UBERON:5
name: heart
"""
LABELS = {"MONDO:1": "hypertensive disorder", "MONDO:2": "heart failure",
          "MONDO:3": "congestive heart failure", "MONDO:4": "asthma",
          "MONDO:7": "merged disease", "MONDO:8": "phenotype not carried by the EFO file",
          "HP:1": "Hypertension", "HP:2": "Cardiac failure", "HP:4": "Asthma", "HP:5": "Wheeze",
          "HP:6": "Old sign", "HP:7": "Merged sign", "OBA:10": "erythrocyte volume"}
COLLISION = {"MONDO:7": frozenset({"EFO:77"})}


@pytest.fixture()
def mondo(tmp_path):
    path = tmp_path / "mondo.obo"
    path.write_text(MONDO)
    return list(stanzas(path))


@pytest.fixture()
def efo(tmp_path):
    path = tmp_path / "efo.obo"
    path.write_text(EFO)
    return list(stanzas(path))


@pytest.mark.parametrize("raw, expected", [
    ("efo:EFO_0004340", "EFO:0004340"), ("MONDO:0005044", "MONDO:0005044"),
    ("http://purl.obolibrary.org/obo/MONDO_0005044", "MONDO:0005044"),
    ("http://purl.obolibrary.org/obo/OBA_VT0005007", "OBA:VT0005007"),
    ("http://www.orpha.net/ORDO/Orphanet_60", "Orphanet:60"), ("OBA:VT0001547", "OBA:VT0001547"),
    ("HP:0000822", "HP:0000822")])
def test_identifiers_are_written_prefix_colon_number(raw, expected):
    assert term_id(raw) == expected


def test_stanzas_read_terms_only_with_their_xrefs_and_source_tags(mondo):
    assert [t["id"] for t in mondo] == [f"MONDO:{i}" for i in (1, 2, 3, 4, 6, 7, 8)]
    first = mondo[0]
    assert first["name"] == "hypertensive disorder" and first["obsolete"] is False
    assert first["xrefs"] == [("HP:1", ("MONDO:otherHierarchy",)),
                              ("ICD10CM:I10", ("MONDO:equivalentTo", "DOID:1")),
                              ("ICD10CM:I15", ("MONDO:relatedTo",)),
                              ("UMLS:C1", ("MONDO:equivalentTo",))]
    assert mondo[3]["xrefs"] == [("HP:4", ()), ("HP:5", ("MONDO:relatedTo",))]
    assert mondo[4]["obsolete"] is True


def test_phenotype_is_listed_when_exactly_one_canonical_term_cross_references_it(mondo):
    rows, counts = phenotype_cross_references(mondo, LABELS, COLLISION)
    assert [(r["phenotype_id"], r["canonical_id"], r["xref_tags"]) for r in rows] == [
        ("HP:1", "MONDO:1", "MONDO:otherHierarchy"), ("HP:7", "EFO:77", "MONDO:otherHierarchy")]
    assert rows[0]["phenotype_label"] == "Hypertension"
    assert rows[0]["canonical_label"] == "hypertensive disorder"
    # HP:2 is cross-referenced by two disease terms; HP:4 and HP:5 carry no registered tag;
    # HP:6 only by an obsolete term; HP:99 is not a term the verifier can return.
    assert counts == {"phenotype_terms_cross_referenced": 3, "rows": 2,
                      "phenotype_terms_with_several_canonical_terms": 1,
                      "by_tag": {"MONDO:otherHierarchy": 2}}


def test_replacement_follows_single_live_successors_only(efo, mondo):
    terms = {t["id"]: t for t in mondo + efo}
    assert replacement("EFO:0000010", terms) == "OBA:10"
    assert replacement("EFO:0000030", terms) == "MONDO:1"
    assert replacement("EFO:0000040", terms) is None
    assert replacement("EFO:0000050", terms) is None
    assert replacement("EFO:0000060", terms) is None
    assert replacement("MONDO:1", terms) == "MONDO:1"


def test_obsolete_labels_stand_for_their_single_live_replacement(efo, mondo):
    terms = {t["id"]: t for t in mondo + efo}
    in_use = {compact("asthma"): {"MONDO:4"}}
    rows, counts = obsolete_label_replacements(efo, terms, in_use, set(LABELS), compact)
    assert [(r["surface"], r["obsolete_id"], r["term_id"], r["term_label"]) for r in rows] == [
        ("chained", "EFO:0000030", "MONDO:1", "hypertensive disorder"),
        ("chained, the middle step", "EFO:0000031", "MONDO:1", "hypertensive disorder"),
        ("mean corpuscular volume", "EFO:0000010", "OBA:10", "erythrocyte volume")]
    assert counts["obsolete_efo_terms"] == 10
    assert counts["label_is_a_live_name"] == 1
    assert counts["no_single_replacement"] == 2
    assert counts["replacement_not_a_live_outcome_term"] == 2
    assert counts["label_with_several_replacements"] == 1
    assert counts["rows"] == 3 and counts["rows_replaced_by_MONDO"] == 2
    assert counts["rows_replaced_by_OBA"] == 1


def test_icd10_code_gives_the_terms_that_carry_it_as_an_equivalent_cross_reference(mondo):
    icd = icd10_terms(mondo, COLLISION)
    assert icd == {"I10": frozenset({"MONDO:1"}), "I50": frozenset({"MONDO:2", "MONDO:3"})}


def table_with_xrefs(tmp_path, rows):
    (tmp_path / "collision.csv").write_text(
        "mondo_id,efo_id,canonical_id,conflicts\nMONDO:20,EFO:20,MONDO:20,\n")
    write_rows(tmp_path / "phenotype_cross_references.csv", PHENOTYPE_FIELDS, rows)
    return load_collision_table(tmp_path / "collision.csv")


def xref(hp, term):
    return {"phenotype_id": hp, "phenotype_label": hp, "canonical_id": term,
            "canonical_label": term, "xref_tags": "MONDO:otherHierarchy"}


def test_name_with_only_phenotype_identifiers_takes_the_cross_referenced_disease(tmp_path):
    table = table_with_xrefs(tmp_path, [xref("HP:1", "MONDO:1"), xref("HP:2", "MONDO:1"),
                                        xref("HP:3", "MONDO:3")])
    assert table[PHENOTYPE_XREF_KEY + "HP:1"] == {"MONDO:1"}
    assert canonical_outcomes(["HP:1"], table) == ["MONDO:1"]
    assert canonical_outcomes(["HP:1", "HP:2"], table) == ["MONDO:1"]
    # Two phenotype terms with different diseases, or one with none, keep their identifiers.
    assert canonical_outcomes(["HP:1", "HP:3"], table) == ["HP:1", "HP:3"]
    assert canonical_outcomes(["HP:1", "HP:9"], table) == ["HP:1", "HP:9"]
    assert canonical_outcomes(["HP:9"], table) == ["HP:9"]
    assert canonical_outcomes(["OBA:5"], table) == ["OBA:5"]
    assert phenotype_term(["HP:1"], table) == "MONDO:1" and phenotype_term([], table) is None


def test_cross_reference_is_not_read_when_the_name_gives_a_mondo_or_efo_identifier(tmp_path):
    table = table_with_xrefs(tmp_path, [xref("HP:2", "MONDO:3")])
    # "heart failure" labels HP:2 and MONDO:2; HP:2 is cross-referenced by MONDO:3.
    assert canonical_outcomes(["HP:2", "MONDO:2"], table) == ["MONDO:2"]
    assert canonical_outcomes(["EFO:20", "HP:2"], table) == ["MONDO:20"]
    assert phenotype_term(["HP:2", "MONDO:2"], table) is None


def test_table_without_the_cross_references_keeps_phenotype_identifiers(tmp_path):
    table = table_with_xrefs(tmp_path, [xref("HP:1", "MONDO:1")])
    plain = without_phenotype_xrefs(table)
    assert canonical_outcomes(["HP:1"], plain) == ["HP:1"]
    assert plain == {"MONDO:20": frozenset({"MONDO:20"}), "EFO:20": frozenset({"MONDO:20"})}
    (tmp_path / "other").mkdir()
    (tmp_path / "other" / "collision.csv").write_text(
        "mondo_id,efo_id,canonical_id,conflicts\nMONDO:20,EFO:20,MONDO:20,\n")
    alone = load_collision_table(tmp_path / "other" / "collision.csv")
    assert alone == plain
    given = load_collision_table(tmp_path / "other" / "collision.csv",
                                 tmp_path / "phenotype_cross_references.csv")
    assert given == table
