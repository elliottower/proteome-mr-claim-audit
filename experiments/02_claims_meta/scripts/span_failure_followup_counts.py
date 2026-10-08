# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Two count-only looks at the evidence spans that failed the stage 4 span check (PREREG.md,
Amendment 2). No span, abstract or claim text is written or printed: counts only.

`duplicates`: among the records whose span stands in the abstract more than once, whether the
extraction returned the same claim more than once. Per paper, the number of those records, the
number of distinct claims as written (protein, outcome and direction as written), the number
of distinct claims after mapping (protein identifiers, outcome identifiers, direction), and the
same for the records that pass the other claim-level criteria. Records beyond the distinct
count are duplicates.

`omissions`: for the records whose span is two pieces of the abstract joined, whether the
text left out between the two pieces holds a negation or contrast token. The tokens are fixed
here: no, not, without, however, but, whereas, and the phrase "in contrast". A token is matched
as a whole word, case folded; the phrase as its two words one after the other. The omitted
text is the abstract's tokens between the end of the first piece and the start of the second,
the pieces found as scripts/classify_failed_spans.py finds them.

Usage: uv run scripts/span_failure_followup_counts.py --classes <span_failure_classes.json> \\
           --spans <label>=<spans.jsonl> [...] --checks <label>=<claim_checks.jsonl> [...] \\
           --abstracts <eligible_abstracts.jsonl> [...] --out <json>
"""

import argparse
import collections
import json
import pathlib

from classify_failed_spans import tokens

WORDS = ("no", "not", "without", "however", "but", "whereas")
PHRASES = (("in", "contrast"),)


def runs(span: list[str], abstract: list[str]) -> list[tuple[int, int]]:
    """(start in the abstract, length) of the greedy longest runs that make up the span."""
    out, i = [], 0
    while i < len(span):
        best, at = 0, -1
        for j in range(len(abstract)):
            k = 0
            while i + k < len(span) and j + k < len(abstract) and span[i + k] == abstract[j + k]:
                k += 1
            if k > best:
                best, at = k, j
        if best == 0:
            return []
        out.append((at, best))
        i += best
    return out


def omitted(span: str, abstract: str) -> list[str] | None:
    """The abstract's tokens left out between two pieces in order, or None when the span is
    not two such pieces."""
    at = tokens(abstract)
    found = runs(tokens(span), at)
    if len(found) != 2 or found[0][0] + found[0][1] > found[1][0]:
        return None
    return at[found[0][0] + found[0][1]:found[1][0]]


def contrast_tokens(words: list[str]) -> list[str]:
    """The fixed tokens and phrases the words hold, each once."""
    folded = [w.casefold() for w in words]
    hit = [w for w in WORDS if w in folded]
    hit += [" ".join(p) for p in PHRASES
            if any(tuple(folded[i:i + len(p)]) == p for i in range(len(folded)))]
    return hit


def would_enter(check: dict) -> bool:
    return (check["evidence_type"] == "mr_estimate" and check["protein_check"] == "pass"
            and check["outcome_check"] == "pass" and check["relation_ambiguous"] is not True)


def duplicate_counts(checks: list[dict]) -> dict:
    """Counts over the records of one paper."""
    def as_written(c):
        return (c["protein_as_written"], c["outcome_as_written"], c["direction"])

    def mapped(c):
        return (tuple(c["protein_ids"]), tuple(c["outcome_ids"]), c["direction"])

    entering = [c for c in checks if would_enter(c)]
    return {"records": len(checks), "distinct_as_written": len(set(map(as_written, checks))),
            "distinct_after_mapping": len(set(map(mapped, checks))),
            "records_passing_the_other_criteria": len(entering),
            "distinct_after_mapping_among_those": len(set(map(mapped, entering)))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--classes", type=pathlib.Path, required=True)
    ap.add_argument("--spans", nargs="+", required=True)
    ap.add_argument("--checks", nargs="+", required=True)
    ap.add_argument("--abstracts", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise FileExistsError(f"{a.out} exists; the counts are written once")
    classes = json.loads(a.classes.read_text())["files"]
    abstracts = {}
    for path in a.abstracts:
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                abstracts.setdefault(r["pmid"], r["abstract"])
    spans, checks = {}, {}
    for item in a.spans:
        label, path = item.split("=", 1)
        for r in map(json.loads, pathlib.Path(path).read_text().splitlines()):
            spans[(label, f"{r['pmid']}:{r['claim_index']:03d}")] = r
    for item in a.checks:
        label, path = item.split("=", 1)
        for r in map(json.loads, pathlib.Path(path).read_text().splitlines()):
            checks[(label, r["claim_record_id"])] = r
    by_paper: dict = collections.defaultdict(list)
    token_counts: collections.Counter = collections.Counter()
    segments = {"records": 0, "two_pieces_in_order": 0, "with_a_token": 0,
                "omitted_tokens_total": 0}
    for label, f in classes.items():
        for rid, made in f["classes"].items():
            if made["class"] == "in_abstract_more_than_once":
                by_paper[rid.split(":")[0]].append(checks[(label, rid)])
            elif made["class"] == "pieces_joined":
                segments["records"] += 1
                left_out = omitted(spans[(label, rid)]["evidence_span"],
                                   abstracts[rid.split(":")[0]])
                if left_out is None:
                    continue
                segments["two_pieces_in_order"] += 1
                segments["omitted_tokens_total"] += len(left_out)
                hit = contrast_tokens(left_out)
                segments["with_a_token"] += bool(hit)
                token_counts.update(hit)
    papers = [duplicate_counts(v) for _, v in sorted(by_paper.items(),
                                                     key=lambda kv: -len(kv[1]))]
    result = {"duplicates": {
        "papers": papers,
        "records": sum(p["records"] for p in papers),
        "distinct_after_mapping": sum(p["distinct_after_mapping"] for p in papers),
        "records_passing_the_other_criteria": sum(
            p["records_passing_the_other_criteria"] for p in papers),
        "distinct_after_mapping_among_those": sum(
            p["distinct_after_mapping_among_those"] for p in papers)},
        "omissions": {**segments, "tokens": list(WORDS) + [" ".join(p) for p in PHRASES],
                      "segments_by_token": dict(sorted(token_counts.items()))}}
    a.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
