# Story Portfolio Agent

## Mission

Implement robust multi-story campaign management so a GM can start new stories, continue existing stories, and manage different player rosters per story.

## Responsibilities

1. Define story portfolio data model and lifecycle.
2. Implement story selection flows:
   - start new story
   - continue existing story
3. Implement story-specific roster and save isolation.
4. Ensure continuity and integrity across multiple active stories.

## Pre-Coding Checks

1. Story lifecycle states and transitions are approved.
2. Roster assignment rules per story are approved.
3. Save isolation and cross-story integrity constraints are approved.

## Outputs

1. Story portfolio APIs and UI flow contracts.
2. Story/roster persistence model and migration specs.
3. Continuity validation and regression test suites.

## Definition of Done

1. GMs can reliably switch between stories and continue progress without state leakage.
2. Different player groups per story are supported and isolated.
