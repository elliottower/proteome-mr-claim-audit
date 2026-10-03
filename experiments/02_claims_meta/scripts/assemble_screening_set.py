# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "numpy==2.5.3", "pydantic==2.13.5", "rapidfuzz==3.14.6"]
# ///
"""Build the screening set from the stored search responses.

Each stored PubMed, Europe PMC and OpenAlex record becomes one `RetrievedRecord`. Two retrieved
records are one screening record when they share a PMID, a PMCID or a DOI (DOIs compared in
lower case without a resolver prefix); sharing is transitive. A screening record takes, in the
order PubMed, Europe PMC, OpenAlex (SOURCE_ORDER):

    record id        its PMID; else its Europe PMC identifier; else its OpenAlex identifier
    title, first author, date, kind    from the first source that holds the record
    abstract         the first abstract of at least ABSTRACT_FLOOR characters
                     (scripts/abstract_floor.py); when no source holds one, the record is
                     `no_abstract` and keeps the first non-empty text, or none
    journal          the first non-empty journal title (PubMed `Journal/Title`, Europe PMC
                     `journalInfo.journal.title`, OpenAlex `primary_location.source`); read
                     only for the journal tabulation of scripts/registry_secondaries.py

A PubMed record fetched because another source returned its PMID (`efetch_linked`) carries no
query stream; it supplies the PubMed abstract and metadata of that record.

Kind (the document class), from the first source that holds the record:

    preprint   a PubMed record of publication type Preprint, a Europe PMC record of source PPR,
               an OpenAlex work of type preprint
    journal    any other PubMed record; a Europe PMC record of source MED or PMC; an OpenAlex
               work of type article, review, letter or editorial
    other      everything else: Europe PMC patents, theses and other sources; OpenAlex
               conference abstracts, dissertations, datasets, peer-review reports, book chapters
               and the like

Records of every kind are screened. A record of kind `other` enters no primary result
(scripts/assemble_registry.py). The source's own type string is kept as `source_type`.

A `no_abstract` record is not screened: it is written to no_abstract.jsonl and left out of
screening_set.jsonl, so the keyword prefilter, the gate, the gate audit and GPT-6.1 Sol never
read it. It stays in screening_records.jsonl and search_records.jsonl, flagged, because a
family links its records whatever their abstracts (scripts/assemble_registry.py).

First public date, at the resolution the source gives: PubMed, the electronic article date,
else the issue date; Europe PMC, the electronic publication date, else the issue date, and for
a preprint its first publication date; OpenAlex, `publication_date`.

A Europe PMC preprint's "Preprint of" link names the published article by PMID. It becomes the
record's `published_as_doi`: the article's DOI when the article is in the retrieved set, else
`pmid:<PMID>`, which matches no record and keeps the preprint out of fuzzy linking.

Outputs, in outputs/screening/<run>/: retrieved_records.jsonl, screening_records.jsonl,
search_records.jsonl (input of link_families.py), screening_set.jsonl (the records with an
abstract: input of keyword_prefilter.py and run_extraction.py; `pmid` holds the record id),
no_abstract.jsonl (the `no_abstract` records: id, title, document class, abstract length and
the stub text) and funnel.json.

Usage: uv run scripts/assemble_screening_set.py --run outputs/raw/search/<date>
"""

import argparse
import collections
import datetime
import json
import pathlib
import re
import xml.etree.ElementTree as ET
from typing import Literal

from pydantic import BaseModel, computed_field

from abstract_floor import ABSTRACT_FLOOR, abstract_length, is_no_abstract
from build_registry import PublicDate
from link_families import SearchRecord
from run_search import read_body, read_manifest

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
OUT = EXP / "outputs" / "screening"
SOURCE_ORDER = ("pubmed", "epmc", "openalex")
EPMC_JOURNAL_SOURCES = ("MED", "PMC")
OPENALEX_JOURNAL_TYPES = ("article", "review", "letter", "editorial")
Kind = Literal["journal", "preprint", "other"]
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


class AssembleError(Exception):
    """A stored response cannot be read, or an output already exists."""


class RetrievedRecord(BaseModel):
    source: Literal["pubmed", "epmc", "openalex"]
    source_id: str
    pmid: str | None
    pmcid: str | None
    doi: str | None
    kind: Kind
    source_type: str
    title: str
    abstract: str
    first_author_surname: str
    first_public: PublicDate
    published_as_pmid: str | None = None
    streams: list[str] = []
    journal: str | None = None


class ScreeningRecord(BaseModel):
    record_id: str
    pmid: str | None
    pmcid: str | None
    doi: str | None
    kind: Kind
    source_types: dict[str, str]
    title: str
    abstract: str
    abstract_source: str | None
    first_author_surname: str
    first_public: PublicDate
    published_as_doi: str | None
    sources: list[str]
    streams: list[str]
    member_ids: list[str]
    journal: str | None = None

    @computed_field
    @property
    def no_abstract(self) -> bool:
        return is_no_abstract(self.abstract)


def norm_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    return re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", doi.strip(), flags=re.I).lower()


def norm_pmid(pmid: str | None) -> str | None:
    if not pmid:
        return None
    return pmid.rstrip("/").rsplit("/", 1)[-1]


def norm_pmcid(pmcid: str | None) -> str | None:
    if not pmcid:
        return None
    digits = re.search(r"(\d+)\s*$", pmcid.rstrip("/"))
    return f"PMC{digits.group(1)}" if digits else None


def _text(el: ET.Element | None) -> str:
    return "" if el is None else " ".join("".join(el.itertext()).split())


def _month(text: str) -> int:
    text = text.strip()
    return int(text) if text.isdigit() else MONTHS[text[:3].lower()]


def _pubmed_date(el: ET.Element) -> PublicDate | None:
    year = el.findtext("Year")
    if not year:
        medline = el.findtext("MedlineDate")
        m = re.match(r"(\d{4})", medline or "")
        return PublicDate(value=datetime.date(int(m.group(1)), 1, 1),
                          resolution="year") if m else None
    month, day = el.findtext("Month"), el.findtext("Day")
    if not month:
        return PublicDate(value=datetime.date(int(year), 1, 1), resolution="year")
    if not day:
        return PublicDate(value=datetime.date(int(year), _month(month), 1), resolution="month")
    return PublicDate(value=datetime.date(int(year), _month(month), int(day)), resolution="day")


def parse_pubmed(body: bytes) -> list[RetrievedRecord]:
    out = []
    for article in ET.fromstring(body).findall("./PubmedArticle"):
        pmid = article.findtext("./MedlineCitation/PMID")
        art = article.find("./MedlineCitation/Article")
        if pmid is None or art is None:
            raise AssembleError("PubMed record without PMID or Article")
        parts = []
        for node in art.findall("./Abstract/AbstractText"):
            label, text = node.get("Label"), _text(node)
            parts.append(f"{label}: {text}" if label else text)
        electronic = next((d for d in (_pubmed_date(ad) for ad in art.findall("./ArticleDate")
                                       if ad.get("DateType") == "Electronic") if d), None)
        issue = art.find("./Journal/JournalIssue/PubDate")
        date = electronic or (_pubmed_date(issue) if issue is not None else None)
        if date is None:
            raise AssembleError(f"PubMed {pmid}: no electronic or issue date")
        ids = {i.get("IdType"): i.text for i in
               article.findall("./PubmedData/ArticleIdList/ArticleId")}
        types = [t.text or "" for t in art.findall("./PublicationTypeList/PublicationType")]
        first = art.find("./AuthorList/Author")
        surname = "" if first is None else (first.findtext("LastName")
                                            or first.findtext("CollectiveName") or "")
        out.append(RetrievedRecord(
            source="pubmed", source_id=pmid, pmid=pmid, pmcid=norm_pmcid(ids.get("pmc")),
            doi=norm_doi(ids.get("doi")), kind="preprint" if "Preprint" in types else "journal",
            source_type="; ".join(types), title=_text(art.find("./ArticleTitle")),
            abstract="\n".join(parts), first_author_surname=surname, first_public=date,
            journal=art.findtext("./Journal/Title") or None))
    return out


def _epmc_issue_date(text: str | None) -> PublicDate | None:
    """Europe PMC `journalInfo.dateOfPublication`: "2018", "2018 Nov" or "2018 Nov 15"."""
    m = re.fullmatch(r"(\d{4})(?: ([A-Za-z]{3})[A-Za-z]*)?(?: (\d{1,2}))?", (text or "").strip())
    if not m or (m.group(2) and m.group(2).lower() not in MONTHS):
        year = re.match(r"(\d{4})", text or "")
        return PublicDate(value=datetime.date(int(year.group(1)), 1, 1),
                          resolution="year") if year else None
    year, month, day = int(m.group(1)), m.group(2), m.group(3)
    if not month:
        return PublicDate(value=datetime.date(year, 1, 1), resolution="year")
    if not day:
        return PublicDate(value=datetime.date(year, MONTHS[month.lower()], 1),
                          resolution="month")
    return PublicDate(value=datetime.date(year, MONTHS[month.lower()], int(day)),
                      resolution="day")


def _day(text: str) -> PublicDate:
    return PublicDate(value=datetime.date.fromisoformat(text), resolution="day")


def parse_epmc(body: bytes) -> list[RetrievedRecord]:
    out = []
    for r in json.loads(body).get("resultList", {}).get("result", []):
        preprint = r["source"] == "PPR"
        if preprint or not (r.get("electronicPublicationDate")
                            or (r.get("journalInfo") or {}).get("dateOfPublication")):
            date = _day(r["firstPublicationDate"])
        elif r.get("electronicPublicationDate"):
            date = _day(r["electronicPublicationDate"])
        else:
            date = _epmc_issue_date(r["journalInfo"]["dateOfPublication"]) or _day(
                r["firstPublicationDate"])
        authors = (r.get("authorList") or {}).get("author") or [{}]
        published = [c["id"] for c in (r.get("commentCorrectionList") or {}).get(
            "commentCorrection", []) if c.get("type") == "Preprint of" and c.get("source") == "MED"]
        types = (r.get("pubTypeList") or {}).get("pubType", [])
        out.append(RetrievedRecord(
            source="epmc", source_id=r["id"] if r["source"] in ("MED", "PPR")
            else f"{r['source']}{r['id']}",
            pmid=r.get("pmid"), pmcid=norm_pmcid(r.get("pmcid")), doi=norm_doi(r.get("doi")),
            kind="preprint" if preprint else "journal"
            if r["source"] in EPMC_JOURNAL_SOURCES else "other",
            source_type=f"{r['source']}: {'; '.join(types)}", title=r.get("title") or "",
            abstract=r.get("abstractText") or "",
            first_author_surname=authors[0].get("lastName") or authors[0].get(
                "collectiveName") or "",
            first_public=date, published_as_pmid=published[0] if published else None,
            journal=((r.get("journalInfo") or {}).get("journal") or {}).get("title") or None))
    return out


def abstract_from_inverted_index(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    positions = sorted((p, word) for word, ps in index.items() for p in ps)
    return " ".join(word for _, word in positions)


def parse_openalex(body: bytes) -> list[RetrievedRecord]:
    out = []
    for w in json.loads(body)["results"]:
        ids = w.get("ids") or {}
        first = next((a for a in w.get("authorships") or []
                      if a.get("author_position") == "first"), None)
        name = "" if first is None else ((first.get("author") or {}).get("display_name")
                                         or first.get("raw_author_name") or "")
        out.append(RetrievedRecord(
            source="openalex", source_id=w["id"].rsplit("/", 1)[-1],
            pmid=norm_pmid(ids.get("pmid")), pmcid=norm_pmcid(ids.get("pmcid")),
            doi=norm_doi(w.get("doi")),
            kind="preprint" if w.get("type") == "preprint" else "journal"
            if w.get("type") in OPENALEX_JOURNAL_TYPES else "other",
            source_type=w.get("type") or "", title=w.get("display_name") or "",
            abstract=abstract_from_inverted_index(w.get("abstract_inverted_index")),
            first_author_surname=name.split()[-1] if name.split() else "",
            first_public=_day(w["publication_date"]),
            journal=((w.get("primary_location") or {}).get("source") or {}).get(
                "display_name") or None))
    return out


PARSERS = {"pubmed": parse_pubmed, "epmc": parse_epmc, "openalex": parse_openalex}


def load_run(run_dir: pathlib.Path) -> list[RetrievedRecord]:
    """Every record of every stored page, with the query streams that retrieved it."""
    pages = [l for l in read_manifest(run_dir) if l.get("status") == 200]
    pmid_streams: dict[str, list[str]] = collections.defaultdict(list)
    merged: dict[tuple[str, str], RetrievedRecord] = {}
    for l in pages:
        body = read_body(run_dir, l)
        if l["source"] == "pubmed" and l["stream"].startswith("esearch_"):
            for pmid in json.loads(body)["esearchresult"]["idlist"]:
                pmid_streams[pmid].append(l["stream"].removeprefix("esearch_"))
            continue
        for rec in PARSERS[l["source"]](body):
            key = (rec.source, rec.source_id)
            stream = [] if l["source"] == "pubmed" else [l["stream"]]
            if key in merged:
                merged[key].streams.extend(s for s in stream if s not in merged[key].streams)
            else:
                merged[key] = rec.model_copy(update={"streams": stream})
    for (source, source_id), rec in merged.items():
        if source == "pubmed":
            rec.streams.extend(pmid_streams[source_id])
    return list(merged.values())


def deduplicate(records: list[RetrievedRecord]) -> list[ScreeningRecord]:
    parent = list(range(len(records)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen: dict[tuple[str, str], int] = {}
    for i, r in enumerate(records):
        for field in ("pmid", "pmcid", "doi"):
            value = getattr(r, field)
            if not value:
                continue
            j = seen.setdefault((field, value), i)
            parent[find(i)] = find(j)
    clusters: dict[int, list[RetrievedRecord]] = collections.defaultdict(list)
    for i, r in enumerate(records):
        clusters[find(i)].append(r)
    doi_of_pmid = {r.pmid: r.doi for r in records if r.pmid and r.doi}

    out = []
    for members in clusters.values():
        members.sort(key=lambda r: (SOURCE_ORDER.index(r.source), r.source_id))
        lead = members[0]
        pmids = sorted({r.pmid for r in members if r.pmid}, key=int)
        with_abstract = (next((r for r in members if not is_no_abstract(r.abstract)), None)
                         or next((r for r in members if r.abstract.strip()), None))
        published = next((r.published_as_pmid for r in members if r.published_as_pmid), None)
        out.append(ScreeningRecord(
            record_id=pmids[0] if pmids else lead.source_id,
            pmid=pmids[0] if pmids else None,
            pmcid=next((r.pmcid for r in members if r.pmcid), None),
            doi=next((r.doi for r in members if r.doi), None),
            kind=lead.kind, source_types={r.source: r.source_type for r in reversed(members)},
            title=lead.title, abstract=with_abstract.abstract if with_abstract else "",
            abstract_source=with_abstract.source if with_abstract else None,
            first_author_surname=lead.first_author_surname, first_public=lead.first_public,
            published_as_doi=(doi_of_pmid.get(published) or f"pmid:{published}")
            if published else None,
            sources=sorted({r.source for r in members}, key=SOURCE_ORDER.index),
            streams=sorted({f"{r.source}/{s}" for r in members for s in r.streams}),
            member_ids=[f"{r.source}:{r.source_id}" for r in members],
            journal=next((r.journal for r in members if r.journal), None)))
    ids = [s.record_id for s in out]
    if len(set(ids)) != len(ids):
        raise AssembleError("two screening records share a record id")
    return sorted(out, key=lambda s: s.record_id)


def no_abstract_counts(screening: list[ScreeningRecord]) -> dict:
    """The `no_abstract` records of a screening set: with no text at all, with a stub below
    the floor, and by document class."""
    rows = [s for s in screening if s.no_abstract]
    return {"records": len(rows), "empty": sum(not s.abstract.strip() for s in rows),
            "stub_below_floor": sum(bool(s.abstract.strip()) for s in rows),
            "by_document_class": dict(sorted(collections.Counter(s.kind for s in rows).items())),
            "floor_characters": ABSTRACT_FLOOR}


def write_screening_files(out_dir: pathlib.Path, screening: list[ScreeningRecord]) -> None:
    """screening_records.jsonl, search_records.jsonl, screening_set.jsonl (records with an
    abstract only) and no_abstract.jsonl, for the search and for a chase round alike."""
    (out_dir / "screening_records.jsonl").write_text(
        "".join(s.model_dump_json() + "\n" for s in screening))
    (out_dir / "search_records.jsonl").write_text("".join(SearchRecord(
        record_id=s.record_id, kind=s.kind, doi=s.doi, pmid=s.pmid, pmcid=s.pmcid,
        published_as_doi=s.published_as_doi, title=s.title,
        first_author_surname=s.first_author_surname, first_public=s.first_public,
        no_abstract=s.no_abstract).model_dump_json() + "\n" for s in screening))
    (out_dir / "screening_set.jsonl").write_text("".join(json.dumps(
        {"pmid": s.record_id, "title": s.title, "abstract": s.abstract},
        ensure_ascii=False) + "\n" for s in screening if not s.no_abstract))
    (out_dir / "no_abstract.jsonl").write_text("".join(json.dumps(
        {"pmid": s.record_id, "title": s.title, "kind": s.kind,
         "abstract_length": abstract_length(s.abstract), "abstract": s.abstract},
        ensure_ascii=False) + "\n" for s in screening if s.no_abstract))


def funnel(records: list[RetrievedRecord], screening: list[ScreeningRecord]) -> dict:
    per_stream: dict[str, int] = collections.Counter(
        f"{r.source}/{s}" for r in records for s in r.streams)
    return {
        "source_records": dict(collections.Counter(r.source for r in records)),
        "pubmed_records_fetched_for_other_sources": sum(
            r.source == "pubmed" and not r.streams for r in records),
        "retrieved_records_by_stream": dict(sorted(per_stream.items())),
        "screening_records": len(screening),
        "duplicates_removed": len(records) - len(screening),
        "screening_records_by_sources": dict(collections.Counter(
            "+".join(s.sources) for s in screening)),
        "screening_records_by_kind": dict(collections.Counter(s.kind for s in screening)),
        "screening_records_by_lead_source_type": dict(collections.Counter(
            f"{s.sources[0]}: {s.source_types[s.sources[0]]}" for s in screening)),
        "no_abstract": no_abstract_counts(screening),
        "screening_records_with_an_abstract": sum(not s.no_abstract for s in screening),
        "preprints_with_published_link": sum(s.published_as_doi is not None for s in screening),
    }


def write_outputs(run_dir: pathlib.Path, out_dir: pathlib.Path) -> dict:
    if out_dir.exists():
        raise AssembleError(f"{out_dir} exists; archive it before rerunning")
    records = load_run(run_dir)
    screening = deduplicate(records)
    out_dir.mkdir(parents=True)
    (out_dir / "retrieved_records.jsonl").write_text(
        "".join(r.model_dump_json() + "\n" for r in records))
    write_screening_files(out_dir, screening)
    result = {"run": str(run_dir), **funnel(records, screening)}
    (out_dir / "funnel.json").write_text(json.dumps(result, indent=1))
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=pathlib.Path, required=True,
                    help="a run directory written by run_search.py")
    ap.add_argument("--out", type=pathlib.Path,
                    help="output directory (default outputs/screening/<run name>)")
    a = ap.parse_args()
    print(json.dumps(write_outputs(a.run, a.out or OUT / a.run.name), indent=1))


if __name__ == "__main__":
    main()
