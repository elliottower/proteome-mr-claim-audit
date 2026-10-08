# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Digest of what one build of `citations` makes of every stored abstract and evidence span
with its two folding functions (PREREG.md, Amendment 2). Run once under each build; the two
digests must be equal for the corrected build to read the study's texts as the registered one
did. No text is written: per text, the sha256 of `passage_fold` and of `skeleton`.

Usage, with the build named for uv:
    uv run --with "citations @ git+<repository>@<commit>#subdirectory=packages/citations" \\
        scripts/citations_fold_digest.py --spans <label>=<spans.jsonl> [...] \\
        --abstracts <eligible_abstracts.jsonl> [...] --out <json>
"""

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import pathlib


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def digest(texts: dict[str, str], folds: dict) -> dict:
    """text id -> {fold name: sha256 of the folded text}, and one sha256 over all of it."""
    items = {key: {name: sha(fold(text)) for name, fold in sorted(folds.items())}
             for key, text in sorted(texts.items())}
    return {"items": items, "texts": len(items),
            "sha256": sha(json.dumps(items, sort_keys=True))}


def collect(spans: list[str], abstracts: list[pathlib.Path]) -> dict[str, str]:
    """Every evidence span of the span files and the abstract of every record they name."""
    records = {}
    for path in abstracts:
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                records.setdefault(r["pmid"], r["abstract"])
    texts = {}
    for item in spans:
        label, path = item.split("=", 1)
        for line in pathlib.Path(path).read_text().splitlines():
            r = json.loads(line)
            texts[f"span:{label}:{r['pmid']}:{r['claim_index']:03d}"] = r["evidence_span"]
            texts[f"abstract:{r['pmid']}"] = records[r["pmid"]]
    return texts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spans", nargs="+", required=True)
    ap.add_argument("--abstracts", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise FileExistsError(f"{a.out} exists; a digest is written once")
    verify = importlib.import_module("citations.verify")
    dist = importlib.metadata.distribution("citations")
    made = digest(collect(a.spans, a.abstracts),
                  {"passage_fold": verify.passage_fold, "skeleton": verify.skeleton})
    made["citations"] = {"version": dist.version,
                         "direct_url": json.loads(dist.read_text("direct_url.json") or "null")}
    a.out.write_text(json.dumps(made, indent=1) + "\n")
    print(json.dumps({k: made[k] for k in ("texts", "sha256", "citations")}, indent=1))


if __name__ == "__main__":
    main()
