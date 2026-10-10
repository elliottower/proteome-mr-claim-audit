# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Build the two reference tables of the release-resolution plan from the stored resource
documents (PREREG.md, §Study design, reference tables), with no inference: a row is written only
where the stored document states the value.

`accession_releases.csv` (resource, release identifier, identifier type, dictionary row,
provenance):
- OpenGWAS batch prefixes that the OpenGWAS batch list describes as one dictionary release
  (`reference/opengwas_batch_rows.json`; each description is checked against the stored list);
- GWAS Catalog accessions of a publication that is the source of exactly one dictionary row,
  when every catalog study of that publication states the same initial sample;
- OpenGWAS `ieu-a` and `ieu-b` identifiers of such a publication, when every one of its datasets
  there states the same sample size and population.
Every publication or batch not mapped is listed with its reason in
`accession_releases_omitted.csv`.

`release_counts.csv` (resource, release identifier, dictionary row, endpoint label, endpoint
code, canonical outcome identifier, count type and scope, cases, controls, sex, ancestry, genome
build, duplicate count, provenance): one row per endpoint and scope for which the stored manifest
gives both a case and a control count as numbers. A field the manifest does not state is
`not_stated`; no canonical outcome identifier is stated by any manifest. `duplicate_count` is the
number of dictionary rows of the same resource that hold the same case and control counts for the
same endpoint code, scope, sex and ancestry. A stored file that is not the documented manifest (a
web page returned in its place) gives no rows and is listed in the build summary.

Usage:
    uv run scripts/build_reference_tables.py --raw <dir> --dictionary <csv> \\
        --batches <json> --out <dir> --summary <json>
"""

import argparse
import collections
import csv
import gzip
import hashlib
import html
import io
import json
import pathlib
import re

NS = "not_stated"
ACCESSION_FIELDS = ["resource", "release_identifier", "identifier_type", "dictionary_row",
                    "provenance_url", "access_date", "source_sha256"]
OMITTED_FIELDS = ["resource", "identifier", "dictionary_rows", "reason"]
COUNT_FIELDS = ["resource", "release_identifier", "dictionary_row", "endpoint_label",
                "endpoint_code", "canonical_outcome_identifier", "count_type", "count_scope",
                "cases", "controls", "sex", "ancestry", "genome_build", "duplicate_count",
                "provenance_url", "access_date", "source_sha256"]
PMID = re.compile(r"PMID:\s*(\d+)", re.I)
INT = re.compile(r"^\d+$")


class BuildError(Exception):
    """A stored document is missing, changed, or disagrees with a frozen decision."""


class Raw:
    def __init__(self, raw: pathlib.Path):
        self.raw = raw
        self.manifest = json.loads((raw / "manifest.json").read_text())
        for key, m in self.manifest.items():
            if hashlib.sha256((raw / key).read_bytes()).hexdigest() != m["sha256"]:
                raise BuildError(f"{key} changed since it was fetched")

    def provenance(self, key: str) -> dict:
        m = self.manifest[key]
        return {"provenance_url": m["url"], "access_date": m["access_date"],
                "source_sha256": m["sha256"]}

    def text(self, key: str) -> str:
        data = (self.raw / key).read_bytes()
        if data[:2] == b"\x1f\x8b":
            data = gzip.decompress(data)
        return data.decode("utf-8", errors="replace")

    def json(self, key: str):
        return json.loads(self.text(key))

    def tsv(self, key: str, required: set[str]) -> list[dict] | None:
        rows = list(csv.DictReader(io.StringIO(self.text(key)), delimiter="\t"))
        if not rows or not required <= set(rows[0]):
            return None
        return rows


def pmid_rows(dictionary: list[dict]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = collections.defaultdict(list)
    for r in dictionary:
        for p in set(PMID.findall(r["source_identifier"])):
            out[p].append(r["name"])
    return out


def accession_table(raw: Raw, dictionary: list[dict], batches: dict
                    ) -> tuple[list[dict], list[dict]]:
    names = {r["name"] for r in dictionary}
    listed = {b["id"]: b["description"] for b in raw.json("opengwas_batches")}
    rows, omitted = [], []
    for b in batches["mapped"]:
        if listed.get(b["batch"]) != b["description"] or b["dictionary_row"] not in names:
            raise BuildError(f"batch {b['batch']}: description or dictionary row differs")
        rows.append({"resource": "OpenGWAS", "release_identifier": b["batch"],
                     "identifier_type": "opengwas_batch", "dictionary_row": b["dictionary_row"],
                     **raw.provenance("opengwas_batches")})
    for b in batches["not_mapped"]:
        omitted.append({"resource": "OpenGWAS", "identifier": b["batch"], "dictionary_rows": "",
                        "reason": b["reason"]})
    by_pmid = pmid_rows(dictionary)
    for pmid, row_names in sorted(by_pmid.items(), key=lambda x: int(x[0])):
        if len(row_names) != 1:
            omitted.append({"resource": "GWAS Catalog and OpenGWAS", "identifier": f"PMID:{pmid}",
                            "dictionary_rows": "|".join(sorted(row_names)),
                            "reason": "the publication is the source of several dictionary rows"})
            continue
        pages = sorted((k for k in raw.manifest if k.startswith(f"gwas_catalog_pmid{pmid}_page")),
                       key=lambda k: int(k.rsplit("page", 1)[1]))
        studies = [(k, s) for k in pages
                   for s in raw.json(k).get("_embedded", {}).get("studies", [])]
        samples = {s["initial_sample_size"] for _, s in studies}
        if not studies:
            omitted.append({"resource": "GWAS Catalog", "identifier": f"PMID:{pmid}",
                            "dictionary_rows": row_names[0], "reason": "no catalog study"})
        elif len(samples) != 1:
            omitted.append({"resource": "GWAS Catalog", "identifier": f"PMID:{pmid}",
                            "dictionary_rows": row_names[0],
                            "reason": f"catalog studies state {len(samples)} different initial samples"})
        else:
            for k, s in studies:
                rows.append({"resource": "GWAS Catalog", "release_identifier": s["accession_id"],
                             "identifier_type": "gwas_catalog", "dictionary_row": row_names[0],
                             **raw.provenance(k)})
    info = raw.json("opengwas_gwasinfo")
    curated: dict[str, list[dict]] = collections.defaultdict(list)
    for gid, d in info.items():
        if gid.startswith(("ieu-a-", "ieu-b-")) and d.get("pmid"):
            curated[str(d["pmid"])].append(d)
    for pmid, sets in sorted(curated.items(), key=lambda x: int(x[0])):
        row_names = by_pmid.get(pmid, [])
        if len(row_names) != 1:
            continue
        if len({(d.get("sample_size"), d.get("population")) for d in sets}) != 1:
            omitted.append({"resource": "OpenGWAS", "identifier": f"PMID:{pmid}",
                            "dictionary_rows": row_names[0],
                            "reason": "curated datasets state different sample sizes or populations"})
            continue
        for d in sorted(sets, key=lambda d: d["id"]):
            rows.append({"resource": "OpenGWAS", "release_identifier": d["id"],
                         "identifier_type": "opengwas", "dictionary_row": row_names[0],
                         **raw.provenance("opengwas_gwasinfo")})
    seen = collections.defaultdict(set)
    for r in rows:
        seen[r["release_identifier"]].add(r["dictionary_row"])
    clash = sorted(k for k, v in seen.items() if len(v) > 1)
    if clash:
        raise BuildError(f"identifiers mapped to several rows: {clash[:5]}")
    return rows, omitted


def count_row(resource, release, row, label, code, scope, cases, controls, sex, ancestry,
              build, prov) -> dict | None:
    cases, controls = str(cases).strip(), str(controls).strip()
    if not (INT.match(cases) and INT.match(controls)):
        return None
    return {"resource": resource, "release_identifier": release, "dictionary_row": row,
            "endpoint_label": label or NS, "endpoint_code": code or NS,
            "canonical_outcome_identifier": NS, "count_type": "cases_and_controls",
            "count_scope": scope, "cases": cases, "controls": controls, "sex": sex or NS,
            "ancestry": ancestry or NS, "genome_build": build or NS, **prov}


def counts_table(raw: Raw, dictionary: list[dict]) -> tuple[list[dict], list[str]]:
    names = {r["name"] for r in dictionary}
    out, unusable = [], []

    def add(r):
        if r is not None:
            if r["dictionary_row"] not in names:
                raise BuildError(f"{r['dictionary_row']} is not a dictionary row")
            out.append(r)

    for n in range(3, 13):
        key = f"finngen_r{n}_manifest"
        rows = raw.tsv(key, {"phenocode"})
        if rows is None:
            unusable.append(key)
            continue
        for m in rows:
            add(count_row("FinnGen", f"R{n}", f"FinnGen R{n}", m.get("phenotype") or m.get("name"),
                          m["phenocode"], "release", m.get("num_cases", m.get("n_cases")),
                          m.get("num_controls", m.get("n_controls")), NS, NS, NS,
                          raw.provenance(key)))
    for sex in ("both_sexes", "female", "male"):
        for version in ("", "_v2"):
            key = f"neale_r2_phenotypes_{sex}{version}"
            rows = raw.tsv(key, {"phenotype", "n_cases", "n_controls"})
            if rows is None:
                unusable.append(key)
                continue
            for m in rows:
                add(count_row("Neale lab", "round 2", "Neale lab UK Biobank GWAS round 2",
                              m["description"], m["phenotype"],
                              f"phenotype summary file{' v2' if version else ''}",
                              m["n_cases"], m["n_controls"],
                              {"both_sexes": "both"}.get(sex, sex), NS, NS, raw.provenance(key)))
    if raw.text("neale_r1_phenosummary").lstrip()[:1] == "<":
        unusable.append("neale_r1_phenosummary")
    else:
        raise BuildError("neale_r1_phenosummary is a data file; its format is not yet read")
    key = "panukb_phenotype_manifest"
    rows = raw.tsv(key, {"phenocode", "pheno_sex"})
    if rows is None:
        unusable.append(key)
    else:
        for m in rows:
            code = "-".join(x for x in (m["trait_type"], m["phenocode"], m["coding"],
                                        m["modifier"]) if x)
            for pop in ("AFR", "AMR", "CSA", "EAS", "EUR", "MID"):
                add(count_row("Pan-UKB", "Pan-UKB release", "Pan-UK Biobank", m["description"],
                              code, f"ancestry group {pop}", m.get(f"n_cases_{pop}"),
                              m.get(f"n_controls_{pop}"),
                              {"both_sexes": "both", "females": "female",
                               "males": "male"}.get(m["pheno_sex"], m["pheno_sex"]), pop, NS,
                              raw.provenance(key)))
    for key, resource, release, row in (
            ("ukb_saige_pheweb_phenotypes", "UKB-SAIGE PheWeb", "2018",
             "UK Biobank SAIGE PheWeb (Zhou et al. 2018)"),
            ("ukb_topmed_pheweb_phenotypes", "UKB-TOPMed PheWeb", "TOPMed-imputed",
             "UK Biobank TOPMed-imputed PheWeb (Lee/Michigan)"),
            ("finngen_r12_ukbb_meta_phenotypes", "FinnGen-UKBB meta-analysis", "R12",
             "FinnGen R12 + UK Biobank meta-analysis"),
            ("finngen_r12_mvp_ukbb_meta_phenotypes", "FinnGen-MVP-UKBB meta-analysis", "R12",
             "FinnGen R12 + MVP + UK Biobank meta-analysis")):
        for m in raw.json(key):
            add(count_row(resource, release, row, m.get("phenostring"), m.get("phenocode"),
                          "meta-analysis total" if "meta" in key else "release",
                          m.get("num_cases"), m.get("num_controls"), NS, NS, NS,
                          raw.provenance(key)))
    info = raw.json("opengwas_gwasinfo")
    for gid, d in sorted(info.items()):
        if gid.startswith("ukb-b-"):
            add(count_row("MRC-IEU UK Biobank pipeline", "ukb-b",
                          "MRC-IEU UK Biobank GWAS pipeline (OpenGWAS ukb-b)", d.get("trait"), gid,
                          "release", d.get("ncase", ""), d.get("ncontrol", ""),
                          {"Males and Females": "both", "Females": "female",
                           "Males": "male"}.get(d.get("sex"), NS), d.get("population"),
                          d.get("build"), raw.provenance("opengwas_gwasinfo")))
    key = "covid19hg_r7_results_page"
    page = re.sub(r"<script.*?</script>|<style.*?</style>", "", raw.text(key), flags=re.S)
    flat = re.sub(r"\|(\s*\|)+", "|", html.unescape(re.sub(r"<[^>]+>", "|", page)))
    blocks = re.findall(r"\|\s*([A-C]\d_[A-Za-z0-9_]+)\s*\|\s*Phenotype\s*\|([^|]+)\|\s*Population"
                        r"\s*\|([^|]+)\|\s*Total Cases\s*\|\s*(\d+)\s*\|\s*Total Controls\s*\|"
                        r"\s*(\d+)\s*\|", flat)
    if not blocks:
        unusable.append(key)
    for code, label, pop, cases, controls in blocks:
        add(count_row("COVID-19 HGI", "release 7", "COVID-19 HGI release 7", label.strip(),
                      code, "meta-analysis total", cases, controls, NS, pop.strip(), NS,
                      raw.provenance(key)))
    group = {"FinnGen": "FinnGen", "Neale lab": "Neale lab"}
    holders = collections.defaultdict(set)
    for r in out:
        holders[(group.get(r["resource"], r["resource"]), r["endpoint_code"], r["count_scope"],
                 r["sex"], r["ancestry"], r["cases"], r["controls"])].add(r["dictionary_row"])
    for r in out:
        r["duplicate_count"] = str(len(holders[(group.get(r["resource"], r["resource"]),
                                                r["endpoint_code"], r["count_scope"], r["sex"],
                                                r["ancestry"], r["cases"], r["controls"])]))
    return out, unusable


def write(path: pathlib.Path, fields: list[str], rows: list[dict]) -> None:
    if path.exists():
        raise FileExistsError(f"{path} exists; it is written once")
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=pathlib.Path, required=True)
    ap.add_argument("--dictionary", type=pathlib.Path, required=True)
    ap.add_argument("--batches", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--summary", type=pathlib.Path, required=True)
    a = ap.parse_args()
    raw = Raw(a.raw)
    with a.dictionary.open(newline="") as fh:
        dictionary = list(csv.DictReader(fh))
    accessions, omitted = accession_table(raw, dictionary, json.loads(a.batches.read_text()))
    counts, unusable = counts_table(raw, dictionary)
    summary = {
        "accession_rows": len(accessions),
        "accession_rows_by_type": dict(collections.Counter(r["identifier_type"] for r in accessions)),
        "accession_rows_by_dictionary_row": dict(sorted(collections.Counter(
            r["dictionary_row"] for r in accessions).items())),
        "omitted": omitted,
        "count_rows": len(counts),
        "count_rows_by_dictionary_row": dict(sorted(collections.Counter(
            r["dictionary_row"] for r in counts).items())),
        "count_rows_with_duplicate_count_above_1": sum(r["duplicate_count"] != "1" for r in counts),
        "stored_files_not_the_documented_manifest": unusable,
        "raw_files": len(raw.manifest),
    }
    if a.summary.exists():
        raise FileExistsError(f"{a.summary} exists; it is written once")
    a.summary.write_text(json.dumps(summary, indent=1) + "\n")
    write(a.out / "accession_releases.csv", ACCESSION_FIELDS, accessions)
    write(a.out / "accession_releases_omitted.csv", OMITTED_FIELDS, omitted)
    write(a.out / "release_counts.csv", COUNT_FIELDS, counts)
    print(json.dumps({k: v for k, v in summary.items() if k != "omitted"}, indent=1))


if __name__ == "__main__":
    main()
