# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""Stage A estimands of the second release-resolution registration (PREREG.md: H1 [H2-R], H2
[H2b-R], H3 [H1-R]; the first registration's PREREG.md §Study design, §Indices, §Inference
criteria and §Other planned analysis, as amended; stage B did not run, so stage A is primary).
No model is called. Paper 1's functions compute every class and bound (build_registry.build,
estimates, tables; dataset_relations), unchanged; this module only puts the accepted codes into
the claim records, as the four added rules say.

Claims (`claims_with_codes`). Each Paper 1 claim record keeps its names as written (the assembly
made without Paper 1's manual codes; Paper 1's codes are not inherited). A name, or a
`not_stated` side, whose queue row has an accepted code that identifies releases with role
`primary` or `meta_analysis_component` is replaced by those dictionary rows, each a name that
maps to its row (added rules 2 to 4; a replication or sensitivity release does not enter). Every
other name stays as written, so an unresolved row keeps the abstract's name. Added rule 1: a
record Paper 1 marks `unclear` is read as attributed (`claim_specific`) when every queue row of
the record has an accepted code whose attribution state is `explicit` or `paper_wide`; any other
record keeps Paper 1's attribution.

Representation (`representation_unresolved`): a comparison of one family side whose names are
all unique and include one of the 14 meta-analysis or combination rows of Paper 1's dictionary
with another family side whose names are all unique, include no such row, and each name a row
whose participant components lie within the meta-analysis row's components, is
`representation_unresolved` and enters the H2 bounds as unresolved, never as
`known_not_identical` (no row has an expansion, so nothing is canonicalized).

Variants (`variant`): primary; without attribution resolution (Paper 1's attribution stands);
Europe PMC sources only (a release whose every decisive passage stands in a full text of route
R3 does not enter; abstract and R1 evidence stand); without canonicalization and with all
count-only mappings unresolved, equal to the primary by construction.
"""

import collections
import itertools

import build_registry as br
import coding_queue as q
from dataset_relations import map_name

ENTERING = ("primary", "meta_analysis_component")


def row_key(cid: str, side: str, name: str, written: str) -> str:
    stated = name.strip() != q.NOT_STATED
    record = cid.rsplit(":", 1)[0]
    outcome = "" if stated or side == "pqtl" else written
    return q.row_id(record, side, name if stated else q.NOT_STATED, outcome)


def entering(code: dict, keep_release=lambda release: True) -> list[str]:
    roles = {r["release"]: r["role"] for r in code["roles"]}
    return [r for r in code["identified_releases"]
            if roles.get(r) in ENTERING and keep_release(r)]


def claims_with_codes(coded: list, plain: dict, written: dict, accepted: dict,
                      attribution_resolution: bool = True, keep=None) -> tuple[list, dict]:
    """`accepted`: row id -> {"accepted": bool, "code": accepted code or None}; `keep`: row id ->
    a predicate on a release (the Europe PMC variant), else every release enters."""
    out, stats = [], collections.Counter()
    for c in coded:
        cid = c.claim_record_id
        names, row_ids = {}, []
        for side, field in (("pqtl", "pqtl_datasets"), ("outcome", "outcome_datasets")):
            new = []
            for name in plain[cid][field]:
                rid = row_key(cid, side, name, written[cid])
                a = accepted.get(rid)
                if a is not None:
                    row_ids.append(rid)
                rels = entering(a["code"], (keep or {}).get(rid, lambda r: True)) \
                    if a is not None and a["accepted"] else []
                if rels:
                    new.extend(rels)
                    stats["names_replaced_by_codes"] += 1
                else:
                    new.append(name)
            names[field] = tuple(dict.fromkeys(new))
        attribution = c.dataset_attribution
        if (attribution_resolution and attribution == "unclear" and row_ids
                and all(accepted[r]["accepted"] and accepted[r]["code"]["attribution_state"]
                        in ("explicit", "paper_wide") for r in row_ids)):
            attribution = "claim_specific"
            stats["records_attribution_settled"] += 1
        out.append(c.model_copy(update={"pqtl_datasets": names["pqtl_datasets"],
                                        "outcome_datasets": names["outcome_datasets"],
                                        "dataset_attribution": attribution,
                                        "manual_dataset_codes": ()}))
    return out, dict(stats)


def representation_unresolved(a: list, b: list, meta: set[str], components: dict) -> bool:
    if not a or not b or not all(m.state == "unique" for m in a + b):
        return False
    for x, y in ((a, b), (b, a)):
        rows_x = {m.candidates[0] for m in x}
        rows_y = {m.candidates[0] for m in y}
        metas = rows_x & meta
        if metas and not rows_y & meta and any(
                all(components[r] <= components[mm] for r in rows_y) for mm in metas):
            return True
    return False


def pair_h2_rep(fams, meta: set[str], components: dict) -> tuple[str | None, int]:
    if len(fams) < 2:
        return None, 0
    ids, rep = [], 0
    for x, y in itertools.combinations(sorted(fams), 2):
        for side in ("pqtl", "outcome"):
            i = br.family_release_identity(fams[x], fams[y], side)
            if i == "not_identical" and representation_unresolved(
                    getattr(fams[x], side), getattr(fams[y], side), meta, components):
                i, rep = "undetermined", rep + 1
            ids.append(i)
    if all(i == "identical" for i in ids):
        return "known_identical", rep
    if "not_identical" in ids:
        return "known_not_identical", rep
    return "unresolved", rep


def estimates_rep(registry, meta: set[str], components: dict) -> dict:
    est = br.estimates(registry)
    multi = [f for f in registry.values() if len(f) >= 2]
    h2, rep_cmp, rep_pairs = [], 0, 0
    for f in multi:
        cls, rep = pair_h2_rep(f, meta, components)
        h2.append(cls)
        rep_cmp += rep
        rep_pairs += bool(rep)
    n2 = len(h2)
    k_id, k_not, k_un = (h2.count(x) for x in ("known_identical", "known_not_identical",
                                               "unresolved"))
    est.update({"h2_known_identical": k_id, "h2_known_not_identical": k_not,
                "h2_unresolved": k_un, "h2_lower": k_id / n2 if n2 else None,
                "h2_upper": (k_id + k_un) / n2 if n2 else None,
                "h2_complete_case": k_id / (k_id + k_not) if (k_id + k_not) else None,
                "h2_h2b_pairs_not_nested": sum(
                    (x == "known_identical" and y != "known_overlapping")
                    or (x != "known_not_identical" and y == "known_not_overlapping")
                    for x, y in zip(h2, est["_h2b"])),
                "representation_unresolved_comparisons": rep_cmp,
                "representation_unresolved_pairs": rep_pairs,
                "canonicalized_comparisons": 0, "_h2": h2})
    return est


def tables_rep(registry, meta: set[str], components: dict, n_boot: int = br.N_BOOT,
               seed: int = br.SEED) -> dict:
    est = estimates_rep(registry, meta, components)
    public = {k: v for k, v in est.items() if not k.startswith("_")}
    families = sorted({f for fams in registry.values() for f in fams})
    keys = ("h1_pair_concordance", "h1_edge_concordance", "h2_lower", "h2_upper", "h2b_lower",
            "h2b_upper", "h2_resolvable_share")
    values = {k: [] for k in keys}
    for drop in families:
        reduced = {pair: {f: fp for f, fp in fams.items() if f != drop}
                   for pair, fams in registry.items()}
        e = estimates_rep(reduced, meta, components)
        for k in keys:
            if e[k] is not None:
                values[k].append((e[k], drop))
    jack = {k: ({"min": min(v)[0], "min_when_dropping": min(v)[1], "max": max(v)[0],
                 "max_when_dropping": max(v)[1], "n_deletions": len(v)} if v else None)
            for k, v in values.items()}
    h2v, h2bv = br.h2_verdict(est), br.h2_verdict(est, "h2b")
    return {"denominators": br.denominator_report(registry), "estimates": public,
            "wilson_descriptive": {
                "h1_pair_concordance": br.wilson(est["h1_pairs_agreeing"], est["h1_pairs"]),
                "h2_lower": br.wilson(est["h2_known_identical"], est["h2_multi_family_pairs"]),
                "h2_upper": br.wilson(est["h2_known_identical"] + est["h2_unresolved"],
                                      est["h2_multi_family_pairs"]),
                "h2b_lower": br.wilson(est["h2b_known_overlapping"],
                                       est["h2_multi_family_pairs"]),
                "h2b_upper": br.wilson(est["h2b_known_overlapping"] + est["h2b_unresolved"],
                                       est["h2_multi_family_pairs"])},
            "verdict_rule": "finite_corpus_bounds", "h2_verdict": h2v, "h2b_verdict": h2bv,
            "two_verdict_reading": br.two_verdict_reading(h2v, h2bv),
            "h2_supported_attainable": (est["h2_resolvable_share"] is not None
                                        and est["h2_resolvable_share"] > 0.5),
            "pair_bootstrap": br.pair_bootstrap(est, n_boot, seed),
            "protein_cluster_bootstrap": br.protein_cluster_bootstrap(est, n_boot, seed),
            "family_jackknife": jack,
            "imprecise_under_20_pairs": {"h1": est["h1_pairs"] < 20,
                                         "h2": est["h2_multi_family_pairs"] < 20},
            "_h2": est["_h2"], "_h2b": est["_h2b"]}


def pair_classes(registry, meta: set[str], components: dict) -> dict[tuple, tuple[str, str]]:
    return {pair: (pair_h2_rep(f, meta, components)[0], br.pair_overlap(f))
            for pair, f in registry.items() if len(f) >= 2}


def movement(before: dict, after: dict) -> dict:
    out = {}
    for i, name in ((0, "h2"), (1, "h2b")):
        table = collections.Counter(f"{before[p][i]} -> {after[p][i]}" for p in before
                                    if p in after)
        out[name] = dict(sorted(table.items()))
    return out


def mention_state(name: str, side: str, rows) -> str:
    return map_name(name, side, rows).state if name.strip() != q.NOT_STATED else "not_stated"


def resolved(a: dict | None) -> bool:
    """A mention resolved here: accepted, at least one release identified, no unresolved reason."""
    return bool(a and a["accepted"] and a["code"]["identified_releases"]
                and not a["code"]["unresolved_reasons"])


def mention_indices(mentions: list[dict]) -> dict:
    """`mentions`: one per study row of the scope, with `side`, `abstract_state` (Paper 1's
    mapping of the name as written), `resolved`, `locations` (where its decisive passages
    stand: abstract, full_text), `transition` (the code's abstract_transition), `route` (the
    record's full-text route: R1, R3, or none), `has_full_text`."""
    c = collections.Counter
    unres_abs = [m for m in mentions if m["abstract_state"] != "unique"]
    out = {"mentions": len(mentions),
           "full_text_resolution_yield": {
               "mentions_unresolved_from_the_abstract": len(unres_abs),
               "resolved_here": sum(m["resolved"] for m in unres_abs),
               "by_side": {s: {"unresolved_from_the_abstract": sum(m["side"] == s for m in unres_abs),
                               "resolved_here": sum(m["side"] == s and m["resolved"]
                                                    for m in unres_abs)}
                           for s in ("pqtl", "outcome")},
               "by_abstract_state": {k: {"mentions": v, "resolved_here": sum(
                   m["resolved"] for m in unres_abs if m["abstract_state"] == k)}
                   for k, v in sorted(c(m["abstract_state"] for m in unres_abs).items())}}}
    res = [m for m in mentions if m["resolved"]]
    where = c("both" if {"abstract", "full_text"} <= m["locations"] else
              "full_text_only" if "full_text" in m["locations"] else
              "abstract_only" if "abstract" in m["locations"] else "none" for m in res)
    out["incremental_yield_by_source"] = {"resolved_mentions": len(res), **dict(sorted(
        where.items())), "supplement": 0}
    eligible = [m for m in mentions if m["abstract_state"] == "unique" and m["has_full_text"]]
    out["abstract_to_full_text_transitions"] = {
        "mentions_the_abstract_resolves_to_one_release_with_an_eligible_source": len(eligible),
        **dict(sorted(c(m["transition"] for m in eligible).items()))}
    out["accessibility_stratified_resolution"] = {
        r: {"mentions": sum(m["route"] == r for m in mentions),
            "resolved": sum(m["route"] == r and m["resolved"] for m in mentions)}
        for r in ("R1", "R3", "none")}
    out["accessibility_stratified_resolution"]["R2 present"] = {"mentions": 0, "resolved": 0}
    return out
