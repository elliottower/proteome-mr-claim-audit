import pytest

from ontology_graph import OntologyGraph
from therapeutic_areas import (AREA_NAMES, NOT_DISEASE_AREAS, AreaError, all_areas_of,
                               area_assignment, areas_of, build_table, load_areas, load_names,
                               minimum_cover, normalize_id, write_table)

MEASUREMENT, PHENOTYPE, PROCESS = "EFO:0001444", "EFO:0000651", "GO:0008150"
PROCEDURE, ANIMAL, GENETIC, INJURY = ("EFO:0002571", "MONDO:0005583", "OTAR:0000018",
                                      "OTAR:0000009")


def row(term, areas, name=None, is_area=False):
    return {"id": term, "name": name or term, "therapeuticAreas": areas,
            "ontology": {"isTherapeuticArea": is_area}}


ROWS = [
    row("MONDO_1", ["MONDO_1"], "cardiovascular disorder", True),
    row("MONDO_2", ["MONDO_2"], "nervous system disorder", True),
    row("EFO_0001444", ["EFO_0001444"], "measurement", True),
    row("EFO_10", ["MONDO_1", "MONDO_2"], "stroke"),
    row("MONDO_10", ["MONDO_1"], "stroke, the Mondo term"),
    row("EFO_20", ["EFO_0001444"], "body mass index"),
    row("EFO_30", ["MONDO_2"], "term with two canonical identifiers"),
]
COLLISION = {"EFO:10": frozenset({"MONDO:10"}), "MONDO:10": frozenset({"MONDO:10"}),
             "EFO:30": frozenset({"MONDO:31", "MONDO:32"})}


def test_table_takes_the_union_of_areas_over_rows_with_one_canonical_identifier():
    areas, names, counts = build_table(ROWS, COLLISION)
    assert areas["MONDO:10"] == {"MONDO:1", "MONDO:2"}
    assert "EFO:10" not in areas
    assert areas["MONDO:31"] == areas["MONDO:32"] == {"MONDO:2"}
    assert areas["EFO:20"] == {MEASUREMENT}
    assert names == {"EFO:0001444": "measurement", "MONDO:1": "cardiovascular disorder",
                     "MONDO:2": "nervous system disorder"}
    assert counts["disease_rows"] == 7 and counts["rows_with_several_areas"] == 1
    assert counts["areas"] == 3 and counts["areas_flagged_is_therapeutic_area"] == 3


def test_file_without_the_field_or_with_an_unknown_area_is_refused():
    with pytest.raises(AreaError, match="therapeuticAreas"):
        build_table([{"id": "EFO_1", "name": "x"}], {})
    with pytest.raises(AreaError, match="MONDO:99"):
        build_table([row("EFO_1", ["MONDO_99"])], {})


def test_table_round_trips_and_marks_the_areas_that_are_not_disease_areas(tmp_path):
    areas, names, _ = build_table(ROWS, COLLISION)
    table, name_table = tmp_path / "areas.csv", tmp_path / "names.csv"
    write_table(areas, names, table, name_table)
    assert load_areas(table) == areas
    assert load_names(name_table) == names
    lines = name_table.read_text().splitlines()
    assert lines[0] == "area_id,name,disease_area"
    assert "EFO:0001444,measurement,0" in lines and "MONDO:1,cardiovascular disorder,1" in lines


def test_identifier_normalization():
    assert normalize_id("EFO_0000685") == "EFO:0000685"
    assert normalize_id("MONDO:0004975") == "MONDO:0004975"
    assert normalize_id("Orphanet_12") == "Orphanet:12"


def test_registered_non_disease_areas():
    assert NOT_DISEASE_AREAS == {MEASUREMENT, PHENOTYPE, PROCESS, PROCEDURE, ANIMAL, GENETIC}
    names = load_names(AREA_NAMES)
    assert {names[a] for a in NOT_DISEASE_AREAS} == {
        "measurement", "phenotype", "biological_process", "medical procedure",
        "non-human animal disease", "genetic, familial or congenital disease"}
    assert names[INJURY] == "injury, poisoning or other complication"
    assert INJURY not in NOT_DISEASE_AREAS
    with AREA_NAMES.open() as f:
        flagged = {line.split(",")[0] for line in f if line.rstrip().endswith(",0")}
    assert flagged == NOT_DISEASE_AREAS


def test_cross_cutting_areas_do_not_add_hub_breadth_and_injury_does():
    graph = OntologyGraph([])
    areas = {"o1": frozenset({"cardio", GENETIC}), "o2": frozenset({"neuro", GENETIC}),
             "o3": frozenset({GENETIC}), "o4": frozenset({PROCEDURE, ANIMAL}),
             "o5": frozenset({INJURY})}
    sets = [areas_of(o, areas, graph)[0] for o in ("o1", "o2", "o3", "o4")]
    assert sets == [frozenset({"cardio"}), frozenset({"neuro"}), frozenset(), frozenset()]
    assert minimum_cover(sets) == 2
    assert minimum_cover(sets + [areas_of("o5", areas, graph)[0]]) == 3


def test_area_assignment_records_direct_inherited_distance_and_ties():
    graph = OntologyGraph([("rare", "mid"), ("mid", "top"), ("rare", "side"), ("side", "far"),
                           ("lone", "near"), ("near", "top"), ("lost", "nowhere")])
    areas = {"top": frozenset({"A"}), "far": frozenset({"B", MEASUREMENT}), "mid": frozenset(),
             "near": frozenset({"N"}), "known": frozenset({"C", GENETIC})}
    assert area_assignment("known", areas, graph) == {
        "areas": sorted(["C", GENETIC]), "disease_areas": ["C"], "assignment": "direct",
        "ancestor_distance": None, "nearest_ancestors": [],
        "several_equally_near_ancestors": False}
    assert area_assignment("rare", areas, graph) == {
        "areas": sorted(["A", "B", MEASUREMENT]), "disease_areas": ["A", "B"],
        "assignment": "inherited", "ancestor_distance": 2, "nearest_ancestors": ["far", "top"],
        "several_equally_near_ancestors": True}
    lone = area_assignment("lone", areas, graph)
    assert (lone["assignment"], lone["ancestor_distance"], lone["nearest_ancestors"],
            lone["several_equally_near_ancestors"]) == ("inherited", 1, ["near"], False)
    assert area_assignment("lost", areas, graph)["assignment"] == "none"
    assert area_assignment("lost", areas, graph)["areas"] == []


def test_outcome_absent_from_the_table_takes_its_nearest_ancestors_areas():
    graph = OntologyGraph([("rare", "mid"), ("mid", "top"), ("rare", "side"), ("side", "far"),
                           ("lost", "nowhere")])
    areas = {"top": frozenset({"A"}), "far": frozenset({"B"}), "mid": frozenset(),
             "known": frozenset({"C", MEASUREMENT}), "trait": frozenset({MEASUREMENT})}
    # `top` and `far` are both two steps above `rare`; their areas are joined.
    assert all_areas_of("rare", areas, graph) == (frozenset({"A", "B"}), "nearest_ancestor")
    assert all_areas_of("mid", areas, graph) == (frozenset({"A"}), "nearest_ancestor")
    assert all_areas_of("known", areas, graph) == (frozenset({"C", MEASUREMENT}), "direct")
    assert all_areas_of("lost", areas, graph) == (frozenset(), "none")
    assert all_areas_of("never seen", areas, graph) == (frozenset(), "none")
    assert areas_of("known", areas, graph) == (frozenset({"C"}), "direct")
    assert areas_of("trait", areas, graph) == (frozenset(), "direct")


def test_nearer_ancestor_wins_over_a_farther_one():
    graph = OntologyGraph([("x", "near"), ("near", "far")])
    areas = {"near": frozenset({"N"}), "far": frozenset({"F"})}
    assert all_areas_of("x", areas, graph) == (frozenset({"N"}), "nearest_ancestor")


@pytest.mark.parametrize("sets, expected", [
    ([], 0),
    ([set(), set()], 0),
    ([{"a"}], 1),
    ([{"a"}, {"a", "b"}, {"a", "c"}], 1),
    ([{"a"}, {"b"}], 2),
    ([{"a", "b"}, {"b", "c"}, {"c", "d"}], 2),
    ([{"a"}, {"b"}, {"c"}], 3),
    ([{"a", "b"}, {"c"}, {"d"}, set()], 3),
    ([{"a", "x"}, {"b", "x"}, {"c", "y"}, {"d", "y"}, {"e"}], 3),
    ([{"a"}, {"b"}, {"c"}, {"d"}], 4),
    ([{str(i)} for i in range(9)], 6),
])
def test_minimum_cover(sets, expected):
    assert minimum_cover([frozenset(s) for s in sets]) == expected
