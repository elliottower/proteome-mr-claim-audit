"""Pin the original workbook, `.docx` or article XML behind a text-pinned source, read through a
named `citations` extractor.

`repin_originals.py` pinned the original PDFs and XML files that `citations` could read as they
were served. Workbooks and `.docx` supplements could not be pinned then, and XML quotations that
cross an inline tag did not resolve. `citations` now ships three built-in extractors
(`sheet-rows`, `docx-text`, `jats-text`), so a claims file can pin the publisher's file and name
the reader that turns it into the text quoted; `citations pin` records the extractor version and
the digest of the text it produced.

Two kinds of entry:

- `sheet`/`docx`: the original is downloaded from the publisher's static file address and
  written to `sources/original/`; `claims/<stem>_original.yaml` pins it with the extractor its
  suffix names.
- `jats`: the XML already pinned as served in `claims/<stem>_original.yaml` is pinned again in
  `claims/<stem>_original_jats.yaml` under `jats-text`, for the quotations the plain reading
  refused.

`claims/<stem>.yaml` and the existing `_original.yaml` files are never edited. A quotation
`citations pin` refuses stays pinned where it already was, and is listed in the result file.

Run from the repository root with the build of `citations` that ships the extractors:

    uv run --project ~/Documents/GitHub/reproducible-science-main \
        python docs/source_verification/repin_with_extractors.py --plan PLAN.json --out RESULT.json
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

CLAIMS = pathlib.Path("claims")
ORIGINALS = pathlib.Path("sources/original")
EXTRACTOR_BY_SUFFIX = {".xlsx": "sheet-rows", ".xls": "sheet-rows", ".docx": "docx-text"}


class OriginalUnavailableError(Exception):
    """The original could not be downloaded or is not held."""


class Entry(BaseModel):
    stem: str
    kind: str  # "sheet", "docx" or "jats"
    url: str | None = None
    doi: str | None = None
    origin: str


class Refusal(BaseModel):
    claim_id: str
    quote: str
    said: str


class Outcome(BaseModel):
    stem: str
    target: str
    original: str
    sha256: str
    extractor: str
    quotes: int
    pinned: int
    already_present: int
    refused: list[Refusal]


def original_for(entry: Entry) -> tuple[pathlib.Path, str, str]:
    """The original file, its sha256, and the claims file to write."""
    if entry.kind == "jats":
        served = yaml.safe_load((CLAIMS / f"{entry.stem}_original.yaml").read_text())["source"]
        original = pathlib.Path(served["local"])
        if not original.exists():
            raise OriginalUnavailableError(f"{entry.stem}: {original} is not held")
        digest = hashlib.sha256(original.read_bytes()).hexdigest()
        if digest != served["sha256"]:
            raise OriginalUnavailableError(f"{entry.stem}: {original} does not match its pin")
        return original, digest, f"{entry.stem}_original_jats.yaml"
    if entry.url is None:
        raise OriginalUnavailableError(f"{entry.stem}: no url")
    body = citations_fetch.download(entry.url)
    if body is None:
        raise OriginalUnavailableError(f"{entry.stem}: {entry.url} gave no file")
    suffix = pathlib.PurePosixPath(entry.url).suffix.lower()
    original = ORIGINALS / f"{entry.stem}{suffix}"
    original.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(body).hexdigest()
    if not original.exists() or hashlib.sha256(original.read_bytes()).hexdigest() != digest:
        original.write_bytes(body)
    return original, digest, f"{entry.stem}_original.yaml"


def extractor_for(entry: Entry, original: pathlib.Path) -> str:
    if entry.kind == "jats":
        return "jats-text"
    return EXTRACTOR_BY_SUFFIX[original.suffix.lower()]


def repin(entry: Entry) -> Outcome:
    text_pin = yaml.safe_load((CLAIMS / f"{entry.stem}.yaml").read_text())
    original, digest, target_name = original_for(entry)
    extractor = extractor_for(entry, original)
    target = CLAIMS / target_name
    if not target.exists():
        block = {
            "citation": text_pin["source"].get("citation", entry.stem),
            "local": str(original),
            "sha256": digest,
        }
        if entry.url:
            block["url"] = entry.url
        if entry.doi:
            block["doi"] = entry.doi
        block["extractor"] = extractor
        block["note"] = (
            f"Original file behind claims/{entry.stem}.yaml: {entry.origin}, read by the citations "
            f"extractor {extractor}. The quotations here are those of that file that resolve in this "
            f"reading; a quotation absent here stays pinned where it already was."
        )
        target.write_text(
            yaml.safe_dump({"source": block, "claims": {}}, sort_keys=False, allow_unicode=True, width=100)
        )
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
                refused.append(Refusal(claim_id=claim_id, quote=quote["exact"], said=said.getvalue().strip()))
    return Outcome(
        stem=entry.stem,
        target=str(target),
        original=str(original),
        sha256=digest,
        extractor=extractor,
        quotes=total,
        pinned=pinned,
        already_present=already,
        refused=refused,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--plan", required=True, type=pathlib.Path)
    parser.add_argument("--stems", nargs="*", help="only these sources; default is the whole plan")
    parser.add_argument("--out", required=True, type=pathlib.Path, help="result file to write")
    args = parser.parse_args()

    plan = [Entry.model_validate(e) for e in json.loads(args.plan.read_text())]
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
