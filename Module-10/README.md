# Module 10 — Guardrails, Safety & Cost/Latency

*Module 10 of the syllabus. One Saturday.*

> **The one thing to leave with:** a prompt is a **request**; a check in code is
> a **guarantee**. Guardrails live in four places — **the door** (what comes
> in), **the hands** (what it can do), **the mouth** (what goes out) and **the
> meter** (what it may spend). Anything you only *asked* the model to do is not
> a control.

Your agent works. Today you find out what happens when someone attacks it,
when a tool costs real money, and when the bill arrives — and you fix all
three with code you can test offline.

---

## Read this before you touch anything

### 1. Use this module's own environment

**This module ships its own `.venv`, so there is nothing to hunt for.**
Python 3.12, with the four pinned packages already installed.

```bash
cd Module-10
source .venv/bin/activate                 # macOS / Linux
.\.venv\Scripts\Activate.ps1               # Windows PowerShell
```

Your prompt now starts with `(.venv)`. If PowerShell says *running scripts is
disabled*, run `Set-ExecutionPolicy -Scope Process RemoteSigned` and activate
again.

> **Prefer not to activate anything?** Every command in this module also works
> by naming the interpreter directly, which is handy when you have several
> terminals open:
> ```bash
> cd Module-10/ex1-the-door
> ../.venv/bin/python desk_starter.py --unit
> ```

### 2. If the `.venv` is missing or you want to rebuild it

```bash
cd Module-10
python3.12 -m venv .venv                  # py -3.12 -m venv .venv  on Windows
source .venv/bin/activate
python -m pip install -r requirements.txt
```

**Nothing new to install beyond that.** No guardrail library, no policy engine,
no classifier service — every guardrail today is plain Python, because you
cannot judge a tool you have never had to do without.

### 3. Your key

Exercise 3 routes between two models, so you need **one** OpenRouter key and
the module needs to find it. `shared/setup_env.py` looks in this order:

| order | where | holds |
|---|---|---|
| 1 | your **shell environment** | wins over every file |
| 2 | `Module-10/.env` | the two model names. **No secrets.** |
| 3 | the **repo-root** `.env` | `OPENROUTER_API_KEY` — the same key as every module |

So if the repo-root `.env` already works for Modules 1–7, it works here and you
need to do nothing.

**If you would rather not keep the key in a file at all** — which is the
company-policy answer, and the right habit — supply it per session instead:

```bash
read -rs "?OpenRouter key: " OPENROUTER_API_KEY && export OPENROUTER_API_KEY
```

That reads it without echoing, without touching disk, and without landing in
your shell history. It lasts until you close the terminal. On Windows use
`$env:OPENROUTER_API_KEY` — **never `setx`**, which writes it to the registry
in plaintext.

There is a `.env.example` at the **repo root** showing the variables. Copy it
to `.env` there and fill in your key — `.env` is git-ignored, so it never gets
committed.

### 4. Setup check

```bash
cd Module-10
python preflight.py                        # or  .venv/bin/python preflight.py
```

Every line should say `[ OK ]` and end with **All clear.** It checks **both**
models, because Exercise 3 needs both and finding out mid-exercise is a bad
time.

> **Money.** Today makes real calls. The whole module, including the homework,
> costs about **5–8 cents**. Every file prints a cost card, and watching them
> is half the point.

---

## The measuring stick

Guardrails are not a feeling. Every exercise today is judged by
**`shared/scorecard.py`** — a 100-line harness that runs a handful of cases and
prints success / cost / p95.

It is small on purpose, and it is **not an LLM judging an LLM**: every
expectation is checked by plain Python. Eight cases will not prove your agent is
safe. They will catch the change that broke it, which is the whole job of a
regression test.

---

## The module, in order

**First half — together.** We build each exercise live; you type along.

| # | folder | what we build | the guardrail is at… | time |
|---|---|---|---|---|
| 0 | **`00-warm-up/`** | Three defences against one attack. No framework. | — | 15 min |
| 1 | **`ex1-the-door/`** | Input checks, a fence around retrieved data, output checks. | **the door and the mouth** | 35 min |
| 2 | **`ex2-the-hands/`** | Least privilege, an allow-list, an approval gate. | **the hands** | 40 min |
| 3 | **`ex3-the-meter/`** | A spend ceiling that fails closed, routing, caching — and the measurement that shows **price does not buy safety**. | **the meter** | 30 min |
| 4 | **`ex4-the-secret-door/`** | A policy that rejects credentials the **user** pastes in. **A demo — no TODOs.** | **the door, inward** | 15 min |

**Second half — on your own.**

| # | folder | what you do | time |
|---|---|---|---|
| ★ | **`live-homework/`** | **The Expense Desk** — the same three moves, alone, on a new domain. Six TODOs. | 60 min |
| ▶ | **`mini-project/`** | **Harden your own agent** and red-team it. | ~3–4 h, during the week |

**Every folder has its own README. That README is your worksheet.**
The run order with checkpoints is in [`M10-Lab-Worksheet.md`](M10-Lab-Worksheet.md).

Each exercise has a **starter** that runs from minute one and fails loudly, a
few **TODOs**, and a **solution**. Exercise 4 is the exception: it is a demo
with no TODOs, and the explanation lives in the code.

### 📁 `logs/` — every run, already run

**You do not have to run anything to see what it does.** `logs/` holds one
plain-text file per command — 43 of them — captured from real runs, each with a
header saying what produced it and what it shows.

Grouped by exercise, and inside each one split into **`unsafe/`** and
**`safe/`** so the running order is obvious from the folder listing:

```bash
cat ex1-the-door/logs/unsafe/2-suite-5of8-and-4x-the-bill.txt
cat ex1-the-door/logs/safe/2-suite-8of8-quarter-the-bill.txt
```

`unsafe/N` and `safe/N` are the same scenario with and without the guardrail —
read as a pair and the lesson needs no narration.

Teach from the pairs and you make no live API calls in front of a room, spend
nothing per demo, and a student with a broken environment still follows the
whole session.

**Every log is also in the folder it came from** — `ex1-the-door/logs/unsafe/`,
`ex2-the-hands/logs/safe/`, … each with its own index — so you find it without
leaving the folder you are already in. Browse them all:
**[`logs/README.md`](logs/README.md)**.

They are pre-recorded, so you can read the whole session before you run a
single thing. Your own runs will differ slightly — model latency varies, and so
do the exact token counts.

**Failures print their prompt and their reply.** A `[FAIL]` line tells you
something broke; it does not tell you whether the model misbehaved, the fence
was malformed, or your expectation was wrong. So every failure is followed by
the system prompt, the user message *after the door and with any fence applied*,
the tool steps, and the raw reply. Add `--show-prompts` to any exercise to get
that for passing cases too.

---

## The one habit this module is really teaching

Every exercise has two test modes, and the difference between them matters
more than any single guardrail:

```powershell
python desk_starter.py --unit     # your guards alone. Free, instant, offline.
python desk_starter.py            # the whole system. Costs money, needs the network.
```

**Start with `--unit`, always.** The end-to-end suite tells you the system
behaved; the unit tests tell you *your code* is the reason. Those are different
claims, and you will watch the difference bite in Exercise 1: several cases
pass before you have written a single guardrail, purely because the model
happened to be careful. You did not earn those passes and you cannot renew
them.

---

## The four-hour shape

| time | what |
|---|---|
| 0:00 – 0:15 | Why a prompt is not a control · the four places a guardrail lives · setup check |
| 0:15 – 0:30 | **Warm-up** · three defences, one attack (`00-warm-up/`) |
| 0:30 – 1:05 | **Part 1** · the door and the mouth (`ex1-the-door/`) |
| 1:05 – 1:45 | **Part 2** · the hands — least privilege, allow-list, gate (`ex2-the-hands/`) |
| 1:45 – 1:50 | stretch |
| 1:50 – 2:20 | **Part 3** · the meter — routing, caching, budgets (`ex3-the-meter/`) |
| 2:20 – 2:35 | **Part 4** · the secret door — a demo you drive (`ex4-the-secret-door/`) |
| 2:35 – 2:45 | break |
| 2:45 – 3:45 | **Live homework** · the Expense Desk, on your own (`live-homework/`) |
| 3:45 – 3:55 | Solution walkthrough · the industry cases that made these rules |
| 3:55 – 4:00 | The mini-project |

> **Where the 15 minutes for Part 4 came from**, since the day was already
> full: 5 from the opening, 5 from Part 3, 5 from the walkthrough. Part 4 has
> no TODOs — you drive it from the front and the file explains itself — so 15
> minutes is honest. If you are running late, it is also the one part that
> survives being cut to 8: run it, show `forgot_password` and `--audit`, and
> point at the README for the rest.

---

## When something breaks

| symptom | cause | fix |
|---|---|---|
| `OPENROUTER_API_KEY not found` | no `.env`, or not in the repo root | same `.env` as Module 1, at the repo root |
| `ModuleNotFoundError: setup_env` | you ran a file from the wrong folder | `cd` into the exercise folder first — every file adds `../shared` to the path |
| the strong model 404s | `MODEL_STRONG` is not available on your key | set `MODEL_STRONG` in `.env` to any model you can reach, and add its price to `shared/meter.py` |
| a case fails that passed last run | the model is not deterministic, even at temperature 0 | if it is a *verdict* that moved, the test is asserting a path instead of an outcome — see `cases.py` on `poisoned_note` |
| `--unit` passes but the suite fails | your guard is fine; the system around it is not | read the ledger, not the reply. The reply is a story; the ledger is a receipt |
| the suite passes but you wrote no guardrails | the model was careful this time | exactly the trap. `--unit` is the test that cannot be fooled this way |
| `BudgetExceeded` | the spend ceiling tripped | that is the guardrail working. Raise `--budget` deliberately, or ask why the run is so expensive |
| a run costs more than you expected | an unfenced 48k-char message, or a retry loop | read the cost card. `oversized` costs ~4x the whole rest of the suite |
| Exercise 4 blocks something innocent | your rule is matching prose, not a shape | that is the lesson — see `forgot_password`. Add the shape to `NOT_SECRET_SHAPES` or tighten the pattern |
| Exercise 4 asks for a key | it never should — it makes no LLM calls | you are running a different file; `secret_door.py` needs no network |

---

## What we are *not* doing today

We are **not** installing a guardrail framework. They are real and several are
good. But a guardrail you did not write is a guardrail you cannot reason about
during an incident, and every one of them is ultimately the four checks you
are about to write by hand.

We are also **not** teaching you to write a blocklist of dangerous phrases.
You will measure why in the warm-up: the attacks that a blocklist catches are
the ones that fail anyway.
