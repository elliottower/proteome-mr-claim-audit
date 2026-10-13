# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""The fixed prompt and the packets of the release-resolution coding (PREREG.md, §Study design,
Checks and What the models read; prompts/api_framing_v2.md; Amendment 1). No model is called.

Fixed prompt. `prompts/coding_prompt_v2.md`, a line `## Dictionary definitions`, then Paper 1's
`dictionary_definitions.csv` as CSV, joined by blank lines (`fixed_prompt`).

Packet. One JSON object (`record_id`, `title`, `rows`, `files`, `accession_table_rows`). A row
shows `row_id`, `side`, `name` (as the abstract writes it, or `not stated`), for an outcome-side
row `outcomes_as_written`, and `candidates`. A file has `file_id`, `kind` (`abstract`,
`full_text`, `supplement`, `supplement_chunk`) and `text`. `accession_table_rows` holds the rows
of `reference/accession_releases.csv` (columns `release_identifier`, `identifier_type`,
`dictionary_row`) for every match of the accession patterns of
`reference/c1_scanner_patterns_v2.json` in the packet's files, in its canonical case (an
`ebi-a-` identifier also under the GWAS Catalog accession it carries), and every row of type
`opengwas_batch`.

Passes and requests. One request carries at most LIMIT (400,000) characters of source text.
- SA1 (`sa1_packets`): the record's abstract as Paper 1 stored it, and no other file.
- Full text (`fulltext_packets`): the first request holds the abstract and every full text of the
  record (routes R1, R3) and then supplement items in file order while they fit; each further
  request holds the abstract and the next supplement items. A supplement the threshold gives
  whole is one item when it fits within LIMIT less the abstract; a larger one is divided by the
  exhaustive whole-supplement pass (`exhaustive_chunks`). A cut supplement is packed by
  `cut_supplements_v2.requests` within LIMIT less the abstract, each part an item. An item that
  is one of several parts of a file is of kind `supplement_chunk`.
- Diagnostic (`diagnostic_packet`): one removed chunk, as a `supplement_chunk`, with the
  record's rows.

Exhaustive whole-supplement pass. The file's lines in order; a table row (a line with a tab under
a header) is never split and its header is repeated at the head of each chunk that holds rows of
its table; a prose line is divided into sentences, and a chunk that begins in prose begins with
the last two sentences of the chunk before. Every line is in some chunk. Each chunk is logged
with its file, its character range in the file, its table headers and its sha256
(`chunk_log`).
"""

import csv
import hashlib
import json
import re

import cut_supplements_v2 as cv
import source_scanner_v2 as scanner

LIMIT = 400_000
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\[])")


class PacketError(Exception):
    """A record's abstract and full texts alone exceed the input limit, or a field is missing."""


def fixed_prompt(prompt: str, definitions: str) -> str:
    return prompt.rstrip("\n") + "\n\n## Dictionary definitions\n\n" + definitions


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class Accessions:
    """The accession-table rows a packet's files call for."""

    def __init__(self, patterns: dict, table: list[dict]):
        self.patterns = [(re.compile(p["pattern"]), p["canonical"]) for p in patterns["accessions"]]
        self.by_id: dict[str, list[dict]] = {}
        self.batches = []
        for r in table:
            row = {k: r[k] for k in ("release_identifier", "identifier_type", "dictionary_row")}
            if r["identifier_type"] == "opengwas_batch":
                self.batches.append(row)
            else:
                self.by_id.setdefault(r["release_identifier"], []).append(row)

    def __call__(self, texts: list[str]) -> list[dict]:
        wanted = set()
        for text in texts:
            for pattern, rule in self.patterns:
                for m in pattern.finditer(text):
                    ident = scanner.canonical(m.group(0), rule)
                    wanted.add(ident)
                    if ident.startswith("ebi-a-"):
                        wanted.add(ident.removeprefix("ebi-a-"))
        out = [r for i in sorted(wanted) for r in self.by_id.get(i, [])]
        return out + self.batches


def shown_rows(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        shown = {"row_id": r["row_id"], "side": r["side"], "name": r["name_as_written"]}
        if r["side"] == "outcome":
            shown["outcomes_as_written"] = r["outcomes_as_written"]
        shown["candidates"] = r["candidates"]
        out.append(shown)
    return out


def packet(record_id: str, title: str, rows: list[dict], files: list[dict],
           accessions: Accessions) -> dict:
    return {"record_id": record_id, "title": title, "rows": shown_rows(rows),
            "files": [{"file_id": f["file_id"], "kind": f["kind"], "text": f["text"]}
                      for f in files],
            "accession_table_rows": accessions([f["text"] for f in files])}


def sa1_packets(record_id: str, title: str, rows: list[dict], abstract: str,
                accessions: Accessions) -> list[dict]:
    if abstract is None:
        raise PacketError(f"{record_id}: no stored abstract")
    return [packet(record_id, title, rows,
                   [{"file_id": "abstract", "kind": "abstract", "text": abstract}], accessions)]


def units_of(lines: list[str], kind: str) -> list[tuple[str, int | None, int, bool]]:
    """(text, header line index or None, line index, is a table row) for each unit of a file."""
    table = cv.cd.tables(lines, kind)
    out = []
    for i, line in enumerate(lines):
        t = table[i]
        if "\t" in line and t >= 0 and t != i:
            out.append((line, t, i, True))
        elif "\t" in line or not line.strip():
            out.append((line, None, i, True))
        else:
            for sentence in SENTENCE.split(line):
                out.append((sentence, None, i, False))
    return out


def exhaustive_chunks(text: str, kind: str, budget: int) -> list[dict]:
    """A supplement given whole, divided into chunks of at most `budget` characters (a single
    unit longer than that is a chunk of its own), with the log of each chunk."""
    lines = text.split("\n")
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line) + 1)
    chunks, current, length, prose = [], [], 0, []

    def close():
        body = "\n".join(u[0] for u in current)
        first, last = current[0][2], current[-1][2]
        heads = sorted({u[1] for u in current if u[1] is not None})
        chunks.append({"text": body, "start": offsets[first], "end": offsets[last + 1] - 1,
                       "headers": [lines[h] for h in heads], "sha256": sha256(body)})

    for unit in units_of(lines, kind):
        text_u, head, i, row = unit
        size = len(text_u) + 1
        if current and length + size > budget:
            close()
            carried = prose[-2:] if not row else []
            current = []
            length = 0
            if head is not None:
                current.append((lines[head], head, head, True))
                length += len(lines[head]) + 1
            for p in carried:
                current.append(p)
                length += len(p[0]) + 1
        if not current and head is not None:
            current.append((lines[head], head, head, True))
            length += len(lines[head]) + 1
        current.append(unit)
        length += size
        prose = prose + [unit] if not row else []
    if current:
        close()
    return chunks


def fulltext_packets(record_id: str, title: str, rows: list[dict], abstract: str,
                     full_texts: list[dict], supplements: list[dict],
                     accessions: Accessions) -> tuple[list[dict], list[dict]]:
    """The packets of one record for the full-text pass, and the log of every exhaustive chunk.
    `full_texts`: retrieval sources of route R1 or R3 with text; `supplements`: the files of the
    amended cut (scripts/cut_supplements_v2.cut) in file order."""
    if abstract is None:
        raise PacketError(f"{record_id}: no stored abstract")
    head = [{"file_id": "abstract", "kind": "abstract", "text": abstract}]
    body = [{"file_id": f"full_text_{n + 1}", "kind": "full_text", "text": s["text"]}
            for n, s in enumerate(full_texts)]
    first = len(abstract) + sum(len(f["text"]) for f in body)
    if first > LIMIT:
        raise PacketError(f"{record_id}: abstract and full texts hold {first} characters")
    room = LIMIT - len(abstract)
    items, log = [], []
    for n, s in enumerate(supplements):
        fid = f"supplement_{n + 1}"
        if s["cut"]:
            parts = cv.requests(s["rows"], room)
        elif len(s["text"]) <= room:
            parts = [s["text"]]
        else:
            chunks = exhaustive_chunks(s["text"], s["type"], room)
            log.append({"record_id": record_id, "file_id": fid, "file_sha256": s["sha256"],
                        "chunks": [{k: c[k] for k in ("start", "end", "headers", "sha256")}
                                   | {"characters": len(c["text"])} for c in chunks]})
            parts = [c["text"] for c in chunks]
        for k, part in enumerate(parts):
            items.append({"file_id": fid if len(parts) == 1 else f"{fid}_part_{k + 1}",
                          "kind": "supplement" if len(parts) == 1 else "supplement_chunk",
                          "text": part})
    requests, current, used = [], head + body, first
    for item in items:
        if used + len(item["text"]) > LIMIT and current != head:
            requests.append(current)
            current, used = list(head), len(abstract)
        current = current + [item]
        used += len(item["text"])
    requests.append(current)
    return [packet(record_id, title, rows, files, accessions) for files in requests], log


def diagnostic_packet(record_id: str, title: str, rows: list[dict], chunk: dict, index: int,
                      accessions: Accessions) -> dict:
    return packet(record_id, title, rows,
                  [{"file_id": f"removed_chunk_{index}", "kind": "supplement_chunk",
                    "text": chunk["text"]}], accessions)


def read_accessions(patterns_path, table_path) -> Accessions:
    with open(table_path, newline="") as fh:
        table = list(csv.DictReader(fh))
    return Accessions(json.loads(open(patterns_path).read()), table)
