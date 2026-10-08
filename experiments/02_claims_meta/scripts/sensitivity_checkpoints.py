# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Checkpoints inside the stage 5 sensitivity run (PREREG.md log, 2026-10-08), so that a run
stopped part-way resumes instead of starting again. Nothing that is computed changes.

scripts/sensitivity_analyses.py `run` builds every registered table in one call and returns
them together. Its body is not copied or edited here. The tables are built by three functions
of that module, each called once per table: `tables` (the indices and the resampling of one
registry), `recomputed` (the pair-family variant) and `h1_unclear_as_independent`. `checkpointed`
replaces those three names, for the length of one call of `run`, by versions that store each
result as JSON when it is computed and return the stored result when one exists. `run` then
executes as registered: the same assemblies, the same calls in the same order, the same seeds.

A stored result is taken only for the same call: the k-th call of the run, of the same
function, on an input with the same fingerprint (the sha256 of the call's registry or claims,
written so that the order in which a set or mapping is held does not enter, with the number of
resamples and the seed). A stored call that does not
fit raises; nothing is recomputed over it.

A result that is stored and read back has passed through JSON, as the whole result of the run
does when it is written. tests/test_sensitivity_checkpoints.py checks, on the synthetic study
of scripts/dry_run_biology_synthetic.py, that a checkpointed run, an interrupted and resumed
run, and the registered run give the same JSON.
"""

import contextlib
import hashlib
import json
import pathlib
from collections.abc import Callable

import sensitivity_analyses

NAMES = ("tables", "recomputed", "h1_unclear_as_independent")


class CheckpointError(Exception):
    """A stored call is not the call being made."""


def canonical(value):
    """A value as JSON-ready data that does not depend on the order in which a set or a
    mapping happens to be held (which differs from one process to the next)."""
    if hasattr(value, "model_dump"):
        return {"__model__": type(value).__name__, **canonical(value.model_dump(mode="python"))}
    if isinstance(value, dict):
        items = [(json.dumps(canonical(k), sort_keys=True), canonical(v))
                 for k, v in value.items()]
        return {"__dict__": sorted(items, key=lambda kv: kv[0])}
    if isinstance(value, (set, frozenset)):
        return {"__set__": sorted((canonical(v) for v in value),
                                  key=lambda v: json.dumps(v, sort_keys=True))}
    if isinstance(value, (list, tuple)):
        return [canonical(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return {"__repr__": repr(value)}


def fingerprint(name: str, args: tuple, kwargs: dict) -> str:
    return hashlib.sha256(json.dumps(canonical([name, list(args), kwargs]),
                                     sort_keys=True).encode()).hexdigest()


@contextlib.contextmanager
def checkpointed(store: pathlib.Path, commit: Callable[[], None] = lambda: None,
                 module=sensitivity_analyses):
    """Within the block, the three table builders of `module` store and reuse their results
    under `store`. Yields the list of calls made: (index, name, `computed` or `stored`)."""
    store.mkdir(parents=True, exist_ok=True)
    originals = {name: getattr(module, name) for name in NAMES}
    calls: list[tuple[int, str, str]] = []

    def wrap(name: str):
        def call(*args, **kwargs):
            index = len(calls)
            path = store / f"call_{index:03d}_{name}.json"
            mark = fingerprint(name, args, kwargs)
            others = [p for p in store.glob(f"call_{index:03d}_*.json") if p != path]
            if others:
                raise CheckpointError(f"call {index} is stored as {others[0].name}, not {name}")
            if path.exists():
                held = json.loads(path.read_text())
                if held["fingerprint"] != mark:
                    raise CheckpointError(f"{path.name} was stored for another input")
                calls.append((index, name, "stored"))
                return held["result"]
            result = originals[name](*args, **kwargs)
            partial = path.with_suffix(".partial")
            partial.write_text(json.dumps({"fingerprint": mark, "result": result}))
            partial.rename(path)
            commit()
            calls.append((index, name, "computed"))
            return json.loads(path.read_text())["result"]
        return call

    for name in NAMES:
        setattr(module, name, wrap(name))
    try:
        yield calls
    finally:
        for name, original in originals.items():
            setattr(module, name, original)
