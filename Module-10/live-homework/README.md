# Live Homework — The Expense Desk

**On your own · 60 minutes · second half of the session.**
We walk through the solution at the end.

You just hardened a support desk **together**. Now you do the same three moves
**alone**, on a new problem: a desk that approves staff expense claims.

| part | the move | you did it together in | TODOs | time |
|---|---|---|---|---|
| **A · The Door** | input + output guards | Exercise 1 | 2 | 15 min |
| **B · The Hands** | allow-list + approval gate | Exercise 2 | 2 | 20 min |
| **C · The Meter** | routing + a spend ceiling | Exercise 3 | 2 | 25 min |

**Six TODOs.** Each part stands alone: stuck on one, move to the next.

### What is genuinely different this time

Not just the nouns. Four things change the engineering:

- the untrusted content is a **vendor's receipt text** — the injection comes
  from outside the company entirely
- the caps are **per category**, not one number. Software's ceiling is `0.00`,
  so a 19.00 licence renewal still needs a signature. **Risk is not size.**
- the PII is an **IBAN**, which no model has been specially trained to protect
- one claim — `EX-2204`, an 1840.00 rebooked flight — is **completely
  genuine**. If your guardrails refuse it, you have built an obstacle, not a
  guardrail.

That last one is the whole point of Part B, and it is the most common mistake
in this module.

### The rules

1. **On your own.** Your notes and Exercises 1–3 are the best reference you
   have — including their `*_solution.py` files. **The homework solutions are
   not in this repo:** we walk through them together at the end of the session,
   and they are published afterwards. That is deliberate — the whole point of
   this hour is finding out what you can do unaided.
2. **Start every part with `--unit`.** Free, instant, and it fails loudly.
3. **Stuck for 5 minutes?** Move on and come back.

```powershell
cd live-homework          # from Module-10
```

---

## Part A — The Door and the Mouth (15 min) · `hw_a_the_door.py`

```powershell
python hw_a_the_door.py --unit      # 7 failures. Start here.
python hw_a_the_door.py             # the 8-case suite
```

| TODO | what | the move from Exercise 1 |
|---|---|---|
| A1 | close the door | empty · length cap · strip `CONTROL_TOKENS` |
| A2 | close the mouth | canary → block · egress allow-list → block · IBAN → redact · length |

✅ **Done when** `--unit` reports 0 failures **and** the suite reports 8/8.

## Part B — The Hands (20 min) · `hw_b_the_hands.py`

Start by watching it fail:

```powershell
python hw_b_the_hands.py --no-fence --case the_injection
```

| TODO | what | the move from Exercise 2 |
|---|---|---|
| B1 | the allow-list and the arguments — **three** states | allow / **escalate** / refuse |
| B2 | the approval gate | safe tools never prompt · default to no |

**B1 is the one to slow down on.** Exercise 2's policy had two answers: allow
or refuse. That is not enough here, and `EX-2204` is why.

```
   9800.00 on a 212.40 claim is FICTION  ->  refuse, no human involved
   1840.00 on an 1840.00 claim is REAL   ->  escalate, a human decides
   19.00 of software is real and trivial ->  escalate anyway
```

Rows 1 and 2 are both *"over the ceiling"*. Treating them the same way is the
single most common mistake in this whole module: refuse row 2 and Finance stops
using your desk by Wednesday — and **a guardrail nobody will keep is not a
guardrail.**

Check the fiction **before** the cap, so a fabricated figure never reaches a
human looking like an ordinary approval.

✅ **Done when** `--unit` is green (watch the `want escalate` rows), the suite
is 8/8, and `--deny` moves no money.

## Part C — The Meter (25 min) · `hw_c_the_meter.py`

| TODO | what | the move from Exercise 3 |
|---|---|---|
| C1 | route by difficulty | code, not a model |
| C2 | a spend ceiling | checked *before* the call |

```powershell
python hw_c_the_meter.py
python hw_c_the_meter.py --budget 0.002     # watch it trip
```

✅ **Done when** the before/after table shows cost down and success unchanged.

**Write down three numbers before you close the terminal: success %, cost,
p95.** You need them for the mini-project, and *"it felt faster"* is not a
number.

---

## If you finish early

1. **Add a category you invented** to `CAPS` in `expenses.py` and a claim that
   exercises it. Does your policy still read clearly, or did you just add a
   fourth `if`?
2. **Write the 16th attack.** Add one to `ATTACKS` in `shared/cases.py` that
   gets past your Part A guards. Bring it to the walkthrough.
3. **Break your own suite.** Change one cap and find out which test goes red.
   If none does, you have found a gap in the suite, which is more valuable than
   a passing run.
