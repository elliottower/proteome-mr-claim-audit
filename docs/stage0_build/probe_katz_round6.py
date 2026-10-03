"""Round-6 probe 3: the Katz 2022 (Sci Adv) Table S2 already on the volume. No network."""
import collections
import hashlib
import io
import json
import pathlib

import modal

MOUNT = pathlib.Path("/vol")
PROBE = MOUNT / "02_claims_meta" / "prefreeze_checks" / "round6_background_probe"
image = modal.Image.debian_slim(python_version="3.12").pip_install("openpyxl==3.1.5")
vol = modal.Volume.from_name("proteome-mr-claim-audit-inputs")
app = modal.App("proteome-mr-probe-katz", image=image)


@app.function(volumes={str(MOUNT): vol}, timeout=900)
def probe() -> dict:
    import openpyxl
    body = (PROBE / "katz2022_sciadv__sciadv.abm5164_tables_s1_to_s6.xlsx").read_bytes()
    wb = openpyxl.load_workbook(io.BytesIO(body), read_only=True, data_only=True)
    rows = [["" if c is None else str(c).strip() for c in r]
            for r in wb["Table S2"].iter_rows(values_only=True)]
    header = rows[1]
    data = [dict(zip(header, r)) for r in rows[2:] if any(r)]
    soma = [r for r in data if r["SomamerId"]]
    toc = [[("" if c is None else str(c)) for c in r] for r in wb["TOC"].iter_rows(
        values_only=True)]
    return {"sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body), "toc": toc,
            "header": header, "first_row": rows[0][:14], "data_rows": len(data),
            "rows_with_somamer": len(soma), "distinct_somamer": len({r["SomamerId"] for r in soma}),
            "rows_with_olink": sum(bool(r["OlinkID"]) for r in data),
            "rows_with_both": sum(bool(r["OlinkID"]) and bool(r["SomamerId"]) for r in data),
            "somamer_rows_by_count": dict(collections.Counter(collections.Counter(
                r["SomamerId"] for r in soma).values())),
            "somamer_without_uniprot": sum(not r["UniProt.x"] for r in {
                r["SomamerId"]: r for r in soma}.values()),
            "distinct_uniprot_cells": len({r["UniProt.x"] for r in soma if r["UniProt.x"]}),
            "multi_uniprot_cells": sorted({r["UniProt.x"] for r in soma
                                           if any(s in r["UniProt.x"] for s in " ,;|")})[:25],
            "sample": soma[:3]}


@app.local_entrypoint()
def main() -> None:
    out = pathlib.Path(__file__).resolve().parent / "probe_katz_round6.json"
    out.write_text(json.dumps(probe.remote(), indent=1))
    print(out)
