# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Running the span step of one extraction file in parts (PREREG.md, Amendment 2).

scripts/verify_spans_occurrence.py pins every evidence span with one call of the `citations`
tool, about two hours for the 14,053 claim records in one process, and it writes its results
only when it ends. So that the step can be run on Modal with its progress kept, the extraction
file is cut into parts of consecutive rows (a row is one paper), the sealed script is run
unchanged on each part, each part's results are stored as soon as it ends, and the parts are
joined here. A paper's spans are pinned in that paper's own claims file against that paper's
own source, so what is computed for a record does not depend on which other papers are in the
file with it.

Joined: `spans.jsonl` is the parts' lines in order; `span_occurrences.json` holds the union
of the parts' records; `span_summary.json` is computed from the joined lines with the sealed
script's own expressions; `citations verify --strict` is run once over the joined claims tree
(by the wrapper). scripts/modal_verify_spans_occurrence.py checks on synthetic records that
the joined files are byte for byte what the sealed script writes for the whole file at once.
"""

import json


class ShardError(Exception):
    """The parts do not fit together."""


def shard_stem(stem: str, index: int) -> str:
    return f"{stem}.shard{index:04d}"


def split(lines: list[str], size: int) -> list[list[str]]:
    """Consecutive parts of at most `size` lines, in order."""
    if size < 1:
        raise ShardError("a part holds at least one row")
    return [lines[i:i + size] for i in range(0, len(lines), size)]


def abstracts_for(rows: list[str], abstract_lines: list[str]) -> list[str]:
    """The lines of the abstracts file for the papers of `rows`, in the file's order (the
    sealed script takes the last line of a paper where there are several)."""
    wanted = {json.loads(line)["pmid"] for line in rows if line.strip()}
    return [line for line in abstract_lines
            if line.strip() and json.loads(line)["pmid"] in wanted]


def join_spans(parts: list[list[str]]) -> list[str]:
    lines = [line for part in parts for line in part]
    ids = [(r["pmid"], r["claim_index"]) for r in map(json.loads, lines)]
    if len(set(ids)) != len(ids):
        raise ShardError("a claim record stands in two parts")
    return lines


def join_occurrences(parts: list[dict]) -> dict:
    """One `span_occurrences.json` from the parts': the same build and rule in every part, and
    the union of their records."""
    head = {k: parts[0][k] for k in ("citations_installed", "citations_commit", "rule")}
    records: dict = {}
    duplicated: dict = {}
    for part in parts:
        if {k: part[k] for k in head} != head:
            raise ShardError("two parts were made under different builds or rules")
        for name, target in (("records_pinned_at_an_occurrence", records),
                             ("stored_abstract_has_duplicated_passage", duplicated)):
            if set(part[name]) & set(target):
                raise ShardError("a paper or record stands in two parts")
            target |= part[name]
    return head | {"records_pinned_at_an_occurrence": records,
                   "stored_abstract_has_duplicated_passage": dict(sorted(duplicated.items()))}


def summary(extraction: str, results: list[dict], verify_exit: int) -> dict:
    """`span_summary.json`, with the expressions of scripts/verify_spans_occurrence.py."""
    n = len(results)
    return {
        "extraction": extraction, "n_claims": n,
        "registered_check_pass": sum(r["registered_check"] for r in results),
        "citations_pin_found": sum(r["citations_pin"] == "found" for r in results),
        "citations_found_only_after_punctuation_folding": sum(
            r["citations_pin"] == "found" and not r["registered_check"] for r in results),
        "citations_normalized_warning": sum(
            "normalized" in r["citations_warnings"] for r in results),
        "both_pass": sum(r["passes"] for r in results),
        "span_verification_rate": (sum(r["passes"] for r in results) / n) if n else None,
        "spans_over_two_sentences": sum(r["n_sentences"] > 2 for r in results),
        "citations_verify_exit": verify_exit,
        "failing": [r for r in results if not r["passes"]],
    }


def summary_text(extraction: str, span_lines: list[str], verify_exit: int) -> str:
    return json.dumps(summary(extraction, [json.loads(line) for line in span_lines],
                              verify_exit), indent=1, ensure_ascii=False)


def occurrences_text(joined: dict) -> str:
    return json.dumps(joined, indent=1) + "\n"
