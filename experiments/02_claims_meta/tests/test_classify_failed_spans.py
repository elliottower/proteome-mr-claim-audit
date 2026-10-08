import pytest

import classify_failed_spans as c

ABSTRACT = ("Background: plasma proteins matter. We found that higher IL6R lowered risk of "
            "coronary disease (OR 0.90, 95% CI 0.85–0.95). Higher PCSK9 raised LDL "
            "cholesterol in 12,000 people. We found that higher IL6R lowered risk of coronary "
            "disease (OR 0.90, 95% CI 0.85–0.95). Conclusions: several targets were supported "
            "by the genetic evidence and merit follow-up in trials of adequate size.")
ONCE = "Higher PCSK9 raised LDL cholesterol in 12,000 people."
TWICE = "We found that higher IL6R lowered risk of coronary disease (OR 0.90, 95% CI 0.85–0.95)."


def cls(span, abstract=ABSTRACT, title="", request="", pin="not found"):
    return c.classify(span, abstract, title, request, pin)


def test_a_span_in_the_abstract_twice_is_the_pins_failure_not_the_models():
    made = cls(TWICE.upper(), pin="ambiguous")
    assert made == {"class": "in_abstract_more_than_once", "occurrences": 2, "pin": "ambiguous"}
    assert cls(ONCE, pin="error")["class"] == "in_abstract_pin_refused"


@pytest.mark.parametrize("span,expected", [
    (TWICE.replace("–", "-"), "after_unicode_normalisation"),
    (ONCE.replace("LDL cholesterol", "LDL­cholesterol").replace(" in ", "​ in "),
     "after_unicode_normalisation"),
    (ONCE.replace("LDL", "<i>LDL</i>").replace("12,000", "12,000&nbsp;"),
     "after_removing_markup"),
    ("Higher PCSK9 raised LDL cholesterol ... several targets were supported",
     "joined_with_an_ellipsis"),
    ("Higher PCSK9 raised LDL cholesterol several targets were supported by the genetic "
     "evidence", "pieces_joined"),
    ("Higher PCSK9 raised LDL cholesterol in 12,500 people.", "near_match"),
    ("Higher PCSK9 strongly raised LDL cholesterol in 12,000 people.", "near_match"),
    ("Sortilin was associated with an entirely different outcome in another cohort of men.",
     "no_close_counterpart"),
])
def test_each_kind_of_failure_takes_its_class(span, expected):
    assert cls(span)["class"] == expected


def test_a_changed_number_is_marked_and_a_changed_word_is_not():
    number = cls("Higher PCSK9 raised LDL cholesterol in 12,500 people.")
    word = cls("Higher PCSK9 strongly raised LDL cholesterol in 12,000 people.")
    assert (number["digit_differs"], word["digit_differs"]) == (True, False)
    assert number["tokens_changed"] <= c.NEAR and word["tokens_changed"] == 1


def test_pieces_keep_or_lose_the_abstracts_order():
    forward = cls("Higher PCSK9 raised LDL cholesterol several targets were supported by the "
                  "genetic evidence")
    back = cls("several targets were supported by the genetic evidence Higher PCSK9 raised "
               "LDL cholesterol")
    assert (forward["pieces"], forward["pieces_in_order"]) == (2, True)
    assert back["class"] == "pieces_joined" and back["pieces_in_order"] is False


def test_title_request_and_stub_classes():
    title = "Proteome-wide Mendelian randomization of 2,000 plasma proteins"
    assert cls(title, title=title)["class"] == "in_title_only"
    sent = "Title. A sentence only the request holds about apolipoprotein B and stroke risk."
    assert cls("A sentence only the request holds about apolipoprotein B and stroke risk.",
               request=sent)["class"] == "in_request_not_in_abstract"
    assert cls("Something else entirely here now.", abstract="Short stub.")["class"] == (
        "abstract_empty_or_stub")


def test_the_registered_folding_is_white_space_and_case_only():
    assert c.registered("  Two   WORDS\n") == "two words"
    assert c.registered("0.85–0.95") != c.registered("0.85-0.95")
    assert c.normalised("0.85–0.95") == c.normalised("0.85-0.95")
