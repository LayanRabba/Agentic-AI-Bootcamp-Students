# 03-ex2-the-hands

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
| 1 | [`1-unit-tests-fail.txt`](unsafe/1-unit-tests-fail.txt) | `python hands_starter.py --unit` | free | 8 policy failures, including a tool that does not exist |
| 2 | [`2-attack-lands-money-moves.txt`](unsafe/2-attack-lands-money-moves.txt) | `python hands_starter.py --no-fence --case poisoned_note` | ~$ | unapproved refund, and mail sent to 'R. Okonkwo' -- a name, not an address |
| 3 | [`3-suite-attack-in-the-ledger.txt`](unsafe/3-suite-attack-in-the-ledger.txt) | `python hands_starter.py --no-fence` | ~$ | the full ledger with the attack landing twice |
| 4 | [`4-rubber-stamp-ledger-identical.txt`](unsafe/4-rubber-stamp-ledger-identical.txt) | `python hands_solution.py --rubber-stamp` | ~$ | GOOD CODE, BAD PRACTICE: a human who approves without reading. Diff this ledger against safe/2 -- they are the same |

### 🟢 `safe/` — show these SECOND

The guardrail is in place.

| # | log | command | cost | what it proves |
|---|---|---|---|---|
| 1 | [`1-unit-tests-pass.txt`](safe/1-unit-tests-pass.txt) | `python hands_solution.py --unit` | free | 0 failures, plus the gate assertions |
| 2 | [`2-suite-8of8-nothing-moved.txt`](safe/2-suite-8of8-nothing-moved.txt) | `python hands_solution.py` | ~$ | 8/8 and a ledger with no unauthorised movement |
| 3 | [`3-attack-refused-by-the-cap.txt`](safe/3-attack-refused-by-the-cap.txt) | `python hands_solution.py --no-fence --case poisoned_note` | ~$ | THE MONEY SHOT: the model obeys the injection, one float comparison stops it |
| 4 | [`4-suite-no-fence-layers-hold.txt`](safe/4-suite-no-fence-layers-hold.txt) | `python hands_solution.py --no-fence` | ~$ | the fence removed on purpose; the policy layer holds anyway |
| 5 | [`5-deny-fails-closed.txt`](safe/5-deny-fails-closed.txt) | `python hands_solution.py --deny --case refund_request` | ~$ | no refund in the ledger, and no lie to the customer |
| 6 | [`6-all-transcripts.txt`](safe/6-all-transcripts.txt) | `python hands_solution.py --no-fence --show-prompts` | ~$ | every case's prompt, tool steps and reply -- the long one |

These are pre-recorded. To make your own, run the command in the table from the
folder named in each log's header — your numbers will differ slightly, because
model latency and token counts vary between runs.
