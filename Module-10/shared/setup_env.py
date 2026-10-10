"""
shared/setup_env.py  --  every exercise imports this FIRST.

You never need to edit this file. It does four boring jobs so the exercise
files can stay about guardrails:

  1. makes the Windows terminal print emoji and arrows instead of  â€"
  2. stops CrewAI freezing for 20 seconds to ask about "execution traces"
  3. finds your .env and checks OPENROUTER_API_KEY is in it
  4. gives you TWO models: a cheap one and a capable one (Exercise 3 routes
     between them)

Why job 2 exists: CrewAI decides "is this your first run?" the moment it is
imported, and it remembers the answer per FOLDER. Every new exercise folder
counts as a first run, so without this you would get a 20-second question in
every folder today. Recording the answer before the import stops it.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# 1 -- UTF-8 console -----------------------------------------------------------
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 2 -- CrewAI's first-run question (must run BEFORE crewai is imported) ---------
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_STORAGE_DIR", "jhf-agentic-bootcamp")
try:
    from crewai_core.user_data import update_user_data  # small import, not crewai itself

    update_user_data({"first_execution_done": True, "trace_consent": False})
except Exception:
    pass  # CrewAI not installed, or a different version: nothing to silence

# 3 -- your key ---------------------------------------------------------------
from dotenv import find_dotenv, load_dotenv  # noqa: E402

# Load EVERY .env from here up to the repo root, nearest first.
#
# The order matters and the lack of a `break` matters. python-dotenv does not
# overwrite a value that is already set, so:
#
#   1. anything already in your SHELL environment wins over every file
#   2. then this module's own .env (model choices live there)
#   3. then the repo-root .env (your OPENROUTER_API_KEY lives there)
#
# An earlier version stopped at the first .env it found. That meant adding a
# .env to this module silently hid the repo-root one, and the key vanished
# with a confusing error. Load the chain, stop at nothing.
load_dotenv(find_dotenv(usecwd=True))
for _parent in Path(__file__).resolve().parents:
    _candidate = _parent / ".env"
    if _candidate.exists():
        load_dotenv(_candidate)

API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
if not API_KEY:
    sys.exit(
        "\nOPENROUTER_API_KEY not found.\n"
        "Put a file called .env in the repo root containing:\n"
        "    OPENROUTER_API_KEY=sk-or-...\n"
        "It is the same key you have used since Module 1.\n"
    )

BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# 4 -- two models: cheap and capable -------------------------------------------
# .env may say MODEL=openai/gpt-4o-mini or MODEL=openrouter/openai/gpt-4o-mini.
# Exercise 3 sends easy work to CHEAP and hard work to STRONG, then measures
# whether that was a good trade. Both are priced in shared/meter.py.
MODEL = os.environ.get("MODEL", "openai/gpt-4o-mini").strip().removeprefix("openrouter/")
CHEAP_MODEL = MODEL
STRONG_MODEL = os.environ.get("MODEL_STRONG", "openai/gpt-4.1-mini").strip().removeprefix("openrouter/")


def client():
    """A plain OpenAI-style client pointed at OpenRouter.

    The warm-up and Exercise 2 use this directly instead of a framework: when
    you are learning where a guardrail goes, you want to see every call.
    """
    from openai import OpenAI

    return OpenAI(base_url=BASE_URL, api_key=API_KEY)


def crew_llm():
    """The model, in the form CrewAI wants it.

    Call this once PER AGENT -- do not share one LLM object between agents.
    CrewAI 1.15 keeps a running token count on the LLM object and adds it up
    once per agent, so a shared object makes a 3-agent crew report 3x its real
    usage (9 calls instead of 3). One object per agent keeps the meter honest.
    """
    from crewai import LLM

    return LLM(model=f"openrouter/{MODEL}", temperature=0, api_key=API_KEY)


def graph_llm(model: str | None = None):
    """The model, in the form LangGraph / LangChain wants it.

    Pass a model name to pick one deliberately (Exercise 3):
        setup_env.graph_llm(setup_env.CHEAP_MODEL)
        setup_env.graph_llm(setup_env.STRONG_MODEL)
    """
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=model or MODEL, temperature=0, base_url=BASE_URL, api_key=API_KEY)
