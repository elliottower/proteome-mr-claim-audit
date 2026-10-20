# /// script
# requires-python = ">=3.12"
# dependencies = ["anthropic==1.13.0", "httpx==0.28.1", "jsonschema==4.26.0"]
# ///
"""Spend caps of the second release-resolution registration's stage A recode. The one ledger of
both registrations (/03_release_resolution/coding/spend.jsonl; coding_runner.Ledger, sealed,
imported unchanged) keeps its line format and its total ceiling; two hard stops are added:

- the registration as a whole: the ledger's total may not pass FIRST_REGISTRATION_USD +
  NEW_SPEND_CEILING_USD (86.09 + 300), so this registration's new spend stops at 300, of which
  295.42 remained when the recode was approved;
- a provider: this registration's spend at one provider (the ledger lines after the first
  registration's BASELINE_LINES, by model) may not pass its cap (Anthropic 170 US dollars, coding
  and judging together).

A request is not sent when its reserved bound would take either total, with every reservation in
flight, past its stop. Each runner gets a `View` of one shared `CappedLedger`, carrying its
provider, with the methods coding_runner.Ledger offers (reserve, record, release, spent,
reserved), so the sealed runners use it unchanged.
"""

import json
import pathlib

import coding_runner as cr

FIRST_REGISTRATION_USD = 86.09
NEW_SPEND_CEILING_USD = 300.0
BASELINE_LINES = 1_698
BASELINE_USD = 86.0906
PROVIDER_CAPS_USD = {"anthropic": 170.0}
PROVIDER = {"claude-sonnet-5-5": "anthropic", "claude-fable-5-1": "anthropic",
            "gpt-6.1-sol": "openai", "gpt-6-astra": "openai"}


class CapError(Exception):
    """The ledger's first lines are not the first registration's."""


class CappedLedger(cr.Ledger):
    def __init__(self, path: pathlib.Path, persist=lambda: None,
                 caps: dict[str, float] = PROVIDER_CAPS_USD):
        super().__init__(path, FIRST_REGISTRATION_USD + NEW_SPEND_CEILING_USD, persist)
        lines = [json.loads(line) for line in path.read_text().splitlines() if line.strip()] \
            if path.exists() else []
        base = sum(e["usd"] for e in lines[:BASELINE_LINES])
        if len(lines) < BASELINE_LINES or abs(base - BASELINE_USD) > 0.0001:
            raise CapError(f"the first {BASELINE_LINES} ledger lines sum to {base:.4f}")
        self.caps = caps
        self.provider_spent = {p: 0.0 for p in set(PROVIDER.values())}
        for e in lines[BASELINE_LINES:]:
            self.provider_spent[PROVIDER[e["model"]]] += e["usd"]
        self.provider_of: dict[str, str] = {}

    def new_spend(self) -> float:
        return self.spent - BASELINE_USD

    def reserve_for(self, provider: str, key: str, amount: float) -> None:
        with self.lock:
            if self.spent + sum(self.reserved.values()) + amount > self.ceiling:
                raise cr.CeilingReached(
                    f"registration stop: spent {self.spent:.2f}, reserved "
                    f"{sum(self.reserved.values()):.2f}, next bound {amount:.2f}, ceiling "
                    f"{self.ceiling:.2f}")
            cap = self.caps.get(provider)
            held = sum(a for k, a in self.reserved.items() if self.provider_of.get(k) == provider)
            if cap is not None and self.provider_spent[provider] + held + amount > cap:
                raise cr.CeilingReached(
                    f"{provider} stop: spent {self.provider_spent[provider]:.2f}, reserved "
                    f"{held:.2f}, next bound {amount:.2f}, cap {cap:.2f}")
            self.reserved[key] = amount
            self.provider_of[key] = provider

    def record(self, key: str, entry: dict) -> None:
        super().record(key, entry)
        with self.lock:
            self.provider_spent[PROVIDER[entry["model"]]] += entry["usd"]
            self.provider_of.pop(key, None)

    def release(self, key: str) -> None:
        super().release(key)
        with self.lock:
            self.provider_of.pop(key, None)

    def view(self, model: str) -> "View":
        return View(self, PROVIDER[model])


class View:
    def __init__(self, ledger: CappedLedger, provider: str):
        self.ledger, self.provider = ledger, provider

    def reserve(self, key: str, amount: float) -> None:
        self.ledger.reserve_for(self.provider, key, amount)

    def record(self, key: str, entry: dict) -> None:
        self.ledger.record(key, entry)

    def release(self, key: str) -> None:
        self.ledger.release(key)

    @property
    def spent(self) -> float:
        return self.ledger.spent

    @property
    def reserved(self) -> dict[str, float]:
        return self.ledger.reserved
