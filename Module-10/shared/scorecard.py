"""
shared/scorecard.py  --  a 100-line evaluation harness.

The measuring stick for every exercise in this module. It is deliberately
small, and it is deliberately NOT an LLM judging an LLM: every expectation here
is checked by CODE.

Why that matters today: you are about to make your agent cheaper. The only
thing standing between "cheaper" and "cheaper and broken" is a suite you can
re-run in 30 seconds.

    suite  = a handful of Cases, each with an expected verdict
    run    = run_suite(CASES, handler) -> Scorecard
    judge  = plain Python: did we get the verdict we expected, and did the
             reply avoid everything it must never contain?

    compare(before, after)  prints the delta -- and shouts if success dropped.

A suite of seven cases will not prove your agent is safe. It will catch the
change that broke it, which is the whole job of a regression test.
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field


# ── the transcript ───────────────────────────────────────────────────────────
# A failing test that does not show you the prompt is not a failing test, it is
# a rumour. "[FAIL] poisoned_note -- wrong verdict" tells you something broke;
# it does not tell you whether the model misbehaved, the fence was malformed,
# or your own expectation was wrong.
#
# So every exercise records what it SENT and what came BACK, and the scorecard
# prints both for any case that fails. Three lines in the handler, and the
# difference between a diagnosis and a guess.
@dataclass
class Transcript:
    system: str = ""
    user: str = ""
    steps: list[str] = field(default_factory=list)   # tool calls, gates, refusals
    reply: str = ""
    model: str = ""

    def is_empty(self) -> bool:
        return not (self.system or self.user or self.steps or self.reply)

    def render(self, width: int = 96) -> str:
        def block(label: str, body: str, limit: int = 1400) -> list[str]:
            if not body:
                return []
            body = body if len(body) <= limit else body[:limit] + f"\n  … [{len(body) - limit} more chars]"
            return [f"  ── {label} " + "─" * max(4, width - len(label) - 6),
                    *("    " + ln for ln in body.splitlines())]

        out: list[str] = []
        if self.model:
            out.append(f"  ── model ─ {self.model}")
        out += block("the SYSTEM prompt we sent", self.system)
        out += block("the USER message we sent (after the door, with any fence)", self.user)
        if self.steps:
            out.append("  ── what happened in between " + "─" * max(4, width - 32))
            out += ["    " + ln for ln in self.steps]
        out += block("what came BACK, verbatim", self.reply)
        return "\n".join(out)


CURRENT = Transcript()


def capture(*, system: str | None = None, user: str | None = None,
            reply: str | None = None, step: str | None = None,
            model: str | None = None) -> None:
    """Called from an exercise's handler. Everything is optional.

        capture(system=SYSTEM_PROMPT, user=user_block, model=MODEL)
        ...
        capture(step="asked for issue_refund(order_id='1142', amount=4999)")
        capture(reply=text)
    """
    if system is not None:
        CURRENT.system = system
    if user is not None:
        CURRENT.user = user
    if reply is not None:
        CURRENT.reply = reply
    if model is not None:
        CURRENT.model = model
    if step is not None:
        CURRENT.steps.append(step)


def _reset() -> Transcript:
    global CURRENT
    CURRENT = Transcript()
    return CURRENT


@dataclass
class Case:
    """One thing we expect the desk to do."""

    name: str
    text: str
    # "ANSWER" | "REFUSE" | "GATE" -- or a tuple, when more than one outcome is
    # genuinely safe. A safety test should assert the ABSENCE of the bad
    # outcome, not the presence of one particular good one: if the fence stops
    # an injection, the policy layer never fires, and demanding that it fire
    # would fail a system that is working. Pin the path and you are testing
    # your implementation; pin the outcome and you are testing your safety.
    expect: str | tuple[str, ...]
    must_not_contain: tuple[str, ...] = ()   # never appears in the reply, case-insensitive
    must_contain: tuple[str, ...] = ()       # at least one of these appears
    hard: bool = False                       # is this case genuinely difficult?
    note: str = ""


@dataclass
class Result:
    case: Case
    got: str
    reply: str
    seconds: float
    ok: bool
    why: str
    transcript: Transcript = field(default_factory=Transcript)


@dataclass
class Scorecard:
    label: str
    results: list[Result] = field(default_factory=list)
    dollars: float = 0.0

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.ok)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def success_rate(self) -> float:
        return 100.0 * self.passed / self.total if self.results else 0.0

    @property
    def failures(self) -> list[Result]:
        return [r for r in self.results if not r.ok]

    def percentile(self, pct: float) -> float:
        times = sorted(r.seconds for r in self.results)
        if not times:
            return 0.0
        if len(times) == 1:
            return times[0]
        return statistics.quantiles(times, n=100, method="inclusive")[int(pct) - 1]

    def table(self) -> str:
        lines = [f"-- scorecard: {self.label} " + "-" * max(4, 52 - len(self.label))]
        for r in self.results:
            mark = "PASS" if r.ok else "FAIL"
            lines.append(f"  [{mark}] {r.case.name:<18} want {wanted_text(r.case):<20} "
                         f"got {r.got:<7} {r.seconds:5.1f} s   {r.why}")
        lines.append(f"  success {self.passed}/{self.total} ({self.success_rate:.0f}%) "
                     f"· ${self.dollars:.5f} · p50 {self.percentile(50):.1f} s "
                     f"· p95 {self.percentile(95):.1f} s")
        return "\n".join(lines)


def wanted_text(case: Case) -> str:
    """How an expectation prints: "GATE" or "GATE|REFUSE"."""
    return case.expect if isinstance(case.expect, str) else "|".join(case.expect)


def judge(case: Case, got: str, reply: str) -> tuple[bool, str]:
    """Did the desk do what we expected? Decided by code, every time."""
    low = (reply or "").lower()
    for forbidden in case.must_not_contain:
        if forbidden.lower() in low:
            return False, f"the reply contained {forbidden!r}"
    if case.must_contain and not any(w.lower() in low for w in case.must_contain):
        return False, f"the reply mentioned none of {list(case.must_contain)}"
    wanted = (case.expect,) if isinstance(case.expect, str) else case.expect
    if got not in wanted:
        return False, "wrong verdict"
    return True, ""


def run_suite(cases, handler, *, label: str = "run", dollars_at_end=None,
              quiet: bool = False, show_prompts: bool = False) -> Scorecard:
    """Run `handler(case)` over every case. The handler returns (verdict, reply).

    `dollars_at_end` is a zero-argument callable (usually `meter.dollars`) read
    once the suite has finished, so the scorecard can show what it cost.

    `show_prompts` prints the full transcript for EVERY case. By default only
    failures print theirs -- which is the behaviour you want, because a passing
    case's prompt is noise and a failing case's prompt is the evidence.
    """
    card = Scorecard(label=label)
    for case in cases:
        _reset()
        started = time.perf_counter()
        try:
            got, reply = handler(case)
        except Exception as crash:            # a crash is a failure, not an excuse
            got, reply = "CRASH", f"{type(crash).__name__}: {crash}"
            capture(reply=f"{type(crash).__name__}: {crash}")
        took = time.perf_counter() - started
        ok, why = judge(case, got, reply or "")
        if not CURRENT.reply and reply:
            capture(reply=reply)              # handler did not record it; use what it returned
        result = Result(case, got, reply or "", took, ok, why, CURRENT)
        card.results.append(result)
        if not quiet:
            print(f"  [{'PASS' if ok else 'FAIL'}] {case.name:<18} {got:<7} ({took:.1f} s) {why}")
            if (show_prompts or not ok) and not result.transcript.is_empty():
                print(detail(result))
    if dollars_at_end is not None:
        card.dollars = float(dollars_at_end())
    return card


def detail(r: Result) -> str:
    """The evidence for one case: what we expected, what we sent, what came back."""
    head = (f"\n  ┌─ {'FAILED' if not r.ok else 'transcript'}: {r.case.name} "
            + "─" * max(4, 70 - len(r.case.name)))
    lines = [head,
             f"  │ expected : {wanted_text(r.case)}",
             f"  │ got      : {r.got}"]
    if r.why:
        lines.append(f"  │ because  : {r.why}")
    if r.case.must_not_contain:
        lines.append(f"  │ forbidden: {', '.join(repr(w) for w in r.case.must_not_contain)}")
    if r.case.must_contain:
        lines.append(f"  │ needed   : one of {', '.join(repr(w) for w in r.case.must_contain)}")
    if r.case.note:
        lines.append(f"  │ why this case exists: {r.case.note}")
    lines.append("  └" + "─" * 76)
    lines.append(r.transcript.render())
    lines.append("")
    return "\n".join(lines)


def failures_report(card: Scorecard) -> str:
    """Every failure, with its prompt and its reply. Print this after table()."""
    if not card.failures:
        return ""
    out = ["", "=" * 78,
           f" {len(card.failures)} FAILURE(S) -- the prompt and the reply for each",
           "=" * 78,
           "",
           " Read the SYSTEM and USER blocks before you change any code. Most",
           " 'the model is broken' bugs turn out to be a malformed prompt, a fence",
           " that did not close, or an expectation that was wrong in the first place.",
           ]
    for r in card.failures:
        out.append(detail(r))
    return "\n".join(out)


def _pct(before: float, after: float) -> str:
    if before == 0:
        return "   n/a"
    return f"{100.0 * (after - before) / before:+.0f}%"


def compare(before: Scorecard, after: Scorecard) -> str:
    """The delta table -- and the verdict that stops you shipping a cheap regression."""
    width = 13
    lines = [
        "-- before / after " + "-" * 52,
        f"  {'':<22}{before.label[:width]:>{width}}{after.label[:width]:>{width}}{'delta':>10}",
        f"  {'success':.<22}{f'{before.passed}/{before.total} {before.success_rate:.0f}%':>{width}}"
        f"{f'{after.passed}/{after.total} {after.success_rate:.0f}%':>{width}}"
        f"{f'{after.success_rate - before.success_rate:+.0f} pts':>10}",
        f"  {'money':.<22}{f'${before.dollars:.5f}':>{width}}{f'${after.dollars:.5f}':>{width}}"
        f"{_pct(before.dollars, after.dollars):>10}",
        f"  {'p95 latency':.<22}{f'{before.percentile(95):.1f} s':>{width}}"
        f"{f'{after.percentile(95):.1f} s':>{width}}"
        f"{_pct(before.percentile(95), after.percentile(95)):>10}",
        "",
    ]

    was_ok = {r.case.name for r in before.results if r.ok}
    now_bad = sorted(r.case.name for r in after.failures if r.case.name in was_ok)
    cheaper = after.dollars < before.dollars

    if now_bad:
        lines += [
            f"  [X] CHEAPER, BUT WRONG. {len(now_bad)} case(s) that used to pass now fail:",
            f"      {', '.join(now_bad)}",
            "",
            "      Cheaper but wrong is not cheaper. Do not ship this.",
            "      Raise the routing threshold, or send this case class to the capable model.",
        ]
    elif cheaper:
        lines += [
            f"  [OK] Cheaper AND no regression: ${before.dollars:.5f} -> ${after.dollars:.5f} "
            f"({_pct(before.dollars, after.dollars).strip()}), success held at {after.success_rate:.0f}%.",
            "       THIS is an optimisation. The one above is a bug with a discount.",
        ]
    else:
        lines += [
            "  [--] No regression, but no saving either. The change bought you nothing;",
            "       revert it rather than carry the extra code.",
        ]
    return "\n".join(lines)
