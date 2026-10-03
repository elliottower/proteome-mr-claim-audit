import csv

import pytest

from build_outcome_aliases import (ALIAS_FIELDS, EQUIVALENT_RELATIONS, RELATIONS, SEED,
                                   SEED_FIELDS, TRAIT_SEED, AliasError, build, load_terms,
                                   search)

OBO = """[Term]
id: MONDO:1
name: asthma

[Term]
id: HP:1
name: Asthma

[Term]
id: efo:EFO_0000002
name: body height

[Term]
id: MONDO:3
name: old name
is_obsolete: true
replaced_by: MONDO:4

[Term]
id: MONDO:4
name: new name

[Term]
id: MONDO:5
name: twin

[Term]
id: MONDO:6
name: twin
"""


@pytest.fixture()
def terms(tmp_path):
    path = tmp_path / "x.obo"
    path.write_text(OBO)
    return load_terms([path])


def seed(tmp_path, rows):
    path = tmp_path / "seed.csv"
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(SEED_FIELDS)
        w.writerows(rows)
    return path


def row(surface, label, relation="normalized_equivalent", source="t", rationale="why"):
    return (surface, label, relation, source, rationale)


def test_seed_labels_resolve_to_live_terms_with_mondo_before_other_ontologies(terms, tmp_path):
    out = tmp_path / "aliases.csv"
    resolved = build(seed(tmp_path, [row("self-reported: asthma", "Asthma"),
                                     row("Height", "body height", "exact_equivalent"),
                                     row("Renamed", "old name", "broader_proxy")]), out, terms)
    assert [(r["surface"], r["term_id"], r["term_label"], r["alias_relation"], r["rule"])
            for r in resolved] == [
        ("self-reported: asthma", "MONDO:1", "asthma", "normalized_equivalent", "hand_alias"),
        ("Height", "EFO:0000002", "body height", "exact_equivalent", "hand_alias"),
        ("Renamed", "MONDO:4", "new name", "broader_proxy", "hand_alias")]
    with out.open(newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ALIAS_FIELDS
        assert [r["term_id"] for r in reader] == ["MONDO:1", "EFO:0000002", "MONDO:4"]


@pytest.mark.parametrize("rows", [
    [row("x", "no such label")],
    [row("x", "twin")],
    [row("x", "asthma"), row("x", "body height")],
    [row("x", "asthma", relation="similar")],
    [row("x", "asthma", relation="")],
    [row("x", "asthma", rationale=" ")],
    [row("x", "asthma", source="")],
])
def test_unresolved_ambiguous_or_repeated_seed_rows_raise(terms, tmp_path, rows):
    with pytest.raises(AliasError):
        build(seed(tmp_path, rows), tmp_path / "aliases.csv", terms)


def test_label_search_lists_exact_and_containing_live_labels(terms):
    found = search(terms, ["asthma", "name"])
    assert found["asthma"]["exact"] == ["HP:1 Asthma", "MONDO:1 asthma"]
    assert found["name"] == {"exact": [], "contains": ["MONDO:4 new name"]}


def test_seed_with_the_old_columns_is_refused(terms, tmp_path):
    path = tmp_path / "seed.csv"
    path.write_text("surface,target_label,source,note\nx,asthma,t,\n")
    with pytest.raises(AliasError, match="columns"):
        build(path, tmp_path / "aliases.csv", terms)


def test_committed_seeds_give_every_alias_a_relation_a_source_and_a_rationale():
    assert RELATIONS == ("exact_equivalent", "normalized_equivalent", "broader_proxy",
                         "derived_measurement")
    assert EQUIVALENT_RELATIONS == ("exact_equivalent", "normalized_equivalent")
    for path in (SEED, TRAIT_SEED):
        with path.open(newline="") as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames == SEED_FIELDS
            rows = list(reader)
        assert rows and all(r["alias_relation"] in RELATIONS for r in rows)
        assert all(r["source"].strip() and r["rationale"].strip() for r in rows)
        assert len({r["surface"] for r in rows}) == len(rows)
    with TRAIT_SEED.open(newline="") as f:
        relation = {r["surface"]: r["alias_relation"] for r in csv.DictReader(f)}
    assert relation["Childhood intelligence"] == "broader_proxy"
    assert relation["Serum creatinine (eGFRcrea)"] == "derived_measurement"
    assert relation["Diagnoses - main ICD10: K35 Acute appendicitis"] == "broader_proxy"
    assert relation["Non-cancer illness code  self-reported: pernicious anaemia"] == (
        "exact_equivalent")
