from collections.abc import Sequence
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DBSession
from app.db.models import (
    NarrativeMemoryChunk,
    NarrativeMemoryType,
    NarrativeSummary,
    RetrievalAuditEvent,
    Story,
    TimelineEvent,
)
from app.schemas.memory import (
    MemoryChunkCreate,
    MemoryChunkRead,
    MemorySearchRequest,
    MemorySearchResult,
    MemorySummaryGenerateRequest,
    MemorySummaryRead,
    RetrievalAuditEventRead,
)
from app.services.embedding import hash_text_embedding
from app.services.memory_store import (
    create_memory_chunk,
    create_retrieval_audit_event,
    search_memory_chunks,
)

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


def _to_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _map_summary(item: NarrativeSummary) -> MemorySummaryRead:
    return MemorySummaryRead.model_validate(item)


def _map_audit(item: RetrievalAuditEvent) -> RetrievalAuditEventRead:
    return RetrievalAuditEventRead(
        id=item.id,
        story_id=item.story_id,
        query_text=item.query_text,
        retrieved_memory_ids=_to_string_list(item.retrieved_memory_ids),
        applied_memory_ids=_to_string_list(item.applied_memory_ids),
        created_at=item.created_at,
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


def _event_text(event: TimelineEvent) -> str:
    if event.text_content and event.text_content.strip():
        return event.text_content.strip()
    for transcript in sorted(event.transcripts, key=lambda item: item.timestamp):
        if transcript.content.strip():
            return transcript.content.strip()
    return ""


def _build_story_summary(events: Sequence[TimelineEvent]) -> str:
    if not events:
        return "No timeline events available for this summary window."

    type_counts: dict[str, int] = {}
    highlights: list[str] = []
    for event in events:
        event_key = event.event_type.value
        type_counts[event_key] = type_counts.get(event_key, 0) + 1
        text = _event_text(event)
        if text and len(highlights) < 5:
            highlights.append(f"{event_key}: {text[:220]}")

    counts = ", ".join(f"{name}={count}" for name, count in sorted(type_counts.items()))
    lines = [
        f"Summary generated at {datetime.now(UTC).isoformat()}",
        f"Window events: {len(events)}",
        f"Event mix: {counts}",
    ]
    if highlights:
        lines.append("Highlights:")
        lines.extend(f"- {item}" for item in highlights)

    return "\n".join(lines)


@router.get("/chunks", response_model=list[MemoryChunkRead])
async def list_chunks(
    story_id: str,
    current_user: CurrentUser,
    db: DBSession,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[MemoryChunkRead]:
    await _assert_story_owner(story_id, current_user, db)
    chunks = await db.scalars(
        select(NarrativeMemoryChunk)
        .where(NarrativeMemoryChunk.story_id == story_id)
        .order_by(NarrativeMemoryChunk.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return [_map_chunk(item) for item in chunks.all()]


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
    if payload.query_embedding is not None:
        query_embedding = payload.query_embedding
        _validate_embedding_size(
            embedding=query_embedding,
            expected_size=expected_size,
            field_name="query_embedding",
        )
    else:
        query_embedding = hash_text_embedding(payload.query_text or "", expected_size)

    results = await search_memory_chunks(
        db,
        story_id=payload.story_id,
        query_embedding=query_embedding,
        limit=payload.limit,
        memory_types=payload.memory_types or None,
    )
    response = [
        MemorySearchResult(
            chunk=_map_chunk(item.chunk),
            similarity=item.similarity,
        )
        for item in results
    ]
    query_text = (payload.query_text or "").strip() or "vector-search"
    retrieved_ids = [item.chunk.id for item in results]
    await create_retrieval_audit_event(
        db,
        story_id=payload.story_id,
        query_text=query_text,
        retrieved_memory_ids=retrieved_ids,
        applied_memory_ids=payload.applied_memory_ids,
    )
    return response


@router.post(
    "/summaries/generate",
    response_model=MemorySummaryRead,
    status_code=status.HTTP_201_CREATED,
)
async def generate_summary(
    payload: MemorySummaryGenerateRequest,
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
) -> MemorySummaryRead:
    await _assert_story_owner(payload.story_id, current_user, db)

    events = await db.scalars(
        select(TimelineEvent)
        .where(TimelineEvent.story_id == payload.story_id)
        .options(selectinload(TimelineEvent.transcripts))
        .order_by(TimelineEvent.created_at.desc())
        .limit(payload.max_events)
    )
    selected_events = events.all()
    summary_text = _build_story_summary(selected_events)

    summary = NarrativeSummary(
        story_id=payload.story_id,
        summary_window=payload.summary_window,
        summary_text=summary_text,
        quality_score=None,
    )
    db.add(summary)
    await db.flush()

    embedding_dimensions = request.app.state.settings.memory_embedding_dimensions
    embedding = hash_text_embedding(summary_text, embedding_dimensions)
    await create_memory_chunk(
        db,
        story_id=payload.story_id,
        memory_type=NarrativeMemoryType.summary,
        content=summary_text,
        embedding=embedding,
        source_event_id=selected_events[0].id if selected_events else None,
        metadata_json={
            "generated_from_events": len(selected_events),
            "summary_window": payload.summary_window,
        },
        commit=False,
    )
    await db.commit()
    await db.refresh(summary)
    return _map_summary(summary)


@router.get("/summaries", response_model=list[MemorySummaryRead])
async def list_summaries(
    story_id: str,
    current_user: CurrentUser,
    db: DBSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[MemorySummaryRead]:
    await _assert_story_owner(story_id, current_user, db)
    summaries = await db.scalars(
        select(NarrativeSummary)
        .where(NarrativeSummary.story_id == story_id)
        .order_by(NarrativeSummary.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return [_map_summary(item) for item in summaries.all()]


@router.get("/audit", response_model=list[RetrievalAuditEventRead])
async def list_retrieval_audit(
    story_id: str,
    current_user: CurrentUser,
    db: DBSession,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[RetrievalAuditEventRead]:
    await _assert_story_owner(story_id, current_user, db)
    audits = await db.scalars(
        select(RetrievalAuditEvent)
        .where(RetrievalAuditEvent.story_id == story_id)
        .order_by(RetrievalAuditEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return [_map_audit(item) for item in audits.all()]
