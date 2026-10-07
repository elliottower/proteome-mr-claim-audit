# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.13.5"]
# ///
"""Deterministic checks of each extracted claim against its evidence span. No model is called.

    span       the span passed verify_spans.py (registered quote check and `citations` pin)
    protein    the protein Sol named maps to at least one HGNC entry, trying in order (1) the
               approved symbol, (2) the approved name and the UniProtKB/Swiss-Prot protein
               names of the entry's UniProt accession, (3) alias and previous symbols and
               names, and stopping at the first tier with a hit; and a name of a mapped entry
               occurs in the span. More than one entry in the winning tier is counted as
               ambiguous, not failed
    evidence   Sol's `evidence_type` is `mr_estimate`; every other type is counted and kept
               out of the registry (`not_mr_estimate`)
    outcome    the outcome Sol named maps to at least one Mondo or EFO term (or a term EFO
               imports from HP, OBA or Orphanet), trying in order (1) the committed alias
               table verification/outcome_aliases.csv, (2) term labels and EXACT synonyms,
               (3) the labels of obsolete EFO terms, each standing for the live term the EFO
               file names as its replacement (verification/obsolete_label_replacements.csv;
               scripts/outcome_alias_completion.py), (4) RELATED synonyms, each also with
               " measurement" appended (EFO's trait labels), and stopping at the first tier
               with a hit; and the matched name or a label or synonym of a mapped term occurs
               in the span. A record mapped through the alias table carries the relation the
               table gives its alias (`outcome_alias_relation`)
    direction  the estimate parser reads the effect estimate printed nearest the outcome
               mention in the span (odds, hazard or risk ratio, or a difference such as a
               beta, SD or unit change, with its interval and/or P value): its sign or ratio
               gives the direction, and it is `reported_nonsignificant_or_null` when the printed
               interval includes the null value (1 for ratios, 0 for differences) or, with no
               interval, when P >= 0.05. When no estimate can be assigned to the outcome, the
               committed lexicon (verification/direction_lexicon.json) reads cue words, and a
               span stating no association reads `reported_nonsignificant_or_null`.
               `direction_unverified` when neither decides, `not_applicable` when Sol gave
               `not_stated`. Tie-breaking (`parse_direction`): each estimate claims the text on
               one side of it; an outcome mention inside several estimates' text is resolved to
               the one preceded by an MR cue; if several remain, their directions must agree,
               else no estimate is assigned. The lexicon never reads printed ratios, and a
               lexicon reading of a span shared by claims of both directions is
               `direction_unverified`
    datasets   each dataset name mapped, on its side, to its candidate rows of the dataset
               dictionary by `dataset_relations.map_name` (unique, release_ambiguous, unmatched,
               not_stated); never a first match
    relation   a claim Sol flagged `relation_ambiguous` (a protein and an outcome listed
               together without wording that links them) is kept out of the registry and counted

A claim enters the registry when span, evidence type, protein, outcome and relation pass. Its
direction enters direction-based results only when the direction check agrees. Every other claim
is counted by its first failing check, and its record is written in full with that reason.

Every record carries its mapping provenance: `protein_mapping_state`, `outcome_mapping_state`
(`mapped`, `ambiguous` when the winning tier gives more than one identifier, `unmapped`,
`not_in_span`), `dataset_mapping_state`, `direction_verification_state`, `mapping_rule_used`
(the tier that matched, per field) and `candidate_identifier_count` (per field). Sol's text is
never overwritten.

The reference files are the registered ones in reference/MANIFEST.json (RELEASES.md); each is
re-hashed before use and a mismatch raises. Outputs from prompt revisions before r8 are read with
`null` renamed to `reported_nonsignificant_or_null` and the fields r8 added set to
`not_in_revision`.

Names are compared after folding: Greek letters spelled out, accents removed, lower case,
every run of non-alphanumeric characters removed, so `IL-6R`, `IL6R` and `il 6 r` agree. A name
occurs in the span when its folded form equals the folded join of one to eight consecutive
span tokens. Folded names shorter than two characters are never matched.

Usage: uv run scripts/verify_claims.py --extraction outputs/parsed/sol_extraction_r2_<rev>.jsonl
"""

import argparse
import collections
import csv
import json
import pathlib
import re
import hashlib
import unicodedata

from pydantic import BaseModel

from dataset_relations import load_rows, map_name

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
REF = EXP / "reference"
LEXICON = EXP / "verification" / "direction_lexicon.json"
DATASET_DICTIONARY = EXP / "dataset_dictionary.csv"
NONSIG = "reported_nonsignificant_or_null"
NOT_IN_REVISION = "not_in_revision"
PROTEIN_TIERS = ("approved_symbol", "approved_or_uniprot_name", "alias_or_previous")
OUTCOME_TIERS = ("alias_table", "label_or_exact_synonym", "obsolete_label_replacement",
                 "related_synonym")
OUTCOME_ALIASES = EXP / "verification" / "outcome_aliases.csv"
OBSOLETE_LABELS = EXP / "verification" / "obsolete_label_replacements.csv"
OUTCOME_PREFIXES = ("MONDO:", "EFO:", "HP:", "OBA:", "Orphanet:")
MAX_WINDOW = 8
GREEK = {"α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon", "κ": "kappa",
         "λ": "lambda", "μ": "mu", "ω": "omega", "τ": "tau", "θ": "theta", "ζ": "zeta",
         "Α": "alpha", "Β": "beta", "Γ": "gamma", "Δ": "delta"}
PROTEIN_LEAD = ("circulating", "plasma", "serum", "blood", "genetically", "predicted",
                "determined", "elevated", "higher", "lower", "high", "low", "increased",
                "decreased", "levels of", "level of", "concentration of", "concentrations of")
PROTEIN_TAIL = ("levels", "level", "concentration", "concentrations", "protein levels")
OUTCOME_LEAD = ("risk of", "incident", "prevalent", "increased", "decreased", "higher", "lower",
                "circulating", "log", "serum", "plasma", "the", "a", "an")
OUTCOME_TAIL = ("risk", "events", "event", "levels", "level", "concentration",
                "concentrations", "decline")


class VerifyError(Exception):
    """A required input is missing or inconsistent."""


class DatasetMapping(BaseModel):
    written: str
    side: str
    state: str
    rule: str
    candidates: list[str]


class ClaimCheck(BaseModel):
    pmid: str
    claim_index: int
    claim_record_id: str
    protein_as_written: str
    outcome_as_written: str
    direction: str
    evidence_type: str
    claim_scope: str
    analysis_context_as_written: str
    subgroup_as_written: str
    relation_ambiguous: bool | str
    dataset_attribution: str
    pqtl_datasets: list[str]
    outcome_datasets: list[str]
    span_passes: bool
    protein_ids: list[str]
    protein_check: str
    protein_mapping_state: str
    outcome_ids: list[str]
    outcome_check: str
    outcome_mapping_state: str
    outcome_alias_relation: str | None
    direction_check: str
    direction_verification_state: str
    parsed_direction: str | None
    direction_method: str
    dataset_mappings: list[DatasetMapping]
    dataset_mapping_state: str
    mapping_rule_used: dict[str, str]
    candidate_identifier_count: dict[str, int]
    enters_registry: bool
    enters_direction_results: bool
    first_failure: str | None


def fold_tokens(text: str) -> list[str]:
    for g, name in GREEK.items():
        text = text.replace(g, f" {name} ")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return [t for t in re.split(r"[^a-z0-9]+", text) if t]


def compact(text: str) -> str:
    return "".join(fold_tokens(text))


def windows(text: str) -> set[str]:
    toks = fold_tokens(text)
    return {"".join(toks[i:i + n]) for n in range(1, MAX_WINDOW + 1)
            for i in range(len(toks) - n + 1)}


def strip_affixes(text: str, lead: tuple[str, ...], tail: tuple[str, ...]) -> set[str]:
    out, s = {text}, text.strip()
    changed = True
    while changed:
        changed = False
        low = s.lower()
        for w in lead:
            if low.startswith(w + " "):
                s, changed = s[len(w) + 1:].strip(), True
                break
        low = s.lower()
        for w in tail:
            if low.endswith(" " + w):
                s, changed = s[:-(len(w) + 1)].strip(), True
                break
        out.add(s)
    return out


def variants(text: str, lead: tuple[str, ...], tail: tuple[str, ...]) -> set[str]:
    base = {text}
    inside = re.findall(r"\(([^()]*)\)", text)
    base.update(inside)
    base.add(re.sub(r"\([^()]*\)", " ", text))
    out: set[str] = set()
    for b in base:
        for v in strip_affixes(b, lead, tail):
            out.add(v)
            if v.endswith("s") and len(v) > 4:
                out.add(v[:-1])
    return {v for v in out if len(compact(v)) >= 2}


def top_level_parentheticals(text: str) -> tuple[str, list[str]]:
    """UniProt protein_name: 'Recommended (alt 1) (alt 2) [Cleaved into: ...]'."""
    text = re.sub(r"\[.*\]", "", text)
    head, alts, depth, cur = [], [], 0, []
    for ch in text:
        if ch == "(":
            if depth == 0:
                cur = []
            else:
                cur.append(ch)
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                alts.append("".join(cur).strip())
            else:
                cur.append(ch)
        elif depth == 0:
            head.append(ch)
        else:
            cur.append(ch)
    return "".join(head).strip(), [a for a in alts if a]


def file_sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> dict:
    path = REF / "MANIFEST.json"
    if not path.exists():
        raise VerifyError("reference/MANIFEST.json missing; see RELEASES.md")
    manifest = json.loads(path.read_text())
    for name, spec in manifest.items():
        f = EXP / spec["file"]
        if not f.exists():
            raise VerifyError(f"{spec['file']} missing; fetch it from the Modal volume "
                              "(inputs/README_MOVED_TO_MODAL.md)")
        if file_sha256(f) != spec["sha256"]:
            raise VerifyError(f"{spec['file']}: sha256 differs from reference/MANIFEST.json")
    return manifest


def build_protein_index(
        manifest: dict) -> tuple[list[dict[str, set[str]]], dict[str, set[str]]]:
    """Three tiers of folded name -> HGNC IDs, tried in order: approved symbol; approved name
    and UniProt protein names; alias and previous symbols and names. Also HGNC ID -> every
    name (raw) of that entry, for the span check."""
    names: dict[str, set[str]] = collections.defaultdict(set)
    tiers: list[dict[str, set[str]]] = [collections.defaultdict(set) for _ in range(3)]

    def add(tier: int, hid: str, value: str) -> None:
        c = compact(value)
        if len(c) >= 2:
            tiers[tier][c].add(hid)

    uniprot_to_hgnc: dict[str, set[str]] = collections.defaultdict(set)
    with (EXP / manifest["hgnc"]["file"]).open() as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["status"] != "Approved":
                continue
            hid = row["hgnc_id"]
            add(0, hid, row["symbol"])
            add(1, hid, row["name"])
            add(1, hid, row["name"].split(",")[0])
            vals = [row["symbol"], row["name"], row["name"].split(",")[0]]
            for col in ("alias_symbol", "prev_symbol", "alias_name", "prev_name"):
                extra = [v.strip() for v in row[col].strip('"').split("|") if v.strip()]
                for v in extra:
                    add(2, hid, v)
                vals += extra
            names[hid].update(v for v in vals if v)
            for acc in row["uniprot_ids"].split("|"):
                if acc.strip():
                    uniprot_to_hgnc[acc.strip()].add(hid)
    with (EXP / manifest["uniprot"]["file"]).open() as f:
        for row in csv.DictReader(f, delimiter="\t"):
            head, alts = top_level_parentheticals(row["Protein names"])
            for hid in uniprot_to_hgnc.get(row["Entry"], ()):
                names[hid].update([head, *alts])
                for v in (head, *alts):
                    add(1, hid, v)
    return tiers, names


def canonical_id(raw: str) -> str:
    """EFO's obo writes `efo:EFO_0004340`; Mondo writes `MONDO:0005010`. Both become PREFIX:N."""
    m = re.fullmatch(r"[A-Za-z]+:([A-Za-z]+)_(\w+)", raw)
    return f"{m.group(1)}:{m.group(2)}" if m else raw


def parse_obo(path: pathlib.Path) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """(term ID -> label and EXACT synonyms, term ID -> RELATED synonyms), obsolete dropped."""
    terms: dict[str, set[str]] = {}
    related: dict[str, set[str]] = {}
    tid, vals, rel, obsolete, in_term = None, set(), set(), False, False

    def flush() -> None:
        if in_term and tid and not obsolete and tid.startswith(OUTCOME_PREFIXES):
            terms.setdefault(tid, set()).update(vals)
            related.setdefault(tid, set()).update(rel)

    with path.open() as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("["):
                flush()
                in_term, tid, vals, rel, obsolete = line == "[Term]", None, set(), set(), False
            elif line.startswith("id: "):
                tid = canonical_id(line[4:].strip())
            elif line.startswith("name: "):
                vals.add(line[6:].strip())
            elif line.startswith("synonym: ") and " EXACT" in line:
                m = re.match(r'synonym: "((?:[^"\\]|\\.)*)" EXACT', line)
                if m:
                    vals.add(m.group(1).replace('\\"', '"'))
            elif line.startswith("synonym: ") and " RELATED" in line:
                m = re.match(r'synonym: "((?:[^"\\]|\\.)*)" RELATED', line)
                if m:
                    rel.add(m.group(1).replace('\\"', '"'))
            elif line.startswith("is_obsolete: true"):
                obsolete = True
        flush()
    return terms, related


def label_index(manifest: dict) -> tuple[dict[str, set[str]], dict[str, set[str]],
                                         dict[str, set[str]]]:
    """(folded label or EXACT synonym -> term IDs, folded RELATED synonym -> term IDs, term ID
    -> its labels and EXACT synonyms) over the live terms of the pinned files."""
    names: dict[str, set[str]] = collections.defaultdict(set)
    related: dict[str, set[str]] = collections.defaultdict(set)
    for src in ("mondo", "efo"):
        exact, rel = parse_obo(EXP / manifest[src]["file"])
        for tid, vals in exact.items():
            names[tid].update(vals)
        for tid, vals in rel.items():
            related[tid].update(vals)
    exact_index: dict[str, set[str]] = collections.defaultdict(set)
    related_index: dict[str, set[str]] = collections.defaultdict(set)
    for tid, vals in names.items():
        for v in vals:
            c = compact(v)
            if len(c) >= 2:
                exact_index[c].add(tid)
    for tid, vals in related.items():
        for v in vals:
            c = compact(v)
            if len(c) >= 2:
                related_index[c].add(tid)
    return exact_index, related_index, names


def surface_index(path: pathlib.Path, names: dict[str, set[str]]) -> dict[str, set[str]]:
    """Folded `surface` -> `term_id` of a committed table; a term that is not live raises."""
    if not path.exists():
        raise VerifyError(f"{path} missing; build it with the resource tables "
                          "(scripts/modal_biology_joins.py::resource_tables)")
    index: dict[str, set[str]] = collections.defaultdict(set)
    with path.open() as f:
        for row in csv.DictReader(f):
            if row["term_id"] not in names:
                raise VerifyError(f"{path.name}: {row['surface']!r} names {row['term_id']}, "
                                  "not a live term of the pinned files; rebuild the table")
            c = compact(row["surface"])
            if len(c) >= 2:
                index[c].add(row["term_id"])
    return index


def build_outcome_index(manifest: dict, aliases: pathlib.Path = OUTCOME_ALIASES,
                        obsolete: pathlib.Path = OBSOLETE_LABELS
                        ) -> tuple[list[dict[str, set[str]]], dict[str, set[str]]]:
    """Four tiers: the committed alias table; labels and EXACT synonyms; the labels of obsolete
    EFO terms with their replacements; RELATED synonyms."""
    exact_index, related_index, names = label_index(manifest)
    return [surface_index(aliases, names), exact_index, surface_index(obsolete, names),
            related_index], names


def alias_relations(path: pathlib.Path = OUTCOME_ALIASES) -> dict[str, str]:
    """Folded alias surface -> the relation the alias table gives it."""
    with path.open() as f:
        return {compact(r["surface"]): r["alias_relation"] for r in csv.DictReader(f)}


def outcome_keys(written: str) -> set[str]:
    """The folded forms an outcome name is looked up under."""
    keys = {compact(v) for v in variants(written, OUTCOME_LEAD, OUTCOME_TAIL)}
    return keys | {k + "measurement" for k in keys}


def map_and_check(written: str, span: str, tiers: list[dict[str, set[str]]],
                  names: dict[str, set[str]], lead: tuple[str, ...],
                  tail: tuple[str, ...], kind: str) -> tuple[list[str], str, int | None]:
    """Map through the first tier with any hit, then require the name in the span.

    The span check passes when a matching key (Sol's name after the registered affix
    stripping) or any name of a mapped entry occurs in the span. For outcomes a trailing
    " measurement" is ignored, because EFO labels traits "X measurement" and abstracts write X.
    """
    keys = outcome_keys(written) if kind == "outcome" else {
        compact(v) for v in variants(written, lead, tail)}
    ids: set[str] = set()
    hit_keys: set[str] = set()
    tier_used = None
    for t, tier in enumerate(tiers):
        for k in keys:
            if tier.get(k):
                ids |= tier[k]
                hit_keys.add(k)
        if ids:
            tier_used = t
            break
    if not ids:
        return [], f"{kind}_unmapped", None
    candidates = set(hit_keys)
    for i in ids:
        candidates |= {compact(n) for n in names[i]}
    if kind == "outcome":
        candidates |= {c.removesuffix("measurement") for c in candidates}
    span_windows = windows(span)
    if any(len(c) >= 2 and c in span_windows for c in candidates):
        return sorted(ids), "pass", tier_used
    return sorted(ids), f"{kind}_not_in_span", tier_used


class Lexicon:
    def __init__(self, spec: dict) -> None:
        def rx(words: list[str]) -> re.Pattern:
            alt = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
            return re.compile(rf"(?<![A-Za-z0-9-])(?:{alt})(?![A-Za-z0-9-])", re.IGNORECASE)
        self.up, self.down = rx(spec["up"]), rx(spec["down"])
        self.null, self.contrast = rx(spec["null"]), rx(spec["contrast"])
        ratio_alt = "|".join(re.escape(w) for w in sorted(spec["ratio_names"], key=len,
                                                           reverse=True))
        self.ratio = re.compile(rf"\b(?:{ratio_alt})\b[^0-9.·]{{0,40}}?(\d*[.·]?\d+)")

    def read(self, span: str, single_claim: bool) -> tuple[str | None, bool]:
        """(direction the lexicon reads or None, whether a null cue is present).

        Printed ratios are read only when the span supports a single claim: a span listing
        several outcomes prints one ratio per outcome, and nothing here assigns ratios to
        outcomes."""
        has_null = bool(self.null.search(span))
        n_up, n_down = len(self.up.findall(span)), len(self.down.findall(span))
        cue_sign = None
        if 1 <= n_up + n_down <= 2 and not self.contrast.search(span):
            cue_sign = 1 if n_down % 2 == 0 else -1
        ratios = ([float(v.replace("·", ".")) for v in self.ratio.findall(span)]
                  if single_claim else [])
        ratio_sign = None
        if ratios and all(r > 1 for r in ratios):
            ratio_sign = 1
        elif ratios and all(r < 1 for r in ratios):
            ratio_sign = -1
        if cue_sign is not None and ratio_sign is not None and cue_sign != ratio_sign:
            return None, has_null
        sign = cue_sign if cue_sign is not None else ratio_sign
        return (None if sign is None else "raises" if sign > 0 else "lowers"), has_null


NUM = r"(?:[-−]\s?)?(?:\d+(?:[.·]\d+)?|[.·]\d+)"
# An estimate is a number not glued to a word ("IL-10", "type 2"): no letter, digit or
# decimal point before it, and no letter-hyphen before it.
EST = rf"(?<![A-Za-z0-9.·])(?<![A-Za-z]-)(?P<est>{NUM})"
# Units between an estimate and its interval: letters, µ, %, slashes and spaces, with digits
# only after a slash or a letter ("ml/min/1.73 m2"); never a comma, so a following estimate
# in a list is not swallowed.
UNIT = r"(?P<unit>(?:[A-Za-zµ%/\s]|(?<=/)[\d.]+|(?<=[A-Za-z])\d){0,30}?)"
CI_PREFIX = r"(?:95\s?%\s*(?:CI|confidence interval)(?:\s*\[CI\])?\s*[:,]?\s*)"
SEP = r"\s*(?:-|–|—|to|;|,)\s*"
ESTIMATE_PATTERNS = [
    # 1.15 (1.08-1.22 ...  /  OR 0.86 [95% CI 0.79-0.94]  /  0.01 ml/min/1.73 m2 (95% CI ...
    re.compile(rf"{EST}{UNIT}\s*[(\[]\s*{CI_PREFIX}?"
               rf"(?P<lo>{NUM}){SEP}(?P<hi>{NUM})", re.IGNORECASE),
    # 0.85 µg/ml, 95 % confidence interval 0.80 to 0.90  /  9·45%, 95% CI 8·34-10·57
    re.compile(rf"{EST}{UNIT}\s*[;,]?\s*{CI_PREFIX}"
               rf"(?P<lo>{NUM}){SEP}(?P<hi>{NUM})", re.IGNORECASE),
    # estimate -0.19, p=6.46×10-03
    re.compile(rf"(?:estimate|β|beta|OR|HR|RR)\s*[=:]?\s*(?P<est>{NUM})(?P<unit>)\s*,?\s*\(?\s*"
               rf"(?=[pP]\s*[=<>≤≥])", re.IGNORECASE),
]
P_VALUE = re.compile(rf"\b[pP]\s*(?P<op>=|<|>|≤|≥)\s*(?P<v>{NUM})"
                     r"(?:\s*[×x]\s*10\s*\(?\s*(?P<e1>[-−]?\s*\d+)\s*\)?|[eE](?P<e2>[-−]?\d+))?")
RATIO_WORDS = re.compile(r"\b(?:ORs?|odds ratios?|HRs?|hazards? ratios?|RRs?|risk ratios?|"
                         r"relative risks?|odds|risk)\b", re.IGNORECASE)
DIFF_WORDS = re.compile(r"(?:\bbeta\b|β|\bestimate\b|\bmmol|mm ?Hg|g/dl|ml/min|mg/dl|"
                        r"%|\bper ?cent\b|\bunits?\b|\bincrease of\b|\bdecrease of\b)",
                        re.IGNORECASE)
UNIT_AFTER = re.compile(r"^[\s)\]]*(?:mm ?Hg|g/dl|ml/min|mmol|mg/dl|%|SD\b|units?\b|µg/ml|"
                        r"ng/ml)", re.IGNORECASE)
AFTER_OUTCOME = re.compile(r"^[\s)\],]*(?:(?:mm ?Hg|g/dl|ml/min\S*|mmol/l|mg/dl|%|SD|units?|"
                           r"µg/ml)\s*)?(?:for|in|on)\b", re.IGNORECASE)
DOWN_BEFORE = re.compile(r"(?:decreas\w*|reduc\w*|lower\w*|declin\w*)\W*(?:\w+\W+){0,3}$",
                         re.IGNORECASE)
# "95% CI" names the interval, not a percentage scale; it is masked before scale cues are read.
CI_LABEL = re.compile(r"95\s?%\s*(?:CI\b|confidence interval)", re.IGNORECASE)
MR_CUES = re.compile(r"\b(?:causal\w*|genetic\w*|mendelian|instrument\w*|allele\w*|variants?|"
                     r"snps?|IV|per-allele|MR)\b", re.IGNORECASE)


# Corrected copy of verify_claims.py (PREREG.md log, 2026-10-07). NUM and the exponent of P_VALUE
# admit any white-space character (`\s`) after a sign; the two number conversions below strip
# every such character, where verify_claims.py strips the ordinary space only and raises on a
# thin or no-break space. Nothing else differs.
WHITE_SPACE = re.compile(r"\s")


def to_float(num: str) -> float:
    return float(WHITE_SPACE.sub("", num.replace("·", ".").replace("−", "-")))


class Estimate(BaseModel):
    start: int
    end: int
    unit_text: str
    est: float
    lo: float | None
    hi: float | None
    p: float | None
    p_op: str | None


def find_estimates(span: str) -> list[Estimate]:
    found: list[Estimate] = []
    for pat in ESTIMATE_PATTERNS:
        for m in pat.finditer(span):
            start = m.start("est")
            if any(e.start <= start < e.end for e in found):
                continue
            close = min([i for i in (span.find(")", m.end()), span.find("]", m.end()))
                         if i != -1 and i - m.end() < 80] or [m.end()])
            end = max(close + 1, m.end())
            pm = P_VALUE.search(span, m.end(), min(len(span), end + 5))
            p = op = None
            if pm:
                p = to_float(pm.group("v"))
                exp = pm.group("e1") or pm.group("e2")
                if exp:
                    p *= 10 ** int(WHITE_SPACE.sub("", exp.replace("−", "-")))
                op = pm.group("op")
            lo = to_float(m.group("lo")) if "lo" in m.groupdict() and m.group("lo") else None
            hi = to_float(m.group("hi")) if "hi" in m.groupdict() and m.group("hi") else None
            found.append(Estimate(start=start, end=end, unit_text=m.group("unit") or "",
                                  est=to_float(m.group("est")), lo=lo, hi=hi, p=p, p_op=op))
    return sorted(found, key=lambda e: e.start)


def outcome_positions(span: str, written: str) -> list[int]:
    low = span.lower()
    out: list[int] = []
    for v in sorted(variants(written, OUTCOME_LEAD, OUTCOME_TAIL), key=len, reverse=True):
        i = low.find(v.lower())
        while i != -1:
            out.append(i)
            i = low.find(v.lower(), i + 1)
        if out:
            break
    return out


def estimate_direction(span: str, e: Estimate, prev_end: int) -> str | None:
    span = CI_LABEL.sub(lambda m: " " * len(m.group()), span)
    before = span[prev_end:e.start]
    near = before[-60:]
    after = span[e.end:e.end + 20]
    scale = None
    if RATIO_WORDS.search(near):
        scale = "ratio"
    elif e.est < 0 or (e.lo is not None and e.lo < 0):
        scale = "difference"
    elif e.unit_text.strip() or UNIT_AFTER.match(after):
        scale = "difference"
    else:
        r = [m.end() for m in RATIO_WORDS.finditer(span[:e.start])]
        d = [m.end() for m in DIFF_WORDS.finditer(span[:e.start])]
        if r and (not d or r[-1] > d[-1]):
            scale = "ratio"
        elif d:
            scale = "difference"
    if scale is None:
        return None
    null = 1.0 if scale == "ratio" else 0.0
    down_word = scale == "difference" and bool(DOWN_BEFORE.search(before[-40:]))
    if e.lo is not None and e.hi is not None:
        lo, hi = min(e.lo, e.hi), max(e.lo, e.hi)
        if lo <= null <= hi:
            return NONSIG
        above = lo > null
        # A magnitude printed with "decreased by" and a positive interval is a decrease; an
        # interval already printed below zero carries its own sign.
        if above and down_word:
            above = False
        return "raises" if above else "lowers"
    if e.p is None:
        return None
    if e.p_op in (">", "≥") or (e.p_op == "=" and e.p >= 0.05):
        return NONSIG
    if e.est == null:
        return NONSIG
    above = e.est > null
    if above and down_word:
        above = False
    return "raises" if above else "lowers"


TABLE_ROW = re.compile(r"^\[Table[^\]]*\] ")


def table_cells_for_outcome(span: str, outcome_written: str) -> str | None:
    """For a table row rendered by fetch_fulltext.py, the cells whose column header names the
    outcome, joined by " ; "; None when the span is not a table row or no header names it."""
    m = TABLE_ROW.match(span)
    if not m:
        return None
    cells = span[m.end():].split(" | ")
    keep = [c for c in cells
            if ": " in c and outcome_positions(c.split(": ", 1)[0], outcome_written)]
    return " ; ".join(keep) if keep else None


def parse_direction(span: str, outcome_written: str) -> str | None:
    """Direction of the estimate assigned to the outcome, or None when none can be assigned.

    Each estimate claims the text on one side of it: the text after it when that text begins
    with "for", "in" or "on" (after an optional unit), as in "0.97 (0.95-0.99) for rheumatoid
    arthritis"; otherwise the text since the previous estimate, as in "coronary artery disease
    (OR 0.88 ...)". An outcome mention inside several estimates' text is resolved to the one
    preceded by an MR cue; if several remain, their directions must agree. A full-text table
    row is first narrowed to the cells whose column header names the outcome."""
    span = table_cells_for_outcome(span, outcome_written) or span
    ests = find_estimates(span)
    positions = outcome_positions(span, outcome_written)
    if not ests or not positions:
        return None
    segments = []
    for k, e in enumerate(ests):
        prev_end = ests[k - 1].end if k else 0
        next_start = ests[k + 1].start if k + 1 < len(ests) else len(span)
        if AFTER_OUTCOME.match(span[e.end:next_start]):
            segments.append((e.end, next_start))
        else:
            segments.append((prev_end, e.start))
    # In "ORs were 1.12 (...) and .98 (...)" the second estimate's own text is only a
    # connector; it shares the outcome of the estimate before it.
    merged = False
    for k in range(1, len(segments)):
        a, b = segments[k]
        if re.fullmatch(r"[\s,;]*(?:and|or|respectively|vs\.?|versus)?[\s,;]*", span[a:b]):
            segments[k] = segments[k - 1]
            merged = True
    hits = sorted({k for k, (a, b) in enumerate(segments) for p in positions if a <= p < b})
    if not hits:
        return None
    # A list of estimates sharing one outcome ("were A and B") gives no way to tell which is
    # the genetic estimate, so the MR-cue preference is not applied to it.
    if len(hits) > 1 and not merged:
        cued = [k for k in hits if MR_CUES.search(span[max(0, ests[k].start - 100):ests[k].start])]
        if len(cued) == 1:
            hits = cued
    dirs = {estimate_direction(span, ests[k], ests[k - 1].end if k else 0) for k in hits}
    if len(dirs) != 1 or None in dirs:
        return None
    return dirs.pop()


def direction_check(sol: str, derived: str | None) -> str:
    if sol == "not_stated":
        return "not_applicable"
    if derived is None:
        return "direction_unverified"
    return "agrees" if derived == sol else "disagrees"


def mapping_state(check: str, ids: list[str]) -> str:
    if check.endswith("_unmapped"):
        return "unmapped"
    if check.endswith("_not_in_span"):
        return "not_in_span"
    return "ambiguous" if len(ids) > 1 else "mapped"


def claims_state(maps: list[DatasetMapping]) -> str:
    states = {m.state for m in maps}
    if states <= {"not_stated"}:
        return "not_stated"
    if "unmatched" in states:
        return "some_unmatched"
    if "release_ambiguous" in states:
        return "some_release_ambiguous"
    return "not_stated_on_one_side" if "not_stated" in states else "all_unique"


def legacy(c: dict) -> dict:
    """Read a claim from a revision before r8: `null` renamed, r8 fields marked absent."""
    c = dict(c)
    if c["direction"] == "null":
        c["direction"] = NONSIG
    for field in ("claim_scope", "analysis_context_as_written", "subgroup_as_written",
                  "dataset_attribution", "relation_ambiguous"):
        c.setdefault(field, NOT_IN_REVISION)
    return c


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extraction", type=pathlib.Path, required=True)
    a = ap.parse_args()
    run = a.extraction.stem
    span_file = EXP / "outputs" / "verification" / run / "spans.jsonl"
    if not span_file.exists():
        raise VerifyError(f"{span_file} missing; run scripts/verify_spans.py first")
    spans = {(r["pmid"], r["claim_index"]): r["passes"]
             for r in map(json.loads, span_file.read_text().splitlines())}

    manifest = load_manifest()
    p_index, p_names = build_protein_index(manifest)
    o_index, o_names = build_outcome_index(manifest)
    relation_of = alias_relations()
    lexicon = Lexicon(json.loads(LEXICON.read_text()))
    rows = load_rows()
    out_dir = EXP / "outputs" / "verification" / run
    if (out_dir / "claim_checks.jsonl").exists():
        raise VerifyError(f"{out_dir}/claim_checks.jsonl exists; archive it before rerunning")

    checks: list[ClaimCheck] = []
    for row in map(json.loads, a.extraction.read_text().splitlines()):
        if row["status"] != "ok":
            continue
        claims = [legacy(c) for c in row["output"]["claims"]]
        span_dirs: dict[str, set[str]] = collections.defaultdict(set)
        for c in claims:
            if c["direction"] in ("raises", "lowers"):
                span_dirs[c["evidence_span"]].add(c["direction"])
        for i, c in enumerate(claims):
            span = c["evidence_span"]
            p_ids, p_check, p_tier = map_and_check(c["protein_as_written"], span, p_index,
                                                   p_names, PROTEIN_LEAD, PROTEIN_TAIL,
                                                   "protein")
            o_ids, o_check, o_tier = map_and_check(c["outcome_as_written"], span, o_index,
                                                   o_names, OUTCOME_LEAD, OUTCOME_TAIL,
                                                   "outcome")
            parsed = parse_direction(span, c["outcome_as_written"])
            method = "estimate"
            if parsed is None:
                lex_dir, has_null = lexicon.read(span, False)
                method = "lexicon"
                parsed = NONSIG if has_null and c["direction"] == NONSIG else lex_dir
                if parsed in ("raises", "lowers") and len(span_dirs[span]) > 1:
                    # One span-level cue reading cannot agree with claims of both directions.
                    parsed, method = None, "lexicon_mixed_span"
                if parsed is None:
                    method = "none"
            d_check = direction_check(c["direction"], parsed)
            span_ok = spans[(row["pmid"], i)]
            is_mr = c["evidence_type"] == "mr_estimate"
            failure = next((f for f, ok in (("span_not_verified", span_ok),
                                            ("not_mr_estimate", is_mr),
                                            (p_check, p_check == "pass"),
                                            (o_check, o_check == "pass"),
                                            ("relation_ambiguous",
                                             c["relation_ambiguous"] is not True)) if not ok),
                           None)
            enters = failure is None
            maps = [DatasetMapping(written=m.written, side=m.side, state=m.state, rule=m.rule,
                                   candidates=list(m.candidates))
                    for side, field in (("pqtl", "pqtl_datasets"),
                                        ("outcome", "outcome_datasets"))
                    for m in (map_name(n, side, rows) for n in c[field])]
            checks.append(ClaimCheck(
                pmid=row["pmid"], claim_index=i, claim_record_id=f"{row['pmid']}:{i:03d}",
                protein_as_written=c["protein_as_written"],
                outcome_as_written=c["outcome_as_written"], direction=c["direction"],
                evidence_type=c["evidence_type"], claim_scope=c["claim_scope"],
                analysis_context_as_written=c["analysis_context_as_written"],
                subgroup_as_written=c["subgroup_as_written"],
                relation_ambiguous=c["relation_ambiguous"],
                dataset_attribution=c["dataset_attribution"],
                pqtl_datasets=c["pqtl_datasets"], outcome_datasets=c["outcome_datasets"],
                span_passes=span_ok, protein_ids=p_ids, protein_check=p_check,
                protein_mapping_state=mapping_state(p_check, p_ids),
                outcome_ids=o_ids, outcome_check=o_check,
                outcome_mapping_state=mapping_state(o_check, o_ids),
                outcome_alias_relation="|".join(sorted({
                    relation_of[k] for k in outcome_keys(c["outcome_as_written"])
                    if k in relation_of})) if o_tier == 0 else None,
                direction_check=d_check, direction_verification_state=d_check,
                parsed_direction=parsed, direction_method=method,
                dataset_mappings=maps, dataset_mapping_state=claims_state(maps),
                mapping_rule_used={
                    "protein": PROTEIN_TIERS[p_tier] if p_tier is not None else "none",
                    "outcome": OUTCOME_TIERS[o_tier] if o_tier is not None else "none",
                    "direction": method,
                    "datasets": ",".join(sorted({m.rule for m in maps})) or "none"},
                candidate_identifier_count={
                    "protein": len(p_ids), "outcome": len(o_ids),
                    "datasets_max": max((len(m.candidates) for m in maps), default=0)},
                enters_registry=enters,
                enters_direction_results=enters and d_check == "agrees",
                first_failure=failure))

    with (out_dir / "claim_checks.jsonl").open("w") as f:
        for c in checks:
            f.write(c.model_dump_json() + "\n")
    n = len(checks)
    directional = [c for c in checks if c.direction != "not_stated"]
    summary = {
        "extraction": str(a.extraction),
        "reference_releases": {k: v["release"] for k, v in manifest.items()},
        "reference_sha256": {k: v["sha256"] for k, v in manifest.items()},
        "lexicon": str(LEXICON.relative_to(EXP)),
        "dataset_dictionary": str(DATASET_DICTIONARY.relative_to(EXP)),
        "dataset_dictionary_sha256": file_sha256(DATASET_DICTIONARY),
        "dataset_components_sha256": file_sha256(EXP / "verification" / "dataset_components.csv"),
        "outcome_aliases_sha256": file_sha256(OUTCOME_ALIASES),
        "obsolete_label_replacements_sha256": file_sha256(OBSOLETE_LABELS),
        "outcome_mapping_rule": dict(collections.Counter(
            c.mapping_rule_used["outcome"] for c in checks)),
        "outcome_alias_relation": dict(collections.Counter(
            c.outcome_alias_relation for c in checks if c.outcome_alias_relation)),
        "lexicon_sha256": file_sha256(LEXICON),
        "n_claims": n,
        "span_pass": sum(c.span_passes for c in checks),
        "protein_check": dict(collections.Counter(c.protein_check for c in checks)),
        "protein_ambiguous_multiple_hgnc": sum(len(c.protein_ids) > 1 for c in checks),
        "outcome_check": dict(collections.Counter(c.outcome_check for c in checks)),
        "direction_check": dict(collections.Counter(c.direction_check for c in checks)),
        "direction_check_among_directional_claims": dict(
            collections.Counter(c.direction_check for c in directional)),
        "direction_method_among_directional_claims": dict(
            collections.Counter(c.direction_method for c in directional)),
        "evidence_type": dict(collections.Counter(c.evidence_type for c in checks)),
        "outcome_aliases": str(OUTCOME_ALIASES.relative_to(EXP)),
        "dataset_names_by_state": dict(collections.Counter(
            m.state for c in checks for m in c.dataset_mappings)),
        "dataset_names_by_rule": dict(collections.Counter(
            m.rule for c in checks for m in c.dataset_mappings)),
        "dataset_mapping_state": dict(collections.Counter(
            c.dataset_mapping_state for c in checks)),
        "protein_mapping_state": dict(collections.Counter(
            c.protein_mapping_state for c in checks)),
        "outcome_mapping_state": dict(collections.Counter(
            c.outcome_mapping_state for c in checks)),
        "direction_values": dict(collections.Counter(c.direction for c in checks)),
        "claim_scope": dict(collections.Counter(c.claim_scope for c in checks)),
        "dataset_attribution": dict(collections.Counter(c.dataset_attribution for c in checks)),
        "relation_ambiguous": dict(collections.Counter(
            str(c.relation_ambiguous) for c in checks)),
        "enters_registry": sum(c.enters_registry for c in checks),
        "enters_direction_results": sum(c.enters_direction_results for c in checks),
        "first_failure": dict(collections.Counter(c.first_failure for c in checks
                                                  if c.first_failure)),
    }
    (out_dir / "claim_summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
