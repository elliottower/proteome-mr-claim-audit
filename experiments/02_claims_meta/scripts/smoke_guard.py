"""Guards of the pre-freeze smoke window (scripts/assemble_registry.py `--smoke-label`). No
registered run uses a smoke label. Standard library only, so the Modal wrappers import it on
the laptop.

A smoke run is made before the freeze on records first public before 2019. Its registry treats
those families as inside the window so that stages 4b to 6 run with content. The guards keep
such a registry and everything built from it under names that start with its label:

    label       `smoke_` followed by letters, digits and underscores
    registry    written to outputs/registry/<label>... only; registry_assembly.json carries
                `smoke_label`
    results     a run name or output folder for the results of a smoke registry starts with
                its label; a registry of the registered run never takes a smoke name
"""

import json
import pathlib

SMOKE_PREFIX = "smoke_"
REGISTRY_ROOT = pathlib.Path(__file__).resolve().parent.parent / "outputs" / "registry"


class SmokeWindowError(Exception):
    """A smoke registry holds a record of the registered window, has a label that is not a
    smoke label, or would be written (or its results would be) outside its smoke folders."""


def check_smoke_label(label: str) -> None:
    if not label.startswith(SMOKE_PREFIX) or not label.replace("_", "").isalnum():
        raise SmokeWindowError(f"{label!r} is not a smoke label ({SMOKE_PREFIX}<letters, "
                               f"digits, underscores>)")


def check_smoke_folder(label: str, out: pathlib.Path) -> None:
    """A smoke registry is written to outputs/registry/<label>... and nowhere else."""
    check_smoke_label(label)
    out = out.resolve()
    if out.parent != REGISTRY_ROOT or not out.name.startswith(label):
        raise SmokeWindowError(f"a smoke registry is written under {REGISTRY_ROOT}/{label}..., "
                               f"not {out}")


def smoke_label_of(registry_dir: pathlib.Path) -> str | None:
    """The smoke label of an assembled registry, or None for a registry of the registered run."""
    return json.loads((registry_dir / "registry_assembly.json").read_text()).get("smoke_label")


def check_smoke_output(registry_dir: pathlib.Path, name: str) -> None:
    """The results of a smoke registry go under a run name or folder that starts with its
    label; the results of any other registry never go under a smoke name."""
    label = smoke_label_of(registry_dir)
    if label is not None and not name.startswith(label):
        raise SmokeWindowError(f"{registry_dir} is a smoke registry ({label}); its results "
                               f"cannot be written as {name!r}")
    if label is None and name.startswith(SMOKE_PREFIX):
        raise SmokeWindowError(f"{registry_dir} is not a smoke registry; {name!r} is a smoke "
                               f"name")


def check_run_name(run_name: str, smoke_label: str) -> None:
    """A run made with the smoke switch has a run name that starts with its label, and a smoke
    run name is used only with the switch."""
    if smoke_label:
        check_smoke_label(smoke_label)
    if bool(smoke_label) != run_name.startswith(SMOKE_PREFIX) or not run_name.startswith(
            smoke_label):
        raise SmokeWindowError(f"run name {run_name!r} and smoke label {smoke_label!r} do not "
                               f"agree")
