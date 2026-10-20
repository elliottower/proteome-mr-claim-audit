# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Cost estimate of the stage A recode of the second release-resolution registration
(PREREG.md, Data collection procedures: "build packets; write the cost estimate and stop for the
author's approval"). No model is called.

Coders (`coders`): both coders on every packet, priced as the first registration priced stage A
(outputs/stage_a_sa1_estimate_2026-10-13.json): coding_packets_v2.layout_cost over the packets'
JSON characters with the fixed prompt (prompt v3 and the dictionary definitions) cached after the
first request, at the preflight's and the plan's characters per token, and
stage_pricing.with_outputs at 1,500, 3,000 and 6,000 output tokens a request; beside it, the same
packets at the mean output each coder billed per request in the first registration's stage A
(MEASURED_OUTPUT, PREREG.log of 14 October 2026), and the sum of the runner's reservation bounds
(coding_runner_v2.bound).

Judges (`judges`): each judge of Amendment 4 gets one request per judged row: the judge system
(judge prompt, coding prompt v3, dictionary definitions; judge.system_text) cached after its first
request, and a body of the row's packet files, its row and the answers (ANSWER_CHARACTERS for two
answers), as new input at judge_v2.MIN_RATIO, with output at 1,500, 3,000 and 8,192 tokens.
Rows judged: expected, each population's rows times the share on which the coders differed in the
first registration's stage A (study rows 147 of 657, control rows 25 of 70), plus the audit of
agreements (10%, at least 30); upper, every row (the escalated review). Rows are priced on their
own packet. The settling step of Amendment 7 is a script and costs nothing; calibration and
routing are the author's.
"""

import json
import math

import coding_packets_v2 as cp2
import judge_v2 as j2
import stage_pricing as sp

RATIOS = {"preflight_ratios": {"claude-sonnet-5-5": 1.98, "gpt-6.1-sol": 3.11},
          "pooled_full_text_ratios_of_the_plan": {"claude-sonnet-5-5": 2.62, "gpt-6.1-sol": 4.28}}
MEASURED_OUTPUT = {"claude-sonnet-5-5": 2_289, "gpt-6.1-sol": 1_168}
DIFFER_SHARE = {"study": 147 / 657, "control": 25 / 70}
AUDIT_SHARE, AUDIT_MINIMUM = 0.10, 30
ANSWER_CHARACTERS = 6_000
JUDGE_OUTPUTS = (1_500, 3_000, 8_192)


def packet_chars(packet: dict) -> int:
    return len(json.dumps(packet, ensure_ascii=False))


def coders(packets: list[dict], prompt_chars: int) -> dict:
    recs = [{"record_id": p["record_id"], "carried": 0, "packets": [packet_chars(p)]}
            for p in packets]
    out = {}
    for name, ratio in RATIOS.items():
        cost = cp2.layout_cost(recs, prompt_chars, ratio, True)
        out[name] = sp.with_outputs(cost)
        measured = {m: round(cost[m]["usd"] + cost[m]["requests"] * (MEASURED_OUTPUT[m]
                                                                     - cp2.OUTPUT_TOKENS)
                             * cp2.PRICE[m]["output"] / 1e6, 2) for m in MEASURED_OUTPUT}
        out[name]["measured_output_of_the_first_stage_a"] = measured | {
            "total_usd": round(sum(measured.values()), 2)}
    return out


def judge_row_usd(model: str, system_chars: int, files_chars: int, output: int) -> float:
    p = j2.PRICE[model]
    body = (files_chars + ANSWER_CHARACTERS) / j2.MIN_RATIO[model]
    return (system_chars / j2.MIN_RATIO[model] * p["cached"] + body * p["new"]
            + output * p["output"]) / 1e6


def rows_judged(packets: list[dict], control_ids: set[str]) -> dict:
    study = sum(1 for p in packets for r in p["rows"] if r["row_id"] not in control_ids)
    control = sum(1 for p in packets for r in p["rows"] if r["row_id"] in control_ids)
    differ = study * DIFFER_SHARE["study"] + control * DIFFER_SHARE["control"]
    agreed = study + control - differ
    audit = max(AUDIT_MINIMUM, math.ceil(AUDIT_SHARE * agreed))
    return {"study_rows": study, "control_rows": control, "expected_disagreements": round(differ, 1),
            "expected_audit_rows": audit, "expected_rows_judged": round(differ + audit, 1),
            "upper_rows_judged": study + control}


def judges(packets: list[dict], control_ids: set[str], system_chars: int) -> dict:
    counts = rows_judged(packets, control_ids)
    total_rows = counts["upper_rows_judged"]
    expected_share = counts["expected_rows_judged"] / total_rows
    out = {"rows": counts, "system_characters": system_chars}
    for output in JUDGE_OUTPUTS:
        per = {}
        for m in j2.JUDGES:
            every = sum(judge_row_usd(m, system_chars,
                                      sum(len(f["text"]) for f in p["files"]), output)
                        for p in packets for _ in p["rows"])
            per[m] = {"expected_usd": round(every * expected_share, 2),
                      "upper_usd": round(every, 2)}
        out[str(output)] = per | {
            "expected_total_usd": round(sum(v["expected_usd"] for v in per.values()), 2),
            "upper_total_usd": round(sum(v["upper_usd"] for v in per.values()), 2)}
    return out
