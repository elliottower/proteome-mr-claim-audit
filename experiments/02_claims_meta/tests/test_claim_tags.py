import json

import pytest

from claim_tags import load_lexicon, read_extractions, tags_from_extraction


@pytest.fixture(scope="module")
def kw():
    return load_lexicon()


@pytest.mark.parametrize("span, expected", [
    ("Genetically predicted IL6R had a causal effect on CAD, a therapeutic target.", "target"),
    ("PCSK9 was causally associated with stroke.", "causal"),
    ("Higher FGF21 causes lower BMI.", "causal"),
    ("We estimated the effect of APOB on coronary disease.", "causal"),
    ("Higher IL6R was associated with lower CAD risk.", "association"),
    ("Because CRP was higher, risk was higher.", "association"),
    ("The effects of APOB on coronary disease were positive.", "association"),
    ("MMP12 is DRUGGABLE.", "target"),
    ("Suggesting repurposing opportunities for tocilizumab.", "target"),
    ("An untargeted screen linked ABO to thrombosis.", "association"),
])
def test_wording_class_first_match_wins_at_word_starts(kw, span, expected):
    assert kw.wording_class(span)[0] == expected


@pytest.mark.parametrize("span, expected", [
    ("We identify a novel association of ABO with stroke.", True),
    ("Newly identified proteins include FURIN.", True),
    ("The novelty of this design is its scale.", False),
    ("A new protein, FURIN, was linked to CAD.", False),
    ("shown for the  first time for IL6R", True),
    ("an association not previously reported", True),
    ("the first evidence that F11 raises stroke risk", True),
    ("PREVIOUSLY UNREPORTED effects of F11", True),
    ("previously reported effects of F11", False),
])
def test_novelty_language_whole_words_and_phrases(kw, span, expected):
    assert bool(kw.novelty_terms(span)) is expected


def test_tags_follow_the_verifier_record_ids_and_skip_failed_rows(kw):
    claim = {"evidence_span": "IL6R is a novel causal protein.", "platform": ["Olink", "SomaScan"],
             "ancestry": "European", "protein_as_written": "IL6R", "outcome_as_written": "CAD"}
    plain = {"evidence_span": "ABO was associated with stroke.", "platform": ["not_stated"],
             "ancestry": "not_stated", "protein_as_written": "ABO",
             "outcome_as_written": "stroke"}
    rows = [{"pmid": "11", "status": "ok", "output": {"claims": [claim, plain]}},
            {"pmid": "12", "status": "extraction_failed", "output": None},
            {"pmid": "13", "status": "ok", "output": {"claims": [plain]}}]
    tags = tags_from_extraction(rows, kw)
    assert [t.claim_record_id for t in tags] == ["11:000", "11:001", "13:000"]
    assert (tags[0].wording_class, tags[0].novelty_language, tags[0].platform) == (
        "causal", True, ("Olink", "SomaScan"))
    assert (tags[1].wording_class, tags[1].novelty_language, tags[1].platform) == (
        "association", False, ("not_stated",))


def test_tags_ignore_keywords_inside_the_outcome_name(kw):
    def row(span, outcome, protein="IL6R"):
        return {"evidence_span": span, "platform": ["not_stated"], "ancestry": "not_stated",
                "protein_as_written": protein, "outcome_as_written": outcome}

    rows = [{"pmid": "21", "status": "ok", "output": {"claims": [
        row("IL6R was associated with treatment-resistant depression.",
            "treatment-resistant depression"),
        row("IL6R is a drug target for treatment-resistant depression.",
            "treatment-resistant depression"),
        row("IL6R was associated with treatment-resistant depression.", "depression"),
        row("IL6R had a causal effect on drug-induced liver injury.",
            "drug-induced liver injury")]}}]
    assert [t.wording_class for t in tags_from_extraction(rows, kw)] == [
        "association", "target", "target", "causal"]


def test_tags_ignore_novelty_terms_inside_the_outcome_name(kw):
    def row(span, outcome):
        return {"evidence_span": span, "platform": ["not_stated"], "ancestry": "not_stated",
                "protein_as_written": "IL6R", "outcome_as_written": outcome}

    rows = [{"pmid": "31", "status": "ok", "output": {"claims": [
        row("IL6R was associated with novel coronavirus infection.",
            "novel coronavirus infection"),
        row("A novel association of IL6R with novel coronavirus infection.",
            "novel coronavirus infection"),
        row("IL6R was associated with novel coronavirus infection.", "coronavirus infection")]}}]
    assert [t.novelty_language for t in tags_from_extraction(rows, kw)] == [False, True, True]


def test_several_extraction_files_are_read_as_one_and_a_repeated_record_raises(tmp_path):
    a, b = tmp_path / "search.jsonl", tmp_path / "round1.jsonl"
    a.write_text(json.dumps({"pmid": "1", "status": "ok"}) + "\n")
    b.write_text(json.dumps({"pmid": "W2", "status": "ok"}) + "\n")
    assert [r["pmid"] for r in read_extractions([a, b])] == ["1", "W2"]
    with pytest.raises(ValueError, match="occurs twice"):
        read_extractions([a, b, a])
