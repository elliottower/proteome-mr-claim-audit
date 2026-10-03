# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.13.5"]
# ///
"""Per-claim tags for the stage 5 joins, one JSON line per extracted claim record. No model is
called.

    wording_class, novelty_language   scripts/tag_wording.py, unchanged (the committed lexicon
                                      verification/wording_lexicon.json; wording-keyword and
                                      novelty-term matches inside the record's outcome or
                                      protein name do not count)
    platform, ancestry                GPT-6.1 Sol's values, carried unchanged for the joins that
                                      read them
    pmid                              the record id of the abstract, for the joins that read the
                                      abstract text

Records are keyed by `claim_record_id` (`<pmid>:<record index>`, the identifier verify_claims.py
assigns). scripts/drug_joins.py reads `claim_record_id` and `wording_class` from this file.
The wording audit is written beside it: `wording.jsonl` (every wording-keyword and novelty-term
match of every record, with its position and the name it lay in, and the class and the novelty
flag without the name rule) and `wording_summary.json`.

Several extraction files (the search and each citation-chasing round) are read as one, in the
order given; a record id in two of them raises.

Usage: uv run scripts/claim_tags.py --extraction outputs/parsed/sol_extraction_<label>_<rev>.jsonl
           [<...> ...] --out <dir>
"""

import argparse
import json
import pathlib
from typing import Literal

from pydantic import BaseModel, ConfigDict

from tag_wording import LEXICON, Lexicon, summarize, tag_rows

WordingClass = Literal["target", "causal", "association"]


class ClaimTags(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    claim_record_id: str
    pmid: str
    wording_class: WordingClass
    novelty_language: bool
    platform: tuple[str, ...]
    ancestry: str


def load_lexicon(path: pathlib.Path = LEXICON) -> Lexicon:
    return Lexicon(json.loads(path.read_text()))


def tags_from_extraction(rows: list[dict], lexicon: Lexicon) -> list[ClaimTags]:
    """Tags for every claim of every `ok` extraction row, in verify_claims.py's record order."""
    wording = {w.claim_record_id: w for w in tag_rows(rows, lexicon)}
    out = []
    for row in rows:
        if row["status"] != "ok":
            continue
        for i, c in enumerate(row["output"]["claims"]):
            w = wording[f"{row['pmid']}:{i:03d}"]
            out.append(ClaimTags(
                claim_record_id=w.claim_record_id, pmid=row["pmid"],
                wording_class=w.wording_class, novelty_language=w.novelty_language,
                platform=tuple(c["platform"]), ancestry=c["ancestry"]))
    return out


def load_tags(path: pathlib.Path) -> dict[str, ClaimTags]:
    return {t.claim_record_id: t for t in (ClaimTags.model_validate_json(l)
                                           for l in path.read_text().splitlines() if l.strip())}


def read_extractions(paths: list[pathlib.Path]) -> list[dict]:
    """The rows of the extraction files as one list; a record id in two rows raises."""
    rows = [json.loads(l) for p in paths for l in p.read_text().splitlines() if l.strip()]
    ids = [r["pmid"] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{[str(p) for p in paths]}: a record id occurs twice")
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extraction", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    rows = read_extractions(a.extraction)
    lexicon = load_lexicon()
    tags = tags_from_extraction(rows, lexicon)
    wording = tag_rows(rows, lexicon)
    a.out.mkdir(parents=True, exist_ok=True)
    target = a.out / "claim_tags.jsonl"
    if target.exists():
        raise FileExistsError(f"{target} exists; archive it before rerunning")
    (a.out / "wording.jsonl").write_text("".join(w.model_dump_json() + "\n" for w in wording))
    (a.out / "wording_summary.json").write_text(json.dumps(
        {"extraction": [str(p) for p in a.extraction], **summarize(wording)}, indent=1))
    target.write_text("".join(t.model_dump_json() + "\n" for t in tags))
    print(json.dumps({"claims": len(tags), "out": str(target)}))


if __name__ == "__main__":
    main()
