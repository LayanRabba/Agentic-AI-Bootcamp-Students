# Module 2 Bridge Project — The Evidence Desk

## Use Case: Fact-Check Desk

This project implements a fact-checking agent using two frameworks: LangGraph and CrewAI. Both systems search for evidence and decide whether to answer a claim or report that there is insufficient information.

## Test Results

| Framework | Test Claim | Result |
|---|---|---|
| LangGraph | Anthropic was founded by former OpenAI employees | ENOUGH — ANSWERED |
| LangGraph | The flurbotron 9000 was released in 2019 | NOT_ENOUGH — GAP REPORTED |
| CrewAI | Anthropic was founded by former OpenAI employees | ANSWERED |
| CrewAI | The flurbotron 9000 was released in 2019 | COULD NOT VERIFY — GAP REPORTED |

The Anthropic test successfully retrieved evidence with a source URL: https://en.wikipedia.org/wiki/Anthropic.

The search tool initially had difficulty handling some responses from DuckDuckGo. I adjusted the tool to accept valid JSON returned with HTTP status 202 and added shorter search-query fallbacks.

## 1. Which framework would I ship, and why?

I would choose **LangGraph** for this fact-checking use case because it provides an explicit and inspectable decision path. Its conditional routing guarantees that when the evidence assessment returns `NOT_ENOUGH`, the program runs the `report_gap` node rather than the answer-writing node.

CrewAI offers more flexible task delegation through a hierarchical manager, but its final decision depends more heavily on the language model following instructions. For a fact-checking product where unsupported answers are a serious concern, LangGraph offers better control over the workflow.

## 2. Did both versions refuse the nonsense claim?

Yes. In the observed tests, both versions refused to verify the claim that the flurbotron 9000 was released in 2019.

**LangGraph output:**

`VERDICT: NOT_ENOUGH`

`ROUTE: GAP REPORTED`

`This claim could not be verified using the available evidence.`

`NEXT SEARCH: flurbotron 9000 reliable source verification`

**CrewAI output:**

`VERDICT: COULD NOT VERIFY`

`The claim that the flurbotron 9000 was released in 2019 could not be verified.`

`NEXT SEARCH: "flurbotron 9000 release date"`

`ROUTE: GAP REPORTED`

CrewAI performed several searches without finding useful results. Its manager ultimately refused to answer instead of inventing a release date.

## 3. Where does the decision live in each framework?

In **LangGraph**, the decision is stored in the graph state as `verdict`. The `choose_next` router selects either `write_answer` or `report_gap` through a conditional edge.

In **CrewAI**, the hierarchical manager coordinates the researcher and writer and decides how to proceed. The final route is inferred from the generated text rather than recorded by a guaranteed conditional graph branch.

For a customer asking how the system prevents answers without sufficient evidence, I could demonstrate LangGraph's explicit routing and the fact that `report_gap` does not generate a factual answer. However, this is not a complete guarantee against hallucinations when evidence is incorrectly assessed as sufficient; additional validation would still be needed.

## 4. Why couldn't report_gap run the NEXT SEARCH?

The graph currently has an edge from `report_gap` directly to `END`, so it terminates after suggesting another search query. To execute that search automatically, it would need a conditional loop from the gap-reporting stage back to `run_search` (or `plan_query`), with the new query stored in the graph state and a maximum retry limit to prevent infinite searching.

## Submitted Files

- `research_langgraph.py`
- `research_crewai.py`
- `search_tools.py` — search compatibility fix
- `outputs/langgraph_real.txt`
- `outputs/langgraph_nonsense.txt`
- `outputs/crewai_real.txt`
- `outputs/crewai_nonsense.txt`
- `README.md`

Both framework implementations use OpenRouter with `openai/gpt-4o-mini`. The `.env` file containing API credentials must remain private and must not be committed.