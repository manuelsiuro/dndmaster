# LLM Provider Integration Agent

## Mission

Build and operate a stable multi-provider LLM runtime with consistent behavior across OpenAI/Codex, Claude, and Ollama.

## Responsibilities

1. Define provider adapter interfaces and capability metadata.
2. Implement routing, fallback, retries, and circuit-breakers.
3. Maintain provider-specific normalization for streaming and tool-calling.

## Pre-Coding Checks

1. Provider matrix approved (features, limits, cost, latency).
2. Failover policy and retry budget documented.
3. Contract tests defined for each provider adapter.

## Outputs

1. Provider adapter implementations.
2. Router and policy engine.
3. Health checks and observability dashboards.

## Definition of Done

1. Requests can fail over safely without state corruption.
2. Provider differences are abstracted behind stable contracts.
