"""Round 6: move the supplementary files the probe fetched (same URLs as the committed source
tables) into the registered folder of the volume, each checked against the sha256 the tables
record. No network. A file already there is checked and left."""
import hashlib
import json
import pathlib

import modal

MOUNT = pathlib.Path("/vol")
REMOTE = MOUNT / "02_claims_meta"
PROBE = REMOTE / "prefreeze_checks" / "round6_background_probe"
PUBLISHED = REMOTE / "inputs" / "platform_assays_published"
FILES = {
    "koprulu2026_S5.xlsx": ("koprulu2026_epmc__NIHMS2173841-supplement-MMC5.xlsx",
                            "b8c18cb41d7680b19f0461bd621b94b3ce5dfe9ea3ed3e128d465c671f1c9eed"),
    "katz2022sciadv_tables_S1_S6.xlsx": (
        "katz2022_sciadv__sciadv.abm5164_tables_s1_to_s6.xlsx",
        "bd8ba000d37fb2d56bcb68a6eb19e68c71caeee726c40251e2d9976efdca34d6"),
    "gilly2020_SD7.xlsx": ("gilly2020_SD7",
                           "078dc5395da72d66546081625d1c804a7a576a8c65203f794ff2be9cce001670"),
    "png2021_SD8.xlsx": ("png2021_SD8",
                         "1b872d9843835fe5c30c69bf75b7948a274766964cc6ec29b4141462399c62ae"),
    "folkersen2017_S3.pdf": ("folkersen2017_improve_epmc__pgen.1006706.s005.pdf",
                             "9fe8bed8ca5acbba1ea828611fa0d3ee33eafe55d5aac586a8f7c2252c88451a"),
    "enroth2014_SD2.xlsx": ("enroth2014_epmc", None),
}
image = modal.Image.debian_slim(python_version="3.12")
vol = modal.Volume.from_name("proteome-mr-claim-audit-inputs")
app = modal.App("proteome-mr-copy-probe-files", image=image)


@app.function(volumes={str(MOUNT): vol}, timeout=900)
def copy() -> dict:
    out = {}
    for name, (probe_name, sha) in FILES.items():
        target = PUBLISHED / name
        if sha is None:
            out[name] = {"present": target.exists(), "sha256": hashlib.sha256(
                target.read_bytes()).hexdigest() if target.exists() else None}
            continue
        if not target.exists():
            body = (PROBE / probe_name).read_bytes()
            found = hashlib.sha256(body).hexdigest()
            if found != sha:
                raise ValueError(f"{name}: sha256 {found}, expected {sha}")
            target.write_bytes(body)
            vol.commit()
            copied = True
        else:
            copied = False
        out[name] = {"copied_now": copied, "bytes": target.stat().st_size,
                     "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "expected": sha}
    return out


@app.local_entrypoint()
def main() -> None:
    result = copy.remote()
    path = pathlib.Path(__file__).resolve().parent / "copy_probe_files_round6.json"
    path.write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))
