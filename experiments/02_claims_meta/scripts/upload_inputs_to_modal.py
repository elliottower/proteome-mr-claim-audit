"""Hash the pinned inputs, write a manifest, and upload them to a Modal volume.

Every file under inputs/ (except inputs/chembl_37/) and reference/raw/ is hashed first and the
manifest is written before any upload. Each top-level folder is then uploaded with
`modal volume put`, and the manifest is rewritten with `uploaded_at` for the files of that
folder, so an interrupted run leaves a manifest that says what reached the volume.

Remote layout: /02_claims_meta/<path relative to experiments/02_claims_meta>.
"""

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VOLUME = "proteome-mr-claim-audit-inputs"
REMOTE_PREFIX = "/02_claims_meta"
MANIFEST = ROOT / "modal_inputs_manifest.json"
EXCLUDE = {"inputs/chembl_37"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def upload_units() -> list[Path]:
    units = [p for p in sorted((ROOT / "inputs").iterdir()) if p.is_dir()]
    units = [p for p in units if str(p.relative_to(ROOT)) not in EXCLUDE]
    stray = [p for p in (ROOT / "inputs").iterdir() if p.is_file()]
    if stray:
        raise RuntimeError(f"files directly under inputs/ are not handled: {stray}")
    if (ROOT / "reference" / "raw").is_dir():
        units.append(ROOT / "reference" / "raw")
    return units


def write(manifest: dict) -> None:
    MANIFEST.write_text(json.dumps(manifest, indent=1) + "\n")


def main() -> None:
    units = upload_units()
    files = []
    for unit in units:
        for p in sorted(unit.rglob("*")):
            if p.is_file() and not p.is_symlink():
                rel = str(p.relative_to(ROOT))
                files.append({
                    "path": rel,
                    "remote_path": f"{REMOTE_PREFIX}/{rel}",
                    "bytes": p.stat().st_size,
                    "sha256": sha256(p),
                    "uploaded_at": None,
                })
    manifest = {
        "volume": VOLUME,
        "remote_prefix": REMOTE_PREFIX,
        "local_root": "experiments/02_claims_meta",
        "hashed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_files": len(files),
        "total_bytes": sum(f["bytes"] for f in files),
        "files": files,
    }
    write(manifest)
    print(f"manifest: {len(files)} files, {manifest['total_bytes']} bytes")

    for unit in units:
        rel = str(unit.relative_to(ROOT))
        remote = f"{REMOTE_PREFIX}/{rel}"
        subprocess.run(["modal", "volume", "put", VOLUME, str(unit), remote], check=True)
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for f in files:
            if f["path"].startswith(rel + "/"):
                f["uploaded_at"] = stamp
        write(manifest)
        print(f"{stamp} uploaded {rel}")


if __name__ == "__main__":
    main()
