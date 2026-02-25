from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.db.models import Story, TimelineEvent, TimelineEventType, UserSettings
from app.schemas.orchestration import (
    OrchestrationContextRead,
    OrchestrationContextRequest,
    OrchestrationMemoryItem,
    OrchestrationRespondRead,
    OrchestrationRespondRequest,
    OrchestrationSummaryItem,
    OrchestrationTimelineItem,
)
from app.services.gm_response import compose_gm_response
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


async def _get_or_create_user_settings(current_user: CurrentUser, db: DBSession) -> UserSettings:
    settings = await db.scalar(select(UserSettings).where(UserSettings.user_id == current_user.id))
    if settings is not None:
        return settings

    settings = UserSettings(user_id=current_user.id)
    db.add(settings)
    await db.commit()
    await db.refresh(settings)
    return settings


def _to_context_read(
    *,
    story_id: str,
    query_text: str,
    language: str,
    retrieval_audit_id: str,
    assembled_at: datetime,
    prompt_context: str,
    retrieved_memory_items: list[OrchestrationMemoryItem],
    summary_items: list[OrchestrationSummaryItem],
    timeline_items: list[OrchestrationTimelineItem],
) -> OrchestrationContextRead:
    return OrchestrationContextRead(
        story_id=story_id,
        query_text=query_text,
        language=language,
        assembled_at=assembled_at,
        prompt_context=prompt_context,
        retrieval_audit_id=retrieval_audit_id,
        retrieved_memory=retrieved_memory_items,
        summaries=summary_items,
        recent_events=timeline_items,
    )


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

    return _to_context_read(
        story_id=payload.story_id,
        query_text=payload.query_text.strip(),
        language=payload.language,
        retrieval_audit_id=audit.id,
        assembled_at=datetime.now(UTC),
        prompt_context=bundle.prompt_context,
        retrieved_memory_items=[
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
        summary_items=[
            OrchestrationSummaryItem(
                id=item.id,
                summary_window=item.summary_window,
                summary_text=item.summary_text,
                quality_score=item.quality_score,
                created_at=item.created_at,
            )
            for item in bundle.summaries
        ],
        timeline_items=[
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


@router.post("/respond", response_model=OrchestrationRespondRead)
async def respond_as_gm(
    payload: OrchestrationRespondRequest,
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
) -> OrchestrationRespondRead:
    await _assert_story_owner(payload.story_id, current_user, db)
    user_settings = await _get_or_create_user_settings(current_user, db)

    settings = request.app.state.settings
    language = (payload.language or user_settings.language).strip().lower() or "en"
    assembled_at = datetime.now(UTC)
    bundle = await build_orchestration_context(
        db,
        story_id=payload.story_id,
        query_text=payload.player_input,
        embedding_dimensions=settings.memory_embedding_dimensions,
        memory_limit=payload.memory_limit,
        summary_limit=payload.summary_limit,
        timeline_limit=payload.timeline_limit,
        memory_types=payload.memory_types or None,
    )

    retrieved_items = [
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
    ]
    summary_items = [
        OrchestrationSummaryItem(
            id=item.id,
            summary_window=item.summary_window,
            summary_text=item.summary_text,
            quality_score=item.quality_score,
            created_at=item.created_at,
        )
        for item in bundle.summaries
    ]
    timeline_items = [
        OrchestrationTimelineItem(
            id=item.id,
            event_type=item.event_type,
            text_content=item.text_content,
            language=item.language,
            created_at=item.created_at,
        )
        for item in bundle.timeline_events
    ]
    retrieved_ids = [item.id for item in retrieved_items]
    audit = await create_retrieval_audit_event(
        db,
        story_id=payload.story_id,
        query_text=payload.player_input.strip(),
        retrieved_memory_ids=retrieved_ids,
        applied_memory_ids=retrieved_ids,
        commit=not payload.persist_to_timeline,
    )

    provider = user_settings.llm_provider
    model = (user_settings.llm_model or "").strip() or "auto"
    response_text = compose_gm_response(
        provider=provider,
        model=model,
        language=language,
        player_input=payload.player_input,
        prompt_context=bundle.prompt_context,
    )

    timeline_event_id: str | None = None
    if payload.persist_to_timeline:
        event = TimelineEvent(
            story_id=payload.story_id,
            actor_id=current_user.id,
            event_type=TimelineEventType.gm_prompt,
            text_content=response_text,
            language=language,
            source_event_id=None,
            metadata_json={
                "orchestration": "gm_response",
                "provider": provider,
                "model": model,
                "retrieval_audit_id": audit.id,
            },
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        timeline_event_id = event.id

    context = _to_context_read(
        story_id=payload.story_id,
        query_text=payload.player_input.strip(),
        language=language,
        retrieval_audit_id=audit.id,
        assembled_at=assembled_at,
        prompt_context=bundle.prompt_context,
        retrieved_memory_items=retrieved_items,
        summary_items=summary_items,
        timeline_items=timeline_items,
    )
    return OrchestrationRespondRead(
        story_id=payload.story_id,
        provider=provider,
        model=model,
        language=language,
        response_text=response_text,
        timeline_event_id=timeline_event_id,
        context=context,
    )
