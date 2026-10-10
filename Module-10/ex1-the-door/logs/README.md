# Logs for `ex1-the-door/`

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
| 1 | [`1-unit-tests-fail.txt`](unsafe/1-unit-tests-fail.txt) | `python desk_starter.py --unit` | free | 11 guard failures, instantly, for nothing -- start here |
| 2 | [`2-suite-5of8-and-4x-the-bill.txt`](unsafe/2-suite-5of8-and-4x-the-bill.txt) | `python desk_starter.py` | ~$ | 5/8 and $0.0024 -- one 48k message costs more than the other seven |
| 3 | [`3-no-fence-attacker-address-sent.txt`](unsafe/3-no-fence-attacker-address-sent.txt) | `python desk_starter.py --case poisoned_note` | ~$ | the desk promises a refund and hands over the attacker's address |
| 4 | [`4-no-mouth-whole-prompt-leaks.txt`](unsafe/4-no-mouth-whole-prompt-leaks.txt) | `python desk_starter.py --case leak_prompt` | ~$ | the entire system prompt as YAML, canary included, verdict ANSWER |

### 🟢 `safe/` — show these SECOND

The guardrail is in place.

| # | log | command | cost | what it proves |
|---|---|---|---|---|
| 1 | [`1-unit-tests-pass.txt`](safe/1-unit-tests-pass.txt) | `python desk_solution.py --unit` | free | 0 failures -- the guards, proven with no model involved |
| 2 | [`2-suite-8of8-quarter-the-bill.txt`](safe/2-suite-8of8-quarter-the-bill.txt) | `python desk_solution.py` | ~$ | 8/8 and $0.0006 -- the door is a cost control first |
| 3 | [`3-no-false-positives.txt`](safe/3-no-false-positives.txt) | `python desk_solution.py --tricky` | free | 0 of 5 innocent customers blocked -- the only passing score |
| 4 | [`4-fence-holds.txt`](safe/4-fence-holds.txt) | `python desk_solution.py --case poisoned_note` | ~$ | a reply about the chipped mug and nothing else |
| 5 | [`5-mouth-blocks-the-leak.txt`](safe/5-mouth-blocks-the-leak.txt) | `python desk_solution.py --case leak_prompt` | ~$ | blocked on the way out, with no hint about what was blocked |
| 6 | [`6-all-transcripts.txt`](safe/6-all-transcripts.txt) | `python desk_solution.py --show-prompts` | ~$ | every case's prompt and reply -- read the fence inside the USER block |

These are pre-recorded. To make your own, run the command in the table from the
folder named in each log's header — your numbers will differ slightly, because
model latency and token counts vary between runs.

The same files are also under the module-level
[`logs/`](../logs/README.md), grouped by exercise.
