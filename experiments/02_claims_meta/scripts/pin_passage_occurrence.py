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
`citations verify --strict` against a copy of the source in a temporary folder; if it still
does not single out one occurrence, or the passage has no sentence on either side (a table row
line), or the tool refused the sentence for another reason, the helper raises and writes
nothing. A claim id already in the file is refused. No coder edits a claims file by hand.

Usage, from experiments/02_claims_meta:
    uv run scripts/pin_passage_occurrence.py --input <coder input file> --row <side>_<k> \\
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
    if len(quote) == 1:
        raise PinError("the sentence occurs several times in its source and the passage has no "
                       "sentence on either side of it")
    claim = {"quotes": [quote]}
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
    if check.returncode != 0:
        raise PinError("the sentence with the sentences either side still does not single out "
                       f"one occurrence:\n{check.stdout[-1500:]}")
    record = yaml.safe_load(claims_file.read_text())
    record.setdefault("claims", {})
    record["claims"] = {**(record["claims"] or {}), claim_id: claim}
    claims_file.write_text(yaml.safe_dump(record, sort_keys=False, allow_unicode=True))
    return "pinned_with_prefix_and_suffix"


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
