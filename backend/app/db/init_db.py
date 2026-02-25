from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db import models  # noqa: F401
from app.db.base import Base


async def init_db(engine: AsyncEngine, *, memory_embedding_dimensions: int = 1536) -> None:
    backend_name = engine.url.get_backend_name()

    async with engine.begin() as conn:
        if backend_name.startswith("postgres"):
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        if backend_name.startswith("postgres"):
            lists = max(10, min(200, memory_embedding_dimensions // 10))
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_memory_chunk_embedding_cosine "
                    "ON narrative_memory_chunks "
                    "USING ivfflat (embedding vector_cosine_ops) "
                    f"WITH (lists = {lists})"
                )
            )
