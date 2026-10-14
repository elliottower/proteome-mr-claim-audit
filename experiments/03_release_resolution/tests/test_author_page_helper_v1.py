import pathlib
import re

import author_page_helper_v1 as hp

HERE = pathlib.Path(__file__).resolve().parents[1]
DEFS = HERE.parent / "02_claims_meta" / "outputs" / "manual_coding" / "2026-10-03" / "coders" / "dictionary_definitions.csv"
ACC = HERE / "reference" / "accession_releases.csv"


def card(n: int, abstract: str, name: str = "not stated", side: str = "outcome", row: str = "") -> str:
    row = row or f"{n:012x}"
    return (f'<section class="card" data-row="{row}" data-n="{n}"><div class="top"><span>{n} of 42 · '
            f'{side} side</span><span>row {row}</span></div><h2>{name}</h2><div class="pair"><div class="ans q1">'
            f'<div class="lab">Answer 1</div><ul><li>none</li></ul></div></div><div class="lab">Abstract</div>'
            f'<p class="snip">{abstract}</p><div class="ctl"><label><input type="radio" name="r{n + 1}" '
            f'value="answer_1"> Answer 1</label><input type="text" class="reason" placeholder="r"></div></section>')


def page(cards: list[str]) -> str:
    return ('<!doctype html><html><head><style>x{}</style></head><body><h1>SA1: 42 rows for the author</h1>'
            '<p>intro</p><div id="bar"><span id="count"></span><button id="save">Save my marks</button></div>'
            + "".join(cards) + '<script>\nconst KEY="sa1_author_page_deviation01";a={page:"sa1_author_page_deviation01"};'
            'b="sa1_author_marks_42.json";c="sa1_author_marks_42.json";</script></body></html>')


def built(abstract: str, name: str = "not stated", side: str = "outcome") -> tuple[str, dict]:
    return hp.build_card(card(1, abstract, name, side), hp.load_dictionary(DEFS),
                         hp.Index(hp.load_dictionary(DEFS), hp.load_accessions(ACC)))


def tags(made: str) -> list[str]:
    return re.findall(r'<span class="tag [^"]*">(.*?)</span>', made)


def test_a_release_number_after_its_resource_is_highlighted_and_mapped_and_alone_is_not():
    made, counts = built("Validation used the FinnGen R10 and UK Biobank cohorts.")
    assert '<span class="ident">R10</span><span class="tag idmap">→ FinnGen R10 (release after resource name)</span>' in made
    assert counts["identifiers"] == 1 and counts["identifiers_mapped"] == 1
    made, counts = built("Validation used R10 data.")
    assert '<span class="ident">R10</span><span class="tag idmap">no match</span>' in made
    assert counts["identifiers_mapped"] == 0


def test_a_stated_maximum_matches_the_one_row_documented_up_to_that_size():
    made, counts = built("Disease effects from UK Biobank (N≤408 961) and 12,345 controls.", "UKB-SAIGE")
    assert tags(made) == ["size match → UK Biobank SAIGE PheWeb (Zhou et al. 2018)"]
    assert '<span class="num">12,345</span>' in made and counts["numbers"] == 2
    assert counts["size_question"] and hp.html.escape(hp.QUESTION) in made


def test_an_explicit_qualifier_makes_a_number_approximate_and_trailing_zeros_do_not():
    made, _ = built("Data from about 408,961 participants.", "UKB-SAIGE")
    assert tags(made) == [] and '<span class="num">408,961</span>' in made
    made, _ = built("Up to 628,000 participants.", "Sakaue 2021 cross-population", "outcome")
    assert tags(made) == ["size match → Sakaue 2021 cross-population meta-analysis (BBJ + UKB + FinnGen R3)"]


def test_equal_sizes_are_ambiguous_different_rows_conflict_and_repeats_count_once():
    made, _ = built("Proteins from 10 708 participants.", "Fenland", "pqtl")
    assert tags(made) == ["size ambiguous"]
    made, _ = built("deCODE with 35 559 and later 35,892 participants.", "deCODE", "pqtl")
    assert tags(made) == ["size conflict → deCODE SomaScan v4 (Ferkingstad 2021)",
                          "size conflict → deCODE SomaScan v4 (Eldjarn 2023 update)"]
    made, _ = built("deCODE with 35 559 and again 35,559 participants.", "deCODE", "pqtl")
    assert tags(made) == ["size match → deCODE SomaScan v4 (Ferkingstad 2021)"] * 2


def test_the_coders_marks_survive_around_new_highlights():
    made, _ = built('In <mark class="q1">FinnGen R</mark>10 &amp; more, n=7.')
    assert ('<p class="snip">In <mark class="q1">FinnGen </mark><mark class="q1"><span class="ident">R</span>'
            '</mark><span class="ident">10</span><span class="tag idmap">→ FinnGen R10 (release after '
            'resource name)</span> &amp; more, n=<span class="num">7</span>.</p>') in made


def test_the_page_keeps_42_cards_and_their_controls_and_moves_marks_to_a_new_key():
    src = page([card(n, f"Text {n} with 5 GWAS.") for n in range(1, 43)])
    made, counts = hp.build(src, hp.load_dictionary(DEFS), hp.load_accessions(ACC))
    assert len(counts) == 42 and made.count('<section class="card"') == 42
    head = r'<section class="card" data-row="[0-9a-f]+" data-n="\d+">'
    assert re.findall(head, made) == re.findall(head, src)
    assert re.findall(r'name="r\d+" value="\w+"', made) == re.findall(r'name="r\d+" value="\w+"', src)
    assert 'const KEY="sa1_author_page_assisted_v2",OLD="sa1_author_page_deviation01"' in made
    assert "localStorage.setItem(OLD" not in made and "entered_before_aids:true" in made
    assert made.count('"sa1_author_marks_42_assisted.json"') == 2 and "sa1_author_marks_42.json" not in made
    assert hp.html.escape(hp.INSTRUCTION) in made and 'id="legend"' in made
    for word in ("claude", "gpt", "fable", "astra", "sonnet", "gemini"):
        assert word not in made.lower()
