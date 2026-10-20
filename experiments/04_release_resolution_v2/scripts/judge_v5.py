# /// script
# requires-python = ">=3.12"
# dependencies = ["anthropic==1.13.0", "httpx==0.28.1", "jsonschema==4.26.0"]
# ///
"""Fifth version of the two-judge runner (scripts/judge_v4.py, sealed, unchanged and imported,
with the first registration's judge_v3 and judge_v2 under it). One change: every refusal on the
account's side is not an attempt, whatever its status code or wording. judge_v4 recognised only
the credit-balance message; on 20 October 2026 Anthropic refused requests with HTTP 400 and
"You have reached your specified API usage limits" (PREREG.log of
experiments/04_release_resolution_v2), which judge_v4 counted as attempts.

`account_side(send)` wraps a judge's transport before judge_v4's own wrapper: a response whose
status is not 200 and whose body names a credit balance or a usage limit (ACCOUNT_REFUSAL), or
whose status is 402 or 429, is returned with status 402 (in judge_v2.ACCOUNT_SIDE), its returned
status kept in `status_returned_by_api` (judge_v4's own wrapper may rewrite `status_returned`)
and the reason in `account_side_reason`; judge_v2.Judge.one then
stores it as a refusal, releases its reservation and leaves the request pending. Every other
response is returned unchanged and is an attempt as before. Exchanges are stored apart
(`STORE_SUFFIX`); the prompt, schema, requests, attempt rule and ceiling are unchanged.
"""

import re

import judge_v2 as j2
import judge_v4 as j4

ACCOUNT_REFUSAL = re.compile(r"(?i)credit balance|usage limit")
STORE_SUFFIX = "_v5"
REFUSAL_STATUS = 402


def account_side(send):
    def wrapped(body: dict) -> dict:
        got = send(body)
        status = got.get("status")
        if status != 200 and (status in (402, 429)
                              or ACCOUNT_REFUSAL.search(str(got.get("body", "")))):
            got = got | {"status_returned": status, "status_returned_by_api": status,
                         "status": REFUSAL_STATUS, "account_side_reason": "account_refusal"}
        return got
    return wrapped


class Judge(j4.Judge):
    def __init__(self, model, system, schema, store, ledger, send, **kwargs):
        super().__init__(model, system, schema, store, ledger, account_side(send), **kwargs)


assert REFUSAL_STATUS in j2.ACCOUNT_SIDE
