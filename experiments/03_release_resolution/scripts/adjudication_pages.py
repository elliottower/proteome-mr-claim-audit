# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""The author's adjudication and audit pages of a coding pass of the release-resolution follow-up
(PREREG.md, §Study design, Checks; Data collection procedures, Tooling reused from Paper 1). A new
versioned copy of the page style of Paper 1's check pages (the unsealed builders kept under the
ignored planning folder); the seeded draw is Paper 1's (manual_coding_check3_sample.draw, sealed,
imported unchanged). No model is called.

Disagreement page. Every row on which the two models' accepted answers differ, or for which a
model has no accepted answer (pass_summary.adjudication_rows). The two answers are shown side by
side as "Answer 1" and "Answer 2", never naming the model; which model is Answer 1 is drawn per
row by `random.Random(f"{seed}:{row_id}").random() < 0.5`, and the key is written apart from the
page. The author picks Answer 1, Answer 2 or neither, with a reason.

Audit page. A seeded sample of the rows on which the answers agree: 10% of them, at least 30
(all if fewer), drawn by manual_coding_check3_sample.draw over the agreed rows in the order of
the packets. The agreed answer is shown once. The author marks it correct, a substantive error
(a wrong row, a wrong role or a wrong attribution state, which the plan's escalation counts), or
another issue, with a note.

Every card shows the record (with a link to its open page), the side, the name as written, the
outcomes as written, the row's id, each answer's releases, roles, ancestry, attribution state,
unresolved reasons, note and gate verdict, and the record's abstract with each answer's quoted
passages highlighted. Marks are kept in the browser as the author goes, and a button saves them
as a JSON file through the browser's save dialog where it has one.
"""

import hashlib
import html
import json
import math
import random

import manual_coding_check3_sample as sample
import pass_summary as ps

AUDIT_SHARE, AUDIT_MINIMUM = 0.10, 30


def source_link(record_id: str) -> str:
    if record_id.startswith("PPR"):
        return f"https://europepmc.org/article/PPR/{record_id}"
    if record_id.isdigit():
        return f"https://pubmed.ncbi.nlm.nih.gov/{record_id}/"
    return f"https://openalex.org/{record_id}"


def audit_draw(agreed: list[str], seed: int) -> list[str]:
    n = min(len(agreed), max(AUDIT_MINIMUM, math.ceil(AUDIT_SHARE * len(agreed))))
    return [agreed[i] for i in sample.draw(list(range(len(agreed))), seed, n)]


def first_is_a(row_id: str, seed: int) -> bool:
    return random.Random(f"{seed}:{row_id}").random() < 0.5


def highlight(text: str, quotes: dict[str, list[str]]) -> str:
    """The text with each answer's quotes marked (class `q1`, `q2`, or `both` where they meet)."""
    owner = [set() for _ in text]
    for label, qs in quotes.items():
        for q in qs:
            if not q:
                continue
            start = text.find(q)
            while start >= 0:
                for i in range(start, start + len(q)):
                    owner[i].add(label)
                start = text.find(q, start + 1)
    out, i = [], 0
    while i < len(text):
        j = i
        while j < len(text) and owner[j] == owner[i]:
            j += 1
        chunk = html.escape(text[i:j])
        who = owner[i]
        cls = "both" if len(who) > 1 else (next(iter(who)) if who else None)
        out.append(f'<mark class="{cls}">{chunk}</mark>' if cls else chunk)
        i = j
    return "".join(out)


def answer_block(label: str, row: dict | None, verdict: dict | None) -> str:
    if row is None:
        return f'<div class="ans {label}"><div class="lab">{label.upper()}</div><p>No accepted answer.</p></div>'
    roles = {r["release"]: r["role"] for r in row["roles"]}
    anc = {r["release"]: r["ancestry"] for r in row["ancestry"]}
    rels = "".join(f"<li><b>{html.escape(r)}</b> · {html.escape(roles.get(r, '—'))} · "
                   f"{html.escape(anc.get(r, '—'))}</li>" for r in row["identified_releases"])
    ev = "".join(f'<li><span class="rule">{html.escape(e["rule"])}</span> '
                 f'{html.escape(e["release"])}: “{html.escape(e["quote"])}”</li>'
                 for e in row["decisive_evidence"])
    gate = ("passes" if verdict and verdict["passes"] else "fails" if verdict else "—")
    return (f'<div class="ans {label}"><div class="lab">{"Answer 1" if label == "q1" else "Answer 2" if label == "q2" else "Agreed answer"}</div>'
            f'<p><b>Releases</b> (release · role · ancestry):</p><ul>{rels or "<li>none</li>"}</ul>'
            f'<p><b>Attribution:</b> {html.escape(row["attribution_state"])} · <b>Unresolved:</b> '
            f'{html.escape(", ".join(row["unresolved_reasons"]) or "none")}</p>'
            f'<p><b>Decisive passages:</b></p><ul>{ev or "<li>none</li>"}</ul>'
            f'<p><b>Gate:</b> {gate}</p><p class="note">{html.escape(row["note"])}</p></div>')


def card(k: int, total: int, qrow: dict, abstract: str, blocks: list[tuple[str, dict | None,
         dict | None]], controls: str) -> str:
    quotes = {label: [e["quote"] for e in (row or {}).get("decisive_evidence", [])]
              + ([row["attribution_passage"]["quote"]] if row and row.get("attribution_passage")
                 else []) for label, row, _ in blocks}
    outcomes = (f'<p><b>Outcome as written:</b> {html.escape("; ".join(qrow["outcomes_as_written"]))}</p>'
                if qrow["side"] == "outcome" else "")
    return (f'<section class="card" data-row="{qrow["row_id"]}" data-n="{k}">'
            f'<div class="top"><span>{k} of {total} · {html.escape(qrow["side"])} side</span>'
            f'<span>row {qrow["row_id"]}</span></div>'
            f'<h2>{html.escape(qrow["name_as_written"])}</h2>'
            f'<p><a href="{source_link(qrow["record_id"])}" target="_blank" rel="noopener">'
            f'Record {html.escape(qrow["record_id"])}</a></p>{outcomes}'
            f'<div class="pair">{"".join(answer_block(l, r, v) for l, r, v in blocks)}</div>'
            f'<div class="lab">Abstract</div><p class="snip">{highlight(abstract, quotes)}</p>'
            f'{controls}</section>')


STYLE = """body{font:17px/1.55 -apple-system,Helvetica,Arial,sans-serif;background:#fff;color:#111;max-width:1100px;margin:20px auto;padding:0 16px}
.card{border:1px solid #999;border-radius:8px;padding:14px 18px;margin:18px 0}.card.done{border-color:#2a7;background:#f6fcf8}
h1{font-size:22px}h2{font-size:20px;margin:6px 0 4px}.top{display:flex;justify-content:space-between;font-size:14px;color:#222}
.lab{font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.03em;color:#333;margin-top:6px}
.pair{display:flex;gap:14px;flex-wrap:wrap}.ans{flex:1;min-width:300px;border-radius:6px;padding:8px 12px;font-size:15.5px}
.ans.q1{border-left:6px solid #1f77b4;background:#eef5fc}.ans.q2{border-left:6px solid #d1495b;background:#fdf0f2}.ans.agreed{border-left:6px solid #555;background:#f4f4f4}
mark.q1{background:#bcdcf5;color:#000}mark.q2{background:#f7c6ce;color:#000}mark.both{background:#ffe066;color:#000}mark.agreed{background:#ffe066;color:#000}
.rule{font-size:12px;font-weight:700;border:1px solid #333;border-radius:3px;padding:0 3px}.note{font-style:italic;color:#222}
.ctl{display:flex;gap:18px;flex-wrap:wrap;align-items:center;margin-top:10px}.reason{flex:1;min-width:260px;font-size:15px;padding:4px 6px}label{font-weight:600}
#bar{position:sticky;top:0;background:#fff;border-bottom:2px solid #111;padding:10px 0;display:flex;justify-content:space-between;align-items:center;gap:10px;z-index:2}
button{font-size:16px;padding:8px 14px;border-radius:6px;border:2px solid #111;background:#111;color:#fff;cursor:pointer}"""


def page(title: str, intro: str, cards: list[str], key: str, choices: list[tuple[str, str]],
         file_name: str) -> str:
    script = f"""
const KEY={json.dumps(key)};const cards=[...document.querySelectorAll('.card')];let st={{}};
try{{st=JSON.parse(localStorage.getItem(KEY)||'{{}}');}}catch(e){{st={{}};}}
cards.forEach(c=>{{const s=st[c.dataset.row];if(s){{const r=c.querySelector('input[value="'+s.choice+'"]');if(r)r.checked=true;c.querySelector('.reason').value=s.reason||'';}}}});
function upd(){{let k=0;cards.forEach(c=>{{const v=c.querySelector('input[type=radio]:checked');c.classList.toggle('done',!!v);if(v){{k++;st[c.dataset.row]={{choice:v.value,reason:c.querySelector('.reason').value}};}}}});
try{{localStorage.setItem(KEY,JSON.stringify(st));}}catch(e){{}}document.getElementById('count').textContent=k+' of '+cards.length+' marked';}}
document.addEventListener('change',upd);document.addEventListener('input',e=>{{if(e.target.classList.contains('reason'))upd();}});upd();
document.getElementById('save').addEventListener('click',async()=>{{const out={{page:{json.dumps(key)},saved_at:new Date().toISOString(),marks:cards.map(c=>{{const v=c.querySelector('input[type=radio]:checked');return {{n:+c.dataset.n,row_id:c.dataset.row,choice:v?v.value:'',reason:c.querySelector('.reason').value}};}})}};
const blob=new Blob([JSON.stringify(out,null,1)],{{type:'application/json'}});
if(window.showSaveFilePicker){{try{{const h=await showSaveFilePicker({{suggestedName:{json.dumps(file_name)},types:[{{description:'JSON',accept:{{'application/json':['.json']}}}}]}});const w=await h.createWritable();await w.write(blob);await w.close();return;}}catch(e){{if(e.name==='AbortError')return;}}}}
const el=document.createElement('a');el.href=URL.createObjectURL(blob);el.download={json.dumps(file_name)};el.click();}});"""
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>'
            f'<style>{STYLE}</style></head><body><h1>{html.escape(title)}</h1><p>{intro}</p>'
            f'<div id="bar"><span id="count"></span><button id="save">Save my marks</button></div>'
            f'{"".join(cards)}<script>{script}</script></body></html>')


def controls(k: int, choices: list[tuple[str, str]], placeholder: str) -> str:
    radios = "".join(f'<label><input type="radio" name="r{k}" value="{v}"> {html.escape(t)}</label>'
                     for v, t in choices)
    return (f'<div class="ctl">{radios}<input type="text" class="reason" '
            f'placeholder="{html.escape(placeholder)}"></div>')


DISAGREE = [("answer_1", "Answer 1"), ("answer_2", "Answer 2"), ("neither", "Neither")]
AUDIT = [("correct", "Correct"), ("substantive_error", "Substantive error"),
         ("other_issue", "Other issue")]


def build(stage: str, queue_rows: dict[str, dict], abstracts: dict[str, str],
          answers: dict[str, dict[str, dict]], verdicts: dict[str, dict[str, dict]],
          order: list[str], models: tuple[str, str], seed_audit: int,
          seed_blind: int) -> dict:
    """Both pages and their keys. `answers[model][row_id]`, `verdicts[model][row_id]`; `order`:
    the row ids in packet order."""
    a, b = models
    adj = ps.adjudication_rows(order, answers[a], answers[b])
    disagree = [r for r in order if r in set(adj["row_ids_to_adjudicate"])]
    agreed = [r for r in order if r not in set(disagree)]
    audited = audit_draw(agreed, seed_audit)
    key, dcards = {}, []
    for k, rid in enumerate(disagree, 1):
        q = queue_rows[rid]
        one, two = (a, b) if first_is_a(rid, seed_blind) else (b, a)
        key[rid] = {"answer_1": one, "answer_2": two}
        blocks = [("q1", answers[one].get(rid), verdicts[one].get(rid)),
                  ("q2", answers[two].get(rid), verdicts[two].get(rid))]
        dcards.append(card(k, len(disagree), q, abstracts[q["record_id"]], blocks,
                           controls(k, DISAGREE, "reason (required for Neither)")))
    acards = []
    for k, rid in enumerate(audited, 1):
        q = queue_rows[rid]
        blocks = [("agreed", answers[a].get(rid), verdicts[a].get(rid))]
        acards.append(card(k, len(audited), q, abstracts[q["record_id"]], blocks,
                           controls(k, AUDIT, "note (what is wrong, if anything)")))
    d_intro = ("Each card is a dataset mention on which the two coders disagree. The two answers "
               "are shown in an order drawn per row; which coder gave which is not shown. "
               "Blue and red mark each answer's quoted passages in the abstract, yellow where "
               "they overlap. Pick the answer the abstract supports, or Neither with a reason.")
    a_intro = ("Each card is a dataset mention on which the two coders agree, drawn at random for "
               "the audit. The agreed answer's passages are marked in the abstract. Mark it "
               "Correct, a Substantive error (a wrong release, role or attribution state), or "
               "Other issue, with a note.")
    pages = {"disagreement": page(f"{stage.upper()}: rows where the coders differ", d_intro,
                                  dcards, f"{stage}_disagreement", DISAGREE,
                                  f"{stage}_disagreement_marks.json"),
             "audit": page(f"{stage.upper()}: audit of agreed rows", a_intro, acards,
                           f"{stage}_audit", AUDIT, f"{stage}_audit_marks.json")}
    manifest = {"stage": stage, "rows": len(order), "disagreement_rows": len(disagree),
                "agreed_rows": len(agreed), "audit_rows": len(audited),
                "audit_rule": f"max({AUDIT_MINIMUM}, ceil({AUDIT_SHARE} x agreed)), all if fewer; "
                              "manual_coding_check3_sample.draw over the agreed rows in packet order",
                "seed_audit": seed_audit, "seed_blind": seed_blind,
                "disagreement_row_ids": disagree, "audit_row_ids": audited,
                "blinding_key_sha256": hashlib.sha256(json.dumps(key, sort_keys=True)
                                                      .encode()).hexdigest()}
    return {"pages": pages, "manifest": manifest, "key": key}
