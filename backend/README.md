# DragonWeaver Backend

## Run (local)

1. Install dependencies:
   - `python -m venv .venv && source .venv/bin/activate`
   - `pip install -e .[dev]`
2. Copy env template:
   - `cp .env.example .env`
3. Start API with SQLite (default local mode):
   - `DW_DATABASE_URL=sqlite+aiosqlite:///./dragonweaver.db uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
4. Optional PostgreSQL + pgvector mode (recommended for production/performance):
   - from repo root: `docker compose up -d postgres`
   - then run:
     - `DW_DATABASE_URL=postgresql+asyncpg://dragonweaver:dragonweaver@127.0.0.1:5432/dragonweaver uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

### Key env toggles

- `DW_MEMORY_EMBEDDING_DIMENSIONS` (default: `1536`)
- `DW_MEMORY_AUTO_INGEST_TIMELINE` (default: `true`)

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

- `GET /api/v1/memory/chunks`
  - host-only by story owner
  - lists stored narrative memory chunks
- `POST /api/v1/memory/chunks`
  - host-only by story owner
  - stores narrative memory chunks with vector embeddings
- `POST /api/v1/memory/search`
  - host-only by story owner
  - accepts either `query_embedding` or `query_text` (server hashes text to deterministic embedding)
  - semantic retrieval via pgvector on PostgreSQL (cosine), deterministic fallback on SQLite
  - writes retrieval audit events for traceability (`query_text`, retrieved/applied memory IDs)
- `GET /api/v1/memory/audit`
  - host-only by story owner
  - lists retrieval audit events for a story
- `POST /api/v1/memory/summaries/generate`
  - host-only by story owner
  - generates a deterministic timeline-window summary and stores it in `narrative_summaries`
  - also writes a `summary` memory chunk for downstream retrieval
- `GET /api/v1/memory/summaries`
  - host-only by story owner
  - lists generated narrative summaries

## Timeline Memory Auto-Ingest

- When `DW_MEMORY_AUTO_INGEST_TIMELINE=true`, each created timeline event automatically writes a memory chunk using deterministic embeddings.
- Memory type mapping:
  - `choice_prompt` / `choice_selection` -> `quest`
  - `outcome` -> `summary`
  - `system` -> `rule`
  - all others -> `fact`

## GM Orchestration Context

- `POST /api/v1/orchestration/context`
  - host-only by story owner
  - assembles one RAG payload for GM prompt construction from:
    - semantic memory retrieval
    - recent narrative summaries
    - recent timeline events
  - emits retrieval audit trail and returns `retrieval_audit_id` with the assembled payload
- `POST /api/v1/orchestration/respond`
  - host-only by story owner
  - builds orchestration context and returns a GM response text in one call
  - uses current user settings (`llm_provider`, `llm_model`, `language`) when not overridden
  - can persist generated response as a `gm_prompt` timeline event (`persist_to_timeline=true`)
  - supports synthesized audio output (`audio_ref`, `audio_duration_ms`, `audio_codec`)
  - when persisted, synthesized audio is attached to the timeline event recording and playable in UI
  - current implementation is deterministic and offline-friendly (no paid LLM/TTS provider required)

## SQLite vs PostgreSQL

- SQLite:
  - fully supported for local development and functional RAG behavior
  - vector search uses deterministic in-app cosine similarity fallback
- PostgreSQL + pgvector:
  - recommended for production/performance workloads
  - vector search uses indexed DB-side similarity operations
