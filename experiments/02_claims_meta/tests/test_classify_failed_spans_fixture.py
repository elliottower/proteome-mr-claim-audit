import classify_failed_spans as c
from test_classify_failed_spans import ONCE, cls

SOFT_HYPHEN, ZERO_WIDTH = chr(0xAD), chr(0x200B)


def test_a_soft_hyphen_inside_a_word_and_a_zero_width_space_are_normalised_away():
    span = ONCE.replace("cholesterol", f"choles{SOFT_HYPHEN}terol").replace(
        " in ", f"{ZERO_WIDTH} in ")
    assert span != ONCE and c.registered(span) != c.registered(ONCE)
    assert cls(span)["class"] == "after_unicode_normalisation"


def test_a_soft_hyphen_in_place_of_a_space_joins_two_words_and_is_a_near_match():
    span = ONCE.replace("LDL cholesterol", f"LDL{SOFT_HYPHEN}cholesterol")
    assert c.normalised(span) == c.normalised(ONCE.replace("LDL cholesterol", "LDLcholesterol"))
    assert cls(span)["class"] == "near_match"
