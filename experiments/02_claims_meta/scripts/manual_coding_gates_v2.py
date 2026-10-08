# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "numpy==2.5.3", "pydantic==2.13.5", "pyyaml==6.0.3"]
# ///
"""Machine gates on a coder's file of manual dataset codes, run before the second check
(PREREG.md log, 2026-10-07). The gates are quality-control checks added to the three
registered checks and replace none of them: a literal match does not show that a sentence
describes the dataset an analysis used. This is the gate script of the run from attempt 3 on;
it supersedes scripts/manual_coding_gates.py, which stays sealed. It accepts everything that
script accepts and, where that script finds no identifier, two further forms (rules A and E of
the log of 2026-10-08):

    release number   the pinned sentence writes the coded row's numbered release in another
                     form. A dictionary name or alias that ends in a release word and a number
                     ("FinnGen R9", "FinnGen release 9", "finngen_R9", "FinnGen DF9") gives a
                     dataset name and a number. The sentence holds that name and, attached to
                     it, a release expression with the same number: a release word (R, DF,
                     round, release, version, freeze, data freeze) followed by the number, or
                     an ordinal ("12th", "twelfth") followed by a release word; case, spaces,
                     underscores and hyphens are ignored. Attached means: after the name with
                     nothing between but filler words (study, consortium, cohort, project,
                     database, biobank, data ...), or before it and joined by of, from or in.
                     A name with release expressions of two different numbers attached, or
                     with no number ("latest release"), does not pass.
    citation and     for a `companion_source` row whose reference entry is verified by its
    attribute        identifier and is the source of several dictionary rows of the side: the
                     pinned sentence holds an attribute of the coded row that no other of those
                     rows has: a name, alias or release term, an exact sample size, a platform,
                     or the row's ancestry when it is written as a plain phrase.

The gate file of an attempt goes to `gates_v2/`; a second file, `gates_v2_for_coder/`, lists the
failing rows by side and name with their failures and no coded value, for the coder.

A quote may also be a sentence of a passage given for another row of the same paper, when the
coder names it as `<side>_<k>:<passage id>` (rule I2); the gate accepts it with the warning
`passage_given_for_another_row`.

For every row of an attempt file (`coders/<coder>/codes/<file name>.attempt<n>.json`):

    value        the value is a dictionary row of the row's side, `not_stated_in_source` or
                 `source_names_dataset_absent_from_dictionary`; an unresolved row gives one of
                 the four reasons, and the reason fits the value and the row's passage status
    pin          the quoted sentence is a sentence of a passage given for that row, occurs in
                 that passage's source document, and is the quotation the named claim of that
                 passage's claims file holds; `source_read` is the passage's; for a
                 `companion_source` row the same holds for the reference entry, which must be
                 an entry listed with that passage
    identifier   the pinned material (the sentence, and the reference entry when there is one)
                 holds a term of the coded dictionary row that no other candidate row has
                 (from `name`, `aliases`, `release`, `source_citation` or `source_identifier`),
                 or the row's exact sample size, shared with no other candidate, together with
                 its platform or a year of its release or source citation
    reference    for a `companion_source` row, the reference entry is verified against the
                 coded row's `source_identifier` by the first identifier the XML gives for
                 it: its DOI; else (`no_doi`) its PMID; else its PMC identifier. An identifier
                 that is not one of the dictionary row's fails. An entry with none of the
                 three (`no_stable_identifier`) fails: a reference entry that cannot be
                 verified cannot carry a code, and the row is unresolved

Candidate rows are the row's candidates that are dictionary rows; for a row with none, every
dictionary row of its side. A coded value outside the candidate set is a warning. Terms and
their matching are those of scripts/manual_coding_passages.py.

`citations verify --strict` is run once over the claims folder and its report kept. A gate
file `coders/<coder>/gates/<file name>.attempt<n>.gate.json` is written per attempt and never
overwritten; a failed attempt goes back to the same coder, who writes the next attempt, and
every attempt and gate file is kept.

Usage: uv run scripts/manual_coding_gates_v2.py --coders <coders dir> --citations <citations dir>
"""

import argparse
import collections
import csv
import datetime
import json
import os
import pathlib
import re
import subprocess

import yaml

from dataset_relations import DICTIONARY
from manual_coding_passages import NO_PASSAGE, bounded, dictionary_terms, matches, normalize
from manual_coding_table import ABSENT, ATTEMPT, BASES, REASONS, UNRESOLVED_VALUES

UNIQUE_FIELDS = ("name", "aliases", "release", "source_citation", "source_identifier")
YEAR = re.compile(r"(?:19|20)\d{2}")
DOI = re.compile(r"10\.\d{4,9}/[^\s;]+")
PMID = re.compile(r"PMID\s*:\s*(\d+)", re.IGNORECASE)
PMCID = re.compile(r"PMC\s*(\d+)", re.IGNORECASE)


RELEASE_WORDS = ("r", "df", "round", "release", "version", "freeze")
ORDINALS = {w: i for i, w in enumerate(
    ("first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth "
     "thirteenth fourteenth fifteenth sixteenth seventeenth eighteenth nineteenth "
     "twentieth").split(), 1)}
FUSED = re.compile(r"^(r|df|round|release|version|freeze)(\d{1,2})$")
NUMBER = re.compile(r"^(\d{1,2})(st|nd|rd|th)?$")
FILLER_AFTER = frozenset("study studies consortium cohort project database biobank data "
                         "research the gwas summary statistics dataset datasets".split())
LINKS = frozenset(("of", "from", "in"))
FILLER_BEFORE = LINKS | frozenset("the data summary statistics gwas results dataset datasets "
                                  "study".split())
GATES, FOR_CODER = "gates_v2", "gates_v2_for_coder"


def tokens(text: str) -> list[str]:
    return re.findall(r"[0-9a-z]+", normalize(text))


def numbered_names(row: dict) -> set[tuple[tuple[str, ...], int]]:
    """(dataset name tokens, release number) for each name or alias of the row that ends in a
    release word and a number."""
    found = set()
    for field, term in dictionary_terms(row):
        if field not in ("name", "aliases"):
            continue
        t = tokens(term)
        if len(t) >= 2 and FUSED.match(t[-1]):
            found.add((tuple(t[:-1]), int(FUSED.match(t[-1])[2])))
        elif len(t) >= 3 and t[-2] in RELEASE_WORDS and NUMBER.match(t[-1]):
            stem = t[:-3] if t[-2] == "freeze" and t[-3] == "data" else t[:-2]
            if stem:
                found.add((tuple(stem), int(t[-1])))
    return found


def release_expressions(t: list[str]) -> list[tuple[int, int, int]]:
    """(first token, token after the last, number) of each release expression."""
    out = []
    for i, tok in enumerate(t):
        start = i - 1 if tok == "freeze" and i and t[i - 1] == "data" else i
        if FUSED.match(tok):
            out.append((i, i + 1, int(FUSED.match(tok)[2])))
        elif tok in RELEASE_WORDS and i + 1 < len(t) and NUMBER.match(t[i + 1]):
            out.append((start, i + 2, int(NUMBER.match(t[i + 1])[1])))
        elif tok in RELEASE_WORDS[2:] and i:
            before = t[start - 1] if start else ""
            ordinal = NUMBER.match(before)
            if before in ORDINALS:
                out.append((start - 1, i + 1, ORDINALS[before]))
            elif ordinal and ordinal[2]:
                out.append((start - 1, i + 1, int(ordinal[1])))
    return out


def release_number_basis(row: dict, sentence: str) -> list[str]:
    """Rule A: the sentence writes the row's numbered release in another form. The release
    expressions attached to an occurrence of the dataset name must all carry the row's
    number."""
    t = tokens(sentence)
    found = release_expressions(t)
    for stem, number in sorted(numbered_names(row)):
        attached = set()
        for s in range(len(t) - len(stem) + 1):
            if tuple(t[s:s + len(stem)]) != stem:
                continue
            e = s + len(stem)
            for start, end, n in found:
                after = t[e:start] if start >= e else None
                before = t[end:s] if end <= s else None
                if ((after is not None and len(after) <= 4 and set(after) <= FILLER_AFTER)
                        or (before is not None and 0 < len(before) <= 5
                            and set(before) <= FILLER_BEFORE and set(before) & LINKS)):
                    attached.add(n)
        if attached == {number}:
            return [f"release_number:{' '.join(stem)} {number}"]
    return []


def plain_ancestry(row: dict) -> str | None:
    words = row.get("ancestry", "").strip().split()
    plain = 0 < len(words) <= 3 and all(w.isalpha() for w in words) and words != ["NA"]
    return " ".join(words) if plain else None


def separating_attribute_basis(row: dict, sharing: list[dict], sentence: str) -> list[str]:
    """Rule E: an attribute of the row, in the sentence, that no other row of the same source
    has."""
    others = [r for r in sharing if r["name"] != row["name"]]
    if not others:
        return []
    other_terms = {t for r in others for t in dictionary_terms(r)}
    found = [f"{f}:{t}" for f, t in dictionary_terms(row)
             if f in ("name", "aliases", "release", "sample_size") and (f, t) not in other_terms
             and matches((f, t), sentence)]
    norm = normalize(sentence)
    found += [f"platform:{p}" for p in platform_terms(row)
              if all(p not in platform_terms(r) for r in others) and bounded(p).search(norm)]
    ancestry = plain_ancestry(row)
    if (ancestry and all(plain_ancestry(r) != ancestry for r in others)
            and bounded(ancestry).search(norm)):
        found.append(f"ancestry:{ancestry}")
    return [f"citation+{f}" for f in found]


class GateError(Exception):
    """An attempt file has no input file, or a gate file exists."""


def platform_terms(row: dict) -> list[str]:
    head = row["platform"].split("(")[0].strip()
    if not head or head == "NA":
        return []
    return list(dict.fromkeys([head, head.split()[0]]))


def identifier_basis(value_row: dict, pool: list[dict], material: str) -> list[str]:
    """Which identifiers of the coded row the pinned material holds; empty fails the gate."""
    others = {t for r in pool if r["name"] != value_row["name"] for t in dictionary_terms(r)}
    own = [t for t in dictionary_terms(value_row) if t not in others]
    found = [f"{f}:{t}" for f, t in own if f in UNIQUE_FIELDS and matches((f, t), material)]
    sizes = [t for t in own if t[0] == "sample_size" and matches(t, material)]
    norm = normalize(material)
    years = YEAR.findall(value_row["release"] + " " + value_row["source_citation"])
    beside = ([p for p in platform_terms(value_row) if bounded(p).search(norm)]
              + [y for y in years if bounded(y).search(norm)])
    if sizes and beside:
        found.append(f"sample_size:{sizes[0][1]}+{beside[0]}")
    return found


def reference_check(entry: dict, source_identifier: str) -> tuple[str, str | None]:
    """(the identifier the entry was verified by, the failure or None): DOI, else PMID, else
    PMC identifier, each against the dictionary row's `source_identifier`; none fails."""
    if entry.get("doi"):
        wanted = {d.rstrip(".").casefold() for d in DOI.findall(source_identifier)}
        return "doi", (None if entry["doi"].strip().casefold() in wanted
                       else "reference_doi_differs_from_the_dictionary_source")
    if entry.get("pmid"):
        return "pmid", (None if entry["pmid"].strip() in PMID.findall(source_identifier)
                        else "reference_pmid_differs_from_the_dictionary_source")
    if entry.get("pmcid"):
        number = "".join(c for c in entry["pmcid"] if c.isdigit())
        return "pmcid", (None if number in PMCID.findall(source_identifier)
                         else "reference_pmcid_differs_from_the_dictionary_source")
    return "none", "reference_entry_has_no_stable_identifier"


def pinned_quote(claims_root: pathlib.Path, reference: str) -> str | None:
    """The quotation of `claims/<file>.yaml#<id>`, or None when it is not there."""
    if "#" not in reference:
        return None
    name, claim_id = reference.rsplit("#", 1)
    path = claims_root / name
    if not path.is_file():
        return None
    quotes = (yaml.safe_load(path.read_text()).get("claims") or {}).get(claim_id, {}).get(
        "quotes") or []
    return quotes[0].get("exact") if quotes else None


def gate_row(coded: dict, given: dict, dictionary: dict[tuple[str, str], dict],
             texts: dict[str, str], reference_text: str, claims_root: pathlib.Path,
             paper_rows: dict[str, dict] | None = None) -> dict:
    """The gate result of one coded row against the row the coder was given. `texts` holds
    the source documents of the paper by their `document` path. A `passage_id` written
    `<side>_<k>:<passage id>` names a passage given for another row of the same paper
    (`paper_rows`, by row id); it is accepted with a warning."""
    failures, warnings, basis, verified_by, entry_verified = [], [], [], None, None
    side, value = given["side"], coded.get("value")
    row = dictionary.get((side, value))
    reason = coded.get("unresolved_reason")
    if row is None and value not in UNRESOLVED_VALUES:
        failures.append("value_not_allowed")
    if row is not None and reason:
        failures.append("coded_row_gives_an_unresolved_reason")
    if row is None and value in UNRESOLVED_VALUES:
        fits = (reason in REASONS
                and (reason == "dataset_absent_from_dictionary") == (value == ABSENT)
                and (reason == "no_local_passage_found") == (given["status"] == NO_PASSAGE))
        if not fits:
            failures.append("unresolved_reason_does_not_fit")
    needs_pin = row is not None or value == ABSENT
    sentence = coded.get("quote") or ""
    passage_id, origin = coded.get("passage_id") or "", given
    if ":" in passage_id:
        other, passage_id = passage_id.split(":", 1)
        origin = (paper_rows or {}).get(other) or {"passages": []}
        warnings.append("passage_given_for_another_row")
    passage = next((p for p in origin["passages"] if p["passage_id"] == passage_id), None)
    if needs_pin:
        if passage is None or sentence not in passage["sentences"]:
            failures.append("quote_is_not_a_sentence_of_a_passage_given")
        source_text = texts.get((passage or {}).get("document"), "")
        if not sentence or normalize(sentence) not in normalize(source_text):
            failures.append("quote_not_in_the_source_document")
        claim = coded.get("citations_claim") or ""
        if (pinned_quote(claims_root, claim) != sentence
                or claim.rsplit("#", 1)[0] != (passage or {}).get("claims_file")):
            failures.append("quote_is_not_the_pinned_quotation")
        if passage is not None and coded.get("source_read") != passage["source_read"]:
            failures.append("source_read_is_not_the_passages")
    if value == ABSENT and not (coded.get("dataset_named_in_source")
                                and normalize(coded["dataset_named_in_source"])
                                in normalize(sentence)):
        failures.append("named_dataset_not_in_the_quote")
    entry_text = ""
    if row is not None and coded.get("companion_source"):
        entry_text = coded.get("reference_quote") or ""
        entry = next((r for r in (passage or {}).get("references", [])
                      if r["entry"] == entry_text), None)
        if entry is None:
            failures.append("reference_entry_not_listed_with_the_passage")
        if not entry_text or normalize(entry_text) not in normalize(reference_text):
            failures.append("reference_entry_not_in_the_reference_list")
        if pinned_quote(claims_root, coded.get("reference_citations_claim") or "") != entry_text:
            failures.append("reference_entry_is_not_the_pinned_quotation")
        if entry:
            verified_by, failure = reference_check(entry, row["source_identifier"])
            if failure:
                failures.append(failure)
            else:
                entry_verified = entry
            if verified_by != "doi":
                warnings.append("no_stable_identifier" if verified_by == "none" else "no_doi")
    if row is not None:
        if coded.get("identification_basis") not in BASES:
            failures.append("identification_basis_not_allowed")
        named = [dictionary[(side, c)] for c in given["candidates"] if (side, c) in dictionary]
        if named and row not in named:
            warnings.append("value_outside_the_candidate_set")
        pool = named if row in named else [r for (s, _), r in dictionary.items() if s == side]
        basis = (identifier_basis(row, pool, f"{sentence} {entry_text}")
                 or release_number_basis(row, sentence))
        if not basis and entry_verified:
            side_rows = [r for (s, _), r in dictionary.items() if s == side]
            sharing = [r for r in side_rows
                       if reference_check(entry_verified, r["source_identifier"])[1] is None]
            basis = separating_attribute_basis(row, sharing, sentence)
        if not basis:
            failures.append("no_identifier_of_the_coded_row_in_the_pinned_material")
    return {"side": side, "name_as_written": given["name_as_written"], "value": value,
            "passes": not failures, "failures": failures, "warnings": warnings,
            "machine_basis": basis, "reference_verified_by": verified_by}


def gate_attempt(attempt: dict, given: dict, dictionary: dict[tuple[str, str], dict],
                 citations: pathlib.Path) -> dict:
    """The gate result of one attempt file: every row given must be coded once."""
    documents = {p["document"] for g in given["rows"] for p in g["passages"]}
    texts = {d: (citations / d).read_text() for d in sorted(documents)}
    refs = given["source"]["references"]
    reference_text = (citations / refs["document"]).read_text() if refs else ""
    nth: collections.Counter = collections.Counter()
    paper_rows = {}
    for g in given["rows"]:
        nth[g["side"]] += 1
        paper_rows[f"{g['side']}_{nth[g['side']]}"] = g
    by_key = collections.defaultdict(list)
    for r in attempt["rows"]:
        by_key[(r["side"], r["name_as_written"])].append(r)
    rows, missing = [], []
    for g in given["rows"]:
        coded = by_key.pop((g["side"], g["name_as_written"]), [])
        if len(coded) != 1:
            missing.append([g["side"], g["name_as_written"]])
            continue
        rows.append(gate_row(coded[0], g, dictionary, texts, reference_text, citations,
                             paper_rows))
    wrong_coder = attempt["coder_id"] != given["coder_id"]
    return {"record_id": given["record_id"], "coder_id": attempt["coder_id"],
            "attempt": attempt["attempt"], "rows": rows,
            "rows_not_coded_once": missing, "rows_not_given": sorted(map(list, by_key)),
            "wrong_coder": wrong_coder,
            "passes": (not missing and not by_key and not wrong_coder
                       and all(r["passes"] for r in rows))}


def for_coder(result: dict) -> dict:
    """The gate result a coder is given: the failing rows by side and name with their
    failures, and no coded value or basis."""
    return {"record_id": result["record_id"], "coder_id": result["coder_id"],
            "attempt": result["attempt"], "passes": result["passes"],
            "rows_not_coded_once": result["rows_not_coded_once"],
            "rows_not_given": result["rows_not_given"],
            "failing_rows": [{"side": r["side"], "name_as_written": r["name_as_written"],
                              "failures": r["failures"]}
                             for r in result["rows"] if not r["passes"]]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coders", type=pathlib.Path, required=True)
    ap.add_argument("--citations", type=pathlib.Path, required=True)
    a = ap.parse_args()
    with DICTIONARY.open(newline="") as f:
        dictionary = {(r["side"], r["name"]): r for r in csv.DictReader(f)}
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    env = {k: v for k, v in os.environ.items() if k != "CITATIONS_HOME"}
    verify = subprocess.run(["citations", "verify", "--claims", "claims", "--strict"],
                            capture_output=True, text=True, env=env, cwd=a.citations)
    (a.coders / f"citations_verify_v2_{stamp}.txt").write_text(
        f"exit {verify.returncode}\n{verify.stdout}\n{verify.stderr}".replace(
            f"{a.citations.resolve()}/", ""))
    counts: collections.Counter = collections.Counter()
    for path in sorted(a.coders.glob("coder_*/codes/*.json")):
        m = ATTEMPT.match(path.name)
        if not m:
            raise GateError(f"{path}: not an attempt file")
        coder = path.parent.parent
        target = coder / GATES / f"{m['name']}.attempt{m['n']}.gate.json"
        if target.exists():
            continue
        given_path = coder / "input" / f"{m['name']}.json"
        if not given_path.is_file():
            raise GateError(f"{path}: no input file {given_path}")
        result = gate_attempt(json.loads(path.read_text()), json.loads(given_path.read_text()),
                              dictionary, a.citations)
        result["gated_utc"] = stamp
        target.parent.mkdir(exist_ok=True)
        target.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
        shown = coder / FOR_CODER / target.name
        shown.parent.mkdir(exist_ok=True)
        shown.write_text(json.dumps(for_coder(result), indent=1, ensure_ascii=False) + "\n")
        counts["attempts_gated"] += 1
        counts["attempts_passed" if result["passes"] else "attempts_failed"] += 1
        counts["rows_failed"] += sum(not r["passes"] for r in result["rows"])
    print(json.dumps({"citations_verify_exit": verify.returncode, **counts}, indent=1))


if __name__ == "__main__":
    main()
