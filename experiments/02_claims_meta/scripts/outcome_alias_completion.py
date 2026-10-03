# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Equivalences between outcome terms that the pinned ontology files assert and the label tiers
do not use. Resource files only: no claim, pair or registry record is read. Run on Modal with
the resource tables (scripts/biology_resource_tables.py); the three tables are committed under
verification/.

No table here is written by hand, and none uses the similarity of two names.

phenotype_cross_references.csv
    A disease name can be the label of a phenotype term only: "hypertension" labels HP:0000822,
    and the disease term is MONDO:0005044, "hypertensive disorder". The pinned MONDO file links
    the two with a cross-reference on the disease term (`xref: HP:0000822`, source tag
    `MONDO:otherHierarchy` or `MONDO:equivalentTo`). The table lists every live HP term of the
    EFO file that exactly one canonical MONDO or EFO term cross-references in this way.
    scripts/canonical_ids.py uses it for an outcome name that gives no MONDO or EFO identifier.

obsolete_label_replacements.csv
    The EFO file keeps the terms it has retired, each with the live term that replaces it
    (`replaced_by`): "mean corpuscular volume" was EFO:0004526 and is now OBA:0003460. The table
    lists the label of every obsolete EFO term (without its `obsolete_` prefix) that has one
    replacement, a live outcome term, and whose label is not a label or exact synonym of any
    live term. scripts/verify_claims.py reads it as a tier of its own, after labels and exact
    synonyms and before related synonyms.

icd10 cross-references (not a committed table)
    `icd10_terms` gives, per ICD-10 code, the canonical terms whose MONDO stanza cross-references
    the code (`ICD10CM:` or `ICD10WHO:`) with source tag `MONDO:equivalentTo`.
    scripts/reference_screen.py maps a snapshot trait whose name holds an ICD-10 code through
    it when exactly one term carries the code.
"""

import collections
import csv
import pathlib
import re
from collections.abc import Callable, Collection, Iterator, Mapping

HP_TAGS = ("MONDO:otherHierarchy", "MONDO:equivalentTo")
ICD_PREFIXES = ("ICD10CM", "ICD10WHO")
ICD_TAG = "MONDO:equivalentTo"
OBSOLETE_PREFIX = re.compile(r"^obsolete[_ ]", re.I)
OUTCOME_PREFIXES = ("MONDO:", "EFO:", "HP:", "OBA:", "Orphanet:")
MAX_REPLACEMENT_STEPS = 5
XREF = re.compile(r"xref: (\S+)(?:\s+\{(.*)\})?")
PHENOTYPE_FIELDS = ["phenotype_id", "phenotype_label", "canonical_id", "canonical_label",
                    "xref_tags"]
OBSOLETE_FIELDS = ["surface", "obsolete_id", "term_id", "term_label"]


def term_id(raw: str) -> str:
    """`efo:EFO_0004340`, `http://purl.obolibrary.org/obo/MONDO_0005044` and `MONDO:0005044`
    are written PREFIX:N."""
    raw = raw.strip()
    if "://" in raw:
        tail = raw.rsplit("/", 1)[-1]
    elif re.fullmatch(r"[a-z]+:[A-Za-z]+_\w+", raw):
        tail = raw.split(":", 1)[1]
    else:
        return raw
    m = re.fullmatch(r"([A-Za-z]+)_(\w+)", tail)
    return f"{m.group(1)}:{m.group(2)}" if m else raw


def stanzas(path: pathlib.Path) -> Iterator[dict]:
    """The [Term] stanzas of an OBO file: id, name, obsolete, replaced_by, xrefs (target, source
    tags)."""
    cur: dict | None = None

    def done(c: dict | None) -> Iterator[dict]:
        if c is not None and "id" in c:
            yield c

    with path.open() as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("["):
                yield from done(cur)
                cur = {"name": "", "obsolete": False, "replaced_by": [], "xrefs": []} \
                    if line == "[Term]" else None
            elif cur is None:
                continue
            elif line.startswith("id: "):
                cur["id"] = term_id(line[4:])
            elif line.startswith("name: "):
                cur["name"] = line[6:].strip()
            elif line.startswith("is_obsolete: true"):
                cur["obsolete"] = True
            elif line.startswith("replaced_by: "):
                cur["replaced_by"].append(term_id(line[13:]))
            elif line.startswith("xref: "):
                m = XREF.match(line)
                cur["xrefs"].append((m.group(1), tuple(re.findall(r'source="([^"]+)"',
                                                                  m.group(2) or ""))))
    yield from done(cur)


def canonical(tid: str, collision: Mapping[str, frozenset[str]]) -> frozenset[str]:
    return collision.get(tid, frozenset({tid}))


def phenotype_cross_references(mondo: list[dict], live_labels: Mapping[str, str],
                               collision: Mapping[str, frozenset[str]]
                               ) -> tuple[list[dict], dict]:
    """(rows, counts). `mondo` are the stanzas of the pinned MONDO file; `live_labels` maps
    every live outcome term the verifier can return (MONDO, EFO, HP, OBA, Orphanet) to its
    label."""
    linked: dict[str, set[str]] = collections.defaultdict(set)
    tags: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for t in mondo:
        if t["obsolete"] or not t["id"].startswith("MONDO:") or t["id"] not in live_labels:
            continue
        for target, sources in t["xrefs"]:
            used = [s for s in sources if s in HP_TAGS]
            if not target.startswith("HP:") or not used or target not in live_labels:
                continue
            for c in canonical(t["id"], collision):
                linked[target].add(c)
                tags[(target, c)].update(used)
    rows = []
    for hp in sorted(linked):
        terms = sorted(linked[hp])
        if len(terms) != 1 or not terms[0].startswith(("MONDO:", "EFO:")):
            continue
        rows.append({"phenotype_id": hp, "phenotype_label": live_labels[hp],
                     "canonical_id": terms[0], "canonical_label": live_labels.get(terms[0], ""),
                     "xref_tags": "|".join(sorted(tags[(hp, terms[0])]))})
    counts = {"phenotype_terms_cross_referenced": len(linked), "rows": len(rows),
              "phenotype_terms_with_several_canonical_terms": sum(
                  len(v) > 1 for v in linked.values()),
              "by_tag": dict(sorted(collections.Counter(r["xref_tags"] for r in rows).items()))}
    return rows, counts


def replacement(tid: str, terms: Mapping[str, dict]) -> str | None:
    """The live term at the end of a term's `replaced_by` chain, or None when the chain forks,
    ends at an obsolete or unknown term, or is longer than MAX_REPLACEMENT_STEPS."""
    for _ in range(MAX_REPLACEMENT_STEPS):
        t = terms.get(tid)
        if t is None:
            return None
        if not t["obsolete"]:
            return tid
        if len(t["replaced_by"]) != 1:
            return None
        tid = t["replaced_by"][0]
    return None


def obsolete_label_replacements(efo: list[dict], terms: Mapping[str, dict],
                                names_in_use: Mapping[str, object], live: Collection[str],
                                fold: Callable[[str], str]) -> tuple[list[dict], dict]:
    """(rows, counts). `efo` are the stanzas of the pinned EFO file, `terms` every stanza of both
    files by identifier, `names_in_use` the folded labels and exact synonyms of the live terms,
    `live` the terms the verifier can return, and `fold` the verifier's name folding."""
    found: dict[str, dict[str, dict]] = collections.defaultdict(dict)
    counts: collections.Counter = collections.Counter()
    for t in efo:
        if not t["obsolete"] or not t["id"].startswith("EFO:"):
            continue
        counts["obsolete_efo_terms"] += 1
        label = OBSOLETE_PREFIX.sub("", t["name"]).strip()
        key = fold(label)
        if len(key) < 2:
            counts["label_too_short"] += 1
            continue
        if len(t["replaced_by"]) != 1:
            counts["no_single_replacement"] += 1
            continue
        new = replacement(t["id"], terms)
        if new is None or new not in live or not new.startswith(OUTCOME_PREFIXES):
            counts["replacement_not_a_live_outcome_term"] += 1
            continue
        if key in names_in_use:
            counts["label_is_a_live_name"] += 1
            continue
        found[key][new] = {"surface": label, "obsolete_id": t["id"], "term_id": new,
                           "term_label": terms[new]["name"]}
    rows = []
    for key in sorted(found):
        if len(found[key]) != 1:
            counts["label_with_several_replacements"] += 1
            continue
        rows.append(next(iter(found[key].values())))
    counts["rows"] = len(rows)
    counts.update({f"rows_replaced_by_{p.rstrip(':')}": sum(r["term_id"].startswith(p)
                                                            for r in rows)
                   for p in OUTCOME_PREFIXES})
    return rows, dict(counts)


def icd10_terms(mondo: list[dict], collision: Mapping[str, frozenset[str]]
                ) -> dict[str, frozenset[str]]:
    """ICD-10 code -> the canonical terms whose live MONDO stanza cross-references it as
    equivalent."""
    out: dict[str, set[str]] = collections.defaultdict(set)
    for t in mondo:
        if t["obsolete"] or not t["id"].startswith("MONDO:"):
            continue
        for target, sources in t["xrefs"]:
            prefix, _, code = target.partition(":")
            if prefix in ICD_PREFIXES and ICD_TAG in sources:
                out[code] |= canonical(t["id"], collision)
    return {k: frozenset(v) for k, v in out.items()}


def write_rows(path: pathlib.Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
