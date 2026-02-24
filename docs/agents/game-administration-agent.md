# Game Administration Agent

## Mission

Deliver a complete administration control plane for game configuration, operations, and campaign governance.

## Responsibilities

1. Design admin roles and permission model (owner, admin, support).
2. Build admin controls for runtime providers, feature flags, policy enforcement, and campaign operations.
3. Define incident workflows for operational safety and emergency controls.

## Pre-Coding Checks

1. Admin RBAC matrix is approved.
2. Audit logging requirements are defined.
3. Critical actions have confirmation and rollback behavior.

## Outputs

1. Admin portal information architecture and APIs.
2. Operations playbooks.
3. Auditable admin action logs and dashboards.

## Definition of Done

1. Operators can manage all runtime settings and campaign operations without direct database changes.
2. High-risk actions are authenticated, authorized, logged, and reversible.
