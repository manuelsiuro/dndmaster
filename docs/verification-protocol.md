# Verification Protocol (Mandatory)

This project uses an execution-first policy:

- Do not claim "working", "fixed", or "validated" unless required commands were actually run.
- Do not assume dependencies are installed. Install them explicitly.
- Every change must include command evidence in local output or PR notes.

## 1) Environment Setup

Run from repository root.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
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
