# Contributing

## Branching

- Default branch: `main`
- Create feature branches from `main`
- Use clear branch names, for example:
  - `feat/multiplayer-lobby`
  - `fix/audio-stream-timeout`
  - `chore/ci-cleanup`

## Commits

Use concise, scoped commit messages:

- `feat(scope): description`
- `fix(scope): description`
- `docs(scope): description`
- `chore(scope): description`

## Pull Requests

- Keep PRs focused on one concern.
- Include tests for behavior changes.
- Update docs for architecture or user-facing changes.
- Follow [`docs/verification-protocol.md`](docs/verification-protocol.md) and include command evidence.
- Complete the PR template checklist.

## Quality Gate Before Merge

- Dependencies installed for touched stack(s)
- Lint passes
- Type checks pass
- Tests pass
- Runtime smoke test passes for backend/API changes
- No secrets in changed files

## No-Assumption Rule

- Never claim "working" or "fixed" without executed verification commands.
- If verification was partial, clearly list what was not executed and why.
