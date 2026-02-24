from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db import models  # noqa: F401
from app.db.base import Base


async def init_db(engine: AsyncEngine) -> None:
    backend_name = engine.url.get_backend_name()

    async with engine.begin() as conn:
        if backend_name.startswith("postgres"):
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
