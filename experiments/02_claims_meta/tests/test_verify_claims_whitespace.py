import pathlib

import pytest

import verify_claims as sealed
import verify_claims_whitespace as corrected

SCRIPTS = pathlib.Path(sealed.__file__).resolve().parent
NON_ASCII_SPACES = [" ", " ", " "]
ORDINARY_SPANS = [
    "Higher protein X was associated with coronary disease, OR 1.15 (1.08-1.22; P = 2.0 × 10-6).",
    "Genetically predicted protein Y lowered risk (OR 0.86 [95% CI 0.79-0.94], p=0.001).",
    "estimate -0.19, p=6.46×10-03 for body mass index.",
    "beta = − 0.19 (− 0.30 to − 0.08), P = 3 x 10 (− 4)",
    "9·45%, 95% CI 8·34-10·57 for the outcome; P<5e-8",
    "No estimate is printed in this sentence.",
]


def exponent_span(space):
    return f"OR 1.15 (1.08-1.22; P = 2.0 × 10−{space}6)"


def signed_span(space):
    return f"beta = −{space}0.19 (−{space}0.30 to −{space}0.08)"


@pytest.mark.parametrize("space", NON_ASCII_SPACES)
def test_the_sealed_verifier_raises_on_a_non_ascii_space_in_an_exponent(space):
    with pytest.raises(ValueError):
        sealed.find_estimates(exponent_span(space))


@pytest.mark.parametrize("space", NON_ASCII_SPACES)
def test_the_sealed_verifier_raises_on_a_non_ascii_space_after_a_sign(space):
    with pytest.raises(ValueError):
        sealed.find_estimates(signed_span(space))


@pytest.mark.parametrize("space", [" ", *NON_ASCII_SPACES])
def test_the_corrected_copy_reads_the_exponent(space):
    (estimate,) = corrected.find_estimates(exponent_span(space))
    assert estimate.est == pytest.approx(1.15)
    assert (estimate.lo, estimate.hi) == (pytest.approx(1.08), pytest.approx(1.22))
    assert estimate.p == pytest.approx(2.0e-6)
    assert estimate.p_op == "="


@pytest.mark.parametrize("space", [" ", *NON_ASCII_SPACES])
def test_the_corrected_copy_reads_a_signed_number(space):
    (estimate,) = corrected.find_estimates(signed_span(space))
    assert estimate.est == pytest.approx(-0.19)
    assert (estimate.lo, estimate.hi) == (pytest.approx(-0.30), pytest.approx(-0.08))


@pytest.mark.parametrize("space", NON_ASCII_SPACES)
def test_to_float_strips_each_space_the_pattern_admits(space):
    assert corrected.to_float(f"−{space}0·5") == pytest.approx(-0.5)
    with pytest.raises(ValueError):
        sealed.to_float(f"−{space}0·5")


@pytest.mark.parametrize("span", ORDINARY_SPANS)
def test_both_read_the_same_estimates_where_the_sealed_one_does_not_raise(span):
    assert ([e.model_dump() for e in corrected.find_estimates(span)]
            == [e.model_dump() for e in sealed.find_estimates(span)])
    assert (corrected.parse_direction(span, "the outcome")
            == sealed.parse_direction(span, "the outcome"))


def test_the_copy_differs_from_the_sealed_script_in_the_two_conversions_only():
    text = (SCRIPTS / "verify_claims_whitespace.py").read_text()
    start = text.index("# Corrected copy of verify_claims.py")
    end = text.index("def to_float(num: str) -> float:")
    undone = (text[:start] + text[end:]).replace(
        'float(WHITE_SPACE.sub("", num.replace("·", ".").replace("−", "-")))',
        'float(num.replace("·", ".").replace("−", "-").replace(" ", ""))').replace(
        'int(WHITE_SPACE.sub("", exp.replace("−", "-")))',
        'int(exp.replace("−", "-").replace(" ", ""))')
    assert undone == (SCRIPTS / "verify_claims.py").read_text()
    assert "WHITE_SPACE" not in undone


def test_the_compact_folding_is_the_same_function_body():
    names = ["Interleukin-6 receptor α", "C-reactive protein", "β-2 microglobulin", "naïve T cell"]
    assert [corrected.compact(n) for n in names] == [sealed.compact(n) for n in names]
