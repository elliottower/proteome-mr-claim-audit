from ontology_graph import OntologyGraph, canonical_edges, load_graph, parse_is_a, write_edges

OBO = """format-version: 1.2

[Term]
id: MONDO:1
name: disease

[Term]
id: MONDO:2
name: heart disease
is_a: MONDO:1 {source="x"} ! disease
is_a: BFO:9 ! not an outcome term
relationship: part_of MONDO:7 ! not an edge

[Term]
id: efo:EFO_0000003
name: trait in the EFO file's id style
is_a: MONDO:2 ! heart disease
is_a: MONDO:5 {gci_filler="UBERON:1", gci_relation="BFO:0000050"} ! conditional

[Term]
id: MONDO:4
name: obsolete thing
is_a: MONDO:1 ! disease
is_obsolete: true

[Typedef]
id: part_of
is_a: MONDO:1
"""


def test_parse_is_a_keeps_unconditional_edges_between_live_outcome_terms(tmp_path):
    path = tmp_path / "x.obo"
    path.write_text(OBO)
    live, edges = parse_is_a(path)
    assert live == {"MONDO:1", "MONDO:2", "EFO:0000003"}
    assert edges == {("MONDO:2", "MONDO:1"), ("EFO:0000003", "MONDO:2")}


def test_canonical_edges_merge_collisions_and_drop_self_loops():
    collision = {"EFO:1": frozenset({"MONDO:1"}), "MONDO:1": frozenset({"MONDO:1"}),
                 "EFO:9": frozenset({"MONDO:8", "MONDO:9"})}
    edges = {("EFO:1", "MONDO:1"), ("MONDO:2", "EFO:1"), ("EFO:9", "MONDO:3")}
    assert canonical_edges(edges, collision) == {
        ("MONDO:2", "MONDO:1"), ("MONDO:8", "MONDO:3"), ("MONDO:9", "MONDO:3")}


def test_distance_is_the_shortest_path_and_one_step_is_an_edge():
    g = OntologyGraph([("A", "B"), ("B", "C"), ("C", "D"), ("A", "C"), ("X", "D")])
    assert g.ancestors("A") == {"B": 1, "C": 1, "D": 2}
    assert g.distance("A", "D") == 2 and g.distance("D", "A") is None
    assert g.one_step("C") == {"B", "A", "D"}
    assert g.one_step("B") == {"A", "C"}
    assert g.distance("A", "X") is None


def test_edges_round_trip_in_the_drug_join_format(tmp_path):
    path = tmp_path / "edges.csv"
    write_edges({("B", "A"), ("C", "A")}, path)
    assert path.read_text().splitlines() == ["child,parent", "B,A", "C,A"]
    assert load_graph(path).edges() == [("B", "A"), ("C", "A")]
