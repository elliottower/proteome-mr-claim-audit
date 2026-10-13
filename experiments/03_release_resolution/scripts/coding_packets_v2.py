# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Second version of the packet builder (scripts/coding_packets.py, sealed, unchanged and
imported). It adds:

- `fulltext_packets_carrying`: the full-text layout in which every request of a record carries
  the abstract and every full text, and the supplement items are sized to the room that leaves
  (LIMIT less the abstract and the full texts); the first version's layout (`fulltext_packets`:
  only the first request carries the full texts) is unchanged. Neither layout is chosen here.
- `layout_cost`: the cost of a list of requests per model, under stated characters per token,
  with the fixed prompt cached after the first request of the run and, for the carrying layout,
  the carried prefix (abstract and full texts) written to the cache in a record's first request
  and read from it in the record's later requests.
- control rows merged into a record's rows (c1_controls.merge), by `rows` passed in.
"""

import coding_packets as cp

OUTPUT_TOKENS = 1_500
# USD per million tokens: Claude Sonnet 5.5 at the vendor's list prices (cache read 0.20, cache
# write 1.25 times input); GPT-6.1 Sol at the plan's cost table.
PRICE = {"claude-sonnet-5-5": {"new": 2.00, "write": 2.50, "cached": 0.20, "output": 10.00},
         "gpt-6.1-sol": {"new": 2.00, "write": 2.00, "cached": 0.10, "output": 10.00}}


def fulltext_packets_carrying(record_id: str, title: str, rows: list[dict], abstract: str,
                              full_texts: list[dict], supplements: list[dict],
                              accessions: cp.Accessions) -> tuple[list[dict], list[dict]]:
    if abstract is None:
        raise cp.PacketError(f"{record_id}: no stored abstract")
    head = [{"file_id": "abstract", "kind": "abstract", "text": abstract}] + [
        {"file_id": f"full_text_{n + 1}", "kind": "full_text", "text": s["text"]}
        for n, s in enumerate(full_texts)]
    carried = sum(len(f["text"]) for f in head)
    if carried >= cp.LIMIT:
        raise cp.PacketError(f"{record_id}: abstract and full texts hold {carried} characters")
    room = cp.LIMIT - carried
    items, log = [], []
    for n, s in enumerate(supplements):
        fid = f"supplement_{n + 1}"
        if s["cut"]:
            parts = cp.cv.requests(s["rows"], room)
        elif len(s["text"]) <= room:
            parts = [s["text"]]
        else:
            chunks = cp.exhaustive_chunks(s["text"], s["type"], room)
            log.append({"record_id": record_id, "file_id": fid, "file_sha256": s["sha256"],
                        "chunks": [{k: c[k] for k in ("start", "end", "headers", "sha256")}
                                   | {"characters": len(c["text"])} for c in chunks]})
            parts = [c["text"] for c in chunks]
        for k, part in enumerate(parts):
            items.append({"file_id": fid if len(parts) == 1 else f"{fid}_part_{k + 1}",
                          "kind": "supplement" if len(parts) == 1 else "supplement_chunk",
                          "text": part})
    requests, current, used = [], list(head), carried
    for item in items:
        if used + len(item["text"]) > cp.LIMIT and current != head:
            requests.append(current)
            current, used = list(head), carried
        current = current + [item]
        used += len(item["text"])
    requests.append(current)
    return [cp.packet(record_id, title, rows, files, accessions) for files in requests], log


def layout_cost(records: list[dict], prompt_chars: int, ratio: dict[str, float],
                carrying: bool) -> dict:
    """`records`: per record, `packets` (the characters of each request's packet) and `carried`
    (the characters of the carried prefix). The first request of the run writes the prompt to
    the cache; every later request reads it."""
    out = {}
    for model, p in PRICE.items():
        r = ratio[model]
        new = write = cached = 0.0
        requests = 0
        for rec in records:
            for k, chars in enumerate(rec["packets"]):
                prompt_tok = prompt_chars / r
                if requests == 0:
                    write += prompt_tok
                else:
                    cached += prompt_tok
                body = chars / r
                if carrying and len(rec["packets"]) > 1:
                    pre = min(rec["carried"], chars) / r
                    if k == 0:
                        write += pre
                    else:
                        cached += pre
                    body -= pre
                new += body
                requests += 1
        output = requests * OUTPUT_TOKENS
        usd = (new * p["new"] + write * p["write"] + cached * p["cached"]
               + output * p["output"]) / 1e6
        out[model] = {"requests": requests, "new_input_tokens": round(new),
                      "cache_write_tokens": round(write), "cached_input_tokens": round(cached),
                      "output_tokens": output, "usd": round(usd, 2)}
    out["total_usd"] = round(sum(v["usd"] for v in out.values()), 2)
    return out
