# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.13.5"]
# ///
"""Set-valued dataset mapping and the registered comparison rules between two family records.

Mapping. A dataset name as written maps, on its side (pQTL or outcome), to zero, one or several
rows of `dataset_dictionary.csv`. Names are folded (lower case, accents and every
non-alphanumeric character removed, token boundaries kept) and tried in order:

    1. exact: the folded name equals a row's folded name or one of its folded aliases; every
       such row is a candidate.
    2. qualified: the longest alias or row name that is a token prefix of the written name
       ("FinnGen R10" in "FinnGen R10 release"); every row carrying it is a candidate. The
       remaining words never narrow the candidates ("UKB-PPP European" stays ambiguous among
       the UKB-PPP rows, because a word such as "European" also occurs in "non-European").
    3. generic: the written name is a token prefix of aliases or row names ("FinnGen" of
       "FinnGen R10"); every such row is a candidate.

The first rule with a candidate wins. No rule ever picks one row out of several.

Combination (registered default for OPEN_QUESTIONS item 41). A qualified match whose remaining
words name another dataset ("FinnGen R12 and UK Biobank meta-analysis", "CARDIoGRAMplusC4D 2015
+ UK Biobank") never maps to the leading release alone. The remaining words name another dataset
when the written name contains "+", or the remaining words contain "and", "plus", "with",
"meta"/"meta-analysis", or a source token (UK Biobank, UKB, UKBB, MVP, BBJ). Then:

    a. rows on the same side, other than the leading release's rows, with a name or alias
       carrying every token of the leading key and every non-generic word of the remaining
       words (generic: "meta", "analysis", "and", "plus", "with" and similar) are the
       meta-analysis candidates; among them, the rows naming no further source (UK Biobank,
       MVP, BBJ) are kept when any exist. One such row is unique; several are
       release_ambiguous. A leading key with no digit that is not a row's own name states no
       release, so an `unlisted combination` candidate is added as well.
    b. with no such row, the name is release_ambiguous over the leading release's rows plus an
       `unlisted combination` candidate. Its known components are the leading rows' shared
       components plus each source the remaining words name (UKB, MVP, BBJ); its composition
       is never resolved, so it is never `disjoint`.

A name matched by the exact or qualified rule through an alias with no digit that is not a row's
own name ("INTERVAL", "CARDIoGRAMplusC4D", "deCODE") states no release, year or author, and the
dictionary cannot list every release of a cohort or consortium. Such a name also gets the
candidate `unlisted release of <alias>`. Its components are the candidates' shared components;
its composition is complete only when every candidate is complete with the same single
component (a release of one cohort draws on that cohort), so "INTERVAL" stays disjoint from
"Fenland" but never has a known release.

    unique             one candidate row: the release is known
    release_ambiguous  several candidate rows
    unmatched          no candidate row
    not_stated         Sol returned `not_stated`

Components. Each row's participant sources are the component identifiers committed in
`verification/dataset_components.csv`, plus `UKB` when the dictionary's `includes_ukb` is yes.
Icelandic cohorts are separate components (`AGES_REYKJAVIK`, `DECODE_COHORT`); nationality is
never a component. A row whose `includes_iceland` is yes must name an Icelandic cohort
component to be complete, and a row whose flag is no must name none. A row's composition is
complete when the components file says so, neither flag is `unknown`, and the Icelandic rule
holds. For a name, the known components are the components shared by every candidate row (UK
Biobank for "UKB-PPP" whichever release is meant); its composition is resolved when every
candidate row is complete and all candidates have the same component set.

Possible overlap. AGES-Reykjavik and the deCODE cohort both recruit in Iceland, and no pinned
source documents shared recruitment, so two sides of which one has `AGES_REYKJAVIK` and the
other `DECODE_COHORT`, with no shared component, are `unclear`, never `disjoint`
(`POSSIBLE_OVERLAP`). A pair moves to `overlapping_participant_source` only through a shared
component, that is, when a source places AGES participants in a deCODE release and the
components file lists `AGES_REYKJAVIK` on that release.

Comparison of one side (pQTL or outcome) of two family records, each a list of names:

    identical_release               both sides have every name unique and the two release sets
                                    are equal
    overlapping_participant_source  not identical, and the known components of the two sides
                                    share at least one component
    disjoint                        every name on both sides has a resolved composition, and no
                                    component of one side is a component of the other
    unclear                         anything else, including any `not_stated` or unmatched name,
                                    or a side whose dataset attribution is `unclear`

Release identity for H2 is three-valued: `identical` (as identical_release), `not_identical`
(no choice of one candidate per name makes the two release sets equal, with every name matched),
`undetermined` otherwise.
"""

import csv
import itertools
import pathlib
import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, ConfigDict

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
DICTIONARY = EXP / "dataset_dictionary.csv"
COMPONENTS = EXP / "verification" / "dataset_components.csv"
MAX_ASSIGNMENTS = 100_000

Side = Literal["pqtl", "outcome"]
MappingState = Literal["unique", "release_ambiguous", "unmatched", "not_stated"]
Relation = Literal["identical_release", "overlapping_participant_source", "disjoint", "unclear"]
ReleaseIdentity = Literal["identical", "not_identical", "undetermined"]


class DatasetDictionaryError(Exception):
    """The dictionary and the components file disagree, or a row is malformed."""


class Row(BaseModel):
    model_config = ConfigDict(frozen=True)
    side: Side
    name: str
    name_key: tuple[str, ...]
    keys: tuple[tuple[str, ...], ...]
    components: frozenset[str]
    complete: bool


class NameMapping(BaseModel):
    model_config = ConfigDict(frozen=True)
    written: str
    side: Side
    state: MappingState
    rule: Literal["exact", "qualified", "combination", "generic", "none"]
    candidates: tuple[str, ...]
    known_components: frozenset[str]
    composition_resolved: bool


COMBINER_WORDS = frozenset({"and", "plus", "with"})
GENERIC_WORDS = frozenset({"meta", "metaanalysis", "analysis", "analyses", "and", "plus", "with",
                           "the", "of", "release", "gwas", "summary", "statistics", "data",
                           "combined", "joint"})
SOURCE_COMPONENTS = {"ukb": "UKB", "mvp": "MVP", "bbj": "BBJ"}
ICELANDIC_COHORTS = frozenset({"AGES_REYKJAVIK", "DECODE_COHORT"})
POSSIBLE_OVERLAP = (("AGES_REYKJAVIK", "DECODE_COHORT"),)


def tokens(text: str) -> tuple[str, ...]:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return tuple(t for t in re.split(r"[^a-z0-9]+", text) if t)


def source_tokens(toks: tuple[str, ...]) -> tuple[str, ...]:
    """Tokens with each biobank written as one token ("uk biobank", "ukbb" -> "ukb";
    "biobank japan" -> "bbj")."""
    out: list[str] = []
    i = 0
    while i < len(toks):
        pair = toks[i:i + 2]
        if pair == ("uk", "biobank"):
            out.append("ukb")
            i += 2
        elif pair == ("biobank", "japan"):
            out.append("bbj")
            i += 2
        else:
            out.append("ukb" if toks[i] == "ukbb" else toks[i])
            i += 1
    return tuple(out)


def _names_combination(written: str, rest: tuple[str, ...]) -> bool:
    rest_set = set(source_tokens(rest))
    return ("+" in written or bool(COMBINER_WORDS & rest_set)
            or bool({"meta", "metaanalysis"} & rest_set) or bool(SOURCE_COMPONENTS.keys() & rest_set))


def load_rows(dictionary: pathlib.Path = DICTIONARY,
              components: pathlib.Path = COMPONENTS) -> list[Row]:
    with components.open() as f:
        comp = {r["name"]: r for r in csv.DictReader(f)}
    rows = []
    with dictionary.open() as f:
        for r in csv.DictReader(f):
            if r["name"] not in comp:
                raise DatasetDictionaryError(f"{r['name']!r} has no row in {components.name}")
            c = comp.pop(r["name"])
            parts = set(c["components"].split("|"))
            if r["includes_ukb"] == "yes":
                parts.add("UKB")
            icelandic = bool(parts & ICELANDIC_COHORTS)
            if r["includes_iceland"] == "no" and icelandic:
                raise DatasetDictionaryError(f"{r['name']!r} has includes_iceland no and an "
                                             f"Icelandic cohort component")
            complete = (c["components_complete"] == "yes"
                        and "unknown" not in (r["includes_ukb"], r["includes_iceland"])
                        and (r["includes_iceland"] == "no" or icelandic))
            names = [r["name"], *r["aliases"].split("|")]
            keys = tuple(sorted({tokens(n) for n in names if tokens(n)}))
            rows.append(Row(side=r["side"], name=r["name"], name_key=tokens(r["name"]), keys=keys,
                            components=frozenset(parts), complete=complete))
    if comp:
        raise DatasetDictionaryError(f"components file names rows not in the dictionary: "
                                     f"{sorted(comp)}")
    return rows


def _mapping(written: str, side: Side, state: MappingState, rule: str,
             cands: list[Row], named: frozenset[str] = frozenset()) -> NameMapping:
    known = frozenset.intersection(*(r.components for r in cands)) | named if cands else named
    resolved = bool(cands) and all(r.complete for r in cands) and len(
        {r.components for r in cands}) == 1
    return NameMapping(written=written, side=side, state=state, rule=rule,
                       candidates=tuple(sorted(r.name for r in cands)),
                       known_components=known, composition_resolved=resolved)


def map_name(written: str, side: Side, rows: list[Row]) -> NameMapping:
    if written.strip() == "not_stated":
        return NameMapping(written=written, side=side, state="not_stated", rule="none",
                           candidates=(), known_components=frozenset(),
                           composition_resolved=False)
    w = tokens(written)
    pool = [r for r in rows if r.side == side]
    cands: list[Row] = []
    rule = "none"
    key: tuple[str, ...] = ()
    if w:
        cands = [r for r in pool if w in r.keys]
        rule, key = "exact", w
        if not cands:
            best = max((len(k) for r in pool for k in r.keys
                        if len(k) < len(w) and w[:len(k)] == k), default=0)
            if best:
                cands = [r for r in pool if w[:best] in r.keys]
                rule, key = "qualified", w[:best]
                if _names_combination(written, w[best:]):
                    return _combination(written, side, pool, cands, key, w[best:])
        if cands and not any(t.isdigit() for t in key) and not any(
                r.name_key == key for r in cands):
            shared = frozenset.intersection(*(r.components for r in cands))
            single = (len({r.components for r in cands}) == 1 and len(shared) == 1
                      and all(r.complete for r in cands))
            cands = cands + [Row(side=side, name=f"unlisted release of {' '.join(key)}",
                                 name_key=(), keys=(), components=shared, complete=single)]
        if not cands:
            cands = [r for r in pool if any(len(k) > len(w) and k[:len(w)] == w
                                            for k in r.keys)]
            rule = "generic"
    if not cands:
        return _mapping(written, side, "unmatched", "none", [])
    state = "unique" if len(cands) == 1 else "release_ambiguous"
    return _mapping(written, side, state, rule, cands)


def _combination(written: str, side: Side, pool: list[Row], lead: list[Row],
                 key: tuple[str, ...], rest: tuple[str, ...]) -> NameMapping:
    """A leading release followed by words naming another dataset (see the module docstring)."""
    wanted = set(key) | (set(source_tokens(rest)) - GENERIC_WORDS)
    named_sources = wanted & SOURCE_COMPONENTS.keys()
    lead_names = {r.name for r in lead}
    matched: dict[str, tuple[Row, bool]] = {}
    for r in pool:
        if r.name in lead_names:
            continue
        for k in r.keys:
            ks = set(source_tokens(k))
            if wanted <= ks:
                extra = bool((ks & SOURCE_COMPONENTS.keys()) - named_sources)
                prev = matched.get(r.name)
                matched[r.name] = (r, extra if prev is None else prev[1] and extra)
    no_digit = not any(t.isdigit() for t in key) and not any(r.name_key == key for r in lead)
    shared = frozenset.intersection(*(r.components for r in lead))
    named = frozenset(SOURCE_COMPONENTS[t] for t in named_sources)
    unlisted = Row(side=side, name=f"unlisted combination of {' '.join(key)} with "
                   f"{' '.join(rest)}", name_key=(), keys=(), components=shared | named,
                   complete=False)
    if matched:
        plain = [r for r, extra in matched.values() if not extra]
        cands = plain or [r for r, _ in matched.values()]
        if no_digit:
            cands = cands + [unlisted]
    else:
        cands = lead + [unlisted]
    state = "unique" if len(cands) == 1 else "release_ambiguous"
    return _mapping(written, side, state, "combination", cands, named)


def possibly_overlapping(a: frozenset[str], b: frozenset[str]) -> bool:
    """Whether two component sets hold a `POSSIBLE_OVERLAP` pair, one member on each side."""
    return any((x in a and y in b) or (y in a and x in b) for x, y in POSSIBLE_OVERLAP)


def compare_side(a: list[NameMapping], b: list[NameMapping],
                 a_attribution_clear: bool = True, b_attribution_clear: bool = True) -> Relation:
    """Relation between one side of two family records (each the union of its names)."""
    if (
        not a
        or not b
        or not a_attribution_clear
        or not b_attribution_clear
    ):
        return "unclear"
    if any(m.state in ("not_stated", "unmatched") for m in a + b):
        known_a = frozenset().union(*(m.known_components for m in a))
        known_b = frozenset().union(*(m.known_components for m in b))
        return "overlapping_participant_source" if known_a & known_b else "unclear"
    if all(m.state == "unique" for m in a + b):
        if {m.candidates[0] for m in a} == {m.candidates[0] for m in b}:
            return "identical_release"
    known_a = frozenset().union(*(m.known_components for m in a))
    known_b = frozenset().union(*(m.known_components for m in b))
    if known_a & known_b:
        return "overlapping_participant_source"
    if all(m.composition_resolved for m in a + b) and not possibly_overlapping(known_a, known_b):
        return "disjoint"
    return "unclear"


def release_identity(a: list[NameMapping], b: list[NameMapping]) -> ReleaseIdentity:
    """Whether the two sides name the same release set, for the H2 bounds."""
    if not a or not b or any(m.state in ("not_stated", "unmatched") for m in a + b):
        return "undetermined"
    if all(m.state == "unique" for m in a + b):
        same = {m.candidates[0] for m in a} == {m.candidates[0] for m in b}
        return "identical" if same else "not_identical"
    n_a = 1
    for m in a:
        n_a *= len(m.candidates)
    n_b = 1
    for m in b:
        n_b *= len(m.candidates)
    if n_a > MAX_ASSIGNMENTS or n_b > MAX_ASSIGNMENTS:
        return "undetermined"
    sets_a = {frozenset(c) for c in itertools.product(*(m.candidates for m in a))}
    sets_b = {frozenset(c) for c in itertools.product(*(m.candidates for m in b))}
    return "undetermined" if sets_a & sets_b else "not_identical"


def edge_label(pqtl: Relation, outcome: Relation) -> Literal["independent", "overlapping",
                                                            "unclear"]:
    if pqtl == "disjoint" and outcome == "disjoint":
        return "independent"
    if {pqtl, outcome} & {"identical_release", "overlapping_participant_source"}:
        return "overlapping"
    return "unclear"
