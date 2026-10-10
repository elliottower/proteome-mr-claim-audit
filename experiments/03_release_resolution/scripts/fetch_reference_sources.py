# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1"]
# ///
"""Fetch the documents the two reference tables of the release-resolution plan are built from
(experiments/03_release_resolution/PREREG.md, §Study design, reference tables).

Three kinds, all listed in `reference/reference_table_sources.json`:

- `documents`: a resource's documentation page, data-portal listing or manifest, at a fixed URL.
  An entry with `auth` sends the named credential, read from the environment and never written,
  as a bearer token.
- `linked`: a manifest fetched only from the URL its documentation page states. The pattern
  must match exactly one distinct URL in the stored page; `query` is appended to it (a Dropbox
  link is documented with `dl=0` and served with `dl=1`). Both URLs are recorded.
- `gwas_catalog`: the GWAS Catalog's study records for each PubMed identifier that is the source
  of exactly one row of Paper 1's dictionary, every page.

Everything is stored under an ignored folder (it may hold third-party text) with a manifest of
URL, access date (UTC), byte count and sha256, written after each file, so a stopped run resumes
and a stored file is never fetched again. No request carries an e-mail address and none
imitates a browser. A request is tried three times, 60 seconds apart.

Usage:
    uv run scripts/fetch_reference_sources.py --sources <json> --dictionary <csv> --raw <dir>
"""

import argparse
import collections
import csv
import datetime
import hashlib
import json
import os
import pathlib
import re
import time

import httpx

PMID = re.compile(r"PMID:\s*(\d+)", re.I)


class FetchError(Exception):
    """A documented link is missing or ambiguous, or a request keeps failing."""


def single_row_pmids(dictionary: list[dict]) -> list[str]:
    counts = collections.Counter(p for r in dictionary
                                 for p in set(PMID.findall(r["source_identifier"])))
    return sorted((p for p, n in counts.items() if n == 1), key=int)


def documented_link(page: str, pattern: str) -> str:
    found = sorted(set(re.findall(pattern, page)))
    if len(found) != 1:
        raise FetchError(f"pattern {pattern!r} matches {len(found)} distinct URLs")
    return found[0]


class Store:
    def __init__(self, raw: pathlib.Path, client, today: datetime.date, sleep=time.sleep):
        self.raw, self.client, self.today, self.sleep = raw, client, today, sleep
        raw.mkdir(parents=True, exist_ok=True)
        path = raw / "manifest.json"
        self.manifest = json.loads(path.read_text()) if path.exists() else {}

    def get(self, key: str, url: str, headers: dict | None = None, **extra) -> bytes:
        if key in self.manifest:
            return (self.raw / key).read_bytes()
        for attempt in range(3):
            try:
                r = self.client.get(url, headers=headers or {})
                r.raise_for_status()
                break
            except httpx.HTTPError as e:
                if attempt == 2:
                    raise FetchError(f"{key}: {url}: {e}") from e
                self.sleep(60)
        (self.raw / key).write_bytes(r.content)
        self.manifest[key] = {"url": url, "access_date": self.today.isoformat(),
                              "bytes": len(r.content), "sha256": hashlib.sha256(r.content).hexdigest(),
                              **extra}
        (self.raw / "manifest.json").write_text(json.dumps(self.manifest, indent=1, sort_keys=True)
                                                + "\n")
        return r.content


def fetch_all(store: Store, sources: dict, dictionary: list[dict]) -> dict:
    for d in sources["documents"]:
        headers = {"Authorization": f"Bearer {os.environ[d['auth']]}"} if d.get("auth") else None
        store.get(d["key"], d["url"], headers)
    for d in sources["linked"]:
        page = (store.raw / d["from"]).read_text(errors="replace")
        documented = documented_link(page, d["pattern"])
        url = f"{documented}?{d['query']}" if d.get("query") else documented
        store.get(d["key"], url, url_as_documented=documented, found_in=d["from"])
    for pmid in single_row_pmids(dictionary):
        page, pages = 0, 1
        while page < pages:
            url = sources["gwas_catalog"]["url"].format(pmid=pmid, page=page)
            body = store.get(f"gwas_catalog_pmid{pmid}_page{page}", url, pubmed_id=pmid)
            pages = json.loads(body).get("page", {}).get("totalPages", 1)
            page += 1
    return store.manifest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", type=pathlib.Path, required=True)
    ap.add_argument("--dictionary", type=pathlib.Path, required=True)
    ap.add_argument("--raw", type=pathlib.Path, required=True)
    a = ap.parse_args()
    sources = json.loads(a.sources.read_text())
    with a.dictionary.open(newline="") as fh:
        dictionary = list(csv.DictReader(fh))
    today = datetime.datetime.now(datetime.UTC).date()
    with httpx.Client(timeout=300, follow_redirects=True) as client:
        manifest = fetch_all(Store(a.raw, client, today), sources, dictionary)
    print(json.dumps({"files": len(manifest), "bytes": sum(m["bytes"] for m in manifest.values())},
                     indent=1))


if __name__ == "__main__":
    main()
