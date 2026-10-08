# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Restore, from the stored abstract, an evidence span that leaves out exactly one whole token
(PREREG.md, Amendment 2: the amended primary analysis is "source-restored and checked under the
registered verifier"). The model's output is never overwritten: this script writes a repair
map and a derived extraction file beside it. It prints counts only.

The rule is a predicate applied to every claim record of an extraction file, not a list. With
the abstract and the span each split at white space and case folded, as the registered quote
check folds them (scripts/verify_spans.py), a span is eligible when all of these hold:

    1. the registered quote check fails: the span is not one stretch of the abstract;
    2. the span's tokens are two runs, the first of k and the second of n - k tokens
       (1 <= k < n), that stand in the abstract in order with exactly one abstract token
       between them. The tokens at the junction and the token left out are whole abstract
       tokens. As in the registered check, the first token of the span may be the end of an
       abstract token and its last token the beginning of one;
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
`crosscheck` compares the map's passage hashes with hashes from another source (the
`citations` tool at the pinned commit: a JSON object record id -> sha256 of its restored
passage); every record must be present and equal, or it exits non-zero.
`transitions` compares the registered verifier's records before and after, in counts only: for
the restored records the transitions of protein mapping, outcome mapping, parsed direction,
verification method, registry eligibility and direction-result eligibility; for every other
record whether its line is identical, with the ids of any that differ.

Usage:
    uv run scripts/span_restoration.py restore --extraction <parsed jsonl> \\
        --abstracts <eligible_abstracts.jsonl> [...] --expected <json> --label <label> --out <dir>
    uv run scripts/span_restoration.py crosscheck --map <repair_map.json> --other <json>
    uv run scripts/span_restoration.py transitions --map <repair_map.json> \\
        --before <claim_checks.jsonl> --after <claim_checks.jsonl> --out <json>
"""

import argparse
import collections
import hashlib
import json
import pathlib
import re

RULE = "one_whole_token_omitted_unique_alignment"
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


def alignments(span: list[str], abstract: list[str]) -> list[tuple[int, int]]:
    """Every (i, k): the span's first k tokens stand at abstract[i:i+k] and the rest at
    abstract[i+k+1:], one abstract token left out. Junction tokens are whole; the span's first
    token may end an abstract token and its last token begin one."""
    n, out = len(span), []
    for i in range(len(abstract) - n):
        window = abstract[i:i + n + 1]
        for k in range(1, n):
            kept = window[:k] + window[k + 1:]

            def same(j: int) -> bool:
                if j == 0 and k > 1:
                    return kept[0].endswith(span[0])
                if j == n - 1 and k < n - 1:
                    return kept[-1].startswith(span[-1])
                return kept[j] == span[j]

            if all(same(j) for j in range(n)):
                out.append((i, k))
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
    hits = alignments(s, a)
    if len(hits) != 1:
        return None
    i, k = hits[0]
    first, last = found[i], found[i + len(s)]
    if len(first.group(0)) != len(a[i]) or len(last.group(0)) != len(a[i + len(s)]):
        return None  # case folding changed a boundary token's length: offsets would not hold
    start, end = first.end() - len(s[0]), last.start() + len(s[-1])
    return {"start": start, "end": end, "omitted_token_index_in_abstract": i + k,
            "omitted_after_span_token": k, "passage": abstract[start:end]}


def restore_file(rows: list[dict], abstracts: dict[str, str], script_sha: str
                 ) -> tuple[dict, list[dict]]:
    """(the repair map, the rows with eligible spans replaced)."""
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
                    "omitted_after_span_token": made["omitted_after_span_token"],
                    "rule": RULE, "script_sha256": script_sha}
                claim["evidence_span"] = made["passage"]
        out.append(new)
    return repairs, out


def transition_counts(repairs: dict, before: list[dict], after: list[dict]) -> dict:
    """Counts of what changed in the verifier's records; ids, no text."""
    old = {r["claim_record_id"]: r for r in before}
    new = {r["claim_record_id"]: r for r in after}
    if list(old) != list(new):
        raise RestorationError("the two runs do not hold the same records in the same order")
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
    return {"restored_records": len(repairs),
            "restored_with_every_listed_field_unchanged": same,
            "transitions": {k: dict(sorted(v.items())) for k, v in sorted(restored.items())},
            "restored_entering_registry_before": sum(old[r]["enters_registry"] for r in repairs),
            "restored_entering_registry_after": sum(new[r]["enters_registry"] for r in repairs),
            "restored_in_direction_results_after": sum(
                new[r]["enters_direction_results"] for r in repairs),
            "other_records": len(old) - len(repairs),
            "other_records_differing": sorted(others),
            "other_records_differing_share_a_paper_with_a_restored_record": sum(
                r.split(":")[0] in {x.split(":")[0] for x in repairs} for r in others)}


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
    c = sub.add_parser("crosscheck")
    c.add_argument("--map", type=pathlib.Path, required=True)
    c.add_argument("--other", type=pathlib.Path, required=True)
    t = sub.add_parser("transitions")
    for name in ("map", "before", "after", "out"):
        t.add_argument(f"--{name}", type=pathlib.Path, required=True)
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
        repairs, restored = restore_file(rows, abstracts, script_sha)
        expected = sorted(json.loads(a.expected.read_text())["files"][a.label])
        if sorted(repairs) != expected:
            raise RestorationError(
                f"eligible records ({len(repairs)}) are not the expected ones ({len(expected)}): "
                f"{len(set(repairs) - set(expected))} not expected, "
                f"{len(set(expected) - set(repairs))} expected and not eligible")
        a.out.mkdir(parents=True)
        (a.out / "repair_map.json").write_text(json.dumps(
            {"rule": RULE, "extraction": str(a.extraction),
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
        ours = {k: v["restored_passage_sha256"]
                for k, v in json.loads(a.map.read_text())["repairs"].items()}
        theirs = json.loads(a.other.read_text())
        differing = sorted(k for k in set(ours) | set(theirs) if ours.get(k) != theirs.get(k))
        print(json.dumps({"records": len(ours), "equal": len(ours) - len(
            [k for k in differing if k in ours]), "differing_or_missing": len(differing)}))
        if differing:
            raise SystemExit("the two restorations differ: stop")
    else:
        if a.out.exists():
            raise RestorationError(f"{a.out} exists")
        made = transition_counts(json.loads(a.map.read_text())["repairs"],
                                 read_jsonl(a.before), read_jsonl(a.after))
        a.out.write_text(json.dumps(made, indent=1) + "\n")
        print(json.dumps(made, indent=1))


if __name__ == "__main__":
    main()
