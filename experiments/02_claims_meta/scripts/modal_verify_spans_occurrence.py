"""Modal wrapper for scripts/verify_spans_occurrence.py, the span step of Amendment 2
(PREREG.md). The sealed script is run unchanged, under `citations` installed from the commit
named below (not editable; the script itself refuses any other build).

The step makes one call of the tool per evidence span and writes its results only when it
ends. Here an extraction file is cut into parts of consecutive rows (scripts/span_shards.py);
each part is one run of the sealed script in its own container; a part's results are stored on
the volume and committed as soon as it ends; a run that is started again takes the stored
parts and computes only the missing ones. The parts are then joined: `spans.jsonl` in order,
the union of `span_occurrences.json`, `span_summary.json` computed from the joined lines, and
`citations verify --strict` run once over the joined claims tree.

Run from experiments/02_claims_meta:

    modal run --detach scripts/modal_verify_spans_occurrence.py::synthetic
    modal run --detach scripts/modal_verify_spans_occurrence.py::span_step \\
        --extraction outputs/parsed/<file>.jsonl --abstracts outputs/parsed/<abstracts>.jsonl

`span_step` stores under `/02_claims_meta/amendment02/span_step/<stem>/` and saves locally the
four result files in `outputs/verification_occurrence/<stem>/` with `span_step_run.json` (the
build, the environment, the parts and every hash), and the claims tree in
`outputs/citations_occurrence/<stem>/`. It prints counts, paths and hashes, no record.

`synthetic` reads no study record and writes nothing on the volume: on made-up records it
checks that the files joined from parts are byte for byte the files the sealed script writes
for the whole file at once (the four results and the claims tree), that a span standing twice
in its abstract is pinned at its first occurrence and passes, that a span with a word left out
fails, and that the script refuses a build other than the one named.

Client modal 1.4.3; image python 3.12 debian_slim.
"""

import datetime
import json
import pathlib

import modal

COMMIT = "fb89bb6104be091585f87c8d1a35aa2fd2c44b74"
REPOSITORY = "https://github.com/elliottower/reproducible-science"
VOLUME = "proteome-mr-claim-audit-inputs"
MOUNT = pathlib.Path("/vol")
REMOTE = MOUNT / "02_claims_meta" / "amendment02" / "span_step"
EXP = pathlib.Path("/exp")
LOCAL_EXP = pathlib.Path(__file__).resolve().parents[1]
IGNORE = ["__pycache__", "*.pyc", ".pytest_cache"]
SCRIPT = "scripts/verify_spans_occurrence.py"
RESULTS = ("spans.jsonl", "span_occurrences.json", "span_summary.json", "citations_verify.txt")
TREE = "claims_tree.tar"

image = (modal.Image.debian_slim(python_version="3.12")
         .apt_install("git")
         .pip_install(
             "pydantic==2.13.5", "pyyaml==6.0.3", "platformdirs==4.12.3",
             f"provenance-core @ git+{REPOSITORY}@{COMMIT}#subdirectory=packages/provenance-core",
             f"citations @ git+{REPOSITORY}@{COMMIT}#subdirectory=packages/citations")
         .env({"PYTHONPATH": str(EXP / "scripts"), "PYTHONUTF8": "1"})
         .add_local_dir(LOCAL_EXP / "scripts", str(EXP / "scripts"), copy=True, ignore=IGNORE))
vol = modal.Volume.from_name(VOLUME)
app = modal.App("proteome-mr-verify-spans-occurrence", image=image)

with image.imports():
    import hashlib
    import importlib.metadata
    import io
    import os
    import platform
    import shutil
    import subprocess
    import tarfile

    import span_shards


def stamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def digests(files: dict[str, bytes]) -> dict[str, dict]:
    return {name: {"bytes": len(content), "sha256": sha256(content)}
            for name, content in sorted(files.items())}


def pack(folder: pathlib.Path) -> bytes:
    """The files of a claims tree as one tar, paths relative to the tree, in name order."""
    held = io.BytesIO()
    with tarfile.open(fileobj=held, mode="w") as tar:
        for path in sorted(p for p in folder.rglob("*") if p.is_file()):
            tar.add(path, arcname=str(path.relative_to(folder)))
    return held.getvalue()


def unpack(content: bytes, folder: pathlib.Path) -> None:
    """Add a part's tree to `folder`; a file that is already there stops the run."""
    with tarfile.open(fileobj=io.BytesIO(content)) as tar:
        for member in tar.getmembers():
            target = folder / member.name
            if target.exists():
                raise FileExistsError(f"{member.name} stands in two parts")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(tar.extractfile(member).read())


def tree_files(content: bytes) -> dict[str, bytes]:
    with tarfile.open(fileobj=io.BytesIO(content)) as tar:
        return {m.name: tar.extractfile(m).read() for m in tar.getmembers()}


def command(name: str, commit: str = COMMIT) -> list[str]:
    return ["python", SCRIPT, "--citations-commit", commit,
            "--extraction", f"outputs/parsed/{name}.jsonl",
            "--abstracts", f"outputs/parsed/{name}.abstracts.jsonl"]


def run_sealed(name: str, rows: bytes, abstracts: bytes, commit: str = COMMIT
               ) -> tuple[int, str, dict[str, bytes]]:
    """The sealed script on one file, from /exp. Returns the return code, the end of stderr
    and the four results with the claims tree."""
    parsed = EXP / "outputs" / "parsed"
    parsed.mkdir(parents=True, exist_ok=True)
    (parsed / f"{name}.jsonl").write_bytes(rows)
    (parsed / f"{name}.abstracts.jsonl").write_bytes(abstracts)
    run = subprocess.run(command(name, commit), cwd=EXP, capture_output=True, text=True)
    if run.returncode:
        return run.returncode, run.stderr[-3000:], {}
    out = EXP / "outputs" / "verification_occurrence" / name
    files = {n: (out / n).read_bytes() for n in RESULTS}
    files[TREE] = pack(EXP / "outputs" / "citations_occurrence" / name)
    return 0, "", files


def join(extraction_name: str, parts: list[dict[str, bytes]]) -> dict[str, bytes]:
    """The results of the whole file from its parts' results, in order."""
    stem = pathlib.Path(extraction_name).stem
    tree = EXP / "outputs" / "citations_occurrence" / stem
    shutil.rmtree(tree, ignore_errors=True)
    (tree / "sources").mkdir(parents=True)
    (tree / "claims").mkdir()
    for part in parts:
        unpack(part[TREE], tree)
    spans = span_shards.join_spans([p["spans.jsonl"].decode().splitlines() for p in parts])
    occurrences = span_shards.join_occurrences(
        [json.loads(p["span_occurrences.json"]) for p in parts])
    env = {k: v for k, v in os.environ.items() if k != "CITATIONS_HOME"}
    verify = subprocess.run(["citations", "verify", "--claims",
                             f"outputs/citations_occurrence/{stem}/claims", "--strict"],
                            capture_output=True, text=True, env=env, cwd=EXP)
    text = f"exit {verify.returncode}\n{verify.stdout}\n{verify.stderr}".replace(f"{EXP}/", "")
    return {"spans.jsonl": "".join(line + "\n" for line in spans).encode(),
            "span_occurrences.json": span_shards.occurrences_text(occurrences).encode(),
            "span_summary.json": span_shards.summary_text(
                f"outputs/parsed/{extraction_name}", spans, verify.returncode).encode(),
            "citations_verify.txt": text.encode(), TREE: pack(tree)}


def environment() -> dict:
    dist = importlib.metadata.distribution("citations")
    return {"python": platform.python_version(), "platform": platform.platform(),
            "image": "modal debian_slim, python 3.12",
            "citations": {"version": dist.version,
                          "direct_url": json.loads(dist.read_text("direct_url.json") or "null")},
            "packages": {d.metadata["Name"]: d.version
                         for d in sorted(importlib.metadata.distributions(),
                                         key=lambda d: d.metadata["Name"].lower())},
            "modal": modal.__version__,
            "scripts_sha256": {s: sha256((EXP / s).read_bytes())
                               for s in (SCRIPT, "scripts/span_shards.py",
                                         "scripts/modal_verify_spans_occurrence.py")}}


@app.function(volumes={str(MOUNT): vol}, timeout=6 * 3600, cpu=1.0, memory=2048, retries=2,
              max_containers=40)
def span_part(stem: str, index: int, rows: bytes, abstracts: bytes) -> dict:
    name = span_shards.shard_stem(stem, index)
    out = REMOTE / stem / "parts" / name
    sent = {"rows_sha256": sha256(rows), "abstracts_sha256": sha256(abstracts)}
    vol.reload()
    if (out / "DONE.json").exists():
        done = json.loads((out / "DONE.json").read_text())
        if {k: done[k] for k in sent} != sent:
            raise RuntimeError(f"{name}: a stored part was made from other rows")
        return done
    code, stderr, files = run_sealed(name, rows, abstracts)
    if code:
        raise RuntimeError(f"{name}: verify_spans_occurrence.py failed:\n{stderr}")
    out.mkdir(parents=True, exist_ok=True)
    for file, content in files.items():
        (out / file).write_bytes(content)
    done = {"part": name, **sent, "files": digests(files), "finished_utc": stamp()}
    (out / "DONE.json").write_text(json.dumps(done, indent=1) + "\n")
    vol.commit()
    return done


@app.function(volumes={str(MOUNT): vol}, timeout=24 * 3600, cpu=2.0, memory=8192)
def span_file_job(extraction_name: str, extraction: bytes, abstracts: bytes,
                  part_rows: int) -> dict:
    stem = pathlib.Path(extraction_name).stem
    joined = REMOTE / stem / "joined"
    sent = {"extraction": {"file": extraction_name, "sha256": sha256(extraction)},
            "abstracts_sha256": sha256(abstracts), "part_rows": part_rows}
    if (joined / "span_step_run.json").exists():
        record = json.loads((joined / "span_step_run.json").read_text())
        if {k: record[k] for k in sent} != sent:
            raise RuntimeError(f"{stem}: a stored result was made from other inputs")
        return {"record": record,
                "files": {n: (joined / n).read_bytes() for n in (*RESULTS, TREE)}}
    lines = [line for line in extraction.decode().splitlines() if line.strip()]
    abstract_lines = abstracts.decode().splitlines()
    parts = span_shards.split(lines, part_rows)
    done = list(span_part.starmap(
        [(stem, i, "".join(line + "\n" for line in part).encode(),
          "".join(line + "\n" for line in span_shards.abstracts_for(part, abstract_lines)
                  ).encode()) for i, part in enumerate(parts)]))
    vol.reload()
    stored = []
    for i, part in enumerate(done):
        folder = REMOTE / stem / "parts" / span_shards.shard_stem(stem, i)
        files = {n: (folder / n).read_bytes() for n in (*RESULTS, TREE)}
        if digests(files) != part["files"]:
            raise RuntimeError(f"{folder}: the stored part differs from what its run reported")
        stored.append(files)
    files = join(extraction_name, stored)
    record = {**sent, "written_utc": stamp(), "citations_commit": COMMIT,
              "repository": REPOSITORY, "command_per_part": command("<part>"),
              "parts": done, "joined": digests(files), "environment": environment(),
              "volume_folder": str(REMOTE / stem)}
    joined.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (joined / name).write_bytes(content)
    (joined / "span_step_run.json").write_text(json.dumps(record, indent=1) + "\n")
    vol.commit()
    return {"record": record, "files": files}


def synthetic_records() -> tuple[bytes, bytes]:
    """Made-up papers: spans that stand once, a span that stands twice, a span with a word left
    out, a span that is nowhere, a paper whose extraction failed, a paper with no claim."""
    twice = "Higher protein Q was associated with lower risk of stroke in the main analysis."
    abstracts = {
        "s1": f"Background. Protein A raised LDL cholesterol in adults (beta 0.20). {twice}",
        "s2": f"{twice} Other proteins were null. {twice} Sensitivity analyses agreed.",
        "s3": "Genetically predicted protein B was causally associated with asthma (OR 1.30).",
        "s4": "Protein C lowered fasting glucose across the three cohorts that were studied.",
        "s5": "Protein D had no association with any outcome that was tested here at all.",
        "s6": "An abstract whose extraction failed and that holds no claim record at all.",
        "s7": "Protein E was associated with body mass index in the pooled sample (P < 0.001)."}
    spans = {"s1": ["Protein A raised LDL cholesterol in adults (beta 0.20).", twice],
             "s2": [twice, "Other proteins were null."],
             "s3": ["Genetically predicted protein B was associated with asthma (OR 1.30)."],
             "s4": ["Protein C lowered fasting glucose across the three cohorts",
                    "Protein C raised fasting glucose across the three cohorts"],
             "s5": [], "s7": ["protein e  was associated with body mass index"]}
    rows = [{"pmid": k, "status": "ok",
             "output": {"claims": [{"evidence_span": s} for s in v]}} for k, v in spans.items()]
    rows.insert(5, {"pmid": "s6", "status": "extraction_failed", "output": None})
    return ("".join(json.dumps(r) + "\n" for r in rows).encode(),
            "".join(json.dumps({"pmid": k, "abstract": v}) + "\n"
                    for k, v in abstracts.items()).encode())


@app.function(timeout=3600, cpu=2.0, memory=4096)
def synthetic_job() -> dict:
    s = stamp()
    checks: dict = {"stamp": s, "environment": environment()}
    name = f"synthetic_{s}"
    rows, abstracts = synthetic_records()
    code, stderr, whole = run_sealed(name, rows, abstracts)
    checks["sealed_script_completes"] = code == 0
    if code:
        return checks | {"stderr": stderr, "passed": False}
    lines = [line for line in rows.decode().splitlines() if line.strip()]
    abstract_lines = abstracts.decode().splitlines()
    for size in (2, 3):
        results = []
        for i, part in enumerate(span_shards.split(lines, size)):
            code, stderr, files = run_sealed(
                span_shards.shard_stem(f"{name}_by{size}", i),
                "".join(line + "\n" for line in part).encode(),
                "".join(line + "\n" for line in span_shards.abstracts_for(part, abstract_lines)
                        ).encode())
            if code:
                return checks | {"stderr": stderr, "passed": False}
            results.append(files)
        joined = join(f"{name}.jsonl", results)
        # The joined tree is unpacked under the whole file's name, so it is compared after
        # the whole file's own tree was packed.
        checks[f"parts_of_{size}_results_byte_identical"] = {
            n: joined[n] == whole[n] for n in RESULTS}
        checks[f"parts_of_{size}_claims_tree_identical"] = (
            tree_files(joined[TREE]) == tree_files(whole[TREE]))
        checks[f"parts_of_{size}_hold"] = (
            all(checks[f"parts_of_{size}_results_byte_identical"].values())
            and checks[f"parts_of_{size}_claims_tree_identical"])
    spans = {(r["pmid"], r["claim_index"]): r
             for r in map(json.loads, whole["spans.jsonl"].decode().splitlines())}
    used = json.loads(whole["span_occurrences.json"])["records_pinned_at_an_occurrence"]
    checks["records"] = len(spans)
    checks["span_standing_twice_is_pinned_at_first_occurrence_and_passes"] = (
        spans[("s2", 0)]["passes"] and set(used) == {"s2:000"}
        and used["s2:000"]["occurrence_count"] == 2)
    checks["span_standing_once_passes_without_an_occurrence"] = all(
        spans[k]["passes"] for k in (("s1", 0), ("s1", 1), ("s2", 1), ("s4", 0), ("s7", 0)))
    checks["span_with_a_word_left_out_fails"] = not spans[("s3", 0)]["passes"]
    checks["span_with_a_changed_word_fails"] = not spans[("s4", 1)]["passes"]
    checks["strict_verify_exit"] = json.loads(whole["span_summary.json"])["citations_verify_exit"]
    code, stderr, _ = run_sealed(f"{name}_other_build", rows, abstracts, commit="0" * 40)
    checks["another_build_is_refused"] = code != 0 and "is not the build of commit" in stderr
    checks["installed_commit_is_the_named_one"] = (
        (checks["environment"]["citations"]["direct_url"] or {}).get("vcs_info", {})
        .get("commit_id") == COMMIT)
    checks["passed"] = all(v for k, v in checks.items() if isinstance(v, bool))
    return checks


def save_local(folder: str, name: str, content: str | bytes) -> pathlib.Path:
    path = LOCAL_EXP / folder / name
    if path.exists():
        raise FileExistsError(f"{path} exists; archive it before rerunning")
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content)
    return path


@app.local_entrypoint()
def synthetic() -> None:
    result = synthetic_job.remote()
    path = save_local("outputs/tests", f"verify_spans_occurrence_modal_{result['stamp']}.json",
                      json.dumps(result, indent=1) + "\n")
    print(path)
    print(json.dumps({k: v for k, v in result.items() if isinstance(v, bool)}, indent=1))
    if not result["passed"]:
        raise SystemExit("a synthetic check failed")


@app.local_entrypoint()
def span_step(extraction: str, abstracts: str, part_rows: int = 40) -> None:
    path = pathlib.Path(extraction)
    out = LOCAL_EXP / "outputs" / "verification_occurrence" / path.stem
    tree = LOCAL_EXP / "outputs" / "citations_occurrence" / path.stem
    if out.exists() or tree.exists():
        raise FileExistsError(f"{out} or {tree} exists; a verification run is never overwritten")
    result = span_file_job.remote(path.name, path.read_bytes(),
                                  pathlib.Path(abstracts).read_bytes(), part_rows)
    for name in RESULTS:
        save_local(f"outputs/verification_occurrence/{path.stem}", name, result["files"][name])
    save_local(f"outputs/verification_occurrence/{path.stem}", "span_step_run.json",
               json.dumps(result["record"], indent=1) + "\n")
    for name, content in tree_files(result["files"][TREE]).items():
        save_local(f"outputs/citations_occurrence/{path.stem}", name, content)
    summary = json.loads(result["files"]["span_summary.json"])
    print(json.dumps({"stem": path.stem, "parts": len(result["record"]["parts"]),
                      "n_claims": summary["n_claims"], "both_pass": summary["both_pass"],
                      "citations_verify_exit": summary["citations_verify_exit"],
                      "joined": result["record"]["joined"]}, indent=1))
