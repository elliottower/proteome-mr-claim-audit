import json

import pytest

import span_omitted_token_kinds as k


@pytest.mark.parametrize("token,before,after,expected", [
    ("14", "the study [", "] showed", "digit/citation_marker"),
    ("3", "as reported (", ") in", "digit/citation_marker"),
    ("95", "a ", "% interval", "digit/signed_percent_or_unit"),
    ("0.85", "ratio =", " in", "digit/signed_percent_or_unit"),
    ("5e", "p <", "-8", "digit/signed_percent_or_unit"),
    ("10mg", "dose ", " daily", "digit/signed_percent_or_unit"),
    ("12,000", "in ", " people", "digit/bare_number"),
    ("2023", "in ", " we", "digit/bare_number"),
    ("β", "the ", " coefficient", "single_letter"),
    ("p", "at ", " below", "single_letter"),
    ("the", "of ", " risk", "word/article_or_determiner"),
    ("with", "associated ", " risk", "word/conjunction_or_preposition"),
    ("significantly", "was ", " lower", "word/intensifier_or_hedge"),
    ("plasma", "higher ", " levels", "word/other"),
])
def test_an_omitted_token_takes_the_first_class_that_applies(token, before, after, expected):
    assert k.kind(token, before, after) == expected


ABSTRACT = ("Background text comes first here. Higher protein X lowered risk of stroke in "
            "12,000 people (OR 0.90). Conclusions follow at the end of this abstract.")


def test_the_omission_of_one_span_is_described_without_its_text():
    span = "Higher protein X lowered risk of stroke in people (OR 0.90)."
    made = k.describe(span, ABSTRACT)
    assert made == {"class": "digit/bare_number", "tokens_omitted": 1, "gap_position": "middle",
                    "neighbour_holds_a_digit": False}
    beside = k.describe("Higher protein X lowered risk of stroke in 12,000 (OR 0.90).", ABSTRACT)
    assert (beside["class"], beside["neighbour_holds_a_digit"]) == ("word/other", True)
    assert "12" not in json.dumps(made)
    word = k.describe("Higher protein X lowered risk stroke in 12,000 people (OR 0.90).",
                      ABSTRACT)
    assert (word["class"], word["neighbour_holds_a_digit"]) == (
        "word/conjunction_or_preposition", False)


def test_several_tokens_left_out_or_a_whole_span_are_counted_apart():
    two = k.describe("Higher protein X lowered risk of stroke people (OR 0.90).", ABSTRACT)
    assert (two["class"], two["tokens_omitted"]) == ("not_one_token", 2)
    whole = k.describe("Higher protein X lowered risk of stroke", ABSTRACT)
    assert whole == {"class": "not_two_pieces_in_order"}


def test_the_gap_position_is_the_first_pieces_share_of_the_span():
    early = "Background text comes here. " + " ".join(f"w{i}" for i in range(40))
    late = " ".join(f"w{i}" for i in range(40)) + " and the very last end words here"
    assert k.describe(early.replace("comes here", "comes first here").replace(
        "first ", ""), early.replace("comes here", "comes first here"))["gap_position"] == (
        "first_tenth")
    span = late.replace(" last", "")
    assert k.describe(span, late)["gap_position"] == "last_tenth"
