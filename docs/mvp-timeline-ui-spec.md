# DragonWeaver MVP Timeline UI Spec

Date: 2026-02-24  
Status: Approved baseline candidate for MVP implementation

## 1) Scope

This spec defines the MVP user experience for the unified interaction timeline:

1. A single conversation timeline that merges:
   - GM questions/prompts
   - player actions
   - numeric choices and selected option
   - outcomes/consequences
   - voice recordings and transcripts
2. Primary surfaces:
   - GM TV presentation
   - GM desktop control workspace
   - mobile companion (read-only)
3. Lifecycle retention:
   - timeline data (text, choice events, recordings, transcripts) is retained while campaign exists.
4. Consent and capture safety:
   - recording starts only after explicit session consent from participants.
5. MVP export policy:
   - voice is replayable in-app only (no downloadable export in MVP).

## 2) Goals

1. Keep story continuity obvious during live play.
2. Make voice turns as easy to follow as text turns.
3. Let players quickly catch up after interruptions/reconnects.
4. Make GM prompts, player actions, and consequences visually distinct.

## 3) User Roles and Permissions

1. `Host GM`:
   - full timeline view and playback
   - search/filter/bookmark/pin
   - transcript correction annotations
   - recap actions
2. `Player` (account-authenticated, mobile read-only):
   - timeline view and playback
   - search/filter (limited to personal + shared story view)
   - no mutation of timeline events
3. `Admin/Support`:
   - no gameplay timeline mutation by default
   - read/audit access per RBAC policy only

## 4) Information Model for UI

Each timeline event rendered in UI must include:

1. `event_id`
2. `story_id`, `campaign_id`
3. `event_type` enum:
   - `gm_prompt`
   - `player_action`
   - `choice_prompt`
   - `choice_selection`
   - `outcome`
   - `system`
4. `actor`:
   - player/GM name
   - role marker
5. `timestamp`
6. `text_content` (if available)
7. `audio_ref` and duration (if voice exists)
8. `transcript_segments` with confidence metadata
9. `language` + optional translated text
10. `links`:
   - source event references (choice to consequence, action to outcome)

## 5) Screen Specifications

## 5.1 GM TV Live Timeline Screen

Layout:

1. `Now Playing / Current Turn` panel (center focus).
2. `Timeline Stream` rail (recent turns).
3. `Status Strip` (live, listening, thinking, speaking, paused, reconnecting).

Screen states:

1. `Loading Session`: skeleton cards + reconnect-safe spinner.
2. `Live Listening`: active mic/speaker indicator, partial transcript streaming.
3. `Live Speaking`: DM audio playback indicator + live transcript reveal.
4. `Choice Pending`: emphasized choice card with options `1,2,3...`.
5. `Paused`: clear paused badge and resume CTA.
6. `Reconnect`: degraded banner, cached timeline still readable.
7. `No Audio Fallback`: transcript-only mode indicator.
8. `Consent Required`: recording-disabled state until required consents are completed.

## 5.2 GM Desktop Timeline Workspace

Layout:

1. `Timeline Feed` (virtualized list).
2. `Search + Filters` toolbar.
3. `Detail Drawer` (full transcript, linked events, notes/pins).
4. `Recap Actions` panel.

Screen states:

1. `Default Live`: auto-scroll on new turns with jump-to-live control.
2. `History Browse`: auto-scroll off, cursor anchored to selected card.
3. `Search Results`: highlighted hits with next/previous match.
4. `No Results`: empty state with clear reset action.
5. `Playback Active`: transcript word highlighting synced with audio.
6. `Playback Error`: retry and fallback transcript view.
7. `Storage Warning`: host-visible quota warning with remediation CTA.

## 5.3 Mobile Companion Timeline (Read-Only)

Layout:

1. `Condensed Timeline Cards` optimized for one-hand scroll.
2. `Quick Catch-Up` chip (last 5 min, combat only, GM prompts only).
3. `Audio Mini Player` pinned when active.

Screen states:

1. `Live`: newest turns appended in near real time.
2. `Catch-Up`: grouped unread turns since last active.
3. `Offline/Reconnecting`: cached timeline available, stale badge shown.
4. `Transcript-Only`: shown when audio playback unavailable.

## 6) Component Catalog (MVP)

1. `TimelineFeed`
   - virtualized list
   - grouped by scene/encounter markers
2. `TimelineCard`
   - event type badge
   - actor identity chip
   - timestamp
   - content area (text/transcript/choice/outcome)
3. `EventTypeBadge`
   - strict color/icon mapping by event type
4. `AudioPlaybackControl`
   - play/pause/seek
   - speed control (1.0x/1.25x/1.5x)
5. `TranscriptBlock`
   - streaming partial + finalized text
   - word-level highlight while playing
6. `ChoiceBlock`
   - choice options and selected option
   - link to resulting outcome event
7. `OutcomeLink`
   - shows consequence card references
8. `SearchBar`
   - full-text query on timeline/transcript
9. `FilterChips`
   - by speaker, event type, scene, language
10. `JumpControls`
   - jump to live
   - next/previous bookmarked event
11. `BookmarkPinControl`
   - host pin + bookmark controls
12. `RecapActionBar`
   - summarize from selected point
   - summarize last N minutes
13. `ConnectivityBanner`
   - realtime status and degradation reason
14. `PermissionGuard`
   - hides mutation controls for player read-only role
15. `RecordingIndicator`
   - persistent visual marker when recording is active
16. `ConsentPrompt`
   - explicit pre-capture consent UI and status
17. `StorageQuotaWarning`
   - host warning when nearing configured voice storage limits

## 7) Interaction Rules

1. Every voice turn creates:
   - one `voice_recording` asset
   - one or more `transcript_segments`
   - one `interaction_timeline_event` linked to both
2. Timeline ordering is authoritative by server timestamp with deterministic tie-breaker.
3. Choice flows must remain linked:
   - `choice_prompt` -> `choice_selection` -> `outcome`
4. GM and player turns must be visually distinguishable without reading full text.
5. Auto-scroll behavior:
   - on by default only when user is at live edge
   - auto-scroll disabled when user browses history
6. Playback behavior:
   - transcript highlights during playback
   - if audio missing, transcript view remains fully usable
7. Consent behavior:
   - no voice capture starts before required consents are present
   - active recording state remains visible on all participating screens

## 8) Acceptance Criteria (MVP Release)

## 8.1 Data Completeness

1. 100% of completed voice turns produce persisted recording + transcript + timeline event link.
2. 100% of choice prompts have linked selection and outcome events.
3. Timeline event loss rate is 0 for normal reconnect scenarios.
4. 100% of captured voice turns have a prior valid consent record in session audit data.

## 8.2 UX Clarity and Polish

1. Event type, speaker, and timestamp are visible on every card.
2. GM prompts, player actions, choices, and outcomes pass design QA distinction checks.
3. TV, desktop, and mobile designs pass responsive layout review without clipping/overlap.

## 8.3 Playback and Transcript Sync

1. Audio playback starts within 800 ms p95 from user tap (warm path target: 300 ms p95).
2. Transcript highlight drift against playback is <= 250 ms p95.
3. Transcript-only fallback activates automatically when audio playback fails.

## 8.4 Performance

1. Timeline feed remains smooth at 5,000 events with virtualization enabled.
2. Search/filter response time is <= 500 ms p95 for 10,000 events in-session scope.
3. New live event render time is <= 200 ms p95 after websocket receipt.

## 8.5 Accessibility

1. Full keyboard navigation for desktop timeline and playback controls.
2. WCAG 2.2 AA contrast for badges/cards/text.
3. All icons/buttons include accessible labels.

## 8.6 Security and Permissions

1. Player mobile role cannot edit/delete/pin timeline events.
2. Only host role can perform transcript correction annotations.
3. Access to recordings/transcripts follows authenticated session and RBAC checks.
4. Voice capture cannot start when consent state is incomplete.

## 8.7 Localization

1. EN and FR timeline UI labels are complete for MVP surfaces.
2. Per-event language metadata is displayed.
3. EN/FR views preserve event ordering and links.

## 8.8 Reliability and Recovery

1. On reconnect, client restores exact timeline position and unread marker.
2. Offline mode preserves cached history and clearly marks stale state.
3. Campaign restore preserves timeline event integrity and recording/transcript links.
4. Quota warning appears before configured storage hard-stop threshold is reached.

## 9) Non-Goals (MVP)

1. Multi-track audio mixing/editing inside timeline.
2. Public sharing or social publishing of recordings.
3. Download/export of voice recordings in MVP.
4. Full transcript rewrite history for non-host users.

## 10) Test Scenarios (Must Exist in Browser Automation)

1. GM prompt by voice appears with recording + transcript in <= 2 s.
2. Player spoken action appears and is linked to resulting outcome.
3. Choice prompt (`1,2,3`) selection renders and links to consequence.
4. Search for transcript term jumps to exact event and playback position.
5. Mobile reconnect after disconnection restores unread timeline correctly.
6. Player role attempts host-only edit action and is blocked.
