# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1"]
# ///
"""Fetch the test fixtures: PubMed, Europe PMC and OpenAlex responses for two pre-2019 development
papers (PMIDs 29875488 and 30111768) and their bioRxiv preprints. Pre-window records only."""
import json, pathlib, time
import httpx
HERE = pathlib.Path(__file__).resolve().parent
FIX = HERE.parent.parent / "experiments" / "02_claims_meta" / "tests" / "fixtures" / "search"
SELECT = "id,doi,ids,display_name,publication_date,publication_year,type,language,authorships,primary_location,abstract_inverted_index"
with httpx.Client(timeout=90) as c:
    r = c.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi", params={"db": "pubmed", "id": "29875488,30111768", "retmode": "xml"})
    r.raise_for_status(); (FIX / "pubmed_efetch.xml").write_bytes(r.content); time.sleep(0.5)
    r = c.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search", params={
        "query": "(EXT_ID:29875488 AND SRC:MED) OR (EXT_ID:30111768 AND SRC:MED) OR (EXT_ID:PPR28578 AND SRC:PPR) OR (EXT_ID:PPR28491 AND SRC:PPR)",
        "format": "json", "resultType": "core", "synonym": "false", "pageSize": 25, "cursorMark": "*"})
    r.raise_for_status(); d = r.json()
    keep = ("id", "source", "pmid", "pmcid", "doi", "title", "abstractText", "firstPublicationDate", "electronicPublicationDate", "journalInfo", "pubTypeList", "commentCorrectionList", "bookOrReportDetails")
    for x in d["resultList"]["result"]:
        first = (x.get("authorList") or {}).get("author", [{}])[0]
        slim = {k: x[k] for k in keep if k in x}
        slim["authorList"] = {"author": [{k: first[k] for k in ("fullName", "lastName", "collectiveName") if k in first}]}
        x.clear(); x.update(slim)
    (FIX / "epmc_page.json").write_text(json.dumps(d, indent=1, ensure_ascii=False))
    r = c.get("https://api.openalex.org/works", params={"filter": "doi:10.1038/s41586-018-0175-2|10.1038/s41467-018-05512-x|10.1101/134551|10.1101/136523", "select": SELECT, "per_page": 100, "cursor": "*"})
    r.raise_for_status(); d = r.json()
    for w in d["results"]:
        w["authorships"] = [{k: a[k] for k in ("author_position", "author", "raw_author_name")} for a in w["authorships"][:2]]
    d["meta"].pop("x_query", None)
    (FIX / "openalex_page.json").write_text(json.dumps(d, indent=1, ensure_ascii=False))
    print([(w["id"], w["doi"], w["type"], w["publication_date"], w["ids"].get("pmid")) for w in d["results"]])
