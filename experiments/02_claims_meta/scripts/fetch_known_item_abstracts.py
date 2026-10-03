# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "pydantic==2.13.5"]
# ///
"""Fetch the known items' titles and abstracts for the eligibility-only check.

Reads the PMIDs from the table in search/known_items.md, fetches each record from PubMed
E-utilities (no email parameter, default user agent), and writes
outputs/known_items/known_items_abstracts.jsonl with pmid, title, abstract and the abstract's
sha256, in the layout run_extraction.py reads. Abstract sections are joined as in
fetch_dev_abstracts.py. Nothing is printed except counts.

With `--controls`, the same fetch for the 50 negative-control records of
search/negative_controls.jsonl, written to outputs/negative_controls/
negative_control_abstracts.jsonl. It runs only after the freeze (no abstract of these records is
fetched before it). A control record classed `no_abstract` (scripts/abstract_floor.py) is not
judged: it is written to negative_control_no_abstract.jsonl (PMID, title, abstract length) and
left out of negative_control_abstracts.jsonl.

Usage: uv run scripts/fetch_known_item_abstracts.py
       uv run scripts/fetch_known_item_abstracts.py --controls      (after the freeze)
"""

import argparse
import hashlib
import json
import pathlib
import re
import xml.etree.ElementTree as ET

import httpx
from pydantic import BaseModel

from abstract_floor import abstract_length, is_no_abstract
from run_search import check_frozen

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
KNOWN = EXP / "search" / "known_items.md"
OUT = EXP / "outputs" / "known_items" / "known_items_abstracts.jsonl"
CONTROLS = EXP / "search" / "negative_controls.jsonl"
CONTROLS_OUT = EXP / "outputs" / "negative_controls" / "negative_control_abstracts.jsonl"
CONTROLS_NO_ABSTRACT = CONTROLS_OUT.with_name("negative_control_no_abstract.jsonl")
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


class FetchError(Exception):
    """A known item could not be fetched or has no abstract."""


class KnownItem(BaseModel):
    pmid: str
    title: str
    abstract: str
    abstract_sha256: str


def text_of(el: ET.Element) -> str:
    return " ".join("".join(el.itertext()).split())


def pmids_from_table() -> list[str]:
    pmids = []
    for line in KNOWN.read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) > 2 and cells[0].isdigit() and re.fullmatch(r"\d{6,9}", cells[1]):
            pmids.append(cells[1])
    if not pmids:
        raise FetchError(f"no PMIDs found in {KNOWN}")
    return pmids


def parse(article: ET.Element, allow_no_abstract: bool = False) -> KnownItem:
    pmid = article.findtext(".//MedlineCitation/PMID")
    art = article.find(".//MedlineCitation/Article")
    if pmid is None or art is None:
        raise FetchError("record without PMID or Article")
    parts = []
    for node in art.findall("./Abstract/AbstractText"):
        label = node.get("Label")
        body = text_of(node)
        parts.append(f"{label}: {body}" if label else body)
    if not parts and not allow_no_abstract:
        raise FetchError(f"{pmid}: no abstract")
    abstract = "\n".join(parts)
    return KnownItem(pmid=pmid, title=text_of(art.find("./ArticleTitle")), abstract=abstract,
                     abstract_sha256=hashlib.sha256(abstract.encode()).hexdigest())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--controls", action="store_true",
                    help="fetch the negative-control records (after the freeze)")
    a = ap.parse_args()
    if a.controls:
        check_frozen()
        pmids = [json.loads(l)["pmid"] for l in CONTROLS.read_text().splitlines() if l.strip()]
        out = CONTROLS_OUT
        if out.exists():
            raise FetchError(f"{out} exists; the control abstracts are fetched once")
    else:
        pmids, out = pmids_from_table(), OUT
    with httpx.Client(timeout=60) as client:
        r = client.get(EFETCH, params={"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"})
        r.raise_for_status()
    root = ET.fromstring(r.text)
    items = {i.pmid: i for i in (parse(art, a.controls)
                                 for art in root.findall("./PubmedArticle"))}
    missing = [p for p in pmids if p not in items]
    if missing:
        raise FetchError(f"not returned by PubMed: {missing}")
    short = [p for p in pmids if is_no_abstract(items[p].abstract)]
    if short and not a.controls:
        raise FetchError(f"known items classed no_abstract: {short}")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for p in pmids:
            if p not in short:
                f.write(items[p].model_dump_json() + "\n")
    if a.controls:
        CONTROLS_NO_ABSTRACT.write_text("".join(json.dumps(
            {"pmid": p, "title": items[p].title,
             "abstract_length": abstract_length(items[p].abstract)}) + "\n" for p in short))
    print(f"{out}: {len(pmids) - len(short)} records written; no_abstract: {len(short)}")


if __name__ == "__main__":
    main()
