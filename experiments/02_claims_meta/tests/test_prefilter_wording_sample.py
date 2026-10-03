import collections
import json
import math
import pathlib
import random
import re

import pytest

import keyword_prefilter as kp
import sample_repeat_run as srr
import tag_wording as tw

EXP = pathlib.Path(kp.__file__).resolve().parent.parent
PREREG = (EXP / "PREREG.md").read_text()
TERMS = kp.load_terms()
LEXICON = tw.Lexicon(json.loads(tw.LEXICON.read_text()))


def marked(title: str, abstract: str = "") -> tuple[bool, bool, bool]:
    m = kp.mark("x", title, abstract, TERMS)
    return m.has_genetic_term, m.has_protein_term, m.marked


def test_committed_terms_are_the_text_terms_of_the_registered_blocks():
    committed = json.loads(kp.TERMS.read_text())["terms"]
    assert committed == kp.derive_terms()
    assert "Mendelian Randomization Analysis" not in committed["genetic"]
    assert ["plasma", "protein*"] in committed["protein"]
    assert "SMR" in committed["genetic"] and "proteom*" in committed["protein"]
    assert not set(committed["genetic"]) & {"SomaScan", "druggable"}


def test_record_is_marked_unless_it_has_a_genetic_and_a_protein_term():
    assert marked("Mendelian randomization of plasma proteins") == (True, True, False)
    assert marked("Mendelian randomization of body mass index") == (True, False, True)
    assert marked("A proteomic study of sepsis") == (False, True, True)
    assert marked("A cohort study of dietary fibre") == (False, False, True)
    assert marked("Dietary fibre", "We used pQTLs as instruments.") == (True, True, False)


def test_term_matching_follows_word_boundaries_truncation_and_hyphens():
    assert marked("consmr of proteomes")[0] is False
    assert marked("SMR.")[0] is True and marked("smr")[0] is True
    assert marked("Co-localization analysis")[0] is True
    assert marked("colocalisation")[0] is True
    assert marked("Proteome-wide scan")[1] is True and marked("proteome wide scan")[1] is True
    assert marked("the proteins of plasma")[1] is True
    assert marked("plasma and proteinuria")[1] is True
    assert marked("serum proteinuria")[1] is True
    assert marked("the protein of serum")[1] is False
    assert marked("pQTLs")[0] is True and marked("pQTLx")[0] is False
    assert marked("cis MR analysis")[0] is True
    assert marked("genetically\npredicted   levels")[0] is True


def test_queue_holds_every_record_with_unmarked_records_first():
    dev = [json.loads(l) for l in (EXP / "prompts" / "dev_abstracts.jsonl").read_text()
           .splitlines()]
    ordered, marks = kp.queue(dev, TERMS)
    assert sorted(r["pmid"] for r in ordered) == sorted(r["pmid"] for r in dev)
    flags = [m.marked for m in marks]
    assert flags == sorted(flags) and [m.record_id for m in marks] == [
        r["pmid"] for r in ordered]
    for value in (False, True):
        ids = [m.record_id for m in marks if m.marked is value]
        assert ids == sorted(ids)
    by_id = {m.record_id: m for m in marks}
    for r in dev:
        text = f"{r['title']} {r['abstract']}".lower()
        if "mendelian randomi" in text and "plasma protein" in text:
            assert by_id[r["pmid"]].marked is False


def test_wording_lexicon_is_the_registered_lists():
    raw = json.loads(tw.LEXICON.read_text())
    m = re.search(r"\*\*Wording class\.\*\*.*?`target` \(([^)]*)\),\s+then `causal` "
                  r"\(([^)]*)\), otherwise `(\w+)`", PREREG, re.S)
    assert raw["wording_class"]["order"] == ["target", "causal"]
    assert raw["wording_class"]["keywords"]["target"] == m.group(1).replace("\n", " ").split(", ")
    assert raw["wording_class"]["keywords"]["causal"] == m.group(2).replace("\n", " ").split(", ")
    assert raw["wording_class"]["default"] == m.group(3)
    n = re.search(r"\*\*Novelty and prior claims\.\*\*.*?as whole words or phrases, (.*?)\. "
                  r"The name rule of the wording class\s+applies", PREREG, re.S).group(1)
    terms = [t.strip().strip('"') for t in re.split(r",| or ", " ".join(n.split())) if t.strip()]
    assert raw["novelty_language"] == terms


@pytest.mark.parametrize("span, expected", [
    ("IL6R had a causal effect on CAD, making it a drug target.", "target"),
    ("Genetically predicted IL6R was causally associated with CAD.", "causal"),
    ("Higher IL6R causes CAD.", "causal"),
    ("We estimated the effect of IL6R on CAD.", "causal"),
    ("IL6R was associated with CAD because of inflammation.", "association"),
    ("IL6R was associated with CAD.", "association"),
    ("IL6R may be REPURPOSED for CAD.", "target"),
    ("IL6R is a Druggable protein.", "target"),
    ("An untargeted analysis associated IL6R with CAD.", "association"),
    ("IL6R is a candidate for Therapeutic\nintervention.", "target"),
])
def test_wording_class_first_match_wins(span, expected):
    assert LEXICON.wording_class(span)[0] == expected


@pytest.mark.parametrize("span, terms", [
    ("We identify a novel association of IL6R with CAD.", ["novel"]),
    ("The novelty of IL6R is unclear.", []),
    ("A new association of IL6R with CAD.", []),
    ("IL6R was Newly linked to CAD, for the\nfirst time.", ["newly", "for the first time"]),
    ("IL6R, not previously reported, lowers CAD risk.", ["not previously"]),
    ("A previously unreported effect; the first evidence in humans.",
     ["previously unreported", "first evidence"]),
    ("A renewly named protein.", []),
])
def test_novelty_language_matches_whole_words_and_phrases(span, terms):
    assert LEXICON.novelty_terms(span) == terms
    assert tw.tag("1:000", span, LEXICON, "IL6R", "CAD").novelty_language is bool(terms)


MASKING_CASES = [
    # (span, protein, outcome, class, class without the name rule, keywords inside a name)
    ("IL6R was associated with treatment-resistant depression.", "IL6R",
     "treatment-resistant depression", "association", "target", ["outcome:treatment"]),
    ("IL6R was associated with Treatment Resistant\nDepression.", "IL6R",
     "treatment-resistant depression", "association", "target", ["outcome:treatment"]),
    ("IL6R had a causal effect on drug-induced liver injury.", "IL6R",
     "drug-induced liver injury", "causal", "target", ["outcome:drug"]),
    ("IL6R is a drug target for drug-induced liver injury.", "IL6R",
     "drug-induced liver injury", "target", "target", ["outcome:drug"]),
    ("Treatment of drug-induced liver injury may target IL6R.", "IL6R",
     "drug-induced liver injury", "target", "target", ["outcome:drug"]),
    ("Mechanistic target of rapamycin was associated with CAD.",
     "mechanistic target of rapamycin", "CAD", "association", "target", ["protein:target"]),
    ("IL6R was associated with treatment-resistant depression.", "IL6R", "depression",
     "target", "target", []),
    ("IL6R was associated with the effect of statins.", "IL6R", "effect of statins",
     "association", "causal", ["outcome:effect of"]),
    ("IL6R was associated with therapeutic response; a therapeutic option.", "IL6R",
     "therapeutic response", "target", "target", ["outcome:therapeutic"]),
    ("IL6R was associated with CAD.", "IL6R", "CAD", "association", "association", []),
]


@pytest.mark.parametrize("span, protein, outcome, expected, unmasked, inside", MASKING_CASES)
def test_wording_keywords_inside_a_protein_or_outcome_name_do_not_count(
        span, protein, outcome, expected, unmasked, inside):
    w = tw.tag("1:000", span, LEXICON, protein, outcome)
    assert (w.wording_class, w.wording_class_unmasked) == (expected, unmasked)
    assert sorted(f"{m.inside}:{m.keyword}" for m in w.keyword_matches if m.inside) == inside
    assert LEXICON.wording_class(span, (protein, outcome))[0] == expected
    assert LEXICON.wording_class(span)[0] == unmasked


def test_keyword_matches_keep_every_occurrence_with_its_position():
    span = "A drug target; drug-induced liver injury; the drug."
    w = tw.tag("1:000", span, LEXICON, "IL6R", "drug-induced liver injury")
    drug = [(m.start, m.inside) for m in w.keyword_matches if m.keyword == "drug"]
    assert drug == [(2, None), (15, "outcome"), (46, None)]
    assert span[15:19] == "drug" and w.wording_keyword == "target"


def test_wording_summary_counts_the_classes_the_name_rule_changes():
    rows = [{"pmid": "5", "status": "ok", "output": {"claims": [
        {"evidence_span": "IL6R was associated with treatment-resistant depression.",
         "protein_as_written": "IL6R", "outcome_as_written": "treatment-resistant depression"},
        {"evidence_span": "IL6R is a drug target for CAD.", "protein_as_written": "IL6R",
         "outcome_as_written": "CAD"}]}},
            {"pmid": "6", "status": "extraction_failed", "output": None}]
    tagged = tw.tag_rows(rows, LEXICON)
    assert [t.claim_record_id for t in tagged] == ["5:000", "5:001"]
    summary = tw.summarize(tagged)
    assert summary["wording_class"] == {"association": 1, "target": 1}
    assert summary["wording_class_unmasked"] == {"target": 2}
    assert summary["class_changed_by_name_masking"] == {"target -> association": 1}
    assert summary["keyword_matches_inside_a_name"] == {"outcome:treatment": 1}


NOVELTY_MASKING_CASES = [
    # (span, protein, outcome, flag, flag without the name rule, terms, terms inside a name)
    ("IL6R was associated with novel coronavirus infection.", "IL6R",
     "novel coronavirus infection", False, True, [], ["outcome:novel"]),
    ("A novel association of IL6R with novel coronavirus infection.", "IL6R",
     "novel coronavirus infection", True, True, ["novel"], ["outcome:novel"]),
    ("IL6R was associated with Novel-Coronavirus\nInfection.", "IL6R",
     "novel coronavirus infection", False, True, [], ["outcome:novel"]),
    ("IL6R was associated with novel coronavirus infection.", "IL6R", "coronavirus infection",
     True, True, ["novel"], []),
    ("IL6R was newly linked to novel coronavirus infection.", "IL6R",
     "novel coronavirus infection", True, True, ["newly"], ["outcome:novel"]),
    ("Novel protein kinase C delta was associated with CAD.", "novel protein kinase C delta",
     "CAD", False, True, [], ["protein:novel"]),
    ("Novel protein kinase C delta was associated with CAD for the first time.",
     "novel protein kinase C delta", "CAD", True, True, ["for the first time"],
     ["protein:novel"]),
    ("IL6R was associated with CAD.", "IL6R", "CAD", False, False, [], []),
]


@pytest.mark.parametrize("span, protein, outcome, flag, unmasked, terms, inside",
                         NOVELTY_MASKING_CASES)
def test_novelty_terms_inside_a_protein_or_outcome_name_do_not_count(
        span, protein, outcome, flag, unmasked, terms, inside):
    w = tw.tag("1:000", span, LEXICON, protein, outcome)
    assert (w.novelty_language, w.novelty_language_unmasked) == (flag, unmasked)
    assert w.novelty_terms == terms
    assert sorted(f"{m.inside}:{m.term}" for m in w.novelty_matches if m.inside) == inside
    assert LEXICON.novelty_terms(span, (protein, outcome)) == terms
    assert bool(LEXICON.novelty_terms(span)) is unmasked


def test_novelty_matches_keep_every_occurrence_with_its_position():
    span = "A novel association with novel coronavirus infection."
    w = tw.tag("1:000", span, LEXICON, "IL6R", "novel coronavirus infection")
    assert [(m.term, m.start, m.end, m.inside) for m in w.novelty_matches] == [
        ("novel", 2, 7, None), ("novel", 25, 30, "outcome")]
    assert span[25:30] == "novel" and w.novelty_language is True


def test_wording_summary_counts_the_novelty_flags_the_name_rule_removes():
    def claim(span, outcome):
        return {"evidence_span": span, "protein_as_written": "IL6R",
                "outcome_as_written": outcome}

    rows = [{"pmid": "7", "status": "ok", "output": {"claims": [
        claim("IL6R was associated with novel coronavirus infection.",
              "novel coronavirus infection"),
        claim("A novel association of IL6R with novel coronavirus infection.",
              "novel coronavirus infection"),
        claim("IL6R was newly associated with CAD.", "CAD"),
        claim("IL6R was associated with CAD.", "CAD")]}}]
    summary = tw.summarize(tw.tag_rows(rows, LEXICON))
    assert summary["novelty_language"] == 2
    assert summary["novelty_language_unmasked"] == 3
    assert summary["novelty_language_removed_by_name_masking"] == 1
    assert summary["novelty_matches_inside_a_name"] == {"outcome:novel": 2}
    assert summary["novelty_terms"] == {"novel": 1, "newly": 1}


def test_repeat_sample_is_a_tenth_rounded_up_and_ignores_input_order():
    ids = [str(i) for i in range(1, 1238)]
    sample = srr.draw(ids)
    assert len(sample) == math.ceil(0.10 * 1237) == 124
    assert set(sample) <= set(ids) and len(set(sample)) == len(sample)
    shuffled = ids[:]
    random.Random().shuffle(shuffled)
    assert srr.draw(shuffled) == sample
    assert srr.draw(ids) == sample
    assert srr.draw(ids, seed=srr.SEED + 1) != sample
    assert len(srr.draw(["a"])) == 1 and srr.draw([]) == []
    with pytest.raises(srr.SampleError):
        srr.draw(["a", "a"])


def test_repeat_sample_draws_each_record_with_equal_probability():
    ids = [f"R{i:02d}" for i in range(50)]
    hits = collections.Counter(i for seed in range(4000) for i in srr.draw(ids, seed=seed))
    assert sum(hits.values()) == 4000 * 5
    for i in ids:
        assert hits[i] / 4000 == pytest.approx(0.10, abs=0.025)


def test_repeat_sample_uses_the_registered_seed_and_fraction():
    stated = re.search(r"random 10% of eligible abstracts \(seed `(\d+)`\)", PREREG)
    assert (srr.SEED, srr.FRACTION) == (int(stated.group(1)), 0.10)


def test_repeat_sample_script_takes_only_eligible_records(tmp_path, monkeypatch):
    decisions = [{"pmid": str(i), "decision": d} for i, d in enumerate(
        ["eligible"] * 12 + ["eligible_count_not_stated"] * 5 + ["uncertain"] * 4
        + ["ineligible"] * 30 + ["extraction_failed"] * 3)]
    (tmp_path / "x.decisions.jsonl").write_text("".join(json.dumps(d) + "\n" for d in decisions))
    (tmp_path / "abstracts.jsonl").write_text("".join(json.dumps(
        {"pmid": d["pmid"], "title": "t", "abstract": f"abstract {d['pmid']}"}) + "\n"
        for d in decisions))
    monkeypatch.setattr("sys.argv", ["sample_repeat_run.py", "--decisions",
                                     str(tmp_path / "x.decisions.jsonl"), "--abstracts",
                                     str(tmp_path / "abstracts.jsonl")])
    srr.main()
    meta = json.loads((tmp_path / "x.decisions.repeat_sample.json").read_text())
    rows = [json.loads(l) for l in (tmp_path / "x.decisions.repeat_sample.jsonl").read_text()
            .splitlines()]
    assert (meta["seed"], meta["n_eligible"], meta["n_sampled"]) == (20261001, 21, 3)
    assert [r["pmid"] for r in rows] == meta["sampled_ids"]
    assert all(int(r["pmid"]) < 21 and r["abstract"] == f"abstract {r['pmid']}" for r in rows)
    with pytest.raises(srr.SampleError):
        srr.main()
