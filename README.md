# DragonWeaver

AI-driven multiplayer D&D 5E platform with a backend-authoritative rules engine and LLM narrative orchestration.

## Repository Status

Project planning and architecture are documented. Implementation will follow the phased plan in:

- [`docs/implementation-plan.md`](docs/implementation-plan.md)
- [`docs/draft.md`](docs/draft.md)

## High-Level Principles

- Backend is authoritative for game state and rules.
- LLMs generate narrative and call tools, but do not directly mutate game state.
- Multiplayer, voice interaction, and multilingual support (EN/FR) are mandatory.
- Narrative depth and map polish are release quality gates.

## Development Standards

- Use feature branches and open pull requests for every change.
- Keep commits focused and atomic.
- Run lint/type/test checks locally before pushing.
- Update docs when architecture or behavior changes.

## Security

See [`SECURITY.md`](SECURITY.md) for vulnerability reporting.

