import json
import pathlib

import build_registry as br
import coding_queue as q
import estimands_v1 as es
from build_registry import RegistryClaim
from dataset_relations import load_rows, map_name

EXPERIMENTS = pathlib.Path(__file__).resolve().parents[2]
REG = EXPERIMENTS / "02_claims_meta/outputs/registry/2026-10-03_amended_primary_coded_a"
ROWS = load_rows()


def claim(cid, pq=("not_stated",), oc=("FinnGen",), attribution="claim_specific", fam="f1"):
    return RegistryClaim(claim_record_id=cid, family_id=fam, protein_id="P1", outcome_id="O1",
                         direction="raises", direction_verified=True, claim_scope="overall",
                         context_key="", pqtl_datasets=pq, outcome_datasets=oc,
                         dataset_attribution=attribution)


def code(releases, roles, state="explicit", reasons=()):
    return {"accepted": True, "code": {
        "identified_releases": list(releases),
        "roles": [{"release": r, "role": x} for r, x in zip(releases, roles)],
        "attribution_state": state, "unresolved_reasons": list(reasons)}}


def test_paper1_functions_reproduce_its_registered_amended_primary_counts():
    coded = [RegistryClaim.model_validate_json(l) for l in
             (REG / "registry_claims.jsonl").read_text().splitlines() if l.strip()]
    e = br.estimates(br.build(coded, ROWS))
    assert (e["h2_multi_family_pairs"], e["h2_known_identical"], e["h2_known_not_identical"],
            e["h2_unresolved"]) == (245, 0, 11, 234)
    assert (e["h2b_known_overlapping"], e["h2b_known_not_overlapping"]) == (8, 5)


def test_every_dictionary_row_name_maps_to_its_own_row():
    for r in ROWS:
        m = map_name(r.name, r.side, ROWS)
        assert m.state == "unique" and m.candidates == (r.name,), r.name


def test_codes_replace_names_by_the_four_added_rules():
    c = claim("100:000", pq=("not_stated",), oc=("FinnGen", "UK Biobank"), attribution="unclear")
    written = {"100:000": "gout"}
    plain = {"100:000": {"pqtl_datasets": ["not_stated"], "outcome_datasets": ["FinnGen",
                                                                               "UK Biobank"]}}
    ids = {"pq": es.row_key("100:000", "pqtl", "not_stated", "gout"),
           "fg": es.row_key("100:000", "outcome", "FinnGen", "gout"),
           "uk": es.row_key("100:000", "outcome", "UK Biobank", "gout")}
    assert ids["pq"] == q.row_id("100", "pqtl", "not_stated", "")
    assert ids["fg"] == q.row_id("100", "outcome", "FinnGen", "")
    accepted = {ids["pq"]: code(["deCODE SomaScan v4 (Ferkingstad 2021)"], ["primary"]),
                ids["fg"]: code(["FinnGen R10", "FinnGen R9"], ["primary", "replication"]),
                ids["uk"]: code(["Neale lab UK Biobank GWAS round 2"], ["replication"],
                                state="paper_wide")}
    [got], stats = es.claims_with_codes([c], plain, written, accepted)
    assert got.pqtl_datasets == ("deCODE SomaScan v4 (Ferkingstad 2021)",)
    assert got.outcome_datasets == ("FinnGen R10", "UK Biobank")
    assert got.dataset_attribution == "claim_specific"
    [kept], _ = es.claims_with_codes([c], plain, written, accepted, attribution_resolution=False)
    assert kept.dataset_attribution == "unclear"
    accepted[ids["uk"]] = code([], [], state="unresolved", reasons=["attribution_unresolved"])
    [still], _ = es.claims_with_codes([c], plain, written, accepted)
    assert still.dataset_attribution == "unclear"
    [ft], _ = es.claims_with_codes([c], plain, written, accepted,
                                   keep={ids["fg"]: lambda r: r != "FinnGen R10"})
    assert ft.outcome_datasets == ("FinnGen", "UK Biobank")


def test_a_meta_analysis_row_against_its_components_is_representation_unresolved():
    meta_rows = [r for r in ROWS if r.name == "FinnGen R12 + UK Biobank meta-analysis"]
    assert meta_rows
    meta = {meta_rows[0].name}
    components = {r.name: r.components for r in ROWS}
    a = [map_name(meta_rows[0].name, "outcome", ROWS)]
    b = [map_name("FinnGen R12", "outcome", ROWS)]
    if components["FinnGen R12"] <= components[meta_rows[0].name]:
        assert es.representation_unresolved(a, b, meta, components)
    c = [map_name("FinnGen R11", "outcome", ROWS)]
    assert not es.representation_unresolved(b, c, meta, components)


def test_mention_indices_count_yield_sources_transitions_and_routes():
    ms = [{"side": "pqtl", "abstract_state": "not_stated", "resolved": True,
           "locations": {"full_text"}, "transition": "none", "route": "R1", "has_full_text": True},
          {"side": "outcome", "abstract_state": "release_ambiguous", "resolved": False,
           "locations": set(), "transition": "none", "route": "R3", "has_full_text": True},
          {"side": "outcome", "abstract_state": "unique", "resolved": True,
           "locations": {"abstract", "full_text"}, "transition": "confirmed", "route": "R1",
           "has_full_text": True},
          {"side": "outcome", "abstract_state": "unique", "resolved": True,
           "locations": {"abstract"}, "transition": "none", "route": "none",
           "has_full_text": False}]
    got = es.mention_indices(ms)
    y = got["full_text_resolution_yield"]
    assert (y["mentions_unresolved_from_the_abstract"], y["resolved_here"]) == (2, 1)
    assert got["incremental_yield_by_source"] == {"resolved_mentions": 3, "abstract_only": 1,
                                                  "both": 1, "full_text_only": 1,
                                                  "supplement": 0}
    t = got["abstract_to_full_text_transitions"]
    assert t["mentions_the_abstract_resolves_to_one_release_with_an_eligible_source"] == 1
    assert t["confirmed"] == 1
    assert got["accessibility_stratified_resolution"]["none"] == {"mentions": 1, "resolved": 1}
