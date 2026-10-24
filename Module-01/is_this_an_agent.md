# Module 1 — Is This an Agent?

## Understanding Single LLM Calls, Workflows, and Autonomous Agents

The main difference between an LLM call, a workflow, and an autonomous agent is who decides the next action. In an autonomous agent, the model decides what to do next based on the goal and the information collected during execution.

### (a) Support Email Reply Generator

**Classification: Single LLM Call — Not an Agent**

A program that receives a support email and generates a drafted reply through one LLM call is not an agent because it only produces a response without choosing tools or deciding further actions.

### (b) Research Assistant

**Classification: Autonomous Agent**

A system that repeatedly searches for information, reads sources, and decides whether enough information has been collected to write a summary is an autonomous agent because it dynamically chooses its next actions based on previous observations.

### (c) Nightly Sales Summary

**Classification: Workflow — Not an Agent**

A scheduled program that fetches sales data, asks an LLM to summarize it, and automatically posts the summary to a channel is a workflow because the execution steps are predetermined rather than selected dynamically by the model.

## Conclusion

An autonomous agent differs from a workflow because the model controls the next action during execution. A single LLM call generates a response, while a workflow follows predefined steps. Agents provide greater flexibility but require guardrails, such as step limits and loop detection, to remain reliable.