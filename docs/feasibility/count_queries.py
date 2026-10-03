"""Outcome-blind feasibility: result COUNTS only for the registered census queries.
No titles, abstracts or records are printed or stored. PubMed E-utilities and Europe PMC REST;
no email or personal identifier is sent."""
import json, datetime, time, urllib.parse, urllib.request

MR = '("Mendelian Randomization Analysis"[Mesh] OR "Mendelian randomization"[tiab] OR "Mendelian randomisation"[tiab])'
PROT = '(proteome-wide[tiab] OR "proteome wide"[tiab] OR protein-wide[tiab] OR proteomic*[tiab] OR "plasma proteom*"[tiab] OR "circulating proteom*"[tiab] OR "plasma protein*"[tiab] OR "serum protein*"[tiab] OR "circulating protein*"[tiab] OR pQTL[tiab] OR pQTLs[tiab] OR "protein quantitative trait*"[tiab] OR "protein QTL*"[tiab] OR "genetically proxied protein*"[tiab] OR "genetically predicted protein*"[tiab] OR "genetically predicted plasma protein*"[tiab])'
PLAT = '(SomaScan[tiab] OR SomaLogic[tiab] OR Olink[tiab] OR Fenland[tiab] OR "UKB-PPP"[tiab] OR "UK Biobank Pharma Proteomics"[tiab] OR deCODE[tiab] OR SCALLOP[tiab] OR "INTERVAL study"[tiab] OR ARIC[tiab])'
TARGET = '("drug target*"[tiab] OR "therapeutic target*"[tiab] OR druggable[tiab] OR repurpos*[tiab] OR "target prioriti*"[tiab] OR "therapeutic prioriti*"[tiab] OR "drug-target MR"[tiab])'
LOCUS = '("summary-data-based Mendelian randomization"[tiab] OR SMR[tiab] OR colocali*[tiab] OR "cis-MR"[tiab] OR "cis Mendelian randomization"[tiab])'
PQTLB = '(pQTL[tiab] OR pQTLs[tiab] OR "protein quantitative trait*"[tiab] OR "protein QTL*"[tiab] OR "plasma protein*"[tiab] OR proteom*[tiab])'
DATE = '("2020/01/01"[dp] : "2025/12/31"[dp])'
Q = {"Q1": f"{MR} AND {PROT} AND {DATE}", "Q2": f"{MR} AND {PLAT} AND {DATE}",
     "Q3": f"{TARGET} AND {PQTLB} AND {DATE}", "Q4": f"{LOCUS} AND {PQTLB} AND {DATE}"}
EU = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

def pubmed_ids(term: str) -> list[str]:
    ids, start = [], 0
    while True:
        url = EU + "?" + urllib.parse.urlencode({"db": "pubmed", "term": term, "retmode": "json", "retmax": 9999, "retstart": start})
        r = json.load(urllib.request.urlopen(url, timeout=60))["esearchresult"]
        ids += r["idlist"]; start += 9999; time.sleep(0.5)
        if start >= int(r["count"]): return ids

def main() -> None:
    out = {"date": datetime.date.today().isoformat(), "window": "2020-01-01..2025-12-31", "note": "counts only; no record content read", "pubmed": {}}
    union = set()
    for k, q in Q.items():
        ids = pubmed_ids(q); union |= set(ids)
        out["pubmed"][k] = {"query": q, "count": len(ids)}
    out["pubmed"]["union_unique_pmids"] = len(union)
    json.dump(out, open("query_counts_2026-09-30.json", "w"), indent=2)
    print({k: v["count"] for k, v in out["pubmed"].items() if isinstance(v, dict)}, "union", len(union))

if __name__ == "__main__":
    main()
