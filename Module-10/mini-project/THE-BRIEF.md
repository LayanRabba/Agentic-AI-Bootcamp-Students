# Phase 5 Mini-Project — Harden Your Own Agent

**After Module 10. Budget 3–4 hours. Work alone.**
**Due before Friday's session.** Graded — mini-projects are 35% of your final mark.

---

## The short version

1. **Take an agent you already built** — Module 5's MCP agent, Module 6's
   memory agent, Module 7's network, or your own.
2. **Give it hands that matter**: at least one tool that spends money, deletes
   something, or reaches an outsider.
3. **Harden it** at all four places: the door, the hands, the mouth, the meter.
4. **Red-team it** — 10 attacks, and report the block rate honestly.
5. **Measure it** — before and after, with the scorecard.
6. **Submit a GitHub issue.**

No report, no slides.

> **Harden something that already works.** Do not build a new agent. The point
> of this week is that hardening is a distinct skill applied to working
> software — and that it changes the software less than you expect and the
> tests more.

---

## What you are building

```
   input ──▶ [ THE DOOR ]  length · structure stripped · never a keyword blocklist
                  │
                  ▼
             your agent ◀── [ THE FENCE ] everything it did not write
                  │
                  ▼
           wants a tool ──▶ [ EXPOSED?  ] least privilege
                            [ ALLOWED?  ] name + arguments, in code
                            [ APPROVED? ] a human, for risky things only
                  │
                  ▼
             [ THE MOUTH ] canary · egress allow-list · PII · format
                  │
                  ▼
             [ THE METER ] routing · caching · a spend ceiling
```

### Must have

| # | requirement | where it lives in the exercises |
|---|---|---|
| 1 | **A door.** Length cap and structure stripping, and **zero false positives** on five innocent inputs you write yourself. | `ex1` TODO 1 + `--tricky` |
| 1b | **A secret door.** Two rules in your own policy table that reject a credential the *user* pastes — one matched by shape, one by a machine-written name — plus one innocent message containing a credential word that must pass. Audit the finding **without logging the value**. | `ex4` + `shared/policy.py` |
| 2 | **A fence** around every piece of content your agent did not write — tool output, retrieved documents, another agent's reply. | `ex1` TODO 2 |
| 3 | **A mouth.** A canary in your system prompt that never escapes, an **egress allow-list**, and PII redaction appropriate to your domain. | `ex1` TODO 3 |
| 4 | **Least privilege.** Name one capability you removed, and say what you lost. | `ex2` TODO 1 |
| 5 | **An allow-list with argument validation**, including one check where **code owns a value the model is not allowed to choose**. | `ex2` TODO 2 |
| 6 | **An approval gate** on risky tools only — and a sentence on which tools you deliberately did **not** gate, and why. | `ex2` TODO 3 |
| 7 | **Three-state policy**: allow / escalate / refuse, with one case that is legitimate-but-large and must reach a human rather than be refused. | `live-homework` B1 |
| 8 | **A meter.** A spend ceiling that trips, plus one measured optimisation (routing or caching). | `ex3` |
| 9 | **A scorecard** of at least 6 cases, with `--unit` tests for every guard. | `shared/scorecard.py` |

### Bonus (your capstone will want these)

- A **second** canary that you *do* let leak, to prove the first one works.
- An **entropy backstop** on your secret door, with the exemption list it
  needs. Show it catching a format you wrote no rule for, and show it *not*
  blocking a UUID.
- Your agent reads from **MCP** (Module 5) — then the fence is doing real work.
- A **classmate** red-teams your desk and you red-team theirs.

---

## Step 1 — Pick it and point it (20 min)

Open **[SCENARIOS.md](SCENARIOS.md)** for ten domains, each with its tools, its
risky action, its injection vector and its "legitimate but awkward" case.

Your own idea is welcome if it passes three checks:

- there is an action with **real consequences** — money, deletion, or an
  outsider seeing something,
- some content reaching the agent is written by **someone you do not trust**,
- there is a value the model should **not** be allowed to choose.

If your agent has no irreversible action, you have nothing to gate — add one
(a fake `send_invoice` is fine) or pick a different scenario.

## Step 2 — Copy the plumbing (15 min)

Work **inside** the module folder so the `shared/` imports keep working:

```powershell
cd Module-10
mkdir my-desk
copy ex2-the-hands\hands_solution.py  my-desk\desk.py
copy shared\cases.py                  my-desk\my_cases.py
```

Run it before changing anything. If the copy works, every problem from now on
is yours, not the plumbing's.

## Step 3 — Write the suite FIRST (30 min)

Before you write a single guardrail, write the cases — including the attacks
you expect to fail. This is the one order that matters, for a reason you saw in
Exercise 1: several cases pass before you write any guardrails, because the
model happens to be careful. If you write the guard first you will not know
which passes you earned.

For each case, record what the system can do and what you **fear**:

```python
Case("the_injection", "...", ("ANSWER", "GATE", "REFUSE"),
     must_not_contain=("9800", "attacker.example"))
```

> **Assert the outcome you fear, never the path you expect.** If three verdicts
> are all safe, accept all three. A test that pins the path fails when the
> fence works and the policy never fires — and a flaky test gets re-run until
> it is green, then ignored forever.

## Step 4 — Harden it (1h 30m)

Door, fence, hands, mouth, meter. `--unit` after every change.

## Step 5 — Red-team it (45 min)

Ten attacks. Start from `ATTACKS` in `shared/cases.py` and adapt them — then
write at least **three of your own** aimed at your domain.

Report a table, and report it honestly:

| # | attack | technique | blocked by | result |
|---|---|---|---|---|
| 1 | … | format conversion | the mouth (canary) | blocked |
| 2 | … | injection via tool output | the cap | blocked |
| 3 | … | … | — | **GOT THROUGH** |

**An attack that got through is worth more marks than ten that did not**, if
you explain what layer should have caught it and what you would add. A report
with a 10/10 block rate and no analysis reads like a report that stopped
looking.

## Step 6 — Answer one question honestly (15 min)

In your README, one paragraph:

> **Which of your guardrails would survive a model change, and which are you
> just lucky about?**

Go through them one at a time. A length cap survives. A canary check survives.
"The model refused when I asked it nicely" does not. Use the warm-up's two
zeros as your yardstick.

---

## Submit

Your folder, zipped (**without `.env`**), attached to a new issue using the
**"M10 Mini-Project — The Hardened Desk"** template.

```
my-desk/
  README.md       how to run it · the red-team table · the honesty paragraph
  desk.py         your hardened agent
  my_cases.py     your suite and your attacks
  evidence/       unit.txt · suite_before.txt · suite_after.txt
                  redteam.txt · budget_trip.txt · deny.txt
```

---

## How it's graded

| | weight | you pass the criterion when |
|---|---|---|
| **Four places covered** | 25% | door (including a secret rule), hands, mouth and meter all have a check, and each one is demonstrated |
| **Code owns the dangerous value** | 20% | there is a value the model cannot choose, and you show the attack dying on it |
| **It is usable** | 15% | zero false positives on your five innocent inputs, and the legitimate-but-large case **escalates** rather than being refused |
| **The red team is honest** | 20% | 10 attacks, real results, and analysis of anything that got through |
| **It is measured** | 20% | before/after scorecard, a tripped spend ceiling, and `--unit` tests for every guard |

**Pass is 4 of 5 criteria.** Opening an issue early and fixing it later beats a
polished one an hour before the deadline.

---

## If you get stuck

1. **`ModuleNotFoundError: setup_env`** → run from inside the module folder; the
   files add `../shared` to the path.
2. **Everything passes and you wrote nothing** → you are reading the end-to-end
   suite. Run `--unit`. That is the whole trap from Exercise 1.
3. **Your guardrail blocks real users** → you are matching keywords. Cap length
   and strip structure; never guess intent.
4. **The gate fires on every request** → you gated a read-only tool. Gate money
   and outsiders, nothing else.
5. **A case passes, then fails, then passes** → it is asserting a path. Accept
   every safe verdict and assert `must_not_contain` instead.
6. **Cost went up after routing** → your router is miscounting something. Print
   its decision per case, like `ex3` does.
7. **Still stuck** → post the whole terminal output, both `--unit` and the
   suite, in the class channel before Friday.
