import hashlib
import io
import zipfile

import pytest

from assay_backgrounds import build_published, load_lists, published_list
from pathway_enrichment import (ASSAY_LISTS, ATTACHMENTS, MIN_PROXY_COVERAGE, PathwayInputError,
                                attachment_records, load_attachments, proxy_coverage)
from platform_list_sources import (DERIVED, SOURCE_FILES, SOURCES, ListSource, ListSourceError,
                                   SourceFile, checked_content, csv_rows, id_cells, is_derived,
                                   load_source_files, load_sources, table)

REVIEWED = frozenset({"P11111", "P22222", "P33333", "Q44444", "Q55555"})


def source(**kw):
    base = dict(list_id="demo", file="demo.xlsx", url="https://example.org/demo.xlsx",
                zip_member="", sha256="", sheet="", id_column="UniProt", id_kind="uniprot",
                filter_column="", filter_value="", source="Demo et al.")
    return ListSource(**{**base, **kw})


SHEET = [
    ("Supplementary Data 1", None, None),
    (None, None, None),
    ("Name", "UniProt", "On panel (1-yes, 0-no)"),
    ("A", "P11111", 1.0),
    ("B", "P22222  P33333", 0),
    ("C", None, 1),
    (None, None, None),
    ("D", "A0A000XYZ1;Q44444", 1),
]


def test_header_is_the_first_row_holding_the_identifier_column():
    header, data = table(SHEET, source())
    assert header == ["Name", "UniProt", "On panel (1-yes, 0-no)"]
    assert [r["Name"] for r in data] == ["A", "B", "C", "D"]
    assert id_cells(SHEET, source()) == ["P11111", "P22222  P33333", "", "A0A000XYZ1;Q44444"]


def test_row_filter_compares_cell_text_and_reads_whole_numbers_without_a_decimal():
    filtered = source(filter_column="On panel (1-yes, 0-no)", filter_value="1")
    assert id_cells(SHEET, filtered) == ["P11111", "", "A0A000XYZ1;Q44444"]


def test_missing_identifier_or_filter_column_raises():
    with pytest.raises(ListSourceError, match="Accession"):
        table(SHEET, source(id_column="Accession"))
    with pytest.raises(ListSourceError, match="QC"):
        table(SHEET, source(filter_column="QC", filter_value="1"))


def test_uniprot_list_keeps_every_reviewed_accession_of_every_cell():
    kept, meta = published_list(id_cells(SHEET, source()), source(), REVIEWED,
                                lambda symbol: frozenset())
    assert kept == {"P11111", "P22222", "P33333", "Q44444"}
    assert (meta["rows"], meta["rows_without_identifier"], meta["accessions_printed"],
            meta["accessions_in_reviewed_uniprot"]) == (4, 1, 5, 4)
    assert meta["cells_or_symbols_without_reviewed_accession"] == []


def test_gene_symbol_list_maps_each_symbol_and_lists_the_unmapped_ones():
    symbols = {"IL6R": frozenset({"P11111"}), "C4A": frozenset({"P22222"}),
               "C4B": frozenset({"P33333", "Q99999"}), "HLA-DRB1": frozenset({"Q44444"})}
    cells = ["IL6R", "C4A C4B", "HLA-DRB1", "LOC123", "", "IL6R"]
    kept, meta = published_list(cells, source(id_kind="gene_symbol"), REVIEWED,
                                lambda s: symbols.get(s, frozenset()))
    assert kept == {"P11111", "P22222", "P33333", "Q44444"}
    assert meta["cells_or_symbols_without_reviewed_accession"] == ["LOC123"]
    assert (meta["rows"], meta["rows_without_identifier"],
            meta["distinct_identifier_cells"]) == (6, 1, 4)


def test_downloaded_file_is_refused_when_its_checksum_differs():
    body = b"workbook bytes"
    good = source(sha256=hashlib.sha256(body).hexdigest())
    assert checked_content(good, body) == body
    with pytest.raises(ListSourceError, match="sha256"):
        checked_content(good, body + b"x")
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("supp/other.pdf", b"pdf")
        z.writestr("supp/list.xlsx", body)
    zipped = source(zip_member="list.xlsx", sha256=hashlib.sha256(body).hexdigest())
    assert checked_content(zipped, archive.getvalue()) == body
    with pytest.raises(ListSourceError, match="members"):
        checked_content(source(zip_member="absent.xlsx"), archive.getvalue())


def test_member_of_a_member_is_read_through_both_archives():
    body = b"tables"
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as z:
        z.writestr("tables.xlsx", body)
        z.writestr("readme.txt", b"x")
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w") as z:
        z.writestr("supp/tables.zip", inner.getvalue())
        z.writestr("supp/figure.pdf", b"pdf")
    nested = SourceFile(file="t.xlsx", url="https://example.org/s", source="Demo",
                        zip_member="tables.zip!tables.xlsx",
                        sha256=hashlib.sha256(body).hexdigest())
    assert checked_content(nested, outer.getvalue()) == body
    wrong = nested.model_copy(update={"zip_member": "tables.zip!absent.xlsx"})
    with pytest.raises(ListSourceError, match="absent.xlsx"):
        checked_content(wrong, outer.getvalue())
    with pytest.raises(ListSourceError, match="t.xlsx: sha256"):
        checked_content(nested.model_copy(update={"sha256": "0" * 64}), outer.getvalue())


def test_committed_source_tables_are_well_formed():
    sources = load_sources(SOURCES)
    published = [s for s in sources if not is_derived(s)]
    derived = [s for s in sources if is_derived(s)]
    assert len(published) == 10 and len(derived) == 4
    assert all(len(s.sha256) == 64 and s.url.startswith("https://") for s in published)
    assert all(len(s.sha256) == 64 and not s.url and (DERIVED / s.file).exists()
               for s in derived)
    assert {s.list_id for s in sources if s.id_kind == "gene_symbol"} == {
        "somascan_ages_custom", "fhs_luminex_71", "olink_cvd1_improve_analysed"}
    files = load_source_files(SOURCE_FILES)
    assert len(files) == 4 and all(len(f.sha256) == 64 and f.url.startswith("https://")
                                   for f in files)
    assert {f.file for f in files}.isdisjoint({s.file for s in sources})


def test_source_table_refuses_a_derived_table_with_a_url(tmp_path):
    path = tmp_path / "sources.csv"
    header = ("list_id,file,url,zip_member,sha256,sheet,id_column,id_kind,filter_column,"
              "filter_value,source\n")
    path.write_text(header + "a,a.csv,https://example.org/a,,0,,UniProt,uniprot,,,Demo\n")
    with pytest.raises(ListSourceError, match="derived"):
        load_sources(path)
    path.write_text(header + "a,a.xlsx,,,0,,UniProt,uniprot,,,Demo\n")
    with pytest.raises(ListSourceError, match="derived"):
        load_sources(path)


def test_derived_table_is_read_with_its_row_filter_and_checksum(tmp_path):
    derived = tmp_path / "derived"
    derived.mkdir()
    table_text = "gene,included\nIL6R,yes\nCASP8,no\nC4A,yes\n"
    (derived / "demo.csv").write_text(table_text)
    src = source(list_id="demo_analysed", file="demo.csv", url="", id_column="gene",
                 id_kind="gene_symbol", filter_column="included", filter_value="yes",
                 sha256=hashlib.sha256(table_text.encode()).hexdigest())
    assert csv_rows(derived / "demo.csv")[0] == ("gene", "included")
    symbols = {"IL6R": frozenset({"P11111"}), "C4A": frozenset({"P22222"}),
               "CASP8": frozenset({"Q44444"})}
    lists, meta = build_published(tmp_path / "volume", [src], REVIEWED,
                                  lambda s: symbols.get(s, frozenset()), derived)
    assert lists == {"demo_analysed": {"P11111", "P22222"}}
    assert meta["demo_analysed"]["rows"] == 2
    bad = src.model_copy(update={"sha256": "0" * 64})
    with pytest.raises(Exception, match="sha256"):
        build_published(tmp_path / "volume", [bad], REVIEWED, lambda s: frozenset(), derived)


ATTACHMENT_HEADER = ("dictionary_row,platform_string,assay_list,background_level,"
                     "whole_panel_assay_list,alternative_assay_list,assay_reagents,"
                     "reported_targets,analysed_targets\n")


def attachment_table(tmp_path, rows):
    """`rows`: (row, platform string, assay list, alternative list[, level, whole-panel list,
    reported targets])."""
    dictionary = tmp_path / "dictionary.csv"
    dictionary.write_text("side,name,platform\n" + "".join(
        f"pqtl,{r[0]},{r[1]}\n" for r in rows) + "outcome,FinnGen,none\n")
    path = tmp_path / "attachments.csv"
    lines = []
    for r in rows:
        level, whole, reported = (*r[4:], *("analysed" if r[2] else "unavailable", "", ""))[:3]
        lines.append(",".join([r[0], r[1], r[2], level, whole, r[3], "", reported, ""]) + "\n")
    path.write_text(ATTACHMENT_HEADER + "".join(lines))
    return path, dictionary


def test_union_attachment_adds_the_union_list_and_alternative_is_read_on_request(tmp_path):
    path, dictionary = attachment_table(tmp_path, [
        ("Row A", "Olink", "panel:1", ""), ("Row B", "Olink two panels", "panel:1|panel:2", ""),
        ("Row C", "instruments", "small", "panel:1|panel:2|panel:3"), ("Row D", "unknown", "", "")])
    lists = {"panel:1": frozenset({"P1", "P2"}), "panel:2": frozenset({"P2", "P3"}),
             "panel:3": frozenset({"P9"}), "small": frozenset({"P1"})}
    attached = load_attachments(path, lists, dictionary)
    assert attached == {"Row A": "panel:1", "Row B": "panel:1|panel:2", "Row C": "small",
                        "Row D": None}
    assert lists["panel:1|panel:2"] == {"P1", "P2", "P3"}
    alternative = load_attachments(path, lists, dictionary, alternative=True)
    assert alternative == {**attached, "Row C": "panel:1|panel:2|panel:3"}
    assert lists["panel:1|panel:2|panel:3"] == {"P1", "P2", "P3", "P9"}


def test_attachment_to_an_unknown_list_or_a_changed_platform_string_is_refused(tmp_path):
    lists = {"panel:1": frozenset({"P1"})}
    path, dictionary = attachment_table(tmp_path, [("Row A", "Olink", "panel:1|panel:7", "")])
    with pytest.raises(PathwayInputError, match="panel:7"):
        load_attachments(path, lists, dictionary)
    path, dictionary = attachment_table(tmp_path, [("Row A", "Olink", "panel:1", "")])
    dictionary.write_text("side,name,platform\npqtl,Row A,SomaScan\n")
    with pytest.raises(PathwayInputError, match="platform string"):
        load_attachments(path, lists, dictionary)


def test_whole_panel_list_is_read_only_on_request(tmp_path):
    path, dictionary = attachment_table(tmp_path, [
        ("Row A", "Olink", "analysed_a", "", "analysed", "panel:1|panel:2", ""),
        ("Row B", "Olink", "panel:1", "", "platform", "", ""),
        ("Row C", "SomaScan", "", "", "unavailable", "panel:2", "")])
    lists = {"panel:1": frozenset({"P1", "P2"}), "panel:2": frozenset({"P3"}),
             "analysed_a": frozenset({"P1"})}
    assert load_attachments(path, lists, dictionary) == {
        "Row A": "analysed_a", "Row B": "panel:1", "Row C": None}
    assert load_attachments(path, lists, dictionary, whole_panel=True) == {
        "Row A": "panel:1|panel:2", "Row B": "panel:1", "Row C": "panel:2"}
    assert lists["panel:1|panel:2"] == {"P1", "P2", "P3"}


def test_background_level_must_be_registered_and_agree_with_the_assay_list(tmp_path):
    lists = {"panel:1": frozenset({"P1"})}
    path, dictionary = attachment_table(tmp_path, [("Row A", "Olink", "panel:1", "", "exact")])
    with pytest.raises(PathwayInputError, match="background level"):
        load_attachments(path, lists, dictionary)
    path, dictionary = attachment_table(tmp_path, [("Row A", "Olink", "panel:1", "",
                                                    "unavailable")])
    with pytest.raises(PathwayInputError, match="unavailable"):
        load_attachments(path, lists, dictionary)
    path, dictionary = attachment_table(tmp_path, [("Row A", "Olink", "", "", "platform")])
    with pytest.raises(PathwayInputError, match="unavailable"):
        load_attachments(path, lists, dictionary)


@pytest.mark.parametrize("level, accessions, reported, expected", [
    ("platform", 1063, 1297, 1063 / 1297), ("assayed", 90, 100, 0.9),
    ("analysed", 10, 100, None), ("platform", 50, None, None), ("assayed", 50, 0, None)])
def test_proxy_coverage_is_the_share_of_reported_targets_on_a_proxy_list(
        level, accessions, reported, expected):
    assert proxy_coverage(level, accessions, reported) == (
        None if expected is None else pytest.approx(expected))


def test_proxy_list_covering_under_ninety_percent_of_the_reported_targets_is_refused(tmp_path):
    assert MIN_PROXY_COVERAGE == pytest.approx(0.90)
    lists = {"proxy": frozenset(f"P{i}" for i in range(89)),
             "enough": frozenset(f"P{i}" for i in range(90))}
    for level in ("platform", "assayed"):
        path, dictionary = attachment_table(tmp_path, [("Row A", "SomaScan", "proxy", "",
                                                        level, "", "100")])
        with pytest.raises(PathwayInputError, match="unavailable"):
            load_attachments(path, lists, dictionary)
    path, dictionary = attachment_table(tmp_path, [
        ("Row A", "SomaScan", "enough", "", "platform", "", "100"),
        ("Row B", "SomaScan", "proxy", "", "analysed", "", "100"),
        ("Row C", "SomaScan", "", "", "unavailable", "proxy", "100")])
    assert load_attachments(path, lists, dictionary) == {
        "Row A": "enough", "Row B": "proxy", "Row C": None}
    assert load_attachments(path, lists, dictionary, whole_panel=True)["Row C"] == "proxy"


def test_committed_attachments_cover_every_pqtl_row_and_the_union_lists_exist():
    lists = load_lists(ASSAY_LISTS)
    attached = load_attachments(ATTACHMENTS, lists)
    assert len(attached) == 28 and all(attached.values())
    png = "MANOLIS and Pomak neurology (Png 2021)"
    union = "olink_target_96:NEU|olink_target_96:NEX"
    whole = load_attachments(ATTACHMENTS, lists, whole_panel=True)
    assert (attached[png], whole[png]) == ("olink_helic_png2021", union)
    assert lists[union] == lists["olink_target_96:NEU"] | lists["olink_target_96:NEX"]
    zheng = "Zheng 2020 proteome-wide MR instrument set"
    assert attached[zheng] == "zheng2020_instrumented_1699"
    alternative = load_attachments(ATTACHMENTS, lists, alternative=True)
    assert alternative[zheng] != attached[zheng]
    assert lists[alternative[zheng]] >= lists["somascan_160410"] | lists["fhs_luminex_71"]
    assert {k for k in attached if alternative[k] != attached[k]} == {zheng}


def test_committed_backgrounds_follow_the_registered_hierarchy():
    lists = load_lists(ASSAY_LISTS)
    attached = load_attachments(ATTACHMENTS, lists)
    whole = load_attachments(ATTACHMENTS, lists, whole_panel=True)
    rows = {r["dictionary_row"]: r for r in attachment_records(ATTACHMENTS)}
    levels = {k: r["background_level"] for k, r in rows.items()}
    assert sorted(set(levels.values())) == ["analysed", "assayed", "platform"]
    # The rows whose analysed proteins the source marks take the analysed list, a subset of
    # the whole panel that the sensitivity analysis reads.
    for row, analysed in (("IMPROVE (Folkersen 2017)", 83), ("MANOLIS (Gilly 2020)", 257),
                          ("NSPHS (Enroth 2014)", 77),
                          ("MANOLIS and Pomak neurology (Png 2021)", 184)):
        assert levels[row] == "analysed" and rows[row]["analysed_targets"] == analysed
        assert whole[row] != attached[row]
        assert lists[attached[row]] <= lists[whole[row]]
        assert abs(len(lists[attached[row]]) - analysed) <= 2
    assert len(lists[attached["IMPROVE (Folkersen 2017)"]]) < len(
        lists[whole["IMPROVE (Folkersen 2017)"]])
    # The Folkersen 2020 table does not mark the two proteins that failed quality control.
    scallop = "SCALLOP CVD-I (Folkersen 2020)"
    assert (levels[scallop], rows[scallop]["analysed_targets"], whole[scallop]) == (
        "assayed", 90, attached[scallop])
    # The Jackson Heart Study row takes the study's 1,301 reagents; the incomplete commercial
    # list is read only in the sensitivity analysis.
    jhs = "Jackson Heart Study (Katz 2022)"
    assert (attached[jhs], whole[jhs], levels[jhs]) == (
        "somascan_1.3k_jhs_katz2022", "somascan_1.3k", "analysed")
    assert len(lists[attached[jhs]]) > len(lists[whole[jhs]])
    assert proxy_coverage("platform", len(lists[whole[jhs]]), 1297) < MIN_PROXY_COVERAGE
    koprulu = "SCALLOP multi-cohort meta-analysis (Koprulu 2026)"
    assert levels[koprulu] == "analysed" and lists[attached[koprulu]] != lists[whole[koprulu]]
    for row, r in rows.items():
        coverage = proxy_coverage(r["background_level"], len(lists[attached[row]]),
                                  r["reported_targets"])
        assert coverage is None or coverage >= MIN_PROXY_COVERAGE
    assert {k for k in attached if whole[k] != attached[k]} == {
        "IMPROVE (Folkersen 2017)", "MANOLIS (Gilly 2020)", "NSPHS (Enroth 2014)", jhs,
        "MANOLIS and Pomak neurology (Png 2021)", koprulu}


def test_committed_lists_hold_every_published_list():
    lists = load_lists(ASSAY_LISTS)
    for source in load_sources(SOURCES):
        assert lists[source.list_id], source.list_id
