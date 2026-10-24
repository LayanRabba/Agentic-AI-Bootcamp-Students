
"""
Module 2 Bridge Project - The Evidence Desk
Part A: LangGraph

Use case: Fact-Check Desk

The agent plans a search, retrieves evidence,
assesses its quality and conditionally routes
to an answer or an evidence-gap report.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Literal, TypedDict

from dotenv import find_dotenv, load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph


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

base_url = os.getenv(
    "OPENROUTER_BASE_URL",
    "https://openrouter.ai/api/v1",
)

if not api_key:
    raise RuntimeError(
        "OPENROUTER_API_KEY not found. "
        "Check your .env file."
    )


# ==========================================
# TODO 1: Model Client
# ==========================================

llm = ChatOpenAI(
    model="openai/gpt-4o-mini",
    temperature=0,
    base_url=base_url,
    api_key=api_key,
)


def ask_llm(prompt: str) -> str:
    """Call the language model and return text."""

    response = llm.invoke(prompt)
    content = response.content

    if isinstance(content, str):
        return content.strip()

    return str(content).strip()


# ==========================================
# State
# ==========================================

class DeskState(TypedDict):
    question: str
    query: str
    evidence: str
    verdict: str
    reasoning: str
    output: str
    route_taken: str


# ==========================================
# TODO 2: Plan Query
# ==========================================

def plan_query(state: DeskState) -> dict:
    """Generate a short, useful web-search query."""

    print("\n[1] Planning search query...")

    prompt = f"""
You are a web search query planner.

The user wants to fact-check this claim:

{state["question"]}

Generate ONE very short search query.

IMPORTANT:
- Prefer the main entity's name.
- For claims about an organization, search
  the organization's name first.
- Avoid complete sentences.
- Avoid unnecessary words such as
  "founded by", "former employees", etc.
- For unfamiliar product names, keep the
  product name, including model numbers.
- Return ONLY the query.
- No quotation marks or explanations.

Example:
Claim: Anthropic was founded by former OpenAI employees
Query: Anthropic

Example:
Claim: The flurbotron 9000 was released in 2019
Query: flurbotron 9000
"""

    query = ask_llm(prompt)

    query = query.strip().strip("\"'`")

    if not query:
        query = state["question"]

    print("SEARCH QUERY:", query)

    return {"query": query}


# ==========================================
# Search Query Fallback
# ==========================================

def find_main_entity(question: str) -> str:
    """
    Extract a likely named entity for a fallback
    search when a longer query returns no results.

    This is a simple heuristic, not a full
    named-entity recognition system.
    """

    ignored = {
        "the",
        "a",
        "an",
        "was",
        "is",
        "are",
        "did",
        "does",
        "when",
        "who",
        "what",
        "where",
        "how",
        "claim",
    }

    words = re.findall(
        r"\b[A-Z][A-Za-z0-9-]*\b",
        question,
    )

    for word in words:
        if word.lower() not in ignored:
            return word

    return ""


# ==========================================
# TODO 3: Run Search
# ==========================================

def run_search(state: DeskState) -> dict:
    """
    Run the actual web-search tool.

    No LLM is called by this node.
    """

    print("\n[2] Running web search...")

    query = state["query"]
    evidence = web_search(query)

    print("FIRST SEARCH:", query)
    print("SEARCH RESULT:", evidence[:120])

    # A different search query may recover useful
    # results if the first query was too specific.
    #
    # Only retry on NO_RESULTS.
    # Never pretend SEARCH_UNAVAILABLE means no results.

    if evidence == NO_RESULTS:

        fallback = find_main_entity(
            state["question"]
        )

        if (
            fallback
            and fallback.lower() != query.lower()
        ):
            print(
                "SEARCH FALLBACK:",
                fallback,
            )

            fallback_evidence = web_search(fallback)

            # Preserve the result and query of the
            # second search so the evidence is traceable.
            if fallback_evidence != NO_RESULTS:
                evidence = fallback_evidence
                query = fallback

    return {
        "query": query,
        "evidence": evidence,
    }


# ==========================================
# TODO 6: Safe Verdict Parser
# ==========================================

def read_verdict(raw: str) -> str:
    """
    Return ENOUGH or NOT_ENOUGH.

    If the verdict is unclear, fail closed.
    """

    lines = [
        line.strip()
        for line in raw.splitlines()
        if line.strip()
    ]

    if not lines:
        return "NOT_ENOUGH"

    last_line = lines[-1].upper()

    normalized = re.sub(
        r"[\s-]+",
        "_",
        last_line,
    )

    # NOT_ENOUGH must be checked FIRST.
    if re.search(
        r"(?<![A-Z_])NOT_ENOUGH(?![A-Z_])",
        normalized,
    ):
        return "NOT_ENOUGH"

    if re.search(
        r"(?<![A-Z_])ENOUGH(?![A-Z_])",
        normalized,
    ):
        return "ENOUGH"

    return "NOT_ENOUGH"


# ==========================================
# TODO 4 + 5: Assess Evidence
# ==========================================

def assess(state: DeskState) -> dict:
    """Evaluate whether evidence is sufficient."""

    print("\n[3] Assessing evidence...")

    evidence = state["evidence"].strip()

    # Marker 1: Search ran but found nothing.
    if evidence == NO_RESULTS:

        return {
            "verdict": "NOT_ENOUGH",
            "reasoning": (
                "The search completed but returned "
                "no matching evidence."
            ),
        }

    # Marker 2: Search could not run.
    if evidence == SEARCH_UNAVAILABLE:

        return {
            "verdict": "NOT_ENOUGH",
            "reasoning": (
                "The search service was unavailable. "
                "The claim could not be checked."
            ),
        }

    if not evidence:

        return {
            "verdict": "NOT_ENOUGH",
            "reasoning": "No evidence was returned.",
        }

    urls = re.findall(
        r"https?://[^\s<>\]\"']+",
        evidence,
    )

    if not urls:

        return {
            "verdict": "NOT_ENOUGH",
            "reasoning": (
                "The evidence contains no source URLs."
            ),
        }

    prompt = f"""
You are a strict fact-checking evaluator.

CLAIM:
{state["question"]}

WEB SEARCH EVIDENCE:
{evidence[:12000]}

Decide if the evidence is sufficient to give
a reliable answer to the claim.

Important rules:
- Use only this evidence.
- Do not use your own background knowledge.
- Check whether the sources actually discuss
  the exact claim.
- A valid source can support OR contradict
  a claim. Both can count as sufficient.
- An unrelated search result is not evidence.
- The presence of a URL alone is not enough.
- If the information is incomplete, unclear,
  or unrelated, choose NOT_ENOUGH.
- Explain your reasoning in 1-3 short bullets.
- End with exactly one verdict on its own line:
  ENOUGH
  or
  NOT_ENOUGH
"""

    reasoning = ask_llm(prompt)
    verdict = read_verdict(reasoning)

    print("VERDICT:", verdict)

    return {
        "verdict": verdict,
        "reasoning": reasoning,
    }


# ==========================================
# TODO 7: Conditional Router
# ==========================================

def choose_next(
    state: DeskState,
) -> Literal["write_answer", "report_gap"]:

    if state["verdict"] == "ENOUGH":
        return "write_answer"

    return "report_gap"


# ==========================================
# TODO 8: Answer Route
# ==========================================

def write_answer(state: DeskState) -> dict:
    """Answer the claim using retrieved evidence."""

    print("\n[4] Writing evidence-based answer...")

    evidence = state["evidence"]

    urls = re.findall(
        r"https?://[^\s<>\]\"']+",
        evidence,
    )

    prompt = f"""
You are a careful fact-checking assistant.

CLAIM:
{state["question"]}

EVIDENCE:
{evidence[:12000]}

Write a fact-checking answer.

Rules:
- Use ONLY supplied evidence.
- Do not invent facts.
- State whether the claim is supported
  or contradicted.
- Explain briefly.
- Cite at least one actual source URL
  present in the evidence.
- If any part is not covered, mention that.
- Maximum 180 words.
- Do not invent URLs.
"""

    answer = ask_llm(prompt)

    if urls:
        source_url = urls[0].rstrip(".,;)")
        answer += f"\nsource: {source_url}"

    return {
        "output": answer,
        "route_taken": "ANSWERED",
    }


# ==========================================
# TODO 9: Gap Route
# ==========================================

def report_gap(state: DeskState) -> dict:
    """
    Explain what evidence is missing.

    Never provide an unsupported answer.
    No LLM call is necessary.
    """

    print("\n[4] Reporting evidence gap...")

    evidence = state["evidence"].strip()

    if evidence == NO_RESULTS:

        missing = (
            "- The search returned no matching results.\n"
            "- No source was found to verify the claim."
        )

    elif evidence == SEARCH_UNAVAILABLE:

        missing = (
            "- The search service could not be reached.\n"
            "- The claim has not been checked."
        )

    else:

        missing = (
            "- The available sources do not establish "
            "the claim reliably.\n"
            "- More relevant evidence is needed."
        )

    next_query = (
        state["query"].strip()
        + " reliable source verification"
    )

    output = (
        "This claim could not be verified "
        "using the available evidence.\n\n"
        f"{missing}\n\n"
        f"NEXT SEARCH: {next_query}"
    )

    return {
        "output": output,
        "route_taken": "GAP REPORTED",
    }


# ==========================================
# TODO 10-13: Build Graph
# ==========================================

def build_graph():

    graph = StateGraph(DeskState)

    # TODO 10: Register all nodes.
    graph.add_node("plan_query", plan_query)
    graph.add_node("run_search", run_search)
    graph.add_node("assess", assess)
    graph.add_node("write_answer", write_answer)
    graph.add_node("report_gap", report_gap)

    # TODO 11: Entry point and fixed path.
    graph.set_entry_point("plan_query")

    graph.add_edge(
        "plan_query",
        "run_search",
    )

    graph.add_edge(
        "run_search",
        "assess",
    )

    # TODO 12: Conditional decision.
    graph.add_conditional_edges(
        "assess",
        choose_next,
        {
            "write_answer": "write_answer",
            "report_gap": "report_gap",
        },
    )

    # TODO 13: Both routes end.
    graph.add_edge("write_answer", END)
    graph.add_edge("report_gap", END)

    return graph.compile()


# ==========================================
# Run Agent
# ==========================================

def run(question: str) -> DeskState:

    initial_state: DeskState = {
        "question": question,
        "query": "",
        "evidence": "",
        "verdict": "",
        "reasoning": "",
        "output": "",
        "route_taken": "",
    }

    return build_graph().invoke(initial_state)


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
    print("FRAMEWORK: LangGraph")
    print("USE CASE: Fact-Check Desk")
    print("=" * 70)

    result = run(question)

    print("\n" + "=" * 70)
    print("QUESTION :", result["question"])
    print("QUERY    :", result["query"])
    print("VERDICT  :", result["verdict"])
    print("ROUTE    :", result["route_taken"])
    print("=" * 70)

    print("\nASSESSMENT:")
    print(result["reasoning"])

    print("\nEVIDENCE PREVIEW:")
    print(result["evidence"][:700])

    print("\nFINAL OUTPUT:")
    print(result["output"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
