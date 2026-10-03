# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1"]
# ///
"""Assemble the prospective negative-control set from PubMed, before the freeze.

Five strata of records that are ineligible by construction, each drawn from a PubMed query
restricted to publication dates 2014–2018 (before the census window). From each query's PMIDs,
sorted, 10 are drawn with random.Random(20261001), after removing the development abstracts
and the known items. Only PMIDs and titles are retrieved (ESummary); no abstract is fetched or
read, and no record is sent to any prompt. The set is run once, with the frozen eligibility
prompt, after the freeze, and it is never used to revise a prompt.

    non_protein_mr          MR of a non-protein exposure
    observational_proteomics plasma or serum proteomics with no genetic term
    mr_review               reviews of MR
    pqtl_without_mr         pQTL mapping with no MR, causal or SMR term
    non_human_pqtl          protein or proteome QTL studies in animals or plants

Output: search/negative_controls.jsonl (pmid, stratum, title) and
search/negative_controls_meta.json (queries, hit counts, seed, date). No email or other
identifier is sent.

Usage: uv run scripts/assemble_negative_controls.py
"""

import datetime
import json
import pathlib
import random
import re
import time

import httpx

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
OUT = EXP / "search" / "negative_controls.jsonl"
META = EXP / "search" / "negative_controls_meta.json"
ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
SEED = 20261001
PER_STRATUM = 10
DATE = '"2014/01/01"[dp] : "2018/12/31"[dp]'
STRATA = {
    "non_protein_mr": '"Mendelian randomization"[tiab] AND ("body mass index"[tiab] OR '
                      'alcohol[tiab] OR smoking[tiab] OR education[tiab]) NOT (protein*[tiab] '
                      'OR proteom*[tiab] OR pQTL*[tiab]) NOT Review[pt]',
    "observational_proteomics": '(proteomic*[tiab] OR "plasma proteom*"[tiab]) AND '
                                '(plasma[tiab] OR serum[tiab]) AND (cohort[tiab] OR '
                                '"case-control"[tiab]) NOT (Mendelian[tiab] OR genetic*[tiab] '
                                'OR QTL*[tiab] OR GWAS[tiab] OR variant*[tiab]) NOT Review[pt]',
    "mr_review": '"Mendelian randomization"[tiab] AND Review[pt]',
    "pqtl_without_mr": '(pQTL*[tiab] OR "protein quantitative trait"[tiab]) NOT '
                       '(Mendelian[tiab] OR causal*[tiab] OR SMR[tiab]) NOT Review[pt]',
    "non_human_pqtl": '(proteom*[tiab] OR "protein level*"[tiab] OR pQTL*[tiab]) AND (QTL*[tiab] '
                      'OR "quantitative trait"[tiab]) AND (mice[tiab] OR mouse[tiab] OR rat[tiab] '
                      'OR cattle[tiab] OR pig*[tiab] OR maize[tiab] OR Arabidopsis[tiab] OR '
                      'wheat[tiab] OR rice[tiab]) NOT humans[mh]',
}


class NegativeControlError(Exception):
    """A query returned too few records, or the output already exists."""


def excluded_pmids() -> set[str]:
    dev = {json.loads(l)["pmid"] for l in (EXP / "prompts" / "dev_abstracts.jsonl")
           .read_text().splitlines() if l.strip()}
    known = set(re.findall(r"^\| \d+ \| (\d+) \|", (EXP / "search" / "known_items.md")
                           .read_text(), re.MULTILINE))
    return dev | known


def main() -> None:
    if OUT.exists():
        raise NegativeControlError(f"{OUT} exists; the set is assembled once")
    skip = excluded_pmids()
    rng = random.Random(SEED)
    rows, meta = [], {"seed": SEED, "per_stratum": PER_STRATUM, "date_limit": DATE,
                      "retrieved_utc": datetime.datetime.now(datetime.UTC).isoformat(
                          timespec="seconds"), "excluded_pmids": len(skip), "strata": {}}
    with httpx.Client(timeout=60) as client:
        for stratum, query in STRATA.items():
            term = f"({query}) AND {DATE}"
            r = client.get(ESEARCH, params={"db": "pubmed", "term": term, "retmax": 10000,
                                            "retmode": "json"})
            r.raise_for_status()
            res = r.json()["esearchresult"]
            ids = sorted((p for p in res["idlist"] if p not in skip), key=int)
            if len(ids) < PER_STRATUM:
                raise NegativeControlError(f"{stratum}: {len(ids)} records")
            picked = rng.sample(ids, PER_STRATUM)
            time.sleep(0.4)
            s = client.get(ESUMMARY, params={"db": "pubmed", "id": ",".join(picked),
                                             "retmode": "json"})
            s.raise_for_status()
            summ = s.json()["result"]
            for pmid in picked:
                rows.append({"pmid": pmid, "stratum": stratum, "title": summ[pmid]["title"]})
            meta["strata"][stratum] = {"query": term, "count": int(res["count"]),
                                       "ids_returned": len(res["idlist"]),
                                       "eligible_for_draw": len(ids)}
            time.sleep(0.4)
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    META.write_text(json.dumps(meta, indent=1))
    print(json.dumps({k: v["count"] for k, v in meta["strata"].items()}), len(rows))


if __name__ == "__main__":
    main()
