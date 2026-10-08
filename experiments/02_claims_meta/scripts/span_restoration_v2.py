# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Restore, from the stored abstract, an evidence span that leaves out exactly one whole token
(PREREG.md, Amendment 2: the amended primary analysis is "source-restored and checked under the
registered verifier"). The model's output is never overwritten: this script writes a repair
map and a derived extraction file beside it. It prints counts only.

This copy supersedes scripts/span_restoration.py, which stays sealed. It differs in four
things. (a) A token is stated in the terms of the `citations` tool: a stretch of the stored
abstract between white space of the abstract's own, where a thin, narrow or no-break space
between two digits (`12 500`) is not white space, so a group of digits joined by such spaces is
one token: it is left out whole or not at all, and a part of it is never the token left out.
(b) `crosscheck` takes any number of other sources and both of their forms. (c) `transitions`
takes either a repair map or a list of record ids, names the set it counts, and can count a
second time with some records set apart. (d) `restore` can write the derived extraction file
with some eligible records left as the model wrote them (`--leave`), for a comparison.

The rule is a predicate applied to every claim record of an extraction file, not a list. With
the abstract and the span each split at white space and case folded, as the registered quote
check folds them (scripts/verify_spans.py), a span is eligible when all of these hold:

    1. the registered quote check fails: the span is not one stretch of the abstract;
    2. the span's tokens are two runs, the first of k and the second of n - k tokens
       (1 <= k < n), that stand in the abstract in order with exactly one abstract token
       between them. The tokens at the junction and the token left out are whole abstract
       tokens: white-space-delimited tokens of the abstract as the abstract has them, a group
       of digits joined by thin, narrow or no-break spaces being one token, so that a part of
       such a group is never what is left out. As in the registered check, the first token of
       the span may be the end of an abstract token and its last token the beginning of one;
    3. the alignment is unique: one position in the abstract and one k satisfy 2.

A changed sign, a truncated number, a substituted word, a compound cut inside a token, two or
more tokens left out, or an alignment that can be made in two ways is not eligible, and the
record stays failed. Eligibility does not look at what the record's verification will give.

The restored passage is the stored abstract's own text from the start of the first run to the
end of the second, nothing wider: its characters are taken from the stored abstract by offset.

`restore` evaluates the predicate over every claim record, checks that the eligible records
are exactly those of `--expected` (it stops otherwise, writing nothing), and writes:
    <out>/repair_map.json     per eligible record: sha256 of the original span and of the
                              restored passage, the record and sha256 of the stored abstract,
                              the offsets of the passage in it, the index of the token left
                              out (in the abstract and in the span), the rule and this
                              script's sha256; no text
    <out>/<stem>_restored.jsonl
                              the extraction rows with the evidence span of each eligible
                              record replaced by the restored passage, every other field and
                              every other record byte-identical in content
`crosscheck` compares the map's passage hashes with hashes from other sources (the `citations`
tool at the pinned commit, run by scripts/span_restoration_tool_side.py; a file of hashes made
with the tool elsewhere). A source is a JSON object record id -> sha256 of the restored
passage, or `{"records": {"<label>:<record id>": {"restored_passage_sha256", ...}}}`, of which
the records of `--label` are read; where a source gives `passage_start`, `passage_end` or
`source_sha256` these are compared too. Every record must be present and equal in every
source, or it exits non-zero.
`transitions` compares the verifier's records before and after, in counts only: for the
records of the map (or of `--ids`) the transitions of protein mapping, outcome mapping, parsed
direction, verification method, registry eligibility and direction-result eligibility; for
every other record whether its line is identical, with the ids of any that differ. With
`--apart`, the same counts are given a second time without the records named there.

Usage:
    uv run scripts/span_restoration_v2.py restore --extraction <parsed jsonl> \\
        --abstracts <eligible_abstracts.jsonl> [...] --expected <json> --label <label> \\
        --out <dir> [--leave <record id> ...]
    uv run scripts/span_restoration_v2.py crosscheck --map <repair_map.json> --label <label> \\
        --other <json> [...] --out <json>
    uv run scripts/span_restoration_v2.py transitions (--map <repair_map.json> | --ids <id> ...) \\
        --set <name> --before <claim_checks.jsonl> --after <claim_checks.jsonl> --out <json> \\
        [--apart <record id> ...]
"""

import argparse
import collections
import hashlib
import json
import pathlib
import re
import unicodedata

RULE = "one_whole_token_omitted_unique_alignment"
RULE_VERSION = 2  # tokens in the terms of the citations tool (digit groups are one token)
FIELDS = ("protein_mapping_state", "outcome_mapping_state", "parsed_direction",
          "direction_method", "enters_registry", "enters_direction_results",
          "direction_check", "first_failure")


class RestorationError(Exception):
    """The eligible records are not the expected ones, or an output exists."""


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def fold(text: str) -> str:
    """The folding of the registered quote check."""
    return " ".join(text.split()).casefold()


def groups_digits(text: str, start: int, end: int) -> bool:
    """Whether text[start:end], the white space between two words, is one thin, narrow or
    no-break space standing between two digits: the two words are then one token."""
    return (end - start == 1 and text[start] != " "
            and unicodedata.category(text[start]) == "Zs"
            and 0 < start < len(text) - 1
            and text[start - 1].isdigit() and text[end].isdigit())


def tokens(text: str, words: list[re.Match]) -> list[tuple[int, int]]:
    """The tokens of `text` as runs of its white-space words: (first word, one past the last).
    Words joined by a digit-grouping space are one token."""
    out: list[tuple[int, int]] = []
    for j in range(len(words)):
        if out and groups_digits(text, words[j - 1].end(), words[j].start()):
            out[-1] = (out[-1][0], j + 1)
        else:
            out.append((j, j + 1))
    return out


def alignments(span: list[str], abstract: list[str], whole: list[tuple[int, int]]
               ) -> list[tuple[int, int, int, int]]:
    """Every (i, k, p, q): the span's first k words stand at abstract[i:p] (p = i + k) and the
    rest at abstract[q:], the one token abstract[p:q] left out. `whole` gives the abstract's
    tokens as runs of its words, so the junction words are ends of whole tokens. The span's
    first word may end an abstract word and its last word begin one."""
    n, out = len(span), []
    for p, q in whole:
        for k in range(1, n):
            i = p - k
            if i < 0 or q + n - k > len(abstract):
                continue
            kept = abstract[i:p] + abstract[q:q + n - k]

            def same(j: int) -> bool:
                if j == 0 and k > 1:
                    return kept[0].endswith(span[0])
                if j == n - 1 and k < n - 1:
                    return kept[-1].startswith(span[-1])
                return kept[j] == span[j]

            if all(same(j) for j in range(n)):
                out.append((i, k, p, q))
    return out


def restore_span(span: str, abstract: str) -> dict | None:
    """The restoration of one span, or None when it is not eligible. Offsets are in the
    stored abstract."""
    if fold(span) in fold(abstract):
        return None
    found = list(re.finditer(r"\S+", abstract))
    a = [m.group(0).casefold() for m in found]
    s = [t.casefold() for t in span.split()]
    if len(s) < 2:
        return None
    hits = alignments(s, a, tokens(abstract, found))
    if len(hits) != 1:
        return None
    i, k, p, q = hits[0]
    first, last = found[i], found[q + len(s) - k - 1]
    if len(first.group(0)) != len(a[i]) or len(last.group(0)) != len(a[q + len(s) - k - 1]):
        return None  # case folding changed a boundary token's length: offsets would not hold
    start, end = first.end() - len(s[0]), last.start() + len(s[-1])
    return {"start": start, "end": end, "omitted_token_index_in_abstract": p,
            "omitted_token_words": q - p, "omitted_after_span_token": k,
            "passage": abstract[start:end]}


def restore_file(rows: list[dict], abstracts: dict[str, str], script_sha: str,
                 leave: frozenset[str] = frozenset()) -> tuple[dict, list[dict]]:
    """(the repair map, the rows with eligible spans replaced). A record named in `leave` is
    in the map and keeps the span the model wrote."""
    repairs, out = {}, []
    for row in rows:
        new = json.loads(json.dumps(row))
        if row["status"] == "ok":
            abstract = abstracts[row["pmid"]]
            for index, claim in enumerate(new["output"]["claims"]):
                made = restore_span(claim["evidence_span"], abstract)
                if made is None:
                    continue
                repairs[f"{row['pmid']}:{index:03d}"] = {
                    "record": row["pmid"], "source_sha256": sha(abstract),
                    "original_span_sha256": sha(claim["evidence_span"]),
                    "restored_passage_sha256": sha(made["passage"]),
                    "source_offsets": [made["start"], made["end"]],
                    "omitted_token_index_in_abstract": made["omitted_token_index_in_abstract"],
                    "omitted_token_words": made["omitted_token_words"],
                    "omitted_after_span_token": made["omitted_after_span_token"],
                    "rule": RULE, "rule_version": RULE_VERSION,
                    "script_sha256": script_sha,
                    "span_replaced_in_derived_file": f"{row['pmid']}:{index:03d}" not in leave}
                if f"{row['pmid']}:{index:03d}" not in leave:
                    claim["evidence_span"] = made["passage"]
        out.append(new)
    return repairs, out


def transition_counts(repairs, before: list[dict], after: list[dict],
                      name: str = "restored") -> dict:
    """Counts of what changed in the verifier's records for the records of `repairs` (ids),
    and whether every other record is the same; ids, no text."""
    old = {r["claim_record_id"]: r for r in before}
    new = {r["claim_record_id"]: r for r in after}
    if list(old) != list(new):
        raise RestorationError("the two runs do not hold the same records in the same order")
    if not set(repairs) <= set(old):
        raise RestorationError("a record of the set is in neither run")
    restored = collections.defaultdict(collections.Counter)
    same = 0
    for rid in repairs:
        a, b = old[rid], new[rid]
        same += all(a[f] == b[f] for f in FIELDS)
        for f in FIELDS:
            restored[f][f"{a[f]} -> {b[f]}"] += 1
        restored["protein_ids"]["same" if a["protein_ids"] == b["protein_ids"]
                                else "differ"] += 1
        restored["outcome_ids"]["same" if a["outcome_ids"] == b["outcome_ids"]
                                else "differ"] += 1
    others = [rid for rid in old if rid not in repairs and old[rid] != new[rid]]
    return {"set": name, f"{name}_records": len(repairs),
            f"{name}_with_every_listed_field_unchanged": same,
            "transitions": {k: dict(sorted(v.items())) for k, v in sorted(restored.items())},
            f"{name}_entering_registry_before": sum(old[r]["enters_registry"] for r in repairs),
            f"{name}_entering_registry_after": sum(new[r]["enters_registry"] for r in repairs),
            f"{name}_in_direction_results_before": sum(
                old[r]["enters_direction_results"] for r in repairs),
            f"{name}_in_direction_results_after": sum(
                new[r]["enters_direction_results"] for r in repairs),
            "other_records": len(old) - len(repairs),
            "other_records_differing": sorted(others),
            f"other_records_differing_share_a_paper_with_a_{name}_record": sum(
                r.split(":")[0] in {x.split(":")[0] for x in repairs} for r in others)}


def other_hashes(source: dict, label: str) -> dict[str, dict]:
    """record id -> what another source says of its restored passage."""
    if "records" not in source:
        return {k: {"restored_passage_sha256": v} for k, v in source.items()}
    return {k.split(":", 1)[1]: v for k, v in source["records"].items()
            if k.split(":", 1)[0] == label}


def crosscheck(repairs: dict, others: dict[str, dict[str, dict]]) -> dict:
    """Per other source: how many records are equal, and the ids that differ or are missing
    on either side. Equal means the same passage hash and, where the source gives them, the
    same offsets and the same source hash."""
    out = {}
    for name, theirs in others.items():
        differing = []
        for rid in sorted(set(repairs) | set(theirs)):
            ours, other = repairs.get(rid), theirs.get(rid)
            same = ours is not None and other is not None and (
                ours["restored_passage_sha256"] == other["restored_passage_sha256"]
                and other.get("passage_start", ours["source_offsets"][0])
                == ours["source_offsets"][0]
                and other.get("passage_end", ours["source_offsets"][1])
                == ours["source_offsets"][1]
                and other.get("source_sha256", ours["source_sha256"]) == ours["source_sha256"])
            if not same:
                differing.append(rid)
        out[name] = {"records_in_map": len(repairs), "records_in_source": len(theirs),
                     "equal": len(set(repairs) | set(theirs)) - len(differing),
                     "differing_or_missing": differing}
    return out


def read_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    r = sub.add_parser("restore")
    r.add_argument("--extraction", type=pathlib.Path, required=True)
    r.add_argument("--abstracts", type=pathlib.Path, nargs="+", required=True)
    r.add_argument("--expected", type=pathlib.Path, required=True)
    r.add_argument("--label", required=True)
    r.add_argument("--out", type=pathlib.Path, required=True)
    r.add_argument("--leave", nargs="*", default=[])
    c = sub.add_parser("crosscheck")
    c.add_argument("--map", type=pathlib.Path, required=True)
    c.add_argument("--label", required=True)
    c.add_argument("--other", type=pathlib.Path, nargs="+", required=True)
    c.add_argument("--out", type=pathlib.Path, required=True)
    t = sub.add_parser("transitions")
    for name in ("before", "after", "out"):
        t.add_argument(f"--{name}", type=pathlib.Path, required=True)
    t.add_argument("--map", type=pathlib.Path)
    t.add_argument("--ids", nargs="*")
    t.add_argument("--set", required=True)
    t.add_argument("--apart", nargs="*", default=[])
    a = ap.parse_args()
    if a.command == "restore":
        if a.out.exists():
            raise RestorationError(f"{a.out} exists; a restoration is written once")
        abstracts = {}
        for path in a.abstracts:
            for rec in read_jsonl(path):
                abstracts.setdefault(rec["pmid"], rec["abstract"])
        script_sha = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
        rows = read_jsonl(a.extraction)
        if not set(a.leave) <= set(json.loads(a.expected.read_text())["files"][a.label]):
            raise RestorationError("a record to leave is not an expected record")
        repairs, restored = restore_file(rows, abstracts, script_sha, frozenset(a.leave))
        expected = sorted(json.loads(a.expected.read_text())["files"][a.label])
        if sorted(repairs) != expected:
            raise RestorationError(
                f"eligible records ({len(repairs)}) are not the expected ones ({len(expected)}): "
                f"{len(set(repairs) - set(expected))} not expected, "
                f"{len(set(expected) - set(repairs))} expected and not eligible")
        a.out.mkdir(parents=True)
        (a.out / "repair_map.json").write_text(json.dumps(
            {"rule": RULE, "rule_version": RULE_VERSION, "extraction": str(a.extraction),
             "spans_left_as_written": sorted(a.leave),
             "extraction_sha256": hashlib.sha256(a.extraction.read_bytes()).hexdigest(),
             "claim_records": sum(len(r["output"]["claims"]) for r in rows
                                  if r["status"] == "ok"),
             "repairs": repairs}, indent=1) + "\n")
        target = a.out / f"{a.extraction.stem}_restored.jsonl"
        target.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in restored))
        print(json.dumps({"claim_records_evaluated": sum(
            len(r["output"]["claims"]) for r in rows if r["status"] == "ok"),
            "restored": len(repairs), "papers": len({v["record"] for v in repairs.values()})}))
    elif a.command == "crosscheck":
        if a.out.exists():
            raise RestorationError(f"{a.out} exists")
        made = crosscheck(json.loads(a.map.read_text())["repairs"],
                          {str(p): other_hashes(json.loads(p.read_text()), a.label)
                           for p in a.other})
        made = {"map": str(a.map),
                "map_sha256": hashlib.sha256(a.map.read_bytes()).hexdigest(),
                "sources_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in a.other},
                "label": a.label, "sources": made,
                "all_equal": all(not v["differing_or_missing"] for v in made.values())}
        a.out.write_text(json.dumps(made, indent=1) + "\n")
        print(json.dumps(made, indent=1))
        if not made["all_equal"]:
            raise SystemExit("the restorations differ: stop")
    else:
        if a.out.exists():
            raise RestorationError(f"{a.out} exists")
        if (a.map is None) == (a.ids is None):
            raise RestorationError("give the records by --map or by --ids, one of the two")
        ids = list(json.loads(a.map.read_text())["repairs"]) if a.map else list(a.ids)
        before, after = read_jsonl(a.before), read_jsonl(a.after)
        made = transition_counts(ids, before, after, a.set)
        if a.apart:
            if not set(a.apart) <= set(ids):
                raise RestorationError("a record set apart is not a record of the set")
            made[f"without_{len(a.apart)}_records_set_apart"] = {
                "set_apart": sorted(a.apart),
                **{k: v for k, v in transition_counts(
                    [i for i in ids if i not in a.apart], before, after, a.set).items()
                   if not k.startswith("other_records")}}
        a.out.write_text(json.dumps(made, indent=1) + "\n")
        print(json.dumps(made, indent=1))


if __name__ == "__main__":
    main()
