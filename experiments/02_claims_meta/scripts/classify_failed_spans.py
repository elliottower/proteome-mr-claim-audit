# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Classify, by cause, the evidence spans that failed the stage 4 span check (PREREG.md log,
2026-10-08). A descriptive addition: no rule changes, the registered treatment of a failed
span stands, and no record's status changes. The script reads the failing spans and their
abstracts and writes a class per record; it prints counts only, and no span or abstract text
goes into its output.

A span fails when the registered quote check (scripts/verify_spans.py: the span, white space
collapsed and case folded, is a substring of the abstract treated the same way) or the
`citations pin` (found exactly once in the pinned abstract) does not hold. Each failing span
takes the first class that applies:

    in_abstract_more_than_once   the registered check holds and the span occurs two or more
                                 times in the abstract; the pin has no single occurrence to name
    in_abstract_pin_refused      the registered check holds, the span occurs once, and the pin
                                 was refused all the same
    after_unicode_normalisation  found once the span and the abstract are normalised: NFKC,
                                 every dash as "-", curly quotes straightened, soft hyphen and
                                 zero-width characters removed, white space of any kind as a space
    after_removing_markup        found once tags, HTML entities and sub/superscript marks are
                                 also removed from both
    joined_with_an_ellipsis      the span holds an ellipsis and each piece between ellipses is
                                 in the abstract
    pieces_joined                the span is two to four pieces of the abstract, each of three
                                 tokens or more, written one after the other with the text
                                 between them left out (`pieces_in_order` says whether they
                                 keep the abstract's order)
    in_title_only                found in the record's title, not in its abstract
    in_request_not_in_abstract   found in the text sent to the model, which the stored
                                 abstract does not hold
    near_match                   the span's tokens align with one stretch of the abstract with
                                 at most NEAR tokens changed, added or dropped (NEAR = 3, or a
                                 tenth of the span's tokens when that is more); `digit_differs`
                                 says whether a changed token holds a digit
    abstract_empty_or_stub       the stored abstract has fewer than 200 characters
    no_close_counterpart         none of the above

Case folding alone cannot be a class: the registered check already folds case.

Usage: uv run scripts/classify_failed_spans.py --spans <label>=<spans.jsonl> [...] \\
           --abstracts <eligible_abstracts.jsonl> [...] --raw <stored exchanges dir> \\
           --out <json>
"""

import argparse
import collections
import difflib
import html
import json
import pathlib
import re
import unicodedata

NEAR = 3
STUB = 200
DASHES = dict.fromkeys(map(ord, "‐‑‒–—−"), "-")
QUOTES = {ord("’"): "'", ord("‘"): "'", ord("“"): '"', ord("”"): '"'}
INVISIBLE = dict.fromkeys(map(ord, "­​‌‍⁠﻿"))
TAG = re.compile(r"</?[A-Za-z][^<>]*>")
MARKS = re.compile(r"[\^_~{}]")
ELLIPSIS = re.compile(r"\s*(?:\[\s*(?:\.{3}|…)\s*\]|\.{3,}|…)\s*")


class ClassifyError(Exception):
    """A failing span has no abstract, or the output exists."""


def registered(text: str) -> str:
    """The folding of scripts/verify_spans.py."""
    return " ".join(text.split()).casefold()


def normalised(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(DASHES).translate(QUOTES)
    return registered(text.translate(INVISIBLE))


def unmarked(text: str) -> str:
    return normalised(MARKS.sub("", TAG.sub(" ", html.unescape(html.unescape(text)))))


def tokens(text: str) -> list[str]:
    return re.findall(r"[^\W_]+(?:[.,][^\W_]+)*", unmarked(text))


def pieces(span: list[str], abstract: list[str]) -> list[int] | None:
    """Start positions in the abstract of two to four runs that make up the span, or None."""
    starts, i = [], 0
    while i < len(span):
        best, at = 0, -1
        for j in range(len(abstract)):
            k = 0
            while i + k < len(span) and j + k < len(abstract) and span[i + k] == abstract[j + k]:
                k += 1
            if k > best:
                best, at = k, j
        if best < 3:
            return None
        starts.append(at)
        i += best
    return starts if 2 <= len(starts) <= 4 else None


def near(span: list[str], abstract: list[str]) -> dict | None:
    """The near match of the span in the abstract, or None."""
    allowed = max(NEAR, len(span) // 10)
    blocks = [b for b in difflib.SequenceMatcher(None, abstract, span, autojunk=False)
              .get_matching_blocks() if b.size]
    if not blocks:
        return None
    matched = sum(b.size for b in blocks)
    window = blocks[-1].a + blocks[-1].size - blocks[0].a
    changed = (len(span) - matched) + max(0, window - len(span))
    if changed == 0 or changed > allowed:
        return None
    kept = set()
    for b in blocks:
        kept.update(range(b.b, b.b + b.size))
    differing = [t for i, t in enumerate(span) if i not in kept]
    between = [t for x, y in zip(blocks, blocks[1:]) for t in abstract[x.a + x.size:y.a]]
    return {"tokens_changed": changed,
            "digit_differs": any(c.isdigit() for t in differing + between for c in t)}


def classify(span: str, abstract: str, title: str, request: str, pin: str) -> dict:
    """The class of one failing span, with its details."""
    s, a = registered(span), registered(abstract)
    if s and s in a:
        n = a.count(s)
        return {"class": "in_abstract_more_than_once" if n > 1 else "in_abstract_pin_refused",
                "occurrences": n, "pin": pin}
    if normalised(span) in normalised(abstract):
        return {"class": "after_unicode_normalisation"}
    if unmarked(span) in unmarked(abstract):
        return {"class": "after_removing_markup"}
    parts = [p for p in ELLIPSIS.split(span) if p.strip()]
    if len(parts) > 1 and all(unmarked(p) in unmarked(abstract) for p in parts):
        return {"class": "joined_with_an_ellipsis", "pieces": len(parts)}
    st, at = tokens(span), tokens(abstract)
    starts = pieces(st, at)
    if starts:
        return {"class": "pieces_joined", "pieces": len(starts),
                "pieces_in_order": starts == sorted(starts)}
    if title and unmarked(span) in unmarked(title):
        return {"class": "in_title_only"}
    if request and unmarked(span) in unmarked(request):
        return {"class": "in_request_not_in_abstract"}
    close = near(st, at)
    if close:
        return {"class": "near_match", **close}
    if len(abstract.strip()) < STUB:
        return {"class": "abstract_empty_or_stub", "abstract_characters": len(abstract.strip())}
    return {"class": "no_close_counterpart"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spans", nargs="+", required=True, help="<label>=<spans.jsonl>")
    ap.add_argument("--abstracts", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--raw", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise ClassifyError(f"{a.out} exists; a classification is written once")
    records = {}
    for path in a.abstracts:
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                records.setdefault(r["pmid"], r)
    result: dict = {"near_tokens": NEAR, "stub_characters": STUB, "files": {}}
    total: collections.Counter = collections.Counter()
    for item in a.spans:
        label, path = item.split("=", 1)
        classes, counts, seen = {}, collections.Counter(), 0
        for line in pathlib.Path(path).read_text().splitlines():
            r = json.loads(line)
            seen += 1
            if r["passes"]:
                continue
            if r["pmid"] not in records:
                raise ClassifyError(f"{r['pmid']}: no abstract")
            rec = records[r["pmid"]]
            exchange = a.raw / f"{r['pmid']}_attempt1.json"
            request = (json.loads(exchange.read_text()).get("request", {}).get("input", "")
                       if exchange.is_file() else "")
            made = classify(r["evidence_span"], rec["abstract"], rec.get("title") or "",
                            request, r["citations_pin"])
            made["registered_check"] = r["registered_check"]
            classes[f"{r['pmid']}:{r['claim_index']:03d}"] = made
            key = made["class"] + ("/digit_differs" if made.get("digit_differs") else "")
            counts[key] += 1
        result["files"][label] = {"claim_records": seen, "failing": len(classes),
                                  "counts": dict(sorted(counts.items())), "classes": classes}
        total.update(counts)
    result["counts"] = dict(sorted(total.items()))
    result["failing"] = sum(f["failing"] for f in result["files"].values())
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({"failing": result["failing"], "counts": result["counts"],
                      "per_file": {k: v["counts"] for k, v in result["files"].items()}},
                     indent=1))


if __name__ == "__main__":
    main()
