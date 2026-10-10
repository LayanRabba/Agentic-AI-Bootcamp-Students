# Exercise 3 — The Meter

**The fourth guardrail: what the agent may *consume*.** · ~30 min · built together

The door bounds what comes **in**. The hands bound what the agent may **do**.
The mouth bounds what goes **out**. The meter bounds what it may **spend** —
and that is a safety property, not an accounting one.

> **Read this before you decide this exercise is about money.**
>
> An agent that loops until your credit dies is an availability failure, and
> availability is a security property. It is also cheap to trigger: Exercise 1's
> `oversized` case was a 48,000-character message that **quadrupled the bill**.
> That is an attack whose payload is *length* rather than text, and the door
> stopped it for the same reason the cap stops a 4,999 refund — a bound in code.
>
> Two of the three techniques below are **fail-closed controls wearing cost
> clothing**, and the finale is pure safety with no cost content at all.

| | what |
|---|---|
| **Phase 1** | baseline — every request on the capable model |
| **TODO 1** | **routing** — *which model reads the untrusted content?* Then measure. |
| **TODO 2** | **caching** — and the two things you must never cache |
| **TODO 3** | **a spend ceiling** that trips *before* the call — fail closed, on cost |
| **finale** | **the risk meter** — the sharpest safety finding in the module |

### Where this sits in the incident list

The handout's §5 has two rows that belong to this exercise, and neither is a
cost story:

- **Bing / "Sydney", 2023.** Users extracted the internal prompt; long
  conversations drifted badly. The most effective early mitigation was **not a
  better prompt** — it was a **cap on turns per conversation**. The single most
  effective control in that whole list was a budget.
- **Knight Capital, 2012.** A deployment error in automated trading lost around
  $440M in about 45 minutes. Automation with no kill switch.
  **A spend ceiling is a kill switch.**

> Your first guardrail was M1's step cap. This is the same idea, denominated in
> money.

### Being straight about the rest

Routing and caching *are* cost techniques. They are in a safety module for two
reasons, and it is worth saying both out loud:

1. **Routing is a security decision in disguise.** Choosing a cheap model for
   "easy" requests means choosing which model reads your most **untrusted**
   content — and the finale measures what that choice actually costs you.
2. **"Cheaper but wrong is not cheaper" is the same discipline as "a missing
   check must never look like a passed check."** Both are about refusing to let
   an optimisation quietly downgrade a guarantee.

---

## Step 0 — run it and read the table

```powershell
cd ..\ex3-the-meter
python meter_starter.py
```

It works, and it saves you nothing — and the before/after table says so out
loud:

```
  [--] No regression, but no saving either. The change bought you nothing;
       revert it rather than carry the extra code.
```

A measurement that is allowed to say *"you wasted your time"* is the only kind
worth having.

## TODO 1 — route by difficulty  (`pick_model`)

Decide in code — length, how many orders are involved, a word list. **Do not
ask a model which model to use**: a router that costs an LLM call has spent the
money it was trying to save, on every single request, and added its latency to
all of them.

> **Keep one eye on which cases get routed where.** Print the table the
> solution prints and look at `poisoned_note` — the case carrying the injection.
> Your router just decided which model reads an attacker's text. Hold that
> thought until the finale.

✅ **Checkpoint:** cost down roughly **45–50%**, p95 down, success unchanged at
100%. One of our runs:

```
  [OK] Cheaper AND no regression: $0.00310 -> $0.00162 (-48%), success held at 100%.
```

Your exact numbers will differ — model latency varies, and so does how many
tool steps each case takes. The *direction* is the checkpoint, and the
"no regression" line is the part that matters.

Now read the honest version of that result: the capable model cost **3x** and
bought nothing the suite could detect. If you had shipped the baseline out of
caution, you would have paid that 3x forever and called it diligence.

> **There is a bug hiding in this function, and it is in the comments.** The
> router used to count order ids with a plain regex over the whole message —
> and a card number is four groups of four digits. So every customer who
> mentioned a card looked like a four-order question and got the expensive
> model. Nothing failed. No test went red. It just quietly cost more.
> **Your router's bugs do not crash; they invoice.**

## TODO 2 — caching  (`cache_get`)

Exact match, with a TTL — and **two exclusions that are safety rules, not
performance ones**.

- **Never cache a turn that moved money or opened a gate.** A cached refund is
  a *second* refund; worse, it is an action no human approved. The solution's
  condition is `if not refused and not gated`, and that is a guardrail.
- **Exact**, not similarity. A semantic cache serves the answer for *"where is
  order 1187"* to someone asking about **1188** — which is not a staleness bug,
  it is **wrong-record disclosure**, the same bug class as Exercise 1's PII
  redaction.
- **A TTL**, because an order's status changes. A cache with no expiry is a
  promise that the world holds still.

✅ **Checkpoint:** second pass roughly **$0.0016 → $0.0005** (about −70%), p50
to 0.0s, with 5 of 8 served from cache.

Look at which three were **not** cached: the two that opened a gate, and
`oversized` (which never calls a model). A cached refund is a second refund —
or worse, a refund nobody gated.

## TODO 3 — the spend ceiling

Check `meter.dollars()` **before** the call. Checking afterwards is an apology,
not a control — exactly the argument the door makes in Exercise 1 and the gate
makes in Exercise 2.

```powershell
python meter_starter.py --budget 0.002
```

Every case after the ceiling trips comes back `CRASH / BudgetExceeded`, which
is the correct outcome. A run that stops and says *"I ran out of budget"* is a
run you can reason about. A run that quietly spends 400x what you expected is
the invoice you find on Monday.

`BudgetExceeded` is **fail closed**: the run stops and says so rather than
continuing on a guess. Same shape as a blocked input and a denied gate.

---

## The finale — the risk meter  ·  *the point of the exercise*

No code from you, and **no cost content at all**. The same poisoned note,
unfenced, on both models, counting how often each one has to be **saved by the
cap** — which is to say: this is a safety measurement that happens to need the
routing machinery you just built.

```powershell
python meter_solution.py --risk-only
```

**What we measured while building this exercise**, on these two models, within
the same hour, changing nothing but the list of tools on offer:

| tools exposed | `gpt-4o-mini` | `gpt-4.1-mini` |
|---|---|---|
| lookup + refund + email | 0 of 6 | **6 of 6** |
| lookup + refund | **3 of 3** | 0 of 3 |

The two models **swapped places**. The only thing that changed was a tuple.

So the finding is not *"the expensive model is more dangerous"*. It is worse
than that, and more useful:

1. **You cannot rank models by safety from the outside.** Not by price — the
   pricier model is 2.7x the cost and that bought nothing in either row — and
   not by a benchmark, which was not run on your tools, your prompt or your
   attacker.
2. **A config change is a safety change.** Adding one tool reversed the result.
   Exposing a tool, editing the prompt, bumping a version, raising a cap:
   every one of those invalidates your last measurement. Which is why the
   suite has to be cheap enough to run on every commit — and why you keep the
   `--unit` tests from Exercises 1 and 2.
3. **The code held in every cell of that table.** In all four cells, every
   forbidden call was refused. The cap did not care which model, which tool
   list, or which run.

> That is the difference between a **control** and a **tendency**.
> If anyone tells you an agent is safe because it runs on a good model, show
> them this table.

### This is where the cost thread and the safety thread meet

Conclusion 2 — *a config change is a safety change* — is the reason the suite
has to be **cheap enough to run on every commit**. Exposing a tool, editing the
prompt, bumping a model version or raising a cap all invalidate your last
safety measurement. A suite that costs real money and ten minutes gets run at
release time; a suite that costs nothing gets run every time you touch the
config.

**So the cost work is what makes the safety work affordable enough to repeat.**
That is the honest reason these two subjects share an exercise.

## ⚠️ One thing this exercise does *not* demonstrate

`shared/scorecard.py` can print **`[X] CHEAPER, BUT WRONG — do not ship this`**
when a cost cut breaks a case that used to pass. On this suite it never fires:
`--greedy` puts everything on the cheap model and success still holds at 100%,
because `gpt-4o-mini` handles these cases fine.

That is a real result and we did not manufacture a regression to hide it. But
it means the "cheaper but wrong" lesson here is **told, not shown**. If you want
it demonstrated live, add a case your cheap model actually fails and put it in
the suite — that is a good mini-project extension, and finding one honestly
takes measurement rather than assumption.

## 🔍 Look closer

- `shared/meter.py` counts **per model**, because with routing a single price
  makes "cheaper" a feeling rather than a number.
- It also counts **retries** separately. A run that "worked" after three
  retries cost four times the happy path. Retries are the cost nobody budgets.
- `p50` and `p95` are both printed. p50 is what you feel while developing; p95
  is what your users complain about.
