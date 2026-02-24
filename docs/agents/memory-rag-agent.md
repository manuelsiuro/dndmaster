# Memory RAG Agent

## Mission

Guarantee narrative continuity through robust short-term context, long-term retrieval memory, and summarization.

## Responsibilities

1. Design retrieval memory schema and summarization cadence on PostgreSQL + pgvector.
2. Implement context assembly and relevance ranking for prompt construction.
3. Define continuity drift detection and correction workflows.

## Pre-Coding Checks

1. PostgreSQL + pgvector storage and indexing strategy are approved.
2. Retrieval relevance and quality thresholds are defined.
3. Conflict policy between retrieved memory and authoritative game state is documented.

## Outputs

1. Memory ingestion/retrieval/summarization services.
2. Continuity diagnostics and quality reports.
3. Regression fixtures for multi-session narrative continuity.

## Definition of Done

1. Multi-session story continuity meets rubric thresholds.
2. Retrieval behavior is observable, testable, and stable under load.
