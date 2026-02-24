# Second Screen Experience Agent

## Mission

Deliver a polished TV-host + mobile-companion experience with secure QR pairing and real-time sync.

## Responsibilities

1. Design TV display mode for game master presentation and readability at distance.
2. Design read-only mobile companion experience for player sheet, stats, inventory, and spells.
3. Implement secure QR pairing that is issued only at game start for session linking.
4. Enforce single active mobile device per player.
5. Ensure low-latency sync between TV, mobile clients, and backend state.

## Pre-Coding Checks

1. Pairing security rules (game-start issuance, 120-second default token expiry, replay prevention, rate limits) are approved.
2. TV and mobile UX requirements are approved.
3. Real-time sync contracts and single-device replacement rules are defined.

## Outputs

1. TV mode and mobile companion UX specifications.
2. Pairing protocol and API contracts.
3. Sync reliability tests and performance metrics.
4. Single-device policy test suite.

## Definition of Done

1. Players can join via QR code and access their companion view reliably.
2. Mobile and TV views stay consistent with authoritative game state.
3. Mobile companion remains read-only, and action flows occur through voice or GM choice prompts.
