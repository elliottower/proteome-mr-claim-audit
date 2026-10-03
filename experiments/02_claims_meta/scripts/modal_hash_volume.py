"""Modal wrapper: hash files on the volume.

Run from experiments/02_claims_meta:
    modal run scripts/modal_hash_volume.py::main
        every uploaded input against the local manifest; writes modal_inputs_verification.json
        beside the manifest
    modal run scripts/modal_hash_volume.py::tree --prefix /02_claims_meta/stage5/<run> --out <file.json>
        bytes and sha256 of every file under one volume folder, for scripts/stage_record.py
Client: modal 1.4.3.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import modal

from volume_hash import compare, hash_tree

ROOT = Path(__file__).resolve().parents[1]
VOLUME = "proteome-mr-claim-audit-inputs"
MOUNT = Path("/vol")

image = modal.Image.debian_slim(python_version="3.12").add_local_python_source("volume_hash")
vol = modal.Volume.from_name(VOLUME)
app = modal.App("proteome-mr-hash-volume", image=image)


@app.function(volumes={str(MOUNT): vol}, timeout=3600)
def hash_remote(prefix: str) -> dict[str, dict]:
    return hash_tree(MOUNT, prefix)


@app.local_entrypoint()
def main() -> None:
    manifest = json.loads((ROOT / "modal_inputs_manifest.json").read_text())
    remote = {}
    for sub in ("inputs", "reference/raw"):
        remote.update(hash_remote.remote(f"{manifest['remote_prefix']}/{sub}"))
    result = compare(manifest, remote)
    result["volume"] = VOLUME
    result["verified_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result["manifest_hashed_at"] = manifest["hashed_at"]
    out = ROOT / "modal_inputs_verification.json"
    out.write_text(json.dumps(result, indent=1) + "\n")
    print(f"{result['n_match']}/{result['n_manifest']} match; "
          f"{result['n_mismatch_or_missing']} mismatched or missing; "
          f"{len(result['remote_not_in_manifest'])} remote files not in manifest")


@app.local_entrypoint()
def tree(prefix: str, out: str) -> None:
    target = Path(out)
    if target.exists():
        raise FileExistsError(f"{target} exists; a listing is written once")
    listing = hash_remote.remote(prefix)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(listing, indent=1, sort_keys=True) + "\n")
    print(f"{len(listing)} files under {prefix} -> {target}")
