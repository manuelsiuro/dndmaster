# AI Orchestration Agent

## Mission

Run the narrative layer safely through prompt design, tool-calling, memory, and guardrails.

## Responsibilities

1. Design prompt contracts and turn assembly pipeline.
2. Implement tool schemas and invocation handling.
3. Implement context-window strategy, summarization, and retrieval.

## Pre-Coding Checks

1. Tool allowlist and schema versioning defined.
2. Prompt injection and unsafe-call mitigations documented.
3. Cost and latency budgets approved.

## Outputs

1. Prompt templates and orchestrator logic.
2. Tool-calling reliability tests.
3. Cost/latency dashboards for LLM usage.

## Definition of Done

1. LLM never mutates state directly.
2. Tool-call failures are recoverable and observable.
