# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "pydantic==2.13.5"]
# ///
"""Fetch the Europe PMC preprint records (SRC:PPR) of Q1 for 2014-2018, core format, to see the
shape of a preprint record. Pre-window records only."""
import datetime, importlib.util, json, pathlib
import httpx
HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("search_queries", HERE.parent.parent / "experiments" / "02_claims_meta" / "scripts" / "search_queries.py")
sq = importlib.util.module_from_spec(spec); spec.loader.exec_module(sq)
q = f"({sq.epmc_query('Q1', datetime.date(2014,1,1), datetime.date(2018,12,31))}) AND SRC:PPR"
r = httpx.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search", params={"query": q, "format": "json", "resultType": "core", "synonym": "false", "pageSize": 25}, timeout=90)
(HERE / "epmc_ppr_shape_pre2019.json").write_bytes(r.content)
for x in r.json()["resultList"]["result"]:
    print(x["source"], x["id"], x.get("pmid"), x.get("doi"), x.get("firstPublicationDate"), x.get("pubTypeList"), x.get("commentCorrectionList"), {k: x[k] for k in x if "ersion" in k or k in ("bookOrReportDetails",)}, (x.get("authorList") or {}).get("author", [{}])[0].get("lastName"), sorted(set(x) - {"abstractText", "title", "authorList", "authorString", "affiliation"}))
