# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""The manifest of a manual dataset-coding run before coding starts (PREREG.md log,
2026-10-07): one file tying the queue, the dictionary, the generator, its inputs, its outputs,
the assignment and the coder instructions together by sha256.

A folder's hash is the sha256 of its sorted lines `<sha256>  <relative path>`. The citations
folder is hashed over `sources/` only, because coders add quotations to `claims/`. The manifest
also counts the attempt files in the coders' folders, which is 0 before any coder has started.

Usage: uv run scripts/manual_coding_manifest.py --queue <csv> --dictionary <csv> \\
           --scripts <generator> <assignment> <gates> <table> --instructions <md> \\
           --abstracts <jsonl> [...] --fulltext <dir> --passages <dir> --citations <dir> \\
           --coders <dir> --superseded <dir> [...] --out <run_manifest.json>
"""

import argparse
import datetime
import hashlib
import json
import pathlib


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tree(folder: pathlib.Path) -> dict:
    files = sorted(p for p in folder.rglob("*") if p.is_file())
    lines = "".join(f"{sha256(p)}  {p.relative_to(folder).as_posix()}\n" for p in files)
    return {"path": str(folder), "files": len(files),
            "sha256": hashlib.sha256(lines.encode()).hexdigest()}


def one(path: pathlib.Path) -> dict:
    return {"path": str(path), "sha256": sha256(path)}


def main() -> None:
    ap = argparse.ArgumentParser()
    for name in ("queue", "dictionary", "instructions", "fulltext", "passages", "citations",
                 "coders", "out"):
        ap.add_argument(f"--{name}", type=pathlib.Path, required=True)
    ap.add_argument("--scripts", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--abstracts", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--superseded", type=pathlib.Path, nargs="*", default=[])
    a = ap.parse_args()
    if a.out.exists():
        raise FileExistsError(f"{a.out} exists; a manifest is written once")
    assignment = json.loads((a.coders / "assignment.json").read_text())
    coders = sorted(p for p in a.coders.glob("coder_*") if p.is_dir())
    manifest = {
        "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "queue": one(a.queue), "dictionary": one(a.dictionary),
        "scripts": [one(p) for p in a.scripts], "coder_instructions": one(a.instructions),
        "abstract_inputs": [one(p) for p in a.abstracts], "full_text_input": tree(a.fulltext),
        "passages": tree(a.passages),
        "passages_summary": json.loads((a.passages / "passages_summary.json").read_text()),
        "citations_sources": tree(a.citations / "sources"),
        "assignment": {**one(a.coders / "assignment.json"), "seed": assignment["seed"],
                       "n_coders": assignment["n_coders"],
                       "papers_per_coder": assignment["papers_per_coder"]},
        "dictionary_definitions": one(a.coders / "dictionary_definitions.csv"),
        "coder_inputs": {c.name: tree(c / "input") for c in coders},
        "attempt_files_before_coding": sum(len(list((c / "codes").glob("*"))) for c in coders),
        "superseded_outputs": [tree(p) for p in a.superseded],
    }
    a.out.write_text(json.dumps(manifest, indent=1) + "\n")
    print(json.dumps({k: manifest[k] for k in ("attempt_files_before_coding",)}
                     | {"passages_sha256": manifest["passages"]["sha256"],
                        "assignment_sha256": manifest["assignment"]["sha256"]}, indent=1))


if __name__ == "__main__":
    main()
