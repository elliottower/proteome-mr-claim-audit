"""Freeze EpiGraphDB's pQTL MR resource (Zheng et al. 2020) as local files.

The resource has no bulk download; its data-availability statement points to the API.
For every exposure in /pqtl/list/?flag=exposures this writes the /pqtl/ response for
rtype=mrres and rtype=simple with pvalue=1 (the API filters r.pvalue < 1.0) to one JSON
file per protein and request type. Existing files are skipped, so a rerun resumes.
A manifest with the sha256 of every file is written at the end.
"""

import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.epigraphdb.org"
OUT = Path(__file__).resolve().parents[1] / "inputs" / "epigraphdb_pqtl"
RTYPES = ("mrres", "simple")


def get(path: str, params: dict) -> bytes:
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return r.read()
        except Exception as e:  # network errors are retried, then raised
            if attempt == 4:
                raise RuntimeError(f"failed {url}") from e
            time.sleep(5 * (attempt + 1))
    raise AssertionError("unreachable")


def main() -> None:
    (OUT / "responses").mkdir(parents=True, exist_ok=True)
    for flag in ("exposures", "outcomes"):
        p = OUT / f"list_{flag}.json"
        if not p.exists():
            p.write_bytes(get("/pqtl/list/", {"flag": flag}))
    proteins = [r["expID"] for r in json.loads((OUT / "list_exposures.json").read_bytes())["results"]]
    for i, prot in enumerate(proteins):
        for rtype in RTYPES:
            f = OUT / "responses" / f"{rtype}__{urllib.parse.quote(prot, safe='')}.json"
            if f.exists():
                continue
            body = get("/pqtl/", {"query": prot, "rtype": rtype, "searchflag": "proteins", "pvalue": 1})
            json.loads(body)  # must parse before it is kept
            tmp = f.with_suffix(".part")
            tmp.write_bytes(body)
            tmp.rename(f)
            time.sleep(0.2)
        if i % 50 == 0:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {i + 1}/{len(proteins)} {prot}", flush=True)
    files = sorted(OUT.rglob("*.json"))
    manifest = {
        "retrieved": time.strftime("%Y-%m-%d"),
        "api": API,
        "n_proteins": len(proteins),
        "files": {str(f.relative_to(OUT)): hashlib.sha256(f.read_bytes()).hexdigest()
                  for f in files if f.name != "manifest.json"},
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    print("done", len(manifest["files"]), "files")


if __name__ == "__main__":
    main()
