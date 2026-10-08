import subprocess

import pytest
import yaml

import pin_passage_occurrence as first
import pin_passage_occurrence_v2 as helper

S = "We used data from release R9 of the study."
BLOCK = f"Some intro text. {S} Final words here."
UNIQUE = f"## Methods\nAlpha. {S} Omega.\n## Data\nBeta. {S} Gamma."
DUPLICATED = f"## Methods\nLead in one. {BLOCK}\n## Data availability\nLead in two. {BLOCK}\nEnd."
TABLE = f"## Results\n[Table 1. Sources] Trait: A | Source: X\n{S}\nMiddle text.\n{S}\nLast."


def fake(source):
    """A stand-in for the tool: `pin` is ambiguous when the quote occurs more than once;
    `verify` passes when prefix, quote and suffix joined occur exactly once."""
    doc = " ".join(source.split())

    def run(args, cwd):
        if args[0] == "pin":
            n = doc.count(args[-1])
            return subprocess.CompletedProcess(args, 0 if n == 1 else 1,
                                               "found" if n == 1 else "ambiguous  ...", "")
        held = yaml.safe_load(next((cwd / "claims").glob("*.yaml")).read_text())["claims"]
        q = next(iter(held.values()))["quotes"][0]
        joined = " ".join(x for x in (q.get("prefix"), q["exact"], q.get("suffix")) if x)
        return subprocess.CompletedProcess(args, 0 if doc.count(joined) == 1 else 1, "report", "")
    return run


def folder(tmp_path, source):
    (tmp_path / "claims").mkdir()
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources" / "x.txt").write_text(source)
    (tmp_path / "claims" / "x.yaml").write_text(yaml.safe_dump(
        {"source": {"citation": "x", "local": "sources/x.txt", "sha256": "0"}, "claims": {}},
        sort_keys=False))
    return tmp_path


def passage(sentences, line, read="full_text"):
    return {"passage_id": "p001", "sentences": sentences, "claims_file": "claims/x.yaml",
            "line": line, "source_read": read}


def held(root):
    return yaml.safe_load((root / "claims" / "x.yaml").read_text())["claims"]


def test_where_the_first_helper_pins_this_one_writes_the_same_record(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    p = passage(["Beta.", S, "Gamma."], 3)
    states = [m.pin(p, 2, "o_1", folder(tmp_path / d, UNIQUE), fake(UNIQUE))
              for m, d in ((first, "a"), (helper, "b"))]
    assert states == ["pinned_with_prefix_and_suffix"] * 2
    assert held(tmp_path / "a") == held(tmp_path / "b") == {"o_1": {"quotes": [
        {"exact": S, "prefix": "Beta.", "suffix": "Gamma."}]}}
    single = passage(["Alpha."], 1)
    assert helper.pin(single, 1, "o_2", tmp_path / "b", fake(UNIQUE)) == "pinned"


def test_duplicated_neighbours_are_passed_by_widening_through_the_source(tmp_path):
    root = folder(tmp_path, DUPLICATED)
    second = passage(["Some intro text.", S, "Final words here."], 3)
    with pytest.raises(first.PinError):
        first.pin(second, 2, "o_1", root, fake(DUPLICATED))
    assert helper.pin(second, 2, "o_1", root, fake(DUPLICATED)) == (
        "pinned_with_source_text_either_side")
    q = held(root)["o_1"]["quotes"][0]
    assert q["exact"] == S and q["prefix"].endswith("Lead in two. Some intro text.")
    assert q["suffix"].startswith("Final words here. End.")
    earlier = passage(["Some intro text.", S, "Final words here."], 1)
    assert helper.pin(earlier, 2, "o_2", root, fake(DUPLICATED)) == (
        "pinned_with_source_text_either_side")
    q = held(root)["o_2"]["quotes"][0]
    assert q["prefix"] == "## Methods Lead in one. Some intro text."
    assert "## Data availability" in q["suffix"]


def test_a_line_standing_alone_is_pinned_from_the_lines_around_it(tmp_path):
    root = folder(tmp_path, TABLE)
    assert helper.pin(passage([S], 4), 1, "o_1", root, fake(TABLE)) == (
        "pinned_with_source_text_either_side")
    q = held(root)["o_1"]["quotes"][0]
    assert q["prefix"].endswith("Middle text.") and q["suffix"] == "Last."
    assert helper.pin(passage([S], 2), 1, "o_2", root, fake(TABLE)) == (
        "pinned_with_source_text_either_side")
    assert held(root)["o_2"]["quotes"][0]["suffix"].startswith("Middle text.")


def test_an_abstract_passage_is_found_in_the_abstract_as_a_whole(tmp_path):
    abstract = f"Background.\n{S} Results follow. Then again: {S} Conclusions."
    root = folder(tmp_path, abstract)
    p = passage(["Then again: " + S, "Conclusions."], 0, "abstract")
    before, after = helper.around(p, 1, abstract)
    assert before == f"Background. {S} Results follow." and after == "Conclusions."


def test_widening_doubles_and_ends_with_all_the_text():
    before, after = "a " * 300, "b " * 50
    pairs = list(helper.widening(before.strip(), after.strip(), 80))
    assert [len(p) <= 80 * 2 ** i for i, (p, _) in enumerate(pairs)] == [True] * len(pairs)
    assert pairs[-1] == (before.strip(), after.strip()) and len(pairs) == 4
    assert all(not p.startswith(" ") and not s.endswith(" ") for p, s in pairs)


def test_nothing_is_written_when_the_tool_never_confirms_or_the_passage_is_not_there(tmp_path):
    root = folder(tmp_path, DUPLICATED)

    def never(args, cwd):
        return subprocess.CompletedProcess(args, 1, "ambiguous  ...", "")
    with pytest.raises(helper.PinError):
        helper.pin(passage(["Some intro text.", S, "Final words here."], 3), 2, "o_1", root,
                   never)
    with pytest.raises(helper.PinError):
        helper.pin(passage(["Not in the source.", S], 3), 2, "o_1", root, fake(DUPLICATED))
    assert held(root) == {}
