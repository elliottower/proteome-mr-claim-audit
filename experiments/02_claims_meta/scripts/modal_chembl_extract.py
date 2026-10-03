"""Modal wrapper: download, verify, extract and export ChEMBL 37 to the shared volume path /chembl_37/.

Logic is in scripts/chembl_extract.py. Run detached from experiments/02_claims_meta:
    modal run --detach scripts/modal_chembl_extract.py
The job resumes from whatever is already on the volume, so relaunching it is safe.
Standard library only in the container; client modal 1.4.3; image python 3.12 debian_slim.
"""

from pathlib import Path

import modal

from chembl_extract import run

VOLUME = "proteome-mr-claim-audit-inputs"
MOUNT = Path("/vol")

image = modal.Image.debian_slim(python_version="3.12").add_local_python_source("chembl_extract")
vol = modal.Volume.from_name(VOLUME)
app = modal.App("proteome-mr-chembl37-extract", image=image)


@app.function(volumes={str(MOUNT): vol}, timeout=24 * 3600, retries=modal.Retries(max_retries=3),
              cpu=2.0, memory=4096)
def chembl_job() -> dict:
    return run(MOUNT / "chembl_37", vol.commit)


@app.local_entrypoint()
def main() -> None:
    record = chembl_job.remote()
    print(record["tarball"]["match"], record["database"]["sha256"])
