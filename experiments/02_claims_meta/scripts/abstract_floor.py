"""The `no_abstract` rule. No dependency, so every script can import it.

A record is `no_abstract` when no source holds an abstract of at least ABSTRACT_FLOOR
characters for it; the length is counted after runs of whitespace are collapsed to one space
and the ends are stripped. Such a record states no abstract claim. It is classed before
eligibility screening and is never sent to GPT-6.1 Sol: it is counted in the funnel where it
arises (the search, each citation-chasing round), is never an eligible family, a chase seed or
a gate-audit positive, and joins a study family only as a linked record of a family that has a
record with an abstract.

The floor is a convention fixed on records first public before 2019 only
(docs/stage0_build/NO_ABSTRACT_FLOOR_2026-10-02.md): among the 313 such records held on
2026-10-02, 7 have no abstract in any source, 2 have a stub of 3 and 151 characters ("n/a"; a
truncated opening sentence of a software manual) and the other 304 have 408 characters or
more. 200 lies above both stubs and at about half the shortest abstract.
"""

ABSTRACT_FLOOR = 200


class NoAbstractError(Exception):
    """A record without an abstract reached a step that reads abstracts."""


def abstract_length(text: str | None) -> int:
    return len(" ".join((text or "").split()))


def is_no_abstract(text: str | None) -> bool:
    return abstract_length(text) < ABSTRACT_FLOOR


def refuse_no_abstract(records: list[dict], step: str, id_field: str = "pmid") -> None:
    """Raise when a record's abstract is below the floor. `records` are the rows a step is
    about to read (`pmid`/`record_id`, `abstract`)."""
    short = sorted(r[id_field] for r in records if is_no_abstract(r.get("abstract")))
    if short:
        raise NoAbstractError(
            f"{step}: {len(short)} record(s) with no abstract of {ABSTRACT_FLOOR} characters "
            f"or more ({short[:5]}); such records are classed no_abstract and are not read")
