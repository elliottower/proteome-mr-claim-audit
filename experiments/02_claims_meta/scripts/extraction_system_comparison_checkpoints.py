# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Checkpoints inside the extraction-system comparison (AMENDMENT_03), and the check that its Sol
comparator is the originally registered analysis. Nothing that is computed changes.

scripts/extraction_system_comparison.py `comparison` builds the comparison in one call. Its body
is not copied or edited here. The work is done by two functions of that module: `compare` (the
agreement of two sources, with its pair bootstraps) and `h1_h2` (the H1, H2 and H2b tables of one
claim list). `checkpointed` replaces those two names, for the length of one block, by versions
that store each result as JSON when it is computed and return the stored result when one
exists for the same call: the same function on an input with the same fingerprint
(`sensitivity_checkpoints.fingerprint`, which does not depend on the order in which a set or
mapping is held). A stored result is keyed by its fingerprint, so a call made again, in any
order, takes the stored result.

`comparator_check` raises unless the rule label given is the originally registered analysis's and
the Sol registry and the Sol tables given to the comparison are that analysis's files named in
AMENDMENT_03, each by path and sha256; whatever file is passed, a registry or table of another
analysis, a changed file or a file in another role fails.
"""

import contextlib
import hashlib
import json
import pathlib
from collections.abc import Callable

import extraction_system_comparison
from sensitivity_checkpoints import fingerprint

NAMES = ("compare", "h1_h2")
COMPARATOR = {
    "rule_label": "originally_registered",
    "analysis": "originally registered analysis (the 27 pinned at their first occurrence, the 37 "
                "excluded), code table version a",
    "sol": {"path": "outputs/registry/2026-10-03_registered_with_27_coded_a/registry_claims.jsonl",
            "sha256": "faba35bd4cbe135f56761d2eec7d6ff92d446d1c6bef149615afda7f1f5de381"},
    "sol_tables": {"path": "outputs/stage5_biology/2026-10-03_registered_with_27_a/"
                           "sensitivity_tables.json",
                   "sha256": "42758a3ca1ef0993b6559762990f32bd0c1e39aa8892fe7595d036b43092908c"},
}


class ComparatorError(Exception):
    """A file given as the Sol comparator is not the originally registered analysis's."""


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def comparator_check(rule_label: str, sol_path: str, sol: bytes, tables_path: str,
                     tables: bytes) -> dict:
    """The rule label, the Sol registry and the Sol tables are all the originally registered
    analysis's."""
    if rule_label != COMPARATOR["rule_label"]:
        raise ComparatorError(f"rule label {rule_label!r} is not {COMPARATOR['rule_label']!r}")
    given = {"sol": (sol_path, sol), "sol_tables": (tables_path, tables)}
    for role, (path, content) in given.items():
        want = COMPARATOR[role]
        if pathlib.PurePosixPath(path).as_posix().removeprefix("./") != want["path"]:
            raise ComparatorError(f"{role}: {path} is not {want['path']}")
        if sha256(content) != want["sha256"]:
            raise ComparatorError(f"{role}: {path} does not have the sha256 of the originally "
                                  "registered analysis")
    return {"rule_label": rule_label,
            **{role: {"path": path, "sha256": sha256(content)}
               for role, (path, content) in given.items()}}


@contextlib.contextmanager
def checkpointed(store: pathlib.Path, commit: Callable[[], None] = lambda: None,
                 module=extraction_system_comparison):
    """Within the block, `compare` and `h1_h2` of `module` store and reuse their results under
    `store`. Yields the list of calls made: (name, fingerprint, `computed` or `stored`)."""
    store.mkdir(parents=True, exist_ok=True)
    originals = {name: getattr(module, name) for name in NAMES}
    calls: list[tuple[str, str, str]] = []

    def wrap(name: str):
        def call(*args, **kwargs):
            mark = fingerprint(name, args, kwargs)
            path = store / f"{name}_{mark}.json"
            if path.exists():
                calls.append((name, mark, "stored"))
                return json.loads(path.read_text())
            result = originals[name](*args, **kwargs)
            partial = path.with_suffix(".partial")
            partial.write_text(json.dumps(result))
            partial.rename(path)
            commit()
            calls.append((name, mark, "computed"))
            return json.loads(path.read_text())
        return call

    for name in NAMES:
        setattr(module, name, wrap(name))
    try:
        yield calls
    finally:
        for name, original in originals.items():
            setattr(module, name, original)
