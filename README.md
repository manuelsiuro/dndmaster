# DragonWeaver

AI-driven multiplayer D&D 5E platform with a backend-authoritative rules engine and LLM narrative orchestration.

## Repository Status

Project planning and architecture are documented and initial code scaffolding is now in place.

- [`docs/implementation-plan.md`](docs/implementation-plan.md)
- [`docs/draft.md`](docs/draft.md)
- [`docs/mvp-timeline-ui-spec.md`](docs/mvp-timeline-ui-spec.md)
- [`docs/verification-protocol.md`](docs/verification-protocol.md)

## Project Layout

- `backend/` FastAPI service (auth, stories, timeline APIs, DB models, tests)
- `frontend/` React + TypeScript app shell (auth/story/timeline MVP view)
- `docs/` planning, specs, specialized agent charters
- `docker-compose.yml` local pgvector-enabled PostgreSQL

## Quick Start

### 1) Run Backend (SQLite default for now)

SQLite is the current default local mode and supports the full app, including RAG fallback.

```bash
DW_DATABASE_URL=sqlite+aiosqlite:///./dragonweaver.db ./start-backend.sh
```

If running manually from `backend/`, use:

```bash
DW_DATABASE_URL=sqlite+aiosqlite:///./dragonweaver.db uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 2) Run Frontend

```bash
./start-frontend.sh
```

Do not use `uvicorn backend.app.main:app` when your cwd is `backend/` (it raises `ModuleNotFoundError: No module named 'backend'`).

### 3) Optional: Start PostgreSQL + pgvector (recommended for production-like perf)

```bash
docker compose up -d postgres
```

Then start backend with:

```bash
DW_DATABASE_URL=postgresql+asyncpg://dragonweaver:dragonweaver@127.0.0.1:5432/dragonweaver ./start-backend.sh
```

If frontend runs on a custom port, pass it so backend CORS is aligned:

```bash
./start-backend.sh --frontend-port 5180
```

If backend runs on a non-default port, pass the API base explicitly:

```bash
./start-frontend.sh --api-base-url http://127.0.0.1:8010/api/v1
```

Always keep backend/frontend ports aligned:

- If frontend port changes, start backend with `--frontend-port`.
- If backend port changes, start frontend with `--api-base-url`.

Default local endpoints:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

## Automated MCP Browser Validation

Run the repeatable Chrome MCP progression flow from repo root:

```bash
npm run test:mcp
```

This command starts backend/frontend, executes an end-to-end host+player session flow in MCP Chrome, validates XP progression sync, and exits non-zero on failure.

## High-Level Principles

- Backend is authoritative for game state and rules.
- LLMs generate narrative and call tools, but do not directly mutate game state.
- SQLite is supported for local development; PostgreSQL + pgvector is the recommended production/performance path.
- Multiplayer, voice interaction, and multilingual support (EN/FR) are mandatory.
- Narrative depth and map polish are release quality gates.

## Development Standards

- Use feature branches and open pull requests for every change.
- Keep commits focused and atomic.
- Follow the mandatory verification protocol before claiming success:
  - install dependencies
  - run checks/tests
  - run runtime smoke tests
  - report exact results
- Do not state "working" unless commands were executed successfully.
- Update docs when architecture or behavior changes.
- For multiplayer/session changes, run a browser E2E smoke (host + player join) before claiming done.
- For voice signaling changes, run backend voice tests (`pytest -q -k voice`) and confirm fallback timeline recording still works.

## Security

See [`SECURITY.md`](SECURITY.md) for vulnerability reporting.
