# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Pricing of a staged design of the release-resolution coding, and a stratified C1 draw, for
the author's decision on a draft second amendment (post-results planning; nothing here is
registered). No model is called; counts only.

Stage A: every queue row coded from the record's abstract and full texts (routes R1, R3), no
supplement; one request per record (coding_packets.fulltext_packets with no supplement), with
the control rows of the stratified draw merged into the records they come from. Stage B, an upper
bound: every record with a readable supplement read again with its supplements under the amended
cut, every request carrying the abstract and full texts (coding_packets_v2.
fulltext_packets_carrying), as if every such record still held an unresolved row. SA1: the
abstract-only packets already built.

Costs per model by coding_packets_v2.layout_cost, from the packets' JSON characters, at the
plan's pooled ratios and at the preflight's ratios, with 1,500 output tokens a request and the
sensitivity at 3,000 and 6,000 (thinking and reasoning tokens are billed as output and are not
otherwise counted).

Stratified draw (`stratified_draw`): among the scanner's matches (source_scanner_v2.controls,
already stored per record), those in text stage A reads (routes R1, R3); one candidate per
(record, identifier), the first in sorted order of source and unit; shuffled by the frozen seed;
then taken in that order, at most PER_RECORD per record, up to the frozen maximum.
"""

import random

import coding_packets_v2 as cp2

PER_RECORD = 5
STAGE_A_ROUTES = ("R1", "R3")
OUTPUTS = (1_500, 3_000, 6_000)


def route(match: dict) -> str:
    return match["source_key"].split(":")[0]


def stratified_draw(found: list[dict], seed: int, maximum: int,
                    per_record: int = PER_RECORD, routes=STAGE_A_ROUTES) -> list[dict]:
    first: dict[tuple, dict] = {}
    for c in sorted(found, key=lambda c: (c["record_id"], c["identifier"], c["source_key"],
                                          c["unit_id"])):
        if route(c) in routes:
            first.setdefault((c["record_id"], c["identifier"]), c)
    pool = list(first.values())
    random.Random(seed).shuffle(pool)
    taken, per = [], {}
    for c in pool:
        if per.get(c["record_id"], 0) < per_record and len(taken) < maximum:
            taken.append(c)
            per[c["record_id"]] = per.get(c["record_id"], 0) + 1
    return taken


def with_outputs(cost: dict) -> dict:
    """The cost at each output length per request (the extra output at the output price)."""
    out = {}
    for tokens in OUTPUTS:
        extra = tokens - cp2.OUTPUT_TOKENS
        per = {m: round(v["usd"] + v["requests"] * extra * cp2.PRICE[m]["output"] / 1e6, 2)
               for m, v in cost.items() if m in cp2.PRICE}
        out[str(tokens)] = per | {"total_usd": round(sum(per.values()), 2)}
    return out
