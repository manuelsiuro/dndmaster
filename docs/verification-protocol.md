# Verification Protocol (Mandatory)

This project uses an execution-first policy:

- Do not claim "working", "fixed", or "validated" unless required commands were actually run.
- Do not assume dependencies are installed. Install them explicitly.
- Every change must include command evidence in local output or PR notes.

## 1) Environment Setup

Run from repository root.

### Infrastructure (optional for SQLite mode)

```bash
docker compose up -d postgres
```

Use infrastructure when:

- validating PostgreSQL + pgvector behavior
- running `tests/test_memory_postgres.py`

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

SQLite-first local run (current default):

```bash
export DW_DATABASE_URL=sqlite+aiosqlite:///./dragonweaver.db
```

PostgreSQL + pgvector run:

```bash
export DW_DATABASE_URL=postgresql+asyncpg://dragonweaver:dragonweaver@127.0.0.1:5432/dragonweaver
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
```

## 2) Mandatory Verification Before Claiming Success

Prefer root scripts for runtime startup to avoid command drift:

```bash
./start-backend.sh
./start-frontend.sh
```

### Backend static and tests

```bash
cd backend
source .venv/bin/activate
ruff check app tests
mypy app
pytest
```

### Backend PostgreSQL + pgvector integration test (recommended for memory/orchestration changes)

```bash
cd backend
source .venv/bin/activate
TEST_POSTGRES_URL=postgresql+asyncpg://dragonweaver:dragonweaver@127.0.0.1:5432/dragonweaver pytest -q tests/test_memory_postgres.py
```

### Backend runtime smoke test

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Important:

- If cwd is `backend/`, do not run `uvicorn backend.app.main:app`.
- For custom frontend port, run backend with `./start-backend.sh --frontend-port <port>`.
- For custom backend port, run frontend with `./start-frontend.sh --api-base-url http://127.0.0.1:<port>/api/v1`.

In another shell:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Expected response:

```json
{"status":"ok","service":"dragonweaver-backend"}
```

### Frontend build check

```bash
cd frontend
npm run build
```

### Browser E2E smoke for sessions (mandatory when touching auth/session/join UI)

Verify this exact path in a real browser (manual or MCP Chrome):

1. Register host and confirm `Authenticated` appears.
2. Create a story.
3. Create a 4-player session and start it.
4. Confirm join token is visible.
5. In a second page, register a second player and join with token.
6. Refresh host session and confirm `ACTIVE • 1/4 players` plus player email appears.
7. Confirm no user-facing error banner remains after successful player join.

### Automated MCP Chrome regression (repeatable command)

Run this from repository root:

```bash
npm run test:mcp
```

What it does:

1. Starts backend and frontend with root startup scripts.
2. Runs a Codex MCP Chrome end-to-end validation (host + player) for:
   - story/session creation
   - join token flow
   - multiplayer join verification
   - host XP award to player
   - player `My Progression` sync verification
3. Enforces PASS/FAIL by parsing a final `RESULT: ...` line.

Notes:

- Requires `codex` CLI and configured `chrome-devtools` MCP server.
- Single-active-device policy is honored by using an isolated browser context for the player.
- Artifacts:
  - `/tmp/codex_mcp_progression_test.txt`
  - `/tmp/dw-mcp-backend.log`
  - `/tmp/dw-mcp-frontend.log`

## 3) Required Reporting Discipline

- If any command was not run, explicitly say it was not run.
- If a command fails, report failure and fix before claiming completion.
- If runtime could not be verified, state the blocker and exact command that failed.

## 4) Pre-Commit Minimum

Before commit/push, ensure:

- Dependencies installed for touched stack(s).
- Relevant checks executed successfully.
- Runtime smoke executed for backend API changes.
- Browser E2E smoke executed for session/join/auth changes.
- Documentation updated when behavior/setup changed.

## 5) Known Pitfalls (Do Not Repeat)

- Wrong backend import path: `uvicorn backend.app.main:app` fails when started inside `backend/`.
- Port/CORS mismatch: changing frontend/backend ports without matching script flags causes preflight and fetch failures.
- Session join false-negative UX: successful join must not leave stale error text visible to player.
