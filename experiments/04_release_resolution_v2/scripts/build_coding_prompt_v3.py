# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Coding prompt v3 of the second release-resolution registration (PREREG.md, §Study design,
item 2), built mechanically. No model is called.

v3 is the first registration's prompts/coding_prompt_v2.md (sealed) with one bullet replaced:
the bullet that begins "- A citation identifies a release only when" and ends "Give the reference
entry as a second passage." becomes the bullet PREREG.md quotes in full after "is v2 with that
bullet replaced by:", taken from the frozen PREREG.md bytes (sha256 FROZEN_PREREG), each line with
its "> " blockquote prefix removed, which leaves v2's indentation (a "- " first line and
two-space continuation lines). PREREG.md states that nothing else in the prompt changes.

Usage, from experiments/04_release_resolution_v2:
    uv run --no-project python scripts/build_coding_prompt_v3.py
"""

import hashlib
import pathlib

FROZEN_PREREG = "555ec9a9ddb628e55fd3642a0282a9b5b75702646968092f98dfd8b74c4ba62c"
SEALED_V2 = "6b10c93ff232c6b1f763ef67cd1e03a7c8356585c59abea902004744c0615736"
START = "- A citation identifies a release only when"
END = "Give the reference entry as a second passage."
INTRO = "is v2 with that bullet replaced by:"
PREREG = pathlib.Path("PREREG.md")
V2 = pathlib.Path("../03_release_resolution/prompts/coding_prompt_v2.md")
V3 = pathlib.Path("prompts/coding_prompt_v3.md")


class PromptError(Exception):
    """An input differs from its frozen bytes, or the bullet is not found exactly once."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def quoted_bullet(prereg: str) -> list[str]:
    lines = prereg.split("\n")
    starts = [i for i, line in enumerate(lines) if line.rstrip().endswith(INTRO)]
    if len(starts) != 1:
        raise PromptError("the sentence introducing the replacement is not found exactly once")
    i = starts[0] + 1
    while i < len(lines) and not lines[i].startswith(">"):
        i += 1
    out = []
    while i < len(lines) and lines[i].startswith(">"):
        out.append(lines[i][2:] if lines[i].startswith("> ") else lines[i][1:])
        i += 1
    if not out or not out[0].startswith(START):
        raise PromptError("the quoted replacement does not begin with the bullet's start")
    return out


def bullet_span(v2: list[str]) -> tuple[int, int]:
    starts = [i for i, line in enumerate(v2) if line.startswith(START)]
    if len(starts) != 1:
        raise PromptError("the v2 bullet is not found exactly once")
    i = starts[0]
    j = i
    while not v2[j].rstrip().endswith(END):
        j += 1
        if j == len(v2) or (v2[j].startswith("- ") and j > i):
            raise PromptError("the v2 bullet does not end as expected")
    return i, j + 1


def build(prereg: str, v2: str) -> str:
    lines = v2.split("\n")
    i, j = bullet_span(lines)
    return "\n".join(lines[:i] + quoted_bullet(prereg) + lines[j:])


def main() -> None:
    prereg, v2 = PREREG.read_bytes(), V2.read_bytes()
    if sha256(prereg) != FROZEN_PREREG or sha256(v2) != SEALED_V2:
        raise PromptError("PREREG.md or coding_prompt_v2.md differs from its frozen bytes")
    if V3.exists():
        raise FileExistsError(f"{V3} exists; it is written once")
    V3.parent.mkdir(parents=True, exist_ok=True)
    V3.write_bytes(build(prereg.decode(), v2.decode()).encode())
    print(f"{V3} sha256 {sha256(V3.read_bytes())}")


if __name__ == "__main__":
    main()
