import difflib
import hashlib
import pathlib

import pytest

import build_coding_prompt_v3 as b

HERE = pathlib.Path(__file__).resolve().parents[1]
PREREG = (HERE / "PREREG.md").read_bytes()
V2 = (HERE.parent / "03_release_resolution/prompts/coding_prompt_v2.md").read_bytes()
V3_PATH = HERE / "prompts" / "coding_prompt_v3.md"
FROZEN_QUOTE = """\
- A citation identifies a release only when the passage explicitly attributes the analysed
  dataset to it and its identifier is the source identifier of exactly one dictionary row. The
  identifier is the DOI, else the PMID, else the PMC identifier of the reference entry the
  passage cites, when that entry resolves to one bibliographic record; or a DOI or PMID written
  in the paper's own text (a table cell, a data-availability or key-resources statement) and
  attributed there to the analysed dataset. If the cited source has several dictionary rows, the
  citation identifies one of them only with an attribute of the same analysed dataset in the
  same passage that matches exactly one (ancestry, subcohort, panel, platform), with no conflict.
  A citation of a general cohort description identifies no release. Give the reference entry,
  when there is one, as a second passage with rule `D2_reference_entry`; an identifier written
  in the text is quoted in the D2 passage itself."""


def test_the_inputs_are_the_frozen_bytes():
    assert hashlib.sha256(PREREG).hexdigest() == b.FROZEN_PREREG
    assert hashlib.sha256(V2).hexdigest() == b.SEALED_V2


def test_the_only_change_is_the_one_bullet_and_it_equals_the_frozen_quote():
    v2, v3 = V2.decode().split("\n"), b.build(PREREG.decode(), V2.decode()).split("\n")
    i, j = b.bullet_span(v2)
    assert v2[i].startswith(b.START) and v2[j - 1].rstrip().endswith(b.END)
    blocks = [m for m in difflib.SequenceMatcher(a=v2, b=v3, autojunk=False).get_opcodes()
              if m[0] != "equal"]
    assert blocks and all(i <= a1 and a2 <= j for _, a1, a2, _, _ in blocks)
    assert v3 == v2[:i] + FROZEN_QUOTE.split("\n") + v2[j:]


def test_the_quote_is_read_from_the_frozen_text_with_the_prefix_removed():
    assert "\n".join(b.quoted_bullet(PREREG.decode())) == FROZEN_QUOTE
    assert FROZEN_QUOTE in "\n".join(line[2:] for line in PREREG.decode().split("\n")
                                     if line.startswith("> "))


def test_the_written_file_is_the_build():
    assert V3_PATH.read_text() == b.build(PREREG.decode(), V2.decode())


def test_a_missing_or_doubled_bullet_is_refused():
    with pytest.raises(b.PromptError):
        b.build(PREREG.decode(), "no bullet here\n")
    doubled = V2.decode() + "\n" + V2.decode()
    with pytest.raises(b.PromptError):
        b.build(PREREG.decode(), doubled)
