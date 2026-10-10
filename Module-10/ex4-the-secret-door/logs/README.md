# Logs for `ex4-the-secret-door/`

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
| 1 | [`1-provider-key-pasted.txt`](unsafe/1-provider-key-pasted.txt) | `python secret_door.py --case provider_key` | free | WHAT THE USER TRIED TO SEND: the key that pays for this very call |
| 2 | [`2-dotenv-pasted.txt`](unsafe/2-dotenv-pasted.txt) | `python secret_door.py --case dotenv_paste` | free | a whole env file; MODEL= ignored, CLIENT_SECRET= blocked |
| 3 | [`3-stack-trace-with-password.txt`](unsafe/3-stack-trace-with-password.txt) | `python secret_door.py --case stack_trace` | free | the secret arriving as collateral -- they wanted help with the traceback |
| 4 | [`4-connection-string.txt`](unsafe/4-connection-string.txt) | `python secret_door.py --case connection_string` | free | the rule captures the PASSWORD group, so the host stays readable |

### 🟢 `safe/` — show these SECOND

The guardrail is in place.

| # | log | command | cost | what it proves |
|---|---|---|---|---|
| 1 | [`1-suite-14-cases.txt`](safe/1-suite-14-cases.txt) | `python secret_door.py` | free | 7 blocked, 2 redacted, 5 allowed -- and 0 failures |
| 2 | [`2-the-policy-table.txt`](safe/2-the-policy-table.txt) | `python secret_door.py --policy` | free | eight rules as DATA: add a rule, add a row |
| 3 | [`3-audit-log-holds-no-secrets.txt`](safe/3-audit-log-holds-no-secrets.txt) | `python secret_door.py --audit` | free | read it for what is NOT in it -- rule, offset, length, fingerprint |
| 4 | [`4-innocent-password-question-allowed.txt`](safe/4-innocent-password-question-allowed.txt) | `python secret_door.py --case forgot_password` | free | says 'password' twice and sails through -- the false positive that matters |
| 5 | [`5-iban-redacted-and-answered.txt`](safe/5-iban-redacted-and-answered.txt) | `python secret_door.py --case customer_iban` | free | redact-and-continue, and why redaction is by span |

These are pre-recorded. To make your own, run the command in the table from the
folder named in each log's header — your numbers will differ slightly, because
model latency and token counts vary between runs.

The same files are also under the module-level
[`logs/`](../logs/README.md), grouped by exercise.
