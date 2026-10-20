# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""Stage A packets of the second release-resolution registration (PREREG.md, §Study design,
item 1, Packets). No model is called.

Scope packets (`scope_packet`): each frozen stage A packet of the first registration (volume
manifest sha256 fef6b59516082495b62c2233659661f325fb602d29020a66168db29bb93aa7ed) with the rows
of the first registration's 70 control rows (outputs/c1a_controls_2026-10-13.json) removed; every
other key, the files and the accession-table rows unchanged.

Packets of records outside the scope (`outside_packets`), only for a record with a drawn
control: the record's abstract (Paper 1's screening record) and its R1 and R3 full texts,
in the first registration's layout (coding_packets_v2.fulltext_packets_carrying, sealed, no
supplement); its study rows built by the queue rule (`queue_rows`) from every Paper 1 claim
record of the record; and its control rows (c1_controls.control_rows over the drawn controls,
with the outcomes as written of the record's outcome-side rows), merged in order of row id
(c1_controls.merge), so that control rows are not told from study rows.

Queue rule (`queue_rows`). coding_queue.queue (sealed) applies its unit rule only to claims whose
pair is repeated; no claim of a record outside the scope is. `queue_rows` is the same loop, line
for line, over the given claim records, without the repeated-pair condition: one row per record,
side and name as written; on a `not_stated` side one row per record and side (pQTL) or per
record, side and outcome as written (outcome); candidates from dataset_relations.map_name, or
every row of the side; row ids from coding_queue.row_id. On claims of repeated pairs it returns
the rows coding_queue.queue returns.
"""

import c1_controls as c1
import coding_packets_v2 as cp2
import coding_queue as q
from dataset_relations import DICTIONARY, load_rows, map_name

FULL_TEXT_ROUTES = ("R1", "R3")


class PacketsError(Exception):
    """A claim record lacks its inputs, a control row id does not match, or rows are lost."""


def queue_rows(coded: list, plain: dict[str, dict], outcome_written: dict[str, str],
               dictionary=DICTIONARY) -> list[dict]:
    rows = load_rows()
    names_of_side = q.side_rows(dictionary)
    real = {r.name for r in rows}
    found: dict[tuple, dict] = {}
    for c in coded:
        cid = c.claim_record_id
        if cid not in plain or cid not in outcome_written:
            raise PacketsError(f"{cid}: no plain names or no outcome as written")
        record = cid.rsplit(":", 1)[0]
        written = outcome_written[cid]
        for side, field in (("pqtl", "pqtl_datasets"), ("outcome", "outcome_datasets")):
            for name in plain[cid][field]:
                stated = name.strip() != q.NOT_STATED
                outcome = "" if stated or side == "pqtl" else written
                key = (record, side, name if stated else q.NOT_STATED, outcome)
                if key not in found:
                    if stated:
                        cands = [x for x in map_name(name, side, rows).candidates if x in real]
                    else:
                        cands = names_of_side[side]
                    found[key] = {"row_id": q.row_id(*key), "record_id": record, "side": side,
                                  "name_as_written": name if stated else q.SHOWN_NOT_STATED,
                                  "outcomes_as_written": [], "candidates": cands,
                                  "claim_record_ids": [], "family_id": c.family_id,
                                  "kind": "study"}
                row = found[key]
                if side == "outcome" and written not in row["outcomes_as_written"]:
                    row["outcomes_as_written"].append(written)
                if cid not in row["claim_record_ids"]:
                    row["claim_record_ids"].append(cid)
    return [found[k] for k in sorted(found)]


def as_found(candidate: dict) -> dict:
    return {"record_id": candidate["record_id"], "side": candidate["side"],
            "identifier": candidate["name_as_written"], "expected_row": candidate["expected_row"],
            "source_key": candidate["control_source_key"],
            "unit_id": candidate["control_unit_id"]}


def control_rows(drawn: list[dict], study: list[dict], side_rows: dict[str, list[str]]) -> list:
    rows = c1.control_rows([as_found(c) for c in drawn], study, side_rows)
    for row, c in zip(rows, drawn):
        if row["row_id"] != c["row_id"]:
            raise PacketsError(f"{c['row_id']}: control row id differs from the candidate's")
    return rows


def scope_packet(packet: dict, control_ids: set[str]) -> tuple[dict, int]:
    kept = [r for r in packet["rows"] if r["row_id"] not in control_ids]
    return packet | {"rows": kept}, len(packet["rows"]) - len(kept)


def outside_packets(record_id: str, title: str, abstract: str, sources: list[dict],
                    study: list[dict], controls: list[dict], accessions) -> list[dict]:
    if not abstract:
        raise PacketsError(f"{record_id}: no stored abstract")
    full = [s for s in sources if s["route"] in FULL_TEXT_ROUTES and s.get("text")]
    packets, _ = cp2.fulltext_packets_carrying(record_id, title, c1.merge(study, controls),
                                               abstract, full, [], accessions)
    return packets
