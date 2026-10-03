# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1"]
# ///
"""Does PubMed's colocali*[tiab] also match the hyphenated "co-locali..." forms? 2014-2018, counts only."""
import json, pathlib, time
import httpx
D_PM = ' AND ("2014/01/01"[dp] : "2018/12/31"[dp])'
D_EP = ' AND FIRST_PDATE:[2014-01-01 TO 2018-12-31] AND SRC:MED'
PM = {
 "repurpos*": 'repurpos*[tiab]', "re-purpos*": '"re-purpos*"[tiab]', "repurpos* OR re-purpos*": '(repurpos*[tiab] OR "re-purpos*"[tiab])',
 "pQTL": 'pQTL[tiab]', "p-QTL": '"p-QTL"[tiab]', "pQTL OR p-QTL": '(pQTL[tiab] OR "p-QTL"[tiab])',
 "colocalization": 'colocalization[tiab]',
 "co-localization": '"co-localization"[tiab]',
 "colocalization OR co-localization": '(colocalization[tiab] OR "co-localization"[tiab])',
 "colocalization NOT co-localization": '(colocalization[tiab] NOT "co-localization"[tiab])',
 "colocali*": 'colocali*[tiab]',
 "colocali* OR co-locali*": '(colocali*[tiab] OR "co-locali*"[tiab])',
 "proteome-wide": 'proteome-wide[tiab]', "proteome wide (phrase)": '"proteome wide"[tiab]', "proteomewide": 'proteomewide[tiab]',
 "tiab vs ti OR ab: colocalization[ti] OR colocalization[ab]": '(colocalization[ti] OR colocalization[ab])',
 "colocalization[ot]": 'colocalization[ot]',
}
EP = {
 "repurpos*": 'TITLE_ABS:repurpos*', "repurpos* + hyphen forms": '(TITLE_ABS:repurpos* OR TITLE_ABS:"re-purpose" OR TITLE_ABS:"re-purposed" OR TITLE_ABS:"re-purposes" OR TITLE_ABS:"re-purposing")',
 "colocali* + hyphen forms": '(TITLE_ABS:colocali* OR ' + " OR ".join(f'TITLE_ABS:"co-locali{x}"' for x in ["zation","sation","zations","sations","zed","sed","ze","se","zes","ses","zing","sing"]) + ")",
 "pQTL": 'TITLE_ABS:pQTL', "pQTL OR p-QTL": '(TITLE_ABS:pQTL OR TITLE_ABS:"p-QTL")',
 "colocalization": 'TITLE_ABS:colocalization',
 "co-localization": 'TITLE_ABS:"co-localization"',
 "colocalization OR co-localization": '(TITLE_ABS:colocalization OR TITLE_ABS:"co-localization")',
 "colocali*": 'TITLE_ABS:colocali*',
 "KW:colocalization": 'KW:colocalization',
 "TITLE_ABS or KW colocalization": '(TITLE_ABS:colocalization OR KW:colocalization)',
}
out = {"pubmed": {}, "epmc_med": {}}
with httpx.Client(timeout=90) as c:
    for k, q in PM.items():
        r = c.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params={"db": "pubmed", "term": q + D_PM, "retmode": "json", "retmax": 0})
        out["pubmed"][k] = int(r.json()["esearchresult"]["count"]); time.sleep(0.5)
    for k, q in EP.items():
        r = c.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search", params={"query": q + D_EP, "format": "json", "resultType": "idlist", "pageSize": 1, "synonym": "false"})
        out["epmc_med"][k] = r.json()["hitCount"]; time.sleep(0.4)
pathlib.Path(__file__).with_suffix(".json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
