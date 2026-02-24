# DragonWeaver Implementation Plan

Source: [`docs/draft.md`](./draft.md)  
Date: 2026-02-24  
Status: Updated with confirmed requirements

## 1) Locked Decisions

1. Backend: `FastAPI`
2. Frontend: `React + TypeScript`
3. LLM runtime: multi-provider from day one (`OpenAI/Codex`, `Claude`, `Ollama`)
4. `Ollama` models: selectable from models available on each device (runtime discovery)
5. MVP target: multiplayer-first, 4 players
6. Audio: mandatory (players speak to DM and receive voice response)
7. Voice provider strategy: `hybrid` (local/open-source + managed cloud)
8. Languages: mandatory i18n with English default and French at launch
9. Settings UX: mandatory settings screen to configure all provider/model/audio/language options
10. Quality priorities: deep narrative quality + polished map quality are release gates
11. Cost strategy: avoid unnecessary paid usage with policy-based routing, without failing quality gates

## 2) Mandatory Pre-Coding Checks (Go/No-Go Gates)

All gates must pass before feature coding.

### Gate A: Product Scope (MVP)

1. Freeze MVP features:
   - 4-player lobby and session flow
   - Shared text and voice interaction with AI DM
   - Persistent campaign state
   - English and French UI + gameplay language support
   - Full settings screen for provider/audio/language/model configuration
2. Define out-of-scope items clearly (only if explicitly agreed).
3. Confirm acceptance criteria for first playable session.

### Gate B: Architecture ADR Pack

1. Approve FastAPI module boundaries:
   - API/Game service
   - Rule engine
   - AI orchestration
   - Voice pipeline
   - Settings/config service
   - Persistence
2. Approve React architecture and client-state strategy.
3. Approve transport split:
   - HTTP for CRUD/config/settings
   - WebSocket for live multiplayer, narration, and voice events
4. Approve backend authority rule:
   - LLM proposes, backend validates and commits.

### Gate C: Multi-Provider LLM + Cost Routing

1. Define provider adapter interface and capability matrix.
2. Define routing policy tiers:
   - Local-first for eligible turns/tasks
   - Remote fallback for quality-critical turns
3. Define failover, retry budget, and circuit-breakers.
4. Define Codex adapter strategy with minimal additional paid usage.

### Gate D: Ollama Device Model Discovery

1. Implement runtime model discovery on host device.
2. Define model qualification checks:
   - Tool-calling compatibility
   - Token/context capacity
   - Latency threshold
3. Define fallback when no qualified local model is available.

### Gate E: Narrative Quality Framework (Mandatory)

1. Define deep-storyline rubric:
   - Multi-session coherence
   - NPC memory continuity
   - Consequence tracking
   - Emotional and thematic consistency
2. Add narrative regression harness with golden transcripts.
3. Block release if rubric threshold is not met.

### Gate F: Map Polish + Algorithm Baseline (Mandatory)

1. Select proven algorithms and integration approach:
   - Pathfinding (`A*` baseline, `JPS` optional optimization)
   - Line-of-sight/fog-of-war (shadowcasting or equivalent)
   - Movement range and collision validation
2. Define map polish checklist:
   - Input smoothness
   - Grid clarity
   - Token readability
   - Responsive behavior
3. Define performance targets for target map/token scale.

### Gate G: Audio/Speech Architecture (Mandatory)

1. Define STT and TTS provider abstraction for hybrid runtime.
2. Define provider selection behavior from settings:
   - Auto mode
   - Force local
   - Force cloud
3. Define live voice session protocol:
   - Push-to-talk or continuous mode rules
   - Turn-taking and interruption behavior
4. Define audio fallback behavior and error UX.
5. Define latency targets for speech round trip.

### Gate H: Multilingual Framework (Mandatory)

1. Define i18n/l10n architecture:
   - Language resources
   - Runtime language switching
2. Define narrative language policy:
   - English default
   - French parity targets for launch
3. Define multilingual QA coverage:
   - UI strings
   - Voice paths
   - Narrative quality checks per language

### Gate I: Settings and Configuration Control Plane (Mandatory)

1. Define settings schema and validation rules for:
   - LLM provider and model selection
   - Ollama discovered-model selection
   - Audio provider and voice settings
   - Language preferences
   - Cost/quality routing mode
2. Define settings scope:
   - Global user defaults
   - Campaign/session overrides
3. Define secure handling of provider credentials/tokens.
4. Define UX safety checks to prevent invalid configurations.

### Gate J: Data + Security Baseline

1. Approve schema v1:
   - users, parties, campaigns, characters, world_state, chat_history, events, settings
2. Define migration and rollback workflow.
3. Approve AuthN/AuthZ for multiplayer.
4. Define retention/deletion policy for chat, voice transcripts, and campaign memory.

### Gate K: Test + CI Release Gates

1. Define test layers:
   - Unit (rules, validators, settings schema)
   - Integration (provider routing, tool-calls, audio, i18n, settings APIs)
   - E2E (4-player session: text + voice + map + persistence + settings changes)
2. Define deterministic replay fixtures.
3. Define release blockers:
   - Narrative gate
   - Map gate
   - Audio gate
   - Multiplayer sync gate
   - Multilingual gate
   - Settings gate

## 3) Specialized Agents

See [`docs/agents/README.md`](./agents/README.md).

Execution domains:
1. Product Delivery Agent
2. Architecture Agent
3. Rules Engine Agent
4. AI Orchestration Agent
5. LLM Provider Integration Agent
6. Narrative Design Agent
7. Frontend VTT Agent
8. Map Systems Agent
9. Audio Speech Agent
10. Localization Agent
11. Settings Experience Agent
12. Data Platform Agent
13. QA Automation Agent
14. DevOps Security Agent

## 4) Phase-by-Phase Plan

## Phase 0: Foundations and Contracts (1-2 weeks)

Primary agents:
1. Architecture Agent
2. LLM Provider Integration Agent
3. Audio Speech Agent
4. Localization Agent
5. Settings Experience Agent
6. DevOps Security Agent

Tasks:
1. Complete Gates A-K approvals.
2. Implement provider abstraction contracts and mocks.
3. Implement audio provider contract and local test harness.
4. Implement i18n framework skeleton (EN + FR).
5. Define settings schema and build settings API skeleton.
6. Build prompt playground for story/tool/voice turn validation.

Exit criteria:
1. Gate pack approved.
2. CI baseline green.
3. Provider, audio, i18n, and settings contract tests pass.

## Phase 1: Multiplayer MVP with Voice + EN/FR + Settings (4-6 weeks)

Primary agents:
1. AI Orchestration Agent
2. Audio Speech Agent
3. Localization Agent
4. Settings Experience Agent
5. Data Platform Agent
6. QA Automation Agent

Tasks:
1. 4-player lobby, join, reconnect, and session authority.
2. Shared narrative stream and synchronized events.
3. Voice input (player to DM) and voice output (DM to players).
4. English/French support across UI and core narrative flow.
5. Full settings screen:
   - Provider/model selection
   - Audio mode/provider/voice controls
   - Language switching
   - Cost/quality mode controls
6. Persistent campaign state and settings persistence.

Exit criteria:
1. Stable 4-player session.
2. Voice round trip works end-to-end.
3. EN and FR flows pass functional and quality checks.
4. Settings changes apply safely in-session or at next-turn boundaries.

## Phase 2: Rule Authority + Multi-Provider Runtime (4-6 weeks)

Primary agents:
1. Rules Engine Agent
2. AI Orchestration Agent
3. LLM Provider Integration Agent
4. Settings Experience Agent
5. QA Automation Agent

Tasks:
1. Authoritative action-resolution pipeline.
2. Tool-calling contracts for gameplay actions.
3. Routing policy implementation for quality/cost balance.
4. Connect settings controls to runtime routing and fallback behavior.
5. Replay framework for deterministic validation.

Exit criteria:
1. LLM cannot mutate state directly.
2. Failover remains stable across providers.
3. Replay suite passes determinism criteria.
4. Runtime honors settings constraints consistently.

## Phase 3: Polished Map System (4-7 weeks)

Primary agents:
1. Frontend VTT Agent
2. Map Systems Agent
3. Rules Engine Agent
4. QA Automation Agent

Tasks:
1. Clean tactical map UX and token controls.
2. Integrate proven algorithms for pathing/LOS/fog/collision.
3. Synchronize map actions reliably across 4 players.
4. Execute polish and performance pass.

Exit criteria:
1. Map quality gate passes.
2. Algorithm correctness suite passes.
3. Multiplayer map sync is stable under reconnect/load.

## Phase 4: Hardening and Launch Readiness (2-4 weeks)

Primary agents:
1. QA Automation Agent
2. DevOps Security Agent
3. Product Delivery Agent
4. Narrative Design Agent

Tasks:
1. Load, chaos, and failover tests.
2. Security hardening and abuse controls.
3. Final narrative/map/audio/multilingual/settings certification.

Exit criteria:
1. All mandatory quality gates pass.
2. Release checklist is signed off.

## 5) Mandatory Release Quality Gates

1. Narrative Gate: deep storyline rubric threshold achieved.
2. Map Gate: polish checklist + algorithm correctness + performance pass.
3. Audio Gate: bidirectional voice path reliability and latency pass.
4. Multilingual Gate: EN default + FR parity checks pass.
5. Multiplayer Gate: 4-player stability, sync, and reconnect pass.
6. Settings Gate: all configuration paths validated and safe.

## 6) Immediate Sprint 0 Backlog

1. ADR-001: FastAPI + React architecture baseline.
2. ADR-002: Multi-provider adapter and routing policy.
3. ADR-003: Hybrid audio pipeline and voice-turn protocol.
4. ADR-004: i18n architecture for EN/FR.
5. ADR-005: settings schema, overrides, and configuration safety rules.
6. Schema v1 migrations with multiplayer, voice-event, and settings support.
7. Narrative rubric v1 + map polish checklist v1 + multilingual QA matrix v1 + settings QA matrix v1.
