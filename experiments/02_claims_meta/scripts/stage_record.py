# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.13.5"]
# ///
"""Record a stage's outputs in the results ledger (`results run`), through one manifest.

`results run` takes files, not folders, and a stage writes thousands of files (raw responses) or
writes on the Modal volume. `record` hashes every file under the paths given into one manifest,
`outputs/results_manifests/<run-id>.json`, and records that manifest and the files named with
`--file` in the ledger. For a stage that ran on Modal, `--volume-hashes` (the listing written by
`modal run scripts/modal_hash_volume.py::tree`) and one `--volume-map <volume folder>=<local
folder>` per folder compare every local copy with the file on the volume; a local copy whose
bytes differ from the volume file, or that the volume does not hold, raises before anything is
recorded. `results verify --files` then checks the manifest's own hash, and `verify` here
rehashes every file each manifest names.

`--volume-map` also takes one volume file and one local file, for a result a Modal job wrote
beside its folders.

`replace` puts new bytes in a file that manifests already name (for example to strip an
absolute path from a stored tool output). It refuses unless the file still has the bytes every
manifest naming it recorded; it moves the original to the archive folder given, writes the new
bytes, and adds one row per manifest to `outputs/results_manifests/replaced_files.json` (run id,
path, recorded sha256, replaced sha256, reason, time). `verify` then accepts that file only with
exactly the replaced sha256: any other byte, or a row whose recorded sha256 is not the
manifest's, is still reported as CHANGED. The table is committed, so every replacement is in
the history.

`plan` writes `outputs/results_manifests/prereg_freeze.plan.json`: the commit, plan sha256 and
date in the freeze header of PREREG.md, after `prereg check` passes. That file is what
`results seal --role prereg` seals. PREREG.md itself is not sealed: `prereg log` appends to it,
so its whole-file hash changes with every log line, while the plan sha256 (everything above the
log) does not. `verify` compares the header with the record and runs `prereg check` again.

Usage, from experiments/02_claims_meta:
  uv run scripts/stage_record.py plan
  uv run scripts/stage_record.py record --run-id <id> --note "<what the run computed>" \
      [--file <result file> ...] [--volume-hashes <listing.json> --volume-map <remote>=<local> ...] \
      <file or folder> ...
  uv run scripts/stage_record.py verify [--run-id <id>]
  uv run scripts/stage_record.py replace --path <recorded file> --new <file with the new bytes> \
      --archive <folder for the original> --reason "<why>"

The note is written to the ledger, which is public text.
"""

import argparse
import collections
import datetime
import hashlib
import json
import pathlib
import re
import subprocess

from pydantic import BaseModel

MANIFESTS = pathlib.Path("outputs/results_manifests")
VOLUME_LISTING = ".volume.json"  # listings of modal_hash_volume.py::tree kept beside the manifests
PLAN_SUFFIX = ".plan.json"  # the freeze record written by `plan`
REPLACED_NAME = "replaced_files.json"  # the table written by `replace`
PLAN = pathlib.Path("PREREG.md")
PLAN_RECORD = MANIFESTS / f"prereg_freeze{PLAN_SUFFIX}"
STATUS_LINE = re.compile(r"^\*\*Status:\*\* FROZEN at `([0-9a-f]{7,40})`", re.M)
HASH_LINE = re.compile(r"^\*\*Plan sha256:\*\* `([0-9a-f]{64})`", re.M)
DATE_LINE = re.compile(r"^\*\*Frozen:\*\* (\d{4}-\d{2}-\d{2})", re.M)


class StageRecordError(Exception):
    """A manifest exists, a path is missing, or a local copy differs from the volume file."""


class FileEntry(BaseModel):
    path: str
    bytes: int
    sha256: str


class VolumeCheck(BaseModel):
    volume_folder: str
    local_folder: str
    n_compared: int
    volume_only: list[str]


class PlanRecord(BaseModel):
    plan: str
    frozen_at_commit: str
    plan_sha256: str
    frozen: str


class Replacement(BaseModel):
    run_id: str
    path: str
    recorded_sha256: str
    replaced_sha256: str
    reason: str
    replaced_utc: str


class Manifest(BaseModel):
    run_id: str
    note: str
    written_utc: str
    files: list[FileEntry]
    recorded_directly: list[str]
    volume_checks: list[VolumeCheck]


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def expand(paths: list[pathlib.Path]) -> list[pathlib.Path]:
    """Every file under the paths given, sorted, each once."""
    out: set[pathlib.Path] = set()
    for p in paths:
        if p.is_dir():
            out |= {q for q in p.rglob("*") if q.is_file()}
        elif p.is_file():
            out.add(p)
        else:
            raise StageRecordError(f"{p} is neither a file nor a folder")
    return sorted(out)


def entries(files: list[pathlib.Path]) -> list[FileEntry]:
    return [FileEntry(path=str(p), bytes=p.stat().st_size, sha256=sha256(p)) for p in files]


def compare_volume(files: list[FileEntry], volume: dict[str, dict], volume_folder: str,
                   local_folder: str) -> VolumeCheck:
    """Each local file under local_folder against the volume file of the same relative path."""
    remote_root = "/" + volume_folder.strip("/")
    local_root = pathlib.Path(local_folder)
    wrong, seen = [], set()
    for entry in files:
        path = pathlib.Path(entry.path)
        if path == local_root:
            remote = remote_root  # one local file mapped to one volume file
        elif path.is_relative_to(local_root):
            remote = f"{remote_root}/{path.relative_to(local_root).as_posix()}"
        else:
            continue
        seen.add(remote)
        held = volume.get(remote)
        if held is None:
            wrong.append(f"{entry.path}: not on the volume as {remote}")
        elif held["sha256"] != entry.sha256 or held["bytes"] != entry.bytes:
            wrong.append(f"{entry.path}: local {entry.sha256[:12]} ({entry.bytes} bytes), "
                         f"volume {held['sha256'][:12]} ({held['bytes']} bytes)")
    if not seen:
        raise StageRecordError(f"no recorded file lies under {local_folder}")
    if wrong:
        raise StageRecordError("local copies differ from the volume:\n  " + "\n  ".join(wrong))
    under = sorted(r for r in volume if r.startswith(remote_root + "/"))
    return VolumeCheck(volume_folder=remote_root, local_folder=str(local_root),
                       n_compared=len(seen), volume_only=[r for r in under if r not in seen])


def build(run_id: str, note: str, paths: list[pathlib.Path], direct: list[pathlib.Path],
          volume: dict[str, dict], maps: list[tuple[str, str]]) -> Manifest:
    files = entries(expand([*paths, *direct]))
    checks = [compare_volume(files, volume, remote, local) for remote, local in maps]
    stamp = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
    return Manifest(run_id=run_id, note=note, written_utc=stamp, files=files,
                    recorded_directly=sorted(str(p) for p in direct), volume_checks=checks)


def ledger_argv(manifest_path: pathlib.Path, manifest: Manifest) -> list[str]:
    return ["results", "run", "--run-id", manifest.run_id, "--note", manifest.note,
            str(manifest_path), *manifest.recorded_directly]


def record(run_id: str, note: str, paths: list[pathlib.Path], direct: list[pathlib.Path],
           volume: dict[str, dict], maps: list[tuple[str, str]],
           folder: pathlib.Path = MANIFESTS, run=subprocess.run) -> pathlib.Path:
    target = folder / f"{run_id}.json"
    for suffix in (VOLUME_LISTING, PLAN_SUFFIX):
        if target.name.endswith(suffix):
            raise StageRecordError(f"a run id cannot end in {suffix.removesuffix('.json')}")
    if target.name == REPLACED_NAME:
        raise StageRecordError(f"a run id cannot be {REPLACED_NAME.removesuffix('.json')}")
    if target.exists():
        raise StageRecordError(f"{target} exists; a run id is recorded once")
    manifest = build(run_id, note, paths, direct, volume, maps)
    folder.mkdir(parents=True, exist_ok=True)
    target.write_text(manifest.model_dump_json(indent=1) + "\n")
    run(ledger_argv(target, manifest), check=True)
    return target


def manifest_paths(folder: pathlib.Path) -> list[pathlib.Path]:
    return sorted(p for p in folder.glob("*.json")
                  if not p.name.endswith((VOLUME_LISTING, PLAN_SUFFIX))
                  and p.name != REPLACED_NAME)


def load_replacements(folder: pathlib.Path = MANIFESTS) -> list[Replacement]:
    table = folder / REPLACED_NAME
    if not table.exists():
        return []
    return [Replacement.model_validate(r) for r in json.loads(table.read_text())]


def verify(folder: pathlib.Path = MANIFESTS, run_id: str | None = None) -> dict[str, list[str]]:
    """Per manifest, the files that are missing or no longer match their recorded hash. A file
    replaced through `replace` matches when it has exactly the replaced bytes of its row."""
    wrong: dict[str, list[str]] = {}
    replaced = {(r.run_id, r.path, r.recorded_sha256): r.replaced_sha256
                for r in load_replacements(folder)}
    targets = [folder / f"{run_id}.json"] if run_id else manifest_paths(folder)
    for target in targets:
        manifest = Manifest.model_validate_json(target.read_text())
        bad = []
        for entry in manifest.files:
            path = pathlib.Path(entry.path)
            if not path.is_file():
                bad.append(f"MISSING  {entry.path}")
                continue
            now = sha256(path)
            if now != entry.sha256 and now != replaced.get(
                    (manifest.run_id, entry.path, entry.sha256)):
                bad.append(f"CHANGED  {entry.path}")
        wrong[manifest.run_id] = bad
    return wrong


def replace(path: pathlib.Path, new_bytes: bytes, archive: pathlib.Path, reason: str,
            folder: pathlib.Path = MANIFESTS) -> list[Replacement]:
    """Put `new_bytes` in a recorded file: the original goes to `archive`/<path>, and one row
    per manifest naming the file goes into the table. Refused when the file does not have the
    bytes a manifest recorded, when the archive already holds it, or when nothing changes."""
    if not reason.strip():
        raise StageRecordError("a replacement needs its reason")
    current = sha256(path)
    new_sha = hashlib.sha256(new_bytes).hexdigest()
    if new_sha == current:
        raise StageRecordError(f"{path}: the new bytes are the recorded bytes")
    naming = []
    for target in manifest_paths(folder):
        manifest = Manifest.model_validate_json(target.read_text())
        for entry in manifest.files:
            if entry.path == str(path):
                if entry.sha256 != current:
                    raise StageRecordError(f"{path} no longer has the bytes {manifest.run_id} "
                                           f"recorded; it is not replaced")
                naming.append(manifest.run_id)
    if not naming:
        raise StageRecordError(f"no manifest names {path}; edit it without `replace`")
    kept = archive / path
    if kept.exists():
        raise StageRecordError(f"{kept} exists; an original is archived once")
    kept.parent.mkdir(parents=True, exist_ok=True)
    kept.write_bytes(path.read_bytes())
    path.write_bytes(new_bytes)
    stamp = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
    rows = [Replacement(run_id=run_id, path=str(path), recorded_sha256=current,
                        replaced_sha256=new_sha, reason=reason, replaced_utc=stamp)
            for run_id in naming]
    table = folder / REPLACED_NAME
    table.write_text(json.dumps(
        [r.model_dump() for r in [*load_replacements(folder), *rows]], indent=1) + "\n")
    return rows


def read_plan(path: pathlib.Path = PLAN, run=subprocess.run) -> PlanRecord:
    """The freeze recorded in the plan's header, once `prereg check` reports the plan unchanged."""
    text = path.read_text()
    found = [pattern.search(text) for pattern in (STATUS_LINE, HASH_LINE, DATE_LINE)]
    if not all(found):
        raise StageRecordError(f"{path} carries no freeze header; run `prereg freeze` first")
    done = run(["prereg", "check"], capture_output=True, text=True)
    if done.returncode != 0:
        raise StageRecordError(f"`prereg check` did not pass for {path}:\n{done.stdout}")
    commit, digest, date = (m.group(1) for m in found)
    return PlanRecord(plan=str(path), frozen_at_commit=commit, plan_sha256=digest, frozen=date)


def record_plan(path: pathlib.Path = PLAN, target: pathlib.Path | None = None,
                run=subprocess.run) -> pathlib.Path:
    target = target or PLAN_RECORD
    if target.exists():
        raise StageRecordError(f"{target} exists; the freeze is recorded once")
    plan = read_plan(path, run)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(plan.model_dump_json(indent=1) + "\n")
    return target


def verify_plan(path: pathlib.Path = PLAN, target: pathlib.Path | None = None,
                run=subprocess.run) -> list[str]:
    """What differs between the freeze record and the plan's header now; empty when none."""
    target = target or PLAN_RECORD
    recorded = PlanRecord.model_validate_json(target.read_text())
    now = read_plan(path, run)
    return [f"{field}: recorded {getattr(recorded, field)}, plan header {getattr(now, field)}"
            for field in ("frozen_at_commit", "plan_sha256", "frozen")
            if getattr(recorded, field) != getattr(now, field)]


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    rec = sub.add_parser("record")
    rec.add_argument("--run-id", required=True)
    rec.add_argument("--note", required=True)
    rec.add_argument("--file", type=pathlib.Path, action="append", default=[])
    rec.add_argument("--volume-hashes", type=pathlib.Path)
    rec.add_argument("--volume-map", action="append", default=[])
    rec.add_argument("paths", type=pathlib.Path, nargs="*")
    ver = sub.add_parser("verify")
    ver.add_argument("--run-id")
    rep = sub.add_parser("replace")
    rep.add_argument("--path", type=pathlib.Path, required=True)
    rep.add_argument("--new", type=pathlib.Path, required=True)
    rep.add_argument("--archive", type=pathlib.Path, required=True)
    rep.add_argument("--reason", required=True)
    a = ap.parse_args()
    if a.command == "replace":
        rows = replace(a.path, a.new.read_bytes(), a.archive, a.reason)
        print(json.dumps([r.model_dump() for r in rows], indent=1))
        return
    if a.command == "plan":
        target = record_plan()
        print(target.read_text(), end="")
        print(f"seal it: results seal --role prereg {target}")
        return
    if a.command == "verify":
        if PLAN_RECORD.exists() and not a.run_id:
            differs = verify_plan()
            print(f"plan: {'ok' if not differs else 'the freeze header differs from its record'}")
            for line in differs:
                print("  " + line)
            if differs:
                raise StageRecordError("the freeze header differs from its record")
        wrong = verify(run_id=a.run_id)
        replaced = collections.Counter(r.run_id for r in load_replacements())
        for run_id, bad in wrong.items():
            note = f" ({replaced[run_id]} documented replacement(s))" if replaced[run_id] else ""
            print(f"{run_id}: "
                  f"{'ok' if not bad else f'{len(bad)} file(s) changed or missing'}{note}")
            for line in bad:
                print("  " + line)
        if any(wrong.values()):
            raise StageRecordError("a recorded output changed or is missing")
        return
    if a.volume_map and not a.volume_hashes:
        raise StageRecordError("--volume-map needs --volume-hashes")
    volume = json.loads(a.volume_hashes.read_text()) if a.volume_hashes else {}
    maps = [tuple(m.split("=", 1)) for m in a.volume_map]
    direct = [*a.file, *([a.volume_hashes] if a.volume_hashes else [])]
    target = record(a.run_id, a.note, a.paths, direct, volume, maps)
    manifest = Manifest.model_validate_json(target.read_text())
    print(json.dumps({"manifest": str(target), "n_files": len(manifest.files),
                      "volume_checks": [c.model_dump() for c in manifest.volume_checks]},
                     indent=1))


if __name__ == "__main__":
    main()
