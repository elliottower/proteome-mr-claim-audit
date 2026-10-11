import csv
import json
import pathlib
import random

import pytest

import cut_supplements as cs
import manual_coding_passages_v3 as passages

HERE = pathlib.Path(__file__).resolve().parents[1]
DICTIONARY = HERE.parent / "02_claims_meta" / "dataset_dictionary.csv"
PATTERNS = HERE / "reference" / "c1_scanner_patterns_v2.json"


@pytest.fixture(scope="module")
def rows():
    with DICTIONARY.open(newline="") as fh:
        return list(csv.DictReader(fh))


@pytest.fixture(scope="module")
def matcher(rows):
    return cs.TermMatcher(rows, json.loads(PATTERNS.read_text()))


def variants(term):
    field, text = term
    if field == "source_citation":
        surname, year = text.split("|")
        return [f"as in {surname} et al. ({year})", f"{surname}x {year}", f"{surname} {year}1",
                f"{year}: {surname.upper()}"]
    if field == "sample_size":
        grouped = f"{int(text):,}"
        return [f"n = {text}", f"n = {grouped}", f"n = {text}1", f"n={text[:-1]}"]
    return [f"we used {text}.", f"x{text}", f"({text.upper()})", f"{text}9 other",
            f"pre–{text}"]


def test_the_combined_matcher_agrees_with_paper_1s_term_rule_line_by_line(rows, matcher):
    terms = list(dict.fromkeys(t for row in rows for t in passages.dictionary_terms(row)))
    rng = random.Random(1)
    lines = [v for t in rng.sample(terms, 400) for v in variants(t)]
    lines += ["nothing of interest here", "the cohort had 12 participants", "1999 and 2025"]
    for line in lines:
        want = any(passages.matches(t, line) for t in terms)
        assert matcher.term(line) == want, line


def test_accessions_and_releases_mark_a_row(matcher):
    assert matcher("GCST90012345\tbeta\t0.1")
    assert matcher("ukb-b-12345 summary")
    assert matcher("data of finngen r7 were used") or matcher("FinnGen R7 data")
    assert not matcher("protein\tbeta\tse")


def entry(text, kind="XLSX", sheets=1):
    return {"name": "s.xlsx", "type": kind, "text": text, "sheets": sheets}


def test_a_supplement_under_200000_characters_is_given_whole(matcher):
    text = "## sheet A\nprotein\tbeta\nX\t0.1"
    out = cs.cut(entry(text), matcher)
    assert out == {"cut": False, "text": text, "characters_before": len(text),
                   "characters_after": len(text), "lines_kept": None}


def test_a_large_workbook_keeps_sheet_names_headers_and_matching_rows_with_their_header(matcher):
    filler = "\n".join(f"P{i % 97}\tq{i % 9}" for i in range(30000))
    text = ("## sheet Table S1\nprotein\tsource\n" + filler + "\nIL6\tFinnGen R7\n"
            + filler + "\nCRP\tGCST90012345\n## sheet Notes\nhead\tx\nnothing\ty")
    out = cs.cut(entry(text), matcher)
    assert out["cut"] and len(text) >= 200_000
    assert out["text"].split("\n") == ["## sheet Table S1", "protein\tsource", "IL6\tFinnGen R7",
                                       "protein\tsource", "CRP\tGCST90012345", "## sheet Notes",
                                       "head\tx"]


def test_a_small_workbook_of_more_than_20_sheets_is_cut(matcher):
    text = "\n".join(f"## sheet S{i}\nh{i}\tv\nrow\t1" for i in range(21))
    out = cs.cut(entry(text, sheets=21), matcher)
    assert out["cut"] and "row\t1" not in out["text"]
    assert out["text"].count("## sheet") == 21 and "h20\tv" in out["text"]


def test_a_csv_keeps_its_first_line_as_the_header(matcher):
    text = "snp,trait,source\n" + "\n".join(f"rs{i % 89},x,y" for i in range(25000)) + "\nrs1,t,FinnGen R5"
    out = cs.cut(entry(text, "CSV", 0), matcher)
    assert out["text"].split("\n") == ["snp,trait,source", "rs1,t,FinnGen R5"]


def test_a_text_supplement_keeps_table_names_and_matching_lines(matcher):
    text = ("Supplementary Table 3. Cohorts\n" + "plain words line\n" * 20000
            + "We used FinnGen R10 for outcomes.\n")
    out = cs.cut(entry(text, "PDF", 0), matcher)
    assert out["text"].split("\n") == ["Supplementary Table 3. Cohorts",
                                       "We used FinnGen R10 for outcomes."]


def test_an_entry_without_text_is_refused(matcher):
    with pytest.raises(cs.CutError):
        cs.cut({"name": "x", "type": "PDF", "text": None}, matcher)
