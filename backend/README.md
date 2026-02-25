# DragonWeaver Backend

## Run (local)

1. Install dependencies:
   - `python -m venv .venv && source .venv/bin/activate`
   - `pip install -e .[dev]`
2. Copy env template:
   - `cp .env.example .env`
3. Start PostgreSQL + pgvector:
   - from repo root: `docker compose up -d postgres`
4. Start API:
   - `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

## Verify (mandatory before claiming success)

- `ruff check app tests`
- `mypy app`
- `pytest`

## Runtime Smoke Test

1. Start API:
   - `uvicorn app.main:app --host 127.0.0.1 --port 8000`
2. Verify health:
   - `curl http://127.0.0.1:8000/api/v1/health`
3. Expected:
   - `{"status":"ok","service":"dragonweaver-backend"}`

## Memory Foundation Endpoints

- `POST /api/v1/memory/chunks`
  - host-only by story owner
  - stores narrative memory chunks with vector embeddings
- `POST /api/v1/memory/search`
  - host-only by story owner
  - semantic retrieval via pgvector on PostgreSQL (cosine), deterministic fallback on SQLite
