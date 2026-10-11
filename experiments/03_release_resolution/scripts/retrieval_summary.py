# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Counts of the retrieval of the release-resolution follow-up, from the stored results
(<record>/result.json): records by status; records with a readable source by route and by
version; supplement files by type and readable or not; failures by route and reason; unreadable
files by reason. Counts only; no text is written.

Usage: uv run scripts/retrieval_summary.py --results <folder> --out <json>
"""

import argparse
import collections
import json
import pathlib


def summary(results: list[dict]) -> dict:
    by = collections.Counter
    routes = by()
    versions = by()
    for r in results:
        for route in sorted({s["route"] for s in r["sources"] if s.get("text")}):
            routes[route] += 1
        for v in sorted({s["version"] for s in r["sources"] if s.get("text")}):
            versions[v] += 1
    supplements = [s for r in results for s in r["sources"] if s["route"] == "R2"]
    return {
        "records": len(results),
        "records_by_status": dict(by(r["status"] for r in results)),
        "records_by_kind": dict(by(r["kind"] for r in results)),
        "records_with_a_readable_source_by_route": dict(routes),
        "records_with_a_readable_source_by_version": dict(versions),
        "records_with_a_full_text": sum(any(s["route"] in ("R1", "R3") and s.get("text")
                                            for s in r["sources"]) for r in results),
        "records_with_a_readable_supplement": sum(any(s["route"] == "R2" and s.get("text")
                                                      for s in r["sources"]) for r in results),
        "supplement_files": len(supplements),
        "supplement_files_by_type": dict(by(s["type"] for s in supplements)),
        "supplement_files_readable": sum(s.get("text") is not None for s in supplements),
        "unreadable_files_by_reason": dict(by(s["reason"] for r in results for s in r["sources"]
                                              if s.get("text") is None and "reason" in s)),
        "failures_by_route_and_reason": dict(by(f"{f['route']}|{f['reason']}"
                                                for r in results for f in r["failures"])),
        "records_with_a_correction": sum(any(v["version"] == "correction" for v in r["versions"])
                                         for r in results),
        "pdftotext": sorted({r.get("pdftotext", "") for r in results}),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise FileExistsError(f"{a.out} exists; it is written once")
    results = [json.loads(p.read_text()) for p in sorted(a.results.glob("*/result.json"))]
    out = summary(results)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
