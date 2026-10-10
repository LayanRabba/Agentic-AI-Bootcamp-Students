# Exercise 4 — The Secret Door

**What the *user* must not be allowed to send us.** · ~15 min · a demo, not a build

> **No TODOs in this one.** `secret_door.py` is written to be read and run —
> the explanation is in the comments, next to the code that does the work.
> It makes **no LLM calls**, needs no key, and costs nothing. That is the point.

```
   the user pastes                       [ THE SECRET DOOR ]        the model
   a stack trace, a .env,   ─────────▶   policy.SECRET_RULES   ─X─▶  never sees it
   a curl command                         block · redact · allow
```

---

## The question this asks

Exercise 1's door asked *"is this even a message?"* — empty, too long, full of
prompt structure. This asks something different of the same input:

> **Is the user about to hand us something they will regret?**

A colleague pastes a stack trace with a connection string in it. A developer
pastes the curl command they were debugging, `Authorization` header and all.
Someone pastes their whole `.env` because *"the agent can tell me what's
wrong"*. Your agent dutifully forwards every byte to a third-party API.

## Why this check cannot live anywhere else

Once a secret is in the prompt, it is:

- in the provider's request logs
- in your tracing tool
- in your eval fixtures, if that request became a test case
- in the scrollback of whoever was pair-programming
- possibly in a training corpus, depending on your plan

**You cannot un-send a prompt.** No output filter helps, because the damage was
done on the way *in*. This is the only guardrail in the module that must run
**before the first API call** — which is also why it is the only exercise that
needs no API key.

> **Real-world shape.** Samsung restricted internal use of a public assistant
> in 2023 after staff pasted source code into it. The restriction was the
> second-best fix. The best fix is a door.

---

## Run it

```powershell
cd ..\ex4-the-secret-door
python secret_door.py                      # 14 messages through the door
python secret_door.py --policy             # the rule table, as security reads it
python secret_door.py --audit              # what gets logged — and what must not
python secret_door.py --case dotenv_paste  # one case, in full
python secret_door.py --live               # paste your own, see the verdict
```

✅ **Checkpoint:** `0 failure(s).` — 7 blocked, 2 redacted, 5 allowed.

---

## The three rows to stop on

**`forgot_password` → ALLOWED.** *"I forgot my password and the reset email
never arrived."* It contains the word **password**. It is also one of the most
common support messages in existence. A prose keyword rule blocks this
customer, and then your guardrail gets switched off — after which you have no
guardrail at all.

**`dotenv_paste` → BLOCKED**, and look at *why*. `MODEL=` and `DEBUG=` are
ignored. `CLIENT_SECRET=` is not. The rule matches a **machine-written name**
followed by a real value.

> **The rule: match the shape of the secret, or the shape of a machine-written
> name. Never the shape of a sentence.**
>
> `API_KEY=hunter2` is an identifier and a value. Match it.
> `I forgot my password` is a human being. Leave them alone.

**`git_sha` → ALLOWED**, despite being 40 random-looking characters. That is
`NOT_SECRET_SHAPES` earning its keep: the moment you flag *"looks random"* you
owe the world an exemption list — UUIDs, content hashes, tracking numbers, git
SHAs. Leave it out and you block every customer who quotes a tracking number.

---

## How the policy rejects it

The eight rules live in **`shared/policy.py`**, as data:

```python
{
    "name": "aws_access_key_id",
    "pattern": r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b",
    "action": "block",
    "policy": "Passwords and Credentials Policy",
    "rotate": True,
    "why": "AWS key ids have a fixed shape, so this is a high-confidence match",
}
```

`secret_door.py` is the only code that reads them. **To add a rule you add a
row** — no new branch, no function to change, a one-line diff in a file whose
whole job is to be audited. That is the difference between a policy and a pile
of `if` statements, and it is why security review can read it without reading
your Python.

### `block` vs `redact`, and why it is not always `block`

| | action | reason |
|---|---|---|
| a live credential | **block** | there is no safe way to continue, and the user must be told to rotate |
| the customer's card | **redact** | they still deserve an answer; a blocked reply is a support ticket |

Getting this wrong in either direction is the whole craft. Block everything and
the tool gets switched off. Redact everything and you have quietly forwarded a
production key to a third party.

### Two passes, and the order matters

1. **Named rules first** — specific, high confidence, and they can tell the user
   *what* was found, which is what they need in order to rotate it.
2. **The entropy backstop last** — Shannon entropy over long tokens, skipping
   `NOT_SECRET_SHAPES`. It catches formats nobody wrote a rule for, and it can
   only ever say *"this looks random"*.

Run the specific checks first and your message is *"that is an AWS key, go
rotate it"*. Run entropy first and it is *"something looked odd"*, which helps
nobody. The code enforces this with an explicit **specificity beats span
length** tie-break — and the comment explains the bug that taught us to add it.

---

## 🧪 The experiment that matters: `--audit`

```powershell
python secret_door.py --audit
```

```
provider_api_key             block   at=66    len=53   fp=70a5b4b5890b  [Passwords and Credentials Policy]
secret_assignment            block   at=105   len=27   fp=188dab255dcb  [Passwords and Credentials Policy]
iban                         redact  at=17    len=24   fp=ad3d9d6a4876  [Data Classification]
```

**Now read it again looking for what is not there.** No key. No password. No
card number. Not one character of any value. You get the rule, the offset, the
length, and a one-way fingerprint — enough to tell *"one person pasted the same
key three times"* from *"three people pasted three different keys"*, and
useless to anyone who steals the log.

> This is the easiest mistake to make and the hardest to notice: **a guardrail
> that blocks the secret and then writes it to your incident log has moved the
> leak, not stopped it.** Your logs are usually *less* protected than your
> prompts — more people can read them, they are retained longer, and they get
> shipped to a third-party observability vendor.

---

## 🔍 Look closer

- **The sentence everyone forgets.** When the door blocks a credential it tells
  the user to **rotate it anyway**. Blocking the send does not undo anything:
  the secret was on their clipboard, in their shell history, maybe in a
  screenshot. It is already burned. Say so.
- **Why the connection-string rule captures a group.** `postgres://user:pw@host`
  — the rule reports and redacts *group 1*, the password, not the whole URL, so
  the host is still visible to whoever is debugging.
- **Redaction is by span, not `str.replace()`.** An early version replaced
  matched strings and the card rule ate the digits inside an IBAN, after which
  the IBAN rule silently found nothing to replace. Offsets, right to left.
- **`--live`** reads from stdin and never leaves your machine. Paste something
  real-looking from your own notes and see what happens. (Then rotate it.)
