# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5", "rapidfuzz==3.14.6"]
# ///
"""End-to-end dry run on synthetic records: search records -> families -> eligibility decisions
-> verifier-format claim records -> registry -> H1 and H2 tables.

Every record is invented here; no in-window record, abstract or aggregate is read, and no model
is called. The scenario covers a preprint–journal identifier link, a fuzzy link, two journal
articles with near-identical titles (never linked), a preprint later than its look-alike journal
record (not linked), a preprint whose "published as" DOI names another article (not linked), a
duplicate PMID, an ineligible record, a duplicated claim record, a within-family contradiction
across contexts, an ambiguous dataset alias, an unverified direction, a failed span, a claim
mapping to two proteins (a complex: two UniProt accessions), a protein with no reviewed UniProt
accession, an outcome written with an EFO identifier that the collision table merges into the
Mondo identifier another family used, and a relation-ambiguous claim. The HGNC -> UniProt map
and the collision table are synthetic (SYNTHETIC_HGNC_UNIPROT, SYNTHETIC_COLLISION). Each stage's output is written, and the
run raises if any stage's result differs from the expected value stated in EXPECTED.

Usage: uv run scripts/dry_run_synthetic.py
"""

import datetime
import json
import pathlib

from apply_eligibility import decide
from build_registry import (PublicDate, build, registry_claims_from_checks, tables)
from dataset_relations import load_rows
from link_families import SearchRecord, family_dates, link

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
OUT_ROOT = EXP / "outputs" / "dry_run"

EXPECTED = {
    "families": {"J1": ["J1", "P1"], "J2": ["J2", "P2"], "J3": ["J3"], "J4": ["J4"],
                 "J5": ["J5"], "P5": ["P5"], "J6": ["J6"], "P6": ["P6"],
                 "J7": ["J7", "J7b"], "J8": ["J8"]},
    "link_rules": {"published_as": 1, "fuzzy_title_author": 1, "shared_identifier": 1},
    "family_date_J1": "2021-03-01",
    "decisions": {"eligible": 10, "ineligible": 1, "uncertain": 1, "eligible_count_not_stated": 1},
    "dropped": {"not_mr_estimate": 1, "span_not_verified": 1, "pair_ambiguous": 1,
                "relation_ambiguous": 1, "protein_no_uniprot": 1},
    "pair_ambiguous_reasons": {"protein_multiple_uniprot": 1},
    "by_direction": {"raises": 8, "lowers": 1, "mixed": 1, "unresolved": 1},
    "h1_pairs": 2, "h1_pairs_agreeing": 1, "h1_independent_edges": 2,
    "h2_multi_family_pairs": 5, "h2_known_identical": 1, "h2_known_not_identical": 3,
    "h2_unresolved": 1, "contradicting_pairs": 1,
    # H2b: PAIR3 (identical) and PAIR4 (generic UKB-PPP against UKB-PPP discovery: UK Biobank
    # on both, FinnGen R10 identical) overlap; PAIR1, PAIR2 and PAIR5 have a disjoint pQTL side.
    # Only PAIR3 names one release everywhere ("Pan-UKB" and "Fenland" name no release).
    "h2b_known_overlapping": 2, "h2b_known_not_overlapping": 3, "h2b_unresolved": 0,
    "h2_resolvable_pairs": 1, "h2_h2b_pairs_not_nested": 0,
    # Verdicts on the observed bounds: H2 lower 1/5, upper 2/5 (at or below one half:
    # contradicted); H2b lower 2/5, upper 2/5 (contradicted). The resolvable share is 1/5.
    "verdicts": {"h2_verdict": "contradicted", "h2b_verdict": "contradicted",
                 "two_verdict_reading": "at_most_half_on_identical_or_overlapping_sources",
                 "h2_supported_attainable": False, "verdict_rule": "finite_corpus_bounds"},
}


SYNTHETIC_HGNC_UNIPROT = {**{f"HGNC:{i}": frozenset({f"P0000{i}"}) for i in range(1, 10)},
                          "HGNC:10": frozenset()}
SYNTHETIC_COLLISION = {"EFO:1": frozenset({"MONDO:1"}), "MONDO:1": frozenset({"MONDO:1"})}


def day(s: str) -> PublicDate:
    return PublicDate(value=datetime.date.fromisoformat(s), resolution="day")


def search_records() -> list[SearchRecord]:
    def r(rid, kind, title, author, date, doi=None, pmid=None, pmcid=None, pub=None):
        return SearchRecord(record_id=rid, kind=kind, doi=doi, pmid=pmid, pmcid=pmcid,
                            published_as_doi=pub, title=title, first_author_surname=author,
                            first_public=day(date))
    t = "Proteome-wide Mendelian randomization of plasma proteins and {}"
    return [
        r("J1", "journal", t.format("coronary disease"), "Alpha", "2022-01-10", "10.1/j1", "101"),
        r("P1", "preprint", t.format("coronary disease"), "Alpha", "2021-03-01", "10.9/p1",
          pub="10.1/j1"),
        r("J2", "journal", t.format("stroke in Europeans"), "Beta", "2023-05-02", "10.1/j2",
          "102"),
        r("P2", "preprint", t.format("stroke in Europeans."), "Beta", "2022-11-20", "10.9/p2"),
        r("J3", "journal", t.format("kidney function"), "Gamma", "2021-07-07", "10.1/j3", "103"),
        r("J4", "journal", t.format("kidney function"), "Gamma", "2024-02-02", "10.1/j4", "104"),
        r("J5", "journal", t.format("asthma"), "Delta", "2020-02-02", "10.1/j5", "105"),
        r("P5", "preprint", t.format("asthma"), "Delta", "2020-06-06", "10.9/p5"),
        r("J6", "journal", t.format("gout"), "Eps", "2022-02-02", "10.1/j6", "106"),
        r("P6", "preprint", t.format("gout"), "Eps", "2021-02-02", "10.9/p6", pub="10.1/other"),
        r("J7", "journal", t.format("sepsis"), "Zeta", "2023-03-03", "10.1/j7", "107"),
        r("J7b", "journal", t.format("sepsis"), "Zeta", "2023-03-03", None, "107", "PMC7"),
        r("J8", "journal", "A cohort study of dietary fibre", "Eta", "2022-08-08", "10.1/j8",
          "108"),
    ]


def eligibility_outputs() -> dict[str, dict]:
    base = {"genetic_instruments_for_circulating_proteins": "yes",
            "states_protein_outcome_result": "yes", "proteome_or_panel_wide_screen": "yes",
            "n_proteins_tested": 1500, "n_proteins_tested_span": "1,500 proteins",
            "count_other": None, "count_other_span": None, "exclusion": [],
            "also_tissue_or_csf": False}
    out = {rid: dict(base) for rid in ("J1", "P1", "J2", "P2", "J3", "J4", "J5", "P5", "J6",
                                       "J7", "J7b")}
    out["P6"] = {**base, "n_proteins_tested": None, "n_proteins_tested_span": None}
    out["J6"] = {**base, "proteome_or_panel_wide_screen": "uncertain"}
    out["J8"] = {**base, "genetic_instruments_for_circulating_proteins": "no"}
    return out


def check(pmid, i, protein, outcome, direction, pqtl, oc, *, verified=True, scope="overall",
          context="not_stated", attribution="whole_study", first_failure=None,
          protein_ids=None, relation_ambiguous=False):
    return {"pmid": pmid, "claim_index": i, "claim_record_id": f"{pmid}:{i:03d}",
            "direction": direction, "claim_scope": scope,
            "analysis_context_as_written": context, "subgroup_as_written": "not_stated",
            "relation_ambiguous": relation_ambiguous, "dataset_attribution": attribution,
            "pqtl_datasets": list(pqtl), "outcome_datasets": list(oc),
            "protein_ids": protein_ids or [protein], "outcome_ids": [outcome],
            "direction_verification_state": "agrees" if verified else "direction_unverified",
            "enters_registry": first_failure is None, "first_failure": first_failure}


def claim_checks() -> list[dict]:
    ukb_fg = (["UKB-PPP discovery"], ["FinnGen R10"])
    dec_pan = (["deCODE 2023"], ["Pan-UKB"])
    fen_fg12 = (["Fenland"], ["FinnGen R12"])
    return [
        # PAIR1: J1 and J2 on disjoint sources, same direction; J1's record duplicated.
        check("J1", 0, "HGNC:1", "MONDO:1", "raises", *ukb_fg),
        check("J1", 1, "HGNC:1", "MONDO:1", "raises", *ukb_fg),
        check("J2", 0, "HGNC:1", "EFO:1", "raises", *dec_pan),
        # PAIR2: J1 raises, J3 lowers on disjoint sources.
        check("J1", 2, "HGNC:2", "MONDO:2", "raises", *ukb_fg),
        check("J3", 0, "HGNC:2", "MONDO:2", "lowers", *dec_pan),
        # PAIR3: J1 and J4 on the identical releases.
        check("J1", 3, "HGNC:3", "MONDO:3", "raises", *ukb_fg),
        check("J4", 0, "HGNC:3", "MONDO:3", "raises", *ukb_fg),
        # PAIR4: generic UKB-PPP against UKB-PPP discovery: release undetermined.
        check("J2", 1, "HGNC:4", "MONDO:4", "raises", ["UKB-PPP"], ["FinnGen R10"]),
        check("J3", 1, "HGNC:4", "MONDO:4", "raises", *ukb_fg),
        # PAIR5: J4 mixed across contexts; J5 unverified; J1 raises.
        check("J4", 1, "HGNC:5", "MONDO:5", "raises", *fen_fg12, scope="dataset_specific",
              context="in the discovery cohort", attribution="claim_specific"),
        check("J4", 2, "HGNC:5", "MONDO:5", "lowers", *fen_fg12, scope="dataset_specific",
              context="in the replication cohort", attribution="claim_specific"),
        check("J5", 0, "HGNC:5", "MONDO:5", "raises", *dec_pan, verified=False),
        check("J1", 4, "HGNC:5", "MONDO:5", "raises", *ukb_fg),
        # Records that never reach a pair.
        check("J6", 0, "HGNC:6", "MONDO:6", "raises", *ukb_fg, first_failure="not_mr_estimate"),
        check("J6", 1, "HGNC:6", "MONDO:6", "raises", *ukb_fg,
              first_failure="span_not_verified"),
        check("J7", 0, "HGNC:7", "MONDO:7", "raises", *ukb_fg,
              protein_ids=["HGNC:7", "HGNC:8"]),
        check("J7", 1, "HGNC:9", "MONDO:9", "raises", *ukb_fg,
              first_failure="relation_ambiguous", relation_ambiguous=True),
        check("J7", 2, "HGNC:10", "MONDO:10", "raises", *ukb_fg),
    ]


def expect(name: str, got, want) -> None:
    if got != want:
        raise AssertionError(f"dry run: {name} is {got!r}, expected {want!r}")


def main() -> None:
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    out = OUT_ROOT / stamp
    out.mkdir(parents=True)

    records = search_records()
    (out / "search_records.jsonl").write_text(
        "".join(r.model_dump_json() + "\n" for r in records))
    family_of, links = link(records)
    families: dict[str, list[str]] = {}
    for rid, fam in sorted(family_of.items()):
        families.setdefault(fam, []).append(rid)
    decisions = {rid: decide(o)[0] for rid, o in eligibility_outputs().items()}
    dates = family_dates(records, family_of, decisions)
    (out / "families.json").write_text(json.dumps({
        "families": families, "links": [l.model_dump() for l in links],
        "family_dates": {f: d.value.isoformat() for f, d in dates.items()}}, indent=1))
    (out / "eligibility_decisions.json").write_text(json.dumps(decisions, indent=1))
    expect("families", families, EXPECTED["families"])
    rules: dict[str, int] = {}
    for l in links:
        rules[l.rule] = rules.get(l.rule, 0) + 1
    expect("link rules", rules, EXPECTED["link_rules"])
    expect("family date J1", dates["J1"].value.isoformat(), EXPECTED["family_date_J1"])
    counts: dict[str, int] = {}
    for d in decisions.values():
        counts[d] = counts.get(d, 0) + 1
    expect("eligibility decisions", counts, EXPECTED["decisions"])

    checks = claim_checks()
    (out / "claim_checks.jsonl").write_text("".join(json.dumps(c) + "\n" for c in checks))
    claims, dropped, ambiguous = registry_claims_from_checks(
        checks, family_of, SYNTHETIC_HGNC_UNIPROT, SYNTHETIC_COLLISION)
    (out / "registry_claims.jsonl").write_text(
        "".join(c.model_dump_json() + "\n" for c in claims))
    expect("dropped", dropped, EXPECTED["dropped"])
    expect("pair_ambiguous reasons", ambiguous, EXPECTED["pair_ambiguous_reasons"])
    expect("PAIR1 merged across EFO:1 and MONDO:1",
           sorted({c.family_id for c in claims if c.protein_id == "P00001"
                   and c.outcome_id == "MONDO:1"}), ["J1", "J2"])

    result = tables(build(claims, load_rows()))
    result = {"synthetic": True, "written_utc": stamp, "dropped_before_registry": dropped,
              "pair_ambiguous_reasons": ambiguous, **result}
    (out / "h1_h2_tables.json").write_text(json.dumps(result, indent=1))
    den, est = result["denominators"], result["estimates"]
    expect("family-pair directions", den["by_direction"], EXPECTED["by_direction"])
    expect("contradicting pairs", den["contradicting_pairs"], EXPECTED["contradicting_pairs"])
    for k in ("h1_pairs", "h1_pairs_agreeing", "h1_independent_edges", "h2_multi_family_pairs",
              "h2_known_identical", "h2_known_not_identical", "h2_unresolved",
              "h2b_known_overlapping", "h2b_known_not_overlapping", "h2b_unresolved",
              "h2_resolvable_pairs", "h2_h2b_pairs_not_nested"):
        expect(k, est[k], EXPECTED[k])
    for k, v in EXPECTED["verdicts"].items():
        expect(k, result[k], v)
    print(json.dumps({"out": str(out.relative_to(EXP)), "denominators": den,
                      "estimates": est, "pair_bootstrap": result["pair_bootstrap"],
                      "h2_verdict": result["h2_verdict"], "h2b_verdict": result["h2b_verdict"],
                      "two_verdict_reading": result["two_verdict_reading"],
                      "protein_cluster_bootstrap": result["protein_cluster_bootstrap"],
                      "family_jackknife": result["family_jackknife"]}, indent=1))


if __name__ == "__main__":
    main()
