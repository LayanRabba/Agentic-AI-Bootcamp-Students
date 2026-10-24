
import os
import time
from dotenv import load_dotenv
from openai import OpenAI

# ========================================
# Setup: OpenRouter API
# ========================================

load_dotenv()

client = OpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api/v1"
)

MODEL = "openai/gpt-4o-mini"


# ========================================
# Exercise 1: Tokens In, Tokens Out
# ========================================

print("\n=== Exercise 1: Tokens ===")

response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {
            "role": "user",
            "content": "Explain what a token is in one sentence."
        }
    ]
)

print("ANSWER:", response.choices[0].message.content)
print("PROMPT TOKENS:", response.usage.prompt_tokens)
print("COMPLETION TOKENS:", response.usage.completion_tokens)
print("TOTAL TOKENS:", response.usage.total_tokens)

print("\nEXERCISE 1 FINISHED")


# ========================================
# Exercise 2: Statelessness
# ========================================

print("\n=== Exercise 2: Statelessness ===")

# Step 1: Tell the model your favorite animal
client.chat.completions.create(
    model=MODEL,
    messages=[
        {
            "role": "user",
            "content": "My favorite animal is the flamingo."
        }
    ]
)

# Step 2: Ask without conversation history
r1 = client.chat.completions.create(
    model=MODEL,
    messages=[
        {
            "role": "user",
            "content": "What is my favorite animal?"
        }
    ]
)

print("\nWITHOUT MEMORY:")
print(r1.choices[0].message.content)

# Step 3: Ask with conversation history
r2 = client.chat.completions.create(
    model=MODEL,
    messages=[
        {
            "role": "user",
            "content": "My favorite animal is the flamingo."
        },
        {
            "role": "assistant",
            "content": "Noted - flamingos!"
        },
        {
            "role": "user",
            "content": "What is my favorite animal?"
        }
    ]
)

print("\nWITH MEMORY:")
print(r2.choices[0].message.content)

print("\nEXERCISE 2 FINISHED")


# ========================================
# Exercise 3: Temperature
# ========================================

print("\n=== Exercise 3: Temperature ===")

prompt = "Invent a name for a coffee shop."

for temperature in (0, 0, 1.2, 1.2):
    response = client.chat.completions.create(
        model=MODEL,
        temperature=temperature,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    print(
        f"Temperature {temperature} -> "
        f"{response.choices[0].message.content}"
    )

print("\nEXERCISE 3 FINISHED")


#
# ========================================
# Exercise 4: Reasoning - Prompt Comparison
# ========================================

print("\n=== Exercise 4: Reasoning Comparison ===")

question = (
    "A shop sells pens at 3 for $2. "
    "I have $10. How many pens can I buy, "
    "and how much change?"
)

prompts = [
    ("WITHOUT STEP-BY-STEP", question),
    ("WITH STEP-BY-STEP", question + " Think step by step.")
]

for label, prompt in prompts:
    print(f"\n=== {label} ===")

    try:
        start = time.perf_counter()

        response = client.chat.completions.create(
            model=MODEL,
            temperature=0,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        elapsed = time.perf_counter() - start

        print("ANSWER:")
        print(response.choices[0].message.content)
        print(f"LATENCY: {elapsed:.2f} seconds")

        if response.usage:
            print("PROMPT TOKENS:", response.usage.prompt_tokens)
            print("COMPLETION TOKENS:", response.usage.completion_tokens)
            print("TOTAL TOKENS:", response.usage.total_tokens)

    except Exception as e:
        print("ERROR:", e)

print("\nEXERCISE 4 FINISHED")
print("\n=== MODULE 00 LAB FINISHED ===")
