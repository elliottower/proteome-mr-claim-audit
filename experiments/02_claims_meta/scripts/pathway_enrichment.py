# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""Reactome pathway enrichment of claimed proteins against each platform's assay list, and
pathway claim density. Description, not a hypothesis test; no direction is assigned at pathway
level. No model is called.

Pathways. Each UniProt accession maps to its Reactome lowest-level pathways through the pinned
`UniProt2Reactome.txt` (release 97, rows of species Homo sapiens).

Platform of a claim. A study family's pQTL datasets on a pair are the registered family datasets
(scripts/build_registry.py: the union of the names on its records for that pair, each mapped to
its candidate rows of the dataset dictionary). Each pQTL row of the dictionary is attached to at
most one pinned assay list (verification/platform_assay_attachments.csv). A dataset name gives
an assay list when every one of its candidate rows of the dictionary is attached to the same
list; no rule picks one row out of several, and a candidate that is not a dictionary row (an
unlisted release or combination) is not read. A family uses, on a pair, every assay list its
names give. The dataset rows alone decide: GPT-6.1 Sol's `platform` field is not read. A claim
whose family's names on the pair give no pinned assay list enters no enrichment and is counted.

A claim whose direction is `reported_nonsignificant_or_null` asserts no effect and enters no
claimed set; it is counted.

Sensitivity `any_candidate_row_attachment`: a dataset name gives every assay list attached to
any of its candidate rows. Sensitivity `null_result_claims_counted`: claims reporting no
significant estimate enter the claimed sets.

A row can be attached to the union of several pinned lists (a study that ran several panels).
A list on which no pathway has 10 to 500 background proteins has no per-list table; its
proteins enter the pooled analysis.

Background level. The background of a row is the proteins that could enter that release's pQTL
analysis, taken at the highest level its sources allow (`background_level` in the attachment
table):

    analysed      the study's own list of the proteins that entered its analysis
    assayed       a study-specific list of the proteins assayed, used when the analysed proteins
                  are not marked
    platform      a commercial platform list, used when no study-specific list exists
    unavailable   no list: the row gives none, its claims enter no enrichment and are counted,
                  and its proteins are not in the pooled background

An assayed or platform list is used only when its reviewed accessions number at least 90% of the
unique targets its source reports (`reported_targets`); below that the row is `unavailable`. The
table records, per row, the assay reagents, the unique targets reported and the targets analysed
as the source states them; the reviewed accessions on the list are counted when the lists are
built.

Sensitivity `whole_panel_backgrounds`: a row takes its `whole_panel_assay_list` where it has
one, the panel or array as assayed with the proteins dropped at quality control included (for
the Jackson Heart Study row, the incomplete commercial SomaScan 1.3k list).

Primary enrichment, per assay list. Background: the UniProt accessions of the list
(verification/platform_assay_lists.csv). Claimed set: the distinct accessions with at least one
registry claim of wording class `causal` or `target` from a family using the list, restricted to
the background. Pathways with fewer than 10 or more than 500 background proteins are dropped.
For every remaining pathway: claimed and background counts, the one-sided Fisher exact p value
(the probability of at least as many claimed proteins in the pathway, with claimed-set size,
pathway size and background size fixed), and the Benjamini–Hochberg q value over the remaining
pathways of that list.

Secondary pooled enrichment. Background: the union of the attached assay lists; claimed set: the
union of the per-list claimed sets. It is open to platform-composition confounding and is
labelled so.

Pathway claim density. For every pathway × canonical outcome identifier: the number of study
families and of distinct proteins with a registry claim of a protein of the pathway on that
outcome.

Usage: uv run scripts/pathway_enrichment.py --claims <registry_claims.jsonl>
           --tags <claim_tags.jsonl> --reactome <UniProt2Reactome.txt> --out <dir>
"""

import argparse
import collections
import csv
import datetime
import json
import math
import pathlib
from collections.abc import Mapping

from pydantic import BaseModel

from assay_backgrounds import load_lists
from build_registry import RegistryClaim, build
from claim_tags import ClaimTags, load_tags
from dataset_relations import DICTIONARY, NameMapping, Row, load_rows

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
ASSAY_LISTS = EXP / "verification" / "platform_assay_lists.csv"
ATTACHMENTS = EXP / "verification" / "platform_assay_attachments.csv"
SPECIES = "Homo sapiens"
MIN_BACKGROUND, MAX_BACKGROUND = 10, 500
# A pathway is named in the paper's text only when its q is below NAMING_Q and at least
# NAMING_MIN_CLAIMED claimed proteins lie in it; every row is tabulated whatever the flag.
NAMING_Q, NAMING_MIN_CLAIMED = 0.05, 3
BACKGROUND_LEVELS = ("analysed", "assayed", "platform", "unavailable")
PROXY_LEVELS = ("assayed", "platform")
MIN_PROXY_COVERAGE = 0.90
COUNT_FIELDS = ("assay_reagents", "reported_targets", "analysed_targets")
ENRICHMENT_WORDING = ("causal", "target")
POOLED = "pooled"
NONSIG = "reported_nonsignificant_or_null"


class PathwayInputError(Exception):
    """A committed table disagrees with the dataset dictionary or the pinned assay lists."""


def load_reactome(path: pathlib.Path) -> tuple[dict[str, frozenset[str]], dict[str, str]]:
    """(pathway stable ID -> human UniProt accessions, pathway stable ID -> name)."""
    members: dict[str, set[str]] = collections.defaultdict(set)
    names: dict[str, str] = {}
    with path.open() as f:
        for line in f:
            cols = line.rstrip("\n").split("\t")
            if len(cols) >= 6 and cols[5] == SPECIES:
                members[cols[1]].add(cols[0])
                names[cols[1]] = cols[3]
    return {k: frozenset(v) for k, v in members.items()}, names


def proxy_coverage(level: str, reviewed_accessions: int, reported_targets: int | None
                   ) -> float | None:
    """The reviewed accessions of an assayed or platform list over the unique targets its source
    reports; None for an analysed list or when the source reports no number."""
    if level not in PROXY_LEVELS or not reported_targets:
        return None
    return reviewed_accessions / reported_targets


def attachment_records(path: pathlib.Path) -> list[dict]:
    """The rows of the attachment table, with the three counts the source states as integers
    (None when it states none)."""
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        if r["background_level"] not in BACKGROUND_LEVELS:
            raise PathwayInputError(f"{r['dictionary_row']!r}: background level "
                                    f"{r['background_level']!r}")
        if (r["background_level"] == "unavailable") != (not r["assay_list"]):
            raise PathwayInputError(f"{r['dictionary_row']!r}: a row has no assay list exactly "
                                    "when its background level is `unavailable`")
        for field in COUNT_FIELDS:
            r[field] = int(r[field]) if r.get(field) else None
    return rows


def load_attachments(path: pathlib.Path, lists: dict[str, frozenset[str]],
                     dictionary: pathlib.Path = DICTIONARY, alternative: bool = False,
                     whole_panel: bool = False,
                     overrides: Mapping[str, tuple[str, str]] | None = None
                     ) -> dict[str, str | None]:
    """pQTL dictionary row name -> attached assay list, or None. Every pQTL row of the
    dictionary must be listed with its platform string unchanged. A cell naming several lists
    joined by `|` attaches their union, which is added to `lists` under the cell's text.
    `alternative` reads `alternative_assay_list` where a row gives one (the sensitivity
    analysis `alternative_assay_lists`), and `whole_panel` reads `whole_panel_assay_list` where
    a row gives one (`whole_panel_backgrounds`). `overrides` maps a row to (list id, level)
    of a list its authors supplied (scripts/author_lists.py); it replaces the row's list and
    level. An assayed or platform list that covers less than 90% of the unique targets its
    source reports is refused: the row must be `unavailable`."""
    overrides = overrides or {}
    with dictionary.open(newline="") as f:
        platform = {r["name"]: r["platform"] for r in csv.DictReader(f) if r["side"] == "pqtl"}
    out: dict[str, str | None] = {}
    for r in attachment_records(path):
        name = r["dictionary_row"]
        if platform.get(name) != r["platform_string"]:
            raise PathwayInputError(f"{name!r}: platform string differs from the dictionary")
        level = r["background_level"]
        cell = r["assay_list"]
        if name in overrides:
            cell, level = overrides[name]
        if alternative and r.get("alternative_assay_list"):
            cell = r["alternative_assay_list"]
        if whole_panel and r.get("whole_panel_assay_list"):
            cell = r["whole_panel_assay_list"]
        parts = [p for p in cell.split("|") if p]
        missing = [p for p in parts if p not in lists]
        if missing:
            raise PathwayInputError(f"{name!r}: {missing} not among the assay lists")
        if len(parts) > 1:
            lists[cell] = frozenset().union(*(lists[p] for p in parts))
        if cell and (cell == r["assay_list"] or name in overrides):
            coverage = proxy_coverage(level, len(lists[cell]), r["reported_targets"])
            if coverage is not None and coverage < MIN_PROXY_COVERAGE:
                raise PathwayInputError(
                    f"{name!r}: the {level} list holds {len(lists[cell])} "
                    f"reviewed accessions for {r['reported_targets']} reported targets "
                    f"({coverage:.0%}); below {MIN_PROXY_COVERAGE:.0%} the row is unavailable")
        out[name] = cell or None
    if set(out) != set(platform):
        raise PathwayInputError(f"rows not attached: {sorted(set(platform) - set(out))}; "
                                f"rows not in the dictionary: {sorted(set(out) - set(platform))}")
    return out


def lists_of_names(names: list[NameMapping], attachments: Mapping[str, str | None],
                   any_row: bool = False) -> frozenset[str]:
    """Assay lists given by a family's pQTL names: a name gives a list only when all its
    candidate rows of the dictionary are attached to that one list. A candidate that is not a
    dictionary row (`unlisted release of ...`, `unlisted combination of ...`) has no platform
    string and is not read. With `any_row` (sensitivity) a name gives every list attached to
    any of its candidate rows."""
    out = set()
    for m in names:
        rows = [c for c in m.candidates if c in attachments]
        attached = {attachments[c] for c in rows}
        if any_row:
            out |= attached - {None}
        elif len(attached) == 1 and None not in attached:
            out |= attached
    return frozenset(out)


def claimed_sets(claims: list[RegistryClaim], tags: Mapping[str, ClaimTags], rows: list[Row],
                 attachments: Mapping[str, str | None], any_row: bool = False,
                 count_null: bool = False) -> tuple[dict[str, set[str]], dict]:
    """(assay list -> claimed accessions before the background restriction, claim counts).
    `any_row` and `count_null` are the two registered sensitivity readings."""
    registry = build(claims, rows)
    claimed: dict[str, set[str]] = collections.defaultdict(set)
    counts: collections.Counter = collections.Counter()
    for c in claims:
        t = tags[c.claim_record_id]
        if t.wording_class not in ENRICHMENT_WORDING:
            counts["not_causal_or_target"] += 1
            continue
        if c.direction == NONSIG and not count_null:
            counts["reports_no_significant_estimate"] += 1
            continue
        fp = registry[(c.protein_id, c.outcome_id)][c.family_id]
        lists = lists_of_names(fp.pqtl, attachments, any_row=any_row)
        if not lists:
            counts["no_pinned_assay_list"] += 1
            continue
        counts["enters_enrichment"] += 1
        if c.manual_dataset_codes:
            counts["enters_enrichment_with_a_manually_coded_dataset"] += 1
        for name in lists:
            claimed[name].add(c.protein_id)
    return claimed, dict(counts)


def fisher_greater(k: int, pathway: int, claimed: int, background: int) -> float:
    """P(X >= k) for X hypergeometric: `claimed` draws from `background`, `pathway` marked."""
    if k <= 0:
        return 1.0
    total = math.comb(background, claimed)
    tail = sum(math.comb(pathway, i) * math.comb(background - pathway, claimed - i)
               for i in range(k, min(pathway, claimed) + 1))
    return tail / total


def benjamini_hochberg(ps: list[float]) -> list[float]:
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    q = [1.0] * m
    running = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        running = min(running, ps[i] * m / rank)
        q[i] = running
    return q


class PathwayRow(BaseModel):
    assay_list: str
    pathway_id: str
    pathway_name: str
    claimed_in_pathway: int
    claimed: int
    background_in_pathway: int
    background: int
    p_one_sided_fisher: float
    q_benjamini_hochberg: float
    named_in_text: bool


def enrich(name: str, claimed: set[str], background: frozenset[str],
           pathways: Mapping[str, frozenset[str]], names: Mapping[str, str]
           ) -> tuple[list[PathwayRow], dict]:
    inside = claimed & background
    kept = {p: m & background for p, m in pathways.items()
            if MIN_BACKGROUND <= len(m & background) <= MAX_BACKGROUND}
    ids = sorted(kept)
    ps = [fisher_greater(len(inside & kept[p]), len(kept[p]), len(inside), len(background))
          for p in ids]
    qs = benjamini_hochberg(ps)
    rows = [PathwayRow(assay_list=name, pathway_id=p, pathway_name=names[p],
                       claimed_in_pathway=len(inside & kept[p]), claimed=len(inside),
                       background_in_pathway=len(kept[p]), background=len(background),
                       p_one_sided_fisher=pv, q_benjamini_hochberg=qv,
                       named_in_text=qv < NAMING_Q and len(inside & kept[p]) >= NAMING_MIN_CLAIMED)
            for p, pv, qv in zip(ids, ps, qs)]
    annotated = frozenset().union(*pathways.values()) if pathways else frozenset()
    summary = {"background": len(background), "claimed": len(inside),
               "claimed_outside_background": len(claimed - background),
               "background_with_a_pathway": len(background & annotated),
               "pathways_tested": len(ids),
               "pathways_dropped_by_size": sum(bool(m & background) for m in pathways.values())
               - len(ids)}
    return rows, summary


def enrichment(claimed: Mapping[str, set[str]], lists: Mapping[str, frozenset[str]],
               attachments: Mapping[str, str | None], pathways: Mapping[str, frozenset[str]],
               names: Mapping[str, str]) -> tuple[list[PathwayRow], dict]:
    attached = sorted({a for a in attachments.values() if a})
    rows: list[PathwayRow] = []
    summary: dict = {"primary": {}}
    for name in attached:
        r, s = enrich(name, set(claimed.get(name, ())), lists[name], pathways, names)
        rows += r
        summary["primary"][name] = s
    pooled_background = frozenset().union(*(lists[a] for a in attached)) if attached \
        else frozenset()
    pooled_claimed = set().union(*(claimed.get(a, set()) & lists[a] for a in attached)) \
        if attached else set()
    r, s = enrich(POOLED, pooled_claimed, pooled_background, pathways, names)
    summary["secondary_pooled_open_to_platform_composition_confounding"] = s
    return rows + r, summary


class DensityRow(BaseModel):
    pathway_id: str
    outcome_id: str
    families: int
    proteins: int


def claim_density(claims: list[RegistryClaim], pathways: Mapping[str, frozenset[str]]
                  ) -> list[DensityRow]:
    of_protein: dict[str, set[str]] = collections.defaultdict(set)
    for p, members in pathways.items():
        for acc in members:
            of_protein[acc].add(p)
    families: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    proteins: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for c in claims:
        for p in of_protein.get(c.protein_id, ()):
            families[(p, c.outcome_id)].add(c.family_id)
            proteins[(p, c.outcome_id)].add(c.protein_id)
    return [DensityRow(pathway_id=p, outcome_id=o, families=len(families[(p, o)]),
                       proteins=len(proteins[(p, o)])) for p, o in sorted(families)]


def run(claims: list[RegistryClaim], tags: Mapping[str, ClaimTags], rows: list[Row],
        lists: Mapping[str, frozenset[str]], attachments: Mapping[str, str | None],
        pathways: Mapping[str, frozenset[str]], names: Mapping[str, str],
        any_row: bool = False, count_null: bool = False
        ) -> tuple[dict, list[PathwayRow], list[DensityRow]]:
    claimed, counts = claimed_sets(claims, tags, rows, attachments, any_row, count_null)
    table, summary = enrichment(claimed, lists, attachments, pathways, names)
    density = claim_density(claims, pathways)
    annotated = frozenset().union(*pathways.values()) if pathways else frozenset()
    proteins = {c.protein_id for c in claims}
    summary["lists_without_a_kept_pathway"] = sorted(
        k for k, v in summary["primary"].items() if v["pathways_tested"] == 0)
    summary = {"claims": len(claims), "claims_by_enrichment_state": counts,
               "registry_proteins": len(proteins),
               "registry_proteins_with_a_pathway": len(proteins & annotated),
               **summary, "density_cells": len(density)}
    return summary, table, density


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims", type=pathlib.Path, required=True)
    ap.add_argument("--tags", type=pathlib.Path, required=True)
    ap.add_argument("--reactome", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    claims = [RegistryClaim.model_validate_json(l) for l in a.claims.read_text().splitlines()
              if l.strip()]
    lists = load_lists(ASSAY_LISTS)
    pathways, names = load_reactome(a.reactome)
    summary, table, density = run(claims, load_tags(a.tags), load_rows(), lists,
                                  load_attachments(ATTACHMENTS, lists), pathways, names)
    result = {"claims_file": str(a.claims), "tags_file": str(a.tags),
              "reactome_file": str(a.reactome),
              "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
              **summary}
    a.out.mkdir(parents=True, exist_ok=True)
    target = a.out / "pathway_enrichment.json"
    if target.exists():
        raise FileExistsError(f"{target} exists; archive it before rerunning")
    (a.out / "pathway_enrichment_rows.jsonl").write_text(
        "".join(r.model_dump_json() + "\n" for r in table))
    (a.out / "pathway_claim_density.jsonl").write_text(
        "".join(r.model_dump_json() + "\n" for r in density))
    target.write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
