# Module 0 — LLM & Reasoning Primer
## Lab Observations

**Model:** `openai/gpt-4o-mini`
**API Provider:** OpenRouter

### Exercise 1 — Tokens In, Tokens Out

- Prompt tokens: 16
- Completion tokens: 39
- Total tokens: 55

**Observation:** The model received 16 input tokens and generated 39 output tokens. The total usage was 55 tokens. The model initially interpreted "token" as a digital asset rather than a unit of text in language processing, demonstrating that ambiguous prompts can lead to responses outside the intended context.

### Exercise 2 — Statelessness

**Without conversation history:** The model could not identify my favorite animal.

**With conversation history:** The model correctly answered "flamingo."

**Observation:** The model did not remember information from the previous API call. Once the conversation history was included in the request, it could use that information to answer correctly. This demonstrates how conversation context enables short-term memory in LLM applications.

### Exercise 3 — Temperature

| Temperature | Generated Coffee Shop Name |
|---|---|
| 0 — Run 1 | Bean There, Brewed That |
| 0 — Run 2 | Bean There, Brewed That |
| 1.2 — Run 1 | Bean & Brews Café |
| 1.2 — Run 2 | Brewed Awakening |

**Observation:** Temperature 0 produced identical results in both runs, while temperature 1.2 produced different names. Lower temperatures generally encourage more consistent outputs, while higher temperatures can increase variation and creativity.

### Exercise 4 — Reasoning Comparison

The original reasoning-model comparison could not be completed because both attempted reasoning-model providers returned HTTP 404 errors.

Following the worksheet's suggested fallback, I compared the same model at temperature 0 with and without an explicit step-by-step instruction.

| Metric | Without Step-by-Step | With Step-by-Step |
|---|---|---|
| Model | GPT-4o-mini | GPT-4o-mini |
| Correct answer | 15 pens, $0 change | 15 pens, $0 change |
| Latency | 4.50 seconds | 5.84 seconds |
| Prompt tokens | 35 | 40 |
| Completion tokens | 369 | 417 |
| Total tokens | 404 | 457 |

**Observation:** Both prompts produced correct answers. The explicit step-by-step instruction generated a longer explanation, increased token usage, and took more time in this test. It did not improve accuracy for this simple arithmetic question.

### Conceptual Questions

**1. What is an LLM?**

A Large Language Model is an AI model trained on large amounts of data to understand and generate text by predicting tokens based on context.

**2. Why is an LLM stateless?**

A standard LLM API call does not automatically remember previous requests. Conversation history must be provided again to maintain context.

**3. Why use temperature=0 for agents?**

Temperature 0 is useful when AI agents need more consistent and predictable outputs, especially for structured tasks and decision-making.

**4. When is a reasoning model worth it?**

A reasoning model can be useful for complex problems requiring multi-step analysis, planning, or difficult logical decisions, particularly when improved accuracy justifies additional latency and cost.

### Conclusion

This lab demonstrated how tokens, context, temperature, and prompting strategies influence LLM behavior. Understanding these concepts is important for developing reliable AI agents.