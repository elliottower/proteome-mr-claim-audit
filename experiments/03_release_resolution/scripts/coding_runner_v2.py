# /// script
# requires-python = ">=3.12"
# dependencies = ["anthropic==1.13.0", "httpx==0.28.1", "jsonschema==4.26.0"]
# ///
"""Second version of the coding runner (scripts/coding_runner.py, sealed, unchanged and
imported: bodies, transport, answer checks, the ledger, the prices). One change: the bound
reserved before each request uses characters per token at or below those the free preflight
measured on a packet with the fixed prompt (outputs/sa1_preflight_2026-10-13.json: 1.98 for
Claude Sonnet 5.5, 3.11 for GPT-6.1 Sol), here 1.80 and 2.80, so that the bound is an upper
bound on a request's cost: every token of the packet and prompt as new input, plus the maximum
output. Claude spend is counted at the vendor's list prices, cache reads at 0.20 US dollars per
million tokens (the plan's cost table gives 0.10; logged as a departure).
"""

import json

import coding_runner as cr

MIN_RATIO = {cr.CLAUDE: 1.80, cr.SOL: 2.80}


def bound(model: str, prompt: str, packet: dict) -> float:
    chars = len(prompt) + len(json.dumps(packet, ensure_ascii=False))
    p = cr.PRICE[model]
    return (chars / MIN_RATIO[model] * p["new"] + cr.MAX_OUTPUT * p["output"]) / 1e6


class Runner(cr.Runner):
    """The first version's runner with the second version's bound; `one` is the first
    version's, word for word, but for `bound`."""

    def one(self, name: str, packet: dict) -> dict:
        key = cr.request_key(self.model, self.prompt, self.schema, packet)
        final = self.store / f"{name}.{key}.json"
        if final.exists():
            return json.loads(final.read_text())
        attempts = []
        for attempt in (1, 2):
            if self.stopped.is_set():
                raise cr.CeilingReached("the pass stopped at the ceiling")
            try:
                self.ledger.reserve(f"{key}:{attempt}", bound(self.model, self.prompt, packet))
            except cr.CeilingReached:
                self.stopped.set()
                raise
            started = cr.now()
            got = cr.transport(self.model, lambda: self.send(self.body(packet)), self.sleep)
            got.update({"attempt": attempt, "started_utc": started, "finished_utc": cr.now(),
                        "model_requested": self.model})
            (self.store / f"{name}.{key}.attempt{attempt}.json").write_text(
                json.dumps(got, ensure_ascii=False))
            if got["status"] != 200:
                self.ledger.release(f"{key}:{attempt}")
                self.persist()
                return {"name": name, "key": key, "state": "pending", "attempts": attempts + [
                    {k: got.get(k) for k in ("status", "http_try", "body")}]}
            cost = cr.usd(self.model, got["usage"])
            self.ledger.record(f"{key}:{attempt}", {
                "request_key": key, "name": name, "model": self.model, "attempt": attempt,
                "model_returned": got["model_returned"], "usage": got["usage"], "usd": cost,
                "finished_utc": got["finished_utc"]})
            data, errors = cr.check_answer(got.get("text"), self.schema, packet)
            attempts.append({"attempt": attempt, "errors": errors, "usd": cost,
                             "model_returned": got["model_returned"],
                             "stop_reason": got.get("stop_reason")})
            if data is not None:
                result = {"name": name, "key": key, "state": "accepted", "answer": data,
                          "attempts": attempts}
                break
        else:
            result = {"name": name, "key": key, "state": "failed", "answer": None,
                      "attempts": attempts}
        partial = final.with_suffix(".partial")
        partial.write_text(json.dumps(result, ensure_ascii=False))
        partial.rename(final)
        self.persist()
        return result
