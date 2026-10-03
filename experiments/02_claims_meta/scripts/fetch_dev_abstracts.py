# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "pydantic==2.13.5"]
# ///
"""Fetch the prompt-development abstracts from PubMed E-utilities.

Every record must be first public before 2019-01-01: the earliest of the electronic article
date, the issue date and the PubMed entry date is taken as the first public date, and a record
whose dates are all missing or any of whose dates falls on or after 2019-01-01 raises. No email
or other identifier is sent. The raw efetch XML is kept in outputs/raw/pubmed/.

Selection was made by title only, before any abstract was read; `role` is the reason each record
is in the set, not a judgment of its abstract.

Usage: uv run scripts/fetch_dev_abstracts.py
"""

import datetime
import hashlib
import json
import pathlib
import time
import xml.etree.ElementTree as ET

import httpx
from pydantic import BaseModel

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
OUT = EXP / "prompts" / "dev_abstracts.jsonl"
RAW = EXP / "outputs" / "raw" / "pubmed"
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
CUTOFF = datetime.date(2019, 1, 1)
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

# PMID -> role. Roles: pqtl_mr_panel (multi-protein pQTL study with MR or disease links),
# single_protein_mr (MR of one or a few circulating proteins), near_miss_eqtl_mr,
# near_miss_pqtl_discovery, near_miss_review, near_miss_gene_score_mr.
SELECTION: dict[str, str] = {
    "29875488": "pqtl_mr_panel",        # Sun 2018 Nature, genomic atlas of the plasma proteome
    "28240269": "pqtl_mr_panel",        # Suhre 2017 Nat Commun
    "28369058": "pqtl_mr_panel",        # Folkersen 2017 PLoS Genet
    "30072576": "pqtl_mr_panel",        # Emilsson 2018 Science
    "30111768": "pqtl_mr_panel",        # Yao 2018 Nat Commun
    "29258991": "pqtl_mr_panel",        # Benson 2018 Circulation
    "27989323": "pqtl_mr_panel",        # Ahola-Olli 2017 AJHG, 41 cytokines
    "22421340": "single_protein_mr",    # IL6R MR consortium 2012 Lancet
    "22421339": "single_protein_mr",    # IL6R genetics consortium 2012 Lancet
    "21325005": "single_protein_mr",    # CRP CHD genetics collaboration 2011 BMJ
    "25726324": "single_protein_mr",    # IL1RN 2015 Lancet Diabetes Endocrinol
    "19509380": "single_protein_mr",    # Lp(a) 2009 JAMA
    "25938632": "single_protein_mr",    # Lp(a) and inflammation 2015
    "29728394": "single_protein_mr",    # CETP concentration GWAS + MR 2018
    "29191953": "single_protein_mr",    # surfactant protein D and COPD 2017
    "27882376": "single_protein_mr",    # protein C and ischaemic heart disease 2017
    "27327646": "single_protein_mr",    # CRP and 32 outcomes 2016
    "27225428": "single_protein_mr",    # IGFs and binding proteins, prostate cancer 2016
    "26886630": "single_protein_mr",    # IL-10 and digestive cancers 2016
    "25350643": "single_protein_mr",    # vitamin D binding protein 2014
    "24246360": "single_protein_mr",    # CRP, depression and mortality 2014
    "27019110": "near_miss_eqtl_mr",    # Zhu 2016 Nat Genet, SMR on eQTL
    "27506385": "near_miss_eqtl_mr",    # Pavlides 2016 Genome Med, SMR on eQTL
    "18464913": "near_miss_pqtl_discovery",  # Melzer 2008 PLoS Genet
    "23487758": "near_miss_pqtl_discovery",  # Johansson 2013 PNAS
    "22595970": "near_miss_pqtl_discovery",  # Lourdusamy 2012 Hum Mol Genet
    "29226067": "near_miss_review",     # Zheng 2017 Curr Epidemiol Rep
    "29040597": "near_miss_review",     # Walker 2017 IJE
    "28569269": "near_miss_review",     # Holmes 2017 Nat Rev Cardiol
    "27959767": "near_miss_gene_score_mr",  # Ference 2016 NEJM, PCSK9/HMGCR gene scores
}


class FetchError(Exception):
    """A record could not be fetched or fails the pre-2019 rule."""


class DevAbstract(BaseModel):
    pmid: str
    doi: str | None
    title: str
    abstract: str
    journal: str
    role: str
    dates: dict[str, str]
    first_public_date: str
    abstract_sha256: str


def _date(el: ET.Element | None) -> datetime.date | None:
    if el is None:
        return None
    year = el.findtext("Year")
    if not year:
        medline = el.findtext("MedlineDate")
        return datetime.date(int(medline[:4]), 1, 1) if medline else None
    month_txt = (el.findtext("Month") or "1").strip()
    month = int(month_txt) if month_txt.isdigit() else MONTHS[month_txt[:3].lower()]
    day = int(el.findtext("Day") or 1)
    return datetime.date(int(year), month, day)


def _text(el: ET.Element) -> str:
    return " ".join("".join(el.itertext()).split())


def parse(article: ET.Element, role: str) -> DevAbstract:
    pmid = article.findtext(".//MedlineCitation/PMID")
    art = article.find(".//MedlineCitation/Article")
    if pmid is None or art is None:
        raise FetchError("record without PMID or Article")
    parts = []
    for node in art.findall("./Abstract/AbstractText"):
        label = node.get("Label")
        body = _text(node)
        parts.append(f"{label}: {body}" if label else body)
    if not parts:
        raise FetchError(f"{pmid}: no abstract")
    abstract = "\n".join(parts)
    dates: dict[str, datetime.date] = {}
    issue = _date(art.find("./Journal/JournalIssue/PubDate"))
    if issue:
        dates["issue"] = issue
    for ad in art.findall("./ArticleDate"):
        d = _date(ad)
        if d:
            dates[f"article_{ad.get('DateType', 'unknown').lower()}"] = d
    for pd in article.findall(".//PubmedData/History/PubMedPubDate"):
        status = pd.get("PubStatus", "")
        if status in {"entrez", "pubmed", "medline"}:
            d = _date(pd)
            if d:
                dates[f"pubmed_{status}"] = d
    public = [v for k, v in dates.items() if k.startswith(("issue", "article_", "pubmed_entrez"))]
    if not public:
        raise FetchError(f"{pmid}: no public date")
    late = {k: v for k, v in dates.items() if k != "pubmed_medline" and v >= CUTOFF}
    if late:
        raise FetchError(f"{pmid}: date on or after 2019-01-01: {late}")
    doi = next((i.text for i in article.findall(".//PubmedData/ArticleIdList/ArticleId")
                if i.get("IdType") == "doi"), None)
    return DevAbstract(
        pmid=pmid, doi=doi, title=_text(art.find("./ArticleTitle")), abstract=abstract,
        journal=art.findtext("./Journal/Title") or "", role=role,
        dates={k: v.isoformat() for k, v in sorted(dates.items())},
        first_public_date=min(public).isoformat(),
        abstract_sha256=hashlib.sha256(abstract.encode()).hexdigest(),
    )


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    ids = list(SELECTION)
    records: dict[str, DevAbstract] = {}
    with httpx.Client(timeout=60) as client:
        for start in range(0, len(ids), 10):
            batch = ids[start:start + 10]
            r = client.get(EFETCH, params={"db": "pubmed", "id": ",".join(batch), "retmode": "xml"})
            r.raise_for_status()
            stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
            (RAW / f"efetch_{stamp}_{start:03d}.xml").write_bytes(r.content)
            for article in ET.fromstring(r.content).findall("./PubmedArticle"):
                rec = parse(article, SELECTION[article.findtext(".//MedlineCitation/PMID")])
                records[rec.pmid] = rec
            time.sleep(1.0)
    missing = set(ids) - set(records)
    if missing:
        raise FetchError(f"not returned: {sorted(missing)}")
    with OUT.open("w") as f:
        for pmid in ids:
            f.write(records[pmid].model_dump_json() + "\n")
    print(f"wrote {len(records)} records to {OUT}")
    for pmid in ids:
        r = records[pmid]
        print(f"  {pmid}  {r.first_public_date}  {r.role:<26} {r.title[:70]}")


if __name__ == "__main__":
    main()
