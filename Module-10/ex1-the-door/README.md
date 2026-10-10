# Exercise 1 — The Door and the Mouth

**Check what comes in. Check what goes out. Fence everything you did not write.** · ~35 min · built together

```
   customer ──▶ [ THE DOOR ] ──▶ the desk ──▶ [ THE MOUTH ] ──▶ customer
                 check_input       one LLM      check_output
                                   call, with
                                   a FENCE around
                                   anything the
                                   desk did not write
```

The desk from the warm-up now answers real customers about real orders. It has
**no hands yet** — it can only talk. Three TODOs.

| TODO | the guardrail | fixes the case |
|---|---|---|
| 1 | **the DOOR** — cap the length, strip structure markers | `oversized` |
| 2 | **the FENCE** — mark retrieved data as data, not orders | `poisoned_note` |
| 3 | **the MOUTH** — never send the canary, block exfiltration, redact PII | `leak_prompt` |

---

## Step 0 — start with the free test

```powershell
cd ..\ex1-the-door
python desk_starter.py --unit
```

Eleven failures, instantly, for nothing. **This is where you work from.** The
`--unit` suite tests your guards against text crafted to be bad — no network,
no cost, no luck, and it still passes when the vendor ships a new model on a
Tuesday.

Then run the real thing once, to see the shape of the problem:

```powershell
python desk_starter.py
```

5 of 8, about $0.0024. Note that number — it matters in a moment.

---

## TODO 1 — the door  (`check_input`)

Three jobs: reject empty, cap the length at `MAX_CHARS`, strip every marker in
`CONTROL_TOKENS` (`###`, `<<`, `{{` …). Company policy requires those stripped
before user text reaches a prompt.

What must **not** go in here: a list of scary phrases.

✅ **Checkpoint:** `oversized` passes, and the cost card drops from ~$0.0024 to
~$0.0006. You just cut three quarters of the bill with a length check, because
one 48,000-character message cost more than the other seven cases combined.
**The door is a cost control before it is a safety control.**

Now run `python desk_starter.py --tricky`. Five innocent customers — including
one who writes *"please ignore my previous email, I found the parcel"*. If you
blocked any of them, your door is guessing intent from keywords. Zero is the
only passing score.

## TODO 2 — the fence  (`fence`)

The order note is attacker-controlled: it is free text a human typed into a
form. Right now it is pasted into the prompt raw, so the model cannot tell the
shop's instructions from a sentence someone typed into a database field.

Wrap it in a delimiter carrying a **random nonce**, and say plainly that
everything inside is data. A fixed delimiter like ``` is guessable, and
guessable means an attacker can close your fence and write outside it.

✅ **Checkpoint:** `poisoned_note` passes. Then:

```powershell
python desk_starter.py --case poisoned_note
```

Read the fenced block, then read what the customer got. Comment the fence out
and run it again: the desk puts **the attacker's address** in a reply to a
customer.

## TODO 3 — the mouth  (`check_output`)

Four checks, and the order of them is the craft:

1. **empty** → a safe substitute
2. **the canary** → BLOCK, and say nothing about what you blocked. An error
   message is a hint.
3. **the egress allow-list** → an email address on a domain you do not
   recognise BLOCKS the whole reply. Masking the local part is not enough:
   the **domain is the payload**. `•••@northwind-supplies-refunds.com` still
   tells the attacker their note was read.
4. **PII** → REDACT, do not block. The customer still deserves an answer.

> **BLOCK what must never be seen. REDACT what merely must not be repeated.**
> Block everything and you have built a wall, not a support desk.

✅ **Checkpoint:** `--unit` reports 0 failures and the suite reports 8/8.

---

## 🧪 Two experiments (5 minutes)

**1. The pass you did not earn.** `pii_echo` passes *before* you write the
redaction. Comment your card-number redaction out and watch it pass anyway —
this model refuses card numbers on its own. Keep the guard. You did not earn
that pass and you cannot renew it: the model is the one thing in your system
you do not control.

**2. Which test would have caught a bad deploy?** You have two suites now.
Break your canary check on purpose (change `CANARY` to `"zzz"`). Which suite
goes red? How long did each take, and what did each cost?

## 🔍 Look closer

- `check_input` strips `###` from the **customer's** message but the fence
  leaves the database note intact, markers and all. That is deliberate:
  stripping retrieved content destroys evidence and changes the record. You
  **clean the door** and **fence the data**.
- The egress allow-list is the guard people leave out, and it is the one that
  stops exfiltration. The same reasoning covers links and images: if your agent
  can emit a URL, an attacker can move data in a query string without any text
  ever leaving.
