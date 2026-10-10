# 04-ex3-the-meter

Captured output — **read these instead of running the code**. Every file
starts with a header saying what produced it.

> **The folder name is the running order.** Show `unsafe/` first, then the
> matching number in `safe/`. `unsafe/2` and `safe/2` are the same scenario
> with and without the guardrail, so they are meant to be read as a pair.

> A failing case prints **the prompt we sent and the reply we got**. That
> block is the evidence; the PASS/FAIL line is only the headline.


### 🔴 `unsafe/` — show these FIRST

The guardrail is missing, or the practice is wrong. This is the before-picture, and it is the half that makes the other half land.

| # | log | command | cost | what it proves |
|---|---|---|---|---|
| 1 | [`1-no-routing-no-cache-no-ceiling.txt`](unsafe/1-no-routing-no-cache-no-ceiling.txt) | `python meter_starter.py` | ~$ | unbounded and unoptimised: works, saves nothing, and the table says so |
| 2 | [`2-greedy-all-on-the-cheap-model.txt`](unsafe/2-greedy-all-on-the-cheap-model.txt) | `python meter_solution.py --greedy` | ~$ | cost-cutting with no regard for quality -- read the before/after verdict |

### 🟢 `safe/` — show these SECOND

The guardrail is in place.

| # | log | command | cost | what it proves |
|---|---|---|---|---|
| 1 | [`1-routed-cached-measured.txt`](safe/1-routed-cached-measured.txt) | `python meter_solution.py` | ~$ | routing -48%, caching -72%, success held at 100% |
| 2 | [`2-risk-meter-price-buys-nothing.txt`](safe/2-risk-meter-price-buys-nothing.txt) | `python meter_solution.py --risk-only` | ~$ | which model needs saving more often -- the four-cell table |
| 3 | [`3-budget-ceiling-trips.txt`](safe/3-budget-ceiling-trips.txt) | `python meter_solution.py --budget 0.002` | ~$ | the ceiling tripping; everything after it fails closed |

These are pre-recorded. To make your own, run the command in the table from the
folder named in each log's header — your numbers will differ slightly, because
model latency and token counts vary between runs.
