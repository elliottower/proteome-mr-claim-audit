# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.13.5", "rapidfuzz==3.14.6"]
# ///
"""Link search records into study families and date each family.

Identifier links: a preprint whose "published as" DOI is a journal record's DOI, and records
sharing a DOI, PMID or PMCID. Fuzzy links: title token-set ratio >= 90 (rapidfuzz, 0–100 scale)
and the same folded first-author surname, with three safeguards:

    - only a preprint and a journal record are ever fuzzy-linked; two journal articles or two
      preprints are distinct records whatever their titles;
    - never when either record's explicit identifiers link it to a different record (a
      preprint whose "published as" DOI names another article, or a journal record already
      linked to another preprint);
    - only when the preprint's first public date is not later than the journal record's, at
      the resolution the two dates share.

A record of kind `other` (a conference abstract, dissertation, dataset or repository copy;
scripts/assemble_screening_set.py) is joined to a study family, never made a second family of
the same study: it is fuzzy-linked (same title and first-author rule, no date condition) to the
journal and preprint records it matches when those records are all in one family. It is linked
to nothing when they are in several families or when its own identifiers already link it.

Family date: the earliest public version whose own abstract was judged eligible or uncertain
under the registered eligibility rule (the preprint's version 1 when its abstract is; otherwise
the journal record). Title-level linkage alone never dates a family by a version whose abstract
does not describe the protein analysis.

A record classed `no_abstract` (scripts/abstract_floor.py) is linked like any other record of
its kind. It has no eligibility decision, so it never dates a family, and it is never a
family's registry record (scripts/assemble_registry.py).

Every link is returned with its rule.
"""

import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, ConfigDict
from rapidfuzz import fuzz

from build_registry import PublicDate, date_order

FUZZY_MIN = 90.0
ELIGIBLE = {"eligible", "eligible_count_not_stated", "uncertain"}


class SearchRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    record_id: str
    kind: Literal["journal", "preprint", "other"]
    doi: str | None
    pmid: str | None
    pmcid: str | None
    published_as_doi: str | None
    title: str
    first_author_surname: str
    first_public: PublicDate
    no_abstract: bool = False


class Link(BaseModel):
    a: str
    b: str
    rule: Literal["published_as", "shared_identifier", "fuzzy_title_author",
                  "fuzzy_title_author_copy"]


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return re.sub(r"[^a-z0-9 ]+", " ", "".join(
        c for c in text if not unicodedata.combining(c)).lower()).strip()


def link(records: list[SearchRecord]) -> tuple[dict[str, str], list[Link]]:
    """(record_id -> family_id, links). The family id is the smallest record id among the
    family's journal and preprint records (among all its records when it has neither)."""
    parent = {r.record_id: r.record_id for r in records}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    links: list[Link] = []
    by_doi = {r.doi.lower(): r for r in records if r.doi}
    for r in records:
        if r.kind == "preprint" and r.published_as_doi and r.published_as_doi.lower() in by_doi:
            j = by_doi[r.published_as_doi.lower()]
            links.append(Link(a=r.record_id, b=j.record_id, rule="published_as"))
            union(r.record_id, j.record_id)
    for field in ("doi", "pmid", "pmcid"):
        seen: dict[str, str] = {}
        for r in records:
            v = getattr(r, field)
            if not v:
                continue
            v = v.lower()
            if v in seen:
                links.append(Link(a=seen[v], b=r.record_id, rule="shared_identifier"))
                union(seen[v], r.record_id)
            else:
                seen[v] = r.record_id
    id_linked = {x for l in links for x in (l.a, l.b)}
    preprints = [r for r in records if r.kind == "preprint"]
    journals = [r for r in records if r.kind == "journal"]
    for p in preprints:
        if p.record_id in id_linked or p.published_as_doi:
            continue
        for j in journals:
            if j.record_id in id_linked:
                continue
            if fold(p.first_author_surname) != fold(j.first_author_surname):
                continue
            if fuzz.token_set_ratio(fold(p.title), fold(j.title)) < FUZZY_MIN:
                continue
            if date_order(p.first_public, j.first_public) == "later":
                continue
            links.append(Link(a=p.record_id, b=j.record_id, rule="fuzzy_title_author"))
            union(p.record_id, j.record_id)
    for o in (r for r in records if r.kind == "other"):
        if o.record_id in id_linked:
            continue
        matches = [a for a in preprints + journals
                   if fold(o.first_author_surname) == fold(a.first_author_surname)
                   and fuzz.token_set_ratio(fold(o.title), fold(a.title)) >= FUZZY_MIN]
        if len({find(a.record_id) for a in matches}) == 1:
            links.append(Link(a=o.record_id, b=matches[0].record_id,
                              rule="fuzzy_title_author_copy"))
            union(o.record_id, matches[0].record_id)
    family = {r.record_id: find(r.record_id) for r in records}
    # A family is named by its smallest journal or preprint record id, so a record of kind
    # `other` never renames the family it joins.
    named: dict[str, str] = {}
    for r in records:
        if r.kind != "other":
            root = family[r.record_id]
            named[root] = min(named.get(root, r.record_id), r.record_id)
    return {rid: named.get(root, root) for rid, root in family.items()}, links


def family_dates(records: list[SearchRecord], family_of: dict[str, str],
                 decisions: dict[str, str]) -> dict[str, PublicDate]:
    """Earliest public date among a family's versions whose own abstract is eligible or
    uncertain; a family with no such version takes its journal record's date."""
    out: dict[str, PublicDate] = {}
    members: dict[str, list[SearchRecord]] = {}
    for r in records:
        members.setdefault(family_of[r.record_id], []).append(r)
    for fam, rs in members.items():
        ok = [r for r in rs if decisions.get(r.record_id) in ELIGIBLE] or [
            r for r in rs if r.kind == "journal"] or rs
        best = ok[0].first_public
        for r in ok[1:]:
            if date_order(r.first_public, best) == "earlier":
                best = r.first_public
        out[fam] = best
    return out
