
"""
Module 1 - Autonomous Multi-Tool AI Agent

Features:
1. Safe calculator
2. Country capital lookup
3. Autonomous agent loop
4. Maximum step limit
5. LLM call and token tracking
6. Bad-JSON retry
7. Loop detection
8. Offline robustness tests

No agent frameworks are used.
"""

import os
import re
import json
import ast
import operator
from dotenv import load_dotenv
from openai import OpenAI


# ========================================
# Configuration
# ========================================

MAX_STEPS = 6
MODEL = "openai/gpt-4o-mini"
BASE_URL = "https://openrouter.ai/api/v1"

load_dotenv()

client = None


def get_client():
    global client

    if client is None:
        api_key = os.getenv("OPENROUTER_API_KEY")

        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is missing from .env"
            )

        client = OpenAI(
            api_key=api_key,
            base_url=BASE_URL
        )

    return client


# ========================================
# Tool 1: Safe Calculator
# ========================================

def calculator(expr: str) -> str:
    """Safely evaluate basic arithmetic."""

    operations = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }

    def evaluate(node):

        if isinstance(node, ast.Constant):
            if type(node.value) in (int, float):
                return node.value

        if isinstance(node, ast.BinOp):
            if type(node.op) in operations:
                left = evaluate(node.left)
                right = evaluate(node.right)

                return operations[type(node.op)](
                    left, right
                )

        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, (ast.UAdd, ast.USub)):
                value = evaluate(node.operand)

                if isinstance(node.op, ast.UAdd):
                    return value

                return -value

        raise ValueError("Unsupported expression")

    try:
        if not isinstance(expr, str):
            return "Error: invalid expression"

        if len(expr) > 100:
            return "Error: expression too long"

        if not re.fullmatch(r"[0-9+\-*/(). ]+", expr):
            return "Error: invalid characters"

        tree = ast.parse(expr, mode="eval")
        result = evaluate(tree.body)

        if not isinstance(result, (int, float)):
            return "Error: invalid result"

        if abs(result) > 10**15:
            return "Error: result too large"

        return str(result)

    except (
        ValueError,
        SyntaxError,
        ZeroDivisionError,
        OverflowError,
        RecursionError,
        TypeError
    ):
        return "Error: invalid arithmetic expression"


# ========================================
# Tool 2: Lookup
# ========================================

CAPITALS = {
    "france": "Paris",
    "germany": "Berlin",
    "italy": "Rome",
    "spain": "Madrid",
    "japan": "Tokyo",
    "canada": "Ottawa",
    "egypt": "Cairo",
    "jordan": "Amman",
    "turkey": "Ankara",
    "brazil": "Brasilia",
}


def lookup(country: str) -> str:
    """Look up a country's capital."""

    if not isinstance(country, str):
        return "Error: invalid country"

    key = country.strip().lower()

    return CAPITALS.get(
        key,
        f"Country not found: {key}"
    )


# ========================================
# System Prompt
# ========================================

SYSTEM_PROMPT = """
You are an autonomous AI agent.

Solve user questions step by step.

You can choose among three actions:

1. calculator - for arithmetic.
2. lookup - to find a country's capital.
3. final_answer - to finish the task.

Rules:
- Never calculate arithmetic yourself.
- Use calculator whenever arithmetic is needed.
- Use lookup when a country's capital is needed.
- Do not invent tool results.
- Use tool observations to decide your next step.
- Never repeat an identical tool action unnecessarily.
- Choose one action per response.
- Respond using ONLY valid JSON.
- Do not include markdown or explanations outside JSON.

Valid actions:

{"action": "calculator", "args": {"expr": "12*12"}}

{"action": "lookup", "args": {"country": "France"}}

{"action": "final_answer", "args": {"text": "Answer"}}

For multi-tool questions, choose the next
action based on the information still needed.
"""


# ========================================
# Model Call
# ========================================

def call_model(messages: list):
    """Call OpenRouter and return text and token counts."""

    response = get_client().chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0
    )

    content = response.choices[0].message.content or ""

    prompt_tokens = 0
    completion_tokens = 0

    if response.usage:
        prompt_tokens = response.usage.prompt_tokens or 0
        completion_tokens = (
            response.usage.completion_tokens or 0
        )

    return content, prompt_tokens, completion_tokens


# ========================================
# JSON Parser
# ========================================

def parse_action(raw: str) -> dict:
    """Parse and validate a model action."""

    cleaned = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        raw.strip(),
        flags=re.IGNORECASE
    ).strip()

    action = json.loads(cleaned)

    if not isinstance(action, dict):
        raise ValueError("Expected a JSON object")

    name = action.get("action")
    args = action.get("args")

    if name not in (
        "calculator",
        "lookup",
        "final_answer"
    ):
        raise ValueError("Unknown action")

    if not isinstance(args, dict):
        raise ValueError("Invalid action arguments")

    required_field = {
        "calculator": "expr",
        "lookup": "country",
        "final_answer": "text",
    }[name]

    if not isinstance(args.get(required_field), str):
        raise ValueError(
            f"Missing or invalid {required_field}"
        )

    return action


# ========================================
# Autonomous Agent Loop
# ========================================

def run_agent(question: str, model_caller=None) -> str:
    """
    Run the agent with:
    - a step limit
    - token tracking
    - one Bad-JSON retry
    - repeated-action detection

    model_caller allows offline testing.
    """

    if model_caller is None:
        model_caller = call_model

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    llm_calls = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    previous_action = None

    final_result = "No final answer (budget exhausted)."

    def request_model():
        nonlocal llm_calls
        nonlocal total_prompt_tokens
        nonlocal total_completion_tokens

        raw, prompt_tokens, completion_tokens = (
            model_caller(messages)
        )

        llm_calls += 1
        total_prompt_tokens += prompt_tokens
        total_completion_tokens += completion_tokens

        return raw

    for step in range(1, MAX_STEPS + 1):

        print(f"\n=== STEP {step}/{MAX_STEPS} ===")

        # --------------------------------
        # Request the next action
        # --------------------------------

        try:
            raw = request_model()

        except Exception as error:
            final_result = f"Model error: {error}"
            print(final_result)
            break

        print("AI RESPONSE:", raw)

        # --------------------------------
        # Guard 1: Bad-JSON Retry
        # --------------------------------

        try:
            action = parse_action(raw)

        except (json.JSONDecodeError, ValueError):

            print("GUARD: Invalid JSON/action detected.")
            print("RETRY: Asking AI to correct its response.")

            messages.append({
                "role": "assistant",
                "content": raw
            })

            messages.append({
                "role": "user",
                "content": (
                    "Your previous action was invalid. "
                    "Respond with ONLY one valid JSON object "
                    "containing a supported action and its args. "
                    "No markdown. No explanations."
                )
            })

            try:
                raw = request_model()
                print("RETRY RESPONSE:", raw)

                action = parse_action(raw)

                # A successful retry replaces the invalid response.
                messages = messages[:-2]

            except (
                json.JSONDecodeError,
                ValueError
            ):
                final_result = (
                    "Stopped: invalid JSON after one retry."
                )
                print(final_result)
                break

            except Exception as error:
                final_result = f"Retry model error: {error}"
                print(final_result)
                break

        action_name = action["action"]
        args = action["args"]

        # --------------------------------
        # Guard 2: Loop Detection
        # --------------------------------

        if action_name in ("calculator", "lookup"):

            current_action = json.dumps(
                action,
                sort_keys=True
            )

            if current_action == previous_action:

                final_result = (
                    "Stopped: repeated identical action detected."
                )

                print("GUARD: LOOP DETECTED")
                print(final_result)
                break

            previous_action = current_action

        else:
            previous_action = None

        # Store the AI decision
        messages.append({
            "role": "assistant",
            "content": raw
        })

        # --------------------------------
        # Action: Calculator
        # --------------------------------

        if action_name == "calculator":

            expression = args["expr"]
            result = calculator(expression)

            print("TOOL: calculator")
            print("EXPRESSION:", expression)
            print("OBSERVATION:", result)

            messages.append({
                "role": "user",
                "content": (
                    f"Calculator observation: "
                    f"{expression} = {result}. "
                    "Decide your next action."
                )
            })

        # --------------------------------
        # Action: Lookup
        # --------------------------------

        elif action_name == "lookup":

            country = args["country"]
            result = lookup(country)

            print("TOOL: lookup")
            print("COUNTRY:", country)
            print("OBSERVATION:", result)

            messages.append({
                "role": "user",
                "content": (
                    f"Lookup observation for {country}: "
                    f"{result}. "
                    "Decide your next action."
                )
            })

        # --------------------------------
        # Action: Final Answer
        # --------------------------------

        elif action_name == "final_answer":

            final_result = args["text"]

            print("\nFINAL ANSWER:", final_result)
            break

    else:
        print("\nSTOPPED: Step budget exhausted.")

    # ====================================
    # Usage Summary
    # ====================================

    print("\n=== AGENT USAGE SUMMARY ===")
    print("LLM CALLS:", llm_calls)
    print("PROMPT TOKENS:", total_prompt_tokens)
    print("COMPLETION TOKENS:", total_completion_tokens)
    print(
        "TOTAL TOKENS:",
        total_prompt_tokens + total_completion_tokens
    )

    return final_result


# ========================================
# Offline Robustness Tests
# ========================================

def fake_model(responses):
    """Return predetermined responses without API calls."""

    iterator = iter(responses)

    def caller(messages):
        raw = next(iterator)
        return raw, 10, 10

    return caller


def test_bad_json_retry():
    print("\n=== TEST: BAD-JSON RETRY ===")

    responses = [
        "This is not valid JSON",
        '{"action":"final_answer","args":{"text":"Recovered!"}}'
    ]

    result = run_agent(
        "Test invalid JSON recovery",
        model_caller=fake_model(responses)
    )

    assert result == "Recovered!"
    print("TEST PASSED: Bad-JSON retry works.")


def test_loop_detection():
    print("\n=== TEST: LOOP DETECTION ===")

    repeated = (
        '{"action":"lookup","args":{"country":"France"}}'
    )

    responses = [
        repeated,
        repeated
    ]

    result = run_agent(
        "Test repeated action detection",
        model_caller=fake_model(responses)
    )

    assert "repeated identical action" in result
    print("TEST PASSED: Loop detection works.")


# ========================================
# Main
# ========================================

if __name__ == "__main__":

    print("=== MODULE 1: ROBUST MULTI-TOOL AGENT ===")

    question = (
        "What is the capital of France, "
        "and what is 12 * 12?"
    )

    print("\nQUESTION:", question)

    result = run_agent(question)

    print("\nRESULT:", result)

    # Offline tests: no additional API requests
    test_bad_json_retry()
    test_loop_detection()

    print("\n=== ALL TESTS FINISHED ===")
