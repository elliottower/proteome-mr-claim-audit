import supplement_triage_v1 as st

SC = st.Scanner()

TEXT = "\n".join([
    "## sheet Exposure",
    "id.exposure\tid.outcome\tsamplesize.outcome",
    "prot-a-1\tfinngen_R10_I9_STR\t300000",
    "## sheet Outcome",
    "x\tebi-a-GCST005838\ty",
    "Summary statistics were from FinnGen release 7 and ieu-a-7.",
])


def test_identifiers_are_located_mapped_and_not_double_counted():
    idents, raw, *_ = st.scan_text(SC, TEXT)
    by = {(d["pattern"], d["identifier"]): d for d in idents.values()}
    fg = by[("extra:finngen_file_id", "finngen_R10_I9_STR")]
    assert fg["rows"] == ["FinnGen R10"]
    assert fg["first"] == {"line": 3, "sheet": "Exposure"}
    og = by[("accession:opengwas", "ebi-a-GCST005838")]
    assert og["first"] == {"line": 5, "sheet": "Outcome"}
    assert not any(p == "accession:gwas_catalog" for p, _ in by)
    assert not any(p == "extra:opengwas_any" and i == "ebi-a-GCST005838" for p, i in by)
    assert by[("release:FinnGen", "FinnGen R7")]["rows"] == ["FinnGen R7"]
    assert by[("extra:opengwas_any", "prot-a-1")]["rows"] == ["INTERVAL SomaScan (Sun 2018)"]
    ctx = raw["extra:finngen_file_id|finngen_R10_I9_STR"][0]["context"]
    assert ctx[0].startswith("2: id.exposure") and ctx[2].startswith("4: ## sheet Outcome")


def test_an_exact_case_control_pair_on_a_finngen_line_matches_the_counts_table():
    text = "FinnGen R3 arthropod-borne fevers: 866 cases and 134772 controls"
    *_, cm, _, _ = st.scan_text(SC, text)
    assert {"dictionary_row": "FinnGen R3", "endpoint_code": "AB1_ARTHROPOD", "cases": "866",
            "controls": "134772", "line": 1} in cm
