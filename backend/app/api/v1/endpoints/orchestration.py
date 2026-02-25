from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.db.models import Story
from app.schemas.orchestration import (
    OrchestrationContextRead,
    OrchestrationContextRequest,
    OrchestrationMemoryItem,
    OrchestrationSummaryItem,
    OrchestrationTimelineItem,
)
from app.services.memory_store import create_retrieval_audit_event
from app.services.rag_context import build_orchestration_context

router = APIRouter(prefix="/orchestration", tags=["orchestration"])


async def _assert_story_owner(story_id: str, current_user: CurrentUser, db: DBSession) -> Story:
    story = await db.scalar(
        select(Story).where(Story.id == story_id, Story.owner_user_id == current_user.id)
    )
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.post("/context", response_model=OrchestrationContextRead)
async def assemble_context(
    payload: OrchestrationContextRequest,
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
) -> OrchestrationContextRead:
    await _assert_story_owner(payload.story_id, current_user, db)

    settings = request.app.state.settings
    bundle = await build_orchestration_context(
        db,
        story_id=payload.story_id,
        query_text=payload.query_text,
        embedding_dimensions=settings.memory_embedding_dimensions,
        memory_limit=payload.memory_limit,
        summary_limit=payload.summary_limit,
        timeline_limit=payload.timeline_limit,
        memory_types=payload.memory_types or None,
    )

    retrieved_ids = [item.chunk.id for item in bundle.retrieved_memory]
    audit = await create_retrieval_audit_event(
        db,
        story_id=payload.story_id,
        query_text=payload.query_text.strip(),
        retrieved_memory_ids=retrieved_ids,
        applied_memory_ids=retrieved_ids,
    )

    return OrchestrationContextRead(
        story_id=payload.story_id,
        query_text=payload.query_text.strip(),
        language=payload.language,
        assembled_at=datetime.now(UTC),
        prompt_context=bundle.prompt_context,
        retrieval_audit_id=audit.id,
        retrieved_memory=[
            OrchestrationMemoryItem(
                id=item.chunk.id,
                memory_type=item.chunk.memory_type,
                content=item.chunk.content,
                similarity=item.similarity,
                source_event_id=item.chunk.source_event_id,
                metadata_json=item.chunk.metadata_json,
                created_at=item.chunk.created_at,
            )
            for item in bundle.retrieved_memory
        ],
        summaries=[
            OrchestrationSummaryItem(
                id=item.id,
                summary_window=item.summary_window,
                summary_text=item.summary_text,
                quality_score=item.quality_score,
                created_at=item.created_at,
            )
            for item in bundle.summaries
        ],
        recent_events=[
            OrchestrationTimelineItem(
                id=item.id,
                event_type=item.event_type,
                text_content=item.text_content,
                language=item.language,
                created_at=item.created_at,
            )
            for item in bundle.timeline_events
        ],
    )
