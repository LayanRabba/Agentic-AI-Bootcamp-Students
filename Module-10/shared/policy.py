"""
shared/policy.py  --  the desk's tools, and what each one is allowed to do.

This file is CONFIG, not code. That is on purpose.

In a real system the policy lives outside the program -- a config file, a
policy engine, a row in a table -- for three reasons:

  1. Security review can read it without reading your Python.
  2. You can tighten a cap at 3am without a deploy.
  3. The diff when someone raises the refund cap is one obvious line, in a
     file whose whole job is to be audited.

A policy buried in `if` statements across four files is a policy nobody has
ever read end to end. Including you.

Note what is NOT here: the model. The model does not get a vote on its own
limits -- it cannot read this file, cannot change it, and does not know the
cap. If an agent could edit its own policy, it would not be a policy.
"""

from __future__ import annotations

# ── the tools, and their risk ────────────────────────────────────────────────
# risk:            safe     read-only, reversible, no money, no outsider sees it
#                  money    moves money. Irreversible in practice.
#                  outward  a third party sees it. You cannot un-send it.
# needs_approval:  does a human have to say yes before this runs?
TOOLS = {
    "lookup_order": {
        "risk": "safe",
        "needs_approval": False,
        "why": "read-only. Gating this would teach the human to click yes without looking.",
    },
    "issue_refund": {
        "risk": "money",
        "needs_approval": True,
        "max_amount": 100.00,
        "why": "money leaves the company and does not come back.",
    },
    "email_customer": {
        "risk": "outward",
        "needs_approval": True,
        "allowed_domains": ("northwind-supplies.com", "example.com"),
        "why": "an email to the wrong address is a data breach you performed yourself.",
    },
}

# The stop rule. Without it, a confused agent loops until your credit runs out.
MAX_TOOL_STEPS = 4

# How the tools are described to the model (the OpenAI tools format).
# Keep these descriptions boring and literal. They are not the guardrail --
# the code is -- but a vague description invites a creative call.
SCHEMAS = {
    "lookup_order": {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": "Look up one order by its 4-digit id. Read-only.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string", "description": "e.g. 1187"}},
                "required": ["order_id"],
            },
        },
    },
    "issue_refund": {
        "type": "function",
        "function": {
            "name": "issue_refund",
            "description": (
                "Refund one order. The amount must be the order's own recorded "
                "amount: you may not choose a different figure."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "amount": {"type": "number", "description": "must equal the order's amount"},
                },
                "required": ["order_id", "amount"],
            },
        },
    },
    "email_customer": {
        "type": "function",
        "function": {
            "name": "email_customer",
            "description": "Send an email to the customer's address on file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["address", "body"],
            },
        },
    },
}


def risk_of(tool_name: str) -> str:
    return TOOLS.get(tool_name, {}).get("risk", "unknown")


def needs_approval(tool_name: str) -> bool:
    """Unknown tools need approval. Fail closed, including on your own typos."""
    return TOOLS.get(tool_name, {}).get("needs_approval", True)


def schemas_for(names) -> list[dict]:
    """The tool definitions to send to the model -- only for the names given."""
    return [SCHEMAS[n] for n in names if n in SCHEMAS]


# ═════════════════════════════════════════════════════════════════════════════
# SECRET POLICY  --  what must never reach a model, and what to do about it
# ═════════════════════════════════════════════════════════════════════════════
#
# Exercise 4 enforces this table. Read it as a security reviewer would: every
# row is a rule, and the rules are DATA. Adding one is a one-line change to a
# file whose whole job is to be audited -- not a patch to somebody's `if`
# statement three functions deep.
#
# Each rule has:
#   name      what the audit log will call it
#   pattern   how it is RECOGNISED -- by shape, never by the surrounding prose
#   action    "block"  the request never reaches a model, full stop
#             "redact" the value is replaced and the request continues
#   policy    the company policy this row exists to satisfy
#   rotate    is the secret burned the moment it was pasted?
#   why       the sentence you would say in a review
#
# ACTION, AND WHY IT IS NOT ALWAYS "BLOCK":
#   A live credential is "block" -- there is no safe way to continue, and the
#   user needs to be told to rotate it.
#   A customer's card number is "redact" -- they still deserve an answer, and
#   a blocked reply is a support ticket.
#   Getting this distinction wrong in either direction is the whole craft:
#   block everything and the tool gets switched off; redact everything and you
#   have quietly forwarded a production key to a third party.

SECRET_RULES = [
    # ---- live credentials: BLOCK, and tell the user to rotate ----------------
    {
        "name": "private_key_block",
        "pattern": r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----",
        "action": "block",
        "policy": "Passwords and Credentials Policy",
        "rotate": True,
        "why": "a private key in a prompt is a private key in someone else's logs",
    },
    {
        "name": "aws_access_key_id",
        "pattern": r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b",
        "action": "block",
        "policy": "Passwords and Credentials Policy",
        "rotate": True,
        "why": "AWS key ids have a fixed shape, so this is a high-confidence match",
    },
    {
        "name": "provider_api_key",
        # sk-..., sk-or-v1-..., and the same family from other vendors.
        "pattern": r"\b(?:sk|rk|pk)-(?:[a-z]{2,10}-)?(?:v\d-)?[A-Za-z0-9_\-]{16,}\b",
        "action": "block",
        "policy": "Passwords and Credentials Policy",
        "rotate": True,
        "why": "the key that pays for this very call is the one most often pasted",
    },
    {
        "name": "bearer_or_jwt",
        "pattern": r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b",
        "action": "block",
        "policy": "Access Control Policy",
        "rotate": True,
        "why": "a session token is a logged-in user, and it is readable without a password",
    },
    {
        "name": "connection_string_password",
        # scheme://user:password@host -- the password is group 1.
        "pattern": r"\b[a-z][a-z0-9+.\-]{2,}://[^\s:@/]+:([^\s:@/]{3,})@[^\s/]+",
        "action": "block",
        "policy": "Passwords and Credentials Policy",
        "rotate": True,
        "why": "a database URL carries the password inline, so it leaks as one blob",
    },
    {
        "name": "secret_assignment",
        # A MACHINE-WRITTEN NAME that means credential, with a real value after
        # it. Note what this matches: `API_KEY=...`, `"password": "..."`.
        # Note what it does NOT match: a human writing "I forgot my password".
        # Keywords are fine when you are matching an identifier. They are
        # useless when you are matching prose. That distinction is the lesson.
        "pattern": r"(?i)\b(?:api[_-]?key|secret|password|passwd|pwd|access[_-]?token"
                   r"|auth[_-]?token|client[_-]?secret|private[_-]?key)\b"
                   r"\s*[:=]\s*[\"']?([^\s\"',;]{6,})",
        "action": "block",
        "policy": "Passwords and Credentials Policy",
        "rotate": True,
        "why": "catches a pasted .env, a config fragment or a code snippet",
    },

    # ---- the customer's own data: REDACT, and carry on ----------------------
    {
        "name": "payment_card",
        "pattern": r"\b(?:\d[ -]?){12,18}\d\b",
        "action": "redact",
        "policy": "Data Classification",
        "rotate": False,
        "why": "the customer volunteered it; they still deserve an answer",
    },
    {
        "name": "iban",
        # A real IBAN is 15-34 chars and the printed grouping does not always
        # land on a multiple of four -- so allow a short final group, or the
        # redaction leaves the last two digits sitting in the prompt.
        "pattern": r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){3,6}(?:[ ]?[A-Z0-9]{1,3})?\b",
        "action": "redact",
        "policy": "Data Classification",
        "rotate": False,
        "why": "same reasoning as a card number",
    },
]

# Shapes that are long and random-looking but are NOT secrets. The entropy
# backstop (Exercise 4) skips these.
#
# This list is the price of catching unknown secret formats: the moment you
# flag "looks random", you must excuse everything that legitimately looks
# random. Leave it out and you block every customer who pastes a tracking
# number -- which is how a guardrail becomes an outage.
NOT_SECRET_SHAPES = [
    ("uuid",          r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"),
    ("git_sha",       r"\b[0-9a-f]{7,40}\b"),
    ("tracking_no",   r"\b1Z[0-9A-Z]{16}\b"),
    ("order_id",      r"\b(?:EX-)?\d{4}\b"),
    ("content_hash",  r"\bsha256:[0-9a-f]{64}\b"),
]

# How random is "suspiciously random"? Shannon entropy, bits per character.
# Tuned on the cases in Exercise 4: English prose sits near 4.0 bits over a
# whole sentence but low per-token; base64 credentials run 4.5-6.0.
ENTROPY_MIN_LENGTH = 20
ENTROPY_THRESHOLD = 4.2
