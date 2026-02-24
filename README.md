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

### 1) Start PostgreSQL with pgvector

```bash
docker compose up -d postgres
```

### 2) Run Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3) Run Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Default local endpoints:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

## High-Level Principles

- Backend is authoritative for game state and rules.
- LLMs generate narrative and call tools, but do not directly mutate game state.
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

## Security

See [`SECURITY.md`](SECURITY.md) for vulnerability reporting.
