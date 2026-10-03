"""Round-6 probe of published supplementary files for the analysed-protein backgrounds.
Resource files of dataset source papers only; no proteome-wide MR paper, claim or pair.

    modal run docs/stage0_build/probe_backgrounds_round6.py

Writes each fetched body to /02_claims_meta/prefreeze_checks/round6_background_probe/ on the
volume and returns a description (zip members, sheet heads, PDF text heads). No email address
or other identifier is sent; the default httpx client is used.
"""

import datetime
import hashlib
import io
import json
import pathlib
import zipfile

import modal

VOLUME = "proteome-mr-claim-audit-inputs"
MOUNT = pathlib.Path("/vol")
REMOTE = MOUNT / "02_claims_meta"
PROBE = REMOTE / "prefreeze_checks" / "round6_background_probe"
PUBLISHED = REMOTE / "inputs" / "platform_assays_published"
OUT = pathlib.Path(__file__).resolve().parent / "probe_backgrounds_round6.json"

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/{}/supplementaryFiles"
SPRINGER = "https://static-content.springer.com/esm/art%3A10.1038%2F{}/MediaObjects/{}"
URLS = {
    "folkersen2017_improve_epmc": EPMC.format("PMC5393901"),
    "katz2022_circulation_epmc": EPMC.format("PMC9158509"),
    "katz2022_sciadv_epmc": EPMC.format("PMC9390994"),
    "koprulu2026_epmc": EPMC.format("PMC13343581"),
    "enroth2014_epmc": EPMC.format("PMC4143927"),
    "gilly2020_SD7": SPRINGER.format("s41467-020-20079-2", "41467_2020_20079_MOESM10_ESM.xlsx"),
    "png2021_SD8": SPRINGER.format("s41467-021-27387-1", "41467_2021_27387_MOESM11_ESM.xlsx"),
    "katz2022_circulation_oa": "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=PMC9158509",
}
VOLUME_FILES = {"folkersen2020_ST1.xlsx": ["2 Main_hit_list", "8 Scallop_cohorts",
                                           "9 GWAS_sumstats"],
                "enroth2014_SD1.xlsx": ["Sheet2", "Sheet3"],
                "yao2018_SD1.xlsx": None, "pietzner2020_SD1.xlsx": ["Legends"]}

image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "httpx==0.28.1", "openpyxl==3.1.5", "pypdf==5.9.0", "xlrd==2.0.2")
vol = modal.Volume.from_name(VOLUME)
app = modal.App("proteome-mr-probe-backgrounds", image=image)


def describe_xlsx(body: bytes, sheets: list[str] | None = None, rows: int = 6) -> dict:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(body), read_only=True, data_only=True)
    out = {"sheets": wb.sheetnames, "heads": {}}
    for name in sheets or wb.sheetnames[:12]:
        if name not in wb.sheetnames:
            continue
        data = list(wb[name].iter_rows(values_only=True))
        out["heads"][name] = {"rows": len(data),
                              "head": [[str(c)[:60] if c is not None else "" for c in r[:30]]
                                       for r in data[:rows]]}
    return out


def describe_xls(body: bytes, rows: int = 6) -> dict:
    import xlrd
    wb = xlrd.open_workbook(file_contents=body)
    return {"sheets": wb.sheet_names(),
            "heads": {s.name: {"rows": s.nrows,
                               "head": [[str(c)[:60] for c in s.row_values(i)[:30]]
                                        for i in range(min(rows, s.nrows))]}
                      for s in wb.sheets()[:12]}}


def describe_pdf(body: bytes, pages: int = 3, chars: int = 2500) -> dict:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(body))
    return {"pages": len(reader.pages),
            "text_head": [(reader.pages[i].extract_text() or "")[:chars]
                          for i in range(min(pages, len(reader.pages)))]}


def describe(name: str, body: bytes) -> dict:
    out: dict = {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
    lower = name.lower()
    try:
        if body[:2] == b"PK" and lower.endswith((".xlsx", ".xlsm")):
            out |= describe_xlsx(body)
        elif lower.endswith(".xls"):
            out |= describe_xls(body)
        elif lower.endswith(".pdf") or body[:4] == b"%PDF":
            out |= describe_pdf(body)
        elif lower.endswith((".csv", ".txt", ".tsv", ".xml")) or not lower.count("."):
            out["text_head"] = body[:3000].decode("utf-8", "replace")
    except Exception as e:  # a probe reports what it could not read
        out["error"] = f"{type(e).__name__}: {e}"
    return out


@app.function(volumes={str(MOUNT): vol}, timeout=3600, cpu=2.0, memory=8192)
def probe() -> dict:
    import httpx
    PROBE.mkdir(parents=True, exist_ok=True)
    result: dict = {"written_utc": datetime.datetime.now(datetime.UTC).isoformat(
        timespec="seconds"), "fetched": {}, "volume_files": {}}
    with httpx.Client(timeout=300, follow_redirects=True) as client:
        for key, url in URLS.items():
            entry: dict = {"url": url}
            try:
                r = client.get(url)
                entry["status"] = r.status_code
                entry["content_type"] = r.headers.get("content-type")
                body = r.content
                entry["bytes"] = len(body)
                entry["sha256"] = hashlib.sha256(body).hexdigest()
                if r.status_code == 200 and body:
                    (PROBE / key).write_bytes(body)
                    vol.commit()
                    if body[:2] == b"PK" and not url.endswith(".xlsx"):
                        with zipfile.ZipFile(io.BytesIO(body)) as z:
                            entry["members"] = {}
                            for info in z.infolist():
                                member = z.read(info.filename)
                                (PROBE / f"{key}__{info.filename.rsplit('/', 1)[-1]}"
                                 ).write_bytes(member)
                                entry["members"][info.filename] = describe(info.filename, member)
                            vol.commit()
                    else:
                        entry |= describe(url.rsplit("/", 1)[-1] if url.endswith(".xlsx")
                                          else key, body)
            except Exception as e:
                entry["error"] = f"{type(e).__name__}: {e}"
            result["fetched"][key] = entry
    for name, sheets in VOLUME_FILES.items():
        path = PUBLISHED / name
        result["volume_files"][name] = describe_xlsx(path.read_bytes(), sheets, rows=8)
    (PROBE / "probe.json").write_text(json.dumps(result, indent=1))
    vol.commit()
    return result


@app.local_entrypoint()
def main() -> None:
    result = probe.remote()
    target = OUT
    if target.exists():
        target = target.with_name(target.stem + "_" + datetime.datetime.now(
            datetime.UTC).strftime("%Y%m%dT%H%M%SZ") + ".json")
    target.write_text(json.dumps(result, indent=1))
    print(target)
