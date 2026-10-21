"""Third version of the secondary wrapper: scripts/modal_secondary_v2.py (sealed) called the first
version's entrypoint through an attribute this Modal client lacks (LocalEntrypoint.get_raw_f; the
client gives info.raw_f), so it stopped before any job ran. Otherwise as the second version:
scripts/modal_secondary_v1.py (sealed, unchanged and imported). Its first
run stopped before writing anything, because the image held no copy of Paper 1's families.json
(amended primary assembly), which SA6 reads for the families' first-public years. This version
adds that one file to the image and runs the first version's job and entrypoint logic unchanged.

    PYTHONPATH=../03_release_resolution/scripts modal run --detach scripts/modal_secondary_v3.py::run \\
        --sensitivity <json> --secondary <json>
"""

import modal

import modal_secondary_v1 as v1
from modal_coding_v2 import E2, MOUNT, REG, vol
from modal_retrieve_v2 import PAPER1

image = v1.image.add_local_file(PAPER1 / REG / "families.json", f"{E2}/{REG}/families.json",
                                copy=True)
app = modal.App("release-resolution-v2-secondary-3", image=image)
run_job = app.function(volumes={str(MOUNT): vol}, timeout=24 * 3600, memory=65536, cpu=4.0,
                       serialized=True)(v1.run_job.get_raw_f())


@app.local_entrypoint()
def run(sensitivity: str, secondary: str) -> None:
    v1.run_job = run_job
    v1.run.info.raw_f(sensitivity, secondary)
