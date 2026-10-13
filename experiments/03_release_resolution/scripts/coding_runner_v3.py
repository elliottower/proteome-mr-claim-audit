# /// script
# requires-python = ">=3.12"
# dependencies = ["anthropic==1.13.0", "httpx==0.28.1", "jsonschema==4.26.0"]
# ///
"""Third version of the coding runner (scripts/coding_runner_v2.py and scripts/coding_runner.py,
sealed, unchanged and imported). Two defects of the first SA1 run (PREREG.log, 2026-10-13) are
fixed:

- `call_claude`: a streamed message with structured output is a `ParsedMessage`, which has no
  `_request_id`; the first version read it after the response had arrived and been billed, so
  every Claude answer was lost with an AttributeError before it was stored or its cost
  recorded. The message's own `id` is recorded instead, and the response is written before any
  field is read.
- `Runner.run`: an exception other than the ceiling ended the whole pass (and, in a container
  running both models, the other model's pass with it). Here an exception in one request leaves
  that request pending, with the error recorded, and the pass goes on.

The bound of the second version is kept.
"""

import concurrent.futures

import coding_runner as cr
import coding_runner_v2 as cr2


def call_claude(client, body: dict) -> dict:
    with client.messages.stream(**body) as stream:
        message = stream.get_final_message()
    raw = message.to_dict()
    text = next((b.get("text") for b in raw.get("content", []) if b.get("type") == "text"), None)
    return {"status": 200, "model_returned": raw.get("model"),
            "stop_reason": raw.get("stop_reason"), "usage": raw.get("usage") or {},
            "text": text, "request_id": raw.get("id")}


class Runner(cr2.Runner):
    def one(self, name: str, packet: dict) -> dict:
        """The second version's request; on an exception other than the ceiling, the request's
        reservations are released before the exception goes on."""
        try:
            return super().one(name, packet)
        except cr.CeilingReached:
            raise
        except Exception:
            key = cr.request_key(self.model, self.prompt, self.schema, packet)
            for k in list(self.ledger.reserved):
                if k.startswith(f"{key}:"):
                    self.ledger.release(k)
            raise

    def run(self, packets: list[tuple[str, dict]]) -> dict:
        results, stopped, errors = [], None, []
        with concurrent.futures.ThreadPoolExecutor(self.workers) as pool:
            futures = {pool.submit(self.one, name, p): name for name, p in packets}
            for f in concurrent.futures.as_completed(futures):
                try:
                    results.append(f.result())
                except cr.CeilingReached as e:
                    stopped = str(e)
                except Exception as e:  # one request's defect must not end the pass
                    errors.append({"name": futures[f], "error": f"{type(e).__name__}: {e}"[:500]})
                    results.append({"name": futures[f], "state": "pending", "attempts": []})
        states = {s: sum(r["state"] == s for r in results)
                  for s in ("accepted", "failed", "pending")}
        return {"model": self.model, "packets": len(packets), "states": states,
                "not_sent_ceiling": len(packets) - len(results), "stopped": stopped,
                "errors": errors, "spent_usd": round(self.ledger.spent, 4), "results": results}
