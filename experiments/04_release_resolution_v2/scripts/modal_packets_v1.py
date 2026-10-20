"""Modal wrapper of the stage A packets of the second release-resolution registration
(scripts/packets_v1.py holds the logic), on the image of scripts/modal_retrieve_v2.py. No model is
called and no coding request is sent. Packets hold third-party text and stay on the volume; the
output written locally holds names, record ids, row counts, file sha256 and packet sha256.

    PYTHONPATH=../03_release_resolution/scripts modal run scripts/modal_packets_v1.py::tests
    ... modal run scripts/modal_packets_v1.py::build --controls <json> --out <json>

Volume, /04_release_resolution_v2/: inputs/abstracts.json (the abstracts and titles of the
records outside the scope with a drawn control, from Paper 1's screening records);
packets/stage_a/<name>.json and packets/stage_a/manifest.json, written once.
"""

import collections
import hashlib
import json

import modal

from modal_coding_v2 import CHECKS, CODING, E2, E3, MOUNT, REG, vol
from modal_retrieve_v2 import E4, LOCAL, PAPER1, REMOTE, ROOT4, image

app = modal.App("release-resolution-v2-packets", image=image)
FROZEN_STAGE_A_MANIFEST = "fef6b59516082495b62c2233659661f325fb602d29020a66168db29bb93aa7ed"
FIRST_CONTROLS = "outputs/c1a_controls_2026-10-13.json"
SCREENING = [f"outputs/screening/{d}/screening_records.jsonl"
             for d in ("2026-10-03", "chase_round_1", "chase_round_2", "chase_round_3")]
TESTS = ["test_packets_v1.py", "test_coding_gate_v2.py"]
FIRST_TESTS = ["test_coding_gate.py", "test_coding_packets_v2.py", "test_c1_controls.py",
               "test_coding_queue.py", "test_coding_queue_v2.py"]

with image.imports():
    import pathlib
    import subprocess

    import coding_packets as cp
    import coding_queue as q
    import packets_v1 as pk
    from build_registry import RegistryClaim


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@app.function(timeout=1800, cpu=2.0, memory=8192)
def tests_job() -> dict:
    out, code = "", 0
    for cwd, files in ((f"{E4}/tests", TESTS), (f"{E3}/tests", FIRST_TESTS)):
        run = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", *files],
                             capture_output=True, text=True, cwd=cwd)
        out += run.stdout + run.stderr
        code = code or run.returncode
    return {"returncode": code, "output": out}


def claim_inputs():
    coded = [RegistryClaim.model_validate_json(line) for line in
             open(f"{E2}/{REG}/registry_claims.jsonl").read().splitlines() if line.strip()]
    plain = {}
    for line in open(f"{E2}/{REG}/registry_claims_without_manual_coding.jsonl").read().splitlines():
        if line.strip():
            r = json.loads(line)
            plain[r["claim_record_id"]] = r
    written = {}
    for c in CHECKS:
        for line in open(f"{E2}/{c}").read().splitlines():
            if line.strip():
                r = json.loads(line)
                if "claim_record_id" in r:
                    written.setdefault(r["claim_record_id"], r["outcome_as_written"])
    return coded, plain, written


@app.function(volumes={str(MOUNT): vol}, timeout=6 * 3600, memory=32768)
def build_job(drawn: list[dict], first_control_ids: list[str], held: dict) -> dict:
    vol.reload()
    folder = ROOT4 / "packets" / "stage_a"
    if (folder / "manifest.json").exists():
        raise FileExistsError(f"{folder} holds packets already")
    frozen_folder = CODING / "packets" / "stage_a"
    listing_bytes = (frozen_folder / "manifest.json").read_bytes()
    if sha256(listing_bytes) != FROZEN_STAGE_A_MANIFEST:
        raise ValueError("the frozen stage A manifest differs from its logged sha256")
    first_ids = set(first_control_ids)
    folder.mkdir(parents=True, exist_ok=True)
    (ROOT4 / "inputs").mkdir(parents=True, exist_ok=True)
    (ROOT4 / "inputs" / "abstracts.json").write_text(json.dumps(held, ensure_ascii=False))
    manifest, removed_total, study_rows = [], 0, 0
    for m in json.loads(listing_bytes):
        data = (frozen_folder / f"{m['name']}.json").read_bytes()
        p, removed = pk.scope_packet(json.loads(data), first_ids)
        removed_total += removed
        study_rows += len(p["rows"])
        body = json.dumps(p, ensure_ascii=False).encode()
        (folder / f"{m['name']}.json").write_bytes(body)
        manifest.append({"name": m["name"], "record_id": m["record_id"], "population": "scope",
                         "rows": len(p["rows"]), "control_rows": 0,
                         "frozen_packet_sha256": sha256(data), "packet_sha256": sha256(body),
                         "files": [{"file_id": f["file_id"], "kind": f["kind"],
                                    "characters": len(f["text"]), "sha256": cp.sha256(f["text"])}
                                   for f in p["files"]]})
    if removed_total != len(first_ids):
        raise pk.PacketsError(f"{removed_total} control rows removed, not {len(first_ids)}")
    coded, plain, written = claim_inputs()
    side_rows = q.side_rows(pathlib.Path(f"{E2}/dataset_dictionary.csv"))
    acc = cp.read_accessions(f"{E3}/reference/c1_scanner_patterns_v2.json",
                             f"{E3}/reference/accession_releases.csv")
    by_record = collections.defaultdict(list)
    for c in drawn:
        by_record[c["record_id"]].append(c)
    outside_rows = {"study": 0, "control": 0}
    for rec, controls in sorted(by_record.items()):
        mine = [c for c in coded if c.claim_record_id.rsplit(":", 1)[0] == rec]
        study = pk.queue_rows(mine, plain, written)
        ctrl = pk.control_rows(controls, study, side_rows)
        sources = json.loads((REMOTE / rec / "result.json").read_text())["sources"]
        packets = pk.outside_packets(rec, held[rec]["title"], held[rec]["abstract"], sources,
                                     study, ctrl, acc)
        outside_rows["study"] += len(study)
        outside_rows["control"] += len(ctrl)
        for k, p in enumerate(packets, 1):
            name = f"{rec}.{k}"
            body = json.dumps(p, ensure_ascii=False).encode()
            (folder / f"{name}.json").write_bytes(body)
            manifest.append({"name": name, "record_id": rec, "population": "outside_scope",
                             "rows": len(p["rows"]), "control_rows": len(ctrl),
                             "control_row_ids": sorted(r["row_id"] for r in ctrl),
                             "packet_sha256": sha256(body),
                             "files": [{"file_id": f["file_id"], "kind": f["kind"],
                                        "characters": len(f["text"]),
                                        "sha256": cp.sha256(f["text"])} for f in p["files"]]})
    listing = json.dumps(manifest, indent=1).encode()
    (folder / "manifest.json").write_bytes(listing)
    vol.commit()
    scope = [m for m in manifest if m["population"] == "scope"]
    outside = [m for m in manifest if m["population"] == "outside_scope"]
    return {"rule": "PREREG.md, §Study design, item 1, Packets",
            "manifest_sha256": sha256(listing), "packets": len(manifest),
            "scope": {"packets": len(scope), "records": len({m["record_id"] for m in scope}),
                      "study_rows": study_rows, "control_rows_removed": removed_total},
            "outside_scope": {"packets": len(outside),
                              "records": len({m["record_id"] for m in outside}),
                              "study_rows": outside_rows["study"],
                              "control_rows": outside_rows["control"],
                              "records_with_a_full_text": sum(
                                  any(f["kind"] == "full_text" for f in m["files"])
                                  for m in outside)},
            "inputs_sha256": {"volume:03_release_resolution/coding/packets/stage_a/manifest.json":
                              FROZEN_STAGE_A_MANIFEST,
                              "volume:04_release_resolution_v2/c1a/control_set.json":
                              sha256((ROOT4 / "c1a" / "control_set.json").read_bytes()),
                              "volume:04_release_resolution_v2/inputs/abstracts.json":
                              sha256((ROOT4 / "inputs" / "abstracts.json").read_bytes())},
            "manifest": manifest}


@app.local_entrypoint()
def tests() -> None:
    result = tests_job.remote()
    print(result["output"][-3000:])
    if result["returncode"]:
        raise SystemExit("tests failed")


@app.local_entrypoint()
def build(controls: str, out: str) -> None:
    target = LOCAL / out
    if target.exists():
        raise FileExistsError(f"{target} exists; it is written once")
    drawn = json.loads((LOCAL / controls).read_text())["control_rows"]
    first = json.loads((LOCAL.parent / "03_release_resolution" / FIRST_CONTROLS).read_text())
    wanted = {c["record_id"] for c in drawn}
    held = {}
    for path in SCREENING:
        for line in (PAPER1 / path).read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if r["record_id"] in wanted and r["record_id"] not in held:
                    held[r["record_id"]] = {"title": r.get("title") or "",
                                            "abstract": r.get("abstract") or ""}
    missing = sorted(wanted - set(held))
    if missing:
        raise SystemExit(f"no screening record for {missing[:5]}")
    result = build_job.remote(drawn, [r["row_id"] for r in first["control_rows"]], held)
    result["inputs_sha256"] |= {
        controls: hashlib.sha256((LOCAL / controls).read_bytes()).hexdigest(),
        f"../03_release_resolution/{FIRST_CONTROLS}": hashlib.sha256(
            (LOCAL.parent / "03_release_resolution" / FIRST_CONTROLS).read_bytes()).hexdigest(),
        **{f"../02_claims_meta/{p}": hashlib.sha256((PAPER1 / p).read_bytes()).hexdigest()
           for p in SCREENING}}
    target.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "manifest"}, indent=1))
