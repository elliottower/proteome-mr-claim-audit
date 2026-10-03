# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.13.5"]
# ///
"""Mark screening records that lack an MR or genetic-instrument term or a protein or pQTL term.

For the registered search the mark orders the screening queue and is reported; it never excludes
a record, and every record of the input is written to the queue and goes to GPT-6.1 Sol.

For a citation-chasing round (`--gate`) the mark is a gate (prefiltered citation chasing): the
queue holds the unmarked records only, and the marked records are written to `gated_out.jsonl`
and are not screened, except for the sample that audits the gate (scripts/gate_audit.py): the
first batch of it, `gate_sample_batch_01.jsonl`, is written here (the first 600 of the marked
ids, sorted and shuffled with `random.Random(20261001)`), and is judged by the eligibility
prompt like the queue. A sampled record judged eligible or uncertain enters the ordinary
workflow.

The two term lists are the title-and-abstract terms of the registered query blocks
(`search/prefilter_terms.json`, written by `--write-terms`):

    genetic   MR, GEN and LOCUS
    protein   PROT and PQTLB

The input is a screening set of records with an abstract (assemble_screening_set.py leaves the
`no_abstract` records out, scripts/abstract_floor.py); a record below the floor in it raises, so
no such record is marked, gated, sampled by the gate audit or queued for GPT-6.1 Sol.

A term matches the record's title and abstract, joined, without regard to case. Hyphens and
dashes in a term are read as spaces; the text is read twice, with its hyphens as spaces and
with its hyphens removed, so `colocali*` finds "co-localization" as PubMed does. A term matches
from the start of a word, a truncated term (`proteom*`) to any ending and any other term to
the end of its last word; an AND group matches when each of its parts does. A record is marked when no genetic term or no
protein term matches. The queue lists unmarked records first, then marked records, each in
record-id order.

Usage:
    uv run scripts/keyword_prefilter.py --write-terms
    uv run scripts/keyword_prefilter.py --screening-set outputs/screening/<run>/screening_set.jsonl
    uv run scripts/keyword_prefilter.py --gate \
        --screening-set outputs/screening/chase_round_<k>/screening_set.jsonl
"""

import argparse
import json
import pathlib
import re

from pydantic import BaseModel

import gate_audit
import search_queries as sq
from abstract_floor import refuse_no_abstract

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
TERMS = EXP / "search" / "prefilter_terms.json"
GROUPS = {"genetic": ("MR", "GEN", "LOCUS"), "protein": ("PROT", "PQTLB")}


class PrefilterError(Exception):
    """The committed term file differs from the registered blocks, or an output exists."""


class Mark(BaseModel):
    record_id: str
    has_genetic_term: bool
    has_protein_term: bool
    marked: bool


def block_terms(block: str) -> list[str | list[str]]:
    """The title-and-abstract terms of a block: strings, and lists for AND groups."""
    out: list[str | list[str]] = []
    for raw in sq.PUBMED_BLOCKS[block]:
        term = sq.parse_term(raw)
        if term.kind == "block":
            out.extend(block_terms(term.text))
        elif term.kind == "all_of":
            out.append([p.text for p in term.parts])
        elif term.kind == "text":
            out.append(term.text)
    return out


def derive_terms() -> dict[str, list[str | list[str]]]:
    terms: dict[str, list[str | list[str]]] = {}
    for group, blocks in GROUPS.items():
        terms[group] = []
        for block in blocks:
            terms[group].extend(t for t in block_terms(block) if t not in terms[group])
    return terms


def load_terms() -> dict[str, list[str | list[str]]]:
    terms = json.loads(TERMS.read_text())["terms"]
    if terms != derive_terms():
        raise PrefilterError(f"{TERMS} differs from the registered query blocks")
    return terms


DASHES = r"[-‐‑‒–—]"


def normalize(text: str, dash: str = " ") -> str:
    return " ".join(re.sub(DASHES, dash, text).lower().split())


def term_pattern(term: str) -> re.Pattern:
    words = normalize(term.rstrip("*")).split()
    end = r"\w*" if term.endswith("*") else r"(?!\w)"
    return re.compile(r"(?<!\w)" + r"\s".join(re.escape(w) for w in words) + end)


def matches(term: str | list[str], texts: tuple[str, str]) -> bool:
    """`texts` is the record text with hyphens as spaces, and with hyphens removed."""
    if isinstance(term, list):
        return all(matches(t, texts) for t in term)
    pattern = term_pattern(term)
    return any(pattern.search(t) is not None for t in texts)


def mark(record_id: str, title: str, abstract: str,
         terms: dict[str, list[str | list[str]]]) -> Mark:
    texts = (normalize(f"{title} {abstract}"), normalize(f"{title} {abstract}", ""))
    genetic = any(matches(t, texts) for t in terms["genetic"])
    protein = any(matches(t, texts) for t in terms["protein"])
    return Mark(record_id=record_id, has_genetic_term=genetic, has_protein_term=protein,
                marked=not (genetic and protein))


def queue(records: list[dict], terms: dict[str, list[str | list[str]]]
          ) -> tuple[list[dict], list[Mark]]:
    """The records ordered unmarked first, each group in record-id order, and their marks."""
    marks = {r["pmid"]: mark(r["pmid"], r["title"], r["abstract"] or "", terms) for r in records}
    ordered = sorted(records, key=lambda r: (marks[r["pmid"]].marked, r["pmid"]))
    return ordered, [marks[r["pmid"]] for r in ordered]


def gate(ordered: list[dict], marks: list[Mark], seed: int = gate_audit.SEED
         ) -> tuple[list[dict], list[dict], list[dict]]:
    """(records sent to screening, marked records, the first audit batch of the marked
    records), each in record-id order."""
    marked_ids = {m.record_id for m in marks if m.marked}
    kept = [r for r in ordered if r["pmid"] not in marked_ids]
    out = sorted((r for r in ordered if r["pmid"] in marked_ids), key=lambda r: r["pmid"])
    drawn = set(gate_audit.batch_ids(gate_audit.draw_order([r["pmid"] for r in out], seed), 1))
    return kept, out, [r for r in out if r["pmid"] in drawn]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-terms", action="store_true",
                    help="write search/prefilter_terms.json from the registered blocks")
    ap.add_argument("--screening-set", type=pathlib.Path)
    ap.add_argument("--gate", action="store_true",
                    help="citation-chasing round: marked records are not screened")
    a = ap.parse_args()
    if a.write_terms:
        TERMS.write_text(json.dumps({
            "description": "Keyword prefilter term lists (scripts/keyword_prefilter.py): the "
                           "title-and-abstract terms of the registered query blocks. genetic = "
                           "MR, GEN, LOCUS; protein = PROT, PQTLB. A list is an AND group.",
            "terms": derive_terms()}, indent=1) + "\n")
        return
    if a.screening_set is None:
        ap.error("--screening-set or --write-terms is required")
    out_dir = a.screening_set.parent
    if (out_dir / "screening_queue.jsonl").exists():
        raise PrefilterError(f"{out_dir}/screening_queue.jsonl exists; archive it first")
    records = [json.loads(l) for l in a.screening_set.read_text().splitlines() if l.strip()]
    refuse_no_abstract(records, "keyword prefilter")
    ordered, marks = queue(records, load_terms())
    if sorted(r["pmid"] for r in ordered) != sorted(r["pmid"] for r in records):
        raise PrefilterError("the queue does not hold every record of the screening set")
    def lines(rows: list[dict]) -> str:
        return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)

    sent, gated_out, sample = gate(ordered, marks) if a.gate else (ordered, [], [])
    (out_dir / "screening_queue.jsonl").write_text(lines(sent))
    (out_dir / "prefilter_marks.jsonl").write_text(
        "".join(m.model_dump_json() + "\n" for m in marks))
    if a.gate:
        (out_dir / "gated_out.jsonl").write_text(lines(gated_out))
        gate_audit.write_batch(out_dir, 1, sample)
    counts = {"records": len(records), "marked": sum(m.marked for m in marks),
              "no_genetic_term": sum(not m.has_genetic_term for m in marks),
              "no_protein_term": sum(not m.has_protein_term for m in marks),
              "gated": a.gate, "records_sent_to_screening": len(sent),
              "marked_records": len(gated_out),
              "gate_sample_batch_1": len(sample),
              "gate_sample_seed": gate_audit.SEED if a.gate else None}
    (out_dir / "prefilter_counts.json").write_text(json.dumps(counts, indent=1))
    print(json.dumps(counts, indent=1))


if __name__ == "__main__":
    main()
