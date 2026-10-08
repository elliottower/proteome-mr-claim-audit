# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml==6.0.3"]
# ///
"""Process counts of the census, each with the file and address it comes from (PREREG.md log,
2026-10-08). These are descriptive counts of how the study was run: records screened, claim
records, span checks, queue rows, codes, log lines, ledger events, pinned quotations, files and
tests. None is an H1 or H2 quantity and no registry, relation or assembly file is read.

Every count is read from a committed file. A count is one of:
    direct    one value at one JSON address of one file
    sum       the sum of values at JSON addresses of several files
    lines     the number of non-empty lines of one or several files (one record per line; for a
              CSV, the rows after the header)
    computed  counted from the repository by this script (dated log lines of PREREG.md by their
              access level; ledger events by kind; quotations in claims files; script and test
              files; the pass count on the last line of a stored suite output)

The output holds, per count, its value, its meaning, its kind, every source with the value read
there, and `recorded_in_runs`: the run ids of the results ledger whose manifest
(outputs/results_manifests/<run>.json) names every source file of the count with the bytes it
has now. A count with no such run rests on this script's own run. The output also holds the
sha256 of every file read. `--suite` names the stored suite output to read; `--ledger-seq`
is checked against the ledger so that the ledger counts are of a stated state.

Usage: uv run scripts/process_counts.py --suite outputs/tests/pytest_all_modal_<stamp>.txt \\
           --out outputs/process_counts/process_counts_<date>.json
"""

import argparse
import collections
import csv
import datetime
import hashlib
import json
import pathlib
import re

import yaml

EXP = pathlib.Path(__file__).resolve().parent.parent
ROOT = EXP.parent.parent
LEVELS = ("nothing run", "no results seen", "results not opened", "results seen")
STEM = "sol_extraction_{}_0b97103cd7a4"
FILES = ("search", "chase1", "chase2", "chase3")
DECISIONS = ("search_complete", "chase1", "gate1b1", "gate1b2", "gate1b3", "gate1b4", "gate1b5",
             "gateall1", "chase2", "gateall2", "gateall3")
ROUND_OF = {"search_complete": "search", "chase1": "chase1", "gate1b1": "chase1",
            "gate1b2": "chase1", "gate1b3": "chase1", "gate1b4": "chase1", "gate1b5": "chase1",
            "gateall1": "chase1", "chase2": "chase2", "gateall2": "chase2", "gateall3": "chase3"}
CODING = "outputs/manual_coding/2026-10-03"
NEW = "outputs/manual_coding/2026-10-03_new_rows"
AMENDED = "outputs/verification_amendment02"
MARK = re.compile(r"\s+·[0-9a-f]{8}$")  # the chain mark `prereg log` ends a line with
SUMMARY_LINE = re.compile(r"(?:(\d+) failed, )?(\d+) passed(?:, (\d+) skipped)?")


class CountError(Exception):
    """A source is missing, an address does not resolve, or the ledger is not at the stated
    state."""


def at(value, address: str):
    """The value at a dotted address of parsed JSON."""
    for part in address.split("."):
        if not isinstance(value, dict) or part not in value:
            raise CountError(f"no {address!r}")
        value = value[part]
    return value


def non_empty_lines(text: str) -> int:
    return sum(bool(line.strip()) for line in text.splitlines())


def log_lines(plan: str) -> dict[str, int]:
    """Dated lines of the plan's log, in all and by the access level each ends with (before
    the chain mark, where the line has one)."""
    log = plan[plan.index("\n## Log\n"):]
    dated = [line for line in log.splitlines() if re.match(r"^\d{4}-\d{2}-\d{2}  ", line)]
    out = {"all": len(dated), **dict.fromkeys(LEVELS, 0), "no level read": 0}
    for line in dated:
        # `no results seen` ends with `results seen`: the first level in LEVELS that fits.
        end = MARK.sub("", line.rstrip()).rstrip()
        level = next((x for x in LEVELS if end.endswith(x)), "no level read")
        out[level] += 1
    return out


def ledger_events(text: str) -> dict:
    """Ledger events by kind, the last sequence number, and the distinct files sealed."""
    events = [json.loads(line) for line in text.splitlines() if line.strip()]
    kinds = collections.Counter(e["event"] for e in events)
    sealed = {f["path"] if isinstance(f, dict) else f
              for e in events if e["event"] == "seal" for f in e.get("files", [])}
    levels = collections.Counter(e.get("level") for e in events if e["event"] == "access")
    return {"events": len(events), "last_seq": events[-1]["seq"], "by_kind": dict(kinds),
            "distinct_files_sealed": len(sealed),
            "access_by_level": {str(k): v for k, v in sorted(levels.items(), key=str)}}


def quotations(folder: pathlib.Path) -> dict[str, int]:
    """Claims files of a folder and the quotations they hold."""
    files = sorted(folder.glob("*.yaml"))
    quotes = with_one = 0
    for path in files:
        claims = (yaml.safe_load(path.read_text()) or {}).get("claims") or {}
        n = sum(len(c.get("quotes") or []) for c in claims.values() if isinstance(c, dict))
        quotes += n
        with_one += bool(n)
    return {"claims_files": len(files), "claims_files_with_a_quotation": with_one,
            "quotations": quotes}


def suite(text: str) -> dict[str, int]:
    """Passed, skipped and failed of the last summary line of a stored suite output."""
    found = [m for line in text.splitlines() if (m := SUMMARY_LINE.search(line))
             and " in " in line]
    if not found:
        raise CountError("no summary line in the suite output")
    failed, passed, skipped = found[-1].groups()
    return {"passed": int(passed), "skipped": int(skipped or 0), "failed": int(failed or 0)}


def runs_holding(sources: list[str], manifests: dict[str, dict[str, str]],
                 digests: dict[str, str]) -> list[str]:
    """Run ids whose manifest names every source with the bytes it has now."""
    return sorted(run for run, files in manifests.items()
                  if sources and all(files.get(s) == digests[s] for s in sources))


class Counts:
    """Collects counts and the hash of every file read."""

    def __init__(self, root: pathlib.Path = EXP):
        self.root = root
        self.digests: dict[str, str] = {}
        self.counts: dict[str, dict] = {}

    def read(self, path: str) -> str:
        data = (self.root / path).read_bytes()
        self.digests[path] = hashlib.sha256(data).hexdigest()
        return data.decode()

    def add(self, name: str, meaning: str, kind: str, value, sources: list[dict]) -> None:
        if name in self.counts:
            raise CountError(f"{name} is given twice")
        self.counts[name] = {"value": value, "meaning": meaning, "kind": kind,
                             "sources": sources}

    def direct(self, name: str, meaning: str, path: str, address: str) -> int:
        value = at(json.loads(self.read(path)), address)
        self.add(name, meaning, "direct", value,
                 [{"file": path, "address": address, "value": value}])
        return value

    def total(self, name: str, meaning: str, parts: list[tuple[str, str]]) -> int:
        sources = [{"file": p, "address": a, "value": at(json.loads(self.read(p)), a)}
                   for p, a in parts]
        value = sum(s["value"] for s in sources)
        self.add(name, meaning, "sum", value, sources)
        return value

    def lines(self, name: str, meaning: str, paths: list[str], header: bool = False) -> int:
        sources = [{"file": p, "address": "rows after the header" if header
                    else "non-empty lines",
                    "value": (len(list(csv.DictReader(self.read(p).splitlines(keepends=True))))
                              if header else non_empty_lines(self.read(p)))} for p in paths]
        value = sum(s["value"] for s in sources)
        self.add(name, meaning, "lines", value, sources)
        return value

    def computed(self, name: str, meaning: str, value, paths: list[str], how: str) -> None:
        self.add(name, meaning, "computed", value,
                 [{"file": p, "address": how} for p in paths])


def census(c: Counts, suite_file: str) -> None:
    """Every count of the census, in the order of the study's stages."""
    c.direct("search_records_after_deduplication",
             "records of the search after duplicates were removed",
             "outputs/screening/2026-10-03/funnel.json", "screening_records")
    c.direct("search_records_sent_to_screening",
             "search records with an abstract, sent to the screening model",
             "outputs/screening/2026-10-03/prefilter_counts.json", "records_sent_to_screening")
    c.lines("search_records_without_an_abstract",
            "search records with no abstract or a stub, not screened",
            ["outputs/screening/2026-10-03/no_abstract.jsonl"])
    for k in (1, 2, 3):
        c.direct(f"chase_round_{k}_new_records",
                 f"new records found by citation chasing, round {k}",
                 f"outputs/screening/chase_round_{k}/chase_counts.json", "new_screening_records")
        c.direct(f"chase_round_{k}_new_records_without_an_abstract",
                 f"new records of round {k} with no abstract or a stub",
                 f"outputs/screening/chase_round_{k}/chase_counts.json",
                 "new_screening_records_no_abstract.records")
    decision = "outputs/parsed/sol_eligibility_{}_2811496ef424.decisions.jsonl"
    for label in ("search", "chase1", "chase2", "chase3"):
        c.lines(f"records_screened_{label}",
                f"records given an eligibility decision by the screening model, {label}",
                [decision.format(d) for d in DECISIONS if ROUND_OF[d] == label])
    c.lines("records_screened_all",
            "records given an eligibility decision by the screening model, search and three "
            "rounds of citation chasing", [decision.format(d) for d in DECISIONS])
    parsed = "outputs/parsed/" + STEM + ".jsonl"
    for label in FILES:
        c.lines(f"papers_extracted_{label}", f"abstracts sent to extraction, {label}",
                [parsed.format(label)])
    c.lines("papers_extracted_all", "abstracts sent to extraction",
            [parsed.format(label) for label in FILES])
    summary = "outputs/verification/" + STEM + "/claim_summary.json"
    for label in FILES:
        c.direct(f"claim_records_{label}", f"claim records extracted, {label}",
                 summary.format(label), "n_claims")
    c.total("claim_records_all", "claim records extracted",
            [(summary.format(label), "n_claims") for label in FILES])
    c.total("claim_records_passing_the_span_check_registered_run",
            "claim records whose evidence span passed both span checks in the registered run",
            [(summary.format(label), "span_pass") for label in FILES])
    spans = "outputs/verification/" + STEM + "/span_summary.json"
    c.total("pinned_evidence_spans_registered_run",
            "evidence spans pinned by the quotation tool in the registered run",
            [(spans.format(label), "citations_pin_found") for label in FILES])
    follow = "outputs/span_failure_classes/span_failure_followup_counts_2026-10-08.json"
    c.direct("span_failures_passage_standing_twice",
             "failing spans that stand twice in the stored abstract", follow,
             "duplicates.records")
    c.direct("span_failures_one_token_left_out",
             "failing spans that leave out one token of the abstract", follow,
             "omissions.records")
    c.total("span_failures_all", "claim records that failed the span check in the registered "
            "run", [(follow, "duplicates.records"), (follow, "omissions.records")])
    occurrence = "outputs/verification_occurrence/" + STEM + "/span_summary.json"
    c.total("claim_records_passing_the_span_check_corrected_build",
            "claim records passing both span checks under the corrected build of the "
            "quotation tool (the 27 pinned at their first occurrence)",
            [(occurrence.format(label), "both_pass") for label in FILES])
    restored = [f"outputs/verification_occurrence/{STEM.format('search')}_restored",
                f"outputs/verification_occurrence/{STEM.format('chase1')}_restored",
                f"outputs/verification_occurrence/{STEM.format('chase2')}",
                f"outputs/verification_occurrence/{STEM.format('chase3')}"]
    c.total("claim_records_passing_the_span_check_amended_primary",
            "claim records passing both span checks with the 37 spans restored from the "
            "stored abstract", [(f"{p}/span_summary.json", "both_pass") for p in restored])
    for label in ("search", "chase1"):
        repair_map = f"outputs/span_restoration/{label}/repair_map.json"
        c.computed(f"spans_restored_{label}",
                   f"spans restored from the stored abstract, {label}",
                   len(json.loads(c.read(repair_map))["repairs"]), [repair_map],
                   "number of entries of `repairs`")
    c.total("registry_entries_registered_run",
            "claim records the verifier passes into the registry, registered run",
            [(summary.format(label), "enters_registry") for label in FILES])
    with_27 = [(f"{AMENDED}/registered_with_27/{STEM.format('search')}/claim_summary.json",
                "enters_registry")] + [(summary.format(x), "enters_registry")
                                       for x in FILES[1:]]
    c.total("registry_entries_with_the_27",
            "claim records the verifier passes into the registry with the 27 pinned",
            with_27)
    amended = [(f"{AMENDED}/amended_primary/{STEM.format(x)}_restored/claim_summary.json",
                "enters_registry") for x in FILES[:2]] + [
        (summary.format(x), "enters_registry") for x in FILES[2:]]
    c.total("registry_entries_amended_primary",
            "claim records the verifier passes into the registry in the amended primary "
            "analysis", amended)
    c.lines("queue_rows", "rows of the manual-coding queue (record, side, name as written)",
            [f"{CODING}/manual_coding_queue.csv"], header=True)
    c.lines("queue_rows_amended_primary", "rows of the queue rebuilt for the amended primary "
            "analysis", ["outputs/manual_coding/2026-10-03_amended_primary/"
                         "manual_coding_queue.csv"], header=True)
    compared = ("outputs/manual_coding/2026-10-03_amended_primary/"
                "queue_rebuild_comparison_with_passages.json")
    c.direct("queue_rows_new", "queue rows added by the rebuild", compared, "new_rows")
    c.direct("queue_rows_unchanged", "coded queue rows asserted unchanged in the rebuilt queue",
             compared, "coded_rows")
    report = f"{CODING}/manual_dataset_coding_report.json"
    for name, address, meaning in (
            ("queue_rows_coded", "coded", "queue rows coded to a dictionary row"),
            ("queue_rows_release_not_identified", "unresolved_reason_release_not_identified",
             "queue rows unresolved: release not identified"),
            ("queue_rows_conflicting_identifiers", "unresolved_reason_conflicting_identifiers",
             "queue rows unresolved: conflicting identifiers"),
            ("queue_rows_absent_from_dictionary",
             "unresolved_reason_dataset_absent_from_dictionary",
             "queue rows unresolved: dataset named and absent from the dictionary"),
            ("second_check_agreements", "step2_agree",
             "queue rows on which the two checks gave the same value"),
            ("second_check_disagreements", "step2_disagree",
             "queue rows on which the two checks differed, reread")):
        c.direct(name, meaning, report, address)
    coverage = f"{CODING}/check3_coverage_after_second_look_save2.json"
    c.direct("coded_rows_marked_by_the_author", "coded rows the author marked as confirmed",
             coverage, "rows_with_an_author_yes")
    c.direct("coded_rows_machine_checked_only", "coded rows checked by the machine gate only",
             coverage, "rows_machine_gate_only")
    c.direct("new_queue_rows_coded", "new queue rows coded at the first check",
             f"{NEW}/first_check_result.json", "first_check_by_category.coded")
    second = list(csv.DictReader(c.read(
        f"{NEW}/manual_dataset_codes_extended_2_second_check.csv").splitlines(keepends=True)))
    c.computed("new_queue_rows_on_which_the_checks_agree",
               "new queue rows on which the two checks gave the same value",
               sum(r["claude_code_value"] == r["perplexity_value"] for r in second),
               [f"{NEW}/manual_dataset_codes_extended_2_second_check.csv"],
               "rows whose claude_code_value equals perplexity_value")
    log = log_lines(c.read("PREREG.md"))
    c.computed("plan_log_lines", "dated lines of the plan's log", log["all"], ["PREREG.md"],
               "lines of the Log section that begin with a date")
    for level in LEVELS:
        c.computed(f"plan_log_lines_{level.replace(' ', '_')}",
                   f"log lines written at the level `{level}`", log[level], ["PREREG.md"],
                   "dated log lines ending with the level")
    ledger_path = str(pathlib.Path("../..") / ".results" / "ledger.jsonl")
    ledger = ledger_events(c.read(ledger_path))
    c.computed("ledger_events", "events of the results ledger", ledger["events"],
               [ledger_path], f"lines; last seq {ledger['last_seq']}")
    for kind in ("seal", "run", "access", "claim"):
        c.computed(f"ledger_events_{kind}", f"ledger events of kind `{kind}`",
                   ledger["by_kind"].get(kind, 0), [ledger_path], "events of the kind")
    c.computed("ledger_distinct_files_sealed", "distinct files sealed in the ledger",
               ledger["distinct_files_sealed"], [ledger_path], "distinct paths of seal events")
    for level, n in ledger["access_by_level"].items():
        c.computed(f"ledger_access_{level.replace(' ', '_')}",
                   f"access records at the level `{level}`", n, [ledger_path],
                   "access events of the level")
    for name, folder, meaning in (
            ("manual_coding", "outputs/citations/manual_coding_2026-10-03/claims",
             "the manual dataset coding"),
            ("manual_coding_new_rows", "outputs/citations/manual_coding_2026-10-03_new_rows/"
             "claims", "the coding of the new queue rows"),
            ("repository_root", "../../claims", "the repository's own claims folder")):
        found = quotations(c.root / folder)
        for path in sorted((c.root / folder).glob("*.yaml")):
            c.read(str(pathlib.Path(folder) / path.name))
        c.computed(f"pinned_quotations_{name}", f"quotations pinned for {meaning}",
                   found["quotations"], [folder], "quotations of every claims file")
        c.computed(f"claims_files_{name}", f"claims files of {meaning}", found["claims_files"],
                   [folder], "claims files in the folder")
    c.computed("scripts", "Python files under scripts/",
               len(list((c.root / "scripts").glob("*.py"))), ["scripts"], "*.py files")
    c.computed("test_files", "test files under tests/",
               len(list((c.root / "tests").glob("test_*.py"))), ["tests"], "test_*.py files")
    result = suite(c.read(suite_file))
    for key, value in result.items():
        c.computed(f"suite_tests_{key}", f"tests {key} in the stored suite output", value,
                   [suite_file], "last summary line")


def load_manifests(folder: pathlib.Path) -> dict[str, dict[str, str]]:
    out = {}
    for path in sorted(folder.glob("*.json")):
        made = json.loads(path.read_text())
        if isinstance(made, dict) and "run_id" in made and isinstance(made.get("files"), list):
            out[made["run_id"]] = {f["path"]: f["sha256"] for f in made["files"]}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True)
    ap.add_argument("--ledger-seq", type=int, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise CountError(f"{a.out} exists; counts are written once")
    c = Counts()
    census(c, a.suite)
    seq = int(c.counts["ledger_events"]["sources"][0]["address"].rsplit(" ", 1)[1])
    if seq != a.ledger_seq:
        raise CountError(f"the ledger's last seq is {seq}, not {a.ledger_seq}")
    manifests = load_manifests(EXP / "outputs" / "results_manifests")
    for entry in c.counts.values():
        files = [s["file"] for s in entry["sources"]]
        entry["recorded_in_runs"] = (runs_holding(files, manifests, c.digests)
                                     if all(f in c.digests for f in files) else [])
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({
        "written_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "script_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        "suite": a.suite, "ledger_last_seq": seq, "counts": c.counts,
        "inputs_sha256": dict(sorted(c.digests.items()))}, indent=1) + "\n")
    print(json.dumps({k: v["value"] for k, v in c.counts.items()}, indent=1))


if __name__ == "__main__":
    main()
