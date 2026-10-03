# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "numpy==2.5.3", "pydantic==2.13.5", "rapidfuzz==3.14.6"]
# ///
"""One round of citation chasing in OpenAlex: the backward and forward citations of the seed
papers that are not yet in the screening set.

Round 1 seeds are the screening records judged `eligible`, `eligible_count_not_stated` or
`uncertain` from the search, in either window (scripts/select_eligible.py); a later round's
seeds are the records the previous round added with one of those decisions. Chasing stops when
a round adds no such record, and after three rounds (`another_round`).

Only works whose OpenAlex publication date is 2019-01-01 or later are retrieved
(`from_publication_date`, on the cited and on the citing works): an earlier work cannot be first
public in either window.

Steps, every response stored and checkpointed as in run_search.py:

    seeds      the seed papers are found in OpenAlex by DOI, or by PMID when they have no DOI
               (`filter=doi:` / `filter=pmid:`, 40 per request)
    backward   the works in the seeds' `referenced_works` (`filter=openalex:`, 100 per request)
    forward    the works citing the seeds (`filter=cites:`, 40 seeds per request)
    pubmed     `efetch` for the PMIDs of the new works, for their PubMed abstracts

A cited or citing work is new when no record of the screening sets so far shares its OpenAlex
identifier, PMID, PMCID or DOI. The new works are deduplicated and written exactly as
assemble_screening_set.py writes a screening set. The keyword prefilter then gates them
(scripts/keyword_prefilter.py --gate): only the records it leaves unmarked go to GPT-6.1 Sol.
A new work classed `no_abstract` (scripts/abstract_floor.py) is written to no_abstract.jsonl
and reaches neither the gate nor its audit; a seed is never such a record.

No email address is sent. An OpenAlex API key, if OPEN_ALEX_API_KEY is set, travels in the
Authorization header and is never written.

Usage:
    uv run scripts/citation_chase.py --round 1 --seeds <eligible screening_records.jsonl> \\
        --known outputs/screening/<run>/screening_records.jsonl [--known ...]
"""

import argparse
import datetime
import hashlib
import json
import pathlib

import httpx

import assemble_screening_set as ass
import run_search as rs

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
RAW = EXP / "outputs" / "raw" / "citation_chase"
RAW_SMOKE = EXP / "outputs" / "raw" / "citation_chase_smoke"
OUT = EXP / "outputs" / "screening"
OUT_SMOKE = EXP / "outputs" / "screening_smoke"
MAX_ROUNDS = 3
SEED_BATCH = 40
WORK_BATCH = 100
SEED_SELECT = "id,doi,ids,referenced_works"
SMOKE_END = datetime.date(2018, 12, 31)
PUBLISHED_FROM = datetime.date(2019, 1, 1)


class ChaseError(Exception):
    """A round is out of range, or an output exists."""


def another_round(round_number: int, newly_eligible: int) -> bool:
    """Whether to chase again after a round that added `newly_eligible` eligible papers."""
    return newly_eligible > 0 and round_number < MAX_ROUNDS


def batches(items: list[str], size: int) -> list[list[str]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def short_id(openalex_id: str) -> str:
    return openalex_id.rstrip("/").rsplit("/", 1)[-1]


def known_identifiers(known: list[dict]) -> set[tuple[str, str]]:
    """(field, value) for every identifier of the screening records so far."""
    ids: set[tuple[str, str]] = set()
    for s in known:
        ids.update((f, s[f]) for f in ("pmid", "pmcid", "doi") if s.get(f))
        ids.update(("openalex", m.split(":", 1)[1]) for m in s.get("member_ids", [])
                   if m.startswith("openalex:"))
    return ids


def is_known(rec: ass.RetrievedRecord, known: set[tuple[str, str]]) -> bool:
    keys = [(f, getattr(rec, f)) for f in ("pmid", "pmcid", "doi") if getattr(rec, f)]
    if rec.source == "openalex":
        keys.append(("openalex", rec.source_id))
    return any(k in known for k in keys)


def paged(client: httpx.Client, run_dir: pathlib.Path, stream: str, flt: str,
          select: str) -> list[dict]:
    """Every work of an OpenAlex filter stream, from the stored pages."""
    rs.run_paged(client, run_dir, "openalex", stream, rs.OPENALEX,
                 {"filter": flt, "select": select, "per_page": rs.OPENALEX_PAGE, "cursor": "*"},
                 rs.read_openalex)
    return [w for body in rs.stored_pages(rs.read_manifest(run_dir), run_dir, "openalex", stream)
            for w in json.loads(body)["results"]]


def chase(client: httpx.Client, run_dir: pathlib.Path, seeds: list[dict], known: list[dict],
          forward_until: datetime.date | None = None,
          published_from: datetime.date | None = PUBLISHED_FROM
          ) -> tuple[list[ass.ScreeningRecord], dict]:
    """The new screening records of one round, and the round's counts. `published_from` keeps
    cited and citing works published on or after it. The pre-window smoke run alone sets
    `forward_until` (cited and citing works up to that date, so that it retrieves no work of
    the registered window) and passes no `published_from`."""
    without = sorted(str(s.get("record_id")) for s in seeds if s.get("no_abstract"))
    if without:
        raise ChaseError(f"seeds classed no_abstract: {without[:5]}; a record without an "
                         "abstract has no eligibility decision and seeds no round")
    run_dir.mkdir(parents=True, exist_ok=True)
    by_doi = sorted({s["doi"] for s in seeds if s.get("doi")})
    by_pmid = sorted({s["pmid"] for s in seeds if not s.get("doi") and s.get("pmid")}, key=int)
    seed_works: dict[str, dict] = {}
    for field, values in (("doi", by_doi), ("pmid", by_pmid)):
        for i, batch in enumerate(batches(values, SEED_BATCH), 1):
            for w in paged(client, run_dir, f"seeds_{field}_{i:04d}",
                           f"{field}:{'|'.join(batch)}", SEED_SELECT):
                seed_works[short_id(w["id"])] = w
    seed_ids = sorted(seed_works)
    backward_ids = sorted({short_id(r) for w in seed_works.values()
                           for r in w.get("referenced_works") or []} - set(seed_ids))

    bodies: list[bytes] = []
    floor = f",from_publication_date:{published_from.isoformat()}" if published_from else ""
    limit = floor + (f",to_publication_date:{forward_until.isoformat()}" if forward_until
                     else "")
    for i, batch in enumerate(batches(seed_ids, SEED_BATCH), 1):
        paged(client, run_dir, f"forward_{i:04d}", f"cites:{'|'.join(batch)}{limit}",
              rs.OPENALEX_SELECT)
        bodies += rs.stored_pages(rs.read_manifest(run_dir), run_dir, "openalex",
                                  f"forward_{i:04d}")
    forward = [r for b in bodies for r in ass.parse_openalex(b)]
    forward_ids = {r.source_id for r in forward}
    bodies = []
    for i, batch in enumerate(batches([b for b in backward_ids if b not in forward_ids],
                                      WORK_BATCH), 1):
        paged(client, run_dir, f"backward_{i:04d}", f"openalex:{'|'.join(batch)}{limit}",
              rs.OPENALEX_SELECT)
        bodies += rs.stored_pages(rs.read_manifest(run_dir), run_dir, "openalex",
                                  f"backward_{i:04d}")
    backward = [r for b in bodies for r in ass.parse_openalex(b)]

    known_ids = known_identifiers(known)
    works: dict[str, ass.RetrievedRecord] = {}
    for r in forward + backward:
        if r.source_id in seed_works or r.source_id in works or is_known(r, known_ids):
            continue
        directions = [d for d, ids in (("backward", backward_ids), ("forward", forward_ids))
                      if r.source_id in ids]
        works[r.source_id] = r.model_copy(update={"streams": directions})
    new = list(works.values())
    pmids = sorted({r.pmid for r in new if r.pmid}, key=int)
    rs.run_pubmed_efetch(client, run_dir, pmids)
    pubmed = [r for b in rs.stored_pages(rs.read_manifest(run_dir), run_dir, "pubmed", "efetch")
              for r in ass.parse_pubmed(b)]
    screening = ass.deduplicate(pubmed + new)
    counts = {
        "seeds": len(seeds), "seeds_without_doi_or_pmid": sum(
            not s.get("doi") and not s.get("pmid") for s in seeds),
        "seed_works_found": len(seed_works),
        "published_from": published_from.isoformat() if published_from else None,
        "backward_works_referenced": len(backward_ids),
        "backward_works_retrieved": len(backward), "forward_works": len(forward_ids),
        "works_already_in_screening_sets": len({r.source_id for r in forward + backward}
                                               - set(seed_works) - set(works)),
        "new_works": len(new), "new_works_with_pmid": len(pmids),
        "new_screening_records": len(screening),
        "new_screening_records_no_abstract": ass.no_abstract_counts(screening),
    }
    return screening, counts


def dated_until(screening: list[ass.ScreeningRecord], end: datetime.date
                ) -> list[ass.ScreeningRecord]:
    """The screening records first public on or before `end`. The smoke run keeps these only:
    OpenAlex can date a work in 2018 that its PubMed record dates in 2019, and no record of
    the registered window is written to a smoke screening set."""
    return [s for s in screening if s.first_public.value <= end]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, required=True, dest="round_number")
    ap.add_argument("--seeds", type=pathlib.Path, required=True,
                    help="screening records (jsonl) of the papers to chase")
    ap.add_argument("--known", type=pathlib.Path, action="append", required=True,
                    help="screening_records.jsonl of the search and of each earlier round")
    ap.add_argument("--smoke", action="store_true",
                    help="pre-window seeds only; cited and citing works limited to before 2019")
    ap.add_argument("--smoke-label",
                    help="with --smoke: the folder under outputs/raw/citation_chase_smoke and "
                         "outputs/screening_smoke that holds the round")
    a = ap.parse_args()
    if a.smoke_label and not a.smoke:
        ap.error("--smoke-label goes with --smoke")
    if not 1 <= a.round_number <= MAX_ROUNDS:
        raise ChaseError(f"round {a.round_number}: chasing runs for at most {MAX_ROUNDS} rounds")
    if not a.smoke:
        rs.check_frozen()
    name = f"chase_round_{a.round_number}"
    label = pathlib.Path(a.smoke_label) if a.smoke_label else pathlib.Path()
    raw_dir = (RAW_SMOKE / label if a.smoke else RAW) / name
    out_dir = (OUT_SMOKE / label if a.smoke else OUT) / name
    if out_dir.exists():
        raise ChaseError(f"{out_dir} exists; archive it before rerunning")

    def read(path: pathlib.Path) -> list[dict]:
        return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]

    seeds = read(a.seeds)
    known = [s for path in a.known for s in read(path)]
    with httpx.Client(timeout=120) as client:
        screening, counts = chase(client, raw_dir, seeds, known,
                                  SMOKE_END if a.smoke else None,
                                  None if a.smoke else PUBLISHED_FROM)
    if a.smoke:
        kept = dated_until(screening, SMOKE_END)
        counts["smoke_records_first_public_after_2018_left_out"] = len(screening) - len(kept)
        counts["new_screening_records"] = len(kept)
        counts["new_screening_records_no_abstract"] = ass.no_abstract_counts(kept)
        screening = kept
    out_dir.mkdir(parents=True)
    ass.write_screening_files(out_dir, screening)
    result = {"round": a.round_number, "seeds_file": str(a.seeds),
              "seeds_sha256": hashlib.sha256(a.seeds.read_bytes()).hexdigest(),
              "known_files": [str(p) for p in a.known], **counts}
    (out_dir / "chase_counts.json").write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
