"""Modal wrapper that runs the tests of scripts/audit_pricing.py on the image of
scripts/modal_coding_v2.py (sealed, unchanged). The pricing itself is arithmetic over two
committed outputs and runs in seconds.

    modal run scripts/modal_audit_pricing.py::tests
"""

import modal

from modal_coding_v2 import E3, image

app = modal.App("release-resolution-audit-pricing", image=image)

with image.imports():
    import subprocess


@app.function(timeout=900)
def tests_job() -> dict:
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                          "test_audit_pricing.py", "test_stage_pricing.py"],
                         capture_output=True, text=True, cwd=f"{E3}/tests")
    return {"returncode": run.returncode, "output": run.stdout + run.stderr}


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-2500:])
    if result["returncode"]:
        raise SystemExit("tests failed")
