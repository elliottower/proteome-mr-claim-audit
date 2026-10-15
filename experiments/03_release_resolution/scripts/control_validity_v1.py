# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Valid-control marks of C1-A (DEVIATION_02_c1_controls.md, item 2). No coder answer, recovery
status or diagnostic is read here; the two judges of Amendment 4 are called by the Modal wrapper
(scripts/modal_control_validity_v1.py) through scripts/judge_v3.py.

Packet (`packet`), one per C1-A control of the frozen control set, recovered or not, holding only:
- `row_id`, the control's row id, and `side`, its side;
- `identifier`, the identifier as the source writes it (the control's `name_as_written`);
- `passage`: `text`, the control's unit (the sentence or table row the frozen scanner matched,
  scripts/c1_controls.units, sealed, imported unchanged); `before` and `after`, the units
  immediately before and after it in the same source file (None at either end); `table_header`,
  the header line of the table when the unit is a table row (else None);
- `claims`: the record's claims, one per claim record of the record's queue rows
  (outputs/coding_queue_2026-10-13.json, `claim_record_ids`), each with `protein`, `outcome` and
  `direction` from the first claim check of that claim record in the order the queue reads them
  (`protein_as_written`, `outcome_as_written`, `direction`); identical triples are given once, in
  sorted order.

The source file is the record's readable retrieved source the control's `source_key` names
(`<route>:<n>:<sha256 of the text, 16 hex digits>`, n its place among the readable sources); its
units are made by c1_controls.units over that file alone, whose unit ids differ from the scan's
only in the source key, so the control's unit is found by its line and sentence. The route and
the text's digest must match the source key.

Order (`order`): the control row ids, sorted, shuffled by `random.Random(SEED).shuffle`.

Combination (`combine`): `valid` when both judges mark valid; `invalid` when both mark invalid;
any other pair (the judges differ, either marks cannot_mark, or either request failed twice) is
retained as `valid` and counted as disputed.
"""

import hashlib
import json
import random

import c1_controls as c1

SEED = 20261032
MARKS = ("valid", "invalid", "cannot_mark")


class PacketError(Exception):
    """A control's source or unit cannot be located as its source key and unit id name it."""


def file_bytes(packet: dict) -> bytes:
    return (json.dumps(packet, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def passage(record_id: str, sources: list[dict], source_key: str, unit_id: str) -> dict:
    route, n, digest = source_key.split(":")
    readable = [s for s in sources if s.get("text")]
    src = readable[int(n) - 1]
    if src["route"] != route or sha256(src["text"].encode())[:16] != digest:
        raise PacketError(f"{record_id}: {source_key} is not the readable source it names")
    if not unit_id.startswith(source_key + ":"):
        raise PacketError(f"{record_id}: {unit_id} is not a unit of {source_key}")
    line, sentence = unit_id.removeprefix(source_key + ":").split(":")
    units = c1.units(record_id, [src])
    own = [u["unit_id"].split(":")[-2:] for u in units]
    if [line, sentence] not in own:
        raise PacketError(f"{record_id}: no unit {unit_id}")
    i = own.index([line, sentence])
    unit = units[i]
    return {"text": unit["text"],
            "before": units[i - 1]["text"] if i > 0 else None,
            "after": units[i + 1]["text"] if i + 1 < len(units) else None,
            "table_header": unit["header"]}


def claims_of_records(queue: list[dict], checks: list[dict]) -> dict[str, list[dict]]:
    first: dict[str, dict] = {}
    for r in checks:
        if "claim_record_id" in r:
            first.setdefault(r["claim_record_id"], r)
    ids: dict[str, set[str]] = {}
    for row in queue:
        ids.setdefault(row["record_id"], set()).update(row["claim_record_ids"])
    out = {}
    for rec, cids in ids.items():
        triples = {(first[c]["protein_as_written"], first[c]["outcome_as_written"],
                    first[c]["direction"]) for c in cids}
        out[rec] = [{"protein": p, "outcome": o, "direction": d} for p, o, d in sorted(triples)]
    return out


def packet(control: dict, sources: list[dict], claims: list[dict]) -> dict:
    return {"row_id": control["row_id"], "side": control["side"],
            "identifier": control["name_as_written"],
            "passage": passage(control["record_id"], sources, control["control_source_key"],
                               control["control_unit_id"]),
            "claims": claims}


def order(row_ids: list[str], seed: int = SEED) -> list[str]:
    out = sorted(row_ids)
    random.Random(seed).shuffle(out)
    return out


def mark_of(result: dict | None) -> str | None:
    """A judge's mark, or None when its request has no accepted answer."""
    if not result or result.get("state") != "accepted":
        return None
    return result["decision"]["mark"]


def combine(first: str | None, second: str | None) -> str:
    if first == second == "valid":
        return "valid"
    if first == second == "invalid":
        return "invalid"
    return "disputed_retained_valid"


def counts(combined: dict[str, str]) -> dict:
    disputed = sum(v == "disputed_retained_valid" for v in combined.values())
    valid = sum(v == "valid" for v in combined.values())
    return {"controls": len(combined), "both_valid": valid,
            "both_invalid": sum(v == "invalid" for v in combined.values()),
            "disputed_retained_valid": disputed, "valid_controls": valid + disputed}
