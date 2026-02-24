# DragonWeaver Spec Gap Analysis

Date: 2026-02-24  
Input baseline: [`docs/implementation-plan.md`](./implementation-plan.md)
UI baseline: [`docs/mvp-timeline-ui-spec.md`](./mvp-timeline-ui-spec.md)

## 1) Executive Summary

Core product scope is now strong across multiplayer, voice, multilingual, TV/mobile second-screen, administration, progression, save/recovery, character systems, and story continuity.

This pass expands the spec for premium visual quality and core gameplay lifecycle quality:

1. Art asset pipeline with custom Python automation and Stable Diffusion workflows.
2. External map-tool integrations for dungeon/room/village/outdoor content.
3. Asset quality and license compliance as release blockers.
4. D&D-compliant character creation/sheet quality as a release blocker.
5. Multi-story portfolio continuity and roster isolation as a release blocker.

Locked decisions reflected in specs:

1. Progression model is hybrid and story-dependent.
2. Moderation layer is out of scope.
3. UI must be responsive across TV/desktop/tablet/mobile.
4. Mobile companion is read-only.
5. Player actions happen through voice or GM choice prompts (`1`, `2`, `3`, ...).
6. QR token is issued at game start for player connection with a 120-second default TTL.
7. Device policy is single active device per player.
8. Save restore permissions are host-only.
9. Host reassignment policy is required before restore when host changes.
10. Character creation supports automatic, player-dice, and GM-TV-dice modes.
11. GMs can start new stories or continue existing stories with different player rosters.
12. MCP Chrome is the primary browser automation runner with fallback parity requirements.
13. Player accounts are required to persist progression across stories/adventures.
14. Rules/content scope is strict SRD 5.1 only with attribution enforcement.
15. Voice transport baseline is WebRTC-first with fallback path.
16. Default runtime mode is local-first adaptive routing with budget guardrails.
17. Account auth model is email+password for MVP.
18. Memory store baseline is PostgreSQL + pgvector for narrative RAG continuity.
19. Voice recordings/transcripts/text/choice interactions are persisted as a polished unified timeline.
20. Voice recording/transcript retention is lifecycle-based: retained while the game/campaign exists.
21. Recording consent is mandatory before first captured voice turn in each session.
22. Voice storage retention must include quota/alert controls for operational safety.
23. Email verification is not required for gameplay access in MVP.
24. Voice export policy for MVP is in-app playback only.
25. Voice storage quota policy is tiered by account tier/campaign class.

## 2) Coverage Matrix

| Domain | Current Coverage | Gap Level | Required Addition |
| :--- | :--- | :--- | :--- |
| Multiplayer core | Strong | Low | Keep 4-player MVP target and reconnect tests |
| Identity/accounts/session trust | Medium | High | Add account-linked progression ownership, session trust, and reconnect identity rules |
| Auth credentials model | Medium | High | Lock email+password policy, password hardening, and recovery controls |
| Second-screen TV/mobile | Strong | Medium | Formalize pairing SLOs, single-device replacement semantics |
| Voice (STT/TTS) | Strong | Medium | Add voice fallback UX and turn-taking edge-case tests |
| Realtime voice transport | Medium | High | Lock WebRTC baseline with TURN/STUN strategy and fallback transport behavior |
| Recording consent and signaling | Medium | High | Enforce explicit consent before capture and persistent recording-state indicators |
| Interaction timeline UX | Medium | High | Add polished unified timeline for GM prompts, player actions, choices, transcripts, and voice playback |
| Multilingual EN/FR | Strong | Medium | Add localization QA automation and glossary governance |
| Responsive UI | Medium | Medium | Add measurable breakpoint/performance/accessibility criteria |
| Browser automation quality | Medium | High | Add MCP Chrome critical-path coverage, CI stability targets, and triage loops |
| Character creation and sheet compliance | Medium | High | Add full D&D validation, creation mode auditability, and UX quality rubric |
| Narrative quality | Strong | Medium | Add narrative regression dataset curation workflow |
| Narrative memory/RAG continuity | Medium | High | Add memory architecture, retrieval QA, and drift detection checks |
| Memory infrastructure choice | Medium | Medium | Lock PostgreSQL + pgvector baseline and vector indexing strategy |
| Art asset pipeline | Medium | High | Add script orchestration, reproducibility metadata, quality rubric |
| Asset delivery pipeline | Medium | High | Add atlas/compression/CDN/caching strategy with payload budgets |
| Map tool integration | Medium | High | Add format adapters, import validation, and compatibility benchmarks |
| Map quality/algorithms | Strong | Medium | Add benchmark suite and deterministic map simulation tests |
| LLM multi-provider | Strong | Medium | Add provider policy controls and usage governance |
| FinOps governance | Medium | High | Add budget caps, spend alerts, and deterministic degrade behavior |
| Voice storage lifecycle governance | Medium | High | Add quota policies, warning thresholds, and archive/remediation paths |
| SRD rules licensing compliance | Medium | High | Add SRD scope enforcement, attribution placement, and automated non-SRD scans |
| Settings UX | Strong | Medium | Add role-based restrictions and safe defaults |
| Game administration | Medium | Medium | Expand incident playbooks and operations runbooks |
| User progression | Medium | Medium | Expand exploit-prevention and balancing telemetry |
| Save/recovery | Medium | Medium | Add restore permission matrix and DR drills |
| Story portfolio continuity | Medium | High | Add multi-story lifecycle, roster isolation, and story-scoped save integrity checks |
| Campaign lifecycle | Medium | Medium | Add archive, fork, handover ownership, retention rules |
| Compliance/security | Medium | Medium | Add PII/voice transcript handling standards and audit trails |
| Observability | Medium | Medium | Add live ops dashboards and incident playbooks |
| Quantitative SLO readiness | Medium | High | Convert qualitative gates into measurable pass/fail thresholds |
| Accessibility | Weak | Medium | Add WCAG targets, captions, keyboard navigation, color safety |
| Onboarding | Medium | Medium | Add measurable funnel targets and regression checks for session-zero completion |

## 3) Required Additions for a Polished GM Product

## P0 (Must Have Before MVP Release)

1. TV display mode for game master with distance-optimized readability.
2. Game-start QR join flow with secure short-lived pairing tokens.
3. Mobile read-only companion for character sheet, stats, inventory, and spells.
4. Voice and GM-choice action model with deterministic backend validation.
5. Admin control plane with RBAC and audit logs.
6. Save system with autosave + manual checkpoints + restore validation.
7. Hybrid story-based progression with anti-farming protections.
8. Localization QA automation for EN/FR text + voice.
9. Responsive UI quality checks across TV/desktop/tablet/mobile.
10. Art pipeline v1 with Python scripts and reproducible asset generation metadata.
11. Map import v1 for selected external tools covering dungeon and outdoor/village use cases.
12. Asset delivery pipeline v1 with payload and caching budgets.
13. Session-zero onboarding flow v1 with completion telemetry.
14. Polished D&D-compliant character creation and character sheet workflows.
15. Story portfolio v1 with start-new/continue-existing flows and roster/save isolation.
16. MCP Chrome browser automation v1 for critical user journeys.
17. Player account system with authenticated identity and progression ownership.
18. WebRTC-first multiplayer voice transport with fallback behavior and reconnect reliability.
19. Narrative memory v1 (short-term context, retrieval memory, session summarization).
20. Strict SRD 5.1 rules/content baseline with attribution and non-SRD prevention checks.
21. FinOps guardrails v1 (budget caps, alerts, and safe degrade routing).
22. Email+password account auth with secure credential handling and recovery flow.
23. PostgreSQL + pgvector memory store implementation with RAG retrieval for DM continuity.
24. Polished unified interaction timeline with persisted text/voice recordings/transcripts/choice events.
25. Lifecycle-based retention for voice recordings/transcripts and interaction history while campaign exists.
26. Recording consent gating with visible recording-state indicators on TV/desktop/mobile.
27. Voice storage quota alerts and remediation UX for host/admin.
28. Quantitative SLO baseline pack for API, pairing, voice, timeline, and recovery.

## P1 (Should Have During MVP Hardening)

1. Campaign lifecycle management (archive/fork/import/export/handover).
2. Accessibility baseline (captions, keyboard support, contrast checks).
3. Narrative dataset governance (golden sessions + rubric drift tracking).
4. Ops dashboards for provider usage, error rates, save integrity, pairing health.
5. Companion-device trust tools (device rename/revoke/history).
6. Expanded map-tool adapter coverage and import diagnostics UI.
7. Style consistency automation for larger art batches.

## P2 (Post-MVP Enhancers)

1. Advanced progression (seasonal quests, prestige paths, social progression).
2. Community systems (sharing campaigns/templates) with governance controls.
3. Rich mobile companion features (party planning tools, advanced read-only tactical views).
4. Additional model fine-tuning pipeline for style-specialized art assets.

## 4) Data Model Additions

Plan/add these entities:

1. `user_progression`: xp_total, level, milestones, unlocks, last_progress_event_id
2. `achievement_events`: id, user_id, campaign_id, type, payload, timestamp
3. `save_slots`: id, campaign_id, label, save_type (auto/manual/checkpoint), created_by
4. `save_snapshots`: id, save_slot_id, world_state_ref, chat_state_ref, integrity_hash
5. `restore_events`: id, campaign_id, snapshot_id, actor_id, reason, result
6. `admin_audit_log`: id, actor_id, action, target, before_json, after_json, timestamp
7. `join_tokens`: id, campaign_id, role, token_hash, expires_at, consumed_at
8. `player_devices`: id, user_id, device_fingerprint, label, trust_state, last_seen_at
9. `device_sessions`: id, campaign_id, user_id, device_id, status, joined_at, revoked_at
10. `art_assets`: id, type, style_tag, file_ref, source, license, qa_status
11. `art_generation_jobs`: id, model_id, workflow_id, prompt_hash, seed, params_json, result_ref
12. `map_import_jobs`: id, tool_name, source_format, source_ref, conversion_status, report_ref
13. `stories`: id, gm_user_id, title, status, timeline_meta
14. `story_rosters`: id, story_id, user_id, role, joined_at, left_at
15. `character_creation_events`: id, story_id, character_id, mode, roller_actor, roll_payload
16. Constraint: one active device session per player per campaign
17. `auth_identities`: id, user_id, provider, subject, verified_at
18. `auth_sessions`: id, user_id, session_token_hash, device_id, issued_at, expires_at, revoked_at
19. `auth_credentials`: user_id, password_hash, password_algo, password_updated_at, reset_required
20. `narrative_memory_chunks`: id, story_id, memory_type, content, embedding_ref, source_event_id
21. `narrative_summaries`: id, story_id, summary_window, summary_text, quality_score, created_at
22. `retrieval_audit_events`: id, story_id, query_hash, retrieved_refs, applied_refs, timestamp
23. `voice_consent_records`: id, user_id, campaign_id, consent_scope, accepted_at, revoked_at
24. `voice_recordings`: id, campaign_id, speaker_id, audio_ref, duration_ms, codec, captured_at
25. `transcript_segments`: id, campaign_id, speaker_id, language, content, confidence, timestamp
26. `interaction_timeline_events`: id, campaign_id, story_id, event_type, actor_id, display_payload, source_ref, timestamp

## 5) API/Workflow Additions

1. Pairing and second-screen APIs:
   - generate game-start QR join token
   - join session by QR token
   - bind/rebind/revoke device session
   - enforce single active device per player
   - fetch read-only companion data slices (sheet/inventory/spells/resources)
2. Art pipeline APIs/jobs:
   - submit generation batch job
   - fetch job status/results/metadata
   - approve/reject asset QA status
3. Map import APIs/jobs:
   - upload/import external map package
   - parse and convert supported formats
   - validation report retrieval
4. Admin APIs:
   - provider policy management
   - feature flags
   - emergency campaign pause/lock
   - device session revoke and quarantine
5. Progression APIs:
   - grant/revoke progression events
   - recompute progression from event log
   - progression ledger views
6. Character system APIs:
   - validate character build against D&D constraints
   - run creation workflow by mode (auto/player-dice/GM-TV-dice)
   - persist creation roll provenance and audit trail
7. Story portfolio APIs:
   - list/select/start story
   - continue story with roster binding
   - enforce story-scoped save and state isolation
8. Save APIs:
   - create autosave/checkpoint/manual save
   - list/inspect snapshots
   - restore snapshot with dry-run validation
   - fork campaign from snapshot
9. Browser automation workflows:
   - MCP Chrome smoke suite (PR gate)
   - MCP Chrome release-candidate full regression
   - fallback runner parity for critical flows
   - automated failure artifact and bug triage routing
10. Identity/account workflows:
   - email+password signup/login/session refresh/logout
   - password reset and credential rotation
   - authenticated QR-join binding to player identity
   - trusted-device and suspicious-session revoke flows
11. Narrative memory workflows:
   - write/update memory chunks and summaries
   - retrieve ranked memory context for prompt assembly
   - continuity drift diagnostics and repair workflow
12. SRD compliance workflows:
   - ingest SRD source data with attribution metadata
   - validate content packs against non-SRD denylist
   - generate release compliance report
13. FinOps workflows:
   - budget configuration and alert subscription
   - per-session spend tracking and provider-cost attribution
   - degrade/escalate runtime mode decisions under budget pressure
14. Transcript/timeline workflows:
   - persist voice recordings/transcription segments and merge with text/choice events
   - query timeline by speaker/event type/time range
   - render-ready timeline payloads for polished GM/player UI including voice playback
15. Recording consent workflows:
   - collect per-player explicit consent before first voice capture
   - persist consent audit events and expose consent status in session UI/admin
16. Storage lifecycle workflows:
   - monitor quota usage and near-limit alerts
   - enforce remediation path (cleanup/archive/export) before hard-stop thresholds

## 6) Quality Gate Additions

1. Second-Screen Gate:
   - QR join reliability target
   - pairing security tests (issuance window/expiry/replay/rate-limit)
   - TV/mobile sync latency and consistency checks
   - single-device replacement tests
2. Responsive-UI Gate:
   - breakpoint behavior checks across target screen classes
   - readability and touch-target checks
3. Art Quality Gate:
   - visual quality and style consistency checks
   - token/sprite readability checks
4. Asset Licensing Gate:
   - source/license traceability checks
   - no forbidden copyrighted style/content checks
5. Administration Gate:
   - RBAC policy tests
   - audit log integrity tests
6. Progression Gate:
   - hybrid formula determinism tests
   - anti-exploit scenario tests
7. Save/Recovery Gate:
   - restore success rate target
   - corruption detection tests
   - load/recovery under fault injection
8. Security Gate:
   - threat model completion
   - CI security scanning compliance
9. Observability Gate:
   - SLO dashboard and alert readiness
10. Performance Gate:
   - load/latency budget compliance
11. Accessibility Gate:
   - WCAG 2.2 AA and multi-device interaction checks
12. Visual Regression Gate:
   - cross-device snapshot diff threshold compliance
13. Asset Delivery Gate:
   - payload size, caching, and render-time budget compliance
14. Onboarding Gate:
   - session-zero completion funnel and first-session success targets
15. Character-Sheet Gate:
   - D&D rules compliance and creation-mode integrity checks
16. Story-Portfolio Gate:
   - start/continue flows, roster isolation, and cross-story save integrity checks
17. Browser-Automation Gate:
   - MCP Chrome suite stability and pass-rate thresholds
   - reproducible failure artifacts and triage SLA checks
18. Identity Gate:
   - account/session trust policy tests
   - progression ownership continuity across stories
19. Memory Gate:
   - multi-session continuity scoring thresholds
   - retrieval relevance and drift-detection checks
20. SRD Compliance Gate:
   - strict SRD scope validation
   - attribution and provenance checks
21. FinOps Gate:
   - budget cap enforcement checks
   - degrade behavior and user-notification checks
22. Interaction Timeline Gate:
   - text/voice recording/transcript/choice event persistence completeness checks
   - timeline UI clarity checks for GM prompts, player actions, and outcomes
   - search/filter/resume story continuity checks and playback usability checks
23. Recording Consent Gate:
   - explicit consent required before capture
   - recording-state signaling visible on all active clients
   - consent audit trail integrity checks
24. Data Lifecycle Gate:
   - retention and delete/erase behavior checks
   - storage quota alert and remediation-path checks
25. Quantitative SLO Gate:
   - API/pairing/voice/timeline/recovery SLO thresholds are measurable and met

## 7) Required Specialized Agents

1. Game Administration Agent
2. Progression Systems Agent
3. Save Recovery Agent
4. Second Screen Experience Agent
5. Art Asset Pipeline Agent
6. Map Tool Integration Agent
7. Character Sheet Systems Agent
8. Story Portfolio Agent
9. Browser Automation QA Agent
10. Identity Access Agent
11. Memory RAG Agent
12. Legal IP Compliance Agent
13. Realtime Voice Infrastructure Agent
14. FinOps Agent

## 8) Spec Decisions Still Needed

No blocking or non-blocking decision remains for Sprint 1 implementation readiness.
