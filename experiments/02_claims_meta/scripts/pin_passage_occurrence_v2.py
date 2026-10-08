# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml==6.0.3"]
# ///
"""Pin one sentence of a passage of the manual dataset-coding inputs, also when the sentence
occurs more than once in its source (PREREG.md log, 2026-10-08; rule I4 of the settled rules: a
sentence occurring twice does not make the release unidentified).

The sentence is named by the coder's input file, the row (`<side>_<k>`, the k-th row of that
side in the file), the passage id and the sentence's number in the passage (1 for the first).
It is first pinned with `citations pin` as any other. When the tool refuses it as ambiguous
(the passage occurs several times in the source), the quotation is written into the passage's
claims file with the `prefix` and `suffix` fields the tool asks for, taken mechanically from the
passage: the sentence before it and the sentence after it, whole, where the passage has them.
Before anything is written, the quotation with its prefix and suffix is checked with
`citations verify --strict` against a copy of the source in a temporary folder.

This is the second version; scripts/pin_passage_occurrence.py stays sealed and is superseded.
Where the first version raised because the sentences either side are duplicated too, or the
sentence stands alone in its passage (a table row line), this version goes on: it finds the
passage's own occurrence of the sentence in the source text (by the passage's line of the
rendered body and the sentence's place in the passage) and takes as prefix and suffix the text
that stands before and after that occurrence, 80 characters each way cut at a word, then
doubling, until `citations verify --strict` confirms on the copy that one occurrence is named.
The text before an occurrence, taken back to the start of the document, names that occurrence
and no other, so the search ends; if the tool still does not confirm it, or refused the
sentence for another reason, the helper raises and writes nothing. A claim id already in the
file is refused. No coder edits a claims file by hand.

Usage, from experiments/02_claims_meta:
    uv run scripts/pin_passage_occurrence_v2.py --input <coder input file> --row <side>_<k> \\
        --passage <passage id> --sentence <n> --id <claim id> \\
        [--citations outputs/citations/manual_coding_2026-10-03]
"""

import argparse
import collections
import json
import os
import pathlib
import shutil
import subprocess
import tempfile

import yaml

CITATIONS = pathlib.Path("outputs/citations/manual_coding_2026-10-03")


class PinError(Exception):
    """The sentence cannot be pinned as one occurrence, or the request names nothing."""


def find_passage(given: dict, row_id: str, passage_id: str) -> dict:
    nth: collections.Counter = collections.Counter()
    for row in given["rows"]:
        nth[row["side"]] += 1
        if f"{row['side']}_{nth[row['side']]}" == row_id:
            for passage in row["passages"]:
                if passage["passage_id"] == passage_id:
                    return passage
            raise PinError(f"row {row_id} has no passage {passage_id}")
    raise PinError(f"{given['record_id']} has no row {row_id}")


def occurrence_quote(passage: dict, number: int) -> dict:
    """The quotation record of the passage's n-th sentence with the sentences either side."""
    sentences = passage["sentences"]
    if not 1 <= number <= len(sentences):
        raise PinError(f"passage {passage['passage_id']} has {len(sentences)} sentence(s)")
    quote = {"exact": sentences[number - 1]}
    if number >= 2:
        quote["prefix"] = sentences[number - 2]
    if number < len(sentences):
        quote["suffix"] = sentences[number]
    return quote


def collapsed(text: str) -> str:
    return " ".join(text.split())


def around(passage: dict, number: int, source: str) -> tuple[str, str]:
    """The source text before and after the passage's own occurrence of its n-th sentence,
    white space collapsed. A full-text passage is found on its line of the rendered body; an
    abstract passage in the abstract as a whole."""
    whole_line = passage.get("source_read") in ("abstract",
                                                "abstract_fallback_after_fulltext_no_match")
    lines = [source] if whole_line else source.split("\n")
    index = 0 if whole_line else passage["line"]
    if not 0 <= index < len(lines):
        raise PinError("the passage's line is not in the source")
    line = collapsed(lines[index])
    sentences = [collapsed(s) for s in passage["sentences"]]
    at = line.find(" ".join(sentences))
    if at < 0:
        raise PinError("the passage is not on its line of the source")
    start = at + len(" ".join(sentences[:number - 1])) + (1 if number > 1 else 0)
    end = start + len(sentences[number - 1])
    before = " ".join(x for x in (collapsed("\n".join(lines[:index])), line[:start].strip())
                      if x)
    after = " ".join(x for x in (line[end:].strip(), collapsed("\n".join(lines[index + 1:])))
                     if x)
    return before, after


def widening(before: str, after: str, first: int = 80):
    """Prefix and suffix pairs of growing length, cut at a word, ending with all the text."""
    size = first
    while True:
        prefix = before if len(before) <= size else before[-size:].split(" ", 1)[-1]
        suffix = after if len(after) <= size else after[:size].rsplit(" ", 1)[0]
        yield prefix.strip(), suffix.strip()
        if len(before) <= size and len(after) <= size:
            return
        size *= 2


def tool(args: list[str], cwd: pathlib.Path) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "CITATIONS_HOME"}
    return subprocess.run(["citations", *args], capture_output=True, text=True, env=env, cwd=cwd)


def pin(passage: dict, number: int, claim_id: str, citations: pathlib.Path, run=tool) -> str:
    """Pin the sentence; returns `pinned` or `pinned_with_prefix_and_suffix`."""
    quote = occurrence_quote(passage, number)
    claims_file = citations / passage["claims_file"]
    record = yaml.safe_load(claims_file.read_text())
    if claim_id in (record.get("claims") or {}):
        raise PinError(f"{claims_file.name} already holds the claim id {claim_id}")
    first = run(["pin", passage["claims_file"], "--id", claim_id, "--quote", quote["exact"]],
                citations)
    if first.returncode == 0:
        return "pinned"
    if not first.stdout.lstrip().startswith("ambiguous"):
        raise PinError(f"citations pin refused the sentence:\n{first.stdout}{first.stderr}")
    candidates = [quote] if len(quote) > 1 else []
    source = (citations / record["source"]["local"]).read_text()
    for prefix, suffix in widening(*around(passage, number, source)):
        candidates.append({"exact": quote["exact"], **({"prefix": prefix} if prefix else {}),
                           **({"suffix": suffix} if suffix else {})})
    last = ""
    for k, candidate in enumerate(candidates):
        if len(candidate) == 1:
            continue
        claim = {"quotes": [candidate]}
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            (root / "claims").mkdir()
            local = pathlib.Path(record["source"]["local"])
            (root / local).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(citations / local, root / local)
            (root / "claims" / claims_file.name).write_text(yaml.safe_dump(
                {"source": record["source"], "claims": {claim_id: claim}}, sort_keys=False,
                allow_unicode=True))
            check = run(["verify", "--claims", "claims", "--strict"], root)
        if check.returncode == 0:
            record = yaml.safe_load(claims_file.read_text())
            record["claims"] = {**(record.get("claims") or {}), claim_id: claim}
            claims_file.write_text(yaml.safe_dump(record, sort_keys=False, allow_unicode=True))
            return ("pinned_with_prefix_and_suffix" if k == 0 and len(quote) > 1
                    else "pinned_with_source_text_either_side")
        last = check.stdout[-1500:]
    raise PinError(f"no prefix and suffix single out the occurrence:\n{last}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=pathlib.Path, required=True)
    ap.add_argument("--row", required=True)
    ap.add_argument("--passage", required=True)
    ap.add_argument("--sentence", type=int, required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--citations", type=pathlib.Path, default=CITATIONS)
    a = ap.parse_args()
    passage = find_passage(json.loads(a.input.read_text()), a.row, a.passage)
    state = pin(passage, a.sentence, a.id, a.citations)
    print(f"{state}  {passage['claims_file']}#{a.id}")


if __name__ == "__main__":
    main()
