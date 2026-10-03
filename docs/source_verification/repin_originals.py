"""Pin the original file behind a text-pinned source, and re-pin its quotations against it.

A claims file under `claims/` pins a text extracted from a paper or supplement. A reader who
downloads the paper gets the publisher's file, whose bytes can never equal the extracted text,
so `citations fetch` reports `differs`. For a source whose original is a PDF or a plain-text
file, `citations` reads the original itself, so the original can be pinned directly.

For each entry of the plan this script

1. obtains the original file (the copy the text was made from where one is held, else a
   download with the `citations` downloader) and writes it to `sources/original/`,
2. writes `claims/<stem>_original.yaml`, whose `source:` block pins that file by sha256 and
   records its `url:` and `doi:`,
3. passes every quotation of `claims/<stem>.yaml` to `citations pin`, which writes it into the
   new file only when it resolves in the original.

`claims/<stem>.yaml` is never edited. A quotation `citations pin` refuses stays pinned to the
extracted text only, and is listed in the result file with the reason.

Run from the repository root with the build of `citations` that has `fetch`:

    uv run --project ~/Documents/GitHub/reproducible-science-main \
        python docs/source_verification/repin_originals.py --stems a b c
"""

import argparse
import contextlib
import hashlib
import io
import json
import pathlib

import yaml
from citations import fetch as citations_fetch
from citations import pin as citations_pin
from pydantic import BaseModel

PLAN = pathlib.Path("docs/source_verification/originals_plan.json")
CLAIMS = pathlib.Path("claims")
ORIGINALS = pathlib.Path("sources/original")


class OriginalUnavailableError(Exception):
    """No copy of the original could be read or downloaded."""


class Entry(BaseModel):
    stem: str
    suffix: str
    origin: str
    url: str | None = None
    doi: str | None = None
    arxiv: str | None = None
    local_copy: str | None = None


class Refusal(BaseModel):
    claim_id: str
    quote: str
    said: str


class Outcome(BaseModel):
    stem: str
    original: str
    sha256: str
    size_bytes: int
    bytes_from: str
    url_serves_pinned_bytes: bool | None
    quotes: int
    pinned: int
    already_present: int
    refused: list[Refusal]


def obtain(entry: Entry) -> tuple[bytes, str, bool | None]:
    """The original's bytes, where they came from, and whether the url serves the same bytes."""
    held = pathlib.Path(entry.local_copy).read_bytes() if entry.local_copy else None
    served = citations_fetch.download(entry.url) if entry.url else None
    if held is not None:
        same = None if served is None else hashlib.sha256(served).digest() == hashlib.sha256(held).digest()
        return held, f"held copy {entry.local_copy}", same
    if served is None:
        raise OriginalUnavailableError(f"{entry.stem}: no held copy and {entry.url} gave no file")
    return served, f"download {entry.url}", True


def source_block(entry: Entry, text_pin: dict, original: pathlib.Path, digest: str) -> dict:
    block = {
        "citation": text_pin["source"].get("citation", entry.stem),
        "local": str(original),
        "sha256": digest,
    }
    if entry.url:
        block["url"] = entry.url
    if entry.doi:
        block["doi"] = entry.doi
    if entry.arxiv:
        # `citations fetch` asks arXiv for the id it is given; without a version it gets the latest.
        block["arxiv"] = entry.arxiv
    block["note"] = (
        f"Original file behind claims/{entry.stem}.yaml: {entry.origin}. The quotations here are "
        f"the quotations of that file that resolve in this file under the citations readers; a "
        f"quotation absent here is pinned to the extracted text there only."
    )
    return block


def repin(entry: Entry) -> Outcome:
    text_pin = yaml.safe_load((CLAIMS / f"{entry.stem}.yaml").read_text())
    body, bytes_from, same = obtain(entry)
    digest = hashlib.sha256(body).hexdigest()
    original = ORIGINALS / f"{entry.stem}{entry.suffix}"
    original.parent.mkdir(parents=True, exist_ok=True)
    if not original.exists() or hashlib.sha256(original.read_bytes()).hexdigest() != digest:
        original.write_bytes(body)

    target = CLAIMS / f"{entry.stem}_original.yaml"
    if not target.exists():
        doc = {"source": source_block(entry, text_pin, original, digest), "claims": {}}
        target.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100))
    present = set((yaml.safe_load(target.read_text()).get("claims") or {}).keys())

    pinned = already = total = 0
    refused: list[Refusal] = []
    for claim_id, claim in text_pin["claims"].items():
        for quote in claim["quotes"]:
            total += 1
            if claim_id in present:
                already += 1
                continue
            argv = [str(target), "--id", claim_id, f"--quote={quote['exact']}"]
            if quote.get("section"):
                argv.append(f"--section={quote['section']}")
            said = io.StringIO()
            with contextlib.redirect_stdout(said):
                code = citations_pin.main(argv)
            if code == 0:
                pinned += 1
            else:
                refused.append(
                    Refusal(claim_id=claim_id, quote=quote["exact"], said=said.getvalue().strip())
                )
    return Outcome(
        stem=entry.stem,
        original=str(original),
        sha256=digest,
        size_bytes=len(body),
        bytes_from=bytes_from,
        url_serves_pinned_bytes=same,
        quotes=total,
        pinned=pinned,
        already_present=already,
        refused=refused,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--stems", nargs="*", help="only these sources; default is the whole plan")
    parser.add_argument("--out", required=True, type=pathlib.Path, help="result file to write")
    args = parser.parse_args()

    plan = [Entry.model_validate(e) for e in json.loads(PLAN.read_text())]
    if args.stems:
        plan = [e for e in plan if e.stem in set(args.stems)]
    outcomes: list[dict] = []
    for entry in plan:
        try:
            outcome = repin(entry).model_dump()
        except OriginalUnavailableError as error:
            outcome = {"stem": entry.stem, "unavailable": str(error)}
        outcomes.append(outcome)
        # Written after every source, so a stopped run keeps what it finished.
        args.out.write_text(json.dumps(outcomes, indent=1, ensure_ascii=False))
        print(
            entry.stem,
            outcome.get("unavailable")
            or f"{outcome['pinned']} pinned, {len(outcome['refused'])} refused of {outcome['quotes']}",
        )


if __name__ == "__main__":
    main()
