import calibrate_dedup_v2 as cd2


def variant(chars, a1):
    return {"characters": chars, "a1_kept": a1, "a2_kept": 3, "b_kept": 4, "c_kept": 5}


def test_a_paper_without_supplement_files_counts_zero_and_others_pool():
    f = {"characters_whole": 100, "frozen_cut": True,
         "whole": {"a1": 2, "a2": 3, "b": 4, "c": 5},
         "variants": {"k1_all": variant(10, 1), "frozen": variant(60, 2)}}
    out = cd2.aggregate({"p": [f], "q": []})
    assert out["k1_all"]["per_paper"]["q"]["characters_read"] == 0
    assert out["k1_all"]["retention"]["a1"] == 0.5 and out["k1_all"]["papers_losing_a1"] == ["p"]
    assert out["frozen"]["papers_losing_a1"] == []
    assert out["k1_all"]["cuts"]["q"] == {"files": []}
