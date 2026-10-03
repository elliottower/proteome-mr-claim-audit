# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.13.5", "pyyaml==6.0.3"]
# ///
"""Check that every evidence span is a verbatim passage of its abstract.

Two checks, both required for a span to pass:

1. The registered quote check: after collapsing runs of whitespace to one space and folding
   case, the span occurs as one contiguous passage of the abstract.
2. The `citations` CLI. Each abstract is written as a pinned source artifact (sha256 in the
   claims file) and each span is pinned with `citations pin`, which refuses a passage that does
   not resolve. `citations verify --strict` is then run over all claims files and its report is
   kept. `citations` also folds punctuation, so a span can pass it and fail check 1; such spans
   are counted separately.

A diagnostic, not a gate: the number of sentences in the span, by a simple splitter, with
spans of more than two sentences counted.

The citations artifacts go to outputs/citations/<run>/{sources,claims}/; results to
outputs/verification/<run>/.

Full-text extractions are checked the same way against the rendered body text:
`--abstracts prompts/dev_fulltext.jsonl --text-field body`.

When a record of the input carries `<text field>_sha256` (the development abstracts, the
rendered full texts), the artifact written here must have that digest. The abstracts of the
screening sets carry none; their artifact is the text of the record as it is read.

Usage: uv run scripts/verify_spans.py --extraction outputs/parsed/sol_extraction_r1_<rev>.jsonl
"""

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess

import yaml
from pydantic import BaseModel

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
ABSTRACTS = EXP / "prompts" / "dev_abstracts.jsonl"
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[])")


class SpanCheckError(Exception):
    """The inputs are inconsistent or the citations CLI failed to run."""


class SpanResult(BaseModel):
    pmid: str
    claim_index: int
    claim_id: str
    evidence_span: str
    registered_check: bool
    citations_pin: str
    citations_warnings: list[str]
    n_sentences: int
    passes: bool


def fold(text: str) -> str:
    return " ".join(text.split()).casefold()


def n_sentences(span: str) -> int:
    return len([s for s in SENTENCE_END.split(span.strip()) if s])


def record_url(record_id: str) -> str | None:
    """The landing page of a record id: a PMID, an OpenAlex work or a Europe PMC preprint."""
    if record_id.isdigit():
        return f"https://pubmed.ncbi.nlm.nih.gov/{record_id}/"
    if re.fullmatch(r"W\d+", record_id):
        return f"https://openalex.org/{record_id}"
    if re.fullmatch(r"PPR\d+", record_id):
        return f"https://europepmc.org/article/PPR/{record_id}"
    return None


def check_digest(rec: dict, text_field: str, digest: str, source_name: str) -> None:
    """Raise when the record carries a digest of its text and the artifact's differs."""
    recorded = rec.get(f"{text_field}_sha256")
    if recorded is not None and digest != recorded:
        raise SpanCheckError(f"{rec['pmid']}: artifact digest differs from {source_name}")


def pin(claims_file: pathlib.Path, claim_id: str, span: str, env: dict) -> tuple[str, list[str]]:
    r = subprocess.run(["citations", "pin", str(claims_file), "--id", claim_id, "--quote", span],
                       capture_output=True, text=True, env=env)
    first = (r.stdout.splitlines() or [""])[0]
    state = "found" if r.returncode == 0 else first.split("  ")[0].strip() or "error"
    warnings = []
    for line in r.stdout.splitlines():
        if line.strip().startswith("warnings:"):
            warnings = [w.strip() for w in line.split(":", 1)[1].split(",")]
    return state, warnings


def relative_paths(text: str, root: pathlib.Path = EXP) -> str:
    """The text with paths under `root` written relative to it (the `citations` CLI prints the
    absolute path of the claims folder; a stored output names no home folder)."""
    return text.replace(f"{root}/", "")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extraction", type=pathlib.Path, required=True)
    ap.add_argument("--abstracts", type=pathlib.Path, default=ABSTRACTS)
    ap.add_argument("--text-field", default="abstract", choices=["abstract", "body"])
    a = ap.parse_args()

    run = a.extraction.stem
    cit_root = EXP / "outputs" / "citations" / run
    out_dir = EXP / "outputs" / "verification" / run
    if cit_root.exists():
        raise SpanCheckError(f"{cit_root} exists; a verification run is never overwritten")
    (cit_root / "sources").mkdir(parents=True)
    (cit_root / "claims").mkdir()
    out_dir.mkdir(parents=True, exist_ok=True)
    # A run-local claims tree, read without the shared library.
    env = {k: v for k, v in os.environ.items() if k != "CITATIONS_HOME"}

    abstracts = {json.loads(l)["pmid"]: json.loads(l) for l in a.abstracts.read_text().splitlines()
                 if l.strip()}
    rows = [json.loads(l) for l in a.extraction.read_text().splitlines() if l.strip()]

    results: list[SpanResult] = []
    for row in rows:
        if row["status"] != "ok":
            continue
        rec = abstracts[row["pmid"]]
        src = cit_root / "sources" / f"pmid{rec['pmid']}.txt"
        src.write_text(rec[a.text_field])
        digest = hashlib.sha256(src.read_bytes()).hexdigest()
        check_digest(rec, a.text_field, digest, a.abstracts.name)
        claims_file = cit_root / "claims" / f"pmid{rec['pmid']}.yaml"
        url = record_url(rec["pmid"])
        claims_file.write_text(yaml.safe_dump({
            "source": {"citation": f"pmid{rec['pmid']}", "local": f"sources/{src.name}",
                       "sha256": digest, **({"url": url} if url else {}),
                       "note": f"{a.text_field} text exactly as sent to the extractor"},
            "claims": {}}, sort_keys=False, allow_unicode=True))
        abstract_folded = fold(rec[a.text_field])
        for i, claim in enumerate(row["output"]["claims"]):
            span = claim["evidence_span"]
            claim_id = f"c{i:03d}"
            state, warnings = pin(claims_file, claim_id, span, env)
            registered = fold(span) in abstract_folded
            results.append(SpanResult(
                pmid=rec["pmid"], claim_index=i, claim_id=claim_id, evidence_span=span,
                registered_check=registered, citations_pin=state,
                citations_warnings=warnings, n_sentences=n_sentences(span),
                passes=registered and state == "found"))

    verify = subprocess.run(["citations", "verify", "--claims",
                             str((cit_root / "claims").relative_to(EXP)), "--strict"],
                            capture_output=True, text=True, env=env, cwd=EXP)
    (out_dir / "citations_verify.txt").write_text(relative_paths(
        f"exit {verify.returncode}\n{verify.stdout}\n{verify.stderr}"))

    with (out_dir / "spans.jsonl").open("w") as f:
        for r in results:
            f.write(r.model_dump_json() + "\n")
    n = len(results)
    summary = {
        "extraction": str(a.extraction), "n_claims": n,
        "registered_check_pass": sum(r.registered_check for r in results),
        "citations_pin_found": sum(r.citations_pin == "found" for r in results),
        "citations_found_only_after_punctuation_folding": sum(
            r.citations_pin == "found" and not r.registered_check for r in results),
        "citations_normalized_warning": sum("normalized" in r.citations_warnings for r in results),
        "both_pass": sum(r.passes for r in results),
        "span_verification_rate": (sum(r.passes for r in results) / n) if n else None,
        "spans_over_two_sentences": sum(r.n_sentences > 2 for r in results),
        "citations_verify_exit": verify.returncode,
        "failing": [r.model_dump() for r in results if not r.passes],
    }
    (out_dir / "span_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in summary.items() if k != "failing"}, indent=1))
    print(verify.stdout)


if __name__ == "__main__":
    main()
