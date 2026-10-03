import json

import pytest

import drug_joins
from biology_joins import Resources
from build_registry import RegistryClaim
from claim_tags import load_lexicon, load_tags, tags_from_extraction
from ontology_graph import load_graph

SPANS = ["IL6R is a therapeutic target for coronary artery disease.",
         "Genetically predicted PCSK9 had a causal effect on stroke.",
         "Higher APOB was associated with asthma."]


def registry_claim(rid, direction="raises"):
    return RegistryClaim(
        claim_record_id=rid, family_id="F1", protein_id="P1", outcome_id="MONDO:1",
        direction=direction, direction_verified=True, claim_scope="overall", context_key="",
        pqtl_datasets=("not_stated",), outcome_datasets=("not_stated",),
        dataset_attribution="whole_study", hgnc_ids=("HGNC:1",),
        outcome_source_ids=("MONDO:1",))


@pytest.fixture()
def files(tmp_path):
    rows = [{"pmid": "77", "status": "ok", "output": {"claims": [
        {"evidence_span": s, "platform": ["Olink"], "ancestry": "not_stated",
         "protein_as_written": s.split()[0], "outcome_as_written": "asthma"} for s in SPANS]}}]
    tags = tmp_path / "claim_tags.jsonl"
    tags.write_text("".join(t.model_dump_json() + "\n"
                            for t in tags_from_extraction(rows, load_lexicon())))
    claims = tmp_path / "registry_claims.jsonl"
    claims.write_text("".join(registry_claim(f"77:{i:03d}").model_dump_json() + "\n"
                              for i in range(3)))
    return claims, tags


def test_claim_tags_file_gives_the_drug_joins_their_wording_class(files):
    claims, tags = files
    loaded = drug_joins.load_claims(claims, tags)
    assert [(c.claim_record_id, c.wording_class) for c in loaded] == [
        ("77:000", "target"), ("77:001", "causal"), ("77:002", "association")]
    assert [c.wording_class for c in loaded] == [
        t.wording_class for t in load_tags(tags).values()]
    assert loaded[0].protein_id == "P1" and loaded[0].direction_verified is True


def test_registry_claim_without_a_tag_raises(files, tmp_path):
    claims, tags = files
    more = tmp_path / "more.jsonl"
    more.write_text(claims.read_text() + registry_claim("78:000").model_dump_json() + "\n")
    with pytest.raises(KeyError, match="78:000"):
        drug_joins.load_claims(more, tags)


def test_committed_ontology_edges_feed_related_indication():
    path = Resources().ontology_edges
    parents = drug_joins.load_edges(path)
    graph = load_graph(path)
    assert parents == graph.parents
    child, parent = graph.edges()[0]
    index = drug_joins.DrugIndex(mechanisms=[], indications=[], trials=[],
                                 resource_disease_ids=[], provenance={})
    look = drug_joins.Lookup(index, {}, parents)
    assert look.relation(parent, child) == "indication_broader"
    assert look.relation(child, parent) == "indication_narrower"
    assert look.relation(child, child) == "match"
    grandparents = [g for g in graph.parents.get(parent, ()) if g not in graph.parents[child]]
    assert all(look.relation(g, child) is None for g in grandparents)


def test_drug_index_built_by_other_code_is_never_reused(tmp_path):
    index = drug_joins.DrugIndex(mechanisms=[], indications=[], trials=[],
                                 resource_disease_ids=[], provenance={})
    restored = drug_joins.DrugIndex.model_validate_json(index.model_dump_json())
    assert restored == index
    with pytest.raises(ValueError):
        drug_joins.DrugIndex.model_validate_json(json.dumps(
            {"mechanisms": [], "indications": [], "resource_disease_ids": [], "provenance": {},
             "trials": [{"report_id": "r", "parent_molregnos": [1], "disease_ids": [],
                         "status": None, "stop_labels": [], "quality_controls": [],
                         "source": None, "report_type": None}]}))
