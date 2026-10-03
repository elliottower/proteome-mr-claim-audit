# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "numpy==2.5.3", "pydantic==2.13.5", "rapidfuzz==3.14.6"]
# ///
"""Record metadata of the eligible families, for the secondaries that read it
(scripts/registry_secondaries.py: citation of the earlier claim, source overlap, document class
and journals) and for the collected country variable. No model is called.

Two steps.

`fetch` (after the registry is assembled; needs the frozen plan, unless `--smoke` runs it on
records that are all first public before 2019). Every registry and preprint
(dating) record of every eligible family is looked up in OpenAlex by DOI, or by PMID when it has
no DOI, or by its OpenAlex identifier when the search returned it from OpenAlex only
(`filter=doi:` / `pmid:` / `openalex:`, 40 per request, `select=id,doi,ids,referenced_works,
authorships`). Every response is stored and checkpointed as in scripts/run_search.py. No email
address is sent; an OpenAlex API key, if OPEN_ALEX_API_KEY is set, travels in the Authorization
header and is never written.

`build`. One row per record of an eligible family (families.json, families_meta.json):

    kind                  the record's document class
    search_sources        the sources (pubmed, epmc, openalex) whose registered queries returned
                          the record: the source of each of its query streams in the search's
                          screening_records.jsonl; a PubMed record fetched only because another
                          source returned its PMID has no PubMed stream
    chase_round           the citation-chasing round that added the record; empty for a record
                          of the search
    journal               the journal title of the screening record
    openalex_ids          the OpenAlex works of the record: the looked-up work and any OpenAlex
                          member of the screening record
    has_reference_list    whether the looked-up work has a non-empty `referenced_works`; null
                          when no work was found
    referenced_works      the OpenAlex identifiers the looked-up work cites
    first_author_country  the `country_code` of the first listed institution of the work's
                          first author (the first authorship with `author_position` "first");
                          when that authorship lists no institution, the first of its
                          `countries`; null otherwise

Country is a collected variable with no planned analysis: the country code of the first listed
institution of the first author, never nationality. No table of it is generated, it enters no
registered outcome and it does not appear in the paper, because it is confounded with the
journal and with access to public summary data. A table is made only if a reviewer requests one
after submission, and is then reported as requested.

Usage:
    uv run scripts/record_metadata.py fetch --inputs <registry dir> --screening <screening_records.jsonl> [...]
    uv run scripts/record_metadata.py build --inputs <registry dir> --screening <search screening_records.jsonl> \\
        [--chase-screening <round 1 screening_records.jsonl> <round 2 ...>] --openalex <fetch run dir>
"""

import argparse
import collections
import datetime
import json
import pathlib
from collections.abc import Mapping

import httpx

import citation_chase as cc
import run_search as rs
from assemble_screening_set import norm_doi, norm_pmid
from registry_secondaries import RecordMeta

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
RAW = EXP / "outputs" / "raw" / "openalex_metadata"
SELECT = "id,doi,ids,referenced_works,authorships"
BATCH = 40
SOURCES = ("pubmed", "epmc", "openalex")


class RecordMetadataError(Exception):
    """An input is missing, an output exists, or a smoke run holds a record of the window."""


def refuse_window_records(records: list[Mapping]) -> None:
    """A smoke run looks up no record first public in 2019 or later."""
    late = sorted(r["record_id"] for r in records
                  if datetime.date.fromisoformat(r["first_public"]["value"])
                  >= cc.PUBLISHED_FROM)
    if late:
        raise RecordMetadataError(f"--smoke: records first public in the registered window: "
                                  f"{late[:5]}")


def read_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def family_record_ids(inputs: pathlib.Path) -> tuple[dict[str, list[str]], dict[str, dict]]:
    """(family -> its record ids, eligible-family metadata) from the registry assembly."""
    families = json.loads((inputs / "families.json").read_text())["families"]
    meta = json.loads((inputs / "families_meta.json").read_text())
    return {f: families[f] for f in meta}, meta


def lookup_keys(record: Mapping) -> tuple[str, str] | None:
    """The OpenAlex filter field and value that finds a screening record."""
    if record.get("doi"):
        return "doi", norm_doi(record["doi"])
    if record.get("pmid"):
        return "pmid", norm_pmid(record["pmid"])
    openalex = [m.split(":", 1)[1] for m in record.get("member_ids", [])
                if m.startswith("openalex:")]
    return ("openalex", openalex[0]) if openalex else None


def fetch(client: httpx.Client, run_dir: pathlib.Path, records: list[Mapping]) -> dict:
    """Store the OpenAlex works of the records; every response is kept and checkpointed."""
    run_dir.mkdir(parents=True, exist_ok=True)
    by_field: dict[str, list[str]] = collections.defaultdict(list)
    for r in records:
        key = lookup_keys(r)
        if key:
            by_field[key[0]].append(key[1])
    counts = {"records": len(records), "records_without_an_identifier": sum(
        lookup_keys(r) is None for r in records)}
    for field, values in sorted(by_field.items()):
        for i, batch in enumerate(cc.batches(sorted(set(values)), BATCH), 1):
            cc.paged(client, run_dir, f"works_{field}_{i:04d}", f"{field}:{'|'.join(batch)}",
                     SELECT)
        counts[f"looked_up_by_{field}"] = len(set(values))
    return counts


def stored_works(run_dir: pathlib.Path) -> list[dict]:
    manifest = rs.read_manifest(run_dir)
    streams = sorted({l["stream"] for l in manifest if l.get("status") == 200})
    return [w for s in streams for body in rs.stored_pages(manifest, run_dir, "openalex", s)
            for w in json.loads(body)["results"]]


def first_author_country(work: Mapping) -> str | None:
    first = next((a for a in work.get("authorships") or []
                  if a.get("author_position") == "first"), None)
    if first is None:
        return None
    institutions = first.get("institutions") or []
    if institutions:
        return institutions[0].get("country_code") or None
    countries = first.get("countries") or []
    return countries[0] if countries else None


def index_works(works: list[dict]) -> dict[tuple[str, str], dict]:
    """(field, value) -> work, for the three lookup fields."""
    out: dict[tuple[str, str], dict] = {}
    for w in works:
        ids = w.get("ids") or {}
        out[("openalex", cc.short_id(w["id"]))] = w
        if w.get("doi"):
            out.setdefault(("doi", norm_doi(w["doi"])), w)
        if ids.get("pmid"):
            out.setdefault(("pmid", norm_pmid(ids["pmid"])), w)
    return out


def build(families: Mapping[str, list[str]], search: list[Mapping], chase: list[list[Mapping]],
          works: list[dict]) -> list[RecordMeta]:
    """One `RecordMeta` per record of an eligible family. `chase` holds the screening records
    of each citation-chasing round, in round order."""
    by_id: dict[str, tuple[Mapping, int | None]] = {r["record_id"]: (r, None) for r in search}
    for n, records in enumerate(chase, 1):
        for r in records:
            by_id.setdefault(r["record_id"], (r, n))
    found = index_works(works)
    out = []
    for rid in sorted({r for ids in families.values() for r in ids}):
        if rid not in by_id:
            raise RecordMetadataError(f"record {rid} is in no screening set")
        record, chase_round = by_id[rid]
        key = lookup_keys(record)
        work = found.get(key) if key else None
        members = [m.split(":", 1)[1] for m in record.get("member_ids", [])
                   if m.startswith("openalex:")]
        refs = [cc.short_id(x) for x in (work or {}).get("referenced_works") or []]
        sources = () if chase_round is not None else tuple(
            s for s in SOURCES if any(st.startswith(f"{s}/") for st in record["streams"]))
        out.append(RecordMeta(
            record_id=rid, kind=record["kind"], search_sources=sources,
            chase_round=chase_round, journal=record.get("journal"),
            openalex_ids=tuple(sorted({*members, *([cc.short_id(work["id"])] if work else [])})),
            has_reference_list=None if work is None else bool(refs),
            referenced_works=tuple(sorted(set(refs))),
            first_author_country=first_author_country(work) if work else None))
    return out


def write_once(path: pathlib.Path, text: str) -> None:
    if path.exists():
        raise RecordMetadataError(f"{path} exists; archive it before rerunning")
    path.write_text(text)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("fetch", "build"):
        s = sub.add_parser(name)
        s.add_argument("--inputs", type=pathlib.Path, required=True,
                       help="the registry assembly directory (families.json, families_meta.json)")
        s.add_argument("--screening", type=pathlib.Path, required=True)
        s.add_argument("--chase-screening", type=pathlib.Path, nargs="*", default=[])
        if name == "fetch":
            s.add_argument("--smoke", action="store_true",
                           help="before the freeze: records first public before 2019 only")
        if name == "build":
            s.add_argument("--openalex", type=pathlib.Path, required=True)
    a = ap.parse_args()
    families, meta = family_record_ids(a.inputs)
    search = read_jsonl(a.screening)
    chase = [read_jsonl(p) for p in a.chase_screening]
    wanted = {r for ids in families.values() for r in ids}
    if a.command == "fetch":
        records = [r for rs_ in [search, *chase] for r in rs_ if r["record_id"] in wanted]
        if a.smoke:
            refuse_window_records(records)
        else:
            rs.check_frozen()
        run_dir = RAW / a.inputs.name
        with httpx.Client(timeout=120) as client:
            counts = fetch(client, run_dir, records)
        (run_dir / "counts.json").write_text(json.dumps(counts, indent=1))
        print(json.dumps({"run": str(run_dir), **counts}, indent=1))
        return
    rows = build(families, search, chase, stored_works(a.openalex))
    write_once(a.inputs / "record_metadata.jsonl",
               "".join(r.model_dump_json() + "\n" for r in rows))
    print(json.dumps({"records": len(rows),
                      "with_an_openalex_work": sum(r.has_reference_list is not None
                                                   for r in rows),
                      "with_a_reference_list": sum(bool(r.has_reference_list) for r in rows),
                      "with_a_first_author_country": sum(r.first_author_country is not None
                                                         for r in rows)}, indent=1))


if __name__ == "__main__":
    main()
