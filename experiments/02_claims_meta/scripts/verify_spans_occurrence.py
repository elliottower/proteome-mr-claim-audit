# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.13.5", "pyyaml==6.0.3"]
# ///
"""Check that every evidence span is a verbatim passage of its abstract.

Corrected copy of scripts/verify_spans.py (PREREG.md, Amendment 2). The pass condition is
unchanged: the registered quote check and a `citations` pin that is found, both. One thing
differs. `citations pin` refuses a quotation that occurs more than once in its source as
ambiguous, so a span that the registered quote check finds, and that stands twice in the
stored abstract, could not be pinned. Here, when the registered quote check holds and the plain
pin is refused as ambiguous, and only then, the span is pinned again with `--occurrence 1`
(the first occurrence; both occurrences are the same text). `--occurrence` is never used for a
span the registered quote check does not find.

This needs a build of `citations` that has `--occurrence`. The script refuses to run unless the
installed `citations` was installed from the commit given with `--citations-commit` (read from
the installed distribution's `direct_url.json`; an editable or unversioned install is refused),
and it writes the installed version and commit into its outputs.

Outputs go to outputs/citations_occurrence/<run>/ and outputs/verification_occurrence/<run>/,
never into the folders of the registered run. `spans.jsonl` and `span_summary.json` have the
registered script's form, so the two runs can be compared line by line. One further file,
`span_occurrences.json`, records the installed build, each record pinned at an occurrence with
its `occurrence_count`, and the records whose stored abstract holds the span more than once
(`stored_abstract_has_duplicated_passage`).

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

Usage: uv run scripts/verify_spans_occurrence.py --citations-commit <40 hex> \\
           --extraction outputs/parsed/sol_extraction_<label>_<rev>.jsonl --abstracts <...>
"""

import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
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


TAG = "occurrence"
PROBE = ("import importlib.metadata as m, json; d = m.distribution('citations'); "
         "print(json.dumps({'version': d.version, "
         "'direct_url': json.loads(d.read_text('direct_url.json') or 'null')}))")


def commit_of(installed: dict) -> str | None:
    """The commit an installed distribution was built from, or None (an editable install, a
    local folder or an index release names none)."""
    url = installed.get("direct_url") or {}
    return (url.get("vcs_info") or {}).get("commit_id")


def installed_citations(run=subprocess.run) -> dict:
    """Version and install record of the `citations` on the path, asked of its own Python."""
    exe = shutil.which("citations")
    if exe is None:
        raise SpanCheckError("no citations on the path")
    first = pathlib.Path(exe).read_text().splitlines()[0]
    if not first.startswith("#!"):
        raise SpanCheckError(f"{exe} names no interpreter")
    done = run([first[2:].strip(), "-c", PROBE], capture_output=True, text=True, check=True)
    return json.loads(done.stdout)


def pin(claims_file: pathlib.Path, claim_id: str, span: str, env: dict,
        occurrence: int | None = None) -> tuple[str, list[str]]:
    extra = ["--occurrence", str(occurrence)] if occurrence is not None else []
    r = subprocess.run(["citations", "pin", str(claims_file), "--id", claim_id, "--quote", span,
                        *extra], capture_output=True, text=True, env=env)
    first = (r.stdout.splitlines() or [""])[0]
    state = "found" if r.returncode == 0 else first.split("  ")[0].strip() or "error"
    warnings = []
    for line in r.stdout.splitlines():
        if line.strip().startswith("warnings:"):
            warnings = [w.strip() for w in line.split(":", 1)[1].split(",")]
    return state, warnings


def pin_span(claims_file: pathlib.Path, claim_id: str, span: str, registered: bool, env: dict,
             pin_with=pin) -> tuple[str, list[str], str]:
    """(state, warnings, method). The first occurrence is pinned only for a span the registered
    quote check finds and the plain pin refuses as ambiguous."""
    state, warnings = pin_with(claims_file, claim_id, span, env)
    if state == "ambiguous" and registered:
        state, warnings = pin_with(claims_file, claim_id, span, env, occurrence=1)
        return state, warnings, "occurrence_1"
    return state, warnings, "plain"


def relative_paths(text: str, root: pathlib.Path = EXP) -> str:
    """The text with paths under `root` written relative to it (the `citations` CLI prints the
    absolute path of the claims folder; a stored output names no home folder)."""
    return text.replace(f"{root}/", "")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extraction", type=pathlib.Path, required=True)
    ap.add_argument("--abstracts", type=pathlib.Path, default=ABSTRACTS)
    ap.add_argument("--text-field", default="abstract", choices=["abstract", "body"])
    ap.add_argument("--citations-commit", required=True,
                    help="the commit the installed citations must have been installed from")
    a = ap.parse_args()
    installed = installed_citations()
    if commit_of(installed) != a.citations_commit:
        raise SpanCheckError(f"the installed citations ({installed}) is not the build of "
                             f"commit {a.citations_commit}")

    run = a.extraction.stem
    cit_root = EXP / "outputs" / f"citations_{TAG}" / run
    out_dir = EXP / "outputs" / f"verification_{TAG}" / run
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
    occurrences: dict[str, dict] = {}
    duplicated: dict[str, int] = {}
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
            registered = fold(span) in abstract_folded
            state, warnings, method = pin_span(claims_file, claim_id, span, registered, env)
            count = abstract_folded.count(fold(span)) if registered else 0
            if count > 1:
                duplicated[rec["pmid"]] = duplicated.get(rec["pmid"], 0) + 1
            if method != "plain":
                occurrences[f"{rec['pmid']}:{i:03d}"] = {
                    "pin_method": method, "occurrence_count": count, "state": state}
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

    (out_dir / "span_occurrences.json").write_text(json.dumps({
        "citations_installed": installed, "citations_commit": a.citations_commit,
        "rule": "first occurrence, only when the registered quote check holds and the plain "
                "pin is refused as ambiguous",
        "records_pinned_at_an_occurrence": occurrences,
        "stored_abstract_has_duplicated_passage": dict(sorted(duplicated.items()))},
        indent=1) + "\n")
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
