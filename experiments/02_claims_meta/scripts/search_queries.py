# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.13.5"]
# ///
"""The registered search queries and their Europe PMC and OpenAlex translations.

The PubMed blocks below are the text of PREREG.md §Data collection procedures, one term per
entry (`tests/test_search_queries.py` compares them with the registration). The Europe PMC and
OpenAlex queries are derived from the same terms, block for block, by these rules:

    PubMed term                  Europe PMC                         OpenAlex
    "X"[Mesh]                    KW:"X"                             no equivalent; omitted
    word[tiab]                   TITLE_ABS:word                     word
    hyphenated-word[tiab]        TITLE_ABS:"hyphenated-word"        "hyphenated-word"
    stem*[tiab]                  TITLE_ABS:stem*                    stem*
    colocali*, repurpos*         also the hyphenated forms listed in HYPHENATED_FORMS
    "a phrase"[tiab]             TITLE_ABS:"a phrase"               "a phrase"
    "a phrase stem*"[tiab]       one TITLE_ABS:"..." per listed     one "..." per listed
                                 completion of the stem, OR-ed      completion, OR-ed
    (a[tiab] AND b*[tiab])       (TITLE_ABS:a AND TITLE_ABS:b*)     (a AND b*)
    "y/m/d"[dp] : "y/m/d"[dp]    FIRST_PDATE:[y-m-d TO y-m-d]       from_publication_date,
                                                                    to_publication_date

Neither Europe PMC nor OpenAlex accepts a truncation inside a quoted phrase within a Boolean
query, so a truncated phrase is written out as the completions in PHRASE_COMPLETIONS. PubMed
matches "co-localization" for colocali*[tiab]; the other two sources do not, so the hyphenated
forms in HYPHENATED_FORMS are added to them. The
OpenAlex query is the value of the `title_and_abstract.search.exact` filter (unstemmed, title
and abstract only). The Europe PMC request sends `synonym=false`.

Usage: uv run scripts/search_queries.py --write     (writes search/queries.md)
"""

import argparse
import datetime
import pathlib
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
QUERIES_MD = EXP / "search" / "queries.md"

PUBMED_BLOCKS: dict[str, tuple[str, ...]] = {
    "MR": ('"Mendelian Randomization Analysis"[Mesh]', '"Mendelian randomization"[tiab]',
           '"Mendelian randomisation"[tiab]'),
    "PROT": ('proteome-wide[tiab]', '"proteome wide"[tiab]', 'protein-wide[tiab]',
             'proteomic*[tiab]', '"plasma proteom*"[tiab]', '"circulating proteom*"[tiab]',
             '"plasma protein*"[tiab]', '"serum protein*"[tiab]', '"circulating protein*"[tiab]',
             'pQTL[tiab]', 'pQTLs[tiab]', '"protein quantitative trait*"[tiab]',
             '"protein QTL*"[tiab]', '"genetically proxied protein*"[tiab]',
             '"genetically predicted protein*"[tiab]',
             '"genetically predicted plasma protein*"[tiab]',
             '(plasma[tiab] AND protein*[tiab])'),
    "PLAT": ('SomaScan[tiab]', 'SomaLogic[tiab]', 'Olink[tiab]', 'Fenland[tiab]',
             '"UKB-PPP"[tiab]', '"UK Biobank Pharma Proteomics"[tiab]', 'deCODE[tiab]',
             'SCALLOP[tiab]', '"INTERVAL study"[tiab]', 'ARIC[tiab]'),
    "TARGET": ('"drug target*"[tiab]', '"therapeutic target*"[tiab]', 'druggable[tiab]',
               'repurpos*[tiab]', '"target prioriti*"[tiab]', '"therapeutic prioriti*"[tiab]',
               '"drug-target MR"[tiab]'),
    "LOCUS": ('"summary-data-based Mendelian randomization"[tiab]', 'SMR[tiab]',
              'colocali*[tiab]', '"cis-MR"[tiab]', '"cis Mendelian randomization"[tiab]'),
    "PQTLB": ('pQTL[tiab]', 'pQTLs[tiab]', '"protein quantitative trait*"[tiab]',
              '"protein QTL*"[tiab]', '"plasma protein*"[tiab]', 'proteom*[tiab]'),
    "GEN": ('(MR)', 'pQTL[tiab]', 'pQTLs[tiab]', '"protein quantitative trait*"[tiab]',
            '"genetically predicted"[tiab]', '"genetically proxied"[tiab]', '"cis-MR"[tiab]'),
}
QUERIES: dict[str, tuple[str, ...]] = {
    "Q1": ("MR", "PROT"),
    "Q2": ("MR", "PLAT"),
    "Q3": ("TARGET", "PQTLB", "GEN"),
    "Q4": ("LOCUS", "PQTLB"),
}
CONFIRMATORY = (datetime.date(2019, 1, 1), datetime.date(2025, 12, 31))
UPDATE_START = datetime.date(2026, 1, 1)

# Completions written out for a truncated last word of a quoted phrase, by lower-cased stem.
PHRASE_COMPLETIONS: dict[str, tuple[str, ...]] = {
    "proteom": ("proteome", "proteomes", "proteomic", "proteomics"),
    "protein": ("protein", "proteins"),
    "trait": ("trait", "traits"),
    "qtl": ("QTL", "QTLs"),
    "target": ("target", "targets", "targeted", "targeting"),
    "prioriti": ("prioritization", "prioritisation", "prioritizing", "prioritising",
                 "prioritize", "prioritise", "prioritized", "prioritised", "priorities"),
}
# PubMed matches the hyphenated spelling of an unhyphenated term (colocali*[tiab] retrieves
# "co-localization"); Europe PMC and OpenAlex do not, so these forms are added beside the term.
HYPHENATED_FORMS: dict[str, tuple[str, ...]] = {
    "colocali*": ("co-localization", "co-localisation", "co-localizations", "co-localisations",
                  "co-localized", "co-localised", "co-localize", "co-localise", "co-localizes",
                  "co-localises", "co-localizing", "co-localising"),
    "repurpos*": ("re-purpose", "re-purposed", "re-purposes", "re-purposing"),
}
OPENALEX_FILTER = "title_and_abstract.search.exact"
OPENALEX_MAX_URL_BYTES = 4094


class QueryError(Exception):
    """A term cannot be parsed or translated."""


class Term(BaseModel):
    model_config = ConfigDict(frozen=True)
    kind: Literal["mesh", "text", "all_of", "block"]
    text: str = ""
    parts: tuple["Term", ...] = ()

    @property
    def truncated(self) -> bool:
        return self.text.endswith("*")

    @property
    def phrase(self) -> bool:
        return " " in self.text


def parse_term(term: str) -> Term:
    block = re.fullmatch(r"\(([A-Z]+)\)", term)
    if block:
        return Term(kind="block", text=block.group(1))
    if term.startswith("(") and term.endswith(")") and " AND " in term:
        return Term(kind="all_of", parts=tuple(parse_term(t) for t in term[1:-1].split(" AND ")))
    m = re.fullmatch(r'"([^"]+)"\[(Mesh|tiab)\]|([^\s"\[\]()]+)\[(tiab)\]', term)
    if not m:
        raise QueryError(f"unparsed term: {term}")
    text, field = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
    if field == "Mesh":
        return Term(kind="mesh", text=text)
    if "*" in text[:-1]:
        raise QueryError(f"truncation inside a term: {term}")
    return Term(kind="text", text=text)


def completions(phrase: str) -> list[str]:
    """The written-out forms of a truncated phrase ("plasma protein*")."""
    head, _, last = phrase.rpartition(" ")
    stem = last[:-1].lower()
    if stem not in PHRASE_COMPLETIONS:
        raise QueryError(f"no completions listed for the stem of {phrase!r}")
    return [f"{head} {c}" for c in PHRASE_COMPLETIONS[stem]]


def pubmed_block(name: str) -> str:
    """The block as registered, with the (MR) reference expanded."""
    return " OR ".join(f"({pubmed_block(parse_term(t).text)})" if parse_term(t).kind == "block"
                       else t for t in PUBMED_BLOCKS[name])


def _text(term: Term, prefix: str) -> list[str]:
    """One text term in Europe PMC (prefix `TITLE_ABS:`) or OpenAlex (no prefix) syntax."""
    if term.phrase and term.truncated:
        return [f'{prefix}"{c}"' for c in completions(term.text)]
    if term.phrase or not term.text.rstrip("*").isalnum():
        if term.truncated:
            raise QueryError(f"truncated hyphenated word has no translation: {term.text}")
        return [f'{prefix}"{term.text}"']
    return [f"{prefix}{term.text}"] + [f'{prefix}"{h}"'
                                       for h in HYPHENATED_FORMS.get(term.text, ())]


def _translate(name: str, prefix: str, mesh: str | None) -> str:
    out: list[str] = []
    for raw in PUBMED_BLOCKS[name]:
        term = parse_term(raw)
        if term.kind == "block":
            out.append(f"({_translate(term.text, prefix, mesh)})")
        elif term.kind == "mesh":
            if mesh is not None:
                out.append(f'{mesh}"{term.text}"')
        elif term.kind == "all_of":
            parts = [p for t in term.parts for p in _text(t, prefix)]
            if len(parts) != len(term.parts):
                raise QueryError(f"a truncated phrase inside an AND group: {raw}")
            out.append("(" + " AND ".join(parts) + ")")
        else:
            out.extend(_text(term, prefix))
    return " OR ".join(out)


def epmc_block(name: str) -> str:
    return _translate(name, "TITLE_ABS:", "KW:")


def openalex_block(name: str) -> str:
    return _translate(name, "", None)


def windows(search_date: datetime.date) -> dict[str, tuple[datetime.date, datetime.date]]:
    return {"confirmatory": CONFIRMATORY, "update": (UPDATE_START, search_date)}


def pubmed_query(query: str, start: datetime.date, end: datetime.date) -> str:
    blocks = " AND ".join(f"({pubmed_block(b)})" for b in QUERIES[query])
    return f'{blocks} AND ("{start:%Y/%m/%d}"[dp] : "{end:%Y/%m/%d}"[dp])'


def epmc_query(query: str, start: datetime.date, end: datetime.date) -> str:
    blocks = " AND ".join(f"({epmc_block(b)})" for b in QUERIES[query])
    return f"{blocks} AND FIRST_PDATE:[{start.isoformat()} TO {end.isoformat()}]"


def openalex_filter(query: str, start: datetime.date, end: datetime.date) -> str:
    """The value of the `filter` parameter of an OpenAlex /works request."""
    search = " AND ".join(f"({openalex_block(b)})" for b in QUERIES[query])
    if "," in search or ":" in search:
        raise QueryError("a comma or colon in an OpenAlex search value would end the filter")
    return (f"{OPENALEX_FILTER}:{search},from_publication_date:{start.isoformat()},"
            f"to_publication_date:{end.isoformat()}")


def render_markdown() -> str:
    """search/queries.md: every block and query in the three syntaxes."""
    start, end = CONFIRMATORY
    lines = [
        "# Registered search queries",
        "",
        "Generated by `scripts/search_queries.py --write` from the blocks registered in",
        "PREREG.md §Data collection procedures; `tests/test_search_queries.py` fails if this",
        "file and the script disagree, or if the PubMed blocks differ from the registration.",
        "",
        "## Translation rules",
        "",
        "| PubMed | Europe PMC | OpenAlex |",
        "|---|---|---|",
        '| `"X"[Mesh]` | `KW:"X"` (MeSH terms and author keywords) | no MeSH filter; omitted |',
        "| `word[tiab]` | `TITLE_ABS:word` | `word` |",
        '| `hyphenated-word[tiab]` | `TITLE_ABS:"hyphenated-word"` | `"hyphenated-word"` |',
        "| `stem*[tiab]` | `TITLE_ABS:stem*` | `stem*` |",
        "| `colocali*[tiab]`, `repurpos*[tiab]` | the stem, and each listed hyphenated form "
        "| the stem, and each listed hyphenated form |",
        '| `"a phrase"[tiab]` | `TITLE_ABS:"a phrase"` | `"a phrase"` |',
        '| `"a phrase stem*"[tiab]` | each listed completion, OR-ed | each listed completion, '
        "OR-ed |",
        "| `(a[tiab] AND b*[tiab])` | `(TITLE_ABS:a AND TITLE_ABS:b*)` | `(a AND b*)` |",
        '| `"y/m/d"[dp] : "y/m/d"[dp]` | `FIRST_PDATE:[y-m-d TO y-m-d]` | '
        "`from_publication_date:y-m-d,to_publication_date:y-m-d` |",
        "",
        "Europe PMC: REST `search`, `resultType=core`, `synonym=false`, every source (no `SRC`",
        "restriction). OpenAlex: `/works`, the query is the value of the",
        f"`{OPENALEX_FILTER}` filter (unstemmed; title and abstract only), default corpus,",
        "no email address in any request.",
        "",
        "Completions written out for a truncated phrase:",
        "",
        "| stem | completions |",
        "|---|---|",
    ]
    lines += [f"| `{stem}*` | {', '.join(c)} |" for stem, c in PHRASE_COMPLETIONS.items()]
    lines += ["",
              "Hyphenated forms added in Europe PMC and OpenAlex (PubMed retrieves them for the",
              "unhyphenated term):",
              "",
              "| term | hyphenated forms |",
              "|---|---|"]
    lines += [f"| `{t}` | {', '.join(h)} |" for t, h in HYPHENATED_FORMS.items()]
    lines += ["", "## Blocks", ""]
    for name in PUBMED_BLOCKS:
        lines += [f"### {name}", "", "PubMed:", "", "```text", pubmed_block(name), "```", "",
                  "Europe PMC:", "", "```text", epmc_block(name), "```", "",
                  "OpenAlex:", "", "```text", openalex_block(name), "```", ""]
    lines += ["## Queries", "",
              "| query | blocks |", "|---|---|"]
    lines += [f"| {q} | {' AND '.join(f'({b})' for b in blocks)} AND DATE |"
              for q, blocks in QUERIES.items()]
    lines += ["",
              f"DATE is {start.isoformat()} to {end.isoformat()} (confirmatory window). The "
              f"update set runs the same queries from {UPDATE_START.isoformat()} to the search "
              "date.",
              ""]
    for q in QUERIES:
        lines += [f"### {q}, confirmatory window", "", "PubMed:", "", "```text",
                  pubmed_query(q, start, end), "```", "", "Europe PMC:", "", "```text",
                  epmc_query(q, start, end), "```", "", "OpenAlex (`filter=`):", "", "```text",
                  openalex_filter(q, start, end), "```", ""]
    lines += [
        "## De-duplication",
        "",
        "The union across queries and sources, deduplicated by PMID, PMCID and DOI, is the",
        "screening set (`scripts/assemble_screening_set.py`): two retrieved records are one",
        "screening record when they share a PMID, a PMCID or a DOI (DOIs compared",
        "case-insensitively, without a resolver prefix), and sharing is transitive.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="write search/queries.md")
    a = ap.parse_args()
    text = render_markdown()
    if a.write:
        QUERIES_MD.write_text(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
