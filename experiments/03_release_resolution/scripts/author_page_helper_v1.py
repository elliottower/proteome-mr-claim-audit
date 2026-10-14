# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Assisted version of the author's 42-row SA1 page (draft Amendment 5, items 4 and 5; Deviation
1). It reads the page the author already uses (`sa1_author_page_42.html`, a filtered copy of
scripts/adjudication_pages.py's cards) and writes `sa1_author_page_42_v2.html`: the same 42 cards,
in the same order, with the same ids, numbering, radio names and values, blind to both judges,
with display aids computed by this script that decide nothing:

- every number in the abstract is boxed in green (class `num`). Each distinct value, exact or a
  stated maximum, is compared once with the documented sizes of the frozen dictionary rows of the
  resources named on the card. A row's documented size is its sample_size field when that field is
  one total (a breakdown in parentheses allowed, a sum not), or the number after "up to"; ranges,
  per-code counts and sums give none. A value singles out a row when it equals that row's size
  alone. "size match → <row>": one row singled out and no other; "size conflict → <row>":
  different rows singled out; "size ambiguous": a value equals two or more rows and nothing singles
  out one. A number is approximate, and not compared, only after an explicit qualifier (~, ≈,
  about, approximately, around, nearly, over, more than, >). Unmatched numbers stay boxed;
- every citation (author-year, DOI, PMID, PMC), URL and accession (GCST, OpenGWAS ids and
  batches, numbered releases, rounds, freezes, versions) is underlined in purple (class `ident`)
  with the dictionary or accession-table row it maps to, or "no match". Matching is
  conservative: an exact DOI, PMID, PMC or URL of a dictionary row; an exact accession or
  OpenGWAS batch of reference/accession_releases.csv; an author with a year that is a dictionary
  row's alias or first author and year; a numbered release only right after a resource whose alias
  carries that release ("FinnGen R10"). Anything else reads "no match";
- under the abstract, "Dictionary rows for the resources named": every dictionary row, on the
  card's side, of each resource named on the card (the name as written and each release a coder
  identified), matched by name or alias, with its name, release and sample size verbatim;
- a legend and an instruction line at the top; on every card a text field "Inferred release (if
  any) and why", and on a card where a number singles out a row a yes/no attribution question.

Marks live under a new storage key and save file. On first load the page copies every mark kept
under the old key (left untouched) into the new state, flagged `entered_before_aids`, with the
pre-aid mark kept as `before_aids`; every later change is kept in `history` with its time.

    uv run scripts/author_page_helper_v1.py --page <42-row page> --dictionary <csv> \\
        --accessions <csv> --out <v2 page> --counts <outputs json>
"""

import argparse
import csv
import hashlib
import html
import json
import pathlib
import re

DICTIONARY_SHA256 = "57f2c5bcef2b63d2d8526d4950c963a5e92e7d56cb75df215b7bbacff9f11e07"
KEY = "sa1_author_page_assisted_v2"
OLD_KEY = "sa1_author_page_deviation01"
FILE_NAME = "sa1_author_marks_42_assisted.json"
OLD_FILE_NAME = "sa1_author_marks_42.json"
QUESTION = ("Does this sample-size statement belong to the named resource on this side? (This checks "
            "the attribution, not the release.)")
INSTRUCTION = ("The radio button is what the abstract explicitly states (release number, "
               "accession, link or citation). Put any release you infer from a size match in the "
               "Inferred field.")

CARD = re.compile(r'<section class="card" data-row="([0-9a-f]+)" data-n="(\d+)">.*?</section>', re.S)
SNIP = re.compile(r'<p class="snip">(.*?)</p>', re.S)
MARK = re.compile(r'<mark class="(q1|q2|both|agreed)">(.*?)</mark>', re.S)
SIDE = re.compile(r'<div class="top"><span>\d+ of \d+ · (\w+) side</span>')
H2 = re.compile(r"<h2>(.*?)</h2>", re.S)
RELEASE_LI = re.compile(r"<li><b>(.*?)</b> · ")

NUMBER = re.compile(r"(?<![\w.,])(?:\d{1,3}(?:[    ]\d{3})+(?!\d)|\d+(?:[.,]\d+)*)")
APPROXIMATE = re.compile(r"(?:~|∼|≈|\babout|\bapproximately|\baround|\bnearly|\bover|\bmore than|>)\s*$", re.I)
UP_TO = re.compile(r"^up to (\d[\d,]*)\b", re.I)
ONE_TOTAL = re.compile(r"^(\d[\d,]*)(?: \(([^)]*)\))?$")
RELEASE_WORD = r"(?:R|DF|release |round |freeze |data freeze |version )"
IDENTIFIERS = [
    ("url", re.compile(r"https?://[^\s<>\"]+|www\.[^\s<>\"]+|\b[\w-]+(?:\.[\w-]+)*\.(?:org|com|io|fi|jp|net|edu|gov|ac\.uk|co\.uk)\b(?:/[^\s,;<>\"]*)?")),
    ("doi", re.compile(r"\b(?:doi:\s*)?10\.\d{4,9}/[^\s,;<>\"]+", re.I)),
    ("pmid", re.compile(r"\bPMID:?\s*\d+")),
    ("pmc", re.compile(r"\bPMC\d+")),
    ("gcst", re.compile(r"\bGCST\d+")),
    ("opengwas", re.compile(r"\b(?:ukb-[a-e]|ieu-[ab]|finn-[ab]|ebi-a|prot-[a-c]|met-[a-d]|bbj-a|eqtl-a)(?:-[\w.]+)?\b")),
    ("release", re.compile(r"\bfinngen_R\d+\b|\b(?:R|DF)\d{1,2}\b|\b(?:data freeze|release|round|freeze|version|wave)\s+\d+\b|\bv\d+(?:\.\d+)?\b", re.I)),
    ("citation", re.compile(r"\b[A-Z][\w'’‐-]+(?:\s[A-Z]{1,3})?\s+et\s+al\.?(?:,?\s*\(?(?:19|20)\d{2}[a-z]?\)?)?"
                            r"|\(([A-Z][\w'’‐-]+(?:\s+et\s+al\.?)?),?\s*(?:19|20)\d{2}[a-z]?\)")),
]
GENERIC_TAIL = re.compile(r"\s+(?:study|database|data|dataset|datasets|cohort|cohorts|consortium|"
                          r"summary statistics|GWAS|biobank database)$", re.I)
STYLE = (".num{outline:2px solid #1a7f37;outline-offset:0;background:#e3f5e8;border-radius:2px}"
         ".ident{border-bottom:3px solid #7b2cbf;background:#f1e6fb}"
         ".tag{font-size:12px;font-weight:600;border-radius:3px;padding:0 4px;margin:0 2px;white-space:nowrap}"
         ".tag.idmap{color:#5a189a;border:1px solid #7b2cbf;background:#fff}"
         ".tag.size{color:#0b5d23;border:1px solid #1a7f37;background:#fff}"
         ".tag.size.warn{color:#8a4b00;border-color:#b86e00}"
         ".rows{border-collapse:collapse;font-size:14.5px;margin:6px 0}.rows td,.rows th{border:1px solid "
         "#999;padding:3px 8px;text-align:left;vertical-align:top}"
         ".ctl2{display:flex;gap:18px;flex-wrap:wrap;align-items:center;margin-top:8px}"
         ".inferred{flex:1;min-width:260px;font-size:15px;padding:4px 6px}"
         "#legend,#instr{font-size:15px;margin:6px 0}#instr{font-weight:700}")


def digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def norm(s: str) -> str:
    s = s.lower().replace("et al.", " ").replace("et al", " ")
    return " ".join(re.sub(r"[^\w/.:-]+", " ", s).split()).strip(" .")


def norm_url(s: str) -> str:
    s = re.sub(r"^https?://", "", s.strip().lower())
    return re.sub(r"^www\.", "", s).rstrip("/.")


def documented_size(field: str) -> str | None:
    """The dictionary row's documented size: one total, or the number after "up to"."""
    f = field.strip()
    m = UP_TO.match(f)
    if m:
        return digits(m.group(1))
    m = ONE_TOTAL.match(f)
    if m and not (m.group(2) and "sum" in m.group(2).lower()):
        return digits(m.group(1))
    return None


def load_dictionary(path: pathlib.Path) -> list[dict]:
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != DICTIONARY_SHA256:
        raise ValueError(f"{path} is not the frozen dictionary (sha256 {DICTIONARY_SHA256})")
    return list(csv.DictReader(data.decode().splitlines()))


def load_accessions(path: pathlib.Path) -> dict[str, dict]:
    with path.open(newline="") as fh:
        return {r["release_identifier"]: r for r in csv.DictReader(fh)}


def aliases(row: dict) -> list[str]:
    return [row["name"]] + [a for a in row["aliases"].split("|") if a]


def named_rows(names: list[str], side: str, definitions: list[dict]) -> list[dict]:
    """Every dictionary row on `side` of each resource named, matched by name or alias: a name
    equal to a row's name or alias, contained in one as whole words, or containing one (5+
    characters) as whole words; then the resource's other rows (a shared alias, or a shared first
    word of 4+ characters)."""
    rows = [d for d in definitions if d["side"] == side]
    probes = []
    for n in names:
        n = n.strip()
        if not n or n.lower() == "not stated":
            continue
        for part in [re.sub(r"\s*\([^)]*\)", "", n)] + re.findall(r"\(([^)]*)\)", n):
            part = part.strip()
            probes += [part, GENERIC_TAIL.sub("", part)]
    hit = []
    for d in rows:
        for a in aliases(d):
            al = a.lower()
            for p in {p.lower() for p in probes if len(p) >= 3}:
                if (al == p or re.search(rf"(?<!\w){re.escape(p)}(?!\w)", al)
                        or (len(al) >= 5 and re.search(rf"(?<!\w){re.escape(al)}(?!\w)", p))):
                    hit.append(d)
                    break
            else:
                continue
            break
    shared = {a.lower() for d in hit for a in aliases(d)[1:]}
    first = {d["name"].split()[0].lower() for d in hit if len(d["name"].split()[0]) >= 4}
    out = [d for d in rows if d in hit or {a.lower() for a in aliases(d)[1:]} & shared
           or d["name"].split()[0].lower() in first]
    return out


class Index:
    """Exact lookups for identifiers, built once from the dictionary and the accession table."""

    def __init__(self, definitions: list[dict], accessions: dict[str, dict]):
        self.accessions = accessions
        self.ids: dict[str, list[str]] = {}
        self.urls: dict[str, list[str]] = {}
        self.cites: dict[str, list[str]] = {}
        self.releases: dict[str, list[tuple[str, str]]] = {}
        for d in definitions:
            for piece in d["source_identifier"].split(";"):
                piece = piece.strip()
                if not piece:
                    continue
                if re.match(r"https?://", piece):
                    self.urls.setdefault(norm_url(piece), []).append(d["name"])
                else:
                    key = re.sub(r"^(doi|pmid):\s*", lambda m: m.group(1).lower() + ":", piece, flags=re.I).lower()
                    self.ids.setdefault(key, []).append(d["name"])
            for a in aliases(d):
                if "/" in a and "." in a.split("/")[0]:
                    self.urls.setdefault(norm_url(a), []).append(d["name"])
                m = re.fullmatch(r"(.+?)\s*\(?((?:19|20)\d{2})\)?", a.replace("et al.", "").strip())
                if m and len(m.group(1).split()) == 1:
                    self.cites.setdefault(f"{m.group(1).lower()} {m.group(2)}", []).append(d["name"])
                m = re.fullmatch(rf"(.+?)\s+{RELEASE_WORD}(\d+)", a, flags=re.I)
                if m:
                    self.releases.setdefault(m.group(1).lower(), []).append((m.group(2), d["name"]))
                m = re.fullmatch(r"(\w+)_R(\d+)", a)
                if m:
                    self.releases.setdefault(m.group(1).lower(), []).append((m.group(2), d["name"]))
            m = re.match(r"([A-Z][\w'’-]+)\b[^.]*?\b((?:19|20)\d{2})\b", d["source_citation"])
            if m:
                self.cites.setdefault(f"{m.group(1).lower()} {m.group(2)}", []).append(d["name"])

    def lookup(self, kind: str, token: str, before: str) -> tuple[list[str], str]:
        """The rows `token` maps to and the basis, or ([], "")."""
        if kind == "url":
            u = norm_url(token)
            for k, names in self.urls.items():
                if u == k or u.startswith(k + "/"):
                    return names, "URL"
            return [], ""
        if kind == "doi":
            return self.ids.get("doi:" + re.sub(r"^doi:\s*", "", token, flags=re.I).lower().rstrip(".)"), []), "DOI"
        if kind == "pmid":
            return self.ids.get("pmid:" + digits(token), []), "PMID"
        if kind == "pmc":
            return self.ids.get(token.lower(), []), "PMC"
        if kind in ("gcst", "opengwas"):
            row = self.accessions.get(token) or self.accessions.get(token.rsplit("-", 1)[0] if kind == "opengwas" else "")
            if row and row["dictionary_row"]:
                return [row["dictionary_row"]], f"accession table, {row['release_identifier']}"
            return [], ""
        if kind == "release":
            n = digits(token)
            m = re.match(r"(\w+)_R\d+$", token)
            heads = [m.group(1).lower()] if m else []
            if not heads:
                tail = before[-60:].split(". ")[-1].lower()
                found = [(tail.rfind(h), h) for h in self.releases
                         if re.search(rf"(?<!\w){re.escape(h)}\W*$", tail)]
                heads = [h for _, h in sorted(found)[-1:]]
            names = {name for h in heads for num, name in self.releases[h] if num == n}
            return (sorted(names), "release after resource name") if len(names) == 1 else ([], "")
        if kind == "citation":
            m = re.search(r"([A-Z][\w'’‐-]+).*?((?:19|20)\d{2})", token)
            if not m:
                return [], ""
            names = list(dict.fromkeys(self.cites.get(f"{m.group(1).lower()} {m.group(2)}", [])))
            return names, "author and year"
        return [], ""


def parse_snip(snip_html: str) -> tuple[str, list[str | None]]:
    """The plain abstract text and, per character, the class of the mark it sits in."""
    text, owner, i = [], [], 0
    for m in MARK.finditer(snip_html):
        plain = html.unescape(snip_html[i:m.start()])
        text.append(plain)
        owner += [None] * len(plain)
        inner = html.unescape(m.group(2))
        text.append(inner)
        owner += [m.group(1)] * len(inner)
        i = m.end()
    plain = html.unescape(snip_html[i:])
    text.append(plain)
    owner += [None] * len(plain)
    return "".join(text), owner


def render_marks(text: str, owner: list[str | None]) -> str:
    out, i = [], 0
    while i < len(text):
        j = i
        while j < len(text) and owner[j] == owner[i]:
            j += 1
        chunk = html.escape(text[i:j])
        out.append(f'<mark class="{owner[i]}">{chunk}</mark>' if owner[i] else chunk)
        i = j
    return "".join(out)


def find_identifiers(text: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    for kind, pat in IDENTIFIERS:
        for m in pat.finditer(text):
            s, e = m.start(), m.end()
            while e > s and text[e - 1] in ".,;:)]" and not (kind == "citation" and text[e - 1] == ")"
                                                          and "(" in text[s:e]):
                e -= 1
            if e > s and not any(a < e and s < b for a, b, _ in spans):
                spans.append((s, e, kind))
    return sorted(spans)


def find_numbers(text: str, idents: list[tuple[int, int, str]]) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in NUMBER.finditer(text)
            if not any(a < m.end() and m.start() < b for a, b, _ in idents)]


def size_value(text: str, s: int, e: int) -> str | None:
    """The digits of the integer at text[s:e], exact or a maximum; None for a decimal or a number
    with an explicit approximate qualifier before it (never for trailing zeros)."""
    tok = text[s:e]
    if re.search(r"\.\d", tok) and not re.fullmatch(r"\d{1,3}(?:\.\d{3})+", tok):
        return None
    if APPROXIMATE.search(text[max(0, s - 20):s]):
        return None
    return digits(tok)


def size_labels(text: str, numbers: list[tuple[int, int]], rows: list[dict]) -> dict[int, tuple[str, str]]:
    """Per number (by start), ("match" | "ambiguous" | "conflict", row name or ""). Each distinct
    value is compared once with the documented sizes of `rows`. A value singles out a row when it
    equals that row's size alone. One row singled out (by one or more values) and no other: match.
    Different rows singled out: conflict. Values equal to two or more rows and nothing singling
    out a row: ambiguous. Unmatched numbers get no label."""
    sizes: dict[str, list[str]] = {}
    for d in rows:
        v = documented_size(d["sample_size"])
        if v:
            sizes.setdefault(v, []).append(d["name"])
    value_of = {s: size_value(text, s, e) for s, e in numbers}
    hits = {v: sizes[v] for v in set(value_of.values()) if v and v in sizes}
    singled = {h[0] for h in hits.values() if len(h) == 1}
    labels = {}
    for s, v in value_of.items():
        if v not in hits:
            continue
        if len(hits[v]) == 1:
            labels[s] = ("match" if len(singled) == 1 else "conflict", hits[v][0])
        elif not singled:
            labels[s] = ("ambiguous", "")
    return labels


def render_snip(text: str, owner: list[str | None], idents, numbers, maps, labels) -> str:
    kind_at: list[tuple[str, int] | None] = [None] * len(text)
    for s, e, _ in idents:
        for i in range(s, e):
            kind_at[i] = ("ident", s)
    for s, e in numbers:
        for i in range(s, e):
            kind_at[i] = ("num", s)
    ends = {e - 1: ("ident", s) for s, e, _ in idents} | {e - 1: ("num", s) for s, e in numbers}
    out, i = [], 0
    while i < len(text):
        j = i
        while j < len(text) and owner[j] == owner[i] and kind_at[j] == kind_at[i] and (j == i or j - 1 not in ends):
            j += 1
        chunk = html.escape(text[i:j])
        if kind_at[i]:
            chunk = f'<span class="{kind_at[i][0]}">{chunk}</span>'
        out.append(f'<mark class="{owner[i]}">{chunk}</mark>' if owner[i] else chunk)
        if j - 1 in ends:
            what, s = ends[j - 1]
            if what == "ident":
                names, basis = maps[s]
                tag = (f"→ {' | '.join(names)} ({basis})" if len(names) == 1 else
                       f"→ one of {len(names)} rows: {' | '.join(names)} ({basis})" if names else "no match")
                out.append(f'<span class="tag idmap">{html.escape(tag)}</span>')
            elif s in labels:
                kind, row = labels[s]
                tag = {"match": f"size match → {row}", "ambiguous": "size ambiguous",
                       "conflict": f"size conflict → {row}"}[kind]
                out.append(f'<span class="tag size{"" if kind == "match" else " warn"}">{html.escape(tag)}</span>')
        i = j
    return "".join(out)


def rows_table(rows: list[dict]) -> str:
    head = '<div class="lab">Dictionary rows for the resources named</div>'
    if not rows:
        return head + "<p>No dictionary row matches a resource named on this card.</p>"
    body = "".join(f"<tr><td>{html.escape(d['name'])}</td><td>{html.escape(d['release'])}</td>"
                   f"<td>{html.escape(d['sample_size'])}</td></tr>" for d in rows)
    return (head + '<table class="rows"><tr><th>Name</th><th>Release</th><th>Sample size</th></tr>'
            f"{body}</table>")


def extra_controls(row_id: str, has_match: bool) -> str:
    belongs = (f'<span>{html.escape(QUESTION)}</span>'
               f'<label><input type="radio" name="sz_{row_id}" value="yes"> Yes</label>'
               f'<label><input type="radio" name="sz_{row_id}" value="no"> No</label>') if has_match else ""
    return (f'<div class="ctl2">{belongs}<input type="text" class="inferred" '
            f'placeholder="Inferred release (if any) and why"></div>')


def build_card(card_html: str, definitions: list[dict], index: Index) -> tuple[str, dict]:
    side = SIDE.search(card_html).group(1)
    names = [html.unescape(H2.search(card_html).group(1))]
    names += [html.unescape(r) for r in RELEASE_LI.findall(card_html)]
    rows = named_rows(names, side, definitions)
    snip = SNIP.search(card_html)
    text, owner = parse_snip(snip.group(1))
    if render_marks(text, owner) != snip.group(1):
        raise ValueError("the abstract's marks do not round-trip")
    idents = find_identifiers(text)
    numbers = find_numbers(text, idents)
    maps = {s: index.lookup(kind, text[s:e], text[:s]) for s, e, kind in idents}
    labels = size_labels(text, numbers, rows)
    has_match = any(k in ("match", "conflict") for k, _ in labels.values())
    new = (card_html[:snip.start(1)] + render_snip(text, owner, idents, numbers, maps, labels)
           + card_html[snip.end(1):snip.end()] + rows_table(rows) + card_html[snip.end():])
    ctl_end = new.rindex("</section>")
    new = new[:ctl_end] + extra_controls(re.match(CARD, card_html).group(1), has_match) + new[ctl_end:]
    counts = {"numbers": len(numbers), "identifiers": len(idents),
              "identifiers_mapped": sum(1 for v in maps.values() if v[0]),
              "size_match": sum(1 for k, _ in labels.values() if k == "match"),
              "size_ambiguous": sum(1 for k, _ in labels.values() if k == "ambiguous"),
              "size_conflict": sum(1 for k, _ in labels.values() if k == "conflict"),
              "dictionary_rows": len(rows), "size_question": has_match}
    return new, counts


SCRIPT = """
const KEY=%s,OLD=%s;const cards=[...document.querySelectorAll('.card')];const now=()=>new Date().toISOString();
let st=null;try{st=JSON.parse(localStorage.getItem(KEY)||'null');}catch(e){st=null;}
if(!st||!st.rows){st={meta:{created_at:now(),copied_from:null},rows:{}};let old={};try{old=JSON.parse(localStorage.getItem(OLD)||'{}')||{};}catch(e){old={};}
const t=now();Object.keys(old).forEach(k=>{const o=old[k]||{};const m={choice:o.choice||'',reason:o.reason||''};st.rows[k]={...m,inferred:'',size_belongs:null,entered_before_aids:true,before_aids:m,changed_at:t,history:[{at:t,source:'copied from the page without aids',...m}]};});
st.meta.copied_from=OLD;st.meta.copied_at=t;st.meta.copied_rows=Object.keys(old).length;try{localStorage.setItem(KEY,JSON.stringify(st));}catch(e){}}
cards.forEach(c=>{const s=st.rows[c.dataset.row];if(s){const r=c.querySelector('.ctl input[value="'+s.choice+'"]');if(r)r.checked=true;c.querySelector('.reason').value=s.reason||'';
c.querySelector('.inferred').value=s.inferred||'';if(s.size_belongs){const b=c.querySelector('.ctl2 input[value="'+s.size_belongs+'"]');if(b)b.checked=true;}}});
function rec(c){const v=c.querySelector('.ctl input[type=radio]:checked');const b=c.querySelector('.ctl2 input[type=radio]:checked');
return {choice:v?v.value:'',reason:c.querySelector('.reason').value,inferred:c.querySelector('.inferred').value,size_belongs:c.querySelector('.ctl2 input[type=radio]')?(b?b.value:''):null};}
const F=['choice','reason','inferred','size_belongs'];
function upd(log){let k=0;cards.forEach(c=>{const r=rec(c);c.classList.toggle('done',!!r.choice);if(r.choice)k++;
let s=st.rows[c.dataset.row];if(!s){if(!(r.choice||r.reason||r.inferred||r.size_belongs))return;s=st.rows[c.dataset.row]={entered_before_aids:false,before_aids:null,history:[]};}
const t=now();if(F.some(f=>(s[f]??'')!==(r[f]??''))){F.forEach(f=>s[f]=r[f]);s.changed_at=t;}
if(log){const h=s.history[s.history.length-1];if(!h||F.some(f=>(h[f]??'')!==(r[f]??'')))s.history.push({at:t,source:'this page',...r});}});
try{localStorage.setItem(KEY,JSON.stringify(st));}catch(e){}document.getElementById('count').textContent=k+' of '+cards.length+' marked';}
document.addEventListener('change',()=>upd(true));document.addEventListener('input',e=>{if(e.target.classList.contains('reason')||e.target.classList.contains('inferred'))upd(false);});upd(false);
document.getElementById('save').addEventListener('click',async()=>{upd(true);const out={page:%s,saved_at:now(),state_meta:st.meta,marks:cards.map(c=>{const r=rec(c);const s=st.rows[c.dataset.row]||{};return {n:+c.dataset.n,row_id:c.dataset.row,choice:r.choice,reason:r.reason,inferred:r.inferred,size_belongs:r.size_belongs,entered_before_aids:!!s.entered_before_aids,before_aids:s.before_aids||null,changed_at:s.changed_at||null,history:s.history||[]};})};
const blob=new Blob([JSON.stringify(out,null,1)],{type:'application/json'});
if(window.showSaveFilePicker){try{const h=await showSaveFilePicker({suggestedName:%s,types:[{description:'JSON',accept:{'application/json':['.json']}}]});const w=await h.createWritable();await w.write(blob);await w.close();return;}catch(e){if(e.name==='AbortError')return;}}
const el=document.createElement('a');el.href=URL.createObjectURL(blob);el.download=%s;el.click();});""" % (
    json.dumps(KEY), json.dumps(OLD_KEY), json.dumps(KEY), json.dumps(FILE_NAME), json.dumps(FILE_NAME))

LEGEND = ('<p id="legend"><b>Legend:</b> <mark class="q1">blue</mark> Answer 1\'s quoted passages · '
          '<mark class="q2">red</mark> Answer 2\'s · <mark class="both">yellow</mark> both, or the '
          'agreed answer\'s · <span class="num">green box</span> a number, with '
          '<span class="tag size">size match → row</span>, <span class="tag size warn">size '
          'ambiguous</span> or <span class="tag size warn">size conflict → row</span> against the '
          'dictionary rows of the resources named · <span class="ident">purple underline</span> a '
          'citation, URL or accession, with <span class="tag idmap">→ row</span> or <span '
          'class="tag idmap">no match</span>. All are computed by script and decide nothing. Marks '
          'made on the page without these aids are carried over and flagged as entered before '
          'them.</p>')


def build(page_html: str, definitions: list[dict], accessions: dict[str, dict]) -> tuple[str, list[dict]]:
    index = Index(definitions, accessions)
    cards = list(CARD.finditer(page_html))
    script_at = page_html.index("<script>")
    if not cards or page_html[cards[-1].end():script_at] != "":
        raise ValueError("the page is not the expected card layout")
    out, counts, last = [], [], 0
    for m in cards:
        new, c = build_card(m.group(0), definitions, index)
        out += [page_html[last:m.start()], new]
        counts.append({"n": int(m.group(2)), "row_id": m.group(1), **c})
        last = m.end()
    out.append(f"<script>{SCRIPT}</script></body></html>")
    made = "".join(out)
    bar = '<div id="bar">'
    made = made.replace(bar, f'{LEGEND}<p id="instr">{html.escape(INSTRUCTION)}</p>{bar}', 1)
    made = made.replace("</style>", STYLE + "</style>", 1)
    if (page_html[script_at:].count(json.dumps(OLD_KEY)) != 2
            or page_html[script_at:].count(json.dumps(OLD_FILE_NAME)) != 2):
        raise ValueError("the input page does not carry the expected storage key and save file")
    return made, counts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", type=pathlib.Path, required=True)
    ap.add_argument("--dictionary", type=pathlib.Path, required=True)
    ap.add_argument("--accessions", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--counts", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists() or a.counts.exists():
        raise FileExistsError("an output exists already; outputs are written once")
    page_html = a.page.read_text()
    made, counts = build(page_html, load_dictionary(a.dictionary), load_accessions(a.accessions))
    summary = {
        "script": "scripts/author_page_helper_v1.py",
        "inputs": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (a.page, a.dictionary, a.accessions)},
        "page_sha256": hashlib.sha256(made.encode()).hexdigest(),
        "cards": len(counts), "storage_key": KEY, "copies_marks_from_key": OLD_KEY,
        "save_file": FILE_NAME,
        "totals": {k: sum(c[k] for c in counts) for k in ("numbers", "identifiers", "identifiers_mapped",
                                                          "size_match", "size_ambiguous", "size_conflict",
                                                          "dictionary_rows", "size_question")},
        "per_card": counts}
    a.counts.write_text(json.dumps(summary, indent=1) + "\n")
    a.out.write_text(made)
    print(json.dumps(summary["totals"], indent=1))


if __name__ == "__main__":
    main()
