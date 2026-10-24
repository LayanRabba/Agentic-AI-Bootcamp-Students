
"""
Module 2 Bridge Project - The Evidence Desk
Part B: CrewAI (Hierarchical)

Use case: Fact-Check Desk

A hierarchical manager coordinates a Researcher
and a Writer.

The Researcher uses real web search.
The Writer answers only when evidence is sufficient.

A fallback search is attempted if the first
query returns NO_RESULTS.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

from crewai import Agent, Crew, LLM, Process, Task
from crewai.tools import tool
from dotenv import find_dotenv, load_dotenv

try:
    from crewai.events.listeners.tracing.utils import (
        mark_first_execution_done,
    )

    mark_first_execution_done()
except Exception:
    pass


# ==========================================
# Configuration
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(PROJECT_DIR))

from search_tools import (  # noqa: E402
    NO_RESULTS,
    SEARCH_UNAVAILABLE,
    web_search,
)

load_dotenv(PROJECT_DIR / ".env")
load_dotenv(find_dotenv(usecwd=True))

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise RuntimeError(
        "OPENROUTER_API_KEY not found. "
        "Check your .env file."
    )


# ==========================================
# TODO 1: Model Client
# ==========================================

llm = LLM(
    model="openrouter/openai/gpt-4o-mini",
    temperature=0,
    api_key=api_key,
)


# ==========================================
# Search Fallback Helper
# ==========================================

def make_short_query(query: str) -> str:
    """
    Extract a shorter search query.

    For a named organization, prefer its name.
    For lowercase product names with numbers,
    preserve the name and model number.

    This is a simple heuristic, not a full
    named-entity recognition system.
    """

    query = query.strip()

    ignored = {
        "a", "an", "the", "was", "is", "are",
        "were", "did", "does", "do", "who",
        "what", "where", "when", "how",
        "claim", "verify", "fact", "check",
    }

    capitalized = re.findall(
        r"\b[A-Z][A-Za-z0-9-]*\b",
        query,
    )

    for word in capitalized:
        if word.lower() not in ignored:
            return word

    words = re.findall(
        r"[A-Za-z0-9-]+",
        query,
    )

    words = [
        word
        for word in words
        if word.lower() not in ignored
    ]

    if not words:
        return query

    # Keep a product name together with its
    # model number when one is present.
    for index, word in enumerate(words):
        if any(char.isdigit() for char in word):
            if index > 0:
                return (
                    words[index - 1]
                    + " "
                    + word
                )
            return word

    return " ".join(words[:2])


# ==========================================
# TODO 2: Web Search Tool
# ==========================================

@tool("Web Search")
def search_web(query: str) -> str:
    """
    Search the internet for fact-checking evidence.

    Input:
        A short query about a company, person,
        product, or factual claim.

    Output:
        Search findings including source URLs.

    If the search returns NO_RESULTS, this tool
    tries one shorter search query.

    NO_RESULTS means the searches found nothing.
    SEARCH_UNAVAILABLE means searching failed.

    These markers are not proof of a claim.
    Never invent evidence or source URLs.
    """

    print("\n[CREWAI SEARCH]")
    print("FIRST QUERY:", query)

    result = web_search(query)

    print("FIRST RESULT:", result[:120])

    if result == NO_RESULTS:
        fallback = make_short_query(query)

        if fallback.lower() != query.strip().lower():
            print("FALLBACK QUERY:", fallback)

            fallback_result = web_search(fallback)

            print(
                "FALLBACK RESULT:",
                fallback_result[:120],
            )

            # A successful second search replaces
            # the original NO_RESULTS.
            if fallback_result not in (
                NO_RESULTS,
                SEARCH_UNAVAILABLE,
            ):
                return (
                    f"Search query used: {fallback}\n\n"
                    f"{fallback_result}"
                )

            if fallback_result == SEARCH_UNAVAILABLE:
                return (
                    "NO_RESULTS on the first query; "
                    "SEARCH_UNAVAILABLE on the fallback. "
                    "No usable evidence was obtained."
                )

    return result


# ==========================================
# TODO 3-4: Build Agents
# ==========================================

def build_crew() -> Crew:

    researcher = Agent(
        role="Evidence Researcher",
        goal=(
            "Investigate factual claims using "
            "real web-search evidence and preserve "
            "the exact source URLs."
        ),
        backstory=(
            "You are a professional fact-checking "
            "researcher. Always use the Web Search "
            "tool instead of relying on memory. "
            "Prefer short searches about the main "
            "entity. Carefully distinguish evidence "
            "from unsupported assumptions. "
            "Report NO_RESULTS when no results exist "
            "and SEARCH_UNAVAILABLE when searching "
            "failed. Never invent URLs or findings."
        ),
        tools=[search_web],
        llm=llm,
        verbose=True,
        max_iter=4,
        allow_delegation=False,
    )

    writer = Agent(
        role="Evidence-Based Fact-Check Writer",
        goal=(
            "Produce a concise fact-check supported "
            "by real sources, or report that the "
            "claim could not be verified."
        ),
        backstory=(
            "You are a cautious fact-checking writer. "
            "You use only evidence supplied by the "
            "researcher. Your own background knowledge "
            "is not evidence. If sources are missing "
            "or irrelevant, you refuse to answer "
            "the claim. Never invent a URL or fact. "
            "A correct refusal is better than an "
            "unsupported answer."
        ),
        tools=[],
        llm=llm,
        verbose=True,
        max_iter=4,
        allow_delegation=False,
    )

    # ======================================
    # TODO 5: Research Task
    # ======================================

    research_task = Task(
        description=(
            "Investigate this factual claim:\n"
            "{question}\n\n"
            "You MUST use the Web Search tool.\n"
            "Prefer a short query focused on the "
            "main entity, rather than a full sentence.\n"
            "Read the tool results and identify "
            "which findings are relevant.\n\n"
            "Include the exact source URLs provided "
            "by the search tool.\n"
            "Do not use your own memory to fill gaps.\n\n"
            "If the tool reports NO_RESULTS, state "
            "that no useful results were found.\n"
            "If it reports SEARCH_UNAVAILABLE, state "
            "that the search could not be completed.\n"
            "Do not invent evidence."
        ),
        expected_output=(
            "A factual evidence report with relevant "
            "findings and exact source URLs, or an "
            "explicit statement that the search "
            "found nothing or was unavailable."
        ),
    )

    # ======================================
    # TODO 6: Writing Task
    # ======================================

    write_task = Task(
        description=(
            "Fact-check this claim:\n"
            "{question}\n\n"
            "Use ONLY evidence from the research "
            "task. Choose one of two formats.\n\n"

            "FORMAT A: SUFFICIENT EVIDENCE\n"
            "Begin with exactly:\n"
            "VERDICT: ANSWERED\n\n"
            "Then explain whether the claim is "
            "supported or contradicted by the "
            "actual evidence. Keep the answer "
            "under 180 words. Include at least "
            "one genuine source URL from the "
            "research report.\n\n"

            "FORMAT B: INSUFFICIENT EVIDENCE\n"
            "Begin with exactly:\n"
            "VERDICT: COULD NOT VERIFY\n\n"
            "State that the claim could not be "
            "verified. Explain which evidence "
            "is missing in one or two bullets.\n"
            "Do NOT answer the claim.\n"
            "Finish with:\n"
            "NEXT SEARCH: <one useful search query>\n\n"

            "Rules:\n"
            "- NO_RESULTS means insufficient evidence.\n"
            "- SEARCH_UNAVAILABLE is not proof "
            "that the claim is false.\n"
            "- Irrelevant sources are insufficient.\n"
            "- Never invent facts or sources.\n"
            "- If uncertain, use FORMAT B."
        ),
        expected_output=(
            "Either VERDICT: ANSWERED with a "
            "source-supported answer and real URL, "
            "or VERDICT: COULD NOT VERIFY with "
            "missing evidence and NEXT SEARCH."
        ),
        context=[research_task],
    )

    # ======================================
    # TODO 7: Hierarchical Crew
    # ======================================

    return Crew(
        agents=[
            researcher,
            writer,
        ],
        tasks=[
            research_task,
            write_task,
        ],
        process=Process.hierarchical,
        manager_llm=llm,
        verbose=True,
        tracing=False,
    )


# ==========================================
# TODO 8: Route Detection
# ==========================================

def detect_route(text: str) -> str:
    """
    Infer the route from the final answer text.

    This is not a guaranteed code-level branch,
    unlike the LangGraph conditional edge.
    """

    match = re.search(
        r"^\s*VERDICT\s*:\s*(.+?)\s*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )

    if not match:
        return "UNKNOWN - NO VERDICT"

    verdict = match.group(1).strip().upper()

    if verdict.startswith("COULD NOT VERIFY"):
        return "GAP REPORTED"

    if verdict.startswith("ANSWERED"):
        return "ANSWERED"

    return "UNKNOWN - UNRECOGNIZED VERDICT"


# ==========================================
# Main
# ==========================================

def main() -> int:

    question = (
        " ".join(sys.argv[1:]).strip()
        or "Anthropic was founded by former OpenAI employees"
    )

    print("=" * 70)
    print("MODULE 2 - EVIDENCE DESK")
    print("FRAMEWORK: CrewAI")
    print("PROCESS: Hierarchical")
    print("USE CASE: Fact-Check Desk")
    print("=" * 70)

    print("\nQUESTION:", question)
    print("\nStarting hierarchical crew...\n")

    crew = build_crew()

    result = str(
        crew.kickoff(
            inputs={"question": question}
        )
    )

    route = detect_route(result)

    print("\n" + "=" * 70)
    print("QUESTION :", question)
    print("=" * 70)

    print("\nFINAL OUTPUT:")
    print(result)

    print("\n" + "=" * 70)
    print("ROUTE :", route)
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
