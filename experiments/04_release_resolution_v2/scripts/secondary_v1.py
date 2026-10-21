# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""Count-inferred and size-inferred sensitivity analyses and secondary analyses SA1 (A to C), SA2
to SA8 of the second registration's stage A (first registration PREREG.md §Other planned
analysis and §Prespecified secondary analyses; Amendments 5 and 6; second registration item 4).
No model is called.

Count evidence (`count_matches`). A mention's count evidence is every `count_evidence` entry of
its accepted code, or of both coders' answers when the row has no accepted code or a settled
code (which keeps none). An entry names a resource; its candidate rows are
dataset_relations.map_name of that resource on the row's side (dictionary rows only); a row of
reference/release_counts.csv is a count match when its dictionary row is a candidate and its
cases and controls equal the entry's digit for digit. Endpoint fields (`fields`), each `match`,
`conflict` or `unknown` (unknown when either side does not state it): sex and the binary nature
compare enumerations; ancestry compares the table's group with the group the entry's text names;
single cohort or meta-analysis compares the table's resource with the entry; case definition is
a match when the entry holds the row's endpoint code, a conflict when it holds another code of
that form; disease or subtype is a match when its words equal the endpoint label's, otherwise
unknown, because two wordings of one endpoint are not a disagreement; incident or prevalent is
unknown, the table never stating it. Strict: every field match. Compatible: no field in conflict.
A mention with no decisive release resolves to a release when its matches pick exactly one
count row (every row's duplicate_count is 1).

Size flag (`size_flag`, Amendment 5): first registration scripts/author_page_helper_v1.py
(sealed) on the text of the row's passages (its attribution passage and count-evidence quotes)
against the dictionary rows of the resources the row names (its name as written and the count
evidence's resources): `size_match` with the row it singles out, `size_conflict`,
`size_ambiguous`, or none.

Levels (`level`, Amendment 6 item 1) in the order of its table.
"""

import collections
import re

import author_page_helper_v1 as helper
import source_scanner_v2 as scanner
from dataset_relations import compare_side, map_name

GROUPS = {"EUR": "eur", "European": "eur", "AFR": "afr", "EAS": "eas", "CSA": "csa",
          "AMR": "amr", "MID": "mid"}
TEXT_GROUPS = (("eur", r"europ|white|caucas"), ("afr", r"african"),
               ("eas", r"east asian|japan|chinese|korean"), ("csa", r"south asian|indian"),
               ("amr", r"hispanic|latin|admixed american"), ("mid", r"middle east"))
CODE = re.compile(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b")


def words(text: str) -> tuple[str, ...]:
    return tuple(t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if t)


def text_group(text: str) -> str | None:
    t = (text or "").lower()
    found = {g for g, pat in TEXT_GROUPS if re.search(pat, t)}
    return found.pop() if len(found) == 1 else None


def fields(entry: dict, row: dict) -> dict[str, str]:
    def cmp(a, b):
        if a is None or b is None:
            return "unknown"
        return "match" if a == b else "conflict"
    sex_e = entry.get("sex") if entry.get("sex") in ("both", "female", "male") else None
    sex_t = row["sex"] if row["sex"] in ("both", "female", "male") else None
    qb = entry.get("quantitative_or_binary")
    meta_t = "meta_analysis" if "meta" in row["resource"].lower() else "single_cohort"
    meta_e = entry.get("single_cohort_or_meta_analysis")
    codes = set(CODE.findall(entry.get("case_definition") or ""))
    case = ("match" if row["endpoint_code"] and row["endpoint_code"] in codes else
            "conflict" if codes and row["endpoint_code"] else "unknown")
    disease = ("match" if words(entry.get("disease_or_subtype"))
               and words(entry.get("disease_or_subtype")) == words(row["endpoint_label"])
               else "unknown")
    return {"disease_or_subtype": disease, "incident_or_prevalent": "unknown",
            "sex": cmp(sex_e, sex_t),
            "ancestry": cmp(text_group(entry.get("ancestry")), GROUPS.get(row["ancestry"])),
            "case_definition": case,
            "quantitative_or_binary": cmp(qb if qb in ("binary", "quantitative") else None,
                                          "binary"),
            "single_cohort_or_meta_analysis": cmp(
                meta_e if meta_e in ("single_cohort", "meta_analysis") else None, meta_t)}


def digits(x) -> str:
    return re.sub(r"\D", "", str(x or ""))


def count_matches(entries: list[dict], side: str, rows_dict, counts_by_pair: dict) -> list[dict]:
    out = []
    for e in entries:
        cands = {c for c in map_name(e.get("resource") or "", side, rows_dict).candidates
                 if not c.startswith("unlisted")}
        key = (digits(e.get("cases")), digits(e.get("controls")))
        if not all(key):
            continue
        for row in counts_by_pair.get(key, []):
            if row["dictionary_row"] in cands:
                f = fields(e, row)
                out.append({"dictionary_row": row["dictionary_row"],
                            "endpoint_code": row["endpoint_code"], "fields": f,
                            "strict": all(v == "match" for v in f.values()),
                            "compatible": "conflict" not in f.values()})
    return out


def count_inferred(matches: list[dict], mode: str) -> str | None:
    """The release a mention resolves to under `mode` (strict, compatible), or None."""
    picked = {m["dictionary_row"] + "|" + m["endpoint_code"] for m in matches if m[mode]}
    rows = {p.split("|", 1)[0] for p in picked}
    return rows.pop() if len(picked) == 1 else None


def size_flag(text: str, names: list[str], side: str, definitions: list[dict]) -> dict:
    rows = helper.named_rows(names, side, definitions)
    idents = helper.find_identifiers(text)
    numbers = helper.find_numbers(text, idents)
    labels = helper.size_labels(text, numbers, rows)
    kinds = {k for k, _ in labels.values()}
    matched = sorted({r for k, r in labels.values() if k == "match"})
    if "conflict" in kinds:
        return {"flag": "size_conflict", "row": None}
    if "match" in kinds and len(matched) == 1:
        return {"flag": "size_match", "row": matched[0]}
    if "ambiguous" in kinds:
        return {"flag": "size_ambiguous", "row": None}
    return {"flag": None, "row": None}


def level(code: dict | None, accepted: bool, queue_name: str, side: str, resource_names,
          rows_dict, resolved_fn) -> str:
    if accepted and code and "conflicting_identifiers" in code["unresolved_reasons"]:
        return "conflict"
    if accepted and resolved_fn():
        return "L1 release identified"
    if accepted and code and "dataset_absent_from_dictionary" in code["unresolved_reasons"]:
        return "L4 dataset outside the dictionary"
    names = ([] if queue_name == "not stated" else [queue_name]) + list(resource_names)
    cands = set()
    for n in names:
        cands |= {c for c in map_name(n, side, rows_dict).candidates
                  if not c.startswith("unlisted")}
    if len(cands) == 1:
        return "L2 one candidate in the frozen dictionary"
    if len(cands) >= 2:
        return "L3 several candidates in the frozen dictionary"
    release_reasons = set(code["unresolved_reasons"]) - {"attribution_unresolved"} if code else set()
    if (queue_name == "not stated" and accepted and code and not code["decisive_evidence"]
            and not code.get("attribution_passage") and not code.get("count_evidence")
            and release_reasons == {"release_not_identified"}):
        return "L5 no dataset named"
    return "name status undetermined"


def side_classes(fams) -> list[tuple[str, str]]:
    out = []
    names = sorted(fams)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            fa, fb = fams[a], fams[b]
            out.append((compare_side(fa.pqtl, fb.pqtl, fa.attribution_clear, fb.attribution_clear),
                        compare_side(fa.outcome, fb.outcome, fa.attribution_clear,
                                     fb.attribution_clear)))
    return out


SA2_CLASS = {"identical_release": "identical_release",
             "overlapping_participant_source": "overlapping_participant_source",
             "disjoint": "disjoint", "unclear": "unclear"}


def sa2(registry) -> dict:
    raw, weighted = collections.Counter(), collections.Counter()
    for fams in registry.values():
        if len(fams) < 2:
            continue
        comps = side_classes(fams)
        for pq, oc in comps:
            raw[f"{SA2_CLASS[pq]}|{SA2_CLASS[oc]}"] += 1
            weighted[f"{SA2_CLASS[pq]}|{SA2_CLASS[oc]}"] += 1 / len(comps)
    return {"comparisons": sum(raw.values()), "raw": dict(sorted(raw.items())),
            "pair_weighted": {k: round(v, 4) for k, v in sorted(weighted.items())},
            "note": "pQTL-side class | outcome-side class; no cell is called replication"}


def sa4_types(quote: str, patterns: dict, mapper, rule: str) -> set[str]:
    unit = {"record_id": "", "source_key": "", "unit_id": "", "text": quote}
    kinds = {m["kind"] for m in scanner.unit_matches(unit, patterns, mapper)}
    names = {"release": "numbered_release", "accession": "repository_accession",
             "source_identifier": "citation_or_source_doi"}
    out = {names[k] for k in kinds}
    if not out and rule == "D2":
        out.add("citation_or_source_doi")
    return out


def record_overlap(pq, oc, clear: bool) -> str:
    rel = compare_side(pq, oc, clear, clear)
    return {"overlapping_participant_source": "shared_participant_source",
            "identical_release": "same_release", "disjoint": "disjoint"}.get(rel, "unresolved")


def family_class(classes: list[str]) -> str:
    s = set(classes)
    if "unresolved" in s:
        return "any_record_unresolved"
    if s == {"shared_participant_source"}:
        return "all_records_sharing"
    if s == {"disjoint"}:
        return "all_records_disjoint"
    return "mixed"


def sa3_pairs(unresolved_pairs: dict, row_reasons: dict) -> dict:
    """`unresolved_pairs`: pair -> list of blocking row ids, or a list holding one pair-level
    category; `row_reasons`: row id -> set of categories."""
    affected, only, several = collections.Counter(), collections.Counter(), 0
    for pair, blocking in unresolved_pairs.items():
        cats = [row_reasons.get(r, {r}) for r in blocking]
        union = set().union(*cats) if cats else set()
        for c in union:
            affected[c] += 1
        if len(union) == 1:
            only[next(iter(union))] += 1
        elif union:
            several += 1
    return {"unresolved_pairs": len(unresolved_pairs), "affected": dict(sorted(affected.items())),
            "only_blocker": dict(sorted(only.items())), "several_blockers": several}

