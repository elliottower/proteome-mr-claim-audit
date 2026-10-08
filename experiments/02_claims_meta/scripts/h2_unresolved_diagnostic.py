# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pydantic==2.13.5"]
# ///
"""Why repeated pairs are unresolved under H2 and H2b, in counts (PREREG.md log, 2026-10-08).
A diagnostic made after the outcomes were seen, to plan a possible separately registered
follow-up. It changes no registered result and no verdict, classifies nothing anew, and reads
no file that the stage 5 run did not read, apart from stored passages and stored texts that it
only searches for patterns. Counts only: no dataset name, sentence or other third-party text is
written.

The registry is built from the claim file of an assembly by `build_registry.build`, and each
multi-family pair is classed by `pair_h2` and `pair_overlap`, as the registered tables are; the
counts of pairs and of unresolved pairs must equal the counts given with `--expect`, or the
script stops.

A dataset mention is one record, side and name as written (the unit of the manual-coding
queue). For an unresolved pair, a mention of one of its families blocks:
    H2     when its name does not map to exactly one dictionary row
    H2b    when its name is `not_stated` or unmatched, or its composition is not resolved
A family whose dataset attribution is unclear blocks whatever its names are (`attribution`
block): no mention's resolution lifts it. A pair is `resolved by rows` when every blocking
mention of it is resolved and no family of it has an attribution block; resolving every
blocking mention is enough to class the pair and is not always needed (one comparison that is
known to differ already classes a pair for H2).

Reported for each hypothesis: unresolved pairs; blocking mentions and their papers; pairs
blocked per mention; pairs resolved by the k mentions that block most pairs; mentions by side,
by manual-coding category and by the resource their candidate dictionary rows are releases of; pairs
unresolved on one side only; and, for the blocking mentions, what the stored material holds,
found by pattern and counted: a sample size or case and control count, a GWAS accession, a
link to a code repository, a mention of supplementary material, in the passages given to the
coders for the mention and anywhere in the paper's stored text (the full text where one is on
disk, else the abstract).

Usage: uv run scripts/h2_unresolved_diagnostic.py --claims <registry_claims.jsonl> \\
           --codes <extended table of the queue> --passages <dir> [...] --fulltext <dir> [...] \\
           --abstracts <jsonl> [...] --records <search_records.jsonl> [...] \\
           --expect <pairs>,<h2 unresolved>,<h2b unresolved> --out <json>
"""

import argparse
import collections
import csv
import datetime
import hashlib
import itertools
import json
import pathlib
import re

from build_registry import (FamilyPair, RegistryClaim, build, family_release_identity,
                            pair_h2, pair_overlap, side_overlap)
from dataset_relations import NameMapping, load_rows, map_name

SIDES = ("pqtl", "outcome")
TOP = (10, 25, 50, 100)
PATTERNS = {
    "sample_size_or_case_control_count": re.compile(
        r"\b(?:n\s*=\s*\d[\d,\s  ]{2,}|\d[\d,  ]{2,}\d\s+"
        r"(?:cases|controls|participants|individuals|samples|subjects))", re.I),
    "gwas_accession": re.compile(
        r"\b(?:ukb-[a-z]-\w+|finn-[a-z]-\w+|ebi-a-GCST\d+|GCST\d{6,}|ieu-[a-z]-\w+)", re.I),
    "code_repository_link": re.compile(r"github\.com|gitlab\.com|bitbucket\.org|codeocean", re.I),
    "supplementary_material_mention": re.compile(r"supplement", re.I)}
Mention = tuple[str, str, str]


class DiagnosticError(Exception):
    """The registry built here does not give the counts of the registered table."""


def record_of(claim: RegistryClaim) -> str:
    return claim.claim_record_id.rsplit(":", 1)[0]


def blocks(m: NameMapping, hypothesis: str) -> bool:
    if hypothesis == "h2":
        return m.state != "unique"
    return m.state in ("not_stated", "unmatched") or not m.composition_resolved


def sides_undetermined(fams: dict[str, FamilyPair], hypothesis: str) -> set[str]:
    """The sides on which some comparison of two families is not determined."""
    out = set()
    for a, b in itertools.combinations(sorted(fams), 2):
        for side in SIDES:
            state = (family_release_identity(fams[a], fams[b], side) if hypothesis == "h2"
                     else side_overlap(fams[a], fams[b], side))
            if state in ("undetermined", "unclear"):
                out.add(side)
    return out


def coverage(blocked: dict[tuple, set[Mention]], barred: set[tuple]) -> dict:
    """Pairs per mention, and pairs resolved by the k mentions that block most pairs. `barred`
    pairs have an attribution block and are resolved by no set of mentions."""
    per = collections.Counter(m for ms in blocked.values() for m in ms)
    order = [m for m, _ in sorted(per.items(), key=lambda kv: (-kv[1], kv[0]))]
    open_pairs = {p: ms for p, ms in blocked.items() if p not in barred}

    def resolved(k: int) -> int:
        top = set(order[:k])
        return sum(ms <= top for ms in open_pairs.values())

    counts = sorted(per.values(), reverse=True)
    return {"blocking_mentions": len(per),
            "pairs_blocked_per_mention": {
                "max": counts[0] if counts else 0,
                "median": counts[len(counts) // 2] if counts else 0,
                "distribution": dict(sorted(collections.Counter(counts).items()))},
            "pairs_resolved_by_the_top_mentions": {str(k): resolved(k) for k in TOP},
            "pairs_resolved_by_every_blocking_mention": resolved(len(order)),
            "mentions_needed_to_resolve_every_pair_that_mentions_can_resolve": len(
                set().union(*open_pairs.values())) if open_pairs else 0,
            "pairs_with_an_attribution_block": len(barred & set(blocked)),
            "pairs_with_no_blocking_mention_and_no_attribution_block": sum(
                not ms for p, ms in open_pairs.items()),
            "order": order}


def common_prefix(candidates: tuple[str, ...]) -> str:
    """The words the candidate dictionary rows of a name begin with in common (the resource
    they are releases of), from the dictionary's own row names."""
    names = [c.split() for c in candidates if not c.startswith("unlisted release of ")]
    if not names:
        return "unlisted release only"
    shared = []
    for words in zip(*names):
        if len(set(words)) != 1:
            break
        shared.append(words[0])
    return " ".join(shared) or "candidate rows of several resources"


def found(text: str) -> dict[str, bool]:
    return {name: bool(p.search(text)) for name, p in PATTERNS.items()}


def diagnose(claims: list[RegistryClaim], category: dict[Mention, str],
             passages: dict[Mention, str], paper_text: dict[str, tuple[str, str]]) -> dict:
    """`category`: queue row -> manual-coding category; `passages`: queue row -> the text of
    its passages; `paper_text`: record -> (`full_text` or `abstract`, text)."""
    rows = load_rows()
    registry = build(claims, rows)
    mentions: dict[tuple, dict[str, set[Mention]]] = collections.defaultdict(
        lambda: collections.defaultdict(set))
    for c in claims:
        for side, names in (("pqtl", c.pqtl_datasets), ("outcome", c.outcome_datasets)):
            for name in names:
                mentions[(c.protein_id, c.outcome_id)][c.family_id].add(
                    (record_of(c), side, name))
    multi = {p: f for p, f in registry.items() if len(f) > 1}
    out: dict = {"multi_family_pairs": len(multi)}
    for hyp, classify in (("h2", pair_h2), ("h2b", pair_overlap)):
        unresolved = {p: f for p, f in multi.items() if classify(f) == "unresolved"}
        blocked: dict[tuple, set[Mention]] = {}
        barred: set[tuple] = set()
        one_side: collections.Counter = collections.Counter()
        for pair, fams in unresolved.items():
            blocked[pair] = {m for fam in fams for m in mentions[pair][fam]
                             if blocks(map_name(m[2], m[1], rows), hyp)}
            if not all(f.attribution_clear for f in fams.values()):
                barred.add(pair)
            sides = sides_undetermined(fams, hyp)
            one_side["both sides" if len(sides) == 2 else f"{next(iter(sides))} side only"
                     if sides else "no side undetermined"] += 1
        cover = coverage(blocked, barred)
        order = cover.pop("order")
        every = set(order)
        mapped = {m: map_name(m[2], m[1], rows) for m in every}

        def label(m: Mention) -> str:
            if m[2].strip() == "not_stated":
                return "never queued: no dataset named"
            if mapped[m].state == "unique":
                return "never queued: maps to one dictionary row"
            return category.get(m, "never queued: named, not in the queue")

        def resource(m: Mention) -> str:
            got = mapped[m]
            if got.state == "not_stated":
                return "no dataset named"
            if got.state == "unmatched":
                return "named, no dictionary candidate"
            return common_prefix(got.candidates)

        def stored(which: set[Mention]) -> dict:
            in_passages = collections.Counter()
            in_paper = collections.Counter()
            kinds = collections.Counter()
            for m in which:
                for name, hit in found(passages.get(m, "")).items():
                    in_passages[name] += hit
                kind, text = paper_text.get(m[0], ("no stored text", ""))
                kinds[kind] += 1
                for name, hit in found(text).items():
                    in_paper[name] += hit
            return {"mentions": len(which),
                    "mentions_with_passages_given_to_the_coders": sum(m in passages
                                                                      for m in which),
                    "in_the_mention_s_passages": {n: in_passages[n] for n in PATTERNS},
                    "anywhere_in_the_paper_s_stored_text": {n: in_paper[n] for n in PATTERNS},
                    "stored_text_of_the_paper": dict(sorted(kinds.items()))}

        out[hyp] = {
            "unresolved_pairs": len(unresolved),
            "blocking_papers": len({m[0] for m in every}),
            **cover,
            "unresolved_pairs_by_undetermined_side": dict(sorted(one_side.items())),
            "blocking_mentions_by_side": dict(collections.Counter(m[1] for m in every)),
            "blocking_mentions_by_mapping_state": dict(collections.Counter(
                mapped[m].state for m in every)),
            "blocking_mentions_by_manual_coding_category": dict(sorted(collections.Counter(
                label(m) for m in every).items())),
            "blocking_mentions_by_side_and_category": {
                side: dict(sorted(collections.Counter(
                    label(m) for m in every if m[1] == side).items())) for side in SIDES},
            "blocking_mentions_by_resource_of_the_candidate_rows": dict(sorted(collections.Counter(
                resource(m) for m in every).items(), key=lambda kv: -kv[1])),
            "stored_material_for_the_blocking_mentions": stored(every),
            "stored_material_for_the_blocking_mentions_that_name_a_dataset": stored(
                {m for m in every if m[2].strip() != "not_stated"}),
            "top_mentions_by_side_and_category": {
                str(k): dict(sorted(collections.Counter(
                    f"{m[1]}: {label(m)}" for m in order[:k]).items())) for k in TOP}}
    return out


def read_passages(folders: list[pathlib.Path]) -> dict[Mention, str]:
    out = {}
    for folder in folders:
        for path in sorted(folder.glob("*.json")):
            made = json.loads(path.read_text())
            if "record_id" not in made:
                continue
            for row in made["rows"]:
                out[(made["record_id"], row["side"], row["name_as_written"])] = "\n".join(
                    [s for p in row["passages"] for s in p["sentences"]]
                    + [r["entry"] for p in row["passages"] for r in p["references"]])
    return out


def read_paper_text(records: list[pathlib.Path], fulltext: list[pathlib.Path],
                    abstracts: list[pathlib.Path]) -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    for path in abstracts:
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                out.setdefault(r["pmid"], ("abstract", r["abstract"]))
    pmid_of = {}
    for path in records:
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("pmid"):
                    pmid_of.setdefault(str(r["pmid"]), r["record_id"])
    for folder in fulltext:
        for path in sorted(folder.glob("pmid*.jsonl")):
            body = json.loads(path.read_text().splitlines()[0])
            rid = pmid_of.get(str(body["pmid"]))
            if rid is not None:
                out[rid] = ("full_text", body["body"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims", type=pathlib.Path, required=True)
    ap.add_argument("--codes", type=pathlib.Path, required=True)
    for name in ("passages", "fulltext", "abstracts", "records"):
        ap.add_argument(f"--{name}", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--expect", required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise DiagnosticError(f"{a.out} exists; it is written once")
    claims = [RegistryClaim.model_validate_json(l) for l in a.claims.read_text().splitlines()
              if l.strip()]
    with a.codes.open(newline="") as f:
        category = {(r["record_id"], r["side"], r["name_as_written"]):
                    ("coded" if r["status"] == "coded" else r["unresolved_reason"])
                    for r in csv.DictReader(f)}
    made = diagnose(claims, category, read_passages(a.passages),
                    read_paper_text(a.records, a.fulltext, a.abstracts))
    expected = [int(x) for x in a.expect.split(",")]
    got = [made["multi_family_pairs"], made["h2"]["unresolved_pairs"],
           made["h2b"]["unresolved_pairs"]]
    if got != expected:
        raise DiagnosticError(f"pairs and unresolved pairs are {got}, not {expected}")
    files = [a.claims, a.codes]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({
        "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "note": "post-results diagnostic; counts only; changes no registered result or verdict",
        "inputs_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        "folders_read": {n: [str(p) for p in getattr(a, n)]
                         for n in ("passages", "fulltext", "abstracts", "records")},
        "claim_records": len(claims), "patterns": {k: p.pattern for k, p in PATTERNS.items()},
        **made}, indent=1) + "\n")
    print(json.dumps(made, indent=1))


if __name__ == "__main__":
    main()
