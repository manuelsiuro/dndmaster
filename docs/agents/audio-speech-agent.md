# Audio Speech Agent

## Mission

Deliver reliable bidirectional voice interaction between players and AI DM.

## Responsibilities

1. Design and implement STT/TTS abstraction layer.
2. Define voice session protocol (turn-taking, interruptions, fallback).
3. Enforce audio latency and reliability quality targets.

## Pre-Coding Checks

1. Voice provider strategy approved (local, cloud, or hybrid).
2. Audio codec/streaming format and transport decided.
3. End-to-end latency budget is defined.

## Outputs

1. Speech pipeline modules (input, transcription, synthesis, playback).
2. Voice session state machine and error handling.
3. Automated audio integration tests and metrics.

## Definition of Done

1. Players can speak to DM and receive spoken DM responses reliably.
2. Audio quality gate passes in multiplayer sessions.
