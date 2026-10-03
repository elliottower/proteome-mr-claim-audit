"""Round-6 probe 2: read the supplementary files already on the volume (no network).
Resource files of dataset source papers only.

    modal run docs/stage0_build/probe_backgrounds2_round6.py
"""

import collections
import csv
import io
import json
import pathlib
import re
import zipfile

import modal

VOLUME = "proteome-mr-claim-audit-inputs"
MOUNT = pathlib.Path("/vol")
REMOTE = MOUNT / "02_claims_meta"
PROBE = REMOTE / "prefreeze_checks" / "round6_background_probe"
PUBLISHED = REMOTE / "inputs" / "platform_assays_published"
ASSAYS = REMOTE / "inputs" / "platform_assays"
HERE = pathlib.Path(__file__).resolve()
OUT = HERE.parent / "probe_backgrounds2_round6.json"

image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "openpyxl==3.1.5", "pypdf==5.9.0", "xlrd==2.0.2")
vol = modal.Volume.from_name(VOLUME)
app = modal.App("proteome-mr-probe-backgrounds2", image=image)


def sheet_rows(body: bytes, sheet: str | None = None) -> list[list[str]]:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(body), read_only=True, data_only=True)
    ws = wb[sheet] if sheet else wb[wb.sheetnames[0]]
    return [["" if c is None else str(c).strip() for c in r] for r in ws.iter_rows(
        values_only=True)]


@app.function(volumes={str(MOUNT): vol}, timeout=1800, cpu=2.0, memory=8192)
def probe() -> dict:
    from pypdf import PdfReader
    out: dict = {}

    # Folkersen 2020 ST1: the CVD I rows and their per-cohort cells.
    rows = sheet_rows((PUBLISHED / "folkersen2020_ST1.xlsx").read_bytes(), "1 Protein_info")
    h = next(i for i, r in enumerate(rows) if "UniProt ID" in r)
    header = rows[h]
    data = [dict(zip(header, r)) for r in rows[h + 1:] if any(r)]
    cvd1 = [r for r in data if r["CVDI"] == "Y"]
    cohorts = header[header.index("IMPROVE"):header.index("Inter-plate_CV")]
    out["folkersen2020"] = {
        "preamble": [" | ".join(c for c in r if c)[:300] for r in rows[:h]],
        "header": header, "cvd1_rows": len(cvd1),
        "cvd1_rows_by_number_of_cohorts_with_a_value": dict(collections.Counter(
            sum(r[c] not in ("", "NA") for c in cohorts) for r in cvd1)),
        "cvd1_rows_with_no_cohort_value": [
            {k: r[k] for k in ("UniProt ID", "Gene", "Olink_assay", *cohorts)}
            for r in cvd1 if all(r[c] in ("", "NA") for c in cohorts)],
        "cvd1_improve_values": dict(collections.Counter(
            "NA" if r["IMPROVE"] in ("", "NA") else "value" for r in cvd1)),
        "cvd1_improve_na": [r["Gene"] for r in cvd1 if r["IMPROVE"] in ("", "NA")],
        "cvd1_other_panel_flags": dict(collections.Counter(
            f"CVDII={r['CVDII']},CVDIII={r['CVDIII']},INFI={r['INFI']}" for r in cvd1)),
        "main_hit_proteins": len({r[0] for r in sheet_rows(
            (PUBLISHED / "folkersen2020_ST1.xlsx").read_bytes(), "2 Main_hit_list")[2:]
            if r and r[0]}),
        "inter_plate_cv_blank": [r["Gene"] for r in cvd1 if r["Inter-plate_CV"] in ("", "NA")],
        "sample_rows": [{k: r[k] for k in header} for r in cvd1[:3]]}

    # IMPROVE S3 table (PDF).
    reader = PdfReader(io.BytesIO((PROBE / "folkersen2017_improve_epmc__pgen.1006706.s005.pdf"
                                   ).read_bytes()))
    text = "\n".join(p.extract_text() or "" for p in reader.pages)
    flat = " ".join(text.replace("‐", "-").split())
    found = re.findall(r"(?<![A-Za-z0-9-])([A-Z][A-Z0-9-]{1,9}) (?:(?!\b(?:yes|no)\b).){3,160}? "
                       r"(yes|no)(?= )", flat)
    out["improve_s3"] = {"pages": len(reader.pages), "chars": len(flat),
                         "yes_tokens": len(re.findall(r"\byes\b", flat)),
                         "no_tokens": len(re.findall(r"\bno\b", flat)),
                         "rows_found": len(found),
                         "included": dict(collections.Counter(v for _, v in found)),
                         "rows": found, "tail": flat[-600:], "head": flat[:400]}

    # Enroth 2014: the 77 analysed phenotypes against the 92 analytes.
    with zipfile.ZipFile(PROBE / "enroth2014_epmc") as z:
        s2 = sheet_rows(z.read(next(n for n in z.namelist() if n.endswith("s2.xlsx"))),
                        "Analytes")
        s3 = sheet_rows(z.read(next(n for n in z.namelist() if n.endswith("s3.xlsx"))),
                        "Supplementary Table 2")
        s3b = sheet_rows(z.read(next(n for n in z.namelist() if n.endswith("s3.xlsx"))),
                         "Sheet2")
    h2 = next(i for i, r in enumerate(s2) if "UniprotID" in r)
    head2 = s2[h2]
    analytes = [dict(zip(head2, r)) for r in s2[h2 + 1:] if any(r)]
    out["enroth2014_heads"] = {"analytes_header_row": h2, "analytes_header": head2,
                               "analytes_first": s2[h2 + 1][:10],
                               "table2_rows_6_to_9": [r[:6] for r in s3[4:9]]}
    hrow = next(i for i, r in enumerate(s3) if r and r[0] == "Phenotype")
    phen = [r[0] for r in s3[hrow + 1:] if r and r[0]]
    phen_b = [r[0] for r in s3b[1:] if r and r[0]]
    names = {a.get("Name", "") for a in analytes}
    short = {a.get("OlinkShortName", "") for a in analytes}
    out["enroth2014"] = {
        "analytes": len(analytes), "phenotypes_table": len(phen), "phenotypes_sheet2": len(phen_b),
        "same_set": set(phen) == set(phen_b),
        "phenotypes_in_Name": len(set(phen) & names),
        "phenotypes_in_OlinkShortName": len(set(phen) & short),
        "phenotypes_unmatched_Name": sorted(set(phen) - names),
        "phenotypes_unmatched_short": sorted(set(phen) - short),
        "analytes_not_analysed_by_Name": sorted(names - set(phen)),
        "preamble": [" | ".join(c for c in r if c)[:300] for r in s3[:hrow]]}

    # Katz 2022 Sci Adv: the nested tables zip.
    with zipfile.ZipFile(PROBE / "katz2022_sciadv_epmc") as z:
        inner_name = next(n for n in z.namelist() if n.endswith(".zip"))
        with zipfile.ZipFile(io.BytesIO(z.read(inner_name))) as inner:
            katz = {}
            for n in inner.namelist():
                body = inner.read(n)
                entry: dict = {"bytes": len(body)}
                if n.lower().endswith(".xlsx"):
                    import openpyxl
                    wb = openpyxl.load_workbook(io.BytesIO(body), read_only=True, data_only=True)
                    entry["sheets"] = {}
                    for s in wb.sheetnames:
                        rs = [["" if c is None else str(c)[:40] for c in r[:16]]
                              for r in wb[s].iter_rows(values_only=True)]
                        entry["sheets"][s] = {"rows": len(rs), "head": rs[:6]}
                    (PROBE / f"katz2022_sciadv__{n.rsplit('/', 1)[-1]}").write_bytes(body)
                katz[n] = entry
            vol.commit()
    out["katz2022_sciadv_tables"] = katz
    sm = PdfReader(io.BytesIO((PROBE / "katz2022_sciadv_epmc__sciadv.abm5164_sm.pdf"
                               ).read_bytes()))
    out["katz2022_sciadv_sm_text"] = [(p.extract_text() or "")[:1500] for p in sm.pages[:2]]

    # Koprulu 2026 S5 against the UKB-PPP 1.5k protein map.
    with zipfile.ZipFile(PROBE / "koprulu2026_epmc") as z:
        s5 = sheet_rows(z.read(next(n for n in z.namelist() if n.endswith("MMC5.xlsx"))))
        mmc13 = PdfReader(io.BytesIO(z.read(next(n for n in z.namelist()
                                                 if n.endswith("-13.pdf")))))
    phenos = [r[0] for r in s5[2:] if r and r[0]]
    with (ASSAYS / "olink_protein_map_1.5k_v1.tsv").open(newline="") as f:
        ukb = list(csv.DictReader(f, delimiter="\t"))
    with (ASSAYS / "pQTLdata_0.6_Olink_Target_96.tsv").open(newline="") as f:
        t96 = list(csv.DictReader(f, delimiter="\t"))
    second = [p.split("_")[-1] for p in phenos]
    first = [p.split("_")[0] for p in phenos]
    ukb_ids = {r.get("OlinkID", ""): r for r in ukb}
    out["koprulu2026"] = {
        "s5_title": s5[0][0][:300], "s5_rows": len(phenos), "s5_distinct": len(set(phenos)),
        "ukb_map_header": list(ukb[0]), "ukb_map_rows": len(ukb),
        "target96_header": list(t96[0]), "target96_rows": len(t96),
        "second_ids_in_ukb_map": sum(s in ukb_ids for s in second),
        "first_ids_in_ukb_map": sum(s in ukb_ids for s in first),
        "sample_phenos": phenos[:5],
        "distinct_uniprot_via_second": len({ukb_ids[s].get("UniProt", "") for s in second
                                            if s in ukb_ids}),
        "supplement_13_text": [(p.extract_text() or "")[:1200] for p in mmc13.pages[:1]]}
    (PROBE / "probe2.json").write_text(json.dumps(out, indent=1))
    vol.commit()
    return out


@app.local_entrypoint()
def main() -> None:
    OUT.write_text(json.dumps(probe.remote(), indent=1))
    print(OUT)
