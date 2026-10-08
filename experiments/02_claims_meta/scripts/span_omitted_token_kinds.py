# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""The kind of the abstract token left out of each evidence span that is two pieces of its
abstract joined (PREREG.md log, 2026-10-08). Count-only and descriptive: no rule changes and no
record's status changes. No token, span or abstract text is written or printed.

The two pieces and the tokens between them are found as
scripts/span_failure_followup_counts.py finds them (tokens are runs of letters and digits, a
full stop or comma inside a run kept; so a punctuation mark alone is never a token). A record
with exactly one token left out takes the first class that applies; a record with none or
several is counted apart (`not_one_token`).

    digit/citation_marker   the token holds a digit, is digits only, and stands directly inside
                            square brackets or parentheses
    digit/signed_percent_or_unit
                            it holds a digit and has a sign (+ - ± < > = ≤ ≥ ~) directly
                            before it, a percent sign directly after it, or a letter in it
    digit/bare_number       it holds a digit, otherwise
    punctuation_or_symbol   no letter and no digit (cannot occur with this tokeniser; kept so
                            the list is complete)
    single_letter           one letter, Latin or Greek
    word/article_or_determiner      a, an, the, this, these, that, those
    word/conjunction_or_preposition and, or, of, in, on, with, for, to, by, as, at, from
    word/intensifier_or_hedge       significantly, strongly, potentially, possibly, likely,
                                    may, might, could
    word/other              any other token of letters only
    other                   anything else

A superscript citation number written straight after a word or a full stop is part of that
word's token here and cannot be told apart.

Also counted, per class: the records that pass the other claim-level criteria; where the gap
falls in the span (the first piece's share of the span's tokens: under a tenth, over nine
tenths, or between); and whether the token before or after the omitted one in the abstract
holds a digit.

Usage: uv run scripts/span_omitted_token_kinds.py --classes <span_failure_classes.json> \\
           --spans <label>=<spans.jsonl> [...] --checks <label>=<claim_checks.jsonl> [...] \\
           --abstracts <eligible_abstracts.jsonl> [...] --out <json>
"""

import argparse
import collections
import json
import pathlib
import re

from classify_failed_spans import tokens, unmarked
from span_failure_followup_counts import runs, would_enter

TOKEN = re.compile(r"[^\W_]+(?:[.,][^\W_]+)*")
ARTICLES = frozenset("a an the this these that those".split())
CONNECTIVES = frozenset("and or of in on with for to by as at from".split())
HEDGES = frozenset("significantly strongly potentially possibly likely may might could".split())
SIGNS = "+-±<>=≤≥~"


def kind(token: str, before: str, after: str) -> str:
    """The class of one omitted token, given the characters directly before and after it."""
    if any(c.isdigit() for c in token):
        if token.isdigit() and before[-1:] in "[(" and after[:1] in "])":
            return "digit/citation_marker"
        if before[-1:] in SIGNS or after[:1] == "%" or any(c.isalpha() for c in token):
            return "digit/signed_percent_or_unit"
        return "digit/bare_number"
    if not any(c.isalpha() for c in token):
        return "punctuation_or_symbol"
    if len(token) == 1:
        return "single_letter"
    if token.isalpha():
        return ("word/article_or_determiner" if token in ARTICLES
                else "word/conjunction_or_preposition" if token in CONNECTIVES
                else "word/intensifier_or_hedge" if token in HEDGES else "word/other")
    return "other"


def describe(span: str, abstract: str) -> dict:
    """The class and position of the omission of one span; no text."""
    text = unmarked(abstract)
    found = list(TOKEN.finditer(text))
    words = [m.group(0) for m in found]
    if words != tokens(abstract):
        raise ValueError("the abstract's tokens differ between the two tokenisations")
    pieces = runs(tokens(span), words)
    if len(pieces) != 2 or pieces[0][0] + pieces[0][1] > pieces[1][0]:
        return {"class": "not_two_pieces_in_order"}
    first_end, second_start = pieces[0][0] + pieces[0][1], pieces[1][0]
    gap = second_start - first_end
    share = pieces[0][1] / (pieces[0][1] + pieces[1][1])
    place = "first_tenth" if share < 0.1 else "last_tenth" if share > 0.9 else "middle"
    if gap != 1:
        return {"class": "not_one_token", "tokens_omitted": gap, "gap_position": place}
    m = found[first_end]
    neighbours = [words[i] for i in (first_end - 1, first_end + 1) if 0 <= i < len(words)]
    return {"class": kind(m.group(0), text[:m.start()], text[m.end():]), "tokens_omitted": 1,
            "gap_position": place,
            "neighbour_holds_a_digit": any(c.isdigit() for w in neighbours for c in w)}


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
            spans[(label, f"{r['pmid']}:{r['claim_index']:03d}")] = r["evidence_span"]
    for item in a.checks:
        label, path = item.split("=", 1)
        for r in map(json.loads, pathlib.Path(path).read_text().splitlines()):
            checks[(label, r["claim_record_id"])] = r
    records = {}
    by_class: dict = collections.defaultdict(collections.Counter)
    for label, f in json.loads(a.classes.read_text())["files"].items():
        for rid, made in f["classes"].items():
            if made["class"] != "pieces_joined":
                continue
            d = describe(spans[(label, rid)], abstracts[rid.split(":")[0]])
            d["passes_the_other_criteria"] = would_enter(checks[(label, rid)])
            records[rid] = d
            c = by_class[d["class"]]
            c["records"] += 1
            c["pass_the_other_criteria"] += d["passes_the_other_criteria"]
            c[f"gap_{d.get('gap_position', 'none')}"] += 1
            c["neighbour_holds_a_digit"] += bool(d.get("neighbour_holds_a_digit"))
    result = {"records": len(records),
              "by_class": {k: dict(sorted(v.items())) for k, v in sorted(by_class.items())},
              "per_record": records}
    a.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({"records": result["records"], "by_class": result["by_class"]}, indent=1))


if __name__ == "__main__":
    main()
