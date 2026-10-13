"""Modal wrapper that builds the author's adjudication and audit pages of a pass
(scripts/adjudication_pages.py) from the answers on the volume; it reuses the image and volume of
scripts/modal_coding_v2.py (sealed, unchanged), adding openpyxl for Paper 1's draw module. The
pages hold abstracts (third-party text) and are written only to the volume and the ignored
planning folder, with the blinding key beside them; the committed manifest holds row ids, seeds,
counts and the key's sha256.

    modal run scripts/modal_adjudication.py::tests
    modal run scripts/modal_adjudication.py::build --stage sa1 --seed-audit <n> --seed-blind <n> \\
        --pages <planning dir> --manifest <outputs json>
"""

import json
import pathlib

import modal

from modal_coding_v2 import CODING, E2, E3, LOCAL, MOUNT, image as base, vol

image = base.pip_install("openpyxl==3.1.5")
app = modal.App("release-resolution-adjudication", image=image)
MODELS = ("claude-sonnet-5-5", "gpt-6.1-sol")

with image.imports():
    import csv
    import subprocess

    import adjudication_pages as ap
    import coding_gate as gate
    import source_scanner_v2 as scanner


@app.function(timeout=900)
def tests_job() -> dict:
    run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                          "test_adjudication_pages.py", "test_pass_summary.py"],
                         capture_output=True, text=True, cwd=f"{E3}/tests")
    return {"returncode": run.returncode, "output": run.stdout + run.stderr}


@app.function(volumes={str(MOUNT): vol}, timeout=3600, memory=8192)
def build_job(stage: str, seed_audit: int, seed_blind: int) -> dict:
    vol.reload()
    patterns = json.loads(open(f"{E3}/reference/c1_scanner_patterns_v2.json").read())
    with open(f"{E3}/reference/accession_releases.csv", newline="") as fh:
        table = list(csv.DictReader(fh))
    dictionary = gate.dictionary_rows(f"{E2}/dataset_dictionary.csv")
    mapper = scanner.Mapper(patterns, table, list(dictionary.values()))
    queue = {r["row_id"]: r for r in json.loads((CODING / "inputs" / "queue.json").read_text())["queue"]}
    held = json.loads((CODING / "inputs" / "abstracts.json").read_text())
    folder = CODING / "packets" / stage
    packets = {m["name"]: json.loads((folder / f"{m['name']}.json").read_text())
               for m in json.loads((folder / "manifest.json").read_text())}
    order = [r["row_id"] for _, p in sorted(packets.items()) for r in p["rows"]]
    by_row_packet = {r["row_id"]: p for p in packets.values() for r in p["rows"]}
    answers, verdicts = {}, {}
    for model in MODELS:
        answers[model], verdicts[model] = {}, {}
        store = CODING / "answers" / stage / model
        for path in sorted(store.glob("*.json")):
            if ".attempt" in path.name:
                continue
            f = json.loads(path.read_text())
            if f["state"] != "accepted":
                continue
            p = packets[f["name"]]
            frozen = {x["file_id"]: {"key": x["file_id"], "sha256": "", "text": x["text"]}
                      for x in p["files"]}
            sides = {r["row_id"]: r["side"] for r in p["rows"]}
            for row in f["answer"]["rows"]:
                answers[model][row["row_id"]] = row
                verdicts[model][row["row_id"]] = gate.gate_row(row, sides[row["row_id"]], p,
                                                               frozen, patterns, mapper, dictionary)
    made = ap.build(stage, queue, {r: held[r]["abstract"] for r in held}, answers, verdicts,
                    order, MODELS, seed_audit, seed_blind)
    out = CODING / "adjudication" / stage
    out.mkdir(parents=True, exist_ok=True)
    for name, html_page in made["pages"].items():
        (out / f"{name}.html").write_text(html_page)
    (out / "blinding_key.json").write_text(json.dumps(made["key"], indent=1))
    (out / "manifest.json").write_text(json.dumps(made["manifest"], indent=1))
    vol.commit()
    return made


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-2500:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def build(stage: str, seed_audit: int, seed_blind: int, pages: str, manifest: str) -> None:
    target = LOCAL / manifest
    if target.exists():
        raise FileExistsError(f"{target} exists; it is written once")
    made = build_job.remote(stage, seed_audit, seed_blind)
    folder = (LOCAL / pages).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    for name, html_page in made["pages"].items():
        (folder / f"{stage}_{name}.html").write_text(html_page)
    (folder / f"{stage}_blinding_key.json").write_text(json.dumps(made["key"], indent=1))
    target.write_text(json.dumps(made["manifest"], indent=1) + "\n")
    print(json.dumps({k: v for k, v in made["manifest"].items()
                      if not k.endswith("row_ids")}, indent=1))
    print(folder)
