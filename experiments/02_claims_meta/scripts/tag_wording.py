# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.13.5"]
# ///
"""Assign the wording class and the novelty-language flag of each claim record from its
evidence span, with the committed keyword lists (`verification/wording_lexicon.json`).

Wording class, first match wins: `target`, then `causal`, otherwise `association`. A keyword
matches without regard to case from the start of a word and may be followed by further letters,
so `repurpos` matches "repurposing" and `cause` matches "causes" but not "because".

Names are not wording. A keyword match that lies wholly inside an occurrence of the record's
`outcome_as_written` or `protein_as_written` in the span is dropped before the class is
assigned ("treatment" in "treatment-resistant depression", "drug" in "drug-induced liver
injury"), and the class is read from the matches that remain: `target` when a target keyword
remains, else `causal` when a causal keyword remains, else `association`. A name occurs in the
span where its words follow one another, without regard to case, separated by spaces, hyphens
or dashes. Every match is kept with its position and the name it lay in (`keyword_matches`),
and the class the span would have had without this rule is kept beside the class
(`wording_class_unmasked`).

Novelty language: the span contains, without regard to case and as a whole word or phrase, one
of the listed terms. The name rule applies here too: a match that lies wholly inside an
occurrence of the record's outcome or protein name ("novel" in "novel coronavirus infection")
is dropped, and `novelty_language` is set when a match remains. Every match is kept with its
position and the name it lay in (`novelty_matches`), and the flag the span would have had
without the rule is kept beside the flag (`novelty_language_unmasked`).

Input: an extraction file written by run_extraction.py. The record index within the abstract
gives the same `claim_record_id` as verify_claims.py (`<pmid>:<index>`). Output, next to the
verification outputs of the same run: wording.jsonl and wording_summary.json.

Usage: uv run scripts/tag_wording.py --extraction outputs/parsed/sol_extraction_<label>_<rev>.jsonl
"""

import argparse
import collections
import json
import pathlib
import re
from collections.abc import Sequence

from pydantic import BaseModel

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
LEXICON = EXP / "verification" / "wording_lexicon.json"


class WordingError(Exception):
    """An output exists, or the lexicon is malformed."""


class KeywordMatch(BaseModel):
    wording_class: str
    keyword: str
    start: int
    end: int
    inside: str | None


class NoveltyMatch(BaseModel):
    term: str
    start: int
    end: int
    inside: str | None


class Wording(BaseModel):
    claim_record_id: str
    wording_class: str
    wording_keyword: str | None
    wording_class_unmasked: str
    keyword_matches: list[KeywordMatch]
    novelty_language: bool
    novelty_terms: list[str]
    novelty_language_unmasked: bool
    novelty_matches: list[NoveltyMatch]


NAME_GAP = r"[\s\-‐‑‒–—]+"
NAME_FIELDS = ("protein", "outcome")


def _words(term: str) -> str:
    return r"\s+".join(re.escape(w) for w in term.split())


def name_occurrences(name: str, span: str) -> list[tuple[int, int]]:
    """(start, end) of every occurrence of a protein or outcome name in the span: its words in
    order, any case, separated by spaces, hyphens or dashes."""
    words = [w for w in re.split(NAME_GAP, name.strip()) if w]
    if not words:
        return []
    pattern = re.compile(NAME_GAP.join(re.escape(w) for w in words), re.I)
    return [(m.start(), m.end()) for m in pattern.finditer(span)]


def name_zones(span: str, names: Sequence[str]) -> list[tuple[int, int, str]]:
    """(start, end, field) of every occurrence of the protein and outcome names in the span.
    `names` is (protein_as_written, outcome_as_written)."""
    return [(s, e, field) for field, name in zip(NAME_FIELDS, names)
            for s, e in name_occurrences(name, span)]


def inside_name(start: int, end: int, zones: Sequence[tuple[int, int, str]]) -> str | None:
    """The name fields whose occurrence wholly contains [start, end), joined by `|`."""
    return "|".join(sorted({f for s, e, f in zones if s <= start and end <= e})) or None


class Lexicon:
    def __init__(self, raw: dict):
        wc = raw["wording_class"]
        if set(wc["order"]) != set(wc["keywords"]):
            raise WordingError("wording_class order and keywords name different classes")
        self.default = wc["default"]
        self.classes = [(name, [(k, re.compile(r"(?<![A-Za-z0-9])" + _words(k), re.I))
                                for k in wc["keywords"][name]]) for name in wc["order"]]
        self.novelty = [(t, re.compile(r"(?<![A-Za-z0-9])" + _words(t) + r"(?![A-Za-z0-9])",
                                       re.I)) for t in raw["novelty_language"]]

    def keyword_matches(self, span: str, names: Sequence[str] = ()) -> list[KeywordMatch]:
        """Every wording-keyword match in the span, in lexicon order then span order. `names`
        is (protein_as_written, outcome_as_written); a match wholly inside an occurrence of one
        of them carries that field in `inside`."""
        zones = name_zones(span, names)
        out = []
        for name, keywords in self.classes:
            for keyword, pattern in keywords:
                for m in pattern.finditer(span):
                    out.append(KeywordMatch(wording_class=name, keyword=keyword,
                                            start=m.start(), end=m.end(),
                                            inside=inside_name(m.start(), m.end(), zones)))
        return out

    def classify(self, matches: Sequence[KeywordMatch], masked: bool) -> tuple[str, str | None]:
        """First class in the registered order with a match; with `masked`, matches inside a
        protein or outcome name do not count."""
        for name, _ in self.classes:
            for m in matches:
                if m.wording_class == name and not (masked and m.inside):
                    return name, m.keyword
        return self.default, None

    def wording_class(self, span: str, names: Sequence[str] = ()) -> tuple[str, str | None]:
        return self.classify(self.keyword_matches(span, names), masked=True)

    def novelty_matches(self, span: str, names: Sequence[str] = ()) -> list[NoveltyMatch]:
        """Every novelty-term match in the span, in lexicon order then span order; a match
        wholly inside an occurrence of the protein or outcome name carries that field in
        `inside`."""
        zones = name_zones(span, names)
        return [NoveltyMatch(term=t, start=m.start(), end=m.end(),
                             inside=inside_name(m.start(), m.end(), zones))
                for t, pattern in self.novelty for m in pattern.finditer(span)]

    def novelty_terms(self, span: str, names: Sequence[str] = ()) -> list[str]:
        """The listed terms with at least one match outside the protein and outcome names, in
        lexicon order."""
        return list(dict.fromkeys(m.term for m in self.novelty_matches(span, names)
                                  if not m.inside))


def tag(claim_record_id: str, span: str, lexicon: Lexicon, protein: str, outcome: str
        ) -> Wording:
    matches = lexicon.keyword_matches(span, (protein, outcome))
    name, keyword = lexicon.classify(matches, masked=True)
    novelty = lexicon.novelty_matches(span, (protein, outcome))
    terms = list(dict.fromkeys(m.term for m in novelty if not m.inside))
    return Wording(claim_record_id=claim_record_id, wording_class=name, wording_keyword=keyword,
                   wording_class_unmasked=lexicon.classify(matches, masked=False)[0],
                   keyword_matches=matches, novelty_language=bool(terms), novelty_terms=terms,
                   novelty_language_unmasked=bool(novelty), novelty_matches=novelty)


def tag_rows(rows: list[dict], lexicon: Lexicon) -> list[Wording]:
    """Wording records of every claim of every `ok` extraction row, in verify_claims.py's
    record order."""
    return [tag(f"{row['pmid']}:{i:03d}", c["evidence_span"], lexicon, c["protein_as_written"],
                c["outcome_as_written"])
            for row in rows if row["status"] == "ok"
            for i, c in enumerate(row["output"]["claims"])]


def summarize(rows: list[Wording]) -> dict:
    return {"n_records": len(rows),
            "wording_class": dict(collections.Counter(r.wording_class for r in rows)),
            "wording_class_unmasked": dict(collections.Counter(
                r.wording_class_unmasked for r in rows)),
            "class_changed_by_name_masking": dict(collections.Counter(
                f"{r.wording_class_unmasked} -> {r.wording_class}" for r in rows
                if r.wording_class != r.wording_class_unmasked)),
            "keyword_matches_inside_a_name": dict(collections.Counter(
                f"{m.inside}:{m.keyword}" for r in rows for m in r.keyword_matches if m.inside)),
            "wording_keyword": dict(collections.Counter(
                r.wording_keyword for r in rows if r.wording_keyword)),
            "novelty_language": sum(r.novelty_language for r in rows),
            "novelty_language_unmasked": sum(r.novelty_language_unmasked for r in rows),
            "novelty_language_removed_by_name_masking": sum(
                r.novelty_language_unmasked and not r.novelty_language for r in rows),
            "novelty_matches_inside_a_name": dict(collections.Counter(
                f"{m.inside}:{m.term}" for r in rows for m in r.novelty_matches if m.inside)),
            "novelty_terms": dict(collections.Counter(t for r in rows for t in r.novelty_terms))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extraction", type=pathlib.Path, required=True)
    a = ap.parse_args()
    out_dir = EXP / "outputs" / "verification" / a.extraction.stem
    out = out_dir / "wording.jsonl"
    if out.exists():
        raise WordingError(f"{out} exists; archive it before rerunning")
    lexicon = Lexicon(json.loads(LEXICON.read_text()))
    rows = tag_rows([json.loads(l) for l in a.extraction.read_text().splitlines()
                     if l.strip()], lexicon)
    out_dir.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(r.model_dump_json() + "\n" for r in rows))
    summary = {"extraction": str(a.extraction), "lexicon": str(LEXICON.relative_to(EXP)),
               **summarize(rows)}
    (out_dir / "wording_summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
