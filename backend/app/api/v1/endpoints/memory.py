from collections.abc import Sequence

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.db.models import NarrativeMemoryChunk, Story
from app.schemas.memory import (
    MemoryChunkCreate,
    MemoryChunkRead,
    MemorySearchRequest,
    MemorySearchResult,
)
from app.services.memory_store import create_memory_chunk, search_memory_chunks

router = APIRouter(prefix="/memory", tags=["memory"])


def _to_embedding_list(value: Sequence[float] | object) -> list[float]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if not isinstance(value, Sequence):
        raise ValueError("Embedding is not a numeric sequence.")
    return [float(item) for item in value]


def _map_chunk(item: NarrativeMemoryChunk) -> MemoryChunkRead:
    return MemoryChunkRead(
        id=item.id,
        story_id=item.story_id,
        memory_type=item.memory_type,
        content=item.content,
        embedding=_to_embedding_list(item.embedding),
        source_event_id=item.source_event_id,
        metadata_json=item.metadata_json,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


async def _assert_story_owner(story_id: str, current_user: CurrentUser, db: DBSession) -> Story:
    story = await db.scalar(
        select(Story).where(Story.id == story_id, Story.owner_user_id == current_user.id)
    )
    if story is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")
    return story


def _validate_embedding_size(
    *,
    embedding: Sequence[float],
    expected_size: int,
    field_name: str,
) -> None:
    if len(embedding) != expected_size:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must contain exactly {expected_size} dimensions",
        )


@router.post("/chunks", response_model=MemoryChunkRead, status_code=status.HTTP_201_CREATED)
async def create_chunk(
    payload: MemoryChunkCreate,
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
) -> MemoryChunkRead:
    await _assert_story_owner(payload.story_id, current_user, db)
    expected_size = request.app.state.settings.memory_embedding_dimensions
    _validate_embedding_size(
        embedding=payload.embedding,
        expected_size=expected_size,
        field_name="embedding",
    )

    created = await create_memory_chunk(
        db,
        story_id=payload.story_id,
        memory_type=payload.memory_type,
        content=payload.content,
        embedding=payload.embedding,
        source_event_id=payload.source_event_id,
        metadata_json=payload.metadata_json,
    )
    return _map_chunk(created)


@router.post("/search", response_model=list[MemorySearchResult])
async def search_chunks(
    payload: MemorySearchRequest,
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
) -> list[MemorySearchResult]:
    await _assert_story_owner(payload.story_id, current_user, db)
    expected_size = request.app.state.settings.memory_embedding_dimensions
    _validate_embedding_size(
        embedding=payload.query_embedding,
        expected_size=expected_size,
        field_name="query_embedding",
    )

    results = await search_memory_chunks(
        db,
        story_id=payload.story_id,
        query_embedding=payload.query_embedding,
        limit=payload.limit,
        memory_types=payload.memory_types or None,
    )

    return [
        MemorySearchResult(
            chunk=_map_chunk(item.chunk),
            similarity=item.similarity,
        )
        for item in results
    ]
