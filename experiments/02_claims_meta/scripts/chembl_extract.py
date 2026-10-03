"""Download, verify, extract and export ChEMBL 37 (logic for scripts/modal_chembl_extract.py).

Every step is resumable and skips work already on disk:
  1. small release files (checksums.txt, chembl_uniprot_mapping.txt, schema_documentation.txt);
  2. the SQLite tarball, by HTTP Range requests appended to a .part file, checkpointed every
     CHECKPOINT_BYTES;
  3. sha256 of the tarball against the publisher's checksums.txt (a mismatch stops the run);
  4. the .db member streamed out of the tarball to a .part file; a restart re-decompresses and
     skips the bytes already written, checkpointed every CHECKPOINT_BYTES;
  5. one CSV per table, written to .part and renamed, with SHA256SUMS rewritten after each.
`checkpoint` is called after every unit of progress (on Modal it commits the volume).
"""

import csv
import hashlib
import http.client
import json
import re
import sqlite3
import tarfile
import time
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37"
TARBALL = "chembl_37_sqlite.tar.gz"
SMALL_FILES = ("checksums.txt", "chembl_uniprot_mapping.txt", "schema_documentation.txt")
DB_NAME = "chembl_37.db"
CHECKPOINT_BYTES = 256 << 20
CHUNK = 8 << 20

# table -> columns to export (None = every column except those in DROP_COLUMNS)
TABLES: dict[str, list[str] | None] = {
    "drug_indication": None,
    "drug_mechanism": None,
    "action_type": None,
    "molecule_dictionary": ["molregno", "chembl_id", "pref_name", "max_phase", "molecule_type"],
    "molecule_hierarchy": ["molregno", "parent_molregno", "active_molregno"],
    "target_dictionary": None,
    "target_components": None,
    "component_sequences": None,
    "compound_records": None,
    "docs": None,
}
DROP_COLUMNS = {"component_sequences": {"sequence"}}


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {msg}", flush=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def remote_size(url: str) -> int:
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=120) as r:
        return int(r.headers["Content-Length"])


def download_resumable(url: str, dest: Path, checkpoint: Callable[[], None]) -> None:
    if dest.exists():
        log(f"{dest.name} present, skipping download")
        return
    total = remote_size(url)
    part = dest.with_name(dest.name + ".part")
    failures = 0
    last = time.time()
    while True:
        have = part.stat().st_size if part.exists() else 0
        if have == total:
            break
        if have > total:
            raise RuntimeError(f"{part} is larger than the remote file ({have} > {total})")
        req = urllib.request.Request(url, headers={"Range": f"bytes={have}-"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r, part.open("ab") as f:
                if have and r.status != 206:
                    raise RuntimeError(f"server ignored Range request (status {r.status})")
                written = 0
                while written < CHECKPOINT_BYTES:
                    buf = r.read(CHUNK)
                    if not buf:
                        break
                    f.write(buf)
                    written += len(buf)
            failures = 0
        except (OSError, http.client.HTTPException) as e:  # network errors: back off and resume from .part
            failures += 1
            if failures > 20:
                raise RuntimeError(f"download of {url} failed 20 times in a row") from e
            log(f"network error ({e!r}); retry {failures} in {min(300, 10 * failures)} s")
            time.sleep(min(300, 10 * failures))
        checkpoint()
        now = part.stat().st_size if part.exists() else 0
        rate = (now - have) / max(time.time() - last, 1e-6) / 1e6
        last = time.time()
        log(f"{dest.name}: {now / 1e9:.2f} / {total / 1e9:.2f} GB ({rate:.1f} MB/s)")
    part.rename(dest)
    checkpoint()
    log(f"{dest.name} complete ({total} bytes)")


def publisher_sha256(checksums: Path, name: str) -> str:
    for line in checksums.read_text().splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == name and re.fullmatch(r"[0-9a-f]{64}", parts[0]):
            return parts[0]
    raise RuntimeError(f"{name} not listed in {checksums}")


def read_verified(out: Path) -> dict:
    path = out / "VERIFIED.json"
    return json.loads(path.read_text()) if path.exists() else {}


def write_verified(out: Path, record: dict) -> None:
    (out / "VERIFIED.json").write_text(json.dumps(record, indent=1) + "\n")


def verify_tarball(out: Path, checkpoint: Callable[[], None]) -> dict:
    record = read_verified(out)
    if record.get("tarball", {}).get("match"):
        log("tarball already verified")
        return record
    tar = out / TARBALL
    expected = publisher_sha256(out / "checksums.txt", TARBALL)
    log(f"hashing {TARBALL}")
    got = sha256(tar)
    record["tarball"] = {
        "file": TARBALL,
        "url": f"{BASE_URL}/{TARBALL}",
        "bytes": tar.stat().st_size,
        "publisher_sha256": expected,
        "computed_sha256": got,
        "match": got == expected,
        "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    record["small_files"] = {
        n: {"bytes": (out / n).stat().st_size, "sha256": sha256(out / n)} for n in SMALL_FILES
    }
    write_verified(out, record)
    checkpoint()
    if got != expected:
        raise RuntimeError(f"sha256 mismatch for {TARBALL}: {got} != publisher {expected}")
    log("tarball sha256 matches publisher")
    return record


def extract_db(out: Path, checkpoint: Callable[[], None]) -> None:
    db = out / DB_NAME
    if db.exists():
        log(f"{DB_NAME} present, skipping extraction")
        return
    part = out / (DB_NAME + ".part")
    have = part.stat().st_size if part.exists() else 0
    log(f"extracting {DB_NAME} (resuming at {have} bytes)")
    with tarfile.open(out / TARBALL, mode="r|gz") as tf:
        member = next((m for m in tf if m.name.endswith(".db")), None)
        if member is None:
            raise RuntimeError(f"no .db member in {TARBALL}")
        src = tf.extractfile(member)
        if src is None:
            raise RuntimeError(f"{member.name} is not a regular file")
        skipped = 0
        while skipped < have:
            buf = src.read(min(CHUNK, have - skipped))
            if not buf:
                raise RuntimeError(".part is longer than the archive member")
            skipped += len(buf)
        written_since = 0
        f = part.open("ab")
        try:
            for buf in iter(lambda: src.read(CHUNK), b""):
                f.write(buf)
                written_since += len(buf)
                if written_since >= 8 * CHECKPOINT_BYTES:
                    f.close()
                    checkpoint()
                    log(f"{DB_NAME}: {part.stat().st_size / 1e9:.2f} / {member.size / 1e9:.2f} GB")
                    written_since = 0
                    f = part.open("ab")
        finally:
            f.close()
        if part.stat().st_size != member.size:
            raise RuntimeError(f"extracted {part.stat().st_size} bytes, member is {member.size}")
    part.rename(db)
    checkpoint()
    log(f"{DB_NAME} extracted ({member.size} bytes, member {member.name})")


def record_db_hash(out: Path, checkpoint: Callable[[], None]) -> None:
    record = read_verified(out)
    if "database" in record:
        return
    log(f"hashing {DB_NAME}")
    db = out / DB_NAME
    record["database"] = {
        "file": DB_NAME,
        "extracted_from": TARBALL,
        "bytes": db.stat().st_size,
        "sha256": sha256(db),
        "hashed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    write_verified(out, record)
    checkpoint()


def export_tables(out: Path, checkpoint: Callable[[], None]) -> None:
    tables_dir = out / "tables"
    tables_dir.mkdir(exist_ok=True)
    con = sqlite3.connect(f"file:{out / DB_NAME}?mode=ro&immutable=1", uri=True)
    try:
        for table, cols in TABLES.items():
            dest = tables_dir / f"{table}.csv"
            if dest.exists():
                log(f"{dest.name} present, skipping")
                continue
            if cols is None:
                drop = DROP_COLUMNS.get(table, set())
                cols = [r[1] for r in con.execute(f"PRAGMA table_info({table})") if r[1] not in drop]
            if not cols:
                raise RuntimeError(f"table {table} not found in {DB_NAME}")
            part = tables_dir / f"{table}.csv.part"
            n = 0
            with part.open("w", newline="") as f:
                w = csv.writer(f)
                w.writerow(cols)
                cur = con.execute(f"SELECT {', '.join(cols)} FROM {table} ORDER BY rowid")
                for row in cur:
                    w.writerow(row)
                    n += 1
            part.rename(dest)
            write_sums(tables_dir)
            checkpoint()
            log(f"{dest.name}: {n} rows")
    finally:
        con.close()


def write_sums(tables_dir: Path) -> None:
    lines = [f"{sha256(p)}  {p.name}" for p in sorted(tables_dir.glob("*.csv"))]
    (tables_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n")


def run(out: Path, checkpoint: Callable[[], None]) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    for name in SMALL_FILES:
        download_resumable(f"{BASE_URL}/{name}", out / name, checkpoint)
    download_resumable(f"{BASE_URL}/{TARBALL}", out / TARBALL, checkpoint)
    verify_tarball(out, checkpoint)
    extract_db(out, checkpoint)
    record_db_hash(out, checkpoint)
    export_tables(out, checkpoint)
    record = read_verified(out)
    record["tables_sha256sums"] = (out / "tables" / "SHA256SUMS").read_text()
    write_verified(out, record)
    checkpoint()
    log("done")
    return record
