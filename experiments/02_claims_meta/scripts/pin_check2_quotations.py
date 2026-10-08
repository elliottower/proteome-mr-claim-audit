# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml==6.0.3"]
# ///
"""Pin the second check's quotations with `citations`, against the stored sources the coders'
pins use (PREREG.md log, 2026-10-08). For every counted answer of an ingest run
(scripts/manual_coding_check2_ingest_v3.py) that quotes a sentence, the sentence the batch
supplied (`sentence_supplied`, the quotation with the export's marks undone) is found in the
passages of the answer's row, or of the row of the same paper the ingest names, and pinned in
that passage's claims file under the claim id `<side>_<k>_c2` of the answer's own row.

The pin is made by scripts/pin_passage_occurrence_v2.py: `citations pin`, and for a sentence
that occurs more than once in its source the prefix and suffix that name the passage's own
occurrence. A claim id that already holds the same sentence is left as it is, so the script can
be run again after a rerun of a batch; one that holds another sentence is an error. A quotation
that will not pin is recorded, and its batch fails this check: it is rerun, never repaired.

Output, never overwritten: one JSON with, per batch, the counts of quotations pinned, pinned
with prefix and suffix, already pinned and refused, and the refused rows with the tool's
reason (no quotation text).

Usage: uv run scripts/pin_check2_quotations.py --ingested <ingest dir> --coders <coders dir> \\
           --citations <citations dir> --out <json>
"""

import argparse
import collections
import json
import pathlib

import yaml

from pin_passage_occurrence_v2 import PinError, pin, tool


class QuotationPinError(Exception):
    """The output exists, or a claim id holds another sentence."""


def collapsed(text: str) -> str:
    return " ".join(text.split())


def paper_rows(coders: pathlib.Path) -> dict[str, dict]:
    out = {}
    for path in sorted(coders.glob("coder_*/input/*.json")):
        given = json.loads(path.read_text())
        nth: collections.Counter = collections.Counter()
        for row in given["rows"]:
            nth[row["side"]] += 1
            out[f"{given['record_id']}#{row['side']}_{nth[row['side']]}"] = row
    return out


def locate(row: dict, sentence: str) -> tuple[dict, int] | None:
    """(the passage, the sentence's number in it) of the first passage holding the sentence."""
    for passage in row["passages"]:
        for n, s in enumerate(passage["sentences"], 1):
            if collapsed(s) == sentence:
                return passage, n
    return None


def pin_answer(answer: dict, rows: dict[str, dict], citations: pathlib.Path, run=tool) -> str:
    """Pin one answer's quotation; returns how. Raises PinError when it will not pin."""
    source_row = rows[answer["quote_from_another_row"] or answer["row"]]
    found = locate(source_row, answer["sentence_supplied"])
    if found is None:
        raise PinError("the sentence is not in the passages of the row the ingest names")
    passage, number = found
    claim_id = f"{answer['row'].split('#', 1)[1]}_c2"
    held = (yaml.safe_load((citations / passage["claims_file"]).read_text()).get("claims")
            or {}).get(claim_id)
    if held is not None:
        if (held.get("quotes") or [{}])[0].get("exact") != passage["sentences"][number - 1]:
            raise QuotationPinError(f"{answer['row']}: {claim_id} holds another sentence")
        return "already_pinned"
    return pin(passage, number, claim_id, citations, run)


def main() -> None:
    ap = argparse.ArgumentParser()
    for name in ("ingested", "coders", "citations", "out"):
        ap.add_argument(f"--{name}", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise QuotationPinError(f"{a.out} exists; a pin run is written once")
    summary = json.loads((a.ingested / "summary.json").read_text())
    rows = paper_rows(a.coders)
    result: dict = {"ingested": str(a.ingested), "batches": {}}
    total: collections.Counter = collections.Counter()
    for batch, info in sorted(summary["batches"].items()):
        if len(info["passing"]) != 1:
            continue
        stem = pathlib.Path(info["passing"][0]).stem
        answers = json.loads((a.ingested / f"{stem}.json").read_text())["answers"]
        counts: collections.Counter = collections.Counter()
        refused = []
        for answer in answers:
            if answer["quote"] == "none":
                counts["no_quotation"] += 1
                continue
            try:
                counts[pin_answer(answer, rows, a.citations)] += 1
            except PinError as e:
                counts["refused"] += 1
                refused.append({"row": answer["row"], "reason": str(e).splitlines()[0][:200]})
        result["batches"][batch] = {"answers_file": info["passing"][0], "rows": len(answers),
                                    **dict(sorted(counts.items())), "refused_rows": refused,
                                    "passes": not refused}
        total.update(counts)
    result["counts"] = dict(sorted(total.items()))
    result["batches_failing"] = sorted(b for b, v in result["batches"].items() if not v["passes"])
    a.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({"counts": result["counts"], "batches_pinned": len(result["batches"]),
                      "batches_failing": result["batches_failing"]}, indent=1))


if __name__ == "__main__":
    main()
