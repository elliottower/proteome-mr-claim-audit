# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""The author's page of the second registration's stage A (the first registration's Amendments 3
to 5, carried over by PREREG.md item 4). No model is called and no judge answer is shown.

Rows (`page_rows`): every row the routing sends to the author (Amendment 4 item 2), and in each
task the first 20 of the calibration order of the rows the judges decided alone (Amendment 3 item
3), in an order shuffled by `random.Random(PAGE_SEED)` over the rows sorted by row id
(judges_stage_a_v1.PAGE_SEED, 20261041).

Cards: the first registration's cards (adjudication_pages.card, sealed, unchanged): the row as
the coders received it, a link to the record's open page, the row id, the coders' answers with
their gate verdicts (for a disagreement Answer 1 and Answer 2 in the order of seed 20261035, never
naming the coder; for an audit row the agreed answer), and the shown sources with each answer's
quoted passages marked. Stage A's sources are the abstract and the full texts; a card shows the
abstract and, of each full text, every line that holds a quoted passage of either answer, headed
by its file and line (`shown_text`), as PREREG.md (Data collection procedures) requires the
passages and the link to the source's open page.

Assisted aids (Amendment 5 item 4), from the first registration's
scripts/author_page_helper_v1.py (sealed, imported unchanged): per card, numbers boxed with the
size-match flag, citations, URLs and accessions underlined with the row each maps to, the
dictionary rows of the resources named, a field for an inferred release and, where a number
singles out a row, the attribution question; the legend and instruction line. Marks are kept
under this page's own storage key and save file, with each change's time.
"""

import html
import json
import random

import adjudication_pages as ap
import author_page_helper_v1 as helper
import judges_stage_a_v1 as js

KEY = "stage_a_v2_author_page"
FILE_NAME = "stage_a_v2_author_marks.json"
LABEL = '<div class="lab">Abstract</div>'
NEW_LABEL = ('<div class="lab">Abstract, and each line of the full texts that holds a quoted '
             "passage</div>")
CALIBRATION = 20
TITLE = "Stage A (second registration): rows for the author"
INTRO = ("Each card is a dataset mention. Decide it from the sources the coders received, under "
         "the coding instructions: the abstract and the lines of the full texts that the coders "
         "quoted are shown, and the record's link opens the paper. On a card with two answers the "
         "coders disagree: pick the answer the sources support, or Neither with a reason. On a "
         "card with one answer the coders agree: mark it Correct, a Substantive error (a wrong "
         "release, role or attribution state), or Other issue. No judge's answer is shown.")


def quotes_of(row: dict | None) -> list[str]:
    if not row:
        return []
    return [e["quote"] for e in row["decisive_evidence"]] + (
        [row["attribution_passage"]["quote"]] if row.get("attribution_passage") else [])


def shown_text(packet: dict, rows: list[dict | None]) -> str:
    quotes = [q for r in rows for q in quotes_of(r) if q]
    parts = []
    for f in packet["files"]:
        if f["kind"] == "abstract":
            parts.append(f["text"])
            continue
        for n, line in enumerate(f["text"].split("\n"), 1):
            if any(q in line for q in quotes):
                parts.append(f"[{f['file_id']}, line {n}] {line}")
    return "\n\n".join(parts)


def page_rows(routing: dict) -> list[tuple[str, str, str]]:
    rows = []
    for task in ("disagreement", "audit"):
        t = routing["tasks"][task]
        rows += [(task, rid, "routed") for rid in sorted(t["routed_reasons"])]
        rows += [(task, rid, "calibration") for rid in t["calibration_order"][:CALIBRATION]]
    order = sorted(rows, key=lambda x: x[1])
    random.Random(js.PAGE_SEED).shuffle(order)
    return order


def card(k: int, total: int, task: str, rid: str, packet: dict, answers: dict,
         gates: dict) -> str:
    q = js.as_queue_row(next(r for r in packet["rows"] if r["row_id"] == rid))
    q["record_id"] = packet["record_id"]
    if task == "disagreement":
        one, two = js.blinded(rid)
        blocks = [("q1", answers[one].get(rid), {"passes": gates[one].get(rid, False)}),
                  ("q2", answers[two].get(rid), {"passes": gates[two].get(rid, False)})]
        ctl = ap.controls(k, ap.DISAGREE, "reason (required for Neither)")
    else:
        m = js.MODELS[0]
        blocks = [("agreed", answers[m][rid], {"passes": gates[m][rid]})]
        ctl = ap.controls(k, ap.AUDIT, "note (what is wrong, if anything)")
    text = shown_text(packet, [b[1] for b in blocks])
    made = ap.card(k, total, q, text, blocks, ctl)
    if made.count(LABEL) != 1:
        raise ValueError(f"{rid}: the card does not carry one sources label")
    return made.replace(LABEL, NEW_LABEL)


def script() -> str:
    return (helper.SCRIPT.replace(json.dumps(helper.KEY), json.dumps(KEY))
            .replace(json.dumps(helper.OLD_KEY), json.dumps(KEY + "_no_earlier_page"))
            .replace(json.dumps(helper.FILE_NAME), json.dumps(FILE_NAME)))


def build(routing: dict, packet_of: dict, answers: dict, gates: dict, definitions: list[dict],
          accessions: dict) -> tuple[str, dict, list[dict]]:
    order = page_rows(routing)
    index = helper.Index(definitions, accessions)
    cards, counts, key = [], [], {}
    for k, (task, rid, why) in enumerate(order, 1):
        base = card(k, len(order), task, rid, packet_of[rid], answers, gates)
        assisted, c = helper.build_card(base, definitions, index)
        cards.append(assisted)
        counts.append({"n": k, "row_id": rid, "task": task, "why_on_page": why, **c})
        key[rid] = {"task": task, "why_on_page": why,
                    "answer_1": js.blinded(rid)[0] if task == "disagreement" else None}
    page = ap.page(TITLE, INTRO, cards, KEY, [], FILE_NAME)
    head, _ = page.rsplit("<script>", 1)
    legend = helper.LEGEND.replace(" Marks made on the page without these aids are carried over "
                                   "and flagged as entered before them.", "")
    page = (head.replace('<div id="bar">', f'{legend}<p id="instr">{html.escape(helper.INSTRUCTION)}'
                         '</p><div id="bar">', 1)
            .replace("</style>", helper.STYLE + ".snip{white-space:pre-wrap}</style>", 1)
            + f"<script>{script()}</script></body></html>")
    return page, key, counts
