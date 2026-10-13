# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""The cut of supplements under Amendment 1 of the release-resolution follow-up
(AMENDMENT_01_supplement_cut_and_diagnostic.md, sha256
999796b885abf70b11d4ac25eef88d526dccf8f92e81e888bf2dd2ab9949e316; registration
https://osf.io/2s479). Second version of scripts/cut_supplements.py (sealed, unchanged and
imported: the threshold, the term rule, sheet and table names and the header rows).

The threshold is unchanged: a supplement under 200,000 characters and with at most 20 sheets is
given whole. In a larger one the cut keeps, in file order:

- every line matching the frozen keep list (reference/release_language_patterns_v2.json) or a
  C1 identifier pattern (the narrow keep list of scripts/calibrate_keeplist_v2.py);
- the sheet and table names and the header rows;
- every other row of the registered selection (scripts/calibrate_dedup.frozen_selection) except a
  row equal in every normalized cell to a kept row of the same table (the evidence unit of
  scripts/calibrate_containment_v3.row_unit: table, hash of the table's header or name, the
  whole row with each cell normalized).

This is the `full_rows` variant of scripts/calibrate_containment_v3.py; tests check that the
two agree in characters, units and removed-chunk lengths.

Containment. Every whole-row unit the registered cut retains must be retained here; a file where
one is absent raises ContainmentError and the stage stops.

What a model reads. The kept rows, each with its table, its header line and whether it is a
structural line (`rows`); `requests` packs them in file order into parts of at most a given
number of characters, a table's header shown before its first kept row and again at the head of
a part whose first row belongs to that table (as calibrate_containment.pack counts it).

Removed text. The lines the cut removes, in chunks of at most 10,000 characters, a row never
split, the table's header at the head of each chunk (as calibrate_keeplist.chunk_lengths counts
it), each with its sha256: the population of the removed-chunk miss-rate diagnostic.
"""

import hashlib

import calibrate_containment as cn
import calibrate_containment_v3 as c3
import calibrate_dedup as cd
import calibrate_keeplist_v2 as k2
import cut_supplements as cs

CHUNK = 10_000


class ContainmentError(Exception):
    """A whole-row unit the registered cut retains is absent from the amended cut."""


class CutError(Exception):
    """A supplement entry lacks its text or type."""


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def select(lines: list[str], kind: str, matcher, groups: k2.Groups) -> dict:
    """The registered selection, the amended keep, the table of each line, the structural lines
    and the whole-row units of each cut."""
    table = cd.tables(lines, kind)
    head = cs.headers(lines, kind)
    heads = {h for h in head if h is not None} | ({0} if kind in ("CSV", "TSV") and lines else set())
    selected = cd.frozen_selection(lines, kind, matcher)
    structural = {i for i in selected if cs.SHEET.match(lines[i]) or cs.TABLE_NAME.match(lines[i])
                  or i in heads}
    context = {t: hashlib.sha256(lines[t].encode()).hexdigest()[:16] if t >= 0 else "file"
               for t in set(table)}

    def unit(i):
        if i in structural or not lines[i].strip():
            return None
        return c3.row_unit(lines[i], table[i], context[table[i]])

    listed = {i for i, l in enumerate(lines) if l.strip() and k2.narrow(groups(l))}
    keep, seen = [], set()
    for i in sorted(set(selected) | listed):
        u = unit(i)
        if i in structural or i in listed or (u is not None and u not in seen):
            keep.append(i)
            if u is not None:
                seen.add(u)
    units = {"registered": {unit(i) for i in selected} - {None},
             "amended": {unit(i) for i in keep} - {None}}
    return {"table": table, "structural": structural, "selected": sorted(selected),
            "keep": keep, "units": units}


def removed_chunks(lines: list[str], removed: list[int], table: list[int],
                   size: int = CHUNK) -> list[str]:
    """The removed lines as chunk texts (the lengths of calibrate_keeplist.chunk_lengths)."""
    out, current, current_table = [], [], None
    length = 0
    for i in removed:
        t = table[i]
        header = [lines[t]] if t >= 0 and t != i else []
        size_i = len(lines[i]) + 1
        if current and (t != current_table or length + size_i > size):
            out.append("\n".join(current) + "\n")
            current, length = [], 0
        if not current:
            current = list(header)
            length = sum(len(h) + 1 for h in header)
            current_table = t
        current.append(lines[i])
        length += size_i
    if current:
        out.append("\n".join(current) + "\n")
    return out


def cut(entry: dict, matcher, groups: k2.Groups) -> dict:
    """One supplement file as the models read it, with its containment counts and the chunks of
    its removed text."""
    if entry.get("text") is None or "type" not in entry:
        raise CutError(f"{entry.get('name')}: no text or type")
    text = entry["text"]
    base = {"name": entry["name"], "sha256": entry["sha256"], "type": entry["type"],
            "version": entry.get("version"), "characters_before": len(text)}
    if not cs.must_cut(entry):
        return base | {"cut": False, "text": text, "rows": None, "characters_read": len(text),
                       "units_registered": 0, "units_amended": 0, "lost_units": 0, "chunks": []}
    lines = text.split("\n")
    s = select(lines, entry["type"], matcher, groups)
    lost = s["units"]["registered"] - s["units"]["amended"]
    if lost:
        raise ContainmentError(f"{entry['name']}: {len(lost)} registered whole-row units absent")
    table, keep, structural = s["table"], s["keep"], s["structural"]
    rows = [{"table": table[i], "line": lines[i],
             "header": lines[table[i]] if table[i] >= 0 and table[i] != i else None,
             "structural": i in structural} for i in keep]
    kept = set(keep) | {table[i] for i in keep if table[i] >= 0}
    removed = [i for i in range(len(lines)) if i not in kept and lines[i].strip()]
    chunks = removed_chunks(lines, removed, table)
    return base | {"cut": True, "text": None, "rows": rows,
                   "characters_read": cn.pack(lines, keep, table, structural),
                   "units_registered": len(s["units"]["registered"]),
                   "units_amended": len(s["units"]["amended"]), "lost_units": 0,
                   "chunks": [{"text": c, "sha256": sha256(c), "characters": len(c)}
                              for c in chunks]}


def requests(rows: list[dict], budget: int) -> list[str]:
    """Kept rows packed in file order into parts of at most `budget` characters (a row longer
    than the budget is a part of its own), each table's header shown before its first kept row
    and repeated at the head of a part whose first row belongs to that table."""
    order, shown = [], set()
    for r in rows:
        t = r["table"]
        if not r["structural"] and r["header"] is not None and t not in shown:
            order.append((t, r["header"], True))
            shown.add(t)
        if r["structural"]:
            shown.add(t)
        order.append((t, r["line"], r["header"] if not r["structural"] else None))
    parts, current, length = [], [], 0
    for t, line, header in order:
        size = len(line) + 1
        if current and length + size > budget:
            parts.append("\n".join(current))
            current, length = [], 0
            if header is not None and header is not True:
                current.append(header)
                length += len(header) + 1
        current.append(line)
        length += size
    if current:
        parts.append("\n".join(current))
    return parts
