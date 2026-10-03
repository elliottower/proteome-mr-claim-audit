import pytest

from assay_backgrounds import accessions, build_lists, load_lists, write_lists
from eldjarn_pleiotropic_loci import WorkbookError, close_genes, load_list, write_list


@pytest.mark.parametrize("cell, expected", [
    ("P02745  P02746  P02747", {"P02745", "P02746", "P02747"}),
    ("Q14213_Q8NEV9", {"Q14213", "Q8NEV9"}),
    ("P29460,P29459", {"P29460", "P29459"}),
    ("Q13131|Q9Y478|P54619", {"Q13131", "Q9Y478", "P54619"}),
    ("P12345-2", {"P12345"}),
    ("A0A024R161", {"A0A024R161"}),
    ("NA", set()), ("", set()), (None, set()), ("No UniProt", set()),
])
def test_accessions_reads_every_accession_in_a_cell(cell, expected):
    assert accessions(cell) == expected


def test_lists_keep_reviewed_accessions_and_split_panels_and_the_1k_subset(tmp_path):
    (tmp_path / "olink_protein_map_3k_v1.tsv").write_text(
        "UKBPPP_ProteinID\tUniProt\nA\tP11111\nB\tQ22222\nC\tP11111\n")
    (tmp_path / "olink_protein_map_1.5k_v1.tsv").write_text("UKBPPP_ProteinID\tUniProt\nA\tP11111\n")
    (tmp_path / "pQTLdata_0.6_Olink_Target_96.tsv").write_text(
        "UniProt\tProtein\tPanel\nP11111\ta\tINF\nQ22222\tb\tINF, CVD II\nP33333_Q44444\tc\tCVD II\n")
    (tmp_path / "eldjarn2023_ST2_soma_assays.tsv").write_text(
        "ST2: Assays on the SomaScan v4 platform\n\n"
        "seqid\tuniprot\ton_1.2k\nS1\tP11111\tTrue\nS2\tQ22222|P33333\tFalse\nS3\tNA\tTrue\n")
    (tmp_path / "pQTLdata_0.6_SomaScan160410.tsv").write_text("SOMAMER_ID\tUniProt\nx\tP55555\n")
    (tmp_path / "pQTLdata_0.6_SomaScanV4.1.tsv").write_text("#\tSeqID\tUniProt.ID\n1\ty\tP11111\n")
    reviewed = frozenset({"P11111", "Q22222", "P33333", "Q44444"})
    lists, meta = build_lists(tmp_path, reviewed)
    assert lists["olink_explore_3072"] == {"P11111", "Q22222"}
    assert lists["olink_target_96"] == {"P11111", "Q22222", "P33333", "Q44444"}
    assert lists["olink_target_96:INF"] == {"P11111", "Q22222"}
    assert lists["olink_target_96:CVD II"] == {"Q22222", "P33333", "Q44444"}
    assert lists["somascan_v4"] == {"P11111", "Q22222", "P33333"}
    assert lists["somascan_1.3k"] == {"P11111"}
    assert lists["somascan_160410"] == frozenset()
    assert meta["somascan_160410"]["accessions_not_in_reviewed_uniprot"] == ["P55555"]
    assert meta["somascan_v4"]["rows_without_accession"] == 1
    out = tmp_path / "lists.csv"
    write_lists(lists, out)
    assert load_lists(out) == {k: v for k, v in lists.items() if v}


class Sheet:
    def __init__(self, title, rows):
        self.title, self._rows = title, rows

    def iter_rows(self, min_row=1, max_row=None, values_only=True):
        return iter(self._rows[min_row - 1:max_row])


class Workbook:
    def __init__(self, *sheets):
        self.worksheets = list(sheets)


def test_close_genes_reads_every_close_gene_column_of_the_st36_sheet(tmp_path):
    rows = [("ST36: HIGHLY PLEIOTROPIC VARIANTS", None, None, None),
            (None, None, None, None),
            ("Chrom", "Olink\nclose\ngenes", "Soma\nSMP\nclose\ngenes", "Soma PC0 close genes"),
            ("chr10", "JMJD1C,MIR1296", "JMJD1C, NRBF2", None),
            ("chr9", "ABO", "NA", "ABO;SURF6"),
            (None, None, None, None)]
    wb = Workbook(Sheet("ST35_other", [("x",)]), Sheet("ST36_pleiotropic_pQTLs", rows))
    counts, provenance = close_genes(wb)
    assert counts == {"JMJD1C": 1, "MIR1296": 1, "NRBF2": 1, "ABO": 1, "SURF6": 1}
    assert provenance["variant_rows"] == 2 and provenance["distinct_genes"] == 5
    assert provenance["gene_columns"] == ["Olink close genes", "Soma SMP close genes",
                                          "Soma PC0 close genes"]
    path = tmp_path / "loci.csv"
    write_list(counts, path)
    assert load_list(path) == frozenset(counts)


def test_workbook_without_the_sheet_is_refused():
    with pytest.raises(WorkbookError):
        close_genes(Workbook(Sheet("ST35_other", [("x",)])))
    with pytest.raises(WorkbookError):
        close_genes(Workbook(Sheet("ST36_x", [("no gene column",)])))
