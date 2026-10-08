import pytest

import manual_coding_new_rows as n


def q(record, side="outcome", name="FinnGen", claims="1"):
    return {"record_id": record, "side": side, "name_as_written": name, "family_id": "F",
            "mapping_state": "release_ambiguous", "candidates": "a|b", "claim_records": claims}


def test_the_new_queue_is_the_listed_rows_as_the_rebuilt_queue_has_them():
    rebuilt = [q("p1"), q("p2", claims="7"), q("p2", "pqtl", "deCODE"), q("p3")]
    listed = [{"record_id": "p3", "side": "outcome", "name_as_written": "FinnGen"},
              {"record_id": "p2", "side": "outcome", "name_as_written": "FinnGen"}]
    assert n.new_queue(rebuilt, listed) == [rebuilt[1], rebuilt[3]]
    with pytest.raises(n.NewRowsError):
        n.new_queue(rebuilt, [*listed, {"record_id": "p9", "side": "pqtl",
                                        "name_as_written": "x"}])
    with pytest.raises(n.NewRowsError):
        n.new_queue(rebuilt, [listed[0], listed[0]])


def test_a_share_lists_each_paper_for_a_first_attempt():
    assert n.share_list(["W9.json", "123.json"]) == [
        {"input_file": "123.json", "rules": [], "gate_file": None, "next_attempt": 1,
         "write_as": "123.attempt1.json"},
        {"input_file": "W9.json", "rules": [], "gate_file": None, "next_attempt": 1,
         "write_as": "W9.attempt1.json"}]


PAPER = {"record_id": "p2", "rows": [
    {"side": "outcome", "name_as_written": "FinnGen", "candidates": ["FinnGen R9", "FinnGen R10"],
     "passages": [{"passage_id": "p001", "source_read": "full_text", "section": "Methods",
                   "sentences": ["First sentence.", "Second sentence [3]."],
                   "references": [{"label": "3", "entry": "Kurki 2023.", "doi": "10.1/x"},
                                  {"label": "4", "entry": "No identifier.", "doi": None}]},
                  {"passage_id": "p002", "source_read": "abstract", "section": None,
                   "sentences": ["Only one."], "references": []}]},
    {"side": "pqtl", "name_as_written": "deCODE", "candidates": [], "passages": []},
    {"side": "outcome", "name_as_written": "UK Biobank", "candidates": ["UK Biobank"],
     "passages": []}]}
RECORDS = {"p2": {"record_id": "p2", "first_author_surname": "Lee",
                  "first_public": {"value": "2024-05-01"}, "title": "A title", "pmid": "2",
                  "doi": "10.5/y", "pmcid": None},
           "p1": {"record_id": "p1", "first_author_surname": None, "first_public": "2023-01-01",
                  "title": "Other"}}

EXPECTED = """# Check 2, batch 24 of 24: 3 rows in 1 papers

Answer every row below as the prompt file says.

## Paper p2

Reference: Lee (2024). A title. PMID 2; DOI 10.5/y

### Row p2#outcome_1

- Side: outcome
- Dataset name as written: FinnGen
- Candidate dictionary rows: FinnGen R9; FinnGen R10

Passage p001 (full_text; section: Methods):
  1. First sentence.
  2. Second sentence [3].
  [reference 3] Kurki 2023. (DOI 10.1/x)
  [reference 4] No identifier.

Passage p002 (abstract; section: none):
  1. Only one.

### Row p2#pqtl_1

- Side: pqtl
- Dataset name as written: deCODE
- Candidate dictionary rows: none listed (any row of this side may be named)

### Row p2#outcome_2

- Side: outcome
- Dataset name as written: UK Biobank
- Candidate dictionary rows: UK Biobank

"""


def test_a_batch_has_the_format_of_the_batches_of_the_run():
    assert n.batch_text([PAPER], RECORDS, 24) == EXPECTED
    assert n.reference(RECORDS["p1"]) == "Author not recorded (2023). Other. "
    two = n.batch_text([PAPER, {"record_id": "p1", "rows": []}], RECORDS, 3)
    assert two.startswith("# Check 2, batch 3 of 3: 3 rows in 2 papers\n")
    assert two.index("## Paper p1") < two.index("## Paper p2")
