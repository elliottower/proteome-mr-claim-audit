# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Settling by rule of release-concordant rows (the first registration's AMENDMENT_07, carried
over by the second registration's PREREG.md, item 4). No model is called.

A row is a disagreement when the two coders' answers differ by pass_summary.differs (identified
releases, roles, attribution state, unresolved reasons; sealed, unchanged). Among the
disagreements, a row is release-concordant (`concordant`) when both answers pass the gate (the
gate of item 2) and give the same identified release set (empty included), the same role and the
same ancestry for each release, and the same presence or absence of `conflicting_identifiers`.
Its two answers then differ, by pass_summary.differs, only in the attribution state and the
unresolved reasons; fields outside that comparison (notes, passages, count evidence, the
abstract transition) do not make a row a disagreement, and do not keep it from being settled.

Settled code (`settle`): the shared release set, roles and ancestry; the more conservative
attribution state (unresolved, then paper_wide, then explicit); the union of both answers'
unresolved reasons, with attribution_unresolved added when the state is unresolved; the union of
both answers' decisive passages and of their attribution passages.
"""

import pass_summary as ps

CONSERVATIVE = ("unresolved", "paper_wide", "explicit")


def roles(row: dict) -> frozenset:
    return frozenset((r["release"], r["role"]) for r in row["roles"])


def ancestry(row: dict) -> frozenset:
    return frozenset((r["release"], r["ancestry"]) for r in row["ancestry"])


def concordant(a: dict, b: dict, gate_a: bool, gate_b: bool) -> bool:
    return (gate_a and gate_b
            and set(a["identified_releases"]) == set(b["identified_releases"])
            and roles(a) == roles(b) and ancestry(a) == ancestry(b)
            and ("conflicting_identifiers" in a["unresolved_reasons"])
            == ("conflicting_identifiers" in b["unresolved_reasons"]))


def union(items: list) -> list:
    out = []
    for x in items:
        if x is not None and x not in out:
            out.append(x)
    return out


def settle(a: dict, b: dict) -> dict:
    state = min(a["attribution_state"], b["attribution_state"], key=CONSERVATIVE.index)
    reasons = set(a["unresolved_reasons"]) | set(b["unresolved_reasons"])
    if state == "unresolved":
        reasons.add("attribution_unresolved")
    return {"row_id": a["row_id"], "identified_releases": sorted(a["identified_releases"]),
            "roles": sorted(a["roles"], key=lambda r: (r["release"], r["role"])),
            "ancestry": sorted(a["ancestry"], key=lambda r: (r["release"], r["ancestry"])),
            "attribution_state": state, "unresolved_reasons": sorted(reasons),
            "decisive_evidence": union(a["decisive_evidence"] + b["decisive_evidence"]),
            "attribution_passages": union([a["attribution_passage"], b["attribution_passage"]]),
            "settled_by": "AMENDMENT_07 rule"}


def split(row_ids: list[str], first: dict, second: dict, gate_first: dict,
          gate_second: dict) -> dict:
    """The rows by outcome: agreed, settled (with their codes and attribution pairs), or sent on
    as disagreements; a row missing an answer is a disagreement."""
    agreed, settled, disagreements, pairs = [], {}, [], {}
    for rid in row_ids:
        a, b = first.get(rid), second.get(rid)
        if a is None or b is None:
            disagreements.append(rid)
        elif not ps.differs(a, b):
            agreed.append(rid)
        elif concordant(a, b, gate_first.get(rid, False), gate_second.get(rid, False)):
            settled[rid] = settle(a, b)
            pair = "|".join(sorted((a["attribution_state"], b["attribution_state"])))
            pairs[pair] = pairs.get(pair, 0) + 1
        else:
            disagreements.append(rid)
    return {"agreed": agreed, "settled": settled, "disagreements": disagreements,
            "settled_by_attribution_pair": dict(sorted(pairs.items()))}
