# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Diagnostic of the SA1 disagreement calibration (outputs/sa1_calibration_2026-10-14.json), after
scoring; it changes no verdict. Counts only.

1. Label check. For each disagreement calibration row, the content of Answer 1 and Answer 2 as
   the author's page shows it (`page_answers`: each release with its role and ancestry, the
   attribution state, the unresolved reasons, as adjudication_pages.answer_block renders them) is
   hashed, and the same fields of the stored judge request's Answer 1 and Answer 2
   (`request_view`) are hashed; a row is `in_order` when page 1 = request 1 and page 2 = request 2,
   `swapped` when page 1 = request 2 and page 2 = request 1, else `neither`.
2. Direction. For each row where the author's choice differs from the judges' joint choice, from
   the two coders' answers only: the author's chosen answer is read on the page, the judges' in the
   request (so a swap cannot misplace either), and the pair is classed (a) author's answer
   identifies no release, judges' identifies one or more; (b) the reverse; (c) both identify
   releases, different ones; (d) both identify none, differing in attribution or reasons only;
   `other` when either chose neither or an answer is missing.
"""

import hashlib
import html
import json
import re

ANS = re.compile(r'<div class="ans (q1|q2)">(.*?)(?=<div class="ans q2">|<div class="lab">Abstract</div>)', re.S)
CARD = re.compile(r'<section class="card" data-row="([0-9a-f]+)" data-n="\d+">.*?</section>', re.S)
REL = re.compile(r"<li><b>(.*?)</b> · (.*?) · (.*?)</li>")
ATTR = re.compile(r"<b>Attribution:</b> (.*?) · <b>Unresolved:</b> (.*?)</p>")


def parse_answer(block: str) -> dict | None:
    if "No accepted answer." in block and "<b>Attribution:</b>" not in block:
        return None
    rels_html = block.split("<ul>", 1)[1].split("</ul>", 1)[0]
    rels = [[html.unescape(x) for x in m] for m in REL.findall(rels_html)]
    state, reasons = ATTR.search(block).groups()
    reasons = html.unescape(reasons)
    return {"releases": rels, "attribution_state": html.unescape(state),
            "unresolved_reasons": [] if reasons == "none" else reasons.split(", ")}


def page_answers(page_html: str, rows: set[str]) -> dict[str, list[dict | None]]:
    out = {}
    for m in CARD.finditer(page_html):
        if m.group(1) in rows:
            blocks = dict(ANS.findall(m.group(0)))
            out[m.group(1)] = [parse_answer(blocks["q1"]), parse_answer(blocks["q2"])]
    return out


def request_view(answer: dict | None) -> dict | None:
    if answer is None:
        return None
    roles = {r["release"]: r["role"] for r in answer["roles"]}
    anc = {r["release"]: r["ancestry"] for r in answer["ancestry"]}
    return {"releases": [[r, roles.get(r, "—"), anc.get(r, "—")] for r in answer["identified_releases"]],
            "attribution_state": answer["attribution_state"],
            "unresolved_reasons": list(answer["unresolved_reasons"])}


def digest(view: dict | None) -> str:
    return hashlib.sha256(json.dumps(view, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def label_check(page: list[dict | None], request: list[dict | None]) -> str:
    p, r = [digest(x) for x in page], [digest(x) for x in request]
    if p == r:
        return "in_order"
    if p == r[::-1]:
        return "swapped"
    return "neither"


INDEX = {"answer_1": 0, "answer_2": 1}


def direction(author_choice: str, judges_choice: str, page: list[dict | None],
              request: list[dict | None]) -> str:
    if author_choice not in INDEX or judges_choice not in INDEX:
        return "other"
    a, j = page[INDEX[author_choice]], request[INDEX[judges_choice]]
    if a is None or j is None:
        return "other"
    ra, rj = {x[0] for x in a["releases"]}, {x[0] for x in j["releases"]}
    if not ra and rj:
        return "a"
    if ra and not rj:
        return "b"
    if ra and rj:
        return "c"
    return "d"
