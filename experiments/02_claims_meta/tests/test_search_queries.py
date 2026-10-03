import datetime
import pathlib
import re

import httpx
import pytest

import search_queries as sq

EXP = pathlib.Path(sq.__file__).resolve().parent.parent
START, END = sq.CONFIRMATORY


def registered_blocks() -> dict[str, str]:
    text = (EXP / "PREREG.md").read_text()
    code = re.search(r"\*\*Sources and queries\.\*\*.*?```text\n(.*?)```", text, re.S).group(1)
    blocks: dict[str, str] = {}
    for line in code.splitlines():
        m = re.match(r"([A-Z]+)\s+= (.*)", line)
        name = m.group(1) if m else name
        blocks[name] = (blocks.get(name, "") + " " + (m.group(2) if m else line)).strip()
    return {k: " ".join(v.split()) for k, v in blocks.items()}


def top_level(expr: str, op: str) -> list[str]:
    parts, depth, quoted, last, i = [], 0, False, 0, 0
    while i < len(expr):
        c = expr[i]
        quoted = quoted != (c == '"')
        if not quoted:
            depth += (c in "([") - (c in ")]")
            if depth == 0 and expr.startswith(f" {op} ", i):
                parts.append(expr[last:i])
                last = i + len(op) + 2
                i = last
                continue
        i += 1
    assert depth == 0 and not quoted
    return parts + [expr[last:]]


def test_pubmed_blocks_are_the_registered_text():
    registered = registered_blocks()
    assert set(registered) == set(sq.PUBMED_BLOCKS) | {"DATE", "UPDATE"}
    for name, terms in sq.PUBMED_BLOCKS.items():
        assert " OR ".join(terms) == registered[name]
    assert registered["DATE"] == f'"{START:%Y/%m/%d}"[dp] : "{END:%Y/%m/%d}"[dp]'
    assert registered["UPDATE"] == f'"{sq.UPDATE_START:%Y/%m/%d}"[dp] : "SEARCH_DATE"[dp]'


def test_queries_are_the_registered_block_combinations():
    text = (EXP / "PREREG.md").read_text()
    found = dict(re.findall(r"\*\*(Q\d)\*\*\s+`([^`]+)`", text))
    assert found == {q: " AND ".join(f"({b})" for b in blocks) + " AND DATE"
                     for q, blocks in sq.QUERIES.items()}


def test_queries_md_is_the_generated_text():
    assert sq.QUERIES_MD.read_text() == sq.render_markdown()


@pytest.mark.parametrize("query", list(sq.QUERIES))
def test_each_query_is_an_and_of_or_blocks_in_every_source(query):
    n = len(sq.QUERIES[query])
    pubmed = top_level(sq.pubmed_query(query, START, END), "AND")
    epmc = top_level(sq.epmc_query(query, START, END), "AND")
    search, date_from, date_to = sq.openalex_filter(query, START, END).split(",")
    openalex = top_level(search.removeprefix(f"{sq.OPENALEX_FILTER}:"), "AND")
    assert (len(pubmed), len(epmc), len(openalex)) == (n + 1, n + 1, n)
    for part in pubmed[:n] + epmc[:n] + openalex:
        assert part.startswith("(") and part.endswith(")")
        assert len(top_level(part[1:-1], "AND")) == 1
    assert pubmed[n] == '("2019/01/01"[dp] : "2025/12/31"[dp])'
    assert epmc[n] == "FIRST_PDATE:[2019-01-01 TO 2025-12-31]"
    assert (date_from, date_to) == ("from_publication_date:2019-01-01",
                                    "to_publication_date:2025-12-31")


@pytest.mark.parametrize("block", list(sq.PUBMED_BLOCKS))
def test_every_registered_term_is_translated(block):
    epmc = top_level(sq.epmc_block(block), "OR")
    openalex = top_level(sq.openalex_block(block), "OR")
    want_epmc, want_openalex = [], []
    for raw in sq.PUBMED_BLOCKS[block]:
        term = sq.parse_term(raw)
        if term.kind == "block":
            want_epmc.append(f"({sq.epmc_block(term.text)})")
            want_openalex.append(f"({sq.openalex_block(term.text)})")
        elif term.kind == "mesh":
            want_epmc.append(f'KW:"{term.text}"')
        elif term.kind == "all_of":
            words = [p.text for p in term.parts]
            want_epmc.append("(" + " AND ".join(f"TITLE_ABS:{w}" for w in words) + ")")
            want_openalex.append("(" + " AND ".join(words) + ")")
        else:
            forms = [term.text]
            if term.phrase and term.truncated:
                stem = term.text.rsplit(" ", 1)[1][:-1]
                forms = sq.completions(term.text)
                assert len(forms) >= 2 and all(f.rsplit(" ", 1)[1].lower().startswith(
                    stem.lower()) for f in forms)
            forms = forms + list(sq.HYPHENATED_FORMS.get(term.text, ()))
            for f in forms:
                bare = f.rstrip("*").isalnum()
                want_epmc.append(f"TITLE_ABS:{f}" if bare else f'TITLE_ABS:"{f}"')
                want_openalex.append(f if bare else f'"{f}"')
    assert epmc == want_epmc
    assert openalex == want_openalex


def test_no_translation_truncates_inside_a_quoted_phrase():
    for query in sq.QUERIES:
        for text in (sq.epmc_query(query, START, END), sq.openalex_filter(query, START, END)):
            phrases = re.findall(r'"([^"]*)"', text)
            assert phrases and not any("*" in phrase for phrase in phrases)


def test_openalex_requests_fit_the_url_limit_and_carry_no_address():
    for query in sq.QUERIES:
        for start, end in sq.windows(datetime.date(2026, 12, 31)).values():
            url = httpx.Request("GET", "https://api.openalex.org/works", params={
                "filter": sq.openalex_filter(query, start, end), "per_page": 100,
                "select": "id,doi,ids,display_name,publication_date,publication_year,type,"
                          "language,authorships,primary_location,abstract_inverted_index",
                "cursor": "x" * 400}).url
            assert len(str(url).encode()) <= sq.OPENALEX_MAX_URL_BYTES
            assert "mailto" not in str(url) and "@" not in str(url)


def test_update_window_ends_on_the_search_date():
    day = datetime.date(2026, 10, 9)
    assert sq.windows(day) == {"confirmatory": (datetime.date(2019, 1, 1),
                                                datetime.date(2025, 12, 31)),
                               "update": (datetime.date(2026, 1, 1), day)}
    assert sq.pubmed_query("Q2", *sq.windows(day)["update"]).endswith(
        'AND ("2026/01/01"[dp] : "2026/10/09"[dp])')


def test_unparsed_or_untranslatable_terms_raise():
    with pytest.raises(sq.QueryError):
        sq.parse_term("plasma protein[tiab]")
    with pytest.raises(sq.QueryError):
        sq.parse_term("pro*teom[tiab]")
    with pytest.raises(sq.QueryError):
        sq.completions("plasma metabol*")
