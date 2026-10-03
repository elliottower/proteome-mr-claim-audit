# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "pydantic==2.13.5"]
# ///
"""Translation check on records first published 2014-2018 only: hit counts of the four queries in
PubMed, Europe PMC and OpenAlex, with the registered blocks and a pre-window date range. Counts
only; no record content is requested (retmax=0, idlist page of 1, select=id). Keyless OpenAlex."""
import datetime
import importlib.util
import json
import pathlib
import time

import httpx

HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = HERE.parent.parent / "experiments" / "02_claims_meta" / "scripts"
spec = importlib.util.spec_from_file_location("search_queries", SCRIPTS / "search_queries.py")
sq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sq)

START, END = datetime.date(2014, 1, 1), datetime.date(2018, 12, 31)
out = {"window": [START.isoformat(), END.isoformat()], "run_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"), "queries": {}}


def get(client, url, params):
    for attempt in range(5):
        try:
            r = client.get(url, params=params)
            if r.status_code == 200:
                return r
            last = f"{r.status_code} {r.text[:300]}"
            if r.status_code == 400:
                break
        except httpx.HTTPError as e:
            last = repr(e)
        time.sleep(3 + 2 * attempt)
    raise RuntimeError(last)


with httpx.Client(timeout=90) as client:
    for q in sq.QUERIES:
        row = {}
        r = get(client, "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                {"db": "pubmed", "term": sq.pubmed_query(q, START, END), "retmode": "json", "retmax": 0})
        row["pubmed"] = int(r.json()["esearchresult"]["count"])
        time.sleep(0.5)
        e = sq.epmc_query(q, START, END)
        for label, query in (("epmc_all_sources", e), ("epmc_src_med", f"({e}) AND SRC:MED"), ("epmc_src_ppr", f"({e}) AND SRC:PPR"),
                             ("epmc_other_sources", f"({e}) NOT (SRC:MED OR SRC:PPR)")):
            r = get(client, "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                    {"query": query, "format": "json", "resultType": "idlist", "pageSize": 1, "synonym": "false"})
            row[label] = r.json()["hitCount"]
            time.sleep(0.4)
        f = sq.openalex_filter(q, START, END)
        r = get(client, "https://api.openalex.org/works", {"filter": f, "per_page": 1, "select": "id"})
        row["openalex"] = r.json()["meta"]["count"]
        row["openalex_url_bytes"] = len(str(r.request.url))
        row["openalex_credits_remaining"] = r.headers.get("X-RateLimit-Remaining")
        out["queries"][q] = row
        (HERE / "translation_check_pre2019.json").write_text(json.dumps(out, indent=1))
        time.sleep(1)
    # OpenAlex case sensitivity of the exact filter, one pair of calls.
    case = {}
    for word in ("pQTL", "pqtl"):
        r = get(client, "https://api.openalex.org/works",
                {"filter": f"{sq.OPENALEX_FILTER}:{word},from_publication_date:2014-01-01,to_publication_date:2018-12-31", "per_page": 1, "select": "id"})
        case[word] = r.json()["meta"]["count"]
        time.sleep(1)
    out["openalex_case"] = case
(HERE / "translation_check_pre2019.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
