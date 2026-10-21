import accepted_v1 as ac
import judges_stage_a_v1 as js

A, B = js.MODELS


def row(rid, releases=(), state="explicit", reasons=()):
    return {"row_id": rid, "identified_releases": list(releases),
            "roles": [{"release": r, "role": "primary"} for r in releases],
            "ancestry": [], "attribution_state": state, "unresolved_reasons": list(reasons),
            "decisive_evidence": [], "attribution_passage": None}


def test_each_source_of_an_accepted_code():
    order = ["s", "g", "g0", "j", "u", "n", "f"]
    answers = {A: {"s": row("s"), "g": row("g", ["R10"]), "g0": row("g0", ["R10"]),
                   "j": row("j", ["R9"]), "u": row("u", ["R8"]), "n": row("n", ["R7"]),
                   "f": row("f", ["R6"])},
               B: {"s": row("s"), "g": row("g", ["R10"]), "g0": row("g0", ["R10"]),
                   "j": row("j"), "u": row("u"), "n": row("n"), "f": row("f")}}
    gates = {A: {"s": True, "g": False, "g0": False, "j": True, "u": True, "n": True, "f": False},
             B: {"s": True, "g": True, "g0": False, "j": True, "u": True, "n": True, "f": True}}
    first = {r: js.blinded(r)[0] for r in ("j", "u", "f")}
    pick = {r: "answer_1" if first[r] == A else "answer_2" for r in first}
    got = ac.assemble(order, answers, gates, {"s": {"identified_releases": [], "row_id": "s"}},
                      {"j": pick["j"]}, {"u": pick["u"], "n": "neither", "f": pick["f"]})
    assert got["s"]["source"] == "settled" and got["s"]["accepted"]
    assert got["g"]["accepted"] and got["g"]["coder"] == B
    assert not got["g0"]["accepted"]
    assert got["j"]["source"] == "judges" and got["j"]["code"]["identified_releases"] == ["R9"]
    assert got["u"]["source"] == "author" and got["u"]["coder"] == A
    assert not got["n"]["accepted"]
    assert not got["f"]["accepted"]


def test_c1_counts_recovery_over_every_drawn_control_with_the_thresholds():
    accepted = {f"c{i}": {"accepted": True, "coder": A,
                          "code": {"identified_releases": ["R10"]}} for i in range(46)}
    accepted |= {"x1": {"accepted": True, "coder": A, "code": {"identified_releases": ["R9"]}},
                 "x2": {"accepted": False, "coder": None, "code": None},
                 "x3": {"accepted": True, "coder": A, "code": {"identified_releases": ["R8"]}},
                 "x4": {"accepted": True, "coder": A, "code": {"identified_releases": ["R10"]}}}
    expected = {r: "R10" for r in accepted}
    kinds = {r: "release" for r in accepted} | {"x4": "source_identifier"}
    bases = {A: {"x4": {"R10": "D2:inline:pmid"}}}
    got = ac.c1(accepted, expected, kinds, bases)
    o = got["overall"]
    assert (o["controls"], o["recovered"], o["contradicted"]) == (50, 47, 2)
    assert o["recovery"] == 47 / 50 and o["contradiction"] == 2 / 50
    assert got["verdict"] == "fail"
    assert got["by_identifier_type"]["source_identifier"]["recovered"] == 1
    assert got["recovered_through_the_inline_d2_rule"] == 1
    assert got["per_control"]["x2"] == "not_accepted" and got["per_control"]["x3"] == "contradicted"


def test_c1_passes_at_the_thresholds_and_needs_fifty_controls():
    accepted = {f"c{i}": {"accepted": True, "coder": A, "code": {"identified_releases": ["R"]}}
                for i in range(45)} | {f"e{i}": {"accepted": False, "coder": None, "code": None}
                                       for i in range(5)}
    expected = {r: "R" for r in accepted}
    kinds = {r: "accession" for r in accepted}
    assert ac.c1(accepted, expected, kinds, {})["verdict"] == "pass"
    small = {k: v for k, v in list(accepted.items())[:49]}
    assert ac.c1(small, {r: "R" for r in small}, {r: "accession" for r in small},
                 {})["verdict"] == "fail"
