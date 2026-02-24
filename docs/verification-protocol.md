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

## 3) Required Reporting Discipline

- If any command was not run, explicitly say it was not run.
- If a command fails, report failure and fix before claiming completion.
- If runtime could not be verified, state the blocker and exact command that failed.

## 4) Pre-Commit Minimum

Before commit/push, ensure:

- Dependencies installed for touched stack(s).
- Relevant checks executed successfully.
- Runtime smoke executed for backend API changes.
- Documentation updated when behavior/setup changed.
