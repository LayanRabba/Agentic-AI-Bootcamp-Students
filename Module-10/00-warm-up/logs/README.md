# Logs for `00-warm-up/`

Captured output — **read these instead of running the code**. Every file
starts with a header saying what produced it.

> **The folder name is the running order.** Show `unsafe/` first, then the
> matching number in `safe/`. `unsafe/2` and `safe/2` are the same scenario
> with and without the guardrail, so they are meant to be read as a pair.

> A failing case prints **the prompt we sent and the reply we got**. That
> block is the evidence; the PASS/FAIL line is only the headline.


### Logs

| # | log | command | cost | what it proves |
|---|---|---|---|---|
| 1 | [`1-three-rounds.txt`](1-three-rounds.txt) | `python ask_it_nicely.py` | ~$ | naive prompt leaks, hardened does not, four lines of code CANNOT |
| 2 | [`2-all-15-attacks.txt`](2-all-15-attacks.txt) | `python ask_it_nicely.py --all` | ~$ | all 15 attacks with the technique note beside each |

These are pre-recorded. To make your own, run the command in the table from the
folder named in each log's header — your numbers will differ slightly, because
model latency and token counts vary between runs.

The same files are also under the module-level
[`logs/`](../logs/README.md), grouped by exercise.
