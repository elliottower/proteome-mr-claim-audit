"""OSF dry run: build the draft body from PREREG.md. Sends nothing."""
import json
from pathlib import Path

from prereg import osf

PREREG = Path("PREREG.md")

try:
    draft = osf.build_draft(PREREG.read_text())
except Exception as exc:  # the refusal text is the output
    print("REFUSED:", type(exc).__name__)
    print(exc)
else:
    print("ACCEPTED")
    print(json.dumps({k: (v[:80] if isinstance(v, str) else v) for k, v in draft.items()}, indent=1, default=str)[:6000])
