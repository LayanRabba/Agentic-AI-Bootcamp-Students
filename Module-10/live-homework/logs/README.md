# Logs for `live-homework/`

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
| 1 | [`1-part-a-todos-unwritten.txt`](unsafe/1-part-a-todos-unwritten.txt) | `python hw_a_the_door.py --unit` | free | 7 failures: exactly what a student starts Part A from |
| 2 | [`2-part-b-todos-unwritten.txt`](unsafe/2-part-b-todos-unwritten.txt) | `python hw_b_the_hands.py --unit` | free | 7 failures, with the allow/escalate/refuse column |

These are pre-recorded. To make your own, run the command in the table from the
folder named in each log's header — your numbers will differ slightly, because
model latency and token counts vary between runs.

The same files are also under the module-level
[`logs/`](../logs/README.md), grouped by exercise.
