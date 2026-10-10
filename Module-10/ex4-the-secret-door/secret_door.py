"""
Exercise 4 -- THE SECRET DOOR
=============================

   There are no TODOs in this file. It is meant to be READ and RUN.
   Everything it teaches is in the comments, next to the code that does it.

   python secret_door.py              # the 14 cases through the door
   python secret_door.py --policy     # the rule table, as security reads it
   python secret_door.py --case aws_keys        # one case, in full
   python secret_door.py --audit      # the audit log, and what is NOT in it
   python secret_door.py --live       # paste your own text and see the verdict

   It makes NO LLM calls at all. It costs nothing and needs no network. That
   is not a shortcut -- it is the point of the exercise.


THE PROBLEM
-----------
Exercise 1 built a door that asks "is this even a message?" -- empty, too
long, full of prompt structure. This exercise asks a different question of
the same input:

    "Is the USER about to hand us something they will regret?"

A customer, or far more often a colleague, pastes into your agent:

    · a stack trace with a connection string in it
    · a curl command they were debugging, with the Authorization header
    · the contents of a .env file, because "the agent can tell me what's wrong"
    · a private key, because the error mentioned a certificate

Your agent dutifully forwards all of it to a third-party API.


WHY THIS CHECK CANNOT LIVE ANYWHERE ELSE
----------------------------------------
Once a secret is in the prompt it is:

    in the provider's request logs
    in your tracing/observability tool
    in your eval fixtures, if that request became a test case
    in the terminal scrollback of whoever is pair-programming
    possibly in a training corpus, depending on the plan you are on

You cannot un-send a prompt. There is no output filter that helps, because
the damage was done on the way IN. So this is the one guardrail in the module
that must run *before the first API call* -- which is also why it is the only
exercise here that needs no API key.

This is the Samsung 2023 story, which the handout mentions: staff pasted
internal source into a public assistant and the company restricted the tool.
The restriction was the second-best fix. The best fix is a door.


THE TWO THINGS PEOPLE GET WRONG
-------------------------------
1.  They match on PROSE.  "block anything containing the word password" --
    and now "I forgot my password, how do I reset it?" is blocked, which is
    one of the most common support messages there is. Case `forgot_password`
    below must sail straight through.

2.  They block and then LOG THE SECRET.  The audit record says what was
    found, where, and a fingerprint -- never the value. A guardrail that
    writes the credential into your incident log has moved the leak, not
    stopped it. Run --audit and read what is actually recorded.

The rule that resolves (1):

    MATCH THE SHAPE OF THE SECRET, OR THE SHAPE OF A MACHINE-WRITTEN NAME.
    NEVER THE SHAPE OF A SENTENCE.

    `API_KEY=hunter2`      is an identifier and a value. Match it.
    `I forgot my password` is a human being. Leave them alone.
"""

from __future__ import annotations

import hashlib
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))

import policy  # noqa: E402  the rule table lives there, as config
from meter import banner, indent, rule as hrule  # noqa: E402

# Pre-compile once. The rules are data; this is the only code that reads them.
_RULES = [(r, re.compile(r["pattern"])) for r in policy.SECRET_RULES]
_BENIGN = [(n, re.compile(p)) for n, p in policy.NOT_SECRET_SHAPES]
# '=' is allowed only as trailing base64 padding. Include it in the middle and
# `CLIENT_SECRET=Ex4mple-...` becomes ONE 41-character token, which then
# outranks the rule that could actually name it.
_TOKEN = re.compile(r"[A-Za-z0-9+/_\-]{%d,}={0,2}" % policy.ENTROPY_MIN_LENGTH)

# The backstop, shaped like a policy row so the overlap resolver in
# secret_door() can treat it exactly like one.
_ENTROPY_SPEC = {
    "name": "high_entropy_unknown",
    "action": "block",
    "policy": "Passwords and Credentials Policy",
    "rotate": True,
    "why": "no named rule matched, but no human typed this either",
}


# ─── the audit record ────────────────────────────────────────────────────────
@dataclass
class Finding:
    """What we tell the log. Note what is NOT in here: the secret."""

    rule: str
    action: str
    policy_name: str
    rotate: bool
    at: int                  # character offset, so an engineer can find it
    length: int              # how long the matched value was
    fingerprint: str         # first 12 hex of a digest -- enough to correlate
    #                          two reports as "the same secret", useless to an
    #                          attacker who reads the log

    def line(self) -> str:
        return (f"{self.rule:<28} {self.action:<7} at={self.at:<5} "
                f"len={self.length:<4} fp={self.fingerprint}  [{self.policy_name}]")


@dataclass
class Verdict:
    allowed: bool
    text: str                              # what the model would receive
    findings: list[Finding] = field(default_factory=list)
    message: str = ""                      # what the USER is told

    @property
    def action(self) -> str:
        if not self.allowed:
            return "BLOCK"
        return "REDACT" if self.findings else "ALLOW"


AUDIT_LOG: list[Finding] = []


def fingerprint(value: str) -> str:
    """A stable, one-way label for a value we refuse to write down.

    Two pastes of the same credential produce the same fingerprint, so you can
    tell "one person pasted it twice" from "eleven people pasted eleven
    different things" -- without the log holding any of them.
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


# ─── the entropy backstop ────────────────────────────────────────────────────
def shannon_entropy(s: str) -> float:
    """Bits per character. High means "no human wrote this"."""
    if not s:
        return 0.0
    counts = {c: s.count(c) for c in set(s)}
    n = len(s)
    return -sum((k / n) * math.log2(k / n) for k in counts.values())


def benign_shape(token: str) -> str | None:
    """Is this long random-looking thing a known, harmless shape?"""
    for name, pat in _BENIGN:
        if pat.fullmatch(token):
            return name
    return None


# ─── THE DOOR ────────────────────────────────────────────────────────────────
def secret_door(text: str) -> Verdict:
    """Enforce policy.SECRET_RULES against text the USER supplied.

    Order matters, and it is the reverse of what feels natural:

      1. named rules first   -- high confidence, specific, they tell you WHAT
                                was found, which is what the user needs to
                                know in order to rotate it
      2. entropy last        -- low confidence, catches the formats nobody
                                wrote a rule for, and can only ever say
                                "this looks random"

    Run the specific checks first and your message to the user is
    "that is an AWS key, go rotate it". Run entropy first and it is
    "something looked odd", which helps nobody.
    """
    # ---- 1 · gather every candidate, with its span -------------------------
    # We collect (start, end, spec, value) first and decide afterwards. Two
    # reasons, and the second one is a bug we actually hit:
    #
    #   a. RULES OVERLAP. The card-number pattern matches the digits inside an
    #      IBAN. Report both and the audit log says "payment_card" for what is
    #      plainly an IBAN -- a misleading log is worse than a terse one.
    #
    #   b. str.replace() IS POSITION-BLIND. Redact the card digits first and
    #      the IBAN rule then has nothing left to find, so it silently does
    #      nothing. We therefore redact BY SPAN, right to left, so every
    #      offset stays valid as we go.
    candidates = []
    for spec, pat in _RULES:
        for m in pat.finditer(text):
            # If the rule captured a group, the GROUP is the secret (the
            # password inside a connection string, the value after `=`).
            # Otherwise the whole match is.
            if m.groups():
                value, lo, hi = m.group(1), m.start(1), m.end(1)
            else:
                value, lo, hi = m.group(0), m.start(0), m.end(0)
            candidates.append((lo, hi, spec, value))

    # ---- 2 · the entropy backstop ------------------------------------------
    # Only for tokens that are not a known-benign shape. Low confidence, so it
    # runs last and can only ever say "this looks random".
    for m in _TOKEN.finditer(text):
        token = m.group(0)
        if benign_shape(token):
            continue
        if shannon_entropy(token) >= policy.ENTROPY_THRESHOLD:
            candidates.append((m.start(), m.end(), _ENTROPY_SPEC, token))

    # ---- 3 · resolve overlaps: SPECIFICITY first, then length --------------
    # Two tie-breaks, in this order, and the order is a bug we hit:
    #
    #   a. A NAMED RULE ALWAYS BEATS THE BACKSTOP. The entropy check can only
    #      ever say "this looks random". A named rule can say "that is an AWS
    #      key id, go rotate it". If you sort by span length alone, the vague
    #      one wins whenever its match happens to be longer -- and your user
    #      gets told "something looked odd", which helps nobody.
    #
    #   b. Within the same specificity, the LONGER match wins: the IBAN beats
    #      the card-shaped run of digits sitting inside it, so the audit log
    #      names the thing a human would name.
    def priority(spec: dict) -> int:
        return 1 if spec is _ENTROPY_SPEC else 0

    candidates.sort(key=lambda c: (c[0], priority(c[2]), -(c[1] - c[0])))
    accepted: list[tuple[int, int, dict, str]] = []
    for lo, hi, spec, value in candidates:
        if any(lo < a_hi and hi > a_lo for a_lo, a_hi, _, _ in accepted):
            continue                       # overlaps something already taken
        accepted.append((lo, hi, spec, value))

    findings = [
        Finding(rule=spec["name"], action=spec["action"], policy_name=spec["policy"],
                rotate=spec["rotate"], at=lo, length=len(value),
                fingerprint=fingerprint(value))
        for lo, hi, spec, value in accepted
    ]
    blocked = any(f.action == "block" for f in findings)

    # ---- 4 · redact by span, right to left ---------------------------------
    redacted = text
    for lo, hi, spec, _ in sorted(accepted, key=lambda c: -c[0]):
        if spec["action"] == "redact":
            redacted = redacted[:lo] + f"[{spec['name']} removed]" + redacted[hi:]

    AUDIT_LOG.extend(findings)

    # ---- 3 · what the user is told -----------------------------------------
    if blocked:
        kinds = sorted({f.rule for f in findings if f.action == "block"})
        must_rotate = any(f.rotate for f in findings if f.action == "block")
        msg = (
            "I have not sent that message anywhere.\n"
            f"It looks like it contains: {', '.join(kinds)}.\n"
        )
        if must_rotate:
            # The sentence everyone forgets. The secret is already burned:
            # it was on their clipboard, in their scrollback, and possibly in
            # a screenshot. Blocking the send does not undo any of that.
            msg += (
                "Treat that credential as compromised and rotate it now -- it was\n"
                "on your clipboard and in your terminal history regardless of what\n"
                "I did with it. Then send me the part of the message you actually\n"
                "needed help with."
            )
        return Verdict(False, "", findings, msg)

    if findings:
        return Verdict(True, redacted, findings,
                       "I removed some personal details before processing this.")
    return Verdict(True, text, [], "")


# ─── what we throw at it ─────────────────────────────────────────────────────
# Every value below is deliberately non-functional: EXAMPLE markers, documented
# test numbers, obviously fake hosts. Never put a real credential in a fixture.
@dataclass
class Case:
    name: str
    text: str
    expect: str          # BLOCK | REDACT | ALLOW
    teaches: str


CASES = [
    # ---------- must BLOCK ---------------------------------------------------
    Case("provider_key",
         "my script stopped working, here is the config: "
         "OPENROUTER_API_KEY=sk-or-v1-EXAMPLEEXAMPLEEXAMPLEEXAMPLE0123456789abcdef",
         "BLOCK",
         "the key that pays for this very call -- the most-pasted secret there is"),
    Case("aws_keys",
         "deploy fails with AccessDenied. creds are AKIAEXAMPLEEXAMPLE99 / "
         "wJalrXUtnFEMI-K7MDENG-EXAMPLEEXAMPLEKEY",
         "BLOCK",
         "a fixed-shape key id, plus its partner caught by the entropy backstop"),
    Case("private_key",
         "cert error. my key file starts with\n"
         "-----BEGIN RSA PRIVATE KEY-----\nMIIEx4mpl3Fak3K3y...\n",
         "BLOCK",
         "a PEM header is unambiguous -- no entropy maths needed"),
    Case("connection_string",
         "the app cannot reach the db: "
         "postgres://svc_orders:Wint3r-2026-Example@db-internal.example:5432/orders",
         "BLOCK",
         "the password is INSIDE a URL -- the rule captures the group, not the whole match"),
    Case("session_token",
         "the request returns 401 with this header: Authorization: Bearer "
         "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJleGFtcGxlIn0.EXAMPLEsignatureEXAMPLE",
         "BLOCK",
         "a JWT is a logged-in user, readable without any password at all"),
    Case("dotenv_paste",
         "can you tell me what is wrong with my env file?\n"
         "MODEL=openai/gpt-4o-mini\nDB_HOST=localhost\n"
         "CLIENT_SECRET=Ex4mple-Cl1ent-S3cret-Value\nDEBUG=true",
         "BLOCK",
         "MODEL and DEBUG are fine; CLIENT_SECRET is not. A name-based rule, "
         "applied to machine-written names"),
    Case("stack_trace",
         "ValueError in payments.py line 88\n"
         '  conn = connect(host="db.example", password="Pr0d-Example-Pw!")\n'
         "  File payments.py line 91 in charge",
         "BLOCK",
         "the secret arrives as collateral -- they wanted help with the traceback"),

    # ---------- must REDACT, then carry on ----------------------------------
    Case("customer_card",
         "I was charged twice on card 4111 1111 1111 1111 for order 1187, "
         "please check",
         "REDACT",
         "the customer's own data: remove the value, answer the question"),
    Case("customer_iban",
         "please refund to GB33 BUKB 2020 1555 5555 55, order 1203 never arrived",
         "REDACT",
         "same reasoning -- blocking this would just lose you the request"),

    # ---------- must ALLOW: the false positives that matter -----------------
    Case("forgot_password",
         "I forgot my password and the reset email never arrived. "
         "Can you help me log in?",
         "ALLOW",
         "THE IMPORTANT ONE. Contains 'password'. Is a real customer. A prose "
         "keyword rule blocks this and the tool gets switched off in week two"),
    Case("password_advice",
         "Your site says my password is too weak but I am using a passphrase "
         "manager. What are the actual rules?",
         "ALLOW",
         "'password' twice, plus 'passphrase'. Still just a customer"),
    Case("tracking_number",
         "parcel 1Z999AA10123456784 has not moved in four days, order 1187",
         "ALLOW",
         "long, random-looking, completely benign -- the entropy backstop must skip it"),
    Case("git_sha",
         "the bug appeared in commit 9f1c4b7a2e5d8f3061b4c7a9e2d5f80316b4c7a9, "
         "can you tell me what changed?",
         "ALLOW",
         "40 hex characters scores high on entropy. Hence NOT_SECRET_SHAPES"),
    Case("uuid_and_hash",
         "trace id 3f2504e0-4f89-11d3-9a0c-0305e82c3301 and image "
         "sha256:" + "a" * 64 + " -- which one should I quote in the ticket?",
         "ALLOW",
         "two more legitimately-random shapes. Every entropy rule needs this list"),
]


# ─── running it ──────────────────────────────────────────────────────────────
def show_policy() -> int:
    print(banner("THE SECRET POLICY  ·  shared/policy.py, as a reviewer reads it"))
    print(" Eight rules. They are DATA, not code -- which is the point.\n")
    print(f"  {'rule':<28}{'action':<9}{'rotate?':<9}policy")
    print("  " + "-" * 86)
    for spec in policy.SECRET_RULES:
        print(f"  {spec['name']:<28}{spec['action']:<9}"
              f"{('yes' if spec['rotate'] else 'no'):<9}{spec['policy']}")
        print(f"      {spec['why']}")
    print("\n" + hrule("shapes the entropy backstop must SKIP"))
    for name, _ in policy.NOT_SECRET_SHAPES:
        print(f"   {name}")
    print(f"\n entropy: flag tokens of {policy.ENTROPY_MIN_LENGTH}+ chars scoring "
          f">= {policy.ENTROPY_THRESHOLD} bits/char")
    print("""
 TO ADD A RULE you add a row. No function changes, no new branch, no deploy of
 somebody's cleverness -- a one-line diff in a file whose whole job is to be
 audited. That is the difference between a policy and a pile of `if`
 statements, and it is why security review can actually read this.""")
    return 0


def show_audit() -> int:
    for case in CASES:
        secret_door(case.text)
    print(banner("THE AUDIT LOG  ·  and what is deliberately missing from it"))
    print(f" {len(AUDIT_LOG)} finding(s) across {len(CASES)} messages.\n")
    for f in AUDIT_LOG:
        print("  " + f.line())
    print("""
 Now read it again looking for what is NOT there.

 No key. No password. No card number. Not one character of any value that was
 found. What you get is the rule that fired, where it fired, how long the
 value was, and a one-way fingerprint -- enough to tell "the same person
 pasted the same key three times" from "three people pasted three different
 keys", and useless to anyone who steals the log.

 This is the mistake that is easiest to make and hardest to notice: a
 guardrail that blocks the secret and then writes it to your incident log has
 MOVED the leak, not stopped it. Your logs are usually less protected than
 your prompts -- more people can read them, they are retained for longer, and
 they get shipped to a third-party observability vendor.""")
    return 0


def show_case(name: str) -> int:
    case = next((c for c in CASES if c.name == name), None)
    if case is None:
        raise SystemExit(f"Unknown case. Try: {', '.join(c.name for c in CASES)}")
    print(banner(f"ONE CASE  ·  {case.name}"))
    print(f" why it is here: {case.teaches}\n")
    print(hrule("what the user typed"))
    print(indent(case.text))
    v = secret_door(case.text)
    print("\n" + hrule("what the door decided"))
    print(f"   {v.action}   (expected {case.expect})")
    if v.findings:
        print("\n" + hrule("the audit record"))
        for f in v.findings:
            print("   " + f.line())
    print("\n" + hrule("what the MODEL received"))
    print(indent(v.text if v.text else "(nothing -- no API call was made)"))
    if v.message:
        print("\n" + hrule("what the USER was told"))
        print(indent(v.message))
    return 0


def live() -> int:
    print(banner("LIVE  ·  paste something and see what the door says"))
    print(" Ctrl-D (Ctrl-Z on Windows) when you are done. Nothing leaves this machine.\n")
    text = sys.stdin.read()
    v = secret_door(text)
    print(f"\n verdict: {v.action}")
    for f in v.findings:
        print("   " + f.line())
    if v.message:
        print("\n" + indent(v.message))
    return 0


def main() -> int:
    if "--policy" in sys.argv:
        return show_policy()
    if "--audit" in sys.argv:
        return show_audit()
    if "--live" in sys.argv:
        return live()
    if "--case" in sys.argv:
        return show_case(sys.argv[sys.argv.index("--case") + 1])

    print(banner("THE SECRET DOOR  ·  what the user must not be allowed to send us"))
    print(" 14 messages. No API calls, no key, no cost -- the check runs before")
    print(" any of that, because a sent prompt cannot be unsent.\n")
    print(f"  {'':<6}{'case':<20}{'want':<8}{'got':<8}what it teaches")
    print("  " + "-" * 104)

    failures = 0
    for case in CASES:
        v = secret_door(case.text)
        good = v.action == case.expect
        failures += not good
        print(f"  [{'PASS' if good else 'FAIL'}] {case.name:<20}{case.expect:<8}"
              f"{v.action:<8}{case.teaches[:58]}")

    print(f"\n {failures} failure(s).")
    print(f"""
 {hrule('the three rows to stop on')}

 forgot_password   ALLOWED, and it contains the word "password" twice. A prose
                   keyword rule blocks this customer -- and a guardrail that
                   blocks real customers gets switched off, after which you
                   have no guardrail at all.

 dotenv_paste      BLOCKED, and look at WHY: MODEL= and DEBUG= are ignored,
                   CLIENT_SECRET= is not. The rule matches a machine-written
                   NAME, which is a shape. That is allowed. Matching a human
                   sentence is not.

 git_sha           ALLOWED despite being 40 random-looking characters. That is
                   NOT_SECRET_SHAPES earning its place: the moment you flag
                   "looks random" you owe the world an exemption list.

 THE RULE: match the shape of the secret, or the shape of a machine-written
 name. Never the shape of a sentence.

 Next:
   python secret_door.py --policy    the rule table, as security reads it
   python secret_door.py --audit     what gets logged, and what must not
   python secret_door.py --case stack_trace
   python secret_door.py --live      paste your own and see""")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
