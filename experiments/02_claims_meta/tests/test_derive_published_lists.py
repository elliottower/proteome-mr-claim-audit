import pytest

from derive_published_lists import (EXPECTED, DeriveError, improve_s3, jhs_reagents,
                                    nsphs_analysed, records, scallop_targets)

S3_TEXT = """
S3-table
Gene  Pro tein Name  #samples
below
LOD
CV%  Incl\u2010
uded
Mean
(SD)
ADM  Pro\u2010adrenomedullin  1  0.2  yes  0.87
(0.029)
0.87
(0.85\u20100.88)
AGER  Advanced glycosylation end
product\u2010specific receptor
0  0.15  yes  0.66
(0.043)
CASP8  Caspase\u20108  518    no
CCL2  Monocyte chemoattractant
protein 1
0  0.2  yes  0.6
HLA-X  Notoriously long protein name that
wraps over three
lines  3  0.4  no
IL4  Interleukin\u20104  0  0.2  yes  0.5 (0.1)
Included – final choice on inclusion in analysis
"""


def test_s3_rows_are_read_from_wrapped_pdf_text():
    rows = improve_s3(S3_TEXT, rows=6, included=4)
    assert rows == [{"gene": "ADM", "included": "yes"}, {"gene": "AGER", "included": "yes"},
                    {"gene": "CASP8", "included": "no"}, {"gene": "CCL2", "included": "yes"},
                    {"gene": "HLA-X", "included": "no"}, {"gene": "IL4", "included": "yes"}]


def test_s3_table_with_another_count_than_the_paper_states_is_refused():
    with pytest.raises(DeriveError, match="states 5 of 6"):
        improve_s3(S3_TEXT, rows=6, included=5)
    with pytest.raises(DeriveError):
        improve_s3(S3_TEXT, rows=7, included=4)
    with pytest.raises(DeriveError):
        improve_s3(S3_TEXT.replace("CASP8  Caspase\u20108  518    no", ""), rows=6, included=4)
    with pytest.raises(DeriveError, match="twice"):
        improve_s3(S3_TEXT + "ADM  Pro\u2010adrenomedullin  1  0.2  yes  0.87\n", rows=7,
                   included=5)
    with pytest.raises(DeriveError, match="no Included cell for CCL2"):
        improve_s3(S3_TEXT.replace("0  0.2  yes  0.6\n", "0  0.2  0.6\n"), rows=5, included=3)


def test_header_and_footnote_lines_are_not_rows():
    genes = [r["gene"] for r in improve_s3(S3_TEXT, rows=6, included=4)]
    assert "LOD" not in genes and "CV" not in genes and genes[0] == "ADM"


ANALYTES = [
    {"Name": "ADM", "UniprotID": "P35318", "OlinkShortName": "ADM", "HGNC": "ADM"},
    {"Name": "WFCD2", "UniprotID": "Q14508", "OlinkShortName": "HE4", "HGNC": "WFDC2"},
    {"Name": "IL-6RA", "UniprotID": "P08887", "OlinkShortName": "IL-6RA", "HGNC": "IL6R"},
    {"Name": "TNF", "UniprotID": "P01375", "OlinkShortName": "TNF", "HGNC": "TNF"},
]


def test_analysed_analytes_are_those_a_phenotype_names_once():
    rows = nsphs_analysed(ANALYTES, ["IL-6RA", "WFDC2", "ADM"], n_analytes=4, n_analysed=3)
    assert [(r["name"], r["uniprot"], r["analysed"]) for r in rows] == [
        ("ADM", "P35318", "yes"), ("WFCD2", "Q14508", "yes"), ("IL-6RA", "P08887", "yes"),
        ("TNF", "P01375", "no")]
    assert rows[1]["phenotype"] == "WFDC2"


def test_phenotype_naming_no_analyte_or_two_is_refused():
    with pytest.raises(DeriveError, match="'IL-99' names 0"):
        nsphs_analysed(ANALYTES, ["ADM", "IL-99"], n_analytes=4, n_analysed=2)
    twin = ANALYTES + [{"Name": "ADM2", "UniprotID": "Q7Z4H4", "OlinkShortName": "ADM",
                        "HGNC": "ADM2"}]
    with pytest.raises(DeriveError, match="'ADM' names 2"):
        nsphs_analysed(twin, ["ADM"], n_analytes=5, n_analysed=1)
    with pytest.raises(DeriveError, match="name one analyte"):
        nsphs_analysed(ANALYTES, ["WFDC2", "HE4"], n_analytes=4, n_analysed=2)
    with pytest.raises(DeriveError, match="states 3 of 4"):
        nsphs_analysed(ANALYTES, ["ADM", "TNF"], n_analytes=4, n_analysed=3)


UKB_MAP = [{"OlinkID": "OID20049", "UniProt": "P16860"},
           {"OlinkID": "OID20125", "UniProt": "P16860"},
           {"OlinkID": "OID20753", "UniProt": "Q9NQ76"},
           {"OlinkID": "OID29999", "UniProt": "P00001"}]


def test_targets_take_the_uniprot_cell_of_their_explore_identifier():
    rows = scallop_targets(["OID00131_OID20049", "OID00131_OID20125", "OID00132_OID20753"],
                           UKB_MAP, n_targets=3)
    assert rows == [
        {"pheno": "OID00131_OID20049", "explore_olink_id": "OID20049", "uniprot": "P16860"},
        {"pheno": "OID00131_OID20125", "explore_olink_id": "OID20125", "uniprot": "P16860"},
        {"pheno": "OID00132_OID20753", "explore_olink_id": "OID20753", "uniprot": "Q9NQ76"}]


def test_target_outside_the_protein_map_or_another_count_is_refused():
    with pytest.raises(DeriveError, match="OID20000"):
        scallop_targets(["OID00131_OID20000"], UKB_MAP, n_targets=1)
    with pytest.raises(DeriveError, match="states 3"):
        scallop_targets(["OID00131_OID20049"], UKB_MAP, n_targets=3)
    with pytest.raises(DeriveError, match="states 2"):
        scallop_targets(["OID00131_OID20049", "OID00131_OID20049"], UKB_MAP, n_targets=2)
    repeated = UKB_MAP + [UKB_MAP[0]]
    assert scallop_targets(["OID00131_OID20049"], repeated, n_targets=1)[0]["uniprot"] == "P16860"
    conflicting = UKB_MAP + [{"OlinkID": "OID20049", "UniProt": "P99999"}]
    with pytest.raises(DeriveError, match="P99999"):
        scallop_targets(["OID00131_OID20049"], conflicting, n_targets=1)
    assert scallop_targets(["OID00132_OID20753"], conflicting, n_targets=1)[0][
        "uniprot"] == "Q9NQ76"


def s2(somamer, uniprot, olink="", soma_id="SL1", target="T"):
    return {"SomamerId": somamer, "SomaId": soma_id, "Soma Target": target,
            "UniProt.x": uniprot, "OlinkID": olink}


def test_reagents_are_listed_once_per_uniprot_cell_whatever_their_number_of_table_rows():
    rows = jhs_reagents([s2("LEP.1", "P41159", "OID1"), s2("LEP.1", "P41159", "OID2"),
                         s2("", "", "OID3"), s2("CD177.2", "Q8N6Q3"),
                         s2("LEP.9", "P41159"), s2("ITGAV.ITGB5.4", "P06756"),
                         s2("ITGAV.ITGB5.4", "P18084")], n_reagents=4, n_uniprot=4)
    assert [(r["somamer_id"], r["uniprot"], r["table_rows"], r["uniprot_cells_of_reagent"])
            for r in rows] == [
        ("CD177.2", "Q8N6Q3", "1", "1"), ("ITGAV.ITGB5.4", "P06756", "1", "2"),
        ("ITGAV.ITGB5.4", "P18084", "1", "2"), ("LEP.1", "P41159", "2", "1"),
        ("LEP.9", "P41159", "1", "1")]


def test_reagent_table_with_another_count_than_the_papers_state_is_refused():
    with pytest.raises(DeriveError, match="state 4 and 2"):
        jhs_reagents([s2("LEP.1", "P41159"), s2("CD177.2", "Q8N6Q3")], n_reagents=4,
                     n_uniprot=2)
    with pytest.raises(DeriveError, match="state 2 and 3"):
        jhs_reagents([s2("LEP.1", "P41159"), s2("CD177.2", "Q8N6Q3")], n_reagents=2,
                     n_uniprot=3)


def test_header_is_the_first_row_holding_the_named_column():
    rows = [["Table S5: variance explained", "", ""], ["pheno", "h2", ""],
            ["OID1_OID2", "0.1", ""], ["", "", ""], ["OID3_OID4", "0.2", ""]]
    assert [r["pheno"] for r in records(rows, "pheno")] == ["OID1_OID2", "OID3_OID4"]
    with pytest.raises(DeriveError, match="UniProt"):
        records(rows, "UniProt")


def test_expected_counts_are_the_ones_the_attachment_table_records():
    assert EXPECTED == {"improve": {"rows": 92, "included": 83},
                        "nsphs": {"analytes": 92, "analysed": 77},
                        "scallop": {"targets": 1161},
                        "jhs": {"reagents": 1301, "uniprot_cells": 1297}}
