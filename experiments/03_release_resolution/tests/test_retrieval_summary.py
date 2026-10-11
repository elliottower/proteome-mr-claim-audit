import retrieval_summary as sm


def test_the_summary_counts_routes_versions_and_reasons():
    results = [{"record_id": "a", "kind": "journal", "status": "retrieved",
                "versions": [{"version": "journal"}],
                "sources": [{"route": "R1", "version": "journal", "text": "t"},
                            {"route": "R2", "version": "journal", "type": "XLSX", "text": "u"},
                            {"route": "R2", "version": "journal", "type": "other", "text": None,
                             "reason": "type_not_accepted"}],
                "failures": []},
               {"record_id": "b", "kind": "preprint", "status": "no_source",
                "versions": [{"version": "preprint"}], "sources": [],
                "failures": [{"route": "R1", "reason": "no_file"},
                             {"route": "R3", "reason": "no_file"}]}]
    out = sm.summary(results)
    assert out["records_by_status"] == {"retrieved": 1, "no_source": 1}
    assert out["records_with_a_readable_source_by_route"] == {"R1": 1, "R2": 1}
    assert out["records_with_a_full_text"] == 1 and out["records_with_a_readable_supplement"] == 1
    assert out["supplement_files_by_type"] == {"XLSX": 1, "other": 1}
    assert out["unreadable_files_by_reason"] == {"type_not_accepted": 1}
    assert out["failures_by_route_and_reason"] == {"R1|no_file": 1, "R3|no_file": 1}
