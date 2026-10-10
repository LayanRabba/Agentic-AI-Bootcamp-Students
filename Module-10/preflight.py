"""
Module 10 -- preflight check.  Run this BEFORE the session.
It changes nothing. It reports, and tells you how to fix what it finds.

    python preflight.py

This module ships its own .venv (Python 3.12). Activate it, or call it directly:
    .venv/bin/python preflight.py
Every guardrail is plain Python. One extra check compared with Module 7: we
confirm you can reach BOTH models, because Exercise 3 routes between them.
"""

import importlib.metadata as md
import sys
import time
from pathlib import Path

TESTED = {
    "openai": "2.52.0",
    "langgraph": "1.2.10",
    "langchain-openai": "1.4.1",
    "python-dotenv": "1.2.2",
}
OK, WARN, BAD = "[ OK ]", "[WARN]", "[FAIL]"
HERE = Path(__file__).resolve().parent
problems: list[str] = []


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("=" * 66)
    print(" Agentic AI Bootcamp - Module 10 (Guardrails & Safety) preflight")
    print("=" * 66)

    major, minor = sys.version_info[:2]
    if (major, minor) in [(3, 12), (3, 13)]:
        print(f"{OK} Python {sys.version.split()[0]}")
    else:
        print(f"{BAD} Python {sys.version.split()[0]} - use 3.12 or 3.13")
        problems.append("Use this module's own environment: .venv\\Scripts\\python.exe preflight.py "
                        "(macOS/Linux: .venv/bin/python preflight.py)")

    in_venv = sys.prefix != sys.base_prefix
    print(f"{OK if in_venv else WARN} virtual environment: {'active' if in_venv else 'NOT active'}")
    if not in_venv:
        problems.append("Activate this module's environment first: .\\.venv\\Scripts\\Activate.ps1 "
                        "(macOS/Linux: source .venv/bin/activate). Missing? "
                        "python3.12 -m venv .venv && pip install -r requirements.txt")

    print("-" * 66)
    for package, expected in TESTED.items():
        try:
            found = md.version(package)
        except md.PackageNotFoundError:
            print(f"{BAD} {package:<18} not installed")
            problems.append(f"pip install -r requirements.txt   (missing {package})")
            continue
        flag = OK if found == expected else WARN
        note = "" if found == expected else f"   (class tested on {expected})"
        print(f"{flag} {package:<18} {found}{note}")

    print("-" * 66)
    sys.path.insert(0, str(HERE / "shared"))
    try:
        import setup_env  # noqa: F401
        print(f"{OK} shared/setup_env.py loaded")
        print(f"       cheap model  = {setup_env.CHEAP_MODEL}")
        print(f"       strong model = {setup_env.STRONG_MODEL}")
    except SystemExit as stop:
        print(f"{BAD} {str(stop).strip()}")
        problems.append("Put OPENROUTER_API_KEY=sk-or-... in the .env file at the repo root.")
        return report()

    # The module's own files must import cleanly -- they are each other's
    # dependencies today (cases.py imports scorecard.py, and so on).
    for name in ("scorecard", "meter", "cases", "policy"):
        try:
            __import__(name)
            print(f"{OK} shared/{name}.py imports")
        except Exception as exc:
            print(f"{BAD} shared/{name}.py failed: {exc}")
            problems.append(f"shared/{name}.py did not import -- re-pull the module folder")

    # Both models, because Exercise 3 needs both and finding out mid-exercise
    # is a bad time.
    for label, model in (("cheap", setup_env.CHEAP_MODEL),
                         ("strong", setup_env.STRONG_MODEL)):
        started = time.perf_counter()
        try:
            reply = setup_env.graph_llm(model).invoke("Reply with exactly: READY")
            took = time.perf_counter() - started
            print(f"{OK} {label:<6} model answered {reply.content.strip()!r}  ({took:.1f} s)")
        except Exception as exc:
            print(f"{BAD} {label} model ({model}) failed: {str(exc)[:110]}")
            problems.append(
                f"Could not reach {model}. Check credit at https://openrouter.ai/keys, "
                f"or set MODEL_STRONG in .env to a model you can use.")

    # A free, offline sanity check that the harness itself works.
    try:
        from cases import BAD_OUTPUTS, CANARY
        assert any(CANARY in text for _, text, _ in BAD_OUTPUTS)
        print(f"{OK} the unit fixtures are present ({len(BAD_OUTPUTS)} crafted bad outputs)")
    except Exception as exc:
        print(f"{WARN} could not read the unit fixtures: {exc}")

    return report()


def report() -> int:
    print("=" * 66)
    if problems:
        print(f"{len(problems)} thing(s) to fix before the session:\n")
        for number, fix in enumerate(problems, 1):
            print(f"  {number}. {fix}")
        print("\nStuck? Post this whole output in the class channel.")
        return 1
    print("All clear. You are ready.")
    print("\nA note on money: today's exercises make real calls. The whole module,")
    print("run start to finish including the homework, costs roughly 5-8 cents.")
    print("Every file prints a cost card. Watch them -- that is half the lesson.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
