# Save Recovery Agent

## Mission

Implement reliable save, checkpoint, restore, and recovery systems for campaigns and sessions.

## Responsibilities

1. Define save model (autosave, manual saves, checkpoints, branching timelines).
2. Implement host-only restore flows with validation, conflict handling, and host-reassignment compatibility.
3. Define backup, export/import, and disaster recovery procedures.

## Pre-Coding Checks

1. Save consistency model is approved.
2. Recovery objectives (RPO/RTO) are defined.
3. Host-only restore permissions and audit requirements are defined.

## Outputs

1. Save/restore APIs and storage strategy.
2. Recovery runbooks and restore test suites.
3. Snapshot integrity checks and alerts.

## Definition of Done

1. Sessions can be restored safely without state corruption.
2. Save and restore paths pass automated reliability tests.
