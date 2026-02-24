# DragonWeaver Implementation Plan

Source: [`docs/draft.md`](./draft.md)  
Date: 2026-02-24  
Status: Expanded after full spec gap analysis and second-screen requirements

Related analysis: [`docs/spec-gap-analysis.md`](./spec-gap-analysis.md)
Tooling research: [`docs/research/map-art-tools.md`](./research/map-art-tools.md)
Timeline UX spec: [`docs/mvp-timeline-ui-spec.md`](./mvp-timeline-ui-spec.md)

## 1) Locked Product Decisions

1. Backend: `FastAPI`
2. Frontend: `React + TypeScript`
3. LLM runtime: multi-provider day one (`OpenAI/Codex`, `Claude`, `Ollama`)
4. Ollama model strategy: runtime discovery, user-selectable from local available models
5. Multiplayer-first MVP: 4 players
6. Audio is mandatory: player voice input + AI DM voice output
7. Voice provider strategy: hybrid (local/open-source + managed cloud)
8. Multilingual is mandatory: English default + French at launch
9. All web UI must be responsive across TV, desktop, tablet, and mobile screens
10. Settings UX is mandatory: full control screen for providers/models/audio/language/cost-quality mode
11. TV presentation mode is mandatory for game master display
12. Mobile companion is mandatory and read-only for players (character sheet, stats, items, spells)
13. Player actions are entered by voice or by GM-provided numeric choices (`1`, `2`, `3`, ...)
14. Mobile session connection must use QR token issued at game start
15. Device policy: single active mobile device per player
16. Game administration is mandatory: operational control plane (no moderation layer)
17. User progression is mandatory: hybrid progression based on story progression + gameplay signals
18. Save system is mandatory: autosave, checkpoints, restore, and recovery
19. Art-heavy presentation is mandatory: high-quality original images, sprites, tokens, and scene art
20. Custom Python scripts for AI image generation are mandatory in the production pipeline
21. Map authoring/generation tool integrations are mandatory for dungeon, room, village, and outdoor content
22. Release quality gates must pass for narrative depth and map polish
23. Cost optimization cannot break core quality gates
24. Character sheet creation is mandatory, polished, and D&D-rules compliant
25. Character creation modes are mandatory: automatic generation, player-dice mode, and GM-TV-dice mode
26. GM multi-story management is mandatory: start new story, continue existing story, and manage different player rosters per story
27. Browser automation is mandatory using MCP Chrome as primary E2E runner (Playwright fallback path required)
28. Player accounts are mandatory so player progression persists across stories/adventures
29. Rules and content policy is strict SRD 5.1 only with explicit CC-BY attribution handling
30. Voice transport baseline is WebRTC first with managed fallback transport
31. Default runtime mode is local-first adaptive routing (Ollama-first, then low-cost compatible cloud fallback)
32. FinOps guardrails are mandatory (budget caps, usage alerts, and safe degrade behavior)
33. Narrative continuity architecture is mandatory (short-term context + long-term retrieval memory + summarization)
34. Account auth for MVP is email+password with secure password policy
35. Narrative memory store baseline is PostgreSQL + pgvector (RAG retrieval for DM continuity)
36. All voice interactions must be recorded, transcribed, persisted, and displayed in a polished narrative timeline UI
37. Chat/timeline retention policy is lifecycle-based: retained while the game/campaign exists (including voice recordings/transcripts)
38. Recording consent is mandatory before first captured voice interaction in a session
39. Voice recording storage must enforce quota/alert policies to keep lifecycle retention operationally safe
40. Email verification is not required for gameplay access in MVP (email+password remains mandatory)
41. Voice export policy for MVP is in-app playback only (no downloadable/exportable voice files)
42. Voice storage quota policy is tiered by account tier/campaign class

## 2) Mandatory Pre-Coding Gates (Go/No-Go)

All gates must pass before feature coding starts.

### Gate A: Product Scope and Acceptance Criteria

1. Freeze MVP scope:
   - 4-player multiplayer sessions
   - Text + voice interaction
   - EN/FR support
   - Responsive UI across TV/desktop/tablet/mobile
   - Settings screen
   - TV GM mode
   - Read-only mobile companion with player data
   - QR-based join flow with game-start token issuance
   - Voice or GM-choice-based action input model
   - Polished D&D-compliant character creation and sheet workflow
   - Character creation modes (automatic/player dice/GM TV dice)
   - Story portfolio flow (start new story or continue existing story)
   - Story-specific saves and player roster assignment
   - Session-zero onboarding flow for first-time hosts/players
   - Unified polished interaction timeline (GM questions, player actions, choices, and voice recordings/transcripts)
   - Art asset pipeline v1 with generated/curated core asset packs
   - External map tool import pipeline v1
   - Progression v1
   - Save/restore v1
   - Admin v1
2. Define explicit out-of-scope items.
3. Define acceptance tests for first complete session.
4. Define initial quantitative baselines for launch certification:
   - API read/write p95 latency <= 300 ms
   - timeline event fanout p95 <= 250 ms after server commit
   - QR join success >= 99.0% within 10 seconds on supported networks

### Gate B: Core Architecture ADR Pack

1. Approve FastAPI service boundaries:
   - API/Game
   - Rule engine
   - AI orchestration
   - Voice pipeline
   - Settings/config service
   - Device pairing service
   - Character creation/validation service
   - Story portfolio service
   - Art generation pipeline
   - Map import/conversion service
   - Admin service
   - Persistence
2. Approve React app boundaries:
   - TV display app mode
   - Mobile companion app mode
   - Character creation/sheet app mode
   - Story portfolio hub mode
   - Admin/settings mode
3. Approve responsive design baseline:
   - Breakpoints and layout rules for TV/desktop/tablet/mobile
   - Touch targets and readability requirements for companion screens
4. Approve transport split:
   - HTTP for CRUD/admin/config/pairing bootstrap
   - WebSocket for live game/voice/device sync events
5. Approve authority model:
   - LLM proposes, backend validates and commits.

### Gate C: Multi-Provider LLM + Cost Routing

1. Define provider adapter contracts and capability matrix.
2. Define routing modes:
   - local-first
   - balanced
   - quality-first
3. Define fallback/retry/circuit-breaker policy.
4. Define Codex usage strategy with minimal unnecessary paid usage.
5. Define default runtime profile:
   - local-first adaptive mode as default
   - Ollama-first execution with automatic cloud fallback when quality/latency/tooling thresholds fail
6. Define budget guardrails:
   - per-session and daily spend caps
   - hard-stop/degrade policy when caps are hit
   - usage alerts for host/admin

### Gate D: Ollama Model Discovery and Qualification

1. Implement local model discovery.
2. Define qualification tests:
   - tool-calling support
   - context capacity
   - latency threshold
3. Define automatic fallback for unqualified local models.

### Gate E: Narrative Quality Framework (Mandatory)

1. Define narrative rubric:
   - coherence
   - memory continuity
   - consequence consistency
   - emotional/thematic depth
2. Define regression harness with golden story sessions.
3. Make rubric threshold a release blocker.

### Gate F: Map Quality + Algorithm Framework (Mandatory)

1. Define algorithm baseline:
   - pathfinding (`A*`, optional `JPS`)
   - LOS/fog-of-war
   - movement/collision validation
2. Define polish checklist:
   - smooth interactions
   - grid/token readability
   - responsive behavior
3. Define performance targets.

### Gate G: Audio/Speech Architecture (Mandatory)

1. Define STT/TTS abstraction for hybrid provider runtime.
2. Define voice modes and interruption rules.
3. Define fallback behavior and error UX.
4. Define speech round-trip latency targets.
5. Define media transport baseline:
   - WebRTC primary transport with STUN/TURN and reconnect strategy
   - fallback transport path and downgrade UX for unsupported/blocked networks
6. Define multiplayer voice controls:
   - speaker attribution
   - noise suppression/VAD policy
   - interruption and arbitration policy for overlapping speech
7. Define transcript and conversation-log requirements:
   - all voice turns transcribed and persisted
   - original voice clip persistence and playback reference policy
   - in-app playback-only policy for MVP (no downloadable audio export)
   - voice turns merged into canonical interaction timeline with text events
   - clear speaker/action metadata for GM prompts, player actions, and numeric choices
8. Define recording consent workflow:
   - explicit per-player consent before first voice capture in session
   - visible recording indicator while capture is active
   - consent audit event persisted for compliance traceability
9. Define initial audio service-level targets:
   - STT first partial transcript <= 1200 ms p95 after speech start
   - finalized transcript <= 2500 ms p95 after speech end
   - TTS first audible byte <= 1500 ms p95 after response generation starts

### Gate H: Multilingual Framework (Mandatory)

1. Define i18n architecture and runtime switching.
2. Define EN/FR parity requirements.
3. Define multilingual QA matrix for UI + narrative + voice.

### Gate I: Settings and Configuration Control Plane (Mandatory)

1. Define settings schema for:
   - LLM providers/models
   - audio providers/voices
   - language defaults
   - routing mode
   - TV/mobile UX options
2. Define scope:
   - user defaults
   - campaign overrides
3. Define validation rules and safe fallbacks.
4. Define secure secret/token handling.

### Gate J: Second-Screen Pairing and Device Security (Mandatory)

1. Define QR join protocol with token issuance only at game start.
2. Define token security:
   - default expiration: 120 seconds
   - one-time use
   - replay protection
   - rate limiting
   - host-controlled token regeneration on expiry
3. Define single-active-device policy per player, replacement behavior, and revocation flows.
4. Define data visibility rules per device role.
5. Define second-screen reliability baselines:
   - token issuance success >= 99.9%
   - join success >= 99.0% within 10 seconds
   - device replacement completion <= 10 seconds p95

### Gate K: Game Administration (Mandatory)

1. Define admin RBAC (owner/admin/support).
2. Define admin actions:
   - provider policies and limits
   - feature flags
   - session controls (pause/lock/terminate)
   - device/session revoke
   - host handover controls
   - campaign lifecycle controls (archive/fork/ownership transfer)
3. Define audit logging and action traceability.
4. Define incident playbooks and escalation paths.

### Gate L: User Progression System (Mandatory)

1. Define hybrid progression model:
   - story milestones as primary progression driver
   - gameplay XP signals as secondary progression input
2. Define progression entities:
   - account progression
   - character progression
   - achievements/unlocks
3. Define anti-exploit rules and balancing methodology.
4. Define progression transparency in UI.

### Gate M: Save/Restore and Recovery (Mandatory)

1. Define save model:
   - autosave cadence
   - manual saves
   - checkpoints
2. Define restore model:
   - dry-run validation
   - host-only restore permission
   - host reassignment flow before restore when host changes
   - rollback safeguards
3. Define reliability objectives (RPO/RTO).
4. Define export/import and backup policy:
   - include timeline events, transcripts, and voice recording references
5. Set initial recovery targets:
   - RPO <= 60 seconds for active campaign state
   - RTO <= 5 minutes for campaign restore readiness

### Gate N: Data + Security Baseline

1. Approve schema v1:
   - users, auth_identities, auth_credentials, auth_sessions, parties, campaigns, characters, world_state, chat_history, events, settings
   - stories, story_rosters, story_sessions
   - progression, achievements, save_slots, save_snapshots, restore_events, admin_audit_log
   - character_creation_events, character_creation_rolls
   - join_tokens, player_devices, device_sessions
   - art_assets, art_generation_jobs, map_import_jobs
   - narrative_memory_chunks, narrative_summaries, retrieval_audit_events
   - voice_consent_records, voice_recordings, transcript_segments
   - interaction_timeline_events
   - enforce one active `device_session` per player per campaign
2. Define migration and rollback workflows.
3. Approve AuthN/AuthZ and session security.
4. Define retention/deletion policy for chat, voice transcripts, and player data:
   - conversation history retained for full campaign/game lifecycle
   - voice recordings retained for full campaign/game lifecycle
   - deletion occurs only on explicit campaign/game deletion or account/legal erase flow
5. Define credential and data-protection baseline:
   - password hashing with Argon2id (or stronger approved equivalent)
   - login, reset, and token endpoints protected by abuse/rate-limit controls
   - encryption in transit (TLS) and at rest for database/object storage

### Gate O: Test + CI Release Gates

1. Define test levels:
   - unit (rules, settings, progression formulas, character-validation rules, pairing token validators, identity/session validators, memory retrieval ranking rules, SRD scope validators, finops budget policy rules)
   - integration (providers, audio, i18n, saves, character/story APIs, admin APIs, pairing/session APIs, art/map pipelines, account/auth APIs, memory services, finops controls, transcript/timeline APIs)
   - browser automation (MCP Chrome primary runner for critical-path scenarios)
   - visual regression (TV/desktop/tablet/mobile snapshots and critical UI states)
   - E2E (4-player full session with TV + mobile QR join + voice + settings + account identity + character creation + story selection + memory continuity + progression + save/restore + imported maps + generated assets + transcript timeline + budget-guardrail behavior)
2. Define deterministic replay fixtures.
3. Define release blockers:
   - narrative gate
   - map gate
   - audio gate
   - art quality gate
   - asset licensing gate
   - multilingual gate
   - responsive-ui gate
   - accessibility gate
   - multiplayer gate
   - second-screen gate
   - settings gate
   - browser-automation gate
   - progression gate
   - character-sheet gate
   - story-portfolio gate
   - save/recovery gate
   - administration gate
   - security gate
   - observability gate
   - performance gate
   - identity gate
   - memory gate
   - srd compliance gate
   - finops gate
   - interaction timeline gate
   - recording consent gate
   - data lifecycle gate

### Gate P: Art Asset Pipeline and Style Governance (Mandatory)

1. Define art direction bible:
   - visual themes
   - palette and lighting
   - character/token readability standards
2. Define Python generation workflow:
   - txt2img/img2img/inpainting scripts
   - ControlNet and LoRA usage policy
   - deterministic seed and metadata capture
3. Define asset QA:
   - quality rubric
   - style consistency checks
   - human review workflow
4. Define legal/IP constraints:
   - original content policy
   - no copyrighted/trademarked style copying
   - source/license tracking for imported assets
5. Define asset delivery optimization:
   - sprite atlases and texture packing policy
   - compression and format strategy (webp/png/fallback)
   - cache busting, CDN strategy, and runtime fallback assets

### Gate Q: External Map Tool Integration (Mandatory)

1. Select tool stack by map type:
   - dungeon/room
   - village/city
   - outdoor/world
2. Define supported import formats and conversion strategy.
3. Define map metadata mapping:
   - grid
   - walls/doors/lights
   - regions/spawns/encounters
4. Define compatibility and performance acceptance tests.
5. Define per-tool commercial licensing and ToS compatibility checklist.

### Gate R: AAA Engineering and Delivery Excellence (Mandatory)

1. Define security baseline:
   - threat modeling for core flows (auth, pairing, save/restore, admin)
   - SAST/DAST and dependency vulnerability scanning in CI
   - SBOM generation and secret scanning policy
2. Define reliability and observability baseline:
   - SLOs and error budgets (API, WebSocket, voice, map sync, save/restore)
   - OpenTelemetry traces + structured logs + metrics dashboards
   - on-call alert thresholds and runbooks
3. Define performance baseline:
   - backend latency budgets
   - frontend frame-time/FPS and interaction latency budgets
   - load/soak test scenarios and target concurrency
4. Define release management baseline:
   - feature flags for risky features
   - staged rollout/canary strategy
   - rollback and database migration rollback procedures
5. Define accessibility and UX quality baseline:
   - WCAG 2.2 AA target
   - keyboard navigation and captions/transcripts support
   - localization-aware responsive QA on all target form factors

### Gate S: Character Creation and Sheet Compliance (Mandatory)

1. Define D&D-compliant character schema and validation rules:
   - ability scores, modifiers, proficiency logic
   - class/race/background constraints
   - spells, equipment, and inventory rule checks
2. Define character creation modes:
   - automatic generation mode
   - player-dice mode
   - GM-TV-dice mode
3. Define roll authority and auditability for creation:
   - who rolled
   - roll source/device
   - roll result trace
4. Define polished character sheet UX standards:
   - readability and information hierarchy
   - fast editing and validation feedback
   - responsive behavior across all target screens

### Gate T: Story Portfolio and Multi-Campaign Continuity (Mandatory)

1. Define story portfolio model:
   - multiple stories per GM account
   - story metadata, status, and chronology
2. Define flow contracts:
   - start new story
   - continue existing story
3. Define player roster assignment per story:
   - different player groups per story
   - roster snapshoting and history
4. Define save isolation and continuity:
   - story-scoped saves/checkpoints
   - no cross-story state leakage

### Gate U: Browser Automation and Bug-Fix Loop (Mandatory)

1. Define MCP Chrome automation strategy:
   - critical-path scenario coverage
   - deterministic test data and environment setup
   - artifact capture (screenshots, logs, traces)
2. Define CI orchestration:
   - smoke suite on pull requests
   - full regression on release candidates
3. Define fallback runner strategy:
   - Playwright suite parity for key critical paths
4. Define bug triage loop:
   - failure classification and ownership routing
   - reproducibility criteria before closure

### Gate V: Identity, Accounts, and Session Trust (Mandatory)

1. Define player account model for progression continuity:
   - email+password registration/login flow
   - password hashing policy and minimum password requirements
   - password-reset controls
   - optional email verification flow (not required for gameplay in MVP)
   - account linking for campaign participation
   - secure password-recovery/reset flow
2. Define identity policy for second-screen join:
   - QR join maps to authenticated player identity
   - reconnect and rebind policy for device/session handoff
3. Define session trust controls:
   - session expiry/refresh
   - suspicious-device detection and revoke flow
4. Define progression ownership rules:
   - progression attached to account identity
   - story participation history preserved across adventures

### Gate W: Narrative Memory and Continuity Architecture (Mandatory)

1. Define short-term context policy:
   - turn-window management
   - prompt budget allocation
2. Define long-term memory strategy:
   - PostgreSQL + pgvector baseline for retrieval memory
   - retrieval schema for world, NPC, quest, and party history
   - summarization cadence and quality thresholds
   - RAG context packaging for game master narration continuity
3. Define memory retrieval safety:
   - ranking and relevance filters
   - conflict-resolution policy when memory and live state disagree
4. Define narrative continuity QA:
   - golden multi-session traces
   - continuity drift detection thresholds

### Gate X: SRD 5.1 Rules Scope and Licensing Compliance (Mandatory)

1. Define strict SRD 5.1 scope boundaries:
   - allowed rules/spells/creatures/content sets
   - prohibited non-SRD references in defaults
2. Define attribution and compliance policy:
   - CC-BY attribution requirements and placement
   - source-traceability for rules data
3. Define compliance validation:
   - automated scans for non-SRD entities in rules/content packs
   - release-blocking checklist for SRD compliance

### Gate Y: FinOps and Runtime Cost Governance (Mandatory)

1. Define cost policy by runtime mode:
   - local-first adaptive default
   - balanced and quality-first override behavior
2. Define budgets and enforcement:
   - per-session/per-day spend limits
   - soft alert and hard-cap policies
3. Define degrade/fallback policy under budget pressure:
   - lower-cost model substitution order
   - user-visible impact messaging and override permissions
4. Define cost observability:
   - per-provider usage dashboards
   - per-feature cost attribution and anomaly alerts
5. Define storage-cost governance:
   - tiered voice recording storage quota policy (by account tier/campaign class)
   - near-threshold warnings and host/admin remediation actions
   - archive/export behavior before storage hard-stop conditions

## 2.1) Initial Quantitative Baselines (Provisional Launch Targets)

These baselines are mandatory to convert gate pass/fail into measurable checks.  
ADR-033 will finalize exact thresholds by environment profile.

1. API latency:
   - read p95 <= 300 ms
   - write p95 <= 400 ms
2. Realtime timeline:
   - server commit to client render p95 <= 250 ms
3. Voice:
   - STT first partial <= 1200 ms p95
   - transcript finalize <= 2500 ms p95 after speech end
   - TTS first audio <= 1500 ms p95
4. Pairing:
   - join success >= 99.0% within 10 seconds
   - token issuance success >= 99.9%
5. Recovery:
   - RPO <= 60 seconds
   - RTO <= 5 minutes
6. Automation quality:
   - MCP Chrome critical-path suite pass rate >= 98% rolling 30 runs
7. Timeline durability:
   - completed turn persistence success >= 99.99% (event + transcript/recording links)

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
12. Character Sheet Systems Agent
13. Story Portfolio Agent
14. Second Screen Experience Agent
15. Art Asset Pipeline Agent
16. Map Tool Integration Agent
17. Game Administration Agent
18. Progression Systems Agent
19. Save Recovery Agent
20. Data Platform Agent
21. QA Automation Agent
22. Browser Automation QA Agent
23. DevOps Security Agent
24. Identity Access Agent
25. Memory RAG Agent
26. Legal IP Compliance Agent
27. Realtime Voice Infrastructure Agent
28. FinOps Agent

## 4) Phase-by-Phase Delivery Plan

## Phase 0: Foundations and Contracts (1-2 weeks)

Primary agents:
1. Architecture Agent
2. LLM Provider Integration Agent
3. Audio Speech Agent
4. Localization Agent
5. Settings Experience Agent
6. Character Sheet Systems Agent
7. Story Portfolio Agent
8. Second Screen Experience Agent
9. Art Asset Pipeline Agent
10. Map Tool Integration Agent
11. Game Administration Agent
12. Progression Systems Agent
13. Save Recovery Agent
14. Browser Automation QA Agent
15. DevOps Security Agent
16. Identity Access Agent
17. Memory RAG Agent
18. Legal IP Compliance Agent
19. Realtime Voice Infrastructure Agent
20. FinOps Agent

Tasks:
1. Complete Gates A-Y approvals.
2. Define provider/audio/settings/admin/progression/save/character/story/identity/memory/legal/finops contracts.
3. Define TV/mobile/pairing contracts and security policy.
4. Define character creation mode contracts and dice authority rules.
5. Define story portfolio model and continuity contracts.
6. Define art pipeline contracts and Python automation architecture.
7. Define external map tool integration matrix and format adapters.
8. Build prompt playground for narrative/tool/voice tests.
9. Build schema v1 draft and migration strategy.
10. Build MCP Chrome smoke automation harness and failure artifact pipeline.

Exit criteria:
1. Gate pack approved.
2. CI baseline green.
3. Contract tests pass for provider/audio/settings/pairing/admin/progression/save/character/story/art/map/identity/memory/legal/finops interfaces.
4. MCP Chrome smoke suite executes in CI with reproducible artifacts.

## Phase 1: Multiplayer MVP Core + TV/Mobile Companion (4-7 weeks)

Primary agents:
1. AI Orchestration Agent
2. Character Sheet Systems Agent
3. Story Portfolio Agent
4. Second Screen Experience Agent
5. Audio Speech Agent
6. Localization Agent
7. Settings Experience Agent
8. Art Asset Pipeline Agent
9. Map Tool Integration Agent
10. Data Platform Agent
11. QA Automation Agent
12. Browser Automation QA Agent
13. Identity Access Agent
14. Memory RAG Agent
15. Realtime Voice Infrastructure Agent
16. FinOps Agent
17. Legal IP Compliance Agent

Tasks:
1. 4-player lobby/join/reconnect/session authority.
2. Player account onboarding/authentication and account-linked progression identity.
3. TV mode for DM display with distance-optimized UI.
4. QR join flow for mobile players with token issuance only at game start.
   - token default TTL: 120 seconds
   - host can regenerate token if expired
5. Mobile companion views:
   - character sheet and stats
   - inventory and items
   - spells and resources
   - read-only presentation (no direct action submission)
6. Shared text + voice narrative stream across TV and mobile clients.
7. WebRTC voice baseline + fallback transport v1 with reconnect handling.
8. Voice or GM-choice (`1`, `2`, `3`, ...) action input flow.
9. EN/FR support across core loop.
10. Full settings screen with safe validation.
11. Character creation v1 (D&D-compliant):
   - automatic creation mode
   - player-dice creation mode
   - GM-TV-dice creation mode
   - creation validation feedback and correction flow
12. Polished character sheet UX:
   - full sheet readability and navigation
   - fast edit/validation interactions
   - responsive behavior across TV/desktop/tablet/mobile
13. Story portfolio v1 for GMs:
   - start new story
   - continue existing story
   - assign different player rosters per story
   - isolate saves/checkpoints by story
14. Narrative memory v1:
   - short-term context window policy
   - PostgreSQL + pgvector retrieval memory baseline
   - long-term retrieval store and session summarization
15. Session-zero onboarding flow for hosts and first-time players.
16. Responsive UI verification for TV/desktop/tablet/mobile layouts.
17. Art pipeline v1:
   - custom Python generation scripts
   - initial token/portrait/item/background packs
   - metadata capture (model/seed/prompt/version)
18. External map import v1:
   - at least one dungeon/room tool adapter
   - at least one village/outdoor tool adapter
19. Save system v1:
   - autosave
   - manual save
   - checkpoint create/list
   - host-only restore enforcement
20. Strict SRD 5.1 content baseline:
   - SRD data ingestion and attribution
   - non-SRD entity prevention checks
21. FinOps controls v1:
   - per-session budget visibility
   - model routing under budget cap
22. Persistent campaign, settings, device-session, story-portfolio, and asset metadata data.
23. Unified interaction timeline v1:
   - persist text events + voice recordings/transcripts + choice events
   - polished timeline cards for GM prompts, player actions, and outcomes
   - per-turn transcript + audio playback controls
   - story-resume optimized timeline navigation and search
24. Recording consent + capture safety v1:
   - explicit session consent collection before first recording
   - recording-state indicator on TV/desktop/mobile
   - consent audit trail display in admin logs
25. MCP Chrome critical-path suite v1:
   - session start/join
   - character creation (all modes)
   - story selection (new/continue)
   - save/restore host-only enforcement

Exit criteria:
1. Stable 4-player end-to-end session.
2. Voice round trip works reliably.
3. EN/FR core flows pass.
4. TV and mobile stay synchronized without stale state.
5. Single active device policy is enforced per player.
6. Player account identity persists progression across stories.
7. Character creation works in all three modes with D&D rule validation.
8. GM can start new story or continue existing story with correct roster isolation.
9. Narrative continuity passes baseline multi-session memory checks.
10. Art pipeline produces reproducible asset outputs that meet baseline quality rubric.
11. Map imports render correctly with required metadata mapping.
12. Session-zero onboarding completion rates meet baseline target.
13. Save/create/restore basic flow passes with host-only restore policy.
14. SRD compliance baseline checks pass with attribution in place.
15. FinOps guardrails prevent uncontrolled spend under load.
16. Voice/text/choice interactions are persisted and rendered in polished timeline UI.
17. Recording consent enforcement passes on all supported clients.
18. MCP Chrome critical-path suite is stable at target pass rate.

## Phase 2: Authoritative Gameplay + Progression + Recovery (4-7 weeks)

Primary agents:
1. Rules Engine Agent
2. AI Orchestration Agent
3. Progression Systems Agent
4. Save Recovery Agent
5. LLM Provider Integration Agent
6. Character Sheet Systems Agent
7. Story Portfolio Agent
8. Second Screen Experience Agent
9. Art Asset Pipeline Agent
10. Map Tool Integration Agent
11. QA Automation Agent
12. Browser Automation QA Agent

Tasks:
1. Authoritative action-resolution pipeline.
2. Tool-calling contracts for gameplay actions.
3. Progression v1:
   - story milestones + XP signals
   - achievement events
   - progression UI and logs
4. Save/recovery v2:
   - restore dry-run
   - branch/fork from checkpoint
   - integrity checks
5. Provider routing policy connected to settings.
6. Companion read-only enforcement and voice/GM-choice action validation.
7. Art pipeline v2:
   - style consistency improvements (control workflows/LoRA where needed)
   - automated quality scoring hooks
8. Map import v2:
   - broader format support and validation coverage.
9. Story continuity v2:
   - story resume context packaging for AI orchestration
   - cross-story isolation regression tests
10. Browser automation v2:
   - expanded MCP Chrome regression suite for progression/recovery/portfolio flows
   - automated defect triage workflow integration

Exit criteria:
1. LLM cannot mutate state directly.
2. Progression updates are deterministic and auditable.
3. Save recovery succeeds within defined reliability targets.
4. Provider failover behaves correctly.
5. Read-only companion and voice/choice action integrity rules pass.
6. Art outputs pass style consistency threshold in automated and human review.
7. Import adapters pass compatibility test suite.
8. Story continuation remains consistent across multiple active stories.
9. MCP Chrome regression suite detects and reproduces defects on critical flows.

## Phase 3: Polished Map + Administration Console (4-7 weeks)

Primary agents:
1. Frontend VTT Agent
2. Map Systems Agent
3. Map Tool Integration Agent
4. Art Asset Pipeline Agent
5. Game Administration Agent
6. Second Screen Experience Agent
7. Rules Engine Agent
8. QA Automation Agent
9. Browser Automation QA Agent

Tasks:
1. Polished tactical map UX with proven algorithms.
2. Reliable map sync across 4 players.
3. TV presentation polish pass for narrative + tactical readability.
4. Mobile companion tactical overlays (read-only).
5. Admin portal v1:
   - provider policy management
   - emergency controls
   - device/session revoke
   - campaign archive/fork/ownership transfer
   - audit logs
6. Final visual polish pass:
   - scene art cohesion
   - token/sprite readability
   - premium-fantasy presentation quality with original art direction.
7. Browser automation v3:
   - map interaction and admin lifecycle scenario coverage
   - TV/mobile second-screen synchronized assertion suite

Exit criteria:
1. Map gate passes.
2. Admin gate passes (RBAC + audit + action safety).
3. Second-screen and multiplayer sync remain stable.
4. MCP Chrome map/admin/second-screen suites pass release threshold.

## Phase 4: Hardening and Release Readiness (2-4 weeks)

Primary agents:
1. QA Automation Agent
2. Browser Automation QA Agent
3. DevOps Security Agent
4. Product Delivery Agent
5. Narrative Design Agent
6. Game Administration Agent
7. Save Recovery Agent
8. Second Screen Experience Agent
9. Art Asset Pipeline Agent
10. Map Tool Integration Agent

Tasks:
1. Load/chaos/failover testing.
2. Security and operational hardening.
3. Final certification for all mandatory quality gates.
4. Recovery drills and incident simulations.
5. Device pairing penetration tests and reliability tests.
6. Final art quality and licensing compliance certification.
7. Full MCP Chrome + fallback runner release-candidate regressions and bug triage closure.

Exit criteria:
1. All quality gates pass.
2. Release checklist signed.
3. On-call and incident playbooks verified.

## 5) Mandatory Release Quality Gates

1. Narrative Gate: storyline rubric threshold met.
2. Map Gate: polish + algorithm correctness + performance met.
3. Audio Gate: reliable bidirectional voice and latency target met.
4. Multilingual Gate: EN default + FR parity met.
5. Art Quality Gate: generated/imported assets meet visual consistency and readability thresholds.
6. Asset Licensing Gate: all generated/imported assets are tracked and compliant.
7. Responsive-UI Gate: layouts and interactions pass on TV/desktop/tablet/mobile.
8. Multiplayer Gate: 4-player stability and reconnect targets met.
9. Second-Screen Gate: TV mode + game-start QR join + single-device policy + read-only companion sync pass.
10. Settings Gate: all config paths validated and safe.
11. Character-Sheet Gate: polished D&D-compliant character creation/sheet flows pass across all creation modes.
12. Story-Portfolio Gate: GM can start/continue multiple stories with roster and save isolation guarantees.
13. Browser-Automation Gate: MCP Chrome critical-path and regression suites pass stability targets.
14. Administration Gate: RBAC, audit, and operational readiness met.
15. Progression Gate: hybrid story-driven progression is deterministic, fair, and exploit-resistant.
16. Save/Recovery Gate: integrity, restore reliability, and recovery targets met.
17. Security Gate: threat model, scanning, secrets policy, and hardening checks pass.
18. Observability Gate: SLO dashboards, alerts, and runbooks are operational.
19. Performance Gate: backend/frontend load and latency budgets pass.
20. Accessibility Gate: WCAG 2.2 AA and cross-device UX checks pass.
21. Visual Regression Gate: critical UI flows pass snapshot-diff thresholds across target devices.
22. Asset Delivery Gate: asset payload, caching, and render-time budgets pass.
23. Onboarding Gate: session-zero and first-session completion flows meet UX quality targets.
24. Identity Gate: account/session/device trust controls and progression ownership rules pass.
25. Memory Gate: multi-session narrative continuity and retrieval quality thresholds pass.
26. SRD Compliance Gate: strict SRD 5.1 scope and attribution checks pass.
27. FinOps Gate: budget enforcement, cost observability, and degrade policy checks pass.
28. Interaction Timeline Gate: all GM/player turns (text, voice recordings/transcripts, and choices) are persisted, searchable, and visually clear.
29. Recording Consent Gate: recording consent is collected/audited before first captured voice turn in each session.
30. Data Lifecycle Gate: lifecycle retention, quota alerts, and delete/erase workflows behave as specified.

## 6) Immediate Sprint 0 Backlog

1. ADR-001: FastAPI + React architecture baseline.
2. ADR-002: Multi-provider adapter and routing modes.
3. ADR-003: Hybrid audio pipeline and voice-turn protocol.
4. ADR-004: i18n architecture for EN/FR.
5. ADR-005: Settings schema and override safety rules.
6. ADR-006: Administration RBAC, audit logging, and operational controls.
7. ADR-007: Hybrid progression model (story milestones + XP signals) and anti-exploit policy.
8. ADR-008: Save model, host-only restore permissions, host-reassignment rules, reliability targets (RPO/RTO).
9. ADR-009: TV/mobile second-screen architecture + game-start QR pairing + single-device policy.
10. ADR-010: Responsive UI standards and breakpoint/accessibility rules.
11. ADR-011: Art generation pipeline (Python + Stable Diffusion workflow + metadata and QA policy).
12. ADR-012: External map tool integration matrix and supported import formats.
13. ADR-013: Security baseline (threat model, scanning, SBOM, secrets).
14. ADR-014: Observability and SLO design (metrics, tracing, alerts, runbooks).
15. ADR-015: Performance budgets and load test strategy.
16. ADR-016: Release strategy (feature flags, canary, rollback).
17. ADR-017: Accessibility and UX quality baseline (WCAG 2.2 AA).
18. ADR-018: Asset delivery architecture (sprite atlas/compression/CDN/cache strategy).
19. ADR-019: Visual regression and cross-device snapshot strategy.
20. ADR-020: Campaign lifecycle and host handover policy.
21. ADR-021: Session-zero onboarding and first-session UX flow standards.
22. ADR-022: Character creation modes (auto/player-dice/GM-TV-dice) and D&D validation rules.
23. ADR-023: Multi-story portfolio model, roster isolation, and story-scoped save continuity.
24. ADR-024: MCP Chrome automation strategy, CI topology, and fallback runner parity policy.
25. ADR-025: Identity/account model (email+password), trusted session policy, and progression ownership rules.
26. ADR-026: Narrative memory architecture (PostgreSQL + pgvector retrieval, short-term context, summarization).
27. ADR-027: SRD 5.1 compliance policy and attribution implementation.
28. ADR-028: WebRTC-first voice transport architecture with fallback behavior.
29. ADR-029: FinOps guardrails, budget enforcement, and cost observability model.
30. ADR-030: Interaction timeline model, polished rendering UX, and lifecycle retention policy.
31. ADR-031: Voice recording consent policy, UI signaling rules, and auditability requirements.
32. ADR-032: Credential security profile (Argon2id, verification/reset, rate limiting, session hardening).
33. ADR-033: Quantitative SLO/SLI baseline pack for API, voice, pairing, timeline, and restore paths.
34. ADR-034: Voice recording storage lifecycle/quota policy and archive strategy.
35. ADR-035: pgvector indexing/retrieval strategy and operational tuning model.
36. Schema v1 migration set including progression/save/admin/pairing/asset/story/character-creation/identity/memory/voice/transcript/timeline tables.
37. QA matrices:
   - narrative rubric
   - map polish
   - art quality
   - asset licensing/compliance
   - multilingual
   - responsive UI
   - accessibility
   - visual regression
   - browser automation regression
   - security
   - observability/SLO
   - performance/load
   - settings safety
   - second-screen sync and pairing security
   - admin/progression/save reliability
   - character sheet and creation compliance
   - story portfolio continuity and isolation
   - onboarding/session-zero completion quality
   - identity/session trust and progression ownership
   - narrative memory continuity and retrieval quality
   - SRD scope and attribution compliance
   - finops budget/degrade behavior
   - interaction timeline clarity, continuity, and searchability
   - recording consent enforcement and audit integrity
   - data lifecycle and storage-quota behavior
