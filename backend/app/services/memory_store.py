from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import sqrt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import NarrativeMemoryChunk, NarrativeMemoryType


@dataclass(slots=True)
class MemorySearchMatch:
    chunk: NarrativeMemoryChunk
    similarity: float


def _normalize_vector(value: Sequence[float] | object) -> list[float]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if not isinstance(value, Sequence):
        raise ValueError("Embedding must be a numeric sequence.")
    return [float(item) for item in value]


def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError("Embedding vectors must have the same dimensions.")

    numerator = sum(left * right for left, right in zip(a, b, strict=False))
    a_norm = sqrt(sum(item * item for item in a))
    b_norm = sqrt(sum(item * item for item in b))
    denominator = a_norm * b_norm
    if denominator == 0:
        return 0.0
    return numerator / denominator


async def create_memory_chunk(
    db: AsyncSession,
    *,
    story_id: str,
    memory_type: NarrativeMemoryType,
    content: str,
    embedding: Sequence[float],
    source_event_id: str | None,
    metadata_json: Mapping[str, object],
) -> NarrativeMemoryChunk:
    chunk = NarrativeMemoryChunk(
        story_id=story_id,
        memory_type=memory_type,
        content=content.strip(),
        embedding=_normalize_vector(embedding),
        source_event_id=source_event_id,
        metadata_json=dict(metadata_json),
    )
    db.add(chunk)
    await db.commit()
    await db.refresh(chunk)
    return chunk


async def search_memory_chunks(
    db: AsyncSession,
    *,
    story_id: str,
    query_embedding: Sequence[float],
    limit: int,
    memory_types: Sequence[NarrativeMemoryType] | None = None,
) -> list[MemorySearchMatch]:
    normalized_query = _normalize_vector(query_embedding)
    bind = db.get_bind()
    backend_name = bind.dialect.name if bind is not None else ""

    if backend_name.startswith("postgres"):
        distance_expr = NarrativeMemoryChunk.embedding.cosine_distance(normalized_query)
        statement = (
            select(NarrativeMemoryChunk, distance_expr.label("distance"))
            .where(NarrativeMemoryChunk.story_id == story_id)
            .order_by(distance_expr.asc(), NarrativeMemoryChunk.created_at.desc())
            .limit(limit)
        )
        if memory_types:
            statement = statement.where(NarrativeMemoryChunk.memory_type.in_(memory_types))

        result = await db.execute(statement)
        rows = result.all()
        return [
            MemorySearchMatch(
                chunk=chunk,
                similarity=max(0.0, 1.0 - float(distance)),
            )
            for chunk, distance in rows
        ]

    statement = select(NarrativeMemoryChunk).where(NarrativeMemoryChunk.story_id == story_id)
    if memory_types:
        statement = statement.where(NarrativeMemoryChunk.memory_type.in_(memory_types))
    chunks = (await db.scalars(statement)).all()

    scored: list[MemorySearchMatch] = []
    for chunk in chunks:
        chunk_embedding = _normalize_vector(chunk.embedding)
        if len(chunk_embedding) != len(normalized_query):
            continue
        scored.append(
            MemorySearchMatch(
                chunk=chunk,
                similarity=_cosine_similarity(normalized_query, chunk_embedding),
            )
        )

    scored.sort(key=lambda item: item.similarity, reverse=True)
    return scored[:limit]
