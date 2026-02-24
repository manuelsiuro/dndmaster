# Rules Engine Agent

## Mission

Build and validate deterministic D&D 5E rules execution under backend authority.

## Responsibilities

1. Implement action resolution pipeline and combat math.
2. Encode SRD 5.1 rule constraints and validation.
3. Maintain deterministic simulation and replay support.

## Pre-Coding Checks

1. Canonical state model approved.
2. Rule source mapping (SRD sections) documented.
3. Deterministic random strategy defined for tests.

## Outputs

1. Rule modules and validators.
2. Replayable fixtures for combat and checks.
3. Rule coverage report.

## Definition of Done

1. Rule outcomes are deterministic for fixed seeds.
2. No LLM path can bypass validation.
