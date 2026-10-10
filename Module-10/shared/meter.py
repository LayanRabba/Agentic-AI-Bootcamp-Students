"""
shared/meter.py  --  a small, honest meter: what did this run cost?

Module 7's meter assumed one model. Today you ROUTE between two, so this one
counts per model -- otherwise "cheaper" is just a feeling:

    -- what that cost --------------------------------------------
      LLM calls ............ 12   (2 served from cache, 0 retried)
      openai/gpt-4o-mini ... 9 call(s), 4,210 tokens, $0.00139
      openai/gpt-4.1-mini .. 3 call(s), 2,980 tokens, $0.00310
      money ................ $0.00449
      time ................. 11.4 s  (p50 0.8 s / p95 2.6 s per call)

Two habits this file is trying to build:

  1. A cache hit is still a call you MADE -- it is just a call you did not PAY
     for. Counting them separately is how you see whether the cache is working.
  2. A retry costs full price. A run that "worked" after three retries cost
     four times what the happy path costs. Retries are counted, not hidden.
"""

from __future__ import annotations

import statistics
import threading
import time

# USD per 1,000,000 tokens on OpenRouter, checked 9 Oct 2026.
# Prices move. If your cost card looks wrong, check the real number at
# https://openrouter.ai/models and fix it here -- a guardrail built on a stale
# price is a guardrail that lies to you.
PRICES = {
    "openai/gpt-4o-mini": (0.15, 0.60),
    "openai/gpt-4.1-mini": (0.40, 1.60),
    "openai/gpt-4.1": (2.00, 8.00),
}


class Meter:
    """Counts calls, tokens and seconds per model. Safe from parallel threads."""

    def __init__(self) -> None:
        self.by_model: dict[str, dict[str, int]] = {}
        self.cache_hits = 0
        self.retries = 0
        self.blocked = 0          # calls a guardrail stopped before they happened
        self.latencies: list[float] = []
        self._lock = threading.Lock()
        self._start = time.perf_counter()

    # -- recording ------------------------------------------------------------
    def record(self, reply, model: str, seconds: float = 0.0) -> None:
        """A LangChain reply (from llm.invoke). Pass the model you actually used."""
        usage = getattr(reply, "usage_metadata", None) or {}
        self._add(model, int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0)), seconds)

    def record_raw(self, completion, model: str, seconds: float = 0.0) -> None:
        """An OpenAI-SDK completion (client.chat.completions.create)."""
        usage = getattr(completion, "usage", None)
        tin = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
        tout = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
        self._add(model, tin, tout, seconds)

    def _add(self, model: str, tin: int, tout: int, seconds: float) -> None:
        with self._lock:
            row = self.by_model.setdefault(model, {"calls": 0, "tin": 0, "tout": 0})
            row["calls"] += 1
            row["tin"] += tin
            row["tout"] += tout
            if seconds:
                self.latencies.append(seconds)

    def note_cache_hit(self, seconds: float = 0.0) -> None:
        with self._lock:
            self.cache_hits += 1
            if seconds:
                self.latencies.append(seconds)

    def note_retry(self) -> None:
        with self._lock:
            self.retries += 1

    def note_blocked(self) -> None:
        with self._lock:
            self.blocked += 1

    # -- reading --------------------------------------------------------------
    @property
    def calls(self) -> int:
        return sum(row["calls"] for row in self.by_model.values()) + self.cache_hits

    @property
    def paid_calls(self) -> int:
        return sum(row["calls"] for row in self.by_model.values())

    @property
    def tokens(self) -> int:
        return sum(row["tin"] + row["tout"] for row in self.by_model.values())

    def seconds(self) -> float:
        return time.perf_counter() - self._start

    def dollars(self) -> float:
        """What this run cost, adding up each model at its own price."""
        total = 0.0
        for model, row in self.by_model.items():
            price = PRICES.get(model)
            if price is None:
                continue  # unknown model: counted in tokens, not in dollars
            total += (row["tin"] * price[0] + row["tout"] * price[1]) / 1_000_000
        return total

    def unpriced(self) -> list[str]:
        return [m for m in self.by_model if m not in PRICES]

    def percentile(self, pct: float) -> float | None:
        """Per-call latency. p95 is the number your users actually complain about."""
        if not self.latencies:
            return None
        ordered = sorted(self.latencies)
        if len(ordered) == 1:
            return ordered[0]
        return statistics.quantiles(ordered, n=100, method="inclusive")[int(pct) - 1]

    # -- printing -------------------------------------------------------------
    def card(self, *, note: str = "") -> str:
        lines = ["-- what that cost " + "-" * 44]
        extra = []
        if self.cache_hits:
            extra.append(f"{self.cache_hits} served from cache")
        if self.retries:
            extra.append(f"{self.retries} retried")
        if self.blocked:
            extra.append(f"{self.blocked} blocked before sending")
        suffix = f"   ({', '.join(extra)})" if extra else ""
        lines.append(f"  LLM calls ............ {self.calls}{suffix}")

        for model, row in sorted(self.by_model.items()):
            price = PRICES.get(model)
            spend = (
                f"${(row['tin'] * price[0] + row['tout'] * price[1]) / 1_000_000:.5f}"
                if price else "(no price on file)"
            )
            label = (model[:20] + "..") if len(model) > 22 else model
            lines.append(
                f"  {label:<22} {row['calls']} call(s), "
                f"{row['tin'] + row['tout']:,} tokens, {spend}"
            )

        lines.append(f"  money ................ ${self.dollars():.5f}")
        p50, p95 = self.percentile(50), self.percentile(95)
        timing = f"{self.seconds():.1f} s"
        if p50 is not None and p95 is not None:
            timing += f"  (p50 {p50:.1f} s / p95 {p95:.1f} s per call)"
        lines.append(f"  time ................. {timing}")
        if self.unpriced():
            lines.append(f"  !! no price on file for: {', '.join(self.unpriced())} -- fix PRICES in meter.py")
        if note:
            lines.append(f"  note ................. {note}")
        return "\n".join(lines)


def banner(title: str) -> str:
    bar = "=" * 70
    return f"\n{bar}\n {title}\n{bar}"


def rule(title: str = "") -> str:
    return f"-- {title} " + "-" * max(4, 66 - len(title)) if title else "-" * 70


def indent(text: str, prefix: str = "   ") -> str:
    return "\n".join(prefix + line for line in str(text).strip().splitlines())
