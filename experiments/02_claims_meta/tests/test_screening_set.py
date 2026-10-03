import datetime
import json
import pathlib
import random

import pytest

import assemble_screening_set as ass
import run_search as rs
from build_registry import PublicDate
from link_families import SearchRecord

TESTS = pathlib.Path(__file__).resolve().parent
FIX = TESTS / "fixtures" / "search"
DEV = TESTS.parent / "prompts" / "dev_abstracts.jsonl"


def pubmed_xml(pub_date: str, article_date: str = "", types: str = "Journal Article") -> bytes:
    return f"""<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>1</PMID><Article>
      <Journal><JournalIssue><PubDate>{pub_date}</PubDate></JournalIssue></Journal>
      <ArticleTitle>T</ArticleTitle><Abstract><AbstractText Label="AIM">a <i>b</i></AbstractText>
      <AbstractText>c</AbstractText></Abstract>
      <AuthorList><Author><LastName>van der Berg</LastName></Author></AuthorList>
      <PublicationTypeList><PublicationType>{types}</PublicationType></PublicationTypeList>
      {article_date}</Article></MedlineCitation><PubmedData><ArticleIdList>
      <ArticleId IdType="doi">10.1000/ABC</ArticleId><ArticleId IdType="pmc">PMC77</ArticleId>
      </ArticleIdList></PubmedData></PubmedArticle></PubmedArticleSet>""".encode()


def record(source, source_id, pmid=None, pmcid=None, doi=None, abstract="", kind="journal",
           published=None):
    return ass.RetrievedRecord(
        source=source, source_id=source_id, pmid=pmid, pmcid=pmcid, doi=doi, kind=kind,
        source_type="", title=f"title from {source}", abstract=abstract,
        first_author_surname=source, published_as_pmid=published,
        first_public=PublicDate(value=datetime.date(2020, 1, 1), resolution="day"))


def test_pubmed_abstracts_equal_the_development_file():
    dev = {r["pmid"]: r for r in map(json.loads, DEV.read_text().splitlines())}
    parsed = ass.parse_pubmed((FIX / "pubmed_efetch.xml").read_bytes())
    assert sorted(r.pmid for r in parsed) == ["29875488", "30111768"]
    for r in parsed:
        assert r.abstract == dev[r.pmid]["abstract"]
        assert r.title == dev[r.pmid]["title"]
        assert r.doi == dev[r.pmid]["doi"].lower()


@pytest.mark.parametrize("pub_date, article_date, value, resolution", [
    ("<Year>2021</Year>", "", datetime.date(2021, 1, 1), "year"),
    ("<Year>2021</Year><Month>Mar</Month>", "", datetime.date(2021, 3, 1), "month"),
    ("<Year>2021</Year><Month>03</Month><Day>9</Day>", "", datetime.date(2021, 3, 9), "day"),
    ("<MedlineDate>2021 Nov-Dec</MedlineDate>", "", datetime.date(2021, 1, 1), "year"),
    ("<Year>2021</Year><Month>Mar</Month>",
     '<ArticleDate DateType="Electronic"><Year>2020</Year><Month>12</Month><Day>24</Day>'
     "</ArticleDate>", datetime.date(2020, 12, 24), "day"),
])
def test_pubmed_date_is_electronic_else_issue_at_the_source_resolution(
        pub_date, article_date, value, resolution):
    rec, = ass.parse_pubmed(pubmed_xml(pub_date, article_date))
    assert (rec.first_public.value, rec.first_public.resolution) == (value, resolution)


def test_pubmed_fields():
    rec, = ass.parse_pubmed(pubmed_xml("<Year>2021</Year>"))
    assert (rec.abstract, rec.doi, rec.pmcid, rec.first_author_surname, rec.kind) == (
        "AIM: a b\nc", "10.1000/abc", "PMC77", "van der Berg", "journal")
    preprint, = ass.parse_pubmed(pubmed_xml("<Year>2021</Year>", types="Preprint"))
    assert preprint.kind == "preprint"


def test_epmc_records():
    by_id = {r.source_id: r for r in ass.parse_epmc((FIX / "epmc_page.json").read_bytes())}
    preprint, journal = by_id["PPR28578"], by_id["29875488"]
    assert (preprint.kind, preprint.pmid, preprint.published_as_pmid) == (
        "preprint", None, "29875488")
    assert preprint.first_public == PublicDate(value=datetime.date(2017, 5, 5),
                                               resolution="day")
    assert (journal.kind, journal.published_as_pmid) == ("journal", None)
    assert journal.first_public == PublicDate(value=datetime.date(2018, 6, 6),
                                              resolution="day")


@pytest.mark.parametrize("text, value, resolution", [
    ("2018", datetime.date(2018, 1, 1), "year"),
    ("2018 Nov", datetime.date(2018, 11, 1), "month"),
    ("2018 Nov 15", datetime.date(2018, 11, 15), "day"),
    ("2018 Nov-Dec", datetime.date(2018, 1, 1), "year"),
])
def test_epmc_issue_date_resolution(text, value, resolution):
    assert ass._epmc_issue_date(text) == PublicDate(value=value, resolution=resolution)


def test_epmc_journal_record_without_electronic_date_takes_the_issue_date():
    body = json.dumps({"resultList": {"result": [{
        "id": "5", "source": "MED", "pmid": "5", "title": "t",
        "firstPublicationDate": "2018-11-01",
        "journalInfo": {"dateOfPublication": "2018 Nov"}}]}}).encode()
    rec, = ass.parse_epmc(body)
    assert rec.first_public == PublicDate(value=datetime.date(2018, 11, 1), resolution="month")


def test_openalex_records_and_abstract_reconstruction():
    assert ass.abstract_from_inverted_index(
        {"proteins": [1, 4], "Plasma": [0], "and": [2], "more": [3]}) == (
        "Plasma proteins and more proteins")
    assert ass.abstract_from_inverted_index(None) == ""
    by_doi = {r.doi: r for r in ass.parse_openalex((FIX / "openalex_page.json").read_bytes())}
    journal, preprint = by_doi["10.1038/s41586-018-0175-2"], by_doi["10.1101/134551"]
    assert (journal.kind, journal.pmid, journal.first_author_surname) == (
        "journal", "29875488", "Sun")
    assert (preprint.kind, preprint.pmid) == ("preprint", None)
    assert journal.source_id.startswith("W") and "/" not in journal.source_id


@pytest.mark.parametrize("openalex_type, kind", [
    ("article", "journal"), ("review", "journal"), ("letter", "journal"),
    ("editorial", "journal"), ("preprint", "preprint"), ("conference-abstract", "other"),
    ("dissertation", "other"), ("dataset", "other"), ("peer-review", "other"),
    ("book-chapter", "other"), (None, "other")])
def test_openalex_document_class(openalex_type, kind):
    body = json.dumps({"results": [{
        "id": "https://openalex.org/W1", "doi": None, "ids": {}, "display_name": "t",
        "publication_date": "2021-01-01", "type": openalex_type, "authorships": [],
        "abstract_inverted_index": None}]}).encode()
    rec, = ass.parse_openalex(body)
    assert rec.kind == kind


@pytest.mark.parametrize("source, kind", [
    ("MED", "journal"), ("PMC", "journal"), ("PPR", "preprint"), ("PAT", "other"),
    ("ETH", "other"), ("AGR", "other"), ("NBK", "other")])
def test_europe_pmc_document_class(source, kind):
    body = json.dumps({"resultList": {"result": [{
        "id": "5", "source": source, "title": "t", "firstPublicationDate": "2021-01-01"}]}}
    ).encode()
    rec, = ass.parse_epmc(body)
    assert rec.kind == kind


def test_identifier_normalization():
    assert ass.norm_doi("https://doi.org/10.1038/S41586-018-0175-2") == (
        "10.1038/s41586-018-0175-2")
    assert ass.norm_doi("doi:10.1/X") == "10.1/x" and ass.norm_doi("") is None
    assert ass.norm_pmid("https://pubmed.ncbi.nlm.nih.gov/29875488") == "29875488"
    assert ass.norm_pmcid("https://www.ncbi.nlm.nih.gov/pmc/articles/6226147") == "PMC6226147"
    assert ass.norm_pmcid("PMC6226147") == "PMC6226147"


def test_deduplication_is_transitive_and_takes_fields_in_source_order():
    records = [
        record("openalex", "W1", doi="10.1/a", abstract="openalex abstract"),
        record("epmc", "11", pmid="11", pmcid="PMC9", abstract="epmc abstract"),
        record("pubmed", "11", pmid="11", doi="10.1/a"),
        record("openalex", "W2", pmcid="PMC9"),
        record("openalex", "W3", doi="10.1/b", abstract="other"),
    ]
    merged, other = ass.deduplicate(records)
    assert (merged.record_id, merged.title, merged.first_author_surname) == (
        "11", "title from pubmed", "pubmed")
    assert (merged.abstract, merged.abstract_source) == ("epmc abstract", "epmc")
    assert merged.sources == ["pubmed", "epmc", "openalex"]
    assert sorted(merged.member_ids) == ["epmc:11", "openalex:W1", "openalex:W2", "pubmed:11"]
    assert (other.record_id, other.abstract_source) == ("W3", "openalex")


def test_record_without_any_abstract_stays_among_the_screening_records_as_no_abstract():
    only, = ass.deduplicate([record("openalex", "W9", doi="10.1/z")])
    assert (only.abstract, only.abstract_source, only.no_abstract) == ("", None, True)


def test_published_link_is_a_doi_when_the_article_was_retrieved_else_a_pmid_token():
    out = {s.record_id: s for s in ass.deduplicate([
        record("epmc", "PPR1", doi="10.1101/1", kind="preprint", published="50"),
        record("epmc", "PPR2", doi="10.1101/2", kind="preprint", published="60"),
        record("pubmed", "50", pmid="50", doi="10.1/journal")])}
    assert out["PPR1"].published_as_doi == "10.1/journal"
    assert out["PPR2"].published_as_doi == "pmid:60"
    assert out["50"].published_as_doi is None


def test_deduplication_equals_connected_components_of_shared_identifiers():
    rng = random.Random()
    for _ in range(300):
        records = []
        for i in range(rng.randint(1, 14)):
            records.append(record(
                rng.choice(["pubmed", "epmc", "openalex"]), f"R{i}",
                pmid=rng.choice([None, "1", "2", "3"]),
                pmcid=rng.choice([None, "PMC1", "PMC2", "PMC3"]),
                doi=rng.choice([None, "10.1/a", "10.1/b", "10.1/c"])))
        component = {i: {i} for i in range(len(records))}
        changed = True
        while changed:
            changed = False
            for i, a in enumerate(records):
                for j, b in enumerate(records):
                    shares = any(getattr(a, f) and getattr(a, f) == getattr(b, f)
                                 for f in ("pmid", "pmcid", "doi"))
                    if shares and component[i] is not component[j]:
                        merged = component[i] | component[j]
                        for k in merged:
                            component[k] = merged
                        changed = True
        want = {frozenset(f"{records[k].source}:{records[k].source_id}" for k in c)
                for c in component.values()}
        got = {frozenset(s.member_ids) for s in ass.deduplicate(records)}
        assert got == want


def test_outputs_feed_the_family_linker_and_the_extraction_runner(tmp_path):
    run_dir = tmp_path / "run"
    for i, (source, name) in enumerate([("pubmed", "pubmed_efetch.xml"),
                                        ("epmc", "epmc_page.json"),
                                        ("openalex", "openalex_page.json")]):
        body = (FIX / name).read_bytes()
        target = run_dir / source / "s" / "page_0001.gz"
        target.parent.mkdir(parents=True)
        target.write_bytes(rs.gzip.compress(body))
        rs.append_manifest(run_dir, rs.Exchange(
            source=source, stream="efetch" if source == "pubmed" else "Q1_confirmatory",
            page=1, url="u", status=200, started_utc="", finished_utc="", bytes=len(body),
            sha256=rs.hashlib.sha256(body).hexdigest(), file=str(target.relative_to(run_dir))))
    funnel = ass.write_outputs(run_dir, tmp_path / "out")
    assert funnel["screening_records"] == 4 and funnel["duplicates_removed"] == 6
    assert funnel["pubmed_records_fetched_for_other_sources"] == 2
    rows = [json.loads(l) for l in (tmp_path / "out" / "screening_set.jsonl").read_text()
            .splitlines()]
    assert [set(r) for r in rows] == [{"pmid", "title", "abstract"}] * 4
    assert len([SearchRecord.model_validate_json(l) for l in
                (tmp_path / "out" / "search_records.jsonl").read_text().splitlines()]) == 4
    with pytest.raises(ass.AssembleError):
        ass.write_outputs(run_dir, tmp_path / "out")
