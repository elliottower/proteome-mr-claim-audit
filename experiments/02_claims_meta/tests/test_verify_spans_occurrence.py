import pathlib
import subprocess

import pytest

import verify_spans as sealed
import verify_spans_occurrence as spans

SCRIPTS = pathlib.Path(sealed.__file__).resolve().parent


def pinner(plain, with_occurrence="found"):
    calls = []

    def pin_with(claims_file, claim_id, span, env, occurrence=None):
        calls.append(occurrence)
        return (with_occurrence if occurrence else plain), []
    return pin_with, calls


@pytest.mark.parametrize("plain,registered,expected,calls", [
    ("found", True, ("found", "plain"), [None]),
    ("found", False, ("found", "plain"), [None]),
    ("not found", False, ("not found", "plain"), [None]),
    ("not found", True, ("not found", "plain"), [None]),
    ("ambiguous", True, ("found", "occurrence_1"), [None, 1]),
    ("ambiguous", False, ("ambiguous", "plain"), [None]),
])
def test_the_first_occurrence_is_pinned_only_for_a_registered_span_refused_as_ambiguous(
        plain, registered, expected, calls):
    pin_with, made = pinner(plain)
    state, _, method = spans.pin_span("claims.yaml", "c000", "a span", registered, {}, pin_with)
    assert (state, method) == expected and made == calls


def test_an_occurrence_pin_that_is_refused_keeps_its_refusal():
    pin_with, _ = pinner("ambiguous", "not found")
    assert spans.pin_span("c.yaml", "c000", "s", True, {}, pin_with)[::2] == (
        "not found", "occurrence_1")


def test_the_commit_is_read_from_the_install_record_and_an_editable_install_has_none():
    assert spans.commit_of({"version": "0.4.3", "direct_url": {
        "url": "https://example.org/r", "vcs_info": {"vcs": "git", "commit_id": "a" * 40},
        "subdirectory": "packages/citations"}}) == "a" * 40
    assert spans.commit_of({"version": "0.4.2", "direct_url": {
        "url": "file:///somewhere", "dir_info": {"editable": True}}}) is None
    assert spans.commit_of({"version": "0.4.2", "direct_url": None}) is None


def test_the_installed_build_is_asked_of_the_tools_own_interpreter(tmp_path, monkeypatch):
    exe = tmp_path / "citations"
    exe.write_text("#!/opt/tool/bin/python\nimport citations\n")
    monkeypatch.setattr(spans.shutil, "which", lambda name: str(exe))
    seen = []

    def run(argv, **kwargs):
        seen.append(argv)
        return subprocess.CompletedProcess(argv, 0, '{"version": "9", "direct_url": null}', "")
    assert spans.installed_citations(run) == {"version": "9", "direct_url": None}
    assert seen[0][0] == "/opt/tool/bin/python" and seen[0][1] == "-c"
    monkeypatch.setattr(spans.shutil, "which", lambda name: None)
    with pytest.raises(spans.SpanCheckError):
        spans.installed_citations(run)


def test_the_registered_folding_and_the_pass_condition_are_the_sealed_scripts():
    for text in ("  Two   WORDS\n", "0.85–0.95", "Naïve β-cell"):
        assert spans.fold(text) == sealed.fold(text)
    new = (SCRIPTS / "verify_spans_occurrence.py").read_text()
    old = (SCRIPTS / "verify_spans.py").read_text()
    for kept in ("def fold(text: str) -> str:\n    return \" \".join(text.split()).casefold()",
                 "passes=registered and state == \"found\"",
                 "registered = fold(span) in abstract_folded",
                 "abstract_folded = fold(rec[a.text_field])"):
        assert kept in new and kept in old
    assert "outputs\" / \"citations\" / run" not in new
    assert "outputs\" / \"verification\" / run" not in new
    assert new.count("occurrence=1") == 1
