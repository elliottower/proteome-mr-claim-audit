# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "numpy==2.5.3", "pydantic==2.13.5", "rapidfuzz==3.14.6"]
# ///
"""How many of the papers behind repeated pairs have a full text that could be read
(PREREG.md log, 2026-10-08): planning for a possible follow-up stage, made after the outcomes
of stage 5 were seen. Metadata only. No full text and no supplementary file is fetched, no
registered result changes, and no third-party text is written to the result.

Two sets of records, from the claim file of an assembly and the registered functions:
    blocking     records with a dataset mention that blocks a pair unresolved under H2 or
                 under H2b (the union; scripts/h2_unresolved_diagnostic.py `blocks`)
    multi        every record with a claim in a pair that two or more families report

`fetch` asks two services for status fields only, and stores every response as it arrives
(a stored response is not asked for again):
    Europe PMC   for records with a PMID: `resultType=lite`, which carries no abstract
                 (isOpenAccess, inEPMC, inPMC, pmcid, hasPDF, hasSuppl)
    OpenAlex     for every record, by DOI, else PMID, else OpenAlex identifier:
                 `select=id,doi,ids,open_access`
No e-mail address is sent; an OpenAlex key, if OPEN_ALEX_API_KEY is set, travels in the
Authorization header and is never written.

`count` reads the stored responses and the full texts on disk and writes one JSON. Each record
takes the first category that fits:
    full_text_on_disk                     a stored rendered full text (stage 4 coding)
    open_access_full_text_in_europe_pmc   Europe PMC flags open access and gives a PMCID
    full_text_in_europe_pmc_not_flagged_open_access
                                          a PMCID or `inEPMC`, without the open-access flag
    open_access_by_openalex_only          OpenAlex `open_access.is_oa`, no Europe PMC full text
    closed                                found, and none of the above
    no_status_found                       neither service returned the record
and, beside the category, whether Europe PMC lists supplementary files for it (`hasSuppl`).

Usage:
    uv run scripts/release_resolution_availability.py fetch --claims <registry_claims.jsonl> \\
        --records <screening_records.jsonl> [...] --raw <dir>
    uv run scripts/release_resolution_availability.py count --claims <registry_claims.jsonl> \\
        --records <screening_records.jsonl> [...] --fulltext <dir> [...] --raw <dir> --out <json>
"""

import argparse
import collections
import datetime
import hashlib
import json
import os
import pathlib

import httpx

from build_registry import RegistryClaim, build, pair_h2, pair_overlap
from dataset_relations import load_rows, map_name
from h2_unresolved_diagnostic import blocks, record_of
from record_metadata import lookup_keys

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
OPENALEX = "https://api.openalex.org/works"
SELECT = "id,doi,ids,open_access"
EPMC_BATCH, OPENALEX_BATCH = 50, 40
CATEGORIES = ("full_text_on_disk", "open_access_full_text_in_europe_pmc",
              "full_text_in_europe_pmc_not_flagged_open_access", "open_access_by_openalex_only",
              "closed", "no_status_found")


class AvailabilityError(Exception):
    """A response is not what was asked for, or an output exists."""


def record_sets(claims: list[RegistryClaim]) -> dict[str, set[str]]:
    rows = load_rows()
    registry = build(claims, rows)
    multi = {p for p, fams in registry.items() if len(fams) > 1}
    unresolved = {hyp: {p for p in multi if classify(registry[p]) == "unresolved"}
                  for hyp, classify in (("h2", pair_h2), ("h2b", pair_overlap))}
    out: dict[str, set[str]] = {"blocking": set(), "multi": set()}
    for c in claims:
        pair = (c.protein_id, c.outcome_id)
        if pair not in multi:
            continue
        out["multi"].add(record_of(c))
        for side, names in (("pqtl", c.pqtl_datasets), ("outcome", c.outcome_datasets)):
            for hyp in ("h2", "h2b"):
                if pair in unresolved[hyp] and any(
                        blocks(map_name(n, side, rows), hyp) for n in names):
                    out["blocking"].add(record_of(c))
    return out


def batches(values: list[str], size: int) -> list[list[str]]:
    return [values[i:i + size] for i in range(0, len(values), size)]


def stored(raw: pathlib.Path, name: str, get) -> dict:
    """The JSON body stored under `name`, asked for with `get` when it is not there yet."""
    path = raw / f"{name}.json"
    if not path.exists():
        body = get()
        partial = path.with_suffix(".partial")
        partial.write_text(json.dumps(body))
        partial.rename(path)
    return json.loads(path.read_text())


def fetch(client: httpx.Client, raw: pathlib.Path, records: list[dict]) -> dict:
    raw.mkdir(parents=True, exist_ok=True)
    pmids = sorted({str(r["pmid"]) for r in records if r.get("pmid")}, key=int)
    for i, batch in enumerate(batches(pmids, EPMC_BATCH), 1):
        query = "(" + " OR ".join(f"EXT_ID:{p}" for p in batch) + ") AND SRC:MED"

        def get(query=query) -> dict:
            r = client.get(EPMC, params={"query": query, "format": "json",
                                         "resultType": "lite", "pageSize": 100})
            r.raise_for_status()
            return r.json()

        stored(raw, f"europe_pmc_{i:04d}", get)
    key = os.environ.get("OPEN_ALEX_API_KEY")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    by_field: dict[str, list[str]] = collections.defaultdict(list)
    for r in records:
        found = lookup_keys(r)
        if found:
            by_field[found[0]].append(found[1])
    for field, values in sorted(by_field.items()):
        for i, batch in enumerate(batches(sorted(set(values)), OPENALEX_BATCH), 1):
            flt = f"{field}:{'|'.join(batch)}"

            def get(flt=flt) -> dict:
                r = client.get(OPENALEX, params={"filter": flt, "select": SELECT,
                                                 "per_page": 100}, headers=headers)
                r.raise_for_status()
                return r.json()

            stored(raw, f"openalex_{field}_{i:04d}", get)
    return {"records": len(records), "with_a_pmid": len(pmids),
            "openalex_lookups": {k: len(set(v)) for k, v in sorted(by_field.items())},
            "responses_stored": len(list(raw.glob("*.json")))}


def norm_doi(doi: str | None) -> str:
    return (doi or "").lower().removeprefix("https://doi.org/").strip()


def read_status(raw: pathlib.Path) -> tuple[dict[str, dict], dict[str, dict]]:
    """(Europe PMC lite results by PMID; OpenAlex open_access by `doi:<doi>`, `pmid:<pmid>`
    and `openalex:<id>`)."""
    epmc: dict[str, dict] = {}
    for path in sorted(raw.glob("europe_pmc_*.json")):
        for hit in json.loads(path.read_text())["resultList"]["result"]:
            if hit.get("pmid"):
                epmc[str(hit["pmid"])] = hit
    openalex: dict[str, dict] = {}
    for path in sorted(raw.glob("openalex_*.json")):
        for work in json.loads(path.read_text())["results"]:
            access = work.get("open_access") or {}
            ids = work.get("ids") or {}
            keys = [f"openalex:{work['id'].rsplit('/', 1)[-1]}"]
            if work.get("doi"):
                keys.append(f"doi:{norm_doi(work['doi'])}")
            if ids.get("pmid"):
                keys.append(f"pmid:{str(ids['pmid']).rsplit('/', 1)[-1]}")
            for k in keys:
                openalex.setdefault(k, access)
    return epmc, openalex


def status_of(record: dict, on_disk: set[str], epmc: dict[str, dict],
              openalex: dict[str, dict]) -> dict:
    """The availability of one record: its category and the flags it rests on."""
    hit = epmc.get(str(record.get("pmid"))) if record.get("pmid") else None
    found = lookup_keys(record)
    access = openalex.get(f"{found[0]}:{norm_doi(found[1]) if found[0] == 'doi' else found[1]}"
                          ) if found else None
    epmc_oa = bool(hit) and hit.get("isOpenAccess") == "Y" and bool(hit.get("pmcid"))
    epmc_text = bool(hit) and (bool(hit.get("pmcid")) or hit.get("inEPMC") == "Y")
    is_oa = bool(access) and bool(access.get("is_oa"))
    if record["record_id"] in on_disk:
        category = "full_text_on_disk"
    elif epmc_oa:
        category = "open_access_full_text_in_europe_pmc"
    elif epmc_text:
        category = "full_text_in_europe_pmc_not_flagged_open_access"
    elif is_oa:
        category = "open_access_by_openalex_only"
    elif hit or access is not None:
        category = "closed"
    else:
        category = "no_status_found"
    return {"category": category, "kind": record.get("kind"),
            "europe_pmc_record": bool(hit),
            "europe_pmc_lists_supplementary_files": (hit.get("hasSuppl") if hit else None),
            "openalex_record": access is not None,
            "openalex_oa_status": (access or {}).get("oa_status")}


def tally(ids: set[str], status: dict[str, dict]) -> dict:
    these = [status[i] for i in sorted(ids)]
    by = collections.Counter(s["category"] for s in these)
    suppl = collections.Counter(str(s["europe_pmc_lists_supplementary_files"]) for s in these)
    readable = sum(by[c] for c in CATEGORIES[:4])
    return {"records": len(these), "by_category": {c: by[c] for c in CATEGORIES},
            "with_a_full_text_on_disk_or_reachable": readable,
            "closed_or_no_status": len(these) - readable,
            "by_document_class": dict(sorted(collections.Counter(
                str(s["kind"]) for s in these).items())),
            "europe_pmc_lists_supplementary_files": {
                "yes": suppl["Y"], "no": suppl["N"],
                "no_europe_pmc_record_or_field": len(these) - suppl["Y"] - suppl["N"]},
            "supplementary_files_listed_by_category": dict(sorted(collections.Counter(
                s["category"] for s in these
                if s["europe_pmc_lists_supplementary_files"] == "Y").items())),
            "openalex_oa_status": dict(sorted(collections.Counter(
                str(s["openalex_oa_status"]) for s in these).items()))}


def read_records(paths: list[pathlib.Path]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for path in paths:
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                out.setdefault(r["record_id"], r)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("fetch", "count"):
        s = sub.add_parser(name)
        s.add_argument("--claims", type=pathlib.Path, required=True)
        s.add_argument("--records", type=pathlib.Path, nargs="+", required=True)
        s.add_argument("--raw", type=pathlib.Path, required=True)
        if name == "count":
            s.add_argument("--fulltext", type=pathlib.Path, nargs="+", required=True)
            s.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    claims = [RegistryClaim.model_validate_json(l) for l in a.claims.read_text().splitlines()
              if l.strip()]
    sets = record_sets(claims)
    records = read_records(a.records)
    wanted = [records[i] for i in sorted(sets["blocking"] | sets["multi"])]
    if a.command == "fetch":
        with httpx.Client(timeout=120) as client:
            print(json.dumps(fetch(client, a.raw, wanted), indent=1))
        return
    if a.out.exists():
        raise AvailabilityError(f"{a.out} exists; it is written once")
    pmid_of = {str(r["pmid"]): rid for rid, r in records.items() if r.get("pmid")}
    on_disk = {pmid_of[p.stem.removeprefix("pmid")] for folder in a.fulltext
               for p in folder.glob("pmid*.jsonl") if p.stem.removeprefix("pmid") in pmid_of}
    epmc, openalex = read_status(a.raw)
    status = {r["record_id"]: status_of(r, on_disk, epmc, openalex) for r in wanted}
    result = {
        "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "note": "post-results planning; metadata only; no full text or supplement fetched",
        "claims": {"path": str(a.claims),
                   "sha256": hashlib.sha256(a.claims.read_bytes()).hexdigest()},
        "raw_responses": {"folder": str(a.raw), "files": len(list(a.raw.glob("*.json")))},
        "papers_behind_unresolved_pairs": tally(sets["blocking"], status),
        "papers_behind_any_multi_family_pair": tally(sets["multi"], status),
        "papers_in_both_sets": len(sets["blocking"] & sets["multi"]),
        "records": {i: status[i] for i in sorted(status)}}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=1))


if __name__ == "__main__":
    main()
