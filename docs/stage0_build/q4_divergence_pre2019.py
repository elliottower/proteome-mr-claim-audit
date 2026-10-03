# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1"]
# ///
"""Why Q4 differs between PubMed and Europe PMC on 2014-2018: term-pair hit counts only."""
import json, pathlib, time
import httpx
D_PM = ' AND ("2014/01/01"[dp] : "2018/12/31"[dp])'
D_EP = ' AND FIRST_PDATE:[2014-01-01 TO 2018-12-31] AND SRC:MED'
PAIRS = {
 "colocali* alone": ('colocali*[tiab]', 'TITLE_ABS:colocali*'),
 "colocalization|colocalisation|colocalized|colocalised|colocalize|colocalizes|colocalizing": (
     '(colocalization[tiab] OR colocalisation[tiab] OR colocalized[tiab] OR colocalised[tiab] OR colocalize[tiab] OR colocalizes[tiab] OR colocalizing[tiab])',
     '(TITLE_ABS:colocalization OR TITLE_ABS:colocalisation OR TITLE_ABS:colocalized OR TITLE_ABS:colocalised OR TITLE_ABS:colocalize OR TITLE_ABS:colocalizes OR TITLE_ABS:colocalizing)'),
 "proteom* alone": ('proteom*[tiab]', 'TITLE_ABS:proteom*'),
 "colocali* AND proteom*": ('colocali*[tiab] AND proteom*[tiab]', 'TITLE_ABS:colocali* AND TITLE_ABS:proteom*'),
 "SMR alone": ('SMR[tiab]', 'TITLE_ABS:SMR'),
 "SMR AND proteom*": ('SMR[tiab] AND proteom*[tiab]', 'TITLE_ABS:SMR AND TITLE_ABS:proteom*'),
 "colocali* AND plasma protein(s)": ('colocali*[tiab] AND "plasma protein*"[tiab]', 'TITLE_ABS:colocali* AND (TITLE_ABS:"plasma protein" OR TITLE_ABS:"plasma proteins")'),
 "plasma protein* alone": ('"plasma protein*"[tiab]', '(TITLE_ABS:"plasma protein" OR TITLE_ABS:"plasma proteins")'),
 "protein* alone (1 yr 2018)": None,
}
out = {}
with httpx.Client(timeout=90) as c:
    for k, v in PAIRS.items():
        if v is None:
            continue
        pm, ep = v
        r = c.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params={"db": "pubmed", "term": pm + D_PM, "retmode": "json", "retmax": 0})
        res = r.json()["esearchresult"]
        n_pm = int(res["count"])
        time.sleep(0.5)
        r = c.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search", params={"query": ep + D_EP, "format": "json", "resultType": "idlist", "pageSize": 1, "synonym": "false"})
        out[k] = {"pubmed": n_pm, "epmc_med": r.json()["hitCount"], "pubmed_translation": res.get("querytranslation", "")[:300]}
        time.sleep(0.4)
pathlib.Path(__file__).with_suffix(".json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
