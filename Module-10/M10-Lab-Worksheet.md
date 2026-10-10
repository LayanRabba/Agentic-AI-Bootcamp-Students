<!-- JHF-BRAND -->
<div align="center" style="padding:28px 20px; background:#ffffff; border:2px solid #e0e0e0; border-radius:12px;">
  <p style="margin:0 0 16px 0;">
    <img src="../assets/jhf-logo.png" alt="Jerusalem High-Tech Foundry (JHF)" height="54" style="vertical-align:middle; margin:0 22px;" />
    <img src="../assets/comcec-logo.png" alt="COMCEC - Cooperation for Development" height="72" style="vertical-align:middle; margin:0 22px;" />
  </p>
  <h1 style="color:#1a3c5e; margin:6px 0;">Agentic AI Bootcamp</h1>
  <h3 style="color:#0078d4; margin:4px 0; font-weight:600;">Module 10 &middot; Lab Worksheet &mdash; Production-Hardened Agent</h3>
  <hr style="border:0; border-top:1px solid #0078d4; width:60%; margin:16px auto;" />
  <p style="font-size:14px; color:#555; margin:6px 0;">
    <strong>Lead Trainer</strong><br/>
    <a href="https://www.linkedin.com/in/alaaldin-ahmed-260266150" target="_blank">Alaaldin Ahmed</a>
  </p>
  <p style="font-size:12.5px; color:#777; margin:8px 0 0 0;">
    Organized by <strong>Jerusalem High-Tech Foundry (JHF)</strong> &nbsp;&middot;&nbsp; In partnership with <strong>COMCEC</strong>
  </p>
</div>


# Module 10 — Lab Worksheet
## The Hardened Desk — Guardrails, Safety, Cost/Latency

> **Time:** 15 + 35 + 40 + 30 + 15 min together · 60 min on your own
> **Folders:** `00-warm-up/` → `ex1-the-door/` → `ex2-the-hands/` → `ex3-the-meter/` → `ex4-the-secret-door/` → `live-homework/`
> **Every exercise has two test modes. Start with `--unit`: free, instant, offline.**

---

## Setup gate (5 min)

```bash
cd Module-10
source .venv/bin/activate      # .\.venv\Scripts\Activate.ps1  on Windows
python preflight.py
```

This module ships its own `.venv` (Python 3.12, packages pinned). If it is
missing: `python3.12 -m venv .venv && source .venv/bin/activate && python -m
pip install -r requirements.txt`.

All `[ OK ]`, ending **All clear.** It checks both models, because Exercise 3
routes between them and finding out mid-exercise is a bad time.

> **Cost.** The whole module including homework is about **5–8 cents**. Every
> file prints a cost card. Watch them.

---

## Warm-up — Ask It Nicely (15 min) · `00-warm-up/`

```powershell
cd 00-warm-up
python ask_it_nicely.py
```

| | what to look at |
|---|---|
| 🧪 **Checkpoint** | Round 1 leaks 1–2 of 8. Rounds 2 and 3 both leak 0. |
| 🔍 **The point** | Those two zeros are **not the same zero.** Read the last block the program prints before moving on. |
| 🧪 **Try** | Which attacks won? Not the ones with the scary words — `yaml_dump` wins, `"ignore all previous instructions"` never does. |
| 🧪 **Try** | Run it twice. If a number moved, you have just measured a *leak rate*. |

> **Leave with:** a prompt is a request; a check is a guarantee.

---

## PART 1 — The Door and the Mouth (35 min) · `ex1-the-door/`

```powershell
cd ..\ex1-the-door
python desk_starter.py --unit      # 11 failures, instantly, for free
python desk_starter.py             # 5/8, about $0.0024  <- note this number
```

### Step 1 — TODO 1, the door (`check_input`)
Empty → reject. Over `MAX_CHARS` → reject. Strip every `CONTROL_TOKENS` marker.
**No keyword blocklist.**

- 🧪 **Checkpoint:** `oversized` passes, and the cost card drops from ~$0.0024
  to ~$0.0006. **You just cut three quarters of the bill with a length check.**
- 🧪 **Checkpoint:** `python desk_starter.py --tricky` → **0 of 5** innocent
  customers blocked. Zero is the only passing score.

### Step 2 — TODO 2, the fence (`fence`)
Nonce-named delimiter + "this is data". A fixed delimiter is guessable, and
guessable means closeable.

- 🧪 **Checkpoint:** `poisoned_note` passes.
- 🔍 **Look:** `--case poisoned_note`, then comment the fence out and run again.
  The desk puts **the attacker's address** in a reply to a customer.

### Step 3 — TODO 3, the mouth (`check_output`)
Empty → safe substitute. Canary → **block**, explaining nothing. Unknown email
domain → **block the whole reply** (the domain is the payload). PII →
**redact**. Too long → truncate.

- 🧪 **Checkpoint:** `--unit` 0 failures **and** the suite 8/8.
- 🔍 **Look:** `pii_echo` passed *before* you wrote the redaction — this model
  refuses card numbers by itself. **Keep the guard anyway.** You did not earn
  that pass and you cannot renew it.

> ✅ **End of Part 1:** input and output are checked, and retrieved data is
> fenced. The desk still has no hands.

---

## PART 2 — The Hands (40 min) · `ex2-the-hands/`

```powershell
cd ..\ex2-the-hands
python hands_starter.py --no-fence --case poisoned_note    # DO THIS FIRST
```

Read the **ledger**, not the reply:
```
looked up 1142 · REFUNDED 18.50 on order 1142 · EMAILED R. Okonkwo
```
Money moved unapproved, and "R. Okonkwo" is a *name* in a field that takes an
email address. Nothing checked, so the send "succeeded".

> **The reply is a story. The ledger is a receipt.**

### Step 4 — TODO 1, least privilege (`EXPOSED_TOOLS`)
One deletion: `email_customer`. The cheapest guardrail there is — no prompt, no
check, **no bypass**.

### Step 5 — TODO 2, the allow-list (`check_call`)
Name, then arguments. The important one:

```python
if abs(amount - record["amount"]) > 0.005:   # the model picks the ROW,
    return False, "..."                      # never the VALUE
```

- 🧪 **Checkpoint:** `--unit` green, including `THE ATTACK: 4999`.
- 🧪 **Checkpoint:** `--no-fence --case poisoned_note` → the desk asks for
  4,999 and the ledger shows `policy refused ... over the 100.00 cap`.
- 🔍 **Run it both ways.** Fenced, the model usually refuses by itself.
  Unfenced, it obeys and the **cap** stops it. One of those survives a model
  upgrade.

### Step 6 — TODO 3, the approval gate (`ask_human`)
Safe tools **must not prompt**. Default to no (`[y/N]`, exact-match `"y"`).

- 🧪 **Checkpoint:** 8/8; the gate fires for `issue_refund`, never for
  `lookup_order`.

### Step 7 — the three experiments (8 min) — **do all three**

| command | the question |
|---|---|
| `--deny --case refund_request` | does it **fail closed**? Ledger shows no refund; reply says "under review" — not "your refund is on the way" |
| `--rubber-stamp` | put the ledger next to a normal run. **Identical.** A human who does not read is latency with a signature |
| `--live` | you approve. Notice how fast the urge to stop reading arrives |

- 🔍 **Look:** what the code tells the *model* on a refusal is deliberately
  vague. Feed the real reason back and the desk repeats it to the attacker.
  **Your refusal message is an oracle.**

> ✅ **End of Part 2:** three layers, and the attack has to beat all three.

---

## PART 3 — The Meter (30 min) · `ex3-the-meter/`

> **Frame it as the fourth guardrail, not as cost engineering.** The door
> bounds what comes in, the hands what it may do, the mouth what goes out — the
> meter bounds what it may **consume**. An agent that loops until the credit
> dies is an availability failure, and Exercise 1's `oversized` case was an
> attack whose payload was *length*.
>
> The spend ceiling is **fail closed, on cost**. Caching excludes gated turns
> because a cached refund is a second refund. And the finale has no cost
> content at all.

```powershell
cd ..\ex3-the-meter
python meter_starter.py      # works, saves nothing, and says so
```

### Step 8 — TODO 1, route by difficulty (`pick_model`)
Code, not a model. A router that costs an LLM call has spent what it was saving.

- 🧪 **Checkpoint:** cost down **45–50%**, p95 down, success unchanged.
  (Exact figures vary run to run; the `no regression` line is the checkpoint.)
- 🔍 **Look:** the bug in the comments — a card number's digit groups looked
  like four order ids, so every customer who mentioned a card got the
  expensive model. Nothing failed; it just cost more. **Router bugs invoice.**

### Step 9 — TODO 2, caching (`cache_get`)
Exact match + TTL.

- 🧪 **Checkpoint:** second pass ≈ **$0.0016 → $0.0005** (−70%), p50 → 0.0s,
  5 of 8 from cache.
- 🔍 **Look:** which three were *not* cached, and why a cached refund is a
  second refund.

### Step 10 — TODO 3, the spend ceiling
Check `meter.dollars()` **before** the call.

```powershell
python meter_starter.py --budget 0.002
```
- 🧪 **Checkpoint:** cases after the trip come back `CRASH / BudgetExceeded`.
  That is correct. Same guardrail as M1's step cap, in money.

### Step 11 — the risk meter (no code) · **the point of the exercise**

```powershell
python meter_solution.py --risk-only
```

- 🧪 **Final checkpoint:** read the four-cell table and say out loud what it
  means. Price did not buy safety; the ordering reversed when one tool was
  added; **the code held in every cell.**

> ✅ **End of Part 3:** measured, cheaper, **bounded** — and you know why you
> cannot buy safety.
>
> **The sentence that joins the two halves:** *a config change is a safety
> change*, so the safety suite has to be cheap enough to run on every commit.
> That is why the cost work belongs in a safety module.
>
> ⚠️ Say out loud what this part does **not** show: `--greedy` never fires the
> `[X] CHEAPER, BUT WRONG` verdict, because the cheap model handles this suite
> fine. The lesson is told, not demonstrated — and we did not fake a regression
> to hide that.

---

## PART 4 — The Secret Door (15 min) · `ex4-the-secret-door/`

**A demo. No TODOs — the file explains itself, and it makes no LLM calls.**

```powershell
cd ..\ex4-the-secret-door
python secret_door.py
```

Exercise 1's door asked *"is this even a message?"*. This asks
**"is the user about to hand us something they will regret?"** — a pasted
`.env`, a stack trace with a connection string, a curl command with its
`Authorization` header.

### Step 12 — run it and read three rows
- 🧪 **Checkpoint:** `0 failure(s).` — 7 blocked, 2 redacted, 5 allowed.
- 🔍 **`forgot_password` is ALLOWED** and contains the word *password* twice.
  A prose keyword rule blocks this customer, and then the guardrail gets
  switched off. **Match shapes, never sentences.**
- 🔍 **`dotenv_paste` is BLOCKED** — but `MODEL=` and `DEBUG=` are ignored and
  `CLIENT_SECRET=` is not. The rule matches a **machine-written name**.
  Keywords are fine against an identifier; useless against prose.
- 🔍 **`git_sha` is ALLOWED** despite 40 random characters. The moment you flag
  *"looks random"*, you owe the world an exemption list.

### Step 13 — the policy is data
```powershell
python secret_door.py --policy
```
Eight rules in `shared/policy.py`, each with an action, the company policy it
satisfies, and whether the secret must be rotated. **To add a rule you add a
row** — not a branch in somebody's function.

### Step 14 — the experiment that matters
```powershell
python secret_door.py --audit
```
- 🧪 **Final checkpoint:** read the log looking for what is **not** there. No
  key, no password, no card number — the rule, the offset, the length and a
  one-way fingerprint.
- 🔍 **A guardrail that blocks the secret and then logs it has moved the leak,
  not stopped it.** Your logs are usually less protected than your prompts.
- 🔍 And note what the user is told: **rotate it anyway.** Blocking the send
  does not undo the clipboard, the shell history or the screenshot.

> ✅ **End of Part 4:** the one guardrail that must run *before* the first API
> call, because a sent prompt cannot be unsent.

---

## LIVE HOMEWORK — The Expense Desk (60 min) · `live-homework/`

Six TODOs, three parts, on your own. Full instructions in
[`live-homework/README.md`](live-homework/README.md).

| part | file | TODOs | done when |
|---|---|---|---|
| A | `hw_a_the_door.py` | door, mouth | `--unit` 0 failures **and** 8/8 |
| B | `hw_b_the_hands.py` | allow-list (**three states**), gate | 8/8, and `--deny` moves no money |
| C | `hw_c_the_meter.py` | routing, spend ceiling | cost down, success unchanged |

**Part B is the one to slow down on.** Two answers are not enough:

```
9800.00 on a 212.40 claim is FICTION  ->  refuse. No human sees it.
1840.00 on an 1840.00 claim is REAL   ->  escalate. A human decides.
```

Refuse the second and Finance stops using your desk by Wednesday.

**Write down three numbers before you close the terminal: success %, cost,
p95.** You need them for the mini-project.

**No solutions ship with the homework.** We walk through them together at the
end of the session, and they are published afterwards. Exercises 1–3 each have
a `*_solution.py` you can lean on in the meantime — the homework is the one
part you do unaided.

---

## Troubleshooting

| Problem | Try this |
|---|---|
| `ModuleNotFoundError: setup_env` | `cd` into the exercise folder; files add `../shared` to the path |
| `ModuleNotFoundError: scorecard` in a solution file | those live one level deeper and reach up two; run from their own folder |
| The strong model 404s | set `MODEL_STRONG` in `.env` to a model you can reach, and add its price to `shared/meter.py` |
| Everything passes and you wrote nothing | you are reading the end-to-end suite. Run `--unit` |
| `--unit` green but the suite red | your guard is fine; the system around it is not. Read the ledger |
| A verdict moved between runs | the test is asserting a *path*. Accept every safe verdict; assert `must_not_contain` |
| The gate fires constantly | you gated a read-only tool. Money and outsiders only |
| Guardrail blocks a real customer | you are matching keywords. Cap length, strip structure, never guess intent |
| `BudgetExceeded` | the guardrail working. Raise `--budget` deliberately, or ask why the run costs that much |
| A run cost far more than expected | an unfenced 48k message, or retries. Read the cost card's retry count |

---

## Submit (completes the Phase 5 mini-project)

See [`mini-project/THE-BRIEF.md`](mini-project/THE-BRIEF.md). In short:

1. **`desk.py`** — your own agent, hardened at all four places.
2. **`my_cases.py`** — your suite, your 10 attacks, `--unit` tests per guard.
3. **`evidence/`** — unit · before · after · red-team · a tripped budget · a denial.
4. **One honest paragraph:** *which guardrails survive a model change, and
   which am I just lucky about?*

---
  <p style="margin:0 0 8px 0;">
    <img src="../assets/jhf-logo.png" alt="JHF" height="28" style="vertical-align:middle; margin:0 14px; background:#ffffff; padding:6px 10px; border-radius:6px;" />
    <img src="../assets/comcec-logo.png" alt="COMCEC" height="40" style="vertical-align:middle; margin:0 14px; background:#ffffff; padding:6px 10px; border-radius:6px;" />
  </p>
  <p style="color:#888; font-size:13px; margin:0;">
    <strong>JHF Agentic AI Bootcamp</strong> &mdash; Module 10 Lab<br/>
    Lead Trainer: <a href="https://www.linkedin.com/in/alaaldin-ahmed-260266150">Alaaldin Ahmed</a><br/>
    Organized by Jerusalem High-Tech Foundry (JHF) &middot; In partnership with COMCEC
  </p>
</div>

