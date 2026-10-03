# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1"]
# ///
"""Download the registered name sources that verify_claims.py matches against.

    HGNC complete set     monthly archive, dated file name
    UniProtKB/Swiss-Prot  human reviewed entries, the registered six-column query (RELEASES.md);
                          release read from the X-UniProt-Release header
    Mondo                 GitHub release tag, mondo.obo
    EFO                   GitHub release tag v3.93.0 (the Open Targets 26.09 build), efo.obo

The registered files are the ones in RELEASES.md, kept on the Modal volume
`proteome-mr-claim-audit-inputs` under /02_claims_meta/inputs/ and fetched from there
(inputs/README_MOVED_TO_MODAL.md). This script writes to the same paths under inputs/, so a
fresh download is checked against reference/MANIFEST.json: a file already present is re-hashed,
not re-downloaded, and a hash that differs from the manifest raises. A UniProt stream downloaded
again can differ in bytes from the registered file; the registered file is the one on the volume.

No email or other identifier is sent.

Usage: uv run scripts/fetch_reference_files.py
"""

import datetime
import hashlib
import json
import pathlib

import httpx

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
RAW = EXP
MANIFEST = EXP / "reference" / "MANIFEST.json"

HGNC_DATE = "2026-09-04"
UNIPROT_EXPECTED_RELEASE = "2026_03"
MONDO_TAG = "v2026-09-01"
EFO_TAG = "v3.93.0"

SOURCES = {
    "hgnc": {
        "file": f"inputs/hgnc/hgnc_complete_set_{HGNC_DATE}.tsv",
        "url": "https://storage.googleapis.com/public-download-files/hgnc/archive/archive/"
               f"monthly/tsv/hgnc_complete_set_{HGNC_DATE}.tsv",
        "release": HGNC_DATE,
    },
    "uniprot": {
        "file": "inputs/uniprot/uniprot_human_reviewed.tsv",
        "url": "https://rest.uniprot.org/uniprotkb/stream?query=%28organism_id%3A9606%29%20AND"
               "%20%28reviewed%3Atrue%29&format=tsv&fields=accession%2Cid%2Cgene_primary"
               "%2Cgene_synonym%2Cxref_hgnc%2Cprotein_name",
        "release": UNIPROT_EXPECTED_RELEASE,
    },
    "mondo": {
        "file": f"inputs/mondo_{MONDO_TAG}/mondo.obo",
        "url": f"https://github.com/monarch-initiative/mondo/releases/download/{MONDO_TAG}/"
               "mondo.obo",
        "release": MONDO_TAG,
    },
    "efo": {
        "file": f"inputs/efo_{EFO_TAG}/efo.obo",
        "url": f"https://github.com/EBISPOT/efo/releases/download/{EFO_TAG}/efo.obo",
        "release": EFO_TAG,
    },
}


class ReferenceFetchError(Exception):
    """A download failed, a release differs from the pinned one, or a hash changed."""


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(client: httpx.Client, name: str, spec: dict) -> dict:
    target = RAW / spec["file"]
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + ".part")
    with client.stream("GET", spec["url"]) as r:
        r.raise_for_status()
        header_release = r.headers.get("x-uniprot-release")
        if name == "uniprot" and header_release != spec["release"]:
            raise ReferenceFetchError(
                f"UniProt serves release {header_release}, pinned {spec['release']}")
        with part.open("wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    part.rename(target)
    return {"release_header": header_release,
            "last_modified": r.headers.get("last-modified")}


def main() -> None:
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    with httpx.Client(timeout=600, follow_redirects=True) as client:
        for name, spec in SOURCES.items():
            target = RAW / spec["file"]
            if target.exists() and name in manifest:
                digest = sha256(target)
                if digest != manifest[name]["sha256"]:
                    raise ReferenceFetchError(f"{target.name}: sha256 differs from manifest")
                print(f"  {name:<8} present   {digest[:12]}")
                continue
            extra = download(client, name, spec)
            manifest[name] = {
                "file": spec["file"], "url": spec["url"],
                "release": spec["release"], **extra,
                "downloaded_utc": datetime.datetime.now(datetime.UTC).isoformat(
                    timespec="seconds"),
                "bytes": target.stat().st_size, "sha256": sha256(target),
            }
            MANIFEST.write_text(json.dumps(manifest, indent=1))
            print(f"  {name:<8} fetched   {manifest[name]['sha256'][:12]}  "
                  f"{manifest[name]['bytes']:,} bytes")


if __name__ == "__main__":
    main()
