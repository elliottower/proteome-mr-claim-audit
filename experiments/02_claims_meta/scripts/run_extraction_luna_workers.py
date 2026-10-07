# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "pydantic==2.13.5"]
# ///
"""Run run_extraction_luna.py with another number of simultaneous workers.

`run_extraction_luna.py` (sealed) sends its requests through a pool of `run_extraction.WORKERS`
workers, a constant of six. This script sets that number from the environment variable
LUNA_WORKERS (default 16) and calls the Luna runner's own `main` with the command line it was
given. Prompt, schema, request, cache, re-run rule and outputs are the Luna runner's; the
number of simultaneous requests is the only difference.

Usage:
    LUNA_WORKERS=32 uv run scripts/run_extraction_luna_workers.py --abstracts <...> \
        --sol-extraction <...> --label <label> --run 1
"""

import os

import run_extraction as rx
import run_extraction_luna as luna

DEFAULT_WORKERS = 16
MAX_WORKERS = 64


class WorkersError(Exception):
    """LUNA_WORKERS is not a usable number."""


def workers_from_environment() -> int:
    n = int(os.environ.get("LUNA_WORKERS", DEFAULT_WORKERS))
    if not 1 <= n <= MAX_WORKERS:
        raise WorkersError(f"LUNA_WORKERS must be between 1 and {MAX_WORKERS}")
    return n


def main() -> None:
    rx.WORKERS = workers_from_environment()
    luna.main()


if __name__ == "__main__":
    main()
