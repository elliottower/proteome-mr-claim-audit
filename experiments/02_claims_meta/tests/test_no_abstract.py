import datetime
import json
import pathlib
import re

import pytest

import abstract_floor as af
import assemble_screening_set as ass
import fetch_known_item_abstracts as fk
import funnel as fn
import gate_audit as ga
import keyword_prefilter as kp
import negative_control_specificity as ncs
import run_extraction
import select_eligible as se
from assemble_registry import AssemblyError, assemble
from build_registry import PublicDate
from link_families import SearchRecord

PREREG = (pathlib.Path(__file__).resolve().parent.parent / "PREREG.md").read_text()
LONG = "Plasma proteins were instrumented and tested against stroke. " * 4      # 244 characters
STUB = "n/a"


def retrieved(source, source_id, abstract="", pmid=None, doi=None, kind="journal"):
    return ass.RetrievedRecord(
        source=source, source_id=source_id, pmid=pmid, pmcid=None, doi=doi, kind=kind,
        source_type="", title=f"title from {source}", abstract=abstract,
        first_author_surname="A",
        first_public=PublicDate(value=datetime.date(2021, 1, 1), resolution="day"))


def test_floor_counts_characters_after_collapsing_whitespace():
    assert af.ABSTRACT_FLOOR == 200
    assert af.abstract_length("  a \n\n b\t") == 3 and af.abstract_length(None) == 0
    assert af.is_no_abstract("x" * 199) and not af.is_no_abstract("x" * 200)
    # 150 letters separated by runs of spaces are 299 characters once the runs are collapsed,
    # and 100 letters are 199: padding never lifts a text over the floor.
    assert not af.is_no_abstract("     ".join("x" * 150))
    assert af.is_no_abstract("          ".join("x" * 100))
    assert af.is_no_abstract("") and af.is_no_abstract(None) and af.is_no_abstract(STUB)


def test_floor_in_the_preregistration_is_the_one_in_the_code():
    text = " ".join(PREREG.split())
    m = re.search(r"no abstract of at least (\d+) characters", text)
    assert int(m.group(1)) == af.ABSTRACT_FLOOR
    assert "is `no_abstract`" in text


def test_abstract_is_the_first_one_that_reaches_the_floor_in_source_order():
    stub_first, = ass.deduplicate([retrieved("pubmed", "5", STUB, pmid="5"),
                                   retrieved("epmc", "5", LONG, pmid="5"),
                                   retrieved("openalex", "W5", LONG + " more", pmid="5")])
    assert (stub_first.abstract, stub_first.abstract_source, stub_first.no_abstract) == (
        LONG, "epmc", False)
    stub_only, = ass.deduplicate([retrieved("pubmed", "6", "", pmid="6"),
                                  retrieved("openalex", "W6", STUB, pmid="6")])
    assert (stub_only.abstract, stub_only.abstract_source, stub_only.no_abstract) == (
        STUB, "openalex", True)
    assert json.loads(stub_only.model_dump_json())["no_abstract"] is True


def test_no_abstract_record_is_listed_apart_and_left_out_of_the_screening_set(tmp_path):
    screening = ass.deduplicate([
        retrieved("pubmed", "1", LONG, pmid="1"),
        retrieved("openalex", "W2", STUB, doi="10.1/b", kind="other"),
        retrieved("epmc", "PPR3", "", doi="10.1/c", kind="preprint"),
        retrieved("openalex", "W4", "  \n ", doi="10.1/d")])
    ass.write_screening_files(tmp_path, screening)

    def rows(name):
        return [json.loads(l) for l in (tmp_path / name).read_text().splitlines()]

    assert [r["pmid"] for r in rows("screening_set.jsonl")] == ["1"]
    assert [(r["pmid"], r["kind"], r["abstract_length"]) for r in rows("no_abstract.jsonl")] == [
        ("PPR3", "preprint", 0), ("W2", "other", 3), ("W4", "journal", 0)]
    assert {r["record_id"]: r["no_abstract"] for r in rows("screening_records.jsonl")} == {
        "1": False, "PPR3": True, "W2": True, "W4": True}
    assert {r["record_id"]: r["no_abstract"] for r in rows("search_records.jsonl")} == {
        "1": False, "PPR3": True, "W2": True, "W4": True}
    # Two records hold no text (one of them only whitespace) and one holds a stub.
    assert ass.no_abstract_counts(screening) == {
        "records": 3, "empty": 2, "stub_below_floor": 1,
        "by_document_class": {"journal": 1, "other": 1, "preprint": 1},
        "floor_characters": 200}
    counts = ass.funnel([], screening)
    assert counts["no_abstract"]["records"] == 3
    assert counts["screening_records_with_an_abstract"] == 1


def test_prefilter_refuses_a_screening_set_holding_a_record_below_the_floor(tmp_path,
                                                                           monkeypatch):
    path = tmp_path / "screening_set.jsonl"
    path.write_text(json.dumps({"pmid": "1", "title": "t", "abstract": LONG}) + "\n"
                    + json.dumps({"pmid": "2", "title": "t", "abstract": "x" * 199}) + "\n")
    monkeypatch.setattr("sys.argv", ["keyword_prefilter.py", "--gate", "--screening-set",
                                     str(path)])
    with pytest.raises(af.NoAbstractError, match="keyword prefilter.*'2'"):
        kp.main()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["screening_set.jsonl"]


def test_gate_audit_refuses_a_marked_record_below_the_floor(tmp_path, monkeypatch):
    (tmp_path / "gated_out.jsonl").write_text(
        json.dumps({"pmid": "1", "title": "t", "abstract": LONG}) + "\n"
        + json.dumps({"pmid": "2", "title": "t", "abstract": STUB}) + "\n")
    decisions = tmp_path / "gate.decisions.jsonl"
    decisions.write_text("".join(json.dumps({"pmid": i, "decision": "ineligible"}) + "\n"
                                 for i in ("1", "2")))
    monkeypatch.setattr("sys.argv", ["gate_audit.py", "--round-dir", str(tmp_path),
                                     "--decisions", str(decisions)])
    with pytest.raises(af.NoAbstractError, match="gate audit.*'2'"):
        ga.main()
    assert not list(tmp_path.glob("gate_audit_after_batch_*.json"))


@pytest.mark.parametrize("task", ["eligibility", "extraction"])
def test_no_record_below_the_floor_is_sent_to_the_model(tmp_path, monkeypatch, task):
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / f"{task}_prompt.md").write_text("Decide.")
    (prompts / "schema.json").write_text(json.dumps({task: {"type": "object"}}))
    abstracts = tmp_path / "abstracts.jsonl"
    abstracts.write_text(json.dumps({"pmid": "1", "title": "t", "abstract": LONG}) + "\n"
                         + json.dumps({"pmid": "2", "title": "A long title", "abstract": STUB})
                         + "\n")
    requests = []
    monkeypatch.setattr(run_extraction, "PROMPTS", prompts)
    monkeypatch.setattr(run_extraction, "PARSED", tmp_path / "parsed")
    monkeypatch.setattr(run_extraction, "run_one", lambda *args: requests.append(args))
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-key")
    monkeypatch.setattr("sys.argv", [
        "run_extraction.py", "--task", task, "--label", "search", "--abstracts", str(abstracts),
        "--raw-root", str(tmp_path / "raw")])
    with pytest.raises(af.NoAbstractError, match="'2'"):
        run_extraction.main()
    assert requests == [] and not (tmp_path / "raw").exists()


def test_decision_on_a_no_abstract_record_is_refused_by_the_selection():
    decisions = [{"pmid": "1", "decision": "eligible"}, {"pmid": "2", "decision": "ineligible"}]
    abstracts = [{"pmid": "1", "title": "t", "abstract": LONG}]
    records = [{"record_id": "1", "no_abstract": False}, {"record_id": "2", "no_abstract": True}]
    with pytest.raises(se.SelectError, match="no_abstract.*'2'"):
        se.select(decisions, abstracts, records)
    kept, seeds = se.select(decisions[:1], abstracts, records)
    assert [r["pmid"] for r in kept] == ["1"] and [r["record_id"] for r in seeds] == ["1"]


def day(text):
    return PublicDate(value=datetime.date.fromisoformat(text), resolution="day")


def search_record(rid, kind, date, doi, pub=None, no_abstract=False, title="Proteome MR of x"):
    return SearchRecord(record_id=rid, kind=kind, doi=doi, pmid=None, pmcid=None,
                        published_as_doi=pub, title=title, first_author_surname="Alpha",
                        first_public=day(date), no_abstract=no_abstract)


def check(rid, protein):
    return {"pmid": rid, "claim_index": 0, "claim_record_id": f"{rid}:000",
            "direction": "raises", "claim_scope": "overall",
            "analysis_context_as_written": "not_stated", "subgroup_as_written": "not_stated",
            "relation_ambiguous": False, "dataset_attribution": "whole_study",
            "pqtl_datasets": ["Sun 2018"], "outcome_datasets": ["FinnGen R10"],
            "protein_ids": [protein], "outcome_ids": ["MONDO:1"],
            "direction_verification_state": "agrees", "span_passes": True,
            "evidence_type": "mr_estimate", "protein_check": "pass", "outcome_check": "pass",
            "enters_registry": True, "first_failure": None}


HGNC = {"HGNC:1": frozenset({"P1"})}
ELIGIBLE = {"decision": "eligible", "flags": []}


def test_no_abstract_journal_record_adds_nothing_to_the_family_of_its_preprint():
    # Preprint P1 (abstract, eligible) is published as journal record J1, which no source gives
    # an abstract. J2 stands alone without an abstract. J3 is an ordinary eligible record.
    def records(flag):
        return [search_record("J1", "journal", "2022-05-05", "10.1/j1", no_abstract=flag),
                search_record("P1", "preprint", "2021-03-01", "10.9/p1", pub="10.1/j1"),
                search_record("J2", "journal", "2023-01-01", "10.1/j2", no_abstract=flag,
                              title="Another paper"),
                search_record("J3", "journal", "2024-01-01", "10.1/j3", title="Third paper")]

    decisions = {"P1": ELIGIBLE, "J3": ELIGIBLE}
    status = {"P1": "ok", "J3": "ok"}
    checks = [check("P1", "HGNC:1"), check("J3", "HGNC:1")]
    a = assemble(records(True), decisions, status, checks, HGNC, {})
    assert a.family_of["P1"] == "J1" and set(a.meta) == {"J1", "J3"}
    family = a.meta["J1"]
    assert (family.registry_records, family.dating_records) == (["P1"], [])
    assert family.first_public == day("2021-03-01") and family.window == "confirmatory"
    assert {(c.family_id, c.protein_id) for c in a.claims["confirmatory"]} == {
        ("J1", "P1"), ("J3", "P1")}
    assert a.report["records_no_abstract"] == 2
    assert a.report["eligible_families_with_a_no_abstract_record"] == 1
    # Without the rule the journal record, which has no decision, would unmake the family.
    without_rule = assemble(records(False), decisions, status, checks, HGNC, {})
    assert set(without_rule.meta) == {"J3"}


def test_no_abstract_record_with_a_decision_is_refused_by_the_assembly():
    records = [search_record("J1", "journal", "2022-05-05", "10.1/j1", no_abstract=True)]
    with pytest.raises(AssemblyError, match="no_abstract.*J1"):
        assemble(records, {"J1": ELIGIBLE}, {"J1": "ok"}, [], HGNC, {})
    assert assemble(records, {}, {}, [], HGNC, {}).meta == {}


def funnel_record(rid, title="t", abstract=LONG, kind="journal", no_abstract=False):
    return {"record_id": rid, "kind": kind, "title": title, "abstract": abstract,
            "no_abstract": no_abstract}


def funnel_mark(rid, marked=False):
    return {"record_id": rid, "has_genetic_term": not marked, "has_protein_term": True,
            "marked": marked}


def funnel_inputs():
    # Search: A screened; N1 (empty, title names both term groups), N2 (stub, a title with
    # neither) and N4 (empty, a title with neither) are no_abstract. Chase round 1: E unmarked and screened, F marked and sampled,
    # N3 no_abstract (empty, a preprint).
    runs = [
        fn.ScreeningRun(
            name="search", chase_round=None, counts={}, gated=False,
            records=[funnel_record("A"),
                     funnel_record("N1", "Proteome-wide Mendelian randomization of plasma "
                                         "proteins", "", no_abstract=True),
                     funnel_record("N2", "Editorial", STUB, "other", no_abstract=True),
                     funnel_record("N4", "Erratum", "", no_abstract=True)],
            marks=[funnel_mark("A")]),
        fn.ScreeningRun(
            name="chase_round_1", chase_round=1, counts={"round": 1}, gated=True,
            records=[funnel_record("E"), funnel_record("F"),
                     funnel_record("N3", "A plasma proteomics atlas", "", "preprint", no_abstract=True)],
            marks=[funnel_mark("E"), funnel_mark("F", marked=True)], gate_sampled=["F"])]
    decisions = [{"pmid": i, "decision": "ineligible", "reasons": [], "flags": []}
                 for i in ("A", "E", "F")]
    return runs, decisions


def run_funnel(runs, decisions):
    return fn.funnel(runs, decisions, [], [], [], [], {}, {})


def test_funnel_counts_no_abstract_records_apart_at_every_stage():
    out = run_funnel(*funnel_inputs())
    assert out["screening"]["records"] == 7
    assert (out["screening"]["no_abstract"], out["screening"]["with_an_abstract"]) == (4, 3)
    assert out["no_abstract"]["floor_characters"] == 200
    assert out["no_abstract"]["search"] == {
        "records": 3, "empty": 2, "stub_below_floor": 1,
        "by_document_class": {"journal": 2, "other": 1},
        "title_holds_both_term_groups": 1, "title_holds_both_term_groups_record_ids": ["N1"]}
    # "A plasma proteomics atlas" names a protein term and no genetic term ("pQTL" would name
    # both: it is in the GEN block and in the PROT block).
    assert out["no_abstract"]["chase_round_1"]["title_holds_both_term_groups"] == 0
    assert out["prefilter"]["search"]["records"] == 1
    assert out["prefilter"]["search"]["no_abstract_records_not_screened"] == 3
    assert out["prefilter"]["search"]["sent_to_screening"] == 1
    assert out["eligibility"]["records_sent_to_screening"] == 3
    audit = out["prefiltered_citation_chasing_gate_audit"]["chase_round_1"]
    assert (audit["marked_records"], audit["sampled"], audit["judged"],
            audit["no_abstract_records_of_the_round"]) == (1, 1, 1, 1)


@pytest.mark.parametrize("stage, change", [
    ("no abstract, search", lambda runs, d: d.append(
        {"pmid": "N1", "decision": "uncertain", "reasons": [], "flags": []})),
    ("prefilter marks of search", lambda runs, d: runs[0].marks.append(funnel_mark("N1"))),
    ("gate sample of chase_round_1", lambda runs, d: setattr(
        runs[1], "gate_sampled", ["F", "N3"])),
])
def test_funnel_raises_when_a_no_abstract_record_reaches_a_later_stage(stage, change):
    runs, decisions = funnel_inputs()
    change(runs, decisions)
    with pytest.raises(fn.FunnelError, match=stage):
        run_funnel(runs, decisions)


def test_no_abstract_control_record_is_not_judged_and_leaves_the_denominator():
    controls = [{"pmid": f"c{i}", "stratum": "review"} for i in range(5)]
    decisions = [{"pmid": f"c{i}", "decision": "ineligible", "reasons": [], "flags": []}
                 for i in range(1, 5)]
    decisions[0]["decision"] = "eligible"
    out = ncs.specificity(controls, decisions, frozenset({"c0"}))
    row = out["per_stratum"]["review"]
    assert (row["records"], row["no_abstract"], row["judged"], row["not_eligible"]) == (
        5, 1, 4, 3)
    assert row["specificity"] == pytest.approx(0.75)
    with pytest.raises(ncs.ControlError):                   # c0 has no decision without the set
        ncs.specificity(controls, decisions)
    with pytest.raises(ncs.ControlError):                   # a judged record cannot be listed
        ncs.specificity(controls, decisions + [
            {"pmid": "c0", "decision": "ineligible", "reasons": [], "flags": []}],
            frozenset({"c0"}))
    with pytest.raises(ncs.ControlError):
        ncs.specificity(controls, decisions, frozenset({"c0", "other"}))


def test_control_fetch_lists_no_abstract_records_apart(tmp_path, monkeypatch):
    def article(pmid, abstract):
        body = f"<Abstract><AbstractText>{abstract}</AbstractText></Abstract>" if abstract else ""
        return (f"<PubmedArticle><MedlineCitation><PMID>{pmid}</PMID><Article>"
                f"<ArticleTitle>Title {pmid}</ArticleTitle>{body}</Article></MedlineCitation>"
                f"</PubmedArticle>")

    xml = ("<PubmedArticleSet>" + article("1", LONG) + article("2", "") + article("3", STUB)
           + "</PubmedArticleSet>")

    class Response:
        text = xml

        def raise_for_status(self):
            return None

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, url, params):
            assert params["id"] == "1,2,3" and "email" not in params
            return Response()

    controls = tmp_path / "negative_controls.jsonl"
    controls.write_text("".join(json.dumps({"pmid": p, "stratum": "review"}) + "\n"
                                for p in ("1", "2", "3")))
    monkeypatch.setattr(fk, "CONTROLS", controls)
    monkeypatch.setattr(fk, "CONTROLS_OUT", tmp_path / "out" / "abstracts.jsonl")
    monkeypatch.setattr(fk, "CONTROLS_NO_ABSTRACT", tmp_path / "out" / "no_abstract.jsonl")
    monkeypatch.setattr(fk, "check_frozen", lambda: None)
    monkeypatch.setattr(fk.httpx, "Client", Client)
    monkeypatch.setattr("sys.argv", ["fetch_known_item_abstracts.py", "--controls"])
    fk.main()
    kept = [json.loads(l) for l in (tmp_path / "out" / "abstracts.jsonl").read_text().splitlines()]
    left = [json.loads(l) for l in
            (tmp_path / "out" / "no_abstract.jsonl").read_text().splitlines()]
    assert [r["pmid"] for r in kept] == ["1"]
    assert [(r["pmid"], r["abstract_length"]) for r in left] == [("2", 0), ("3", 3)]


def test_every_known_item_has_an_abstract_above_the_floor():
    path = (pathlib.Path(__file__).resolve().parent.parent / "outputs" / "known_items"
            / "known_items_abstracts_24.jsonl")
    if not path.exists():
        pytest.skip("the known-item abstracts are not in this copy")
    lengths = [af.abstract_length(json.loads(l)["abstract"])
               for l in path.read_text().splitlines() if l.strip()]
    assert len(lengths) == 24 and min(lengths) >= af.ABSTRACT_FLOOR
