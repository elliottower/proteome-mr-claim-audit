import gzip
import hashlib
import json

import pytest

import build_reference_tables as bt

DICTIONARY = [{"name": f"FinnGen R{n}", "source_identifier": "https://finngen"} for n in range(3, 13)] + [
    {"name": "Neale lab UK Biobank GWAS round 1", "source_identifier": ""},
    {"name": "Neale lab UK Biobank GWAS round 2", "source_identifier": ""},
    {"name": "Pan-UK Biobank", "source_identifier": ""},
    {"name": "MRC-IEU UK Biobank GWAS pipeline (OpenGWAS ukb-b)", "source_identifier": ""},
    {"name": "UK Biobank SAIGE PheWeb (Zhou et al. 2018)", "source_identifier": ""},
    {"name": "UK Biobank TOPMed-imputed PheWeb (Lee/Michigan)", "source_identifier": ""},
    {"name": "FinnGen R12 + UK Biobank meta-analysis", "source_identifier": ""},
    {"name": "FinnGen R12 + MVP + UK Biobank meta-analysis", "source_identifier": ""},
    {"name": "COVID-19 HGI release 7", "source_identifier": ""},
    {"name": "One study", "source_identifier": "doi:10.1/a; PMID:111"},
    {"name": "Varied study", "source_identifier": "PMID:222"},
    {"name": "Shared A", "source_identifier": "PMID:333"},
    {"name": "Shared B", "source_identifier": "PMID:333"},
    {"name": "Curated study", "source_identifier": "PMID:444"}]
BATCHES = {"mapped": [{"batch": "finn-b", "description": "FinnGen biobank analysis round 5",
                       "dictionary_row": "FinnGen R5"}],
           "not_mapped": [{"batch": "bbj-a", "reason": "no row"}]}


def finngen(n, cases):
    head = "phenocode\tname\tn_cases\tn_controls\n" if n < 8 else \
        "phenocode\tphenotype\tcategory\tnum_cases\tnum_controls\n"
    mid = "" if n < 8 else "cat\t"
    return (head + f"T2D\tType 2 diabetes\t{mid}{cases}\t1000\nQ\tA trait\t{mid}NA\tNA\n").encode()


def neale(rows):
    head = "phenotype\tdescription\tvariable_type\tsource\tn_non_missing\tn_missing\tn_controls\tn_cases\n"
    return gzip.compress((head + "".join(rows)).encode())


def files():
    f = {f"finngen_r{n}_manifest": finngen(n, 50 if n in (5, 6) else 100 + n) for n in range(3, 13)}
    for sex in ("both_sexes", "female", "male"):
        for v in ("", "_v2"):
            f[f"neale_r2_phenotypes_{sex}{v}"] = neale(["E11\tDiabetes\tbinary\ticd10\t10\t0\t9\t1\n",
                                                        "50\tHeight\tcontinuous\tphesant\t10\t0\tNA\tNA\n"])
    f["neale_r1_phenosummary"] = b"<!DOCTYPE html><html></html>"
    head = "trait_type\tphenocode\tpheno_sex\tcoding\tmodifier\tdescription\t" + "\t".join(
        f"n_cases_{p}\tn_controls_{p}" for p in ("AFR", "AMR", "CSA", "EAS", "EUR", "MID")) + "\n"
    vals = "\t".join("NA\tNA" if p != "EUR" else "7\t70" for p in ("AFR", "AMR", "CSA", "EAS", "EUR", "MID"))
    f["panukb_phenotype_manifest"] = gzip.compress((head + f"icd10\tE11\tfemales\t\t\tDiabetes\t{vals}\n").encode())
    for k in ("ukb_saige_pheweb_phenotypes", "ukb_topmed_pheweb_phenotypes",
              "finngen_r12_ukbb_meta_phenotypes", "finngen_r12_mvp_ukbb_meta_phenotypes"):
        f[k] = json.dumps([{"phenocode": "250.2", "phenostring": "T2D", "num_cases": 5,
                            "num_controls": 9}]).encode()
    f["opengwas_batches"] = json.dumps([{"id": "finn-b", "description": "FinnGen biobank analysis round 5"}]).encode()
    f["opengwas_gwasinfo"] = json.dumps({
        "ukb-b-1": {"id": "ukb-b-1", "ncase": 3, "ncontrol": 30, "sex": "Males and Females", "population": "European",
                    "build": "HG19/GRCh37", "trait": "T2D"},
        "ieu-a-1": {"id": "ieu-a-1", "pmid": 444, "sample_size": 100, "population": "European"},
        "ieu-a-2": {"id": "ieu-a-2", "pmid": 444, "sample_size": 100, "population": "European"},
        "ieu-a-3": {"id": "ieu-a-3", "pmid": 333, "sample_size": 100, "population": "European"}}).encode()
    f["covid19hg_r7_results_page"] = (b"<div>A2_ALL_x</div><p>Phenotype</p><p>Very severe</p><p>Population</p>"
                                      b"<p>All</p><p>Total Cases</p><p>18</p><p>Total Controls</p><p>99</p>")
    f["gwas_catalog_pmid111_page0"] = json.dumps({"_embedded": {"studies": [
        {"accession_id": "GCST1", "initial_sample_size": "1,000 European"},
        {"accession_id": "GCST2", "initial_sample_size": "1,000 European"}]}}).encode()
    f["gwas_catalog_pmid222_page0"] = json.dumps({"_embedded": {"studies": [
        {"accession_id": "GCST3", "initial_sample_size": "1,000 European"},
        {"accession_id": "GCST4", "initial_sample_size": "300 African American"}]}}).encode()
    return f


def store(tmp_path, f):
    manifest = {}
    for k, body in f.items():
        (tmp_path / k).write_bytes(body)
        manifest[k] = {"url": f"https://x/{k}", "access_date": "2026-10-10", "bytes": len(body),
                       "sha256": hashlib.sha256(body).hexdigest()}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    return bt.Raw(tmp_path)


def test_accessions_map_only_where_the_documents_state_one_release(tmp_path):
    rows, omitted = bt.accession_table(store(tmp_path, files()), DICTIONARY, BATCHES)
    got = {(r["release_identifier"], r["identifier_type"], r["dictionary_row"]) for r in rows}
    assert got == {("finn-b", "opengwas_batch", "FinnGen R5"), ("GCST1", "gwas_catalog", "One study"),
                   ("GCST2", "gwas_catalog", "One study"), ("ieu-a-1", "opengwas", "Curated study"),
                   ("ieu-a-2", "opengwas", "Curated study")}
    reasons = {o["identifier"]: o["reason"] for o in omitted}
    assert reasons["PMID:222"] == "catalog studies state 2 different initial samples"
    assert reasons["PMID:333"] == "the publication is the source of several dictionary rows"
    assert reasons["PMID:444"] == "no catalog study" and reasons["bbj-a"] == "no row"
    assert rows[0]["provenance_url"] == "https://x/opengwas_batches"


def test_a_batch_description_that_differs_from_the_stored_list_stops_the_build(tmp_path):
    bad = {**BATCHES, "mapped": [{**BATCHES["mapped"][0], "description": "FinnGen round 6"}]}
    with pytest.raises(bt.BuildError):
        bt.accession_table(store(tmp_path, files()), DICTIONARY, bad)


def test_counts_keep_only_stated_case_and_control_pairs_and_count_duplicates(tmp_path):
    rows, unusable = bt.counts_table(store(tmp_path, files()), DICTIONARY)
    fg = [r for r in rows if r["resource"] == "FinnGen"]
    assert len(fg) == 10 and {r["endpoint_code"] for r in fg} == {"T2D"}
    assert {(r["release_identifier"], r["duplicate_count"]) for r in fg if r["cases"] == "50"} == {
        ("R5", "2"), ("R6", "2")}
    assert all(r["duplicate_count"] == "1" for r in fg if r["cases"] != "50")
    neale = [r for r in rows if r["resource"] == "Neale lab"]
    assert {(r["sex"], r["count_scope"]) for r in neale} == {
        (s, v) for s in ("both", "female", "male")
        for v in ("phenotype summary file", "phenotype summary file v2")}
    assert all(r["duplicate_count"] == "1" for r in neale)
    pan = [r for r in rows if r["resource"] == "Pan-UKB"]
    assert [(r["endpoint_code"], r["ancestry"], r["sex"], r["cases"], r["controls"]) for r in pan] == [
        ("icd10-E11", "EUR", "female", "7", "70")]
    ukbb = [r for r in rows if r["resource"] == "MRC-IEU UK Biobank pipeline"][0]
    assert (ukbb["sex"], ukbb["ancestry"], ukbb["genome_build"]) == ("both", "European", "HG19/GRCh37")
    hgi = [r for r in rows if r["resource"] == "COVID-19 HGI"][0]
    assert (hgi["endpoint_code"], hgi["endpoint_label"], hgi["ancestry"], hgi["cases"],
            hgi["controls"]) == ("A2_ALL_x", "Very severe", "All", "18", "99")
    assert unusable == ["neale_r1_phenosummary"]
    assert all(r["canonical_outcome_identifier"] == "not_stated" for r in rows)
    assert len(rows) == 10 + 6 + 1 + 4 + 1 + 1


def test_a_changed_stored_file_stops_the_build(tmp_path):
    store(tmp_path, files())
    (tmp_path / "opengwas_batches").write_bytes(b"[]")
    with pytest.raises(bt.BuildError):
        bt.Raw(tmp_path)
