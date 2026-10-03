"""Known-item recall check for the registered PubMed queries Q1-Q4 (PREREG.md, Data collection procedures).

For each known item and each query, PubMed E-utilities esearch is run on `(<query>) AND <PMID>[uid]` and only
the hit count is stored. Item metadata (title, journal, dates, DOI) come from esummary; no abstract is fetched.
No email or other personal identifier is sent. Output: known_item_recall_2026-09-30.json next to this file.
"""

import datetime
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().with_name("known_item_recall_2026-09-30.json")
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

MR = '("Mendelian Randomization Analysis"[Mesh] OR "Mendelian randomization"[tiab] OR "Mendelian randomisation"[tiab])'
PROT = ('(proteome-wide[tiab] OR "proteome wide"[tiab] OR protein-wide[tiab] OR proteomic*[tiab] OR "plasma proteom*"[tiab]'
        ' OR "circulating proteom*"[tiab] OR "plasma protein*"[tiab] OR "serum protein*"[tiab] OR "circulating protein*"[tiab]'
        ' OR pQTL[tiab] OR pQTLs[tiab] OR "protein quantitative trait*"[tiab] OR "protein QTL*"[tiab]'
        ' OR "genetically proxied protein*"[tiab] OR "genetically predicted protein*"[tiab]'
        ' OR "genetically predicted plasma protein*"[tiab])')
PLAT = ('(SomaScan[tiab] OR SomaLogic[tiab] OR Olink[tiab] OR Fenland[tiab] OR "UKB-PPP"[tiab]'
        ' OR "UK Biobank Pharma Proteomics"[tiab] OR deCODE[tiab] OR SCALLOP[tiab] OR "INTERVAL study"[tiab] OR ARIC[tiab])')
TARGET = ('("drug target*"[tiab] OR "therapeutic target*"[tiab] OR druggable[tiab] OR repurpos*[tiab]'
          ' OR "target prioriti*"[tiab] OR "therapeutic prioriti*"[tiab] OR "drug-target MR"[tiab])')
LOCUS = ('("summary-data-based Mendelian randomization"[tiab] OR SMR[tiab] OR colocali*[tiab] OR "cis-MR"[tiab]'
         ' OR "cis Mendelian randomization"[tiab])')
PQTLB = ('(pQTL[tiab] OR pQTLs[tiab] OR "protein quantitative trait*"[tiab] OR "protein QTL*"[tiab]'
         ' OR "plasma protein*"[tiab] OR proteom*[tiab])')
GEN = (f'({MR} OR pQTL[tiab] OR pQTLs[tiab] OR "protein quantitative trait*"[tiab] OR "genetically predicted"[tiab]'
       ' OR "genetically proxied"[tiab] OR "cis-MR"[tiab])')
DATE = '("2019/01/01"[dp] : "2025/12/31"[dp])'
QUERIES = {
    "Q1": f"{MR} AND {PROT} AND {DATE}",
    "Q2": f"{MR} AND {PLAT} AND {DATE}",
    "Q3": f"{TARGET} AND {PQTLB} AND {GEN} AND {DATE}",
    "Q4": f"{LOCUS} AND {PQTLB} AND {DATE}",
}

# PMID -> where the item was found. Identified by title and metadata only.
KNOWN_ITEMS = {
    "32895551": "Chen L 2022 and Yoshikawa 2024 reference lists; foreknowledge item 7",
    "36253349": "project foreknowledge item 7 (Chen L 2022, Nat Commun)",
    "39702585": "project foreknowledge item 7 (Yoshikawa 2024, Commun Biol)",
    "31208196": "Zheng 2020 reference list (Europe PMC references endpoint)",
    "36864689": "Yoshikawa 2024 reference list; Zheng 2020 citing papers (Europe PMC)",
    "38576019": "Yoshikawa 2024 reference list",
    "38049731": "Yoshikawa 2024 reference list",
    "35300523": "OpenAlex scoop query D (2026-09-30 rerun), title only",
    "36388766": "OpenAlex scoop query D (2026-09-30 rerun), title only",
    "36510323": "PubMed scoop query pm_1 (2026-09-30 rerun), title only",
    "36736436": "PubMed scoop query pm_1 (2026-09-30 rerun), title only",
    "37652020": "PubMed scoop query pm_1 (2026-09-30 rerun), title only",
    "37726845": "PubMed scoop query pm_1 (2026-09-30 rerun), title only",
    "37429843": "PubMed scoop query pm_1 (2026-09-30 rerun), title only",
    "39068416": "PubMed scoop query pm_1 (2026-09-30 rerun), title only",
    "41247789": "PubMed scoop query pm_1 (2026-09-30 rerun), title only",
    "41286868": "PubMed scoop query pm_1 (2026-09-30 rerun), title only",
    "37996402": "web search result (2026-09-30), title only",
    "36280454": "Zheng 2020 citing papers (Europe PMC citations endpoint), title only",
    "34758976": "Zheng 2020 citing papers (Europe PMC citations endpoint), title only",
    "38184718": "Zheng 2020 citing papers (Europe PMC citations endpoint), title only",
    "40037332": "Zheng 2020 citing papers (Europe PMC citations endpoint), title only",
    "39806440": "Zheng 2020 citing papers (Europe PMC citations endpoint), title only",
    "39541108": "Zheng 2020 citing papers (Europe PMC citations endpoint), title only",
    "38762700": "Zheng 2020 citing papers (Europe PMC citations endpoint), title only",
}
CONTROL_PMID = "32895551"


def get_json(endpoint: str, params: dict) -> dict:
    url = EUTILS + endpoint + "?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception:
            time.sleep(2 + 2 * attempt)
    raise RuntimeError(f"E-utilities failed: {endpoint} {params}")


def count(term: str) -> int:
    time.sleep(0.4)
    return int(get_json("esearch.fcgi", {"db": "pubmed", "term": term, "retmode": "json", "retmax": 0})["esearchresult"]["count"])


def main() -> None:
    summ = get_json("esummary.fcgi", {"db": "pubmed", "id": ",".join(KNOWN_ITEMS), "retmode": "json"})["result"]
    out = {
        "run_date": datetime.date.today().isoformat(),
        "note": "hit counts of (query) AND PMID[uid]; no abstract fetched or read",
        "queries": QUERIES,
        "control_uid_only_count": count(f"{CONTROL_PMID}[uid]"),
        "items": {},
    }
    for pmid, source in KNOWN_ITEMS.items():
        s = summ[pmid]
        doi = next((a["value"] for a in s.get("articleids", []) if a["idtype"] == "doi"), None)
        hits = {q: count(f"({term}) AND {pmid}[uid]") for q, term in QUERIES.items()}
        out["items"][pmid] = {
            "source": source,
            "title": s.get("title"),
            "journal": s.get("fulljournalname"),
            "pubdate": s.get("pubdate"),
            "epubdate": s.get("epubdate"),
            "doi": doi,
            "pubtype": s.get("pubtype"),
            "counts": hits,
            "retrieved_by": [q for q, n in hits.items() if n > 0],
        }
        # write after every item so an interrupted run keeps what it has
        OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    failures = [p for p, v in out["items"].items() if not v["retrieved_by"]]
    out["recall_failures"] = failures
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"{len(KNOWN_ITEMS)} items; failures: {failures}")


if __name__ == "__main__":
    main()
