import json
import pathlib

import pytest

import source_scanner_v2 as sc

REF = pathlib.Path(__file__).resolve().parent.parent / "reference"
PATTERNS = json.loads((REF / "c1_scanner_patterns_v2.json").read_text())
HOSTS = json.loads((REF / "repository_link_hosts.json").read_text())


def row(name, side="outcome", ident="", release="", aliases=""):
    return {"name": name, "side": side, "aliases": aliases, "release": release,
            "source_identifier": ident}


DICTIONARY = [row("FinnGen R10"), row("Neale lab UK Biobank GWAS round 2"),
              row("MRC pipeline"), row("Consortium A 2019", ident="DOI:10.1038/ng.9999; PMID:12345678"),
              row("Shared one", ident="doi:10.1/shared"), row("Shared two", ident="doi:10.1/shared"),
              row("Named accession row", release="summary statistics (GWAS Catalog GCST90012345)"),
              row("Protein study", side="pqtl", ident="PMID:23456789"),
              row("EGA row", release="EGAS00001234567"), row("dbGaP row", release="phs000123.v1.p1"),
              row("Synapse row", side="pqtl", release="syn51364943")]
ACCESSIONS = [{"release_identifier": "GCST000123", "identifier_type": "gwas_catalog",
               "dictionary_row": "Consortium A 2019"},
              {"release_identifier": "ukb-b", "identifier_type": "opengwas_batch",
               "dictionary_row": "MRC pipeline"}]


def unit(text, uid="u1", rec="r1", ref=False, title="Methods", sec_type=""):
    return {"record_id": rec, "source_key": "full_text", "unit_id": uid, "section_title": title,
            "sec_type": sec_type, "in_reference_list": ref, "text": text}


def found(text, **kw):
    mapper = sc.Mapper(PATTERNS, ACCESSIONS, DICTIONARY)
    return [(c["identifier"], c["expected_row"], c["side"])
            for c in sc.controls([unit(text, **kw)], PATTERNS, mapper)]


@pytest.mark.parametrize("text,expected", [
    ("Outcome GWAS summary statistics came from FinnGen release 10.",
     [("FinnGen release 10", "FinnGen R10", "outcome")]),
    ("We used the finngen_R10 summary statistics.", [("finngen_R10", "FinnGen R10", "outcome")]),
    ("GWAS data were the Neale lab round 2 results.",
     [("Neale lab round 2", "Neale lab UK Biobank GWAS round 2", "outcome")]),
    ("Outcome data (GCST000123) were downloaded.", [("GCST000123", "Consortium A 2019", "outcome")]),
    ("Outcome data (ebi-a-GCST000123) were downloaded.",
     [("ebi-a-GCST000123", "Consortium A 2019", "outcome")]),
    ("The outcome dataset ukb-b-12345 was used.", [("ukb-b-12345", "MRC pipeline", "outcome")]),
    ("Summary statistics are in GCST90012345.", [("GCST90012345", "Named accession row", "outcome")]),
    ("pQTL data were taken from the study (PMID: 23456789).",
     [("PMID: 23456789", "Protein study", "pqtl")]),
    ("GWAS summary statistics (doi:10.1038/NG.9999).",
     [("10.1038/NG.9999", "Consortium A 2019", "outcome")]),
])
def test_a_mapped_identifier_with_context_is_a_control(text, expected):
    assert found(text) == expected


@pytest.mark.parametrize("text,kw", [
    ("Outcome GWAS from FinnGen release 13.", {}),
    ("Outcome GWAS from GCST999999.", {}),
    ("GWAS summary statistics (doi:10.1/shared).", {}),
    ("Participants were recruited in FinnGen release 10.", {}),
    ("GWAS of FinnGen release 10. Nature 2023.", {"ref": True}),
    ("Outcome GWAS from FinnGen, the latest release.", {}),
])
def test_an_unmapped_ambiguous_contextless_or_reference_list_match_is_not(text, kw):
    assert found(text, **kw) == []


def test_the_draw_keeps_one_per_record_identifier_and_row_and_is_seeded():
    mapper = sc.Mapper(PATTERNS, ACCESSIONS, DICTIONARY)
    units = [unit(f"Outcome GWAS from FinnGen R10 and GCST000123 ({i}).", uid=f"u{i}", rec=f"r{i % 90}")
             for i in range(400)]
    got = sc.controls(units, PATTERNS, mapper)
    first = sc.draw(got, PATTERNS)
    assert len(got) == 800 and len(first) == PATTERNS["draw"]["maximum"]
    assert len({(c["record_id"], c["identifier"]) for c in first}) == len(first)
    assert first == sc.draw(list(reversed(got)), PATTERNS)


def test_links_count_presence_by_host_and_inside_an_availability_section():
    units = [unit("Code: https://github.com/someone/tool and doi 10.5281/zenodo.123456", rec="a",
                  title="Code availability"),
             unit("We used TwoSampleMR (github.com/MRCIEU/TwoSampleMR).", rec="b"),
             unit("Data are at osf.io/abcde.", rec="b", sec_type="data-availability"),
             unit("No link here; see gitlab.example.org.", rec="c")]
    out = sc.links(units, HOSTS)
    assert out["a"] == {"any_link": True, "availability_section_link": True,
                        "hosts": ["github", "zenodo"],
                        "hosts_in_availability_section": ["github", "zenodo"]}
    assert out["b"] == {"any_link": True, "availability_section_link": True,
                        "hosts": ["github", "osf"], "hosts_in_availability_section": ["osf"]}
    assert out["c"] == {"any_link": False, "availability_section_link": False, "hosts": [],
                        "hosts_in_availability_section": []}


def test_an_output_is_written_once(tmp_path):
    sc.write_once(tmp_path / "o.json", {})
    with pytest.raises(sc.ScannerError):
        sc.write_once(tmp_path / "o.json", {})


@pytest.mark.parametrize("written,canonical,expected", [
    ("gcst000123", "GCST000123", "Consortium A 2019"),
    ("Gcst000123", "GCST000123", "Consortium A 2019"),
    ("EBI-A-gcst000123", "ebi-a-GCST000123", "Consortium A 2019"),
    ("UKB-B-12345", "ukb-b-12345", "MRC pipeline"),
    ("egas00001234567", "EGAS00001234567", "EGA row"),
    ("PHS000123.V1.P1", "phs000123.v1.p1", "dbGaP row"),
    ("SYN51364943", "syn51364943", "Synapse row"),
])
def test_an_accession_in_any_case_is_put_in_its_canonical_case_before_lookup(written, canonical,
                                                                            expected):
    got = found(f"The GWAS summary statistics ({written}) were used.")
    assert [(g[0], g[1]) for g in got] == [(canonical, expected)]


@pytest.mark.parametrize("terminal", list(".,;:)]}"))
def test_a_doi_loses_each_terminal_character_before_lookup(terminal):
    got = found(f"GWAS summary statistics came from doi:10.1038/ng.9999{terminal} as described")
    assert got == [("10.1038/ng.9999", "Consortium A 2019", "outcome")]


def test_a_doi_followed_by_several_terminal_characters_still_maps():
    assert found("GWAS summary statistics (doi:10.1038/ng.9999)].") == [
        ("10.1038/ng.9999", "Consortium A 2019", "outcome")]
