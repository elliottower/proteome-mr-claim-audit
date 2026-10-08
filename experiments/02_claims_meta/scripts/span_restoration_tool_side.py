# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml==6.0.3"]
# ///
"""The restored passage of each record of a repair map, as the `citations` tool gives it
(PREREG.md, Amendment 2). The study's own restoration (scripts/span_restoration_v2.py) is
cross-checked against this by hash; neither is taken from the other.

For each record of the map, the stored abstract is written as a pinned source and the span the
model wrote as a claim, in a claims tree under `--out`, the only place anything is written.
`citations restore` is then asked for the record, with its default limit of one token left
out. The tool never changes the claims file it is given: it writes the source's passage as a
derived claim in a file beside it, `<name>.restored.yaml`. A refusal stops the run.

The script refuses to run unless the `citations` it imports was installed from the commit given
with `--citations-commit` (read from the installed distribution's `direct_url.json`).

Written, with no text of any abstract or span outside the claims tree:
    <out>/citations/{sources,claims}/        the tree, with the tool's sidecars
    <out>/tool_side_passages.json            per record `<label>:<record id>`: the sha256 of
                                             the restored passage's UTF-8 bytes, its offsets,
                                             the stretches left out, the number of fittings,
                                             the rule, and the hashes of the source and of the
                                             text the offsets count in; and the installed build

Usage, with the build named for uv:
    uv run --with "citations @ git+<repository>@<commit>#subdirectory=packages/citations" \\
        scripts/span_restoration_tool_side.py --map <repair_map.json> --label <label> \\
        --extraction <parsed jsonl> --abstracts <eligible_abstracts.jsonl> [...] \\
        --citations-commit <40 hex> --out <dir>
"""

import argparse
import contextlib
import hashlib
import importlib
import importlib.metadata
import io
import json
import pathlib

import yaml


class ToolSideError(Exception):
    """The installed build is not the pinned one, or the tool refused a record."""


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def installed() -> dict:
    dist = importlib.metadata.distribution("citations")
    return {"version": dist.version,
            "direct_url": json.loads(dist.read_text("direct_url.json") or "null")}


def commit_of(build: dict) -> str | None:
    return ((build.get("direct_url") or {}).get("vcs_info") or {}).get("commit_id")


def write_tree(root: pathlib.Path, records: dict[str, str], abstracts: dict[str, str]
               ) -> dict[str, pathlib.Path]:
    """One source and one claims file per paper; record id -> its claims file. `records` is
    record id (`<paper>:<index>`) -> the span the model wrote."""
    (root / "sources").mkdir(parents=True)
    (root / "claims").mkdir()
    files, by_paper = {}, {}
    for rid, span in records.items():
        by_paper.setdefault(rid.split(":")[0], {})[rid] = span
    for paper, spans in by_paper.items():
        src = root / "sources" / f"pmid{paper}.txt"
        src.write_text(abstracts[paper])
        claims_file = root / "claims" / f"pmid{paper}.yaml"
        claims_file.write_text(yaml.safe_dump({
            "source": {"citation": f"pmid{paper}", "local": f"sources/{src.name}",
                       "sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
                       "note": "abstract text exactly as sent to the extractor"},
            "claims": {f"c{rid.split(':')[1]}": {"quotes": [{"exact": span}]}
                       for rid, span in spans.items()}}, sort_keys=False, allow_unicode=True))
        files |= dict.fromkeys(spans, claims_file)
    return files


def restore_all(files: dict[str, pathlib.Path], restore_main) -> dict[str, dict]:
    """record id -> what the tool wrote for it. `restore_main` is `citations.restore.main`."""
    out = {}
    for rid, claims_file in files.items():
        before = claims_file.read_bytes()
        claim_id = f"c{rid.split(':')[1]}"
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = restore_main([str(claims_file), "--id", claim_id])
        if code != 0:
            raise ToolSideError(f"{rid}: citations restore refused the record (exit {code})")
        if claims_file.read_bytes() != before:
            raise ToolSideError(f"{rid}: the claims file given to the tool was changed")
        sidecar = claims_file.with_name(f"{claims_file.stem}.restored.yaml")
        made = yaml.safe_load(sidecar.read_text())["claims"][f"{claim_id}-restored"]
        record = made["restored"]
        out[rid] = {"restored_passage_sha256": sha(made["quotes"][0]["exact"]),
                    "passage_start": record["passage"]["start"],
                    "passage_end": record["passage"]["end"],
                    "omitted": record["omitted"], "fittings": record["fittings"]["found"],
                    "source_sha256": record["source"]["sha256"],
                    "text_sha256": record["text"]["sha256"], "rule": record["rule"],
                    "original_span_sha256": sha(record["original"])}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", type=pathlib.Path, required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--extraction", type=pathlib.Path, required=True)
    ap.add_argument("--abstracts", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--citations-commit", required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    build = installed()
    if commit_of(build) != a.citations_commit:
        raise ToolSideError(f"the installed citations ({build}) is not the build of commit "
                            f"{a.citations_commit}")
    if a.out.exists():
        raise ToolSideError(f"{a.out} exists; a restoration is written once")
    repairs = json.loads(a.map.read_text())["repairs"]
    abstracts: dict[str, str] = {}
    for path in a.abstracts:
        for line in path.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                abstracts.setdefault(rec["pmid"], rec["abstract"])
    spans = {}
    for line in a.extraction.read_text().splitlines():
        row = json.loads(line) if line.strip() else {"status": ""}
        if row["status"] == "ok":
            for index, claim in enumerate(row["output"]["claims"]):
                if f"{row['pmid']}:{index:03d}" in repairs:
                    spans[f"{row['pmid']}:{index:03d}"] = claim["evidence_span"]
    if sorted(spans) != sorted(repairs):
        raise ToolSideError("a record of the map is not in the extraction file")
    files = write_tree(a.out / "citations", spans, abstracts)
    made = restore_all(files, importlib.import_module("citations.restore").main)
    for rid, entry in made.items():
        if entry["original_span_sha256"] != repairs[rid]["original_span_sha256"]:
            raise ToolSideError(f"{rid}: the tool's record is of another span")
    (a.out / "tool_side_passages.json").write_text(json.dumps({
        "what": "restored passages as `citations restore` wrote them; hashes and offsets only",
        "citations_installed": build, "citations_commit": a.citations_commit,
        "map": str(a.map), "map_sha256": hashlib.sha256(a.map.read_bytes()).hexdigest(),
        "records": {f"{a.label}:{rid}": entry for rid, entry in sorted(made.items())}},
        indent=1) + "\n")
    print(json.dumps({"records": len(made),
                      "fittings": {str(n): sum(e["fittings"] == n for e in made.values())
                                   for n in sorted({e["fittings"] for e in made.values()})},
                      "tokens_left_out": sorted({sum(o["tokens"] for o in e["omitted"])
                                                 for e in made.values()})}))


if __name__ == "__main__":
    main()
