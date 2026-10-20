# /// script
# requires-python = ">=3.12"
# dependencies = ["anthropic==1.13.0", "httpx==0.28.1", "jsonschema==4.26.0"]
# ///
"""Fourth version of the two-judge runner (the first registration's scripts/judge_v3.py and
scripts/judge_v2.py, sealed, unchanged and imported). One change: a refusal on the account's side
for want of credit is not an attempt, whatever its status code. Anthropic answered the first run
of the second registration's validity marks with HTTP 400 and the message
"Your credit balance is too low to access the Anthropic API" (PREREG.log of
experiments/04_release_resolution_v2, 20 October 2026); judge_v2 treats only HTTP 402 and 429 as
account-side, so it counted those refusals as attempts.

`account_side(send)` wraps a judge's transport: a response whose status is not 200 and whose body
holds CREDIT_REFUSAL is returned with status 402 (in judge_v2.ACCOUNT_SIDE), its returned status
kept in `status_returned` and the reason in `account_side_reason`, so judge_v2.Judge.one stores it
as a refusal, releases its reservation and leaves the request pending. Every other response is
returned unchanged. The frozen prompt, schema, packets, attempt rule and ceiling are unchanged.

Exchanges are stored apart from earlier runs (`STORE_SUFFIX`), so the refused requests are sent
again; the other judge's stored answers stand.
"""

import judge_v2 as j2
import judge_v3 as j3

CREDIT_REFUSAL = "credit balance is too low"
STORE_SUFFIX = "_v4"
REFUSAL_STATUS = 402


def account_side(send):
    def wrapped(body: dict) -> dict:
        got = send(body)
        if got.get("status") != 200 and CREDIT_REFUSAL in str(got.get("body", "")):
            got = got | {"status_returned": got.get("status"), "status": REFUSAL_STATUS,
                         "account_side_reason": "credit_balance"}
        return got
    return wrapped


class Judge(j3.Judge):
    def __init__(self, model, system, schema, store, ledger, send, **kwargs):
        super().__init__(model, system, schema, store, ledger, account_side(send), **kwargs)


assert REFUSAL_STATUS in j2.ACCOUNT_SIDE
